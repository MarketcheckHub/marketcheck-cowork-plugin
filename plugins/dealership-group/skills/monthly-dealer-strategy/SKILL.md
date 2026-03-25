---
name: monthly-dealer-strategy
description: >
  Comprehensive monthly market intelligence. Triggers: "monthly review",
  "monthly strategy", "monthly dealer report", "strategic review",
  "monthly market analysis", "end of month analysis", "what's my market
  doing this month", "monthly performance", "strategic briefing",
  market share, depreciation trends, market conditions, full inventory
  intelligence.
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Monthly Dealer Strategy — Comprehensive Market Intelligence Report

A strategic monthly analysis that gives a dealer group the complete picture: how their brands are performing in the market, which models are depreciating fastest, what the broader market trends look like, and a full inventory intelligence report. Run this on the first Monday of each month.

**Architecture:** This skill uses up to 3 parallel sub-agents to generate the 5-section report. Brand analytics, market demand, and lot composition run simultaneously.

**Note: This skill is primarily US-focused.** Most sections require `get_sold_summary` which is US-only. UK locations will receive a supply-side market overview only.

## Dealer Group Profile (Load First)

Load the `marketcheck-profile.md` project memory file. If missing, prompt `/onboarding` and stop.

**Extract ALL locations from `dealer_group.locations[]`.** For each location record: `name`, `dealer_id`, `dealer_type`, `franchise_brands`, `zip` (US) or `postcode` (UK), `state` (US) or `region` (UK), `web_domain`, `country`. Extract group-level preferences: `default_radius_miles` (→ `radius`), `target_margin_pct` (→ `target_margin`), `recon_cost_estimate` (→ `recon_cost`), `floor_plan_cost_per_day`, `max_acceptable_dom` (→ `max_dom`), `dom_aging_threshold` (→ `aging_threshold`).

**Location scope:** If a specific location name is provided, match to `locations[].name` and run for that location only. If "all" or no argument, iterate through EVERY location — all execution steps below run for each location using **that location's own** `dealer_id`, `zip`/`postcode`, `state`/`region`, `dealer_type`, `franchise_brands`, and `country`. Never pass one location's zip, state, or brands to a different location's agent or API call.

**Inventory type:** Read `preferences.default_inventory_type` from profile (`"used"` | `"new"` | `"both"`; default `"used"` if not set). Apply as `inventory_type` / `car_type` in all agent spawns and direct API calls for every location. If the user specifies a different type, override. Never mix new and used data in the same report section.

**Tool routing per location:** US: all agents. UK: Wave 3 (Supply-Side Overview) only. Calculate date ranges from `# currentDate`: `current_month`, `prior_month`, `three_months_ago`. Confirm: "Running monthly strategy for: [location name(s)] | Inventory: [used/new/both]"

### Group Monthly Rollup

```
GROUP MONTHLY STRATEGY — [Group Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BRAND PERFORMANCE (group-wide)
  [Aggregate brand share across all locations' states]
  [Highlight franchise brands with ★]

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

## Execution: Multi-Agent Orchestration

### Wave 1 — Launch Simultaneously (US)

Launch these three agents **in parallel** using the Agent tool. All are independent.

**For each location, spawn agents using THAT location's values (do not reuse values across locations):**

**Agent A: `lot-scanner` (facets-only mode)**

Use the Agent tool to spawn the `dealership-group:lot-scanner` agent with this prompt:

> Pull lot composition for dealer_id=[**this location's** dealer_id], country=[**this location's** country], mode=facets_only. Use rows=0 with facets=make|0|10|1,model|0|20|1 and stats=price,dom. Return the top 5 make/model combinations by count and overall lot statistics. Location label: [**this location's** name].

**Agent B: `market-demand-agent`**

Use the Agent tool to spawn the `dealership-group:market-demand-agent` agent with this prompt:

> Generate full inventory intelligence for state=[**this location's** state], dealer_type=[**this location's** dealer_type], zip=[**this location's** zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Date range: [current_month date_from] to [current_month date_to]. Run sections: ds_ratios, turn_rates. Also include body type breakdown. Location label: [**this location's** name].

**Agent C: `brand-market-analyst`**

Use the Agent tool to spawn the `dealership-group:brand-market-analyst` agent with this prompt:

> Analyze brand performance and market trends for state=[**this location's** state], dealer_type=[**this location's** dealer_type], franchise_brands=[**this location's** franchise_brands]. Current month: [current_month dates]. Prior month: [prior_month dates]. Three months ago: [three_months_ago dates]. Run sections: brand_share, market_trends. Skip depreciation (will provide lot models in Wave 2). Location label: [**this location's** name].

### Wave 2 — After Lot Scanner Completes

Once `lot-scanner` returns the top 5 make/model combos from the location's lot:

**Run depreciation watch directly** (or spawn brand-market-analyst again):

For each of the top 5 models from **this location's** lot-scanner output, call `mcp__marketcheck__get_sold_summary` with:
- `make`, `model`: the model
- `state`: **this location's** state
- `inventory_type`: `Used`
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `top_n`: `1`
- Two calls per model: current_month dates AND three_months_ago dates
→ **Extract only**: per model — average_sale_price (current and baseline). Discard full response.

Calculate:
- Price Change $ = current avg_sale_price - baseline avg_sale_price
- Monthly Depreciation Rate % = (Price Change / baseline) / 3 x 100
- Flag models with monthly depreciation > 1.5% as **ACCELERATING DEPRECIATION**

### Wave 3 — Supply-Side Overview (US + UK)

This simple single call can run after Wave 1 completes or in parallel with Wave 2.

**US:** Call `mcp__marketcheck__search_active_cars`
**UK:** Call `mcp__marketcheck__search_uk_active_cars`

With:
- `zip`/`postcode`: **this location's** zip/postcode
- `radius`: from preferences
- `car_type`: `used`
- `facets`: `make|0|20|1,body_type|0|10|1`
- `stats`: `price,dom`
- `rows`: `0`
→ **Extract only**: total count, avg price (stats), avg DOM (stats), make facets, body_type facets. Discard full response.

### UK Execution Path

For UK locations, only run:
1. Wave 3 (Supply-Side Overview) using `search_uk_active_cars`
2. Note: "Sections 1-4 require US sold data and are not available for UK locations."

### Assembly — Combine All Results

1. **Section 1 (Brand Performance)** — from `brand-market-analyst` agent output
2. **Section 2 (Depreciation Watch)** — from Wave 2 depreciation calculations + lot-scanner facets
3. **Section 3 (Market Trends)** — from `brand-market-analyst` agent output
4. **Section 4 (Inventory Intelligence)** — from `market-demand-agent` agent output
5. **Section 5 (Supply-Side Overview)** — from Wave 3

## Output

Present: 5-section report (Brand Performance share table, Depreciation Watch for lot models, Market Trends with fastest-depreciating models, Inventory Intelligence with D/S ratios and aging, Supply-Side Overview), followed by a 5-item 30-day action plan with dollar impact and key metrics to watch next month.
