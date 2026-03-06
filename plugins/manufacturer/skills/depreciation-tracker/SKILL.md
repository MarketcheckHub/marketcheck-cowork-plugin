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

Before running any workflow, check for a saved manufacturer profile:

1. Read `~/.claude/marketcheck/manufacturer-profile.json`
2. If the file **exists**, extract and use silently:
   - `brands` ← `manufacturer.brands` — your own brands to monitor
   - `states` ← `manufacturer.states` — geographic scope
   - `competitor_brands` ← `manufacturer.competitor_brands` — benchmark against
   - `country` ← `location.country`
3. If the file **does not exist**: Ask: "Which brand(s) do you represent?" and "Which competitors to benchmark against?" This skill works without a profile.
4. **Country note:** This skill requires `get_sold_summary` and `search_active_cars` which are **US-only**. If `country == UK`, inform: "Depreciation tracking requires US sold transaction data and is not available for the UK market."
5. If profile exists, confirm: "Using profile: **[user_name]** — Tracking value retention for **[brands]** vs **[competitor_brands]**"

## User Context

The primary user is an **OEM product planner, brand strategist, or regional manager** who needs to understand how well their brand retains value compared to competitors. This informs residual value support programs, CPO strategy, pricing decisions, and competitive positioning.

The following fields may be auto-filled from the manufacturer profile:

| Required | Field | Source |
|----------|-------|--------|
| Yes | Make and/or Model (or segment) | Profile brands or ask |
| Recommended | Model year(s) of interest | Always ask |
| Auto/Ask | Geography (state) | Profile `manufacturer.states` or ask |
| Optional | Inventory type | `New` or `Used` (default: `Used`) |
| Optional | Comparison dimension | `EV vs ICE`, `SUV vs Sedan`, `Your Brand vs Competitor` |
| Optional | Time horizon | `30 days`, `90 days`, `6 months`, `1 year` |

Always clarify whether the user wants depreciation of **used vehicles** (price decline over time on the secondary market) or **new vehicle transaction-to-MSRP parity** (how much above or below sticker new cars are actually selling). These are different workflows.

## Workflow: Make/Model Depreciation Curve

Use this when a user asks "how fast is our RAV4 losing value" or "depreciation curve for our models."

1. **Get current period sold data** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `date_from` set to the first of the current month minus 30 days, `date_to` set to the last day of that month. If states specified, include `state`. Record the `average_sale_price` and `sold_count`.

2. **Get historical sold data at multiple intervals** — Make separate calls for each lookback period:
   - **60 days ago**
   - **90 days ago**
   - **6 months ago**
   - **1 year ago**
   Record `average_sale_price` at each point. Adjust the actual dates based on today's date.

3. **Get current active market asking price** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `car_type=used`, `stats=price`, `rows=0`. This gives forward-looking pricing.

4. **Get original MSRP baseline** — Call `mcp__marketcheck__search_active_cars` with the same `year`, `make`, `model`, `rows=1`, `sort_by=price`, `sort_order=desc` to find a representative listing. Then call `mcp__marketcheck__decode_vin_neovin` with that listing's VIN to extract the original MSRP. If MSRP is not available, use the highest transaction price from the 1-year-ago sold data as a proxy.

5. **Build the depreciation curve** — Calculate at each time interval:
   - **Retention %** = (average_sale_price at interval / original MSRP) x 100
   - **Monthly depreciation rate** = (price change between consecutive intervals) / (months between intervals)
   - **Annualized depreciation rate** = monthly rate x 12
   Present as a table and describe the curve shape (linear, accelerating, stabilizing).

6. **Compare to competitor model** — If competitor brands are in the profile, run the same analysis for the equivalent competitor model and show side-by-side retention curves.

## Workflow: Brand Residual Ranking — Brand Value Retention

Use this when a user asks "which brands hold value best" or "how does our brand compare on residual value."

1. **Get current period brand prices** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `inventory_type=Used`, `top_n=25`.

2. **Get prior period brand prices** — Same parameters but dates shifted back 6 months.

3. **Get volume context** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (current period), `date_to` (current period end), `inventory_type=Used`, `top_n=25`.

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

1. **Get current period segment data** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `date_from`, `date_to`, `inventory_type=Used`, `top_n=10`.

2. **Get prior period segment data** — Same but shifted back 3 months.

3. **Get fuel type comparison** — Call for `fuel_type_category=EV` and without filter (ICE), both current and prior.

4. **Calculate segment trends** — For each body type and fuel type:
   - Period-over-period price change %
   - Volume change %
   - Flag segments where price declined more than 3% as "accelerating depreciation"
   - Flag segments where your brand outperforms or underperforms the segment average

