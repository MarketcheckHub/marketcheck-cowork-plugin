---
name: depreciation-tracker
description: >
  This skill should be used when the user asks about "depreciation rate",
  "value retention", "residual value", "how fast is it losing value",
  "which cars hold value", "EV depreciation", "price trend over time",
  "brand value ranking", "depreciation curve", "residual forecast",
  "MSRP parity", "price over sticker", "incentive effectiveness",
  "geographic value variance", "which states have higher prices",
  or needs help with vehicle depreciation analysis, residual value forecasting,
  segment value comparisons, brand retention rankings, or MSRP-to-transaction
  price tracking across new and used vehicles for a multi-location dealer group.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Depreciation Tracker — Vehicle Value Retention & Depreciation Intelligence

## Dealer Group Profile (Load First -- Optional Context)

Load `~/.claude/marketcheck/dealership-group-profile.json`. If exists, extract: `group_name`, `locations[]`, `preferences`; from default location: `state`, `franchise_brands`, `dealer_type`, `country`. If missing, ask for fields. US-only (`get_sold_summary` + `search_active_cars`); UK → not available. Confirm profile.

## User Context

Dealer group executive or inventory director tracking collateral value decline to manage floor plan exposure and stocking; also serves lenders, OEM analysts, and appraisers.

| Required | Field | Source |
|----------|-------|--------|
| Yes | Make/Model or segment | Ask |
| Recommended | Model year(s) | Ask |
| Auto/Ask | State/ZIP, dealer_type | Profile or ask |
| Optional | Inventory type, comparison dimension, time horizon | Ask |

Clarify: used-vehicle depreciation vs new-vehicle MSRP parity (different workflows).

## Workflow: Make/Model Depreciation Curve

Use this when a user asks "how fast is the RAV4 losing value" or "show me the depreciation curve for a 2022 Civic."

1. **Get current period sold data** — Call `get_sold_summary` with `make`, `model`, `inventory_type=Used`, `date_from` (first of prior month), `date_to` (end of prior month). Include `state` if specified.
   → **Extract only**: average_sale_price, sold_count. Discard full response.

2. **Get historical sold data at multiple intervals** — Make separate calls to `get_sold_summary` for each lookback period:
   - **60 days ago**
   - **90 days ago**
   - **6 months ago**
   - **1 year ago**
   Record `average_sale_price` at each point. Adjust dates based on today's date.
   → **Extract only**: average_sale_price per interval. Discard full response.

3. **Get current active market asking price** — Call `search_active_cars` with `year`, `make`, `model`, `car_type=used`, `stats=price`, `rows=0`. Include `zip`/`state` if available.
   → **Extract only**: mean, median, min, max price stats. Discard full response.

4. **Get original MSRP baseline** — Call `search_active_cars` with same YMMT, `rows=1`, `sort_by=price`, `sort_order=desc`. Decode the VIN for MSRP. Fallback: highest 1-year-ago sold price.
   → **Extract only**: msrp from decode. Discard full response.

5. **Build the depreciation curve** — Calculate at each time interval:
   - **Retention %** = (average_sale_price at interval / original MSRP) x 100
   - **Monthly depreciation rate** = (price change between consecutive intervals) / (months between intervals)
   - **Annualized depreciation rate** = monthly rate x 12
   Present as a table and describe the curve shape (linear, accelerating, stabilizing).

## Workflow: Segment Value Trends

Use this when a user asks "are SUVs holding value better than sedans" or "how is EV depreciation compared to ICE."

1. **Get current period segment data** — Call `get_sold_summary` with `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `date_from` (first of prior month), `date_to` (end of prior month), `inventory_type=Used`, `top_n=10`.
   → **Extract only**: per body_type — average_sale_price, sold_count. Discard full response.

2. **Get prior period segment data** — Same call with dates shifted back 3 months (or user's chosen comparison window).
   → **Extract only**: per body_type — average_sale_price, sold_count. Discard full response.

3. **Get fuel type comparison** — Call `get_sold_summary` with `fuel_type_category=EV`, current period dates, `inventory_type=Used`. Repeat with `fuel_type_category=ICE`. Repeat both for prior period.
   → **Extract only**: average_sale_price, sold_count per fuel_type per period. Discard full response.

4. **Calculate segment trends** — For each body type and fuel type:
   - **Period-over-period price change** = (current avg price - prior avg price) / prior avg price x 100
   - **Volume change** = (current sold_count - prior sold_count) / prior sold_count x 100
   - Flag segments where price declined more than 3% as "accelerating depreciation"
   - Flag segments where price held within +/- 1% as "stable"
   - Flag segments where price increased as "appreciating" (rare but happens with supply constraints)

5. **Deliver the segment comparison** — Present a ranked table from strongest retention to weakest. Highlight the EV vs ICE gap specifically (this is the most commonly requested comparison). Include volume context — a segment with strong prices but falling volume may be about to soften.

## Workflow: Brand Residual Ranking

Use this when a user asks "which brands hold value best" or "rank the automakers by residual value."

1. **Get current period brand prices** — Call `get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (end of prior month), `inventory_type=Used`, `top_n=25`.
   → **Extract only**: per make — average_sale_price. Discard full response.

