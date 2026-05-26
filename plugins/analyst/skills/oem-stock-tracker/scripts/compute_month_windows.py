#!/usr/bin/env python3
"""
compute_month_windows.py — Emit calendar-month-aligned `current_month`,
`prior_month`, and `baseline_3mo_window` for the W1 (3-window MoM + 3-mo
trend) and W2 / W3 (current month only) workflows.

The skill needs:
  - current_month: the calendar month that ended strictly before today
                   (per the strictly-before rule).
  - prior_month:   the calendar month immediately before current_month.
  - baseline_3mo_window: a date range spanning the 3 months immediately
                   before current_month — i.e., months -1, -2, -3 (NOT
                   including current). Used in a single multi-month
                   `get_sold_summary` call to fetch the rolling-quarter
                   baseline plus per-month rows for current and prior.

Strictly-before rule (sidesteps the race where sold-summary aggregates
lag the calendar): current_month is the calendar month that ended STRICTLY
BEFORE today. On May 31 → April. On June 1 → May. On May 1 → April.

Usage:
  compute_month_windows.py                                # uses system date, default 3-mo baseline
  compute_month_windows.py --today 2026-05-08             # fixed date
  compute_month_windows.py --today 2026-05-08 --baseline-months 6
                                                           # 6-mo baseline window

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
    },
    "baseline_3mo_window": {
      "date_from": "2026-01-01",       // first of (current - 3 months)
      "date_to":   "2026-03-31",       // last of (current - 1 month) — i.e. prior_month.date_to
      "label":     "January 2026 - March 2026",
      "months_count": 3
    }
  }

Note: the baseline_3mo_window's date_to is the SAME as prior_month.date_to.
A multi-month sold-summary call uses date_from = baseline_3mo_window.date_from
and date_to = current_month.date_to to cover all 4 months in one call;
the parser groups the response rows by month and the caller assigns each
month to current / prior / baseline_3mo via this script's emitted windows.

Exit codes:
  0  success
  1  malformed --today value or invalid --baseline-months (must be >= 1)
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


def _build_baseline_window(today: date, current_y: int, current_m: int, baseline_months: int) -> dict:
    """Build the multi-month baseline window: months -1, -2, ..., -baseline_months
    relative to current_month. NOT including current.

    date_from = first day of month (current - baseline_months)
    date_to   = last day of month (current - 1) = prior_month.date_to
    """
    # Start: baseline_months back from current
    start_y, start_m = _months_back(today, baseline_months + 1)
    # End: 1 month back from current (= prior_month)
    end_y, end_m = _months_back(today, 2)
    end_days = monthrange(end_y, end_m)[1]

    return {
        "date_from": f"{start_y:04d}-{start_m:02d}-01",
        "date_to":   f"{end_y:04d}-{end_m:02d}-{end_days:02d}",
        "label":     f"{_MONTH_NAMES[start_m]} {start_y} - {_MONTH_NAMES[end_m]} {end_y}",
        "months_count": baseline_months,
    }


def compute_windows(today: date, baseline_months: int = 3) -> dict:
    """Strictly-before rule: current_month is the month that ended strictly
    before today. Subtracting 1 full month from today gives that month.

    On May 1 → April (1 month back from May 1 = April 1, which is in April). ✓
    On May 31 → April (1 month back from May 31 = April 30, which is in April). ✓
    On June 1 → May (1 month back from June 1 = May 1, which is in May). ✓
    """
    cur_y, cur_m = _months_back(today, 1)
    prior_y, prior_m = _months_back(today, 2)
    baseline = _build_baseline_window(today, cur_y, cur_m, baseline_months)
    return {
        "today": today.isoformat(),
        "current_month": _build_month(cur_y, cur_m),
        "prior_month":   _build_month(prior_y, prior_m),
        # canonical key consumed by compute_oem_stats — same object as the alias
        "baseline_3mo": baseline,
        # legacy alias retained for back-compat with older docs/tests
        "baseline_3mo_window": baseline,
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


def _parse_baseline_months(argv: list[str]) -> int:
    if "--baseline-months" in argv:
        idx = argv.index("--baseline-months")
        if idx + 1 < len(argv):
            raw = argv[idx + 1]
            try:
                n = int(raw)
                if n < 1:
                    raise SystemExit(
                        f"compute_month_windows: --baseline-months {n} must be >= 1"
                    )
                return n
            except ValueError as exc:
                raise SystemExit(
                    f"compute_month_windows: --baseline-months {raw!r} is not an integer ({exc})"
                )
    return 3


def main(argv: list[str]) -> int:
    try:
        today = _parse_today(argv)
        baseline_months = _parse_baseline_months(argv)
    except SystemExit as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    result = compute_windows(today, baseline_months=baseline_months)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
