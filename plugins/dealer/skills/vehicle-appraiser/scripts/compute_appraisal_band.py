#!/usr/bin/env python3
"""
compute_appraisal_band.py — Appraiser-domain low/mid/high band computation.

Reads `comp_stats.py` stdout JSON + a user-supplied condition flag and purpose,
emits a structured appraisal band that the renderer copies verbatim. Closes the
LLM-hand-rolling surface for the appraisal value-band block in the same way
`comp_stats.py` closed the verdict-band surface for competitive-pricer.

Anchor selection (decision tree, first match wins):
  1. comp_stats.sold_count_90d >= 5 AND comp_stats.sold_median is non-null
       → anchor_source = "sold_90d"
       → mid = sold_median
       → low/high = quartile.p25 / quartile.p75 (active distribution as the bracket)
  2. comp_stats.insufficient is False AND quartile.median is non-null
       → anchor_source = "active_comps"
       → mid = quartile.median, low = quartile.p25, high = quartile.p75
  3. comp_stats.insufficient is True AND marketcheck_predict.nocpo_primary is non-null
       → anchor_source = "predict_only"
       → mid = nocpo_primary.marketcheck_price
       → low/high = nocpo_primary.recent_comparables_price_stats.percentiles.{25.0,75.0}
                    or comparables_price_stats.percentiles.{25.0,75.0} fallback
                    or +/- 5% bracket if no stats available
  4. Otherwise → band = null, anchor_source = null, insufficient_reason populated

Confidence: comp_count_total = comp_stats.n + comp_stats.sold_count_90d
  < 5 → "Low"   — NEVER apply condition adjustment (defensive guard)
  5–14 → "Medium"
  15+ → "High"

Condition adjuster (only applied when confidence != "Low"):
  Clean → mid_adjusted = (mid + high) / 2
  Rough → mid_adjusted = (low + mid) / 2
  Average / unknown / null → no adjustment

Input (stdin JSON):
  {
    "comp_stats": <comp_stats output>,
    "condition": "Clean" | "Average" | "Rough" | null,
    "purpose": "Trade-in" | "Retail" | "Insurance" | "Wholesale" | null
  }

Output (stdout JSON):
  {
    "ok": true | false,
    "band": {"low": <float>, "mid": <float>, "high": <float>} | null,
    "confidence": "Low" | "Medium" | "High",
    "anchor_source": "sold_90d" | "active_comps" | "predict_only" | null,
    "comp_count_total": <int>,
    "sold_count_used": <int>,                 # 0 unless anchor_source == "sold_90d"
    "methodology_notes": [<string>, ...],
    "insufficient_reason": <string> | null,
    "condition_applied": "Clean" | "Average" | "Rough" | null,
    "purpose": <string> | null
  }
"""

from __future__ import annotations

import json
import sys
from typing import Any


SOLD_ANCHOR_MIN_COUNT = 5
CONFIDENCE_MEDIUM_MIN = 5
CONFIDENCE_HIGH_MIN = 15
PREDICT_ONLY_FALLBACK_PCT = 0.05  # +/-5% bracket when no stats are available


VALID_CONDITIONS = {"Clean", "Average", "Rough"}


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _confidence_bucket(comp_count_total: int) -> str:
    if comp_count_total < CONFIDENCE_MEDIUM_MIN:
        return "Low"
    if comp_count_total < CONFIDENCE_HIGH_MIN:
        return "Medium"
    return "High"


