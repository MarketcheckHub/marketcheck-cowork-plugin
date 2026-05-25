#!/usr/bin/env python3
"""
parse_search.py — Normalise a `search_active_cars` / `search_past_90_days` /
`search_uk_active_cars` / `search_uk_recent_cars` response. Also computes
signed price-change amounts from percentages when present.

Variant-consistency filtering is NOT performed here — the skill trusts the
server's `trim` facet to return the correct line-variant. `body_type`,
`drivetrain`, `engine`, and `transmission` are carried on every normalised
listing as display-only metadata (rendered on comp listings and in the
subject's Decoded Specs block when present).

Usage:
  parse_search.py [options]
  parse_search.py --file <path> [options]

Options:
  --subject-vin <VIN>          the user's own VIN — shadow-listing detection;
                               matches counted separately as `self_vin_match`
  --exclude-vins <V1,V2,...>   drop listings with these VINs (history-hop, etc);
                               matches counted as `exclude_vin_match`
  --no-price-filter            keep listings with price in {0, null} (default: drop)

Emits:
  {
    "ok": ...,
    "error_type": ..., "error": ...,
    "num_found": <int>,              # echo from response
    "pulled_count": <int>,           # rows parser actually saw before filtering
    "kept_count": <int>,             # rows after all filters
    "listings": [<normalized>, ...],
    "stats": {"price": {...}, "miles": {...}, "dom": {...}},
    "filtered_out": {
      "self_vin_match": <int>,       # subject VIN matches (shadow-listing count)
      "exclude_vin_match": <int>,    # other --exclude-vins matches
      "self_vin": <int>,             # DEPRECATED alias = self_vin_match + exclude_vin_match
      "invalid_price": <int>
    },
    "source": ...
  }

C6 — the old `self_vin` counter conflated shadow-listing hits (the user's
own VIN appearing at a different dealer) with --exclude-vins removals (e.g.
past dealer-hop VINs from get_car_history). The renderer couldn't tell them
apart, so DQ event (c) "shadow listing" and (d) "filtered-out counts"
collapsed into one number. Split into `self_vin_match` (subject only) and
`exclude_vin_match` (others). Legacy `self_vin` alias kept one version for
downstream migration.
"""

from __future__ import annotations

import sys
from typing import Any

from _common import read_input, emit, classify_error, arg_value, arg_value_multi, arg_flag


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _normalize_listing(raw: dict[str, Any]) -> dict[str, Any]:
    # Real `search_active_cars` / `search_past_90_days` listings:
    #   - Vehicle spec fields (year, make, model, trim, body_type, drivetrain,
    #     engine, transmission) live exclusively in the `build` sub-object.
    #   - Dealer fields live exclusively in the `dealer` sub-object.
    #   - Pricing, miles, DOM variants, dates, VIN, id, heading, source,
    #     price_change_percent, ref_price, dist live at listing root.
    # No root-vs-build OR chain for spec fields — root is always null for them.
    dealer = raw.get("dealer") if isinstance(raw.get("dealer"), dict) else {}
    build = raw.get("build") if isinstance(raw.get("build"), dict) else {}

    price = _to_float(raw.get("price"))
    ref_price = _to_float(raw.get("ref_price"))
    price_change_percent = _to_float(raw.get("price_change_percent"))

    # Prefer exact delta from ref_price (when present); fall back to
    # percent-derived delta. Percent is defined as:
    #   change% = (new - old) / old * 100    →   old = new / (1 + change%/100)
    # So change$ = new - old = new * (p/100) / (1 + p/100).
    price_change_amount: float | None = None
    if price is not None and ref_price is not None and ref_price > 0:
        price_change_amount = price - ref_price
    elif price is not None and price_change_percent is not None and price_change_percent != 0:
        try:
            p = price_change_percent / 100.0
            price_change_amount = price * p / (1.0 + p)
        except Exception:
            price_change_amount = None

    dealer_type_raw = None
    if dealer:
        dealer_type_raw = dealer.get("dealer_type")
    if dealer_type_raw:
        dealer_type_raw = str(dealer_type_raw).lower()

    return {
        "id": raw.get("id"),
        "vin": raw.get("vin"),
        "price": price,
        "ref_price": ref_price,
        "miles": _to_float(raw.get("miles")),
        "msrp": _to_float(raw.get("msrp")),
        # DOM fields — three distinct market-presence semantics. They are NOT
        # interchangeable; downstream code (specifically _bucket_dom in
        # comp_stats.py and the DOM column renderer) must read `dom_active`
        # directly, not the OR-chained legacy `dom`. See
        # references/w1-price-check.md step 4 for the field-semantic rationale:
        #   - dom_active   — recent presence (≤30-day gap tolerance). The only
        #                    field used for Fresh/Aging/Stale bucketing and the
        #                    DOM column. Null → bucket as Unknown.
        #   - dom_180      — extended presence (≤180-day gap tolerance).
        #                    Reserved for seasonal-analysis workflows.
        #   - dom_lifetime — all-time cross-dealer accumulator. Reserved for
        #                    long-term VIN-history workflows (W3 trade-in history).
        # The legacy combined `dom` field is preserved (best-available OR-chain)
        # for backward compatibility with downstream readers that have not
        # migrated yet — but new code MUST read `dom_active` directly.
        "dom": _to_int(raw.get("dom_active") or raw.get("dom_180") or raw.get("dom")),  # LEGACY (best-available OR-chain)
        "dom_active":   _to_int(raw.get("dom_active")),
        "dom_180":      _to_int(raw.get("dom_180")),
        "dom_lifetime": _to_int(raw.get("dom")),
        # Spec fields — build-object only.
        "year": build.get("year"),
        "make": build.get("make"),
        "model": build.get("model"),
        "trim": build.get("trim"),
        "body_type": build.get("body_type"),
        "drivetrain": build.get("drivetrain"),
        "engine": build.get("engine"),
        "transmission": build.get("transmission"),
        "dealer_name": dealer.get("name") if dealer else None,
        "dealer_type": dealer_type_raw,
        "dealer_city": dealer.get("city") if dealer else None,
        "dealer_state": dealer.get("state") if dealer else None,
        "dealer_zip": dealer.get("zip") if dealer else None,
        "distance_mi": _to_float(raw.get("dist") or raw.get("distance")),
        # Tri-state is_certified. The wire form is integer 1, integer 0, or absent.
        # Renderer needs to distinguish "unknown" from "confirmed non-CPO" — None
        # renders as `—`, False renders as `N`, True renders as `Y`. In practice
        # the server omits the field for non-CPO listings (31 of 50 rows in a
        # live Honda Accord used sample), so None usually means non-CPO, but
        # never assume. inventory_type only carries "used" / "new" in real
        # responses; do not check for "certified".
        "is_certified": (bool(raw.get("is_certified")) if "is_certified" in raw else None),
        "inventory_type": raw.get("inventory_type"),
        "price_change_percent": price_change_percent,
        "price_change_amount": price_change_amount,
        "last_seen_at_date": raw.get("last_seen_at_date"),
        "first_seen_at_date": raw.get("first_seen_at_date"),
        "heading": raw.get("heading"),
        "vdp_url": raw.get("vdp_url"),
        "source": raw.get("source"),
    }


