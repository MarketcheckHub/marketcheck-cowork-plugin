#!/usr/bin/env python3
"""
parse_sold_summary.py — Normalise a `get_sold_summary` response.

Adapted from `dealer-group-health-monitor/scripts/parse_sold_summary.py`
with two new aggregation modes added (`--aggregate-make-by-window`, mirroring
`oem-stock-tracker`'s pattern; `--aggregate-group-by-window`, net-new
for dealer-group multi-quarter target rollup) and one math change (disciplined
null-handling per `oem-stock-tracker/references/multi-make-aggregation.md`).

Six mutually-exclusive aggregation flags, plus raw normalization with no flag:

  (no flag)
    Raw normalization only — emit per-row canonical-fielded rows for inspection.

  --aggregate-group <canonical>
    Filter to one dealership_group_name and emit weighted-mean baseline across
    all matching rows (multi-month rolled into one aggregate). Preserved from
    dealer-group base.

  --aggregate-group-by-window <canonical>   [NEW]
    Filter to one dealership_group_name; group remaining rows by `month`;
    emit one aggregate per month under `group_by_window.months`. Caller (e.g.,
    compute_earnings_signals.py) assigns each month to current_quarter /
    prior_quarter / year_ago_quarter using the windows from
    compute_quarter_windows.py.

  --aggregate-make <make>                    [NEW; mirrors --aggregate-group]
    Filter to one make and emit weighted-mean baseline (single-window).

  --aggregate-make-by-window <make>          [NEW; mirrors oem-tracker]
    Filter to one make; group remaining rows by `month`; emit one aggregate
    per month under `make_by_window.months`. Used by every per-make OEM target
    sold call and EV-slice call in this skill's Wave A1.

  --aggregate-by-group
    Bucket ALL rows by dealership_group_name (no target filter); emit one
    aggregate record per unique group sorted desc by total_sold_count.
    Preserved from dealer-group base. Not used by W1 in this skill (no
    leaderboard workflow) but kept for parity / future v1.1.

  --aggregate-by-dimension {body_type|make}
    Bucket rows by row dimension; emit one aggregate per distinct value with
    `share_pct` of total. Preserved from dealer-group base. Not used by W1
    in this skill but kept for parity / future v1.1.

Math discipline — null-priced rows drop from BOTH numerator AND denominator
of every weighted mean. The row's `sold_count` (the weight) still contributes
to `total_sold_count`. This differs from the naive "skip nulls in numerator
only" that the dealer-group source originally used. Per
`oem-stock-tracker/references/multi-make-aggregation.md §"Why we drop
null-priced rows from BOTH"`. Matters most for low-volume nameplates in
sub-unit territories (MP, GU, etc.) where null-ASP rows can be 5-10 % of
returned rows.

Server-side field-name normalisations applied at parse time:
  avg_msrp           → average_msrp
  sale_price_std_dev → coerced to float, name preserved
  sale_price_range   → kept as string (single value, NOT a low/high pair)
  rank, sold_count   → coerced to int

Divide-by-zero guards (M8): when `sum(sold_count) == 0` for an aggregate,
emit `null` with a `*_skipped_reason` explaining the cause. Never emit NaN or
fabricate a 0-weight mean. Same guard drops zero-sold buckets entirely from
`--aggregate-by-dimension` output.

Error classification:
  make_model_not_found     → facet-discover and retry once (rare here)
  validation_dimension_limit → drop ranking_dimensions to canonical
  validation                → skip + DQ event
  network_422 / network_5xx → skip + DQ event
  invalid_dimension         → caller passed an unsupported dimension value
  truncation_unrecovered    → re-fire with narrower filter
  unknown                   → skip + DQ event with snippet

See `references/script-contracts.md §parse_sold_summary` for the canonical
per-mode output shape, error envelopes, and edge cases.

Usage:
  parse_sold_summary.py                                       # raw, stdin
  parse_sold_summary.py --file <path>                         # raw, file
  parse_sold_summary.py --aggregate-group "Carmax"
  parse_sold_summary.py --aggregate-group-by-window "Carmax" --file <path>
  parse_sold_summary.py --aggregate-make "Ford" --file <path>
  parse_sold_summary.py --aggregate-make-by-window "Ford" --file <path>
  parse_sold_summary.py --aggregate-by-group
  parse_sold_summary.py --aggregate-by-dimension body_type
  parse_sold_summary.py --aggregate-by-dimension make
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from typing import Any

from _common import read_input, emit, classify_error, arg_value, arg_flag


# ─── Error-classification hints ────────────────────────────────────────────

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

# Dimensions accepted by --aggregate-by-dimension. Restricted to body_type
# and make (the values dealer-group's Wave B fires today). This skill does
# not currently invoke --aggregate-by-dimension, but the mode is preserved.
ALLOWED_DIMENSIONS = ("body_type", "make")


def _classify_sold_error(payload: Any) -> tuple[str, str]:
    """Inspect a sold-summary failure payload and classify the error.

    `get_sold_summary`'s local validator returns a plain string on failure
    (not a JSON envelope). The MCP envelope then wraps it. Upstream HTTP
    errors come back as `{success:false, service, error:"Client error '<code> ..."}`
    with NO structured `status_code` field — status must be parsed from the
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
    # Truncation error string begins with "Error: result (N chars) exceeds
    # maximum allowed tokens..." Check first; otherwise the generic "Error:"
    # prefix below would swallow it as "validation".
    if "exceeds maximum allowed tokens" in low:
        return "truncation_unrecovered", text[:500]
    if any(h in low for h in MAKE_MODEL_HINTS):
        return "make_model_not_found", text[:500]
    if any(h in low for h in DIMENSION_LIMIT_HINTS):
        return "validation_dimension_limit", text[:500]
    if text.startswith("Error:"):
        return "validation", text[:500]
    return "unknown", text[:500]


