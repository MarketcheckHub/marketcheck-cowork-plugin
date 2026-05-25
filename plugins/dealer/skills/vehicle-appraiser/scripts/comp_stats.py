#!/usr/bin/env python3
"""
comp_stats.py — Core statistics engine for the competitive-pricer skill.

Reads a JSON configuration from stdin with the merged active comp set and the
sold-90d aggregates, computes:
  - quartile distribution (min/p25/median/p75/max, mean, stddev)
  - percentile rank of user_price (with bounded range when tail is truncated)
  - DOM bucket counts using profile-driven fresh_max_days / aging_max_days
  - channel_stats (primary / secondary / primary_non_cpo) for same-channel view
  - sold-anchor verdict (if sold_count_90d >= 5) + quartile verdict (fallback)
  - mileage_moat detection (is the user's unit materially lower-miles than the set?)
  - Months-of-Supply (active_count / (sold_count_90d / 3))

Input (stdin JSON):
  {
    "user_price": <float|null>,
    "subject_vin": "...",
    "subject_dealer_type": "franchise"|"independent"|null,
    "subject_is_certified": <bool>,
    "subject_miles": <float|null>,
    "trim_label": "...",
    "radius_mi": <int>,
    "city": "...",
    "comps": [<normalized listing>, ...],      # from parse_search.py
    "active_count": <int>,                      # num_found from the primary asc fetch
    "pulled_count": <int>,                      # rows actually returned across asc+desc
    "sold_count_90d": <int>,
    "sold_median": <float|null>,
    "sold_dom_median": <float|null>,            # median DOM from W1 step 7c. PRIMARY path uses
                                                 # stats.dom_active.median (current-listing time-to-sell);
                                                 # FALLBACK uses stats.dom.median (lifetime cross-dealer)
                                                 # when upstream rejected stats=dom_active.
    "sold_dom_field":  "dom_active" | "dom" | null,  # which server-aggregate field sourced
                                                      # sold_dom_median above. Drives the renderer's
                                                      # label choice (days-to-sell vs lifetime DOM).
    "drops_market_wide_count": <int>,           # num_found from W1 step 6 (price_change="negative")
                                                 # — market-wide drop count (denominator is active_count)
    "server_stats": {"price": {...}, ...},      # optional — parse_search.stats block
    "fresh_max_days": <int>,                    # default 30
    "aging_max_days": <int>,                    # default 60
    "min_n": <int>,                             # default 6
    "exclude_vins": [<VIN>, ...]
  }

Output on stdout: see the `emit` call in main().
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from typing import Any


SOLD_ANCHOR_THRESHOLDS = {
    # Relative to the sold median
    "below":         -0.08,    # gap <= -8%
    "modestly_below": -0.03,    # -8% < gap <= -3%
    "at":             0.03,    # -3% < gap < +3%
    "modestly_above": 0.08,    # +3% <= gap < +8%
    # gap >= +8% is "above"
}

QUARTILE_LABELS = [
    "Below Market",
    "Modestly Below Market",
    "At Market",
    "Modestly Above Market",
    "Above Market",
]

# === Module constants (promoted from inline literals for testability) ===

# Default minimum comp count — sub-threshold runs emit `insufficient: True`
DEFAULT_MIN_N = 6

# Mileage-moat tier thresholds (subject miles vs. comp median miles, as %-under)
MOAT_TIER_THRESHOLD_PCT = 20.0     # >= 20% under median → "moat" tier
MODEST_TIER_THRESHOLD_PCT = 10.0   # 10-20% under median → "modest" tier

# Months-of-Supply tier thresholds (for `mos_tier` output)
MOS_TIGHT_MAX = 1.5    # mos < 1.5 → "tight" (supply < ~6 weeks)
MOS_HEAVY_MIN = 4.0    # mos >= 4.0 → "heavy" (supply > 16 weeks)
# In between → "balanced"

# Server-reported percentile edge bounds — below MIN or above MAX is "approx"
SERVER_PCT_MIN = 5.0
SERVER_PCT_MAX = 99.0

# Outlier detection — listings > N stddevs from mean
OUTLIER_Z_THRESHOLD = 2.0

# Default DOM bucket thresholds (overridden by profile preferences)
DEFAULT_FRESH_MAX_DAYS = 30
DEFAULT_AGING_MAX_DAYS = 60

# Minimum comps required for primary_non_cpo to render (below this is too thin
# for a meaningful median)
MIN_N_PRIMARY_NON_CPO = 2


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _percentile(sorted_vals: list[float], target: float) -> float:
    """Return the percentile rank of `target` within `sorted_vals` — that is,
    what % of values are strictly less than target. Equal values split evenly.
    Range 0–100."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    below = sum(1 for v in sorted_vals if v < target)
    equal = sum(1 for v in sorted_vals if v == target)
    rank = (below + equal / 2.0) / n * 100.0
    return rank


