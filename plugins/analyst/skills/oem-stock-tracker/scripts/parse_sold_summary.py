#!/usr/bin/env python3
"""
parse_sold_summary.py — Normalise a `get_sold_summary` response.

Adapted from `dealer-group-health-monitor/scripts/parse_sold_summary.py`,
with OEM-specific aggregation modes:

  --aggregate-make <make>
    Sum sold_count and weight ASP/DOM by sold_count across all rows whose
    `make` matches <make>. Used by W2 (single-month per-make calls).
    Emits `make_baseline`.

  --aggregate-make-by-window <make>
    Like --aggregate-make but groups rows by `month` first; emits a
    `months: {"YYYY-MM": <aggregate>, ...}` map. Used by W1 (multi-month
    per-make sold call covering current + prior + 3-mo baseline window).
    The caller (compute_oem_stats.py) assigns each month bucket to the
    current / prior / baseline_3mo window via compute_month_windows.py.

  --aggregate-by-dimension <body_type|make>
    Bucket all rows by the named row dimension and emit one aggregate
    record per unique value, with weighted ASP/DOM and share_pct of the
    dimension total. Used by:
      - W3 (top-25 makes leaderboard, single month, ranking_dimensions=make)
      - W1 Wave A1 market share (single month, ranking_dimensions=make)
      - W1 Wave A2 segment mix (single month, ranking_dimensions=body_type)

  --aggregate-by-dimension <body_type|make> --by-window
    Same as above but additionally groups each dimension bucket by month.
    Used by W1 pure-play EV market leaders (multi-month, top_n=10 on
    fuel_type_category=EV). Emits per-bucket `months: {"YYYY-MM":
    <aggregate>, ...}` maps.

All aggregation flags are mutually exclusive. Passing more than one is a
usage error (exit 1).

Divide-by-zero guard: when sum(sold_count) across matching rows is 0,
`make_baseline = null` with `make_baseline_skipped_reason`. Same guard
drops zero-sold buckets entirely from `--aggregate-by-dimension` output.

Null-priced rows (territories like MP with `null` ASP) are dropped from
BOTH the numerator AND denominator of the weighted-ASP mean — they
contribute to neither sum nor weight. Same for null-DOM rows. Per
references/multi-make-aggregation.md.

Usage:
  parse_sold_summary.py                                            # raw normalize
  parse_sold_summary.py --file <path>                              # truncation envelope
  parse_sold_summary.py --aggregate-make "Ford"                    # single-make single-month
  parse_sold_summary.py --aggregate-make-by-window "Ford"          # single-make multi-month
  parse_sold_summary.py --aggregate-by-dimension make              # multi-make single-month
  parse_sold_summary.py --aggregate-by-dimension make --by-window  # multi-make multi-month
  parse_sold_summary.py --aggregate-by-dimension body_type         # segment mix single-month
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _common import read_input, emit, classify_error, arg_value, arg_flag


MAKE_MODEL_HINTS = [
    "make_model_not_found",
    "no data found for make",
    "no data found for model",
    "invalid make",
    "invalid model",
]

DIMENSION_LIMIT_HINTS = [
    "ranking_dimensions",
    "dimension",
    "too many dimensions",
]


ALLOWED_DIMENSIONS = ("body_type", "make")


def _classify_sold_error(payload: Any) -> tuple[str, str]:
    """Inspect a sold-summary failure payload and classify the error."""
    text = ""
    if isinstance(payload, str):
        text = payload
    elif isinstance(payload, dict):
        if payload.get("success") is False:
            status = payload.get("status_code")
            text = payload.get("error") or json.dumps(payload)
            if isinstance(status, int):
                if status == 422:
                    return "network_422", json.dumps(payload)[:500]
                if 500 <= status < 600:
                    return "network_5xx", json.dumps(payload)[:500]
            low = str(text).lower()
            if "client error '422" in low or " 422 " in low or low.startswith("422"):
                return "network_422", text[:500]
            if any(f"client error '{code}" in low for code in ("500", "502", "503", "504")):
                return "network_5xx", text[:500]
        else:
            return "", ""
    low = str(text).lower()
    if "exceeds maximum allowed tokens" in low:
        return "truncation_unrecovered", text[:500]
    if any(h in low for h in MAKE_MODEL_HINTS):
        return "make_model_not_found", text[:500]
    if any(h in low for h in DIMENSION_LIMIT_HINTS):
        return "validation_dimension_limit", text[:500]
    if text.startswith("Error:"):
        return "validation", text[:500]
    return "unknown", text[:500]


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


def _normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise a sold-summary row to canonical field names.

    Server quirks normalised:
      - `avg_msrp`            → `average_msrp`
      - `sale_price_std_dev`  → coerced from string to float
      - `sale_price_range`    → kept as string (single value, not low/high)
      - `rank`, `sold_count`  → coerced to int
      - all price/DOM fields  → coerced to float
    """
    return {
        "month": raw.get("month"),
        "inventory_type": raw.get("inventory_type"),
        "state": raw.get("state"),
        "city": raw.get("city"),
        "dealership_group_name": raw.get("dealership_group_name"),
        "make": raw.get("make"),
        "model": raw.get("model"),
        "body_type": raw.get("body_type"),
        "fuel_type_category": raw.get("fuel_type_category"),
        "rank": _to_int(raw.get("rank")),
        "sold_count": _to_int(raw.get("sold_count")),
        "average_sale_price": _to_float(raw.get("average_sale_price")),
        "total_sale_price": _to_float(raw.get("total_sale_price")),
        "average_msrp": _to_float(raw.get("avg_msrp")),
        "price_over_msrp_percentage": _to_float(raw.get("price_over_msrp_percentage")),
        "average_days_on_market": _to_float(raw.get("average_days_on_market")),
        "median_days_on_market": _to_float(raw.get("median_days_on_market")),
        "sale_price_range": raw.get("sale_price_range"),
        "sale_price_std_dev": _to_float(raw.get("sale_price_std_dev")),
    }


