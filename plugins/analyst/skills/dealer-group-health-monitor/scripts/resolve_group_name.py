#!/usr/bin/env python3
"""
resolve_group_name.py — Map user input to a canonical dealership_group_name.

Resolution order (the order matters):
  1. Exact-match against the 471-entry enum (case- and punctuation-sensitive).
  2. Ticker symbol match (LAD → "Lithia Motors Inc.") via the 8-entry map.
  3. Fuzzy match via difflib.SequenceMatcher; return top-10 candidates.

Why this order:
  - Exact match first means a user who types the canonical name verbatim
    (e.g., copy-pasted "AutoNation Inc.") gets a frictionless answer.
  - Ticker match second handles the canonical equity-analyst input ("AN").
  - Fuzzy last covers typos / paraphrases ("AutoNation" without Inc.,
    "lithia", "carmax" lowercase, etc.).

The script enforces enum membership: a name not in the 471-entry enum
NEVER reaches a get_sold_summary call (that's the only way to avoid the
10-KB error string the tool returns on enum miss).

Usage:
  resolve_group_name.py --input "AutoNation"
  resolve_group_name.py --input "LAD"
  resolve_group_name.py --input "carmax"
  resolve_group_name.py --input "..." --enum-file <path> --ticker-file <path> --classification-file <path>

The reference files default to <script_dir>/../references/dealership_group_enum.md,
ticker-mapping.md, and inventory-type-classification.md respectively.

Output JSON shape:
  {
    "ok": true,
    "input": "<as supplied>",
    "resolution": "exact" | "ticker" | "fuzzy",
    "canonical": "<canonical enum name>",
    "ticker": "AN" | null,
    "classification": "Used-only" | "New-only" | "Both",
    "candidates": [{"name": "...", "score": 0.94}, ...]   # empty for exact/ticker
  }

Or on failure:
  {"ok": false, "error_type": "no_candidates" | "missing_input" | "no_enum",
   "input": "...", "candidates": [...]}

Exit codes:
  0  always (errors signaled via JSON `ok` field)
"""

from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from _common import arg_value, emit


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ENUM = SCRIPT_DIR.parent / "references" / "dealership_group_enum.md"
DEFAULT_TICKER = SCRIPT_DIR.parent / "references" / "ticker-mapping.md"
DEFAULT_CLASSIFICATION = SCRIPT_DIR.parent / "references" / "inventory-type-classification.md"

FUZZY_TOP_N = 10
FUZZY_MIN_SCORE = 0.5     # below this, we treat as no-candidates


# ─── Reference-file parsers ─────────────────────────────────────────────────

def _read_fenced_code_block(path: Path) -> list[str]:
    """Return lines inside the FIRST fenced code block in `path`. Skips
    blank lines. Used for one-name-per-line reference data.
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    inside = False
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.rstrip("\n")
        if stripped.strip().startswith("```"):
            if inside:
                # End of block
                break
            else:
                inside = True
                continue
        if inside and stripped.strip():
            out.append(stripped)
    return out


def load_enum(path: Path) -> list[str]:
    """Load the 471-entry enum from a reference file. One name per line in
    a fenced code block."""
    return _read_fenced_code_block(path)


_TICKER_LINE_RE = re.compile(r"^([A-Z]+)\s*→\s*(.+)$")


def load_ticker_map(path: Path) -> dict[str, str]:
    """Load TICKER → canonical name pairs from the ticker reference file.

    Each line in the fenced code block is `TICKER → Canonical Name` with a
    literal U+2192 RIGHT ARROW between. Returns {ticker: canonical}.
    """
    out: dict[str, str] = {}
    for line in _read_fenced_code_block(path):
        m = _TICKER_LINE_RE.match(line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def load_classification(path: Path) -> dict[str, str]:
    """Load the Used-only / New-only short lists from the classification
    reference file. Returns {canonical_name: classification}.

    Names not in the returned dict default to "Both" — caller applies that
    default. The reference file uses one fenced code block per category
    (Used-only, then New-only); this parser scans for both.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    # Walk the file, tracking which heading section we're in.
    current_label: str | None = None
    inside_block = False
    for line in text.splitlines():
        stripped = line.strip()
        # Detect headings — accept "## Used-only (N)" form
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
        # Track fenced code blocks within a labelled section
        if stripped.startswith("```"):
            if current_label is None:
                inside_block = False
            else:
                inside_block = not inside_block
            continue
        if inside_block and stripped and current_label:
            out[stripped] = current_label
    return out


