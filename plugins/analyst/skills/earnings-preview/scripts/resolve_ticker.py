#!/usr/bin/env python3
"""
resolve_ticker.py — Resolve a user-supplied ticker / brand / company / canonical
name to a normalized entity record covering all 21 tickers tracked by this skill.

Three-tier resolution:

  1. Exact ticker match (case-insensitive, auto-uppercased) against both
     the OEM map (13 entries) and the Dealer-group map (8 entries).
  2. Reverse name lookup (case-insensitive exact) against:
       - OEM company name (e.g., "Ford Motor Company" → F)
       - OEM make name (e.g., "Cadillac" → GM, "Lincoln" → F)
       - Dealer-group canonical name (e.g., "AutoNation Inc." → AN,
         "Carmax" → KMX).
  3. Fuzzy match via `difflib.SequenceMatcher` against the same target set,
     threshold ≥ 0.5.

If no tier produces a match, emits `error_type=no_candidates` with the top-10
fuzzy candidates. **This skill has no brand-orphan recovery branch** — unknown
input halts. (See `references/inventory-type-classification.md §"Why
brand_orphan is omitted"` for the rationale.)

Output (success):
  OEM ticker:
    {
      "ok": true,
      "input": "<as supplied>",
      "resolution": "exact" | "reverse" | "fuzzy",
      "ticker": "F",
      "entity_type": "oem",
      "company_name": "Ford Motor Company",
      "makes": ["Ford", "Lincoln"],
      "classification": "legacy" | "pure_play",
      "candidates": []                  # populated only on fuzzy hits
    }

  Dealer-group ticker:
    {
      "ok": true,
      "input": "<as supplied>",
      "resolution": "exact" | "reverse" | "fuzzy",
      "ticker": "AN",
      "entity_type": "dealer_group",
      "canonical": "AutoNation Inc.",
      "classification": "Used-only" | "New-only" | "Both",
      "candidates": []
    }

Output (failure):
  {
    "ok": false,
    "error_type": "missing_input" | "no_candidates",
    "candidates": [...]                 # top-10 fuzzy candidates (no_candidates) or []
  }

  For `no_candidates`, each candidate is:
    {"ticker": "F", "entity_type": "oem", "name": "Ford Motor Company", "score": 0.42}

The OEM `classification` (legacy / pure_play) is read from the 4th column of
the `### OEM map` fenced block in `references/ticker-mapping.md`. The
dealer-group `classification` (Used-only / New-only / Both) is read from the
`## Used-only` and `## New-only` fenced blocks in
`references/inventory-type-classification.md`; canonical names not in either
block default to `Both`.

Usage:
  resolve_ticker.py --input "F"
  resolve_ticker.py --input "Ford"
  resolve_ticker.py --input "Ford Motor Company"
  resolve_ticker.py --input "AutoNation"        # fuzzy → AN
  resolve_ticker.py --input "carmax"            # fuzzy → KMX
  resolve_ticker.py --input "Subaru"            # → no_candidates

CLI flags:
  --input "<text>"               Required. User-supplied ticker / make /
                                 company / canonical. Empty / absent →
                                 error_type=missing_input.
  --ticker-file <path>           Override the ticker-mapping source.
                                 Default: references/ticker-mapping.md
  --classification-file <path>   Override the inventory-type-classification
                                 source. Default:
                                 references/inventory-type-classification.md

Exit codes:
  0  success or payload-level failure (parse the JSON `ok` field)
  1  reference file unreadable or malformed (no rows parsed)
"""

from __future__ import annotations

import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

# Allow importing _common from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from _common import arg_value, emit                                # noqa: E402


# ─── Path resolution for reference files ───────────────────────────────────

_SCRIPT_DIR = Path(__file__).parent
_DEFAULT_TICKER_FILE = _SCRIPT_DIR.parent / "references" / "ticker-mapping.md"
_DEFAULT_CLASSIFICATION_FILE = (
    _SCRIPT_DIR.parent / "references" / "inventory-type-classification.md"
)


# ─── Reference-file parsers ────────────────────────────────────────────────

_OEM_MAP_FENCE = "### OEM map"
_DEALER_GROUP_FENCE = "### Dealer-group map"

_FUZZY_TOP_N = 10
_FUZZY_MIN_SCORE = 0.5


