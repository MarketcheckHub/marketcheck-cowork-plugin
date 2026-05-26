---
name: sold-summary-safety
description: Parameter discipline and error-handling rules for `get_sold_summary` and `search_active_cars` calls in this skill. Covers both OEM (per-make) and dealer-group (per-canonical-name) call shapes. Includes §EV classification & PHEV double-counting and §Known invalid parameters.
type: reference
---

# `get_sold_summary` / `search_active_cars` safety rules

This skill uses only two MCP tools. Both have silent-failure modes this reference codifies — pipe responses through the matching parser (`parse_sold_summary.py` / `parse_search.py`) and the safety machinery is enforced.

The skill calls each tool in two modes: per-`make` for OEM tickers (F, GM, TM, HMC, STLA, TSLA, RIVN, LCID, HYMTF, NSANY, MBGAF, BMWYY, VWAGY) and per-`dealership_group_name` / `mc_dealership_group_name` for dealer-group tickers (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA). The rules below cover both call shapes; per-shape divergences are called out inline.

## `get_sold_summary` — empirical findings (load-bearing)

Three behaviors verified against the live API; misreading these is the most common source of bugs in this skill's predecessor.

### 1. `ranking_measure` controls sort order, NOT response columns

A single `get_sold_summary` call with `ranking_dimensions=make` (or `=dealership_group_name`), `top_n=1`, and a target filter returns one row per state per month with **all numeric columns** populated regardless of `ranking_measure`:

```
sold_count, average_sale_price, total_sale_price,
average_msrp, price_over_msrp_percentage,
average_days_on_market, median_days_on_market,
sale_price_range (string), sale_price_std_dev
```

Empirically verified on 2026-05-12 (Ford CA Used March 2025): calls with `ranking_measure=sold_count`, `ranking_measure=average_sale_price`, and `ranking_measure=price_over_msrp_percentage` returned byte-identical payloads apart from float-rounding noise in the 13th decimal place. `ranking_measure` only matters when `top_n` cuts the result set.

**Consequence:** the skill collapses Volume + Pricing + DOM + MSRP-gap extraction into ONE call per make per channel per multi-quarter window. Full-row normalization is the default; there is no "discard except sold_count" instruction.

### 2. National mode returns per-state rows, NOT one national row

With `summary_by="state"` (the default; this skill sets it explicitly) and no `state` filter, the response returns one row per US state for each (month, ranking_dimension) combination. Empirically: ~53 rows per single-month per-make call (50 states + DC + PR + GU + AS + MP, some null-priced).

**Consequence:** "National" is an aggregation responsibility on the parser side. `parse_sold_summary.py --aggregate-make-by-window <make>` and `--aggregate-group-by-window <canonical>` sum sold_count across state rows and compute sold-count-weighted means for ASP / DOM / MSRP positioning / avg_msrp.

### 3. Null-priced territories must be dropped from weighted means

Some sub-unit territories (MP, sometimes DC) return `null` for `average_sale_price`, `avg_msrp`, and `price_over_msrp_percentage` when `sold_count == 1`. Empirically observed in Ford Used March 2025: MP has 1 unit sold with `null` ASP and `null` MSRP positioning, but `average_days_on_market = 4`.

**Discipline:** the parser drops null-valued fields from **BOTH the numerator AND the denominator** of every weighted mean. The row's `sold_count` still contributes to `total_sold_count` (so the volume number is correct), but the row does not bias the weighted ASP toward zero or skew DOM.

## `get_sold_summary` — response shape (live)

The live response wraps rows in a **doubly-nested** `data.data[]` array (not the `data.results[]` the public tool doc shows). `parse_sold_summary.py` handles `data.data[]`, `data.results[]`, and `data.rows[]` shapes transparently.

