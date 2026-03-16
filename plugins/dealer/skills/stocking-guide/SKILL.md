---
name: stocking-guide
description: >
  This skill should be used when the user asks to "what should I buy at auction",
  "auction run list check", "pre-auction analysis", "check these VINs before I bid",
  "hot sellers in my area", "what's turning fast", "stocking recommendations",
  "should I bid on this", "avoid list", "what to stock", "auction prep",
  "what's selling quick", "best vehicles to buy right now", "slow movers to avoid",
  "inventory mix check", "category gap analysis", or needs help with auction
  buying decisions, inventory stocking strategy, demand-to-supply analysis,
  or identifying which vehicles to actively seek or avoid at auction.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Stocking Guide — Auction Buying Intelligence for Dealers

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, dealer_id, dealer_type, country, radius, target_margin, recon_cost, floor_plan_per_day, max_dom, aging_threshold, cpo_program, cpo_certification_cost. Also extract: `default_inventory_type` from preferences (`"used"` | `"new"` | `"both"`; default `"used"` if not set). Apply as `car_type` in all supply/comp searches. Override if user explicitly states otherwise. Never mix new and used in the same report section. If missing, ask minimum fields. **US**: `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars`, `search_uk_recent_cars` only (no VIN decode/ML prediction/sold summary — use comp median; Hot List and Avoid List are US-only; Pre-Auction VIN Check works with comp pricing). Confirm: "Using profile: [dealer.name], [ZIP], [Country]". All preference values from profile — do not re-ask.

## User Context
Dealer (owner, buyer, inventory manager) making bid/no-bid decisions at auction in minutes; buying 15-40 units/month.

| Field | Source | Default |
|-------|--------|---------|
| ZIP, state, dealer_type, dealer_id | Profile | — |
| Target margin %, recon cost, radius | Profile | 15%, $1,500, 75mi |
| Floor plan/day, max DOM | Profile | $35, 45 days |

## Workflow: Pre-Auction VIN Check

Use this when a dealer says "check these VINs from tomorrow's auction" or "should I bid on this one." This is the most time-critical workflow — the dealer may be standing at the auction lane with 60 seconds to decide.

1. **Decode the VIN(s)** — For each VIN provided, call `mcp__marketcheck__decode_vin_neovin` with `vin`. Extract: year, make, model, trim, body_type, drivetrain, engine, fuel_type, transmission. Present a one-line summary per vehicle so the dealer can confirm they are looking at the right unit.
   → **Extract only**: year, make, model, trim, body_type, drivetrain, engine, fuel_type, transmission. Discard full response.

2. **Get predicted retail values (dual)** — For each VIN, make TWO calls to `mcp__marketcheck__predict_price_with_comparables`:
   - **Primary:** with `vin`, `miles`, `zip`, `dealer_type` matching the dealer's type from profile. This is the price the dealer can expect to retail at.
   - **Secondary:** with the OTHER `dealer_type`. This provides cross-market context.
   Record both predicted prices.
   → **Extract only**: predicted_price from each call. Discard full response.

2a. **CPO pricing (if dealer has CPO program)** — If `dealer.cpo_program=true` in profile and the vehicle is eligible for certification (used, recent model year, reasonable mileage):
   - Call `predict_price_with_comparables` with `is_certified=true` plus the dealer's `dealer_type` to get the CPO retail value.
   - Calculate **CPO Max Bid** = CPO predicted_retail × (1 - target_margin%) - recon_cost - cpo_certification_cost
   - Show both scenarios:
   ```
   IF CERTIFIED:
     CPO Retail Value: $XX,XXX | CPO Max Bid: $XX,XXX (includes $X,XXX cert cost)
   IF SOLD AS-IS:
     Standard Retail:  $XX,XXX | Standard Max Bid: $XX,XXX
   ```

3. **Check local supply** — For each VIN, call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from decode), `zip` (dealer's zip), `radius` (dealer's radius, default 75), `car_type=used`, `stats=price,dom`, `rows=5`, `sort_by=dom`, `sort_order=asc`. Record: total matching listings (supply count), median price, average DOM of active competing units.
   → **Extract only**: total_count (supply), median_price, avg_dom from stats. Discard full response.

