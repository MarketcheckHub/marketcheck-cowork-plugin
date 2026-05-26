#!/usr/bin/env python3
"""
aggregate_signals.py — Band per-metric values; combine into composite slots;
reduce to a single 4-tier verdict (BULLISH / BEARISH / NEUTRAL / MIXED + null).

Reads the slice of `compute_earnings_signals.py` output containing
`leading_indicators_raw` + `per_make_raw` + `ticker_classification`. Emits
per-metric bands, composite slots, scores, verdict + reduction telemetry,
signal drivers, and per-make divergence (for multi-make OEMs).

Banding rules — quarterly thresholds calibrated per Phase 5 §5d, Phase 6
revision OPEN-1. **Boundary semantics: NEUTRAL is the closed interval
[LOW, HIGH]**; the adjacent BULLISH or CAUTION band is open on the side that
touches NEUTRAL. CAUTION is closed on the BEARISH-touching side. The
closed-NEUTRAL convention eliminates "value falls into both bands" ambiguity.

Per-metric bands (8 underlying metrics) — see `references/signal-aggregation.md`
for worked endpoint examples:

  Volume QoQ %       higher better   BULL x>+7    NEUTRAL -3≤x≤+7    CAUTION -7≤x<-3    BEAR x<-7
  Volume YoY %       higher better   BULL x>+5    NEUTRAL -2≤x≤+5    CAUTION -5≤x<-2    BEAR x<-5
  ASP QoQ %          higher better   BULL x>+2    NEUTRAL -1≤x≤+2    CAUTION -3≤x<-1    BEAR x<-3
  MSRP gap Δ bps     higher better   BULL x>+90   NEUTRAL -90≤x≤+90  CAUTION -200≤x<-90 BEAR x<-200
  Days Supply Used   lower  better   BULL x<35    NEUTRAL 35≤x≤55    CAUTION 55<x≤75    BEAR x>75
  Days Supply New    lower  better   BULL x<50    NEUTRAL 50≤x≤80    CAUTION 80<x≤100   BEAR x>100
  DOM Δ days         lower  better   BULL x<-5    NEUTRAL -5≤x≤+5    CAUTION +5<x≤+10   BEAR x>+10
  EV share Δ bps     higher better   BULL x>+100  NEUTRAL -50≤x≤+100 — (no CAUTION)     BEAR x<-50
  Mix Δ pp           higher better   BULL x>+1.0  NEUTRAL -0.5≤x≤+1  CAUTION -1.5≤x<-0.5 BEAR x<-1.5

EV share intentionally omits the CAUTION band per Phase 5 — EV signal swings
sharply (directional thesis), and a CAUTION band would dilute it.

Per-band scores (asymmetric):  BULLISH +2,  NEUTRAL 0,  CAUTION −1,  BEARISH −2

`volume_momentum` composite combiner — combines QoQ + YoY volume bands per
Phase 5 §5d revision OPEN-1:

  | QoQ band  | YoY band       | Composite                                   |
  |-----------|----------------|---------------------------------------------|
  | BULLISH   | BULLISH        | BULLISH                                     |
  | BEARISH   | BEARISH        | BEARISH                                     |
  | positive (QoQ>0) | negative (YoY<0) | CAUTION  (short-term bounce on long-term decline) |
  | negative (QoQ<0) | positive (YoY>0) | CAUTION                                     |
  | otherwise        |                  | NEUTRAL                                     |

  Degradation: when YoY is null (newly-listed ticker — DQ event (m) from
  compute_earnings_signals), volume_momentum becomes the QoQ band alone.

Reducer (first-match-wins) — domain rule from `signal-aggregation.md`:
  1. Skip slots with null score.
  2. mean = mean(scores) across contributing slots.
  3. n_bullish > 0 AND n_bearish > 0 → MIXED
  4. mean ≥ +1.0 AND n_bearish == 0 → BULLISH
  5. mean ≤ -1.0 AND n_bullish == 0 → BEARISH
  6. else → NEUTRAL

  Edge: no contributing slots → verdict null, reason='no_scoreable_signals'.

Per-make divergence (multi-make OEMs only):
  For each entry in per_make_raw, band the make's qoq_vol_pct; compute
  gap = |make_score − ticker_composite_score| where ticker_composite_score =
  scores.volume_momentum.score. If gap ≥ 2, emit the entry. Closes Phase 6 OPEN-2
  default (composite-band divergence + per-axis bands in rationale).

Signal drivers — strongest = slot with highest score; weakest = slot with
lowest score IF that score is non-NEUTRAL (otherwise null per template
fallback C12 in Phase 6).

Output shape:
  {
    "ok": true,
    "ticker_classification": "...",
    "per_metric_bands": {volume_qoq, volume_yoy, asp, msrp_gap, dom,
                         days_supply_used, days_supply_new, ev_share, mix},
                         (values: "BULLISH"|"NEUTRAL"|"CAUTION"|"BEARISH"|null),
    "composite_slots":   {volume_momentum, asp, msrp_gap, dom,
                          days_supply_used, days_supply_new, ev_share, mix},
    "scores":            {<slot>: {"value": ..., "band": ..., "score": ±2|±1|0}|null},
    "verdict":           "BULLISH"|"BEARISH"|"NEUTRAL"|"MIXED"|null,
    "mean_score":        <float>|null,
    "n_bullish":         <int>,
    "n_bearish":         <int>,
    "rationale":         "<string>",
    "reason":            "no_scoreable_signals"  (only when verdict is null),
    "signal_drivers":    {"strongest": {...}|null, "weakest": {...}|null},
    "per_make_divergence": [{make, make_volume_band, make_volume_score,
                              ticker_composite_score, gap, make_qoq_pct,
                              make_yoy_pct}, ...]
  }

Usage:
  echo '<compute_earnings_signals slice>' | python aggregate_signals.py

Exit codes:
  0  always — bad-stdin emits {ok: false, error_type: "bad_stdin"} per SP6
"""

