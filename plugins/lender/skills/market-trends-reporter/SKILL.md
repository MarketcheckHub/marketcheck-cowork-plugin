---
name: market-trends-reporter
description: >
  This skill should be used when the user asks about "market trends",
  "fastest depreciating cars", "slowest depreciating models", "highest residual risk",
  "EV vs gas prices", "EV vs ICE price parity", "price trends by region",
  "new car markups", "new car discounts", "market report", "depreciation rankings",
  "what's happening in the auto market", "which cars are losing value fastest",
  "price drops this month", "regional price differences", "cheapest state to buy",
  "MSRP vs sale price", "lending risk assessment", "portfolio risk signals",
  or needs help creating data-driven automotive market analysis for lending
  risk assessment and residual value intelligence.
version: 0.1.0
---

# Market Trends Reporter — Lending Risk Assessment & Residual Value Intelligence

Generate lending-focused market trend analyses, residual risk assessments, and data-backed portfolio intelligence using real sold transaction data and live inventory signals. Purpose-built for auto lenders, residual value analysts, portfolio risk managers, and auto finance directors who need timely, defensible data for residual setting, advance rate decisions, and portfolio risk management.

## Lender Profile (Load First — Optional Context)

Before running any workflow, check for a saved lender profile:

1. Read `~/.claude/marketcheck/lender-profile.json`
2. If the file **exists**, use as optional context:
   - `state` ← `location.state` — use as default geographic scope if user says "my market" or "my area"
   - `tracked_segments` ← `lender.tracked_segments` — use as default vehicle focus if user asks about "my segments"
   - `risk_ltv_threshold` ← `lender.risk_ltv_threshold`
   - `high_risk_ltv_threshold` ← `lender.high_risk_ltv_threshold`
   - `country` ← `location.country`
3. If the file **does not exist**, ask for all fields as before — this skill works fine without a profile.
4. **Country note:** This skill requires `get_sold_summary` which is **US-only**. UK users cannot use market trends reporting. If `country == UK`, inform: "Market trends reporting requires US sold transaction data and is not available for the UK market."
5. If profile exists and relevant, confirm: "Using profile context: **[state]**, tracked segments: **[tracked_segments]**"

## User Context

Before running any workflow, collect the following (auto-filled from lender profile where available):

- **Story angle or question**: What specific trend or risk signal are they investigating?
- **Geographic scope**: From profile `location.state` if user says "my market", otherwise national (default), specific state(s), or regional
- **Time period**: Current month, trailing quarter, or year-over-year comparison
- **Vehicle focus** (optional): From profile `lender.tracked_segments` if user says "my segments", otherwise ask for body_type, make, model, fuel_type_category, or inventory_type
- **Portfolio context**: Are they looking at this for new origination decisions, existing portfolio monitoring, or residual setting?

If the user simply asks "what's happening in the market", run a combination of workflows and present a comprehensive lending risk briefing.

## Workflow: Highest Residual Risk Models (Fastest Depreciating)

Identify which models are losing value fastest (highest residual risk) and which hold value best (lowest residual risk) by comparing average sale prices across periods.

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
   - **Highest Residual Risk Models (Top 15)**: Rank, Make, Model, Current Avg Price, Prior Avg Price, Price Drop ($), Depreciation Rate (%), Current Sold Count, Risk Signal
   - **Lowest Residual Risk Models (Bottom 15 / strongest retention)**: Same columns, sorted by depreciation rate ascending

5. Add lending context: "The [Model A] lost X% of its value year-over-year, dropping from $Y to $Z on average. This represents the highest residual risk among mainstream models — lenders should tighten advance rates or require higher down payments on new originations. In contrast, [Model B] held within X% of its prior-year price, making it the lowest residual risk in the [segment] category — standard advance rates are appropriate."

6. For the top 3 highest residual risk models, call `mcp__marketcheck__search_active_cars` with:
   - `make` and `model` for each
   - `car_type`: `used`
   - `sort_by`: `price`
   - `sort_order`: `asc`
   - `rows`: `5`
   - `seller_type`: `dealer`
   - This surfaces current market pricing to validate the depreciation signal.

## Workflow: EV vs ICE Price Parity Tracker

Track the price gap between electric and internal combustion vehicles within the same segments to measure residual risk differentials and lending opportunity.

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

7. Present with lending implications:
   - **Price Parity Tracker** table: Body Type, EV Avg Price, ICE Avg Price, Hybrid Avg Price, EV-ICE Gap ($), EV-ICE Gap (%), YoY Gap Change, Parity Trend (Narrowing/Widening/Stable)
   - **Top EV Models by Segment** table: Body Type, Make, Model, Avg Sale Price, Sold Count — to show which EVs are driving the averages
   - **Lending implications**: "In the SUV segment, the EV-to-ICE price gap is $X,XXX (Y%), [down/up] from $A,AAA (B%) a year ago. The gap is narrowing fastest in [segment], driven primarily by price reductions on [Model]. For lenders: narrowing gap = lending opportunity (EV origination volume will increase); widening gap in used market = higher residual risk on existing EV portfolio."

## Workflow: Regional Price Variance for Collateral

Reveal where in the US a specific vehicle is cheapest and most expensive, helping lenders apply accurate regional collateral value adjustments.

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

4. Present with lending implications:
   - **Regional Collateral Value Map** table: State, Avg Sale Price, vs National Avg ($), vs National Avg (%), Sold Count, Avg DOM
   - Sort by Avg Sale Price ascending (cheapest first)
   - **Summary**: "A used [Year Range] [Make Model] averages $X nationally. The lowest collateral values are in [State] at $Y (-Z% below national avg). The strongest collateral values are in [State] at $A (+B%). The state-to-state collateral spread is $C."

