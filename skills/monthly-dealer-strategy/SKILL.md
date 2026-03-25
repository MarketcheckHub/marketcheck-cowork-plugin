---
name: monthly-dealer-strategy
description: >
  Comprehensive monthly market intelligence. Triggers: "monthly review",
  "monthly strategy", "monthly dealer report", "strategic review",
  "monthly market analysis", "end of month analysis", "what's my market
  doing this month", "monthly performance", "strategic briefing",
  market share, depreciation trends, market conditions, full inventory
  intelligence.
version: 0.1.0
---

# Monthly Dealer Strategy — Comprehensive Market Intelligence Report

A strategic monthly analysis that gives a dealer the complete picture: how their brand is performing in the market, which models are depreciating fastest, what the broader market trends look like, and a full inventory intelligence report. Run this on the first Monday of each month.

**Architecture:** This skill uses up to 3 parallel sub-agents to generate the 5-section report. Brand analytics, market demand, and lot composition run simultaneously.

**Note: This skill is primarily US-focused.** Most sections require `get_sold_summary` which is US-only. UK dealers will receive a supply-side market overview only.

## Dealer Profile (Load First)

→ Full procedure: read `_references/profile-loading.md`

Parse `marketcheck-profile.md` → extract all fields: `dealer_id`, `dealer_name`, `dealer_type`, `franchise_brands`, `zip`/`postcode`, `state`/`region`, `country`, `radius`, `target_margin`, `recon_cost`, `floor_plan_per_day`, `max_dom`, `aging_threshold`. If no profile: tell user to run `/onboarding`, stop.

**Country routing:** US = all agents. UK = only `lot-scanner` works. Skip `brand-market-analyst` and `market-demand-agent`. Only Section 5 (supply-side overview) available. → Full matrix: `_references/country-routing.md`

→ Agent contracts (lot-scanner, market-demand-agent, brand-market-analyst): read `_references/agent-contracts.md`

Calculate date ranges: `current_month` (most recent complete month), `prior_month`, `three_months_ago`.

Confirm: "Running monthly strategy report for **[dealer_name]**..."

## Dealer Group Support

If `user_type` is `dealer_group`:

1. Read `dealer_group.locations[]`
2. Ask: "Run monthly strategy for which location? Or 'all' for group rollup?"
   - Specific location: use that location's context
   - 'All': run per-location, then append GROUP MONTHLY ROLLUP

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

## Gotchas

- **Primarily US-focused** — Sections 1-4 require `get_sold_summary` (US-only). UK dealers only get Section 5 (supply-side overview via `search_uk_active_cars`).
- **Wave dependency is strict** — Wave 2 (depreciation watch) needs lot-scanner results from Wave 1 to know which models to check. Wave 3 can run in parallel with Wave 2.
- **`brand-market-analyst` agent handles brand share AND market trends** — it's a single agent call that returns both Section 1 and Section 3 data. Don't call it twice.
- **Depreciation flag threshold: >1.5%/month** — models depreciating faster than 1.5% monthly are flagged as "ACCELERATING DEPRECIATION" in Section 2.
- **`lot-scanner` in facets-only mode** — use `rows=0` with `facets=make|0|10|1,model|0|20|1` and `stats=price,dom`. This returns composition data without individual vehicle records.
- **Missing `version` field was fixed** — this skill now has `version: 0.1.0` in frontmatter (previously missing).

## Execution: Multi-Agent Orchestration

### Wave 1 — Launch Simultaneously (US)

Launch these three agents **in parallel** using the Agent tool. All are independent.

**Agent A: `lot-scanner` (facets-only mode)**

Use the Agent tool to spawn the `marketcheck-cowork-plugin:lot-scanner` agent with this prompt:

> Pull lot composition for dealer_id=[dealer_id], country=US, mode=facets_only. Use rows=0 with facets=make|0|10|1,model|0|20|1 and stats=price,dom. Return the top 5 make/model combinations by count and overall lot statistics.

**Agent B: `market-demand-agent`**

Use the Agent tool to spawn the `marketcheck-cowork-plugin:market-demand-agent` agent with this prompt:

> Generate full inventory intelligence for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Date range: [current_month date_from] to [current_month date_to]. Run sections: ds_ratios, turn_rates. Also include body type breakdown.

**Agent C: `brand-market-analyst`**

Use the Agent tool to spawn the `marketcheck-cowork-plugin:brand-market-analyst` agent with this prompt:

> Analyze brand performance and market trends for state=[state], dealer_type=[dealer_type], franchise_brands=[brands list]. Current month: [current_month dates]. Prior month: [prior_month dates]. Three months ago: [three_months_ago dates]. Run sections: brand_share, market_trends. Skip depreciation (will provide lot models in Wave 2).

### Validate Wave 1
- [ ] `lot-scanner` returned facets with at least 1 make/model combination — if empty, dealer may have no active inventory
- [ ] `market-demand-agent` returned `ds_ratios` and `turn_rates` sections — if either missing, note in output
- [ ] `brand-market-analyst` returned `brand_share` and `market_trends` sections — if either missing, note in output

### Wave 2 — After Lot Scanner Completes

Once `lot-scanner` returns the top 5 make/model combos from the dealer's lot:

**Run depreciation watch directly** (or spawn brand-market-analyst again):

