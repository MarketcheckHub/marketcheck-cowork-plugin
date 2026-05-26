#!/usr/bin/env python3
"""
resolve_oem.py — Resolve a user-supplied OEM ticker / brand / company name
to a canonical (ticker, company_name, makes[], classification) tuple.

Three-tier resolution:
  1. Exact ticker match (case-insensitive, auto-uppercased) against the
     13-row OEM map.
  2. Reverse make-name lookup (case-insensitive exact) against each
     OEM's makes list. E.g., "Ford" → F, "Lincoln" → F, "Cadillac" → GM.
  3. Fuzzy via `difflib.SequenceMatcher` ≥0.5 against tickers, company
     names, and makes. E.g., "Hundai" → HYMTF (Hyundai is close).

Dealer-group redirect: if input matches any of the 8 dealer-group tickers
(AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA), returns error_type=
dealer_group_redirect. SKILL.md halts with the redirect message.

Brand-orphan handling: NOT in this script. If resolution returns
error_type=no_candidates, SKILL.md's recovery branch fires
search_active_cars facet-discovery and constructs the workflow context
inline with classification="brand_orphan", ticker=null.

Usage:
  resolve_oem.py --input "F"
  resolve_oem.py --input "ford"
  resolve_oem.py --input "Ford Motor Company"
  resolve_oem.py --input "TSLA"
  resolve_oem.py --input "AN"                  # → dealer_group_redirect

CLI flags:
  --input "<text>"             User-supplied ticker / make / company name. Required.
  --ticker-file <path>         Override the OEM ticker-mapping source.
                               Default: references/ticker-mapping.md
  --classification-file <path> Override the pure-play classification source.
                               Default: references/oem-classification.md

Stdout (success):
  {
    "ok": true,
    "input": "<original input>",
    "resolution": "exact" | "ticker" | "fuzzy",
    "ticker": "F",
    "company_name": "Ford Motor Company",
    "makes": ["Ford", "Lincoln"],
    "classification": "legacy" | "pure_play",
    "candidates": []                          // usually empty for non-fuzzy hits
  }

Stdout (failure):
  {
    "ok": false,
    "error_type": "missing_input" | "dealer_group_redirect" | "no_candidates",
    "candidates": [...]                       // top-10 fuzzy candidates (no_candidates) or empty
  }

For dealer_group_redirect, also includes:
  "matched_ticker": "AN"
  "redirect_to":    "dealer-group-health-monitor"

Exit codes:
  0  success or payload-level failure (parse the JSON)
  1  validation error (missing --input)
"""

from __future__ import annotations

import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

# Allow importing _common from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from _common import arg_value, emit


# ──────────────────────────────────────────────────────────────────────────
# Path resolution for reference files
# ──────────────────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).parent
_DEFAULT_TICKER_FILE = _SCRIPT_DIR.parent / "references" / "ticker-mapping.md"
_DEFAULT_CLASSIFICATION_FILE = _SCRIPT_DIR.parent / "references" / "oem-classification.md"


# ──────────────────────────────────────────────────────────────────────────
# Parsing the reference files
# ──────────────────────────────────────────────────────────────────────────

_OEM_MAP_FENCE = "### OEM map"
_DEALER_GROUP_FENCE = "### Dealer-group redirect list"


def _extract_fenced_block(text: str, heading: str) -> str:
    """Extract the contents of the ```...``` fenced code block that follows
    the given markdown heading. Returns the block content (without fences)
    or empty string if not found."""
    lines = text.splitlines()
    in_section = False
    in_fence = False
    out = []
    for line in lines:
        if not in_section:
            if line.strip() == heading.strip():
                in_section = True
            continue
        # In section
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                continue
            else:
                # End of fence
                return "\n".join(out)
        if in_fence:
            out.append(line)
        else:
            # Section continues but not yet in fence — check if we hit a new heading
            if stripped.startswith("#") and not stripped.startswith("##"):
                # Top-level heading change → section ended without fence
                break
    return "\n".join(out)


def _parse_oem_map(content: str) -> list[dict]:
    """Parse the machine-readable OEM map from ticker-mapping.md.

    Format per line: `TICKER → Company Name → Make1,Make2,... → classification`
    """
    block = _extract_fenced_block(content, _OEM_MAP_FENCE)
    if not block:
        return []
    rows = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(" → ")]
        if len(parts) != 4:
            # Malformed line; skip silently
            continue
        ticker, company, makes_csv, classification = parts
        makes = [m.strip() for m in makes_csv.split(",") if m.strip()]
        rows.append({
            "ticker": ticker.upper(),
            "company_name": company,
            "makes": makes,
            "classification": classification,
        })
    return rows


