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

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Trends Reporter — Insurance Risk Assessment Intelligence

Generate actionable market trend analyses for insurance professionals — underwriters, claims managers, actuaries, and risk analysts — who need timely, data-backed intelligence on vehicle value movements that directly impact claims costs, reserve adequacy, premium pricing, and portfolio risk exposure.

## Insurer Profile (Load First)

Load `~/.claude/marketcheck/insurer-profile.json` if exists. Extract: zip, state, role, claim_types, total_loss_threshold_pct, default_comp_radius. If missing, ask for ZIP and state. US-only (`get_sold_summary`); UK not supported. Confirm profile.

## User Context

User is an insurance professional (adjuster, underwriter, claims manager, actuary) needing data-driven market intelligence for risk assessment, claims cost forecasting, and portfolio exposure analysis.

| Required | Field | Source |
|----------|-------|--------|
| Yes | Analysis question or trend | Ask |
| Auto/Ask | Geographic scope | Profile state or ask (default: national) |
| Auto/Ask | Time period | Ask (month, quarter, YoY) |
| Optional | Vehicle focus (body_type, make, model, fuel_type) | Ask |

If user asks "what's happening in the market", run combined workflows as comprehensive insurance risk briefing.

## Workflow: Fastest and Slowest Depreciating Models (Total-Loss Risk Assessment)

Identify which models are losing value fastest (highest total-loss claim risk) and which are holding value best (lowest total-loss risk) by comparing average sale prices across periods.

1. **Current period sold summary** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (current month), `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=50`, `state` if scoped.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

2. **Prior period sold summary** — Repeat step 1 for same month one year ago.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

3. For each make/model appearing in both periods, calculate:
   - **Price Change ($)** = Current Avg Price - Prior Avg Price
   - **Depreciation Rate (%)** = (Prior Avg Price - Current Avg Price) / Prior Avg Price x 100
   - **Total-Loss Risk Score** = Depreciation Rate x (1 + volume weight) — models with high depreciation AND high insured volume represent the greatest claims exposure
   - Only include models with a minimum sold count threshold (e.g., 100+ units in both periods) for statistical reliability

4. Sort by depreciation rate descending. Present two tables:
   - **Highest Total-Loss Risk Models (Top 15)**: Rank, Make, Model, Current Avg Price, Prior Avg Price, Price Drop ($), Depreciation Rate (%), Current Sold Count, Risk Score
   - **Lowest Total-Loss Risk Models (Bottom 15 / strongest value retention)**: Same columns, sorted by depreciation rate ascending

5. Add insurance context: "The [Model A] lost X% of its value year-over-year, dropping from $Y to $Z on average. Insured vehicles of this model are approaching total-loss thresholds faster — a vehicle insured at $Y that now has an FMV of $Z is a total loss if repair costs exceed $W (75% of current FMV). In contrast, [Model B] held within X% of its prior-year price, maintaining strong value and low total-loss risk."

6. **Active listings for top 3 depreciators** — For each, call `mcp__marketcheck__search_active_cars` with `make`, `model`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=5`, `seller_type=dealer`.
   → **Extract only**: per listing — price, miles, dealer_name, dom. Discard full response.

## Workflow: Claims Cost Trend Analysis

Track how average replacement costs are moving for commonly insured vehicle segments — critical for reserve adequacy and premium pricing.

1. **Active inventory by segment** — Call `mcp__marketcheck__search_active_cars` with `car_type=used`, `body_type` if scoped, `sort_by=dom`, `sort_order=desc`, `rows=20`, `seller_type=dealer`, `zip`+`radius=100` or `state`, `stats=price`.
   → **Extract only**: per listing — VIN, price, miles, dom, dealer_name; plus price stats (mean/median). Discard full response.

2. **Sold summary by model** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `inventory_type=Used`, `body_type` if scoped, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=20`.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

3. **Validate replacement cost** — For top 10 models by volume, call `mcp__marketcheck__predict_price_with_comparables` with representative `vin`, `miles`, `zip`, `dealer_type=franchise`.
   → **Extract only**: predicted_price per VIN. Discard full response.

4. Present a **Claims Cost Benchmark** table:
   - Columns: Rank, Make, Model, Avg Transaction Price, Active Listing Median, Predicted Market Value, Avg DOM, Volume, Replacement Cost Trend (Rising/Falling/Stable)
   - Highlight models where replacement cost is rising (reserve pressure) vs falling (reserve release opportunity)

5. Insurance narrative: "Replacement costs for [segment] are [rising/falling] — the average transaction price moved from $X to $Y over the past [period]. This [increases/decreases] total-loss claim severity by an estimated $Z per claim. Claims managers should [adjust reserves upward/consider reserve releases] for this segment."

## Workflow: EV vs ICE Claims Exposure Tracker

