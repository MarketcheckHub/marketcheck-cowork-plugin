---
description: Weekly tactical review — full lot pricing scan + stocking hot list + market demand (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__search_uk_active_cars", "mcp__marketcheck__search_uk_recent_cars"]
argument-hint: []
---

Run the weekly dealer review using parallel sub-agents for faster turnaround. This command triggers the `weekly-dealer-review` skill.

## Step 1: Verify dealer profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter.

- If **missing**: "No dealer profile found. Run `/dealer-onboarding` first." Then stop.
- If **exists**: Extract all fields — `dealer_id`, `dealer_name`, `dealer_type`, `franchise_brands`, `zip`/`postcode`, `state`/`region`, `country`, `radius`, `target_margin`, `recon_cost`, `floor_plan_per_day`, `max_dom`, `aging_threshold`.
- If `dealer_id` is null: "Your profile needs a dealer ID. Run `/dealer-onboarding` to update." Then stop.

**Speed rule — profile-read-once:** Pass the extracted profile fields (dealer_id, source, country, zip/postcode, state/region, radius, aging_threshold, dealer_type, franchise_brands) directly to all sub-agents in their prompt. Sub-agents should NOT re-read the profile.

**Tool routing:** US = all agents. UK = lot-scanner only (skip lot-pricer and market-demand-agent).

Confirm: "Running weekly review for **[dealer_name]**..."

## Step 2: Wave 1 — Launch agents in parallel

Launch these two agents **simultaneously** using the Agent tool:

**Agent A: `lot-scanner`** — Pull complete dealer inventory with pagination.

Spawn `marketcheck-cowork-plugin:lot-scanner` with prompt:
> Pull complete inventory for dealer_id=[dealer_id], country=[country], car_type=used, sort_by=dom, sort_order=desc. Paginate through ALL results. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, DOM.

**Agent B: `market-demand-agent`** (US only) — Hot list + demand snapshot.

Spawn `marketcheck-cowork-plugin:market-demand-agent` with prompt:
> Generate stocking hot list and demand snapshot for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Date range: [first day of last month] to [last day of last month]. Sections: hot_list, demand_snapshot.

## Step 3: Wave 2 — Price all inventory

After `lot-scanner` returns the complete vehicle list:

**Agent C: `lot-pricer`** (US only) — Price every unit against market.

Spawn `marketcheck-cowork-plugin:lot-pricer` with prompt:
> Price these vehicles: [full vehicle list from lot-scanner]. zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold]. Price ALL vehicles.

**UK dealers**: Skip lot-pricer. For each unit, search comparable listings via `search_uk_active_cars` and calculate comp median price.

## Step 4: Assemble report

Combine all agent outputs into the weekly review format:

- **Section 1** (Full Lot Scan): from lot-pricer — pricing table sorted by most overpriced, summary counts
- **Section 2** (Hot List): from market-demand-agent — top 10 models, cross-referenced with lot inventory for gap flags
- **Section 3** (Demand Snapshot): from market-demand-agent — top models + body type breakdown
- **TOP 5 ACTIONS**: synthesized from all outputs ranked by dollar impact

```
WEEKLY DEALER REVIEW — [Dealer Name] — Week of [Date]
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