from __future__ import annotations

import json
import sys
from typing import Any


# ─── Per-band scores (asymmetric) ──────────────────────────────────────────

BAND_SCORE = {
    "BULLISH": +2,
    "NEUTRAL":  0,
    "CAUTION": -1,
    "BEARISH": -2,
}


# ─── Band classifiers (closed-NEUTRAL convention) ──────────────────────────


def band_volume_qoq(x: float) -> str:
    """Volume QoQ % (higher better). Thresholds: -7, -3, +7."""
    if x > 7.0:
        return "BULLISH"
    if x >= -3.0:
        return "NEUTRAL"
    if x >= -7.0:
        return "CAUTION"
    return "BEARISH"


def band_volume_yoy(x: float) -> str:
    """Volume YoY % (higher better). Thresholds: -5, -2, +5."""
    if x > 5.0:
        return "BULLISH"
    if x >= -2.0:
        return "NEUTRAL"
    if x >= -5.0:
        return "CAUTION"
    return "BEARISH"


def band_asp_qoq(x: float) -> str:
    """ASP QoQ % (higher better). Thresholds: -3, -1, +2."""
    if x > 2.0:
        return "BULLISH"
    if x >= -1.0:
        return "NEUTRAL"
    if x >= -3.0:
        return "CAUTION"
    return "BEARISH"


def band_msrp_gap_bps(x: float) -> str:
    """MSRP gap Δ bps (higher better). Thresholds: -200, -90, +90."""
    if x > 90.0:
        return "BULLISH"
    if x >= -90.0:
        return "NEUTRAL"
    if x >= -200.0:
        return "CAUTION"
    return "BEARISH"


def band_days_supply_used(x: float) -> str:
    """Days Supply Used (lower better). Thresholds: 35, 55, 75."""
    if x < 35.0:
        return "BULLISH"
    if x <= 55.0:
        return "NEUTRAL"
    if x <= 75.0:
        return "CAUTION"
    return "BEARISH"


def band_days_supply_new(x: float) -> str:
    """Days Supply New (lower better). Thresholds: 50, 80, 100."""
    if x < 50.0:
        return "BULLISH"
    if x <= 80.0:
        return "NEUTRAL"
    if x <= 100.0:
        return "CAUTION"
    return "BEARISH"


def band_dom_delta_days(x: float) -> str:
    """DOM Δ days (lower better). Thresholds: -5, +5, +10."""
    if x < -5.0:
        return "BULLISH"
    if x <= 5.0:
        return "NEUTRAL"
    if x <= 10.0:
        return "CAUTION"
    return "BEARISH"


def band_ev_share_bps(x: float) -> str:
    """EV share Δ bps (higher better). Asymmetric — no CAUTION band per
    Phase 5 §5d rationale (EV signal swings sharply; CAUTION would dilute).
    Thresholds: -50, +100."""
    if x > 100.0:
        return "BULLISH"
    if x >= -50.0:
        return "NEUTRAL"
    return "BEARISH"


