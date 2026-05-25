#!/usr/bin/env python3
"""
aggregate_w5_signals.py — Deterministic W5 (Competitor Price Movement)
aggregation. Closes the LLM-hand-rolling surface that v4/v5/v6-style "compute
in the agent's head" workflows leave open.

Reads parse_search outputs from W5 Wave B's 4 parallel calls and emits a
canonical W5 signals JSON consumed by the renderer (no LLM judgment in
between).

Inputs (paths to parse_search outputs):
  --drops <step1.json>            # W5 step 1: price_change="negative" scan
  --raises <step2.json>           # W5 step 2: price_change="positive" scan
  --denominator <step3.json>      # W5 step 3: rows=0 stats="price,miles"
  --sold-90d <step4.json>         # W5 step 4: search_past_90_days, rows=0, sold=true

Optional (controls response matrix + self-exclusion):
  --user-reference-price <X>      # anchors response matrix; when omitted, undercut_flags=[]
  --user-reference-miles <X>      # mileage_delta_pct axis (mileage moat detection)
  --user-reference-dom <X>        # dom_delta axis (urgency modulation)
  --user-reference-cpo true|false # CPO-parity axis (bidirectional adjustment)
  --user-reference-vin <V>        # filter listings where vin == V (single-VIN)
  --user-dealer-id <id>           # filter listings where dealer_id == id (multi-VIN)
  --user-dealer-name <name>       # fallback self-exclusion when listing.dealer_id is null (v1.8.1+)
  --user-cost-floor <X>           # never recommend suggested_price below this
  --year-range-inferred true|false # passthrough flag set by W5 reference layer when year was inferred (v1.8.1+)

Output: JSON to stdout. See module-level OUTPUT_SCHEMA docstring for the schema.

Constants and decision algorithm: see DECISION_ALGORITHM_RATIONALE below.

Exit codes:
  0  OK (signals JSON emitted on stdout)
  1  Missing required input file or malformed payload
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# ─── Decision algorithm constants (W5 plan A.3) ───────────────────────────

GAP_PCT_NOISE_FLOOR = 2.0
"""Gap below this is within typical inter-platform price-mapping noise — not
statistically meaningful as an undercut. Below this, recommendation is HOLD
(no action)."""

GAP_PCT_MATCH_FLOOR = 5.0
"""Gap above this materially threatens market share — full match recommended.
Based on retail margin norms (used-car retail margin typically 6-12%); a 5%+
undercut compresses margin enough that defending share trumps margin
protection."""

GAP_PCT_OUTLIER_CEILING = 50.0
"""Gap above this is almost certainly a data error or trim mismatch (different
unit class). Do not recommend matching — surface as data quality concern."""

MOS_TIGHT_THRESHOLD = 1.5
"""MoS below this = supply scarce, demand-driven. Industry-standard tight-market
threshold (sourced from automotive sales analytics: NADA, Cox Automotive market
reports). When tight, demand exceeds supply and there's no pressure to chase
undercutters."""

COMPETITOR_DOM_AGING_DAYS = 60
"""Competitor sitting longer than this AND undercutting us = they're flailing
(the unit isn't moving at the new price either). Match aggressively before
they drop further. Aligns with the SKILL.md profile default
`aging_max_days` threshold."""

CPO_PREMIUM_PCT = 6.0
"""Typical retail premium for CPO vs equivalent non-CPO unit (used-car
research; varies 4-8% by segment). Used to bidirectionally adjust raw_gap_pct
when CPO mismatch exists between user and competitor."""

MILEAGE_MOAT_DELTA_PCT = 20.0
"""Mileage moat threshold; matches comp_stats.MILEAGE_MOAT_DELTA_PCT. Subject
20%+ under competitor's miles = mileage moat justifies a retail premium."""

MILEAGE_MOAT_PREMIUM_PCT = 3.0
"""Estimated retail premium for a mileage-moat unit (per 20% miles delta).
Conservative estimate — used cars depreciate ~$0.10-0.15 per mile in the
30-60K range."""

# ─── Aggregation thresholds (M8 fix) ──────────────────────────────────────

AGGRESSIVE_RAISER_THRESHOLD_PCT = 10.0
"""Raises >10% are typically data corrections (re-listings after a removal),
not strategic moves. Surface as a Key Signal warning rather than treating as
competitive intelligence."""

INVENTORY_PRESSURE_MIN_DROPS = 3
"""3+ drops in the top-20 from a single dealer = significant turn-rate
concern at that rooftop. Below 3 = noise; could be coincidence."""

DEEPEST_CUTS_MAX = 5
"""Cap deepest-drops list at 5 to keep rendering compact; deeper detail is in
the full Drop table."""


# ─── Multi-undercut alert thresholds (v1.8.1+) ────────────────────────────

MULTI_UNDERCUT_MIN_COUNT = 5
"""Number of significant undercuts (gap > MULTI_UNDERCUT_MIN_GAP_PCT) that
triggers a broad-market-pressure Key Signal. Below this, undercuts are
isolated; at/above, market-wide review is warranted rather than per-dealer
chase."""

MULTI_UNDERCUT_MIN_GAP_PCT = 5.0
"""Minimum gap_pct that counts as a 'significant' undercut for the
multi-undercut alert. Matches GAP_PCT_MATCH_FLOOR — undercuts below this
don't materially threaten share, so they don't contribute to broad market
pressure either."""


# ─── Constants snapshot (emitted in output for audit) ─────────────────────

CONSTANTS_USED = {
    "GAP_PCT_NOISE_FLOOR": GAP_PCT_NOISE_FLOOR,
    "GAP_PCT_MATCH_FLOOR": GAP_PCT_MATCH_FLOOR,
    "GAP_PCT_OUTLIER_CEILING": GAP_PCT_OUTLIER_CEILING,
    "MOS_TIGHT_THRESHOLD": MOS_TIGHT_THRESHOLD,
    "COMPETITOR_DOM_AGING_DAYS": COMPETITOR_DOM_AGING_DAYS,
    "CPO_PREMIUM_PCT": CPO_PREMIUM_PCT,
    "MILEAGE_MOAT_DELTA_PCT": MILEAGE_MOAT_DELTA_PCT,
    "MILEAGE_MOAT_PREMIUM_PCT": MILEAGE_MOAT_PREMIUM_PCT,
    "AGGRESSIVE_RAISER_THRESHOLD_PCT": AGGRESSIVE_RAISER_THRESHOLD_PCT,
    "INVENTORY_PRESSURE_MIN_DROPS": INVENTORY_PRESSURE_MIN_DROPS,
    "DEEPEST_CUTS_MAX": DEEPEST_CUTS_MAX,
    "MULTI_UNDERCUT_MIN_COUNT": MULTI_UNDERCUT_MIN_COUNT,
    "MULTI_UNDERCUT_MIN_GAP_PCT": MULTI_UNDERCUT_MIN_GAP_PCT,
}


# ─── CLI helpers ──────────────────────────────────────────────────────────

def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _to_float(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).replace(",", "").replace("$", "").replace("£", ""))
    except (TypeError, ValueError):
        return None


