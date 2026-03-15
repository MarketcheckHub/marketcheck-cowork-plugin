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

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Trends Reporter — Lending Risk Assessment & Residual Value Intelligence

Generate lending-focused market trend analyses, residual risk assessments, and data-backed portfolio intelligence using real sold transaction data and live inventory signals. Purpose-built for auto lenders, residual value analysts, portfolio risk managers, and auto finance directors who need timely, defensible data for residual setting, advance rate decisions, and portfolio risk management.

## Lender Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `state`, `tracked_segments`, `risk_ltv_threshold`, `high_risk_ltv_threshold`, `country`. If missing, ask. US-only (requires `get_sold_summary`). Confirm profile.

## User Context

Lender (residual analyst, portfolio risk manager, auto finance director) investigating market trends for residual setting, advance rate decisions, and portfolio risk management. Collect: story angle, geographic scope (profile or ask), time period, vehicle focus, portfolio context. For "what's happening in the market", run combined workflows as a comprehensive lending risk briefing.

## Workflow: Highest Residual Risk Models (Fastest Depreciating)

Identify which models are losing value fastest (highest residual risk) and which hold value best (lowest residual risk) by comparing average sale prices across periods.

1. **Current period sold summary** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (current month), `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=50`, `state` if scoped.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

2. **Prior period sold summary** — Repeat step 1 for same month one year ago.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

3. For each make/model appearing in both periods, calculate:
   - **Price Change ($)** = Current Avg Price - Prior Avg Price
   - **Depreciation Rate (%)** = (Prior Avg Price - Current Avg Price) / Prior Avg Price x 100
   - Only include models with a minimum sold count threshold (e.g., 100+ units in both periods) for statistical reliability

4. Sort by depreciation rate descending. Present two tables:
   - **Highest Residual Risk Models (Top 15)**: Rank, Make, Model, Current Avg Price, Prior Avg Price, Price Drop ($), Depreciation Rate (%), Current Sold Count, Risk Signal
   - **Lowest Residual Risk Models (Bottom 15 / strongest retention)**: Same columns, sorted by depreciation rate ascending

5. Add lending context: "The [Model A] lost X% of its value year-over-year, dropping from $Y to $Z on average. This represents the highest residual risk among mainstream models — lenders should tighten advance rates or require higher down payments on new originations. In contrast, [Model B] held within X% of its prior-year price, making it the lowest residual risk in the [segment] category — standard advance rates are appropriate."

6. **Active listings for top 3 depreciators** — For each, call `mcp__marketcheck__search_active_cars` with `make`, `model`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=5`, `seller_type=dealer`.
   → **Extract only**: per listing — price, miles, dealer_name. Discard full response.

## Workflow: EV vs ICE Price Parity Tracker

Track the price gap between electric and internal combustion vehicles within the same segments to measure residual risk differentials and lending opportunity.

1. **EV sold summary** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to`, `fuel_type_category=EV`, `body_type=SUV`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`, `state` if scoped.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

2. **ICE sold summary** — Repeat with `fuel_type_category=ICE`.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

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

1. **Sold summary by state** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `make`, `model` (optional), `inventory_type=Used`, `summary_by=state`, `limit=51`.
   → **Extract only**: per state — average_sale_price, sold_count. Discard full response.

2. From the results, calculate:
   - **National average sale price** (weighted by volume)
   - **Cheapest 5 states** by average sale price
   - **Most expensive 5 states** by average sale price
   - **Price spread** = Most Expensive State Avg - Cheapest State Avg
   - **Price spread %** = Spread / National Avg x 100

3. **Volume check** — Call `mcp__marketcheck__get_sold_summary` for cheapest state with `state`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `top_n=1`.
   → **Extract only**: sold_count. Discard full response.

4. Present with lending implications:
   - **Regional Collateral Value Map** table: State, Avg Sale Price, vs National Avg ($), vs National Avg (%), Sold Count, Avg DOM
   - Sort by Avg Sale Price ascending (cheapest first)
   - **Summary**: "A used [Year Range] [Make Model] averages $X nationally. The lowest collateral values are in [State] at $Y (-Z% below national avg). The strongest collateral values are in [State] at $A (+B%). The state-to-state collateral spread is $C."

5. Add lending guidance: "Lenders using national averages for collateral valuation are overstating coverage in [cheap states] and understating it in [expensive states]. For portfolios concentrated in [cheap state], apply a -Z% regional adjustment to collateral values. This affects approximately X% of a typical national portfolio."

6. If year-over-year comparison was requested, repeat step 1 for the prior year and show which states saw the largest collateral value increases or decreases.

## Workflow: New Car Markup and Discount Tracker

Identify which new car models are selling above MSRP (markup) and which require discounts — signals for residual value forecasting on new originations.

1. **Top markups** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=20`, `state` if scoped.
   → **Extract only**: make, model, price_over_msrp_percentage, sold_count per entry. Discard full response.

2. **Deepest discounts** — Repeat with `ranking_order=asc`, `top_n=20`.
   → **Extract only**: make, model, price_over_msrp_percentage, sold_count per entry. Discard full response.

3. **Brand-level pricing power** — Call with `ranking_dimensions=make`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=20`.
   → **Extract only**: make, price_over_msrp_percentage per brand. Discard full response.

4. Present with residual forecasting implications:
   - **Models Commanding Premiums (Above MSRP)** table: Rank, Make, Model, Avg Price Over MSRP (%), Avg Markup ($), Sold Count, Avg DOM
     - These vehicles have lower near-term residual risk — demand exceeds supply
   - **Models Requiring Discounts (Below MSRP)** table: Rank, Make, Model, Avg Discount Off MSRP (%), Avg Discount ($), Sold Count, Avg DOM
     - These vehicles signal residual pressure — discount at origination compresses future residual value
   - **Brand-Level MSRP Positioning** table: Make, Avg Price vs MSRP (%), Direction (Premium/Discount), Residual Implication

5. Narrative with lending guidance: "[Model A] commands the highest premium in the new car market at +X% over MSRP, translating to an average $Y markup — residual risk LOW for new originations. Conversely, [Model B] requires the deepest discount at -Z% off MSRP ($W off) — residual risk ELEVATED as the discounted origination price compresses the residual floor."

6. For prior-period comparison, repeat calls and show trend: "Markups on [Model] have decreased from +X% to +Y% over the past quarter, signaling supply is catching up to demand — reduce residual forecasts for this model on new lease originations." Also add: "Models transitioning from premium to discount territory this month: [list] — downgrade residual assumptions immediately."

## Output

Present: risk signal headline (not methodology), ranked data tables with sample sizes, key lending risk signals (depreciation rate, EV gap, regional spread, MSRP parity shifts), and actionable recommendation tied to advance rates or residual forecasts. Cite data source and period.