# ─── Type coercion helpers ─────────────────────────────────────────────────


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


# ─── Row normalization ─────────────────────────────────────────────────────


def _normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise a sold-summary row to canonical field names.

    Server field-name quirks (verified live; see
    `references/sold-summary-safety.md §Field-name quirks`):
      - `avg_msrp`         → `average_msrp`
      - `sale_price_range` → kept as string (single value, NOT a low/high pair)
      - `sale_price_std_dev` → coerced to float, name preserved
      - `rank`             → present on every row when ranking_dimensions is set
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


# ─── Core aggregation — disciplined null-handling ──────────────────────────


def _aggregate_within_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Sold-count-weighted aggregate over a list of normalised rows.

    Returns a dict of weighted means plus `total_sold_count`, `row_count`,
    and `months_included`. Returns `None` if no row has `sold_count > 0`
    (divide-by-zero guard).

    Math discipline (`references/sold-summary-safety.md §"EV classification"`
    and the upstream multi-make-aggregation.md):

        weighted_X = Σ(X_i × sc_i for non-null X_i)
                   / Σ(sc_i for non-null X_i ONLY)

    Null-valued rows drop from BOTH numerator AND denominator. The row's
    `sold_count` (weight) still contributes to `total_sold_count` regardless.

    The five weighted metrics tracked:
      average_sale_price            → weighted_avg_sale_price
      average_days_on_market        → weighted_avg_days_on_market
      median_days_on_market         → weighted_median_days_on_market
      average_msrp                  → weighted_avg_msrp
      price_over_msrp_percentage    → weighted_price_over_msrp_percentage
    """
    total_sold = 0

    sum_price = 0.0
    n_price = 0
    sum_dom = 0.0
    n_dom = 0
    sum_median_dom = 0.0
    n_median_dom = 0
    sum_msrp = 0.0
    n_msrp = 0
    sum_msrp_gap = 0.0
    n_msrp_gap = 0

    months: set[str] = set()

    for row in rows:
        sc = row.get("sold_count")
        if sc is None or sc <= 0:
            continue
        sc = int(sc)
        total_sold += sc

        price = row.get("average_sale_price")
        if price is not None:
            sum_price += float(price) * sc
            n_price += sc

        dom = row.get("average_days_on_market")
        if dom is not None:
            sum_dom += float(dom) * sc
            n_dom += sc

        median_dom = row.get("median_days_on_market")
        if median_dom is not None:
            sum_median_dom += float(median_dom) * sc
            n_median_dom += sc

        msrp = row.get("average_msrp")
        if msrp is not None:
            sum_msrp += float(msrp) * sc
            n_msrp += sc

        msrp_gap = row.get("price_over_msrp_percentage")
        if msrp_gap is not None:
            sum_msrp_gap += float(msrp_gap) * sc
            n_msrp_gap += sc

        month_str = row.get("month")
        if month_str:
            months.add(month_str)

    if total_sold <= 0:
        return None

    return {
        "total_sold_count": total_sold,
        "weighted_avg_sale_price":
            (sum_price / n_price) if n_price > 0 else None,
        "weighted_avg_days_on_market":
            (sum_dom / n_dom) if n_dom > 0 else None,
        "weighted_median_days_on_market":
            (sum_median_dom / n_median_dom) if n_median_dom > 0 else None,
        "weighted_avg_msrp":
            (sum_msrp / n_msrp) if n_msrp > 0 else None,
        "weighted_price_over_msrp_percentage":
            (sum_msrp_gap / n_msrp_gap) if n_msrp_gap > 0 else None,
        "row_count": len(rows),
        "months_included": sorted(months),
    }


# ─── Single-window aggregators ─────────────────────────────────────────────


def _aggregate_for_group(
    rows: list[dict[str, Any]], canonical: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Filter rows to one dealership_group_name; aggregate across all months.

    Returns (group_baseline, skipped_reason). skipped_reason is set when no
    rows match, when canonical is empty, or when total_sold == 0; baseline
    is None in those cases.
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
    agg = _aggregate_within_rows(matching)
    if agg is None:
        return None, "all_zero"
    agg["dealership_group_name"] = target
    return agg, None


def _aggregate_for_make(
    rows: list[dict[str, Any]], make_name: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Filter rows to one make; aggregate across all months. Mirrors
    `_aggregate_for_group` shape but keys on `make` instead of
    `dealership_group_name`."""
    target = (make_name or "").strip()
    if not target:
        return None, "no_make_provided"
    matching = [r for r in rows if str(r.get("make") or "").strip() == target]
    if not matching:
        return None, "no_matching_rows"
    agg = _aggregate_within_rows(matching)
    if agg is None:
        return None, "all_zero"
    agg["make"] = target
    return agg, None


