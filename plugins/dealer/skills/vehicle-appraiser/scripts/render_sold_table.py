#!/usr/bin/env python3
"""
render_sold_table.py — Deterministic markdown renderer for the Sold
Transaction Comparables table (W1 / W3). Reads `parse_search.py` output
from a `search_past_90_days sold=true` call and emits an 8-column markdown
table sorted descending by `last_seen_at_date` (most-recent sales first).

Schema:
  | Dealer | Type | Sold Price | Miles | DOM | Distance | Sale Date | CPO? |

Standalone script — keeps the golden reference's `render_comp_set_table.py`
byte-identical (we did not extend its mode set with a new sold variant).

Usage:
  render_sold_table.py \\
    --sold <path-to-parse_search-output> \\
    [--currency '$|£'] \\
    [--max-rows N]

Exit codes:
  0  OK (markdown emitted on stdout)
  1  Missing or malformed input
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


MINUS = "−"      # U+2212
EM_DASH = "—"   # U+2014
ELLIPSIS = "…"   # U+2026

DEALER_MAX_CHARS = 30

COLUMNS = ["Dealer", "Type", "Sold Price", "Miles", "DOM", "Distance",
           "Sale Date", "CPO?"]


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _load_json(path_str: str | None, label: str) -> dict[str, Any]:
    if not path_str:
        sys.stderr.write(f"render_sold_table: --{label} is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"render_sold_table: cannot read {label} {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"render_sold_table: {label} {path_str!r} not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"render_sold_table: {label} payload must be JSON object\n")
        raise SystemExit(1)
    return payload


def _money(value: float | None, currency: str) -> str:
    if value is None:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{currency}{abs(int(round(value))):,}"
    return f"{currency}{int(round(value)):,}"


def _truncate_dealer(name: str | None) -> str:
    if name is None:
        return EM_DASH
    s = str(name)
    if len(s) > DEALER_MAX_CHARS:
        s = s[:DEALER_MAX_CHARS - 1] + ELLIPSIS
    return s


def _type_cell(dealer_type: str | None) -> str:
    if dealer_type == "franchise":
        return "F"
    if dealer_type == "independent":
        return "I"
    return EM_DASH


def _miles_cell(miles: float | None) -> str:
    if miles is None:
        return EM_DASH
    return f"{int(round(miles)):,}"


def _dom_cell(dom_active: int | None) -> str:
    if dom_active is None:
        return EM_DASH
    return str(int(dom_active))


def _distance_cell(distance_mi: float | None) -> str:
    if distance_mi is None:
        return EM_DASH
    return f"{distance_mi:.2f} mi"


def _cpo_cell(is_certified: Any) -> str:
    if is_certified is True:
        return "Y"
    if is_certified is False:
        return "N"
    return EM_DASH


def main(argv: list[str]) -> int:
    sold_path = _arg_value(argv, "--sold")
    currency = _arg_value(argv, "--currency") or "$"
    max_rows_raw = _arg_value(argv, "--max-rows")
    max_rows = _to_int(max_rows_raw) if max_rows_raw else None

    payload = _load_json(sold_path, "sold")

    listings_raw = payload.get("listings") or []
    if not isinstance(listings_raw, list):
        listings_raw = []

    rows = [r for r in listings_raw if isinstance(r, dict)]

    # Sort descending by last_seen_at_date (most recent first). Empty dates sort last.
    def _sort_key(r: dict) -> str:
        return r.get("last_seen_at_date") or ""
    rows.sort(key=_sort_key, reverse=True)

    if max_rows is not None and max_rows >= 0:
        rows = rows[:max_rows]

    out_lines: list[str] = []

    if not rows:
        out_lines.append("| " + " | ".join(COLUMNS) + " |")
        out_lines.append("|" + "|".join(["---"] * len(COLUMNS)) + "|")
        out_lines.append("| *(no sold transactions in this radius)* |")
        sys.stdout.write("\n".join(out_lines) + "\n")
        return 0

    out_lines.append("| " + " | ".join(COLUMNS) + " |")
    out_lines.append("|" + "|".join(["---"] * len(COLUMNS)) + "|")

    for r in rows:
        price = _to_float(r.get("price"))
        miles = _to_float(r.get("miles"))
        dom_active = _to_int(r.get("dom_active"))
        distance_mi = _to_float(r.get("distance_mi"))
        sale_date = r.get("last_seen_at_date") or EM_DASH

        cells = [
            _truncate_dealer(r.get("dealer_name")),
            _type_cell(r.get("dealer_type")),
            _money(price, currency),
            _miles_cell(miles),
            _dom_cell(dom_active),
            _distance_cell(distance_mi),
            sale_date,
            _cpo_cell(r.get("is_certified")),
        ]
        out_lines.append("| " + " | ".join(cells) + " |")

    sys.stdout.write("\n".join(out_lines) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"render_sold_table: unexpected error: {exc}\n")
        sys.exit(1)
