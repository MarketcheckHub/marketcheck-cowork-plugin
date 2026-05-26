#!/usr/bin/env python3
"""
msrp_parity.py — Stats engine for W5 (MSRP Parity Tracker).

Reads two parsed sold-summary outputs (current period + prior period, both
keyed on `make,model` and ranked by `price_over_msrp_percentage`) plus
optional volume context, and emits per-(make, model) parity status +
cross-period direction.

Status (per `references/tier-and-verdict-bands.md`):
  - "above"  price_over_msrp_percentage > 0      (above sticker)
  - "at"     -1.0 <= price_over_msrp_percentage <= 0
  - "below"  price_over_msrp_percentage < -1.0   (below sticker — incentives)

Direction (cross-period, computed from current_pct vs prior_pct):
  - "flipped_below"     prior_pct >= 0 AND current_pct < 0
  - "flipped_above"     prior_pct <= 0 AND current_pct > 0
  - "deepening"         both same sign and |current| > |prior|
  - "narrowing"         both same sign and |current| < |prior|
  - "stable"            |current - prior| < 0.5
  - null                prior_pct missing

Input (stdin JSON):
  {
    "current": {
      "rows": [
        {"make": "...", "model": "...",
         "price_over_msrp_percentage": <float>,
         "average_sale_price": <float>,
         "sold_count": <int>}, ...
      ]
    },
    "prior": {
      "rows": [...]
    },
    "volumes": {
      "rows": [
        {"make": "...", "model": "...", "sold_count": <int>}, ...
      ]
    }    (optional)
  }

Output (stdout JSON):
  {
    "ok": true,
    "rows": [
      {
        "make_model":     "Honda Civic",
        "make":           "Honda",
        "model":          "Civic",
        "current_pct":    <float|null>,
        "prior_pct":      <float|null>,
        "change_pct":     <float|null>,
        "current_avg_price": <float|null>,
        "volume":         <int>,
        "status":         "above" | "at" | "below" | null,
        "direction":      "flipped_below" | "flipped_above" | "deepening"
                         | "narrowing" | "stable" | null
      }, ...   (sorted by current_pct desc; null sorted last)
    ],
    "highlights": {
      "above_sticker_count": <int>,
      "below_sticker_count": <int>,
      "flipped_below":  [<make_model>, ...],
      "flipped_above":  [<make_model>, ...],
      "deepening_discounts": [<make_model>, ...]
    }
  }
"""

from __future__ import annotations

import json
import sys
from typing import Any


PARITY_AT_LOWER = -1.0
DIRECTION_STABLE_THRESHOLD = 0.5


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


def _status(pct: float | None) -> str | None:
    if pct is None:
        return None
    if pct > 0:
        return "above"
    if pct >= PARITY_AT_LOWER:
        return "at"
    return "below"


def _direction(current: float | None, prior: float | None) -> str | None:
    if current is None or prior is None:
        return None
    if abs(current - prior) < DIRECTION_STABLE_THRESHOLD:
        return "stable"
    if prior >= 0 and current < 0:
        return "flipped_below"
    if prior <= 0 and current > 0:
        return "flipped_above"
    if (current >= 0 and prior >= 0) or (current <= 0 and prior <= 0):
        if abs(current) > abs(prior):
            return "deepening"
        return "narrowing"
    return None


def _index_make_model(payload: Any) -> dict[str, dict[str, Any]]:
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
        model = r.get("model")
        if not (make and model):
            continue
        key = f"{make} {model}"
        existing = out.get(key)
        if existing is None:
            out[key] = {
                "make": str(make),
                "model": str(model),
                "price_over_msrp_percentage": _to_float(r.get("price_over_msrp_percentage")),
                "average_sale_price": _to_float(r.get("average_sale_price")),
                "sold_count": _to_int(r.get("sold_count")),
            }
        else:
            cur_n = existing["sold_count"]
            new_n = _to_int(r.get("sold_count"))
            total = cur_n + new_n
            existing["sold_count"] = total
            for field in ("price_over_msrp_percentage", "average_sale_price"):
                existing_val = existing.get(field) or 0.0
                new_val = _to_float(r.get(field)) or 0.0
                if total > 0 and (existing_val or new_val):
                    existing[field] = (existing_val * cur_n + new_val * new_n) / total
    return out


def _volumes_index(payload: Any) -> dict[str, int]:
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
        model = r.get("model")
        if not (make and model):
            continue
        key = f"{make} {model}"
        out[key] = out.get(key, 0) + _to_int(r.get("sold_count"))
    return out


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        json.dump({"ok": False, "error_type": "bad_stdin", "error": str(exc)},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    current_idx = _index_make_model(cfg.get("current"))
    prior_idx = _index_make_model(cfg.get("prior"))
    volumes_idx = _volumes_index(cfg.get("volumes"))

    rows_out: list[dict[str, Any]] = []
    keys = set(current_idx.keys()) | set(prior_idx.keys())
    for key in keys:
        cur = current_idx.get(key) or {}
        pri = prior_idx.get(key) or {}
        cur_pct = cur.get("price_over_msrp_percentage")
        pri_pct = pri.get("price_over_msrp_percentage")
        change_pct = (cur_pct - pri_pct) if (cur_pct is not None and pri_pct is not None) else None
        rows_out.append({
            "make_model": key,
            "make": cur.get("make") or pri.get("make"),
            "model": cur.get("model") or pri.get("model"),
            "current_pct": cur_pct,
            "prior_pct": pri_pct,
            "change_pct": change_pct,
            "current_avg_price": cur.get("average_sale_price"),
            "volume": volumes_idx.get(key) or cur.get("sold_count") or 0,
            "status": _status(cur_pct),
            "direction": _direction(cur_pct, pri_pct),
        })

    rows_out.sort(
        key=lambda r: (r["current_pct"] is None, -(r["current_pct"] or 0.0)),
    )

    flipped_below = [r["make_model"] for r in rows_out if r["direction"] == "flipped_below"]
    flipped_above = [r["make_model"] for r in rows_out if r["direction"] == "flipped_above"]
    deepening = [
        r["make_model"] for r in rows_out
        if r["direction"] == "deepening" and r["status"] == "below"
    ]
    highlights = {
        "above_sticker_count": sum(1 for r in rows_out if r["status"] == "above"),
        "below_sticker_count": sum(1 for r in rows_out if r["status"] == "below"),
        "flipped_below": flipped_below,
        "flipped_above": flipped_above,
        "deepening_discounts": deepening,
    }

    out = {"ok": True, "rows": rows_out, "highlights": highlights}
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