4. **Check recent sold velocity** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `state` (dealer's state), `inventory_type=Used`, `date_from` (first of prior month), `date_to` (last of prior month). Record: `sold_count` and `average_days_on_market`.
   → **Extract only**: sold_count, average_days_on_market. Discard full response.

5. **Calculate the verdict** — For each VIN, compute:
   - **Max Bid** = PRIMARY predicted_retail_price × (1 - target_margin%) - recon_cost
   - **Demand-to-Supply Ratio** = monthly sold_count / active supply count. Above 3.0 = strong demand, 1.5-3.0 = moderate, below 1.5 = oversupplied.
   - **Expected Turn Days** = average_days_on_market from sold data
   - **Estimated Floor Plan Cost** = expected_turn_days x daily_floor_plan_cost
   - **Projected Net Profit** = predicted_retail_price - max_bid - recon_cost - floor_plan_cost

   Assign a verdict:
   - **BUY** — Demand-to-supply ratio > 2.5, expected turn < 35 days, projected profit > $2,000
   - **CAUTION** — Demand-to-supply ratio 1.5-2.5, expected turn 35-50 days, projected profit $1,000-$2,000
   - **PASS** — Demand-to-supply ratio < 1.5, expected turn > 50 days, or projected profit < $1,000

   Show both market values:
   ```
   Franchise Retail Value:    $XX,XXX
   Independent Retail Value:  $XX,XXX
   Your Retail (based on [type]): $XX,XXX ← used for Max Bid
   Max Bid:                   $XX,XXX
   ```

## Workflow: Hot List Generator

Use this when a dealer asks "what's selling fast in my area" or "what should I actively look for at auction this week."

**Multi-agent approach:** Use the `market-demand-agent` to generate the hot list with all demand analytics in a single agent call.

Use the Agent tool to spawn the `dealer:market-demand-agent` agent with this prompt:

> Generate stocking hot list for state=[state], dealer_type=[dealer_type], zip=[zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Date range: [first day of prior month] to [last day of prior month]. Sections: hot_list.

The agent will:
1. Get fastest-turning models via `get_sold_summary` (by average_days_on_market)
2. Get highest-volume sellers via `get_sold_summary` (by sold_count)
3. Check supply for cross-referenced models via `search_active_cars` (rows=0)
4. Calculate D/S ratios, opportunity scores, and max auction buy prices
5. Return a ranked top 10 hot list

**Cross-reference with current lot:** If the dealer's lot data is available (from a prior lot-scanner run, dealer_id, or source/domain), check which hot-list models the dealer already has. Flag gaps.

Present the top 10 as: Rank, Make/Model, Avg Days to Sell, Monthly Sold Volume, Active Supply, D/S Ratio, **Franchise Median**, **Independent Median**, Max Auction Buy Price ([dealer_type] basis), On Your Lot?

## Workflow: Category Gap Finder

Use this when a dealer asks "is my inventory mix right" or "what categories am I missing."

1. **Get dealer's current inventory mix** — Call `mcp__marketcheck__search_active_cars` with the best available dealer identifier: `dealer_id` (preferred) or `source` (web domain) if dealer_id unavailable. Add `facets=body_type|0|20|1,make|0|30|1,fuel_type|0|10|1`, `rows=0`. This returns the dealer's current inventory breakdown by body type, make, and fuel type without returning individual listings.
   → **Extract only**: facet counts per body_type, make, fuel_type; total inventory count. Discard full response.

2. **Get market demand by category** — Call `mcp__marketcheck__get_sold_summary` with `state` (dealer's state), `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=15`.
   → **Extract only**: per body_type — sold_count. Discard full response.

3. **Get market demand by make** — Call `mcp__marketcheck__get_sold_summary` with `state` (dealer's state), `inventory_type=Used`, `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=25`.
   → **Extract only**: per make — sold_count. Discard full response.

4. **Calculate alignment score** — For each body type and make:
   - **Dealer share** = dealer's count in that category / dealer's total inventory x 100
   - **Market share** = market sold_count in that category / total market sold_count x 100
   - **Gap** = Market share - Dealer share (positive = dealer is under-indexed, negative = over-indexed)
   - Flag gaps > 5 percentage points as significant mismatches

5. **Deliver the gap analysis** — Present two tables:
   - **Under-stocked categories** (market share > dealer share by 5%+): these are categories the dealer should buy more of at auction. Include the market turn rate and average price for context.
   - **Over-stocked categories** (dealer share > market share by 5%+): these are categories where the dealer has excess exposure. Recommend slowing acquisition and letting natural sales reduce the count.
   Include a one-line mix recommendation (e.g., "Your lot is 40% sedans but your market is 55% SUVs — shift 3-4 units per month from sedans to SUVs").

## Workflow: Avoid List (Slow Movers)

Use this when a dealer asks "what should I stay away from" or "which vehicles are sitting." This prevents the most costly mistake: buying a vehicle that sits for 90+ days eating floor plan.

1. **Get slowest-turning models** — Call `mcp__marketcheck__get_sold_summary` with `state` (dealer's state), `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_days_on_market`, `ranking_order=desc`, `top_n=20`, `date_from` (first of prior month), `date_to` (last of prior month). These are models with the longest average time to sell.
   → **Extract only**: per make/model — average_days_on_market, sold_count. Discard full response.

2. **Get supply context** — For each of the top 20 slow movers, call `mcp__marketcheck__search_active_cars` with `make`, `model`, `state` (use `seller_state` or zip+radius), `car_type=used`, `stats=price,dom`, `rows=0`. Record: active supply count and average DOM of current unsold inventory.
   → **Extract only**: total_count (supply), avg_dom, avg_price from stats. Discard full response.

3. **Get sold volume** — Call `mcp__marketcheck__get_sold_summary` with `state` (dealer's state), `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=asc`, `top_n=20`, `date_from` (first of prior month), `date_to` (last of prior month). Cross-reference with step 1 — models that are both slow AND low-volume are the most dangerous.
   → **Extract only**: per make/model — sold_count. Discard full response.

4. **Calculate holding cost exposure** — For each slow mover:
   - **Estimated holding period** = average_days_on_market from sold data
   - **Floor plan cost** = holding period x daily_floor_plan_cost
   - **Depreciation during hold** = (holding period / 30) x 1.5% x average_sale_price (assumes ~1.5% monthly depreciation while sitting)
   - **Total cost of slow turn** = floor_plan_cost + depreciation_during_hold
   - **Oversupply ratio** = active supply count / monthly sold_count (above 3.0 = dangerously oversupplied)

5. **Deliver the Avoid List** — Present a table: Make/Model, Avg Days to Sell, Monthly Sold Volume, Active Supply, Oversupply Ratio, Est. Floor Plan Cost, Est. Depreciation Loss, Total Holding Cost. Add a header warning: "Buying any of these models costs an estimated $X,XXX-$X,XXX in holding costs before you sell it. This directly reduces — or eliminates — your front-end gross."

## Output
Present: BUY/CAUTION/PASS verdict per VIN with max bid, retail value, expected turn, D/S ratio, projected net profit. Batch VINs as table. Hot/Avoid lists as ranked top-10. Category gaps as "Buy More Of" / "Slow Down On" with unit count recommendations. Optimize for phone readability at auction.
