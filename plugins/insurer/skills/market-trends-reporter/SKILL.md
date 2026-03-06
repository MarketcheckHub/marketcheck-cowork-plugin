---
name: market-trends-reporter
description: >
  This skill should be used when the user asks about "claims market trends",
  "risk assessment trends", "total loss frequency trends", "replacement cost trends",
  "which vehicles are losing value fastest for claims", "EV vs gas claims exposure",
  "regional claims cost differences", "market report for underwriting",
  "depreciation rankings for insurance", "settlement trend analysis",
  "what's happening in the auto market for insurers", "claims cost forecast",
  "which segments have the highest total-loss risk", "fleet insurance risk",
  or needs help creating data-driven market intelligence for insurance
  risk assessment, underwriting decisions, claims cost forecasting,
  or portfolio exposure analysis.
version: 0.1.0
---

# Market Trends Reporter — Insurance Risk Assessment Intelligence

Generate actionable market trend analyses for insurance professionals — underwriters, claims managers, actuaries, and risk analysts — who need timely, data-backed intelligence on vehicle value movements that directly impact claims costs, reserve adequacy, premium pricing, and portfolio risk exposure.

## Insurer Profile (Load First)

Before running any workflow, check for a saved insurer profile:

1. Read `~/.claude/marketcheck/insurer-profile.json`
2. If the file **exists**, use as defaults:
   - `zip` ← `location.zip` — use as default geographic scope
   - `state` ← `location.state`
   - `role` ← `insurer.role` — adjuster, underwriter, claims manager
   - `claim_types` ← `insurer.claim_types`
   - `total_loss_threshold_pct` ← `insurer.total_loss_threshold_pct`
   - `default_comp_radius` ← `insurer.default_comp_radius`
3. If the file **does not exist**, ask for ZIP code and state to proceed. Suggest running `/onboarding` first.
4. **Country note:** This skill requires `get_sold_summary` which is **US-only**. If user indicates UK, inform: "Market trends reporting requires US sold transaction data and is not available for the UK market."
5. If profile exists and relevant, confirm: "Using profile: **[user.name]**, [role], [State]"

## User Context

Before running any workflow, collect the following (auto-filled from insurer profile where available):

- **Role**: Adjuster, underwriter, claims manager, actuary, or risk analyst
- **Analysis question**: What specific trend or risk are they investigating?
- **Geographic scope**: From profile `location.state` if user says "my market", otherwise national (default), specific state(s), or regional
- **Time period**: Current month, trailing quarter, or year-over-year comparison
- **Vehicle focus** (optional): body_type, make, model, fuel_type_category, or inventory_type
- **Output audience**: Internal claims team (operational), underwriting (risk pricing), executive (strategic summary)

If the user simply asks "what's happening in the market", run a combination of workflows and present a comprehensive insurance risk briefing.

## Workflow: Fastest and Slowest Depreciating Models (Total-Loss Risk Assessment)

Identify which models are losing value fastest (highest total-loss claim risk) and which are holding value best (lowest total-loss risk) by comparing average sale prices across periods.

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
   - **Total-Loss Risk Score** = Depreciation Rate x (1 + volume weight) — models with high depreciation AND high insured volume represent the greatest claims exposure
   - Only include models with a minimum sold count threshold (e.g., 100+ units in both periods) for statistical reliability

4. Sort by depreciation rate descending. Present two tables:
   - **Highest Total-Loss Risk Models (Top 15)**: Rank, Make, Model, Current Avg Price, Prior Avg Price, Price Drop ($), Depreciation Rate (%), Current Sold Count, Risk Score
   - **Lowest Total-Loss Risk Models (Bottom 15 / strongest value retention)**: Same columns, sorted by depreciation rate ascending

5. Add insurance context: "The [Model A] lost X% of its value year-over-year, dropping from $Y to $Z on average. Insured vehicles of this model are approaching total-loss thresholds faster — a vehicle insured at $Y that now has an FMV of $Z is a total loss if repair costs exceed $W (75% of current FMV). In contrast, [Model B] held within X% of its prior-year price, maintaining strong value and low total-loss risk."

