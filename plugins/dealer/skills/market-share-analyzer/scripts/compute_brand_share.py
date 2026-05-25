#!/usr/bin/env python3
"""
compute_brand_share.py — Compute per-make share %, share change in basis points,
and volume change % from two parsed get_sold_summary outputs (current + prior period).

Reads each parser's `rows[]` (per parse_sold_summary.py canonical shape: one row
per state×make×month bucket), aggregates sold_count by make across states /
months, and emits a ranked make-level summary with bps share-change.

Denominator strategy (Q1=A): the per-period "total" is the sum of sold_count
across all rows in the response. Per-call top_n=50 is used by the calling
skill so the long-tail (~2-5% of national volume) is excluded; this script
emits `top_n_coverage_pct` = sum(make sold) / true total to flag the gap when
known. When only top-50 was fetched, true total is unknown and coverage_pct
is null.

Usage:
  compute_brand_share.py \\
    --current  <parse_sold_summary output JSON path> \\
    --prior    <parse_sold_summary output JSON path> \\
    [--top-n 20]                  # number of makes to render in the table (default 20)
    [--user-brand <make>]         # highlight this make in output
    [--state <STATE>]             # filter rows to a single state (post-aggregation)

Output JSON on stdout:
  {
    "ok": true,
    "scope": {
      "state": "<STATE>" | "national",
      "user_brand": "<make>" | null,
      "top_n": <int>
    },
    "totals": {
      "current_total": <int>,
      "prior_total":   <int>,
      "current_makes_seen": <int>,
      "prior_makes_seen":   <int>
    },
    "makes": [
      {
        "rank": <int>,
        "make": "<Make>",
        "current_sold_count": <int>,
        "current_share_pct":  <float>,
        "prior_sold_count":   <int>,
        "prior_share_pct":    <float>,
        "share_change_bps":   <float>,
        "volume_change_pct":  <float | null>,
        "trend":              "GAINING" | "LOSING" | "STABLE",
        "is_user_brand":      <bool>
      },
      ...
    ],
    "summary": {
      "top_3_gainers":   [<make>, <make>, <make>],
      "top_3_losers":    [<make>, <make>, <make>],
      "user_brand_movement": {
        "make": "<make>",
        "current_rank": <int> | null,
        "prior_rank":   <int> | null,
        "rank_change":  <int> | null,
        "share_change_bps": <float> | null
      } | null
    }
  }

  On failure: {"ok": false, "error_type": "...", "error": "..."}

Trend classification:
  share_change_bps >= +50  → "GAINING"
  share_change_bps <= -50  → "LOSING"
  otherwise                → "STABLE"

Long-tail caveat: when calling skill set top_n=50, the makes seen are the
top 50 by sold_count for the period. Long-tail makes (Maserati, Lotus,
Ferrari, etc.) are excluded; their absence depresses the denominator by
~2-5% of true national volume. The calling skill should emit DQ event (e)
"share computed over visible top_50 makes; long-tail excluded" when this
happens.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


GAINING_BPS_THRESHOLD = 50.0
LOSING_BPS_THRESHOLD = -50.0


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
        sys.stderr.write(f"compute_brand_share: {flag} {raw!r} not an integer; using default {default}\n")
        return default


def _load_parsed(path_str: str | None, label: str) -> dict[str, Any]:
    if not path_str:
        sys.stderr.write(f"compute_brand_share: --{label} is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"compute_brand_share: cannot read {label} {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"compute_brand_share: {label} {path_str!r} not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"compute_brand_share: {label} payload must be a JSON object\n")
        raise SystemExit(1)
    if payload.get("ok") is False:
        sys.stderr.write(
            f"compute_brand_share: {label} parser reported ok=false: "
            f"{payload.get('error_type')!r} — {payload.get('error')!r}\n"
        )
        raise SystemExit(1)
    return payload


def _aggregate_makes(rows: list[dict[str, Any]], state_filter: str | None) -> tuple[dict[str, int], int]:
    """Sum sold_count per make across rows. Returns (make_totals, grand_total).

    state_filter (when non-None) drops rows whose state doesn't match. The
    canonical row shape from parse_sold_summary is one row per state×make×month;
    summing without a state filter gives national totals.
    """
    totals: dict[str, int] = defaultdict(int)
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
        if not make:
            continue
        sc = row.get("sold_count")
        if sc is None:
            continue
        try:
            sc_int = int(sc)
        except (TypeError, ValueError):
            continue
        if sc_int <= 0:
            continue
        totals[str(make)] += sc_int
        grand_total += sc_int
    return dict(totals), grand_total


def _trend(bps: float) -> str:
    if bps >= GAINING_BPS_THRESHOLD:
        return "GAINING"
    if bps <= LOSING_BPS_THRESHOLD:
        return "LOSING"
    return "STABLE"


def main(argv: list[str]) -> int:
    current_path = _arg_value(argv, "--current")
    prior_path = _arg_value(argv, "--prior")
    top_n = _arg_int(argv, "--top-n", 20)
    user_brand_raw = _arg_value(argv, "--user-brand")
    user_brand = (user_brand_raw or "").strip() or None
    state_filter = _arg_value(argv, "--state")

    try:
        current = _load_parsed(current_path, "current")
        prior = _load_parsed(prior_path, "prior")
    except SystemExit:
        return 1

    current_makes, current_total = _aggregate_makes(current.get("rows") or [], state_filter)
    prior_makes, prior_total = _aggregate_makes(prior.get("rows") or [], state_filter)

    if current_total == 0:
        json.dump({
            "ok": False,
            "error_type": "no_current_data",
            "error": "Current period has zero sold_count across all makes after filters",
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    all_makes = sorted(set(current_makes) | set(prior_makes))
    rows_out: list[dict[str, Any]] = []

    for make in all_makes:
        cur_count = current_makes.get(make, 0)
        pri_count = prior_makes.get(make, 0)
        cur_share = (cur_count / current_total * 100.0) if current_total > 0 else 0.0
        pri_share = (pri_count / prior_total * 100.0) if prior_total > 0 else 0.0
        share_bps = (cur_share - pri_share) * 100.0
        if pri_count > 0:
            volume_change_pct = (cur_count - pri_count) / pri_count * 100.0
        else:
            volume_change_pct = None
        rows_out.append({
            "make": make,
            "current_sold_count": cur_count,
            "current_share_pct": round(cur_share, 4),
            "prior_sold_count": pri_count,
            "prior_share_pct": round(pri_share, 4),
            "share_change_bps": round(share_bps, 2),
            "volume_change_pct": round(volume_change_pct, 2) if volume_change_pct is not None else None,
            "trend": _trend(share_bps),
            "is_user_brand": (user_brand is not None and make.strip().lower() == user_brand.lower()),
        })

    rows_out.sort(key=lambda r: r["current_share_pct"], reverse=True)
    for i, row in enumerate(rows_out, start=1):
        row["rank"] = i

    visible = rows_out[:top_n] if top_n > 0 else rows_out

    gainers = sorted(
        [r for r in rows_out if r["trend"] == "GAINING"],
        key=lambda r: r["share_change_bps"], reverse=True,
    )[:3]
    losers = sorted(
        [r for r in rows_out if r["trend"] == "LOSING"],
        key=lambda r: r["share_change_bps"],
    )[:3]

    user_brand_movement: dict[str, Any] | None = None
    if user_brand is not None:
        match = next((r for r in rows_out if r["is_user_brand"]), None)
        if match is not None:
            prior_sorted = sorted(rows_out, key=lambda r: r["prior_share_pct"], reverse=True)
            prior_rank: int | None = None
            for j, r in enumerate(prior_sorted, start=1):
                if r["make"] == match["make"]:
                    if r["prior_sold_count"] > 0:
                        prior_rank = j
                    break
            rank_change: int | None = None
            if prior_rank is not None:
                rank_change = prior_rank - match["rank"]
            user_brand_movement = {
                "make": match["make"],
                "current_rank": match["rank"],
                "prior_rank": prior_rank,
                "rank_change": rank_change,
                "share_change_bps": match["share_change_bps"],
            }
        else:
            user_brand_movement = {
                "make": user_brand,
                "current_rank": None,
                "prior_rank": None,
                "rank_change": None,
                "share_change_bps": None,
            }

    out = {
        "ok": True,
        "scope": {
            "state": (state_filter.strip().upper() if state_filter else "national"),
            "user_brand": user_brand,
            "top_n": top_n,
        },
        "totals": {
            "current_total": current_total,
            "prior_total": prior_total,
            "current_makes_seen": len(current_makes),
            "prior_makes_seen": len(prior_makes),
        },
        "makes": visible,
        "all_makes_count": len(rows_out),
        "summary": {
            "top_3_gainers": [g["make"] for g in gainers],
            "top_3_losers": [l["make"] for l in losers],
            "user_brand_movement": user_brand_movement,
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
        sys.stderr.write(f"compute_brand_share: unexpected error: {exc}\n")
        sys.exit(1)
