#!/usr/bin/env python3
"""
load_profile.py — Load and parse the MarketCheck appraiser profile.

Reads the `marketcheck-profile.md` memory file (YAML frontmatter + raw JSON body)
from one of the conventional search paths, merges the two sources (frontmatter
preferred for the fields it carries, JSON body as the fallback for everything
else), and emits a canonical profile JSON to stdout.

Country is normalised to uppercase before validation. Country-inapplicable
location fields are zeroed after merge (US profiles drop `postcode`; UK
profiles drop `zip` and `state`) so body-leaked cross-country values do not
poison the downstream US/UK branch.

Profile schema (appraiser plugin per plugins/appraiser/CLAUDE.md):
  user.name, user.company
  appraiser.specialization        — trade-in / insurance / estate_legal / fleet / general
  appraiser.min_comp_count        — default 10
  location.country                — US | UK
  location.{zip,postcode,state,region,city}
  preferences.default_radius_miles — default 75

The depreciation-tracker skill is US-only (every workflow depends on
`get_sold_summary`, which has no UK variant); a UK profile is loaded, but
the skill halts before any MCP call and renders the canonical UK halt
message from `references/country-uk.md`. The loader still emits the
location.country field so the skill can branch.

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
# in a backwards-incompatible way. Older profiles aren't hard-rejected;
# we log a warning on mismatch and proceed on best-effort terms.
PROFILE_SCHEMA_VERSION = "2.0"


SEARCH_PATHS = [
    # Project memory file — primary location
    Path("./marketcheck-profile.md"),
    Path("./.claude/marketcheck-profile.md"),
    # Legacy locations — migration support only.
    # Primary path is ./marketcheck-profile.md (project memory file).
    Path(os.path.expanduser("~/.claude/marketcheck/profile.md")),
    Path(os.path.expanduser("~/.claude/marketcheck-profile.md")),
]


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
    """Reject YAML features the minimal parser silently mis-handles."""
    for lineno, raw in enumerate(block.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "&" in stripped or ("*" in stripped and not stripped.startswith("*#")):
            _key_tail = stripped.split(":", 1)[-1].strip()
            if _key_tail.startswith("&") or _key_tail.startswith("*"):
                raise ProfileParseError(
                    f"minimal YAML parser cannot handle anchors/aliases "
                    f"(line {lineno}: {stripped!r}); install PyYAML"
                )
        if stripped.endswith("|") or stripped.endswith(">") or stripped.endswith("|-") or stripped.endswith(">-"):
            raise ProfileParseError(
                f"minimal YAML parser cannot handle block scalars "
                f"(line {lineno}: {stripped!r}); install PyYAML"
            )
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
    """Tiny YAML subset parser for flat key/value and two-level nested maps."""
    out: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(0, out)]
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
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
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        pass
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_coerce(p.strip()) for p in _split_list_items(inner)]
    return s


def _split_list_items(inner: str) -> list[str]:
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
    """Extract the first JSON object from the body text."""
    stripped = body.strip()
    if not stripped:
        return {}
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
    """Merge frontmatter and JSON body into a canonical appraiser-profile shape.

    Frontmatter wins on conflict (it's the "curated" view); body provides
    fields that aren't in frontmatter.

    Post-merge, country is normalised to uppercase and country-inapplicable
    location fields are zeroed (see `_strip_cross_country_fields`).
    """
    result: dict[str, Any] = {
        "user": {},
        "appraiser": {},
        "location": {},
        "preferences": {},
        "user_type": None,
        "schema_version": None,
        "created_at": None,
        "updated_at": None,
    }

    # Populate from frontmatter first
    if isinstance(fm.get("user"), dict):
        result["user"].update(fm["user"])
    if isinstance(fm.get("appraiser"), dict):
        result["appraiser"].update(fm["appraiser"])
    if isinstance(fm.get("location"), dict):
        result["location"].update(fm["location"])
    if isinstance(fm.get("preferences"), dict):
        result["preferences"].update(fm["preferences"])

    # Fill from body where frontmatter was silent
    def _get(k: str) -> Any:
        return body.get(k) if isinstance(body, dict) else None

    body_user = body.get("user") if isinstance(body, dict) else None
    if isinstance(body_user, dict):
        result["user"].setdefault("name", body_user.get("name"))
        result["user"].setdefault("company", body_user.get("company"))

    body_appraiser = body.get("appraiser") if isinstance(body, dict) else None
    if isinstance(body_appraiser, dict):
        result["appraiser"].setdefault("specialization", body_appraiser.get("specialization"))
        result["appraiser"].setdefault("min_comp_count", body_appraiser.get("min_comp_count"))

    body_loc = body.get("location") if isinstance(body, dict) else None
    if isinstance(body_loc, dict):
        for k in ("country", "zip", "postcode", "state", "region", "city"):
            result["location"].setdefault(k, body_loc.get(k))

    loc = result["location"]
    if loc.get("country"):
        loc["country"] = str(loc["country"]).strip().upper()

    # Normalise zip / postcode / state shape (trim whitespace, uppercase
    # UK postcodes, strip ZIP+4 suffix on US ZIPs).
    _normalize_location(loc)
    _strip_cross_country_fields(loc)

    prefs = result["preferences"]
    body_prefs = body.get("preferences") if isinstance(body, dict) else None
    if isinstance(body_prefs, dict):
        prefs.setdefault("default_radius_miles", body_prefs.get("default_radius_miles"))

    # Appraiser-plugin default radius (per plugins/appraiser/CLAUDE.md: 75 mi).
    prefs.setdefault("default_radius_miles", 75)

    # Default min_comp_count if neither frontmatter nor body supplied it.
    appraiser_block = result["appraiser"]
    if appraiser_block.get("min_comp_count") in (None, ""):
        appraiser_block["min_comp_count"] = 10

    # Passthrough onboarding metadata.
    for key in ("schema_version", "created_at", "updated_at", "user_type"):
        if fm.get(key) is not None:
            result[key] = fm[key]
        elif isinstance(body, dict) and body.get(key) is not None:
            result[key] = body[key]

    return result


def _normalize_location(loc: dict[str, Any]) -> None:
    """Normalise zip / postcode / state shape in place."""
    country = str(loc.get("country") or "").strip().upper()
    for key in ("zip", "postcode", "state", "region", "city"):
        val = loc.get(key)
        if isinstance(val, str):
            loc[key] = val.strip()

    if country == "US":
        z = loc.get("zip")
        if isinstance(z, str) and "-" in z:
            loc["zip"] = z.split("-", 1)[0]
        s = loc.get("state")
        if isinstance(s, str):
            loc["state"] = s.upper()
    elif country == "UK":
        p = loc.get("postcode")
        if isinstance(p, str):
            loc["postcode"] = " ".join(p.upper().split())


def _strip_cross_country_fields(loc: dict[str, Any]) -> None:
    """Zero location fields that don't apply to the profile's country.

    US profiles don't use `postcode` or `region`; UK profiles don't use
    `zip` or `state`. The per-country slot is preserved; the cross-country
    slot is cleared.
    """
    country = loc.get("country")
    if country == "US":
        loc["postcode"] = None
        loc["region"] = None
    elif country == "UK":
        loc["zip"] = None
        loc["state"] = None


def validate(profile: dict[str, Any]) -> tuple[bool, str | None]:
    country = (profile.get("location") or {}).get("country")
    if not country:
        return False, "location.country is required"
    if country not in ("US", "UK"):
        return False, f"location.country must be US or UK (got {country!r})"
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

    # Schema-version check. Mismatch warns but does not block; the skill
    # may have evolved past the profile without breaking the fields it reads.
    profile_schema = profile.get("schema_version")
    if profile_schema and str(profile_schema) != PROFILE_SCHEMA_VERSION:
        sys.stderr.write(
            f"load_profile: WARNING — profile schema_version {profile_schema!r} "
            f"does not match expected {PROFILE_SCHEMA_VERSION!r}. "
            f"Proceeding on best-effort; re-run /onboarding to upgrade.\n"
        )

    # Compute derived session values.
    # car_type is NOT carried in the appraiser profile (no
    # `default_inventory_type` field). The depreciation-tracker skill
    # hardcodes inventory_type per workflow (W1-W4 Used, W5 New); this
    # session block carries no car_type_resolved.
    radius_raw = (profile.get("preferences") or {}).get("default_radius_miles")
    try:
        radius_clamped = min(int(radius_raw) if radius_raw is not None else 75, 200)
    except (TypeError, ValueError):
        radius_clamped = 75

    min_comp_raw = (profile.get("appraiser") or {}).get("min_comp_count")
    try:
        min_comp_count = int(min_comp_raw) if min_comp_raw is not None else 10
    except (TypeError, ValueError):
        min_comp_count = 10

    # Unique scratch-directory ID for this skill flow. Two concurrent
    # invocations of the skill see different run_ids and cannot collide on
    # /tmp/marketcheck/<run_id>/. Pass --run-id <previously-emitted> on
    # mid-session re-runs (e.g., after compaction) to preserve the scratch dir.
    run_id = _run_id_override(argv) or _generate_run_id()

    profile["session"] = {
        "radius_mi_clamped": radius_clamped,
        "min_comp_count": min_comp_count,
        "profile_path": str(path),
        "run_id": run_id,
    }

    json.dump(profile, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def _generate_run_id() -> str:
    """Return a unique scratch-dir identifier for this skill flow.

    Format: ``dt-<unix-epoch-seconds>-<8 hex chars>``. The timestamp prefix
    keeps /tmp/marketcheck/ listings sortable and human-debuggable; the
    random suffix gives 2^32 collision space within the same second.
    """
    return f"dt-{int(time.time())}-{secrets.token_hex(4)}"


_RUN_ID_VALID = re.compile(r"^[A-Za-z0-9_-]+$")


def _run_id_override(argv: list[str]) -> str | None:
    """Extract --run-id <id> from argv, validating against path-traversal."""
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
