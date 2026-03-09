---
name: geographic-arbitrage-finder
description: >
  This skill should be used when the user asks about "arbitrage opportunities",
  "price differences between states", "where to source vehicles",
  "cross-market pricing", "cheapest market for [model]",
  "geographic price gaps", "transport arbitrage",
  "which states are cheap for trucks", or needs help finding vehicles
  priced lower in one DMA vs another to source from cheap markets
  and sell into expensive ones.
version: 0.1.0
---

# Geographic Arbitrage Finder — Cross-Market Price Gap Analysis

## Profile
Load `~/.claude/marketcheck/auction-house-profile.json` if exists. Extract: target_dmas, vehicle_segments, country. If missing, ask for at least 2 states to compare. **US only** — requires `get_sold_summary` for cross-state pricing. **UK**: Not available (single market). Confirm: "Using profile: [company], target DMAs: [list]".

## User Context
Auction house sales exec or regional director looking for arbitrage — vehicles priced lower in one state that can be transported and auctioned in a higher-price state for profit.

## Workflow: Cross-State Price Comparison

Use this when the user says "arbitrage opportunities" or "where to source cheap [vehicles]."

1. **Get per-state pricing for top models** — For each target state (2-5 states), call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=20`, `date_from` (first of prior month), `date_to` (last of prior month).
   → **Extract only**: per make/model — average_sale_price, sold_count. Discard full response.

2. **Get national baseline** — Call `mcp__marketcheck__get_sold_summary` with NO state filter, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `top_n=20`, same date range.
   → **Extract only**: per make/model — average_sale_price (national). Discard full response.

3. **Calculate arbitrage spreads** — For each model present in 2+ states:
   - **Price Index** per state = state_avg / national_avg × 100
   - **Cheapest state** and **most expensive state** for each model
   - **Gross Spread** = expensive_state_avg - cheap_state_avg
   - **Spread %** = gross_spread / cheap_state_avg × 100
   - **Transport Cost Estimate** = estimated distance × $1.50/mile. Use approximate state center-to-center distances.
   - **Net Arbitrage** = gross_spread - transport_cost
   - **Only flag if**: spread % > 8% AND net arbitrage > $500 AND both states have sold_count > 20 (reliable data)

4. **Rank by net arbitrage** — Sort opportunities by net profit, descending.

## Workflow: Segment-Level Arbitrage

Use this when the user asks "which states are cheap for trucks" or "SUV pricing by state."

1. **Get per-state segment pricing** — For each target state, call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `body_type=[segment]`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `top_n=10`.
   → **Extract only**: per model — average_sale_price, sold_count. Discard full response.

2. Compare across states. Identify source markets (cheapest) and destination markets (most expensive).

## Workflow: State Price Index Overview

Use this when the user asks "compare pricing across my markets" or "price index by state."

1. For each target state: `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_measure=average_sale_price`.
   → **Extract only**: overall average_sale_price. Discard full response.

2. Calculate price index = state_avg / average_of_all_states × 100.
3. Rank: cheapest states = source markets, most expensive = destination markets.

## Output
Arbitrage opportunities table: Make/Model, Cheap State, Cheap Avg, Expensive State, Expensive Avg, Gross Spread, Spread %, Transport Est., Net Profit. Top 5 most actionable opportunities highlighted. State price index summary. Sourcing recommendations: "Source [models] from [state] for [state] auctions — $[X] net per unit after transport."