# ──────────────────────────────────────────────────────────────────────────
# Aggregation primitives (shared by all modes)
# ──────────────────────────────────────────────────────────────────────────

def _aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Compute sold-count-weighted aggregate across a row list.

    Null-priced rows drop from BOTH numerator AND denominator of the
    weighted-ASP mean. Same for null-DOM and null-MSRP-positioning.

    Returns None if total_sold == 0 (divide-by-zero guard).
    """
    total_sold = 0
    asp_num, asp_den = 0.0, 0
    dom_num, dom_den = 0.0, 0
    median_dom_num, median_dom_den = 0.0, 0
    msrp_pct_num, msrp_pct_den = 0.0, 0
    msrp_abs_num, msrp_abs_den = 0.0, 0  # avg_msrp dollar value
    months_seen: set[str] = set()

    for row in rows:
        sc = row.get("sold_count")
        if sc is None or sc <= 0:
            continue
        sc_int = int(sc)
        total_sold += sc_int

        if row.get("month"):
            months_seen.add(row["month"])

        # ASP: drop null from BOTH sides
        asp = row.get("average_sale_price")
        if asp is not None:
            asp_num += float(asp) * sc_int
            asp_den += sc_int

        # DOM: drop null from BOTH sides
        dom = row.get("average_days_on_market")
        if dom is not None:
            dom_num += float(dom) * sc_int
            dom_den += sc_int

        # Median DOM: same handling
        mdom = row.get("median_days_on_market")
        if mdom is not None:
            median_dom_num += float(mdom) * sc_int
            median_dom_den += sc_int

        # MSRP positioning (%): same handling
        msrp_pct = row.get("price_over_msrp_percentage")
        if msrp_pct is not None:
            msrp_pct_num += float(msrp_pct) * sc_int
            msrp_pct_den += sc_int

        # Average MSRP (absolute $): same handling
        msrp_abs = row.get("average_msrp")
        if msrp_abs is not None:
            msrp_abs_num += float(msrp_abs) * sc_int
            msrp_abs_den += sc_int

    if total_sold <= 0:
        return None

    return {
        "total_sold_count": total_sold,
        "weighted_avg_sale_price": (asp_num / asp_den) if asp_den > 0 else None,
        "weighted_avg_days_on_market": (dom_num / dom_den) if dom_den > 0 else None,
        "weighted_median_days_on_market": (median_dom_num / median_dom_den) if median_dom_den > 0 else None,
        "weighted_price_over_msrp_percentage": (msrp_pct_num / msrp_pct_den) if msrp_pct_den > 0 else None,
        "weighted_avg_msrp": (msrp_abs_num / msrp_abs_den) if msrp_abs_den > 0 else None,
        "row_count": len(rows),
        "months_included": sorted(months_seen),
    }


def _aggregate_for_make(
    rows: list[dict[str, Any]], make_name: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Single-make rollup (single-month or aggregated across months)."""
    target = (make_name or "").strip()
    if not target:
        return None, "no_make_provided"
    matching = [
        r for r in rows
        if str(r.get("make") or "").strip() == target
    ]
    if not matching:
        return None, "no_matching_rows"
    agg = _aggregate_rows(matching)
    if agg is None:
        return None, "all_zero"
    agg["make"] = target
    return agg, None


