#!/usr/bin/env python3
"""
compute_regional_heatmap.py — Per-state aggregation for a single make (and
optional model). Reads a parsed get_sold_summary output where the call was
filtered by `make=<make>` (and optionally `model=<model>`) with
`summary_by="state"` and no `state` filter — yielding one row per state×month
for the requested make.

Computes per state:
  - Total sold_count for the make
  - Volume rank (1 = highest)
  - % of national volume
  - Weighted-mean avg_sale_price (weight = sold_count)
  - Weighted-mean avg_dom (weight = sold_count)
  - price_vs_national_ratio = state_avg_price / national_avg_price

Usage:
  compute_regional_heatmap.py \\
    --current <parse_sold_summary path>         # required
    --make    <Make>                            # required (metadata + scope)
    [--model  <Model>]                          # optional metadata
    [--prior  <parse_sold_summary path>]        # optional dual-period (not used currently)
    [--top-n  10]                               # default 10 for top + bottom slices

Output JSON on stdout:
  {
    "ok": true,
    "scope": {"make": "<Make>", "model": "<Model>" | null, "top_n": <int>},
    "national": {
      "total_volume":   <int>,
      "avg_sale_price": <float | null>,
      "avg_dom":        <float | null>,
      "states_seen":    <int>
    },
    "states": [
      {
        "rank":                    <int>,
        "state":                   "<STATE>",
        "sold_count":              <int>,
        "pct_of_national_volume":  <float>,
        "avg_sale_price":          <float | null>,
        "avg_dom":                 <float | null>,
        "price_vs_national_ratio": <float | null>
      },
      ...
    ],
    "top_volume_states":   [<STATE>, ...],   # top-N
    "bottom_growth_markets": [<STATE>, ...]  # bottom-N (low-volume large markets)
  }

  On failure: {"ok": false, "error_type": "...", "error": "..."}
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
        sys.stderr.write(f"compute_regional_heatmap: --{label} is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"compute_regional_heatmap: cannot read {label} {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"compute_regional_heatmap: {label} {path_str!r} not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"compute_regional_heatmap: {label} payload must be a JSON object\n")
        raise SystemExit(1)
    if payload.get("ok") is False:
        sys.stderr.write(
            f"compute_regional_heatmap: {label} parser reported ok=false: "
            f"{payload.get('error_type')!r} — {payload.get('error')!r}\n"
        )
        raise SystemExit(1)
    return payload


def main(argv: list[str]) -> int:
    current_path = _arg_value(argv, "--current")
    make = (_arg_value(argv, "--make") or "").strip()
    model = (_arg_value(argv, "--model") or "").strip() or None
    top_n = _arg_int(argv, "--top-n", 10)

    if not make:
        sys.stderr.write("compute_regional_heatmap: --make is required\n")
        return 1

    try:
        current = _load_parsed(current_path, "current")
    except SystemExit:
        return 1

    rows = current.get("rows") or []

    state_volume: dict[str, int] = defaultdict(int)
    state_price_w: dict[str, float] = defaultdict(float)
    state_price_sumw: dict[str, float] = defaultdict(float)
    state_dom_w: dict[str, float] = defaultdict(float)
    state_dom_sumw: dict[str, float] = defaultdict(float)

    for row in rows:
        if not isinstance(row, dict):
            continue
        row_make = str(row.get("make") or "").strip()
        if row_make.lower() != make.lower():
            continue
        if model is not None:
            row_model = str(row.get("model") or "").strip()
            if row_model.lower() != model.lower():
                continue
        state = str(row.get("state") or "").strip().upper()
        if not state:
            continue
        sc = row.get("sold_count")
        try:
            sc_int = int(sc) if sc is not None else 0
        except (TypeError, ValueError):
            continue
        if sc_int <= 0:
            continue
        state_volume[state] += sc_int
        price = row.get("average_sale_price")
        if price is not None:
            try:
                price_f = float(price)
                state_price_w[state] += price_f * sc_int
                state_price_sumw[state] += sc_int
            except (TypeError, ValueError):
                pass
        dom = row.get("average_days_on_market")
        if dom is not None:
            try:
                dom_f = float(dom)
                state_dom_w[state] += dom_f * sc_int
                state_dom_sumw[state] += sc_int
            except (TypeError, ValueError):
                pass

    if not state_volume:
        json.dump({
            "ok": False,
            "error_type": "no_data_for_make",
            "error": f"No rows match make={make!r} (model={model!r}) in current period",
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    national_total = sum(state_volume.values())
    national_price_w = sum(state_price_w.values())
    national_price_sumw = sum(state_price_sumw.values())
    national_dom_w = sum(state_dom_w.values())
    national_dom_sumw = sum(state_dom_sumw.values())

    national_avg_price = (
        national_price_w / national_price_sumw
        if national_price_sumw > 0 else None
    )
    national_avg_dom = (
        national_dom_w / national_dom_sumw
        if national_dom_sumw > 0 else None
    )

    states_out: list[dict[str, Any]] = []
    for state, vol in state_volume.items():
        avg_price = (
            state_price_w[state] / state_price_sumw[state]
            if state_price_sumw[state] > 0 else None
        )
        avg_dom = (
            state_dom_w[state] / state_dom_sumw[state]
            if state_dom_sumw[state] > 0 else None
        )
        ratio = (
            avg_price / national_avg_price
            if (avg_price is not None and national_avg_price not in (None, 0)) else None
        )
        states_out.append({
            "state": state,
            "sold_count": vol,
            "pct_of_national_volume": round(vol / national_total * 100.0, 4) if national_total > 0 else 0.0,
            "avg_sale_price": round(avg_price, 2) if avg_price is not None else None,
            "avg_dom": round(avg_dom, 2) if avg_dom is not None else None,
            "price_vs_national_ratio": round(ratio, 4) if ratio is not None else None,
        })

    states_out.sort(key=lambda r: r["sold_count"], reverse=True)
    for i, row in enumerate(states_out, start=1):
        row["rank"] = i

    top_volume_states = [s["state"] for s in states_out[:top_n]]
    bottom_growth_markets = [s["state"] for s in states_out[-top_n:][::-1]] if len(states_out) > top_n else []

    out = {
        "ok": True,
        "scope": {
            "make": make,
            "model": model,
            "top_n": top_n,
        },
        "national": {
            "total_volume": national_total,
            "avg_sale_price": round(national_avg_price, 2) if national_avg_price is not None else None,
            "avg_dom": round(national_avg_dom, 2) if national_avg_dom is not None else None,
            "states_seen": len(states_out),
        },
        "states": states_out,
        "top_volume_states": top_volume_states,
        "bottom_growth_markets": bottom_growth_markets,
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
        sys.stderr.write(f"compute_regional_heatmap: unexpected error: {exc}\n")
        sys.exit(1)
