#!/usr/bin/env python3
"""
compute_month_windows.py — Emit calendar-month-aligned windows for the
W1 (current + prior month MoM) and W2/W3 (current month) workflows.

The skill needs single-month windows for month-over-month comparison —
distinct from the gold standard's `compute_sold_summary_dates.py` which
emits a 3-month rolling window.

Definition (strictly-before rule):
  current_month = the calendar month that ended STRICTLY BEFORE today.
                  On May 31 → April. On June 1 → May. On May 1 → April.
  prior_month   = the calendar month immediately before current_month.

Why strictly-before: sold-summary aggregates lag the calendar; even on the
last day of a month, that month's data isn't fully assembled upstream.
Strict "month that already ended" sidesteps the race.

Usage:
  compute_month_windows.py                          # uses system date
  compute_month_windows.py --today 2026-05-08       # fixed date

Emits on stdout:
  {
    "today": "2026-05-08",
    "current_month": {
      "date_from": "2026-04-01",
      "date_to":   "2026-04-30",
      "label":     "April 2026",
      "days_in_month": 30
    },
    "prior_month": {
      "date_from": "2026-03-01",
      "date_to":   "2026-03-31",
      "label":     "March 2026",
      "days_in_month": 31
    }
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


_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _months_back(today: date, n: int) -> tuple[int, int]:
    """Return (year, month) n whole months before today's month."""
    y, m = today.year, today.month - n
    while m <= 0:
        m += 12
        y -= 1
    return y, m


def _build_month(year: int, month: int) -> dict:
    days = monthrange(year, month)[1]
    return {
        "date_from": f"{year:04d}-{month:02d}-01",
        "date_to":   f"{year:04d}-{month:02d}-{days:02d}",
        "label":     f"{_MONTH_NAMES[month]} {year}",
        "days_in_month": days,
    }


def compute_windows(today: date) -> dict:
    """Strictly-before rule:

    current_month is the calendar month that ended strictly before `today`.
    On the last day of any month, that month is NOT yet "ended" (it ends at
    23:59:59 of that day) — so today=May 31 has current=April, not May.

    Implementation: current_month is always the month that contained
    `today - 1 day`'s month, EXCEPT when today is the 1st of a month, in
    which case (today - 1 day) is the last day of the previous month
    which would still be "the month that just ended" — and we want one
    further back. So we just unconditionally subtract one full month.

    Wait: re-read the rule. On May 1, "ended strictly before today" — May 1
    means today is in May; the month that ended strictly before May 1 is
    April (which ended April 30). So current = April. (today - 1 month) =
    April 1, which IS in April. ✓

    On May 31, current should be April per the rule. (today - 1 month) =
    April 30, which IS in April. ✓

    On June 1, current should be May per the rule. (today - 1 month) =
    May 1, which IS in May. ✓

    So "subtract 1 month" gives us current_month for every input. Simple.
    """
    cur_y, cur_m = _months_back(today, 1)
    prior_y, prior_m = _months_back(today, 2)
    return {
        "today": today.isoformat(),
        "current_month": _build_month(cur_y, cur_m),
        "prior_month":   _build_month(prior_y, prior_m),
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
                raise SystemExit(
                    f"compute_month_windows: --today {raw!r} is not YYYY-MM-DD ({exc})"
                )
    return date.today()


def main(argv: list[str]) -> int:
    try:
        today = _parse_today(argv)
    except SystemExit as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    result = compute_windows(today)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
