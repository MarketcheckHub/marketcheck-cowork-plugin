---
name: competitive-pricer
description: >
  This skill should be used when the user asks to "price this car",
  "market price for this", "compare pricing", "price check VIN",
  "what's the market on this", or needs help with market pricing context,
  price positioning analysis, or understanding where a vehicle falls
  in the current competitive landscape for appraisal purposes.
version: 0.1.0
---

# Competitive Pricer — Market Price Context for Appraisals

## Appraiser Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, specialization, radius, country, min_comp_count. If missing, ask for ZIP and radius. US-only for full tooling (decode, predict, history); UK uses `search_uk_active_cars`/`search_uk_recent_cars` only (no VIN decode — ask for YMMT). Confirm profile.
Dual pricing: always report BOTH franchise and independent market prices.

## CPO Detection

When pricing a vehicle, determine if it is Certified Pre-Owned (CPO):

1. **From user input:** If the user states the vehicle is certified or CPO.
2. **From listing data:** If the vehicle listing includes `is_certified=true`.
3. **From VIN history:** If `get_car_history` shows the vehicle listed as certified.

When a vehicle IS CPO:

- Call `predict_price_with_comparables` with `is_certified=true` for the CPO market price
- Also call WITHOUT `is_certified` (or with `is_certified=false`) for the non-CPO market price
- Search comps with `is_certified=true` filter for apples-to-apples CPO comparables
- Calculate and display the CPO premium:

```
CPO Market Price:      $XX,XXX  (based on N certified comps)
Non-CPO Market Price:  $XX,XXX  (based on N total comps)
CPO Premium:           +$X,XXX  (+X.X%)
```

When a vehicle is NOT CPO, skip the CPO-specific calls and price normally.

## User Context

User is an appraiser needing market price context for defensible valuations — competitive landscape, listing prices, and price positioning.

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or YMMT | Ask |
| Auto | ZIP, radius | Profile |
| Recommended | Mileage | Ask |
| Optional | Target/asking price | Ask |

VIN provided → decode first (US only; UK → ask for YMMT).

## Workflow: Price-Check a Single VIN

Use this when the user says "price check this VIN" or "what's the market on this one."

1. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to confirm year, make, model, trim, body type, drivetrain, engine, and transmission. Present the decoded specs to the user for confirmation.
   → **Extract only**: year, make, model, trim, body_type, drivetrain, engine, transmission. Discard full response.

2. **Get predicted market prices (dual)** — Make TWO calls to `mcp__marketcheck__predict_price_with_comparables`:
   - **Franchise (retail):** with `vin`, `miles`, `zip`, `dealer_type=franchise`. This represents full retail market value.
   - **Independent (wholesale-proxy):** with the same parameters but `dealer_type=independent`. This provides wholesale-oriented context.
   → **Extract only**: predicted_price, comparable VINs/prices from each call. Discard full response.

2a. **CPO pricing (if applicable)** — If the vehicle is CPO (detected per CPO Detection section above), make additional calls with `is_certified=true` for both franchise and independent predictions. Report CPO market price separately from non-CPO market price, and show the CPO premium.
   → **Extract only**: CPO predicted_price, non-CPO predicted_price, comp counts. Discard full response.

3. **Pull competing active listings** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from step 1), `zip`, `radius=75`, `sort_by=price`, `sort_order=asc`, `rows=15`, `car_type=used`. This returns the competitive set across all dealer types.
   → **Extract only**: per listing — price, miles, dom, dealer_name, dealer_type, distance. Discard full response.

4. **Calculate price position** — If the user provided a subject price or asking price, compare it against the competitive set:
   - Percentile rank (e.g., "The subject price is lower than 72% of competing units")
   - Distance to the cheapest and most expensive unit
   - Median and mean market price
   - Number of competing units within +/- 5% of the subject price

5. **Deliver the market context** — Present both market prices for the appraiser to select the appropriate benchmark:
```
Franchise (Retail) Market Price:    $XX,XXX  (based on N comps)
Independent (Wholesale) Market Price:  $XX,XXX  (based on N comps)
Spread:                             $X,XXX   (X.X%)
Active Comps in Market:             N within [radius] miles
```

## Workflow: Trade-In VIN Price History

Use this when the appraiser asks "what's the history on this VIN" or needs listing trajectory context before finalizing a valuation.

1. **Pull listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=desc` to get the full timeline of listings across dealers.
   → **Extract only**: per listing — date, dealer_name, price, dom, is_certified. Discard full response.

2. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to get full specs.
   → **Extract only**: year, make, model, trim, MSRP. Discard full response.

3. **Get predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.
   → **Extract only**: predicted_price. Discard full response.

4. **Analyze the trajectory** — From the history, extract:
   - Number of dealers that have listed this VIN
   - Price at each listing and the direction of change
   - Total days on market across all listings
   - Whether the vehicle was ever listed as certified

5. **Deliver price history context** — Show the price trajectory, current market value, and flag any red flags (e.g., multiple dealer hops in a short period, steep price drops suggesting a problem unit). This context is critical for the appraiser's confidence assessment.

## Workflow: Market Price Distribution

Use this when the appraiser asks "what's the market look like for this model" or wants a statistical overview to anchor a valuation.

1. **Pull market stats** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=100`, `car_type=used`, `stats=price,miles`, `rows=0`. The `rows=0` returns only stats without individual listings.
   → **Extract only**: mean, median, min, max, stddev for price and miles, total count. Discard full response.

2. **Pull the cheapest listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=asc`, `rows=5`.
   → **Extract only**: per listing — price, miles, dealer_name, dom. Discard full response.

3. **Pull the most expensive listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=desc`, `rows=5`.
   → **Extract only**: per listing — price, miles, dealer_name, dom. Discard full response.

4. **Present the distribution** — Show: mean, median, min, max, standard deviation for price and miles. Identify the price bands (quartiles) and show where the subject vehicle would fall. This statistical context supports the appraiser's valuation methodology.

5. **Highlight outliers** — Flag any listings priced more than 2 standard deviations from the mean as potential data quality issues or unique units (salvage, high miles, rare trim).

## Output

Present: summary headline with vehicle and market price, data table(s) of comparables with price/miles/DOM/dealer, key market signals (price position, spread, comp count), and actionable recommendation for the appraiser's valuation.