def _extract_fenced_block(text: str, heading: str) -> str:
    """Extract the contents of the first fenced code block that follows
    the given markdown heading. Returns the block content (without fences),
    or empty string if not found.
    """
    lines = text.splitlines()
    in_section = False
    in_fence = False
    out: list[str] = []
    for line in lines:
        if not in_section:
            if line.strip() == heading.strip():
                in_section = True
            continue
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                continue
            else:
                return "\n".join(out)
        if in_fence:
            out.append(line)
        else:
            # Section ended without fence (new heading) — stop
            if stripped.startswith("#") and not stripped.startswith("##"):
                break
    return "\n".join(out)


def _parse_oem_map(content: str) -> list[dict]:
    """Parse the OEM map from ticker-mapping.md.

    Format per line: `TICKER → Company Name → Make1,Make2,... → classification`
    """
    block = _extract_fenced_block(content, _OEM_MAP_FENCE)
    rows = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(" → ")]
        if len(parts) != 4:
            # Malformed line; skip silently (consistent with oem-tracker)
            continue
        ticker, company, makes_csv, classification = parts
        makes = [m.strip() for m in makes_csv.split(",") if m.strip()]
        rows.append({
            "entity_type": "oem",
            "ticker": ticker.upper(),
            "company_name": company,
            "makes": makes,
            "classification": classification,
        })
    return rows


def _parse_dealer_group_map(content: str) -> list[dict]:
    """Parse the Dealer-group map from ticker-mapping.md.

    Format per line: `TICKER → canonical_name`. Canonical name preserves
    exact casing (must match the `dealership_group_name` enum verbatim).
    """
    block = _extract_fenced_block(content, _DEALER_GROUP_FENCE)
    rows = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(" → ")]
        if len(parts) != 2:
            continue
        ticker, canonical = parts
        rows.append({
            "entity_type": "dealer_group",
            "ticker": ticker.upper(),
            "canonical": canonical,
        })
    return rows


def _parse_classification(text: str) -> tuple[set[str], set[str]]:
    """Parse the Used-only and New-only ticker sets from
    inventory-type-classification.md.

    Scans every H2 heading; the contents of the first fenced code block
    following an H2 whose text contains 'used-only' / 'used only' goes to
    the Used-only set. Similarly for 'new-only' / 'new only'. Other H2s
    are ignored.

    Returns (used_only_tickers, new_only_tickers).
    """
    used_only: set[str] = set()
    new_only: set[str] = set()
    current_label: str | None = None
    inside_block = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].lower()
            if "used-only" in heading or "used only" in heading:
                current_label = "Used-only"
            elif "new-only" in heading or "new only" in heading:
                current_label = "New-only"
            else:
                current_label = None
            inside_block = False
            continue
        if stripped.startswith("```"):
            if current_label is None:
                inside_block = False
            else:
                inside_block = not inside_block
            continue
        if inside_block and stripped and current_label:
            ticker = stripped.upper()
            if current_label == "Used-only":
                used_only.add(ticker)
            else:
                new_only.add(ticker)
    return used_only, new_only


# ─── Resolution tiers ──────────────────────────────────────────────────────


def _try_exact_ticker(
    input_upper: str, oem_rows: list[dict], dealer_rows: list[dict]
) -> dict | None:
    """Tier 1: exact ticker match (auto-uppercased). Returns the row dict
    or None."""
    for row in oem_rows:
        if row["ticker"] == input_upper:
            return row
    for row in dealer_rows:
        if row["ticker"] == input_upper:
            return row
    return None


def _try_reverse_lookup(
    input_norm: str, oem_rows: list[dict], dealer_rows: list[dict]
) -> dict | None:
    """Tier 2: case-insensitive exact match against OEM company name, OEM
    makes, or dealer-group canonical name."""
    for row in oem_rows:
        if row["company_name"].lower() == input_norm:
            return row
        for make in row["makes"]:
            if make.lower() == input_norm:
                return row
    for row in dealer_rows:
        if row["canonical"].lower() == input_norm:
            return row
    return None