5. Add lending guidance: "Lenders using national averages for collateral valuation are overstating coverage in [cheap states] and understating it in [expensive states]. For portfolios concentrated in [cheap state], apply a -Z% regional adjustment to collateral values. This affects approximately X% of a typical national portfolio."

6. If year-over-year comparison was requested, repeat step 1 for the prior year and show which states saw the largest collateral value increases or decreases.

## Workflow: New Car Markup and Discount Tracker

Identify which new car models are selling above MSRP (markup) and which require discounts — signals for residual value forecasting on new originations.

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

4. Present with residual forecasting implications:
   - **Models Commanding Premiums (Above MSRP)** table: Rank, Make, Model, Avg Price Over MSRP (%), Avg Markup ($), Sold Count, Avg DOM
     - These vehicles have lower near-term residual risk — demand exceeds supply
   - **Models Requiring Discounts (Below MSRP)** table: Rank, Make, Model, Avg Discount Off MSRP (%), Avg Discount ($), Sold Count, Avg DOM
     - These vehicles signal residual pressure — discount at origination compresses future residual value
   - **Brand-Level MSRP Positioning** table: Make, Avg Price vs MSRP (%), Direction (Premium/Discount), Residual Implication

5. Narrative with lending guidance: "[Model A] commands the highest premium in the new car market at +X% over MSRP, translating to an average $Y markup — residual risk LOW for new originations. Conversely, [Model B] requires the deepest discount at -Z% off MSRP ($W off) — residual risk ELEVATED as the discounted origination price compresses the residual floor."

6. For prior-period comparison, repeat calls and show trend: "Markups on [Model] have decreased from +X% to +Y% over the past quarter, signaling supply is catching up to demand — reduce residual forecasts for this model on new lease originations." Also add: "Models transitioning from premium to discount territory this month: [list] — downgrade residual assumptions immediately."

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Depreciation Rate by Model (%) | YoY average sale price change for used vehicles | Highest residual risk models require tightened advance rates; models depreciating >20%/year = immediate portfolio exposure review |
| EV-to-ICE Price Gap ($, %) | Difference in avg sale price within same body type | Tracks EV residual risk differential; each $1,000 widening in gap = additional residual exposure on EV portfolio |
| Regional Collateral Spread ($, %) | Difference between cheapest and most expensive state | A spread exceeding 15% requires state-level collateral value adjustments to avoid overstating coverage |
| Price-to-MSRP Ratio (%) | Sale price relative to sticker on new vehicles | Above 100% = lower residual risk (strong demand); below 95% = elevated residual risk (discount-compressed origination) |
| MSRP Parity Trend | Month-over-month movement toward or away from MSRP | Models crossing from above-MSRP to below-MSRP signal the end of supply constraint — downgrade residual forecasts |
| Volume-Weighted Avg Sale Price | National or state-level transaction price by model | More accurate than book values for collateral valuation; essential for portfolio mark-to-market |

## Action-to-Outcome Funnel

1. **Scenario: Residual analyst asks "What are the highest residual risk models right now?"**
   Run *Highest Residual Risk Models*. Present top 15 depreciators with year-over-year price drops. For the top 3, pull current market pricing to validate. Recommendation: "These models have the highest residual risk — tighten advance rates, increase required down payments, or require GAP coverage on new originations."

2. **Scenario: Portfolio manager asks "What is our EV exposure risk?"**
   Run *EV vs ICE Price Parity Tracker* across SUV, Sedan, and Pickup segments. Show current gap and YoY trend. Recommendation: "EV residual risk is highest in the sedan segment where depreciation is X.X%/mo vs Y.Y%/mo for ICE. Apply separate residual curves for EV portfolio segments."

3. **Scenario: Risk team needs "regional collateral assessment"**
   Run *Regional Price Variance* for the top 5 models in the portfolio. Show state-level collateral values and identify where national book values overstate coverage. Recommendation: "Apply a -Z% adjustment to collateral values in [states] to reflect actual market pricing."

4. **Scenario: Auto finance director needs "monthly risk briefing"**
   Run all workflows as a comprehensive lending risk briefing. Structure as: Executive Summary (3 bullet points), Residual Risk Watch, EV Portfolio Exposure, Regional Collateral Health, New Origination Signals. This becomes a recurring monthly deliverable.

5. **Scenario: Residual committee asks "Should we adjust new car residuals?"**
   Run *New Car Markup/Discount Tracker* filtered by specific makes. Show each model's MSRP positioning and trend over the last 3 months. Flag any model that has crossed from premium to discount territory. Recommendation: "Reduce residual forecasts by X% for [Model] based on the transition from premium to discount pricing over the past quarter."

## Output Format

- **Lead with the risk signal, not the methodology.** Example: "Residual risk is INCREASING on Tesla Model Y — 18.3% value loss in the past year, the steepest in the SUV segment." Not: "We queried sold data and calculated depreciation rates."
- **Always cite sample size.** Include sold count alongside any price metric. "Average price of $34,200 (based on 12,847 transactions)" is defensible. A price based on 15 transactions is not — flag low-volume models with a caveat.
- **Use percentages for risk signals, dollars for impact quantification.** Risk teams respond to "18.3% depreciation rate." Finance directors respond to "$4,200 per-unit exposure increase."
- **Include comparison anchors.** Every number needs context: vs prior period, vs segment average, vs national average, vs MSRP. A standalone number is not actionable.
- **Structure multi-workflow reports with clear section headers** and an executive summary at the top. Keep each section self-contained so readers can skip to what matters to them.
- **Cite the data source and period** at the bottom of every output: "Source: MarketCheck transaction data, [Month Year], [Geography]. Analysis includes [dealer type] transactions only. Minimum volume threshold: [N] units per model."
