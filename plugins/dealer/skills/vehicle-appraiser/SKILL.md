---
name: vehicle-appraiser
description: >
  Comparable-backed vehicle valuation. Triggers: "appraise this vehicle",
  "what's it worth", "trade-in value", "comparable analysis",
  "fair market value", "wholesale vs retail", "appraisal report",
  "how much should I offer", "vehicle valuation", defensible valuations
  for trade-ins, acquisitions, or retail pricing decisions.
version: 0.1.0
---

# Vehicle Appraiser — Comparable-Backed Valuations With Transaction Evidence

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, dealer_type, radius, country, cpo_program, cpo_certification_cost. If missing, ask for ZIP and radius — skill works without profile. **US**: `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`, `search_past_90_days`, `get_car_history`. **UK**: `search_uk_active_cars`, `search_uk_recent_cars` only (no VIN decode/prediction/history — use comp median, ask user for specs). Confirm: "Using profile ZIP [ZIP] for appraisal market."

## CPO Detection & Valuation

When appraising a vehicle, determine if it is Certified Pre-Owned (CPO):

1. **From user input:** If the user states the vehicle is certified/CPO, or the "Certified pre-owned status" field (already collected) is yes.
2. **From listing data:** If the vehicle's listing has `is_certified=true`.
3. **From VIN history:** If `get_car_history` shows the vehicle currently listed as certified.

When the vehicle IS CPO, the Full Comparable Appraisal workflow adds these steps:

- **CPO predicted value:** Call `predict_price_with_comparables` with `is_certified=true` to get the certified market value.
- **Non-CPO predicted value:** Call `predict_price_with_comparables` WITHOUT `is_certified` to get the standard market value.
- **CPO retail comps:** Call `search_active_cars` with the YMMT filters PLUS `is_certified=true` to find certified-only comparables.
- **CPO premium calculation:** CPO Premium = CPO Predicted Value - Non-CPO Predicted Value

In the Valuation Summary output, add:

| Measure | Value |
|---------|-------|
| CPO Predicted Retail Value | $XX,XXX |
| Non-CPO Predicted Retail Value | $XX,XXX |
| CPO Premium | +$X,XXX (+X.X%) |
| Active CPO Comps | N within radius |
| Active Non-CPO Comps | N within radius |

For the Trade-In Quick Appraisal: if CPO, note the premium but keep the quick format. Show: "CPO Value: $XX,XXX | Standard Value: $XX,XXX | Premium: +$X,XXX"

## User Context
Dealer trade-in desk manager or GM needing a comparable-backed valuation for trade-ins, acquisitions, or retail pricing.

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or YMMT, odometer | Ask |
| Auto/Ask | ZIP, radius | Profile or ask |
| Recommended | Condition (Clean/Avg/Rough), purpose (Trade-in/Retail/Insurance/Wholesale), CPO status | Ask |

VIN provided → decode first to lock in specs (US only).

## Workflow: Full Comparable Appraisal

Use this for formal appraisals, insurance claims, or any situation where the valuation must be supported by cited comparables.

1. **Decode VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin`.
   → **Extract only**: year, make, model, trim, body_type, drivetrain, engine, transmission. Discard full response.

2. **Predict price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`, `is_certified` if applicable.
   → **Extract only**: predicted_price, comparable VINs with prices and miles. Discard full response.

3. **Pull active comps** — Call `mcp__marketcheck__search_active_cars` with YMMT from step 1, `zip`, `radius=75`, `miles_range=<odo-15k>-<odo+15k>`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=20`.
   → **Extract only**: per listing — VIN, price, miles, dealer_name, distance, dom. Discard full response.

4. **Pull sold transactions** — Call `mcp__marketcheck__search_past_90_days` with same YMMT + location filters, `sold=true`.
   → **Extract only**: per listing — VIN, sold_price, miles, dealer_name, sale_date. Discard full response.

5. **Synthesize the valuation** — Combine all three data sources:
   - **Algorithmic predicted price** from step 2 (central estimate)
   - **Active comparable range** from step 3 (current retail context)
   - **Sold transaction range** from step 4 (transaction evidence)
   - Calculate a **recommended value range** (low / mid / high) using the overlap of all three.
   - Adjust for condition if the user provided it (rough = low end of range, clean = high end).

6. **Present the appraisal report** — Deliver a structured report with the valuation, every cited comparable (VIN, price, miles, dealer, distance), methodology notes, and confidence assessment.

## Workflow: Trade-In Quick Appraisal

Use this when speed matters — the customer is at the desk and the dealer needs a number in under 60 seconds.

1. **Predict price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.
   → **Extract only**: predicted_price, top comparable VINs with prices and miles. Discard full response.

2. **Pull tight comps** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius` (from profile `default_radius_miles`, minimum 75), `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=5`.
   → **Extract only**: per listing — price, miles, dealer_name, dom, distance. Discard full response.

