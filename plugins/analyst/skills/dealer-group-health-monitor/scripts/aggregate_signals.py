#!/usr/bin/env python3
"""
aggregate_signals.py — Reduce per-metric values to a single headline verdict.

Stdin JSON:  the `mom` and `active_health` blocks from compute_group_stats.
  {
    "mom": {"volume_pct": ..., "asp_pct": ..., "dom_delta": ..., "efficiency_pct": ...},
    "active_health": {
      "used": {"days_supply": ...} | null,
      "new":  {"days_supply": ...} | null,
      ...
    }
  }

Stdout JSON:
  {
    "verdict": "BULLISH" | "BEARISH" | "NEUTRAL" | "MIXED" | null,
    "scores": {
      "volume_mom":       {"value": ..., "band": "...", "score": ...} | null,
      ...
    },
    "mean_score": ...,
    "n_bullish": ...,
    "n_bearish": ...,
    "rationale": "..."
  }

Banding rules (half-open intervals to remove AMB-04 ambiguity from the
original Signal Logic table). NEUTRAL is the closed interval [LOW, HIGH];
the adjacent BULLISH or CAUTION band is open on the side that touches
NEUTRAL. CAUTION is closed on the BEARISH-touching side.

Reduction rule (resolves AMB-01):
  1. Skip metrics with null values.
  2. mean = mean(scores) across contributing metrics.
  3. n_bullish, n_bearish from contributing metrics.
  4. First-match-wins:
     - n_bullish > 0 AND n_bearish > 0 → MIXED
     - mean ≥ +1.0 AND n_bearish == 0  → BULLISH
     - mean ≤ -1.0 AND n_bullish == 0  → BEARISH
     - else                            → NEUTRAL
  5. If no metrics contribute → verdict null.
"""

from __future__ import annotations

import json
import sys
from typing import Any


# Per-band scores
BAND_SCORE = {
    "BULLISH": +2,
    "NEUTRAL":  0,
    "CAUTION": -1,
    "BEARISH": -2,
}


# ─── Band classifiers ──────────────────────────────────────────────────────
#
# Each function returns one of "BULLISH" | "NEUTRAL" | "CAUTION" | "BEARISH"
# given a numeric value. Boundary semantics: NEUTRAL is closed on both ends;
# the adjacent BULLISH or CAUTION band is open on the touching side; CAUTION
# is closed on the BEARISH-touching side.


def band_volume_mom(x: float) -> str:
    """Volume MoM (higher better). Thresholds: -3, -1, +3.
    BULLISH: x > +3
    NEUTRAL: -1 ≤ x ≤ +3
    CAUTION: -3 ≤ x < -1
    BEARISH: x < -3
    """
    if x > 3.0:
        return "BULLISH"
    if x >= -1.0:
        return "NEUTRAL"
    if x >= -3.0:
        return "CAUTION"
    return "BEARISH"


def band_asp_mom(x: float) -> str:
    """ASP MoM (higher better). Thresholds: -3, -1, +1.
    BULLISH: x > +1
    NEUTRAL: -1 ≤ x ≤ +1
    CAUTION: -3 ≤ x < -1
    BEARISH: x < -3
    """
    if x > 1.0:
        return "BULLISH"
    if x >= -1.0:
        return "NEUTRAL"
    if x >= -3.0:
        return "CAUTION"
    return "BEARISH"


def band_dom_delta(x: float) -> str:
    """DOM Change (lower better, units = days). Thresholds: -2, +2, +5.
    BULLISH: x < -2
    NEUTRAL: -2 ≤ x ≤ +2
    CAUTION: +2 < x ≤ +5
    BEARISH: x > +5
    """
    if x < -2.0:
        return "BULLISH"
    if x <= 2.0:
        return "NEUTRAL"
    if x <= 5.0:
        return "CAUTION"
    return "BEARISH"


