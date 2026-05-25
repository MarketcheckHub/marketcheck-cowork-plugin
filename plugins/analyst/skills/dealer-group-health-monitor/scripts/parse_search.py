#!/usr/bin/env python3
"""
parse_search.py — Normalise a `search_active_cars` response.

Two modes:

* `--mode stats` (default) — the active-inventory health call: targets a
  single canonical group via `mc_dealership_group_name`, `rows=0`,
  `stats=price,dom`. Emits `{num_found, stats_present, stats}`.

* `--mode facets` — the recovery-path facet-discovery call: no group
  filter, `facets=mc_dealership_group_name|0|N`, `rows=0`. Emits
  `{num_found, facets: [{item, count}, ...]}` from
  `data.facets.mc_dealership_group_name`. Used by the SKILL.md
  no-candidates recovery branch to suggest live-market group names when
  `resolve_group_name.py` fuzzy-fails.

Stats-mode response shape verified live on 2026-05-08 (Carmax): standard
`data.{num_found, start, rows, listings, seller_type, facets, stats}`. The
syndication-routing warning in `mcp_server_tool_docs/search_active_cars.md`
is conservative — stats DO come back.

Facets-mode response shape verified live on 2026-05-11: standard route
returns `data.facets.mc_dealership_group_name` as an array of
`{item, count}` objects sorted desc by count; `data.stats` is `{}` when
no stats requested.

Wire quirk (both modes): `data.start` and `data.rows` arrive as strings on
the syndication path (e.g., "0" not 0). The parser coerces both to int.

Defensive fallback (stats mode only): if the `data.stats` block is absent,
the parser emits `stats_present: false, stats: null` so the renderer can
surface a Data Quality event instead of crashing.

Usage:
  parse_search.py                              # stats mode, stdin
  parse_search.py --file <path>                # stats mode, truncation envelope
  parse_search.py --mode facets                # facet mode, stdin
  parse_search.py --mode facets --file <path>  # facet mode, truncation envelope

Output JSON (stats mode):
  {
    "ok": true,
    "num_found": 91041,
    "start": 0,
    "rows": 0,
    "stats_present": true,
    "stats": {
      "price": {min, max, count, missing, mean, stddev, median, percentiles{...}},
      "dom":   {...}
    }
  }

Output JSON (facets mode):
  {
    "ok": true,
    "num_found": 6069613,
    "start": 0,
    "rows": 0,
    "facets": [
      {"item": "Lithia Motors Inc.", "count": 114368},
      {"item": "AutoNation Inc.",     "count":  98880},
      ...
    ]
  }

Or on error:
  {"ok": false, "error_type": "...", "error": "...", "source": "..."}
"""

from __future__ import annotations

import sys
from typing import Any

from _common import read_input, emit, classify_error, arg_value


def _to_int(v: Any) -> int | None:
    """Coerce string/int → int. Returns None on failure (avoids crashes on
    the syndication-path string quirk where data.start='0', data.rows='0')."""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _normalize_stats_block(block: Any) -> dict[str, Any] | None:
    """Normalise a single stats block (e.g. data.stats.price). Coerces
    numeric fields; preserves percentiles dict.
    """
    if not isinstance(block, dict):
        return None
    out: dict[str, Any] = {
        "min":     _to_float(block.get("min")),
        "max":     _to_float(block.get("max")),
        "count":   _to_int(block.get("count")),
        "missing": _to_int(block.get("missing")),
        "mean":    _to_float(block.get("mean")),
        "stddev":  _to_float(block.get("stddev")),
        "median":  _to_float(block.get("median")),
    }
    pcts = block.get("percentiles")
    if isinstance(pcts, dict):
        out["percentiles"] = {
            k: _to_float(v) for k, v in pcts.items()
        }
    else:
        out["percentiles"] = None
    return out


def _normalize_facet_list(raw: Any) -> list[dict[str, Any]]:
    """Normalise a facet array. Each entry is `{item, count}` per the
    `search_active_cars` facet response. Missing item → skip; missing count
    → 0. Sorted desc by count (the server already does this, but we sort
    defensively in case of upstream variance)."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        item = entry.get("item")
        if not isinstance(item, str) or not item.strip():
            continue
        count = _to_int(entry.get("count")) or 0
        out.append({"item": item, "count": count})
    out.sort(key=lambda r: r["count"], reverse=True)
    return out


def main(argv: list[str]) -> int:
    mode = (arg_value(argv, "--mode") or "stats").lower()
    if mode not in ("stats", "facets"):
        emit({"ok": False, "error_type": "usage",
              "error": f"--mode must be 'stats' or 'facets'; got {mode!r}",
              "source": None})
        return 0

    payload, source = read_input(argv)

    # Transport-level error classification
    etype, emsg = classify_error(payload)
    if etype:
        emit({"ok": False, "error_type": etype, "error": emsg, "source": source})
        return 0

    if not isinstance(payload, dict):
        emit({"ok": False, "error_type": "unexpected_shape",
              "error": f"payload not a dict: {type(payload).__name__}",
              "source": source})
        return 0

    data = payload.get("data")
    if not isinstance(data, dict):
        emit({"ok": False, "error_type": "unexpected_shape",
              "error": "data field missing or not a dict", "source": source})
        return 0

    num_found = _to_int(data.get("num_found")) or 0
    start = _to_int(data.get("start")) or 0
    rows = _to_int(data.get("rows")) or 0

    if mode == "facets":
        facets_block = data.get("facets") if isinstance(data.get("facets"), dict) else {}
        # The recovery branch targets mc_dealership_group_name specifically.
        # If callers ever ask for other facet fields, we still expose the
        # one they asked for via the FacetName below; today there is only
        # one facet field in play.
        facet_field = "mc_dealership_group_name"
        facet_list = _normalize_facet_list(facets_block.get(facet_field))
        emit({
            "ok": True,
            "num_found": num_found,
            "start": start,
            "rows": rows,
            "facet_field": facet_field,
            "facets": facet_list,
            "source": source,
        })
        return 0

    # mode == "stats"
    stats_raw = data.get("stats") if isinstance(data.get("stats"), dict) else None

    if not stats_raw:
        # Defensive fallback: stats absent. Future API change protection.
        emit({
            "ok": True,
            "num_found": num_found,
            "start": start,
            "rows": rows,
            "stats_present": False,
            "stats": None,
            "source": source,
        })
        return 0

    stats = {
        "price": _normalize_stats_block(stats_raw.get("price")),
        "dom":   _normalize_stats_block(stats_raw.get("dom")),
    }

    emit({
        "ok": True,
        "num_found": num_found,
        "start": start,
        "rows": rows,
        "stats_present": True,
        "stats": stats,
        "source": source,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