def band_mix_pp(x: float) -> str:
    """Mix Δ pp (higher better). Thresholds: -1.5, -0.5, +1.0."""
    if x > 1.0:
        return "BULLISH"
    if x >= -0.5:
        return "NEUTRAL"
    if x >= -1.5:
        return "CAUTION"
    return "BEARISH"


# ─── Helpers ───────────────────────────────────────────────────────────────


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _score_metric(value: Any, band_fn) -> dict[str, Any] | None:
    """Build a {value, band, score} record. Returns None when value is null."""
    v = _to_float(value)
    if v is None:
        return None
    band = band_fn(v)
    return {"value": v, "band": band, "score": BAND_SCORE[band]}


# ─── volume_momentum composite combiner ────────────────────────────────────


def _combine_volume_momentum(
    qoq_score: dict | None, yoy_score: dict | None
) -> dict | None:
    """Combine QoQ + YoY volume bands per Phase 5 §5d revision OPEN-1.

    Degradation: when YoY is null (newly-listed ticker — DQ event (m) from
    compute_earnings_signals), volume_momentum becomes the QoQ band alone.
    Symmetric: when QoQ is null but YoY is present, fall back to YoY-only.
    """
    if qoq_score is None and yoy_score is None:
        return None
    if yoy_score is None:
        # YoY null → degrade to QoQ-only (per C8 in Phase 6 + signal-aggregation.md)
        return {
            "value": {"qoq_pct": qoq_score["value"], "yoy_pct": None},
            "band": qoq_score["band"],
            "score": qoq_score["score"],
            "degraded_to": "qoq_only",
        }
    if qoq_score is None:
        # QoQ null → degrade to YoY-only (defensive — unusual but possible)
        return {
            "value": {"qoq_pct": None, "yoy_pct": yoy_score["value"]},
            "band": yoy_score["band"],
            "score": yoy_score["score"],
            "degraded_to": "yoy_only",
        }

    qoq_band = qoq_score["band"]
    yoy_band = yoy_score["band"]
    qoq_pct = qoq_score["value"]
    yoy_pct = yoy_score["value"]

    if qoq_band == "BULLISH" and yoy_band == "BULLISH":
        composite_band = "BULLISH"
    elif qoq_band == "BEARISH" and yoy_band == "BEARISH":
        composite_band = "BEARISH"
    elif (qoq_pct > 0 and yoy_pct < 0) or (qoq_pct < 0 and yoy_pct > 0):
        # Short-term bounce on long-term decline (or vice versa)
        composite_band = "CAUTION"
    else:
        composite_band = "NEUTRAL"

    return {
        "value": {"qoq_pct": qoq_pct, "yoy_pct": yoy_pct},
        "band": composite_band,
        "score": BAND_SCORE[composite_band],
    }


# ─── Reducer ───────────────────────────────────────────────────────────────


def _build_rationale(scores: dict, verdict: str | None) -> str:
    """One-sentence rationale describing which slots drove the verdict.

    Mirrors dealer-group's `_build_rationale` shape; extended to use composite
    slot names (volume_momentum, etc.)."""
    if verdict is None:
        return "No scoreable signals — all composite slots are null."
    bullish = [k for k, v in scores.items() if v and v["band"] == "BULLISH"]
    bearish = [k for k, v in scores.items() if v and v["band"] == "BEARISH"]
    cautions = [k for k, v in scores.items() if v and v["band"] == "CAUTION"]
    if verdict == "MIXED":
        return f"BULLISH on {', '.join(bullish)}; BEARISH on {', '.join(bearish)}."
    if verdict == "BULLISH":
        return f"BULLISH on {', '.join(bullish) if bullish else 'aggregate signals'}."
    if verdict == "BEARISH":
        return f"BEARISH on {', '.join(bearish) if bearish else 'aggregate signals'}."
    # NEUTRAL
    if cautions:
        return f"NEUTRAL — watch for CAUTION on {', '.join(cautions)}."
    return "NEUTRAL — no metric crossed BULLISH or BEARISH thresholds."


