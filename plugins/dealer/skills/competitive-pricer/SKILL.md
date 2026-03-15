---
name: competitive-pricer
description: >
  This skill should be used when the user asks to "price this car",
  "am I priced right", "competitive pricing", "price check VIN",
  "who is undercutting me", "market price for this", "price my inventory",
  "compare my price", or needs help with pricing strategy, price positioning,
  competitive price analysis, or identifying pricing opportunities in their market.
version: 0.1.0
---

# Competitive Pricer — Real-Time Price Positioning Against Your Market

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, dealer_id, dealer_type, franchise_brands, radius, country, cpo_program, cpo_certification_cost. If missing, ask for ZIP and radius. **US**: `search_active_cars`, `decode_vin_neovin`, `predict_price_with_comparables`, `get_car_history`. **UK**: `search_uk_active_cars`, `search_uk_recent_cars` only (no VIN decode/ML prediction — ask user for YMMT, use comp median). Confirm: "Using profile: [dealer.name], [ZIP], [Country]". Dual pricing: report BOTH franchise and independent prices; dealer's `dealer_type` = PRIMARY, other = SECONDARY context.

## CPO Detection

When pricing a vehicle, determine if it is Certified Pre-Owned (CPO):

1. **From inventory scan:** If the vehicle listing includes `is_certified=true`, it is CPO.
2. **From user input:** If the user states the vehicle is certified or CPO.
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
Your Price:            $XX,XXX  (CPO unit)
Gap vs CPO Market:     -$XXX    (X.X% below CPO market — competitively priced)
```

When a vehicle is NOT CPO, skip the CPO-specific calls and price normally.

## User Context
Dealer user (used car manager, pricing analyst, GM) checking competitive price positioning, margin opportunities, and aging risk.

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or YMMT | Ask |
| Auto | ZIP, radius, dealer_type | Profile |
| Recommended | Mileage, asking price | Ask |

VIN provided → decode first to confirm specs (US only; UK dealers provide specs manually).

## Workflow: Price-Check a Single VIN

Use this when a dealer says "price check this VIN" or "am I priced right on this one."

1. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to confirm year, make, model, trim, body type, drivetrain, engine, and transmission. Present the decoded specs to the user for confirmation.
   → **Extract only**: year, make, model, trim, body_type, drivetrain, engine, transmission. Discard full response.

2. **Get predicted market prices (dual)** — Make TWO calls to `mcp__marketcheck__predict_price_with_comparables`:
   - **Primary:** with `vin`, `miles`, `zip`, `dealer_type` matching the source dealer's type (from profile). This is the primary comparison.
   - **Secondary:** with the same parameters but `dealer_type` set to the OTHER type (franchise<>independent). This provides market context.
   → **Extract only**: predicted_price, comparable VINs/prices from each call. Discard full response.

2a. **CPO pricing (if applicable)** — If the vehicle is CPO (detected per CPO Detection section above), make additional calls with `is_certified=true` for both franchise and independent predictions. Report CPO market price separately from non-CPO market price, and show the CPO premium.
   → **Extract only**: predicted_price (certified), predicted_price (non-certified), delta for CPO premium. Discard full response.

3. **Pull competing active listings** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from step 1), `zip`, `radius` (from profile `default_radius_miles`, minimum 75), `sort_by=price`, `sort_order=asc`, `rows=15`, `car_type=used`. This returns the competitive set. Additionally, call `mcp__marketcheck__search_active_cars` with the same parameters but add `dealer_type` matching the source dealer's type to get a filtered competitive set from SAME-type dealers only.
   → **Extract only**: per listing — price, miles, dom, dealer_name, distance; plus total count. Discard full response.

4. **Calculate price position** — Compare the dealer's asking price (or predicted price) against the competitive set:
   - Percentile rank (e.g., "Your price is lower than 72% of competing units")
   - Distance to the cheapest and most expensive unit
   - Median and mean market price
   - Number of competing units within +/- 5% of the subject price

5. **Deliver the verdict** — Classify the price as **Below Market** (bottom quartile), **At Market** (middle 50%), or **Above Market** (top quartile) and recommend an action: hold, adjust down, or raise. Show both market prices in the output:
```
Franchise Market Price:    $XX,XXX  (based on N comps)
Independent Market Price:  $XX,XXX  (based on N comps)
Your Price:                $XX,XXX  ([your dealer_type] dealer)
Gap vs Your Market:        $X,XXX   (X.X% [above/below] [your type] market) ← PRIMARY
Gap vs Other Market:       $X,XXX   (X.X% [above/below] [other type] market) ← CONTEXT
```

## Workflow: Batch Competitive Scan

Use this when a dealer provides a list of VINs (e.g., "check pricing on my front-line inventory").

1. **Accept VIN list** — Collect all VINs from the user. Confirm the market ZIP and radius once (applies to all).

2. **Loop per VIN** — For each VIN:
   - Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type` (Primary — matching source dealer's type).
   - Call `mcp__marketcheck__predict_price_with_comparables` with the same parameters but `dealer_type` set to the OTHER type (Secondary — franchise<>independent).
   - If the vehicle is CPO, make additional calls with `is_certified=true` for both dealer types.
   - Call `mcp__marketcheck__search_active_cars` with the decoded YMMT, `zip`, `radius` (from profile, minimum 75), `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used`.
   → **Extract only**: per VIN — predicted_price (franchise+independent), comp count, comp price range, total active supply. Discard full response.

3. **Build the price-position table** — For each VIN, calculate: asking price, franchise market price ("Franchise Mkt"), independent market price ("Independent Mkt"), delta vs primary market, delta vs secondary market, percentile rank, competing unit count, and recommended action.

4. **Prioritize actions** — Sort the table by largest overpricing first (highest risk of aging), then by largest underpricing (margin opportunity).

5. **Present the summary** — Show the full table plus a rollup: total units scanned, count overpriced, count underpriced, count at market, estimated margin recovery if adjusted.

## Workflow: Trade-In VIN Price History

Use this when a dealer asks "what's the history on this trade" or needs context before making an offer.

1. **Pull listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=desc` to get the full timeline of listings across dealers.
   → **Extract only**: per listing — date, dealer_name, price, dom, is_certified. Discard full response.

2. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to get full specs.
   → **Extract only**: year, make, model, trim. Discard full response.

3. **Get predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type`.
   → **Extract only**: predicted_price. Discard full response.

4. **Analyze the trajectory** — From the history, extract:
   - Number of dealers that have listed this VIN
   - Price at each listing and the direction of change
   - Total days on market across all listings
   - Whether the vehicle was ever listed as certified

5. **Deliver trade-in context** — Show the price trajectory chart, current market value, and flag any red flags (e.g., multiple dealer hops in a short period, steep price drops suggesting a problem unit).

## Workflow: Market Price Distribution

Use this when a dealer asks "what's the market look like for this model" or wants a statistical overview.

1. **Pull market stats** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=100`, `car_type=used`, `stats=price,miles`, `rows=0`. The `rows=0` returns only stats without individual listings.
   → **Extract only**: mean, median, min, max, stddev for price and miles, total count. Discard full response.

2. **Pull the cheapest listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=asc`, `rows=5`.
   → **Extract only**: per listing — price, miles, dealer_name, dom. Discard full response.

3. **Pull the most expensive listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=desc`, `rows=5`.
   → **Extract only**: per listing — price, miles, dealer_name, dom. Discard full response.

4. **Present the distribution** — Show: mean, median, min, max, standard deviation for price and miles. Identify the price bands (quartiles) and show where the user's vehicle would fall.

5. **Highlight outliers** — Flag any listings priced more than 2 standard deviations from the mean as potential data quality issues or unique units (salvage, high miles, rare trim).

## Workflow: Competitor Price Movement

Use this when a dealer asks "who dropped their price" or "who is undercutting me."

1. **Scan for recent price drops** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=75`, `price_change=negative`, `sort_by=price`, `sort_order=asc`, `rows=20`.
   → **Extract only**: per listing — price, price_change_amount, dealer_name, dom, distance. Discard full response.

2. **Scan for recent price raises** — Call `mcp__marketcheck__search_active_cars` with the same filters but `price_change=positive`, `rows=10`.
   → **Extract only**: per listing — price, price_change_amount, dealer_name. Discard full response.

3. **Identify aggressive competitors** — From the price-drop results, group by dealer and count the number of drops. Dealers with multiple recent drops are signaling inventory pressure.

4. **Calculate competitive exposure** — For each dropped listing, compare the new price to the user's asking price on similar units. Flag any that now undercut the user.

5. **Recommend response** — For each unit where the user is now being undercut, suggest whether to match, split the difference, or hold based on the user's DOM and the competitor's DOM.

## Output
Present: summary headline (vehicle + price position verdict), price position data table (your price, market price, ratio, percentile, comp count), competitive set table with key metrics, comparison context (franchise vs independent), key signals (bullets), and one actionable recommendation with dollar impact.
