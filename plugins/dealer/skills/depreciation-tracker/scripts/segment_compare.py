#!/usr/bin/env python3
"""
segment_compare.py — Stats engine for W2 (Segment Value Trends).

Reads two parsed sold-summary outputs (current period + prior period) plus a
dimension key (`body_type` or `fuel_type_category` or `make`/`model`) and emits
per-row cross-period diffs with classifications.

Classifications (per `references/tier-and-verdict-bands.md` segment-classifier
rule):
  - "appreciating"        price_change_pct >= +1.0%
  - "stable"              -1.0% < price_change_pct < +1.0%
  - "soft"                -3.0% < price_change_pct <= -1.0%
  - "accelerating_dep"    price_change_pct <= -3.0%

Input (stdin JSON):
  {
    "current": {
      "rows": [
        {"<dimension>": "...", "average_sale_price": <float>,
         "sold_count": <int>}, ...
      ]
    },
    "prior": {
      "rows": [...]   (same shape)
    },
    "dimension":   "body_type" | "fuel_type_category" | "make" | "model"
  }

Both `current` and `prior` are typically the FULL parse_sold_summary output
JSON; this script reads the `rows` array and ignores everything else.

Output (stdout JSON):
  {
    "ok": true,
    "dimension": "<dimension>",
    "rows": [
      {
        "key":                  <dimension value>,
        "current_avg":          <float|null>,
        "prior_avg":            <float|null>,
        "current_sold_count":   <int>,
        "prior_sold_count":     <int>,
        "price_change_pct":     <float|null>,    (+ = appreciation, - = depreciation)
        "volume_change_pct":    <float|null>,
        "classification":       "appreciating" | "stable" | "soft" | "accelerating_dep" | null
      }, ...   (sorted by current_avg desc; null avg sorted last)
    ],
    "missing_in_prior":  [<key>, ...],   (keys present in current but absent prior)
    "missing_in_current": [<key>, ...]
  }
"""

from __future__ import annotations

import json
import sys
from typing import Any


SEGMENT_THRESHOLDS = {
    "appreciating":     1.0,
    "stable_lower":    -1.0,
    "soft_lower":      -3.0,
}


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


def _classify(price_change_pct: float | None) -> str | None:
    if price_change_pct is None:
        return None
    if price_change_pct >= SEGMENT_THRESHOLDS["appreciating"]:
        return "appreciating"
    if price_change_pct > SEGMENT_THRESHOLDS["stable_lower"]:
        return "stable"
    if price_change_pct > SEGMENT_THRESHOLDS["soft_lower"]:
        return "soft"
    return "accelerating_dep"


def _index_rows(payload: Any, dimension: str) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        key = r.get(dimension)
        if not key:
            continue
        existing = out.get(str(key))
        if existing is None:
            out[str(key)] = {
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


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    dimension = cfg.get("dimension") or "body_type"
    current_idx = _index_rows(cfg.get("current"), dimension)
    prior_idx = _index_rows(cfg.get("prior"), dimension)

    rows_out: list[dict[str, Any]] = []
    keys = set(current_idx.keys()) | set(prior_idx.keys())
    missing_in_prior: list[str] = []
    missing_in_current: list[str] = []

    for key in sorted(keys):
        cur = current_idx.get(key)
        pri = prior_idx.get(key)
        if cur is None:
            missing_in_current.append(key)
        if pri is None:
            missing_in_prior.append(key)
        cur_avg = (cur or {}).get("average_sale_price")
        pri_avg = (pri or {}).get("average_sale_price")
        cur_n = (cur or {}).get("sold_count", 0)
        pri_n = (pri or {}).get("sold_count", 0)

        price_change_pct: float | None = None
        if pri_avg and cur_avg is not None:
            price_change_pct = (cur_avg - pri_avg) / pri_avg * 100.0
        volume_change_pct: float | None = None
        if pri_n and cur_n is not None:
            volume_change_pct = (cur_n - pri_n) / pri_n * 100.0

        rows_out.append({
            "key": key,
            "current_avg": cur_avg,
            "prior_avg": pri_avg,
            "current_sold_count": cur_n,
            "prior_sold_count": pri_n,
            "price_change_pct": price_change_pct,
            "volume_change_pct": volume_change_pct,
            "classification": _classify(price_change_pct),
        })

    rows_out.sort(
        key=lambda r: (r["current_avg"] is None, -(r["current_avg"] or 0.0)),
    )

    out = {
        "ok": True,
        "dimension": dimension,
        "rows": rows_out,
        "missing_in_prior": missing_in_prior,
        "missing_in_current": missing_in_current,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
