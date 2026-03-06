---
name: depreciation-tracker
description: >
  This skill should be used when the user asks about "depreciation rate",
  "value retention", "residual value", "how fast is it losing value",
  "which cars hold value", "brand value retention", "EV depreciation",
  "price trend over time", "brand residual ranking", "depreciation curve",
  "MSRP parity", "price over sticker", "incentive effectiveness",
  "geographic value variance", "regional pricing strategy",
  or needs help with brand value retention analysis, model depreciation tracking,
  segment value comparisons, brand retention rankings, or MSRP-to-transaction
  price tracking for OEM strategy and competitive benchmarking.
version: 0.1.0
---

# Depreciation Tracker — Brand Value Retention Intelligence for OEMs

Frame all analysis as BRAND VALUE RETENTION — how well does your brand hold value vs competitors? Which of your models are depreciating fastest? Where should you focus residual support or pricing strategy?

## Manufacturer Profile (Load First)

Load `~/.claude/marketcheck/manufacturer-profile.json` if exists. Extract: `brands`, `states`, `competitor_brands`, `country`. If missing, ask brand and competitors. US-only (requires `get_sold_summary` and `search_active_cars`); if UK, inform not available. Confirm profile.

## User Context

User is an OEM product planner, brand strategist, or regional manager tracking brand value retention vs competitors for residual support, CPO strategy, and pricing decisions.

| Required | Field | Source |
|----------|-------|--------|
| Yes | Make/Model/segment | Profile or ask |
| Recommended | Model year(s) | Ask |
| Auto/Ask | State | Profile `manufacturer.states` or ask |
| Optional | Inventory type | `New` or `Used` (default: `Used`) |
| Optional | Comparison | `EV vs ICE`, `SUV vs Sedan`, `Brand vs Competitor` |
| Optional | Time horizon | `30d`, `90d`, `6mo`, `1yr` |

Clarify: used vehicle depreciation (secondary market) vs new vehicle MSRP parity (transaction vs sticker). Different workflows.

## Workflow: Make/Model Depreciation Curve

Use this when a user asks "how fast is our RAV4 losing value" or "depreciation curve for our models."

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

6. **Compare to competitor model** — If competitor brands are in the profile, run the same analysis for the equivalent competitor model and show side-by-side retention curves.

## Workflow: Brand Residual Ranking — Brand Value Retention

Use this when a user asks "which brands hold value best" or "how does our brand compare on residual value."

1. **Get current period brand prices** — Call `get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (end of prior month), `inventory_type=Used`, `top_n=25`.
   → **Extract only**: per make — average_sale_price. Discard full response.

2. **Get prior period brand prices** — Same call with dates shifted back 6 months.
   → **Extract only**: per make — average_sale_price. Discard full response.

3. **Get volume context** — Call `get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, current period dates, `inventory_type=Used`, `top_n=25`.
   → **Extract only**: per make — sold_count. Discard full response.

4. **Calculate brand retention scores** — For each make:
   - **Retention %** = current average_sale_price / prior average_sale_price x 100
   - **Volume trend** = current sold_count vs prior sold_count
   - Rank brands by retention % descending
   - Separate into tiers: Tier 1 (>98% retention), Tier 2 (95-98%), Tier 3 (90-95%), Tier 4 (<90%)

5. **Present the brand ranking** with competitive framing:
   - Show ranked table: Rank, Make, Current Avg Price, Prior Avg Price, Retention %, Volume, Tier
   - **Highlight your brands with ★** and show their tier
   - **Highlight competitor brands** and their tier
   - Note: "Your brand [Brand] is in Tier [X] at [Y]% retention. [Competitor A] is in Tier [Z] at [W]% retention."
   - Flag if your brand dropped or improved tiers since last period

## Workflow: Segment Value Trends

Use this when a user asks "are our SUVs holding value better than sedans" or "how is EV depreciation for our brand."

