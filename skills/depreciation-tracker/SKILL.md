---
name: depreciation-tracker
description: >
  Vehicle depreciation and value retention analysis. Triggers: "depreciation rate",
  "value retention", "residual value", "how fast is it losing value",
  "which cars hold value", "EV depreciation", "price trend over time",
  "brand value ranking", "depreciation curve", "residual forecast",
  "MSRP parity", "price over sticker", "incentive effectiveness",
  "geographic value variance", "which states have higher prices",
  residual value forecasting, segment value comparisons, brand retention
  rankings, MSRP-to-transaction price tracking.
version: 0.1.0
---

# Depreciation Tracker — Vehicle Value Retention & Depreciation Intelligence

## Dealer Profile (Load First — Optional Context)

→ Full procedure: read `_references/profile-loading.md`

Parse `marketcheck-profile.md` if it exists → extract: `state`, `franchise_brands`, `dealer_type`, `country`. This skill works fine without a profile.

**US-only:** This skill requires `get_sold_summary`. If `country == UK`: inform "Depreciation tracking requires US sold transaction data and is not available for the UK market." → Full limitations: `_references/country-routing.md`

Confirm: "Using profile context: **[state]**"

## User Context

The primary user is a **lender** (residual value analyst, portfolio risk manager, or auto finance director) who needs to understand how quickly collateral values are declining to set accurate residual forecasts and manage portfolio exposure. Secondary users include **OEM analysts** evaluating incentive effectiveness and brand value positioning, and **appraisers** who need trend-adjusted valuations that account for recent depreciation velocity rather than stale book values.

The following fields may be auto-filled from the dealer profile:

| Required | Field | Source |
|----------|-------|--------|
| Yes | Make and/or Model (or segment) | Always ask |
| Recommended | Model year(s) of interest | Always ask |
| Auto/Ask | Geography (state or zip) | Profile `location.state` or ask |
| Optional | Inventory type | `New` or `Used` (default: `Used`) |
| Auto/Ask | Dealer type filter | Profile `dealer.dealer_type` or ask |
| Optional | Comparison dimension | `EV vs ICE`, `SUV vs Sedan`, `Brand A vs Brand B` |
| Optional | Time horizon | `30 days`, `90 days`, `6 months`, `1 year` |

Always clarify whether the user wants depreciation of **used vehicles** (price decline over time on the secondary market) or **new vehicle transaction-to-MSRP parity** (how much above or below sticker new cars are actually selling). These are different workflows.

## Gotchas

- **US-only** — this skill requires `get_sold_summary` for transaction data. UK dealers cannot use depreciation tracking. Inform them immediately if `country == UK`.
- **Clarify used vs new upfront** — "depreciation" means different things: for used vehicles it's price decline on the secondary market; for new vehicles it's transaction-to-MSRP parity (how much above or below sticker). These are different workflows (Make/Model Depreciation Curve vs MSRP Parity Tracker).
- **Share change must be in basis points (bps)** — a move from 14.2% to 14.5% is "+30 bps", not "+0.3%". This applies to Brand Residual Ranking tier changes.
- **Quarterly data requires 3 separate monthly calls aggregated** — `get_sold_summary` works on monthly date ranges. For quarterly analysis, call each month separately and combine.
- **MSRP baseline fallback** — if VIN decode doesn't return MSRP, use the highest transaction price from 1-year-ago sold data as a proxy ceiling. This is a rough approximation, not exact.
- **Retention % calculation** uses original MSRP as denominator — `(current_avg_price / original_MSRP) × 100`. This means a 3-year-old vehicle at 87% retention has lost 13% of its original value.

## Workflow: Make/Model Depreciation Curve

Use this when a user asks "how fast is the RAV4 losing value" or "show me the depreciation curve for a 2022 Civic."

1. **Get current period sold data** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `date_from` set to the first of the current month minus 30 days (e.g., `2026-02-01`), `date_to` set to the last day of that month (e.g., `2026-02-28`). If the user specified a state, include `state`. Record the `average_sale_price` and `sold_count`.

2. **Get historical sold data at multiple intervals** — Make separate calls to `mcp__marketcheck__get_sold_summary` for each lookback period to build the curve:
   - **60 days ago**: `date_from=2026-01-01`, `date_to=2026-01-31`
   - **90 days ago**: `date_from=2025-12-01`, `date_to=2025-12-31`
   - **6 months ago**: `date_from=2025-09-01`, `date_to=2025-09-30`
   - **1 year ago**: `date_from=2025-03-01`, `date_to=2025-03-31`
   Record `average_sale_price` at each point. Adjust the actual dates based on today's date.

