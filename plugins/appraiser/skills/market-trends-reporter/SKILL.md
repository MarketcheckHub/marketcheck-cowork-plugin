---
name: market-trends-reporter
description: >
  This skill should be used when the user asks about "market trends", "best deals right now", "fastest depreciating cars", "slowest depreciating models", "EV vs gas prices", "EV vs ICE price parity", "price trends by region", "new car markups", "new car discounts", "market report", "depreciation rankings", "what's happening in the auto market", "which cars are losing value fastest", "price drops this month", "regional price differences", "cheapest state to buy", "MSRP vs sale price", or needs data-driven market trend insights relevant to vehicle valuations, appraisal adjustments, and comparable market intelligence.
version: 0.1.0
---

# Market Trends Reporter — Data-Driven Valuation Intelligence for Appraisers

Generate actionable market trend analyses, valuation adjustment insights, and data-backed comparable market intelligence using real sold transaction data and live inventory signals. Purpose-built for appraisers, insurance adjusters, fleet analysts, and valuation professionals who need timely, defensible market context to support their appraisals.

## Appraiser Profile (Load First — Optional Context)

Before running any workflow, check for a saved appraiser profile:

1. Read `~/.claude/marketcheck/appraiser-profile.json`
2. If the file **exists**, use as optional context:
   - `state` ← `location.state` — use as default geographic scope if user says "my market" or "my area"
   - `specialization` ← `appraiser.specialization` — frame insights for the appraiser's primary use case (trade-in trends, insurance benchmarks, fleet depreciation curves, estate fair market values)
   - `country` ← `location.country`
   - `min_comp_count` ← `appraiser.min_comp_count`
3. If the file **does not exist**, ask for all fields as before — this skill works fine without a profile. Suggest: "No appraiser profile found. Run `/onboarding` to set up your appraiser context once."
4. **Country note:** This skill requires `get_sold_summary` which is **US-only**. UK users cannot use market trends reporting. If `country == UK`, inform: "Market trends reporting requires US sold transaction data and is not available for the UK market."
5. If profile exists and relevant, confirm: "Using profile context: **[state]**, specialization: **[specialization]**"

## User Context

Before running any workflow, collect the following (auto-filled from appraiser profile where available):

- **Specialization context**: From profile `appraiser.specialization` — determines how to frame insights (trade-in trends for trade-in appraisers, total loss benchmarks for insurance adjusters, fleet depreciation curves for fleet analysts, fair market value context for estate appraisers)
- **Story angle or question**: What specific trend or question are they investigating?
- **Geographic scope**: From profile `location.state` if user says "my market", otherwise national (default), specific state(s), or regional
- **Time period**: Current month, trailing quarter, or year-over-year comparison
- **Vehicle focus** (optional): body_type, make, model, fuel_type_category, or inventory_type
- **Appraisal application**: How will this trend data adjust current valuations? (always tie insights back to appraisal impact)

If the user simply asks "what's happening in the market", run a combination of workflows and present a comprehensive briefing with appraisal-relevant takeaways.

## Workflow: Fastest and Slowest Depreciating Models

Identify which models are losing value fastest (or holding value best) by comparing average sale prices across periods. Appraisers use this to apply trend adjustments to book-value-based estimates.

