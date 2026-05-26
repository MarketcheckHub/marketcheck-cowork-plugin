#!/usr/bin/env python3
"""
aggregate_signals.py — Band classifier + composite combiner + verdict
reducer for the OEM Stock Tracker. Consumes raw numeric values from
compute_oem_stats.py; emits per-metric bands, composite-slot bands,
single headline verdict, signal drivers, and per-make divergence detection.

Stdin JSON (from compute_oem_stats output, sliced):
  {
    "leading_indicators_raw": {
      "volume":       {current, prior, baseline_3mo, baseline_3mo_avg_per_month, mom_pct, trend_3mo_pct},
      "asp":          {current, prior, mom_pct},
      "msrp_gap":     {current_pct, prior_pct, delta_bps},
      "days_supply":  {current, prior, mom_pct},
      "market_share": {current_pct, prior_pct, delta_bps},
      "dom":          {current, prior, delta_days},
      "ev_transition":{current_pct, prior_pct, delta_bps} | null
    },
    "per_make_raw": [{make, mom_vol_pct, trend_3mo_pct, ...}, ...] | null,
    "ticker_classification": "legacy" | "pure_play" | "brand_orphan"
  }

Stdout JSON:
  {
    ok, per_metric_bands, composite_slots, verdict, scores,
    mean_score, n_bullish, n_bearish, rationale, signal_drivers,
    per_make_divergence
  }

Banding rule: NEUTRAL is the closed interval [LOW, HIGH]; the adjacent
BULLISH or CAUTION band is open on the side that touches NEUTRAL; CAUTION
is closed on the BEARISH-touching side.

Composite combination rules:
  - volume_momentum: BULLISH iff both volume_mom and volume_trend are BULLISH;
                     BEARISH iff both BEARISH;
                     CAUTION if mom_pct > 0 AND trend_3mo_pct < 0 (short-term bounce);
                     NEUTRAL otherwise.
  - pricing_power:   BULLISH if asp.band == BULLISH AND msrp_gap.current_pct > 0;
                     BEARISH if asp.band == BEARISH AND msrp_gap.current_pct < 0;
                     CAUTION if asp.band == NEUTRAL AND msrp_gap.band ∈ {CAUTION, BEARISH};
                     NEUTRAL otherwise.

Reduction algorithm (first-match-wins):
  1. Skip null slots.
  2. mean = mean(scores) across contributing.
  3. n_bullish > 0 AND n_bearish > 0   → MIXED
  4. mean ≥ +1.0 AND n_bearish == 0    → BULLISH
  5. mean ≤ -1.0 AND n_bullish == 0    → BEARISH
  6. else                              → NEUTRAL
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _common import emit


BAND_SCORE = {
    "BULLISH": +2,
    "NEUTRAL":  0,
    "CAUTION": -1,
    "BEARISH": -2,
}


# ──────────────────────────────────────────────────────────────────────────
# Band classifiers (7 per-metric + 2 composite combiners)
# ──────────────────────────────────────────────────────────────────────────

def band_volume_mom(x: float) -> str:
    """Volume MoM (higher better). Thresholds: -3, -1, +3.
    BULLISH: x > +3 | NEUTRAL: -1 ≤ x ≤ +3 | CAUTION: -3 ≤ x < -1 | BEARISH: x < -3
    """
    if x > 3.0:
        return "BULLISH"
    if x >= -1.0:
        return "NEUTRAL"
    if x >= -3.0:
        return "CAUTION"
    return "BEARISH"


def band_volume_trend(x: float) -> str:
    """Volume 3-mo trend (higher better). Thresholds: -5, -2, +5.
    BULLISH: x > +5 | NEUTRAL: -2 ≤ x ≤ +5 | CAUTION: -5 ≤ x < -2 | BEARISH: x < -5
    """
    if x > 5.0:
        return "BULLISH"
    if x >= -2.0:
        return "NEUTRAL"
    if x >= -5.0:
        return "CAUTION"
    return "BEARISH"


def band_asp_mom(x: float) -> str:
    """ASP MoM (higher better). Thresholds: -3, -1, +1.
    BULLISH: x > +1 | NEUTRAL: -1 ≤ x ≤ +1 | CAUTION: -3 ≤ x < -1 | BEARISH: x < -3
    """
    if x > 1.0:
        return "BULLISH"
    if x >= -1.0:
        return "NEUTRAL"
    if x >= -3.0:
        return "CAUTION"
    return "BEARISH"


def band_msrp_gap_delta(x: float) -> str:
    """MSRP gap delta (bps, higher better). Thresholds: -150, -50, +50.
    BULLISH: x > +50 | NEUTRAL: -50 ≤ x ≤ +50 | CAUTION: -150 ≤ x < -50 | BEARISH: x < -150
    """
    if x > 50.0:
        return "BULLISH"
    if x >= -50.0:
        return "NEUTRAL"
    if x >= -150.0:
        return "CAUTION"
    return "BEARISH"


def band_days_supply(x: float) -> str:
    """Days Supply (lower better). Thresholds: 50, 80, 100.
    BULLISH: x < 50 | NEUTRAL: 50 ≤ x ≤ 80 | CAUTION: 80 < x ≤ 100 | BEARISH: x > 100
    """
    if x < 50.0:
        return "BULLISH"
    if x <= 80.0:
        return "NEUTRAL"
    if x <= 100.0:
        return "CAUTION"
    return "BEARISH"


def band_market_share_delta(x: float) -> str:
    """Market share delta (bps, higher better). Thresholds: -30, +30 (no CAUTION band).
    BULLISH: x > +30 | NEUTRAL: -30 ≤ x ≤ +30 | BEARISH: x ≤ -30
    """
    if x > 30.0:
        return "BULLISH"
    if x >= -30.0:
        return "NEUTRAL"
    return "BEARISH"


def band_dom_delta(x: float) -> str:
    """DOM delta (absolute days, lower better). Thresholds: -2, +2, +5.
    BULLISH: x < -2 | NEUTRAL: -2 ≤ x ≤ +2 | CAUTION: +2 < x ≤ +5 | BEARISH: x > +5
    """
    if x < -2.0:
        return "BULLISH"
    if x <= 2.0:
        return "NEUTRAL"
    if x <= 5.0:
        return "CAUTION"
    return "BEARISH"


def band_ev_transition_delta(x: float) -> str:
    """EV transition delta (bps, higher better). Thresholds: -50, +50 (no CAUTION band).
    BULLISH: x > +50 | NEUTRAL: -50 ≤ x ≤ +50 | BEARISH: x ≤ -50
    """
    if x > 50.0:
        return "BULLISH"
    if x >= -50.0:
        return "NEUTRAL"
    return "BEARISH"


# ──────────────────────────────────────────────────────────────────────────
# Composite combiners
# ──────────────────────────────────────────────────────────────────────────

def composite_volume_momentum(
    mom_band: str | None,
    trend_band: str | None,
    mom_pct: float | None,
    trend_3mo_pct: float | None,
) -> str | None:
    """Combine volume_mom + volume_trend per the composite rule."""
    if mom_band is None and trend_band is None:
        return None
    # If only one is available, use it directly (degraded mode)
    if mom_band is None:
        return trend_band
    if trend_band is None:
        return mom_band

    if mom_band == "BULLISH" and trend_band == "BULLISH":
        return "BULLISH"
    if mom_band == "BEARISH" and trend_band == "BEARISH":
        return "BEARISH"
    # CAUTION: short-term bounce on long-term decline
    if mom_pct is not None and trend_3mo_pct is not None:
        if mom_pct > 0 and trend_3mo_pct < 0:
            return "CAUTION"
    return "NEUTRAL"


def composite_pricing_power(
    asp_band: str | None,
    msrp_band: str | None,
    msrp_current_pct: float | None,
) -> str | None:
    """Combine asp + msrp_gap per the composite rule."""
    if asp_band is None and msrp_band is None:
        return None
    if asp_band is None:
        return msrp_band
    if msrp_band is None:
        return asp_band

    # BULLISH: ASP rising AND vehicles transacting above sticker
    if asp_band == "BULLISH" and msrp_current_pct is not None and msrp_current_pct > 0:
        return "BULLISH"
    # BEARISH: ASP falling AND deepening discounts below sticker
    if asp_band == "BEARISH" and msrp_current_pct is not None and msrp_current_pct < 0:
        return "BEARISH"
    # CAUTION: ASP flat but margin pressure building
    if asp_band == "NEUTRAL" and msrp_band in ("CAUTION", "BEARISH"):
        return "CAUTION"
    return "NEUTRAL"


# ──────────────────────────────────────────────────────────────────────────
# Score record builder
# ──────────────────────────────────────────────────────────────────────────

def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _band_value(value: Any, band_fn) -> str | None:
    v = _to_float(value)
    if v is None:
        return None
    return band_fn(v)


# ──────────────────────────────────────────────────────────────────────────
# Reducer
# ──────────────────────────────────────────────────────────────────────────

def reduce_verdict(composite_slots: dict[str, str | None]) -> dict[str, Any]:
    """Apply the headline-verdict reduction rule to composite slot bands."""
    contributing = {k: v for k, v in composite_slots.items() if v is not None}
    if not contributing:
        return {
            "verdict": None,
            "mean_score": None,
            "n_bullish": 0,
            "n_bearish": 0,
            "rationale": "No scoreable signals — all composite slots are null.",
            "reason": "no_scoreable_signals",
        }
    raw_scores = [BAND_SCORE[band] for band in contributing.values()]
    mean_score = sum(raw_scores) / len(raw_scores)
    n_bullish = sum(1 for band in contributing.values() if band == "BULLISH")
    n_bearish = sum(1 for band in contributing.values() if band == "BEARISH")

    if n_bullish > 0 and n_bearish > 0:
        verdict = "MIXED"
    elif mean_score >= 1.0 and n_bearish == 0:
        verdict = "BULLISH"
    elif mean_score <= -1.0 and n_bullish == 0:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    return {
        "verdict": verdict,
        "mean_score": round(mean_score, 4),
        "n_bullish": n_bullish,
        "n_bearish": n_bearish,
        "rationale": _build_rationale(contributing, verdict),
    }


def _build_rationale(slots: dict[str, str], verdict: str | None) -> str:
    if verdict is None:
        return "No scoreable signals — all composite slots are null."
    bullish = [k for k, b in slots.items() if b == "BULLISH"]
    bearish = [k for k, b in slots.items() if b == "BEARISH"]
    cautions = [k for k, b in slots.items() if b == "CAUTION"]
    if verdict == "MIXED":
        return f"BULLISH on {', '.join(bullish)}; BEARISH on {', '.join(bearish)}."
    if verdict == "BULLISH":
        return f"BULLISH on {', '.join(bullish) if bullish else 'aggregate signals'}."
    if verdict == "BEARISH":
        return f"BEARISH on {', '.join(bearish) if bearish else 'aggregate signals'}."
    if cautions:
        return f"NEUTRAL — watch for CAUTION on {', '.join(cautions)}."
    return "NEUTRAL — no slot crossed BULLISH or BEARISH thresholds."


def _build_signal_drivers(
    composite_slots: dict[str, str | None],
    scores: dict[str, dict[str, Any] | None],
) -> dict[str, dict[str, Any] | None]:
    """Identify strongest (highest score) and weakest (lowest score) composite slots.
    Returns {strongest, weakest} with each being {slot, band, score} or None."""
    contributing = [
        (slot, scores[slot])
        for slot in composite_slots
        if composite_slots[slot] is not None and scores.get(slot) is not None
    ]
    if not contributing:
        return {"strongest": None, "weakest": None}
    contributing.sort(key=lambda kv: kv[1]["score"], reverse=True)
    strongest = contributing[0]
    weakest = contributing[-1]
    # C-S14: "weakest" is meaningful only when there's a genuinely-weak slot
    # (CAUTION or BEARISH, i.e., score < 0). If all non-BULLISH slots are NEUTRAL
    # (tied at 0), reporting one of them as "weakest" misleads the analyst into
    # thinking there's a downside lurking. Return None instead.
    weakest_block = None
    if weakest[1]["score"] < 0:
        weakest_block = {
            "slot": weakest[0],
            "band": weakest[1]["band"],
            "score": weakest[1]["score"],
        }
    return {
        "strongest": {
            "slot": strongest[0],
            "band": strongest[1]["band"],
            "score": strongest[1]["score"],
        },
        "weakest": weakest_block,
    }


def _detect_per_make_divergence(
    per_make_raw: list[dict[str, Any]] | None,
    ticker_composite_score: int | None,
) -> list[dict[str, Any]]:
    """Per-make volume-band divergence detection. Returns list of divergent makes."""
    if per_make_raw is None or ticker_composite_score is None:
        return []
    out: list[dict[str, Any]] = []
    for entry in per_make_raw:
        mom_pct = _to_float(entry.get("mom_vol_pct"))
        if mom_pct is None:
            continue
        make_band = band_volume_mom(mom_pct)
        make_score = BAND_SCORE[make_band]
        gap = abs(make_score - ticker_composite_score)
        if gap >= 2:
            out.append({
                "make": entry.get("make"),
                "make_volume_band": make_band,
                "make_volume_score": make_score,
                "ticker_composite_score": ticker_composite_score,
                "gap": gap,
            })
    return out


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        emit({"ok": False, "error_type": "bad_stdin", "error": str(exc)})
        return 0

    indicators = cfg.get("leading_indicators_raw") or {}
    per_make_raw = cfg.get("per_make_raw")
    classification = cfg.get("ticker_classification") or "legacy"

    # Extract values
    vol = indicators.get("volume") or {}
    asp = indicators.get("asp") or {}
    msrp = indicators.get("msrp_gap") or {}
    ds = indicators.get("days_supply") or {}
    ms = indicators.get("market_share") or {}
    dom = indicators.get("dom") or {}
    ev = indicators.get("ev_transition")  # may be None

    # Band each underlying metric
    per_metric_bands: dict[str, str | None] = {
        "volume_mom":     _band_value(vol.get("mom_pct"),         band_volume_mom),
        "volume_trend":   _band_value(vol.get("trend_3mo_pct"),   band_volume_trend),
        "asp":            _band_value(asp.get("mom_pct"),         band_asp_mom),
        "msrp_gap":       _band_value(msrp.get("delta_bps"),      band_msrp_gap_delta),
        "days_supply":    _band_value(ds.get("current"),          band_days_supply),
        "market_share":   _band_value(ms.get("delta_bps"),        band_market_share_delta),
        "dom":            _band_value(dom.get("delta_days"),      band_dom_delta),
        "ev_transition":  None,
    }
    if ev is not None:
        per_metric_bands["ev_transition"] = _band_value(ev.get("delta_bps"), band_ev_transition_delta)

    # Composite slots
    composite_slots: dict[str, str | None] = {
        "volume_momentum": composite_volume_momentum(
            per_metric_bands["volume_mom"],
            per_metric_bands["volume_trend"],
            _to_float(vol.get("mom_pct")),
            _to_float(vol.get("trend_3mo_pct")),
        ),
        "pricing_power": composite_pricing_power(
            per_metric_bands["asp"],
            per_metric_bands["msrp_gap"],
            _to_float(msrp.get("current_pct")),
        ),
        "days_supply":   per_metric_bands["days_supply"],
        "market_share":  per_metric_bands["market_share"],
        "dom":           per_metric_bands["dom"],
        "ev_transition": per_metric_bands["ev_transition"],
    }

    # Build per-composite-slot scores
    scores: dict[str, dict[str, Any] | None] = {}
    for slot, band in composite_slots.items():
        if band is None:
            scores[slot] = None
        else:
            scores[slot] = {"band": band, "score": BAND_SCORE[band]}

    reduced = reduce_verdict(composite_slots)
    signal_drivers = _build_signal_drivers(composite_slots, scores)

    # Per-make divergence (on volume only, per plan)
    ticker_vol_score = (
        scores.get("volume_momentum", {}).get("score") if scores.get("volume_momentum") else None
    )
    per_make_divergence = _detect_per_make_divergence(per_make_raw, ticker_vol_score)

    out = {
        "ok": True,
        "ticker_classification": classification,
        "per_metric_bands": per_metric_bands,
        "composite_slots": composite_slots,
        "verdict": reduced["verdict"],
        "scores": scores,
        "mean_score": reduced["mean_score"],
        "n_bullish": reduced["n_bullish"],
        "n_bearish": reduced["n_bearish"],
        "rationale": reduced["rationale"],
        "signal_drivers": signal_drivers,
        "per_make_divergence": per_make_divergence,
    }
    if reduced.get("reason"):
        out["reason"] = reduced["reason"]

    emit(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