```json
{
  "success": true,
  "service": "sold_summary",
  "data": {
    "success": true,
    "data": [
      {"month": "2026-04", "inventory_type": "New", "state": "TX",
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

- **`inventory_type`** — MUST be `"New"` or `"Used"` (TitleCase). Omitting causes a silent server default to `New`, which returns zero rows for Used-only groups (KMX is the only tracked Used-only ticker — see `references/inventory-type-classification.md`; **CVNA is classified `Both` per source even though New volume is ~0.4% of total, empirically verified 2026-05-13**). Always set this from the workflow's channel choice.
- **`limit`** — Always set `5000` (the upstream maximum). The tool's default is `1000` and **silently truncates** multi-dimensional results. Truncation is the single most common cause of missing-row bugs.
- **`summary_by`** — `"state"` (the default; set explicitly for clarity).
- **`ranking_measure`** — `"sold_count"` (this skill always ranks/aggregates by volume). Per Finding 1, this only affects sort order for the `top_n` cut; column set is the same regardless.
- **`ranking_dimensions`** — set per call purpose:
  - `"make"` for OEM target sold calls (filtered to one make via the `make` param + `top_n=1`)
  - `"dealership_group_name"` for dealer-group target sold calls (filtered to one group via `dealership_group_name` + `top_n=1`)
- **`top_n`** — `1` for filtered target calls (returns at most 1 row per state per month with the target dimension value).
- **`date_from`** / **`date_to`** — MUST be calendar-month-aligned: `date_from` = first day of a month, `date_to` = last day of a month. **Always use `compute_quarter_windows.py`** to generate the window. The local validator does NOT check alignment — mis-aligned days hit upstream and return HTTP 422.

## `get_sold_summary` — parameters to skip

- **`state`** — DO NOT set on any call in this skill. The skill is national-only; passing `state` would over-narrow. The parser sums across state rows.
- **`dealer_type`** — Including `dealer_type` with narrow filters returns empty rows for non-defective queries. Skip.
- **`dealership_group_name`** — Set only after `resolve_ticker.py` confirms the value is in the bundled 471-entry enum. The full 471-entry enum is NOT bundled in this skill; the 8 dealer-group canonical strings the resolver enforces live in `references/ticker-mapping.md`. Resolution validates enum membership BEFORE the MCP call; the >10 KB enum-mismatch error string from the tool is never reached.
- **`fuel_type_category`** — Set ONLY for EV-slice calls (value `"EV"`). See §"EV classification & PHEV double-counting" below for what `"EV"` actually filters.
- **`model`**, **`body_type`** (as filters, not as `ranking_dimensions`) — Skip. This skill never narrows by these.
- **Advanced operator filters** (`sold_count=">100"`, etc.) — Skip.

## EV classification & PHEV double-counting

`fuel_type_category` is **not a partition** — it's an **overlapping** classifier. PHEV nameplates appear under BOTH `"EV"` and `"Hybrid"` filter values.

**Empirical anchor (verified 2026-05-13, Toyota New April 2026):**

| Filter | Models returned (with national-summed `sold_count`) |
|---|---|
| `fuel_type_category="EV"` | `bZ` (2,595 — BEV), `RAV4 Plug-in Hybrid` (860 — **PHEV — also under Hybrid**), `Prius Plug-in Hybrid` (640 — **PHEV — also under Hybrid**), `bZ4X` (19 — BEV legacy naming), `Prius Prime` (3 — **PHEV — also under Hybrid**) |
| `fuel_type_category="Hybrid"` | `RAV4 Plug-in Hybrid`, `Prius Plug-in Hybrid`, `Prius Prime` (same per-state counts as EV filter), plus `RAV4` (Hybrid trim), `Prius` (HEV), `Camry`, `Avalon`, `Prius v`, `Prius c` |

Sum of `sold_count` for `RAV4 Plug-in Hybrid` under `EV` (~860 national, April 2026) matches sum under `Hybrid` (~806–860 within rounding) — PHEV rows are **duplicated** across both filters, not split.

**Definition the skill uses:**
- `fuel_type_category="EV"` returns **BEV ∪ PHEV** = the *electrified-vehicle* universe
- `fuel_type_category="Hybrid"` returns **HEV ∪ PHEV** = the *any-hybrid* universe
- `fuel_type_category="ICE"` returns ICE only — `[UNCERTAIN]` not directly verified, but follows from `BEV ∩ ICE = ∅`
- **Summing `EV + Hybrid + ICE` double-counts every PHEV unit.**

**The skill's EV signal = electrified-vehicle share** (BEV + PHEV via the `EV` filter). This matches the OEM-tracker convention and the standard equity-analyst framing of "electrified mix" / "EV transition." A future v1.1 could add a model-pattern filter to subtract PHEV nameplates for a BEV-only signal; v1 deliberately uses the wider definition.

## `get_sold_summary` — error-handling branches

The `parse_sold_summary.py` `error_type` catalogue (`make_model_not_found`, `validation_dimension_limit`, `validation`, `network_422`, `network_5xx`, `invalid_dimension`, `truncation_unrecovered`, `unknown`) and the per-error recovery branches live in **`references/script-contracts.md §parse_sold_summary`**. This heading remains as a back-link anchor.

**Never halt the whole workflow on a single `get_sold_summary` failure.** The workflow degrades gracefully — except when the failure removes the entire current-quarter headline for the target ticker, which IS a halt condition (see `references/_failure-recovery.md §Halt vs degrade`).

## `search_active_cars` — call shapes

This skill makes two shapes of `search_active_cars` call. Both run in Wave A2.

### OEM per-make active-inventory call

```python
search_active_cars(
    make="<Make>",                            # e.g., "Ford" — one call per make in makes[]
    car_type="new" | "used",                  # lowercase — opposite case from get_sold_summary.inventory_type
    stats="price,dom",                        # request server-computed stats
    rows=0,                                   # we want stats only
    price_range="1-*",                        # exclude null-price rows from num_found
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

Returns the standard `data.{num_found, start, rows, listings, seller_type, facets, stats}` shape with `data.stats.{price, dom}` populated.

### Dealer-group `mc_dealership_group_name` active-inventory call

```python
search_active_cars(
    mc_dealership_group_name="<canonical>",   # e.g., "AutoNation Inc." — triggers syndication routing
    car_type="used" | "new",
    stats="price,dom",
    rows=0,
    price_range="1-*",
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

#### Syndication routing — empirically verified

The MCP doc (`mcp_server_tool_docs/search_active_cars.md:144-150, 227, 305-307`) warns: any `mc_*` filter (including `mc_dealership_group_name`) routes the call to `/v2/dealerships/inventory` with possibly-different response shape; the doc notes that `facets` and `stats` "may not" be returned.

**Live verification on 2026-05-08** (Carmax test call): the syndication path DOES return the standard shape with full `data.stats.{price, dom}` blocks. Wire quirk: `data.start` and `data.rows` arrive as **strings** (`"0"`) on the syndication path. `parse_search.py` coerces both to int.

**Defensive fallback:** if a future API change drops the `data.stats` block, `parse_search.py` emits `{"ok": true, "stats_present": false, "num_found": N, "stats": null}` and the renderer surfaces a DQ event (d) instead of crashing.

### Payload-shaping discipline (both shapes)

Always pass these flags to keep the response small:
- `fetch_all_photos=False`
- `include_dealer_object=False`
- `include_mc_dealership_object=False`
- `include_build_object=False`

### Price-filter discipline

Always pass `price_range="1-*"`. The API silently excludes null-price rows from `stats.price.{mean, median, percentiles}` but counts them in `num_found`. `compute_earnings_signals.py` reads `num_found` as the active-inventory count for the days-supply ratio; without the filter, days-supply is biased upward by null-price rows. Empirically verified on 2026-05-12 (CarMax test pair): the filter changes `num_found` from 91614 → 91609 (5 null-price rows excluded) with no change to mean/median/percentiles.

## Known invalid parameters — do NOT pass

These parameter names are easy to introduce by mistake. The predecessor `earnings-preview` skill carried `seller_state` as a real bug; documenting these explicitly prevents regression.

| Wrong | Correct | Notes |
|---|---|---|
| `seller_state` | `state` | `search_active_cars` has no `seller_state` parameter. The unknown param is silently dropped by the tool, the query becomes national, and the caller thinks state filtering was applied. **This skill never sets `state` at all** (national-only) — the practical fix is: don't try to add either name to any call. |
| `inventory_type="new"` (lowercase) | `"New"` (TitleCase) | `get_sold_summary` accepts only `"New"` or `"Used"` exactly. Lowercase passes local validation in some configs (or returns zero rows silently). |
| `car_type="New"` (TitleCase) | `"new"` (lowercase) | `search_active_cars` accepts only `"new"`, `"used"`, `"certified"` lowercase. The case is opposite of `get_sold_summary`. |
| `dealership_group_name="CarMax"` | `"Carmax"` | The 471-entry enum has `Carmax` (single-token, lowercase-x). `CarMax` does NOT match. |
| `dealership_group_name="AutoNation"` | `"AutoNation Inc."` | Trailing period is part of the canonical name. Same for `Lithia Motors Inc.`, `Penske Automotive Group Inc.`, `Sonic Automotive Inc.`, `Group 1 Automotive Inc.` (`Asbury Automotive Group` is the trailing-period exception). |
| `fuel_type_category="BEV"` | `"EV"` | The enum is `ICE`/`EV`/`Hybrid`/`Unknown`/`Other`. There is no `BEV` value. To restrict to BEVs only, use `"EV"` and post-filter PHEV models by name — out of scope for v1 per §EV classification above. |

The resolver (`resolve_ticker.py`) enforces the dealer-group canonical strings at the boundary, so the `CarMax`/`AutoNation` mistakes can never reach `get_sold_summary` in this skill. The case-sensitivity and `seller_state` mistakes are guarded only by per-call discipline — hence this list.

## Case-sensitivity divergence between the two tools

| Tool | Parameter | Accepted values |
|---|---|---|
| `get_sold_summary` | `inventory_type` | `"New"`, `"Used"` (TitleCase) |
| `search_active_cars` | `car_type` | `"new"`, `"used"`, `"certified"` (lowercase) |

**Silent-failure risk:** passing `"new"` to `get_sold_summary.inventory_type` or `"New"` to `search_active_cars.car_type` returns zero rows without an error. The skill enforces the case translation at the wave-execution layer:
- `inventory_type` in the assembled JSON for `compute_earnings_signals.py` is TitleCase (`"New"` / `"Used"`).
- Wave A2 active-inventory calls translate the same channel to lowercase for `search_active_cars`.

## Upstream rate limit: ≤5 concurrent calls per sub-batch

**The upstream API at `api.marketcheck.com` rate-limits with `HTTP 429 Too Many Requests` when more than ~3-5 concurrent calls are in flight.** This is independent of the Claude Code runtime's `tool_use` concurrency cap (~20-30) — the upstream cap is much lower and trips first. Like the date-range cap, it is undocumented in the MCP wrapper and only surfaces at runtime.

### Verification (live trace, 2026-05-14)

Running `Get pre earnings of GM` (4 makes × 3 channels × 2 splits = 24 parallel `get_sold_summary` calls in a single agent message):

| Position in burst | Result |
|---|---|
| Calls 1-3 | ✓ 200 (responses persisted to disk by runtime) |
| Calls 4-24 | ✗ HTTP 429 — body: `Client error '429 Too Many Requests' for url '...'` |

Observed safe burst: ≥ 3. Observed failure point: ≥ 4. **Exact threshold between 3 and 5 — not empirically pinned.** No `Retry-After` header surfaced in the MCP error envelope.

### Required Wave A1 / Wave A2 sub-batching

**Every wave is decomposed into sub-batches of at most 5 concurrent `tool_use` blocks per agent message.** If the total wave call count exceeds 5, the orchestrator issues multiple sequential agent messages (each with ≤5 tool calls), waiting for all prior tool results before issuing the next.

The conservative default is **5 concurrent** (one step above the observed safe burst of 3). If a future re-test still trips 429 at 5, the documented fallback is **3 concurrent**, then **sequential (1 concurrent)** if even 3 fails. This file is the canonical location for the current value — update it AND `SKILL.md` AND `references/w1-channel-check.md` AND `mcp_server_tool_docs/get_sold_summary.md` in lockstep when adjusting.

### Wave A1 sub-batch breakdown (current value: 5 concurrent)

After the two-call date-split (§Required Wave A1 split), Wave A1 total = `2 × channels × makes`. Batched at 5:

| Ticker / classification | Wave A1 calls | Sub-batches |
|---|---|---|
| TSLA / RIVN / LCID (pure_play, 1 make, 2 channels) | 4 | 1 batch (4) |
| KMX (Used-only) | 4 | 1 batch (4) |
| AN / LAD / PAG / SAH / GPI / ABG / CVNA (Both) | 6 | 2 batches (5+1) |
| MBGAF (legacy, 1 make) | 6 | 2 batches (5+1) |
| F / TM / HMC / NSANY (legacy, 2 makes) | 12 | 3 batches (5+5+2) |
| BMWYY / HYMTF (legacy, 3 makes) | 18 | 4 batches (5+5+5+3) |
| GM (legacy, 4 makes) | 24 | 5 batches (5+5+5+5+4) |
| VWAGY (legacy, 5 makes) | 30 | 6 batches (5×6) |
| STLA (legacy, 7 makes) | 42 | 9 batches (8×5 + 1×2) |

Wave A2 (active inventory) sub-batches identically: total = `channels × makes`, batched ≤5.

### 429 handling within a sub-batch

If any call in a sub-batch returns 429:
- Log DQ event (a) for that call (channel + make + window).
- **Do NOT retry within the same workflow run** — retrying a 429 in the same sub-batch worsens the rate-limit pressure and is forbidden.
- Proceed with the remaining sub-batches.
- The merge step (Workstream 1 §Months-map merge) deals with whatever months ended up populated. If a whole channel's Call A or Call B was lost, the affected quarter aggregates land null and `compute_earnings_signals` degrades gracefully (`volume_momentum.degraded_to`, etc.).
- If 429 rate exceeds ~50% across a workflow run: drop the batch-size constant from 5 → 3 in this file + propagate to the other 3 docs. That's a one-line change.

### Inter-batch delay (6 seconds)

Sub-batches fire sequentially separated by an **explicit 6-second sleep**, not by the "natural" tool_use round-trip pause. The round-trip pause is empirically ~1-2 seconds — below the upstream rate-limiter's recovery window. Without the explicit delay, multi-sub-batch waves regularly trip 429 in the 3rd-4th sub-batch even though each individual sub-batch is within the 5-concurrent cap.

**Empirical anchor (BMWYY trace, 2026-05-14):** 18 Wave A1 calls across 4 sub-batches at 5/5/5/3 concurrency with no inter-batch delay. Sub-batches 1, 2, 4 succeeded; sub-batch 3 hit 429 on all 5 calls (Rolls-Royce Used A/B + BMW EV A/B + MINI EV A). Sub-batch 4 succeeded again — confirming a momentary rate-limiter saturation in the gap, not a persistent ceiling.

**Implementation:** between sub-batches, the model issues a standalone agent message containing `Bash(sleep 6)`. The first sub-batch in a Wave (A1 or A2) skips the sleep. The Wave A1 → Wave A2 boundary DOES get the 6-second sleep — A2's first sub-batch is treated as "after A1's last".

**Fallback ladder (if 6s still trips 429s):** 6 → 8 → 10 seconds. Update this value in lockstep with `SKILL.md §Parallelization` and `references/w1-channel-check.md §Wall-clock budget`.

**429 retries are still forbidden within a workflow** (per §429 handling within a sub-batch above — unchanged). The delay is preventive; the no-retry rule remains the backstop when prevention fails.

## Upstream date-range constraint: ≤12 months per call

**The upstream API at `api.marketcheck.com/api/v1/sold-vehicles/summary` rejects any request whose `date_to − date_from > 12 calendar months` with `HTTP 422` (response body: `'422 unknown'`).** This constraint is:

- **Not enforced** by the MCP wrapper (`tools/sold_summary_tools.py:573-619` lists every local validator; date-range is not among them).
- **Not documented** in `mcp_server_tool_docs/get_sold_summary.md` (silent at the doc layer; the doc only claims "up to 5 years of history" which is true only when sliced).
- **Only surfaces at runtime** as a generic `'422 unknown'` from the upstream, with no useful error body.

### Verification (live MCP probe, 2026-05-14)

Probed against `make=Tesla, inventory_type=New, ranking_dimensions=make, top_n=1, limit=5000, summary_by=state`:

| Span | `date_from` → `date_to` | Result |
|---|---|---|
| 12 mo | 2025-05-01 → 2026-04-30 | ✓ success |
| 13 mo | 2025-04-01 → 2026-04-30 | ✗ HTTP 422 |
| 16 mo | 2025-01-01 → 2026-04-30 | ✗ HTTP 422 |

Threshold is strictly between 12 and 13 months. **All Wave A1 calls in this skill MUST be sized so `date_to − date_from ≤ 12 months`.**

### Required Wave A1 split (two calls per channel)

The skill needs monthly data from `year_ago_quarter` (3 mo) + `prior_quarter` (3 mo) + `current_quarter` (3 mo) + `most_recent_complete_month` (1 mo). A 6-month calendar gap sits between `year_ago_quarter.date_to` and `prior_quarter.date_from`, fixed by the quarterly cadence. A single call covering all four windows would be 15-17 months → 422. The only correct design is **two calls per channel**:

| Call | `date_from` | `date_to` | Span | Useful months captured |
|---|---|---|---|---|
| **A** (year-ago) | `year_ago_quarter.date_from` | `year_ago_quarter.date_to` | 3 mo | 3 (year_ago_q only) |
| **B** (prior → mrcm) | `prior_quarter.date_from` | `max(current_quarter.date_to, mrcm.date_to)` | ≤8 mo | 7 (prior_q + current_q + 1–2 mrcm months) |

The orchestrator unions Call A's and Call B's monthly aggregates into a single `make_by_window.months: {...}` map before passing to `compute_earnings_signals.py`. See `references/w1-channel-check.md §Wave A1` for the assembled-input shape and `§Months-map merge` for the union step.

**Verification of Call B max span across calendar dates** (run via `compute_quarter_windows.py --today <date>`):

| `today` | current_quarter | mrcm | Call B span | Months |
|---|---|---|---|---|
| 2026-04-01 | Q1 2026 | March 2026 | 2025-10-01 → 2026-03-31 | 6 |
| 2026-05-13 | Q1 2026 | April 2026 | 2025-10-01 → 2026-04-30 | 7 |
| 2026-06-30 | Q1 2026 | May 2026 | 2025-10-01 → 2026-05-31 | 8 |
| 2026-07-01 | Q2 2026 | June 2026 | 2026-01-01 → 2026-06-30 | 6 |
| 2026-09-15 | Q2 2026 | August 2026 | 2026-01-01 → 2026-08-31 | 8 |

Worst case: 8 months — safely under the 12-month cap.

## Row-count budget (5000-row server cap)

With `summary_by="state"` (~53 state rows in the US national universe), `top_n=1`, and the parameters above:

| Call shape | Months | top_n | Rows | Raw size | Verdict |
|---|---|---|---|---|---|
| Per-make sold, Call A (year_ago_quarter only) | 3 | 1 | ~159 | ~15-30 KB | SAFE |
| Per-make sold, Call B (prior → mrcm) | 6–8 | 1 | ~318–424 | ~50-100 KB | SAFE |
| Per-group sold, Call A | 3 | 1 | ~159 | ~15-30 KB | SAFE |
| Per-group sold, Call B | 6–8 | 1 | ~318–424 | ~50-100 KB | SAFE |
| Per-make EV slice, Call A | 3 | 1 | ~159 (often fewer) | ~10-20 KB | SAFE |
| Per-make EV slice, Call B | 6–8 | 1 | ~318–424 (often fewer) | ~30-70 KB | SAFE |

Both calls are well under the 5000-row server cap and well under the 12-month upstream cap. **No 6-month-gap over-fetch** (vs. the discarded earlier single-call design): the orchestrator deliberately skips the 6 months between year_ago_quarter and prior_quarter by issuing two narrow calls.

The mrcm-month aggregate is captured inside Call B (its date_to extends to `mrcm.date_to`). `compute_earnings_signals._extract_mrcm_sold` reads the mrcm month from the merged `months: {...}` map for the Days Supply formula: `days_supply = num_found × days_in_month / sold_count_mrcm`.

## MCP tool naming convention (project-wide)

`SKILL.md` and the wave specs reference the tools as `mcp__marketcheck__get_sold_summary` and `mcp__marketcheck__search_active_cars`. The actual MCP tools available in this environment are `mcp__claude_ai_MarketCheck_MCP_V2__get_sold_summary` and `mcp__claude_ai_MarketCheck_MCP_V2__search_active_cars`. The shorthand is the project-wide convention; the model translates the name at call time. This is consistent across all 9 plugins.

## `search_active_cars` — `facets` mode is NOT used by this skill

The brand-orphan / unknown-group recovery branch present in both reference skills (`oem-stock-tracker` uses `facets="make|0|100"`, `dealer-group-health-monitor` uses `facets="mc_dealership_group_name|0|1000"`) is **deliberately omitted** from this skill. The 21-ticker map is fixed and resolution is exact-or-halt. Unknown tickers do not trigger facet-discovery; they halt with: *"`<X>` is not one of the 21 tracked tickers — add via `references/ticker-mapping.md` if you want to extend coverage."*

If a future v1.1 expands ticker coverage, the `parse_search.py --mode facets` machinery is already byte-identical-reused from the OEM tracker and would just need a SKILL.md recovery branch added.

## Parameters that are deliberately unused

- **Per-workflow facet discovery** — see preceding section.
- **`year`, `model`, `trim`** — VIN-level filtering is out of scope (route to `competitive-pricer` or `vehicle-appraiser`).
- **`zip` / `radius` / `state`** — Ticker-level analysis is national, not local.
- **`is_certified`** — CPO analysis is out of scope for v1 (see SKILL.md §"What this skill does NOT do").
