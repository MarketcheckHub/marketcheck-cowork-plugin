#!/usr/bin/env python3
"""
parse_sold_summary.py — Normalise a `get_sold_summary` response.

Adapted from the gold-standard `competitive-pricer-updated` parser, with
three aggregation flags specific to the dealer-group-health-monitor:

  --aggregate-group <canonical_name>
    Sum sold_count and weight ASP/DOM by sold_count across all rows whose
    dealership_group_name matches <canonical_name>. Used by W1/W2 (filtered
    single-group calls).

  --aggregate-by-group
    Bucket all rows by dealership_group_name and emit one aggregate record
    per unique group. Used by W3 (peer-leaderboard call returns 20 groups
    × multiple states; collapse to per-group records).

  --aggregate-by-dimension <body_type|make>
    Bucket all rows by the named row dimension and emit one aggregate
    record per unique value, with weighted ASP/DOM and share_pct of the
    total. Used by W1/W2 Wave B (mix calls with ranking_dimensions=body_type
    or ranking_dimensions=make).

The three flags are mutually exclusive — passing more than one is a usage error.

Classifies errors so the caller can branch by error_type:
  - make_model_not_found        → facet-discover and retry once (rare here)
  - validation_dimension_limit  → drop ranking_dimensions to "dealership_group_name"
  - validation                  → skip the call
  - network_422 / network_5xx   → skip the call
  - invalid_dimension           → caller passed an unsupported dimension value
  - unknown                     → skip the call

Usage:
  parse_sold_summary.py                                          # stdin, no aggregation
  parse_sold_summary.py --file <path>                            # truncation envelope
  parse_sold_summary.py --aggregate-group "Carmax"               # single-group baseline
  parse_sold_summary.py --aggregate-by-group                     # per-group records (W3)
  parse_sold_summary.py --aggregate-by-dimension body_type       # body-type rollup (W1/W2 Wave B)
  parse_sold_summary.py --aggregate-by-dimension make            # make rollup (W1/W2 Wave B)

Divide-by-zero guard (M8): when sum(sold_count) across matching rows is 0,
`group_baseline = null` with `group_baseline_skipped_reason` explaining
the cause. Never emits NaN or fabricates a 0-weight mean. The same guard
drops zero-sold buckets entirely from `--aggregate-by-dimension` output.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
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


# Dimensions accepted by --aggregate-by-dimension. Restricted to the
# values Wave B actually fires today; extending later is a one-line change
# but every addition needs a corresponding test.
ALLOWED_DIMENSIONS = ("body_type", "make")


def _classify_sold_error(payload: Any) -> tuple[str, str]:
    """Inspect a sold-summary failure payload and classify the error.

    get_sold_summary's local validator returns a plain string on failure
    (not a JSON envelope). The MCP envelope then wraps it. Upstream HTTP
    errors come back as {success:false, service, error:"Client error '<code> ...'"}
    with NO structured status_code field — status must be parsed from the
    error string.
    """
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
    # Truncation error string can begin with "Error: result (N chars)
    # exceeds maximum...", which would otherwise be swallowed by the generic
    # "Error:" prefix check below as "validation". Check truncation first.
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

    Real server field names (confirmed by live calls in the gold standard):
      - `avg_msrp` (NOT `average_msrp`)
      - `sale_price_range` (single string value; NOT `price_range_low`/`high`)
      - `sale_price_std_dev` (NOT `standard_deviation`)
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


# ─── Aggregations ───────────────────────────────────────────────────────────


def _aggregate_for_group(
    rows: list[dict[str, Any]], canonical: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Compute weighted-mean baseline across rows matching `canonical`.

    Returns (group_baseline, skipped_reason). Skipped_reason is set when no
    rows match or total_sold == 0; baseline is None in that case.
    """
    target = (canonical or "").strip()
    if not target:
        return None, "no_canonical_provided"
    matching = [
        r for r in rows
        if str(r.get("dealership_group_name") or "").strip() == target
    ]
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
        if row.get("month") and row["month"] not in months:
            months.append(row["month"])
    if total_sold <= 0:
        return None, "all_zero"
    return {
        "dealership_group_name": target,
        "total_sold_count": total_sold,
        "weighted_avg_sale_price": sum_price_weight / total_sold if sum_price_weight else None,
        "weighted_avg_days_on_market": sum_dom_weight / total_sold if sum_dom_weight else None,
        "months_included": sorted(months),
        "row_count_for_group": len(matching),
    }, None