3. **Deliver the quick value** — Present:
   - **Predicted retail value**: from step 1
   - **Estimated trade-in value**: predicted retail minus a typical retail-to-wholesale spread (usually 15-22% below retail, adjusted by vehicle age and demand)
   - **Top 5 retail comps**: brief table showing the market context
   - **Confidence note**: indicate whether the comparable count supports a high-confidence or low-confidence estimate

## Workflow: Regional Price Variance

Use this when the user needs to understand how values differ across geographies, common for multi-state sourcing or relocation decisions.

1. **Primary market stats** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=100`, `stats=price,miles`, `rows=0`, `car_type=used`.
   → **Extract only**: mean, median, min, max, count for price and miles. Discard full response.

2. **Comparison market stats** — Repeat step 1 for each additional ZIP.
   → **Extract only**: mean, median, count per market. Discard full response.

3. **Sold summary by state** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `summary_by=state`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`.
   → **Extract only**: per state — average_sale_price, sold_count. Discard full response.

4. **Calculate regional variance** — Build a comparison table: market, median price, mean price, sample size, and delta from the lowest market. Identify arbitrage opportunities where the same vehicle sells for significantly more in one region.

5. **Present the regional map** — Show the price variance table and highlight any market where the price delta exceeds 5% — these represent real arbitrage or relocation value.

## Workflow: Wholesale vs Retail Spread

Use this when the user needs to understand the gap between wholesale and retail values, critical for trade-in offers and auction buying decisions.

1. **Predict franchise (retail) price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.
   → **Extract only**: predicted_price. Discard full response.

2. **Predict independent (wholesale-proxy) price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=independent`.
   → **Extract only**: predicted_price. Discard full response.

3. **Pull franchise listings** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=75`, `dealer_type=franchise`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=10`.
   → **Extract only**: per listing — price, miles, dealer_name; plus median. Discard full response.

4. **Pull independent listings** — Call `mcp__marketcheck__search_active_cars` with same filters, `dealer_type=independent`, `rows=10`.
   → **Extract only**: per listing — price, miles, dealer_name; plus median. Discard full response.

5. **Calculate the spread** — Present:
   - Franchise median price vs Independent median price
   - Spread in dollars and percentage
   - Predicted retail value vs predicted wholesale-proxy value
   - Recommended trade-in offer range (typically positioned between wholesale and retail, closer to wholesale)

**Note:** When the dealer profile has a `dealer_type`, highlight which price is their primary market. For franchise dealers, the franchise price is the primary retail benchmark. For independent dealers, the independent price is the primary benchmark. Always show both.

## Workflow: Historical Value Trajectory

Use this when the user asks "what has this VIN been listed at over time" or needs to understand depreciation patterns for a specific unit.

1. **Pull listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=asc`.
   → **Extract only**: per event — date, dealer_name, price, dom. Discard full response.

2. **Decode VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin`.
   → **Extract only**: year, make, model, trim. Discard full response.

3. **Build the trajectory** — From the history, extract each listing event: date, dealer, asking price, and DOM at that dealer. Calculate:
   - Total days on market across all listings
   - Total price depreciation from first listing to most recent
   - Average price drop per listing hop
   - Number of unique dealers

4. **Current market context** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`.
   → **Extract only**: predicted_price. Discard full response.

5. **Present the timeline** — Show a chronological table of all listings with price, dealer, and DOM. Highlight any unusual patterns (rapid dealer hops, price increases between dealers suggesting reconditioning, or steep drops suggesting undisclosed issues).

## Output
Present: vehicle identification line, valuation summary table (predicted value, active comp range, sold transaction range, recommended value, confidence level), active and sold comparable tables with key metrics, methodology notes, and one actionable recommendation.
