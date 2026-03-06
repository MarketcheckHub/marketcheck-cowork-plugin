---
name: monthly-dealer-strategy
description: >
  This skill should be used when the user asks for a "monthly review",
  "monthly strategy", "monthly dealer report", "strategic review",
  "monthly market analysis", "end of month analysis", "what's my market
  doing this month", "monthly performance", "strategic briefing",
  or needs a comprehensive monthly analysis covering market share,
  depreciation trends, market conditions, and full inventory intelligence.
---

# Monthly Dealer Strategy — Comprehensive Market Intelligence Report

A strategic monthly analysis that gives a dealer group the complete picture: how their brands are performing in the market, which models are depreciating fastest, what the broader market trends look like, and a full inventory intelligence report. Run this on the first Monday of each month.

**Architecture:** This skill uses up to 3 parallel sub-agents to generate the 5-section report. Brand analytics, market demand, and lot composition run simultaneously.

**Note: This skill is primarily US-focused.** Most sections require `get_sold_summary` which is US-only. UK locations will receive a supply-side market overview only.

## Dealer Group Profile (Load First)

Load `~/.claude/marketcheck/dealership-group-profile.json`. If missing, prompt `/onboarding` and stop. Ask: location or 'all' for group rollup. Extract from location: `dealer_id`, `dealer_name`, `dealer_type`, `franchise_brands`, `zip`, `state`; from profile: `country`, `radius`, `target_margin`, `recon_cost`, `floor_plan_per_day`, `max_dom`, `aging_threshold`. US: all agents. UK: `lot-scanner` only (Section 5 only). Calculate date ranges: current_month, prior_month, three_months_ago. Confirm location.

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

**Agent A: `lot-scanner` (facets-only mode)**

Use the Agent tool to spawn the `dealership-group:lot-scanner` agent with this prompt:

> Pull lot composition for dealer_id=[dealer_id], country=US, mode=facets_only. Use rows=0 with facets=make|0|10|1,model|0|20|1 and stats=price,dom. Return the top 5 make/model combinations by count and overall lot statistics.

**Agent B: `market-demand-agent`**

Use the Agent tool to spawn the `dealership-group:market-demand-agent` agent with this prompt:

> Generate full inventory intelligence for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Date range: [current_month date_from] to [current_month date_to]. Run sections: ds_ratios, turn_rates. Also include body type breakdown.

**Agent C: `brand-market-analyst`**

Use the Agent tool to spawn the `dealership-group:brand-market-analyst` agent with this prompt:

> Analyze brand performance and market trends for state=[state], dealer_type=[dealer_type], franchise_brands=[brands list]. Current month: [current_month dates]. Prior month: [prior_month dates]. Three months ago: [three_months_ago dates]. Run sections: brand_share, market_trends. Skip depreciation (will provide lot models in Wave 2).

### Wave 2 — After Lot Scanner Completes

Once `lot-scanner` returns the top 5 make/model combos from the location's lot:

**Run depreciation watch directly** (or spawn brand-market-analyst again):

For each of the top 5 models, call `mcp__marketcheck__get_sold_summary` with:
- `make`, `model`: the model
- `state`: from selected location
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
- `zip`/`postcode`: from selected location
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
