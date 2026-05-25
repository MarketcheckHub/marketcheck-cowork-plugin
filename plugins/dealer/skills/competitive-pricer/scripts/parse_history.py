#!/usr/bin/env python3
"""
parse_history.py — Normalise a `get_car_history` response.

Real upstream shape (per mcp_server_tool_docs/get_car_history.md):

  {
    "vin": "<17-char VIN>",
    "num_found": <int>,                  # total history count across pages
    "listings": [
      {
        # Default Fields (returned without `fields=`)
        "id": "<VIN>-<hash>-<hash>",
        "price": <float>,
        "miles": <float or absent>,
        "data_source": "mc",
        "vdp_url": "<url>",
        "seller_type": "dealer",
        "inventory_type": "used" | "new",
        "first_seen_at_date": "<ISO-8601>",
        "last_seen_at_date":  "<ISO-8601>",
        "scraped_at_date":    "<ISO-8601>",
        "source": "<domain>",
        "seller_name": "<dealer name>",   # NOT in a dealer{} sub-object
        "city": "<city>", "state": "<ST>", "zip": "<zip>",
        # Optional Fields — REQUIRE `fields=...` request to populate:
        "vin":           "<17-char VIN>",            # absent → use _vin_from_id(id)
        "is_certified":  0 | 1,                      # absent → cpo tri-state None
        "msrp":          <float>,
        "dealer_id":     <int>,
        "stock_no":      "<dealer's internal stock id>",
        "dom_active":    <int>,                      # cross-listing accumulator (cumulative VIN aging)
        "dom_180":       <int>,
        "dom":           <int>                       # exposed as `dom_lifetime` on parser output
      },
      ...
    ]
  }

NO `{success, service, data}` envelope on success — confirmed inconsistent
with every other MCP tool in the server (per mcp_server_tool_docs/get_car_history.md
line 55). The truncation envelope wrapper `{"result": "<stringified-json>"}`
still applies — `_common._maybe_unwrap` handles that before this script
sees the payload.

Three input shapes accepted (defensive parser, ordered by likelihood):
  (1) upstream-direct: `{vin, num_found, listings: [...]}`            [REAL]
  (2) top-level list: payload itself is the list of listings          [legacy]
  (3) enveloped: `{success, service, data: [...]}` or
      `{data: {listings: [...], num_found: ...}}`                     [misread / future]

Critical: callers MUST pass `fields=CANONICAL_FIELDS_PARAM` (see below) on
every `get_car_history` invocation. Without it, `is_certified` / `dom_*` /
`msrp` / `dealer_id` / `stock_no` / `vin` are silently stripped — breaking
CPO detection (`cpo_ever` returns None) and reducing dealer-rooftop precision.

DOM semantic (per-row trajectory):
  `_derive_dom` priority is **date-pair first** — `last_seen_at_date −
  first_seen_at_date` gives the per-listing duration at this rooftop, the
  semantic the W3 Price Trajectory column wants. The explicit `dom_*` fields
  are cross-listing temporal accumulators (cumulative VIN aging as of scrape
  time) — exposed on parser output as `dom_active` / `dom_180` /
  `dom_lifetime` for consumers that want that distinct semantic, but NOT
  used as the primary source for the per-row `dom` field. `dom_active` is
  rendered by the W3 output template as a "Cumulative VIN aging" line;
  `dom_180` and `dom_lifetime` are currently unrendered (kept on output for
  parity / future use).

Sort semantic (`listings_desc`):
  Sorted by `(last_seen_at_date desc, first_seen_at_date desc)` so
  `listings[0]` is the most-recently-active listing, with first_seen as the
  tiebreaker for rows sharing a last_seen date. This is the genuinely
  "current" listing — a flash relisting that went stale won't win the
  current slot over a continuously-refreshed older listing.

Derives:
  - per-listing DOM from first_seen/last_seen dates (date-pair primary)
  - dealer-hop count: distinct dealer_id (primary), with name-fallback when
    dealer_id absent; cross-references dealer_name → dealer_id when only
    name is present on a row but the same name has been seen with an id
    elsewhere. Provenance surfaced via `dealer_count_source` field.
  - cumulative price-delta % (signed: + = drop, − = rise)
  - dropped_null_price_count: rows skipped when computing cum_change_pct
    because their price was null (baseline-shift signal).
  - num_found: from upstream payload, surfaced for pagination-gap detection.
  - CPO-ever flag (tri-state True/False/None from `is_certified`)
  - flag labels: multi_dealer_churn, sharp_drops, decertified

Usage:
  parse_history.py                  # stdin
  parse_history.py --file <path>    # truncation envelope
"""

