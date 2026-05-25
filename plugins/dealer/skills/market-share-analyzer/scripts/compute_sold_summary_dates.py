#!/usr/bin/env python3
"""
compute_sold_summary_dates.py — Emit a calendar-month-aligned date window for
`get_sold_summary`'s State Baseline call.

The tool's local validator does NOT check month alignment; mis-aligned days
pass through and upstream rejects with HTTP 422. The safe window is:
  date_to   = last day of (current_month − 1)
  date_from = first day of (current_month − 3)

Yielding the "last 3 full calendar months" label (never includes the current
in-progress month).

Usage:
  compute_sold_summary_dates.py                          # uses system date
  compute_sold_summary_dates.py --today 2026-04-23       # fixed date

Emits on stdout:
  {
    "date_from": "YYYY-MM-DD",
    "date_to":   "YYYY-MM-DD",
    "label":     "last 3 full months",
    "months_included": ["YYYY-MM", "YYYY-MM", "YYYY-MM"],
    "today":     "YYYY-MM-DD"
  }

Exit codes:
  0  success
  1  malformed --today value
"""

from __future__ import annotations

import json
import sys
from calendar import monthrange
from datetime import date


def _first_of_month(year: int, month: int) -> date:
    return date(year, month, 1)


def _last_of_month(year: int, month: int) -> date:
    last_day = monthrange(year, month)[1]
    return date(year, month, last_day)


def _months_back(today: date, n: int) -> tuple[int, int]:
    """Return (year, month) n whole months before today's month."""
    y, m = today.year, today.month - n
    while m <= 0:
        m += 12
        y -= 1
    return y, m


def compute_window(today: date) -> dict:
    # date_to: last day of previous month
    prev_year, prev_month = _months_back(today, 1)
    date_to = _last_of_month(prev_year, prev_month)

    # date_from: first day of 3 months back
    from_year, from_month = _months_back(today, 3)
    date_from = _first_of_month(from_year, from_month)

    # Enumerate the 3 months included (for audit / DQ logging)
    months = []
    for i in range(3, 0, -1):
        y, m = _months_back(today, i)
        months.append(f"{y:04d}-{m:02d}")

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "label": "last 3 full months",
        "months_included": months,
        "today": today.isoformat(),
    }


def _parse_today(argv: list[str]) -> date:
    if "--today" in argv:
        idx = argv.index("--today")
        if idx + 1 < len(argv):
            raw = argv[idx + 1]
            try:
                y, m, d = raw.split("-")
                return date(int(y), int(m), int(d))
            except (ValueError, TypeError) as exc:
                raise SystemExit(f"compute_sold_summary_dates: --today {raw!r} is not YYYY-MM-DD ({exc})")
    return date.today()


def main(argv: list[str]) -> int:
    try:
        today = _parse_today(argv)
    except SystemExit as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    result = compute_window(today)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