SERVER_PERCENTILE_KEYS = ("5.0", "25.0", "50.0", "75.0", "90.0", "95.0", "99.0")


def _quartile_from_server(price_stats: dict[str, Any]) -> dict[str, float] | None:
    """Build the quartile dict from the server's stats.price block.

    Real server stats.price shape:
      {min, max, count, missing, sum, mean, stddev, sum_of_squares, median,
       percentiles: {"5.0", "25.0", "50.0", "75.0", "90.0", "95.0", "99.0"}}

    Returns None when the required fields are absent, so the caller can fall
    back to client-side computation.
    """
    if not isinstance(price_stats, dict):
        return None
    pcts = price_stats.get("percentiles") if isinstance(price_stats.get("percentiles"), dict) else None
    if not pcts or not all(k in pcts for k in ("25.0", "50.0", "75.0")):
        return None
    count = price_stats.get("count")
    try:
        return {
            "min": float(price_stats.get("min")),
            "p25": float(pcts["25.0"]),
            "median": float(pcts["50.0"]),
            "p75": float(pcts["75.0"]),
            "max": float(price_stats.get("max")),
            "mean": float(price_stats.get("mean")),
            "stddev": float(price_stats.get("stddev") or 0.0),
            "n": int(count) if count is not None else 0,
        }
    except (TypeError, ValueError):
        return None


def _is_edge_interpolation(user_price: float, price_stats: dict[str, Any]) -> bool:
    """Return True when user_price falls outside the server's known percentile
    breakpoints (below p5 or above p99). In edge regions, `_percentile_from_server`
    returns the midpoint of the unknown half — a reasonable proxy but not a true
    interpolation. Callers mark these as `percentile_approx=True` so the renderer
    can show a `~` prefix.
    """
    pcts = price_stats.get("percentiles") if isinstance(price_stats.get("percentiles"), dict) else None
    if not pcts:
        return False
    prices = []
    for key in SERVER_PERCENTILE_KEYS:
        if key in pcts:
            try:
                prices.append(float(pcts[key]))
            except (TypeError, ValueError):
                continue
    if not prices:
        return False
    return user_price < min(prices) or user_price > max(prices)


def _percentile_from_server(user_price: float, price_stats: dict[str, Any]) -> float | None:
    """Interpolate user_price's percentile rank from the server's 7 known
    percentile points (5, 25, 50, 75, 90, 95, 99).

    Linear interpolation between adjacent breakpoints. Below p5 → 0-5 range
    (returns 2.5); above p99 → 99-100 range (returns 99.5). We use midpoints
    of the edge regions rather than 0 or 100 so the rendered rank doesn't
    claim absolute bounds the server's 7-point sketch can't support.
    """
    pcts = price_stats.get("percentiles") if isinstance(price_stats.get("percentiles"), dict) else None
    if not pcts:
        return None

    # Build sorted (percentile_value, price) points we have
    points: list[tuple[float, float]] = []
    for key in SERVER_PERCENTILE_KEYS:
        if key in pcts:
            try:
                pct_val = float(key)
                price_val = float(pcts[key])
                points.append((pct_val, price_val))
            except (TypeError, ValueError):
                continue
    if len(points) < 2:
        return None
    points.sort(key=lambda t: t[1])  # by price

    lowest_pct, lowest_price = points[0]
    highest_pct, highest_price = points[-1]

    if user_price <= lowest_price:
        # Below the lowest known percentile
        return lowest_pct / 2.0
    if user_price >= highest_price:
        # Above the highest known percentile
        return highest_pct + (100.0 - highest_pct) / 2.0

    # Find the bracketing pair and linearly interpolate
    for (p_lo, price_lo), (p_hi, price_hi) in zip(points, points[1:]):
        if price_lo <= user_price <= price_hi:
            if price_hi == price_lo:
                return (p_lo + p_hi) / 2.0
            frac = (user_price - price_lo) / (price_hi - price_lo)
            return p_lo + frac * (p_hi - p_lo)
    # Shouldn't reach here
    return None


def _quartile(sorted_vals: list[float]) -> dict[str, float]:
    if not sorted_vals:
        return {}
    n = len(sorted_vals)
    mean = statistics.fmean(sorted_vals)
    stddev = statistics.pstdev(sorted_vals) if n > 1 else 0.0
    # Type hints keep ruff happy with the indexing math below
    def q(p: float) -> float:
        if n == 1:
            return sorted_vals[0]
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])
    return {
        "min": sorted_vals[0],
        "p25": q(0.25),
        "median": q(0.5),
        "p75": q(0.75),
        "max": sorted_vals[-1],
        "mean": mean,
        "stddev": stddev,
        "n": n,
    }


# IQR multiplier for the Modestly Above / Above band fence. Symmetric with
# Modestly Below / Below on the lower side. Matches Tukey's standard IQR-based
# outlier fence conceptually — prices beyond this fence are "Above" / "Below".
IQR_FENCE_MULTIPLIER = 1.5


