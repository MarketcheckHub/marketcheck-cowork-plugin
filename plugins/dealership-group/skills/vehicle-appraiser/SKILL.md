---
name: vehicle-appraiser
description: >
  This skill should be used when the user asks to "appraise this vehicle",
  "what's it worth", "trade-in value", "comparable analysis",
  "fair market value", "wholesale vs retail", "appraisal report",
  "how much should I offer", "vehicle valuation", or needs help with
  building a defensible, comparable-backed vehicle valuation for trade-ins,
  acquisitions, or retail pricing decisions.
version: 0.1.0
---

# Vehicle Appraiser — Comparable-Backed Valuations With Transaction Evidence

## Dealer Group Profile (Load First — Optional)

Before running any workflow, check for a saved dealer group profile:

1. Read `~/.claude/marketcheck/dealership-group-profile.json`.
2. If the file **exists**, determine which location to use:
   - Use `dealer_group.locations[dealer_group.default_location_index]` as the default location
   - If the user specifies a location name, find the matching location from `dealer_group.locations[]`
   - Extract from the selected location:
     - `zip` ← location's `zip`
     - `dealer_type` ← location's `dealer_type`
   - Extract from profile:
     - `radius` ← `preferences.default_radius_miles`
     - `country` ← `location.country`
     - `cpo_program` ← `dealer_group.cpo_program`
     - `cpo_certification_cost` ← `dealer_group.cpo_certification_cost`
3. If the file **does not exist**, ask for ZIP and radius as before — this skill works fine without a profile.
4. **Tool routing by country:**
   - **US**: All tools — `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`, `search_past_90_days`, `get_car_history`
   - **UK**: `search_uk_active_cars`, `search_uk_recent_cars` only. VIN decode, price prediction, and car history are **not available**. Use comp median for valuation, ask user for specs instead of VIN decode, and skip listing history steps.
5. If profile exists, confirm briefly: "Using location ZIP **[ZIP]** for appraisal market."

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

The primary user is a **dealer group manager** or **trade-in desk manager** at one of the group's locations who needs a defensible valuation backed by specific comparable vehicles and transaction data.

The following fields are loaded from the dealer group profile if available. Otherwise, ask:

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or Year/Make/Model/Trim | Always ask (vehicle-specific) |
| Yes | Current odometer reading | Always ask (vehicle-specific) |
| Auto/Ask | ZIP code of appraisal market | Profile location's `zip` or ask |
| Recommended | Vehicle condition | Always ask (`Clean`, `Average`, `Rough`) |
| Recommended | Purpose of appraisal | Always ask (`Trade-in`, `Retail`, `Insurance`, `Wholesale`) |
| Optional | Certified pre-owned status | Always ask |
| Auto/Ask | Search radius | Profile `preferences.default_radius_miles` or `50` default |

Always decode the VIN first to lock in exact specs (US only). Appraisals built on assumed trim levels lose credibility.

## Workflow: Full Comparable Appraisal

Use this for formal appraisals, insurance claims, or any situation where the valuation must be supported by cited comparables.

1. **Decode the VIN for exact specs** — Call `mcp__marketcheck__decode_vin_neovin` with `vin`. Confirm year, make, model, trim, body type, drivetrain, engine displacement, transmission, and key options. These specs define the comparable search criteria.

2. **Get the algorithmic market value** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles` (actual odometer), `zip`, `dealer_type=franchise` (for retail value), and `is_certified` if applicable. Record the predicted price and all returned comparable VINs with their prices and miles.

3. **Pull active retail comparables** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from step 1), `zip`, `radius=75`, `miles_range=<odometer-15000>-<odometer+15000>`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=20`. These are currently available competing units that establish the retail market.

4. **Pull sold/expired transaction evidence** — Call `mcp__marketcheck__search_past_90_days` with the same YMMT and location filters, plus `sold=true`. These are actual transactions that prove what buyers have recently paid. This is the strongest evidence in any appraisal.

5. **Synthesize the valuation** — Combine all three data sources:
   - **Algorithmic predicted price** from step 2 (central estimate)
   - **Active comparable range** from step 3 (current retail context)
   - **Sold transaction range** from step 4 (transaction evidence)
   - Calculate a **recommended value range** (low / mid / high) using the overlap of all three.
   - Adjust for condition if the user provided it (rough = low end of range, clean = high end).

6. **Present the appraisal report** — Deliver a structured report with the valuation, every cited comparable (VIN, price, miles, dealer, distance), methodology notes, and confidence assessment.

## Workflow: Trade-In Quick Appraisal

Use this when speed matters — the customer is at the desk and the dealer needs a number in under 60 seconds.

1. **Get predicted value immediately** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`. This returns the market value and top comparables in a single call.

2. **Pull a tight comparable set** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim`, `zip`, `radius=50`, `sort_by=price`, `sort_order=asc`, `rows=5`, `car_type=used`. These are the top 5 closest-priced competing units.

3. **Deliver the quick value** — Present:
   - **Predicted retail value**: from step 1
   - **Estimated trade-in value**: predicted retail minus a typical retail-to-wholesale spread (usually 15-22% below retail, adjusted by vehicle age and demand)
   - **Top 5 retail comps**: brief table showing the market context
   - **Confidence note**: indicate whether the comparable count supports a high-confidence or low-confidence estimate

## Workflow: Regional Price Variance

Use this when the user needs to understand how values differ across geographies, common for multi-state dealer groups or relocation decisions.

1. **Pull price stats for the primary market** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip` (primary market), `radius=100`, `stats=price,miles`, `rows=0`, `car_type=used`.

2. **Pull price stats for comparison markets** — Repeat step 1 for each additional ZIP code the user wants to compare (e.g., `10001` for NYC, `90210` for LA, `77001` for Houston).

3. **Pull sold summary by state** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `summary_by=state`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`. This shows which states command the highest average sale prices.