def _reduce_verdict(scores: dict) -> dict[str, Any]:
    """First-match-wins reducer per `references/signal-aggregation.md`."""
    contributing = [s for s in scores.values() if s is not None]
    if not contributing:
        return {
            "verdict": None,
            "mean_score": None,
            "n_bullish": 0,
            "n_bearish": 0,
            "rationale": "No scoreable signals — all composite slots are null.",
            "reason": "no_scoreable_signals",
        }
    raw_scores = [s["score"] for s in contributing]
    mean_score = sum(raw_scores) / len(raw_scores)
    n_bullish = sum(1 for s in contributing if s["band"] == "BULLISH")
    n_bearish = sum(1 for s in contributing if s["band"] == "BEARISH")

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
        "rationale": _build_rationale(scores, verdict),
    }


# ─── Signal drivers ────────────────────────────────────────────────────────


def _find_signal_drivers(
    composite_slots: dict, scores: dict
) -> dict[str, Any]:
    """strongest = slot with highest score (must be non-null).
    weakest = slot with lowest score IF non-NEUTRAL (per template C12 fallback)."""
    contributing = [
        (slot, scores.get(slot))
        for slot in composite_slots
        if scores.get(slot) is not None
    ]
    if not contributing:
        return {"strongest": None, "weakest": None}

    strongest_slot, strongest_score = max(contributing, key=lambda x: x[1]["score"])
    weakest_slot, weakest_score = min(contributing, key=lambda x: x[1]["score"])

    strongest_record = {
        "slot": strongest_slot,
        "band": strongest_score["band"],
        "score": strongest_score["score"],
        "value": strongest_score.get("value"),
    }

    # Suppress weakest when it would be NEUTRAL or BULLISH (no real downside
    # to surface). Per Phase 6 C12 — Bear Case template handles weakest=null.
    if weakest_score["band"] in ("NEUTRAL", "BULLISH"):
        return {"strongest": strongest_record, "weakest": None}

    weakest_record = {
        "slot": weakest_slot,
        "band": weakest_score["band"],
        "score": weakest_score["score"],
        "value": weakest_score.get("value"),
    }
    return {"strongest": strongest_record, "weakest": weakest_record}


# ─── Per-make divergence (multi-make OEMs) ─────────────────────────────────


def _detect_per_make_divergence(
    per_make_raw: list | None, volume_momentum: dict | None
) -> list[dict[str, Any]]:
    """Flag makes whose volume signal diverges sharply from the ticker
    volume_momentum composite. Per Phase 6 OPEN-2 (composite-band gap ≥ 2).

    Returns the rows whose per-make-QoQ-band score differs from the ticker
    composite score by 2 or more. Empty list when per_make_raw is null
    (single-make ticker) or when composite is null."""
    if not per_make_raw or not volume_momentum:
        return []
    ticker_composite_score = volume_momentum.get("score")
    if ticker_composite_score is None:
        return []

    divergences: list[dict[str, Any]] = []
    for row in per_make_raw:
        make_name = row.get("make")
        qoq_pct = _to_float(row.get("qoq_vol_pct"))
        yoy_pct = _to_float(row.get("yoy_vol_pct"))
        if qoq_pct is None:
            continue
        make_band = band_volume_qoq(qoq_pct)
        make_score = BAND_SCORE[make_band]
        gap = abs(make_score - ticker_composite_score)
        if gap >= 2:
            divergences.append({
                "make": make_name,
                "make_volume_band": make_band,
                "make_volume_score": make_score,
                "make_qoq_pct": qoq_pct,
                "make_yoy_pct": yoy_pct,
                "ticker_composite_score": ticker_composite_score,
                "gap": gap,
            })
    return divergences


# ─── Main ───────────────────────────────────────────────────────────────────