def _quartile_verdict(user_price: float | None, q: dict[str, float]) -> str | None:
    """Five-band classification using symmetric IQR-extension fences.

    Band mapping:
      x < p25 − 1.5·IQR         → Below Market
      p25 − 1.5·IQR ≤ x < p25   → Modestly Below Market
      p25 ≤ x ≤ p75              → At Market
      p75 < x ≤ p75 + 1.5·IQR   → Modestly Above Market
      x > p75 + 1.5·IQR         → Above Market

    Returns None (F6) when user_price or required quartile fields are absent —
    callers must handle a missing verdict rather than render a string label
    like "Insufficient Data".

    A3 — BREAKING CHANGE vs. prior asymmetric layout (where "Above Market"
    only fired for x > max — effectively unreachable). The new layout is
    symmetric around the IQR and meaningful on both ends.
    """
    if not q or user_price is None:
        return None
    p25 = q.get("p25")
    p75 = q.get("p75")
    if p25 is None or p75 is None:
        return None
    iqr = p75 - p25
    lower_fence = p25 - IQR_FENCE_MULTIPLIER * iqr
    upper_fence = p75 + IQR_FENCE_MULTIPLIER * iqr
    if user_price < lower_fence:
        return QUARTILE_LABELS[0]  # Below Market
    if user_price < p25:
        return QUARTILE_LABELS[1]  # Modestly Below Market
    if user_price <= p75:
        return QUARTILE_LABELS[2]  # At Market
    if user_price <= upper_fence:
        return QUARTILE_LABELS[3]  # Modestly Above Market
    return QUARTILE_LABELS[4]      # Above Market


def _sold_anchor_verdict(user_price: float | None, sold_median: float | None) -> str | None:
    """Five-band sold-anchor classification.

    Uses symmetric gap thresholds from SOLD_ANCHOR_THRESHOLDS (±3% At, ±8%
    Below/Above fences). Returns None when inputs are unusable.
    """
    if user_price is None or sold_median is None or sold_median <= 0:
        return None
    gap = (user_price - sold_median) / sold_median
    t = SOLD_ANCHOR_THRESHOLDS
    if gap <= t["below"]:
        return QUARTILE_LABELS[0]
    if gap <= t["modestly_below"]:
        return QUARTILE_LABELS[1]
    if gap < t["at"]:
        return QUARTILE_LABELS[2]
    if gap < t["modestly_above"]:
        return QUARTILE_LABELS[3]
    return QUARTILE_LABELS[4]


def _bucket_dom(dom_active: int | None, fresh_max: int, aging_max: int) -> str:
    """Bucket using `dom_active` ONLY. `dom_180` and lifetime `dom` measure
    different market-presence questions (seasonal cycles and cross-dealer VIN
    history, respectively) and MUST NOT be substituted as fallbacks here. A
    null `dom_active` buckets to `"unknown"` — never silently re-bucket.
    See `references/w1-price-check.md` step 4 for the field-semantic rationale.
    """
    if dom_active is None:
        return "unknown"
    if dom_active <= fresh_max:
        return "fresh"
    if dom_active <= aging_max:
        return "aging"
    return "stale"


def _compute_channel_stats(
    comps: list[dict[str, Any]],
    subject_dealer_type: str | None,
    subject_is_certified: bool,
) -> dict[str, Any]:
    def _group(ltype: str | None, non_cpo_only: bool = False) -> dict[str, Any]:
        if ltype is None:
            pool = comps
        else:
            pool = [c for c in comps if c.get("dealer_type") == ltype]
        if non_cpo_only:
            pool = [c for c in pool if not c.get("is_certified")]
        prices = sorted([c["price"] for c in pool if c.get("price") is not None])
        cpo_count = sum(1 for c in pool if c.get("is_certified"))
        return {
            "dealer_type": ltype,
            "non_cpo_only": non_cpo_only,
            "n": len(pool),
            "cpo_count": cpo_count,
            "stats": _quartile(prices),
        }

    if subject_dealer_type not in ("franchise", "independent"):
        return {"primary": None, "secondary": None, "primary_non_cpo": None}

    secondary_type = "independent" if subject_dealer_type == "franchise" else "franchise"

    primary = _group(subject_dealer_type)
    secondary = _group(secondary_type)

    primary_non_cpo = None
    if not subject_is_certified and primary["n"] >= MIN_N_PRIMARY_NON_CPO and primary["cpo_count"] > 0:
        candidate = _group(subject_dealer_type, non_cpo_only=True)
        # Drop the carve-out when the non-CPO slice is too thin to have a
        # meaningful median (C4 guard — was silently allowing n=1).
        if candidate["n"] >= MIN_N_PRIMARY_NON_CPO:
            primary_non_cpo = candidate

    return {"primary": primary, "secondary": secondary, "primary_non_cpo": primary_non_cpo}


