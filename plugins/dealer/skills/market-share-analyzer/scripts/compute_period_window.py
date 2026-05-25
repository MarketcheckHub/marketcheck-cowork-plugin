#!/usr/bin/env python3
"""
compute_period_window.py — Emit a calendar-month-aligned date window for any
`get_sold_summary` workflow. Sister script to `compute_sold_summary_dates.py`
(which is hardcoded to the 3-month rolling window for W3 dealer-group rollups);
this one is flexible.

Usage:
  compute_period_window.py --months-back 1 --num-months 1
  compute_period_window.py --months-back 1 --num-months 1 --today 2026-04-30
  compute_period_window.py --months-back 2 --num-months 1   # month-before-last
  compute_period_window.py --months-back 4 --num-months 3   # quarter prior to last full quarter

Semantics:
  date_to   = last day of (current_month − months_back)
  date_from = first day of (current_month − months_back − num_months + 1)

So `--months-back 1 --num-months 1` returns the single month immediately
before the current (in-progress) month — the W1/W2/W4/W5 default for
"current period." `--months-back 2 --num-months 1` returns the month
before that — the prior-period default.

Emits on stdout:
  {
    "date_from": "YYYY-MM-DD",
    "date_to":   "YYYY-MM-DD",
    "label":     "<human label>",
    "months_included": ["YYYY-MM", ...],
    "today":     "YYYY-MM-DD",
    "months_back": <int>,
    "num_months": <int>
  }

Exit codes:
  0  success
  1  malformed --today value or invalid --months-back / --num-months
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
    y, m = today.year, today.month - n
    while m <= 0:
        m += 12
        y -= 1
    return y, m


def compute_window(today: date, months_back: int, num_months: int) -> dict:
    if months_back < 1:
        raise ValueError(f"months_back must be >= 1, got {months_back}")
    if num_months < 1:
        raise ValueError(f"num_months must be >= 1, got {num_months}")

    to_year, to_month = _months_back(today, months_back)
    date_to = _last_of_month(to_year, to_month)

    from_offset = months_back + num_months - 1
    from_year, from_month = _months_back(today, from_offset)
    date_from = _first_of_month(from_year, from_month)

    months: list[str] = []
    for i in range(from_offset, months_back - 1, -1):
        y, m = _months_back(today, i)
        months.append(f"{y:04d}-{m:02d}")

    if num_months == 1:
        label = f"month {months[0]}"
    else:
        label = f"{num_months} months {months[0]} to {months[-1]}"

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "label": label,
        "months_included": months,
        "today": today.isoformat(),
        "months_back": months_back,
        "num_months": num_months,
    }


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _parse_today(argv: list[str]) -> date:
    raw = _arg_value(argv, "--today")
    if raw is None:
        return date.today()
    try:
        y, m, d = raw.split("-")
        return date(int(y), int(m), int(d))
    except (ValueError, TypeError) as exc:
        raise SystemExit(f"compute_period_window: --today {raw!r} is not YYYY-MM-DD ({exc})")


def _parse_int(argv: list[str], flag: str, default: int) -> int:
    raw = _arg_value(argv, flag)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"compute_period_window: {flag} {raw!r} is not an integer ({exc})")


def main(argv: list[str]) -> int:
    try:
        today = _parse_today(argv)
        months_back = _parse_int(argv, "--months-back", 1)
        num_months = _parse_int(argv, "--num-months", 1)
        result = compute_window(today, months_back, num_months)
    except SystemExit as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except ValueError as exc:
        sys.stderr.write(f"compute_period_window: {exc}\n")
        return 1

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
