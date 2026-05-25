#!/usr/bin/env python3
"""
compute_ev_penetration.py — Compute EV / Hybrid penetration rates current vs prior
period, plus brand-level EV share. Reads parsed get_sold_summary outputs from
six MCP calls (per Q3=A): EV current/prior, Hybrid current/prior, Total
current/prior (the latter two with no fuel_type_category filter, used as the
denominator).

Penetration formulas:
  ev_pct       = sum(EV sold)     / sum(Total sold) × 100
  hybrid_pct   = sum(Hybrid sold) / sum(Total sold) × 100
  combined_pct = (sum EV + sum Hybrid) / sum(Total) × 100

Period-over-period delta is in basis points (consistent with W1's bps
convention).

Usage:
  compute_ev_penetration.py \\
    --ev-current     <parse_sold_summary path>      # fuel_type_category=EV
    --ev-prior       <parse_sold_summary path>      # fuel_type_category=EV, prior period
    --hybrid-current <parse_sold_summary path>      # fuel_type_category=Hybrid
    --hybrid-prior   <parse_sold_summary path>      # fuel_type_category=Hybrid, prior period
    --total-current  <parse_sold_summary path>      # NO fuel_type_category — denominator
    --total-prior    <parse_sold_summary path>      # NO fuel_type_category, prior period
    [--top-n 15]                                    # top EV / Hybrid model count (default 15)
    [--state <STATE>]                               # post-aggregation state filter

Output JSON on stdout:
  {
    "ok": true,
    "scope": {"state": "<STATE>" | "national", "top_n": <int>},
    "current_period": {
      "ev_count": <int>, "hybrid_count": <int>, "total_count": <int>,
      "ev_pct":   <float>, "hybrid_pct": <float>, "combined_pct": <float>
    },
    "prior_period": { same shape },
    "deltas": {
      "ev_pct_change_bps":       <float>,
      "hybrid_pct_change_bps":   <float>,
      "combined_pct_change_bps": <float>,
      "ev_volume_change_pct":    <float | null>,
      "hybrid_volume_change_pct":<float | null>
    },
    "top_ev_models":     [{rank, make, model, sold_count, share_of_ev_pct}, ...],
    "top_hybrid_models": [...],
    "ev_brand_share":    [{make, ev_units, brand_total_units, brand_ev_pct}, ...]
  }

  On failure: {"ok": false, "error_type": "...", "error": "..."}

Brand-level EV share: per-make rollup combining EV (numerator: sum EV-call
rows by make) and total (denominator: sum Total-call rows by make), sorted
by ev_units desc. Helps identify which OEMs are most electrified.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _arg_int(argv: list[str], flag: str, default: int) -> int:
    raw = _arg_value(argv, flag)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _load_parsed(path_str: str | None, label: str) -> dict[str, Any]:
    if not path_str:
        sys.stderr.write(f"compute_ev_penetration: --{label} is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"compute_ev_penetration: cannot read {label} {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"compute_ev_penetration: {label} {path_str!r} not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"compute_ev_penetration: {label} payload must be a JSON object\n")
        raise SystemExit(1)
    if payload.get("ok") is False:
        sys.stderr.write(
            f"compute_ev_penetration: {label} parser reported ok=false: "
            f"{payload.get('error_type')!r} — {payload.get('error')!r}\n"
        )
        raise SystemExit(1)
    return payload


def _sum_rows(rows: list[dict[str, Any]], state_filter: str | None) -> int:
    state_norm = (state_filter or "").strip().upper() or None
    total = 0
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if state_norm is not None:
            row_state = str(row.get("state") or "").strip().upper()
            if row_state != state_norm:
                continue
        sc = row.get("sold_count")
        try:
            sc_int = int(sc) if sc is not None else 0
        except (TypeError, ValueError):
            continue
        if sc_int > 0:
            total += sc_int
    return total


def _aggregate_models(rows: list[dict[str, Any]], state_filter: str | None) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = defaultdict(int)
    state_norm = (state_filter or "").strip().upper() or None
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if state_norm is not None:
            row_state = str(row.get("state") or "").strip().upper()
            if row_state != state_norm:
                continue
        make = row.get("make")
        model = row.get("model")
        if not make or not model:
            continue
        sc = row.get("sold_count")
        try:
            sc_int = int(sc) if sc is not None else 0
        except (TypeError, ValueError):
            continue
        if sc_int <= 0:
            continue
        out[(str(make), str(model))] += sc_int
    return dict(out)


def _aggregate_makes(rows: list[dict[str, Any]], state_filter: str | None) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    state_norm = (state_filter or "").strip().upper() or None
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if state_norm is not None:
            row_state = str(row.get("state") or "").strip().upper()
            if row_state != state_norm:
                continue
        make = row.get("make")
        if not make:
            continue
        sc = row.get("sold_count")
        try:
            sc_int = int(sc) if sc is not None else 0
        except (TypeError, ValueError):
            continue
        if sc_int > 0:
            out[str(make)] += sc_int
    return dict(out)


def _period_summary(ev_rows, hybrid_rows, total_rows, state_filter):
    ev_count = _sum_rows(ev_rows, state_filter)
    hybrid_count = _sum_rows(hybrid_rows, state_filter)
    total_count = _sum_rows(total_rows, state_filter)
    if total_count > 0:
        ev_pct = round(ev_count / total_count * 100.0, 4)
        hybrid_pct = round(hybrid_count / total_count * 100.0, 4)
        combined_pct = round((ev_count + hybrid_count) / total_count * 100.0, 4)
    else:
        ev_pct = hybrid_pct = combined_pct = 0.0
    return {
        "ev_count": ev_count,
        "hybrid_count": hybrid_count,
        "total_count": total_count,
        "ev_pct": ev_pct,
        "hybrid_pct": hybrid_pct,
        "combined_pct": combined_pct,
    }


def _top_models(rows: list[dict[str, Any]], state_filter: str | None, top_n: int, total_for_pool: int) -> list[dict[str, Any]]:
    models = _aggregate_models(rows, state_filter)
    sorted_models = sorted(models.items(), key=lambda kv: kv[1], reverse=True)
    out: list[dict[str, Any]] = []
    for i, ((make, model), count) in enumerate(sorted_models[:top_n], start=1):
        share = round(count / total_for_pool * 100.0, 4) if total_for_pool > 0 else 0.0
        out.append({
            "rank": i,
            "make": make,
            "model": model,
            "sold_count": count,
            "share_of_pool_pct": share,
        })
    return out


def main(argv: list[str]) -> int:
    ev_cur_path = _arg_value(argv, "--ev-current")
    ev_pri_path = _arg_value(argv, "--ev-prior")
    hyb_cur_path = _arg_value(argv, "--hybrid-current")
    hyb_pri_path = _arg_value(argv, "--hybrid-prior")
    tot_cur_path = _arg_value(argv, "--total-current")
    tot_pri_path = _arg_value(argv, "--total-prior")
    top_n = _arg_int(argv, "--top-n", 15)
    state_filter = _arg_value(argv, "--state")

    try:
        ev_cur = _load_parsed(ev_cur_path, "ev-current")
        ev_pri = _load_parsed(ev_pri_path, "ev-prior")
        hyb_cur = _load_parsed(hyb_cur_path, "hybrid-current")
        hyb_pri = _load_parsed(hyb_pri_path, "hybrid-prior")
        tot_cur = _load_parsed(tot_cur_path, "total-current")
        tot_pri = _load_parsed(tot_pri_path, "total-prior")
    except SystemExit:
        return 1

    ev_cur_rows = ev_cur.get("rows") or []
    ev_pri_rows = ev_pri.get("rows") or []
    hyb_cur_rows = hyb_cur.get("rows") or []
    hyb_pri_rows = hyb_pri.get("rows") or []
    tot_cur_rows = tot_cur.get("rows") or []
    tot_pri_rows = tot_pri.get("rows") or []

    cur = _period_summary(ev_cur_rows, hyb_cur_rows, tot_cur_rows, state_filter)
    pri = _period_summary(ev_pri_rows, hyb_pri_rows, tot_pri_rows, state_filter)

    if cur["total_count"] == 0:
        json.dump({
            "ok": False,
            "error_type": "no_total_current_data",
            "error": "Total-current period has zero sold_count after filters",
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    deltas = {
        "ev_pct_change_bps": round((cur["ev_pct"] - pri["ev_pct"]) * 100.0, 2),
        "hybrid_pct_change_bps": round((cur["hybrid_pct"] - pri["hybrid_pct"]) * 100.0, 2),
        "combined_pct_change_bps": round((cur["combined_pct"] - pri["combined_pct"]) * 100.0, 2),
        "ev_volume_change_pct": (
            round((cur["ev_count"] - pri["ev_count"]) / pri["ev_count"] * 100.0, 2)
            if pri["ev_count"] > 0 else None
        ),
        "hybrid_volume_change_pct": (
            round((cur["hybrid_count"] - pri["hybrid_count"]) / pri["hybrid_count"] * 100.0, 2)
            if pri["hybrid_count"] > 0 else None
        ),
    }

    top_ev = _top_models(ev_cur_rows, state_filter, top_n, cur["ev_count"])
    top_hybrid = _top_models(hyb_cur_rows, state_filter, top_n, cur["hybrid_count"])

    ev_by_make = _aggregate_makes(ev_cur_rows, state_filter)
    total_by_make = _aggregate_makes(tot_cur_rows, state_filter)
    ev_brand_share: list[dict[str, Any]] = []
    for make, ev_units in ev_by_make.items():
        brand_total = total_by_make.get(make, 0)
        brand_ev_pct = round(ev_units / brand_total * 100.0, 4) if brand_total > 0 else None
        ev_brand_share.append({
            "make": make,
            "ev_units": ev_units,
            "brand_total_units": brand_total,
            "brand_ev_pct": brand_ev_pct,
        })
    ev_brand_share.sort(key=lambda r: r["ev_units"], reverse=True)

    out = {
        "ok": True,
        "scope": {
            "state": (state_filter.strip().upper() if state_filter else "national"),
            "top_n": top_n,
        },
        "current_period": cur,
        "prior_period": pri,
        "deltas": deltas,
        "top_ev_models": top_ev,
        "top_hybrid_models": top_hybrid,
        "ev_brand_share": ev_brand_share[:top_n] if top_n > 0 else ev_brand_share,
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
        sys.stderr.write(f"compute_ev_penetration: unexpected error: {exc}\n")
        sys.exit(1)
