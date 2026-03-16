---
description: Weekly tactical review — full lot pricing scan + stocking hot list + market demand, per-location and group rollup (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: [location name or "all"]
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

Weekly dealer review using parallel sub-agents. Per-location or group rollup.

## Step 1: Verify dealer group profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter. Missing -> "Run `/onboarding` first." Stop. Extract `group_name`, `locations[]`, `preferences`.

**Speed rule — profile-read-once:** Pass the extracted profile fields (dealer_id, source, country, zip/postcode, state/region, radius, aging_threshold, dealer_type, franchise_brands) directly to all sub-agents in their prompt. Sub-agents should NOT re-read the profile.

## Step 2: Determine scope

$ARGUMENTS: location name -> match. "all" or empty -> ask. Extract per-location fields. dealer_id null -> skip. **Tool routing:** US = all agents. UK = lot-scanner only.

## Step 3: Per-location Wave 1 -- Two agents in parallel

**Agent A: `lot-scanner`** -- Spawn `dealership-group:lot-scanner`: complete used inventory, sort_by=dom desc. Paginate ALL.

**Agent B: `market-demand-agent`** (US only) -- Spawn `dealership-group:market-demand-agent`: hot list + demand snapshot for state, dealer_type, zip, radius. Previous month. Sections: hot_list, demand_snapshot.

## Step 4: Per-location Wave 2 -- Price all inventory

After lot-scanner: **Agent C: `lot-pricer`** (US only) -- price ALL vehicles. **UK:** Comp medians from `search_uk_active_cars`.

## Step 5: Per-location report

Section 1 (Lot Scan): pricing table sorted by most overpriced — one row per unique VIN (lot-scanner already deduped; show `×N sites` if cross-listed). Section 2 (Hot List): cross-ref with inventory. Section 3 (Demand Snapshot). Price Reductions: deduplicate by VIN, show largest reduction, note `×N sites` if cross-listed. Top 5 actions by $ impact. **UK:** Sections 2-3 replaced with "Requires US sold data."

## Step 6: Group weekly rollup (if "all")

**Per-location stats MUST be queried individually.** For each location, call `search_active_cars(source=<location_domain>, car_type="used", rows=1, stats="price,miles,dom")` and use that location's own `stats` object. Never copy group-level stats across rows — each location has a distinct pricing and DOM profile.

Table: location, units, avg_price (per-location), avg_dom (per-location), overpriced/at-market/underpriced counts, hot list match, stocking gaps. Group stocking priorities (most needed models + best location). Cross-location transfer opportunities.
