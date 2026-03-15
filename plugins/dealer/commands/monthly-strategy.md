---
description: Monthly strategic report — market share, depreciation, trends, inventory intelligence (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: []
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

Monthly dealer strategy report using parallel sub-agents. Triggers `monthly-dealer-strategy` skill.

## Step 1: Verify dealer profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter. Missing -> "Run `/onboarding` first." Stop. Extract all fields.

**Speed rule — profile-read-once:** Pass the extracted profile fields (dealer_id, source, country, zip/postcode, state/region, radius, aging_threshold, dealer_type, franchise_brands) directly to all sub-agents in their prompt. Sub-agents should NOT re-read the profile.

**Tool routing:** US = all agents. UK = lot-scanner only (supply overview). Calculate date ranges: current_month, prior_month, three_months_ago.

## Step 2: Wave 1 -- 3 agents in parallel (US)

**Agent A: `lot-scanner`** (facets-only) -- Spawn `dealer:lot-scanner`: lot composition for dealer_id, mode=facets_only, rows=0. Return top 5 make/model combos.

**Agent B: `market-demand-agent`** -- Spawn `dealer:market-demand-agent`: inventory intelligence for state, dealer_type, zip, radius. Sections: ds_ratios, turn_rates.

**Agent C: `brand-market-analyst`** -- Spawn `dealer:brand-market-analyst`: brand performance for state, franchise_brands. Current/prior/three-months-ago dates. Sections: brand_share, market_trends.

## Step 3: Wave 2 -- Depreciation watch

After lot-scanner returns top 5 models: call `get_sold_summary` twice per model (current month + 3 months ago) with `ranking_measure=average_sale_price`. Calculate monthly depreciation rate. Flag >1.5%/month.

## Step 4: Wave 3 -- Supply-side overview (US + UK)

`search_active_cars` (US) or `search_uk_active_cars` (UK): `zip`, `radius`, `car_type=used`, `facets=make|0|20|1,body_type|0|10|1`, `stats=price,dom`, `rows=0`. **UK:** Only this step. Skip Steps 2-3.

## Step 5: Assemble report

Sections: Brand Performance, Depreciation Watch, Market Trends, Inventory Intelligence, Supply-Side Overview. 30-day action plan (5 actions ranked by $ impact). Key metrics to watch next month.