def _mileage_moat(
    user_miles: float | None,
    comps: list[dict[str, Any]],
    trim_label: str,
    user_price: float | None,
    mkt_median: float | None,
) -> dict[str, Any]:
    """Mileage advantage analysis with tiered output.

    Tiers:
      - "moat"   — subject is ≥20% under the local comp median miles. `is_moat`
                   is True; `moat_phrase` carries a listing-copy-ready sentence
                   to append on the Headline.
      - "modest" — subject is 10%–20% under median. No Headline phrase; the
                   renderer surfaces this as a Key Signals bullet.
      - "none"   — subject is <10% under, at/above median, has missing miles,
                   or <5 comps with usable miles.

    `delta_pct` and `median_comp_miles` are populated in both "moat" and
    "modest" tiers for downstream rendering.
    """
    out: dict[str, Any] = {
        "is_moat": False,
        "moat_phrase": None,
        "user_miles": user_miles,
        "tier": "none",
        "delta_pct": None,
        "median_comp_miles": None,
    }
    if user_miles is None:
        return out
    miles = [c["miles"] for c in comps if c.get("miles") is not None and c["miles"] > 0]
    if len(miles) < 5:
        return out
    med_miles = statistics.median(miles)
    if med_miles <= 0 or user_miles >= med_miles:
        return out
    delta_pct = (med_miles - user_miles) / med_miles * 100.0
    out["delta_pct"] = delta_pct
    out["median_comp_miles"] = med_miles
    if delta_pct >= MOAT_TIER_THRESHOLD_PCT:
        out["tier"] = "moat"
        out["is_moat"] = True
        price_hint = ""
        if user_price is not None and mkt_median is not None and user_price <= mkt_median * 1.02:
            price_hint = " priced at or below market"
        out["moat_phrase"] = (
            f"{int(round(user_miles)):,}-mile {trim_label}"
            f" sits {int(round(delta_pct))}% under the local comp median of "
            f"{int(round(med_miles)):,} miles{price_hint}."
        )
    elif delta_pct >= MODEST_TIER_THRESHOLD_PCT:
        out["tier"] = "modest"
        # No moat_phrase — the "modest" tier surfaces as a Key Signals bullet,
        # not a Headline appendage. Renderer builds the bullet from delta_pct.
    return out


def _compute_mileage_distribution(
    filtered: list[dict[str, Any]],
    server_miles_stats: dict[str, Any],
) -> dict[str, Any] | None:
    """Return {source, min, median, mean, max, n} for comp miles.

    Prefer server-side stats (computed over all `active_count` listings on the
    asc pull's `stats="price,miles"`) because they cover the whole market
    rather than just the visible subset. Fall back to client-side computation
    over the filtered comp set when server stats are absent or incomplete.

    F5 — renderer was previously computing this from `parse_search.stats.miles`
    passthrough. Consolidating here keeps the renderer free of numeric work.
    """
    if isinstance(server_miles_stats, dict) and all(
        k in server_miles_stats for k in ("min", "max", "mean", "median")
    ):
        try:
            return {
                "source": "server",
                "min": float(server_miles_stats["min"]),
                "median": float(server_miles_stats["median"]),
                "mean": float(server_miles_stats["mean"]),
                "max": float(server_miles_stats["max"]),
                "n": int(server_miles_stats.get("count") or 0) or None,
            }
        except (TypeError, ValueError):
            pass  # fall through to client
    miles = sorted([c["miles"] for c in filtered if c.get("miles") is not None and c["miles"] > 0])
    if not miles:
        return None
    return {
        "source": "client",
        "min": miles[0],
        "median": statistics.median(miles),
        "mean": statistics.fmean(miles),
        "max": miles[-1],
        "n": len(miles),
    }


def _compute_mos_tier(mos: float | None) -> str | None:
    """Classify Months-of-Supply into 'tight' | 'balanced' | 'heavy'.

    Bounds from module constants MOS_TIGHT_MAX / MOS_HEAVY_MIN. Returns None
    when mos is unavailable (sold_count_90d == 0 or not computed).
    """
    if mos is None:
        return None
    if mos < MOS_TIGHT_MAX:
        return "tight"
    if mos >= MOS_HEAVY_MIN:
        return "heavy"
    return "balanced"