1. **Get current period segment data** — Call `get_sold_summary` with `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `date_from` (first of prior month), `date_to` (end of prior month), `inventory_type=Used`, `top_n=10`.
   → **Extract only**: per body_type — average_sale_price, sold_count. Discard full response.

2. **Get prior period segment data** — Same call with dates shifted back 3 months (or user's chosen comparison window).
   → **Extract only**: per body_type — average_sale_price, sold_count. Discard full response.

3. **Get fuel type comparison** — Call `get_sold_summary` with `fuel_type_category=EV`, current period dates, `inventory_type=Used`. Repeat with `fuel_type_category=ICE`. Repeat both for prior period.
   → **Extract only**: average_sale_price, sold_count per fuel_type per period. Discard full response.

4. **Calculate segment trends** — For each body type and fuel type:
   - Period-over-period price change %
   - Volume change %
   - Flag segments where price declined more than 3% as "accelerating depreciation"
   - Flag segments where your brand outperforms or underperforms the segment average

5. **Deliver with brand context** — "Your brand's SUVs retained X% of value vs the segment average of Y%. Your sedans are underperforming at Z% retention. EV depreciation across the market runs at [rate] — your EV models are [above/below] this average."

## Workflow: Geographic Value Variance — Regional Pricing Strategy

Use this when a user asks "where do our models hold value best" or "regional pricing strategy."

1. **Get state-level transaction data** — Call `get_sold_summary` with `make`, `model`, `summary_by=state`, `date_from` (first of prior month), `date_to` (end of prior month), `inventory_type=Used`, `limit=5000`.
   → **Extract only**: per state — average_sale_price, sold_count. Discard full response.

2. **Get national baseline** — Same call without `summary_by` for national average.
   → **Extract only**: average_sale_price, sold_count. Discard full response.

3. **Calculate geographic variance** — For each state:
   - **Price index** = state average_sale_price / national average_sale_price x 100
   - **Premium/discount** = state price - national price in dollars

4. **Identify patterns and strategic implications** — Group states into:
   - **Premium markets** (index > 105): your brand commands higher value here — protect these markets
   - **At-national-average** (index 95-105): mainstream pricing
   - **Discount markets** (index < 95): your brand depreciates faster here — investigate causes (oversupply? competition?)

5. **Regional pricing strategy** — Present as a ranked table: State, Avg Transaction Price, National Avg, Price Index, Premium/Discount $, Sold Count.
   - For your responsible states (from profile), provide specific strategic recommendations
   - "In [State], your [Model] trades at a $X premium to national average — this market supports premium positioning. In [State], the $Y discount suggests oversupply or competitive pressure from [Competitor]."

## Workflow: MSRP Parity Tracker — Incentive Effectiveness

Use this when a user asks "are our new models still commanding premiums" or "how effective are our incentives."

1. **Get current MSRP parity data** — Call `get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (end of prior month), `top_n=30`.
   → **Extract only**: per make/model — price_over_msrp_percentage. Discard full response.

2. **Get prior period parity data** — Same call with dates shifted back 3 months.
   → **Extract only**: per make/model — price_over_msrp_percentage. Discard full response.

3. **Get volume context** — Call `get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, current period dates, `top_n=30`.
   → **Extract only**: per make/model — sold_count. Discard full response.

4. **Classify parity status for your models** — For each make/model:
   - **Above MSRP** (>0%): strong demand, no incentives needed
   - **At MSRP** (-1% to 0%): balanced market
   - **Below MSRP** (<-1%): incentives/discounts active — evaluate effectiveness

5. **Present with incentive strategy framing**:
   - Table: Make/Model, Current % Over/Under MSRP, Prior Period %, Change Direction, Sold Volume
   - **Highlight your models** with ★
   - **Compare to competitor equivalent models**
   - Flag your models that flipped from above-MSRP to below (incentive programs taking effect or demand softening?)
   - Flag competitor models still commanding premiums (what are they doing differently?)
   - "Your [Model A] premium eroded from +5.2% to +1.1% over 3 months. At current trajectory, it will cross into discount territory by [month]. Consider adjusting production or targeting incentive spend to specific states."

## Output

Present: brand value retention headline with tier positioning, depreciation/retention data table(s) with competitive comparison, key signals (acceleration/deceleration, geographic anomalies, MSRP shifts), and actionable recommendation (residual support, CPO, allocation, incentive calibration).
