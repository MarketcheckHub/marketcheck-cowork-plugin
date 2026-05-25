#!/usr/bin/env python3
"""
aggregate_signals.py — Translate per-make / per-segment / per-dealer-group
findings into per-ticker BULLISH / BEARISH / NEUTRAL / CAUTION investment
signals. Reads any of the compute_*.py outputs and emits a ticker-level
rollup with per-ticker share %, share-change bps, volume-change %, verdict
band, and contributing-makes attribution.

Modes:
  --mode brand              # input: compute_brand_share.py output
  --mode segment            # input: compute_segment_conquest.py output
  --mode dealer-group       # input: compute_dealer_group_leaderboard.py output
  --mode ev                 # input: compute_ev_penetration.py output (ev_brand_share)
  --mode regional           # input: compute_regional_heatmap.py output

Verdict-band rules (§references/signal-aggregation.md):

  Per-make / per-component verdict:
    BULLISH  : share_change_bps >= +30 AND volume_change_pct >= 0
               OR share_change_bps >= +50 regardless of volume.
    BEARISH  : share_change_bps <= -30 AND volume_change_pct <= 0
               OR share_change_bps <= -50 regardless of volume.
    CAUTION  : share gaining > +10 bps but volume down >= 5%; OR
               volume down >= 10% regardless of share; OR data quality
               degraded (insufficient_data flag set on the row).
    NEUTRAL  : within +/- 30 bps AND volume change within +/- 5%; OR
               insufficient data to classify (no prior share).

  Per-ticker headline rollup:
    - Single make ticker (TSLA, RIVN, LCID, TM-Toyota-only-rolled, etc.):
      inherit the per-make verdict.
    - Multi-make ticker (GM = Chevy + GMC + Buick + Cadillac):
      compute sold_count-weighted majority verdict. If a strict majority
      (> 50% of volume) agrees on BULLISH or BEARISH, that's the headline.
      If majority is NEUTRAL, headline is NEUTRAL. Otherwise headline is
      CAUTION (mixed-make divergence is itself a signal).

Usage:
  aggregate_signals.py \\
    --mode brand \\
    --input <compute_brand_share output JSON path> \\
    --mapping <references/ticker-mapping.md as JSON path; optional> \\
    [--tracked-tickers <ticker1,ticker2,...>]   # highlight subset
    [--focus oem|dealer_groups|ev_transition|lending|general]

The ticker mapping is built in (constants below) and matches
references/ticker-mapping.md. The --mapping flag exists for override; if
unset the built-in mapping is used.

Output JSON on stdout:
  {
    "ok": true,
    "mode": "<mode>",
    "scope": {
      "tracked_tickers": [<ticker>, ...] | null,
      "focus":           "<focus>" | null
    },
    "tickers": [
      {
        "ticker":              "<TICKER>",
        "audience_class":      "oem" | "dealer_group",
        "makes_contributing":  ["<Make1>", "<Make2>"],
        "current_sold_count":  <int>,
        "current_share_pct":   <float>,
        "prior_share_pct":     <float | null>,
        "share_change_bps":    <float | null>,
        "volume_change_pct":   <float | null>,
        "verdict":             "BULLISH" | "BEARISH" | "NEUTRAL" | "CAUTION",
        "verdict_reason":      "<short explanation>",
        "is_tracked":          <bool>,
        "per_make_breakdown":  [
          {"make": "<Make>", "share_change_bps": <float>,
           "volume_change_pct": <float | null>, "verdict": "<BAND>"},
          ...
        ]
      },
      ...
    ],
    "headline_rollup": {
      "top_bullish":    [<ticker>, <ticker>, <ticker>],
      "top_bearish":    [<ticker>, <ticker>, <ticker>],
      "tracked_signals": [{"ticker": "<T>", "verdict": "<BAND>"}, ...] | null
    }
  }

  On failure: {"ok": false, "error_type": "...", "error": "..."}
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# Built-in OEM ticker mapping. Mirrors references/ticker-mapping.md and
# plugins/analyst/commands/onboarding.md Step 4. Keep these three sources in
# lockstep when the mapping changes.
OEM_TICKERS: dict[str, list[str]] = {
    "F":     ["Ford", "Lincoln"],
    "GM":    ["Chevrolet", "GMC", "Buick", "Cadillac"],
    "TM":    ["Toyota", "Lexus"],
    "HMC":   ["Honda", "Acura"],
    "STLA":  ["Chrysler", "Dodge", "Jeep", "Ram", "Fiat", "Alfa Romeo", "Maserati"],
    "TSLA":  ["Tesla"],
    "RIVN":  ["Rivian"],
    "LCID":  ["Lucid"],
    "HYMTF": ["Hyundai", "Kia", "Genesis"],
    "NSANY": ["Nissan", "Infiniti"],
    "MBGAF": ["Mercedes-Benz"],
    "BMWYY": ["BMW", "MINI", "Rolls-Royce"],
    "VWAGY": ["Volkswagen", "Audi", "Porsche", "Lamborghini", "Bentley"],
}

# Dealer-group ticker mapping. Names match get_sold_summary's
# dealership_group_name enum exactly (case-sensitive substring match).
DEALER_GROUP_TICKERS: dict[str, list[str]] = {
    "AN":   ["AutoNation"],
    "LAD":  ["Lithia Motors", "Lithia"],
    "PAG":  ["Penske Automotive", "Penske"],
    "SAH":  ["Sonic Automotive", "Sonic"],
    "GPI":  ["Group 1 Automotive", "Group 1"],
    "ABG":  ["Asbury Automotive", "Asbury"],
    "KMX":  ["CarMax"],
    "CVNA": ["Carvana"],
}

# Reverse maps: make -> ticker, group_name -> ticker
_MAKE_TO_OEM_TICKER: dict[str, str] = {}
for _ticker, _makes in OEM_TICKERS.items():
    for _make in _makes:
        _MAKE_TO_OEM_TICKER[_make.lower()] = _ticker

# Verdict-band thresholds — full grid in references/signal-aggregation.md.
BULLISH_BPS_STRONG = 50.0
BULLISH_BPS_WITH_VOLUME = 30.0
BEARISH_BPS_STRONG = -50.0
BEARISH_BPS_WITH_VOLUME = -30.0
CAUTION_GAINING_BPS = 10.0
CAUTION_VOLUME_DROP_PCT = -5.0
CAUTION_VOLUME_DROP_SEVERE_PCT = -10.0
NEUTRAL_BPS_BAND = 30.0
NEUTRAL_VOLUME_BAND_PCT = 5.0


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _arg_multi(argv: list[str], flag: str) -> list[str]:
    raw = _arg_value(argv, flag)
    if raw is None:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _make_to_oem_ticker(make: str | None) -> str | None:
    if not make:
        return None
    return _MAKE_TO_OEM_TICKER.get(str(make).strip().lower())


def _group_to_ticker(group_name: str | None) -> str | None:
    if not group_name:
        return None
    haystack = str(group_name).strip().lower()
    for ticker, names in DEALER_GROUP_TICKERS.items():
        for name in names:
            if name.lower() in haystack:
                return ticker
    return None


def _classify_make(share_bps: float | None, volume_pct: float | None,
                   insufficient_data: bool = False) -> tuple[str, str]:
    """Return (verdict_band, short_reason)."""
    if insufficient_data or share_bps is None:
        return "NEUTRAL", "insufficient_data_for_verdict"
    if share_bps >= BULLISH_BPS_STRONG:
        return "BULLISH", f"share_change_bps={share_bps:.0f} >= +{BULLISH_BPS_STRONG:.0f}"
    if share_bps <= BEARISH_BPS_STRONG:
        return "BEARISH", f"share_change_bps={share_bps:.0f} <= {BEARISH_BPS_STRONG:.0f}"
    vol = volume_pct if volume_pct is not None else 0.0
    if share_bps >= BULLISH_BPS_WITH_VOLUME and vol >= 0:
        return "BULLISH", f"share_change_bps={share_bps:.0f} and volume up"
    if share_bps <= BEARISH_BPS_WITH_VOLUME and vol <= 0:
        return "BEARISH", f"share_change_bps={share_bps:.0f} and volume down"
    if share_bps > CAUTION_GAINING_BPS and vol <= CAUTION_VOLUME_DROP_PCT:
        return "CAUTION", "share_gain_with_volume_drop"
    if vol <= CAUTION_VOLUME_DROP_SEVERE_PCT:
        return "CAUTION", f"volume_change_pct={vol:.1f}%"
    if abs(share_bps) <= NEUTRAL_BPS_BAND and abs(vol) <= NEUTRAL_VOLUME_BAND_PCT:
        return "NEUTRAL", f"within +/-{NEUTRAL_BPS_BAND:.0f} bps and +/-{NEUTRAL_VOLUME_BAND_PCT:.0f}%"
    return "NEUTRAL", "default_band"


def _rollup_ticker_verdict(per_make: list[dict[str, Any]]) -> tuple[str, str]:
    """Weighted-majority rollup across the makes belonging to a single ticker.

    Returns (headline_verdict, reason).
    """
    if not per_make:
        return "NEUTRAL", "no_makes"
    if len(per_make) == 1:
        v = per_make[0]
        return v["verdict"], f"single_make_{v['make']}"
    total_vol = sum(m.get("current_sold_count") or 0 for m in per_make)
    if total_vol <= 0:
        return "NEUTRAL", "zero_total_volume"
    bucket: dict[str, int] = defaultdict(int)
    for m in per_make:
        sc = m.get("current_sold_count") or 0
        bucket[m["verdict"]] += sc
    # Determine majority (>50% of total).
    majority_verdict: str | None = None
    for verdict, vol in bucket.items():
        if vol > total_vol * 0.5:
            majority_verdict = verdict
            break
    if majority_verdict == "BULLISH":
        return "BULLISH", "majority_makes_bullish"
    if majority_verdict == "BEARISH":
        return "BEARISH", "majority_makes_bearish"
    if majority_verdict == "NEUTRAL":
        return "NEUTRAL", "majority_makes_neutral"
    if majority_verdict == "CAUTION":
        return "CAUTION", "majority_makes_caution"
    # No strict majority — mixed-make ticker, divergence is a signal.
    return "CAUTION", "mixed_make_divergence"


def _aggregate_brand_share(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Aggregate compute_brand_share.makes[] into per-ticker rows."""
    makes_rows = data.get("makes") or []
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in makes_rows:
        ticker = _make_to_oem_ticker(row.get("make"))
        if ticker is None:
            continue
        verdict, reason = _classify_make(
            row.get("share_change_bps"),
            row.get("volume_change_pct"),
        )
        by_ticker[ticker].append({
            "make": row.get("make"),
            "current_sold_count": row.get("current_sold_count") or 0,
            "current_share_pct": row.get("current_share_pct") or 0.0,
            "prior_share_pct": row.get("prior_share_pct"),
            "share_change_bps": row.get("share_change_bps"),
            "volume_change_pct": row.get("volume_change_pct"),
            "verdict": verdict,
            "reason": reason,
        })
    return _emit_tickers(by_ticker, audience_class="oem")


