---
name: market-trends-reporter
description: >
  Data-driven automotive trend analysis. Triggers: "market trends",
  "best deals right now", "fastest depreciating cars", "slowest depreciating models",
  "EV vs gas prices", "EV vs ICE price parity", "price trends by region",
  "new car markups", "new car discounts", "market report", "depreciation rankings",
  "what's happening in the auto market", "which cars are losing value fastest",
  "price drops this month", "regional price differences", "cheapest state to buy",
  "MSRP vs sale price", automotive market analysis, trend stories, consumer
  buying guides.
version: 0.1.0
---

# Market Trends Reporter — Data-Driven Automotive Insights

Generate publishable market trend analyses, consumer buying guides, and data-backed stories using real sold transaction data and live inventory signals. Purpose-built for automotive journalists, market analysts, content teams, and industry professionals who need timely, defensible data narratives.

## Dealer Profile (Load First — Optional Context)

Before running any workflow, check for a saved dealer profile:

1. Read the `marketcheck-profile.md` project memory file
2. If the file **exists**, use as optional context:
   - `state` ← `location.state` — use as default geographic scope if user says "my market" or "my area"
   - `franchise_brands` ← `dealer.franchise_brands` — use as default vehicle focus if user asks about "my brand"
   - `country` ← `location.country`
3. If the file **does not exist**, ask for all fields as before — this skill works fine without a profile.
4. **Country note:** This skill requires `get_sold_summary` which is **US-only**. UK users cannot use market trends reporting. If `country == UK`, inform: "Market trends reporting requires US sold transaction data and is not available for the UK market."
5. If profile exists and relevant, confirm: "Using profile context: **[state]**, **[franchise_brands]**"

## User Context

Before running any workflow, collect the following (auto-filled from dealer profile where available):

- **Role**: Journalist/media, market research analyst, OEM product planner, or dealer/consumer
- **Story angle or question**: What specific trend or question are they investigating?
- **Geographic scope**: From profile `location.state` if user says "my market", otherwise national (default), specific state(s), or regional
- **Time period**: Current month, trailing quarter, or year-over-year comparison
- **Vehicle focus** (optional): From profile `dealer.franchise_brands` if user says "my brand", otherwise ask for body_type, make, model, fuel_type_category, or inventory_type
- **Audience**: Consumer-facing (plain language, buying advice) or industry-facing (technical, strategic)

If the user simply asks "what's happening in the market", run a combination of workflows and present a comprehensive briefing.

## Workflow: Fastest and Slowest Depreciating Models

Identify which models are losing value fastest (or holding value best) by comparing average sale prices across periods.

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

5. Add narrative context: "The [Model A] lost X% of its value year-over-year, dropping from $Y to $Z on average. This represents the steepest depreciation among mainstream models. In contrast, [Model B] held within X% of its prior-year price, making it the strongest value holder in the [segment] category."

6. For the top 3 fastest depreciating models, call `mcp__marketcheck__search_active_cars` with:
   - `make` and `model` for each
   - `car_type`: `used`
   - `sort_by`: `price`
   - `sort_order`: `asc`
   - `rows`: `5`
   - `seller_type`: `dealer`
   - This surfaces specific current listings as "example deals" to anchor the story.

## Workflow: Best Deals Right Now

Find vehicles currently listed with significant price reductions that have been sitting on lots — a proxy for motivated sellers.

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

4. Present a **Best Deals** table:
   - Columns: Rank, Year, Make, Model, Trim, Listed Price, Original Price, Price Drop ($), Price Drop (%), DOM (days), Deal Score, Predicted Market Price, Below/Above Market ($), Dealer, Location
   - Only rank vehicles where Listed Price < Predicted Market Price as "true deals"

5. Narrative: "The best deal in [segment] right now is a [Year Make Model] at [Dealer] in [City, State], listed at $X after a $Y price reduction. It has been on the lot for Z days and is priced $W below comparable market value. This represents a Deal Score of [N], the highest we found."

6. For consumer audiences, add: "If you are in the market for a [segment], these vehicles represent genuine below-market opportunities. Vehicles with high DOM and multiple price cuts signal dealer motivation to sell — use this as leverage in negotiation."

## Workflow: EV vs ICE Price Parity Tracker

Track the price gap between electric and internal combustion vehicles within the same segments to measure progress toward price parity.

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
   - **Parity narrative**: "In the SUV segment, the EV-to-ICE price gap is $X,XXX (Y%), [down/up] from $A,AAA (B%) a year ago. The gap is narrowing fastest in [segment], driven primarily by price reductions on [Model]. At the current rate of convergence, price parity in [segment] could be reached by [estimated quarter/year]."

## Workflow: Regional Price Variance Story

Reveal where in the US a specific vehicle is cheapest and most expensive, helping consumers time and locate purchases and helping OEMs understand regional pricing dynamics.

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

5. For consumer-facing content, add actionable advice: "Buyers in [expensive state] could save $X by purchasing from a dealer in [cheap state], even after factoring in $Y estimated transport costs. Online purchasing and dealer delivery have made cross-state deals increasingly practical."

