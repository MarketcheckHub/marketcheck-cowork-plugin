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

# Stocking Guide — Auction Buying Intelligence for Dealers

## Dealer Profile (Load First)

Before running any workflow, check for a saved dealer profile:

1. Read `~/.claude/marketcheck/dealer-profile.json`.
2. If the file **does not exist**: Tell the user: "No dealer profile found. Run `/onboarding` to set up your dealer context once." Then ask for the minimum required fields to proceed.
3. If the file **exists**, extract and use silently (do not ask the user for these):
   - `zip` or `postcode` ← `location.zip` (US) or `location.postcode` (UK)
   - `state` or `region` ← `location.state` (US) or `location.region` (UK)
   - `dealer_id` ← `dealer.dealer_id`
   - `dealer_type` ← `dealer.dealer_type`
   - `country` ← `location.country`
   - `radius` ← `preferences.default_radius_miles`
   - `target_margin` ← `preferences.target_margin_pct`
   - `recon_cost` ← `preferences.recon_cost_estimate`
   - `floor_plan_per_day` ← `preferences.floor_plan_cost_per_day`
   - `max_dom` ← `preferences.max_acceptable_dom`
   - `aging_threshold` ← `preferences.dom_aging_threshold`
   - `cpo_program` ← `dealer.cpo_program`
   - `cpo_certification_cost` ← `dealer.cpo_certification_cost`
4. **Tool routing by country:**
   - **US**: Use all tools — `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`, `get_sold_summary`
   - **UK**: Use `search_uk_active_cars` for supply data, `search_uk_recent_cars` for recent sales. VIN decode, ML price prediction, and sold summary are **not available** — use comp median for pricing, ask user for specs instead of VIN decode. Hot List and Avoid List workflows require `get_sold_summary` and are **US-only**. Pre-Auction VIN Check works for UK with comp-based pricing.
5. Confirm briefly: "Using profile: **[dealer.name]**, [ZIP/Postcode], [Country]"

All preference values (margin, recon cost, floor plan cost, etc.) are read from the dealer profile. Do not re-ask for these values.

## User Context

The primary user is a **dealer** (owner, buyer, or inventory manager) who attends 2-3 auctions per week and needs to make bid/no-bid decisions in minutes. They are buying 15-40 vehicles per month at auction and every bad buy ties up floor plan capital for 60-90+ days. The difference between data-driven and gut-instinct buying is $2,000-$3,000 per unit in avoided losses on slow movers.

The following fields are loaded from the dealer profile automatically:

| Field | Source | Default |
|-------|--------|---------|
| Dealer's ZIP / Postcode | `location.zip` or `location.postcode` | — |
| Dealer's state / region | `location.state` or `location.region` | — |
| Dealer type | `dealer.dealer_type` | Independent |
| Target retail margin % | `preferences.target_margin_pct` | 15% |
| Average recon cost per unit | `preferences.recon_cost_estimate` | $1,500 |
| Dealer ID | `dealer.dealer_id` | — |
| Radius for retail market | `preferences.default_radius_miles` | 75 miles |
| Floor plan cost per day | `preferences.floor_plan_cost_per_day` | $35 |
| Max acceptable days to retail | `preferences.max_acceptable_dom` | 45 days |

## Workflow: Pre-Auction VIN Check

Use this when a dealer says "check these VINs from tomorrow's auction" or "should I bid on this one." This is the most time-critical workflow — the dealer may be standing at the auction lane with 60 seconds to decide.

1. **Decode the VIN(s)** — For each VIN provided, call `mcp__marketcheck__decode_vin_neovin` with `vin`. Extract: year, make, model, trim, body_type, drivetrain, engine, fuel_type, transmission. Present a one-line summary per vehicle so the dealer can confirm they are looking at the right unit.

2. **Get predicted retail values (dual)** — For each VIN, make TWO calls to `mcp__marketcheck__predict_price_with_comparables`:
   - **Primary:** with `vin`, `miles`, `zip`, `dealer_type` matching the dealer's type from profile. This is the price the dealer can expect to retail at.
   - **Secondary:** with the OTHER `dealer_type`. This provides cross-market context.
   Record both predicted prices.

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

4. **Check recent sold velocity** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `state` (dealer's state), `inventory_type=Used`, `date_from` (first of prior month), `date_to` (last of prior month). Record: `sold_count` and `average_days_on_market`.

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

**Cross-reference with current lot:** If the dealer's lot data is available (from a prior lot-scanner run or dealer_id), check which hot-list models the dealer already has. Flag gaps.

Present the top 10 as: Rank, Make/Model, Avg Days to Sell, Monthly Sold Volume, Active Supply, D/S Ratio, **Franchise Median**, **Independent Median**, Max Auction Buy Price ([dealer_type] basis), On Your Lot?

## Workflow: Category Gap Finder

Use this when a dealer asks "is my inventory mix right" or "what categories am I missing."

1. **Get dealer's current inventory mix** — Call `mcp__marketcheck__search_active_cars` with `dealer_id` (dealer's ID), `facets=body_type|0|20|1,make|0|30|1,fuel_type|0|10|1`, `rows=0`. This returns the dealer's current inventory breakdown by body type, make, and fuel type without returning individual listings.

