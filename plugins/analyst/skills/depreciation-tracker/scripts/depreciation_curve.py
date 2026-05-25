#!/usr/bin/env python3
"""
depreciation_curve.py — Core stats engine for W1 (Make/Model Depreciation Curve).

Reads a JSON config from stdin describing the per-period sold-summary
aggregates and emits the assembled curve: retention %, monthly rate,
annualized rate, acceleration verdict, and curve-shape classifier.

In v1.0.0 of the analyst port, anchor_mode is always "prior_period" (the
MSRP-anchor path is dropped — see SKILL.md §W1 No Wave B).

Acceleration verdict (5-band raw label; analyst BULLISH / NEUTRAL / CAUTION
/ BEARISH mapping lives in `references/signal-aggregation.md`):
  - Strong Retention      monthly_rate < 0.3% (or appreciation, monthly_rate < 0)
  - Stable                0.3% ≤ monthly_rate < 0.6%
  - Slight Decline        0.6% ≤ monthly_rate < 1.0%
  - Moderate Depreciation 1.0% ≤ monthly_rate < 1.5%
  - Accelerated Loss      monthly_rate ≥ 1.5%

Curve-shape classifier:
  Compares the most-recent monthly rate to the longest-window rate.
  - "accelerating"  → recent rate > longest * 1.25
  - "stabilizing"   → recent rate < longest * 0.75
  - "linear"        → in between

Input (stdin JSON):
  {
    "periods": [
      {
        "label":                    "1yr" | "6mo" | "90d" | "60d" | "current",
        "months_offset_from_today": <int>,
        "month":                    "YYYY-MM",
        "weighted_avg_sale_price":  <float|null>,
        "total_sold_count":         <int>
      }, ...   (any order; engine sorts by months_offset_from_today desc)
    ],
    "msrp":        null,                 # always null in v1.0.0 of analyst port
    "anchor_mode": "prior_period"        # always "prior_period" in v1.0.0
  }

Output (stdout JSON):
  {
    "ok": true,
    "anchor_used":      "prior_period",
    "anchor_value":     null,
    "periods": [   (oldest-first)
      {
        "label":                <str>,
        "month":                <YYYY-MM | null>,
        "months_offset_from_today": <int>,
        "avg_price":            <float|null>,
        "sold_count":           <int>,
        "retention_pct_msrp":   null,
        "retention_pct_prior":  <float|null>,
        "monthly_rate_pct":     <float|null>,
        "annualized_rate_pct":  <float|null>
      }, ...
    ],
    "verdict":          "Strong Retention" | ... | "Accelerated Loss" | null,
    "curve_shape":      "accelerating" | "linear" | "stabilizing" | null,
    "recent_monthly_rate_pct":  <float|null>,
    "longest_monthly_rate_pct": <float|null>
  }

Failure modes:
  - bad_stdin            — stdin is not valid JSON
  - insufficient_periods — fewer than 2 priced periods
"""

from __future__ import annotations

import json
import sys
from typing import Any


VERDICT_BANDS = [
    ("Strong Retention",      None,    0.3),
    ("Stable",                0.3,     0.6),
    ("Slight Decline",        0.6,     1.0),
    ("Moderate Depreciation", 1.0,     1.5),
    ("Accelerated Loss",      1.5,     None),
]

CURVE_ACCEL_RATIO = 1.25
CURVE_STABILIZE_RATIO = 0.75


def _verdict_for_rate(rate_pct: float | None) -> str | None:
    if rate_pct is None:
        return None
    for label, lo, hi in VERDICT_BANDS:
        if lo is None and rate_pct < hi:
            return label
        if hi is None and rate_pct >= lo:
            return label
        if lo is not None and hi is not None and lo <= rate_pct < hi:
            return label
    return None


