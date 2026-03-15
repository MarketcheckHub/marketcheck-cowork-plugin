---
name: weekly-dealer-review
description: >
  This skill should be used when the user asks for a "weekly review",
  "weekly inventory scan", "weekly stocking check", "full lot pricing scan",
  "hot list this week", "what should I stock this week", "weekly dealer report",
  "inventory review", "competitive scan", or needs a tactical weekly analysis
  covering full inventory pricing, stocking recommendations, and market demand.
---

# Weekly Dealer Review — Full Inventory Scan + Stocking Intelligence

A tactical weekly analysis that prices every unit on the lot against the market, generates a stocking hot list for auction buying, and provides a market demand snapshot. Run this every Monday morning or before major auction days.

**Architecture:** This skill uses parallel sub-agents to minimize turnaround time. The lot scan and market demand analysis run simultaneously, then pricing runs on the complete inventory.

## Dealer Group Profile (Load First)

Load the `marketcheck-profile.md` project memory file. If missing, prompt `/onboarding` and stop. Ask: location or 'all' for group rollup. Extract from location: `dealer_id` (required -- if null, stop), `dealer_name`, `dealer_type`, `franchise_brands`, `zip`, `state`; from profile: `country`, `radius`, `target_margin`, `recon_cost`, `floor_plan_per_day`, `max_dom`, `aging_threshold`. US: all agents. UK: `lot-scanner` only (comp medians inline). Confirm location.

### Group Weekly Rollup

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

**Agent A: `lot-scanner`**

Use the Agent tool to spawn the `dealership-group:lot-scanner` agent with this prompt:

> Pull the complete inventory for dealer_id=[dealer_id], country=[US/UK], car_type=used, sort_by=dom, sort_order=desc. Paginate through ALL results — do not stop at 50. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, and DOM.

**Agent B: `market-demand-agent`** (US only — skip for UK)

Use the Agent tool to spawn the `dealership-group:market-demand-agent` agent with this prompt:

> Generate the stocking hot list and market demand snapshot for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Use date range [first day of last month] to [last day of last month]. Run sections: hot_list, demand_snapshot.

### Wave 2 — After Lot Scanner Completes

Once the `lot-scanner` agent returns with the complete vehicle list:

**Agent C: `lot-pricer`** (US only)

Use the Agent tool to spawn the `dealership-group:lot-pricer` agent with this prompt:

> Price these vehicles against the market: [pass the full vehicle list from lot-scanner]. Use zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold]. Price ALL vehicles — do not cap at 25.

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

2. **Section 2 (Stocking Hot List)** — from `market-demand-agent` output (US only):
   - Take the hot_list top 10
   - Cross-reference with lot-scanner vehicle list: for each hot-list model, check if the dealer has any units. Flag gaps.

3. **Section 3 (Market Demand Snapshot)** — from `market-demand-agent` output (US only):
   - Use demand_snapshot top models and body type breakdown directly

4. **TOP 5 ACTIONS** — synthesize from all agent outputs:
   - Priority 1-2: From lot-pricer (biggest overpriced units to reduce)
   - Priority 3: From lot-pricer (biggest underpriced units to raise)
   - Priority 4-5: From market-demand-agent (top models missing from lot to acquire)

## Output

Present: full lot competitive scan table (VIN, YMMT, DOM, your price, market price, gap %, action) with above/at/below market summary, stocking hot list top 10 (model, turn days, D/S ratio, max buy), market demand snapshot (top models + segment breakdown), and top 5 weekly actions with dollar impact. UK: competitive scan only.