from __future__ import annotations

import sys
from datetime import date
from typing import Any

from _common import read_input, emit, classify_error


# The canonical `fields=` argument every caller of `get_car_history` should
# pass. Without it, the upstream silently strips Optional Fields
# (is_certified, dom_active, dom_180, dom, msrp, dealer_id, stock_no, vin) —
# breaking CPO detection (cpo_ever returns None) and reducing dealer-rooftop
# precision. Mirror this string verbatim in:
#   - references/w3-trade-in-history.md step 1
#   - references/w1-price-check.md Wave C CPO-ambiguous path
#   - references/cpo.md rule 4
CANONICAL_FIELDS_PARAM = (
    "id,vin,price,miles,msrp,seller_name,dealer_id,city,state,zip,"
    "first_seen_at_date,last_seen_at_date,scraped_at_date,"
    "source,vdp_url,seller_type,inventory_type,"
    "is_certified,dom_active,dom_180,dom,stock_no,data_source"
)


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


def _parse_date(s: Any) -> date | None:
    if not s:
        return None
    try:
        s = str(s)[:10]
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def _derive_dom(raw: dict[str, Any]) -> int | None:
    """Derive DOM (per-listing duration) for a history listing.

    Priority — date-pair PRIMARY, dom_* fallbacks:
      1. `last_seen_at_date − first_seen_at_date` — per-listing duration at
         this rooftop. Semantic match for the W3 Price Trajectory DOM column.
      2. `dom_active` — cumulative VIN aging as-of scrape (cross-listing).
         Different semantic; exposed separately on parser output as
         `dom_active`. Used here only as backstop when both dates are absent.
      3. `dom_180` — 180-day variant of (2).
      4. `dom` — lifetime variant of (2).

    Note: empirical verification (live call on VIN 1N4BL4BV5SN316084) showed
    `dom_active` is a per-row temporal accumulator (e.g. 71 → 293 across the
    trajectory) — cumulative VIN aging at scrape time, NOT per-rooftop
    duration. The W3 trajectory wants per-listing duration, which is the
    date-pair derivation; the previous priority (dom_* first) was wrong for
    that use case (the operational behavior pre-fields= rollout was already
    date-pair, because dom_* were always absent).
    """
    first = _parse_date(raw.get("first_seen_at_date"))
    last = _parse_date(raw.get("last_seen_at_date"))
    if first and last:
        return (last - first).days
    for key in ("dom_active", "dom_180", "dom"):
        val = _to_int(raw.get(key))
        if val is not None:
            return val
    return None


def _vin_from_id(id_str: str | None) -> str | None:
    """Extract the 17-char VIN from a history listing's `id` prefix.

    Real ids look like `"1N4BL4DV7NN323149-29578d50-bd66"` — VIN is the
    first segment before the first hyphen (the hash suffix is dealer/listing
    deduplication data that varies across listings for the same VIN)."""
    if not id_str or not isinstance(id_str, str):
        return None
    head = id_str.split("-", 1)[0]
    return head if len(head) == 17 else None


