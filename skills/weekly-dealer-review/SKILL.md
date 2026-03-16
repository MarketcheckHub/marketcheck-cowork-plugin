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

## Dealer Profile (Load First)

1. Read the `marketcheck-profile.md` project memory file first.
2. If **neither file exists**: Tell the user: "No dealer profile found. Run `/dealer-onboarding` to set up your dealer context once." Then stop.
3. If the file **exists**, extract all fields:
   - `dealer_id`, `dealer_name`, `dealer_type`, `franchise_brands`
   - `zip`/`postcode`, `state`/`region`, `country`
   - `radius`, `target_margin`, `recon_cost`, `floor_plan_per_day`, `max_dom`, `aging_threshold`
4. If `dealer_id` is null: Tell the user to update their profile with `/dealer-onboarding`. Then stop.
5. **Tool routing by country:**
   - **US**: All agents and tools available
   - **UK**: Only `lot-scanner` agent works (uses `search_uk_active_cars`). Skip `lot-pricer` (no ML pricing), `market-demand-agent` (no sold data). For UK, price using comp medians inline.
6. Confirm: "Running weekly review for **[dealer_name]**..."

## Dealer Group Support

If `user_type` is `dealer_group`:

1. Read `dealer_group.locations[]`
2. Ask: "Run weekly review for which location? Or 'all' for group rollup?"
   - Specific location: use that location's context
   - 'All': run per-location, then append GROUP WEEKLY ROLLUP

### Group Weekly Rollup

**IMPORTANT — Per-Location Stats Must Be Queried Individually:**
Each location row in the health scorecard MUST use its own API call with `source=<location_domain>` and `stats=price,miles,dom`. Never copy group-level stats across all rows — every location has different pricing, mileage, and DOM profiles. Query each location separately:

```
search_active_cars(source="location1.com", car_type="used", rows=1, stats="price,miles,dom")
search_active_cars(source="location2.com", car_type="used", rows=1, stats="price,miles,dom")
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

**Agent A: `lot-scanner`**

Use the Agent tool to spawn the `marketcheck-cowork-plugin:lot-scanner` agent with this prompt:

> Pull the complete inventory for dealer_id=[dealer_id], country=[US/UK], car_type=used, sort_by=dom, sort_order=desc. Paginate through ALL results — do not stop at 50. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, and DOM.

**Agent B: `market-demand-agent`** (US only — skip for UK)

Use the Agent tool to spawn the `marketcheck-cowork-plugin:market-demand-agent` agent with this prompt:

> Generate the stocking hot list and market demand snapshot for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Use date range [first day of last month] to [last day of last month]. Run sections: hot_list, demand_snapshot.

### Wave 2 — After Lot Scanner Completes

Once the `lot-scanner` agent returns with the complete vehicle list:

**Agent C: `lot-pricer`** (US only)

Use the Agent tool to spawn the `marketcheck-cowork-plugin:lot-pricer` agent with this prompt:

> Price these vehicles against the market: [pass the full vehicle list from lot-scanner]. Use zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold]. Price ALL vehicles — do not cap at 25.

**UK Alternative (inline, no agent):**

For UK dealers, instead of lot-pricer, price each unit inline:
- For each vehicle from lot-scanner, call `mcp__marketcheck__search_uk_active_cars` with matching year/make/model within radius, `rows=10`
- Calculate median price from comparables
- Classify as Below/At/Above Market using the same ±5% thresholds

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

## Output Format

```
WEEKLY DEALER REVIEW — [Dealer Name] — Week of [Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FULL LOT COMPETITIVE SCAN — [N] Units Analyzed (all [total] units on lot)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VIN (last 6) | Year Make Model | DOM | Your Price | Market Price | Gap % | Position | Action
-------------|-----------------|-----|------------|--------------|-------|----------|-------
[sorted by most overpriced first]

SUMMARY:
  [N] units ABOVE MARKET (avg [X]% overpriced) — reduce to recover ~$[X,XXX]
  [N] units AT MARKET — hold
  [N] units BELOW MARKET — consider raising [N] units to capture ~$[X,XXX]

STOCKING HOT LIST — Top 10 Models to Seek ([State], [Month])
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rank | Make Model | Turn Days | Monthly Sold | Supply | D/S Ratio | Max Buy | On Your Lot?
-----|------------|-----------|-------------|--------|-----------|---------|-------------
[top 10 by opportunity score]

MARKET DEMAND — [State] — [Month Year]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Top 10 Selling Models:
Rank | Make Model | Sold Count | Avg Price | Avg DOM
-----|------------|------------|-----------|--------
[table]

Demand by Segment:
Body Type | Sold Count | Share %
----------|------------|--------
[table]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOP 5 ACTIONS THIS WEEK:
1. [Highest-impact action with $ estimate]
2. [Second action]
3. [Third action]
4. [Fourth action]
5. [Fifth action]

Estimated total impact: $[X,XXX] in margin recovery + $[X,XXX] in stocking opportunity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For strategic monthly analysis (market share, depreciation, trends), run /monthly-strategy
```

**UK dealers**: Sections 2 and 3 are replaced with: "Hot List and Market Demand require US sold data. Use the competitive scan above for UK pricing intelligence."
