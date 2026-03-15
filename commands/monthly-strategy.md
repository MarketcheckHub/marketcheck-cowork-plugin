---
description: Monthly strategic report — market share, depreciation, trends, inventory intelligence (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: []
---

Run the monthly dealer strategy report using parallel sub-agents. This command triggers the `monthly-dealer-strategy` skill.

## Step 1: Verify dealer profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter.

- If **missing**: "No dealer profile found. Run `/dealer-onboarding` first." Then stop.
- If **exists**: Extract all fields.

**Speed rule — profile-read-once:** Pass the extracted profile fields (dealer_id, source, country, zip/postcode, state/region, radius, aging_threshold, dealer_type, franchise_brands) directly to all sub-agents in their prompt. Sub-agents should NOT re-read the profile.

**Tool routing:** US = all agents. UK = lot-scanner only (Section 5 supply overview).

Calculate date ranges: current_month, prior_month, three_months_ago.

Confirm: "Running monthly strategy for **[dealer_name]**..."

## Step 2: Wave 1 — Launch 3 agents in parallel (US)

**Agent A: `lot-scanner` (facets-only)**

Spawn `marketcheck-cowork-plugin:lot-scanner` with prompt:
> Pull lot composition for dealer_id=[dealer_id], country=US, mode=facets_only. Use rows=0 with facets for make/model. Return top 5 make/model combos by count.

**Agent B: `market-demand-agent`**

Spawn `marketcheck-cowork-plugin:market-demand-agent` with prompt:
> Generate inventory intelligence for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius]. Date range: [current month]. Sections: ds_ratios, turn_rates.

**Agent C: `brand-market-analyst`**

Spawn `marketcheck-cowork-plugin:brand-market-analyst` with prompt:
> Analyze brand performance and market trends for state=[state], dealer_type=[dealer_type], franchise_brands=[brands]. Current month: [dates]. Prior month: [dates]. Three months ago: [dates]. Sections: brand_share, market_trends.

## Step 3: Wave 2 — Depreciation watch

After `lot-scanner` returns top 5 models, run depreciation analysis:

For each model, call `mcp__marketcheck__get_sold_summary` twice (current month + 3 months ago) with `ranking_measure=average_sale_price`. Calculate monthly depreciation rate. Flag >1.5%/month.

## Step 4: Wave 3 — Supply-side overview (US + UK)

Call `search_active_cars` (US) or `search_uk_active_cars` (UK) with `zip`, `radius`, `car_type=used`, `facets=make|0|20|1,body_type|0|10|1`, `stats=price,dom`, `rows=0`.

**UK dealers**: Only run this step. Skip Steps 2-3.

## Step 5: Assemble report

```
MONTHLY DEALER STRATEGY REPORT — [Dealer Name] — [Month Year]
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
