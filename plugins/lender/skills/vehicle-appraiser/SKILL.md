---
name: vehicle-appraiser
description: >
  This skill should be used when the user asks to "appraise this vehicle",
  "what's it worth", "collateral value", "comparable analysis",
  "fair market value", "wholesale vs retail", "collateral valuation report",
  "LTV calculation", "vehicle valuation", "loan collateral check",
  or needs help with building a defensible, comparable-backed vehicle valuation
  for collateral assessment, portfolio revaluation, or loan origination decisions.
version: 0.1.0
---

# Vehicle Appraiser — Collateral Valuation With Transaction Evidence

## Lender Profile (Load First)

Load `~/.claude/marketcheck/lender-profile.json` if exists. Extract: `zip`/`postcode`, `default_radius_miles`, `country`, `risk_ltv_threshold`, `high_risk_ltv_threshold`, `portfolio_focus`. If missing, ask for ZIP and radius. US: all tools available. UK: `search_uk_active_cars`, `search_uk_recent_cars` only. Confirm profile.

## User Context

Lender (residual analyst, portfolio risk manager, auto finance director) needing defensible collateral valuations backed by comparables and transaction data for loan origination, portfolio revaluation, or loss mitigation. Also serves floor plan auditors.

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or Year/Make/Model/Trim | Ask |
| Yes | Odometer reading | Ask |
| Auto/Ask | ZIP code | Profile or ask |
| Recommended | Condition | Ask (`Clean`/`Average`/`Rough`) |
| Recommended | Purpose | Ask (`Origination`/`Revalue`/`Loss Mitigation`/`Floor Plan`) |
| Optional | Loan amount (LTV calc) | Ask |
| Auto/Ask | Search radius | Profile or `100` default |

Decode VIN first (US only) to lock exact specs.

## Workflow: Full Collateral Valuation

Use this for loan origination, portfolio revaluation, or any situation where the valuation must be supported by cited comparables.

1. **Decode VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin`.
   → **Extract only**: year, make, model, trim, body_type, drivetrain, engine, transmission, msrp. Discard full response.

2. **Predict price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.
   → **Extract only**: predicted_price, comparable VINs with prices and miles. Discard full response.

3. **Pull active comps** — Call `mcp__marketcheck__search_active_cars` with YMMT from step 1, `zip`, `radius=75`, `miles_range=<odo-15k>-<odo+15k>`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=20`.
   → **Extract only**: per listing — VIN, price, miles, dealer_name, distance, dom. Discard full response.

4. **Pull sold transactions** — Call `mcp__marketcheck__search_past_90_days` with same YMMT + location filters, `sold=true`.
   → **Extract only**: per listing — VIN, sold_price, miles, dealer_name, sale_date. Discard full response.

5. **Synthesize the collateral valuation** — Combine all three data sources:
   - **Algorithmic predicted price** from step 2 (central estimate)
   - **Active comparable range** from step 3 (current retail context)
   - **Sold transaction range** from step 4 (transaction evidence)
   - Calculate a **collateral value range** (low / mid / high) using the overlap of all three.
   - Adjust for condition if the user provided it (rough = low end of range, clean = high end).

6. **Calculate LTV if loan amount provided** — If the user provided a loan amount:
   - **LTV** = loan amount / collateral midpoint value x 100
   - Flag: LTV > risk_ltv_threshold (default 100%) = "UNDERWATER — collateral does not cover loan balance"
   - Flag: LTV > high_risk_ltv_threshold (default 120%) = "HIGH RISK — significant negative equity"
   - Project: At the current segment depreciation rate, when will LTV reach 100% and 120%?

7. **Present the collateral valuation report** — Deliver a structured report with the valuation, every cited comparable (VIN, price, miles, dealer, distance), methodology notes, LTV analysis, and confidence assessment.

## Workflow: Quick Collateral Check

Use this when speed matters — a loan officer needs a collateral value for a quick origination decision.

1. **Predict price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.
   → **Extract only**: predicted_price, top comparable VINs with prices and miles. Discard full response.

2. **Pull tight comps** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=50`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=5`.
   → **Extract only**: per listing — VIN, price, miles, dealer_name, distance. Discard full response.

