---
description: Quick price check on a VIN or vehicle for appraisal context
allowed-tools: ["mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__get_car_history", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [VIN or "year make model"]
---

Quick market price check with retail and wholesale values, competing listings, and comparable context.

## Step 1: Parse input

17-char VIN -> use directly. Year/make/model text -> search active listings (price prediction requires VIN). Empty -> ask for VIN or vehicle description.

## Step 1.5: Load appraiser profile

Read `~/.claude/marketcheck/appraiser-profile.json`. Extract `location.zip`/`postcode`, `preferences.default_radius_miles` (75), `appraiser.min_comp_count`, `location.country`.
**US:** Use `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`.
**UK:** Use `search_uk_active_cars` only. No VIN decode or price prediction -- use comp median.
No profile -> ask for ZIP.

## Step 2: Decode & Price

1. **US:** `decode_vin_neovin` with VIN. **UK:** Ask for year/make/model/trim if needed.
2. Ask mileage if not provided (default: 50,000).
3. **US:** `predict_price_with_comparables` TWICE:
   - **Retail:** `dealer_type=franchise`
   - **Wholesale:** `dealer_type=independent`
   **UK:** Skip.

## Step 3: Market context

`search_active_cars` with `make`, `model`, `year`, `zip`, `radius=75`, `stats=price,miles`, `rows=5`, `sort_by=price`, `sort_order=asc`.

## Step 4: Present results

Show: year/make/model/trim, VIN, mileage, location, market values (retail franchise + wholesale independent + spread), MSRP + retention %, market context (competing units, price range, avg asking, lowest), top 3-5 comparables, confidence level (High/Medium/Low based on comp count vs min_comp_count). If user has subject price, compare to retail and wholesale benchmarks. Note: retail = franchise comps, wholesale = independent comps.
