#!/usr/bin/env python3
"""
merge_comps.py — Merge the asc + desc `search_active_cars` parsed outputs by
VIN, desc-first on duplicates.

Why desc-first: the desc pull surfaces the top-of-market rows that the asc
rows=20 pull missed when num_found > 20. If a VIN happens to appear in both
(e.g., priced mid-distribution), the desc copy is preferred because it was
surfaced by the same query in the tail-coverage path.

Also defensively filters out the subject VIN — the skill's --subject-vin
passed to parse_search should have caught it already, but if a shadow slips
through (different casing, whitespace, etc.), this script catches it.

Usage:
  merge_comps.py --asc <path-to-parse_search-asc-output> \\
                 --desc <path-to-parse_search-desc-output> \\
                 --subject-vin <SUBJECT_VIN>

Emits on stdout:
  {
    "ok": true,
    "merged_listings": [<listing>, ...],
    "asc_n": <int>,            # len(asc.listings)
    "desc_n": <int>,           # len(desc.listings)
    "pulled_count": <int>,     # asc_n + desc_n (pre-merge raw total)
    "overlap_count": <int>,    # how many asc VINs were also in desc
    "subject_vin_excluded": <int>,   # subject VIN matches defensively removed
    "merged_n": <int>,         # len(merged_listings)
    "asc_num_found": <int>,    # echoed from asc parser output
    "desc_num_found": <int>,
    "sources": {"asc": "...", "desc": "..."}
  }

On failure:
  {"ok": false, "error_type": "...", "error": "..."}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _load_parsed(path_str: str, label: str) -> tuple[dict[str, Any] | None, str]:
    """Load a parse_search output file. Returns (payload, error_msg)."""
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot read {label} file {path_str!r}: {exc}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"{label} file {path_str!r} is not valid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, f"{label} payload is not a JSON object"
    if payload.get("ok") is False:
        # parse_search reported an error; propagate
        return None, f"{label} parser reported ok=false: {payload.get('error', '<no detail>')}"
    return payload, ""


def main(argv: list[str]) -> int:
    asc_path = _arg_value(argv, "--asc")
    desc_path = _arg_value(argv, "--desc")
    subject_vin_raw = _arg_value(argv, "--subject-vin") or ""
    subject_vin = subject_vin_raw.upper().strip()

    if not asc_path or not desc_path:
        json.dump({
            "ok": False,
            "error_type": "missing_args",
            "error": "merge_comps.py requires --asc <path> --desc <path> (and --subject-vin <VIN>)",
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1

    asc_payload, asc_err = _load_parsed(asc_path, "asc")
    if asc_err or asc_payload is None:
        json.dump({"ok": False, "error_type": "bad_asc_input", "error": asc_err}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    desc_payload, desc_err = _load_parsed(desc_path, "desc")
    if desc_err or desc_payload is None:
        json.dump({"ok": False, "error_type": "bad_desc_input", "error": desc_err}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    asc_listings_raw = asc_payload.get("listings") or []
    desc_listings_raw = desc_payload.get("listings") or []
    if not isinstance(asc_listings_raw, list):
        asc_listings_raw = []
    if not isinstance(desc_listings_raw, list):
        desc_listings_raw = []

    asc_n = len(asc_listings_raw)
    desc_n = len(desc_listings_raw)

    def _vin_of(listing: dict[str, Any]) -> str:
        return (listing.get("vin") or "").upper().strip()

    merged: list[dict[str, Any]] = []
    seen_vins: set[str] = set()
    subject_vin_excluded = 0

    # Desc first (wins on duplicates)
    for listing in desc_listings_raw:
        if not isinstance(listing, dict):
            continue
        vin = _vin_of(listing)
        if subject_vin and vin == subject_vin:
            subject_vin_excluded += 1
            continue
        if vin and vin in seen_vins:
            # Duplicate inside desc itself (shouldn't happen but defensive)
            continue
        merged.append(listing)
        if vin:
            seen_vins.add(vin)

    # Asc next — skip any VIN already surfaced by desc
    overlap_count = 0
    for listing in asc_listings_raw:
        if not isinstance(listing, dict):
            continue
        vin = _vin_of(listing)
        if subject_vin and vin == subject_vin:
            subject_vin_excluded += 1
            continue
        if vin and vin in seen_vins:
            overlap_count += 1
            continue
        merged.append(listing)
        if vin:
            seen_vins.add(vin)

    pulled_count = asc_n + desc_n

    json.dump({
        "ok": True,
        "merged_listings": merged,
        "asc_n": asc_n,
        "desc_n": desc_n,
        "pulled_count": pulled_count,
        "overlap_count": overlap_count,
        "subject_vin_excluded": subject_vin_excluded,
        "merged_n": len(merged),
        "asc_num_found": asc_payload.get("num_found"),
        "desc_num_found": desc_payload.get("num_found"),
        "sources": {
            "asc": str(Path(asc_path).resolve()),
            "desc": str(Path(desc_path).resolve()),
        },
    }, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
