---
description: Weekly tactical review — full lot pricing scan + stocking hot list + market demand, per-location and group rollup (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: [location name or "all"]
---

Run the weekly dealer review using parallel sub-agents for faster turnaround. This command triggers the `weekly-dealer-review` skill. Supports per-location review or group rollup.

## Step 1: Verify dealer group profile

Read `~/.claude/marketcheck/dealership-group-profile.json`.

- If **missing**: "No dealer group profile found. Run `/onboarding` first." Then stop.
- If **exists**: Extract `dealer_group.group_name`, `dealer_group.locations[]`, and all `preferences`.

## Step 2: Determine scope

Check $ARGUMENTS:

- If a location name is provided: match it and use that location
- If "all" or empty: ask "Run weekly review for which location? Or 'all' for group rollup?"
  - If specific location: use that location's context
  - If 'all': run per-location, then append GROUP WEEKLY ROLLUP

For the selected location(s), extract all fields. If `dealer_id` is null: skip that location with a note.

**Tool routing:** US = all agents. UK = lot-scanner only (skip lot-pricer and market-demand-agent).

Confirm: "Running weekly review for **[location name or group name (all)]**..."

## Step 3: Per-location review — Wave 1

Launch these two agents **simultaneously** using the Agent tool:

**Agent A: `lot-scanner`** — Pull complete location inventory with pagination.

Spawn `dealership-group:lot-scanner` with prompt:
> Pull complete inventory for dealer_id=[dealer_id], country=[country], car_type=used, sort_by=dom, sort_order=desc. Paginate through ALL results. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, DOM.

**Agent B: `market-demand-agent`** (US only) — Hot list + demand snapshot.

Spawn `dealership-group:market-demand-agent` with prompt:
> Generate stocking hot list and demand snapshot for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Date range: [first day of last month] to [last day of last month]. Sections: hot_list, demand_snapshot.

## Step 4: Per-location review — Wave 2

After `lot-scanner` returns the complete vehicle list:

**Agent C: `lot-pricer`** (US only) — Price every unit against market.

Spawn `dealership-group:lot-pricer` with prompt:
> Price these vehicles: [full vehicle list from lot-scanner]. zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold]. Price ALL vehicles.

**UK locations**: Skip lot-pricer. For each unit, search comparable listings via `search_uk_active_cars` and calculate comp median price.

## Step 5: Assemble per-location report

Combine all agent outputs into the weekly review format:

- **Section 1** (Full Lot Scan): from lot-pricer — pricing table sorted by most overpriced, summary counts
- **Section 2** (Hot List): from market-demand-agent — top 10 models, cross-referenced with lot inventory for gap flags
- **Section 3** (Demand Snapshot): from market-demand-agent — top models + body type breakdown
- **TOP 5 ACTIONS**: synthesized from all outputs ranked by dollar impact

```
WEEKLY DEALER REVIEW — [Location Name] — Week of [Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Section 1: Full Lot Competitive Scan — all units, paginated]
[Section 2: Stocking Hot List — US only]
[Section 3: Market Demand Snapshot — US only]

TOP 5 ACTIONS THIS WEEK:
1-5. [Actions with $ estimates]

Estimated total impact: $[X,XXX] in margin recovery + $[X,XXX] in stocking opportunity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For strategic monthly analysis, run /monthly-strategy
```

**UK locations**: Sections 2 and 3 replaced with: "Hot List and Market Demand require US sold data."

## Step 6: Group weekly rollup (if "all" locations)

```
GROUP WEEKLY ROLLUP — [Group Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Location         | Units | Overpriced | At Market | Underpriced | Hot List Match | Stocking Gaps
-----------------|-------|-----------|-----------|-------------|---------------|-------------
[Location 1]     | XXX   | XX        | XX        | XX          | X of 10       | X categories
[Location 2]     | XXX   | XX        | XX        | XX          | X of 10       | X categories
...

GROUP STOCKING PRIORITIES:
  Most needed across group: [model 1], [model 2], [model 3]
  Best location for each: [which location's market has highest D/S ratio]

CROSS-LOCATION TRANSFER OPPORTUNITIES:
  [If one location is over-stocked in a category where another is under-stocked, flag it]
```
