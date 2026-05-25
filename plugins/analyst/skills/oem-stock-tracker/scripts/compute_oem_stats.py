#!/usr/bin/env python3
"""
compute_oem_stats.py — Multi-make / multi-state numerical-aggregation engine
for the OEM Stock Tracker skill. Consumes assembled JSON from the parsed
Wave A1/A2 responses; emits raw numeric values (NO bands — banding lives
in aggregate_signals.py).

Stdin JSON contract (see references/script-contracts.md for full details):
  {
    "ticker": "F" | null,                                # null for brand_orphan
    "company_name": "Ford Motor Company",
    "classification": "legacy" | "pure_play" | "brand_orphan",
    "makes": ["Ford", "Lincoln"],
    "inventory_type": "New" | "Used",
    "windows": {
      "current_month":   {date_from, date_to, label, days_in_month},
      "prior_month":     {date_from, date_to, label, days_in_month},
      "baseline_3mo":    {date_from, date_to, label, months_count}
    },
    "per_make": {
      "<Make>": {
        "sold_by_window":     {"months": {"YYYY-MM": <agg>, ...}},  # from parse_sold_summary --aggregate-make-by-window
        "active":             {num_found, stats: {price, dom}} | null,
        "segment_mix":        [{value, total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, share_pct}, ...] | null,
        "ev_slice_by_window": {"months": {"YYYY-MM": <agg>, ...}} | null
      }
    },
    "market_top25": {
      "current": [<dimension_value_record>, ...],   # from parse_sold_summary --aggregate-by-dimension make
      "prior":   [<dimension_value_record>, ...]
    },
    "ev_market_leaders": {                          # pure-play only
      "months": {<YYYY-MM>: [<dim_value_record>, ...]},
      "all_months": [<dim_value_record>, ...]
    } | null
  }

Where `<agg>` is the parse_sold_summary aggregate shape with keys:
  total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market,
  weighted_price_over_msrp_percentage, weighted_avg_msrp, row_count

Stdout JSON contract (see references/script-contracts.md):
  {
    ok, ticker, company_name, classification,
    headline,
    leading_indicators_raw,     # 7 raw metrics (no bands)
    per_make_raw,                # null for N==1 tickers
    active_inventory,            # per-make
    market_context,              # top_10 + target_share + rank
    ev_block,                    # transition | market_leaders | omitted
    segment_mix,                 # ticker-level top body types
    dq_events
  }

Edge-case handling (resolved as null, never NaN or fabricated):
  - mom_pct / trend_3mo_pct when denominator is 0 or null
  - dom delta_days when either side is null
  - ev_transition entire block when zero EV volume (DQ event k)
  - per_make_raw when N == 1 (no breakdown to render)
  - low-volume DQ event (i) when any make < 100/month national
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _common import emit
from aggregate_signals import band_volume_mom


LOW_VOLUME_FLOOR_NATIONAL = 100  # units/month per make


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


def _safe_pct_change(current: float | None, prior: float | None) -> float | None:
    """(current - prior) / prior * 100. None if prior is None/0 or current is None."""
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / prior * 100.0


def _safe_delta(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None:
        return None
    return current - prior


def _weighted_combine(per_make_aggs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Combine multiple per-make aggregates into one ticker-level aggregate.

    Each per-make aggregate is in parse_sold_summary's output shape:
      {total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market,
       weighted_price_over_msrp_percentage, weighted_avg_msrp, ...}

    Weights by total_sold_count; drops null-valued fields from both
    numerator AND denominator (per multi-make-aggregation.md).
    """
    if not per_make_aggs:
        return None

    total_sold = 0
    asp_num, asp_den = 0.0, 0
    dom_num, dom_den = 0.0, 0
    msrp_pct_num, msrp_pct_den = 0.0, 0
    msrp_abs_num, msrp_abs_den = 0.0, 0

    for agg in per_make_aggs:
        if not isinstance(agg, dict):
            continue
        sc = _to_int(agg.get("total_sold_count")) or 0
        if sc <= 0:
            continue
        total_sold += sc

        asp = _to_float(agg.get("weighted_avg_sale_price"))
        if asp is not None:
            asp_num += asp * sc
            asp_den += sc

        dom = _to_float(agg.get("weighted_avg_days_on_market"))
        if dom is not None:
            dom_num += dom * sc
            dom_den += sc

        msrp_pct = _to_float(agg.get("weighted_price_over_msrp_percentage"))
        if msrp_pct is not None:
            msrp_pct_num += msrp_pct * sc
            msrp_pct_den += sc

        msrp_abs = _to_float(agg.get("weighted_avg_msrp"))
        if msrp_abs is not None:
            msrp_abs_num += msrp_abs * sc
            msrp_abs_den += sc

    if total_sold <= 0:
        return None

    return {
        "total_sold_count": total_sold,
        "weighted_avg_sale_price": (asp_num / asp_den) if asp_den > 0 else None,
        "weighted_avg_days_on_market": (dom_num / dom_den) if dom_den > 0 else None,
        "weighted_price_over_msrp_percentage": (msrp_pct_num / msrp_pct_den) if msrp_pct_den > 0 else None,
        "weighted_avg_msrp": (msrp_abs_num / msrp_abs_den) if msrp_abs_den > 0 else None,
    }


def _extract_window_aggregates(
    per_make_sold_by_window: dict[str, dict],
    windows: dict[str, Any],
    makes: list[str],
) -> dict[str, dict | None]:
    """For each window (current, prior, baseline_3mo), combine per-make
    per-month aggregates into a single ticker-level aggregate.

    For `current` and `prior`, pick the matching month bucket from each
    make's `months` map.

    For `baseline_3mo`, pick the 3 months within the baseline_3mo_window
    range (NOT current) and combine them.

    Handles null prior_month / baseline_3mo windows gracefully (W2 mode):
    - If a window is None or missing, the corresponding aggregate is None.
    - Defensive: if prior_yymm equals current_yymm (the buggy stub pattern
      from the old W2 spec), treat prior as null. This eliminates the silent
      verdict-dilution bug (W2-C).
    """
    current_month_block = windows.get("current_month")
    prior_month_block = windows.get("prior_month")
    baseline_block = windows.get("baseline_3mo")

    current_yymm = current_month_block["date_from"][:7] if current_month_block else None
    prior_yymm = prior_month_block["date_from"][:7] if prior_month_block else None
    baseline_from = baseline_block["date_from"][:7] if baseline_block else None
    baseline_to = baseline_block["date_to"][:7] if baseline_block else None

    def _per_make_in_month(target_yymm: str) -> list[dict]:
        out = []
        for make in makes:
            make_block = per_make_sold_by_window.get(make, {})
            months = make_block.get("months", {}) if isinstance(make_block, dict) else {}
            if target_yymm in months:
                out.append(months[target_yymm])
        return out

    def _per_make_in_range(from_yymm: str, to_yymm: str) -> list[dict]:
        """All make-months within [from_yymm, to_yymm], combining within each make first."""
        out = []
        for make in makes:
            make_block = per_make_sold_by_window.get(make, {})
            months = make_block.get("months", {}) if isinstance(make_block, dict) else {}
            in_range = [
                agg for ym, agg in months.items()
                if from_yymm <= ym <= to_yymm
            ]
            if in_range:
                combined = _weighted_combine(in_range)
                if combined is not None:
                    out.append(combined)
        return out

    current_combined = _weighted_combine(_per_make_in_month(current_yymm)) if current_yymm else None

    # Defensive: treat "prior same as current" stub pattern as null prior.
    # This catches old-spec orchestration that passes stubbed prior_month and
    # eliminates the silent verdict-dilution bug (W2-C).
    if prior_yymm and prior_yymm != current_yymm:
        prior_combined = _weighted_combine(_per_make_in_month(prior_yymm))
    else:
        prior_combined = None

    baseline_combined = (
        _weighted_combine(_per_make_in_range(baseline_from, baseline_to))
        if baseline_from and baseline_to and baseline_from != current_yymm
        else None
    )

    return {
        "current": current_combined,
        "prior": prior_combined,
        "baseline_3mo": baseline_combined,
    }