def _normalize_listing(raw: dict[str, Any]) -> dict[str, Any]:
    id_str = raw.get("id")
    return {
        "id": id_str,
        # Prefer explicit `vin` field (returned via fields=); fall back to
        # id-prefix extraction for legacy responses.
        "vin": raw.get("vin") or _vin_from_id(id_str),
        "price": _to_float(raw.get("price")),
        "miles": _to_float(raw.get("miles")),
        "msrp": _to_float(raw.get("msrp")),
        # Per-listing duration (date-pair primary; see _derive_dom).
        "dom": _derive_dom(raw),
        # Cross-listing temporal variants — exposed for the cumulative-aging
        # consumer. NOT the source for the per-row `dom` field above.
        "dom_active":   _to_int(raw.get("dom_active")),
        "dom_180":      _to_int(raw.get("dom_180")),
        "dom_lifetime": _to_int(raw.get("dom")),
        "first_seen_at_date": raw.get("first_seen_at_date"),
        "last_seen_at_date": raw.get("last_seen_at_date"),
        # Dealer fields at root — no dealer{} sub-object on history listings.
        "dealer_name": raw.get("seller_name"),
        "dealer_id":   raw.get("dealer_id"),
        "stock_no":    raw.get("stock_no"),
        "dealer_city": raw.get("city"),
        "dealer_state": raw.get("state"),
        "dealer_zip":  raw.get("zip"),
        "inventory_type": raw.get("inventory_type"),
        # Tri-state — same semantics as parse_search: None = unknown (field absent),
        # True = CPO, False = explicit non-CPO (integer 0 on the wire).
        "is_certified": (bool(raw.get("is_certified")) if "is_certified" in raw else None),
        "seller_type": raw.get("seller_type"),
        "source": raw.get("source"),
        "data_source": raw.get("data_source"),
        "vdp_url": raw.get("vdp_url"),
    }


# Threshold tuning rationale:
# - SHARP_DROP_THRESHOLD_PCT: 15% chosen as the tipping point where a price
#   trajectory shifts from "ordinary asking-price softening" to "distress /
#   stale unit signal." Asymmetric — fires only on cumulative drops because
#   dealers triage drops more aggressively than rises. A cumulative price
#   RISE is informational (not flagged); rises are surfaced inline via the
#   trajectory table's price column rather than as a red flag.
# - MULTI_DEALER_CHURN_MIN: 4 chosen because 1–3 dealer rooftops over a
#   VIN's life is normal (original retail → trade-in → wholesale → resale).
#   4+ rooftops indicates either repeated wholesale flips or dealer-group
#   inventory replication; the latter is special-cased in the W3 reference's
#   stock_no-collision exception. The count uses dealer_id when available
#   (primary signal), with dealer_name as fallback for rows lacking an id.
SHARP_DROP_THRESHOLD_PCT = 15.0
MULTI_DEALER_CHURN_MIN = 4


