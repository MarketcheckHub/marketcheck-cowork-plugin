#!/usr/bin/env python3
"""
compute_group_stats.py — Compute the headline + MoM + active-health + peer-rank
stats for a single dealer group. Used by W1 and W2.

Stdin JSON:
  {
    "group_canonical": "Carmax",
    "ticker": "KMX" | null,
    "classification": "Used-only" | "New-only" | "Both",
    "current_month_window": {
      "date_from": "2026-04-01", "date_to": "2026-04-30", "days_in_month": 30
    },
    "current_month": {
      "used": {"sold_count": ..., "weighted_avg_sale_price": ...,
               "weighted_avg_days_on_market": ...} | null,
      "new":  {...} | null
    },
    "prior_month": {"used": {...} | null, "new": {...} | null},
    "active": {
      "used": {"num_found": ..., "stats": {...} | null} | null,
      "new":  {...} | null
    },
    "peer_leaderboard": [
      {"dealership_group_name": ..., "total_sold_count": ...,
       "weighted_avg_sale_price": ..., "weighted_avg_days_on_market": ...},
      ...
    ]
  }

Stdout: see emit() at the bottom of main(). Every numeric block is computed in
code, never inline by the model.

Edge-case handling (all returned as `null`, never NaN or fabricated):
  - efficiency_score when DOM is 0 or null
  - volume_pct / asp_pct / efficiency_pct when prior denominator is 0 or null
  - dom_delta when either side is null
  - days_supply when sold_count is 0
  - peer_rank when target group not in peer_leaderboard

Days Supply asymmetry (AMB-08, can't fix):
  - num_found is live (today's snapshot)
  - sold_count is from current_month (most recent complete calendar month)
  - active_health.footnote makes this explicit on every render
"""

from __future__ import annotations

import json
import sys
from typing import Any


# ─── Helpers ────────────────────────────────────────────────────────────────


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


# Public-traded canonical → ticker map for peer_rank computation. Hard-coded
# here (rather than read from references/ticker-mapping.md) because
# compute_group_stats doesn't have classification ref access — and the 8-name
# set is stable.
PUBLIC_NAME_TO_TICKER = {
    "AutoNation Inc.":              "AN",
    "Lithia Motors Inc.":           "LAD",
    "Penske Automotive Group Inc.": "PAG",
    "Sonic Automotive Inc.":        "SAH",
    "Group 1 Automotive Inc.":      "GPI",
    "Asbury Automotive Group":      "ABG",
    "Carmax":                       "KMX",
    "Carvana":                      "CVNA",
}
PUBLIC_TICKER_NAMES = set(PUBLIC_NAME_TO_TICKER.keys())


# ─── Headline (current-month combined) ─────────────────────────────────────


def _combine_channels(
    used: dict[str, Any] | None,
    new: dict[str, Any] | None,
) -> dict[str, Any]:
    """Combine Used + New (or single channel) into one weighted aggregate.

    Returns {sold_count_total, weighted_avg_sale_price, weighted_avg_days_on_market}.
    None per-field when no channel has data.
    """
    channels = [c for c in (used, new) if c is not None]
    if not channels:
        return {
            "sold_count_total": None,
            "weighted_avg_sale_price": None,
            "weighted_avg_days_on_market": None,
        }
    total_sold = 0
    weighted_price_sum = 0.0
    weighted_dom_sum = 0.0
    for c in channels:
        sc = _to_int(c.get("sold_count")) or 0
        if sc <= 0:
            continue
        total_sold += sc
        asp = _to_float(c.get("weighted_avg_sale_price"))
        dom = _to_float(c.get("weighted_avg_days_on_market"))
        if asp is not None:
            weighted_price_sum += asp * sc
        if dom is not None:
            weighted_dom_sum += dom * sc
    if total_sold <= 0:
        return {
            "sold_count_total": 0 if channels else None,
            "weighted_avg_sale_price": None,
            "weighted_avg_days_on_market": None,
        }
    return {
        "sold_count_total": total_sold,
        "weighted_avg_sale_price": weighted_price_sum / total_sold if weighted_price_sum else None,
        "weighted_avg_days_on_market": weighted_dom_sum / total_sold if weighted_dom_sum else None,
    }


