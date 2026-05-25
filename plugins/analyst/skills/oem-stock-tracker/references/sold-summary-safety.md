---
name: sold-summary-safety
description: Parameter discipline and error-handling rules for get_sold_summary and search_active_cars calls in this skill. Includes the empirical findings (column set invariant to ranking_measure, national mode returns per-state rows, null-priced territories) and case-sensitivity divergence between the two tools.
type: reference
---

# `get_sold_summary` / `search_active_cars` safety rules

This skill uses only two MCP tools. Both have silent-failure modes this reference codifies — pipe responses through the matching parser (`parse_sold_summary.py` / `parse_search.py`) and the safety machinery is enforced.

## `get_sold_summary` — empirical findings (load-bearing)

Three empirically-confirmed behaviors that the original `oem-stock-tracker` skill misread:

### 1. `ranking_measure` controls sort order, NOT response columns

A single `get_sold_summary` call with `make=<Make>`, `ranking_dimensions=make`, `top_n=1` returns one row per state with **all 14 numeric columns** populated regardless of `ranking_measure`:

```
sold_count, average_sale_price, total_sale_price,
average_msrp, price_over_msrp_percentage, average_days_on_market,
median_days_on_market, sale_price_range (string), sale_price_std_dev
```

Empirically verified on 2026-05-12 (Ford CA Used March 2025): calls with `ranking_measure=sold_count`, `ranking_measure=average_sale_price`, and `ranking_measure=price_over_msrp_percentage` returned byte-identical payloads apart from float-rounding noise in the 13th decimal place. `ranking_measure` only matters when `top_n` cuts the result set (e.g., `ranking_measure=sold_count, top_n=25` returns the top-25 makes BY sold_count).

**Consequence:** Step 2 (sold_count), Step 3 (ASP), Step 6 (DOM) — all three "metric extractions" in the original SKILL.md — collapse into ONE call per make per window. The "discard full response" instruction in the original is obsolete; full-row normalization is the default.

### 2. National mode returns per-state rows, NOT one national row

With `summary_by="state"` (default) and no `state` filter, the response returns one row per US state for each (month, ranking_dimension) combination. Empirically: ~53 rows per single-month per-make call (50 states + DC + PR + GU + AS + MP, some null-priced).

**Consequence:** "National" is an aggregation responsibility on the parser side. `parse_sold_summary.py --aggregate-make` sums sold_count across state rows and computes sold-count-weighted means for ASP / DOM / MSRP positioning / avg_msrp. See `references/multi-make-aggregation.md` for the math.

### 3. Null-priced territories must be dropped from weighted means

Some sub-unit territories (MP, sometimes DC) return `null` for `average_sale_price`, `avg_msrp`, and `price_over_msrp_percentage` when `sold_count == 1`. Empirically observed in Ford Used March 2025: MP has 1 unit sold with `null` ASP and `null` MSRP positioning, but `average_days_on_market = 4`.

**Discipline:** the parser drops null-valued fields from **BOTH the numerator AND the denominator** of every weighted mean. The row's `sold_count` still contributes to `total_sold_count` (so the volume number is correct), but the row does not bias the weighted ASP toward zero or skew DOM. See `multi-make-aggregation.md` for the exact math.

## `get_sold_summary` — response shape (live)

The live response wraps rows in a **doubly-nested** `data.data[]` array (not `data.results[]` the public tool doc shows). `parse_sold_summary.py` handles both shapes (and `data.rows[]`) transparently.

```json
{
  "success": true,
  "service": "sold_summary",
  "data": {
    "success": true,
    "data": [
      {"month": "2026-04", "inventory_type": "Used", "state": "TX",
       "make": "Ford", "rank": 1,
       "sold_count": 24809, "average_sale_price": 28173.60,
       "avg_msrp": 28252.85, "sale_price_range": "266805.0",
       "sale_price_std_dev": "16834.72", "price_over_msrp_percentage": -0.28,
       "average_days_on_market": 44.13, "median_days_on_market": 21},
      ...
    ]
  }
}
```

