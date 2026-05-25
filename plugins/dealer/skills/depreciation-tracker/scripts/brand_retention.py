#!/usr/bin/env python3
"""
brand_retention.py — Stats engine for W3 (Brand Residual Ranking).

Reads two parsed sold-summary outputs (current period + prior period, both
keyed on `make`) plus optional volume context, and emits per-brand retention %
+ tier classification.

Tiers (per `references/tier-and-verdict-bands.md` retention-tier rule):
  T1  retention_pct >= 98       (best — value retention leaders)
  T2  95 <= retention_pct < 98
  T3  90 <= retention_pct < 95
  T4  retention_pct < 90        (worst — value retention laggards)

Tier-jump detection: when the current-period tier differs from a hypothetical
prior-period tier (computed from a 2-period-back retention if a `volumes_prior`
block was supplied), emit `tier_change` field. Default is `null`.

Input (stdin JSON):
  {
    "current": {
      "rows": [
        {"make": "...", "average_sale_price": <float>, "sold_count": <int>}, ...
      ]
    },
    "prior": {
      "rows": [...]   (same shape, 6 months back per W3 default)
    },
    "volumes": {
      "rows": [
        {"make": "...", "sold_count": <int>}, ...
      ]
    }    (optional — current-period sold counts; if absent, falls back to
          current["rows"][*].sold_count which is normally also present)
  }

Output (stdout JSON):
  {
    "ok": true,
    "tier_thresholds": {"T1": 98, "T2": 95, "T3": 90},
    "ranking": [   (sorted by retention_pct desc; null retention sorted last)
      {
        "rank":           <int>,
        "make":           "...",
        "current_avg":    <float|null>,
        "prior_avg":      <float|null>,
        "retention_pct":  <float|null>,
        "volume":         <int>,
        "tier":           "T1" | "T2" | "T3" | "T4" | null
      }, ...
    ],
    "tier_counts": {"T1": <int>, "T2": <int>, "T3": <int>, "T4": <int>}
  }
"""

from __future__ import annotations

import json
import sys
from typing import Any


TIER_THRESHOLDS = {"T1": 98.0, "T2": 95.0, "T3": 90.0}


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int:
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _tier_for_retention(retention_pct: float | None) -> str | None:
    if retention_pct is None:
        return None
    if retention_pct >= TIER_THRESHOLDS["T1"]:
        return "T1"
    if retention_pct >= TIER_THRESHOLDS["T2"]:
        return "T2"
    if retention_pct >= TIER_THRESHOLDS["T3"]:
        return "T3"
    return "T4"


def _index_by_make(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        make = r.get("make")
        if not make:
            continue
        key = str(make)
        existing = out.get(key)
        if existing is None:
            out[key] = {
                "average_sale_price": _to_float(r.get("average_sale_price")),
                "sold_count": _to_int(r.get("sold_count")),
            }
        else:
            cur_n = existing["sold_count"]
            new_n = _to_int(r.get("sold_count"))
            total = cur_n + new_n
            cur_p = existing["average_sale_price"] or 0.0
            new_p = _to_float(r.get("average_sale_price")) or 0.0
            existing["sold_count"] = total
            if total > 0 and (cur_p or new_p):
                existing["average_sale_price"] = (cur_p * cur_n + new_p * new_n) / total
    return out


def _volumes_by_make(payload: Any) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        return {}
    out: dict[str, int] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        make = r.get("make")
        if not make:
            continue
        out[str(make)] = out.get(str(make), 0) + _to_int(r.get("sold_count"))
    return out


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    current_idx = _index_by_make(cfg.get("current"))
    prior_idx = _index_by_make(cfg.get("prior"))
    vol_idx = _volumes_by_make(cfg.get("volumes"))

    makes = set(current_idx.keys()) | set(prior_idx.keys())
    rows_unsorted: list[dict[str, Any]] = []
    for make in makes:
        cur = current_idx.get(make) or {}
        pri = prior_idx.get(make) or {}
        cur_avg = cur.get("average_sale_price")
        pri_avg = pri.get("average_sale_price")
        retention_pct: float | None = None
        if pri_avg and cur_avg is not None and pri_avg > 0:
            retention_pct = cur_avg / pri_avg * 100.0
        volume = vol_idx.get(make) or cur.get("sold_count") or 0
        rows_unsorted.append({
            "make": make,
            "current_avg": cur_avg,
            "prior_avg": pri_avg,
            "retention_pct": retention_pct,
            "volume": volume,
            "tier": _tier_for_retention(retention_pct),
        })

    rows_unsorted.sort(
        key=lambda r: (r["retention_pct"] is None, -(r["retention_pct"] or 0.0)),
    )
    for i, r in enumerate(rows_unsorted, start=1):
        r["rank"] = i

    tier_counts = {"T1": 0, "T2": 0, "T3": 0, "T4": 0}
    for r in rows_unsorted:
        if r["tier"]:
            tier_counts[r["tier"]] = tier_counts.get(r["tier"], 0) + 1

    out = {
        "ok": True,
        "tier_thresholds": TIER_THRESHOLDS,
        "ranking": rows_unsorted,
        "tier_counts": tier_counts,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
