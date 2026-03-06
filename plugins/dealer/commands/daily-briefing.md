---
description: Morning operational health check — aging inventory alerts + competitor price drops (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: []
---

Daily dealer briefing using parallel sub-agents. Triggers `daily-dealer-briefing` skill.

## Step 1: Verify dealer profile

Read `~/.claude/marketcheck/dealer-profile.json`. Missing -> "Run `/onboarding` first." Stop. Extract `dealer_id` (null -> stop with update message), `dealer_name`, `dealer_type`, `franchise_brands`, `zip`/`postcode`, `state`/`region`, `country`, `radius`, `aging_threshold`, `floor_plan_cost_per_day`.

## Step 2: Wave 1 -- Lot scanner + competitor scan in parallel

**Agent A: `lot-scanner`** -- Spawn `dealer:lot-scanner`: pull aging inventory for dealer_id, car_type=used, sort_by=dom desc, dom_range=[aging_threshold]-999. Paginate all results. Return VIN, year/make/model/trim, price, mileage, DOM.

**Inline: Competitor price drops** -- **US:** For each franchise brand, `search_active_cars` with `make`, `zip`, `radius`, `price_change=negative`, `rows=10`, `car_type=used`, `seller_type=dealer`. Flag UNDERCUT alerts. **UK:** `search_uk_active_cars` with similar filters (skip if unsupported).

## Step 3: Wave 2 -- Price aging units

After lot-scanner returns: **Agent B: `lot-pricer`** (US only) -- Spawn `dealer:lot-pricer`: price top 15 aging vehicles by DOM. **UK:** Price inline using comp medians.

## Step 4: Assemble report

Show: aging inventory table (VIN, vehicle, DOM, your price, market price, gap, action), floor plan burn total, competitor alerts table, top 3 actions today with $ estimates. If all clear: "No units over threshold. No competitor price drops detected."