5. **Deliver with brand context** — "Your brand's SUVs retained X% of value vs the segment average of Y%. Your sedans are underperforming at Z% retention. EV depreciation across the market runs at [rate] — your EV models are [above/below] this average."

## Workflow: Geographic Value Variance — Regional Pricing Strategy

Use this when a user asks "where do our models hold value best" or "regional pricing strategy."

1. **Get state-level transaction data** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model` (from user/profile), `summary_by=state`, `date_from`, `date_to`, `inventory_type=Used`, `limit=5000`.

2. **Get national baseline** — Same but without `summary_by` for the national average.

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

1. **Get current MSRP parity data** — Call `mcp__marketcheck__get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `date_from`, `date_to`, `top_n=30`.

2. **Get prior period parity data** — Same but dates shifted back 3 months.

3. **Get volume context** — Same but `ranking_measure=sold_count`.

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

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Monthly Depreciation Rate % | Price decline rate for your models vs competitors | Drives residual value support decisions; 1% faster depreciation on 50K units = $150M in brand value erosion annually |
| Residual Retention % | Current price / Original MSRP x 100 | Core brand value metric; every 1% improvement in retention strengthens brand perception and resale value |
| Brand Residual Tier | Your brand's tier vs competitor tiers | Strategic positioning; moving from Tier 2 to Tier 1 supports premium pricing strategy |
| Segment Depreciation Comparison | Your brand's retention by segment vs market | Identifies which vehicle lines are helping or hurting brand value |
| Price-Over-MSRP % | Transaction price / MSRP - 1 | Positive = demand exceeds supply; negative = incentive dependency; tracks incentive effectiveness |
| Geographic Value Variance | State price index for your models | Informs regional pricing strategy; premium markets should be protected, discount markets investigated |

## Action-to-Outcome Funnel

1. **Scenario: Brand strategist asks "How does our value retention compare to Honda?"**
   Run *Brand Residual Ranking*. Compare your tier to Honda's. Drill into *Make/Model Depreciation Curve* for the models where the gap is largest. Recommend: "Your brand is Tier 2 at 96.2% retention. Honda is Tier 1 at 98.5%. The gap is driven by [Model] which depreciates X% faster than the Civic. Consider CPO program enhancements or residual value support."

2. **Scenario: Regional manager asks "Where do our trucks hold value best?"**
   Run *Geographic Value Variance* for the pickup model. Show premium and discount markets. Recommend: "Your pickup commands a $2,400 premium in Texas but trades $1,800 below national in Florida. Florida appears oversupplied — consider reducing allocation by N units/month."

3. **Scenario: Product planner asks "Are our new models commanding premiums?"**
   Run *MSRP Parity Tracker* for your brand. Show model-by-model MSRP position and trend. Flag erosion. Recommend: "Your [Model] premium dropped from +5.2% to +1.1% — at this rate it crosses into discount territory by June. Competitor [Model] still holds +3.8%. Evaluate production levels or targeted incentives."

4. **Scenario: EV strategy lead asks "How fast are our EVs depreciating vs ICE?"**
   Run *Segment Value Trends* with EV vs ICE breakdown, filtered to your brand. Compare against competitor EV depreciation. Recommend: "Your EV models depreciate at X.X%/month vs X.X% for your ICE models. Competitor EVs depreciate at Y.Y%. Consider battery warranty extensions or certified pre-owned EV programs to slow depreciation."

## Output Format

**Analysis Summary** — What was analyzed, time period, geography, and your brand context.

**Brand Value Headline** — One sentence: "Your brand retained X% of value over [period], ranking [tier] among [N] brands — [ahead/behind] competitor [Brand] at Y%."

**Value Retention Table / Depreciation Curve**

| Period | Avg Transaction Price | Retention % | Monthly Rate | Volume |
|--------|----------------------|-------------|--------------|--------|
| Current Month | $XX,XXX | XX.X% | X.XX% | X,XXX |
| 60 Days Ago | $XX,XXX | XX.X% | X.XX% | X,XXX |
| 90 Days Ago | $XX,XXX | XX.X% | X.XX% | X,XXX |
| 6 Months Ago | $XX,XXX | XX.X% | X.XX% | X,XXX |
| 1 Year Ago | $XX,XXX | XX.X% | X.XX% | X,XXX |

**Competitive Context** — How your brand compares to competitors. Always include at least one direct comparison.

**Key Signals**:
- Acceleration or deceleration in depreciation rate for your models
- Models where competitors are holding value better (and why)
- Geographic anomalies that inform regional strategy
- MSRP parity shifts that indicate incentive effectiveness

**Strategic Recommendation** — Specific actions: adjust residual support, modify CPO programs, reallocate inventory to premium markets, calibrate incentive spend. Include quantified impact.
