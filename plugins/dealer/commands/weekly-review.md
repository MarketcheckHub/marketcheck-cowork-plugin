---
description: Weekly tactical review — full lot pricing scan + stocking hot list + market demand (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: []
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

Weekly dealer review using parallel sub-agents. Triggers `weekly-dealer-review` skill.

## Step 1: Verify dealer profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter. Missing -> "Run `/onboarding` first." Stop. Extract all fields. dealer_id null -> stop. **Tool routing:** US = all agents. UK = lot-scanner only.

**Speed rule — profile-read-once:** Pass the extracted profile fields (dealer_id, source, country, zip/postcode, state/region, radius, aging_threshold, dealer_type, franchise_brands) directly to all sub-agents in their prompt. Sub-agents should NOT re-read the profile.

## Step 2: Wave 1 -- Two agents in parallel

**Agent A: `lot-scanner`** -- Spawn `dealer:lot-scanner`: pull complete used inventory, sort_by=dom desc. Paginate ALL results.

**Agent B: `market-demand-agent`** (US only) -- Spawn `dealer:market-demand-agent`: stocking hot list + demand snapshot for state, dealer_type, zip, radius. Date range: previous month. Sections: hot_list, demand_snapshot.

## Step 3: Wave 2 -- Price all inventory

After lot-scanner returns: **Agent C: `lot-pricer`** (US only) -- Spawn `dealer:lot-pricer`: price ALL vehicles from lot-scanner. **UK:** Use comp medians from `search_uk_active_cars`.

## Step 4: Assemble report

Section 1 (Full Lot Scan): pricing table from lot-pricer sorted by most overpriced. Section 2 (Hot List): from market-demand-agent, cross-ref with lot inventory. Section 3 (Demand Snapshot): top models + body type breakdown. Top 5 actions ranked by $ impact. End with: "For strategic monthly analysis, run /monthly-strategy"