def _curve_shape(recent: float | None, longest: float | None) -> str | None:
    if recent is None or longest is None:
        return None
    if longest == 0:
        return "linear"
    ratio = recent / longest
    if ratio > CURVE_ACCEL_RATIO:
        return "accelerating"
    if ratio < CURVE_STABILIZE_RATIO:
        return "stabilizing"
    return "linear"


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int:
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    periods_raw = cfg.get("periods") or []
    if not isinstance(periods_raw, list):
        periods_raw = []

    msrp = _to_float(cfg.get("msrp"))
    anchor_mode = (cfg.get("anchor_mode") or "auto").lower()
    if anchor_mode == "auto":
        anchor_used = "msrp" if (msrp is not None and msrp > 0) else "prior_period"
    elif anchor_mode == "msrp":
        if msrp is None or msrp <= 0:
            anchor_used = "prior_period"
        else:
            anchor_used = "msrp"
    else:
        anchor_used = "prior_period"

    cleaned: list[dict[str, Any]] = []
    for p in periods_raw:
        if not isinstance(p, dict):
            continue
        cleaned.append({
            "label": p.get("label"),
            "month": p.get("month"),
            "months_offset_from_today": _to_int(p.get("months_offset_from_today")),
            "avg_price": _to_float(p.get("weighted_avg_sale_price")),
            "sold_count": _to_int(p.get("total_sold_count")),
        })

    cleaned.sort(key=lambda r: -r["months_offset_from_today"])

    priced = [p for p in cleaned if p["avg_price"] is not None and p["avg_price"] > 0]
    if len(priced) < 2:
        json.dump({
            "ok": False,
            "error_type": "insufficient_periods",
            "error": f"only {len(priced)} priced periods (need at least 2)",
            "anchor_used": anchor_used,
            "periods": cleaned,
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    out_periods: list[dict[str, Any]] = []
    prior_price: float | None = None
    prior_offset: int | None = None
    for p in cleaned:
        avg = p["avg_price"]
        retention_msrp: float | None = None
        if anchor_used == "msrp" and msrp and avg is not None:
            retention_msrp = avg / msrp * 100.0
        retention_prior: float | None = None
        monthly_rate: float | None = None
        if avg is not None and prior_price is not None and prior_price > 0:
            retention_prior = avg / prior_price * 100.0
            months_between = (prior_offset - p["months_offset_from_today"]) \
                if prior_offset is not None else None
            if months_between and months_between > 0:
                pct_change = (prior_price - avg) / prior_price * 100.0
                monthly_rate = pct_change / months_between
        annualized = monthly_rate * 12.0 if monthly_rate is not None else None
        out_periods.append({
            "label": p["label"],
            "month": p["month"],
            "months_offset_from_today": p["months_offset_from_today"],
            "avg_price": avg,
            "sold_count": p["sold_count"],
            "retention_pct_msrp": retention_msrp,
            "retention_pct_prior": retention_prior,
            "monthly_rate_pct": monthly_rate,
            "annualized_rate_pct": annualized,
        })
        if avg is not None and avg > 0:
            prior_price = avg
            prior_offset = p["months_offset_from_today"]

    recent_rate = out_periods[-1]["monthly_rate_pct"] if out_periods else None
    longest_rate: float | None = None
    if priced and len(priced) >= 2:
        oldest = priced[0]
        newest = priced[-1]
        months_span = oldest["months_offset_from_today"] - newest["months_offset_from_today"]
        if months_span > 0 and oldest["avg_price"] and oldest["avg_price"] > 0:
            pct = (oldest["avg_price"] - newest["avg_price"]) / oldest["avg_price"] * 100.0
            longest_rate = pct / months_span

    verdict = _verdict_for_rate(recent_rate)
    curve_shape = _curve_shape(recent_rate, longest_rate)

    out = {
        "ok": True,
        "anchor_used": anchor_used,
        "anchor_value": msrp if anchor_used == "msrp" else None,
        "periods": out_periods,
        "verdict": verdict,
        "curve_shape": curve_shape,
        "recent_monthly_rate_pct": recent_rate,
        "longest_monthly_rate_pct": longest_rate,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