3. **Get current active market asking price** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `car_type=used`, `stats=price`, `rows=0`. If state/zip was provided, include `zip` and `radius=100` or `state` in the `seller_name` filter. This gives the current asking price stats (mean, median, min, max) for unsold inventory — the forward-looking indicator.

4. **Get original MSRP baseline** — Call `mcp__marketcheck__search_active_cars` with the same `year`, `make`, `model`, `rows=1`, `sort_by=price`, `sort_order=desc` to find a representative listing. Then call `mcp__marketcheck__decode_vin_neovin` with that listing's VIN to extract the original MSRP from the build data. If MSRP is not available from the decode, use the highest transaction price from the 1-year-ago sold data as a proxy ceiling.

5. **Build the depreciation curve** — Calculate at each time interval:
   - **Retention %** = (average_sale_price at interval / original MSRP) x 100
   - **Monthly depreciation rate** = (price change between consecutive intervals) / (months between intervals)
   - **Annualized depreciation rate** = monthly rate x 12
   Present as a table and describe the curve shape (linear, accelerating, stabilizing).

## Workflow: Segment Value Trends

Use this when a user asks "are SUVs holding value better than sedans" or "how is EV depreciation compared to ICE."

1. **Get current period segment data** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `date_from` (first of prior month), `date_to` (last of prior month), `inventory_type=Used`, `top_n=10`. This returns average transaction prices by body type for the current period.

