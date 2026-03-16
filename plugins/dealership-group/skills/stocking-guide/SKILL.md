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

# Stocking Guide — Auction Buying Intelligence for Dealer Group Locations

## Dealer Group Profile (Load First)

Load the `marketcheck-profile.md` project memory file. If missing, prompt `/onboarding` and ask minimum fields.

**Extract group-level preferences:** `country`, `default_radius_miles` (→ `radius`), `target_margin_pct` (→ `target_margin`), `recon_cost_estimate` (→ `recon_cost`), `floor_plan_cost_per_day` (→ `floor_plan_per_day`), `max_acceptable_dom` (→ `max_dom`).

**Extract per-location data — iterate through ALL entries in `dealer_group.locations[]`:**
For each location, extract: `name`, `zip` (US) or `postcode` (UK), `state` (US) or `region` (UK), `dealer_id`, `dealer_type`, `web_domain`, `franchise_brands`, `cpo_program`, `cpo_certification_cost`.
Store as a named location list: e.g. `locations = [{name, zip, state, dealer_id, dealer_type, web_domain}, ...]`.
Never fall back to a single group-level zip — every workflow must use the **specific location's zip/postcode and state/region**.

**Inventory type:** Read `preferences.default_inventory_type` from profile (`"used"` | `"new"` | `"both"`; default `"used"` if not set). Apply as `car_type` in all supply/comp searches across every location. Override if user explicitly states otherwise. Never mix new and used in the same report section.

**Country routing:** US locations: all tools available. UK locations: `search_uk_active_cars` + `search_uk_recent_cars` only (Hot List/Avoid List US-only; Pre-Auction VIN Check works with comp-based pricing). Do not re-ask profile preference values. Confirm: "Loaded [N] locations: [name1] ([zip1], [state1]), [name2] ([zip2], [state2]), ... | Inventory: [used/new/both]"

## User Context

Dealer group buyer (buyer, inventory manager, or GM) making bid/no-bid decisions at auction in minutes for one or more locations.

All fields auto-loaded from profile: per-location ZIP/postcode, state, dealer_type, dealer_id; group-level target_margin (15%), recon_cost ($1,500), radius (75mi), floor_plan_per_day ($35), max_dom (45d).

## Workflow: Pre-Auction VIN Check

Use this when a dealer says "check these VINs from tomorrow's auction" or "should I bid on this one." This is the most time-critical workflow — the dealer may be standing at the auction lane with 60 seconds to decide.

**Location selection:** If the group has more than one location, confirm which location is bidding on this VIN (or each VIN if different). Use that location's `zip`, `state`, `dealer_id`, and `dealer_type` for all steps below. If unspecified, default to the location whose state matches the auction location, or ask once.

1. **Decode the VIN(s)** — For each VIN provided, call `mcp__marketcheck__decode_vin_neovin` with `vin`.
   → **Extract only**: year, make, model, trim, body_type, drivetrain, engine, fuel_type, transmission. Discard full response.

2. **Get predicted retail values (dual)** — For each VIN, make TWO calls to `mcp__marketcheck__predict_price_with_comparables`:
   - **Primary:** with `vin`, `miles`, `zip`, `dealer_type` matching the selected location's type from profile. This is the price the dealer can expect to retail at.
   - **Secondary:** with the OTHER `dealer_type`. This provides cross-market context.
   → **Extract only**: predicted_price (primary + secondary), comp count. Discard full response.

2a. **CPO pricing (if group has CPO program)** — If `dealer_group.cpo_program=true` in profile and the vehicle is eligible for certification (used, recent model year, reasonable mileage):
   - Call `predict_price_with_comparables` with `is_certified=true` plus the location's `dealer_type` to get the CPO retail value.
   - Calculate **CPO Max Bid** = CPO predicted_retail x (1 - target_margin%) - recon_cost - cpo_certification_cost
   - Show both scenarios:
   ```
   IF CERTIFIED:
     CPO Retail Value: $XX,XXX | CPO Max Bid: $XX,XXX (includes $X,XXX cert cost)
   IF SOLD AS-IS:
     Standard Retail:  $XX,XXX | Standard Max Bid: $XX,XXX
   ```

