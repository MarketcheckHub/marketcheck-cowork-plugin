#!/usr/bin/env python3
"""
compute_earnings_signals.py — Multi-quarter stats engine.

Consumes the assembled JSON document built by the model from Wave A1 + Wave A2
parser outputs, emits raw numeric values only (no bands — banding lives in
`aggregate_signals.py` per the single-source-of-truth discipline).

The assembled JSON shape:

  {
    "ticker": "F" | "AN" | ...,
    "company_name": "Ford Motor Company" | null,       # OEM
    "canonical":    "AutoNation Inc." | null,          # dealer_group
    "entity_type":  "oem" | "dealer_group",
    "classification": "legacy" | "pure_play" |
                      "Used-only" | "New-only" | "Both",
    "makes": ["Ford", "Lincoln"] | [],                  # OEM only
    "windows": <compute_quarter_windows output verbatim>,
    "per_make": {                                        # OEM only
      "<Make>": {
        "sold_new_by_window":  <parser-output.make_by_window> | null,   # the INNER block: {make, row_count, months}
        "sold_used_by_window": <same> | null,
        "ev_slice_by_window":  <same> | null,            # null for pure_play
        "active_new":          <parse_search stats output> | null,
        "active_used":         <same> | null
      }
    } | null,
    "per_group": {                                       # dealer_group only
      "sold_new_by_window":  <parser-output.group_by_window> | null,    # the INNER block: {group, row_count, months}
      "sold_used_by_window": <same> | null,             # null for New-only
      "ev_slice_by_window":  <same> | null,
      "active_new":          <parse_search stats output> | null,
      "active_used":         <same> | null
    } | null

  IMPORTANT: the orchestrator must UNWRAP the parse_sold_summary output before
  assembly. parse_sold_summary --aggregate-make-by-window emits
  `{ok: true, row_count: N, rows: [...], make_by_window: {make, row_count, months}}`.
  The orchestrator passes only the inner `make_by_window` value as
  `sold_new_by_window`, not the full envelope. Same for --aggregate-group-by-window
  (extract `group_by_window`).
  }

Each `*_by_window` block carries `months: {"YYYY-MM": <agg>, ...}` where each
aggregate has fields per `references/script-contracts.md §parse_sold_summary`:
`total_sold_count`, `weighted_avg_sale_price`, `weighted_avg_days_on_market`,
`weighted_median_days_on_market`, `weighted_avg_msrp`,
`weighted_price_over_msrp_percentage`, `row_count`, `months_included`.

Output emits raw numeric values only — never bands. `aggregate_signals.py`
applies the per-metric banding tables from `references/signal-aggregation.md`.

Edge-case discipline (all returned as `null`, never NaN or fabricated):
  - QoQ % / YoY % when prior or year-ago denominator is 0 or null
  - bps Δ when either side is null
  - day delta when either side is null
  - Days Supply when mrcm sold_count is 0 or null
  - EV share when total_sold is 0
  - Mix new% when (new + used) is 0

Days Supply asymmetry — preserved from dealer-group convention:
  - num_found is LIVE (today's snapshot)
  - sold_count is from `most_recent_complete_month` (which may be after the
    end of `current_quarter` — see `references/sold-summary-safety.md
    §Row-count budget`)
  - `active_inventory.footnote` makes this explicit on every render

Private helpers (closes Phase 6 C6 — internal duplication concern):
  - `_combine_monthly_aggs(aggs)` — pool multiple monthly aggregates via
    sold-count-weighted means (matches the disciplined math from
    `parse_sold_summary.py`)
  - `_combine_channels(used, new)` — pool New + Used quarter aggregates
  - `_assign_to_quarter(by_window, windows)` — split monthly aggregates
    into (current_q, prior_q, year_ago_q) lists by month-name lookup
  - `_extract_mrcm_sold(by_window, mrcm_label)` — pull the mrcm month's
    aggregate for Days Supply
  - `_compute_*_block(...)` — per-dimension number-builders

Usage:
  echo '<assembled-input>' | python compute_earnings_signals.py

Exit codes:
  0  success or payload-level failure (parse the JSON `ok` field)
  0  always — bad-stdin emits {ok: false, error_type: "bad_stdin"} per the
     SP6 stdin-parser convention
"""

from __future__ import annotations

import json
import sys
from typing import Any


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


# ─── Delta helpers (null-safe) ─────────────────────────────────────────────


def _safe_pct_change(current: Any, prior: Any) -> float | None:
    """(current - prior) / prior × 100. None if prior is None/0 or current is None."""
    c = _to_float(current)
    p = _to_float(prior)
    if c is None or p is None or p == 0:
        return None
    return (c - p) / p * 100.0


def _safe_delta(current: Any, prior: Any) -> float | None:
    """current - prior. None if either side is null."""
    c = _to_float(current)
    p = _to_float(prior)
    if c is None or p is None:
        return None
    return c - p


def _safe_bps_delta(current_pct: Any, prior_pct: Any) -> float | None:
    """Difference in percentage points × 100 = bps. None if either is null."""
    delta = _safe_delta(current_pct, prior_pct)
    if delta is None:
        return None
    return delta * 100.0


# ─── Core aggregation — combine monthly aggregates into a quarter aggregate ──