def _aggregate_make_by_window(
    rows: list[dict[str, Any]], make_name: str
) -> dict[str, Any]:
    """Group rows for one make by their `month` field. Emits a months map."""
    target = (make_name or "").strip()
    if not target:
        return {"make": None, "months": {}, "make_by_window_skipped_reason": "no_make_provided"}

    matching = [
        r for r in rows
        if str(r.get("make") or "").strip() == target
    ]
    if not matching:
        return {"make": target, "months": {}, "make_by_window_skipped_reason": "no_matching_rows"}

    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in matching:
        month = row.get("month")
        if month:
            by_month[month].append(row)

    months_out: dict[str, dict[str, Any]] = {}
    for month, month_rows in by_month.items():
        agg = _aggregate_rows(month_rows)
        if agg is None:
            continue  # drop zero-sold months
        months_out[month] = agg

    return {
        "make": target,
        "months": months_out,
        "row_count": len(matching),
    }


def _aggregate_by_dimension_all(
    rows: list[dict[str, Any]], dimension: str
) -> tuple[list[dict[str, Any]], int]:
    """Bucket rows by `dimension` and emit one aggregate per distinct value
    with share_pct. Single-month or aggregated-across-months."""
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = row.get(dimension)
        if key is None:
            continue
        key_str = str(key).strip()
        if not key_str:
            continue
        buckets[key_str].append(row)

    aggregated: list[dict[str, Any]] = []
    for value, value_rows in buckets.items():
        agg = _aggregate_rows(value_rows)
        if agg is None:
            continue
        aggregated.append({
            "value": value,
            **agg,
        })

    dimension_total = sum(b["total_sold_count"] for b in aggregated)
    for bucket in aggregated:
        if dimension_total > 0:
            bucket["share_pct"] = round(100 * bucket["total_sold_count"] / dimension_total, 2)
        else:
            bucket["share_pct"] = None

    aggregated.sort(key=lambda r: r["total_sold_count"] or 0, reverse=True)
    return aggregated, dimension_total