def _normalize_condition(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s in VALID_CONDITIONS else None


def _select_anchor(cs: dict[str, Any]) -> tuple[str | None, dict[str, float] | None, str | None, int]:
    """Return (anchor_source, band_pre_adjustment, insufficient_reason, sold_count_used).

    band is {low, mid, high} or None.
    """
    sold_count_90d = int(cs.get("sold_count_90d") or 0)
    sold_median = _to_float(cs.get("sold_median"))
    quartile = cs.get("quartile") if isinstance(cs.get("quartile"), dict) else {}
    insufficient = bool(cs.get("insufficient"))

    # Rule 1: sold_90d anchor
    if sold_count_90d >= SOLD_ANCHOR_MIN_COUNT and sold_median is not None and sold_median > 0:
        p25 = _to_float(quartile.get("p25"))
        p75 = _to_float(quartile.get("p75"))
        if p25 is None or p75 is None:
            # Fall back to +/-5% around sold_median
            low = sold_median * (1 - PREDICT_ONLY_FALLBACK_PCT)
            high = sold_median * (1 + PREDICT_ONLY_FALLBACK_PCT)
        else:
            low, high = p25, p75
        return "sold_90d", {"low": low, "mid": sold_median, "high": high}, None, sold_count_90d

    # Rule 2: active_comps anchor
    quartile_median = _to_float(quartile.get("median"))
    if not insufficient and quartile_median is not None:
        p25 = _to_float(quartile.get("p25")) or quartile_median * (1 - PREDICT_ONLY_FALLBACK_PCT)
        p75 = _to_float(quartile.get("p75")) or quartile_median * (1 + PREDICT_ONLY_FALLBACK_PCT)
        return "active_comps", {"low": p25, "mid": quartile_median, "high": p75}, None, 0

    # Rule 3: predict_only anchor (insufficient comp set, but ML predict succeeded)
    mc_predict = cs.get("marketcheck_predict") if isinstance(cs.get("marketcheck_predict"), dict) else {}
    nocpo_primary = mc_predict.get("nocpo_primary") if isinstance(mc_predict.get("nocpo_primary"), dict) else None
    if nocpo_primary is not None:
        mc_price = _to_float(nocpo_primary.get("marketcheck_price"))
        if mc_price is not None and mc_price > 0:
            low_pct, high_pct = None, None
            recent_stats = nocpo_primary.get("recent_comparables_price_stats")
            if isinstance(recent_stats, dict):
                pcts = recent_stats.get("percentiles") if isinstance(recent_stats.get("percentiles"), dict) else {}
                low_pct = _to_float(pcts.get("25.0"))
                high_pct = _to_float(pcts.get("75.0"))
            if low_pct is None or high_pct is None:
                comp_stats_block = nocpo_primary.get("comparables_price_stats")
                if isinstance(comp_stats_block, dict):
                    pcts = comp_stats_block.get("percentiles") if isinstance(comp_stats_block.get("percentiles"), dict) else {}
                    low_pct = _to_float(pcts.get("25.0")) if low_pct is None else low_pct
                    high_pct = _to_float(pcts.get("75.0")) if high_pct is None else high_pct
            if low_pct is None or high_pct is None:
                low_pct = mc_price * (1 - PREDICT_ONLY_FALLBACK_PCT)
                high_pct = mc_price * (1 + PREDICT_ONLY_FALLBACK_PCT)
            return "predict_only", {"low": low_pct, "mid": mc_price, "high": high_pct}, None, 0

    # Rule 4: nothing usable
    reason = "no anchor available — sold-90d count {sc} below threshold, active comp set {ic}, ML predict missing".format(
        sc=sold_count_90d,
        ic="insufficient" if insufficient else "missing quartile",
    )
    return None, None, reason, 0


def _apply_condition(band: dict[str, float], condition: str | None,
                     confidence: str) -> tuple[dict[str, float], str | None]:
    """Apply condition adjuster. Low confidence → never adjust."""
    if confidence == "Low" or condition is None or condition == "Average":
        return band, None
    low, mid, high = band["low"], band["mid"], band["high"]
    if condition == "Clean":
        return {"low": low, "mid": (mid + high) / 2.0, "high": high}, "Clean"
    if condition == "Rough":
        return {"low": low, "mid": (low + mid) / 2.0, "high": high}, "Rough"
    return band, None


def _build_methodology_notes(*, anchor_source: str | None, comp_count_total: int,
                             sold_count_used: int, active_n: int, confidence: str,
                             condition_applied: str | None, purpose: str | None,
                             insufficient_reason: str | None) -> list[str]:
    notes: list[str] = []
    if anchor_source == "sold_90d":
        notes.append(
            f"Anchored on {sold_count_used}-unit sold-90d trim median (real transaction prices)."
        )
    elif anchor_source == "active_comps":
        notes.append(
            f"Anchored on {active_n}-comp active-listing distribution "
            "(asking-price quartile; sold-90d count below 5)."
        )
    elif anchor_source == "predict_only":
        notes.append(
            "Anchored on MarketCheck Price ML prediction "
            "(active comp set thin; ML model used as fallback central estimate)."
        )
    if anchor_source is not None:
        notes.append(f"Confidence: {confidence} ({comp_count_total} total comps).")
    if condition_applied:
        notes.append(f"Condition adjustment applied: {condition_applied}.")
    if purpose:
        notes.append(f"Purpose: {purpose}.")
    if insufficient_reason:
        notes.append(f"Insufficient evidence: {insufficient_reason}")
    return notes


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if not isinstance(cfg, dict):
        json.dump({"ok": False, "error_type": "bad_stdin", "error": "stdin must be a JSON object"},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    cs = cfg.get("comp_stats") if isinstance(cfg.get("comp_stats"), dict) else {}
    condition = _normalize_condition(cfg.get("condition"))
    purpose_raw = cfg.get("purpose")
    purpose = str(purpose_raw).strip() if purpose_raw else None

    active_n = int(cs.get("n") or 0)
    sold_count_90d = int(cs.get("sold_count_90d") or 0)
    comp_count_total = active_n + sold_count_90d
    confidence = _confidence_bucket(comp_count_total)

    anchor_source, band, insufficient_reason, sold_count_used = _select_anchor(cs)

    if band is not None:
        band, condition_applied = _apply_condition(band, condition, confidence)
    else:
        condition_applied = None

    notes = _build_methodology_notes(
        anchor_source=anchor_source,
        comp_count_total=comp_count_total,
        sold_count_used=sold_count_used,
        active_n=active_n,
        confidence=confidence,
        condition_applied=condition_applied,
        purpose=purpose,
        insufficient_reason=insufficient_reason,
    )

    out = {
        "ok": True,
        "band": band,
        "confidence": confidence,
        "anchor_source": anchor_source,
        "comp_count_total": comp_count_total,
        "sold_count_used": sold_count_used,
        "methodology_notes": notes,
        "insufficient_reason": insufficient_reason,
        "condition_applied": condition_applied,
        "purpose": purpose,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
