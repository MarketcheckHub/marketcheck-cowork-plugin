#!/usr/bin/env python3
"""
aggregate_signals.py — Reduce per-workflow numeric values to a single
headline verdict on the analyst's BULLISH / BEARISH / NEUTRAL / CAUTION /
MIXED scale.

This is the bridge between the workflow stats engines
(`depreciation_curve.py`, `segment_compare.py`, `brand_retention.py`,
`msrp_parity.py`) and the Ticker Impact Summary in the output template.

Per-metric banding rules are codified in `references/signal-aggregation.md`;
this script is the executable mirror of those tables.

Headline-verdict reduction (per `references/signal-aggregation.md`):
  1. Skip metrics with null values.
  2. mean = mean(scores) across contributing entries.
  3. n_bullish, n_bearish, n_caution from contributing entries.
  4. First-match-wins:
     - n_bullish > 0 AND n_bearish > 0 → MIXED
     - mean >= +1.0 AND n_bearish == 0 → BULLISH
     - mean <= -1.0 AND n_bullish == 0 → BEARISH
     - n_caution > 0 AND n_bullish == 0 AND n_bearish == 0 → CAUTION
     - else → NEUTRAL
  5. No contributors → verdict null + reason "no_scoreable_signals".

Input (stdin JSON), one of four shapes:

  # W1 (single make/model, single ticker)
  {"workflow": "w1",
   "metrics": {
     "monthly_rate_pct":     <float|null>,
     "annualized_rate_pct":  <float|null>,
     "retention_pct_prior":  <float|null>
   }}

  # W2 (per-segment classifications)
  {"workflow": "w2",
   "segments": [
     {"key": "SUV", "price_change_pct": <float>,
      "classification": "appreciating"|"stable"|"soft"|"accelerating_dep"}, ...
   ],
   "dimension": "body_type" | "fuel_type_category"}

  # W3 (per-make rankings)
  {"workflow": "w3",
   "makes": [
     {"make": "Toyota", "retention_pct": <float>,
      "tier": "T1"|"T2"|"T3"|"T4"}, ...
   ]}

  # W5 (per-(make,model) parity rows)
  {"workflow": "w5",
   "rows": [
     {"make_model": "Honda Civic", "make": "Honda",
      "current_pct": <float>,
      "status": "above"|"at"|"below",
      "direction": "flipped_above"|"flipped_below"|"deepening"|"narrowing"|"stable"|null}, ...
   ]}

Output (stdout JSON):
  {
    "ok": true,
    "workflow": "w1"|"w2"|"w3"|"w5",
    "headline_verdict": "BULLISH"|"BEARISH"|"NEUTRAL"|"CAUTION"|"MIXED"|null,
    "per_metric":  { ... } | null,    # W1
    "per_segment": [ ... ] | null,    # W2
    "per_make":    [ ... ] | null,    # W3
    "per_row":     [ ... ] | null,    # W5
    "mean_score":  <float|null>,
    "n_bullish":   <int>,
    "n_bearish":   <int>,
    "n_caution":   <int>,
    "rationale":   "<str>",
    "reason":      "no_scoreable_signals"   (only when verdict is null)
  }
"""

from __future__ import annotations

import json
import sys
from typing import Any


BAND_SCORE = {
    "BULLISH": +2,
    "NEUTRAL":  0,
    "CAUTION": -1,
    "BEARISH": -2,
}


# ─── Band classifiers ──────────────────────────────────────────────────────


def band_monthly_rate(x: float) -> str:
    """W1 monthly_rate_pct (lower better, units = % per month).
    BULLISH:  x < 0.3 (or appreciation — x < 0)
    NEUTRAL:  0.3 <= x < 0.6
    CAUTION:  0.6 <= x < 1.5
    BEARISH:  x >= 1.5
    """
    if x < 0.3:
        return "BULLISH"
    if x < 0.6:
        return "NEUTRAL"
    if x < 1.5:
        return "CAUTION"
    return "BEARISH"


def band_retention_pct(x: float) -> str:
    """W3 retention_pct (higher better, units = %).
    BULLISH (T1):  x >= 98
    NEUTRAL (T2):  95 <= x < 98
    CAUTION (T3):  90 <= x < 95
    BEARISH (T4):  x < 90
    """
    if x >= 98.0:
        return "BULLISH"
    if x >= 95.0:
        return "NEUTRAL"
    if x >= 90.0:
        return "CAUTION"
    return "BEARISH"


