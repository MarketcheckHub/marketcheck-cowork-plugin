---
name: geographic-arbitrage-finder
description: >
  Cross-market price gap analysis. Triggers: "arbitrage opportunities",
  "price differences between states", "where to source vehicles",
  "cross-market pricing", "cheapest market for [model]",
  "geographic price gaps", "transport arbitrage",
  "which states are cheap for trucks", finding vehicles
  priced lower in one DMA vs another to source from cheap markets
  and sell into expensive ones.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Geographic Arbitrage Finder — Cross-Market Price Gap Analysis

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: target_dmas, vehicle_segments, country. If missing, ask for at least 2 states to compare. **US only** — requires `get_sold_summary` for cross-state pricing. **UK**: Not available (single market). Confirm: "Using profile: [company], target DMAs: [list]".

## User Context
Auction house sales exec or regional director looking for arbitrage — vehicles priced lower in one state that can be transported and auctioned in a higher-price state for profit.

## Gotchas

1. **US-only skill** — Geographic arbitrage requires `get_sold_summary` with per-state breakdowns. UK is a single market with no state-level sold data. If a UK profile triggers this skill, respond: "Geographic arbitrage analysis is available for US markets only."
2. **Average sale price is not wholesale price** — `get_sold_summary` returns retail sold averages, not auction hammer prices. Apply a 10-12% wholesale discount when estimating actual arbitrage profit: `net_arbitrage = (expensive_state_avg × 0.90) - (cheap_state_avg × 0.90) - transport_cost`. Without this adjustment, gross spreads look 10-15% better than reality.
3. **Volume thresholds prevent noise** — States with fewer than 20 sold units for a model in a month produce unreliable averages (one outlier luxury trim skews the mean). The workflow requires `sold_count > 20` in both states. Enforce this strictly — do not present opportunities that fail this check.
4. **Transport cost estimates are rough** — The $1.50/mile estimate assumes open carrier. Enclosed transport (luxury, exotics) runs $2.50-3.00/mile. For vehicles with expected hammer > $50,000, use $2.50/mile. Also add a flat $200 for terminal-to-terminal fees.
5. **Seasonal and regional distortions** — 4WD/AWD trucks and SUVs command premiums in northern states during winter. Convertibles command premiums in southern states in spring. Always note the analysis month and flag segments with known seasonal patterns.

## Workflow: Cross-State Price Comparison

Use this when the user says "arbitrage opportunities" or "where to source cheap [vehicles]."

1. **Get per-state pricing for top models** — For each target state (2-5 states), call `mcp__marketcheck__get_sold_summary` with `state=[XX]`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=20`, `date_from=[YYYY-MM-01]` (first of prior month), `date_to=[YYYY-MM-DD]` (last of prior month). Run these calls in parallel (one per state).
   → **Extract only**: per make/model — average_sale_price, sold_count. Reject any model with sold_count < 20 (see Gotcha #3). Discard full response.

2. **Get national baseline** — Call `mcp__marketcheck__get_sold_summary` with NO state filter, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `top_n=20`, same date range.
   → **Extract only**: per make/model — average_sale_price (national). Discard full response.

3. **Calculate arbitrage spreads** — For each model present in 2+ states:
   - **Price Index** per state = state_avg / national_avg × 100
   - **Cheapest state** and **most expensive state** for each model
   - **Gross Spread** = expensive_state_avg - cheap_state_avg
   - **Spread %** = gross_spread / cheap_state_avg × 100
   - **Transport Cost Estimate** = estimated distance x $1.50/mile (or $2.50/mile if expected hammer > $50k — see Gotcha #4). Use approximate state center-to-center distances. Add $200 flat for terminal fees.
   - **Net Arbitrage** = gross_spread - transport_cost - (gross_spread x 0.10 for wholesale discount adjustment, see Gotcha #2)
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

### Output Template

```
-- Geographic Arbitrage: [State A] vs [State B] vs ... — [Month Year] -------------

| Make/Model       | Cheap State | Cheap Avg  | Exp. State | Exp. Avg   | Gross Spread | Spread % | Transport | Net Profit |
|------------------|-------------|------------|------------|------------|------------- |----------|-----------|------------|
| Toyota RAV4      | OH          |    $26,200 | CA         |    $29,800 |       $3,600 |    13.7% |      $900 |     $2,340 |
| Ford F-150       | TX          |    $32,100 | NY         |    $36,500 |       $4,400 |    13.7% |    $1,100 |     $2,860 |
| ...              | ...         |        ... | ...        |        ... |          ... |      ... |       ... |        ... |

-- State Price Index ---------------------------------------------------------------
| State | Avg Sale Price | Price Index | Role             |
|-------|---------------|-------------|------------------|
| OH    |       $24,800 |        92.1 | SOURCE MARKET    |
| TX    |       $26,100 |        97.0 | NEUTRAL          |
| CA    |       $29,200 |       108.5 | DESTINATION      |

-- Top 5 Actionable Opportunities --------------------------------------------------
1. Source [Model] from [State] -> [State] auctions — $[X] net/unit
2. ...

-- Seasonal Notes ------------------------------------------------------------------
[Flag any known seasonal patterns for the analysis month]
```

## Self-Check (before presenting to user)

1. **Both states have sufficient volume** — Every model in the arbitrage table has sold_count > 20 in BOTH the cheap and expensive states. No thin-data opportunities slipped through.
2. **Net profit accounts for all costs** — Net = gross_spread - transport - wholesale discount adjustment. Verify no row shows net profit = gross spread (missing transport deduction).
3. **Transport cost uses correct rate** — Vehicles with expected value > $50k use $2.50/mile. All others use $1.50/mile. Terminal fee of $200 is included.
4. **Price index is internally consistent** — The average of all state price indices should be approximately 100 (it is the mean). Verify no state has an index of 0 or > 150 (likely data error).
5. **Seasonal flag is present** — If the analysis month is Oct-Mar, flag 4WD/AWD vehicles. If Apr-Sep, flag convertibles. Always include the seasonal notes section even if "No significant seasonal patterns for this period."
6. **US-only confirmation** — Verify the profile country is US. If UK, the skill should have exited early with an explanatory message.
