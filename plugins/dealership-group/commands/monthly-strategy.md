---
description: Monthly strategic report — market share, depreciation, trends, inventory intelligence, per-location and group rollup (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: [location name or "all"]
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

Monthly dealer strategy report using parallel sub-agents. Per-location or group rollup.

## Step 1: Verify dealer group profile

Read `~/.claude/marketcheck/dealership-group-profile.json`. Missing -> "Run `/onboarding` first." Stop. Extract all fields.

## Step 2: Determine scope

$ARGUMENTS: location name -> match. "all" or empty -> ask. **Tool routing:** US = all agents. UK = lot-scanner only (supply overview). Calculate date ranges: current_month, prior_month, three_months_ago.

## Step 3: Per-location Wave 1 -- 3 agents in parallel (US)

**Agent A: `lot-scanner`** (facets-only) -- Spawn `dealership-group:lot-scanner`: lot composition, mode=facets_only, rows=0. Top 5 make/model combos.

**Agent B: `market-demand-agent`** -- Spawn `dealership-group:market-demand-agent`: inventory intelligence for state, dealer_type, zip, radius. Sections: ds_ratios, turn_rates.

**Agent C: `brand-market-analyst`** -- Spawn `dealership-group:brand-market-analyst`: brand performance for state, franchise_brands. Current/prior/three-months-ago dates. Sections: brand_share, market_trends.

## Step 4: Per-location Wave 2 -- Depreciation watch

After lot-scanner returns top 5 models: `get_sold_summary` twice per model (current + 3 months ago), `ranking_measure=average_sale_price`. Flag depreciation >1.5%/month.

## Step 5: Per-location Wave 3 -- Supply-side overview (US + UK)

`search_active_cars` (US) or `search_uk_active_cars` (UK): `zip`, `radius`, `car_type=used`, facets, stats. **UK:** Only this step.

## Step 6: Per-location report

Sections: Brand Performance, Depreciation Watch, Market Trends, Inventory Intelligence, Supply-Side Overview. 30-day action plan (5 actions by $ impact).

## Step 7: Group monthly rollup (if "all")

Group-wide brand performance. Location scorecard: units, avg DOM, aged %, D/S ratio, depreciation risk, health. 3 strategic priorities. Next month focus areas.
