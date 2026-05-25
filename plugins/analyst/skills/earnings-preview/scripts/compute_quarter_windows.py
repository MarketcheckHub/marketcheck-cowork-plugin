#!/usr/bin/env python3
"""
compute_quarter_windows.py — Emit calendar-quarter-aligned windows for W1's
per-quarter sold data (current, prior, year-ago) PLUS a single
`most_recent_complete_month` block for the Days Supply calculation (which
pairs live `num_found` with one month of sold velocity, not one quarter).

The skill needs:
  - current_quarter:    the latest calendar quarter that ended STRICTLY BEFORE
                        today. Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep,
                        Q4 = Oct-Dec.
  - prior_quarter:      the calendar quarter immediately before current_quarter.
  - year_ago_quarter:   the same calendar quarter from one year earlier.
  - most_recent_complete_month:
                        the calendar month that ended STRICTLY BEFORE today.
                        Uses the same monthly strictly-before rule as
                        oem-stock-tracker/scripts/compute_month_windows.py.
                        Days Supply divisor:
                          days_supply = num_found * days_in_month / sold_count_mrcm

Strictly-before rule examples:
  today = 2026-05-13 → current_quarter = Q1 2026 (Jan-Mar);
                       most_recent_complete_month = April 2026
  today = 2026-04-01 → current_quarter = Q1 2026; mrcm = March 2026
  today = 2026-03-31 → current_quarter = Q4 2025 (Q1 2026 not yet ended);
                       mrcm = February 2026
  today = 2026-07-01 → current_quarter = Q2 2026; mrcm = June 2026
  today = 2024-03-15 → current_quarter = Q4 2023; mrcm = February 2024
                       (leap-year February: days_in_month = 29)

Note: `most_recent_complete_month` and `current_quarter.date_to` can differ.
  On 2026-05-13: current_quarter.date_to = 2026-03-31 (end of Q1)
                 most_recent_complete_month.date_to = 2026-04-30
  This is intentional: the quarter window captures the analyst-reportable
  quarter; the month block captures the live-data divisor for Days Supply.

KMX fiscal-year caveat: KMX (CarMax) reports on a March-February fiscal year,
so its fiscal Q4 (Dec-Feb) overlaps but does not match calendar Q1 (Jan-Mar).
This script ALWAYS emits calendar quarters; SKILL.md surfaces a KMX-specific
caveat in the confirmation header. Per-ticker fiscal-quarter override is a
v1.1 candidate.

Usage:
  compute_quarter_windows.py                       # uses system date
  compute_quarter_windows.py --today 2026-05-13    # fixed date

Emits on stdout (JSON, indented):
  {
    "today": "2026-05-13",
    "current_quarter": {
      "date_from":       "2026-01-01",
      "date_to":         "2026-03-31",
      "label":           "Q1 2026",
      "days_in_quarter": 90,
      "months":          ["2026-01", "2026-02", "2026-03"]
    },
    "prior_quarter":    {<same shape, Q4 2025>},
    "year_ago_quarter": {<same shape, Q1 2025>},
    "most_recent_complete_month": {
      "date_from":     "2026-04-01",
      "date_to":       "2026-04-30",
      "label":         "April 2026",
      "days_in_month": 30
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
    """Return (year, month) n whole months before today's month.

    Mirrors oem-stock-tracker's helper so the monthly strictly-before
    rule remains identical across skills.
    """
    y, m = today.year, today.month - n
    while m <= 0:
        m += 12
        y -= 1
    return y, m


def _today_quarter(today: date) -> int:
    """Return the calendar quarter (1-4) containing today's date.

    Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dec.
    """
    return (today.month - 1) // 3 + 1


def _quarter_minus_one(year: int, q: int) -> tuple[int, int]:
    """One calendar quarter back. Wraps year boundary at Q1."""
    if q == 1:
        return year - 1, 4
    return year, q - 1


def _build_quarter(year: int, q: int) -> dict:
    """Emit a quarter block.

    Returns {date_from, date_to, label, days_in_quarter, months}.

    days_in_quarter handles month-length variation correctly:
      Q1 = 90 (or 91 in leap years), Q2 = 91, Q3 = 92, Q4 = 92.
    """
    first_month = (q - 1) * 3 + 1                  # Q1→1, Q2→4, Q3→7, Q4→10
    last_month = first_month + 2
    first_date = date(year, first_month, 1)
    last_day = monthrange(year, last_month)[1]
    last_date = date(year, last_month, last_day)
    days_in_quarter = (last_date - first_date).days + 1
    months = [f"{year:04d}-{m:02d}" for m in range(first_month, last_month + 1)]
    return {
        "date_from": first_date.isoformat(),
        "date_to": last_date.isoformat(),
        "label": f"Q{q} {year}",
        "days_in_quarter": days_in_quarter,
        "months": months,
    }


def _build_most_recent_complete_month(today: date) -> dict:
    """The calendar month that ended STRICTLY BEFORE today.

    Matches the monthly strictly-before rule from oem-tracker:
      today=2026-05-01 → April 2026  (April ended Apr 30, strictly before May 1)
      today=2026-05-31 → April 2026  (May not yet ended at any time on May 31)
      today=2026-06-01 → May 2026
      today=2024-02-29 → January 2024
      today=2026-01-15 → December 2025  (year boundary)
    """
    y, m = _months_back(today, 1)
    days = monthrange(y, m)[1]
    return {
        "date_from": f"{y:04d}-{m:02d}-01",
        "date_to":   f"{y:04d}-{m:02d}-{days:02d}",
        "label":     f"{_MONTH_NAMES[m]} {y}",
        "days_in_month": days,
    }


def compute_windows(today: date) -> dict:
    """Compute all three quarter windows + most_recent_complete_month.

    The strictly-before rule applies at both the quarter level (current_quarter
    is the latest quarter that ended STRICTLY before today) and the month
    level (most_recent_complete_month is the latest month that ended STRICTLY
    before today). The two windows can resolve to non-overlapping date ranges
    when today sits well inside a quarter — see module docstring example for
    2026-05-13.
    """
    today_q = _today_quarter(today)
    # current_quarter = the quarter immediately before today's calendar quarter
    # (today's quarter is in progress and has not ended).
    cur_year, cur_q = _quarter_minus_one(today.year, today_q)
    prior_year, prior_q = _quarter_minus_one(cur_year, cur_q)
    year_ago_year, year_ago_q = cur_year - 1, cur_q

    return {
        "today": today.isoformat(),
        "current_quarter":  _build_quarter(cur_year, cur_q),
        "prior_quarter":    _build_quarter(prior_year, prior_q),
        "year_ago_quarter": _build_quarter(year_ago_year, year_ago_q),
        "most_recent_complete_month": _build_most_recent_complete_month(today),
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
                    f"compute_quarter_windows: --today {raw!r} is not YYYY-MM-DD ({exc})"
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
