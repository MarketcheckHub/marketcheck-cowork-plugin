---
description: Monthly strategic report — market share, depreciation, trends, inventory intelligence, per-location and group rollup (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: [location name or "all"]
---

Run the monthly dealer strategy report using parallel sub-agents. This command triggers the `monthly-dealer-strategy` skill. Supports per-location analysis or group rollup.

## Step 1: Verify dealer group profile

Read `~/.claude/marketcheck/dealership-group-profile.json`.

- If **missing**: "No dealer group profile found. Run `/onboarding` first." Then stop.
- If **exists**: Extract all fields from `dealer_group` and `preferences`.

## Step 2: Determine scope

Check $ARGUMENTS:

- If a location name is provided: match it and use that location
- If "all" or empty: ask "Run monthly strategy for which location? Or 'all' for group rollup?"
  - Specific location: use that location's context
  - 'All': run per-location, then append GROUP MONTHLY ROLLUP

**Tool routing:** US = all agents. UK = lot-scanner only (Section 5 supply overview).

Calculate date ranges: current_month, prior_month, three_months_ago.

Confirm: "Running monthly strategy for **[location name or group name (all)]**..."

## Step 3: Per-location — Wave 1 (US, launch 3 agents in parallel)

**Agent A: `lot-scanner` (facets-only)**

Spawn `dealership-group:lot-scanner` with prompt:
> Pull lot composition for dealer_id=[dealer_id], country=US, mode=facets_only. Use rows=0 with facets for make/model. Return top 5 make/model combos by count.

**Agent B: `market-demand-agent`**

Spawn `dealership-group:market-demand-agent` with prompt:
> Generate inventory intelligence for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius]. Date range: [current month]. Sections: ds_ratios, turn_rates.

**Agent C: `brand-market-analyst`**

Spawn `dealership-group:brand-market-analyst` with prompt:
> Analyze brand performance and market trends for state=[state], dealer_type=[dealer_type], franchise_brands=[brands]. Current month: [dates]. Prior month: [dates]. Three months ago: [dates]. Sections: brand_share, market_trends.

## Step 4: Per-location — Wave 2 (depreciation watch)

After `lot-scanner` returns top 5 models, run depreciation analysis:

For each model, call `mcp__marketcheck__get_sold_summary` twice (current month + 3 months ago) with `ranking_measure=average_sale_price`. Calculate monthly depreciation rate. Flag >1.5%/month.

## Step 5: Per-location — Wave 3 (supply-side overview, US + UK)

Call `search_active_cars` (US) or `search_uk_active_cars` (UK) with `zip`, `radius`, `car_type=used`, `facets=make|0|20|1,body_type|0|10|1`, `stats=price,dom`, `rows=0`.

**UK locations**: Only run this step. Skip Steps 3-4.

## Step 6: Assemble per-location report

```
MONTHLY DEALER STRATEGY REPORT — [Location Name] — [Month Year]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Section 1: Brand Performance — from brand-market-analyst]
[Section 2: Depreciation Watch — from Wave 2]
[Section 3: Market Trends — from brand-market-analyst]
[Section 4: Inventory Intelligence — from market-demand-agent]
[Section 5: Supply-Side Overview — from Wave 3]

30-DAY ACTION PLAN:
1-5. [Actions ranked by $ impact]

Key Metrics to Watch Next Month:
- Market share, aging units, average DOM targets
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Step 7: Group monthly rollup (if "all" locations)

```
GROUP MONTHLY STRATEGY — [Group Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BRAND PERFORMANCE (group-wide)
  [Aggregate brand share across all locations' states]
  [Highlight franchise brands]

LOCATION SCORECARD
Location         | Units | Avg DOM | Aged % | D/S Ratio | Depreciation Risk | Health
-----------------|-------|---------|--------|-----------|-------------------|-------
[per location]

STRATEGIC PRIORITIES
1. [Group-level strategic recommendation]
2. [Second]
3. [Third]

NEXT MONTH FOCUS
  [What to watch for, acquisitions to pursue, categories to shift]
```