def _detect_zero_sold_baseline_months(
    per_make_sold_by_window: dict[str, dict],
    windows: dict[str, Any],
    makes: list[str],
) -> list[str]:
    """DQ event (n): a make missing data for a baseline month means zero sales
    (or absent from response). Flag so the analyst knows the 3-mo baseline
    trend may underestimate."""
    baseline_block = windows.get("baseline_3mo")
    if not baseline_block:
        return []
    baseline_from = baseline_block.get("date_from", "")[:7]
    baseline_to = baseline_block.get("date_to", "")[:7]
    if not (baseline_from and baseline_to):
        return []

    # Build the set of expected YYYY-MM months in [from, to] inclusive (typically 3 months).
    def _months_inclusive(yymm_from: str, yymm_to: str) -> list[str]:
        out: list[str] = []
        y, m = int(yymm_from[:4]), int(yymm_from[5:7])
        ey, em = int(yymm_to[:4]), int(yymm_to[5:7])
        while (y, m) <= (ey, em):
            out.append(f"{y:04d}-{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1
        return out

    expected = _months_inclusive(baseline_from, baseline_to)
    events: list[str] = []
    for make in makes:
        make_block = per_make_sold_by_window.get(make, {})
        months = make_block.get("months", {}) if isinstance(make_block, dict) else {}
        if not months:
            continue  # whole make has no data; handled elsewhere
        missing = [m for m in expected if m not in months]
        for m in missing:
            events.append(
                f"(n) Zero-sold month {m} for make {make} — baseline_3mo trend may underestimate."
            )
    return events


def _build_leading_indicators_raw(
    sold_windows: dict[str, dict | None],
    ev_windows: dict[str, dict | None] | None,
    days_supply_current: float | None,
    days_supply_prior: float | None,
    market_share: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the 7 leading_indicators_raw metrics. No banding."""
    cur = sold_windows.get("current") or {}
    pri = sold_windows.get("prior") or {}
    bsl = sold_windows.get("baseline_3mo") or {}

    cur_sold = _to_int((cur or {}).get("total_sold_count"))
    pri_sold = _to_int((pri or {}).get("total_sold_count"))
    bsl_sold = _to_int((bsl or {}).get("total_sold_count"))
    # Baseline 3-mo trend compares current vs average-per-month over the 3-mo baseline
    bsl_per_month_avg = (bsl_sold / 3.0) if bsl_sold and bsl_sold > 0 else None

    cur_asp = _to_float((cur or {}).get("weighted_avg_sale_price"))
    pri_asp = _to_float((pri or {}).get("weighted_avg_sale_price"))
    bsl_asp = _to_float((bsl or {}).get("weighted_avg_sale_price"))

    cur_msrp_pct = _to_float((cur or {}).get("weighted_price_over_msrp_percentage"))
    pri_msrp_pct = _to_float((pri or {}).get("weighted_price_over_msrp_percentage"))
    bsl_msrp_pct = _to_float((bsl or {}).get("weighted_price_over_msrp_percentage"))
    msrp_delta_bps = (
        (cur_msrp_pct - pri_msrp_pct) * 100.0
        if cur_msrp_pct is not None and pri_msrp_pct is not None
        else None
    )

    cur_dom = _to_float((cur or {}).get("weighted_avg_days_on_market"))
    pri_dom = _to_float((pri or {}).get("weighted_avg_days_on_market"))
    bsl_dom = _to_float((bsl or {}).get("weighted_avg_days_on_market"))

    indicators: dict[str, Any] = {
        "volume": {
            "current": cur_sold,
            "prior": pri_sold,
            "baseline_3mo": bsl_sold,
            "baseline_3mo_avg_per_month": bsl_per_month_avg,
            "mom_pct": _safe_pct_change(cur_sold, pri_sold),
            "trend_3mo_pct": _safe_pct_change(cur_sold, bsl_per_month_avg),
        },
        "asp": {
            "current": cur_asp,
            "prior": pri_asp,
            "baseline_3mo": bsl_asp,                          # NEW (Gap 1)
            "mom_pct": _safe_pct_change(cur_asp, pri_asp),
        },
        "msrp_gap": {
            "current_pct": cur_msrp_pct,
            "prior_pct": pri_msrp_pct,
            "baseline_3mo_pct": bsl_msrp_pct,                 # NEW (Gap 1)
            "delta_bps": msrp_delta_bps,
        },
        "days_supply": {
            "current": days_supply_current,
            "prior": days_supply_prior,
            "mom_pct": _safe_pct_change(days_supply_current, days_supply_prior),
        },
        "market_share": market_share if market_share else {
            "current_pct": None,
            "prior_pct": None,
            "baseline_3mo_pct": None,                         # NEW (Gap 1)
            "delta_bps": None,
        },
        "dom": {
            "current": cur_dom,
            "prior": pri_dom,
            "baseline_3mo": bsl_dom,                          # NEW (Gap 1)
            "delta_days": _safe_delta(cur_dom, pri_dom),
        },
        "ev_transition": None,  # populated below if applicable
    }

    if ev_windows:
        ev_cur = ev_windows.get("current") or {}
        ev_pri = ev_windows.get("prior") or {}
        ev_bsl = ev_windows.get("baseline_3mo") or {}
        ev_cur_sold = _to_int((ev_cur or {}).get("total_sold_count")) or 0
        ev_pri_sold = _to_int((ev_pri or {}).get("total_sold_count")) or 0
        ev_bsl_sold = _to_int((ev_bsl or {}).get("total_sold_count")) or 0
        cur_total = cur_sold or 0
        pri_total = pri_sold or 0
        bsl_total = bsl_sold or 0
        ev_cur_pct = (100.0 * ev_cur_sold / cur_total) if cur_total > 0 else None
        ev_pri_pct = (100.0 * ev_pri_sold / pri_total) if pri_total > 0 else None
        ev_bsl_pct = (100.0 * ev_bsl_sold / bsl_total) if bsl_total > 0 else None    # NEW (Gap 1)
        ev_delta_bps = (
            (ev_cur_pct - ev_pri_pct) * 100.0
            if ev_cur_pct is not None and ev_pri_pct is not None
            else None
        )
        indicators["ev_transition"] = {
            "current_pct": ev_cur_pct,
            "prior_pct": ev_pri_pct,
            "baseline_3mo_pct": ev_bsl_pct,                                          # NEW (Gap 1)
            "delta_bps": ev_delta_bps,
        }

    return indicators


def _compute_market_share(
    market_top25: dict[str, Any],
    target_makes: list[str],
    windows: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Compute the ticker's aggregate market share in the top-25 cohort.

    Returns (market_share_metric, market_context_block, dq_events).
    market_share_metric: {current_pct, prior_pct, delta_bps}
    market_context_block: top_10_makes, ticker_aggregate_share_pct,
                          target_makes_in_top25, target_makes_outside_top25
    dq_events: list of DQ event strings (e.g., (o) legacy-shape warning).
    """
    current_rows = market_top25.get("current") or []

    # Backward compat: accept either `prior` (legacy single-month flat) OR
    # `baseline_3mo_by_window` (new multi-month with per-make months map).
    # baseline_3mo_by_window is the new shape from `--aggregate-by-dimension make --by-window`.
    baseline_data = market_top25.get("baseline_3mo_by_window") or []
    legacy_prior_rows = market_top25.get("prior") or []

    # C-S3 halt: market_top25.current MUST have data for W1 (current month is required).
    # Empty current_rows means the leaderboard MCP call returned nothing — a real data
    # gap, not a recoverable degradation. Surface loudly.
    if not current_rows:
        return (
            {"current_pct": None, "prior_pct": None, "baseline_3mo_pct": None, "delta_bps": None},
            {"top_10_makes": [], "ticker_aggregate_share_pct": None,
             "target_makes_in_top25": [], "target_makes_outside_top25": list(target_makes)},
            ["(u) Empty market_top25.current — leaderboard returned no rows; market-share "
             "verdict cannot be computed for this month."],
        )

    target_set = {m.lower() for m in target_makes}

    # Build prior_rows: extract prior month's data from baseline_3mo_by_window if present,
    # else fall back to legacy `prior` shape.
    prior_rows: list[dict] = []
    prior_yymm = (
        windows.get("prior_month", {}).get("date_from", "")[:7]
        if windows and windows.get("prior_month") else None
    )
    if baseline_data and prior_yymm:
        for entry in baseline_data:
            month_agg = (entry.get("months") or {}).get(prior_yymm)
            if month_agg:
                prior_rows.append({
                    "value": entry.get("value"),
                    "total_sold_count": _to_int(month_agg.get("total_sold_count")),
                    # share_pct is recomputed below from per-month cohort total
                })
        # Compute per-month share_pct for prior_rows
        prior_cohort_total = sum((r.get("total_sold_count") or 0) for r in prior_rows)
        if prior_cohort_total > 0:
            for r in prior_rows:
                r["share_pct"] = round(100.0 * (r.get("total_sold_count") or 0) / prior_cohort_total, 2)
    else:
        prior_rows = legacy_prior_rows

    # Prior share lookup by make (for per-row delta_bps on top_10_makes).
    # C-S4: recompute share_pct from prior_cohort_total to ensure consistency
    # with the script's recomputed share_pct on the current rows.
    prior_cohort_total_for_shares = sum(_to_int(r.get("total_sold_count")) or 0 for r in prior_rows)
    prior_share_by_make: dict[str, float | None] = {
        (r.get("value") or ""): (
            round(100.0 * (_to_int(r.get("total_sold_count")) or 0) / prior_cohort_total_for_shares, 2)
            if prior_cohort_total_for_shares > 0 else None
        )
        for r in prior_rows
        if r.get("value")
    }

    def _build_top_makes(rows: list[dict], include_delta: bool = False) -> tuple[list[dict], int, list[str], int]:
        """Returns (annotated top-10 list, ticker aggregate sold, makes-in-top25, cohort_total)."""
        cohort_total = sum(_to_int(r.get("total_sold_count")) or 0 for r in rows)
        target_in_top25: list[str] = []
        ticker_sold = 0
        top_10: list[dict] = []
        for i, r in enumerate(rows):
            make_name = r.get("value") or ""
            is_target = make_name.lower() in target_set
            if is_target:
                target_in_top25.append(make_name)
                ticker_sold += _to_int(r.get("total_sold_count")) or 0
            if i < 10:
                # C-S4: recompute share_pct from cohort_total (this function's denominator),
                # not from parser's r.get("share_pct"). Ensures top_10_makes share matches
                # market_share.current_pct's denominator within the same script invocation.
                sold_count = _to_int(r.get("total_sold_count")) or 0
                cur_share = round(100.0 * sold_count / cohort_total, 2) if cohort_total > 0 else None
                row: dict[str, Any] = {
                    "rank": i + 1,
                    "make": make_name,
                    "is_target_make": is_target,
                    "sold": sold_count,
                    "share_pct": cur_share,
                }
                if include_delta:
                    prior_share = prior_share_by_make.get(make_name)
                    row["delta_bps"] = (
                        (cur_share - prior_share) * 100.0
                        if cur_share is not None and prior_share is not None
                        else None
                    )
                top_10.append(row)
        return top_10, ticker_sold, target_in_top25, cohort_total

    cur_top10, cur_ticker_sold, cur_target_in, cur_cohort_total = _build_top_makes(current_rows, include_delta=True)
    pri_top10, pri_ticker_sold, _, pri_cohort_total = _build_top_makes(prior_rows)

    cur_share_pct = (100.0 * cur_ticker_sold / cur_cohort_total) if cur_cohort_total > 0 else None
    pri_share_pct = (100.0 * pri_ticker_sold / pri_cohort_total) if pri_cohort_total > 0 else None
    delta_bps = (
        (cur_share_pct - pri_share_pct) * 100.0
        if cur_share_pct is not None and pri_share_pct is not None
        else None
    )

    # baseline_3mo_pct from the across-months totals in baseline_data (Gap 1)
    baseline_3mo_pct: float | None = None
    if baseline_data:
        baseline_cohort_total = sum(
            (_to_int(entry.get("total_sold_count_all_months")) or 0)
            for entry in baseline_data
        )
        baseline_ticker_sold = sum(
            (_to_int(entry.get("total_sold_count_all_months")) or 0)
            for entry in baseline_data
            if (entry.get("value") or "").lower() in target_set
        )
        if baseline_cohort_total > 0:
            baseline_3mo_pct = 100.0 * baseline_ticker_sold / baseline_cohort_total

    # Cross-check: which of the target's makes are NOT in current top-25?
    target_outside_top25 = [
        m for m in target_makes if m not in cur_target_in
    ]

    market_share_metric = {
        "current_pct": cur_share_pct,
        "prior_pct": pri_share_pct,
        "baseline_3mo_pct": baseline_3mo_pct,
        "delta_bps": delta_bps,
    }

    market_context_block = {
        "top_10_makes": cur_top10,
        "ticker_aggregate_share_pct": cur_share_pct,
        "target_makes_in_top25": cur_target_in,
        "target_makes_outside_top25": target_outside_top25,
    }

    # DQ event (o): orchestration passed the legacy `prior` shape instead of the
    # preferred `baseline_3mo_by_window` shape. The script's backward-compat path
    # still works, but the orchestration spec drifted — surface the warning.
    dq_events: list[str] = []
    if not baseline_data and "prior" in market_top25:
        dq_events.append(
            "(o) Legacy `market_top25.prior` shape used — orchestration spec drift; "
            "expected `baseline_3mo_by_window` for W1. Backward-compat path engaged."
        )

    return market_share_metric, market_context_block, dq_events


def _build_active_inventory(
    per_make: dict[str, Any],
    sold_current_per_make: dict[str, dict | None],
    days_in_month: int,
) -> tuple[list[dict[str, Any]], float | None, float | None, int, bool, list[str], list[str]]:
    """Per-make active inventory + ticker-level days_supply.

    days_supply = (sum of all makes' active count) × days_in_month / (sum of all makes' current sold)

    Returns (per_make_active_list, days_supply_current, days_supply_prior_placeholder).
    NOTE: prior Days Supply requires a prior-month active snapshot which we don't have
    (search_active_cars is a live snapshot only). We approximate prior Days Supply as null
    in v1 — the mom_pct on Days Supply will be null, and the banding logic skips it.
    """
    out: list[dict[str, Any]] = []
    total_active = 0
    makes_with: list[str] = []
    makes_without: list[str] = []
    for make, blocks in per_make.items():
        active = blocks.get("active") if isinstance(blocks, dict) else None
        if not isinstance(active, dict):
            makes_without.append(make)
            continue
        makes_with.append(make)
        num_found = _to_int(active.get("num_found")) or 0
        total_active += num_found
        stats = active.get("stats") if isinstance(active.get("stats"), dict) else None
        # C-S10: defend against stats.price / stats.dom being null (parser emits
        # None for non-dict blocks). Use isinstance check before .get().
        price_block = stats.get("price") if stats else None
        dom_block = stats.get("dom") if stats else None
        avg_price = _to_float(price_block.get("mean")) if isinstance(price_block, dict) else None
        avg_dom = _to_float(dom_block.get("mean")) if isinstance(dom_block, dict) else None

        sold_cur = sold_current_per_make.get(make)
        sold_cur_count = _to_int(sold_cur.get("total_sold_count")) if sold_cur else None
        ds_make = None
        if num_found and sold_cur_count and sold_cur_count > 0 and days_in_month > 0:
            ds_make = num_found * days_in_month / sold_cur_count

        out.append({
            "make": make,
            "active_count": num_found,
            "active_avg_price": avg_price,
            "active_dom": avg_dom,
            "days_supply": ds_make,
        })

    # Ticker-level Days Supply: total active / total current sold
    total_sold_cur = sum(
        (_to_int(a.get("total_sold_count")) or 0)
        for a in sold_current_per_make.values()
        if a
    )
    days_supply_current = None
    if total_active and total_sold_cur > 0 and days_in_month > 0:
        days_supply_current = total_active * days_in_month / total_sold_cur

    # Prior days supply is null per the v1 limitation noted above.
    days_supply_prior = None

    active_inventory_complete = len(makes_without) == 0
    return out, days_supply_current, days_supply_prior, total_active, active_inventory_complete, makes_with, makes_without


def _build_ev_block(
    classification: str,
    ev_windows: dict[str, dict | None] | None,
    sold_windows: dict[str, dict | None],
    per_make_ev: dict[str, Any],
    ev_market_leaders: dict[str, Any] | None,
    makes: list[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Build the ev_block. Returns (block, dq_events_appended).

    For pure-play classification:
    - W1 path (ev_market_leaders provided) → render market_leaders substitute leaderboard.
    - W2 path (ev_market_leaders is None)  → synthesize a transition block from
      headline values (ticker_ev_pct = 100.0, EV ASP/DOM/sold = headline values).
      The pure-play OEM's entire volume is EV by definition.
    """
    dq: list[str] = []
    makes = makes or []

    if classification == "pure_play":
        # W1 path: ev_market_leaders substitute
        if ev_market_leaders:
            leaders = ev_market_leaders.get("all_months") or []
            if not leaders:
                # Try to extract from `months` (multi-window response)
                months = ev_market_leaders.get("months", {}) if isinstance(ev_market_leaders, dict) else {}
                if months:
                    latest_month = sorted(months.keys())[-1]
                    leaders = months.get(latest_month) or []
            if not leaders:
                return {"shape": "omitted", "transition": None, "market_leaders": None}, ["(k) EV market leaders returned zero rows; EV block omitted."]
            market_leaders = []
            for i, lead in enumerate(leaders[:10]):
                market_leaders.append({
                    "rank": i + 1,
                    "make": lead.get("value"),
                    "ev_sold": _to_int(lead.get("total_sold_count")),
                    "ev_share_pct": _to_float(lead.get("share_pct")),
                    "ev_asp": _to_float(lead.get("weighted_avg_sale_price")),
                })
            dq.append("(k) EV slice skipped for pure-play; EV market leaders substituted.")
            return {"shape": "market_leaders", "transition": None, "market_leaders": market_leaders}, dq

        # W2 path: synthesize transition block from headline (no ev_market_leaders call)
        sold_cur = sold_windows.get("current") or {}
        sold_pri = sold_windows.get("prior") or {}
        cur_asp = _to_float(sold_cur.get("weighted_avg_sale_price"))
        cur_dom = _to_float(sold_cur.get("weighted_avg_days_on_market"))
        cur_sold = _to_int(sold_cur.get("total_sold_count"))
        pri_asp = _to_float(sold_pri.get("weighted_avg_sale_price"))
        pri_dom = _to_float(sold_pri.get("weighted_avg_days_on_market"))
        pri_sold = _to_int(sold_pri.get("total_sold_count"))

        per_make_breakdown = []
        if makes and cur_sold is not None:
            per_make_breakdown.append({
                "make": makes[0],
                "ev_sold": cur_sold,
                "ev_pct_of_make": 100.0,
                "ev_asp": cur_asp,
            })

        # Pure-play EV % is 100 by definition (current); prior is 100 iff prior had sales.
        ticker_ev_pct_prior = 100.0 if (pri_sold is not None and pri_sold > 0) else None
        ticker_ev_pct_delta_bps = 0.0 if ticker_ev_pct_prior is not None else None

        transition = {
            "ticker_ev_pct":            100.0,
            "ticker_ev_pct_prior":      ticker_ev_pct_prior,
            "ticker_ev_pct_delta_bps":  ticker_ev_pct_delta_bps,
            "ticker_ev_asp":            cur_asp,
            "ticker_ev_dom":            cur_dom,
            "ticker_ev_sold":           cur_sold,
            "ticker_ev_asp_prior":      pri_asp,
            "ticker_ev_dom_prior":      pri_dom,
            "ticker_ev_sold_prior":     pri_sold,
            "ticker_ev_asp_mom_pct":    _safe_pct_change(cur_asp, pri_asp),
            "ticker_ev_dom_delta_days": _safe_delta(cur_dom, pri_dom),
            "ticker_ev_sold_mom_pct":   _safe_pct_change(cur_sold, pri_sold),
            "per_make_breakdown":       per_make_breakdown,
            "narrative_note":           "Pure-play EV maker — entire volume is EV by definition.",
        }
        dq.append("(k) Pure-play EV normalized — transition block synthesized from headline.")
        return {"shape": "transition", "transition": transition, "market_leaders": None}, dq

    # Legacy or brand_orphan path
    if ev_windows is None:
        return {"shape": "omitted", "transition": None, "market_leaders": None}, []

    ev_cur = ev_windows.get("current") or {}
    ev_pri = ev_windows.get("prior") or {}
    ev_cur_sold = _to_int(ev_cur.get("total_sold_count")) or 0

    if ev_cur_sold == 0:
        dq.append("(k) EV slice returned zero across all makes; EV block omitted.")
        return {"shape": "omitted", "transition": None, "market_leaders": None}, dq

    sold_cur = sold_windows.get("current") or {}
    sold_cur_total = _to_int(sold_cur.get("total_sold_count")) or 0

    ticker_ev_pct = (100.0 * ev_cur_sold / sold_cur_total) if sold_cur_total > 0 else None
    ticker_ev_asp = _to_float(ev_cur.get("weighted_avg_sale_price"))
    ticker_ev_dom = _to_float(ev_cur.get("weighted_avg_days_on_market"))

    # Prior-month EV fields (Gap 2)
    ticker_ev_asp_prior = _to_float(ev_pri.get("weighted_avg_sale_price"))
    ticker_ev_dom_prior = _to_float(ev_pri.get("weighted_avg_days_on_market"))
    ticker_ev_sold_prior = _to_int(ev_pri.get("total_sold_count"))

    # DQ event (m) — low prior-month EV volume noise warning (Gap 2)
    if ticker_ev_sold_prior is not None and 0 < ticker_ev_sold_prior < 500:
        dq.append(
            f"(m) Prior-month EV volume {ticker_ev_sold_prior} below 500 — Δ may be noisy."
        )

    # Per-make EV breakdown — fixed: use current_yymm from sold_windows / month_blocks
    # explicitly, not "whatever sorts last" (Gap 2 sub-bug fix).
    per_make_breakdown = []
    # We need current_yymm; pull from sold_windows.current (if non-null) by inspecting any
    # nested per-make sold_by_window block — but the cleanest is to take the max key of
    # per_make_ev's months map per-make, defaulting to None.
    # Resolve current month from the windows block (canonical source); fall back to
    # per-make max if windows is unusable. This avoids the M1 edge case where a
    # make's months dict is empty (would have crashed `max()`).
    current_yymm_canonical: str | None = None
    if isinstance(ev_windows, dict):
        # ev_windows came from _extract_window_aggregates which used windows.current_month
        # internally — but to read the current_yymm we need the original windows dict.
        # Detect via the caller-set sold_windows.current as a proxy: if current exists,
        # then a current month was extracted.
        pass  # windows reference isn't in scope here; fall through to per-make max
    excluded_zero_ev_makes: list[str] = []
    for make, blocks in per_make_ev.items():
        if not isinstance(blocks, dict):
            continue
        months = blocks.get("months", {}) if isinstance(blocks.get("months"), dict) else {}
        if not months:
            # M1: make with empty months dict (zero EV across all months) — skip
            # the per-make row gracefully. Track for DQ (s).
            excluded_zero_ev_makes.append(make)
            continue
        # Pick the latest month present in this make's EV months map. Guarded by
        # the `if not months: continue` above — max() over a non-empty sequence.
        current_month_yymm = max(months.keys())
        agg = months[current_month_yymm]
        ev_sold_make = _to_int(agg.get("total_sold_count")) or 0
        if ev_sold_make == 0:
            excluded_zero_ev_makes.append(make)
            continue
        per_make_breakdown.append({
            "make": make,
            "ev_sold": ev_sold_make,
            "ev_pct_of_make": None,
            "ev_asp": _to_float(agg.get("weighted_avg_sale_price")),
        })
    # DQ (s): informational — zero-EV makes excluded from per-make EV breakdown
    if excluded_zero_ev_makes:
        dq.append(
            f"(s) Excluded from EV per-make breakdown (zero EV in current month): "
            f"{', '.join(excluded_zero_ev_makes)}."
        )

    # Prior EV % and delta in bps — matches leading_indicators_raw.ev_transition math
    sold_pri = sold_windows.get("prior") or {}
    sold_pri_total = _to_int(sold_pri.get("total_sold_count")) or 0
    ev_pri_sold_safe = ticker_ev_sold_prior or 0
    ticker_ev_pct_prior = (
        (100.0 * ev_pri_sold_safe / sold_pri_total) if sold_pri_total > 0 else None
    )
    ticker_ev_pct_delta_bps = (
        (ticker_ev_pct - ticker_ev_pct_prior) * 100.0
        if ticker_ev_pct is not None and ticker_ev_pct_prior is not None
        else None
    )

    transition = {
        "ticker_ev_pct":            ticker_ev_pct,
        "ticker_ev_pct_prior":      ticker_ev_pct_prior,
        "ticker_ev_pct_delta_bps":  ticker_ev_pct_delta_bps,
        "ticker_ev_asp":            ticker_ev_asp,
        "ticker_ev_dom":            ticker_ev_dom,
        "ticker_ev_sold":           ev_cur_sold,
        "ticker_ev_asp_prior":      ticker_ev_asp_prior,
        "ticker_ev_dom_prior":      ticker_ev_dom_prior,
        "ticker_ev_sold_prior":     ticker_ev_sold_prior,
        "ticker_ev_asp_mom_pct":    _safe_pct_change(ticker_ev_asp, ticker_ev_asp_prior),
        "ticker_ev_dom_delta_days": _safe_delta(ticker_ev_dom, ticker_ev_dom_prior),
        "ticker_ev_sold_mom_pct":   _safe_pct_change(ev_cur_sold, ticker_ev_sold_prior),
        "per_make_breakdown":       per_make_breakdown,
        "narrative_note":           _ev_narrative(ticker_ev_pct, ev_windows),
    }
    return {"shape": "transition", "transition": transition, "market_leaders": None}, dq


def _ev_narrative(ev_pct: float | None, ev_windows: dict[str, dict | None] | None) -> str:
    """One-line interpretation of EV transition (heuristic)."""
    if ev_pct is None or ev_windows is None:
        return ""
    pri = ev_windows.get("prior") or {}
    pri_total = _to_int(pri.get("total_sold_count")) or 0
    cur_total = _to_int((ev_windows.get("current") or {}).get("total_sold_count")) or 0
    if pri_total == 0:
        return f"EV mix at {ev_pct:.1f}% of total volume; first month of EV sales recorded."
    delta = cur_total - pri_total
    direction = "rising" if delta > 0 else "falling" if delta < 0 else "flat"
    return f"EV mix at {ev_pct:.1f}% of total volume — units {direction} ({cur_total:,} vs {pri_total:,})."


def _build_per_make_raw(
    classification: str,
    makes: list[str],
    per_make_sold_by_window: dict[str, dict],
    windows: dict[str, Any],
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    """Build per_make_raw for multi-make tickers. Returns (rows, skipped_makes).
    Returns (None, []) when N == 1. Skipped makes are those with empty months dict;
    caller emits DQ (r)."""
    if classification in ("pure_play", "brand_orphan"):
        return None, []
    if len(makes) < 2:
        return None, []

    # Handle null windows (W2 mode): only current_month is guaranteed.
    current_month_block = windows.get("current_month") if windows else None
    prior_month_block = windows.get("prior_month") if windows else None
    baseline_block = windows.get("baseline_3mo") if windows else None
    current_yymm = current_month_block["date_from"][:7] if current_month_block else None
    prior_yymm = prior_month_block["date_from"][:7] if prior_month_block else None
    baseline_from = baseline_block["date_from"][:7] if baseline_block else None
    baseline_to = baseline_block["date_to"][:7] if baseline_block else None

    # Defensive: treat "prior same as current" stub as null prior
    if prior_yymm and prior_yymm == current_yymm:
        prior_yymm = None

    out: list[dict[str, Any]] = []
    skipped: list[str] = []
    for make in makes:
        make_block = per_make_sold_by_window.get(make, {})
        months = make_block.get("months", {}) if isinstance(make_block, dict) else {}

        # Skip makes with no monthly data (DQ (r) emitted by caller)
        if not months:
            skipped.append(make)
            continue

        cur_agg = months.get(current_yymm) or {} if current_yymm else {}
        pri_agg = months.get(prior_yymm) or {} if prior_yymm else {}
        if baseline_from and baseline_to:
            baseline_aggs = [
                agg for ym, agg in months.items()
                if baseline_from <= ym <= baseline_to
            ]
            baseline_combined = _weighted_combine(baseline_aggs)
        else:
            baseline_combined = None

        cur_sold = _to_int(cur_agg.get("total_sold_count"))
        pri_sold = _to_int(pri_agg.get("total_sold_count"))
        baseline_sold = _to_int((baseline_combined or {}).get("total_sold_count"))
        baseline_per_month = (baseline_sold / 3.0) if baseline_sold and baseline_sold > 0 else None

        out.append({
            "make": make,
            "sold_count_current": cur_sold,
            "sold_count_prior": pri_sold,
            "sold_count_baseline_3mo": baseline_sold,
            "weighted_avg_sale_price_current": _to_float(cur_agg.get("weighted_avg_sale_price")),
            "weighted_avg_days_on_market_current": _to_float(cur_agg.get("weighted_avg_days_on_market")),
            "mom_vol_pct": _safe_pct_change(cur_sold, pri_sold),
            "trend_3mo_pct": _safe_pct_change(cur_sold, baseline_per_month),
            "volume_band": (
                band_volume_mom(float(_safe_pct_change(cur_sold, pri_sold)))
                if _safe_pct_change(cur_sold, pri_sold) is not None else None
            ),
        })
    return out, skipped


def _build_segment_mix(per_make: dict[str, Any]) -> tuple[list[dict[str, Any]], bool, list[str], list[str]]:
    """Combine per-make segment_mix into ticker-level top body types.

    Each per-make has segment_mix = [{value, total_sold_count, weighted_avg_sale_price,
    weighted_avg_days_on_market, share_pct}, ...]. We sum per body_type across makes
    and re-rank.

    Returns (top5_segment_mix, segment_mix_complete, makes_with_segment_mix,
             makes_without_segment_mix).
    Loud about partial coverage: any make with null segment_mix is recorded in
    makes_without_segment_mix; segment_mix_complete=False. Caller emits DQ (p).
    """
    by_type: dict[str, list[dict[str, Any]]] = {}
    makes_with: list[str] = []
    makes_without: list[str] = []
    for make, blocks in per_make.items():
        seg = blocks.get("segment_mix") if isinstance(blocks, dict) else None
        if not isinstance(seg, list):
            makes_without.append(make)
            continue
        makes_with.append(make)
        for entry in seg:
            if not isinstance(entry, dict):
                continue
            bt = entry.get("value")
            if not bt:
                continue
            by_type.setdefault(bt, []).append(entry)

    out: list[dict[str, Any]] = []
    for bt, entries in by_type.items():
        combined = _weighted_combine(entries)
        if combined is None:
            continue
        out.append({
            "body_type": bt,
            "sold": combined["total_sold_count"],
            "asp": combined.get("weighted_avg_sale_price"),
            "dom": combined.get("weighted_avg_days_on_market"),
        })

    total = sum(b["sold"] or 0 for b in out)
    for entry in out:
        entry["share_pct"] = (100.0 * entry["sold"] / total) if total > 0 and entry["sold"] else None

    out.sort(key=lambda r: r["sold"] or 0, reverse=True)
    segment_mix_complete = len(makes_without) == 0
    return out[:5], segment_mix_complete, makes_with, makes_without  # Top 5


def _build_headline(sold_windows: dict[str, dict | None]) -> dict[str, Any]:
    """Build the headline block (current-month combined)."""
    cur = sold_windows.get("current") or {}
    sold_count = _to_int(cur.get("total_sold_count"))
    asp = _to_float(cur.get("weighted_avg_sale_price"))
    dom = _to_float(cur.get("weighted_avg_days_on_market"))
    eff = (sold_count / dom) if sold_count and dom and dom > 0 else None
    return {
        "sold_count_total": sold_count,
        "weighted_avg_sale_price": asp,
        "weighted_avg_days_on_market": dom,
        "efficiency_score": eff,
    }


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

def _validate_input(cfg: dict) -> tuple[bool, str | None, str | None]:
    """Loud failure gate: catch missing required keys at the boundary instead of
    silently degrading via .get() → None. Returns (ok, error_type, field)."""
    if not isinstance(cfg, dict):
        return False, "bad_stdin", "<root>"

    windows = cfg.get("windows")
    if not isinstance(windows, dict):
        return False, "missing_required_field", "windows"
    if not isinstance(windows.get("current_month"), dict):
        return False, "missing_required_field", "windows.current_month"
    cm = windows["current_month"]
    if not cm.get("date_from") or not cm.get("date_to"):
        return False, "missing_required_field", "windows.current_month.date_from|date_to"

    classification = cfg.get("classification") or "legacy"
    per_make = cfg.get("per_make")
    if classification in ("legacy", "brand_orphan"):
        if not isinstance(per_make, dict) or len(per_make) == 0:
            return False, "missing_required_field", "per_make"
        # C-S8: deep validation — each make value must be a dict with sold_by_window
        for make, blocks in per_make.items():
            if not isinstance(blocks, dict):
                return False, "malformed_per_make_value", f"per_make.{make} (expected dict, got {type(blocks).__name__})"
            if "sold_by_window" not in blocks:
                return False, "missing_required_field", f"per_make.{make}.sold_by_window"
            # active/segment_mix/ev_slice_by_window may be null (handled by builders);
            # but if present, must be a dict (active, ev_slice_by_window) or list (segment_mix).
            sbw = blocks.get("sold_by_window")
            if sbw is not None and not isinstance(sbw, dict):
                return False, "malformed_per_make_field", f"per_make.{make}.sold_by_window (expected dict|null)"
            act = blocks.get("active")
            if act is not None and not isinstance(act, dict):
                return False, "malformed_per_make_field", f"per_make.{make}.active (expected dict|null)"
            seg = blocks.get("segment_mix")
            if seg is not None and not isinstance(seg, list):
                return False, "malformed_per_make_field", f"per_make.{make}.segment_mix (expected list|null)"
            evs = blocks.get("ev_slice_by_window")
            if evs is not None and not isinstance(evs, dict):
                return False, "malformed_per_make_field", f"per_make.{make}.ev_slice_by_window (expected dict|null)"

    market_top25 = cfg.get("market_top25")
    if not isinstance(market_top25, dict):
        return False, "missing_required_field", "market_top25"
    # At least one shape key must be PRESENT (empty array is valid — means cohort had no rows).
    if not any(k in market_top25 for k in ("current", "baseline_3mo_by_window", "prior")):
        return False, "missing_required_field", "market_top25.current|baseline_3mo_by_window|prior"

    return True, None, None


_INPUT_SHAPE_EXAMPLE = {
    "ticker": "F",
    "company_name": "Ford Motor Company",
    "classification": "legacy",
    "makes": ["Ford", "Lincoln"],
    "inventory_type": "New",
    "windows": {
        "current_month": {"date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD",
                          "label": "<Month YYYY>", "days_in_month": 30},
        "prior_month":   {"date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD",
                          "label": "<Month YYYY>", "days_in_month": 31},
        "baseline_3mo":  {"date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD",
                          "label": "<MonthA YYYY - MonthC YYYY>", "months_count": 3},
    },
    "per_make": {
        "<Make>": {
            "sold_by_window": {"months": {"YYYY-MM": {"total_sold_count": 0, "weighted_avg_sale_price": 0.0, "weighted_avg_days_on_market": 0.0}}},
            "active": {"num_found": 0, "stats": {"price": {"mean": 0.0}, "dom": {"mean": 0.0}}},
            "segment_mix": [{"value": "<body_type>", "total_sold_count": 0, "weighted_avg_sale_price": 0.0, "weighted_avg_days_on_market": 0.0, "share_pct": 0.0}],
            "ev_slice_by_window": {"months": {"YYYY-MM": {"total_sold_count": 0}}},
        }
    },
    "market_top25": {
        "current": [{"value": "<Make>", "total_sold_count": 0, "weighted_avg_sale_price": 0.0, "weighted_avg_days_on_market": 0.0, "share_pct": 0.0}],
        "baseline_3mo_by_window": [{"value": "<Make>", "total_sold_count_all_months": 0, "months": {"YYYY-MM": {"total_sold_count": 0}}}],
    },
    "ev_market_leaders": None,
    "_required_fields": ["windows.current_month", "per_make (for legacy/brand_orphan)", "market_top25 (current OR baseline_3mo_by_window OR prior)"],
    "_optional_fields": ["windows.prior_month", "windows.baseline_3mo", "ev_market_leaders", "ticker", "company_name"],
    "_dq_events_emitted": ["d", "g", "h", "i", "k", "m", "n", "o"],
}


def main(argv: list[str]) -> int:
    if "--print-input-shape" in argv:
        emit({"ok": True, "shape": _INPUT_SHAPE_EXAMPLE})
        return 0

    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        emit({"ok": False, "error_type": "bad_stdin", "error": str(exc)})
        return 0

    ok, error_type, field = _validate_input(cfg)
    if not ok:
        emit({
            "ok": False,
            "error_type": error_type,
            "field": field,
            "error": f"compute_oem_stats input missing required field: {field}. "
                     f"See references/script-contracts.md §compute_oem_stats input schema.",
        })
        return 0

    ticker = cfg.get("ticker")
    company_name = cfg.get("company_name", "")
    classification = cfg.get("classification") or "legacy"
    makes = cfg.get("makes") or []
    inventory_type = cfg.get("inventory_type") or "New"
    windows = cfg.get("windows") or {}
    per_make = cfg.get("per_make") or {}
    market_top25 = cfg.get("market_top25") or {}
    ev_market_leaders = cfg.get("ev_market_leaders")

    days_in_month = _to_int(windows.get("current_month", {}).get("days_in_month")) or 30

    dq_events: list[str] = []

    # Extract per-make sold-by-window structures
    per_make_sold_by_window: dict[str, dict] = {}
    per_make_ev_by_window: dict[str, dict] = {}
    for make, blocks in per_make.items():
        if not isinstance(blocks, dict):
            continue
        sold_block = blocks.get("sold_by_window")
        if isinstance(sold_block, dict):
            per_make_sold_by_window[make] = sold_block
        ev_block = blocks.get("ev_slice_by_window")
        if isinstance(ev_block, dict):
            per_make_ev_by_window[make] = ev_block

    # Compute ticker-level sold windows
    sold_windows = _extract_window_aggregates(per_make_sold_by_window, windows, makes)

    # DQ event (n): detect zero-sold baseline months per make
    dq_events.extend(_detect_zero_sold_baseline_months(per_make_sold_by_window, windows, makes))

    # Compute ticker-level EV windows (legacy + brand_orphan only)
    ev_windows: dict[str, dict | None] | None = None
    if classification != "pure_play" and per_make_ev_by_window:
        ev_windows = _extract_window_aggregates(per_make_ev_by_window, windows, makes)

    # Per-make current-month sold (for active inventory days_supply ratio)
    sold_current_per_make: dict[str, dict | None] = {}
    current_yymm = windows.get("current_month", {}).get("date_from", "")[:7]
    for make in makes:
        make_block = per_make_sold_by_window.get(make, {})
        months = make_block.get("months", {}) if isinstance(make_block, dict) else {}
        sold_current_per_make[make] = months.get(current_yymm)

    # Market share + market context
    market_share_metric, market_context_block, market_dq = _compute_market_share(market_top25, makes, windows)
    dq_events.extend(market_dq)

    # Active inventory + Days Supply (+ total_active_count for Gap W2-D)
    (active_inventory, days_supply_current, days_supply_prior, total_active_count,
     active_inventory_complete, makes_with_active, makes_without_active) = _build_active_inventory(
        per_make, sold_current_per_make, days_in_month
    )
    # DQ (q): partial active inventory — any make's active block was null
    if makes_without_active:
        dq_events.append(
            f"(q) Partial active inventory — {', '.join(makes_without_active)} excluded "
            f"(active block missing or non-dict). Days Supply rollup may be incomplete."
        )

    # Leading indicators (raw)
    leading_indicators_raw = _build_leading_indicators_raw(
        sold_windows,
        ev_windows,
        days_supply_current,
        days_supply_prior,
        market_share_metric,
    )

    # EV block
    ev_block, ev_dq = _build_ev_block(
        classification, ev_windows, sold_windows, per_make_ev_by_window, ev_market_leaders,
        makes=makes,
    )
    dq_events.extend(ev_dq)

    # Per-make breakdown (multi-make tickers only)
    per_make_raw, per_make_skipped = _build_per_make_raw(classification, makes, per_make_sold_by_window, windows)
    # DQ (r): makes excluded from per-make breakdown due to empty months
    if per_make_skipped:
        dq_events.append(
            f"(r) Per-make breakdown excluded {', '.join(per_make_skipped)} — "
            f"empty months dict (no sold data in any captured window)."
        )

    # Segment mix
    segment_mix, segment_mix_complete, makes_with_segment_mix, makes_without_segment_mix = _build_segment_mix(per_make)
    # DQ (p): partial segment-mix — any make's segment_mix block was null
    if makes_without_segment_mix:
        dq_events.append(
            f"(p) Partial segment-mix — {', '.join(makes_without_segment_mix)} excluded "
            f"(segment_mix is null). Body-type rollup reflects only {', '.join(makes_with_segment_mix)}."
        )

    # Low-volume DQ event
    for entry in per_make_raw or []:
        sold = entry.get("sold_count_current") or 0
        if 0 < sold < LOW_VOLUME_FLOOR_NATIONAL:
            dq_events.append(
                f"(i) Low-volume make flagged: {entry['make']} = {sold} units in current month "
                f"(below {LOW_VOLUME_FLOOR_NATIONAL}/month national floor)."
            )

    # Headline
    headline = _build_headline(sold_windows)

    # Determine if peer ticker is in top-25 leaderboard for DQ event (g)
    if not market_context_block["target_makes_in_top25"]:
        dq_events.append(
            f"(g) Target ticker's makes ({', '.join(makes)}) absent from current-month "
            f"market-share top-25 leaderboard."
        )

    out = {
        "ok": True,
        "ticker": ticker,
        "company_name": company_name,
        "classification": classification,
        "inventory_type": inventory_type,
        "windows": windows,
        "headline": headline,
        "leading_indicators_raw": leading_indicators_raw,
        "per_make_raw": per_make_raw,
        "active_inventory": active_inventory,
        "active_inventory_complete": active_inventory_complete,
        "makes_with_active": makes_with_active,
        "total_active_count": total_active_count,
        "market_context": market_context_block,
        "ev_block": ev_block,
        "segment_mix": segment_mix,
        "segment_mix_complete": segment_mix_complete,
        "makes_with_segment_mix": makes_with_segment_mix,
        "dq_events": dq_events,
    }

    # Math consistency assertions (Phase 2 / DQ t)
    if per_make_raw:
        sum_per_make = sum(_to_int(p.get("sold_count_current")) or 0 for p in per_make_raw)
        head_total = _to_int(headline.get("sold_count_total")) or 0
        if head_total > 0 and abs(sum_per_make - head_total) / head_total > 0.001:
            dq_events.append(
                f"(t) Math consistency: sum(per_make_raw[*].sold_count_current)={sum_per_make:,} "
                f"differs from headline.sold_count_total={head_total:,} by "
                f"{100*abs(sum_per_make - head_total)/head_total:.2f}% (>0.1% threshold). "
                f"Per-make data may be incomplete."
            )
    if segment_mix:
        sum_seg = sum(_to_int(s.get("sold")) or 0 for s in segment_mix)
        head_total = _to_int(headline.get("sold_count_total")) or 0
        # top_n=5 cushion: up to 5% loss is normal; >5% means partial-make case
        if head_total > 0 and abs(sum_seg - head_total) / head_total > 0.05:
            dq_events.append(
                f"(t) Math consistency: sum(segment_mix[*].sold)={sum_seg:,} "
                f"differs from headline.sold_count_total={head_total:,} by "
                f"{100*abs(sum_seg - head_total)/head_total:.2f}% (>5% threshold). "
                f"Segment-mix likely missing a make."
            )
    if active_inventory:
        sum_active = sum(_to_int(a.get("active_count")) or 0 for a in active_inventory)
        tot_active = _to_int(total_active_count) or 0
        if tot_active > 0 and abs(sum_active - tot_active) / tot_active > 0.001:
            dq_events.append(
                f"(t) Math consistency: sum(active_inventory[*].active_count)={sum_active:,} "
                f"differs from total_active_count={tot_active:,} by "
                f"{100*abs(sum_active - tot_active)/tot_active:.2f}% (>0.1% threshold)."
            )

    emit(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
