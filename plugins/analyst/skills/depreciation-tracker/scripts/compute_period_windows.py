#!/usr/bin/env python3
"""
compute_period_windows.py — Emit calendar-month-aligned date windows for the
depreciation-tracker workflows (W1 / W2 / W3 / W5).

`get_sold_summary` rejects mis-aligned dates with HTTP 422 (per
`references/sold-summary-safety.md`); the safe pattern is to anchor every
window on the first / last day of a calendar month. This helper computes a
full set of windows in one shot so the workflow caller never hand-computes
any date.

Usage:
  compute_period_windows.py                                    # default periods
  compute_period_windows.py --today 2026-05-25                 # fixed today
  compute_period_windows.py --periods current,60d,90d,6mo,1yr  # explicit list

Default periods: current,60d,90d,6mo,1yr.

Period semantics (each window is exactly one calendar month wide):
  current  → most-recent full calendar month (date_to is end of last month)
  60d      → 2 months before current
  90d      → 3 months before current
  6mo      → 6 months before current
  1yr      → 12 months before current

NOTE on "current": the *current* in-progress month is never used for sold
data — it lags. So `current` resolves to *the most-recent full calendar
month*.

Emits on stdout:
  {
    "today": "YYYY-MM-DD",
    "periods": [
      {"label": "current", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD",
       "month": "YYYY-MM", "months_offset_from_today": <int>},
      ...   (sorted oldest-first by months_offset_from_today desc, current last)
    ]
  }

Exit codes:
  0  success
  1  malformed --today value or unknown period token
"""

from __future__ import annotations

import json
import sys
from calendar import monthrange
from datetime import date


PERIOD_OFFSETS = {
    "current": 1,
    "60d": 2,
    "90d": 3,
    "6mo": 6,
    "1yr": 12,
}

DEFAULT_PERIODS = ["current", "60d", "90d", "6mo", "1yr"]


def _months_back(today: date, n: int) -> tuple[int, int]:
    y, m = today.year, today.month - n
    while m <= 0:
        m += 12
        y -= 1
    return y, m


def _window_for_offset(today: date, offset_months: int) -> dict:
    y, m = _months_back(today, offset_months)
    last_day = monthrange(y, m)[1]
    return {
        "date_from": date(y, m, 1).isoformat(),
        "date_to": date(y, m, last_day).isoformat(),
        "month": f"{y:04d}-{m:02d}",
    }


def compute_periods(today: date, period_tokens: list[str]) -> dict:
    rows = []
    for token in period_tokens:
        if token not in PERIOD_OFFSETS:
            raise ValueError(
                f"unknown period token {token!r}; valid: {sorted(PERIOD_OFFSETS)}"
            )
        offset = PERIOD_OFFSETS[token]
        win = _window_for_offset(today, offset)
        rows.append({
            "label": token,
            "months_offset_from_today": offset,
            **win,
        })
    rows.sort(key=lambda r: -r["months_offset_from_today"])
    return {"today": today.isoformat(), "periods": rows}


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
                    f"compute_period_windows: --today {raw!r} is not YYYY-MM-DD ({exc})"
                )
    return date.today()


def _parse_periods(argv: list[str]) -> list[str]:
    if "--periods" in argv:
        idx = argv.index("--periods")
        if idx + 1 < len(argv):
            raw = argv[idx + 1]
            tokens = [t.strip() for t in raw.split(",") if t.strip()]
            if not tokens:
                raise SystemExit("compute_period_windows: --periods is empty")
            return tokens
    return DEFAULT_PERIODS


def main(argv: list[str]) -> int:
    try:
        today = _parse_today(argv)
        tokens = _parse_periods(argv)
        result = compute_periods(today, tokens)
    except SystemExit as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except ValueError as exc:
        sys.stderr.write(f"compute_period_windows: {exc}\n")
        return 1

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
