---
name: market-trends-reporter
description: >
  This skill should be used when the user asks about "competitive landscape",
  "market dynamics", "fastest depreciating models", "slowest depreciating models",
  "EV vs gas prices", "EV vs ICE price parity", "price trends by region",
  "new car markups", "new car discounts", "market trends", "depreciation rankings",
  "what's happening in the auto market", "which models are losing value fastest",
  "price drops this month", "regional price differences", "cheapest state to buy",
  "MSRP vs sale price", "competitive pricing dynamics",
  or needs help creating data-driven competitive landscape analysis,
  market dynamics reports, or strategic pricing intelligence
  for OEM decision-making and brand positioning.
version: 0.1.0
---

# Market Trends Reporter — Competitive Landscape & Market Dynamics Intelligence

Generate competitive landscape analyses, segment pricing intelligence, and data-driven market dynamics reports. Purpose-built for OEM strategists, product planners, brand managers, and regional distributors who need timely, defensible data narratives to inform brand positioning and competitive response.

## Manufacturer Profile (Load First)

Before running any workflow, check for a saved manufacturer profile:

1. Read `~/.claude/marketcheck/manufacturer-profile.json`
2. If the file **exists**, extract and use silently:
   - `brands` <- `manufacturer.brands` — your own brands (highlight in all results with a star)
   - `states` <- `manufacturer.states` — geographic scope
   - `competitor_brands` <- `manufacturer.competitor_brands` — always show prominently
   - `country` <- `location.country`
   - `user_name` <- `user.name`
   - `company` <- `user.company`
3. If the file **does not exist**: Ask: "Which brand(s) do you represent?" and "Which competitors to track?" This skill works without a profile. Suggest running `/onboarding` for persistent setup.
4. **Country note:** This skill requires `get_sold_summary` which is **US-only**. If `country == UK`, inform: "Market trends reporting requires US sold transaction data and is not available for the UK market."
5. If profile exists, confirm: "Using profile: **[user_name]** at **[company]** — Brands: **[brands]**, Competitors: **[competitor_brands]**"

## User Context

Before running any workflow, collect the following (auto-filled from manufacturer profile where available):

- **Story angle or question**: What specific trend or competitive question are they investigating?
- **Geographic scope**: From profile `manufacturer.states` if user says "my markets", otherwise national (default), specific state(s), or regional
- **Time period**: Current month, trailing quarter, or year-over-year comparison
- **Vehicle focus** (optional): body_type, make, model, fuel_type_category, or inventory_type
- **Competitive context**: Always include your brands vs competitor brands from profile

If the user simply asks "what's happening in the market" or "competitive landscape update", run a combination of workflows and present a comprehensive competitive briefing.

## Workflow: Fastest and Slowest Depreciating Models

Identify which models are losing value fastest (or holding value best) — highlight your brand's models and competitor models throughout.

