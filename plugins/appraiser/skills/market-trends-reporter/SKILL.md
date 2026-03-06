---
name: market-trends-reporter
description: >
  This skill should be used when the user asks about "market trends", "best deals right now", "fastest depreciating cars", "slowest depreciating models", "EV vs gas prices", "EV vs ICE price parity", "price trends by region", "new car markups", "new car discounts", "market report", "depreciation rankings", "what's happening in the auto market", "which cars are losing value fastest", "price drops this month", "regional price differences", "cheapest state to buy", "MSRP vs sale price", or needs data-driven market trend insights relevant to vehicle valuations, appraisal adjustments, and comparable market intelligence.
version: 0.1.0
---

# Market Trends Reporter — Data-Driven Valuation Intelligence for Appraisers

Generate actionable market trend analyses, valuation adjustment insights, and data-backed comparable market intelligence using real sold transaction data and live inventory signals. Purpose-built for appraisers, insurance adjusters, fleet analysts, and valuation professionals who need timely, defensible market context to support their appraisals.

## Appraiser Profile (Load First — Optional Context)

Load `~/.claude/marketcheck/appraiser-profile.json` if exists. Extract: state, specialization, country, min_comp_count. If missing, ask — skill works without profile. US-only (`get_sold_summary`); UK not supported. Confirm profile.

## User Context

User is an appraiser needing data-driven market trend intelligence to adjust current valuations with timely, defensible comparable market context.

| Required | Field | Source |
|----------|-------|--------|
| Yes | Story angle or question | Ask |
| Auto/Ask | Geographic scope | Profile state or ask (default: national) |
| Auto/Ask | Time period | Ask (month, quarter, YoY) |
| Optional | Vehicle focus (body_type, make, model, fuel_type) | Ask |

If user asks "what's happening in the market", run combined workflows as comprehensive briefing.

## Workflow: Fastest and Slowest Depreciating Models

Identify which models are losing value fastest (or holding value best) by comparing average sale prices across periods. Appraisers use this to apply trend adjustments to book-value-based estimates.

1. **Current period sold summary** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (current month), `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=50`, `state` if scoped.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

2. **Prior period sold summary** — Repeat step 1 for same month one year ago.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

3. For each make/model appearing in both periods, calculate:
   - **Price Change ($)** = Current Avg Price - Prior Avg Price
   - **Depreciation Rate (%)** = (Prior Avg Price - Current Avg Price) / Prior Avg Price x 100
   - Only include models with a minimum sold count threshold (e.g., 100+ units in both periods) for statistical reliability

4. Sort by depreciation rate descending. Present two tables:
   - **Fastest Depreciating Models (Top 15)**: Rank, Make, Model, Current Avg Price, Prior Avg Price, Price Drop ($), Depreciation Rate (%), Current Sold Count
   - **Best Value-Holding Models (Bottom 15 / lowest depreciation)**: Same columns, sorted by depreciation rate ascending

5. Add appraisal-relevant narrative: "The [Model A] lost X% of its value year-over-year, dropping from $Y to $Z on average. Appraisers valuing this model should apply a trend-down adjustment of approximately X% to book values. In contrast, [Model B] held within X% of its prior-year price — book values remain reliable for this model without trend adjustment."

6. **Active listings for top 3 depreciators** — For each, call `mcp__marketcheck__search_active_cars` with `make`, `model`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=5`, `seller_type=dealer`.
   → **Extract only**: per listing — price, miles, dealer_name, dom. Discard full response.

## Workflow: Best Deals Right Now

Find vehicles currently listed with significant price reductions that have been sitting on lots — useful for appraisers who need to identify below-market comparables and understand seller motivation in the current market.

1. **Search price-reduced inventory** — Call `mcp__marketcheck__search_active_cars` with `car_type=used`, `body_type` if scoped, `price_change=negative`, `sort_by=dom`, `sort_order=desc`, `rows=20`, `seller_type=dealer`, `zip`+`radius=100` or `state`.
   → **Extract only**: per listing — VIN, price, original_price, miles, dom, dealer_name, zip. Discard full response.

2. For each result, calculate a **Deal Score**:
   - Deal Score = (Price Drop % from original list price) x (DOM / 30)
   - Higher score = bigger discount on a unit that has been sitting longer (more motivated seller)

3. **Validate top 5 deals** — For each, call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type` from listing.
   → **Extract only**: predicted_price per VIN. Discard full response.

4. Present a **Below-Market Comparables** table:
   - Columns: Rank, Year, Make, Model, Trim, Listed Price, Original Price, Price Drop ($), Price Drop (%), DOM (days), Deal Score, Predicted Market Price, Below/Above Market ($), Dealer, Location
   - Only rank vehicles where Listed Price < Predicted Market Price as "true below-market units"