1. Call `mcp__marketcheck__get_sold_summary` for the **current period**:
   - `date_from`: first of current month (e.g. `2026-01-01`)
   - `date_to`: last of current month (e.g. `2026-01-31`)
   - `inventory_type`: `Used`
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_sale_price`
   - `ranking_order`: `desc`
   - `top_n`: `50`
   - `state`: user's state filter (omit for national)

2. Call `mcp__marketcheck__get_sold_summary` for the **prior period** (same month one year ago, e.g. `2025-01-01` to `2025-01-31`) with identical filters.

3. For each make/model appearing in both periods, calculate:
   - **Price Change ($)** = Current Avg Price - Prior Avg Price
   - **Depreciation Rate (%)** = (Prior Avg Price - Current Avg Price) / Prior Avg Price x 100
   - Only include models with a minimum sold count threshold (e.g., 100+ units in both periods) for statistical reliability

4. Sort by depreciation rate descending. Present two tables:
   - **Fastest Depreciating Models (Top 15)**: Rank, Make, Model, Current Avg Price, Prior Avg Price, Price Drop ($), Depreciation Rate (%), Current Sold Count
   - **Best Value-Holding Models (Bottom 15 / lowest depreciation)**: Same columns, sorted by depreciation rate ascending

5. Add appraisal-relevant narrative: "The [Model A] lost X% of its value year-over-year, dropping from $Y to $Z on average. Appraisers valuing this model should apply a trend-down adjustment of approximately X% to book values. In contrast, [Model B] held within X% of its prior-year price — book values remain reliable for this model without trend adjustment."

6. For the top 3 fastest depreciating models, call `mcp__marketcheck__search_active_cars` with:
   - `make` and `model` for each
   - `car_type`: `used`
   - `sort_by`: `price`
   - `sort_order`: `asc`
   - `rows`: `5`
   - `seller_type`: `dealer`
   - This surfaces specific current listings as comparable evidence to support trend-adjusted valuations.

## Workflow: Best Deals Right Now

Find vehicles currently listed with significant price reductions that have been sitting on lots — useful for appraisers who need to identify below-market comparables and understand seller motivation in the current market.

1. Call `mcp__marketcheck__search_active_cars` with:
   - `car_type`: `used` (or user's preference)
   - `body_type`: user's target segment (e.g. `SUV`, `Sedan`) or omit for all
   - `price_change`: `negative` (only vehicles with price reductions)
   - `sort_by`: `dom`
   - `sort_order`: `desc`
   - `rows`: `20`
   - `seller_type`: `dealer`
   - `zip`: user's zip code (if provided)
   - `radius`: `100` (if zip provided)
   - `state`: user's state (if no zip provided)

2. For each result, calculate a **Deal Score**:
   - Deal Score = (Price Drop % from original list price) x (DOM / 30)
   - Higher score = bigger discount on a unit that has been sitting longer (more motivated seller)

3. For the top 5 deals by Deal Score, call `mcp__marketcheck__predict_price_with_comparables` with:
   - `vin`: the vehicle's VIN
   - `miles`: the vehicle's mileage
   - `zip`: the vehicle's zip or user's zip
   - `dealer_type`: based on listing dealer type
   - This validates whether the "deal" is actually below market value or just a price cut to market

4. Present a **Below-Market Comparables** table:
   - Columns: Rank, Year, Make, Model, Trim, Listed Price, Original Price, Price Drop ($), Price Drop (%), DOM (days), Deal Score, Predicted Market Price, Below/Above Market ($), Dealer, Location
   - Only rank vehicles where Listed Price < Predicted Market Price as "true below-market units"

5. Appraisal narrative: "The most significant below-market listing is a [Year Make Model] at [Dealer] in [City, State], listed at $X after a $Y price reduction. It has been on the lot for Z days and is priced $W below comparable market value. Appraisers should note: vehicles with high DOM and multiple price reductions may indicate condition issues not reflected in listing data — use as lower-bound comparables with caution."

6. For appraisers specifically, add: "These below-market listings serve as lower-bound anchors for comparable analysis. When building a valuation range, distressed-price comparables should be weighted less heavily unless the subject vehicle has similar condition concerns. These price reductions also indicate downward pricing pressure in this segment — factor current market conditions when setting valuations."

## Workflow: EV vs ICE Price Parity Tracker

Track the price gap between electric and internal combustion vehicles within the same segments — critical for appraisers handling mixed-powertrain fleets or insurance claims on EVs.

1. Call `mcp__marketcheck__get_sold_summary` for **EV** sales:
   - `date_from` / `date_to`: target period
   - `fuel_type_category`: `EV`
   - `body_type`: `SUV` (start with the largest segment)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_sale_price`
   - `ranking_order`: `desc`
   - `top_n`: `10`
   - `state`: user's state filter (omit for national)

2. Call `mcp__marketcheck__get_sold_summary` for **ICE** sales with same filters but:
   - `fuel_type_category`: `ICE`

3. Repeat steps 1-2 for additional body types: `Sedan`, `Pickup`, `Hatchback`.

4. Also repeat steps 1-2 for **Hybrid** to show the middle ground.

5. For the prior-year same period, repeat all calls to calculate the trend.

6. Calculate per body type:
   - **EV Average Sale Price** (segment-wide, not per model)
   - **ICE Average Sale Price** (segment-wide)
   - **Hybrid Average Sale Price** (segment-wide)
   - **EV-to-ICE Price Gap ($)** = EV Avg - ICE Avg
   - **EV-to-ICE Price Gap (%)** = (EV Avg - ICE Avg) / ICE Avg x 100
   - **Year-over-Year Gap Change** = Current Gap % - Prior Year Gap %