def _aggregate_by_group_all(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bucket rows by dealership_group_name and emit one aggregate per group.

    Skips groups with total_sold_count == 0 (don't emit a null record per
    group; just drop them from the list).
    """
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        name = row.get("dealership_group_name")
        if not name:
            continue
        buckets[name].append(row)
    out: list[dict[str, Any]] = []
    for name, group_rows in buckets.items():
        baseline, _ = _aggregate_for_group(group_rows, name)
        if baseline is not None:
            # rename the field for the per-group emission shape (Plan §parse_sold_summary)
            out.append({
                "dealership_group_name": name,
                "total_sold_count": baseline["total_sold_count"],
                "weighted_avg_sale_price": baseline["weighted_avg_sale_price"],
                "weighted_avg_days_on_market": baseline["weighted_avg_days_on_market"],
                "row_count": baseline["row_count_for_group"],
                "months_included": baseline["months_included"],
            })
    # Sort desc by total_sold_count for downstream convenience (W3 leaderboard).
    out.sort(key=lambda r: r["total_sold_count"] or 0, reverse=True)
    return out


def _aggregate_by_dimension_all(
    rows: list[dict[str, Any]], dimension: str
) -> tuple[list[dict[str, Any]], int]:
    """Bucket rows by `dimension` (a row field, e.g. body_type or make) and emit
    one aggregate per distinct value, with share_pct of the dimension total.

    Mirrors `_aggregate_by_group_all` but keys on `row.get(dimension)`.

    Rows with a None / empty-string dimension value are skipped (the API can
    emit blank ranking values when underlying data is partially classified).
    Buckets whose summed sold_count is 0 are dropped (same divide-by-zero
    guard as `_aggregate_for_group`).

    Returns (dimension_values, dimension_total_sold_count). The list is
    sorted desc by total_sold_count.
    """
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
        total_sold = 0
        sum_price_weight = 0.0
        sum_dom_weight = 0.0
        months: list[str] = []
        for row in value_rows:
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
            if row.get("month") and row["month"] not in months:
                months.append(row["month"])
        if total_sold <= 0:
            # Drop the bucket entirely — never emit a null aggregate per value.
            continue
        aggregated.append({
            "value": value,
            "total_sold_count": total_sold,
            "weighted_avg_sale_price": sum_price_weight / total_sold if sum_price_weight else None,
            "weighted_avg_days_on_market": sum_dom_weight / total_sold if sum_dom_weight else None,
            "row_count": len(value_rows),
            "months_included": sorted(months),
        })

    dimension_total = sum(b["total_sold_count"] for b in aggregated)
    # Second pass to attach share_pct now that the denominator is known.
    # Done as a second pass (not inline) so the denominator reflects the
    # post-skip total, not the pre-skip total.
    for bucket in aggregated:
        if dimension_total > 0:
            bucket["share_pct"] = round(100 * bucket["total_sold_count"] / dimension_total, 2)
        else:
            bucket["share_pct"] = None

    aggregated.sort(key=lambda r: r["total_sold_count"] or 0, reverse=True)
    return aggregated, dimension_total


# ─── Main ───────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    payload, source = read_input(argv)
    aggregate_group = arg_value(argv, "--aggregate-group")
    aggregate_by_group = arg_flag(argv, "--aggregate-by-group")
    aggregate_by_dim = arg_value(argv, "--aggregate-by-dimension")

    # Mutual-exclusion check (three-way: at most one aggregation flag).
    active_modes = sum([
        aggregate_group is not None,
        aggregate_by_group,
        aggregate_by_dim is not None,
    ])
    if active_modes > 1:
        sys.stderr.write(
            "parse_sold_summary: --aggregate-group, --aggregate-by-group, and "
            "--aggregate-by-dimension are mutually exclusive\n"
        )
        return 1

    # Validate the dimension value before any payload work so a bad CLI
    # invocation fails fast and consistently.
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
        # Pass through the sold-specific classifier for finer diagnosis
        sold_type, sold_msg = _classify_sold_error(payload)
        if sold_type:
            emit({"ok": False, "error_type": sold_type, "error": sold_msg, "source": source})
            return 0
        emit({"ok": False, "error_type": etype, "error": emsg, "source": source})
        return 0

    # A plain string payload means the local validator rejected the request
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

    # Upstream may return rows under `results`, `rows`, or `data`
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

    if aggregate_group is not None:
        baseline, skipped_reason = _aggregate_for_group(rows, aggregate_group)
        out["group_baseline"] = baseline
        if skipped_reason is not None:
            out["group_baseline_skipped_reason"] = skipped_reason

    if aggregate_by_group:
        out["groups"] = _aggregate_by_group_all(rows)

    if aggregate_by_dim is not None:
        dim_values, dim_total = _aggregate_by_dimension_all(rows, aggregate_by_dim)
        out["dimension"] = aggregate_by_dim
        out["dimension_values"] = dim_values
        out["dimension_total_sold_count"] = dim_total

    emit(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