**Field-name quirks** (server's actual names, not the doc's idealized names):
- `avg_msrp` (NOT `average_msrp`)
- `sale_price_range` — single string value (e.g., `"266805.0"`), NOT a low/high pair
- `sale_price_std_dev` (NOT `standard_deviation`)
- `rank` — present on every row when `ranking_dimensions` is set

`parse_sold_summary.py` normalises these to canonical names for downstream consumers.

**Envelope quirk:** `get_sold_summary` is the **only** MCP tool that's NOT envelope-wrapped — its payload arrives as the direct `{success, service, data}` shape, no `{"result": "<stringified>"}` wrapper. The shared `_common._maybe_unwrap` helper passes unwrapped payloads through transparently.

## `get_sold_summary` — always-set parameters

- **`inventory_type`** — MUST be `"New"` or `"Used"` (TitleCase). Omitting causes a silent server default (returns zero rows for Used queries in some configurations). Always set this from the workflow's `inventory_type` (default `"New"`, user-overrideable to `"Used"`).
- **`limit`** — Always set `5000` (the upstream maximum). The tool's default is `1000` and **silently truncates** multi-dimensional results. Truncation is the single most common cause of missing-row bugs.
- **`summary_by`** — `"state"` (the default; set explicitly for clarity).
- **`ranking_dimensions`** — set per the call's purpose:
  - `"make"` for per-make sold (filtered to one make via `make` param + `top_n=1`)
  - `"make"` for market-share top-25 (no `make` filter + `top_n=25`)
  - `"make"` for EV market leaders (pure-play substitute — `fuel_type_category="EV"` + no `make` filter + `top_n=10`)
  - `"body_type"` for segment-mix calls (one per make + `top_n=10`)
- **`ranking_measure`** — `"sold_count"` (this skill always ranks/aggregates by volume). The empirical finding above means this only affects sort order for the `top_n` cut; column set is the same regardless.
- **`top_n`** — set per the call's purpose:
  - `1` for filtered per-make calls (returns at most 1 row per state per month).
  - `25` for market-share (returns top-25 makes per state per month).
  - `10` for EV market leaders and segment mix.
- **`date_from`** / **`date_to`** — MUST be calendar-month-aligned: `date_from` = first day of a month, `date_to` = last day of a month. **Always use `compute_month_windows.py`** to generate the window. The local validator does NOT check alignment — mis-aligned days hit upstream and return HTTP 422.

## `get_sold_summary` — parameters to skip