For each of the top 5 models, call `mcp__marketcheck__get_sold_summary` with:
- `make`, `model`: the model
- `state`: from profile
- `inventory_type`: `Used`
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `top_n`: `1`
- Two calls per model: current_month dates AND three_months_ago dates

Calculate:
- Price Change $ = current avg_sale_price - baseline avg_sale_price
- Monthly Depreciation Rate % = (Price Change / baseline) / 3 × 100
- Flag models with monthly depreciation > 1.5% as **ACCELERATING DEPRECIATION**

### Validate Wave 2
- [ ] Depreciation calculations completed for all top 5 models — if any failed, note which and why
- [ ] Both current and 3-month-ago price data returned for each model — if baseline missing, skip that model with a note
- [ ] Monthly depreciation rates are calculated as (change / baseline) / 3, not annualized

### Wave 3 — Supply-Side Overview (US + UK)

This simple single call can run after Wave 1 completes or in parallel with Wave 2.

**US:** Call `mcp__marketcheck__search_active_cars`
**UK:** Call `mcp__marketcheck__search_uk_active_cars`

With:
- `zip`/`postcode`: from profile
- `radius`: from profile
- `car_type`: `used`
- `facets`: `make|0|20|1,body_type|0|10|1`
- `stats`: `price,dom`
- `rows`: `0`

### Validate Wave 3
- [ ] Supply-side query returned facet data with at least 1 make and 1 body type
- [ ] Stats object contains `price` and `dom` fields — if missing, note "Market stats unavailable"
- [ ] Total active supply count is non-zero — if zero, check radius and filters

### UK Execution Path

For UK dealers, only run:
1. Wave 3 (Supply-Side Overview) using `search_uk_active_cars`
2. Note: "Sections 1-4 require US sold data and are not available for UK dealers."

### Assembly — Combine All Results

1. **Section 1 (Brand Performance)** — from `brand-market-analyst` agent output
2. **Section 2 (Depreciation Watch)** — from Wave 2 depreciation calculations + lot-scanner facets
3. **Section 3 (Market Trends)** — from `brand-market-analyst` agent output
4. **Section 4 (Inventory Intelligence)** — from `market-demand-agent` agent output
5. **Section 5 (Supply-Side Overview)** — from Wave 3

## Output Format

```
MONTHLY DEALER STRATEGY REPORT — [Dealer Name] — [Month Year]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. BRAND PERFORMANCE — [State] — [Current Month] vs [Prior Month]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Make | Current Sold | Share % | Prior Share % | Change (bps) | Trend
-----|-------------|---------|---------------|-------------|------
[table — highlight dealer's franchise brands]

Your Brand Summary: [Brand] holds [X]% share, [up/down] [X] bps month-over-month.

2. DEPRECIATION WATCH — Models on Your Lot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Make Model | Units on Lot | Avg Price 3mo Ago | Avg Price Now | Monthly Depr. Rate | Alert
-----------|-------------|-------------------|---------------|--------------------|---------
[table — flag >1.5%/month]

3. MARKET TRENDS — [State]
━━━━━━━━━━━━━━━━━━━━━━━━━

Fastest Depreciating Models (statewide):
Make Model | 3mo Ago Avg | Current Avg | Drop $ | Drop % | On Your Lot?
-----------|-------------|-------------|--------|--------|-------------
[top 10]

[If franchise:]
New Car MSRP Status — [Brand]:
Model | Avg Sale vs MSRP | Status
------|------------------|-------
[Above/At/Below MSRP]

4. INVENTORY INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━

Demand-to-Supply — Top Opportunities:
Make Model | Monthly Sold | Active Supply | D/S Ratio | Signal
-----------|-------------|---------------|-----------|-------
[top 10 under-supplied]

Aging Summary:
  Units > 60 days: [N] ($[X,XXX] floor plan burn/month)
  Units > 90 days: [N]
  Units > 120 days: [N]

Turn Rate by Segment:
Body Type | Avg DOM | Sold Volume | Speed
----------|---------|-------------|------
[table]

5. SUPPLY-SIDE MARKET OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total active supply within [radius] miles: [N] units
Average asking price: $[X,XXX]
Average DOM: [X] days

By Body Type:
Body Type | Count | Avg Price | Avg DOM
----------|-------|-----------|--------
[table]

By Make (top 10):
Make | Count | Avg Price
-----|-------|----------
[table]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
30-DAY ACTION PLAN:
1. [Highest $ impact action]
2. [Second action]
3. [Third action]
4. [Fourth action]
5. [Fifth action]

Key Metrics to Watch Next Month:
- [Brand] market share: currently [X]% — target [X]%
- Aging units: currently [N] — target < [N]
- Average DOM: currently [X] days — target < [X] days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Report period: [Month Year] | Data source: MarketCheck | Market: [State/Region]
```

## Self-Check (before presenting to user)

- [ ] All 5 sections present (or noted as unavailable for UK)
- [ ] Tables have consistent column counts
- [ ] Share changes expressed in basis points (bps), not percentage points
- [ ] Depreciation rates are monthly (not annualized) in Section 2
- [ ] Franchise brands highlighted with ★ in brand performance table
- [ ] 30-day action plan items cite specific numbers from the data
- [ ] Report period and data source cited at bottom