5. Appraisal narrative: "The most significant below-market listing is a [Year Make Model] at [Dealer] in [City, State], listed at $X after a $Y price reduction. It has been on the lot for Z days and is priced $W below comparable market value. Appraisers should note: vehicles with high DOM and multiple price reductions may indicate condition issues not reflected in listing data — use as lower-bound comparables with caution."

6. For appraisers specifically, add: "These below-market listings serve as lower-bound anchors for comparable analysis. When building a valuation range, distressed-price comparables should be weighted less heavily unless the subject vehicle has similar condition concerns. These price reductions also indicate downward pricing pressure in this segment — factor current market conditions when setting valuations."

## Workflow: EV vs ICE Price Parity Tracker

Track the price gap between electric and internal combustion vehicles within the same segments — critical for appraisers handling mixed-powertrain fleets or insurance claims on EVs.

1. **EV sold summary** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to`, `fuel_type_category=EV`, `body_type=SUV`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`, `state` if scoped.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

2. **ICE sold summary** — Repeat with `fuel_type_category=ICE`.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

3. Repeat steps 1-2 for additional body types: `Sedan`, `Pickup`, `Hatchback`.

4. Also repeat steps 1-2 for **Hybrid**.
   → **Extract only**: average_sale_price, sold_count per fuel_type/body_type combo. Discard full response.

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

4. Present:
   - **Regional Price Map** table: State, Avg Sale Price, vs National Avg ($), vs National Avg (%), Sold Count, Avg DOM
   - Sort by Avg Sale Price ascending (cheapest first)
   - **Summary box**: "A used [Year Range] [Make Model] averages $X nationally. The cheapest market is [State] at $Y (-Z% below national avg). The most expensive is [State] at $A (+B%). The coast-to-coast price spread is $C."

5. For appraisers specifically, add actionable guidance: "When appraising this vehicle in [expensive state], the geographic adjustment factor is +B% above national average. For insurance replacement value claims, cite the local market average of $A rather than the national average. For multi-state fleet revaluations, apply state-level adjustments to each unit's location rather than using a single national figure."

6. If year-over-year comparison was requested, repeat step 1 for the prior year and show which states saw the largest price increases or decreases.

## Workflow: New Car Markup and Discount Tracker

Identify which new car models are selling above MSRP (markup) and which require discounts — provides context for appraisers setting residual values and understanding supply-demand dynamics that affect used vehicle values.

1. **Top markups** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=20`, `state` if scoped.
   → **Extract only**: make, model, price_over_msrp_percentage, sold_count per entry. Discard full response.

2. **Deepest discounts** — Repeat with `ranking_order=asc`, `top_n=20`.
   → **Extract only**: make, model, price_over_msrp_percentage, sold_count per entry. Discard full response.

3. **Brand-level pricing power** — Call with `ranking_dimensions=make`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=20`.
   → **Extract only**: make, price_over_msrp_percentage per brand. Discard full response.

4. Present three sections:
   - **Models Commanding Premiums (Above MSRP)** table: Rank, Make, Model, Avg Price Over MSRP (%), Avg Markup ($), Sold Count, Avg DOM
     - These are supply-constrained vehicles where demand exceeds availability
   - **Models Requiring Discounts (Below MSRP)** table: Rank, Make, Model, Avg Discount Off MSRP (%), Avg Discount ($), Sold Count, Avg DOM
     - These are over-supplied or slow-demand vehicles needing incentives
   - **Brand-Level MSRP Positioning** table: Make, Avg Price vs MSRP (%), Direction (Premium/Discount), Interpretation

5. Narrative: "[Model A] commands the highest premium in the new car market at +X% over MSRP, translating to an average $Y markup. Conversely, [Model B] requires the deepest discount at -Z% off MSRP ($W off). At the brand level, [Make C] is the only mainstream brand still commanding premiums across its lineup."

6. For appraisers, add valuation context: "Models transitioning from above-MSRP to discount territory signal weakening demand — appraisers should lower residual estimates for recently purchased units of these models. Models still commanding premiums will retain value better on the secondary market. New models selling below MSRP accelerate used vehicle depreciation for the same nameplate — apply an additional trend-down adjustment to 1-3 year old used units of discounted models."

## Output

Present: appraisal-impact headline (lead with the adjustment, not methodology), data table(s) with price/volume/trend metrics and sample sizes, key market signals (depreciation velocity, regional variance, MSRP parity shifts), and actionable valuation adjustment recommendation with quantified impact. Cite data source and period.