def _normalise_channel(channel: Any) -> dict[str, Any] | None:
    """Coerce a stdin channel record. Treat absent / empty-dict as None."""
    if not isinstance(channel, dict):
        return None
    sc = _to_int(channel.get("sold_count"))
    if sc is None:
        # Accept also `total_sold_count` as a synonym (parser emits this name)
        sc = _to_int(channel.get("total_sold_count"))
    if sc is None:
        return None
    return {
        "sold_count": sc,
        "weighted_avg_sale_price": _to_float(channel.get("weighted_avg_sale_price")),
        "weighted_avg_days_on_market": _to_float(channel.get("weighted_avg_days_on_market")),
    }


# ─── MoM ────────────────────────────────────────────────────────────────────


def _safe_pct_change(current: float | None, prior: float | None) -> float | None:
    """(current - prior) / prior * 100. None if prior is None / 0 / current is None."""
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / prior * 100.0


def _safe_delta(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None:
        return None
    return current - prior


def _efficiency(sold_count: int | float | None, dom: float | None) -> float | None:
    """sold / DOM. None when DOM <= 0 or null, or sold null."""
    if sold_count is None or dom is None or dom <= 0:
        return None
    return float(sold_count) / float(dom)


# ─── Active health ─────────────────────────────────────────────────────────


def _channel_active_health(
    active_channel: dict[str, Any] | None,
    sold_channel: dict[str, Any] | None,
    days_in_month: int,
) -> dict[str, Any] | None:
    """Compute one channel's active-health record. Returns None if the channel
    has no active data (channel not applicable to the classification)."""
    if not isinstance(active_channel, dict):
        return None
    num_found = _to_int(active_channel.get("num_found"))
    if num_found is None:
        return None
    stats = active_channel.get("stats") if isinstance(active_channel.get("stats"), dict) else None
    avg_price = _to_float(stats.get("price", {}).get("mean")) if stats else None
    avg_dom = _to_float(stats.get("dom", {}).get("mean")) if stats else None

    # Days Supply pairs live num_found with current_month sold_count
    sold_count = None
    if isinstance(sold_channel, dict):
        sold_count = _to_int(sold_channel.get("sold_count")) or _to_int(sold_channel.get("total_sold_count"))

    days_supply: float | None = None
    if num_found is not None and sold_count and sold_count > 0 and days_in_month > 0:
        days_supply = num_found * days_in_month / sold_count

    return {
        "num_found": num_found,
        "days_supply": days_supply,
        "active_avg_price": avg_price,
        "active_avg_dom": avg_dom,
    }


# ─── Peer rank ─────────────────────────────────────────────────────────────


def _build_peer_rank(
    target: str, leaderboard: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Rank target against the public-traded subset of the leaderboard.

    Returns None when target isn't in the leaderboard (e.g., fell below top-20).
    """
    if not leaderboard:
        return None
    # Filter to public-traded names
    public = [
        g for g in leaderboard
        if g.get("dealership_group_name") in PUBLIC_TICKER_NAMES
    ]
    if not any(g.get("dealership_group_name") == target for g in public):
        return None

    def rank_by(field: str, reverse: bool = True) -> dict[str, Any] | None:
        valid = [g for g in public if _to_float(g.get(field)) is not None]
        if not valid:
            return None
        sorted_g = sorted(valid, key=lambda g: _to_float(g.get(field)), reverse=reverse)
        for i, g in enumerate(sorted_g, start=1):
            if g.get("dealership_group_name") == target:
                out: dict[str, Any] = {"rank": i}
                if i < len(sorted_g):
                    target_val = _to_float(g.get(field))
                    next_val = _to_float(sorted_g[i].get(field))
                    if target_val and next_val and field == "total_sold_count":
                        out["delta_to_next_pct"] = (target_val - next_val) / next_val * 100.0
                return out
        return None

    # Add efficiency_score to each public group for ranking
    for g in public:
        sc = _to_int(g.get("total_sold_count"))
        dom = _to_float(g.get("weighted_avg_days_on_market"))
        g["_efficiency"] = _efficiency(sc, dom)

    # Build the per-peer KPI table. Sort desc by sold_count; mark the target row.
    # Peers with null total_sold_count sink to the end (treat as 0 for sort
    # only; the rendered value stays null).
    def _sort_key(g: dict[str, Any]) -> float:
        sc = _to_float(g.get("total_sold_count"))
        return sc if sc is not None else -1.0

    peers_sorted = sorted(public, key=_sort_key, reverse=True)
    peers = [
        {
            "canonical": g.get("dealership_group_name"),
            "ticker": PUBLIC_NAME_TO_TICKER.get(g.get("dealership_group_name")),
            "is_target": g.get("dealership_group_name") == target,
            "sold_count": _to_int(g.get("total_sold_count")),
            "weighted_avg_sale_price": _to_float(g.get("weighted_avg_sale_price")),
            "weighted_avg_days_on_market": _to_float(g.get("weighted_avg_days_on_market")),
            "efficiency_score": _to_float(g.get("_efficiency")),
        }
        for g in peers_sorted
    ]

    # Public groups that didn't make the top-20 leaderboard this month.
    present_names = {g.get("dealership_group_name") for g in public}
    dropped = sorted(PUBLIC_TICKER_NAMES - present_names)

    return {
        "of": len(public),
        "by_volume":     rank_by("total_sold_count", reverse=True),
        "by_asp":        rank_by("weighted_avg_sale_price", reverse=True),
        "by_dom":        rank_by("weighted_avg_days_on_market", reverse=False),  # lower better
        "by_efficiency": rank_by("_efficiency", reverse=True),
        "peers":         peers,
        "dropped":       dropped,
    }


# ─── Main ───────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)}, sys.stdout)
        sys.stdout.write("\n")
        return 0

    group_canonical = cfg.get("group_canonical")
    ticker = cfg.get("ticker")
    classification = cfg.get("classification") or "Both"
    cmw = cfg.get("current_month_window") or {}
    days_in_month = _to_int(cmw.get("days_in_month")) or 30

    cur = cfg.get("current_month") or {}
    pri = cfg.get("prior_month") or {}
    act = cfg.get("active") or {}
    peer_leaderboard = cfg.get("peer_leaderboard") or []

    cur_used = _normalise_channel(cur.get("used"))
    cur_new  = _normalise_channel(cur.get("new"))
    pri_used = _normalise_channel(pri.get("used"))
    pri_new  = _normalise_channel(pri.get("new"))

    # Headline: combined current-month aggregate
    cur_combined = _combine_channels(cur_used, cur_new)
    pri_combined = _combine_channels(pri_used, pri_new)

    headline = {
        "sold_count_total": cur_combined["sold_count_total"],
        "weighted_avg_sale_price": cur_combined["weighted_avg_sale_price"],
        "weighted_avg_days_on_market": cur_combined["weighted_avg_days_on_market"],
        "efficiency_score": _efficiency(
            cur_combined["sold_count_total"],
            cur_combined["weighted_avg_days_on_market"],
        ),
    }

    # MoM: percentage and delta values
    mom = {
        "volume_pct": _safe_pct_change(
            cur_combined["sold_count_total"], pri_combined["sold_count_total"]
        ),
        "asp_pct": _safe_pct_change(
            cur_combined["weighted_avg_sale_price"],
            pri_combined["weighted_avg_sale_price"],
        ),
        "dom_delta": _safe_delta(
            cur_combined["weighted_avg_days_on_market"],
            pri_combined["weighted_avg_days_on_market"],
        ),
        "efficiency_pct": _safe_pct_change(
            headline["efficiency_score"],
            _efficiency(
                pri_combined["sold_count_total"],
                pri_combined["weighted_avg_days_on_market"],
            ),
        ),
    }

    # Active health per channel (Days Supply uses current_month sold)
    used_health = _channel_active_health(act.get("used"), cur_used, days_in_month)
    new_health  = _channel_active_health(act.get("new"),  cur_new,  days_in_month)

    active_health = {
        "used": used_health,
        "new":  new_health,
        "footnote": "Days Supply pairs live active inventory (today's snapshot) "
                    "with the most-recent-complete-month sold velocity — "
                    "a live-vs-historical mix.",
    }

    # Peer rank (None when target not in leaderboard)
    peer_rank = _build_peer_rank(group_canonical, peer_leaderboard)

    out = {
        "ok": True,
        "group_canonical": group_canonical,
        "ticker": ticker,
        "classification": classification,
        "headline": headline,
        "mom": mom,
        "active_health": active_health,
        "peer_rank": peer_rank,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