2. **Get market demand by category** — Call `mcp__marketcheck__get_sold_summary` with `state` (dealer's state), `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=15`.

3. **Get market demand by make** — Call `mcp__marketcheck__get_sold_summary` with `state` (dealer's state), `inventory_type=Used`, `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=25`.

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

2. **Get supply context** — For each of the top 20 slow movers, call `mcp__marketcheck__search_active_cars` with `make`, `model`, `state` (use `seller_state` or zip+radius), `car_type=used`, `stats=price,dom`, `rows=0`. Record: active supply count and average DOM of current unsold inventory.

3. **Get sold volume** — Call `mcp__marketcheck__get_sold_summary` with `state` (dealer's state), `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=asc`, `top_n=20`, `date_from` (first of prior month), `date_to` (last of prior month). Cross-reference with step 1 — models that are both slow AND low-volume are the most dangerous.

4. **Calculate holding cost exposure** — For each slow mover:
   - **Estimated holding period** = average_days_on_market from sold data
   - **Floor plan cost** = holding period x daily_floor_plan_cost
   - **Depreciation during hold** = (holding period / 30) x 1.5% x average_sale_price (assumes ~1.5% monthly depreciation while sitting)
   - **Total cost of slow turn** = floor_plan_cost + depreciation_during_hold
   - **Oversupply ratio** = active supply count / monthly sold_count (above 3.0 = dangerously oversupplied)

5. **Deliver the Avoid List** — Present a table: Make/Model, Avg Days to Sell, Monthly Sold Volume, Active Supply, Oversupply Ratio, Est. Floor Plan Cost, Est. Depreciation Loss, Total Holding Cost. Add a header warning: "Buying any of these models costs an estimated $X,XXX-$X,XXX in holding costs before you sell it. This directly reduces — or eliminates — your front-end gross."

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Max Bid Price | predicted_retail - margin% - recon_cost | Prevents overbidding at auction; every $500 over max bid comes directly from gross profit |
| Demand-to-Supply Ratio | monthly sold / active supply | Above 3.0 = strong (bid confidently), 1.5-3.0 = moderate (bid carefully), below 1.5 = oversupplied (avoid or lowball) |
| Expected Turn Days | average_days_on_market from sold data | Every 10 extra days = $350 floor plan cost + ~0.5% depreciation on a $25K unit ($125) = $475 lost |
| Projected Net Profit per Unit | retail - buy price - recon - floor plan - depreciation | The single number that matters; target $2,000+ for independent dealers to cover overhead |
| Inventory Mix Alignment Score | weighted average of category gap magnitudes | Score near 0 = well-aligned with market demand; every 5% gap in a major category = estimated 3-5 extra days average DOM across the lot |
| Floor Plan Cost Avoidance | slow-mover holding cost x units NOT purchased | The money saved by avoiding bad buys; 3 avoided slow movers/month x $2,500 avg holding cost = $7,500/month saved |

## Action-to-Outcome Funnel

1. **VIN scores BUY with demand-to-supply > 3.0 and turn < 30 days** — Bid up to the calculated max bid confidently. Expected outcome: retail sale within 25-35 days at target margin. If the auction price exceeds max bid by more than $500, walk away — the next lane will have another unit.

2. **VIN scores CAUTION with demand-to-supply 1.5-2.5** — Bid only if the auction price is 10%+ below max bid to create a cushion for the moderate turn time. If the vehicle has cosmetic issues that inflate recon above $2,000, convert this to a PASS. Expected turn: 35-50 days.

3. **VIN scores PASS but the dealer really wants it** — Show the holding cost math explicitly. A vehicle with 65-day average turn and $35/day floor plan costs $2,275 in floor plan alone before it sells. Add 2 months of depreciation (~3% on a $25K unit = $750). Total: $3,025 in invisible costs. The front-end gross needs to be $3,025+ just to break even.

4. **Hot List model appears on the auction run list** — Flag it proactively with the max bid calculation. These are the units worth driving to a farther auction to get. If the dealer's average monthly buy is 25 units, ideally 60%+ should come from the Hot List.

5. **Dealer's inventory is 15%+ over-indexed in a slow category** — Do not buy any more units in that category regardless of individual VIN scores. The lot-level oversupply in that category will drag DOM higher for all units in the category, not just the new one. Recommend holding until natural sales bring the category back into alignment.

## Output Format

Always present results in this structure, optimized for quick reading on a phone at the auction:

**For Pre-Auction VIN Checks (single VIN — keep it fast):**

```
VERDICT: BUY / CAUTION / PASS

Vehicle: 2022 Toyota RAV4 XLE AWD — 34,200 mi
VIN: XXXXXXXXXXXXXXXXX

Max Bid:        $24,800
Retail Value:   $30,500
Expected Turn:  28 days
Demand/Supply:  3.8 (strong)
Projected Net:  $2,950

Supply: 14 competing units within 75 mi
        Median asking: $31,200
        Fastest comp sold in 18 days
```

**For Pre-Auction VIN Checks (batch — table format):**

| VIN (last 8) | Vehicle | Verdict | Max Bid | Retail Value | Turn Days | D/S Ratio | Projected Net |
|---------------|---------|---------|---------|-------------|-----------|-----------|---------------|
| PA012345 | 22 RAV4 XLE | BUY | $24,800 | $30,500 | 28d | 3.8 | $2,950 |
| KB987654 | 21 Accord EXL | CAUTION | $21,200 | $26,800 | 42d | 2.1 | $1,600 |
| LM456789 | 20 Altima SR | PASS | $14,100 | $18,900 | 58d | 1.2 | $780 |

**For Hot List / Avoid List:**

Present as a numbered list with the most important models first. Include the Max Auction Buy Price for hot list items and the Estimated Holding Cost for avoid list items. Keep it to 10 items max — the dealer needs to remember these while walking the auction lanes.

**For Category Gap Analysis:**

Two short lists: "Buy More Of" and "Slow Down On" with the market vs dealer share numbers and a concrete unit count recommendation (e.g., "Add 3 more SUVs, reduce sedans by 2").
