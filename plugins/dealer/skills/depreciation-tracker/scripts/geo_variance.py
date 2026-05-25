#!/usr/bin/env python3
"""
geo_variance.py — Stats engine for W4 (Geographic Depreciation Variance).

Reads a parsed sold-summary output keyed on `state` plus a national-baseline
average and emits per-state price index + premium/discount classification.

Classifications (per `references/tier-and-verdict-bands.md` geo-classifier
rule):
  - "premium"   price_index > 105
  - "average"   95 <= price_index <= 105
  - "discount"  price_index < 95

Input (stdin JSON):
  {
    "state_rows": {
      "rows": [
        {"state": "CA", "average_sale_price": <float>, "sold_count": <int>}, ...
      ]
    },
    "national_avg": <float>     (single scalar; weighted national mean)
  }

`state_rows` is the FULL parse_sold_summary output; this script reads `rows`
and ignores everything else.

Output (stdout JSON):
  {
    "ok": true,
    "national_avg": <float|null>,
    "rows": [
      {
        "state":              "CA",
        "avg_price":          <float>,
        "price_index":        <float>,
        "premium_dollars":    <float>,
        "sold_count":         <int>,
        "classification":     "premium" | "average" | "discount" | null
      }, ...   (sorted by price_index desc; null index sorted last)
    ],
    "summary": {
      "premium_count":  <int>,
      "average_count":  <int>,
      "discount_count": <int>,
      "top_5_premium":  [<state>, ...],
      "bottom_5_discount": [<state>, ...]
    }
  }
"""

from __future__ import annotations

import json
import sys
from typing import Any


GEO_PREMIUM_THRESHOLD = 105.0
GEO_DISCOUNT_THRESHOLD = 95.0


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


def _classify(price_index: float | None) -> str | None:
    if price_index is None:
        return None
    if price_index > GEO_PREMIUM_THRESHOLD:
        return "premium"
    if price_index < GEO_DISCOUNT_THRESHOLD:
        return "discount"
    return "average"


def _index_states(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        state = r.get("state")
        if not state:
            continue
        key = str(state).upper()
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


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    national_avg = _to_float(cfg.get("national_avg"))
    state_idx = _index_states(cfg.get("state_rows"))

    rows_out: list[dict[str, Any]] = []
    for state, blob in state_idx.items():
        avg = blob.get("average_sale_price")
        n = blob.get("sold_count") or 0
        price_index: float | None = None
        premium_dollars: float | None = None
        if avg is not None and national_avg and national_avg > 0:
            price_index = avg / national_avg * 100.0
            premium_dollars = avg - national_avg
        rows_out.append({
            "state": state,
            "avg_price": avg,
            "price_index": price_index,
            "premium_dollars": premium_dollars,
            "sold_count": n,
            "classification": _classify(price_index),
        })

    rows_out.sort(
        key=lambda r: (r["price_index"] is None, -(r["price_index"] or 0.0)),
    )

    classified = [r for r in rows_out if r["classification"] is not None]
    summary = {
        "premium_count": sum(1 for r in classified if r["classification"] == "premium"),
        "average_count": sum(1 for r in classified if r["classification"] == "average"),
        "discount_count": sum(1 for r in classified if r["classification"] == "discount"),
        "top_5_premium": [
            r["state"] for r in rows_out if r["classification"] == "premium"
        ][:5],
        "bottom_5_discount": [
            r["state"] for r in reversed(rows_out) if r["classification"] == "discount"
        ][:5],
    }

    out = {
        "ok": True,
        "national_avg": national_avg,
        "rows": rows_out,
        "summary": summary,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