2. **Get prior period segment data** — Call `mcp__marketcheck__get_sold_summary` with the same parameters but `date_from` and `date_to` shifted back 3 months (or the user's chosen comparison window). This gives the baseline for calculating segment-level price movement.

3. **Get fuel type comparison** — Call `mcp__marketcheck__get_sold_summary` with `fuel_type_category=EV`, `date_from` (current period), `date_to` (current period end), `inventory_type=Used`. Record the average sale price and sold count. Repeat with `fuel_type_category=ICE`. Repeat both calls for the prior period.

4. **Calculate segment trends** — For each body type and fuel type:
   - **Period-over-period price change** = (current avg price - prior avg price) / prior avg price x 100
   - **Volume change** = (current sold_count - prior sold_count) / prior sold_count x 100
   - Flag segments where price declined more than 3% as "accelerating depreciation"
   - Flag segments where price held within +/- 1% as "stable"
   - Flag segments where price increased as "appreciating" (rare but happens with supply constraints)

5. **Deliver the segment comparison** — Present a ranked table from strongest retention to weakest. Highlight the EV vs ICE gap specifically (this is the most commonly requested comparison). Include volume context — a segment with strong prices but falling volume may be about to soften.

## Workflow: Brand Residual Ranking

Use this when a user asks "which brands hold value best" or "rank the automakers by residual value."

1. **Get current period brand prices** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `inventory_type=Used`, `top_n=25`.

2. **Get prior period brand prices** — Call `mcp__marketcheck__get_sold_summary` with the same parameters but dates shifted back 6 months (or user's preferred comparison window). This establishes the baseline for retention calculation.

3. **Get volume context** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (current period), `date_to` (current period end), `inventory_type=Used`, `top_n=25`.

4. **Calculate brand retention scores** — For each make:
   - **Retention %** = current average_sale_price / prior average_sale_price x 100
   - **Volume trend** = current sold_count vs prior sold_count (indicates demand strength)
   - Rank brands by retention % descending
   - Separate into tiers: Tier 1 (>98% retention), Tier 2 (95-98%), Tier 3 (90-95%), Tier 4 (<90%)

5. **Present the brand ranking** — Show a ranked table with: Rank, Make, Current Avg Price, Prior Avg Price, Retention %, Volume, Tier. Highlight notable movers (brands that jumped or dropped tiers since the last period).

## Workflow: Geographic Depreciation Variance

Use this when a user asks "where do Tacomas hold value best" or "which states have the highest used car prices."

1. **Get state-level transaction data** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model` (from user), `summary_by=state`, `date_from` (first of prior month), `date_to` (last of prior month), `inventory_type=Used`, `limit=5000`.

2. **Get national baseline** — Call `mcp__marketcheck__get_sold_summary` with the same `make`, `model`, same date range, but without `summary_by` to get the national average transaction price.

3. **Calculate geographic variance** — For each state:
   - **Price index** = state average_sale_price / national average_sale_price x 100 (100 = national average)
   - **Premium/discount** = state price - national price in dollars
   - Sort by price index descending to show where vehicles command the highest premiums

4. **Identify patterns** — Group states into:
   - **Premium markets** (index > 105): vehicles retain more value, typically lower supply or higher demand
   - **At-national-average** (index 95-105): mainstream pricing
   - **Discount markets** (index < 95): vehicles depreciate faster, often oversupplied or lower demand
   Note regional patterns (e.g., trucks command premiums in mountain/rural states, EVs hold better in CA/Northeast).

5. **Deliver the geographic map** — Present as a ranked table: State, Avg Transaction Price, National Avg, Price Index, Premium/Discount $, Sold Count. Highlight the top 5 and bottom 5 states for the specific vehicle.

## Workflow: MSRP Parity Tracker

Use this when a user asks "which new cars are selling over sticker" or "are markups coming down" or "incentive effectiveness."

1. **Get current MSRP parity data** — Call `mcp__marketcheck__get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=30`.

2. **Get prior period parity data** — Call `mcp__marketcheck__get_sold_summary` with the same parameters but dates shifted back 3 months. This shows the direction of parity movement.

3. **Get volume context** — Call `mcp__marketcheck__get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (current period), `date_to` (current period end), `top_n=30`.

4. **Classify parity status** — For each make/model:
   - **Above MSRP** (price_over_msrp_percentage > 0): dealer markups or strong demand
   - **At MSRP** (price_over_msrp_percentage between -1% and 0%): balanced market
   - **Below MSRP** (price_over_msrp_percentage < -1%): incentives/discounts active
   - **Trend direction**: compare current vs prior period to show if markups are growing or shrinking

5. **Present the parity report** — Show a table: Make/Model, Current % Over/Under MSRP, Prior Period %, Change Direction, Sold Volume. Highlight:
   - Models that flipped from above-MSRP to below (incentive programs taking effect)
   - Models still commanding premiums (constrained supply or high demand)
   - Models with deepening discounts (potential oversupply or model-year transition)

## KPIs & Business Impact

→ After assembling results, read `references/outcomes.md` to frame recommendations with quantified business impact, KPI benchmarks, and action-to-outcome guidance.

## Output Format

Always present results in this structure:

**Analysis Summary** — What was analyzed (make/model/segment), time period, geography, and inventory type.

**Depreciation Headline** — One sentence with the key finding (e.g., "The 2022 Toyota RAV4 has retained 87.3% of its original MSRP after 3 years, depreciating at 0.35% per month — outperforming the SUV segment average of 0.52% monthly").

**Depreciation Curve / Trend Table**

| Period | Avg Transaction Price | Retention % | Monthly Rate | Volume |
|--------|----------------------|-------------|--------------|--------|
| Current Month | $XX,XXX | XX.X% | X.XX% | X,XXX |
| 60 Days Ago | $XX,XXX | XX.X% | X.XX% | X,XXX |
| 90 Days Ago | $XX,XXX | XX.X% | X.XX% | X,XXX |
| 6 Months Ago | $XX,XXX | XX.X% | X.XX% | X,XXX |
| 1 Year Ago | $XX,XXX | XX.X% | X.XX% | X,XXX |

**Comparison Context** — How the subject compares to its segment, competing models, or prior periods. Always include at least one comparison dimension.

**Key Signals** — Bullet list of notable trends:
- Acceleration or deceleration in depreciation rate
- Volume trends that may predict future price movements
- Geographic or segment-specific anomalies
- MSRP parity shifts for new vehicles

**Recommendation** — One clear action tied to the user's segment (lender: adjust residual / advance rate; OEM: evaluate incentive / production; appraiser: apply trend adjustment to current valuation). Include the quantified business impact.

## Self-Check (before presenting to user)

- [ ] Depreciation rates are monthly (not annualized unless labeled)
- [ ] Retention % uses MSRP as denominator (not prior period price)
- [ ] Share changes in basis points (bps), not percentage points
- [ ] At least one comparison dimension included (segment, brand, or period)
- [ ] Data period and geography cited in output
- [ ] Recommendation tailored to user's role (lender/OEM/appraiser)