def _compute_marketcheck_predict_block(
    predict_input: dict[str, Any] | None,
    subject_dealer_type: str | None,
) -> dict[str, Any]:
    """Consolidate the four MarketCheck Price predict-call outputs + derived
    CPO premium / net margin into a single block the renderer reads verbatim.

    `predict_input` is the `marketcheck_predict_input` field from build_comp_stats_input,
    a dict of four roles (`nocpo_primary` / `nocpo_context` / `cpo_primary` /
    `cpo_context`) plus `certification_cost`. Each role is either a dict with
    {marketcheck_price, comparables_n, recent_comparables_n, comparables_price_stats,
    recent_comparables_price_stats} or None when that prediction call didn't run /
    didn't recover.

    `subject_dealer_type` is the lowercase subject dealer_type ("franchise" /
    "independent"); used to assign the human PRIMARY/CONTEXT labels.

    Returns the consolidated `marketcheck_predict` block. Per-role fields are
    null when the role is missing. Derived fields (premium_*, pct_*,
    net_margin_primary) are non-null only when both relevant predictions exist.

    The block name reflects that it owns every value derived from the
    MarketCheck Price MCP call surface — not just CPO derivations. Per-call
    detail (comp counts + price stats) is bundled so the renderer reads one
    consolidated source for every MarketCheck Price line in the report.
    """
    if not isinstance(predict_input, dict):
        predict_input = {}

    def _role(name: str) -> dict[str, Any] | None:
        block = predict_input.get(name)
        return block if isinstance(block, dict) else None

    nocpo_primary = _role("nocpo_primary")
    nocpo_context = _role("nocpo_context")
    cpo_primary   = _role("cpo_primary")
    cpo_context   = _role("cpo_context")
    certification_cost = _to_float(predict_input.get("certification_cost"))

    # Map lowercase dealer_type to display labels. None when subject_dealer_type
    # is missing — skill halts upstream when dealer_type isn't set, so this is
    # belt-and-suspenders.
    primary_label: str | None = None
    context_label: str | None = None
    if subject_dealer_type == "franchise":
        primary_label, context_label = "Franchise", "Independent"
    elif subject_dealer_type == "independent":
        primary_label, context_label = "Independent", "Franchise"

    def _price(role: dict[str, Any] | None) -> float | None:
        return _to_float(role.get("marketcheck_price")) if role else None

    nocpo_primary_price = _price(nocpo_primary)
    nocpo_context_price = _price(nocpo_context)
    cpo_primary_price   = _price(cpo_primary)
    cpo_context_price   = _price(cpo_context)

    # Premium = MarketCheck Price (CPO) − MarketCheck Price (non-CPO).
    # Computed only when both CPO and non-CPO prices exist for the same channel.
    premium_primary: float | None = None
    premium_context: float | None = None
    pct_primary:     float | None = None
    pct_context:     float | None = None
    if cpo_primary_price is not None and nocpo_primary_price is not None:
        premium_primary = cpo_primary_price - nocpo_primary_price
        if nocpo_primary_price > 0:
            pct_primary = premium_primary / nocpo_primary_price * 100.0
    if cpo_context_price is not None and nocpo_context_price is not None:
        premium_context = cpo_context_price - nocpo_context_price
        if nocpo_context_price > 0:
            pct_context = premium_context / nocpo_context_price * 100.0

    # Net Margin from CPO = CPO Premium − Certification Cost. Both Premium
    # inputs are MarketCheck Price values; the Premium itself is a derived
    # market concept (not a MarketCheck product), so it renders unprefixed.
    # Only the PRIMARY-channel net margin is computed (the dealer's own channel
    # is the only one where they'd actually pay the cert cost).
    net_margin_primary: float | None = None
    if premium_primary is not None and certification_cost is not None:
        net_margin_primary = premium_primary - certification_cost

    return {
        "primary_label":      primary_label,
        "context_label":      context_label,
        "nocpo_primary":      nocpo_primary,
        "nocpo_context":      nocpo_context,
        "cpo_primary":        cpo_primary,
        "cpo_context":        cpo_context,
        "premium_primary":    premium_primary,
        "premium_context":    premium_context,
        "pct_primary":        pct_primary,
        "pct_context":        pct_context,
        "certification_cost": certification_cost,
        "net_margin_primary": net_margin_primary,
    }