def _aggregate_by_dimension_by_window(
    rows: list[dict[str, Any]], dimension: str
) -> tuple[list[dict[str, Any]], int, list[str]]:
    """Bucket rows by `dimension` AND month. Emits per-bucket month maps."""
    # First bucket by dimension value, then within each bucket group by month
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = row.get(dimension)
        if key is None:
            continue
        key_str = str(key).strip()
        if not key_str:
            continue
        buckets[key_str].append(row)

    all_months: set[str] = set()
    aggregated: list[dict[str, Any]] = []

    for value, value_rows in buckets.items():
        by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in value_rows:
            m = row.get("month")
            if m:
                by_month[m].append(row)

        months_out: dict[str, dict[str, Any]] = {}
        total_for_bucket = 0
        for month, mrows in by_month.items():
            agg = _aggregate_rows(mrows)
            if agg is None:
                continue
            # H1: lean per-month bucket — only `total_sold_count` is consumed by
            # compute_oem_stats._compute_market_share (per-month shares recomputed
            # downstream from cohort totals). Dropping the other 7 weighted-stat
            # fields takes M=3 leaderboard output from ~48 KB → ~5-7 KB.
            months_out[month] = {"total_sold_count": agg["total_sold_count"]}
            total_for_bucket += agg["total_sold_count"]
            all_months.add(month)

        if total_for_bucket == 0:
            continue

        # H1: top-level lean shape — keep only `value`, `months`, `total_sold_count_all_months`.
        # `share_pct_all_months` and `row_count` are dropped (not consumed downstream).
        aggregated.append({
            "value": value,
            "months": months_out,
            "total_sold_count_all_months": total_for_bucket,
        })

    dimension_total_all = sum(b["total_sold_count_all_months"] for b in aggregated)
    aggregated.sort(key=lambda r: r["total_sold_count_all_months"] or 0, reverse=True)
    return aggregated, dimension_total_all, sorted(all_months)


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    payload, source = read_input(argv)

    aggregate_make = arg_value(argv, "--aggregate-make")
    aggregate_make_window = arg_value(argv, "--aggregate-make-by-window")
    aggregate_by_dim = arg_value(argv, "--aggregate-by-dimension")
    by_window = arg_flag(argv, "--by-window")

    # Mutual-exclusion check
    active_modes = sum([
        aggregate_make is not None,
        aggregate_make_window is not None,
        aggregate_by_dim is not None,
    ])
    if active_modes > 1:
        sys.stderr.write(
            "parse_sold_summary: --aggregate-make, --aggregate-make-by-window, and "
            "--aggregate-by-dimension are mutually exclusive\n"
        )
        return 1

    # --by-window is only meaningful with --aggregate-by-dimension
    if by_window and aggregate_by_dim is None:
        sys.stderr.write(
            "parse_sold_summary: --by-window requires --aggregate-by-dimension\n"
        )
        return 1

    # Validate dimension value before any payload work
    if aggregate_by_dim is not None and aggregate_by_dim not in ALLOWED_DIMENSIONS:
        emit({
            "ok": False,
            "error_type": "invalid_dimension",
            "error": (
                f"--aggregate-by-dimension must be one of "
                f"{list(ALLOWED_DIMENSIONS)}; got {aggregate_by_dim!r}"
            ),
            "source": source,
        })
        return 0

    # First, check for the generic transport-level failures
    etype, emsg = classify_error(payload)
    if etype:
        sold_type, sold_msg = _classify_sold_error(payload)
        if sold_type:
            emit({"ok": False, "error_type": sold_type, "error": sold_msg, "source": source})
            return 0
        emit({"ok": False, "error_type": etype, "error": emsg, "source": source})
        return 0

    # A plain string payload means the local validator rejected the request
    if isinstance(payload, str):
        sold_type, sold_msg = _classify_sold_error(payload)
        emit({"ok": False, "error_type": sold_type or "validation",
              "error": sold_msg, "source": source})
        return 0

    data = payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]

    if not isinstance(data, dict):
        emit({"ok": False, "error_type": "unexpected_shape",
              "error": "payload not a dict", "source": source})
        return 0

    # Upstream may return rows under `results`, `rows`, or `data` (live shape)
    rows_raw = data.get("results") or data.get("rows") or data.get("data") or []
    if not isinstance(rows_raw, list):
        rows_raw = []

    rows = [_normalize_row(r) for r in rows_raw if isinstance(r, dict)]

    out: dict[str, Any] = {
        "ok": True,
        "row_count": len(rows),
        "rows": rows,
        "source": source,
    }

    if aggregate_make is not None:
        baseline, skipped_reason = _aggregate_for_make(rows, aggregate_make)
        out["make_baseline"] = baseline
        if skipped_reason is not None:
            out["make_baseline_skipped_reason"] = skipped_reason

    if aggregate_make_window is not None:
        by_window_result = _aggregate_make_by_window(rows, aggregate_make_window)
        out["make_by_window"] = by_window_result

    if aggregate_by_dim is not None:
        if by_window:
            dim_values, dim_total_all, all_months = _aggregate_by_dimension_by_window(rows, aggregate_by_dim)
            out["dimension"] = aggregate_by_dim
            out["by_window"] = True
            out["dimension_values"] = dim_values
            out["dimension_total_sold_count_all_months"] = dim_total_all
            out["months_included"] = all_months
        else:
            dim_values, dim_total = _aggregate_by_dimension_all(rows, aggregate_by_dim)
            out["dimension"] = aggregate_by_dim
            out["by_window"] = False
            out["dimension_values"] = dim_values
            out["dimension_total_sold_count"] = dim_total

    if aggregate_make is not None or aggregate_make_window is not None or aggregate_by_dim is not None:
        out.pop("rows", None)

    emit(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
