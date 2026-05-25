#!/usr/bin/env python3
"""
parse_sold_summary.py — Normalise a `get_sold_summary` response.

Classifies errors so the caller can branch by error_type:
  - make_model_not_found        → facet-discover and retry once
  - validation_dimension_limit  → drop ranking_dimensions to "make" and retry
  - validation                  → skip the state line
  - network_422 / network_5xx   → skip the state line
  - unknown                     → skip the state line

On success, normalises the rows to a canonical shape.

Usage:
  parse_sold_summary.py                              # stdin, no aggregation
  parse_sold_summary.py --file <path>                # truncation envelope
  parse_sold_summary.py --aggregate-state CA         # compute state_baseline
  parse_sold_summary.py --aggregate-multi-period     # group rows by month +
                                                     # emit per-month + overall
                                                     # weighted aggregates
                                                     # (used by W1 curve)

The two aggregation flags are independent and may be combined.

With --aggregate-state, after normalising the returned month-bucketed rows,
compute a weighted-mean State Baseline across rows where `state == <STATE>`.
Divide-by-zero guard: when sum(sold_count) across matching rows is 0,
`state_baseline = null` with `state_baseline_skipped_reason` explaining the
cause. Never emits NaN or fabricates a 0-weight mean.
"""

from __future__ import annotations

import json
import sys
from typing import Any

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


def _classify_sold_error(payload: Any) -> tuple[str, str]:
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

    Real server field names (confirmed by live call, not from the doc):
      - `avg_msrp` (NOT `average_msrp`)
      - `sale_price_range` (single string value)
      - `sale_price_std_dev`
      - `rank` (present on every row when ranking_dimensions is set)
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


def _aggregate_multi_period(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Group rows by `month` and emit per-month + overall weighted aggregates.

    Used by the depreciation-tracker W1 curve workflow. Each call typically
    spans a single month, but the server returns one row per (month,
    dimensions) tuple — so multi-make rollups yield multiple rows.

    Aggregation: sum `sold_count`, weighted means of `average_sale_price`,
    `average_days_on_market`, and `average_msrp` (weight = sold_count).

    Divide-by-zero guard: when `total_sold_count == 0` for a month bucket
    (or overall), the corresponding `weighted_avg_*` fields emit `None`
    instead of NaN.
    """
    months_index: dict[str, dict[str, Any]] = {}

    def _bucket_init(label: str | None) -> dict[str, Any]:
        return {
            "month": label,
            "total_sold_count": 0,
            "_price_weight_sum": 0.0,
            "_dom_weight_sum": 0.0,
            "_msrp_weight_sum": 0.0,
            "row_count": 0,
        }

    overall = _bucket_init(None)

    for row in rows:
        sc = row.get("sold_count")
        if sc is None or sc <= 0:
            continue
        month_label = row.get("month") or "unknown"
        bucket = months_index.setdefault(month_label, _bucket_init(month_label))
        for dest in (bucket, overall):
            dest["total_sold_count"] += int(sc)
            dest["row_count"] += 1
            price = row.get("average_sale_price")
            if price is not None:
                dest["_price_weight_sum"] += float(price) * int(sc)
            dom = row.get("average_days_on_market")
            if dom is not None:
                dest["_dom_weight_sum"] += float(dom) * int(sc)
            msrp = row.get("average_msrp")
            if msrp is not None:
                dest["_msrp_weight_sum"] += float(msrp) * int(sc)

    def _finalize(bucket: dict[str, Any]) -> dict[str, Any]:
        n = bucket["total_sold_count"]
        if n <= 0:
            return {
                "month": bucket["month"],
                "total_sold_count": 0,
                "weighted_avg_sale_price": None,
                "weighted_avg_days_on_market": None,
                "weighted_avg_msrp": None,
                "row_count": bucket["row_count"],
            }
        return {
            "month": bucket["month"],
            "total_sold_count": n,
            "weighted_avg_sale_price": bucket["_price_weight_sum"] / n if bucket["_price_weight_sum"] else None,
            "weighted_avg_days_on_market": bucket["_dom_weight_sum"] / n if bucket["_dom_weight_sum"] else None,
            "weighted_avg_msrp": bucket["_msrp_weight_sum"] / n if bucket["_msrp_weight_sum"] else None,
            "row_count": bucket["row_count"],
        }

    months_out = [_finalize(b) for _, b in sorted(months_index.items(), key=lambda t: t[0])]
    return {
        "months": months_out,
        "overall": _finalize(overall),
        "row_count_total": len(rows),
    }


def _aggregate_state_baseline(rows: list[dict[str, Any]], state: str) -> tuple[dict[str, Any] | None, str | None]:
    """Compute weighted-mean State Baseline across rows matching `state`.

    Returns (state_baseline, skipped_reason). Preserved from the dealer-side
    reference for forward compatibility; not currently used by any analyst
    workflow.
    """
    target = (state or "").strip().upper()
    if not target:
        return None, "no_state_provided"
    matching = [r for r in rows if str(r.get("state") or "").strip().upper() == target]
    if not matching:
        return None, "no_matching_rows"
    total_sold = 0
    sum_price_weight = 0.0
    sum_dom_weight = 0.0
    months: list[str] = []
    for row in matching:
        sc = row.get("sold_count")
        if sc is None or sc <= 0:
            continue
        total_sold += int(sc)
        price = row.get("average_sale_price")
        if price is not None:
            sum_price_weight += float(price) * int(sc)
        dom = row.get("average_days_on_market")
        if dom is not None:
            sum_dom_weight += float(dom) * int(sc)
        if row.get("month"):
            months.append(row["month"])
    if total_sold <= 0:
        return None, "all_zero"
    baseline = {
        "state": target,
        "total_sold_count": total_sold,
        "weighted_avg_sale_price": sum_price_weight / total_sold if sum_price_weight else None,
        "weighted_avg_days_on_market": sum_dom_weight / total_sold if sum_dom_weight else None,
        "months_included": months,
        "row_count_for_state": len(matching),
    }
    return baseline, None


def main(argv: list[str]) -> int:
    payload, source = read_input(argv)
    aggregate_state = arg_value(argv, "--aggregate-state")

    etype, emsg = classify_error(payload)
    if etype:
        sold_type, sold_msg = _classify_sold_error(payload)
        if sold_type:
            emit({"ok": False, "error_type": sold_type, "error": sold_msg, "source": source})
            return 0
        emit({"ok": False, "error_type": etype, "error": emsg, "source": source})
        return 0

    if isinstance(payload, str):
        sold_type, sold_msg = _classify_sold_error(payload)
        emit({"ok": False, "error_type": sold_type or "validation", "error": sold_msg, "source": source})
        return 0

    data = payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]

    if not isinstance(data, dict):
        emit({"ok": False, "error_type": "unexpected_shape", "error": "payload not a dict", "source": source})
        return 0

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

    if aggregate_state:
        baseline, skipped_reason = _aggregate_state_baseline(rows, aggregate_state)
        out["state_baseline"] = baseline
        if skipped_reason is not None:
            out["state_baseline_skipped_reason"] = skipped_reason

    if arg_flag(argv, "--aggregate-multi-period"):
        out["multi_period_aggregate"] = _aggregate_multi_period(rows)

    emit(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
