---
description: Weekly tactical review — full lot pricing scan + stocking hot list + market demand (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: []
---

Weekly dealer review using parallel sub-agents. Triggers `weekly-dealer-review` skill.

## Step 1: Verify dealer profile

Read `~/.claude/marketcheck/dealer-profile.json`. Missing -> "Run `/onboarding` first." Stop. Extract all fields. dealer_id null -> stop. **Tool routing:** US = all agents. UK = lot-scanner only.

## Step 2: Wave 1 -- Two agents in parallel

**Agent A: `lot-scanner`** -- Spawn `dealer:lot-scanner`: pull complete used inventory, sort_by=dom desc. Paginate ALL results.

**Agent B: `market-demand-agent`** (US only) -- Spawn `dealer:market-demand-agent`: stocking hot list + demand snapshot for state, dealer_type, zip, radius. Date range: previous month. Sections: hot_list, demand_snapshot.

## Step 3: Wave 2 -- Price all inventory

After lot-scanner returns: **Agent C: `lot-pricer`** (US only) -- Spawn `dealer:lot-pricer`: price ALL vehicles from lot-scanner. **UK:** Use comp medians from `search_uk_active_cars`.

## Step 4: Assemble report

Section 1 (Full Lot Scan): pricing table from lot-pricer sorted by most overpriced. Section 2 (Hot List): from market-demand-agent, cross-ref with lot inventory. Section 3 (Demand Snapshot): top models + body type breakdown. Top 5 actions ranked by $ impact. End with: "For strategic monthly analysis, run /monthly-strategy"
