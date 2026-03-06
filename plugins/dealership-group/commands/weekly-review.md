---
description: Weekly tactical review — full lot pricing scan + stocking hot list + market demand, per-location and group rollup (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: [location name or "all"]
---

Weekly dealer review using parallel sub-agents. Per-location or group rollup.

## Step 1: Verify dealer group profile

Read `~/.claude/marketcheck/dealership-group-profile.json`. Missing -> "Run `/onboarding` first." Stop. Extract `group_name`, `locations[]`, `preferences`.

## Step 2: Determine scope

$ARGUMENTS: location name -> match. "all" or empty -> ask. Extract per-location fields. dealer_id null -> skip. **Tool routing:** US = all agents. UK = lot-scanner only.

## Step 3: Per-location Wave 1 -- Two agents in parallel

**Agent A: `lot-scanner`** -- Spawn `dealership-group:lot-scanner`: complete used inventory, sort_by=dom desc. Paginate ALL.

**Agent B: `market-demand-agent`** (US only) -- Spawn `dealership-group:market-demand-agent`: hot list + demand snapshot for state, dealer_type, zip, radius. Previous month. Sections: hot_list, demand_snapshot.

## Step 4: Per-location Wave 2 -- Price all inventory

After lot-scanner: **Agent C: `lot-pricer`** (US only) -- price ALL vehicles. **UK:** Comp medians from `search_uk_active_cars`.

## Step 5: Per-location report

Section 1 (Lot Scan): pricing table sorted by most overpriced. Section 2 (Hot List): cross-ref with inventory. Section 3 (Demand Snapshot). Top 5 actions by $ impact. **UK:** Sections 2-3 replaced with "Requires US sold data."

## Step 6: Group weekly rollup (if "all")

Table: location, units, overpriced/at-market/underpriced counts, hot list match, stocking gaps. Group stocking priorities (most needed models + best location). Cross-location transfer opportunities.