3. **Deliver the quick collateral value** — Present:
   - **Predicted retail value**: from step 1
   - **Estimated wholesale value**: predicted retail minus a typical retail-to-wholesale spread (usually 15-22% below retail, adjusted by vehicle age and demand)
   - **LTV calculation**: if loan amount provided, calculate LTV against both retail and wholesale values
   - **Top 5 retail comps**: brief table showing the market context
   - **Confidence note**: indicate whether the comparable count supports a high-confidence or low-confidence estimate
   - **Risk flag**: if LTV exceeds threshold, prominently flag the risk level

## Workflow: Regional Collateral Variance

Use this when the lender needs to understand how collateral values differ across geographies, common for multi-state portfolio management or understanding regional LTV exposure.

1. **Primary market stats** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=100`, `stats=price,miles`, `rows=0`, `car_type=used`.
   → **Extract only**: mean, median, min, max, count for price and miles. Discard full response.

2. **Comparison market stats** — Repeat step 1 for each additional ZIP.
   → **Extract only**: mean, median, count per market. Discard full response.

3. **Sold summary by state** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `summary_by=state`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`.
   → **Extract only**: per state — average_sale_price, sold_count. Discard full response.

4. **Calculate regional variance and LTV impact** — Build a comparison table: market, median price, mean price, sample size, and delta from the lowest market. For each region, calculate what the LTV would be on a standard loan amount. Identify regions where the same loan would be underwater vs. adequately covered.

5. **Present the regional collateral map** — Show the price variance table and highlight any market where the price delta exceeds 5% — these represent regions where collateral value assumptions need adjustment. Include LTV impact per region.

## Workflow: Wholesale vs Retail Spread

Use this when the lender needs to understand the gap between wholesale and retail values, critical for loss mitigation and recovery estimates.

1. **Predict franchise (retail) price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.
   → **Extract only**: predicted_price. Discard full response.

2. **Predict independent (wholesale-proxy) price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=independent`.
   → **Extract only**: predicted_price. Discard full response.

3. **Pull franchise listings** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=75`, `dealer_type=franchise`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=10`.
   → **Extract only**: per listing — price, miles, dealer_name; plus median. Discard full response.

4. **Pull independent listings** — Call `mcp__marketcheck__search_active_cars` with same filters, `dealer_type=independent`, `rows=10`.
   → **Extract only**: per listing — price, miles, dealer_name; plus median. Discard full response.

5. **Calculate the spread and recovery implications** — Present:
   - Franchise median price vs Independent median price
   - Spread in dollars and percentage
   - Predicted retail value vs predicted wholesale-proxy value
   - **Recovery estimate**: In a repo/liquidation scenario, expect to recover the wholesale value minus remarketing costs (typically $1,500-2,500)
   - **Deficiency exposure**: If loan balance exceeds wholesale recovery, calculate the expected deficiency

## Workflow: Historical Value Trajectory

Use this when the user asks "what has this VIN been listed at over time" or needs to understand depreciation patterns for a specific collateral unit.

1. **Pull listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=asc`.
   → **Extract only**: per event — date, dealer_name, price, dom. Discard full response.

2. **Decode VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin`.
   → **Extract only**: year, make, model, trim, msrp. Discard full response.

3. **Build the trajectory** — From the history, extract each listing event: date, dealer, asking price, and DOM at that dealer. Calculate:
   - Total days on market across all listings
   - Total price depreciation from first listing to most recent
   - Average price drop per listing hop
   - Number of unique dealers

4. **Current market context** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`.
   → **Extract only**: predicted_price. Discard full response.

5. **Present the timeline with collateral implications** — Show a chronological table of all listings with price, dealer, and DOM. Highlight any unusual patterns (rapid dealer hops suggesting distressed sale, price increases between dealers suggesting reconditioning, or steep drops suggesting undisclosed issues). Flag: "Vehicles with extended market exposure (>90 days total DOM) or multiple dealer hops typically command lower values — apply a 3-5% haircut to collateral value."

## Output

Present: vehicle identification and specs, collateral valuation summary table (retail/wholesale/comp range/confidence), LTV analysis if loan amount provided, cited comparable tables (active + sold), and actionable risk recommendation.