def _aggregate_segment(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Aggregate compute_segment_conquest.models[] into per-ticker rows."""
    model_rows = data.get("models") or []
    # First, roll up per-(make) across model rows.
    per_make: dict[str, dict[str, Any]] = {}
    for row in model_rows:
        m = row.get("make")
        if not m:
            continue
        agg = per_make.setdefault(m, {
            "make": m,
            "current_sold_count": 0,
            "current_share_pct": 0.0,
            "prior_share_pct": 0.0,
            "share_change_bps": 0.0,
            "volume_change_pct": None,
            "_models_count": 0,
        })
        agg["current_sold_count"] += row.get("current_sold_count") or 0
        agg["current_share_pct"] += row.get("current_share_pct") or 0.0
        agg["prior_share_pct"] += row.get("prior_share_pct") or 0.0
        agg["share_change_bps"] += row.get("share_change_bps") or 0.0
        agg["_models_count"] += 1
    # Recompute share_change_bps and volume_change_pct at the per-make level
    # using accumulated current_share - prior_share for stability.
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for make, agg in per_make.items():
        share_bps = (agg["current_share_pct"] - agg["prior_share_pct"]) * 100.0
        vol_pct = None
        verdict, reason = _classify_make(share_bps, vol_pct)
        ticker = _make_to_oem_ticker(make)
        if ticker is None:
            continue
        by_ticker[ticker].append({
            "make": make,
            "current_sold_count": agg["current_sold_count"],
            "current_share_pct": round(agg["current_share_pct"], 4),
            "prior_share_pct": round(agg["prior_share_pct"], 4),
            "share_change_bps": round(share_bps, 2),
            "volume_change_pct": vol_pct,
            "verdict": verdict,
            "reason": reason,
        })
    return _emit_tickers(by_ticker, audience_class="oem")


def _aggregate_dealer_group(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Aggregate compute_dealer_group_leaderboard.leaderboard[] by ticker."""
    rows = data.get("leaderboard") or []
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        ticker = _group_to_ticker(row.get("dealership_group_name"))
        if ticker is None:
            continue
        share_bps = None  # leaderboard is current-period only per W3 design
        vol_pct = None
        verdict, reason = _classify_make(share_bps, vol_pct, insufficient_data=True)
        by_ticker[ticker].append({
            "make": row.get("dealership_group_name"),
            "current_sold_count": row.get("sold_count") or 0,
            "current_share_pct": row.get("market_share_pct") or 0.0,
            "prior_share_pct": None,
            "share_change_bps": None,
            "volume_change_pct": None,
            "avg_dom": row.get("avg_dom"),
            "avg_sale_price": row.get("avg_sale_price"),
            "efficiency_score": row.get("efficiency_score"),
            "verdict": verdict,
            "reason": reason,
        })
    return _emit_tickers(by_ticker, audience_class="dealer_group")


def _aggregate_ev(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Aggregate compute_ev_penetration.ev_brand_share[] into per-ticker rows.

    The ev_brand_share field carries make-level EV / brand-total breakdowns.
    """
    rows = data.get("ev_brand_share") or []
    deltas = data.get("deltas") or {}
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ev_bps = deltas.get("ev_pct_change_bps")  # market-level, not per-make
    for row in rows:
        ticker = _make_to_oem_ticker(row.get("make"))
        if ticker is None:
            continue
        # For EV mode, the per-make signal is the brand's EV penetration
        # (brand_ev_pct) vs the market EV share trend. Translate to bps-like.
        brand_ev_pct = row.get("brand_ev_pct") or 0.0
        share_bps_proxy = (brand_ev_pct - 5.0) * 100.0 if brand_ev_pct else None
        verdict, reason = _classify_make(share_bps_proxy, None)
        by_ticker[ticker].append({
            "make": row.get("make"),
            "current_sold_count": row.get("ev_units") or 0,
            "brand_total_units": row.get("brand_total_units"),
            "brand_ev_pct": brand_ev_pct,
            "current_share_pct": brand_ev_pct,
            "prior_share_pct": None,
            "share_change_bps": None,
            "volume_change_pct": None,
            "verdict": verdict,
            "reason": reason,
        })
    return _emit_tickers(by_ticker, audience_class="oem")


def _aggregate_regional(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Aggregate compute_regional_heatmap.states[] into a single-ticker row.

    Regional heatmap is per-make/-model: a single ticker is in scope. Each
    state row contributes a concentration-risk component but the ticker
    rollup is one entry.
    """
    scope = data.get("scope") or {}
    make = scope.get("make")
    ticker = _make_to_oem_ticker(make)
    if ticker is None:
        return []
    states = data.get("states") or []
    national = data.get("national") or {}
    total_volume = national.get("total_volume") or 0
    # Concentration index: % of national in top-3 states.
    top3 = sorted(states, key=lambda r: -(r.get("sold_count") or 0))[:3]
    top3_pct = sum(r.get("pct_of_national_volume") or 0.0 for r in top3)
    insufficient = total_volume <= 0
    # Verdict: concentration above 50% in top 3 -> CAUTION; otherwise NEUTRAL.
    if insufficient:
        verdict = "NEUTRAL"
        reason = "no_volume"
    elif top3_pct >= 50.0:
        verdict = "CAUTION"
        reason = f"top3_states_concentration={top3_pct:.1f}%"
    else:
        verdict = "NEUTRAL"
        reason = f"diversified_top3={top3_pct:.1f}%"
    return [{
        "ticker": ticker,
        "audience_class": "oem",
        "makes_contributing": [make],
        "current_sold_count": total_volume,
        "current_share_pct": None,
        "prior_share_pct": None,
        "share_change_bps": None,
        "volume_change_pct": None,
        "verdict": verdict,
        "verdict_reason": reason,
        "is_tracked": False,  # set later
        "per_make_breakdown": [],
        "concentration_top3_pct": round(top3_pct, 1),
        "top_states": [r.get("state") for r in top3],
    }]


def _emit_tickers(by_ticker: dict[str, list[dict[str, Any]]],
                  audience_class: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ticker, rows in by_ticker.items():
        if not rows:
            continue
        total_vol = sum(r.get("current_sold_count") or 0 for r in rows)
        # Sum share % across makes for this ticker.
        cur_share = sum(r.get("current_share_pct") or 0.0 for r in rows)
        pri_share = sum(r.get("prior_share_pct") or 0.0 for r in rows
                        if r.get("prior_share_pct") is not None)
        if any(r.get("prior_share_pct") is not None for r in rows):
            share_bps = (cur_share - pri_share) * 100.0
        else:
            share_bps = None
        # Volume change: only computable when all contributing makes have it.
        vols = [r.get("volume_change_pct") for r in rows]
        if vols and all(v is not None for v in vols):
            # Weight by current_sold_count.
            wsum = 0.0
            wn = 0
            for r in rows:
                sc = r.get("current_sold_count") or 0
                vc = r.get("volume_change_pct")
                if sc > 0 and vc is not None:
                    wsum += sc * vc
                    wn += sc
            volume_pct = wsum / wn if wn else None
        else:
            volume_pct = None
        headline_verdict, headline_reason = _rollup_ticker_verdict(rows)
        out.append({
            "ticker": ticker,
            "audience_class": audience_class,
            "makes_contributing": [r["make"] for r in rows],
            "current_sold_count": total_vol,
            "current_share_pct": round(cur_share, 4) if cur_share else None,
            "prior_share_pct": round(pri_share, 4) if pri_share else None,
            "share_change_bps": round(share_bps, 2) if share_bps is not None else None,
            "volume_change_pct": round(volume_pct, 2) if volume_pct is not None else None,
            "verdict": headline_verdict,
            "verdict_reason": headline_reason,
            "is_tracked": False,
            "per_make_breakdown": [
                {"make": r["make"], "share_change_bps": r.get("share_change_bps"),
                 "volume_change_pct": r.get("volume_change_pct"),
                 "verdict": r["verdict"]}
                for r in rows
            ],
        })
    out.sort(key=lambda r: -(r.get("current_sold_count") or 0))
    return out


def _load_input(path_str: str | None) -> dict[str, Any]:
    if not path_str:
        sys.stderr.write("aggregate_signals: --input is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"aggregate_signals: cannot read {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"aggregate_signals: {path_str!r} not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write("aggregate_signals: input payload must be a JSON object\n")
        raise SystemExit(1)
    if payload.get("ok") is False:
        sys.stderr.write(
            f"aggregate_signals: input reported ok=false: "
            f"{payload.get('error_type')!r} - {payload.get('error')!r}\n"
        )
        raise SystemExit(1)
    return payload


MODE_DISPATCH = {
    "brand": _aggregate_brand_share,
    "segment": _aggregate_segment,
    "dealer-group": _aggregate_dealer_group,
    "ev": _aggregate_ev,
    "regional": _aggregate_regional,
}


def main(argv: list[str]) -> int:
    mode = _arg_value(argv, "--mode")
    if mode not in MODE_DISPATCH:
        sys.stderr.write(
            f"aggregate_signals: --mode required, one of {sorted(MODE_DISPATCH)}\n"
        )
        return 1

    try:
        payload = _load_input(_arg_value(argv, "--input"))
    except SystemExit:
        return 1

    tracked = _arg_multi(argv, "--tracked-tickers")
    tracked_set = {t.upper() for t in tracked}
    focus = _arg_value(argv, "--focus")

    tickers = MODE_DISPATCH[mode](payload)
    for t in tickers:
        t["is_tracked"] = t["ticker"] in tracked_set

    bullish = [t["ticker"] for t in tickers if t["verdict"] == "BULLISH"][:3]
    bearish = [t["ticker"] for t in tickers if t["verdict"] == "BEARISH"][:3]
    tracked_signals = None
    if tracked_set:
        tracked_signals = [
            {"ticker": t["ticker"], "verdict": t["verdict"],
             "share_change_bps": t.get("share_change_bps")}
            for t in tickers if t["is_tracked"]
        ]

    out = {
        "ok": True,
        "mode": mode,
        "scope": {
            "tracked_tickers": list(tracked_set) if tracked_set else None,
            "focus": focus,
        },
        "tickers": tickers,
        "headline_rollup": {
            "top_bullish": bullish,
            "top_bearish": bearish,
            "tracked_signals": tracked_signals,
        },
    }
    json.dump(out, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"aggregate_signals: unexpected error: {exc}\n")
        sys.exit(1)
