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

## Profile
Load the `marketcheck-profile.md` project memory file — **required** (if missing, tell user to run `/onboarding` and stop). Extract: dealer_id (required — if null, stop), dealer_name, dealer_type, franchise_brands, zip/postcode, state/region, country, radius, target_margin, recon_cost, floor_plan_per_day, max_dom, aging_threshold. Also extract: `default_inventory_type` from preferences (`"used"` | `"new"` | `"both"`; default `"used"` if not set). Apply as `car_type` in all lot-scanner and search calls. Override if user explicitly states otherwise. Never mix new and used data in the same report section. **US**: all agents and tools. **UK**: `lot-scanner` only (comp medians inline, skip `lot-pricer` and `market-demand-agent`). Confirm: "Running weekly review for [dealer_name]..."

## Execution: Multi-Agent Orchestration

### Wave 1 — Launch Simultaneously

Launch these two agents **in parallel** using the Agent tool. Both are independent and can run at the same time.

**Agent A: `lot-scanner`**

Use the Agent tool to spawn the `dealer:lot-scanner` agent with this prompt:

> Pull the complete inventory for dealer_id=[dealer_id], country=[US/UK], car_type=used, sort_by=dom, sort_order=desc. Paginate through ALL results — do not stop at 50. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, and DOM.

**Agent B: `market-demand-agent`** (US only — skip for UK)

Use the Agent tool to spawn the `dealer:market-demand-agent` agent with this prompt:

> Generate the stocking hot list and market demand snapshot for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Use date range [first day of last month] to [last day of last month]. Run sections: hot_list, demand_snapshot.

### Wave 2 — After Lot Scanner Completes

Once the `lot-scanner` agent returns with the complete vehicle list:

**Agent C: `lot-pricer`** (US only)

Use the Agent tool to spawn the `dealer:lot-pricer` agent with this prompt:

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
Present: full lot competitive scan table (VIN, YMMT, DOM, your price, market price, gap%, position, action) with above/at/below market summary, stocking hot list top 10 (US only), market demand snapshot (top models + body type breakdown, US only), and TOP 5 ACTIONS THIS WEEK with estimated dollar impact. UK dealers: competitive scan only, note sold data sections unavailable.
