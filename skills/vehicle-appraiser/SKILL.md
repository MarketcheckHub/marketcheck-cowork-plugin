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

## Dealer Profile (Load First — Optional)

→ Full procedure: read `_references/profile-loading.md`

Parse `marketcheck-profile.md` if it exists → extract: `zip`/`postcode`, `dealer_type`, `radius`, `country`, `cpo_program`, `cpo_certification_cost`, `user_type`. This skill works fine without a profile — ask for ZIP and radius if missing.

**Country routing:** US = all tools. UK = `search_uk_active_cars` / `search_uk_recent_cars` only — no VIN decode, no prediction, no car history, no sold summary. Use comp median for valuation. → Full matrix: `_references/country-routing.md`

Confirm: "Using profile ZIP **[ZIP/Postcode]** for appraisal market."

## CPO Detection & Valuation

→ Full procedure: read `_references/cpo-detection.md`

If vehicle is CPO: call `predict_price_with_comparables` with and without `is_certified=true`. Search comps with `is_certified=true` for CPO-specific comparables. Calculate CPO premium. For Trade-In Quick Appraisal, show: "CPO Value: $XX,XXX | Standard Value: $XX,XXX | Premium: +$X,XXX"

## User Context

The primary user is an **appraiser** (independent appraiser, insurance adjuster, or fleet valuation analyst) who needs a defensible valuation backed by specific comparable vehicles and transaction data. The secondary user is a **dealer trade-in desk manager** who needs a quick but credible number to present to a customer sitting across the desk.

The following fields are loaded from the dealer profile if available. Otherwise, ask:

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or Year/Make/Model/Trim | Always ask (vehicle-specific) |
| Yes | Current odometer reading | Always ask (vehicle-specific) |
| Auto/Ask | ZIP code of appraisal market | Dealer profile `location.zip` or ask |
| Recommended | Vehicle condition | Always ask (`Clean`, `Average`, `Rough`) |
| Recommended | Purpose of appraisal | Always ask (`Trade-in`, `Retail`, `Insurance`, `Wholesale`) |
| Optional | Certified pre-owned status | Always ask |
| Auto/Ask | Search radius | Dealer profile `preferences.default_radius_miles` or `50` default |

Always decode the VIN first to lock in exact specs (US only). Appraisals built on assumed trim levels lose credibility.

## Gotchas

- **UK: no VIN decode, no ML prediction, no sold summary, no car history** — for UK appraisals, ask user for specs directly, use comp median from `search_uk_active_cars` for valuation, and skip listing history steps entirely.
- **CPO requires dual pricing calls** — call `predict_price_with_comparables` with and without `is_certified=true` to get separate CPO and non-CPO values. The CPO premium is the difference.
- **Confidence score is tied to comparable count** — fewer than 5 comps = Low confidence (give a range, not a point estimate); 5-14 = Medium; 15+ = High. Never give a point estimate on Low confidence.
- **Retail-to-wholesale spread is typically 15-22%** — spreads above 25% suggest strong retail demand; below 12% suggests a commoditized segment. This is an industry rule-of-thumb, not a formula.
- **`search_past_90_days` with `sold=true` provides actual transaction evidence** — this is the strongest data source for any appraisal, stronger than active listings or predicted prices.

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

Use this when the user needs to understand how values differ across geographies, common for fleet valuations, multi-state dealer groups, or relocation decisions.

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

**Note:** When the user's profile has a `dealer_type`, highlight which price is their primary market. For franchise dealers, the franchise price is the primary retail benchmark. For independent dealers, the independent price is the primary benchmark. Always show both.

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

## KPIs & Business Impact

→ After assembling results, read `references/outcomes.md` to frame recommendations with quantified business impact, KPI benchmarks, and action-to-outcome guidance.

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

## Self-Check (before presenting to user)

- [ ] Confidence level (High/Medium/Low) matches comparable count (15+/5-14/<5)
- [ ] Low-confidence appraisals give a RANGE, not a point estimate
- [ ] All cited comparables include VIN (last 6), price, miles, dealer, distance
- [ ] Sold transaction evidence prioritized over active listings in methodology
- [ ] Condition adjustment noted if user provided condition rating
- [ ] CPO and non-CPO values shown separately if vehicle is certified