7. Present:
   - **Price Parity Tracker** table: Body Type, EV Avg Price, ICE Avg Price, Hybrid Avg Price, EV-ICE Gap ($), EV-ICE Gap (%), YoY Gap Change, Parity Trend (Narrowing/Widening/Stable)
   - **Top EV Models by Segment** table: Body Type, Make, Model, Avg Sale Price, Sold Count — to show which EVs are driving the averages
   - **Appraisal impact narrative**: "In the SUV segment, the EV-to-ICE price gap is $X,XXX (Y%), [down/up] from $A,AAA (B%) a year ago. Appraisers should note: EV depreciation curves differ significantly from ICE equivalents. Do not apply ICE depreciation rates to EV appraisals — use EV-specific comparables and the current gap data to set appropriate value ranges. For insurance replacement claims on EVs, the replacement cost must reflect the EV market, not the ICE equivalent."

## Workflow: Regional Price Variance Story

Reveal where in the US a specific vehicle is cheapest and most expensive — essential for multi-state fleet appraisals, insurance replacement value disputes, and geographic adjustment factors.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `make`: user's target make (required)
   - `model`: user's target model (required for model-level; omit for brand-level)
   - `inventory_type`: `Used` (or `New` based on user intent)
   - `summary_by`: `state`
   - `limit`: `51`

2. From the results, calculate:
   - **National average sale price** (weighted by volume)
   - **Cheapest 5 states** by average sale price
   - **Most expensive 5 states** by average sale price
   - **Price spread** = Most Expensive State Avg - Cheapest State Avg
   - **Price spread %** = Spread / National Avg x 100

3. For context, call `mcp__marketcheck__get_sold_summary` for the same make/model in the cheapest state with:
   - `state`: cheapest state code
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `top_n`: `1`
   - This confirms volume is sufficient for the price to be meaningful.

4. Present:
   - **Regional Price Map** table: State, Avg Sale Price, vs National Avg ($), vs National Avg (%), Sold Count, Avg DOM
   - Sort by Avg Sale Price ascending (cheapest first)
   - **Summary box**: "A used [Year Range] [Make Model] averages $X nationally. The cheapest market is [State] at $Y (-Z% below national avg). The most expensive is [State] at $A (+B%). The coast-to-coast price spread is $C."

5. For appraisers specifically, add actionable guidance: "When appraising this vehicle in [expensive state], the geographic adjustment factor is +B% above national average. For insurance replacement value claims, cite the local market average of $A rather than the national average. For multi-state fleet revaluations, apply state-level adjustments to each unit's location rather than using a single national figure."

6. If year-over-year comparison was requested, repeat step 1 for the prior year and show which states saw the largest price increases or decreases.

## Workflow: New Car Markup and Discount Tracker

Identify which new car models are selling above MSRP (markup) and which require discounts — provides context for appraisers setting residual values and understanding supply-demand dynamics that affect used vehicle values.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `inventory_type`: `New`
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `price_over_msrp_percentage`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   - `state`: user's state filter (omit for national)

2. Call `mcp__marketcheck__get_sold_summary` with same filters but:
   - `ranking_order`: `asc`
   - `top_n`: `20`
   - This gets the models with the deepest discounts off MSRP.

3. For broader context, also call with:
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `price_over_msrp_percentage`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   - This shows brand-level pricing power.

4. Present three sections:
   - **Models Commanding Premiums (Above MSRP)** table: Rank, Make, Model, Avg Price Over MSRP (%), Avg Markup ($), Sold Count, Avg DOM
     - These are supply-constrained vehicles where demand exceeds availability
   - **Models Requiring Discounts (Below MSRP)** table: Rank, Make, Model, Avg Discount Off MSRP (%), Avg Discount ($), Sold Count, Avg DOM
     - These are over-supplied or slow-demand vehicles needing incentives
   - **Brand-Level MSRP Positioning** table: Make, Avg Price vs MSRP (%), Direction (Premium/Discount), Interpretation

5. Narrative: "[Model A] commands the highest premium in the new car market at +X% over MSRP, translating to an average $Y markup. Conversely, [Model B] requires the deepest discount at -Z% off MSRP ($W off). At the brand level, [Make C] is the only mainstream brand still commanding premiums across its lineup."