def band_days_supply_used(x: float) -> str:
    """Days Supply Used (lower better). Thresholds: 35, 55, 75.
    BULLISH: x < 35
    NEUTRAL: 35 ≤ x ≤ 55
    CAUTION: 55 < x ≤ 75
    BEARISH: x > 75
    """
    if x < 35.0:
        return "BULLISH"
    if x <= 55.0:
        return "NEUTRAL"
    if x <= 75.0:
        return "CAUTION"
    return "BEARISH"


def band_days_supply_new(x: float) -> str:
    """Days Supply New (lower better). Thresholds: 50, 80, 100.
    BULLISH: x < 50
    NEUTRAL: 50 ≤ x ≤ 80
    CAUTION: 80 < x ≤ 100
    BEARISH: x > 100
    """
    if x < 50.0:
        return "BULLISH"
    if x <= 80.0:
        return "NEUTRAL"
    if x <= 100.0:
        return "CAUTION"
    return "BEARISH"


def band_efficiency_mom(x: float) -> str:
    """Efficiency MoM (higher better). Thresholds: -5, -2, +5.
    BULLISH: x > +5
    NEUTRAL: -2 ≤ x ≤ +5
    CAUTION: -5 ≤ x < -2
    BEARISH: x < -5
    """
    if x > 5.0:
        return "BULLISH"
    if x >= -2.0:
        return "NEUTRAL"
    if x >= -5.0:
        return "CAUTION"
    return "BEARISH"


# ─── Score record builder ──────────────────────────────────────────────────


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


# ─── Reducer ───────────────────────────────────────────────────────────────


def reduce_verdict(scores: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    """Apply the headline-verdict reduction rule to a dict of scored metrics.

    Returns {verdict, mean_score, n_bullish, n_bearish, rationale}.
    """
    contributing = [s for s in scores.values() if s is not None]
    if not contributing:
        return {
            "verdict": None,
            "mean_score": None,
            "n_bullish": 0,
            "n_bearish": 0,
            "rationale": None,
            "reason": "no_scoreable_signals",
        }
    raw_scores = [s["score"] for s in contributing]
    mean_score = sum(raw_scores) / len(raw_scores)
    n_bullish = sum(1 for s in contributing if s["band"] == "BULLISH")
    n_bearish = sum(1 for s in contributing if s["band"] == "BEARISH")

    # First-match-wins
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


def _build_rationale(scores: dict[str, dict[str, Any] | None], verdict: str | None) -> str:
    """Generate a one-sentence rationale describing which metrics drove the
    verdict. The renderer can use this verbatim or extend it."""
    if verdict is None:
        return "No scoreable signals — all metric values are null."
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


# ─── Main ───────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)}, sys.stdout)
        sys.stdout.write("\n")
        return 0

    mom = cfg.get("mom") or {}
    active = cfg.get("active_health") or {}
    used_h = active.get("used") if isinstance(active.get("used"), dict) else None
    new_h  = active.get("new")  if isinstance(active.get("new"),  dict) else None

    scores = {
        "volume_mom":       _score_metric(mom.get("volume_pct"),     band_volume_mom),
        "asp_mom":          _score_metric(mom.get("asp_pct"),        band_asp_mom),
        "dom_delta":        _score_metric(mom.get("dom_delta"),      band_dom_delta),
        "days_supply_used": _score_metric(used_h.get("days_supply") if used_h else None,
                                          band_days_supply_used),
        "days_supply_new":  _score_metric(new_h.get("days_supply") if new_h else None,
                                          band_days_supply_new),
        "efficiency_mom":   _score_metric(mom.get("efficiency_pct"), band_efficiency_mom),
    }

    reduced = reduce_verdict(scores)

    out = {
        "ok": True,
        "verdict":     reduced["verdict"],
        "scores":      scores,
        "mean_score":  reduced["mean_score"],
        "n_bullish":   reduced["n_bullish"],
        "n_bearish":   reduced["n_bearish"],
        "rationale":   reduced["rationale"],
    }
    if "reason" in reduced:
        out["reason"] = reduced["reason"]

    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