def _parse_dealer_group_redirect(content: str) -> set[str]:
    """Parse the dealer-group redirect list. Format: one ticker per line."""
    block = _extract_fenced_block(content, _DEALER_GROUP_FENCE)
    if not block:
        return set()
    return {
        line.strip().upper()
        for line in block.splitlines()
        if line.strip()
    }


# ──────────────────────────────────────────────────────────────────────────
# Resolution
# ──────────────────────────────────────────────────────────────────────────

def _try_exact_ticker(input_upper: str, rows: list[dict]) -> dict | None:
    for row in rows:
        if row["ticker"] == input_upper:
            return row
    return None


def _try_reverse_make_lookup(input_norm: str, rows: list[dict]) -> dict | None:
    """Case-insensitive exact match on any make."""
    for row in rows:
        for make in row["makes"]:
            if make.lower() == input_norm:
                return row
        # Also try company name exact match (case-insensitive)
        if row["company_name"].lower() == input_norm:
            return row
    return None


def _try_fuzzy(input_norm: str, rows: list[dict], threshold: float = 0.5) -> tuple[dict | None, list[dict]]:
    """Fuzzy-match input against ticker, company_name, and each make.
    Returns (best_row_above_threshold, top_10_candidates)."""
    candidates: list[dict] = []
    for row in rows:
        # Score against ticker, company_name, and each make; keep best
        scores = [
            SequenceMatcher(None, input_norm, row["ticker"].lower()).ratio(),
            SequenceMatcher(None, input_norm, row["company_name"].lower()).ratio(),
        ]
        for make in row["makes"]:
            scores.append(SequenceMatcher(None, input_norm, make.lower()).ratio())
        best = max(scores)
        candidates.append({
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "score": round(best, 4),
            "_row": row,
        })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    top_10 = [
        {"ticker": c["ticker"], "company_name": c["company_name"], "score": c["score"]}
        for c in candidates[:10]
    ]
    if candidates and candidates[0]["score"] >= threshold:
        return candidates[0]["_row"], top_10
    return None, top_10


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

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
    # classification_file is loaded by parser via the ticker-mapping (which
    # already carries `classification`); the separate flag exists for
    # future-proofing but isn't strictly needed for this resolver.
    _ = arg_value(argv, "--classification-file") or str(_DEFAULT_CLASSIFICATION_FILE)

    try:
        ticker_file_content = Path(ticker_file_path).read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"resolve_oem: cannot read ticker file: {exc}\n")
        return 1

    rows = _parse_oem_map(ticker_file_content)
    dealer_group_redirect = _parse_dealer_group_redirect(ticker_file_content)

    if not rows:
        sys.stderr.write(
            f"resolve_oem: ticker file at {ticker_file_path} parsed to zero OEM rows. "
            "Check the '### OEM map' fenced block.\n"
        )
        return 1

    input_norm = user_input.strip().lower()
    input_upper = user_input.strip().upper()

    # Tier 0: dealer-group redirect (must precede OEM resolution; an OEM
    # ticker can never collide with a dealer-group ticker since the two sets
    # are disjoint, but we check first for clarity).
    if input_upper in dealer_group_redirect:
        emit({
            "ok": False,
            "error_type": "dealer_group_redirect",
            "matched_ticker": input_upper,
            "redirect_to": "dealer-group-health-monitor",
            "candidates": [],
        })
        return 0

    # Tier 1: exact ticker
    row = _try_exact_ticker(input_upper, rows)
    if row:
        emit({
            "ok": True,
            "input": user_input,
            "resolution": "exact",
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "makes": row["makes"],
            "classification": row["classification"],
            "candidates": [],
        })
        return 0

    # Tier 2: reverse make / company name lookup
    row = _try_reverse_make_lookup(input_norm, rows)
    if row:
        emit({
            "ok": True,
            "input": user_input,
            "resolution": "ticker",  # "ticker" = mapped via make → ticker
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "makes": row["makes"],
            "classification": row["classification"],
            "candidates": [],
        })
        return 0

    # Tier 3: fuzzy
    row, top_10 = _try_fuzzy(input_norm, rows, threshold=0.5)
    if row:
        emit({
            "ok": True,
            "input": user_input,
            "resolution": "fuzzy",
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "makes": row["makes"],
            "classification": row["classification"],
            "candidates": top_10,
        })
        return 0

    # No candidates → brand-orphan recovery in SKILL.md
    emit({
        "ok": False,
        "error_type": "no_candidates",
        "candidates": top_10,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
