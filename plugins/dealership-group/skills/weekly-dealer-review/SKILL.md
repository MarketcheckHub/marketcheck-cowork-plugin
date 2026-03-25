---
name: weekly-dealer-review
description: >
  Tactical weekly inventory and stocking analysis. Triggers: "weekly review",
  "weekly inventory scan", "weekly stocking check", "full lot pricing scan",
  "hot list this week", "what should I stock this week", "weekly dealer report",
  "inventory review", "competitive scan", full inventory pricing, stocking
  recommendations, market demand.
---

# Weekly Dealer Review — Full Inventory Scan + Stocking Intelligence

A tactical weekly analysis that prices every unit on the lot against the market, generates a stocking hot list for auction buying, and provides a market demand snapshot. Run this every Monday morning or before major auction days.

**Architecture:** This skill uses parallel sub-agents to minimize turnaround time. The lot scan and market demand analysis run simultaneously, then pricing runs on the complete inventory.

## Dealer Group Profile (Load First)

Load the `marketcheck-profile.md` project memory file. If missing, prompt `/onboarding` and stop.

**Extract ALL locations from `dealer_group.locations[]`.** For each location record: `name`, `dealer_id`, `dealer_type`, `franchise_brands`, `zip` (US) or `postcode` (UK), `state` (US) or `region` (UK), `web_domain`, `country`. Extract group-level preferences: `default_radius_miles` (→ `radius`), `target_margin_pct` (→ `target_margin`), `recon_cost_estimate` (→ `recon_cost`), `floor_plan_cost_per_day`, `max_acceptable_dom` (→ `max_dom`), `dom_aging_threshold` (→ `aging_threshold`).

**Location scope:** If a specific location name is provided, match to `locations[].name` and run for that location only. If "all" or no argument, iterate through EVERY location — all execution steps below run for each location using **that location's own** `dealer_id`, `zip`/`postcode`, `state`/`region`, `dealer_type`, and `franchise_brands`. Never pass one location's zip or state to a different location's agent or API call.

**Inventory type:** Read `preferences.default_inventory_type` from profile (`"used"` | `"new"` | `"both"`; default `"used"` if not set). Apply as `car_type` in all lot-scanner, lot-pricer, and search calls for every location. If the user specifies a different type in their request, override. Never mix new and used data in the same report section.

**Tool routing per location:** US: all agents (`lot-scanner`, `market-demand-agent`, `lot-pricer`). UK: `lot-scanner` only (comp medians inline). Confirm: "Running weekly review for: [location name(s)] | Inventory: [used/new/both]"

### Group Weekly Rollup

**IMPORTANT — Per-Location Stats Must Be Queried Individually:**
Each location row in the health scorecard MUST use its own API call with `source=<location_domain>` and `stats=price,miles,dom`. Never copy group-level stats across all rows — every location has different pricing, mileage, and DOM profiles. Query each location separately:

```
search_active_cars(source="gunnhonda.com", car_type="used", rows=1, stats="price,miles,dom")
search_active_cars(source="gunncdjr.com",  car_type="used", rows=1, stats="price,miles,dom")
... one call per location domain
```

Then use each response's `stats` object for that location's row only.

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
  Best location for each: [which store's market has highest D/S ratio]

CROSS-LOCATION TRANSFER OPPORTUNITIES:
  [If one location is over-stocked in a category where another is under-stocked, flag it]
```

## Execution: Multi-Agent Orchestration

### Wave 1 — Launch Simultaneously

Launch these two agents **in parallel** using the Agent tool. Both are independent and can run at the same time.

**For each location, spawn the following agents using THAT location's values:**

**Agent A: `lot-scanner`**

Use the Agent tool to spawn the `dealership-group:lot-scanner` agent with this prompt:

> Pull the complete inventory for dealer_id=[**this location's** dealer_id], country=[**this location's** country], car_type=used, sort_by=dom, sort_order=desc. Paginate through ALL results — do not stop at 50. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, and DOM. Location label: [**this location's** name].

**Agent B: `market-demand-agent`** (US only — skip for UK locations)

Use the Agent tool to spawn the `dealership-group:market-demand-agent` agent with this prompt:

> Generate the stocking hot list and market demand snapshot for state=[**this location's** state], dealer_type=[**this location's** dealer_type], zip=[**this location's** zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Use date range [first day of last month] to [last day of last month]. Run sections: hot_list, demand_snapshot. Location label: [**this location's** name].

### Wave 2 — After Lot Scanner Completes

Once the `lot-scanner` agent returns with the complete vehicle list:

**Agent C: `lot-pricer`** (US only)

Use the Agent tool to spawn the `dealership-group:lot-pricer` agent with this prompt:

> Price these vehicles against the market: [pass the full vehicle list from THIS location's lot-scanner]. Use zip=[**this location's** zip], dealer_type=[**this location's** dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold]. Price ALL vehicles — do not cap at 25. Location label: [**this location's** name].

**UK Alternative (inline, no agent):**

For UK dealers, instead of lot-pricer, price each unit inline:
- For each vehicle from lot-scanner, call `mcp__marketcheck__search_uk_active_cars` with matching year/make/model within radius, `rows=10`
- Calculate median price from comparables
- Classify as Below/At/Above Market using the same +/-5% thresholds

### Assembly — Combine Results

After all agents complete, assemble the report from their outputs:

1. **Section 1 (Full Lot Competitive Scan)** — from `lot-pricer` output:
   - Use the pricing table directly (already sorted by most overpriced first)
   - Use the summary statistics (above/at/below market counts and dollar estimates)
   - Each VIN appears **once** only (lot-scanner already deduped). If `cross_listed_count > 1`, show `(×N sites)` next to the source column as a note — do NOT repeat the row.

2. **Section 2 (Stocking Hot List)** — from `market-demand-agent` output (US only):
   - Take the hot_list top 10
   - Cross-reference with lot-scanner vehicle list: for each hot-list model, check if the dealer has any units. Flag gaps.

3. **Section 3 (Market Demand Snapshot)** — from `market-demand-agent` output (US only):
   - Use demand_snapshot top models and body type breakdown directly

4. **Price Reductions** — if querying `price_change` data for the group:
   - Deduplicate by VIN: same VIN reduced on multiple group sites = one entry, show the **largest reduction** amount. Note `(×N sites)` if cross-listed.
   - Never list the same VIN more than once in a price reduction table.

5. **TOP 5 ACTIONS** — synthesize from all agent outputs:
   - Priority 1-2: From lot-pricer (biggest overpriced units to reduce)
   - Priority 3: From lot-pricer (biggest underpriced units to raise)
   - Priority 4-5: From market-demand-agent (top models missing from lot to acquire)

## Output

Present: full lot competitive scan table (VIN, YMMT, DOM, your price, market price, gap %, action) with above/at/below market summary, stocking hot list top 10 (model, turn days, D/S ratio, max buy), market demand snapshot (top models + segment breakdown), and top 5 weekly actions with dollar impact. UK: competitive scan only.