2. **Get prior period brand prices** — Same call with dates shifted back 6 months.
   → **Extract only**: per make — average_sale_price. Discard full response.

3. **Get volume context** — Call `get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, current period dates, `inventory_type=Used`, `top_n=25`.
   → **Extract only**: per make — sold_count. Discard full response.

4. **Calculate brand retention scores** — For each make:
   - **Retention %** = current average_sale_price / prior average_sale_price x 100
   - **Volume trend** = current sold_count vs prior sold_count (indicates demand strength)
   - Rank brands by retention % descending
   - Separate into tiers: Tier 1 (>98% retention), Tier 2 (95-98%), Tier 3 (90-95%), Tier 4 (<90%)

5. **Present the brand ranking** — Show a ranked table with: Rank, Make, Current Avg Price, Prior Avg Price, Retention %, Volume, Tier. Highlight notable movers (brands that jumped or dropped tiers since the last period). Highlight the group's franchise brands with a marker.

## Workflow: Geographic Depreciation Variance

Use this when a user asks "where do Tacomas hold value best" or "which states have the highest used car prices." Particularly useful for dealer groups operating across multiple states.

1. **Get state-level transaction data** — Call `get_sold_summary` with `make`, `model`, `summary_by=state`, `date_from` (first of prior month), `date_to` (end of prior month), `inventory_type=Used`, `limit=5000`.
   → **Extract only**: per state — average_sale_price, sold_count. Discard full response.

2. **Get national baseline** — Same call without `summary_by` for national average.
   → **Extract only**: average_sale_price, sold_count. Discard full response.

3. **Calculate geographic variance** — For each state:
   - **Price index** = state average_sale_price / national average_sale_price x 100 (100 = national average)
   - **Premium/discount** = state price - national price in dollars
   - Sort by price index descending to show where vehicles command the highest premiums

4. **Identify patterns** — Group states into:
   - **Premium markets** (index > 105): vehicles retain more value, typically lower supply or higher demand
   - **At-national-average** (index 95-105): mainstream pricing
   - **Discount markets** (index < 95): vehicles depreciate faster, often oversupplied or lower demand
   Note regional patterns. Highlight states where group locations operate.

5. **Deliver the geographic map** — Present as a ranked table: State, Avg Transaction Price, National Avg, Price Index, Premium/Discount $, Sold Count. Highlight the top 5 and bottom 5 states for the specific vehicle. Flag any cross-location transfer or sourcing opportunities.

## Workflow: MSRP Parity Tracker

Use this when a user asks "which new cars are selling over sticker" or "are markups coming down" or "incentive effectiveness."

1. **Get current MSRP parity data** — Call `get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (end of prior month), `top_n=30`.
   → **Extract only**: per make/model — price_over_msrp_percentage. Discard full response.

2. **Get prior period parity data** — Same call with dates shifted back 3 months.
   → **Extract only**: per make/model — price_over_msrp_percentage. Discard full response.

3. **Get volume context** — Call `get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, current period dates, `top_n=30`.
   → **Extract only**: per make/model — sold_count. Discard full response.

4. **Classify parity status** — For each make/model:
   - **Above MSRP** (price_over_msrp_percentage > 0): dealer markups or strong demand
   - **At MSRP** (price_over_msrp_percentage between -1% and 0%): balanced market
   - **Below MSRP** (price_over_msrp_percentage < -1%): incentives/discounts active
   - **Trend direction**: compare current vs prior period to show if markups are growing or shrinking

5. **Present the parity report** — Show a table: Make/Model, Current % Over/Under MSRP, Prior Period %, Change Direction, Sold Volume. Highlight:
   - Models that flipped from above-MSRP to below (incentive programs taking effect)
   - Models still commanding premiums (constrained supply or high demand)
   - Models with deepening discounts (potential oversupply or model-year transition)

## Output

Present: depreciation headline with retention % and monthly rate, trend table (period, avg price, retention %, monthly rate, volume), comparison context vs segment/peers, key signals (acceleration, volume shifts, geographic anomalies), and one actionable recommendation with dollar impact.
