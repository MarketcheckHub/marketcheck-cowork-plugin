#!/usr/bin/env python3
"""
load_profile.py — Load and parse the MarketCheck appraiser profile.

Reads the `marketcheck-profile.md` memory file (YAML frontmatter + raw JSON
body) from one of the conventional search paths, merges the two sources
(frontmatter preferred for the fields it carries, JSON body as the fallback
for everything else), and emits a canonical appraiser profile JSON to stdout.

Country is normalised to uppercase before validation. Country-inapplicable
location fields are zeroed after merge (US profiles drop `postcode`; UK
profiles drop `zip`, `state`) so body-leaked cross-country values do not
poison the downstream US/UK branch.

Profile shape expected (per `plugins/appraiser/commands/onboarding.md`):

  {
    "schema_version": "2.0",
    "user_type": "appraiser",
    "user": {"name": "...", "company": "..."},
    "appraiser": {"specialization": "...", "min_comp_count": 10},
    "location": {"country": "US|UK", "zip": ..., "postcode": ..., "state": ...,
                 "region": ..., "city": ...},
    "preferences": {"default_radius_miles": 75}
  }

The appraiser profile does **not** carry the dealer-side fields
(`dealer_type`, `cpo_program`, `cpo_certification_cost`,
`default_inventory_type`, `dom_thresholds`, `recon_cost_estimate`). The
calling skill derives subject `car_type` per-call from decoded specs or
user input; CPO state is asked per-VIN; recon cost is asked per-W3.

Specialization → purpose-default mapping (emitted on `session.purpose_default`
for the skill to use when the user omits `purpose`):
  trade-in       → Trade-in
  insurance      → Insurance
  estate_legal   → Retail   (IRS fair-market-value convention)
  fleet          → Wholesale
  general        → Retail   (safe default)
  <unknown / absent> → Retail (safe default)

Exit codes:
  0  Profile loaded successfully (JSON on stdout)
  1  Profile file not found, or not readable
  2  Profile frontmatter YAML is malformed (PyYAML error) — the calling
     skill should read the raw file and parse it manually
  3  Required field missing (country, zip/postcode)
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
# in a backwards-incompatible way. Older profiles aren't hard-rejected; we
# log a warning on mismatch and proceed on best-effort terms.
PROFILE_SCHEMA_VERSION = "2.0"


SEARCH_PATHS = [
    # Project memory file — primary location
    Path("./marketcheck-profile.md"),
    Path("./.claude/marketcheck-profile.md"),
    # Legacy locations — migration support only.
    Path(os.path.expanduser("~/.claude/marketcheck/profile.md")),
    Path(os.path.expanduser("~/.claude/marketcheck-profile.md")),
]


def resolve_profile_path(argv: list[str]) -> Path | None:
    """Allow the caller to override via --file."""
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
        # safety: yaml.safe_load is required — never use yaml.load or yaml.Loader.
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


# Specialization → purpose-default mapping. The 4-purpose taxonomy
# (Trade-in / Retail / Insurance / Wholesale) is preserved from the
# appraisal-band purpose-bias formulas; `estate_legal` maps to Retail
# because the IRS fair-market-value convention is retail-anchored.
SPECIALIZATION_TO_PURPOSE = {
    "trade-in":     "Trade-in",
    "trade_in":     "Trade-in",
    "tradein":      "Trade-in",
    "insurance":    "Insurance",
    "estate_legal": "Retail",
    "estate":       "Retail",
    "legal":        "Retail",
    "fleet":        "Wholesale",
    "general":      "Retail",
}


def _purpose_default(specialization: str | None) -> str:
    """Return the default `purpose` value for the given specialization.

    Falls back to "Retail" on unknown / absent input — the safe default
    matches the IRS fair-market-value convention and is the standard
    appraiser benchmark when intent is not specified.
    """
    key = (specialization or "").strip().lower().replace("-", "_")
    # Try both kebab and snake variants
    return (
        SPECIALIZATION_TO_PURPOSE.get(specialization or "")
        or SPECIALIZATION_TO_PURPOSE.get(key)
        or "Retail"
    )


def merge(fm: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    """Merge frontmatter and JSON body into the canonical appraiser profile shape."""
    result: dict[str, Any] = {
        "appraiser": {},
        "location": {},
        "preferences": {},
        "user": {},
        "schema_version": None,
        "user_type": None,
        "created_at": None,
        "updated_at": None,
    }

    # Populate from frontmatter first
    if isinstance(fm.get("appraiser"), dict):
        result["appraiser"].update(fm["appraiser"])
    if isinstance(fm.get("location"), dict):
        result["location"].update(fm["location"])
    if isinstance(fm.get("preferences"), dict):
        result["preferences"].update(fm["preferences"])
    if isinstance(fm.get("user"), dict):
        result["user"].update(fm["user"])

    # Fill from body where frontmatter was silent
    def _get(k: str) -> Any:
        return body.get(k) if isinstance(body, dict) else None

    appr = result["appraiser"]
    body_appraiser = body.get("appraiser") if isinstance(body, dict) else None
    if isinstance(body_appraiser, dict):
        appr.setdefault("specialization", body_appraiser.get("specialization"))
        appr.setdefault("min_comp_count", body_appraiser.get("min_comp_count"))
    # Default min_comp_count to 10 if neither source provides it
    appr.setdefault("min_comp_count", 10)
    appr.setdefault("specialization", "general")

    usr = result["user"]
    body_user = body.get("user") if isinstance(body, dict) else None
    if isinstance(body_user, dict):
        usr.setdefault("name", body_user.get("name"))
        usr.setdefault("company", body_user.get("company"))

    loc = result["location"]
    body_loc = body.get("location") if isinstance(body, dict) else None
    if isinstance(body_loc, dict):
        loc.setdefault("country", body_loc.get("country"))
        loc.setdefault("zip", body_loc.get("zip"))
        loc.setdefault("postcode", body_loc.get("postcode"))
        loc.setdefault("state", body_loc.get("state"))
        loc.setdefault("region", body_loc.get("region"))
        loc.setdefault("city", body_loc.get("city"))
    # Final fall-through to top-level body for legacy flat shapes
    loc.setdefault("country", _get("country"))
    loc.setdefault("zip", _get("zip"))
    loc.setdefault("postcode", _get("postcode"))
    loc.setdefault("state", _get("state"))
    loc.setdefault("region", _get("region"))
    loc.setdefault("city", _get("city"))

    # Normalise country to uppercase before any downstream comparison
    if loc.get("country"):
        loc["country"] = str(loc["country"]).strip().upper()

    _normalize_location(loc)
    _strip_cross_country_fields(loc)

    prefs = result["preferences"]
    body_prefs = body.get("preferences") if isinstance(body, dict) else None
    if isinstance(body_prefs, dict):
        prefs.setdefault("default_radius_miles", body_prefs.get("default_radius_miles"))

    # Default radius — 75mi per `plugins/appraiser/CLAUDE.md`
    prefs.setdefault("default_radius_miles", 75)

    # Passthrough onboarding metadata
    for key in ("schema_version", "user_type", "created_at", "updated_at"):
        if fm.get(key) is not None:
            result[key] = fm[key]
        elif isinstance(body, dict) and body.get(key) is not None:
            result[key] = body[key]

    return result


def _normalize_location(loc: dict[str, Any]) -> None:
    """Normalise zip / postcode / state / city shape in place."""
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
    """Zero location fields that don't apply to the profile's country."""
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
        return False, (
            f"location.country must be one of US / UK (got {country!r}). "
            "Vehicle Appraiser is US + UK only."
        )
    zip_or_postcode = (profile.get("location") or {}).get("zip") or \
                      (profile.get("location") or {}).get("postcode")
    if not zip_or_postcode:
        return False, "location.zip (US) or location.postcode (UK) is required"
    return True, None


def main(argv: list[str]) -> int:
    path = resolve_profile_path(argv)
    if path is None:
        sys.stderr.write(
            "load_profile: no marketcheck-profile.md found in any search path. "
            "Run /appraiser:onboarding or pass --file <path>.\n"
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

    profile_schema = profile.get("schema_version")
    if profile_schema and str(profile_schema) != PROFILE_SCHEMA_VERSION:
        sys.stderr.write(
            f"load_profile: WARNING — profile schema_version {profile_schema!r} "
            f"does not match expected {PROFILE_SCHEMA_VERSION!r}. "
            f"Proceeding on best-effort; re-run /appraiser:onboarding to upgrade.\n"
        )

    # Compute derived session values.
    appr = profile.get("appraiser") or {}
    radius_raw = (profile.get("preferences") or {}).get("default_radius_miles") or 75
    try:
        radius_int = int(radius_raw)
    except (TypeError, ValueError):
        radius_int = 75
    # Clamp 25–150mi. Below 25 the comp pool is too thin for most segments;
    # above 150 the "local market" framing breaks down and W4 (regional
    # variance) is the better tool.
    radius_mi_clamped = max(25, min(radius_int, 150))

    try:
        min_comp_count = int(appr.get("min_comp_count") or 10)
    except (TypeError, ValueError):
        min_comp_count = 10

    specialization = str(appr.get("specialization") or "general").strip()

    run_id = _run_id_override(argv) or _generate_run_id()

    profile["session"] = {
        "radius_mi_clamped": radius_mi_clamped,
        "min_comp_count": min_comp_count,
        "specialization": specialization,
        "purpose_default": _purpose_default(specialization),
        "profile_path": str(path),
        "run_id": run_id,
        "country": profile.get("location", {}).get("country"),
    }

    json.dump(profile, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def _generate_run_id() -> str:
    """Return a unique scratch-dir identifier for this skill flow.

    Format: ``appraisal-<unix-epoch-seconds>-<8 hex chars>``. The timestamp
    prefix keeps /tmp/marketcheck/ listings sortable and human-debuggable;
    the random suffix gives 2^32 collision space within the same second.
    """
    return f"appraisal-{int(time.time())}-{secrets.token_hex(4)}"


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