def _derive_flags(listings: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    """Derive history-level flags + summary fields.

    F1 — input order is not trusted. We sort locally by
    `(last_seen_at_date desc, first_seen_at_date desc)` so `listings[0]` is
    always the most-recently-active listing, keeping the "current is
    listings[0]" invariant that the `decertified` flag depends on. The new
    sort fixes the prior false-positive case where a flash relisting with a
    recent first-seen but stale last-seen wrongly won the current slot over
    a continuously-refreshed older listing.

    F2 — the cumulative change field is signed: positive when price has
    dropped cumulatively, negative when it has risen. Renamed from
    `cum_drop_pct` to `cum_change_pct` to reflect the sign convention; the
    legacy alias is preserved for one release.

    F3 — dealer-hop count uses dealer_id when available (primary signal),
    with a dealer_name fallback for rows that lack an id. When some rows
    have id and others have only name, the name-to-id map merges
    name-only rows back into their corresponding id when the name matches a
    seen-with-id row. `dealer_count_source` surfaces provenance:
      "dealer_id"   — every named row had an id; count is strict-id
      "mixed"       — some rows had id, some only name; count is best-effort
      "dealer_name" — no row had an id; count is name-based (legacy fallback)

    F4 — `dropped_null_price_count` tracks rows skipped when computing
    `cum_change_pct` because their price was null. When > 0, the cum-change
    baseline shifted from oldest history row to oldest priced row.
    """
    flags: list[str] = []

    # Internal desc sort: last_seen primary, first_seen tiebreaker. Empty
    # dates sort to the end (treated as oldest) so they never steal the
    # "current" slot from a properly-dated listing.
    def _sort_key(l: dict[str, Any]) -> tuple[str, str]:
        return (l.get("last_seen_at_date") or "", l.get("first_seen_at_date") or "")

    listings_desc = sorted(listings, key=_sort_key, reverse=True)

    # F3: dealer-hop count — dealer_id-primary with name fallback.
    # Build a name → id map from rows that carry both fields. Lets us merge
    # rows that have only a dealer_name back to a known id when the name
    # matches.
    name_to_id: dict[str, Any] = {
        l["dealer_name"]: l["dealer_id"]
        for l in listings_desc
        if l.get("dealer_id") is not None and l.get("dealer_name")
    }

    def _dealer_key(l: dict[str, Any]) -> tuple[str, Any] | None:
        """Per-row canonical dealer key. Prefer dealer_id; cross-reference
        via name_to_id when the row has only a name; final fallback is the
        raw name. None when neither field is present."""
        if l.get("dealer_id") is not None:
            return ("id", l["dealer_id"])
        name = l.get("dealer_name")
        if name:
            if name in name_to_id:
                return ("id", name_to_id[name])
            return ("name", name)
        return None

    dealer_keys = {key for l in listings_desc if (key := _dealer_key(l)) is not None}
    dealer_count = len(dealer_keys)

    # Provenance of dealer_count: "dealer_id" when every named row carries
    # an id, "mixed" when some named rows lack id, "dealer_name" when no
    # row has an id (legacy fallback path).
    has_any_id = any(l.get("dealer_id") is not None for l in listings_desc)
    named_rows = [l for l in listings_desc if l.get("dealer_name")]
    all_named_have_id = all(l.get("dealer_id") is not None for l in named_rows) if named_rows else True
    if has_any_id and all_named_have_id:
        dealer_count_source = "dealer_id"
    elif has_any_id:
        dealer_count_source = "mixed"
    else:
        dealer_count_source = "dealer_name"

    if dealer_count >= MULTI_DEALER_CHURN_MIN:
        flags.append("multi_dealer_churn")

    # F2 + F4: cumulative change %. Sort priced rows ascending by
    # first_seen_at_date — "oldest baseline → newest" is genuinely a
    # creation-time semantic, not an active-time one (so we use first_seen
    # here, NOT last_seen).
    def _first_seen_key(l: dict[str, Any]) -> str:
        return l.get("first_seen_at_date") or ""

    priced_rows = [(_first_seen_key(l), l.get("price")) for l in listings_desc if l.get("price") is not None]
    dropped_null_price_count = len(listings_desc) - len(priced_rows)
    prices_asc = sorted(priced_rows, key=lambda t: t[0])

    cum_change_pct: float | None = None
    if len(prices_asc) >= 2:
        first_p = prices_asc[0][1]
        last_p = prices_asc[-1][1]
        if first_p and first_p > 0:
            cum_change_pct = (first_p - last_p) / first_p * 100.0
            if cum_change_pct >= SHARP_DROP_THRESHOLD_PCT:
                flags.append("sharp_drops")

    # Tri-state CPO-ever derivation. None when NO listing carries is_certified
    # at all (field absent across the whole history — common in real responses).
    # True when any listing explicitly has is_certified truthy. False when all
    # listings that DO carry the field have it explicitly 0.
    present = [l.get("is_certified") for l in listings_desc if l.get("is_certified") is not None]
    if not present:
        cpo_ever: bool | None = None
    elif any(present):
        cpo_ever = True
    else:
        cpo_ever = False

    # Decertified fires only when CPO-ever is definitively True AND the current
    # listing (listings_desc[0] post internal sort) is definitively non-CPO
    # (explicit False, not None — absent is "unknown", not "confirmed non-CPO").
    # The new last_seen-primary sort makes `current` the genuinely
    # most-recently-active row.
    current = listings_desc[0] if listings_desc else None
    if cpo_ever is True and current is not None and current.get("is_certified") is False:
        flags.append("decertified")

    return flags, {
        "dealer_count": dealer_count,
        "dealer_count_source": dealer_count_source,
        "cum_change_pct": cum_change_pct,   # F2 — signed (+ = dropped, − = rose)
        "cum_drop_pct": cum_change_pct,     # DEPRECATED alias; same numeric value
        "dropped_null_price_count": dropped_null_price_count,
        "cpo_ever": cpo_ever,
        "listings_desc": listings_desc,      # internal — consumer may want the sorted view
    }


def main(argv: list[str]) -> int:
    payload, source = read_input(argv)
    etype, emsg = classify_error(payload)
    if etype:
        emit({"ok": False, "error_type": etype, "error": emsg, "source": source})
        return 0

    # Real upstream shape (per mcp_server_tool_docs/get_car_history.md):
    #   {vin, num_found, listings: [...]}
    # NO {success, service, data} envelope on success — confirmed inconsistent
    # with every other MCP tool. The truncation envelope wrapper {result: ...}
    # is unwrapped upstream by `_common._maybe_unwrap`.
    #
    # Three input shapes accepted (defensive parser, ordered by likelihood):
    #   (1) upstream-direct: {vin, num_found, listings: [...]}              [REAL]
    #   (2) top-level list: payload itself is the list                      [legacy]
    #   (3) enveloped: {success, service, data: [...]} or
    #       {data: {listings: [...], num_found: ...}}                       [misread / future]
    num_found: int | None = None
    if isinstance(payload, list):
        listings_raw = payload
    elif isinstance(payload, dict):
        # Try shape (1) first: top-level `listings`
        listings_raw = payload.get("listings")
        if isinstance(listings_raw, list):
            # Got direct-upstream shape; pick up num_found at top level
            nf = payload.get("num_found")
            if isinstance(nf, (int, float)):
                num_found = int(nf)
        else:
            # Try shape (3): enveloped under `data`
            data_field = payload.get("data")
            if isinstance(data_field, list):
                listings_raw = data_field
            elif isinstance(data_field, dict):
                listings_raw = data_field.get("listings") or data_field.get("history") or []
                nf = data_field.get("num_found")
                if isinstance(nf, (int, float)):
                    num_found = int(nf)
            else:
                # Last-ditch: maybe `history` at top level
                listings_raw = payload.get("history") or []
        if not isinstance(listings_raw, list):
            listings_raw = []
    else:
        emit({
            "ok": False,
            "error_type": "unexpected_shape",
            "error": "payload is neither a list nor a dict",
            "source": source,
        })
        return 0

    listings = [_normalize_listing(l) for l in listings_raw if isinstance(l, dict)]
    flags, derived = _derive_flags(listings)

    vins = sorted({l["vin"] for l in listings if l.get("vin")})

    # Emit `listings` as the sorted-desc view so downstream consumers can
    # safely rely on `listings[0]` being the most-recently-active listing
    # regardless of the original MCP response order (F1 guarantee).
    listings_out = derived.pop("listings_desc", listings)

    emit({
        "ok": True,
        "vin": vins[0] if vins else None,
        "vins_seen": vins,
        "num_found": num_found,                                 # NEW — pagination-gap signal (None when absent)
        "listing_count": len(listings),
        "listings": listings_out,
        "dealer_count": derived["dealer_count"],
        "dealer_count_source": derived["dealer_count_source"],  # NEW — provenance label
        "cum_change_pct": derived["cum_change_pct"],            # F2 — signed (+ = dropped)
        "cum_drop_pct": derived["cum_drop_pct"],                # DEPRECATED alias
        "dropped_null_price_count": derived["dropped_null_price_count"],  # NEW — baseline-shift signal
        "cpo_ever": derived["cpo_ever"],
        "flags": flags,
        "source": source,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
