#!/usr/bin/env python3
"""
compute_dealer_group_leaderboard.py — Merge three parsed get_sold_summary outputs
(volume / DOM / avg-price calls) by `dealership_group_name` and emit a unified
leaderboard with an efficiency score.

Per the existing market-share-analyzer SKILL.md (W3) and the plan's Q2=A,
this script consumes a single period's three calls (no prior-period merge).
Each input was a get_sold_summary call with ranking_dimensions=
"dealership_group_name" and a different ranking_measure (sold_count /
average_days_on_market / average_sale_price). The script aggregates each
input by dealership_group_name (summing sold_count for volume, weighted-mean
for DOM and price), merges the three into one row per group, and emits a
ranked leaderboard.

efficiency_score = sold_count / avg_dom (per existing target SKILL.md:135 —
"higher is better — moves more units faster"). Groups with avg_dom == 0 or
null get efficiency_score = null.

Usage:
  compute_dealer_group_leaderboard.py \\
    --volume     <parse_sold_summary path>    # ranking_measure=sold_count
    --dom        <parse_sold_summary path>    # ranking_measure=average_days_on_market
    --avg-price  <parse_sold_summary path>    # ranking_measure=average_sale_price
    [--user-make <make>]                       # context only (passthrough)
    [--top-n     20]                           # default 20 in the table

Output JSON on stdout:
  {
    "ok": true,
    "scope": {"user_make": "<make>" | null, "top_n": <int>},
    "totals": {"market_total_sold": <int>, "groups_seen": <int>},
    "leaderboard": [
      {
        "rank_by_volume":    <int>,
        "dealership_group_name": "<Group>",
        "sold_count":        <int>,
        "market_share_pct":  <float>,
        "avg_dom":           <float | null>,
        "avg_sale_price":    <float | null>,
        "efficiency_score":  <float | null>
      },
      ...
    ],
    "top_volume":     "<Group>" | null,
    "top_efficiency": "<Group>" | null,
    "top_avg_price":  "<Group>" | null
  }

  On failure: {"ok": false, "error_type": "...", "error": "..."}

Aggregation semantics:
  - sold_count: simple sum across rows for the group (rows arrive bucketed by
    state; aggregation gives national-level group volume).
  - avg_dom:    weighted mean by sold_count (each row contributes its avg_dom
    weighted by its sold_count). Same for avg_sale_price.
  - When a group appears in only some of the three inputs, missing fields
    render as null in the leaderboard row.
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
        sys.stderr.write(f"compute_dealer_group_leaderboard: --{label} is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"compute_dealer_group_leaderboard: cannot read {label} {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"compute_dealer_group_leaderboard: {label} {path_str!r} not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"compute_dealer_group_leaderboard: {label} payload must be a JSON object\n")
        raise SystemExit(1)
    if payload.get("ok") is False:
        sys.stderr.write(
            f"compute_dealer_group_leaderboard: {label} parser reported ok=false: "
            f"{payload.get('error_type')!r} — {payload.get('error')!r}\n"
        )
        raise SystemExit(1)
    return payload


def _aggregate_volume(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Sum sold_count by group across rows."""
    out: dict[str, int] = defaultdict(int)
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        group = row.get("dealership_group_name")
        if not group:
            continue
        sc = row.get("sold_count")
        try:
            sc_int = int(sc) if sc is not None else 0
        except (TypeError, ValueError):
            continue
        if sc_int <= 0:
            continue
        out[str(group)] += sc_int
    return dict(out)


def _aggregate_weighted(rows: list[dict[str, Any]], measure_field: str) -> dict[str, float | None]:
    """Weighted-mean of `measure_field` by sold_count, per group. Returns the
    weighted mean per group (or None when total weight is zero)."""
    sum_w: dict[str, float] = defaultdict(float)
    sum_xw: dict[str, float] = defaultdict(float)
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        group = row.get("dealership_group_name")
        if not group:
            continue
        sc = row.get("sold_count")
        try:
            sc_int = int(sc) if sc is not None else 0
        except (TypeError, ValueError):
            continue
        if sc_int <= 0:
            continue
        x = row.get(measure_field)
        if x is None:
            continue
        try:
            x_f = float(x)
        except (TypeError, ValueError):
            continue
        sum_xw[str(group)] += x_f * sc_int
        sum_w[str(group)] += sc_int
    out: dict[str, float | None] = {}
    for g in set(sum_w) | set(sum_xw):
        w = sum_w.get(g, 0.0)
        if w <= 0:
            out[g] = None
        else:
            out[g] = sum_xw.get(g, 0.0) / w
    return out


def main(argv: list[str]) -> int:
    volume_path = _arg_value(argv, "--volume")
    dom_path = _arg_value(argv, "--dom")
    price_path = _arg_value(argv, "--avg-price")
    top_n = _arg_int(argv, "--top-n", 20)
    user_make_raw = _arg_value(argv, "--user-make")
    user_make = (user_make_raw or "").strip() or None

    try:
        volume = _load_parsed(volume_path, "volume")
        dom = _load_parsed(dom_path, "dom")
        price = _load_parsed(price_path, "avg-price")
    except SystemExit:
        return 1

    vol_totals = _aggregate_volume(volume.get("rows") or [])
    dom_means = _aggregate_weighted(dom.get("rows") or [], "average_days_on_market")
    price_means = _aggregate_weighted(price.get("rows") or [], "average_sale_price")

    if not vol_totals:
        json.dump({
            "ok": False,
            "error_type": "no_volume_data",
            "error": "Volume input has no usable dealership_group_name rows",
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    market_total = sum(vol_totals.values())

    leaderboard: list[dict[str, Any]] = []
    for group, sold_count in vol_totals.items():
        avg_dom = dom_means.get(group)
        avg_price = price_means.get(group)
        if avg_dom is not None and avg_dom > 0:
            efficiency_score = round(sold_count / avg_dom, 2)
        else:
            efficiency_score = None
        leaderboard.append({
            "dealership_group_name": group,
            "sold_count": sold_count,
            "market_share_pct": round(sold_count / market_total * 100.0, 4) if market_total > 0 else 0.0,
            "avg_dom": round(avg_dom, 2) if avg_dom is not None else None,
            "avg_sale_price": round(avg_price, 2) if avg_price is not None else None,
            "efficiency_score": efficiency_score,
        })

    leaderboard.sort(key=lambda r: r["sold_count"], reverse=True)
    for i, row in enumerate(leaderboard, start=1):
        row["rank_by_volume"] = i

    visible = leaderboard[:top_n] if top_n > 0 else leaderboard

    top_volume = leaderboard[0]["dealership_group_name"] if leaderboard else None

    eligible_eff = [r for r in leaderboard if r["efficiency_score"] is not None]
    top_efficiency = (
        max(eligible_eff, key=lambda r: r["efficiency_score"])["dealership_group_name"]
        if eligible_eff else None
    )

    eligible_price = [r for r in leaderboard if r["avg_sale_price"] is not None]
    top_avg_price = (
        max(eligible_price, key=lambda r: r["avg_sale_price"])["dealership_group_name"]
        if eligible_price else None
    )

    out = {
        "ok": True,
        "scope": {
            "user_make": user_make,
            "top_n": top_n,
        },
        "totals": {
            "market_total_sold": market_total,
            "groups_seen": len(leaderboard),
        },
        "leaderboard": visible,
        "all_groups_count": len(leaderboard),
        "top_volume": top_volume,
        "top_efficiency": top_efficiency,
        "top_avg_price": top_avg_price,
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
        sys.stderr.write(f"compute_dealer_group_leaderboard: unexpected error: {exc}\n")
        sys.exit(1)