def main(argv: list[str]) -> int:
    payload, source = read_input(argv)
    etype, emsg = classify_error(payload)
    if etype:
        emit({"ok": False, "error_type": etype, "error": emsg, "source": source})
        return 0

    data = payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]

    if not isinstance(data, dict):
        emit({"ok": False, "error_type": "unexpected_shape", "error": "payload not a dict", "source": source})
        return 0

    num_found = _to_int(data.get("num_found")) or 0
    listings_raw = data.get("listings") or []
    if not isinstance(listings_raw, list):
        listings_raw = []

    # C6 — split subject VIN from other exclusions. --subject-vin is the
    # user's own VIN (shadow-listing detection); --exclude-vins is everything
    # else (history-hop VINs passed through from get_car_history, etc.).
    # Both drop the listing, but the counters track them separately so the
    # renderer can emit DQ events (c) and (d) distinctly.
    subject_vin_raw = arg_value(argv, "--subject-vin") or ""
    subject_vin = subject_vin_raw.upper().strip()
    exclude_vins = set(v.upper() for v in arg_value_multi(argv, "--exclude-vins"))
    no_price_filter = arg_flag(argv, "--no-price-filter")

    filtered_out = {
        "self_vin_match": 0,
        "exclude_vin_match": 0,
        "invalid_price": 0,
    }

    pulled_count = len(listings_raw)
    kept: list[dict[str, Any]] = []
    for raw in listings_raw:
        if not isinstance(raw, dict):
            continue
        norm = _normalize_listing(raw)
        vin = (norm.get("vin") or "").upper()

        # Subject-VIN match (shadow listing at another dealer)
        if subject_vin and vin == subject_vin:
            filtered_out["self_vin_match"] += 1
            continue

        # Other excluded VINs (history-hop, etc.)
        if vin and vin in exclude_vins:
            filtered_out["exclude_vin_match"] += 1
            continue

        # Price filter
        if not no_price_filter:
            if norm["price"] in (None, 0) or (norm["price"] is not None and norm["price"] <= 0):
                filtered_out["invalid_price"] += 1
                continue

        kept.append(norm)

    # Deprecated `self_vin` alias — equals the old semantics (any VIN-based drop).
    # Callers should migrate to the split counters; alias kept for one version.
    filtered_out["self_vin"] = filtered_out["self_vin_match"] + filtered_out["exclude_vin_match"]

    stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
    # Facet-discovery passthrough — see references/facet-discovery.md.
    facets = data.get("facets") if isinstance(data.get("facets"), dict) else {}

    emit({
        "ok": True,
        "num_found": num_found,
        "pulled_count": pulled_count,
        "kept_count": len(kept),
        "listings": kept,
        "stats": stats,
        "facets": facets,
        "filtered_out": filtered_out,
        "source": source,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