Track the price gap between electric and internal combustion vehicles — critical for understanding differential depreciation risk in insured EV portfolios.

1. **EV sold summary** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to`, `fuel_type_category=EV`, `body_type=SUV`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`, `state` if scoped.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

2. **ICE sold summary** — Repeat with `fuel_type_category=ICE`.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

3. Repeat steps 1-2 for additional body types: `Sedan`, `Pickup`, `Hatchback`.

4. Also repeat steps 1-2 for **Hybrid**.
   → **Extract only**: average_sale_price, sold_count per fuel_type/body_type combo. Discard full response.

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

1. **Sold summary by state** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `make`, `model` (optional), `inventory_type=Used`, `summary_by=state`, `limit=51`.
   → **Extract only**: per state — average_sale_price, sold_count. Discard full response.

2. From the results, calculate:
   - **National average replacement cost** (weighted by volume)
   - **Cheapest 5 states** by average sale price (lowest claims severity)
   - **Most expensive 5 states** by average sale price (highest claims severity)
   - **Claims cost spread** = Most Expensive State Avg - Cheapest State Avg
   - **Claims cost spread %** = Spread / National Avg x 100

3. **Volume check** — Call `mcp__marketcheck__get_sold_summary` for most expensive state with `state`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `top_n=1`.
   → **Extract only**: sold_count. Discard full response.

4. Present:
   - **Regional Claims Cost Map** table: State, Avg Replacement Cost, vs National Avg ($), vs National Avg (%), Volume, Claims Cost Risk (High/Medium/Low)
   - Sort by Avg Sale Price descending (highest claims cost first)
   - **Risk summary**: "A total-loss claim on a used [Year Range] [Make Model] averages $X nationally. Claims in [State] cost $Y (+Z% above national avg) — the most expensive market. Claims in [State] cost $A (-B% below national avg) — the lowest cost market. The state-to-state claims cost spread is $C."

5. For underwriting, add: "Premium pricing should reflect regional replacement cost variance. Policyholders in [expensive state] face replacement costs Z% above national average — collision and comprehensive premiums should be calibrated accordingly."

6. If year-over-year comparison was requested, repeat step 1 for the prior year and show which states saw the largest replacement cost increases or decreases. Flag states where costs rose more than 5% as requiring reserve review.

## Workflow: New Car Replacement Cost Monitor

Identify which new car models are selling above MSRP (elevated replacement cost for new-vehicle total-loss claims) and which are discounted — directly impacts settlement calculations for vehicles under 1 year old.

1. **Top markups** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=20`, `state` if scoped.
   → **Extract only**: make, model, price_over_msrp_percentage, sold_count per entry. Discard full response.

2. **Deepest discounts** — Repeat with `ranking_order=asc`, `top_n=20`.
   → **Extract only**: make, model, price_over_msrp_percentage, sold_count per entry. Discard full response.

3. **Brand-level pricing power** — Call with `ranking_dimensions=make`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=20`.
   → **Extract only**: make, price_over_msrp_percentage per brand. Discard full response.

4. Present three sections:
   - **Elevated Replacement Cost Models (Above MSRP)** table: Rank, Make, Model, Avg Price Over MSRP (%), Avg Markup ($), Sold Count, Avg DOM
     - These vehicles cost more to replace than MSRP suggests — total-loss settlements at MSRP will leave the claimant unable to purchase a replacement
   - **Favorable Replacement Cost Models (Below MSRP)** table: Rank, Make, Model, Avg Discount Off MSRP (%), Avg Discount ($), Sold Count, Avg DOM
     - These vehicles can be replaced below MSRP — settlement at MSRP may overcompensate
   - **Brand-Level Replacement Cost Positioning** table: Make, Avg Price vs MSRP (%), Direction (Premium/Discount), Claims Implication

5. Insurance narrative: "[Model A] commands the highest premium at +X% over MSRP, translating to an average $Y above sticker. A total-loss claim on a new [Model A] settled at MSRP would leave the claimant $Y short of actual replacement cost — a potential bad-faith exposure. Conversely, [Model B] sells at -Z% off MSRP, meaning settlements at MSRP may overcompensate by $W."

6. For prior-period comparison, repeat calls and show trend: "Replacement costs on [Model] have decreased from +X% over MSRP to +Y%, reducing the above-MSRP claims exposure by $Z per unit." Also add: "Models transitioning from premium to discount territory this month: [list] — standard MSRP-based settlements are now adequate for these models."

## Output

Present: risk-signal headline (lead with the insurance impact, not methodology), data table(s) with price/volume/trend metrics and sample sizes, key claims and underwriting signals (total-loss risk, EV exposure, regional variance, replacement cost shifts), and role-specific actionable recommendation with quantified business impact. Cite data source and period.
