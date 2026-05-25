#!/usr/bin/env python3
"""
parse_predict.py — Normalise a `predict_price_with_comparables` response.

Real response shape (confirmed by live MCP call 2026-04-28):

  {
    "success": true,
    "service": "price_prediction",
    "data": {
      "marketcheck_price": <float>,
      "msrp": <float>,
      "comparables":        {"num_found": N, "listings": [...], "stats": {price, miles, dos_active}},
      "recent_comparables": {"num_found": N, "listings": [...], "stats": {price, miles, dos_active}}
    }
  }

This parser extracts only what's consumed downstream:
  - `marketcheck_price` — the MarketCheck Price scalar (the ML predicted price)
  - `comparables_n` / `recent_comparables_n` — counts of the comp pools the
    model used (rendered as MC-Price comp counts in the output)
  - `comparables_price_stats` / `recent_comparables_price_stats` — server-computed
    price distribution (min/p25/median/p75/max/mean/stddev/percentiles) over each
    comp pool. Rendered as MC-Price comp distribution sub-lines.

Listings arrays, MSRP, and miles/dos_active stats from the predict response are
intentionally NOT parsed — predict-listings lack `dealer_type`/`is_certified`/build
metadata and so cannot drive `channel_stats` or CPO detection (those flow from
search comps via parse_search.py). MSRP is preferred from decode. Miles/dos_active
distributions are not surfaced.

Usage:
  parse_predict.py                   # stdin
  parse_predict.py --file <path>     # truncation envelope (common path)

Emits on stdout:
  {
    "ok": true,
    "marketcheck_price": <float>,
    "comparables_n": <int>,                          # server-reported num_found
    "recent_comparables_n": <int>,                   # server-reported num_found
    "comparables_price_stats": {...} | null,         # server stats.price block, verbatim
    "recent_comparables_price_stats": {...} | null,  # server stats.price block, verbatim
    "source": "stdin" | "file:<path>"
  }

  On failure: {"ok": false, "error_type": "...", "error": "...", "source": ...}

Failure modes:
  - missing_price            — marketcheck_price absent (and no fallback alias matches)
  - truncation_unwrap_failed — envelope file unparseable (from _common)
  - network / upstream / network_422 / network_5xx — from _common.classify_error
  - unexpected_shape         — payload not a dict
"""

from __future__ import annotations

import sys
from typing import Any

from _common import read_input, emit, classify_error


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


def _price_stats(block: Any) -> dict[str, Any] | None:
    """Pull `block.stats.price` verbatim with shape guards.

    Returns None when the block is malformed or stats.price is absent — the
    renderer reads None as "skip the price-distribution sub-line." Mirrors the
    defensive `isinstance(..., dict) else {}` pattern in parse_search.py for
    server `stats` passthrough.
    """
    if not isinstance(block, dict):
        return None
    stats = block.get("stats")
    if not isinstance(stats, dict):
        return None
    price = stats.get("price")
    return price if isinstance(price, dict) else None


def _num_found(block: Any) -> int | None:
    """Pull `block.num_found` with shape guards. Returns None on absence."""
    if not isinstance(block, dict):
        return None
    return _to_int(block.get("num_found"))


def main(argv: list[str]) -> int:
    payload, source = read_input(argv)
    etype, emsg = classify_error(payload)
    if etype:
        emit({"ok": False, "error_type": etype, "error": emsg, "source": source})
        return 0

    # Predict response is envelope-wrapped: {success, service, data: {marketcheck_price, ...}}.
    # Fall back to flat top-level shape for backward-compatibility with any pre-envelope variant.
    if not isinstance(payload, dict):
        emit({"ok": False, "error_type": "unexpected_shape", "error": "payload not a dict", "source": source})
        return 0
    data = payload["data"] if isinstance(payload.get("data"), dict) else payload

    mkt_price = (
        _to_float(data.get("marketcheck_price"))
        or _to_float(data.get("predicted_price"))
        or _to_float(data.get("price"))
    )
    if mkt_price is None:
        emit({
            "ok": False,
            "error_type": "missing_price",
            "error": "marketcheck_price not present in response",
            "source": source,
        })
        return 0

    emit({
        "ok": True,
        "marketcheck_price": mkt_price,
        "comparables_n": _num_found(data.get("comparables")),
        "recent_comparables_n": _num_found(data.get("recent_comparables")),
        "comparables_price_stats": _price_stats(data.get("comparables")),
        "recent_comparables_price_stats": _price_stats(data.get("recent_comparables")),
        "source": source,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