def _try_fuzzy(
    input_norm: str,
    oem_rows: list[dict],
    dealer_rows: list[dict],
    threshold: float = _FUZZY_MIN_SCORE,
) -> tuple[dict | None, list[dict]]:
    """Tier 3: fuzzy match via SequenceMatcher against ticker, company /
    canonical, and (for OEM) makes. Returns (best_row_above_threshold,
    top_10_candidates). top_10 is always returned regardless of best score
    so callers can surface candidates on `no_candidates` errors.
    """
    candidates: list[dict] = []

    for row in oem_rows:
        scores = [
            SequenceMatcher(None, input_norm, row["ticker"].lower()).ratio(),
            SequenceMatcher(None, input_norm, row["company_name"].lower()).ratio(),
        ]
        for make in row["makes"]:
            scores.append(SequenceMatcher(None, input_norm, make.lower()).ratio())
        best = max(scores)
        candidates.append({
            "ticker": row["ticker"],
            "entity_type": "oem",
            "name": row["company_name"],
            "score": round(best, 4),
            "_row": row,
        })

    for row in dealer_rows:
        scores = [
            SequenceMatcher(None, input_norm, row["ticker"].lower()).ratio(),
            SequenceMatcher(None, input_norm, row["canonical"].lower()).ratio(),
        ]
        best = max(scores)
        candidates.append({
            "ticker": row["ticker"],
            "entity_type": "dealer_group",
            "name": row["canonical"],
            "score": round(best, 4),
            "_row": row,
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    top_10 = [
        {
            "ticker": c["ticker"],
            "entity_type": c["entity_type"],
            "name": c["name"],
            "score": c["score"],
        }
        for c in candidates[:_FUZZY_TOP_N]
    ]

    if candidates and candidates[0]["score"] >= threshold:
        return candidates[0]["_row"], top_10
    return None, top_10


# ─── Result assembly ───────────────────────────────────────────────────────


def _resolve_classification(
    row: dict, used_only: set[str], new_only: set[str]
) -> str:
    """OEM rows carry classification verbatim from the ticker-mapping 4th
    column. Dealer-group rows look up the ticker against the Used-only /
    New-only sets; default is `Both`.
    """
    if row["entity_type"] == "oem":
        return row["classification"]
    ticker = row["ticker"]
    if ticker in used_only:
        return "Used-only"
    if ticker in new_only:
        return "New-only"
    return "Both"


def _build_result(
    user_input: str,
    row: dict,
    resolution: str,
    used_only: set[str],
    new_only: set[str],
    candidates: list[dict] | None = None,
) -> dict:
    classification = _resolve_classification(row, used_only, new_only)
    result = {
        "ok": True,
        "input": user_input,
        "resolution": resolution,
        "ticker": row["ticker"],
        "entity_type": row["entity_type"],
        "classification": classification,
        "candidates": candidates or [],
    }
    if row["entity_type"] == "oem":
        result["company_name"] = row["company_name"]
        result["makes"] = row["makes"]
    else:
        result["canonical"] = row["canonical"]
    return result


# ─── Main ───────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    user_input = arg_value(argv, "--input")
    if not user_input or not user_input.strip():
        emit({
            "ok": False,
            "error_type": "missing_input",
            "candidates": [],
        })
        return 0

    ticker_file_path = arg_value(argv, "--ticker-file") or str(_DEFAULT_TICKER_FILE)
    classification_file_path = (
        arg_value(argv, "--classification-file") or str(_DEFAULT_CLASSIFICATION_FILE)
    )

    try:
        ticker_content = Path(ticker_file_path).read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"resolve_ticker: cannot read ticker file: {exc}\n")
        return 1

    try:
        classification_content = Path(classification_file_path).read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        sys.stderr.write(
            f"resolve_ticker: cannot read classification file: {exc}\n"
        )
        return 1

    oem_rows = _parse_oem_map(ticker_content)
    dealer_rows = _parse_dealer_group_map(ticker_content)

    if not oem_rows and not dealer_rows:
        sys.stderr.write(
            f"resolve_ticker: ticker file at {ticker_file_path} parsed to zero rows. "
            f"Check the '{_OEM_MAP_FENCE}' / '{_DEALER_GROUP_FENCE}' fenced blocks.\n"
        )
        return 1

    used_only, new_only = _parse_classification(classification_content)

    input_norm = user_input.strip().lower()
    input_upper = user_input.strip().upper()

    # Tier 1: exact ticker
    row = _try_exact_ticker(input_upper, oem_rows, dealer_rows)
    if row:
        emit(_build_result(user_input, row, "exact", used_only, new_only))
        return 0

    # Tier 2: reverse lookup (company / make / canonical)
    row = _try_reverse_lookup(input_norm, oem_rows, dealer_rows)
    if row:
        emit(_build_result(user_input, row, "reverse", used_only, new_only))
        return 0

    # Tier 3: fuzzy
    row, top_10 = _try_fuzzy(input_norm, oem_rows, dealer_rows)
    if row:
        emit(_build_result(user_input, row, "fuzzy", used_only, new_only, top_10))
        return 0

    # No match — no brand-orphan recovery in this skill
    emit({
        "ok": False,
        "error_type": "no_candidates",
        "input": user_input,
        "candidates": top_10,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
