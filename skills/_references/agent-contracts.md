# Agent Contracts — Input/Output Reference

> **Progressive disclosure:** Skills reference this file via `→ Agent contracts: read _references/agent-contracts.md`. Read on-demand when you need exact input parameters, output formats, or error handling for an agent — the skill's workflow section covers the spawn prompt.

## lot-scanner

**Purpose:** Pull a dealer's complete inventory with automatic pagination.

**Spawn:** `marketcheck-cowork-plugin:lot-scanner`

**Input parameters (in prompt):**
- `dealer_id` (required) — MarketCheck dealer ID
- `country` (required) — `US` or `UK`
- `car_type` — default `used`
- `sort_by` / `sort_order` — default `dom` / `desc`
- `dom_range` — e.g., `60-999` for aging units only
- `mode` — `full`, `aging`, `facets_only`, `stats_only`

**Output (returned to caller):**
- `total_count`, `pages_fetched`, `page_size`, `pagination_status` (`complete` or `partial`)
- `file_path` — TOON file at `/tmp/marketcheck/lot-scan-[dealer_id]-[timestamp].toon`
- Top 10 aging units (highest DOM) as inline TOON table
- Make/model facet summary with counts
- Price stats: min, max, mean, median
- DOM stats: min, max, mean, median

**Error handling:** If `pagination_status=partial`, warn user that not all inventory was captured. If page 1 fails twice, agent stops entirely.

**UK:** Uses `search_uk_active_cars` instead of `search_active_cars`. Same output format.

---

## lot-pricer

**Purpose:** Batch-price a list of VINs against market using `predict_price_with_comparables`.

**Spawn:** `marketcheck-cowork-plugin:lot-pricer`

**Input parameters (in prompt):**
- Vehicle list from lot-scanner (pass top N by DOM)
- `zip` (required) — dealer ZIP
- `dealer_type` — default `franchise`; prices against BOTH types
- `floor_plan_per_day` — default `$35`
- `aging_threshold` — default `60`

**Output:**
- Pricing table in TOON format: `pricing[N]{vin,year,make,model,trim,listed_price,predicted_price,price_gap,comparables_count}`
- Summary: above/at/below counts, REDUCE NOW count, wholesale candidates, total floor plan burn
- Top 3 actions by dollar impact

**Classification:**
- Below Market: gap < -5%
- At Market: gap -5% to +5%
- Above Market: gap > +5%

**Actions:** REDUCE NOW (gap >+10% AND DOM > threshold), REDUCE (>+5%), HOLD (±5%), RAISE (<-5% AND DOM <30), CONSIDER WHOLESALE (±5% AND DOM >90)

**UK:** NOT available. Price inline using comp median from `search_uk_active_cars`.

---

## market-demand-agent

**Purpose:** Market demand analytics — sold velocity, D/S ratios, stocking hot lists, turn rates.

**Spawn:** `marketcheck-cowork-plugin:market-demand-agent`

**Input parameters (in prompt):**
- `state` (required) — 2-letter code
- `zip` (required) — for supply radius
- `dealer_type` — default from profile
- `radius` — default 50
- `target_margin_pct` — default 15
- `recon_cost` — default 1500
- `date_from` / `date_to` (required) — analysis month
- `sections` — `hot_list`, `demand_snapshot`, `ds_ratios`, `turn_rates`, `all`

**Output:**
- Hot list: rank, make/model, turn days, sold count, supply, D/S ratio, max buy price, on lot?
- Demand snapshot: top models + body type breakdown
- D/S ratios: top under-supplied and over-supplied
- Turn rates by body type

**D/S thresholds:** Under-supplied >1.5, Balanced 0.8-1.5, Over-supplied <0.8

**US-only.** Returns error message for UK.

---

## brand-market-analyst

**Purpose:** Brand share analysis, depreciation watch, market trends (fastest depreciating, MSRP parity).

**Spawn:** `marketcheck-cowork-plugin:brand-market-analyst`

**Input parameters (in prompt):**
- `state` (required) — 2-letter code
- `dealer_type` — from profile
- `franchise_brands` — for highlighting and MSRP parity
- `current_month` / `prior_month` (required) — `{date_from, date_to}`
- `three_months_ago` — for depreciation baseline
- `top_lot_models` — top 5 from lot-scanner, needed for Section 2
- `sections` — `brand_share`, `depreciation`, `market_trends`, `all`

**Output (TOON format):**
- Section 1 (Brand Performance): `brand_share[N]{make,sold_count,share_pct,share_change_bps,volume_change_pct,trend}`
- Section 2 (Depreciation Watch): per-model monthly depreciation rate, ACCELERATING flag if >1.5%/month
- Section 3 (Market Trends): fastest depreciating statewide + MSRP parity for franchise brands

**Note:** Sections can be requested selectively. Depreciation (Section 2) requires `top_lot_models` from lot-scanner — skip if not provided.

**US-only.** Returns error message for UK.

---

## group-scanner

**Purpose:** Scan inventory across multiple dealer locations in parallel.

**Spawn:** `marketcheck-cowork-plugin:group-scanner`

**Input:**
- `locations` (required) — array of `{dealer_id, name, zip, state, dealer_type, country}`
- `mode` — `facets_only`, `facets_and_aging`, `full`
- `aging_threshold` — default 60

**Output:** Per-location summaries + group-level aggregation (total units, aged units, average DOM, price stats by location).

**Works for both US and UK.**

---

## portfolio-scanner

**Purpose:** Process multiple VINs for batch decode + pricing + supply checks.

**Spawn:** `marketcheck-cowork-plugin:portfolio-scanner`

**Input:** VIN list, use case (auction prep / revalue / pricing), location from profile.

**Output:** Per-VIN results (decoded specs, predicted price, supply count, verdict) + aggregate summary.

**UK:** Partial — no decode, no predict. Uses comp search only.

---

## cohort-benchmarking-agent

**Purpose:** Benchmark dealer groups against the full ~400 dealer group industry cohort with quintile scoring.

**Spawn:** `marketcheck-cowork-plugin:cohort-benchmarking-agent`

**Input:** Date ranges (4 time periods), target groups to score.

**Output:** Quintile thresholds (P20/P40/P60/P80) for 6 KPIs + target group values positioned within the distribution.

**US-only.** Requires `get_sold_summary` with `top_n=500`.
