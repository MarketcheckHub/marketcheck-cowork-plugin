---
name: sold-summary-safety
description: Parameter discipline and error-handling rules for `get_sold_summary` and `search_active_cars` calls in this skill. Hard-won safety guards from the original `dealer-group-health-monitor`'s production usage.
type: reference
---

# `get_sold_summary` / `search_active_cars` safety rules

This skill uses only two MCP tools. Both have silent-failure modes that this reference codifies — pipe responses through the matching parser (`parse_sold_summary.py` / `parse_search.py`) and the safety machinery is enforced.

## `get_sold_summary` — response shape (live)

The live response wraps rows in a **doubly-nested** `data.data[]` array (not the `data.results[]` the public tool doc shows). `parse_sold_summary.py` handles both shapes transparently.

```json
{
  "success": true,
  "service": "sold_summary",
  "data": {
    "success": true,
    "data": [
      {"month": "2026-04", "inventory_type": "Used", "state": "TX",
       "dealership_group_name": "Carmax", "rank": 1,
       "sold_count": 2069, "average_sale_price": 19750.72,
       "avg_msrp": 20004.03, "sale_price_range": "34991.0",
       "sale_price_std_dev": "6978.24", "average_days_on_market": 38.1,
       "median_days_on_market": 35.0, ...},
      ...
    ]
  }
}
```

**Field-name quirks** (server's actual names, not the doc's idealized names):
- `avg_msrp` (NOT `average_msrp`)
- `sale_price_range` — single string (e.g., `"34991.0"`), NOT a low/high pair
- `sale_price_std_dev` (NOT `standard_deviation`)
- `rank` — present on every row when `ranking_dimensions` is set

`parse_sold_summary.py` normalises these to canonical names for downstream consumers.

**Envelope quirk:** `get_sold_summary` is the **only** MCP tool that's NOT envelope-wrapped — its payload arrives as the direct `{success, service, data}` shape, no `{"result": "<stringified>"}` wrapper. The shared `_common._maybe_unwrap` helper passes unwrapped payloads through transparently.

## `get_sold_summary` — always-set parameters

- **`inventory_type`** — MUST be `"Used"` or `"New"` (title case). Omitting defaults upstream to silent New, which returns zero rows for Used-only groups (KMX, CVNA). Always set this from the workflow's `primary_channel` / `secondary_channel`.
- **`limit`** — Always set `5000` (the upstream maximum). The tool's default is `1000` and **silently truncates** multi-dimensional results. Truncation is the single most common cause of missing-row bugs.
- **`summary_by`** — `"state"` (the default; set explicitly for clarity).
- **`ranking_measure`** — `"sold_count"` (this skill always ranks/aggregates by volume).
- **`ranking_dimensions`** — `"dealership_group_name"` for target-group filters and peer leaderboards. `"body_type"` or `"make"` for W1's optional Wave B mix calls.
- **`top_n`** — `1` for target-group calls (the response is already filtered to that group), `20` for peer leaderboards.
- **`date_from`** / **`date_to`** — MUST be calendar-month-aligned: `date_from` = first day of a month, `date_to` = last day of a month. The tool's local validator does NOT check this — mis-aligned days pass local validation and hit upstream, which rejects with HTTP 422. **Always use `compute_month_windows.py` to generate the window.**

## `get_sold_summary` — parameters to skip

- **`state`** — DO NOT set on any call in this skill. We always want per-group totals across all states; passing `state` would over-narrow. The parser sums across state rows.
- **`dealer_type`** — Including `dealer_type` with narrow filters returns empty rows for non-defective queries. Skip.
- **`dealership_group_name`** — Set only after `resolve_group_name.py` confirms the value is in the bundled 471-entry enum. Resolution enforces this; the call site never bypasses.
- **`fuel_type_category`** — Skip (not relevant to this skill).
- **Advanced operator filters** (`sold_count=">100"`, etc.) — Skip.

## `get_sold_summary` — error-handling branches

> Moved. The `parse_sold_summary.py` `error_type` catalogue (`make_model_not_found`, `validation_dimension_limit`, `validation`, `network_422`, `network_5xx`, `invalid_dimension`, `truncation_unrecovered`, `unknown`) and the per-error recovery branches are now in **`references/script-contracts.md §parse_sold_summary`**. The heading remains here as a back-link anchor.

**Never halt the whole workflow on a single `get_sold_summary` failure.** The workflow degrades gracefully — missing peer leaderboard means no peer rank but the headline still renders; missing prior month means MoM is null but current-month KPIs still render.

## `search_active_cars` — active-inventory call shape

This skill makes only one shape of `search_active_cars` call:

```python
search_active_cars(
    mc_dealership_group_name="<canonical>",   # triggers syndication routing (see below)
    car_type="used" | "new",                   # set per primary/secondary channel
    stats="price,dom",                         # request server-computed stats
    rows=0,                                    # we want stats only
    price_range="1-*",                         # exclude null-price rows from num_found (the API excludes them from stats.price either way, but counts them in num_found, biasing any downstream num_found consumer)
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

### Syndication routing — empirically verified

`mcp_server_tool_docs/search_active_cars.md:144-150, 227, 305-307` warns: any `mc_*` filter (including `mc_dealership_group_name`) routes the call to `/v2/dealerships/inventory` with possibly-different response shape; the doc notes that `facets` and `stats` "may not" be returned.

**Live verification on 2026-05-08** (Carmax test call): the syndication path DOES return the standard shape with full `data.stats.{price,dom}` blocks. Specifically:

```json
{
  "success": true,
  "service": "car_search",
  "data": {
    "num_found": 91041,
    "start": "0",                         // STRING, not int — wire quirk
    "rows": "0",                          // STRING, not int — wire quirk
    "listings": [],
    "seller_type": "dealer",
    "facets": {},
    "stats": {
      "price": {"min": ..., "max": ..., "mean": ..., "median": ..., "stddev": ...,
                "count": ..., "percentiles": {"5.0": ..., "25.0": ..., "50.0": ...,
                                              "75.0": ..., "90.0": ..., "95.0": ..., "99.0": ...}},
      "dom":   {"min": 1, "max": 2224, "mean": 108.31, "median": 79.67, "stddev": 102,
                "count": 91041, "percentiles": {...}}
    }
  }
}
```

**Wire quirk:** `data.start` and `data.rows` arrive as strings on the syndication path. `parse_search.py` coerces both to int.

**Defensive fallback:** if a future API change drops the `data.stats` block, `parse_search.py` emits `{"ok": true, "stats_present": false, "num_found": N, "stats": null}` and the renderer surfaces a DQ event "active inventory stats unavailable; rendering num_found only" instead of crashing or fabricating values.

### `search_active_cars` — payload-shaping discipline

Always pass these flags to keep the response small:
- `fetch_all_photos=false` — every listing's `media.photo_links[]` is truncated to one URL otherwise; we skip listings entirely (`rows=0`) so this matters less, but stay on for safety.
- `include_dealer_object=false` — we don't render dealer details.
- `include_mc_dealership_object=false` — same.
- `include_build_object=false` — we don't render vehicle specs.
- `include_finance=false` / `include_lease=false` / `include_relevant_links=false` — we don't render finance / lease / supplementary links.

These reduce payload size and token consumption.

### `search_active_cars` — price-filter discipline

Always pass `price_range="1-*"` on the stats-only call. The API silently excludes null-price rows from `stats.price.{mean, median, percentiles}` but counts them in `num_found`. `compute_group_stats.py:204` reads `num_found` as the active-inventory count for `days_supply = num_found × days_in_month / sold_count` — without the filter, the days-supply ratio is biased upward by however many null-price rows the upstream returned (typically ≤1% on syndication-routed group queries, but unverified on long-tail groups). Empirically verified on 2026-05-12 (CarMax test pair): the filter changes `num_found` from 91614 → 91609 (5 null-price rows excluded) with no change to mean/median/percentiles.

## `search_active_cars` — facet-discovery call (recovery branch only)

This second shape is used ONLY by the SKILL.md "Before you start" recovery branch when `resolve_group_name.py` returns `no_candidates`. It is NOT part of the W1/W2/W3 waves.

```python
search_active_cars(
    facets="mc_dealership_group_name|0|1000",  # full active-facet universe (~400 names)
    rows=0,                                     # we want facets only, no listings
    country="US",
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

**Why `limit=1000`, not `20`:** `1000` is the doc-stated upper bound for the facet `limit`. The active-facet universe is ~400 distinct groups today, so 1000 captures all of them with headroom. A smaller limit (e.g., 20) would return only the giants (Lithia, AutoNation, Carmax, etc.) — ~80% of listings but only ~5% of distinct names — and the long-tail regional / private groups that are the most common source of fuzzy-resolution misses would never be surfaced. Payload at 1000 entries ≈ 40 KB, which is comfortably within the MCP envelope and fires only on the cold path.

**Live-verified response shape (2026-05-11):** standard route (no `mc_*` filter → no syndication routing). Returns:

```json
{
  "success": true,
  "service": "car_search",
  "data": {
    "num_found": 6069613,
    "start": "0",                // STRING wire quirk — coerced by parser
    "rows": "0",                  // STRING wire quirk — coerced by parser
    "listings": [],
    "seller_type": "dealer",
    "facets": {
      "mc_dealership_group_name": [
        {"item": "Lithia Motors Inc.", "count": 114368},
        {"item": "AutoNation Inc.",     "count":  98880},
        {"item": "Carmax",              "count":  91521},
        {"item": "Berkshire Hathaway Automotive", "count": 37787},
        ...
      ]
    },
    "stats": {}                   // empty dict — no stats requested
  }
}
```

Pipe through:
```
parse_search.py --mode facets
```

Output:
```json
{
  "ok": true,
  "num_found": 6069613,
  "facet_field": "mc_dealership_group_name",
  "facets": [
    {"item": "Lithia Motors Inc.", "count": 114368},
    ...
  ]
}
```

The skill (in SKILL.md) compares the `facets[]` list to the user's input — pick the 3-5 closest matches and present them as live-market alternatives. Important: a name returned by this facet call may NOT be in the bundled `dealership_group_enum.md` (the active-cars facet space drifts from the sold-summary enum). If the user picks a facet name that doesn't round-trip through `resolve_group_name.py` (exact match against the bundled enum), halt cleanly with a "no sold-summary aggregates for this group" message — do NOT fire `get_sold_summary` with a non-enum name (the tool returns a ~10 KB error string on enum miss).

## Parameters that are deliberately unused

- **Per-workflow facet discovery** — the W1/W2/W3 waves never call facets. The only facet usage is the cold-path recovery branch above.
- **`year`, `make`, `model`, `trim`** — VIN-level filtering is out of scope (route to `competitive-pricer-updated` or `vehicle-appraiser-updated`).
- **`zip` / `radius`** — group-level analysis is national, not local. We don't scope by ZIP.