3. **Check local supply** — For each VIN, call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from decode), `zip` (location's zip), `radius` (from preferences, default 75), `car_type=used`, `stats=price,dom`, `rows=5`, `sort_by=dom`, `sort_order=asc`.
   → **Extract only**: total count (supply), median price (stats), avg DOM (stats). Discard full response.

4. **Check recent sold velocity** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `state` (location's state), `inventory_type=Used`, `date_from` (first of prior month), `date_to` (last of prior month).
   → **Extract only**: sold_count, average_days_on_market. Discard full response.

5. **Calculate the verdict** — For each VIN, compute:
   - **Max Bid** = PRIMARY predicted_retail_price x (1 - target_margin%) - recon_cost
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

**Multi-agent approach — run per location:** For each location in the group, spawn a separate `dealership-group:market-demand-agent` using that location's specific `zip` and `state`. Locations in the same state may be grouped into a single agent call to avoid redundant API requests (pass the state once, note which locations it covers).

For each location (or unique state group), use the Agent tool to spawn the `dealership-group:market-demand-agent` with this prompt:

> Generate stocking hot list for state=[location.state], dealer_type=[location.dealer_type], zip=[location.zip], radius=[radius], target_margin_pct=[target_margin], recon_cost=[recon_cost]. Date range: [first day of prior month] to [last day of prior month]. Sections: hot_list. Location label: [location.name].

The agent will:
1. Get fastest-turning models via `get_sold_summary` (by average_days_on_market)
2. Get highest-volume sellers via `get_sold_summary` (by sold_count)
3. Check supply for cross-referenced models via `search_active_cars` with that location's `zip` + `radius` (rows=0)
4. Calculate D/S ratios, opportunity scores, and max auction buy prices
5. Return a ranked top 10 hot list for that location's trade area

**Cross-reference with current lot per location:** Using each location's `dealer_id` or `web_domain`, call `search_active_cars` with `facets=make,model|0|30|1`, `rows=0` to get current inventory. Flag which hot-list models that specific location already has vs. gaps.

**Consolidation:** After all per-location agents complete, present results as a **location-by-location** breakdown with each location's name, zip, and top 10. If the user requests a group rollup, produce a deduplicated group-wide top 10 weighted by the location with the largest gap.

Present per location: Location Name (ZIP), Rank, Make/Model, Avg Days to Sell, Monthly Sold Volume, Active Supply in Trade Area, D/S Ratio, **Franchise Median**, **Independent Median**, Max Auction Buy Price ([location.dealer_type] basis), On This Location's Lot?

## Workflow: Category Gap Finder

Use this when a dealer asks "is my inventory mix right" or "what categories am I missing."

Run for each location independently. Deduplicate state-level market demand queries — if multiple locations share the same state, run `get_sold_summary` once per unique state and reuse the result across those locations.

**For each location:**

1. **Get this location's current inventory mix** — Call `mcp__marketcheck__search_active_cars` with this location's best available identifier: `dealer_id` (preferred) or `source` = `web_domain` if dealer_id unavailable. Add `facets=body_type|0|20|1,make|0|30|1,fuel_type|0|10|1`, `rows=0`.
   → **Extract only**: facet counts per body_type, make, fuel_type; total count. Discard full response.

2. **Get market demand by category** — Call `mcp__marketcheck__get_sold_summary` with `state` = **this location's state**, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=15`.
   → **Extract only**: per body_type — sold_count. Discard full response. (Skip if same state already queried; reuse result.)

3. **Get market demand by make** — Call `mcp__marketcheck__get_sold_summary` with `state` = **this location's state**, `inventory_type=Used`, `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=25`.
   → **Extract only**: per make — sold_count. Discard full response. (Skip if same state already queried; reuse result.)

4. **Calculate alignment score** — For each body type and make:
   - **Location share** = this location's count in that category / this location's total inventory x 100
   - **Market share** = market sold_count in that category / total market sold_count x 100
   - **Gap** = Market share - Location share (positive = under-indexed, negative = over-indexed)
   - Flag gaps > 5 percentage points as significant mismatches

5. **Deliver the gap analysis per location** — For each location, present two tables:
   - **Under-stocked categories** (market share > location share by 5%+): categories this rooftop should buy more of at auction. Include market turn rate and average price.
   - **Over-stocked categories** (location share > market share by 5%+): categories with excess exposure. Recommend slowing acquisition.
   Include a one-line mix recommendation per location (e.g., "[Location Name]: Your lot is 40% sedans but your [state] market is 55% SUVs — shift 3-4 units per month from sedans to SUVs").

## Workflow: Avoid List (Slow Movers)

Use this when a dealer asks "what should I stay away from" or "which vehicles are sitting." This prevents the most costly mistake: buying a vehicle that sits for 90+ days eating floor plan.

The Avoid List is state-scoped. Run once per unique state represented across the group's locations. Label each result clearly with the state(s) and the locations it applies to. If the group spans multiple states, run separate queries per state.

1. **Get slowest-turning models** — For each unique state in the group, call `mcp__marketcheck__get_sold_summary` with `state` = **that state**, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_days_on_market`, `ranking_order=desc`, `top_n=20`, `date_from` (first of prior month), `date_to` (last of prior month). Label the result with the state and which locations it covers.
   → **Extract only**: per make/model — average_days_on_market. Discard full response.

2. **Get supply context** — For each of the top 20 slow movers, call `mcp__marketcheck__search_active_cars` with `make`, `model`, `state`, `car_type=used`, `stats=price,dom`, `rows=0`.
   → **Extract only**: per make/model — active supply count, avg DOM from stats. Discard full response.

3. **Get sold volume** — For each unique state, call `mcp__marketcheck__get_sold_summary` with `state` = **that state**, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=asc`, `top_n=20`, `date_from` (first of prior month), `date_to` (last of prior month).
   → **Extract only**: per make/model — sold_count. Discard full response.

4. **Calculate holding cost exposure** — For each slow mover:
   - **Estimated holding period** = average_days_on_market from sold data
   - **Floor plan cost** = holding period x daily_floor_plan_cost
   - **Depreciation during hold** = (holding period / 30) x 1.5% x average_sale_price (assumes ~1.5% monthly depreciation while sitting)
   - **Total cost of slow turn** = floor_plan_cost + depreciation_during_hold
   - **Oversupply ratio** = active supply count / monthly sold_count (above 3.0 = dangerously oversupplied)

5. **Deliver the Avoid List** — Present a table: Make/Model, Avg Days to Sell, Monthly Sold Volume, Active Supply, Oversupply Ratio, Est. Floor Plan Cost, Est. Depreciation Loss, Total Holding Cost. Add a header warning: "Buying any of these models costs an estimated $X,XXX-$X,XXX in holding costs before you sell it. This directly reduces — or eliminates — your front-end gross."

## Output

Present: BUY/CAUTION/PASS verdict with max bid, retail value, turn days, D/S ratio, and projected net per VIN. For batch: table format. For hot/avoid lists: top 10 ranked with max buy price or holding cost. For gap analysis: "Buy More Of" and "Slow Down On" lists with unit count recommendations.