def _combine_monthly_aggs(aggs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pool a list of monthly aggregates into one aggregate via sold-count-weighted
    means. Matches the disciplined null-handling discipline from
    `parse_sold_summary._aggregate_within_rows` — a null-valued metric drops
    from BOTH numerator and denominator of the weighted mean.

    Returns None when total_sold across input aggregates is 0.
    """
    if not aggs:
        return None

    total_sold = 0
    sum_price, n_price = 0.0, 0
    sum_dom, n_dom = 0.0, 0
    sum_median_dom, n_median_dom = 0.0, 0
    sum_msrp, n_msrp = 0.0, 0
    sum_msrp_gap, n_msrp_gap = 0.0, 0
    months: list[str] = []

    for agg in aggs:
        sc = _to_int(agg.get("total_sold_count"))
        if sc is None or sc <= 0:
            continue
        total_sold += sc

        price = _to_float(agg.get("weighted_avg_sale_price"))
        if price is not None:
            sum_price += price * sc
            n_price += sc

        dom = _to_float(agg.get("weighted_avg_days_on_market"))
        if dom is not None:
            sum_dom += dom * sc
            n_dom += sc

        median_dom = _to_float(agg.get("weighted_median_days_on_market"))
        if median_dom is not None:
            sum_median_dom += median_dom * sc
            n_median_dom += sc

        msrp = _to_float(agg.get("weighted_avg_msrp"))
        if msrp is not None:
            sum_msrp += msrp * sc
            n_msrp += sc

        msrp_gap = _to_float(agg.get("weighted_price_over_msrp_percentage"))
        if msrp_gap is not None:
            sum_msrp_gap += msrp_gap * sc
            n_msrp_gap += sc

        for m in agg.get("months_included") or []:
            if m not in months:
                months.append(m)

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
        "months_included": sorted(months),
    }


def _combine_channels(
    used: dict[str, Any] | None, new: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Combine New + Used quarter aggregates into a single combined aggregate.

    Same disciplined null-handling discipline as `_combine_monthly_aggs` —
    null-valued metric drops from both num and denom; sold_count is the
    universal weight.
    """
    channels = [c for c in (used, new) if c is not None]
    return _combine_monthly_aggs(channels)


# ─── Quarter assignment ────────────────────────────────────────────────────


def _assign_to_quarter(
    by_window: dict[str, Any] | None, windows: dict[str, Any]
) -> tuple[dict | None, dict | None, dict | None]:
    """Split monthly aggregates from a `make_by_window` / `group_by_window`
    block into (current_quarter, prior_quarter, year_ago_quarter) aggregates.

    The windows file's per-quarter `months` list determines membership.
    Months that fall outside any of the three target quarters (e.g., the
    6-month gap between year_ago and prior, or the mrcm month if it extends
    past current_q) are silently dropped from quarter rollups — but the mrcm
    month is still accessible via `_extract_mrcm_sold` for Days Supply.

    Returns (current_q_agg, prior_q_agg, year_ago_q_agg) where each is the
    pooled aggregate of all months that fall in that quarter, or None.
    """
    if not by_window or not isinstance(by_window.get("months"), dict):
        return None, None, None

    months_by_month = by_window["months"]
    cur_month_set = set(windows.get("current_quarter", {}).get("months") or [])
    prior_month_set = set(windows.get("prior_quarter", {}).get("months") or [])
    year_ago_month_set = set(windows.get("year_ago_quarter", {}).get("months") or [])

    cur_aggs = [months_by_month[m] for m in months_by_month if m in cur_month_set]
    prior_aggs = [months_by_month[m] for m in months_by_month if m in prior_month_set]
    year_ago_aggs = [
        months_by_month[m] for m in months_by_month if m in year_ago_month_set
    ]

    return (
        _combine_monthly_aggs(cur_aggs),
        _combine_monthly_aggs(prior_aggs),
        _combine_monthly_aggs(year_ago_aggs),
    )


def _extract_mrcm_sold(
    by_window: dict[str, Any] | None, mrcm_month_label: str | None
) -> int | None:
    """Extract the `total_sold_count` for the most-recent-complete-month from
    a by_window block. Returns None if the mrcm month is missing or has zero
    sold_count.

    `mrcm_month_label` is the "YYYY-MM" string from
    `windows.most_recent_complete_month.date_from[:7]`. The mrcm month may or
    may not appear in the by_window response (depending on date-range
    extension); a missing mrcm row returns None and Days Supply degrades to
    null with DQ event (n) per `_failure-recovery.md`.
    """
    if not by_window or not mrcm_month_label:
        return None
    months = by_window.get("months") or {}
    agg = months.get(mrcm_month_label)
    if not agg:
        return None
    return _to_int(agg.get("total_sold_count"))


# ─── Leading-indicator block builders ──────────────────────────────────────


def _compute_volume_block(
    current: dict | None, prior: dict | None, year_ago: dict | None
) -> dict[str, Any]:
    """Volume momentum: total_sold_count across each quarter window + QoQ + YoY."""
    c = _to_int(current.get("total_sold_count")) if current else None
    p = _to_int(prior.get("total_sold_count")) if prior else None
    y = _to_int(year_ago.get("total_sold_count")) if year_ago else None
    return {
        "current": c,
        "prior": p,
        "year_ago": y,
        "qoq_pct": _safe_pct_change(c, p),
        "yoy_pct": _safe_pct_change(c, y),
    }


def _compute_asp_block(
    current: dict | None, prior: dict | None, year_ago: dict | None
) -> dict[str, Any]:
    """Pricing — weighted average sale price across each quarter + QoQ + YoY %."""
    c = _to_float(current.get("weighted_avg_sale_price")) if current else None
    p = _to_float(prior.get("weighted_avg_sale_price")) if prior else None
    y = _to_float(year_ago.get("weighted_avg_sale_price")) if year_ago else None
    return {
        "current": c,
        "prior": p,
        "year_ago": y,
        "qoq_pct": _safe_pct_change(c, p),
        "yoy_pct": _safe_pct_change(c, y),
    }


def _compute_msrp_gap_block(
    current: dict | None, prior: dict | None, year_ago: dict | None
) -> dict[str, Any]:
    """MSRP-gap (price_over_msrp_percentage): per-quarter weighted % + QoQ / YoY
    delta expressed as bps (percentage-point Δ × 100)."""
    c = _to_float(current.get("weighted_price_over_msrp_percentage")) if current else None
    p = _to_float(prior.get("weighted_price_over_msrp_percentage")) if prior else None
    y = _to_float(year_ago.get("weighted_price_over_msrp_percentage")) if year_ago else None
    return {
        "current_pct": c,
        "prior_pct": p,
        "year_ago_pct": y,
        "qoq_delta_bps": _safe_bps_delta(c, p),
        "yoy_delta_bps": _safe_bps_delta(c, y),
    }


def _compute_dom_block(
    current: dict | None, prior: dict | None, year_ago: dict | None
) -> dict[str, Any]:
    """DOM Velocity: weighted mean + median days_on_market + QoQ / YoY deltas.

    Mean is right-skewed by long-tail sitting inventory; median is more
    representative of "typical car sold" velocity. Both surfaced for analyst
    interpretation. Median is display-only (not banded).
    """
    c = _to_float(current.get("weighted_avg_days_on_market")) if current else None
    p = _to_float(prior.get("weighted_avg_days_on_market")) if prior else None
    y = _to_float(year_ago.get("weighted_avg_days_on_market")) if year_ago else None
    mc = _to_float(current.get("weighted_median_days_on_market")) if current else None
    mp = _to_float(prior.get("weighted_median_days_on_market")) if prior else None
    my = _to_float(year_ago.get("weighted_median_days_on_market")) if year_ago else None
    return {
        "current": c,
        "prior": p,
        "year_ago": y,
        "qoq_delta_days": _safe_delta(c, p),
        "yoy_delta_days": _safe_delta(c, y),
        "median_current": mc,
        "median_prior": mp,
        "median_year_ago": my,
        "qoq_delta_median_days": _safe_delta(mc, mp),
        "yoy_delta_median_days": _safe_delta(mc, my),
    }


def _compute_days_supply(
    num_found: int | None, mrcm_sold: int | None, days_in_month: int
) -> float | None:
    """num_found × days_in_month / sold_count_mrcm. None if either input is null
    or sold_count_mrcm is 0 (divide-by-zero guard)."""
    if num_found is None or mrcm_sold is None or mrcm_sold <= 0 or days_in_month <= 0:
        return None
    return num_found * days_in_month / mrcm_sold


# ─── EV block builder ──────────────────────────────────────────────────────


def _build_ev_block(
    sold_combined_by_quarter: dict[str, dict | None],
    ev_combined_by_quarter: dict[str, dict | None],
    classification: str,
    dq_events: list[str],
) -> dict[str, Any]:
    """EV transition block. For pure_play OEMs: skipped (volume IS EV).
    For others: compute EV share = ev_sold / total_sold × 100 per quarter.

    Inputs:
      sold_combined_by_quarter: {"current": <agg>|None, "prior": ..., "year_ago": ...}
                                 from the combined-channel rollup.
      ev_combined_by_quarter:   {"current": <agg>|None, "prior": ..., "year_ago": ...}
                                 from the EV-slice rollup (on whichever channel
                                 the classification dictates).

    For pure_play classifications, ev_combined_by_quarter is expected to be
    all-None and the block renders as shape="skipped".
    """
    if classification == "pure_play":
        dq_events.append("(k) EV slice skipped for pure-play OEM — total volume is electrified.")
        return {
            "shape": "skipped",
            "transition": None,
            "skipped_reason": "pure_play_volume_is_ev",
        }

    cur_sold = sold_combined_by_quarter.get("current")
    cur_ev = ev_combined_by_quarter.get("current")
    if not cur_sold or not cur_ev:
        # No data available for the current quarter on either side
        dq_events.append("(k) EV slice returned zero or absent for current quarter; EV block omitted.")
        return {
            "shape": "skipped",
            "transition": None,
            "skipped_reason": "no_ev_volume",
        }

    def _ev_pct(ev_agg, sold_agg):
        if not ev_agg or not sold_agg:
            return None
        ev_sold = _to_int(ev_agg.get("total_sold_count")) or 0
        total_sold = _to_int(sold_agg.get("total_sold_count")) or 0
        if total_sold <= 0:
            return None
        return ev_sold / total_sold * 100.0

    cur_pct = _ev_pct(cur_ev, cur_sold)
    prior_pct = _ev_pct(
        ev_combined_by_quarter.get("prior"), sold_combined_by_quarter.get("prior")
    )
    year_ago_pct = _ev_pct(
        ev_combined_by_quarter.get("year_ago"), sold_combined_by_quarter.get("year_ago")
    )

    # Low-volume guard — if current EV volume nationally < 100, log DQ (i)
    cur_ev_sold = _to_int(cur_ev.get("total_sold_count")) or 0
    if cur_ev_sold < 100:
        dq_events.append(
            f"(i) Low-volume EV slice — current-quarter EV sold = {cur_ev_sold} (<100); EV signal noisier than usual."
        )

    # Multi-period EV ASP / DOM / units trajectory (current already in scope;
    # add prior + year-ago from the EV-slice combined-by-quarter aggregates).
    prior_ev = ev_combined_by_quarter.get("prior")
    year_ago_ev = ev_combined_by_quarter.get("year_ago")
    ev_asp_current = _to_float(cur_ev.get("weighted_avg_sale_price"))
    ev_dom_current = _to_float(cur_ev.get("weighted_avg_days_on_market"))
    ev_asp_prior = _to_float(prior_ev.get("weighted_avg_sale_price")) if prior_ev else None
    ev_asp_year_ago = _to_float(year_ago_ev.get("weighted_avg_sale_price")) if year_ago_ev else None
    ev_dom_prior = _to_float(prior_ev.get("weighted_avg_days_on_market")) if prior_ev else None
    ev_dom_year_ago = _to_float(year_ago_ev.get("weighted_avg_days_on_market")) if year_ago_ev else None
    ev_sold_prior = _to_int(prior_ev.get("total_sold_count")) if prior_ev else None
    ev_sold_year_ago = _to_int(year_ago_ev.get("total_sold_count")) if year_ago_ev else None

    return {
        "shape": "transition",
        "transition": {
            "ev_pct_current": cur_pct,
            "ev_pct_prior": prior_pct,
            "ev_pct_year_ago": year_ago_pct,
            "qoq_delta_bps": _safe_bps_delta(cur_pct, prior_pct),
            "yoy_delta_bps": _safe_bps_delta(cur_pct, year_ago_pct),
            "ev_asp_current": ev_asp_current,
            "ev_dom_current": ev_dom_current,
            "ev_sold_current": cur_ev_sold,
            "ev_asp_prior": ev_asp_prior,
            "ev_asp_year_ago": ev_asp_year_ago,
            "ev_dom_prior": ev_dom_prior,
            "ev_dom_year_ago": ev_dom_year_ago,
            "ev_sold_prior": ev_sold_prior,
            "ev_sold_year_ago": ev_sold_year_ago,
            "qoq_asp_delta_pct": _safe_pct_change(ev_asp_current, ev_asp_prior),
            "yoy_asp_delta_pct": _safe_pct_change(ev_asp_current, ev_asp_year_ago),
            "qoq_dom_delta_days": _safe_delta(ev_dom_current, ev_dom_prior),
            "yoy_dom_delta_days": _safe_delta(ev_dom_current, ev_dom_year_ago),
            "qoq_sold_delta_pct": _safe_pct_change(cur_ev_sold, ev_sold_prior),
            "yoy_sold_delta_pct": _safe_pct_change(cur_ev_sold, ev_sold_year_ago),
        },
        "skipped_reason": None,
    }


# ─── Mix block builder ─────────────────────────────────────────────────────


def _build_mix_block(
    new_by_quarter: dict[str, dict | None],
    used_by_quarter: dict[str, dict | None],
    classification: str,
    dq_events: list[str],
) -> dict[str, Any] | None:
    """New/Used mix = new_sold / (new_sold + used_sold) × 100 per quarter,
    plus QoQ / YoY delta in pp.

    Used-only / New-only dealer-groups: Mix is undefined (single-channel by
    definition); return None and DQ event (f).
    """
    if classification in ("Used-only", "New-only"):
        dq_events.append(f"(f) Mix dimension skipped for {classification} classification.")
        return None

    def _new_pct(new_agg, used_agg):
        if not new_agg and not used_agg:
            return None
        new_sold = _to_int(new_agg.get("total_sold_count")) if new_agg else 0
        used_sold = _to_int(used_agg.get("total_sold_count")) if used_agg else 0
        new_sold = new_sold or 0
        used_sold = used_sold or 0
        total = new_sold + used_sold
        if total <= 0:
            return None
        return new_sold / total * 100.0

    cur = _new_pct(new_by_quarter.get("current"), used_by_quarter.get("current"))
    prior = _new_pct(new_by_quarter.get("prior"), used_by_quarter.get("prior"))
    year_ago = _new_pct(new_by_quarter.get("year_ago"), used_by_quarter.get("year_ago"))

    return {
        "new_pct_current": cur,
        "new_pct_prior": prior,
        "new_pct_year_ago": year_ago,
        "qoq_delta_pp": _safe_delta(cur, prior),
        "yoy_delta_pp": _safe_delta(cur, year_ago),
    }


# ─── Per-make raw (OEM multi-make only) ────────────────────────────────────


def _build_per_make_raw(
    per_make: dict[str, Any] | None,
    makes: list[str],
    windows: dict[str, Any],
    dq_events: list[str],
    headline_sold_count_total: int | None = None,
) -> list[dict[str, Any]] | None:
    """Build per-make raw rows for multi-make OEM tickers. Returns None for
    single-make tickers (N=1) or non-OEM entities. Each row carries the
    current-quarter combined-channel volume + QoQ + YoY for use in the
    `per_make_divergence` rule in `aggregate_signals.py`, plus per-make
    ASP/DOM/MSRP-gap deltas + share-of-ticker for the §4 breakdown table.

    Rows are sorted by `sold_count_current` descending to match the template's
    rendering order (assets/w1-output-template.md §4: "ordered by sold_count_current desc").

    MSRP-gap deltas use New-channel only (structurally — MSRP is a new-vehicle
    concept; Used MSRP-gap captures depreciation, not discount).
    """
    if not per_make or len(makes) < 2:
        return None

    rows: list[dict[str, Any]] = []
    for make in makes:
        make_data = per_make.get(make)
        if not make_data:
            dq_events.append(f"(r) Per-make breakdown excluded {make} — no data assembled.")
            continue

        new_by_window = make_data.get("sold_new_by_window")
        used_by_window = make_data.get("sold_used_by_window")
        new_cur, new_prior, new_year_ago = _assign_to_quarter(new_by_window, windows)
        used_cur, used_prior, used_year_ago = _assign_to_quarter(used_by_window, windows)

        cur = _combine_channels(used_cur, new_cur)
        prior = _combine_channels(used_prior, new_prior)
        year_ago = _combine_channels(used_year_ago, new_year_ago)

        cur_sold = _to_int(cur.get("total_sold_count")) if cur else None
        if cur_sold is None:
            dq_events.append(
                f"(r) Per-make breakdown excluded {make} — no current-quarter sold data."
            )
            continue

        if cur_sold < 100:
            dq_events.append(
                f"(i) Low-volume make {make} — current-quarter sold = {cur_sold} (<100/month threshold scaled to quarter)."
            )

        prior_sold = _to_int(prior.get("total_sold_count")) if prior else None
        year_ago_sold = _to_int(year_ago.get("total_sold_count")) if year_ago else None

        # Combined-channel ASP + DOM for per-make trajectory
        cur_asp = _to_float(cur.get("weighted_avg_sale_price")) if cur else None
        prior_asp = _to_float(prior.get("weighted_avg_sale_price")) if prior else None
        year_ago_asp = _to_float(year_ago.get("weighted_avg_sale_price")) if year_ago else None
        cur_dom = _to_float(cur.get("weighted_avg_days_on_market")) if cur else None
        prior_dom = _to_float(prior.get("weighted_avg_days_on_market")) if prior else None
        year_ago_dom = _to_float(year_ago.get("weighted_avg_days_on_market")) if year_ago else None

        # New-channel-only MSRP-gap (MSRP-gap is structurally new-vehicle only)
        cur_msrp_gap = _to_float(new_cur.get("weighted_price_over_msrp_percentage")) if new_cur else None
        prior_msrp_gap = _to_float(new_prior.get("weighted_price_over_msrp_percentage")) if new_prior else None
        year_ago_msrp_gap = _to_float(new_year_ago.get("weighted_price_over_msrp_percentage")) if new_year_ago else None

        # Share-of-ticker
        share_pct = None
        if (
            headline_sold_count_total is not None
            and headline_sold_count_total > 0
            and cur_sold is not None
        ):
            share_pct = cur_sold / headline_sold_count_total * 100.0

        rows.append({
            "make": make,
            "share_pct": share_pct,
            "sold_count_current": cur_sold,
            "sold_count_prior": prior_sold,
            "sold_count_year_ago": year_ago_sold,
            "qoq_vol_pct": _safe_pct_change(cur_sold, prior_sold),
            "yoy_vol_pct": _safe_pct_change(cur_sold, year_ago_sold),
            "weighted_avg_sale_price_current": cur_asp,
            "qoq_asp_pct": _safe_pct_change(cur_asp, prior_asp),
            "yoy_asp_pct": _safe_pct_change(cur_asp, year_ago_asp),
            "weighted_avg_days_on_market_current": cur_dom,
            "qoq_dom_delta_days": _safe_delta(cur_dom, prior_dom),
            "yoy_dom_delta_days": _safe_delta(cur_dom, year_ago_dom),
            "qoq_msrp_gap_delta_bps": _safe_bps_delta(cur_msrp_gap, prior_msrp_gap),
            "yoy_msrp_gap_delta_bps": _safe_bps_delta(cur_msrp_gap, year_ago_msrp_gap),
        })

    # Sort by sold_count_current desc to align with template §4 rendering rule.
    rows.sort(key=lambda r: (r.get("sold_count_current") or 0), reverse=True)
    return rows or None


# ─── Active inventory + Days Supply ────────────────────────────────────────


def _build_active_inventory_channel(
    active: dict[str, Any] | None,
    mrcm_sold: int | None,
    days_in_month: int,
    dq_events: list[str],
    channel_label: str,
) -> dict[str, Any] | None:
    """Build active-inventory record for one channel (Used or New).

    Returns None if the channel was not queried (active is None — channel
    not applicable to the classification). Otherwise emits num_found +
    days_supply + price/dom stats.
    """
    if not isinstance(active, dict):
        return None

    if not active.get("ok"):
        # Parser-reported error
        dq_events.append(f"(a) Active-inventory call for {channel_label} failed: {active.get('error_type')}")
        return None

    num_found = _to_int(active.get("num_found"))
    if num_found is None:
        return None

    stats_present = bool(active.get("stats_present"))
    if not stats_present:
        dq_events.append(f"(d) Active-inventory stats absent for {channel_label}; rendering num_found only.")

    stats = active.get("stats") if stats_present else None
    avg_price = None
    avg_dom = None
    p50_price = p75_price = p90_price = median_price = None
    p50_dom = p75_dom = p90_dom = median_dom = None
    if isinstance(stats, dict):
        price_block = stats.get("price")
        if isinstance(price_block, dict):
            avg_price = _to_float(price_block.get("mean"))
            median_price = _to_float(price_block.get("median"))
            pcts_p = price_block.get("percentiles")
            if isinstance(pcts_p, dict):
                p50_price = _to_float(pcts_p.get("50"))
                p75_price = _to_float(pcts_p.get("75"))
                p90_price = _to_float(pcts_p.get("90"))
        dom_block = stats.get("dom")
        if isinstance(dom_block, dict):
            avg_dom = _to_float(dom_block.get("mean"))
            median_dom = _to_float(dom_block.get("median"))
            pcts_d = dom_block.get("percentiles")
            if isinstance(pcts_d, dict):
                p50_dom = _to_float(pcts_d.get("50"))
                p75_dom = _to_float(pcts_d.get("75"))
                p90_dom = _to_float(pcts_d.get("90"))

    days_supply = _compute_days_supply(num_found, mrcm_sold, days_in_month)
    if days_supply is None and num_found is not None:
        dq_events.append(
            f"(n) Days Supply for {channel_label} null — mrcm sold_count was 0 or unavailable."
        )

    return {
        "num_found": num_found,
        "days_supply": days_supply,
        "active_avg_price": avg_price,
        "active_avg_dom": avg_dom,
        "active_p50_price": p50_price,
        "active_p75_price": p75_price,
        "active_p90_price": p90_price,
        "active_median_price": median_price,
        "active_p50_dom": p50_dom,
        "active_p75_dom": p75_dom,
        "active_p90_dom": p90_dom,
        "active_median_dom": median_dom,
        "mrcm_sold_count": _to_int(mrcm_sold),
    }


# ─── Main orchestration ────────────────────────────────────────────────────


def _classify_inputs(cfg: dict) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Validate top-level shape. Returns (per_make, per_group, validation_error)."""
    entity_type = cfg.get("entity_type")
    if entity_type == "oem":
        if not isinstance(cfg.get("per_make"), dict) or not cfg.get("makes"):
            return None, None, "missing_per_make_for_oem"
        return cfg["per_make"], None, None
    if entity_type == "dealer_group":
        if not isinstance(cfg.get("per_group"), dict):
            return None, None, "missing_per_group_for_dealer_group"
        return None, cfg["per_group"], None
    return None, None, "unknown_entity_type"


def _build_combined_quarters_for_oem(
    per_make: dict[str, Any], makes: list[str], windows: dict[str, Any]
) -> tuple[dict, dict, dict, int | None, int | None]:
    """For an OEM, roll up per-make per-quarter aggregates into ticker-level
    aggregates per channel. Returns:
      (new_by_quarter, used_by_quarter, combined_by_quarter,
       mrcm_sold_new, mrcm_sold_used)
    Each *_by_quarter dict has keys 'current', 'prior', 'year_ago'.
    """
    mrcm_label = (
        windows.get("most_recent_complete_month", {}).get("date_from", "")[:7] or None
    )

    new_cur_aggs, new_prior_aggs, new_year_ago_aggs = [], [], []
    used_cur_aggs, used_prior_aggs, used_year_ago_aggs = [], [], []
    mrcm_new = 0
    mrcm_used = 0
    mrcm_new_seen = False
    mrcm_used_seen = False

    for make in makes:
        make_data = per_make.get(make) or {}
        for channel, cur_list, prior_list, year_ago_list in (
            ("new", new_cur_aggs, new_prior_aggs, new_year_ago_aggs),
            ("used", used_cur_aggs, used_prior_aggs, used_year_ago_aggs),
        ):
            by_window = make_data.get(f"sold_{channel}_by_window")
            cur, prior, year_ago = _assign_to_quarter(by_window, windows)
            if cur is not None:
                cur_list.append(cur)
            if prior is not None:
                prior_list.append(prior)
            if year_ago is not None:
                year_ago_list.append(year_ago)
            mrcm_count = _extract_mrcm_sold(by_window, mrcm_label)
            if mrcm_count is not None:
                if channel == "new":
                    mrcm_new += mrcm_count
                    mrcm_new_seen = True
                else:
                    mrcm_used += mrcm_count
                    mrcm_used_seen = True

    new_by_quarter = {
        "current": _combine_monthly_aggs(new_cur_aggs),
        "prior": _combine_monthly_aggs(new_prior_aggs),
        "year_ago": _combine_monthly_aggs(new_year_ago_aggs),
    }
    used_by_quarter = {
        "current": _combine_monthly_aggs(used_cur_aggs),
        "prior": _combine_monthly_aggs(used_prior_aggs),
        "year_ago": _combine_monthly_aggs(used_year_ago_aggs),
    }
    combined_by_quarter = {
        "current": _combine_channels(used_by_quarter["current"], new_by_quarter["current"]),
        "prior":   _combine_channels(used_by_quarter["prior"],   new_by_quarter["prior"]),
        "year_ago":_combine_channels(used_by_quarter["year_ago"],new_by_quarter["year_ago"]),
    }
    return (
        new_by_quarter, used_by_quarter, combined_by_quarter,
        mrcm_new if mrcm_new_seen else None,
        mrcm_used if mrcm_used_seen else None,
    )


def _build_combined_quarters_for_dealer_group(
    per_group: dict[str, Any], windows: dict[str, Any]
) -> tuple[dict, dict, dict, int | None, int | None]:
    """Dealer-group equivalent of `_build_combined_quarters_for_oem`. Returns
    the same 5-tuple shape."""
    mrcm_label = (
        windows.get("most_recent_complete_month", {}).get("date_from", "")[:7] or None
    )

    new_cur, new_prior, new_year_ago = _assign_to_quarter(
        per_group.get("sold_new_by_window"), windows
    )
    used_cur, used_prior, used_year_ago = _assign_to_quarter(
        per_group.get("sold_used_by_window"), windows
    )

    new_by_quarter = {"current": new_cur, "prior": new_prior, "year_ago": new_year_ago}
    used_by_quarter = {"current": used_cur, "prior": used_prior, "year_ago": used_year_ago}
    combined_by_quarter = {
        "current": _combine_channels(used_cur, new_cur),
        "prior":   _combine_channels(used_prior, new_prior),
        "year_ago":_combine_channels(used_year_ago, new_year_ago),
    }
    mrcm_new = _extract_mrcm_sold(per_group.get("sold_new_by_window"), mrcm_label)
    mrcm_used = _extract_mrcm_sold(per_group.get("sold_used_by_window"), mrcm_label)
    return new_by_quarter, used_by_quarter, combined_by_quarter, mrcm_new, mrcm_used


def _build_ev_by_quarter(
    per_entity: dict[str, Any], windows: dict[str, Any], is_oem: bool, makes: list[str] | None
) -> dict[str, dict | None]:
    """Pool EV-slice aggregates per quarter. For OEM: sum across makes. For
    dealer-group: single entry."""
    if not is_oem:
        cur, prior, year_ago = _assign_to_quarter(
            per_entity.get("ev_slice_by_window") if per_entity else None, windows
        )
        return {"current": cur, "prior": prior, "year_ago": year_ago}

    cur_aggs, prior_aggs, year_ago_aggs = [], [], []
    for make in (makes or []):
        make_data = (per_entity or {}).get(make) or {}
        cur, prior, year_ago = _assign_to_quarter(
            make_data.get("ev_slice_by_window"), windows
        )
        if cur is not None:
            cur_aggs.append(cur)
        if prior is not None:
            prior_aggs.append(prior)
        if year_ago is not None:
            year_ago_aggs.append(year_ago)
    return {
        "current": _combine_monthly_aggs(cur_aggs),
        "prior":   _combine_monthly_aggs(prior_aggs),
        "year_ago":_combine_monthly_aggs(year_ago_aggs),
    }


def _resolve_active(per_entity: dict[str, Any] | None, is_oem: bool, makes: list[str] | None) -> tuple[dict | None, dict | None]:
    """Resolve combined active-inventory records (new, used) for the entity.

    For OEM with N≥2 makes: sum num_found across makes, weighted-mean the
    price/dom stats by num_found. For N=1 or dealer-group: pass through the
    single block.
    """
    if not is_oem:
        return (
            (per_entity or {}).get("active_used"),
            (per_entity or {}).get("active_new"),
        )

    # OEM: pool across makes.
    # Note: pooled percentiles use num_found-weighted mean of per-make percentile
    # values — an approximation consistent with the existing `mean` pooling
    # convention. A true distribution-aware pooled P90 would require raw
    # inventory rows; the weighted-mean approach is analyst-grade for the
    # purposes of relative comparisons and aging-tail detection.
    def _pool(channel: str) -> dict | None:
        records = []
        for make in (makes or []):
            mdata = (per_entity or {}).get(make) or {}
            rec = mdata.get(channel)
            if isinstance(rec, dict) and rec.get("ok"):
                records.append(rec)
        if not records:
            return None
        total_found = 0
        sum_price, n_price = 0.0, 0
        sum_dom, n_dom = 0.0, 0
        sum_p50p, n_p50p = 0.0, 0
        sum_p75p, n_p75p = 0.0, 0
        sum_p90p, n_p90p = 0.0, 0
        sum_medp, n_medp = 0.0, 0
        sum_p50d, n_p50d = 0.0, 0
        sum_p75d, n_p75d = 0.0, 0
        sum_p90d, n_p90d = 0.0, 0
        sum_medd, n_medd = 0.0, 0
        any_stats_present = False
        for r in records:
            nf = _to_int(r.get("num_found")) or 0
            total_found += nf
            stats = r.get("stats") if r.get("stats_present") else None
            if isinstance(stats, dict):
                any_stats_present = True
                price_block = stats.get("price") or {}
                price_mean = _to_float(price_block.get("mean"))
                if price_mean is not None and nf > 0:
                    sum_price += price_mean * nf
                    n_price += nf
                price_median = _to_float(price_block.get("median"))
                if price_median is not None and nf > 0:
                    sum_medp += price_median * nf
                    n_medp += nf
                pcts_p = price_block.get("percentiles") or {}
                if isinstance(pcts_p, dict) and nf > 0:
                    v50 = _to_float(pcts_p.get("50"))
                    if v50 is not None:
                        sum_p50p += v50 * nf; n_p50p += nf
                    v75 = _to_float(pcts_p.get("75"))
                    if v75 is not None:
                        sum_p75p += v75 * nf; n_p75p += nf
                    v90 = _to_float(pcts_p.get("90"))
                    if v90 is not None:
                        sum_p90p += v90 * nf; n_p90p += nf
                dom_block = stats.get("dom") or {}
                dom_mean = _to_float(dom_block.get("mean"))
                if dom_mean is not None and nf > 0:
                    sum_dom += dom_mean * nf
                    n_dom += nf
                dom_median = _to_float(dom_block.get("median"))
                if dom_median is not None and nf > 0:
                    sum_medd += dom_median * nf
                    n_medd += nf
                pcts_d = dom_block.get("percentiles") or {}
                if isinstance(pcts_d, dict) and nf > 0:
                    v50 = _to_float(pcts_d.get("50"))
                    if v50 is not None:
                        sum_p50d += v50 * nf; n_p50d += nf
                    v75 = _to_float(pcts_d.get("75"))
                    if v75 is not None:
                        sum_p75d += v75 * nf; n_p75d += nf
                    v90 = _to_float(pcts_d.get("90"))
                    if v90 is not None:
                        sum_p90d += v90 * nf; n_p90d += nf

        def _wm(s: float, n: int) -> float | None:
            return (s / n) if n > 0 else None

        return {
            "ok": True,
            "num_found": total_found,
            "stats_present": any_stats_present,
            "stats": {
                "price": {
                    "mean":   _wm(sum_price, n_price),
                    "median": _wm(sum_medp, n_medp),
                    "percentiles": {
                        "50": _wm(sum_p50p, n_p50p),
                        "75": _wm(sum_p75p, n_p75p),
                        "90": _wm(sum_p90p, n_p90p),
                    },
                },
                "dom": {
                    "mean":   _wm(sum_dom, n_dom),
                    "median": _wm(sum_medd, n_medd),
                    "percentiles": {
                        "50": _wm(sum_p50d, n_p50d),
                        "75": _wm(sum_p75d, n_p75d),
                        "90": _wm(sum_p90d, n_p90d),
                    },
                },
            } if any_stats_present else None,
        }

    return _pool("active_used"), _pool("active_new")


def compute(cfg: dict[str, Any]) -> dict[str, Any]:
    """Multi-quarter stats engine — pure callable.

    Consumes an assembled JSON document (as a Python dict) and emits the same
    output dict that `main()` would emit on stdout. Used directly by
    `orchestrate.py`; also wrapped by the CLI `main()` below for stdin/stdout
    use + tests.

    On halt (no current-quarter data): returns a dict with `ok: False`,
    `error_type: "no_current_quarter_data"`, `ticker`, `dq_events`.
    On validation failure: returns a dict with `ok: False`, `error_type`,
    `ticker`.
    On success: returns the full output envelope (see module docstring).
    """
    ticker = cfg.get("ticker")
    entity_type = cfg.get("entity_type")
    classification = cfg.get("classification")
    windows = cfg.get("windows") or {}
    makes = cfg.get("makes") or []

    per_make, per_group, validation_err = _classify_inputs(cfg)
    if validation_err:
        return {"ok": False, "error_type": validation_err, "ticker": ticker}

    dq_events: list[str] = []
    is_oem = entity_type == "oem"
    per_entity = per_make if is_oem else per_group

    # Roll up quarter aggregates
    if is_oem:
        new_by_q, used_by_q, combined_by_q, mrcm_new, mrcm_used = (
            _build_combined_quarters_for_oem(per_make or {}, makes, windows)
        )
    else:
        new_by_q, used_by_q, combined_by_q, mrcm_new, mrcm_used = (
            _build_combined_quarters_for_dealer_group(per_group or {}, windows)
        )

    # EV slice per quarter
    ev_by_q = _build_ev_by_quarter(per_entity, windows, is_oem, makes)

    # Active inventory (channel-level)
    active_used_raw, active_new_raw = _resolve_active(per_entity, is_oem, makes)

    # Days-in-month for Days Supply formula
    days_in_month = _to_int(
        windows.get("most_recent_complete_month", {}).get("days_in_month")
    ) or 30

    # ─── Build output blocks ────────────────────────────────────────────────

    headline_cur = combined_by_q.get("current")
    headline = {
        "sold_count_total":
            _to_int(headline_cur.get("total_sold_count")) if headline_cur else None,
        "weighted_avg_sale_price":
            _to_float(headline_cur.get("weighted_avg_sale_price")) if headline_cur else None,
        "weighted_avg_days_on_market":
            _to_float(headline_cur.get("weighted_avg_days_on_market")) if headline_cur else None,
    }

    leading_indicators_raw: dict[str, Any] = {
        "volume": _compute_volume_block(
            combined_by_q.get("current"),
            combined_by_q.get("prior"),
            combined_by_q.get("year_ago"),
        ),
        "asp": _compute_asp_block(
            combined_by_q.get("current"),
            combined_by_q.get("prior"),
            combined_by_q.get("year_ago"),
        ),
        "msrp_gap": _compute_msrp_gap_block(
            new_by_q.get("current"),
            new_by_q.get("prior"),
            new_by_q.get("year_ago"),
        ),
        "dom": _compute_dom_block(
            combined_by_q.get("current"),
            combined_by_q.get("prior"),
            combined_by_q.get("year_ago"),
        ),
    }

    # YoY-null handling (DQ event (m)) — when year-ago is null, the volume
    # composite degrades to QoQ-only per aggregate_signals.py
    if leading_indicators_raw["volume"]["year_ago"] is None and leading_indicators_raw["volume"]["current"] is not None:
        dq_events.append(
            "(m) Year-ago volume unavailable — volume_momentum will degrade to QoQ-only band."
        )

    # Days Supply blocks
    active_used = _build_active_inventory_channel(
        active_used_raw, mrcm_used, days_in_month, dq_events, "used"
    )
    active_new = _build_active_inventory_channel(
        active_new_raw, mrcm_new, days_in_month, dq_events, "new"
    )

    leading_indicators_raw["days_supply_used"] = (
        {"current": active_used["days_supply"]} if active_used and active_used.get("days_supply") is not None else None
    )
    leading_indicators_raw["days_supply_new"] = (
        {"current": active_new["days_supply"]} if active_new and active_new.get("days_supply") is not None else None
    )

    # EV block + leading_indicators_raw["ev_share"]
    ev_block = _build_ev_block(combined_by_q, ev_by_q, classification, dq_events)
    if ev_block["shape"] == "transition":
        leading_indicators_raw["ev_share"] = {
            "current_pct": ev_block["transition"]["ev_pct_current"],
            "prior_pct": ev_block["transition"]["ev_pct_prior"],
            "year_ago_pct": ev_block["transition"]["ev_pct_year_ago"],
            "qoq_delta_bps": ev_block["transition"]["qoq_delta_bps"],
            "yoy_delta_bps": ev_block["transition"]["yoy_delta_bps"],
        }
    else:
        leading_indicators_raw["ev_share"] = None

    # Mix block — dealer-group only. For OEM tickers, the New-vs-Used share is not
    # an OEM-level signal (OEMs ship New; Used is a downstream secondary market).
    # The slot is suppressed structurally so it does not contribute to the verdict.
    if is_oem:
        mix_block = None
        dq_events.append("(f) Mix dimension skipped for OEM ticker — not an OEM-level signal.")
    else:
        mix_block = _build_mix_block(new_by_q, used_by_q, classification, dq_events)
    if mix_block is not None:
        leading_indicators_raw["mix"] = {
            "new_pct_current": mix_block["new_pct_current"],
            "new_pct_prior": mix_block["new_pct_prior"],
            "new_pct_year_ago": mix_block["new_pct_year_ago"],
            "qoq_delta_pp": mix_block["qoq_delta_pp"],
            "yoy_delta_pp": mix_block["yoy_delta_pp"],
        }
    else:
        leading_indicators_raw["mix"] = None

    # Channel split (New vs Used) — display-only per-channel views of Volume,
    # ASP, DOM, MSRP-gap. Omitted for single-channel classifications.
    def _channel_split_for(by_q: dict[str, dict | None] | None) -> dict | None:
        if not by_q or all(by_q.get(k) is None for k in ("current", "prior", "year_ago")):
            return None
        return {
            "volume":   _compute_volume_block(by_q.get("current"), by_q.get("prior"), by_q.get("year_ago")),
            "asp":      _compute_asp_block(by_q.get("current"),    by_q.get("prior"), by_q.get("year_ago")),
            "dom":      _compute_dom_block(by_q.get("current"),    by_q.get("prior"), by_q.get("year_ago")),
            "msrp_gap": _compute_msrp_gap_block(by_q.get("current"),by_q.get("prior"),by_q.get("year_ago")),
        }

    leading_indicators_raw["channel_split"] = {
        "new":  _channel_split_for(new_by_q)  if classification != "Used-only" else None,
        "used": _channel_split_for(used_by_q) if classification != "New-only"  else None,
    }

    # Per-make raw (OEM N≥2 only). Pass headline.sold_count_total for share_pct.
    per_make_raw = _build_per_make_raw(
        per_make, makes, windows, dq_events, headline["sold_count_total"]
    ) if is_oem else None

    # Halt condition: no current-quarter sold data at all
    if headline["sold_count_total"] is None or headline["sold_count_total"] == 0:
        return {
            "ok": False,
            "error_type": "no_current_quarter_data",
            "ticker": ticker,
            "dq_events": dq_events,
        }

    return {
        "ok": True,
        "ticker": ticker,
        "company_name": cfg.get("company_name"),
        "canonical": cfg.get("canonical"),
        "entity_type": entity_type,
        "classification": classification,
        "windows": windows,
        "headline": headline,
        "leading_indicators_raw": leading_indicators_raw,
        "per_make_raw": per_make_raw,
        "active_inventory": {
            "used": active_used,
            "new": active_new,
            "footnote": (
                "Days Supply pairs live active inventory (today's snapshot) with "
                "the most-recent-complete-month sold velocity — a live-vs-historical mix."
            ),
        },
        "ev_block": ev_block,
        "mix_block": mix_block,
        "dq_events": dq_events,
    }


def main(argv: list[str]) -> int:
    """Thin stdin/stdout wrapper around `compute(cfg)`. CLI entry-point."""
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump(
            {"ok": False, "error_type": "bad_stdin", "error": str(exc)},
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 0

    out = compute(cfg)

    # Halt and validation-error outputs: compact JSON (matches prior behavior).
    # Success output: indented JSON.
    if out.get("ok"):
        json.dump(out, sys.stdout, indent=2)
    else:
        json.dump(out, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