def _dom_buckets_pct(buckets: dict[str, int], n: int) -> dict[str, float]:
    """Return DOM bucket counts as percentages of the total n.

    D1 — renderer previously hand-computed these. When n == 0, all buckets
    are 0.0% (not NaN).
    """
    if n <= 0:
        return {k: 0.0 for k in buckets}
    return {k: (v / n * 100.0) for k, v in buckets.items()}


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    comps = cfg.get("comps") or []
    exclude_vins = {v.upper() for v in (cfg.get("exclude_vins") or [])}
    user_price = _to_float(cfg.get("user_price"))
    subject_vin = (cfg.get("subject_vin") or "").upper()
    subject_dealer_type = (cfg.get("subject_dealer_type") or "").lower() or None
    subject_is_certified = bool(cfg.get("subject_is_certified"))
    subject_miles = _to_float(cfg.get("subject_miles"))
    trim_label = cfg.get("trim_label") or "this unit"
    fresh_max = int(cfg.get("fresh_max_days") or DEFAULT_FRESH_MAX_DAYS)
    aging_max = int(cfg.get("aging_max_days") or DEFAULT_AGING_MAX_DAYS)
    min_n = int(cfg.get("min_n") or DEFAULT_MIN_N)
    active_count = int(cfg.get("active_count") or 0)
    pulled_count = int(cfg.get("pulled_count") or 0)
    sold_count_90d = int(cfg.get("sold_count_90d") or 0)
    sold_median = _to_float(cfg.get("sold_median"))
    sold_dom_median = _to_float(cfg.get("sold_dom_median"))  # H6 — data-backed action phrasing
    sold_dom_field = cfg.get("sold_dom_field")  # "dom_active" (PRIMARY) | "dom" (FALLBACK) | None
    if sold_dom_field not in ("dom_active", "dom", None):
        sold_dom_field = None
    drops_market_wide_count = int(cfg.get("drops_market_wide_count") or 0)  # C3/M11
    # Optional server-side stats block (from parse_search output's `stats` field).
    # When present with a usable count, we prefer its percentiles over
    # client-side computation because the server computes over all `num_found`
    # listings, not just the `pulled_count` subset.
    server_stats = cfg.get("server_stats") if isinstance(cfg.get("server_stats"), dict) else {}
    server_price_stats = server_stats.get("price") if isinstance(server_stats.get("price"), dict) else {}
    server_miles_stats = server_stats.get("miles") if isinstance(server_stats.get("miles"), dict) else {}

    # MarketCheck Price predict-call outputs — one record per role
    # (nocpo_primary / nocpo_context / cpo_primary / cpo_context) plus
    # certification cost from profile. All optional: when a role didn't run
    # (non-CPO subject skips CPO roles) or a prediction degraded, the role is
    # null and downstream derivations skip cleanly.
    marketcheck_predict_input = cfg.get("marketcheck_predict_input") if isinstance(cfg.get("marketcheck_predict_input"), dict) else {}

    # Defensive re-exclusion and re-filter (the calling skill should have
    # already excluded these, but be defensive). Counter shape matches
    # parse_search.py's filtered_out output — subject-VIN shadow hits and
    # other exclude_vins hits (e.g. history-hop VINs) count separately so
    # DQ events (c) and (d) can render distinct numbers.
    filtered: list[dict[str, Any]] = []
    filtered_out = {
        "self_vin_match": 0,
        "exclude_vin_match": 0,
        "invalid_price": 0,
    }
    for c in comps:
        vin = (c.get("vin") or "").upper()
        if subject_vin and vin == subject_vin:
            filtered_out["self_vin_match"] += 1
            continue
        if exclude_vins and vin in exclude_vins:
            filtered_out["exclude_vin_match"] += 1
            continue
        if c.get("price") in (None, 0) or (c.get("price") is not None and c["price"] <= 0):
            filtered_out["invalid_price"] += 1
            continue
        filtered.append(c)

    # Deprecated alias — matches parse_search.py's migration pattern. Kept for
    # one-version downstream migration; consumers should read the split keys.
    filtered_out["self_vin"] = filtered_out["self_vin_match"] + filtered_out["exclude_vin_match"]

    n = len(filtered)
    if n < min_n:
        json.dump({
            "ok": True,
            "insufficient": True,
            "reason": f"only {n} comps after filters (need {min_n})",
            "n": n,
            "min_n": min_n,
            "filtered_out": filtered_out,
            "active_count": active_count,
            "pulled_count": pulled_count,
            "sold_count_90d": sold_count_90d,
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    prices_sorted = sorted([c["price"] for c in filtered if c.get("price") is not None])

    # Stats source: prefer server-side (over all active_count listings) when
    # usable; otherwise compute from the visible pulled_count subset.
    server_quartile = _quartile_from_server(server_price_stats)
    if server_quartile is not None and server_quartile.get("n", 0) >= min_n:
        quartile = server_quartile
        stats_source = "server"
    else:
        quartile = _quartile(prices_sorted)
        stats_source = "client"

    # Percentile rank — decoupled from quartile source (M4).
    #
    # When server_stats.price.percentiles is present, we interpolate against
    # the server's 7-point sketch REGARDLESS of whether we used server or
    # client quartile, because the server percentiles cover ALL active_count
    # listings (not just the pulled_count visible subset). This resolves the
    # "middle-unseen" case that a pure bounded-range guard can't handle.
    #
    # Emit four states to downstream:
    #   percentile_source == "server", percentile_approx=False → exact rank
    #   percentile_source == "server", percentile_approx=True  → approx rank
    #       (server_n thin, or user_price outside p5..p99 edge region)
    #   percentile_source == "client", percentile_bounded set  → bounded range
    #       (no server percentiles AND user above visible max with unseen tail)
    #   percentile_source == "client", percentile_bounded None → exact rank
    #       over the visible subset
    percentile: float | None = None
    percentile_source: str | None = None
    percentile_approx: bool = False
    percentile_bounded: tuple[float, float] | None = None
    if user_price is not None:
        server_has_pcts = (
            isinstance(server_price_stats, dict)
            and isinstance(server_price_stats.get("percentiles"), dict)
            and server_price_stats["percentiles"]  # non-empty
        )
        if server_has_pcts:
            percentile = _percentile_from_server(user_price, server_price_stats)
            percentile_source = "server"
            server_n = int(server_price_stats.get("count") or 0)
            # Mark approx when the underlying count is thin OR the subject is
            # in the below-p5 / above-p99 edge region (midpoint proxy, not
            # true interpolation).
            percentile_approx = (
                server_n < min_n
                or _is_edge_interpolation(user_price, server_price_stats)
            )
        else:
            percentile = _percentile(prices_sorted, user_price)
            percentile_source = "client"
            # Bounded range only when server percentiles are absent entirely
            # AND we're above the visible tail with unseen rows remaining.
            # M4: apply the filter rate (n / pulled_count) to the unseen
            # population so we don't mix raw and filtered counts in the same
            # fraction.
            if pulled_count > 0 and pulled_count < active_count and user_price > prices_sorted[-1]:
                known_below = sum(1 for p in prices_sorted if p < user_price)
                filter_rate = n / pulled_count
                adjusted_unseen = (active_count - pulled_count) * filter_rate
                denom = n + adjusted_unseen
                if denom > 0:
                    low = known_below / denom * 100.0
                    high = (known_below + adjusted_unseen) / denom * 100.0
                    percentile_bounded = (low, high)

    # DOM bucket counts. Normalized listings carry dom as int | None from parse_*,
    # so a plain pass-through is correct (M2 — the prior ternary was a no-op).
    # DOM buckets: read `dom_active` only (per references/w1-price-check.md step 4
    # field-semantic rule). Do NOT fall back to `dom_180` or lifetime `dom` —
    # those measure different market-presence questions and would inflate Stale
    # counts on re-listings and dealer-hopped VINs.
    dom_buckets = {"fresh": 0, "aging": 0, "stale": 0, "unknown": 0}
    for c in filtered:
        b = _bucket_dom(c.get("dom_active"), fresh_max, aging_max)
        if isinstance(b, str):
            dom_buckets[b] += 1

    # Channel stats
    channel_stats = _compute_channel_stats(filtered, subject_dealer_type, subject_is_certified)

    # primary_only — canonical "same-channel" comparison for the renderer.
    # The output template's "Gap vs <PRIMARY>-Only Median" line reads from this
    # single consolidated field so the renderer never has to pick between
    # channel_stats.primary (all same-channel, inc. CPO) and
    # channel_stats.primary_non_cpo (same-channel minus CPO) inline.
    #
    # Source selection:
    #   - subject non-CPO AND primary_non_cpo.n >= 2 → use primary_non_cpo
    #     (strips CPO comps that would inflate the same-channel median against
    #     a non-CPO subject — avoids the "franchise comps look right, but 40%
    #     are CPO" misread).
    #   - otherwise → use primary (correct for CPO subjects, and for channels
    #     where the non-CPO carve isn't meaningful).
    #   - primary.n < 2 → primary_only is None; renderer skips the line.
    primary_only: dict[str, Any] | None = None
    if isinstance(channel_stats.get("primary"), dict) and (channel_stats["primary"].get("n") or 0) >= MIN_N_PRIMARY_NON_CPO:
        pri = channel_stats["primary"]
        pnc = channel_stats.get("primary_non_cpo")
        if (
            not subject_is_certified
            and isinstance(pnc, dict)
            and (pnc.get("n") or 0) >= MIN_N_PRIMARY_NON_CPO
        ):
            source, source_name = pnc, "primary_non_cpo"
        else:
            source, source_name = pri, "primary"
        median = (source.get("stats") or {}).get("median")
        diff = (user_price - median) if (user_price is not None and median is not None) else None
        pct = (diff / median * 100.0) if (diff is not None and median) else None
        primary_only = {
            "source": source_name,
            "dealer_type": source.get("dealer_type"),
            "n": source.get("n"),
            "median": median,
            "diff": diff,
            "pct": pct,
        }

    # Sold anchor vs quartile verdict
    verdict_quartile = _quartile_verdict(user_price, quartile) if user_price is not None else None
    verdict_sold_anchor = (
        _sold_anchor_verdict(user_price, sold_median)
        if user_price is not None and sold_median is not None and sold_count_90d >= 5
        else None
    )
    if verdict_sold_anchor is not None:
        verdict_source = "sold_anchor"
        verdict = verdict_sold_anchor
    else:
        verdict_source = "quartile"
        verdict = verdict_quartile

    # Months of Supply (active / (sold_90d / 3))
    mos: float | None = None
    if sold_count_90d > 0:
        sold_per_month = sold_count_90d / 3.0
        if sold_per_month > 0:
            mos = active_count / sold_per_month

    # Mileage moat
    mkt_median = quartile["median"] if quartile else None
    mileage_moat = _mileage_moat(subject_miles, filtered, trim_label, user_price, mkt_median)

    # Price-drop rate — two distinct scopes:
    #   visible: drops in the filtered comp set we rendered.
    #   market-wide: drops reported by the W1 step 6 price_change=negative call
    #                (num_found over the full active_count). Surfaces "how
    #                aggressive is the broader market" vs. "how aggressive are
    #                the 17 comps in the table."
    drops_in_set = sum(
        1 for c in filtered
        if c.get("price_change_percent") is not None and c["price_change_percent"] < 0
    )
    drop_rate_visible = drops_in_set / n if n > 0 else 0.0
    drop_rate_market_wide: float | None = None
    if active_count > 0:
        drop_rate_market_wide = drops_market_wide_count / active_count

    # Outliers (|x - mean| > N*stddev). C5 — when stats came from server but
    # the server-reported stddev is 0 / missing (thin samples, uniform prices
    # within the server's rollup), fall back to client-side stddev over the
    # filtered comp set. Otherwise outliers would silently never flag.
    outliers = []
    mean_for_outliers = quartile.get("mean") or 0.0
    sd_for_outliers = quartile.get("stddev") or 0.0
    if sd_for_outliers <= 0 and stats_source == "server" and len(prices_sorted) >= 2:
        client_q = _quartile(prices_sorted)
        sd_for_outliers = client_q.get("stddev") or 0.0
        mean_for_outliers = client_q.get("mean") or mean_for_outliers
    if sd_for_outliers > 0:
        for c in filtered:
            if c.get("price") is None:
                continue
            z = abs(c["price"] - mean_for_outliers) / sd_for_outliers
            if z > OUTLIER_Z_THRESHOLD:
                outliers.append({
                    "vin": c.get("vin"),
                    "price": c["price"],
                    "z": z,
                    "dealer_name": c.get("dealer_name"),
                    "miles": c.get("miles"),
                })

    # Gap vs market (primary signal line)
    gap_vs_median: dict[str, Any] = {}
    if user_price is not None and mkt_median:
        gap_vs_median = {
            "diff": user_price - mkt_median,
            "pct": (user_price - mkt_median) / mkt_median * 100.0,
        }

    # New output fields (D1/D2/D3/F5): pre-compute so renderer reads
    # fully-formed values instead of doing any math itself.
    dom_buckets_pct = _dom_buckets_pct(dom_buckets, n)
    mos_tier = _compute_mos_tier(mos)
    mileage_distribution = _compute_mileage_distribution(filtered, server_miles_stats)
    marketcheck_predict = _compute_marketcheck_predict_block(
        marketcheck_predict_input,
        subject_dealer_type,
    )

    out = {
        "ok": True,
        "insufficient": False,
        "n": n,
        "active_count": active_count,
        "pulled_count": pulled_count,
        "sold_count_90d": sold_count_90d,
        "sold_median": sold_median,
        "sold_dom_median": sold_dom_median,           # H6 — action-phrase anchor
        "sold_dom_field": sold_dom_field,             # H6 — "dom_active" | "dom" | None;
                                                       #      drives renderer label semantics
        "stats_source": stats_source,
        "quartile": quartile,
        "percentile": percentile,
        "percentile_source": percentile_source,       # M4 — "server" or "client"
        "percentile_approx": percentile_approx,       # M4 — True when thin/edge
        "percentile_bounded": list(percentile_bounded) if percentile_bounded else None,
        "gap_vs_median": gap_vs_median,
        "dom_buckets": dom_buckets,
        "dom_buckets_pct": dom_buckets_pct,           # D1 — renderer reads %s verbatim
        "mileage_distribution": mileage_distribution, # F5 — server-preferred, client fallback
        "channel_stats": channel_stats,
        "primary_only": primary_only,                 # canonical same-channel gap source
        "verdict": verdict,
        "verdict_source": verdict_source,
        "verdict_sold_anchor": verdict_sold_anchor,
        "verdict_quartile": verdict_quartile,
        "verdicts_disagree": (
            verdict_sold_anchor is not None
            and verdict_quartile is not None
            and verdict_sold_anchor != verdict_quartile
        ),
        "mos": mos,
        "mos_tier": mos_tier,                         # D2 — "tight" | "balanced" | "heavy"
        "mileage_moat": mileage_moat,
        "marketcheck_predict": marketcheck_predict,   # MarketCheck Price per role (4) + premiums + net margin. Renderer reads verbatim.
        "drops_in_set": drops_in_set,
        "drop_rate_visible": drop_rate_visible,       # C3/M11 — renamed from drop_rate_in_set
        "drops_market_wide_count": drops_market_wide_count,  # C3/M11 — raw count
        "drop_rate_market_wide": drop_rate_market_wide,      # C3/M11 — rate over active_count
        "outliers": outliers,
        "filtered_out": filtered_out,
        "fresh_max_days": fresh_max,
        "aging_max_days": aging_max,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