def _to_int(raw: Any) -> int | None:
    f = _to_float(raw)
    if f is None:
        return None
    try:
        return int(f)
    except (TypeError, ValueError):
        return None


def _to_bool(raw: Any) -> bool | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return raw
    s = str(raw).lower().strip()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    return None


def _load_json(path_str: str | None, label: str, required: bool = True) -> dict[str, Any]:
    if not path_str:
        if required:
            sys.stderr.write(f"aggregate_w5_signals: --{label} is required\n")
            raise SystemExit(1)
        return {}
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"aggregate_w5_signals: cannot read {label} file {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"aggregate_w5_signals: {label} file {path_str!r} is not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"aggregate_w5_signals: {label} payload must be a JSON object\n")
        raise SystemExit(1)
    return payload


# ─── Aggregation helpers ──────────────────────────────────────────────────

def _filter_self(
    listings: list[dict],
    user_vin: str | None,
    user_dealer_id: int | None,
    user_dealer_name: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Split listings into (kept, self_excluded). Self-exclusion priority:
    1. listing.vin matches --user-reference-vin (single-VIN, most specific)
    2. listing.dealer_id matches --user-dealer-id (multi-VIN, server-canonical id)
    3. listing.dealer_name matches --user-dealer-name (fallback when
       listing.dealer_id is None — v1.8.1+; some server responses omit the id)
    Any of the three matches excludes the listing."""
    kept: list[dict] = []
    excluded: list[dict] = []
    user_vin_upper = (user_vin or "").upper().strip()
    user_dealer_name_norm = (user_dealer_name or "").strip()
    for lst in listings:
        is_self = False
        if user_vin_upper:
            lvin = (lst.get("vin") or "").upper().strip() if isinstance(lst.get("vin"), str) else ""
            if lvin and lvin == user_vin_upper:
                is_self = True
        if not is_self and user_dealer_id is not None:
            ldid = lst.get("dealer_id")
            if ldid is not None:
                try:
                    if int(ldid) == int(user_dealer_id):
                        is_self = True
                except (TypeError, ValueError):
                    pass
        if not is_self and user_dealer_name_norm and lst.get("dealer_id") is None:
            lname_raw = lst.get("dealer_name")
            if isinstance(lname_raw, str):
                lname = lname_raw.strip()
                if lname and lname == user_dealer_name_norm:
                    is_self = True
        (excluded if is_self else kept).append(lst)
    return kept, excluded


def _group_by_dealer(listings: list[dict]) -> list[dict]:
    """Group listings by dealer_name; within each group, total drop count and
    sum of |price_change_amount| (drop magnitude). Returns sorted by drop_count
    desc."""
    groups: dict[str, dict] = {}
    for lst in listings:
        # v1.8.1: strip leading/trailing whitespace; case preserved (display value).
        # Catches server-data artifacts like "Big Sky Ford" vs "Big Sky Ford ".
        name = (lst.get("dealer_name") or "").strip() or "<unknown dealer>"
        g = groups.setdefault(name, {
            "dealer_name": name,
            "dealer_id": lst.get("dealer_id"),
            "drop_count": 0,
            "drop_total_$": 0.0,
            "listings": [],
        })
        g["drop_count"] += 1
        amt = _to_float(lst.get("price_change_amount"))
        if amt is not None:
            g["drop_total_$"] += abs(amt)
        g["listings"].append(lst)
    out = list(groups.values())
    # Round to int dollars for display
    for g in out:
        g["drop_total_$"] = int(round(g["drop_total_$"]))
    out.sort(key=lambda g: (-g["drop_count"], -g["drop_total_$"]))
    return out


def _detect_aggregate_heterogeneity(listings: list[dict]) -> dict:
    """Detect when aggregate signals span heterogeneous sub-trim variants
    (W5 v1.8.1+).

    Surfaces drivetrain / fuel_type / body_type variance at the SET level
    (distinct from render_comp_set_table.py's per-ROW spec subtitle, which
    handles the table cells). When `is_heterogeneous == true`, the renderer
    emits a Key Signal warning that aggregate signals (drop_rate,
    dealer_groups, deepest_drops, response_matrix gap_pct) span variants.

    Note on field availability: parse_search.py emits `body_type` and
    `drivetrain` flat at the listing root (parse_search.py lines 143-144),
    but does NOT currently emit `fuel_type`. The check tolerates absence —
    when a field is missing across all listings, its set is empty and
    contributes zero to the heterogeneity decision.
    """
    drivetrains = sorted({l.get("drivetrain") for l in listings if l.get("drivetrain")})
    fuel_types = sorted({l.get("fuel_type") for l in listings if l.get("fuel_type")})
    body_types = sorted({l.get("body_type") for l in listings if l.get("body_type")})
    return {
        "is_heterogeneous": (
            len(drivetrains) > 1
            or len(fuel_types) > 1
            or len(body_types) > 1
        ),
        "drivetrains": drivetrains,
        "fuel_types": fuel_types,
        "body_types": body_types,
        "drivetrain_count": len(drivetrains),
        "fuel_type_count": len(fuel_types),
        "body_type_count": len(body_types),
    }


def _decide_response(axes: dict, user_price: float, competitor_price: float,
                     user_cost_floor: float | None) -> dict | None:
    """Return decision dict {recommendation, reason, suggested_price, axes_used}
    for an undercut listing, OR None if the listing is not a real undercut.

    Axes input keys (all optional except raw_gap_pct):
      raw_gap_pct, adjusted_gap_pct, cpo_adjustment_pct, mileage_delta_pct,
      dom_delta, mos, competitor_dom_active, competitor_in_pressure
    """
    raw = axes["raw_gap_pct"]
    adj = axes.get("adjusted_gap_pct", raw)
    used: list[str] = ["raw_gap_pct"]

    # Step 0: Skip non-undercuts
    if raw <= 0:
        return None  # listing is at or below user price; not an undercut

    # Step 1: Outlier sanity check
    if raw > GAP_PCT_OUTLIER_CEILING:
        return {
            "recommendation": "HOLD",
            "reason": f"Outlier gap ({raw:.1f}%) — likely data error or trim mismatch; do not match.",
            "suggested_price": None,
            "axes_used": used + ["outlier_ceiling"],
        }

    # Step 2: CPO premium absorbs gap (we have CPO, they don't, gap within noise after adjustment)
    if axes.get("cpo_adjustment_pct", 0) > 0 and adj <= GAP_PCT_NOISE_FLOOR:
        return {
            "recommendation": "HOLD",
            "reason": f"After CPO adjustment, adjusted gap is {adj:.1f}% — within noise. Our CPO justifies the premium vs competitor's non-CPO.",
            "suggested_price": None,
            "axes_used": used + ["cpo_adjustment_pct", "adjusted_gap_pct"],
        }

    # Step 3: Mileage moat absorbs gap
    miles_delta = axes.get("mileage_delta_pct")
    if miles_delta is not None and miles_delta >= MILEAGE_MOAT_DELTA_PCT and adj <= GAP_PCT_NOISE_FLOOR:
        return {
            "recommendation": "HOLD",
            "reason": f"Our unit has {miles_delta:.0f}% fewer miles; mileage premium absorbs the gap.",
            "suggested_price": None,
            "axes_used": used + ["mileage_delta_pct", "adjusted_gap_pct"],
        }

    # Step 4: Tight market override
    mos = axes.get("mos")
    if mos is not None and mos < MOS_TIGHT_THRESHOLD:
        return {
            "recommendation": "HOLD",
            "reason": f"Tight market (MoS={mos:.1f}); demand-driven — no pressure to chase.",
            "suggested_price": None,
            "axes_used": used + ["mos"],
        }

    # Step 5: Core gap-based decision
    if adj != raw:
        used.append("adjusted_gap_pct")

    if adj <= GAP_PCT_NOISE_FLOOR:
        return {
            "recommendation": "HOLD",
            "reason": f"Adjusted gap {adj:.1f}% within {GAP_PCT_NOISE_FLOOR}% noise floor; not material.",
            "suggested_price": None,
            "axes_used": used,
        }

    if adj <= GAP_PCT_MATCH_FLOOR:
        # SPLIT — midpoint
        suggested = user_price - (user_price - competitor_price) * 0.5
        if user_cost_floor is not None and suggested < user_cost_floor:
            return {
                "recommendation": "HOLD",
                "reason": f"Split would breach cost floor (${int(user_cost_floor):,}); recommend HOLD and absorb DOM cost rather than below-cost sale.",
                "suggested_price": None,
                "axes_used": used + ["user_cost_floor"],
            }
        return {
            "recommendation": "SPLIT",
            "reason": f"Moderate gap ({adj:.1f}%); split to midpoint for partial response.",
            "suggested_price": int(round(suggested)),
            "axes_used": used,
        }

    # adj > GAP_PCT_MATCH_FLOOR — full match territory
    suggested = competitor_price
    if user_cost_floor is not None and suggested < user_cost_floor:
        return {
            "recommendation": "HOLD",
            "reason": f"Match would breach cost floor (${int(user_cost_floor):,}); recommend HOLD and absorb DOM cost rather than below-cost sale.",
            "suggested_price": None,
            "axes_used": used + ["user_cost_floor"],
        }

    # Refinement A: inventory-pressure dealer — single drop is part of broader pattern; downgrade to SPLIT
    if axes.get("competitor_in_pressure") is True:
        suggested_split = user_price - (user_price - competitor_price) * 0.5
        if user_cost_floor is None or suggested_split >= user_cost_floor:
            return {
                "recommendation": "SPLIT",
                "reason": f"Large gap ({adj:.1f}%) but competitor is in inventory-pressure list — drop is part of broader pattern, not isolated. SPLIT (not full match) for proportional response.",
                "suggested_price": int(round(suggested_split)),
                "axes_used": used + ["competitor_in_pressure"],
            }

    # Refinement B: competitor sitting AND we're not — they're flailing
    comp_dom = axes.get("competitor_dom_active")
    user_dom = axes.get("user_reference_dom")
    if comp_dom is not None and comp_dom > COMPETITOR_DOM_AGING_DAYS \
       and (user_dom is None or user_dom < comp_dom):
        return {
            "recommendation": "MATCH-AGGRESSIVE",
            "reason": f"Competitor sitting {comp_dom}d AND priced {adj:.1f}% under — match now or chase further drops.",
            "suggested_price": int(round(suggested)),
            "axes_used": used + ["competitor_dom_active", "dom_delta"],
        }

    # Default: full match
    return {
        "recommendation": "MATCH",
        "reason": f"Large gap ({adj:.1f}%); match competitor to defend market share.",
        "suggested_price": int(round(suggested)),
        "axes_used": used,
    }


def _build_undercut_flag(
    competitor: dict,
    user_price: float,
    user_miles: float | None,
    user_dom: int | None,
    user_cpo: bool | None,
    user_cost_floor: float | None,
    mos: float | None,
    inventory_pressure_dealer_ids: set,
) -> dict | None:
    """Compute axes for one undercut listing + invoke decision algorithm.
    Returns a populated undercut_flag dict, or None when the listing is not
    a real undercut (raw_gap_pct <= 0)."""
    competitor_price = _to_float(competitor.get("price"))
    if competitor_price is None or competitor_price <= 0:
        return None

    raw_gap_pct = (user_price - competitor_price) / user_price * 100.0
    if raw_gap_pct <= 0:
        return None  # not an undercut; user is at or below competitor

    # CPO adjustment
    competitor_cpo = competitor.get("is_certified")
    if isinstance(competitor_cpo, bool):
        comp_cpo_bool = competitor_cpo
    else:
        comp_cpo_bool = None
    if user_cpo is True and comp_cpo_bool is False:
        cpo_adj = +CPO_PREMIUM_PCT
    elif user_cpo is False and comp_cpo_bool is True:
        cpo_adj = -CPO_PREMIUM_PCT
    else:
        cpo_adj = 0.0

    adjusted_gap_pct = raw_gap_pct - cpo_adj

    # Mileage moat
    competitor_miles = _to_float(competitor.get("miles"))
    mileage_delta_pct = None
    if user_miles is not None and competitor_miles is not None and user_miles > 0:
        mileage_delta_pct = (competitor_miles - user_miles) / user_miles * 100.0
        if mileage_delta_pct >= MILEAGE_MOAT_DELTA_PCT:
            adjusted_gap_pct -= MILEAGE_MOAT_PREMIUM_PCT

    # DOM delta
    competitor_dom = _to_int(competitor.get("dom_active"))
    dom_delta = None
    if user_dom is not None and competitor_dom is not None:
        dom_delta = user_dom - competitor_dom

    # Inventory pressure flag
    comp_dealer_id = competitor.get("dealer_id")
    competitor_in_pressure = comp_dealer_id is not None and comp_dealer_id in inventory_pressure_dealer_ids

    axes = {
        "raw_gap_pct": raw_gap_pct,
        "adjusted_gap_pct": adjusted_gap_pct,
        "cpo_adjustment_pct": cpo_adj,
        "mileage_delta_pct": mileage_delta_pct,
        "dom_delta": dom_delta,
        "mos": mos,
        "competitor_dom_active": competitor_dom,
        "competitor_in_pressure": competitor_in_pressure,
        "user_reference_dom": user_dom,
    }

    decision = _decide_response(axes, user_price, competitor_price, user_cost_floor)
    if decision is None:
        return None

    return {
        "competitor_dealer_name": competitor.get("dealer_name"),
        "competitor_dealer_id": comp_dealer_id,
        "competitor_vin": competitor.get("vin"),
        "competitor_price": int(round(competitor_price)),
        "competitor_miles": _to_int(competitor_miles) if competitor_miles is not None else None,
        "competitor_dom_active": competitor_dom,
        "competitor_is_certified": comp_cpo_bool,
        "competitor_distance_mi": _to_float(competitor.get("distance_mi")),
        "competitor_in_pressure": competitor_in_pressure,
        "raw_gap_pct": round(raw_gap_pct, 2),
        "cpo_adjustment_pct": round(cpo_adj, 2),
        "mileage_delta_pct": round(mileage_delta_pct, 2) if mileage_delta_pct is not None else None,
        "dom_delta": dom_delta,
        "adjusted_gap_pct": round(adjusted_gap_pct, 2),
        "recommendation": decision["recommendation"],
        "reason": decision["reason"],
        "suggested_price": decision["suggested_price"],
        "axes_used": decision["axes_used"],
    }


# ─── Main ─────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    drops_path = _arg_value(argv, "--drops")
    raises_path = _arg_value(argv, "--raises")
    denominator_path = _arg_value(argv, "--denominator")
    sold_90d_path = _arg_value(argv, "--sold-90d")

    drops = _load_json(drops_path, "drops")
    raises = _load_json(raises_path, "raises")
    denominator = _load_json(denominator_path, "denominator")
    sold_90d = _load_json(sold_90d_path, "sold-90d", required=False)

    # Optional reference inputs
    user_price = _to_float(_arg_value(argv, "--user-reference-price"))
    user_miles = _to_float(_arg_value(argv, "--user-reference-miles"))
    user_dom = _to_int(_arg_value(argv, "--user-reference-dom"))
    user_cpo = _to_bool(_arg_value(argv, "--user-reference-cpo"))
    user_vin = _arg_value(argv, "--user-reference-vin")
    user_dealer_id = _to_int(_arg_value(argv, "--user-dealer-id"))
    user_dealer_name = _arg_value(argv, "--user-dealer-name")
    user_cost_floor = _to_float(_arg_value(argv, "--user-cost-floor"))
    year_range_inferred = _to_bool(_arg_value(argv, "--year-range-inferred"))

    # Extract listings + counts
    drop_listings_raw = drops.get("listings") or []
    raise_listings_raw = raises.get("listings") or []

    if not isinstance(drop_listings_raw, list):
        drop_listings_raw = []
    if not isinstance(raise_listings_raw, list):
        raise_listings_raw = []

    # Self-exclude user's own listings
    drop_listings, self_excluded = _filter_self(
        drop_listings_raw, user_vin, user_dealer_id, user_dealer_name,
    )

    # Active count from denominator
    active_count = int(_to_int(denominator.get("num_found")) or 0)

    # Drop / raise counts (post-self-exclusion for drops)
    drop_count = len(drop_listings)
    raise_count = len(raise_listings_raw)

    # Drop / raise rates
    drop_rate = drop_count / active_count if active_count > 0 else 0.0
    raise_rate = raise_count / active_count if active_count > 0 else 0.0

    # MoS
    sold_count_90d = int(_to_int(sold_90d.get("num_found")) or 0)
    mos = active_count / (sold_count_90d / 3.0) if sold_count_90d > 0 else None

    # Deepest drops (cap at DEEPEST_CUTS_MAX)
    # Sort by abs(price_change_percent) descending — deepest drops first
    def _abs_pct(lst: dict) -> float:
        pct = _to_float(lst.get("price_change_percent"))
        return abs(pct) if pct is not None else 0.0
    deepest_drops = sorted(drop_listings, key=_abs_pct, reverse=True)[:DEEPEST_CUTS_MAX]

    # Dealer grouping (only counts drops)
    dealer_groups = _group_by_dealer(drop_listings)
    inventory_pressure_dealers = [
        g for g in dealer_groups
        if g["drop_count"] >= INVENTORY_PRESSURE_MIN_DROPS
    ]
    inventory_pressure_dealer_ids = {
        g["dealer_id"] for g in inventory_pressure_dealers if g["dealer_id"] is not None
    }

    # Aggressive raisers (filter from step 2 by abs(pct) > threshold)
    aggressive_raisers = [
        r for r in raise_listings_raw
        if (_to_float(r.get("price_change_percent")) or 0) > AGGRESSIVE_RAISER_THRESHOLD_PCT
    ]

    # Undercut flags + response matrix
    undercut_flags: list[dict] = []
    response_matrix_fired = user_price is not None

    if response_matrix_fired:
        # Only listings BELOW user_price are undercuts; build axes + decision per row
        for competitor in drop_listings:
            flag = _build_undercut_flag(
                competitor=competitor,
                user_price=user_price,
                user_miles=user_miles,
                user_dom=user_dom,
                user_cpo=user_cpo,
                user_cost_floor=user_cost_floor,
                mos=mos,
                inventory_pressure_dealer_ids=inventory_pressure_dealer_ids,
            )
            if flag is not None:
                undercut_flags.append(flag)

    # v1.8.1: Multi-undercut market-pressure alert.
    # When ≥ MULTI_UNDERCUT_MIN_COUNT undercuts have raw_gap_pct >
    # MULTI_UNDERCUT_MIN_GAP_PCT, surface as a broad-market signal rather
    # than per-dealer chase recommendations.
    significant_undercuts = [
        f for f in undercut_flags
        if (f.get("raw_gap_pct") or 0) > MULTI_UNDERCUT_MIN_GAP_PCT
    ]
    sig_gaps = sorted(f["raw_gap_pct"] for f in significant_undercuts)
    if sig_gaps:
        median_gap = sig_gaps[len(sig_gaps) // 2]
        median_gap_rounded: float | None = round(float(median_gap), 2)
    else:
        median_gap_rounded = None
    multi_undercut_alert = {
        "fired": len(significant_undercuts) >= MULTI_UNDERCUT_MIN_COUNT,
        "count": len(significant_undercuts),
        "median_gap_pct": median_gap_rounded,
    }

    # v1.8.1: Aggregate-level heterogeneity detection over post-self-exclusion drops.
    # Renderer surfaces a Key Signal when is_heterogeneous == true.
    heterogeneity = _detect_aggregate_heterogeneity(drop_listings)

    # Emit
    out = {
        "ok": True,
        "active_count": active_count,
        "drop_count": drop_count,
        "raise_count": raise_count,
        "drop_rate": round(drop_rate, 4),
        "raise_rate": round(raise_rate, 4),
        "mos": round(mos, 2) if mos is not None else None,
        "deepest_drops": deepest_drops,
        "dealer_groups": dealer_groups,
        "inventory_pressure_dealers": inventory_pressure_dealers,
        "aggressive_raisers": aggressive_raisers,
        "self_excluded_drops": self_excluded,
        "undercut_flags": undercut_flags,
        "response_matrix_fired": response_matrix_fired,
        "multi_undercut_alert": multi_undercut_alert,
        "heterogeneity": heterogeneity,
        "year_range_inferred": year_range_inferred,
        "constants_used": CONSTANTS_USED,
        "source_files": {
            "drops": drops_path or "",
            "raises": raises_path or "",
            "denominator": denominator_path or "",
            "sold_90d": sold_90d_path or "",
        },
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
