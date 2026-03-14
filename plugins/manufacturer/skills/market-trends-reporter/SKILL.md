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

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Trends Reporter — Competitive Landscape & Market Dynamics Intelligence

Generate competitive landscape analyses, segment pricing intelligence, and data-driven market dynamics reports. Purpose-built for OEM strategists, product planners, brand managers, and regional distributors who need timely, defensible data narratives to inform brand positioning and competitive response.

## Manufacturer Profile (Load First)

Load `~/.claude/marketcheck/manufacturer-profile.json` if exists. Extract: `brands` (star in results), `states`, `competitor_brands`, `country`, `user_name`, `company`. If missing, ask brand and competitors. US-only (requires `get_sold_summary`); if UK, inform not available. Confirm profile.

## User Context

User is an OEM strategist, product planner, or brand manager investigating competitive landscape, pricing dynamics, or market trends for brand positioning and competitive response.

| Field | Source |
|-------|--------|
| Story angle | What trend or competitive question to investigate |
| Geographic scope | Profile `manufacturer.states` or national (default) |
| Time period | Current month, trailing quarter, or YoY |
| Vehicle focus | Optional: body_type, make, model, fuel_type_category |
| Competitive context | Profile brands vs competitor brands |

If user asks "what's happening in the market", run combined workflows as a comprehensive competitive briefing.

## Workflow: Fastest and Slowest Depreciating Models

Identify which models are losing value fastest (or holding value best) — highlight your brand's models and competitor models throughout.

1. **Current period sold summary** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (current month), `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=50`, `state` if scoped.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

2. **Prior period sold summary** — Repeat step 1 for same month one year ago.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

3. For each make/model appearing in both periods, calculate:
   - **Price Change ($)** = Current Avg Price - Prior Avg Price
   - **Depreciation Rate (%)** = (Prior Avg Price - Current Avg Price) / Prior Avg Price x 100
   - Only include models with a minimum sold count threshold (e.g., 100+ units in both periods)

4. Sort by depreciation rate descending. Present two tables:
   - **Fastest Depreciating Models (Top 15)**: Rank, Make, Model, Current Avg Price, Prior Avg Price, Price Drop ($), Depreciation Rate (%), Current Sold Count — mark your models with a star and competitor models
   - **Best Value-Holding Models (Bottom 15 / lowest depreciation)**: Same columns, sorted ascending

5. Add competitive narrative: "Among your brand's models, [Model A] lost X% of its value year-over-year — the [Nth] steepest in the market. Competitor [Brand]'s [Model B] held within Y%, outperforming your equivalent by $Z per unit. [Model C] from your lineup is among the strongest value holders, retaining X% — use this in marketing and CPO positioning."

6. **Active listings for top 3 depreciators (your brand)** — For each, call `mcp__marketcheck__search_active_cars` with `make`, `model`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=5`, `seller_type=dealer`.
   → **Extract only**: per listing — price, miles, dealer_name, city, state. Discard full response.

## Workflow: EV vs ICE Price Parity Tracker

Track the price gap between electric and internal combustion vehicles within the same segments — essential for OEM electrification strategy and pricing decisions.

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
   - **Your brand's EV price** vs market EV average in each segment

7. Present:
   - **Price Parity Tracker** table: Body Type, EV Avg Price, ICE Avg Price, Hybrid Avg Price, EV-ICE Gap ($), EV-ICE Gap (%), YoY Gap Change, Parity Trend (Narrowing/Widening/Stable)
   - **Top EV Models by Segment** table — highlight your models and competitor models
   - **Strategic parity narrative**: "In the SUV segment, the EV-to-ICE price gap is $X,XXX (Y%), [down/up] from $A,AAA (B%) a year ago. Your brand's EV SUV averages $Z,ZZZ — [above/below] the EV segment average. Competitor [Brand]'s EV is priced at $W,WWW. At the current rate of convergence, price parity in [segment] could be reached by [estimated quarter/year] — plan production ramps accordingly."

## Workflow: Regional Price Variance — Competitive Geography

Reveal where your brand is priced highest and lowest across states, and how you compare to competitors in each region.

1. **Sold summary by state (your brand)** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `make` (your brand), `model` (optional), `inventory_type=Used`, `summary_by=state`, `limit=51`.
   → **Extract only**: per state — average_sale_price, sold_count. Discard full response.

2. **Competitor sold summary by state** — Repeat step 1 for each competitor brand.
   → **Extract only**: per state — average_sale_price, sold_count. Discard full response.

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

1. **Top markups** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=20`, `state` if scoped.
   → **Extract only**: make, model, price_over_msrp_percentage, sold_count per entry. Discard full response.

2. **Deepest discounts** — Repeat with `ranking_order=asc`, `top_n=20`.
   → **Extract only**: make, model, price_over_msrp_percentage, sold_count per entry. Discard full response.

3. **Brand-level pricing power** — Call with `ranking_dimensions=make`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=20`.
   → **Extract only**: make, price_over_msrp_percentage per brand. Discard full response.

4. Present three sections:
   - **Models Commanding Premiums (Above MSRP)** — mark your models with star, highlight competitors
   - **Models Requiring Discounts (Below MSRP)** — same marking
   - **Brand-Level MSRP Positioning** table: Make, Avg Price vs MSRP (%), Direction — your brands vs competitors

5. Competitive narrative: "Your [Model A] commands +X% premium (#Y in market), while competitor [Brand]'s [Model B] is at +Z%. In the discount category, your [Model C] requires -W% discount vs competitor [Model D] at -V%. At the brand level, your brand averages [premium/discount] of X.X% vs competitor's Y.Y%."

6. Strategic advice: "Your premium models should have production protected. Discount models may need production cuts or targeted incentives. Models transitioning from premium to discount this month: [list] — monitor closely."

## Output

Present: competitive insight headline (lead with finding, not methodology), data tables with star on your brands (always include sold count with price metrics), competitive comparison anchors, and strategic recommendations (production, incentives, allocation, competitive response). Cite data source and period.