- **`state`** — DO NOT set on any call in this skill. The skill is national-only; passing `state` would over-narrow. The parser sums across state rows.
- **`dealer_type`** — Including `dealer_type` with narrow filters returns empty rows for non-defective queries. Skip.
- **`dealership_group_name`** — NOT used by this skill. (Dealer-group analysis is `dealer-group-health-monitor`'s job.)
- **`fuel_type_category`** — Set to `"EV"` for the EV slice and EV market leaders calls. Skip on all other calls.
- **Advanced operator filters** (`sold_count=">100"`, etc.) — Skip.
- **`model`**, **`body_type`** (as filters, not as `ranking_dimensions`) — Skip. We aggregate by these via `ranking_dimensions`, not narrow by them.

## Row-count budget (5000-row server cap)

With `summary_by="state"` (~53 state rows in the US national universe) and the parameters above:

| Call shape | M months | top_n | Rows | Verdict |
|---|---|---|---|---|
| Per-make sold (1 make filter, multi-month) | 4 | 1 | ~212 | SAFE |
| Per-make EV slice (1 make + fuel filter, multi-month) | 4 | 1 | ~212 | SAFE |
| Market share (no make filter, single month) | 1 | 25 | ~1,325 | SAFE |
| Market share (multi-month) | 2 | 25 | ~2,650 | SAFE |
| Market share (multi-month) | 4 | 25 | ~5,300 | **OVER LIMIT — split into 2 calls** |
| EV market leaders (no make, fuel filter, multi-month) | 2 | 10 | ~1,060 | SAFE |
| Segment mix per make (single month) | 1 | 10 | ~530 | SAFE |

**Multi-month no-make-filter safe `top_n` ceiling** = `floor(5000 / (M × 53))`. For M=4 → `top_n ≤ 23`. For M=2 → `top_n ≤ 47`. For M=3 → `top_n ≤ 31`.

The skill therefore uses **2 separate single-month market-share calls** (current, prior) rather than one M=2 multi-month call at `top_n=25` — keeping the parser invocation pattern simple and the row count well within the budget.

## Case-sensitivity divergence between the two tools

| Tool | Parameter | Accepted values |
|---|---|---|
| `get_sold_summary` | `inventory_type` | `"New"`, `"Used"` (TitleCase) |
| `search_active_cars` | `car_type` | `"new"`, `"used"`, `"certified"` (lowercase) |

**Silent-failure risk:** passing `"new"` to `get_sold_summary.inventory_type` or `"New"` to `search_active_cars.car_type` returns zero rows without an error. The skill enforces the case translation at the wave-execution layer:
- `inventory_type` in the assembled JSON for `compute_oem_stats.py` is TitleCase (`"New"` / `"Used"`).
- Wave A2 active-inventory calls translate the same channel to lowercase for `search_active_cars`.

This is documented in `SKILL.md §Before you start` step 4 and in the per-call audit table.

## MCP tool naming convention (project-wide)

SKILL.md and the wave specs reference the tools as `mcp__marketcheck__get_sold_summary` and `mcp__marketcheck__search_active_cars`. The actual MCP tools available in this environment are `mcp__claude_ai_MarketCheck_MCP_V2__get_sold_summary` and `mcp__claude_ai_MarketCheck_MCP_V2__search_active_cars`. The shorthand is the project-wide convention; the model translates the name at call time. This is consistent across all 9 plugins.

## `search_active_cars` — active-inventory call shape (per-make)

```python
search_active_cars(
    make="<Make>",                            # e.g., "Ford"
    car_type="new" | "used",                  # follows user's inventory_type choice
    stats="price,dom",                        # request server-computed stats
    rows=0,                                   # we want stats only
    price_range="1-*",                        # exclude null-price rows from num_found
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

### Defensive fallback

If a future API change drops the `data.stats` block, `parse_search.py` emits `{"ok": true, "stats_present": false, "num_found": N, "stats": null}` and the renderer surfaces a DQ event (d) "active inventory stats unavailable; rendering num_found only" instead of crashing.

### Wire quirks

`data.start` and `data.rows` arrive as strings (`"0"`) on some routing paths. `parse_search.py` coerces both to int.

### Price-filter discipline

Always pass `price_range="1-*"` on the stats-only call. The API silently excludes null-price rows from `stats.price.{mean, median, percentiles}` but counts them in `num_found`. Without the filter, the days-supply ratio is biased upward by null-price rows. Empirically verified on 2026-05-12: the filter changed `num_found` by ≤5 rows on a 91,000-row Ford active call.

## `search_active_cars` — facet-discovery call (brand-orphan recovery only)

This shape is used ONLY by the SKILL.md "Before you start" brand-orphan recovery branch when `resolve_oem.py` returns `no_candidates`. It is NOT part of W1/W2/W3 waves.

```python
search_active_cars(
    facets="make|0|100",                     # full active make universe (~80 makes)
    rows=0,                                  # facets only, no listings
    country="US",
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

**Why `limit=100`:** The active US-market make universe is ~80 distinct makes (luxury + mass + new EV entrants). `100` captures all of them with headroom. Payload ≈ 4 KB, comfortably within the MCP envelope.

Pipe through `parse_search.py --mode facets`. Output is a sorted-by-count list of `{item: <make>, count: <listings>}` records that the SKILL.md recovery branch then ranks by string similarity to the user's input.

## Parameters that are deliberately unused

- **Per-workflow facet discovery on make** — the W1/W2/W3 waves never call facets. The only facet usage is the cold-path brand-orphan recovery branch above.
- **`year`, `model`, `trim`** — VIN-level filtering is out of scope (route to `competitive-pricer` or `vehicle-appraiser`).
- **`zip` / `radius` / `state`** — OEM-level analysis is national, not local. We don't scope by ZIP or state.
- **`is_certified`** — CPO analysis is out of scope for v1.