4. **Calculate regional variance** — Build a comparison table: market, median price, mean price, sample size, and delta from the lowest market. Identify arbitrage opportunities where the same vehicle sells for significantly more in one region.

5. **Present the regional map** — Show the price variance table and highlight any market where the price delta exceeds 5% — these represent real arbitrage or relocation value.

## Workflow: Wholesale vs Retail Spread

Use this when the user needs to understand the gap between wholesale and retail values, critical for trade-in offers and auction buying decisions.

1. **Get franchise (retail) predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.

2. **Get independent (wholesale-proxy) predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=independent`.

3. **Pull franchise dealer listings** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=75`, `dealer_type=franchise`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used`.

4. **Pull independent dealer listings** — Call `mcp__marketcheck__search_active_cars` with the same filters but `dealer_type=independent`, `rows=10`.

5. **Calculate the spread** — Present:
   - Franchise median price vs Independent median price
   - Spread in dollars and percentage
   - Predicted retail value vs predicted wholesale-proxy value
   - Recommended trade-in offer range (typically positioned between wholesale and retail, closer to wholesale)

**Note:** When the location has a `dealer_type`, highlight which price is their primary market. For franchise locations, the franchise price is the primary retail benchmark. For independent locations, the independent price is the primary benchmark. Always show both.

## Workflow: Historical Value Trajectory

Use this when the user asks "what has this VIN been listed at over time" or needs to understand depreciation patterns for a specific unit.

1. **Pull the full listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=asc` to get chronological listing data across all dealers.

2. **Decode the VIN for baseline specs** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to anchor the timeline with exact vehicle specs.

3. **Build the trajectory** — From the history, extract each listing event: date, dealer, asking price, and DOM at that dealer. Calculate:
   - Total days on market across all listings
   - Total price depreciation from first listing to most recent
   - Average price drop per listing hop
   - Number of unique dealers

4. **Contextualize with current market** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip` to get today's predicted value. Compare to the trajectory endpoint.

5. **Present the timeline** — Show a chronological table of all listings with price, dealer, and DOM. Highlight any unusual patterns (rapid dealer hops, price increases between dealers suggesting reconditioning, or steep drops suggesting undisclosed issues).

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Comparable Count Within Radius | Number of active + sold comps found within the search radius | Fewer than 5 comps = low confidence, flag for manual review; 15+ comps = high confidence valuation |
| Retail-to-Wholesale Spread | Dollar and percentage gap between franchise and independent predicted prices | Typical spread is 15-22%; spreads above 25% suggest strong retail demand; below 12% suggest commoditized segment |
| Regional Price Variance | Standard deviation of median prices across compared markets | Variance above 8% signals arbitrage opportunity or relocation value for the seller |
| Historical Depreciation Rate | Price decline per month from first listing to current value | Rates above 2% per month indicate rapid depreciation; below 0.5% per month signals strong value retention |
| Valuation Confidence Score | Composite of comparable count, spread tightness, and data recency | Present as High / Medium / Low; refuse to give a point estimate on Low confidence — give a range instead |

## Action-to-Outcome Funnel

1. **High-confidence appraisal (15+ comps, tight spread)** — Deliver a point estimate with a narrow range (+/- 3%). The dealer can quote with confidence. Cite the 3 closest comparables by VIN.

2. **Medium-confidence appraisal (5-14 comps, moderate spread)** — Deliver a range (low to high) with the midpoint as the recommended value. Note which data source (active, sold, predicted) most heavily influenced the range. Recommend the user inspect condition carefully as it will determine where in the range the vehicle falls.

3. **Low-confidence appraisal (< 5 comps)** — Do not give a point estimate. Deliver a wide range and explicitly state the confidence is low. Recommend broadening the radius, relaxing the trim filter, or waiting for more transaction data. Suggest the user consider a physical auction check or third-party inspection.

4. **Trade-in where customer expects retail value** — Show the wholesale-to-retail spread with specific comparables. The sold transaction data from the past 90 days is the strongest tool for resetting customer expectations — these are real prices real buyers paid.

5. **Insurance total-loss claim** — Use the Full Comparable Appraisal workflow with the widest defensible radius. Emphasize sold transaction evidence over active listings. Present every comparable with full detail — adjusters need to see the work.

## Output Format

Always present results in this structure:

**Vehicle Identification**
- VIN: `5YJ3E1EA8PF123456`
- Year / Make / Model / Trim: `2023 Tesla Model 3 Long Range`
- Body: Sedan | Drivetrain: AWD | Engine: Electric | Transmission: Single-Speed
- Odometer: 28,400 miles

**Valuation Summary**
| Measure | Value |
|---------|-------|
| Predicted Retail Value | $35,200 |
| Active Comp Range (25th-75th pctl) | $33,800 — $37,100 |
| Sold Transaction Range (90 days) | $32,500 — $36,400 |
| Recommended Value (condition-adjusted) | $34,500 — $35,800 |
| Confidence | High (18 active comps, 7 sold comps) |

**Active Retail Comparables** — Table with columns: VIN (last 6) | Year | Trim | Miles | Price | Dealer | Distance | DOM

**Sold Transaction Comparables** — Table with columns: VIN (last 6) | Year | Trim | Miles | Sold Price | Dealer | Sale Date

**Methodology Notes** — Brief explanation of how the three data sources were weighted and any condition adjustments applied.

**Caveats** — Any factors that could not be accounted for (accident history, aftermarket modifications, regional demand anomalies).