1. Call `mcp__marketcheck__get_sold_summary` for the **current period**:
   - `date_from`: first of current month (e.g. `2026-01-01`)
   - `date_to`: last of current month (e.g. `2026-01-31`)
   - `inventory_type`: `Used`
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_sale_price`
   - `ranking_order`: `desc`
   - `top_n`: `50`
   - `state`: user's state filter (omit for national)

2. Call `mcp__marketcheck__get_sold_summary` for the **prior period** (same month one year ago) with identical filters.

3. For each make/model appearing in both periods, calculate:
   - **Price Change ($)** = Current Avg Price - Prior Avg Price
   - **Depreciation Rate (%)** = (Prior Avg Price - Current Avg Price) / Prior Avg Price x 100
   - Only include models with a minimum sold count threshold (e.g., 100+ units in both periods)

4. Sort by depreciation rate descending. Present two tables:
   - **Fastest Depreciating Models (Top 15)**: Rank, Make, Model, Current Avg Price, Prior Avg Price, Price Drop ($), Depreciation Rate (%), Current Sold Count — mark your models with a star and competitor models
   - **Best Value-Holding Models (Bottom 15 / lowest depreciation)**: Same columns, sorted ascending

5. Add competitive narrative: "Among your brand's models, [Model A] lost X% of its value year-over-year — the [Nth] steepest in the market. Competitor [Brand]'s [Model B] held within Y%, outperforming your equivalent by $Z per unit. [Model C] from your lineup is among the strongest value holders, retaining X% — use this in marketing and CPO positioning."

6. For the top 3 fastest depreciating models that belong to YOUR brand, call `mcp__marketcheck__search_active_cars` with:
   - `make` and `model` for each
   - `car_type`: `used`
   - `sort_by`: `price`
   - `sort_order`: `asc`
   - `rows`: `5`
   - `seller_type`: `dealer`
   - This surfaces current market pricing to inform residual support decisions.

## Workflow: EV vs ICE Price Parity Tracker

Track the price gap between electric and internal combustion vehicles within the same segments — essential for OEM electrification strategy and pricing decisions.

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
   - **Your brand's EV price** vs market EV average in each segment

7. Present:
   - **Price Parity Tracker** table: Body Type, EV Avg Price, ICE Avg Price, Hybrid Avg Price, EV-ICE Gap ($), EV-ICE Gap (%), YoY Gap Change, Parity Trend (Narrowing/Widening/Stable)
   - **Top EV Models by Segment** table — highlight your models and competitor models
   - **Strategic parity narrative**: "In the SUV segment, the EV-to-ICE price gap is $X,XXX (Y%), [down/up] from $A,AAA (B%) a year ago. Your brand's EV SUV averages $Z,ZZZ — [above/below] the EV segment average. Competitor [Brand]'s EV is priced at $W,WWW. At the current rate of convergence, price parity in [segment] could be reached by [estimated quarter/year] — plan production ramps accordingly."

## Workflow: Regional Price Variance — Competitive Geography

Reveal where your brand is priced highest and lowest across states, and how you compare to competitors in each region.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `make`: your brand (from profile)
   - `model`: user's target model (optional)
   - `inventory_type`: `Used` (or `New` based on user intent)
   - `summary_by`: `state`
   - `limit`: `51`

2. Repeat for each competitor brand to show competitive pricing geography.

3. From the results, calculate:
   - **National average sale price** for your brand and each competitor
   - **Cheapest 5 states** and **most expensive 5 states** for your brand
   - **Price spread** = Most Expensive State Avg - Cheapest State Avg
   - **Competitive advantage by state** = Your brand avg - Competitor avg (positive = you are priced higher)

4. Present:
   - **Regional Price Map** table: State, Your Brand Avg, Competitor A Avg, Competitor B Avg, Your Price vs Competitors, Sold Count, Avg DOM
   - Focus on states in your profile
   - **Summary box**: "Your [Model] averages $X nationally. Cheapest in [State] at $Y (-Z% below national). Most expensive in [State] at $A (+B%). Competitor [Brand] is $C [cheaper/more expensive] than you nationally, but the gap varies by state."

5. Strategic advice: "In [State], your brand commands a $X premium over [Competitor]. In [State], the competitor undercuts you by $Y — this market may need targeted incentive support or allocation adjustment."

## Workflow: New Car Markup and Discount Tracker — Competitive Pricing Power

Identify which new models are selling above MSRP (pricing power) and which require discounts — compare your models vs competitors.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `inventory_type`: `New`
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `price_over_msrp_percentage`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   - `state`: user's state filter (omit for national)

2. Call same with `ranking_order`: `asc`, `top_n`: `20` for deepest discounts.

3. For brand-level view, call with `ranking_dimensions`: `make`.

4. Present three sections:
   - **Models Commanding Premiums (Above MSRP)** — mark your models with star, highlight competitors
   - **Models Requiring Discounts (Below MSRP)** — same marking
   - **Brand-Level MSRP Positioning** table: Make, Avg Price vs MSRP (%), Direction — your brands vs competitors

5. Competitive narrative: "Your [Model A] commands +X% premium (#Y in market), while competitor [Brand]'s [Model B] is at +Z%. In the discount category, your [Model C] requires -W% discount vs competitor [Model D] at -V%. At the brand level, your brand averages [premium/discount] of X.X% vs competitor's Y.Y%."

6. Strategic advice: "Your premium models should have production protected. Discount models may need production cuts or targeted incentives. Models transitioning from premium to discount this month: [list] — monitor closely."

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Depreciation Rate by Model (%) | YoY average sale price change for your models vs competitors | Informs residual support decisions; models depreciating >20%/year need intervention |
| EV-to-ICE Price Gap ($, %) | Difference in avg sale price within same body type | Tracks EV affordability for your brand; each $1,000 gap reduction accelerates adoption consideration |
| Regional Price Spread ($, %) | Your brand price difference between cheapest and most expensive state | A spread exceeding 15% indicates allocation or demand imbalance — strategic opportunity |
| Price-to-MSRP Ratio (%) | Your models' sale price relative to sticker | Above 100% = pricing power; below 95% = incentive dependency; compare vs competitors |
| Competitive Price Gap ($) | Your brand avg price vs competitor avg price by state | Quantifies competitive pricing advantage/disadvantage by geography |
| MSRP Parity Trend | MoM movement of your models toward or away from MSRP | Models crossing from above to below MSRP signal demand softening — production signal |

## Action-to-Outcome Funnel

1. **Scenario: Brand strategist asks "How does our depreciation compare to competitors?"**
   Run *Fastest/Slowest Depreciating Models*. Show your models in context. Identify where competitors hold value better. Recommend: "Your [Model] depreciates X% faster than competitor [Model]. This impacts trade-in satisfaction and loyalty. Consider CPO warranty extensions or residual value support to close the gap."

2. **Scenario: Product planner asks "Is EV price parity getting closer for our segment?"**
   Run *EV vs ICE Price Parity Tracker* across SUV, Sedan, and Pickup. Show your brand's EV pricing vs market. Recommend: "Your EV SUV is $X,XXX above the EV segment average. Competitor [Brand]'s EV is $Y,YYY cheaper. At current convergence rate, segment parity by [quarter/year] — plan production ramp accordingly."

3. **Scenario: Regional manager asks "Where are our models most competitive on price?"**
   Run *Regional Price Variance* for the brand and model. Show state-level pricing vs competitors. Recommend: "In [State], your [Model] is $X cheaper than [Competitor]. In [State], they undercut you by $Y — targeted incentive of $Z per unit could close the gap."

4. **Scenario: Strategy team needs "monthly competitive landscape briefing"**
   Run all workflows as a comprehensive briefing. Structure as: Executive Summary, Depreciation Landscape, EV Transition Dynamics, Regional Pricing Intelligence, Pricing Power Index. Frame as a monthly strategic input document.

5. **Scenario: Brand manager asks "Are our new models still commanding premiums?"**
   Run *New Car Markup/Discount Tracker* for your brand and competitors. Show model-by-model MSRP positioning. Recommend: "Your [Model X] premium has eroded from +5.2% to +1.1%. Competitor [Model Y] still holds +3.8%. Evaluate production levels or retarget incentive spend to high-demand states."

## Output Format

- **Lead with the competitive insight, not the methodology.** Example: "Your Model Y lost 18.3% of its value this year — the steepest in the SUV segment. Competitor CR-V held at 8.1%." Not: "We queried sold data and calculated depreciation rates."
- **Always cite sample size.** Include sold count alongside any price metric.
- **Always mark your brands with a star in tables** and competitor brands distinctly.
- **Include competitive comparison anchors.** Every metric for your brand needs context: vs competitors, vs segment average, vs national average, vs prior period.
- **Structure multi-workflow reports with clear section headers** and an executive summary.
- **End with strategic recommendations** specific to the manufacturer role: production adjustments, incentive targeting, allocation changes, competitive response.
- **Cite the data source and period** at the bottom of every output: "Source: MarketCheck transaction data, [Month Year], [Geography]."