6. For appraisers, add valuation context: "Models transitioning from above-MSRP to discount territory signal weakening demand — appraisers should lower residual estimates for recently purchased units of these models. Models still commanding premiums will retain value better on the secondary market. New models selling below MSRP accelerate used vehicle depreciation for the same nameplate — apply an additional trend-down adjustment to 1-3 year old used units of discounted models."

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Appraisal Impact |
|-----|-------------|------------------|
| Depreciation Rate by Model (%) | YoY average sale price change for used vehicles | Apply as trend adjustment to book values; models depreciating >20%/year require aggressive downward adjustment from published guides |
| Deal Score | (Price Drop % x DOM/30) for active listings | Identifies distressed-price comparables; scores above 5.0 indicate potential lower-bound anchors for valuation ranges |
| EV-to-ICE Price Gap ($, %) | Difference in avg sale price within same body type | Use separate depreciation curves for EVs; do not blend EV and ICE comparables in the same valuation |
| Regional Price Spread ($, %) | Difference between cheapest and most expensive state | Apply geographic adjustment factors to appraisals; spreads exceeding 15% require state-level rather than national comparables |
| Price-to-MSRP Ratio (%) | Sale price relative to sticker on new vehicles | Above 100% = strong residual retention forecast; below 95% = weaker residuals, apply higher depreciation to recent purchases |
| MSRP Parity Trend | Month-over-month movement toward or away from MSRP | Models crossing from above-MSRP to below signal accelerated depreciation on 1-2 year old used units |
| Volume-Weighted Avg Sale Price | National or state-level transaction price by model | More accurate than book values for current market appraisals; cite as primary evidence in defensible valuations |

## Action-to-Outcome Funnel

1. **Scenario: Appraiser asks "What are the fastest depreciating cars right now?"**
   Run *Fastest/Slowest Depreciating Models*. Present top 15 depreciators with year-over-year price drops. For the top 3, pull current listings as comparable evidence. Appraisal guidance: "Apply a trend-down adjustment of X% to book values for these models. Current transaction data shows values are declining faster than published guides reflect."

2. **Scenario: Insurance adjuster asks "Where can I find comparable evidence for a RAV4 total loss claim?"**
   Run *Best Deals Right Now* filtered by make=Toyota, model=RAV4. Cross-reference with *Regional Price Variance* to show local market pricing vs national average. Guidance: "For the replacement value claim, cite local market comps at $X (state average). The national average of $Y is not appropriate — the claimant's market commands a [premium/discount] of Z%."

3. **Scenario: Fleet analyst asks "Is EV price parity getting closer?"**
   Run *EV vs ICE Price Parity Tracker* across SUV, Sedan, and Pickup segments. Show current gap and YoY trend. Guidance: "For fleet revaluation, apply separate depreciation curves to EV and ICE units. The EV-ICE gap in the sedan segment has narrowed to $X,XXX — EVs purchased in the last 12 months have depreciated Y% faster than ICE equivalents."

4. **Scenario: Appraiser needs a monthly market context update**
   Run all workflows as a comprehensive briefing. Structure as: Executive Summary (3 bullet points), Depreciation Watch, Below-Market Comparable Scan, EV Transition Update, Regional Pricing Adjustments, New Car MSRP Signal. Frame every section with explicit appraisal adjustments and confidence scores.

5. **Scenario: Appraiser asks "Are markups on new trucks still happening?"**
   Run *New Car Markup/Discount Tracker* filtered by body_type=Pickup. Show each model's MSRP positioning and trend over the last 3 months. Guidance: "New truck premiums have [increased/decreased] from +X% to +Y% — this [supports/undermines] strong residual values on 1-3 year old used trucks. Adjust appraisal ranges accordingly."

## Output Format

- **Lead with the appraisal impact, not the methodology.** Example: "Appraisers should apply a -18.3% trend adjustment to 2023 Tesla Model Y book values — this model has the steepest depreciation of any SUV." Not: "We queried sold data and calculated depreciation rates."
- **Always cite sample size.** Include sold count alongside any price metric. "Average price of $34,200 (based on 12,847 transactions)" is credible. A price based on 15 transactions is not — flag low-volume models with a caveat and note they fall below the min_comp_count threshold.
- **Frame numbers for appraisal use.** Provide both dollar amounts and percentages. Appraisers need percentages for trend adjustments and dollar amounts for valuation reports. Always include a confidence assessment.
- **Include comparison anchors.** Every number needs context: vs prior period, vs segment average, vs national average, vs MSRP. A standalone number is not defensible in an appraisal report.
- **For "Below-Market" content, always validate against predicted market price.** A price cut from an inflated original list is not a below-market comparable. Only highlight vehicles priced below `predict_price_with_comparables` output as genuine below-market evidence.
- **Structure multi-workflow reports with clear section headers** and an executive summary at the top. Keep each section self-contained so the appraiser can cite specific sections in their valuation reports.
- **Cite the data source and period** at the bottom of every output: "Source: MarketCheck transaction data, [Month Year], [Geography]. Analysis includes [dealer type] transactions only. Minimum volume threshold: [N] units per model."