def aggregate(cfg: dict[str, Any]) -> dict[str, Any]:
    """Reduce raw leading-indicators to bands + composite slots + 4-tier verdict
    + signal drivers + per-make divergence. Pure callable used by
    `orchestrate.py`; also wrapped by the CLI `main()` below.

    Input shape: `{leading_indicators_raw, per_make_raw, ticker_classification}`.
    Output shape: see module docstring (`ok`, `verdict`, `per_metric_bands`,
    `composite_slots`, `scores`, `mean_score`, `n_bullish`, `n_bearish`,
    `rationale`, `signal_drivers`, `per_make_divergence`, optional `reason`).
    """
    li = cfg.get("leading_indicators_raw") or {}
    per_make_raw = cfg.get("per_make_raw")
    ticker_classification = cfg.get("ticker_classification")

    # ─── Step 1: per-metric bands (8 underlying metrics) ────────────────────
    volume_block = li.get("volume") or {}
    asp_block = li.get("asp") or {}
    msrp_gap_block = li.get("msrp_gap") or {}
    dom_block = li.get("dom") or {}
    days_supply_used_block = li.get("days_supply_used")
    days_supply_new_block = li.get("days_supply_new")
    ev_share_block = li.get("ev_share")
    mix_block = li.get("mix")

    volume_qoq_score = _score_metric(volume_block.get("qoq_pct"), band_volume_qoq)
    volume_yoy_score = _score_metric(volume_block.get("yoy_pct"), band_volume_yoy)
    asp_score = _score_metric(asp_block.get("qoq_pct"), band_asp_qoq)
    msrp_gap_score = _score_metric(msrp_gap_block.get("qoq_delta_bps"), band_msrp_gap_bps)
    dom_score = _score_metric(dom_block.get("qoq_delta_days"), band_dom_delta_days)
    days_supply_used_score = (
        _score_metric((days_supply_used_block or {}).get("current"), band_days_supply_used)
        if days_supply_used_block else None
    )
    days_supply_new_score = (
        _score_metric((days_supply_new_block or {}).get("current"), band_days_supply_new)
        if days_supply_new_block else None
    )
    ev_share_score = (
        _score_metric((ev_share_block or {}).get("qoq_delta_bps"), band_ev_share_bps)
        if ev_share_block else None
    )
    mix_score = (
        _score_metric((mix_block or {}).get("qoq_delta_pp"), band_mix_pp)
        if mix_block else None
    )

    per_metric_bands = {
        "volume_qoq":       volume_qoq_score["band"] if volume_qoq_score else None,
        "volume_yoy":       volume_yoy_score["band"] if volume_yoy_score else None,
        "asp":              asp_score["band"] if asp_score else None,
        "msrp_gap":         msrp_gap_score["band"] if msrp_gap_score else None,
        "dom":              dom_score["band"] if dom_score else None,
        "days_supply_used": days_supply_used_score["band"] if days_supply_used_score else None,
        "days_supply_new":  days_supply_new_score["band"] if days_supply_new_score else None,
        "ev_share":         ev_share_score["band"] if ev_share_score else None,
        "mix":              mix_score["band"] if mix_score else None,
    }

    # ─── Step 2: composite slots ────────────────────────────────────────────
    # volume_momentum combines QoQ + YoY; everything else passes through.
    volume_momentum_score = _combine_volume_momentum(volume_qoq_score, volume_yoy_score)

    # The composite-slot scores (used by reducer + signal-drivers)
    scores: dict[str, dict | None] = {
        "volume_momentum":  volume_momentum_score,
        "asp":              asp_score,
        "msrp_gap":         msrp_gap_score,
        "dom":              dom_score,
        "days_supply_used": days_supply_used_score,
        "days_supply_new":  days_supply_new_score,
        "ev_share":         ev_share_score,
        "mix":              mix_score,
    }

    composite_slots = {slot: (sc["band"] if sc else None) for slot, sc in scores.items()}

    # ─── Step 3: reducer → headline verdict ─────────────────────────────────
    reduced = _reduce_verdict(scores)

    # ─── Step 4: signal drivers ─────────────────────────────────────────────
    signal_drivers = _find_signal_drivers(composite_slots, scores)

    # ─── Step 5: per-make divergence ────────────────────────────────────────
    per_make_divergence = _detect_per_make_divergence(per_make_raw, volume_momentum_score)

    # ─── Assemble output ────────────────────────────────────────────────────
    out: dict[str, Any] = {
        "ok": True,
        "ticker_classification": ticker_classification,
        "per_metric_bands":  per_metric_bands,
        "composite_slots":   composite_slots,
        "scores":            scores,
        "verdict":           reduced["verdict"],
        "mean_score":        reduced["mean_score"],
        "n_bullish":         reduced["n_bullish"],
        "n_bearish":         reduced["n_bearish"],
        "rationale":         reduced["rationale"],
        "signal_drivers":    signal_drivers,
        "per_make_divergence": per_make_divergence,
    }
    if "reason" in reduced:
        out["reason"] = reduced["reason"]
    return out


def main(argv: list[str]) -> int:
    """Thin stdin/stdout wrapper around `aggregate(cfg)`. CLI entry-point."""
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump(
            {"ok": False, "error_type": "bad_stdin", "error": str(exc)},
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 0

    out = aggregate(cfg)
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