def band_price_change(x: float) -> str:
    """W2 price_change_pct (higher better, units = %).
    BULLISH:   x >= +1.0
    NEUTRAL:  -1.0 < x < +1.0
    CAUTION:  -3.0 < x <= -1.0
    BEARISH:   x <= -3.0
    """
    if x >= 1.0:
        return "BULLISH"
    if x > -1.0:
        return "NEUTRAL"
    if x > -3.0:
        return "CAUTION"
    return "BEARISH"


def band_parity(status: str | None, direction: str | None) -> str | None:
    """W5 parity status × direction composite.

    BULLISH:  status == "above" AND direction != "flipped_below"
    NEUTRAL:  status == "at"
    CAUTION:  status == "below" AND direction in {narrowing, stable, null}
    BEARISH:  status == "below" AND direction in {deepening, flipped_below}
              OR status == "above" AND direction == "flipped_below"
    """
    if status is None:
        return None
    if status == "above":
        if direction == "flipped_below":
            return "BEARISH"
        return "BULLISH"
    if status == "at":
        return "NEUTRAL"
    if status == "below":
        if direction in ("deepening", "flipped_below"):
            return "BEARISH"
        # narrowing, stable, or None
        return "CAUTION"
    return None


# ─── Reducer ───────────────────────────────────────────────────────────────