6. For the top 3 fastest depreciating models, call `mcp__marketcheck__search_active_cars` with:
   - `make` and `model` for each
   - `car_type`: `used`
   - `sort_by`: `price`
   - `sort_order`: `asc`
   - `rows`: `5`
   - `seller_type`: `dealer`
   - This surfaces current market floor prices to validate depreciation severity.

## Workflow: Claims Cost Trend Analysis

Track how average replacement costs are moving for commonly insured vehicle segments — critical for reserve adequacy and premium pricing.

1. Call `mcp__marketcheck__search_active_cars` with:
   - `car_type`: `used`
   - `body_type`: user's target segment (e.g. `SUV`, `Sedan`) or omit for all
   - `sort_by`: `dom`
   - `sort_order`: `desc`
   - `rows`: `20`
   - `seller_type`: `dealer`
   - `zip`: user's zip code (if provided)
   - `radius`: `100` (if zip provided)
   - `state`: user's state (if no zip provided)
   - `stats`: `price`

2. For context on actual transaction values, call `mcp__marketcheck__get_sold_summary` with:
   - `inventory_type`: `Used`
   - `body_type`: same segment filter
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_sale_price`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   - `date_from` / `date_to`: most recent full month

3. For the top 10 models by volume, call `mcp__marketcheck__predict_price_with_comparables` with:
   - `vin`: representative VIN from search results
   - `miles`: average mileage from listings
   - `zip`: user's zip or a central market zip
   - `dealer_type`: `franchise`
   - This validates current replacement cost against ML-predicted market value

4. Present a **Claims Cost Benchmark** table:
   - Columns: Rank, Make, Model, Avg Transaction Price, Active Listing Median, Predicted Market Value, Avg DOM, Volume, Replacement Cost Trend (Rising/Falling/Stable)
   - Highlight models where replacement cost is rising (reserve pressure) vs falling (reserve release opportunity)

5. Insurance narrative: "Replacement costs for [segment] are [rising/falling] — the average transaction price moved from $X to $Y over the past [period]. This [increases/decreases] total-loss claim severity by an estimated $Z per claim. Claims managers should [adjust reserves upward/consider reserve releases] for this segment."

## Workflow: EV vs ICE Claims Exposure Tracker

Track the price gap between electric and internal combustion vehicles — critical for understanding differential depreciation risk in insured EV portfolios.

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

6. Calculate per body type with insurance risk framing:
   - **EV Average Sale Price** (segment-wide, not per model)
   - **ICE Average Sale Price** (segment-wide)
   - **Hybrid Average Sale Price** (segment-wide)
   - **EV-to-ICE Price Gap ($)** = EV Avg - ICE Avg
   - **EV-to-ICE Price Gap (%)** = (EV Avg - ICE Avg) / ICE Avg x 100
   - **Year-over-Year Gap Change** = Current Gap % - Prior Year Gap %
   - **EV Depreciation Premium** = EV depreciation rate - ICE depreciation rate (how much faster EVs lose value)

7. Present:
   - **EV Claims Exposure Tracker** table: Body Type, EV Avg Price, ICE Avg Price, EV-ICE Gap ($), EV-ICE Gap (%), YoY Gap Change, EV Depreciation Premium, Risk Assessment
   - **Risk narrative**: "In the SUV segment, EVs are depreciating X% faster than ICE equivalents. An insured EV SUV purchased at $55,000 reaches total-loss threshold Y months sooner than an equivalent ICE SUV at $45,000. The EV-to-ICE price gap is [narrowing/widening], which [reduces/increases] the differential claims risk. Underwriters should apply a [X%] depreciation premium to EV collision/comprehensive premiums to account for accelerated value loss."
   - **Parity narrative**: "At the current rate of convergence, EV-ICE price parity in [segment] could be reached by [estimated quarter/year], which would normalize claims severity between fuel types."

## Workflow: Regional Claims Cost Variance

Reveal where in the US replacement costs are highest and lowest for specific vehicles — critical for regional reserve calibration and settlement offer accuracy.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `make`: user's target make (required)
   - `model`: user's target model (required for model-level; omit for brand-level)
   - `inventory_type`: `Used`
   - `summary_by`: `state`
   - `limit`: `51`

2. From the results, calculate:
   - **National average replacement cost** (weighted by volume)
   - **Cheapest 5 states** by average sale price (lowest claims severity)
   - **Most expensive 5 states** by average sale price (highest claims severity)
   - **Claims cost spread** = Most Expensive State Avg - Cheapest State Avg
   - **Claims cost spread %** = Spread / National Avg x 100

3. For context, call `mcp__marketcheck__get_sold_summary` for the same make/model in the most expensive state with:
   - `state`: most expensive state code
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `top_n`: `1`
   - This confirms volume is sufficient for the price to be meaningful.

4. Present:
   - **Regional Claims Cost Map** table: State, Avg Replacement Cost, vs National Avg ($), vs National Avg (%), Volume, Claims Cost Risk (High/Medium/Low)
   - Sort by Avg Sale Price descending (highest claims cost first)
   - **Risk summary**: "A total-loss claim on a used [Year Range] [Make Model] averages $X nationally. Claims in [State] cost $Y (+Z% above national avg) — the most expensive market. Claims in [State] cost $A (-B% below national avg) — the lowest cost market. The state-to-state claims cost spread is $C."

5. For underwriting, add: "Premium pricing should reflect regional replacement cost variance. Policyholders in [expensive state] face replacement costs Z% above national average — collision and comprehensive premiums should be calibrated accordingly."

6. If year-over-year comparison was requested, repeat step 1 for the prior year and show which states saw the largest replacement cost increases or decreases. Flag states where costs rose more than 5% as requiring reserve review.

## Workflow: New Car Replacement Cost Monitor

Identify which new car models are selling above MSRP (elevated replacement cost for new-vehicle total-loss claims) and which are discounted — directly impacts settlement calculations for vehicles under 1 year old.

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
   - **Elevated Replacement Cost Models (Above MSRP)** table: Rank, Make, Model, Avg Price Over MSRP (%), Avg Markup ($), Sold Count, Avg DOM
     - These vehicles cost more to replace than MSRP suggests — total-loss settlements at MSRP will leave the claimant unable to purchase a replacement
   - **Favorable Replacement Cost Models (Below MSRP)** table: Rank, Make, Model, Avg Discount Off MSRP (%), Avg Discount ($), Sold Count, Avg DOM
     - These vehicles can be replaced below MSRP — settlement at MSRP may overcompensate
   - **Brand-Level Replacement Cost Positioning** table: Make, Avg Price vs MSRP (%), Direction (Premium/Discount), Claims Implication

5. Insurance narrative: "[Model A] commands the highest premium at +X% over MSRP, translating to an average $Y above sticker. A total-loss claim on a new [Model A] settled at MSRP would leave the claimant $Y short of actual replacement cost — a potential bad-faith exposure. Conversely, [Model B] sells at -Z% off MSRP, meaning settlements at MSRP may overcompensate by $W."

6. For prior-period comparison, repeat calls and show trend: "Replacement costs on [Model] have decreased from +X% over MSRP to +Y%, reducing the above-MSRP claims exposure by $Z per unit." Also add: "Models transitioning from premium to discount territory this month: [list] — standard MSRP-based settlements are now adequate for these models."

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Insurance Business Impact |
|-----|-------------|--------------------------|
| Depreciation Rate by Model (%) | YoY average sale price change for used vehicles | Drives total-loss threshold calculations; models depreciating >20%/year reach total-loss faster, increasing claim frequency |
| Total-Loss Risk Score | Depreciation Rate x Volume Weight | Composite metric identifying which models pose the greatest aggregate claims exposure in the insured portfolio |
| EV Depreciation Premium (%) | EV depreciation rate minus ICE depreciation rate within same segment | Quantifies the additional claims risk for insured EV portfolios; basis for differential EV premiums |
| Regional Claims Cost Spread ($, %) | Difference between most and least expensive state for replacement | A spread exceeding 15% signals the need for regional reserve calibration and premium differentiation |
| Replacement-to-MSRP Ratio (%) | Sale price relative to sticker on new vehicles | Above 100% = replacement cost exceeds MSRP (bad-faith risk if settling at sticker); below 95% = favorable claims environment |
| MSRP Parity Trend | Month-over-month movement toward or away from MSRP | Models crossing from above-MSRP to below signal normalizing replacement costs — reserves can be adjusted |
| Volume-Weighted Avg Replacement Cost | National or state-level transaction price by model | More accurate than book values for setting claim reserves; essential for actuarial loss modeling |

## Action-to-Outcome Funnel

1. **Scenario: Claims manager asks "Which vehicles have the highest total-loss risk?"**
   Run *Fastest/Slowest Depreciating Models*. Present top 15 depreciators with year-over-year price drops and total-loss risk scores. For the top 3, pull current market floor prices. Narrative: "These models represent the highest total-loss claim risk in your portfolio — [Model A] is depreciating at X%/year, meaning an insured vehicle that was worth $Y at policy inception is now worth $Z. Total-loss threshold is $W."

2. **Scenario: Underwriter asks "How should we price EV comprehensive coverage?"**
   Run *EV vs ICE Claims Exposure Tracker* across SUV, Sedan, and Pickup segments. Show current depreciation premium and YoY trend. Recommend: "EVs are depreciating X% faster than ICE equivalents in the [segment]. Apply a [Y%] depreciation premium to EV collision/comprehensive to account for accelerated total-loss risk. Review annually as EV-ICE parity narrows."

3. **Scenario: Actuary asks "What's happening to replacement costs in Florida?"**
   Run *Regional Claims Cost Variance* for the top 10 insured models in FL. Cross-reference with national averages. Recommend: "Florida replacement costs are X% [above/below] national average for [model]. Current reserves [are/are not] adequate. Adjust state-level loss picks by [amount]."

4. **Scenario: Risk analyst needs a "quarterly insurance market intelligence briefing"**
   Run all workflows as a comprehensive briefing. Structure as: Executive Summary (3 bullet points), Total-Loss Risk Watch, EV Exposure Update, Regional Claims Cost Map, New Vehicle Replacement Cost Monitor. This becomes a recurring quarterly publication for the underwriting committee.

5. **Scenario: Claims manager asks "Are replacement costs rising for new trucks?"**
   Run *New Car Replacement Cost Monitor* filtered by body_type=Pickup. Show MSRP parity and trend. Flag any models selling above MSRP. Recommend: "The [Model] is still commanding a X% premium over MSRP. Total-loss settlements at MSRP on this model leave claimants $Y short of replacement — creating dispute and bad-faith risk. Settle at market replacement cost, not MSRP."

## Output Format

- **Lead with the risk signal, not the methodology.** Example: "The Tesla Model Y depreciated 18.3% year-over-year — the fastest in the SUV segment, pushing more insured units toward total-loss thresholds." Not: "We queried sold data and calculated depreciation rates."
- **Always cite sample size.** Include sold count alongside any price metric. "Average replacement cost of $34,200 (based on 12,847 transactions)" is defensible. A price based on 15 transactions is not — flag low-volume models with a caveat.
- **Use dollar amounts for claims/settlement context, percentages for underwriting/actuarial context.** Adjusters respond to "$4,200 drop in claim value." Underwriters respond to "18.3% depreciation rate impacting loss ratios."
- **Include comparison anchors.** Every number needs context: vs prior period, vs segment average, vs national average, vs MSRP. A standalone number is not actionable intelligence.
- **For claims cost tracking, always validate against predicted market price.** Use `predict_price_with_comparables` to confirm that trend-level data aligns with individual vehicle valuations.
- **Structure multi-workflow reports with clear section headers** and an executive summary at the top. Keep each section self-contained so different audiences (claims, underwriting, actuarial) can skip to what matters to them.
- **Cite the data source and period** at the bottom of every output: "Source: MarketCheck transaction data, [Month Year], [Geography]. Analysis includes [dealer type] transactions only. Minimum volume threshold: [N] units per model."