6. If year-over-year comparison was requested, repeat step 1 for the prior year and show which states saw the largest price increases or decreases.

## Workflow: New Car Markup and Discount Tracker

Identify which new car models are selling above MSRP (markup) and which require discounts, providing a real-time view of supply-demand balance at the model level.

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

6. For prior-period comparison, repeat calls and show trend: "Markups on [Model] have decreased from +X% to +Y% over the past quarter, signaling supply is catching up to demand." Also add: "Models transitioning from premium to discount territory this month: [list]."

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Depreciation Rate by Model (%) | YoY average sale price change for used vehicles | Guides consumer purchase timing and trade-in strategy; models depreciating >20%/year represent buying opportunities |
| Deal Score | (Price Drop % x DOM/30) for active listings | Combines discount depth with seller motivation; scores above 5.0 indicate strong negotiation leverage |
| EV-to-ICE Price Gap ($, %) | Difference in avg sale price within same body type | Tracks EV affordability trajectory; each $1,000 reduction in gap correlates with ~2-3% increase in EV consideration |
| Regional Price Spread ($, %) | Difference between cheapest and most expensive state | A spread exceeding 15% on popular models represents meaningful consumer savings opportunity via cross-state purchase |
| Price-to-MSRP Ratio (%) | Sale price relative to sticker on new vehicles | Above 100% = seller's market (supply constrained); below 95% = buyer's market (negotiate aggressively) |
| MSRP Parity Trend | Month-over-month movement toward or away from MSRP | Models crossing from above-MSRP to below-MSRP signal the end of a supply shortage |
| Volume-Weighted Avg Sale Price | National or state-level transaction price by model | More accurate than MSRP for understanding real consumer cost; essential for affordability reporting |

## Action-to-Outcome Funnel

1. **Scenario: Journalist asks "What are the fastest depreciating cars right now?"**
   Run *Fastest/Slowest Depreciating Models*. Present top 15 depreciators with year-over-year price drops. For the top 3, pull current listings to show example deals. Narrative angle: "These models have lost the most value in the past year — here is why, and what it means for buyers and current owners."

2. **Scenario: Consumer asks "Where can I find the best deal on a used RAV4?"**
   Run *Best Deals Right Now* filtered by make=Toyota, model=RAV4. Cross-reference with *Regional Price Variance* to show cheapest states. Recommend: "The best current deal is [specific listing]. If you are flexible on location, [State] averages $X less than [your state] for the same vehicle."

3. **Scenario: Analyst asks "Is EV price parity getting closer?"**
   Run *EV vs ICE Price Parity Tracker* across SUV, Sedan, and Pickup segments. Show current gap and YoY trend. Recommend: "Parity is closest in the sedan segment at only $X,XXX gap (-Y% from last year). SUV gap remains large at $Z,ZZZ but is narrowing at $W/quarter. At this rate, expect SUV parity by [quarter/year]."

4. **Scenario: Content team needs "monthly market report data"**
   Run all five workflows as a comprehensive briefing. Structure as: Executive Summary (3 bullet points), Depreciation Watch, Best Consumer Deals, EV Transition Update, Regional Pricing, New Car Markup/Discount Monitor. This becomes a recurring monthly publication.

5. **Scenario: OEM product planner asks "Are our new models still commanding premiums?"**
   Run *New Car Markup/Discount Tracker* filtered by the OEM's make. Show each model's MSRP positioning and trend over the last 3 months. Flag any model that has crossed from premium to discount territory. Recommend: "Your [Model X] premium has eroded from +5.2% to +1.1% over 3 months. At current trajectory, it will cross into discount territory by [month]. Consider adjusting production or adding incentive support preemptively."

## Output Format

- **Lead with the insight, not the methodology.** Example: "The Tesla Model Y lost 18.3% of its value in the past year — the steepest depreciation of any SUV." Not: "We queried sold data and calculated depreciation rates."
- **Always cite sample size.** Include sold count alongside any price metric. "Average price of $34,200 (based on 12,847 transactions)" is credible. A price based on 15 transactions is not — flag low-volume models with a caveat.
- **Use dollar amounts for consumer audiences, percentages for industry audiences.** Consumers respond to "$4,200 price drop." Analysts respond to "18.3% depreciation rate."
- **Include comparison anchors.** Every number needs context: vs prior period, vs segment average, vs national average, vs MSRP. A standalone number is not a story.
- **For "Best Deals" content, always validate against predicted market price.** A price cut from an inflated original list is not a deal. Only highlight vehicles priced below `predict_price_with_comparables` output as genuine below-market opportunities.
- **Structure multi-workflow reports with clear section headers** and an executive summary at the top. Keep each section self-contained so readers can skip to what matters to them.
- **Cite the data source and period** at the bottom of every output: "Source: MarketCheck transaction data, [Month Year], [Geography]. Analysis includes [dealer type] transactions only. Minimum volume threshold: [N] units per model."

## Self-Check (before presenting to user)

- [ ] Trends include both price direction and volume context
- [ ] Fastest/slowest depreciating lists include actual depreciation rates
- [ ] EV vs ICE comparison included where relevant
- [ ] Regional price differences quantified in dollars
- [ ] Data period and geography cited