def reduce_verdict(scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Reduce a list of {band, score} records to a single headline verdict."""
    contributing = [s for s in scores if s is not None and s.get("band") is not None]
    if not contributing:
        return {
            "headline_verdict": None,
            "mean_score": None,
            "n_bullish": 0,
            "n_bearish": 0,
            "n_caution": 0,
            "rationale": "No scoreable signals — all metric values are null.",
            "reason": "no_scoreable_signals",
        }
    raw = [s["score"] for s in contributing]
    mean_score = sum(raw) / len(raw)
    n_bullish = sum(1 for s in contributing if s["band"] == "BULLISH")
    n_bearish = sum(1 for s in contributing if s["band"] == "BEARISH")
    n_caution = sum(1 for s in contributing if s["band"] == "CAUTION")

    if n_bullish > 0 and n_bearish > 0:
        verdict = "MIXED"
    elif mean_score >= 1.0 and n_bearish == 0:
        verdict = "BULLISH"
    elif mean_score <= -1.0 and n_bullish == 0:
        verdict = "BEARISH"
    elif n_caution > 0 and n_bullish == 0 and n_bearish == 0:
        verdict = "CAUTION"
    else:
        verdict = "NEUTRAL"

    return {
        "headline_verdict": verdict,
        "mean_score": round(mean_score, 4),
        "n_bullish": n_bullish,
        "n_bearish": n_bearish,
        "n_caution": n_caution,
        "rationale": _rationale(contributing, verdict),
    }


def _rationale(scores: list[dict[str, Any]], verdict: str | None) -> str:
    if verdict is None:
        return "No scoreable signals."
    bullish_keys = [s.get("label", "?") for s in scores if s["band"] == "BULLISH"]
    bearish_keys = [s.get("label", "?") for s in scores if s["band"] == "BEARISH"]
    caution_keys = [s.get("label", "?") for s in scores if s["band"] == "CAUTION"]
    if verdict == "MIXED":
        return f"BULLISH on {', '.join(bullish_keys) or '—'}; BEARISH on {', '.join(bearish_keys) or '—'}."
    if verdict == "BULLISH":
        return f"BULLISH on {', '.join(bullish_keys) or 'aggregate signals'}."
    if verdict == "BEARISH":
        return f"BEARISH on {', '.join(bearish_keys) or 'aggregate signals'}."
    if verdict == "CAUTION":
        return f"CAUTION on {', '.join(caution_keys) or 'aggregate signals'}."
    return "NEUTRAL — no metric crossed BULLISH or BEARISH thresholds."


# ─── Helpers ───────────────────────────────────────────────────────────────


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _score_numeric(label: str, value: Any, band_fn) -> dict[str, Any] | None:
    v = _to_float(value)
    if v is None:
        return None
    band = band_fn(v)
    return {"label": label, "value": v, "band": band, "score": BAND_SCORE[band]}


# ─── Workflow drivers ──────────────────────────────────────────────────────


def _run_w1(cfg: dict[str, Any]) -> dict[str, Any]:
    metrics = cfg.get("metrics") or {}
    scored = [
        _score_numeric("monthly_rate_pct",     metrics.get("monthly_rate_pct"),     band_monthly_rate),
        _score_numeric("annualized_rate_pct",  _annual_to_monthly_band_input(metrics.get("annualized_rate_pct")), band_monthly_rate),
        _score_numeric("retention_pct_prior",  metrics.get("retention_pct_prior"),  band_retention_pct),
    ]
    reduced = reduce_verdict(scored)
    per_metric = {s["label"]: s for s in scored if s is not None}
    return {
        "workflow": "w1",
        "per_metric": per_metric,
        "per_segment": None,
        "per_make": None,
        "per_row": None,
        **reduced,
    }


def _annual_to_monthly_band_input(annual: Any) -> Any:
    """The W1 banding table is anchored on the monthly rate. When the
    annualized rate is passed, convert to its monthly equivalent (÷ 12) so
    the band function reads the same scale. Keeps the band thresholds
    documented in `references/signal-aggregation.md` consistent."""
    v = _to_float(annual)
    if v is None:
        return None
    return v / 12.0


def _run_w2(cfg: dict[str, Any]) -> dict[str, Any]:
    segments = cfg.get("segments") or []
    scored = []
    per_segment = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        v = _to_float(seg.get("price_change_pct"))
        key = str(seg.get("key") or "?")
        if v is None:
            per_segment.append({"key": key, "price_change_pct": None, "classification": seg.get("classification"), "band": None, "score": None})
            continue
        band = band_price_change(v)
        s = {"label": key, "value": v, "band": band, "score": BAND_SCORE[band]}
        scored.append(s)
        per_segment.append({
            "key": key,
            "price_change_pct": v,
            "classification": seg.get("classification"),
            "band": band,
            "score": BAND_SCORE[band],
        })
    reduced = reduce_verdict(scored)
    return {
        "workflow": "w2",
        "per_metric": None,
        "per_segment": per_segment,
        "per_make": None,
        "per_row": None,
        **reduced,
    }


def _run_w3(cfg: dict[str, Any]) -> dict[str, Any]:
    makes = cfg.get("makes") or []
    scored = []
    per_make = []
    for m in makes:
        if not isinstance(m, dict):
            continue
        v = _to_float(m.get("retention_pct"))
        make_name = str(m.get("make") or "?")
        tier = m.get("tier")
        if v is None:
            per_make.append({"make": make_name, "retention_pct": None, "tier": tier, "band": None, "score": None})
            continue
        band = band_retention_pct(v)
        s = {"label": make_name, "value": v, "band": band, "score": BAND_SCORE[band]}
        scored.append(s)
        per_make.append({
            "make": make_name,
            "retention_pct": v,
            "tier": tier,
            "band": band,
            "score": BAND_SCORE[band],
        })
    reduced = reduce_verdict(scored)
    return {
        "workflow": "w3",
        "per_metric": None,
        "per_segment": None,
        "per_make": per_make,
        "per_row": None,
        **reduced,
    }


def _run_w5(cfg: dict[str, Any]) -> dict[str, Any]:
    rows = cfg.get("rows") or []
    scored = []
    per_row = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        mm = str(r.get("make_model") or "?")
        status = r.get("status")
        direction = r.get("direction")
        band = band_parity(status, direction)
        if band is None:
            per_row.append({"make_model": mm, "current_pct": _to_float(r.get("current_pct")), "status": status, "direction": direction, "band": None, "score": None})
            continue
        score = BAND_SCORE[band]
        s = {"label": mm, "value": _to_float(r.get("current_pct")), "band": band, "score": score}
        scored.append(s)
        per_row.append({
            "make_model": mm,
            "make": r.get("make"),
            "current_pct": _to_float(r.get("current_pct")),
            "status": status,
            "direction": direction,
            "band": band,
            "score": score,
        })
    reduced = reduce_verdict(scored)
    return {
        "workflow": "w5",
        "per_metric": None,
        "per_segment": None,
        "per_make": None,
        "per_row": per_row,
        **reduced,
    }


# ─── Main ──────────────────────────────────────────────────────────────────


WORKFLOW_DRIVERS = {
    "w1": _run_w1,
    "w2": _run_w2,
    "w3": _run_w3,
    "w5": _run_w5,
}


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)}, sys.stdout)
        sys.stdout.write("\n")
        return 0

    workflow = (cfg.get("workflow") or "").lower()
    driver = WORKFLOW_DRIVERS.get(workflow)
    if driver is None:
        json.dump({"ok": False, "error_type": "bad_workflow",
                   "error": f"workflow={workflow!r} must be one of {sorted(WORKFLOW_DRIVERS)}"},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    result = driver(cfg)
    out = {"ok": True, **result}
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
