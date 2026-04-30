#!/usr/bin/env python3
"""
load_profile.py — Load and parse the MarketCheck dealer profile.

Reads the `marketcheck-profile.md` memory file (YAML frontmatter + raw JSON body)
from one of the conventional search paths, merges the two sources (frontmatter
preferred for the fields it carries, JSON body as the fallback for everything
else), and emits a canonical profile JSON to stdout.

Country is normalised to uppercase before validation. Country-inapplicable
location fields are zeroed after merge (US profiles drop `postcode`; UK
profiles drop `zip`, `state`, `msa_code`) so body-leaked cross-country values
do not poison the downstream US/UK branch.

Non-zero exit codes signal the skill to halt and ask the user for minimum
inputs — or, on exit 2, to read the raw profile file and parse it manually
rather than trust a lenient fallback.

Exit codes:
  0  Profile loaded successfully (JSON on stdout)
  1  Profile file not found, or not readable
  2  Profile frontmatter YAML is malformed (PyYAML error) — the calling
     skill should read the raw file and parse it manually
  3  Required field missing (country, zip/postcode, state-for-US)
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sys
import time
from pathlib import Path
from typing import Any


class ProfileParseError(Exception):
    """Raised when frontmatter YAML fails to parse under PyYAML.

    main() catches this and exits with code 2, signalling the calling skill
    to read the raw profile file and parse it manually rather than trusting
    a lenient fallback parse.
    """


# Schema version this loader expects. Bumped when frontmatter shape changes
# in a backwards-incompatible way. G6 — older profiles aren't hard-rejected;
# we log a warning on mismatch and proceed on best-effort terms.
PROFILE_SCHEMA_VERSION = "1.0.0"


SEARCH_PATHS = [
    # Project memory file — primary location
    Path("./marketcheck-profile.md"),
    Path("./.claude/marketcheck-profile.md"),
    # Legacy locations — migration support only.
    # Primary path is ./marketcheck-profile.md (project memory file).
    Path(os.path.expanduser("~/.claude/marketcheck/profile.md")),
    Path(os.path.expanduser("~/.claude/marketcheck-profile.md")),
]

# Allow the caller to override via --file
def resolve_profile_path(argv: list[str]) -> Path | None:
    if "--file" in argv:
        idx = argv.index("--file")
        if idx + 1 < len(argv):
            return Path(argv[idx + 1])
    for candidate in SEARCH_PATHS:
        if candidate.exists():
            return candidate
    return None


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file into (frontmatter_dict, body_text).

    Returns ({}, text) when no frontmatter is present.

    Raises ProfileParseError when PyYAML is available but fails to parse the
    frontmatter. Only falls back to _minimal_yaml when PyYAML itself cannot
    be imported — malformed YAML is not silently accepted, so the caller
    sees a clear exit 2 rather than an output shaped from garbage.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    block = m.group(1)
    body = text[m.end():]
    try:
        import yaml  # PyYAML is broadly available
    except ImportError:
        # Only an environment without PyYAML uses the lenient minimal parser.
        # F3 — harden: scan for constructs the minimal parser mis-handles and
        # refuse to parse rather than produce a silent mis-parse.
        _guard_minimal_yaml(block)
        sys.stderr.write(
            "load_profile: WARNING — PyYAML not installed; using minimal "
            "YAML fallback. Install PyYAML for robust parsing.\n"
        )
        return _minimal_yaml(block), body
    try:
        # safety: yaml.safe_load is required — never use yaml.load or yaml.Loader,
        # which would evaluate arbitrary object tags in the profile text.
        fm = yaml.safe_load(block) or {}
    except yaml.YAMLError as exc:
        raise ProfileParseError(str(exc)) from exc
    if not isinstance(fm, dict):
        fm = {}
    return fm, body


def _guard_minimal_yaml(block: str) -> None:
    """Reject YAML features the minimal parser silently mis-handles.

    F3 — rather than misparse anchors, block scalars, multi-line strings, or
    flow-style objects (all of which the minimal parser would silently drop
    or mangle), raise ProfileParseError so the caller sees a clear error
    code instead of a garbage-shaped profile.
    """
    for lineno, raw in enumerate(block.splitlines(), start=1):
        # Strip quoted strings so we don't false-positive on values containing
        # these characters.
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Anchors (&name) and aliases (*name) are both unsupported
        if "&" in stripped or ("*" in stripped and not stripped.startswith("*#")):
            # Allow '*' inside quoted strings — crude check: line-starts-with
            _key_tail = stripped.split(":", 1)[-1].strip()
            if _key_tail.startswith("&") or _key_tail.startswith("*"):
                raise ProfileParseError(
                    f"minimal YAML parser cannot handle anchors/aliases "
                    f"(line {lineno}: {stripped!r}); install PyYAML"
                )
        # Block scalars `|` or `>` at end of line
        if stripped.endswith("|") or stripped.endswith(">") or stripped.endswith("|-") or stripped.endswith(">-"):
            raise ProfileParseError(
                f"minimal YAML parser cannot handle block scalars "
                f"(line {lineno}: {stripped!r}); install PyYAML"
            )
        # Flow-style objects: `key: {a: 1, b: 2}` after a colon
        if ":" in stripped:
            value_part = stripped.split(":", 1)[1].strip()
            if value_part.startswith("{") and not value_part.endswith("}"):
                raise ProfileParseError(
                    f"minimal YAML parser cannot handle multi-line flow objects "
                    f"(line {lineno}: {stripped!r}); install PyYAML"
                )
            if value_part.startswith("{"):
                raise ProfileParseError(
                    f"minimal YAML parser cannot handle flow-style maps "
                    f"(line {lineno}: {stripped!r}); install PyYAML"
                )


def _minimal_yaml(text: str) -> dict[str, Any]:
    """Tiny YAML subset parser for flat key/value and two-level nested maps.

    Only supports:
      key: value
      key:
        nested: value
    and arrays in bracket form: key: [a, b, c].

    F3 — hardened by `_guard_minimal_yaml` which refuses to run the parser
    on input containing anchors, block scalars, or flow-style maps.
    """
    out: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(0, out)]
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        # Pop stack entries at or deeper than this indent
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else out
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().strip('"').strip("'")
        value = value.strip()
        if value == "":
            # Start a nested map
            nested: dict[str, Any] = {}
            parent[key] = nested
            stack.append((indent, nested))
        else:
            parent[key] = _coerce(value)
    return out


def _coerce(s: str) -> Any:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.lower() in ("null", "~", ""):
        return None
    # Numbers
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        pass
    # Bracketed lists — respect quoted strings so commas inside them aren't splits
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_coerce(p.strip()) for p in _split_list_items(inner)]
    return s


def _split_list_items(inner: str) -> list[str]:
    """Split a comma-separated list respecting quoted string boundaries."""
    items: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escape = False
    for ch in inner:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\" and quote:
            escape = True
            current.append(ch)
            continue
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            current.append(ch)
            continue
        if ch == ",":
            items.append("".join(current))
            current = []
            continue
        current.append(ch)
    if current:
        items.append("".join(current))
    return items


def parse_json_body(body: str) -> dict[str, Any]:
    """Extract the first JSON object from the body text.

    The body often contains a formatted JSON blob. We scan forward for the
    first '{' and match braces to find the end.
    """
    stripped = body.strip()
    if not stripped:
        return {}
    # Find first '{'
    start = stripped.find("{")
    if start == -1:
        return {}
    depth = 0
    end = -1
    in_str = False
    escape = False
    for i, ch in enumerate(stripped[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return {}
    try:
        return json.loads(stripped[start:end])
    except json.JSONDecodeError:
        return {}


def merge(fm: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    """Merge frontmatter and JSON body into a canonical profile shape.

    Frontmatter wins on conflict (it's the "curated" view); body provides
    fields that aren't in frontmatter (e.g., `seller_phone`, full address).

    Post-merge, country is normalised to uppercase and country-inapplicable
    location fields are zeroed (see `_strip_cross_country_fields`). Onboarding
    metadata (`user`, `schema_version`, `created_at`, `updated_at`) is
    passed through alongside the core blocks so audit/stale-profile tooling
    has something to read.
    """
    # The frontmatter shape in the profile has nested dealer/location/preferences
    # blocks. The body has the flat MarketCheck dealer record.
    result: dict[str, Any] = {
        "dealer": {},
        "location": {},
        "preferences": {},
        "user": {},
        "schema_version": None,
        "created_at": None,
        "updated_at": None,
    }

    # Populate from frontmatter first
    if isinstance(fm.get("dealer"), dict):
        result["dealer"].update(fm["dealer"])
    if isinstance(fm.get("location"), dict):
        result["location"].update(fm["location"])
    if isinstance(fm.get("preferences"), dict):
        result["preferences"].update(fm["preferences"])
    if isinstance(fm.get("user"), dict):
        result["user"].update(fm["user"])

    # Fill from body where frontmatter was silent
    def _get(k: str) -> Any:
        return body.get(k) if isinstance(body, dict) else None

    d = result["dealer"]
    d.setdefault("id", _get("dealer_id"))
    d.setdefault("name", _get("seller_name"))
    d.setdefault("dealer_type", _get("dealer_type"))
    d.setdefault("franchise_brands", _get("franchise_brands"))
    d.setdefault("cpo_program", _get("cpo_program"))
    d.setdefault("cpo_certification_cost", _get("cpo_certification_cost"))
    d.setdefault("phone", _get("seller_phone"))
    d.setdefault("email", _get("seller_email"))
    d.setdefault("inventory_url", _get("inventory_url"))
    d.setdefault("listing_count", _get("listing_count"))
    d.setdefault("street", _get("street"))

    loc = result["location"]
    loc.setdefault("country", _get("country"))
    # Normalise country to uppercase before any downstream comparison
    if loc.get("country"):
        loc["country"] = str(loc["country"]).strip().upper()
    loc.setdefault("state", _get("state"))
    loc.setdefault("city", _get("city"))
    loc.setdefault("zip", _get("zip") or _get("postcode"))
    loc.setdefault("postcode", _get("postcode") or _get("zip"))
    loc.setdefault("msa_code", _get("msa_code"))
    lat = _get("latitude")
    lon = _get("longitude")
    try:
        loc.setdefault("latitude", float(lat) if lat is not None else None)
        loc.setdefault("longitude", float(lon) if lon is not None else None)
    except (TypeError, ValueError):
        loc.setdefault("latitude", None)
        loc.setdefault("longitude", None)

    # Normalise zip / postcode shape (trim whitespace, uppercase UK/CA postcodes,
    # strip ZIP+4 suffix on US ZIPs). Applied before cross-country stripping so
    # the kept value is clean.
    _normalize_location(loc)

    # Zero country-inapplicable fields so body-leaked values don't poison the
    # downstream US/UK/CA branch.
    _strip_cross_country_fields(loc)

    prefs = result["preferences"]
    body_prefs = body.get("preferences") if isinstance(body, dict) else None
    if isinstance(body_prefs, dict):
        prefs.setdefault("default_radius_miles", body_prefs.get("default_radius_miles"))
        prefs.setdefault("default_inventory_type", body_prefs.get("default_inventory_type"))
        if isinstance(body_prefs.get("dom_thresholds"), dict):
            prefs.setdefault("dom_thresholds", body_prefs["dom_thresholds"])

    # Defaults
    prefs.setdefault("default_radius_miles", 50)
    prefs.setdefault("default_inventory_type", "used")
    prefs.setdefault("dom_thresholds", {"fresh": 30, "aging": 60})

    # Passthrough onboarding metadata — not consumed by the pricer skill, but
    # preserved so audit / stale-profile tooling has something to read.
    for key in ("schema_version", "created_at", "updated_at"):
        if fm.get(key) is not None:
            result[key] = fm[key]
        elif isinstance(body, dict) and body.get(key) is not None:
            result[key] = body[key]

    return result


def _normalize_location(loc: dict[str, Any]) -> None:
    """Normalise zip / postcode / state shape in place.

    - Trim whitespace on any string field.
    - US ZIPs: strip "90247-1234" → "90247" (drop ZIP+4 suffix).
    - UK / CA postcodes: uppercase.
    - State / region: uppercase 2-letter codes.
    Malformed values are preserved as-is and caught by validate().
    """
    country = str(loc.get("country") or "").strip().upper()
    for key in ("zip", "postcode", "state", "region", "city"):
        val = loc.get(key)
        if isinstance(val, str):
            loc[key] = val.strip()

    if country == "US":
        z = loc.get("zip")
        if isinstance(z, str) and "-" in z:
            # ZIP+4: keep the 5-digit head, drop the +4 suffix
            loc["zip"] = z.split("-", 1)[0]
        s = loc.get("state")
        if isinstance(s, str):
            loc["state"] = s.upper()
    elif country == "UK":
        p = loc.get("postcode")
        if isinstance(p, str):
            # Canonical UK postcode form: uppercase, single space before the
            # last 3 chars (e.g. "sw1a1aa" → "SW1A 1AA"). Normalise to upper +
            # collapse internal whitespace — the tool accepts either.
            loc["postcode"] = " ".join(p.upper().split())
    elif country == "CA":
        # Canadian postcodes arrive in the `postcode` slot from onboarding;
        # move into `zip` for downstream tool calls (search_active_cars uses
        # the `zip` parameter for both US and Canada).
        if not loc.get("zip") and loc.get("postcode"):
            loc["zip"] = loc["postcode"]
        z = loc.get("zip")
        if isinstance(z, str):
            loc["zip"] = " ".join(z.upper().split())
        s = loc.get("state")
        if isinstance(s, str):
            loc["state"] = s.upper()


def _strip_cross_country_fields(loc: dict[str, Any]) -> None:
    """Zero location fields that don't apply to the profile's country.

    US / CA profiles don't use `postcode`; UK profiles don't use `zip`, `state`,
    or `msa_code`. The per-country slot is preserved; the cross-country slot
    is cleared.
    """
    country = loc.get("country")
    if country in ("US", "CA"):
        loc["postcode"] = None
        if country == "CA":
            # Canada has provinces, not states, and no MSA codes.
            loc["msa_code"] = None
    elif country == "UK":
        loc["zip"] = None
        loc["state"] = None
        loc["msa_code"] = None


def validate(profile: dict[str, Any]) -> tuple[bool, str | None]:
    country = (profile.get("location") or {}).get("country")
    if not country:
        return False, "location.country is required"
    if country not in ("US", "UK", "CA"):
        return False, f"location.country must be one of US / UK / CA (got {country!r})"
    zip_or_postcode = (profile.get("location") or {}).get("zip") or \
                      (profile.get("location") or {}).get("postcode")
    if not zip_or_postcode:
        return False, "location.zip (or location.postcode) is required"
    if country == "US":
        state = (profile.get("location") or {}).get("state")
        if not state:
            return False, "location.state is required for US profiles"
    return True, None


def main(argv: list[str]) -> int:
    path = resolve_profile_path(argv)
    if path is None:
        sys.stderr.write(
            "load_profile: no marketcheck-profile.md found in any search path. "
            "Run /onboarding or pass --file <path>.\n"
        )
        return 1

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"load_profile: cannot read {path}: {exc}\n")
        return 1

    try:
        fm, body = parse_frontmatter(text)
    except ProfileParseError as exc:
        sys.stderr.write(
            f"load_profile: frontmatter YAML is malformed in {path}: {exc}\n"
            f"load_profile: raw profile preserved at {path} — "
            "the calling skill can parse manually.\n"
        )
        return 2

    body_json = parse_json_body(body)
    profile = merge(fm, body_json)
    ok, error = validate(profile)
    if not ok:
        sys.stderr.write(f"load_profile: profile validation failed: {error}\n")
        return 3

    # G6 — schema-version check. Mismatch warns but does not block; the skill
    # may have evolved past the profile without breaking the fields it reads,
    # and refusing would lock out valid users.
    profile_schema = profile.get("schema_version")
    if profile_schema and str(profile_schema) != PROFILE_SCHEMA_VERSION:
        sys.stderr.write(
            f"load_profile: WARNING — profile schema_version {profile_schema!r} "
            f"does not match expected {PROFILE_SCHEMA_VERSION!r}. "
            f"Proceeding on best-effort; re-run /onboarding to upgrade.\n"
        )

    # Compute derived session values. dealer_type is NOT defaulted — a missing
    # value emits None and the calling skill halts to ask the user. Silent
    # defaults (e.g. "independent") would ship franchise dealers independent-
    # channel pricing advice without any signal.
    dealer_type_raw = (profile.get("dealer") or {}).get("dealer_type")
    if dealer_type_raw:
        dealer_type_lower = str(dealer_type_raw).lower()
        dealer_type_title = str(dealer_type_raw).title()
        dealer_type_opposite_lower = (
            "independent" if dealer_type_lower == "franchise" else "franchise"
        )
    else:
        dealer_type_lower = None
        dealer_type_title = None
        dealer_type_opposite_lower = None
    # car_type resolution. When the profile stores "both", the calling skill
    # must halt and ask the user which inventory type to price-check. The
    # answer is passed back via --car-type-override so subsequent re-reads of
    # the profile (after compaction, or from another step in the same session)
    # emit the resolved value in session.car_type_resolved and the skill
    # doesn't have to re-ask. Accepts "used" or "new"; any other value is
    # silently dropped (the skill's halt-and-ask path handles "both" / absent).
    car_type_raw = (profile.get("preferences") or {}).get("default_inventory_type")
    override = _car_type_override(argv)
    if override in ("used", "new"):
        car_type_resolved = override
    elif car_type_raw in ("used", "new"):
        car_type_resolved = car_type_raw
    else:
        car_type_resolved = None  # "both" or absent — skill halts and asks

    # Unique scratch-directory ID for this skill flow. Two concurrent
    # invocations of the skill see different run_ids and cannot collide on
    # /tmp/marketcheck/<run_id>/. Pass --run-id <previously-emitted> on
    # mid-session re-runs (e.g., after compaction) to preserve the scratch
    # dir; mirror of the --car-type-override re-run pattern.
    run_id = _run_id_override(argv) or _generate_run_id()

    profile["session"] = {
        "dealer_type_lower": dealer_type_lower,
        "dealer_type_title": dealer_type_title,
        # Binary flip for every CONTEXT (cross-channel) predict call — read this
        # verbatim at call sites; do not re-derive per call.
        "dealer_type_opposite_lower": dealer_type_opposite_lower,
        "radius_mi_clamped": min(
            int((profile.get("preferences") or {}).get("default_radius_miles") or 50),
            100,
        ),
        "car_type_resolved": car_type_resolved,
        "profile_path": str(path),
        "run_id": run_id,
    }

    json.dump(profile, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def _car_type_override(argv: list[str]) -> str | None:
    """Extract --car-type-override value from argv. Returns the (lower-cased)
    string when present, None otherwise. Invalid values return None — the
    caller's fallback logic handles that."""
    if "--car-type-override" not in argv:
        return None
    idx = argv.index("--car-type-override")
    if idx + 1 >= len(argv):
        return None
    return str(argv[idx + 1]).strip().lower()


def _generate_run_id() -> str:
    """Return a unique scratch-dir identifier for this skill flow.

    Format: ``cpr-<unix-epoch-seconds>-<8 hex chars>``. The timestamp prefix
    keeps /tmp/marketcheck/ listings sortable and human-debuggable; the
    random suffix gives 2^32 collision space within the same second — even
    1000 concurrent invocations per second collide with negligible
    probability over the lifetime of the universe.
    """
    return f"cpr-{int(time.time())}-{secrets.token_hex(4)}"


_RUN_ID_VALID = re.compile(r"^[A-Za-z0-9_-]+$")


def _run_id_override(argv: list[str]) -> str | None:
    """Extract --run-id <id> from argv, validating against path-traversal.

    Mirror of _car_type_override above plus the persist_response.py:64-65
    safety guard. Returns the validated run_id, or None when absent / invalid
    so the caller falls back to _generate_run_id() — never propagate a tainted
    ID into a /tmp/ subpath.

    Validation: only ``[A-Za-z0-9_-]``, with explicit rejection of ``/`` and
    ``..`` for defense-in-depth and a clearer stderr message when the regex
    would already have caught them.
    """
    if "--run-id" not in argv:
        return None
    idx = argv.index("--run-id")
    if idx + 1 >= len(argv):
        return None
    val = argv[idx + 1].strip()
    if not val:
        return None
    if "/" in val or ".." in val or not _RUN_ID_VALID.match(val):
        sys.stderr.write(
            f"load_profile: WARNING — --run-id {val!r} contains invalid "
            "characters; regenerating a fresh run_id.\n"
        )
        return None
    return val


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
