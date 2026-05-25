#!/usr/bin/env python3
"""
compute_segment_conquest.py — Within a single body_type segment, compute per-make
share, identify the segment leader, the user-brand rank/gap, and the fastest
gaining model. Reads two parsed get_sold_summary outputs (current + prior period)
where each call was filtered by body_type=<segment> with ranking_dimensions=
"make,model".

Usage:
  compute_segment_conquest.py \\
    --current      <parse_sold_summary path>     # body_type-filtered
    --prior        <parse_sold_summary path>     # body_type-filtered, prior period
    --body-type    <segment>                     # e.g. "SUV"; metadata only
    [--user-brand  <make>]                       # highlight user's brand
    [--top-n       15]                           # default 15 models in the table
    [--state       <STATE>]                      # post-aggregation state filter

Output JSON on stdout:
  {
    "ok": true,
    "scope": {
      "body_type": "<segment>",
      "state":     "<STATE>" | "national",
      "user_brand": "<make>" | null,
      "top_n":     <int>
    },
    "totals": {
      "current_total": <int>,
      "prior_total":   <int>
    },
    "leader": {
      "make":              "<Make>",
      "share_pct":         <float>,
      "sold_count":        <int>
    } | null,
    "user_brand_rank": <int> | null,
    "user_brand_share_pct": <float> | null,
    "gap_to_leader_units": <int> | null,
    "gap_to_leader_share_pts": <float> | null,
    "fastest_gainer": {
      "make":             "<Make>",
      "model":            "<Model>",
      "share_change_bps": <float>
    } | null,
    "models": [
      {
        "rank": <int>,
        "make": "<Make>",
        "model": "<Model>",
        "current_sold_count": <int>,
        "current_share_pct":  <float>,
        "prior_sold_count":   <int>,
        "prior_share_pct":    <float>,
        "share_change_bps":   <float>,
        "is_user_brand":      <bool>
      },
      ...
    ]
  }

  On failure: {"ok": false, "error_type": "...", "error": "..."}

Per-make and per-(make,model) ranking lives in the same response —
make-level rollup feeds the leader / user-brand-rank fields; model-level
rollup feeds the table and fastest-gainer.
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
        sys.stderr.write(f"compute_segment_conquest: --{label} is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"compute_segment_conquest: cannot read {label} {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"compute_segment_conquest: {label} {path_str!r} not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"compute_segment_conquest: {label} payload must be a JSON object\n")
        raise SystemExit(1)
    if payload.get("ok") is False:
        sys.stderr.write(
            f"compute_segment_conquest: {label} parser reported ok=false: "
            f"{payload.get('error_type')!r} — {payload.get('error')!r}\n"
        )
        raise SystemExit(1)
    return payload


def _aggregate(rows: list[dict[str, Any]], state_filter: str | None) -> tuple[
    dict[str, int], dict[tuple[str, str], int], int
]:
    """Sum sold_count by make and by (make, model). Returns (make_totals,
    model_totals, grand_total)."""
    make_totals: dict[str, int] = defaultdict(int)
    model_totals: dict[tuple[str, str], int] = defaultdict(int)
    grand_total = 0
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
        if not make:
            continue
        sc = row.get("sold_count")
        try:
            sc_int = int(sc) if sc is not None else 0
        except (TypeError, ValueError):
            continue
        if sc_int <= 0:
            continue
        make_totals[str(make)] += sc_int
        if model:
            model_totals[(str(make), str(model))] += sc_int
        grand_total += sc_int
    return dict(make_totals), dict(model_totals), grand_total


def main(argv: list[str]) -> int:
    current_path = _arg_value(argv, "--current")
    prior_path = _arg_value(argv, "--prior")
    body_type = (_arg_value(argv, "--body-type") or "").strip()
    top_n = _arg_int(argv, "--top-n", 15)
    user_brand_raw = _arg_value(argv, "--user-brand")
    user_brand = (user_brand_raw or "").strip() or None
    state_filter = _arg_value(argv, "--state")

    if not body_type:
        sys.stderr.write("compute_segment_conquest: --body-type is required\n")
        return 1

    try:
        current = _load_parsed(current_path, "current")
        prior = _load_parsed(prior_path, "prior")
    except SystemExit:
        return 1

    cur_makes, cur_models, cur_total = _aggregate(current.get("rows") or [], state_filter)
    pri_makes, pri_models, pri_total = _aggregate(prior.get("rows") or [], state_filter)

    if cur_total == 0:
        json.dump({
            "ok": False,
            "error_type": "no_current_data",
            "error": f"Current period has zero sold_count for body_type={body_type!r}",
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    leader: dict[str, Any] | None = None
    if cur_makes:
        top_make, top_count = max(cur_makes.items(), key=lambda kv: kv[1])
        leader = {
            "make": top_make,
            "sold_count": top_count,
            "share_pct": round(top_count / cur_total * 100.0, 4),
        }

    user_brand_rank: int | None = None
    user_brand_share_pct: float | None = None
    gap_to_leader_units: int | None = None
    gap_to_leader_share_pts: float | None = None
    if user_brand is not None:
        sorted_makes = sorted(cur_makes.items(), key=lambda kv: kv[1], reverse=True)
        for i, (make_name, count) in enumerate(sorted_makes, start=1):
            if make_name.strip().lower() == user_brand.lower():
                user_brand_rank = i
                user_brand_share_pct = round(count / cur_total * 100.0, 4)
                if leader is not None:
                    gap_to_leader_units = leader["sold_count"] - count
                    gap_to_leader_share_pts = round(leader["share_pct"] - user_brand_share_pct, 4)
                break

    all_keys = sorted(set(cur_models) | set(pri_models))
    model_rows: list[dict[str, Any]] = []
    for (make, model) in all_keys:
        cur_count = cur_models.get((make, model), 0)
        pri_count = pri_models.get((make, model), 0)
        cur_share = (cur_count / cur_total * 100.0) if cur_total > 0 else 0.0
        pri_share = (pri_count / pri_total * 100.0) if pri_total > 0 else 0.0
        share_bps = (cur_share - pri_share) * 100.0
        model_rows.append({
            "make": make,
            "model": model,
            "current_sold_count": cur_count,
            "current_share_pct": round(cur_share, 4),
            "prior_sold_count": pri_count,
            "prior_share_pct": round(pri_share, 4),
            "share_change_bps": round(share_bps, 2),
            "is_user_brand": (user_brand is not None and make.strip().lower() == user_brand.lower()),
        })

    model_rows.sort(key=lambda r: r["current_share_pct"], reverse=True)
    for i, r in enumerate(model_rows, start=1):
        r["rank"] = i

    fastest_gainer: dict[str, Any] | None = None
    if model_rows:
        candidate = max(model_rows, key=lambda r: r["share_change_bps"])
        if candidate["share_change_bps"] > 0:
            fastest_gainer = {
                "make": candidate["make"],
                "model": candidate["model"],
                "share_change_bps": candidate["share_change_bps"],
            }

    visible = model_rows[:top_n] if top_n > 0 else model_rows

    out = {
        "ok": True,
        "scope": {
            "body_type": body_type,
            "state": (state_filter.strip().upper() if state_filter else "national"),
            "user_brand": user_brand,
            "top_n": top_n,
        },
        "totals": {
            "current_total": cur_total,
            "prior_total": pri_total,
        },
        "leader": leader,
        "user_brand_rank": user_brand_rank,
        "user_brand_share_pct": user_brand_share_pct,
        "gap_to_leader_units": gap_to_leader_units,
        "gap_to_leader_share_pts": gap_to_leader_share_pts,
        "fastest_gainer": fastest_gainer,
        "models": visible,
        "all_models_count": len(model_rows),
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
        sys.stderr.write(f"compute_segment_conquest: unexpected error: {exc}\n")
        sys.exit(1)
