---
description: Morning operational health check — aging inventory alerts + competitor price drops, per-location and group rollup (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [location name or "all"]
---

Daily dealer briefing using parallel sub-agents. Per-location or group rollup.

## Step 1: Verify dealer group profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter. Missing -> "Run `/onboarding` first." Stop. Extract `group_name`, `locations[]`, `preferences`.

**Speed rule — profile-read-once:** Pass the extracted profile fields (dealer_id, source, country, zip/postcode, state/region, radius, aging_threshold, dealer_type, franchise_brands) directly to all sub-agents in their prompt. Sub-agents should NOT re-read the profile.

## Step 2: Determine scope

$ARGUMENTS: location name -> match to `locations[].name`. "all" or empty -> ask "Which location or 'all' for group rollup?" Extract per-location: `dealer_id` (null -> skip with note), `name`, `dealer_type`, `franchise_brands`, `zip`/`postcode`, `state`/`region`, `country`.

## Step 3: Per-location Wave 1 -- Lot scanner + competitor scan

**Agent A: `lot-scanner`** -- Spawn `dealership-group:lot-scanner`: aging inventory for dealer_id, car_type=used, sort_by=dom desc, dom_range=[aging_threshold]-999. Paginate all.

**Inline: Competitor price drops** -- **US:** For each franchise brand, `search_active_cars` with `make`, `zip`, `radius`, `price_change=negative`, `rows=10`, `car_type=used`, `seller_type=dealer`. **UK:** `search_uk_active_cars` (skip if unsupported).

## Step 4: Per-location Wave 2 -- Price aging units

After lot-scanner: **Agent B: `lot-pricer`** (US only) -- top 15 aging vehicles. **UK:** Comp medians inline.

## Step 5: Per-location report

Aging inventory table (one row per unique VIN — deduplicate cross-listed VINs, show `×N sites` note), floor plan burn, competitor alerts, price reductions (deduplicate by VIN, show largest reduction), top 3 actions with $ estimates.

## Step 6: Group rollup (if "all")

**Per-location stats MUST be queried individually.** For each location call `search_active_cars(source=<location_domain>, car_type="used", rows=1, stats="price,miles,dom")` and use that location's own `stats` object for its row. Never apply group-level stats to individual location rows.

Summary table: location, units (per-location), aged units (per-location), avg_dom (per-location), floor plan burn/day, competitor alerts, top action. Group total. Top 3 group-level actions ranked by impact.