# ─── Multi-window aggregators (NEW — by-window modes) ──────────────────────


def _aggregate_group_by_window(
    rows: list[dict[str, Any]], canonical: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Filter rows to one dealership_group_name; group remaining rows by
    `month`; emit one aggregate per month under `months: {"YYYY-MM": <agg>, ...}`.

    Output shape:
      {
        "dealership_group_name": "Carmax",
        "months": {
          "2026-04": {<aggregate>},
          "2026-03": {<aggregate>},
          ...
        },
        "row_count": N
      }

    Months with `total_sold_count == 0` are dropped from `months` (divide-by-zero
    discipline). If no months produce a non-zero aggregate, returns
    `(None, "all_zero")`.
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

    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in matching:
        month_str = row.get("month")
        if month_str:
            by_month[month_str].append(row)

    months_map: dict[str, dict[str, Any]] = {}
    for month_str, month_rows in by_month.items():
        agg = _aggregate_within_rows(month_rows)
        if agg is not None:
            months_map[month_str] = agg

    if not months_map:
        return None, "all_zero"

    return {
        "dealership_group_name": target,
        "months": months_map,
        "row_count": len(matching),
    }, None


def _aggregate_make_by_window(
    rows: list[dict[str, Any]], make_name: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Filter rows to one make; group remaining rows by `month`; emit one
    aggregate per month under `months`. Mirrors `_aggregate_group_by_window`
    shape but keys on `make`.
    """
    target = (make_name or "").strip()
    if not target:
        return None, "no_make_provided"
    matching = [r for r in rows if str(r.get("make") or "").strip() == target]
    if not matching:
        return None, "no_matching_rows"

    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in matching:
        month_str = row.get("month")
        if month_str:
            by_month[month_str].append(row)

    months_map: dict[str, dict[str, Any]] = {}
    for month_str, month_rows in by_month.items():
        agg = _aggregate_within_rows(month_rows)
        if agg is not None:
            months_map[month_str] = agg

    if not months_map:
        return None, "all_zero"

    return {
        "make": target,
        "months": months_map,
        "row_count": len(matching),
    }, None


# ─── Cross-bucket aggregators (preserved from dealer-group source) ─────────


def _aggregate_by_group_all(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bucket all rows by `dealership_group_name`; emit one aggregate per
    unique group. Sorted desc by `total_sold_count`. Groups with zero
    sold_count are dropped (not emitted as null records).

    Not used by W1 in this skill; preserved from dealer-group base for parity.
    """
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        name = row.get("dealership_group_name")
        if name:
            buckets[name].append(row)

    out: list[dict[str, Any]] = []
    for name, group_rows in buckets.items():
        agg = _aggregate_within_rows(group_rows)
        if agg is not None:
            agg["dealership_group_name"] = name
            out.append(agg)
    out.sort(key=lambda r: r["total_sold_count"] or 0, reverse=True)
    return out


def _aggregate_by_dimension_all(
    rows: list[dict[str, Any]], dimension: str
) -> tuple[list[dict[str, Any]], int]:
    """Bucket rows by `row[dimension]` value; emit one aggregate per distinct
    value, with `share_pct` of the dimension total. Sorted desc by
    `total_sold_count`. Buckets with `total_sold == 0` are dropped.

    Rows with None / empty-string dimension value are skipped (the API can
    emit blank ranking values when underlying data is partially classified).

    Not used by W1 in this skill; preserved from dealer-group base for parity.
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
        agg = _aggregate_within_rows(value_rows)
        if agg is None:
            continue
        agg["value"] = value
        aggregated.append(agg)

    dimension_total = sum(b["total_sold_count"] for b in aggregated)
    # Second pass attaches share_pct based on the post-skip denominator.
    for bucket in aggregated:
        if dimension_total > 0:
            bucket["share_pct"] = round(
                100 * bucket["total_sold_count"] / dimension_total, 2
            )
        else:
            bucket["share_pct"] = None

    aggregated.sort(key=lambda r: r["total_sold_count"] or 0, reverse=True)
    return aggregated, dimension_total


# ─── Main ───────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    payload, source = read_input(argv)

    aggregate_group = arg_value(argv, "--aggregate-group")
    aggregate_group_by_window = arg_value(argv, "--aggregate-group-by-window")
    aggregate_make = arg_value(argv, "--aggregate-make")
    aggregate_make_by_window = arg_value(argv, "--aggregate-make-by-window")
    aggregate_by_group_flag = arg_flag(argv, "--aggregate-by-group")
    aggregate_by_dim = arg_value(argv, "--aggregate-by-dimension")

    # Six-way mutual-exclusion check (at most one aggregation flag).
    active_modes = sum([
        aggregate_group is not None,
        aggregate_group_by_window is not None,
        aggregate_make is not None,
        aggregate_make_by_window is not None,
        aggregate_by_group_flag,
        aggregate_by_dim is not None,
    ])
    if active_modes > 1:
        sys.stderr.write(
            "parse_sold_summary: --aggregate-group, --aggregate-group-by-window, "
            "--aggregate-make, --aggregate-make-by-window, --aggregate-by-group, "
            "and --aggregate-by-dimension are mutually exclusive\n"
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

    # First, check for the generic transport-level failures.
    etype, emsg = classify_error(payload)
    if etype:
        # Pass through the sold-specific classifier for finer diagnosis.
        sold_type, sold_msg = _classify_sold_error(payload)
        if sold_type:
            emit({"ok": False, "error_type": sold_type, "error": sold_msg, "source": source})
            return 0
        emit({"ok": False, "error_type": etype, "error": emsg, "source": source})
        return 0

    # A plain string payload means the local validator rejected the request.
    if isinstance(payload, str):
        sold_type, sold_msg = _classify_sold_error(payload)
        emit({
            "ok": False,
            "error_type": sold_type or "validation",
            "error": sold_msg,
            "source": source,
        })
        return 0

    data = payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]

    if not isinstance(data, dict):
        emit({
            "ok": False,
            "error_type": "unexpected_shape",
            "error": "payload not a dict",
            "source": source,
        })
        return 0

    # Upstream may return rows under `results`, `rows`, or `data`.
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

    elif aggregate_group_by_window is not None:
        by_window, skipped_reason = _aggregate_group_by_window(
            rows, aggregate_group_by_window
        )
        out["group_by_window"] = by_window
        if skipped_reason is not None:
            out["group_by_window_skipped_reason"] = skipped_reason

    elif aggregate_make is not None:
        baseline, skipped_reason = _aggregate_for_make(rows, aggregate_make)
        out["make_baseline"] = baseline
        if skipped_reason is not None:
            out["make_baseline_skipped_reason"] = skipped_reason

    elif aggregate_make_by_window is not None:
        by_window, skipped_reason = _aggregate_make_by_window(
            rows, aggregate_make_by_window
        )
        out["make_by_window"] = by_window
        if skipped_reason is not None:
            out["make_by_window_skipped_reason"] = skipped_reason

    elif aggregate_by_group_flag:
        out["groups"] = _aggregate_by_group_all(rows)

    elif aggregate_by_dim is not None:
        dim_values, dim_total = _aggregate_by_dimension_all(rows, aggregate_by_dim)
        out["dimension"] = aggregate_by_dim
        out["dimension_values"] = dim_values
        out["dimension_total_sold_count"] = dim_total

    emit(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