# ─── Resolution ─────────────────────────────────────────────────────────────


def _classify(canonical: str, classification_map: dict[str, str]) -> str:
    return classification_map.get(canonical, "Both")


def _ticker_for(canonical: str, ticker_map: dict[str, str]) -> str | None:
    """Reverse-lookup ticker from canonical. Returns None if the canonical
    name isn't one of the 8 tracked tickers."""
    for ticker, name in ticker_map.items():
        if name == canonical:
            return ticker
    return None


def _fuzzy_candidates(query: str, enum_names: list[str], top_n: int = FUZZY_TOP_N) -> list[dict]:
    """Top-N fuzzy candidates ranked by SequenceMatcher ratio.

    Match against the lowercased name to ignore case differences. The
    canonical casing is preserved in the returned `name` field — so a
    `"carmax"` input matches `"Carmax"` (the canonical) with high score.
    """
    q = query.strip().lower()
    if not q:
        return []
    scored: list[tuple[float, str]] = []
    for name in enum_names:
        score = SequenceMatcher(None, q, name.lower()).ratio()
        scored.append((score, name))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        {"name": name, "score": round(score, 4)}
        for score, name in scored[:top_n]
    ]


def resolve(
    user_input: str,
    enum_names: list[str],
    ticker_map: dict[str, str],
    classification_map: dict[str, str],
) -> dict:
    user_input = user_input.strip()
    if not user_input:
        return {
            "ok": False,
            "error_type": "missing_input",
            "input": user_input,
            "candidates": [],
        }
    if not enum_names:
        return {
            "ok": False,
            "error_type": "no_enum",
            "input": user_input,
            "candidates": [],
            "error": "dealership_group_enum.md not found or empty",
        }

    # 1. Exact match (case- and punctuation-sensitive)
    if user_input in enum_names:
        return {
            "ok": True,
            "input": user_input,
            "resolution": "exact",
            "canonical": user_input,
            "ticker": _ticker_for(user_input, ticker_map),
            "classification": _classify(user_input, classification_map),
            "candidates": [],
        }

    # 2. Ticker-symbol match (uppercase the input)
    upper = user_input.upper()
    if upper in ticker_map:
        canonical = ticker_map[upper]
        return {
            "ok": True,
            "input": user_input,
            "resolution": "ticker",
            "canonical": canonical,
            "ticker": upper,
            "classification": _classify(canonical, classification_map),
            "candidates": [],
        }

    # 3. Fuzzy match
    candidates = _fuzzy_candidates(user_input, enum_names)
    top = candidates[0] if candidates else None
    if top is None or top["score"] < FUZZY_MIN_SCORE:
        return {
            "ok": False,
            "error_type": "no_candidates",
            "input": user_input,
            "candidates": candidates,    # may still be helpful even if low-score
        }
    canonical = top["name"]
    return {
        "ok": True,
        "input": user_input,
        "resolution": "fuzzy",
        "canonical": canonical,
        "ticker": _ticker_for(canonical, ticker_map),
        "classification": _classify(canonical, classification_map),
        "candidates": candidates,
    }


# ─── CLI ───────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    user_input = arg_value(argv, "--input")
    if user_input is None:
        emit({
            "ok": False,
            "error_type": "missing_input",
            "input": "",
            "candidates": [],
            "error": "--input is required",
        })
        return 0

    enum_path = Path(arg_value(argv, "--enum-file") or DEFAULT_ENUM)
    ticker_path = Path(arg_value(argv, "--ticker-file") or DEFAULT_TICKER)
    classification_path = Path(arg_value(argv, "--classification-file") or DEFAULT_CLASSIFICATION)

    enum_names = load_enum(enum_path)
    ticker_map = load_ticker_map(ticker_path)
    classification_map = load_classification(classification_path)

    result = resolve(user_input, enum_names, ticker_map, classification_map)
    emit(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
