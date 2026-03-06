---
description: Quick price check on a VIN or vehicle for appraisal context
allowed-tools: ["mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__get_car_history", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [VIN or "year make model"]
---

Quick market price check on a single vehicle. Returns predicted retail and wholesale market values, competing listings, and comparable context in under 30 seconds. Designed for appraisers who need fast market context.

## Step 1: Parse input

Check $ARGUMENTS:

- **If a 17-character VIN**: Use it directly
- **If year/make/model text** (e.g., "2023 Toyota RAV4"): Note that price prediction requires a VIN. Search for matching active listings instead using `mcp__marketcheck__search_active_cars` (or `search_uk_active_cars` for UK) with the provided year, make, model, and ask the user for their zip code.
- **If empty**: Ask: "Provide a VIN (17 characters) or describe the vehicle (e.g., '2023 Toyota RAV4')"

## Step 1.5: Load appraiser profile

Read `~/.claude/marketcheck/appraiser-profile.json`. If it exists:
- Use `location.zip` (US) or `location.postcode` (UK) as the default location — do not ask for ZIP
- Use `preferences.default_radius_miles` as the search radius (default: 75)
- Use `appraiser.min_comp_count` for confidence assessment
- Note `location.country` for tool routing

**Tool routing:**
- **US**: Use `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`
- **UK**: Use `search_uk_active_cars` for market context. VIN decode and price prediction are **not available** — search by year/make/model and use comp median for pricing.

If no profile exists, ask for ZIP code as before.

## Step 2: Decode & Price

1. **US**: Call `mcp__marketcheck__decode_vin_neovin` with the VIN to get full specs. **UK**: Skip decode — ask user for year/make/model/trim if not already provided.
2. Ask for mileage if not provided (default: 50,000)
3. Use ZIP from appraiser profile if available, otherwise ask
4. **US**: Call `mcp__marketcheck__predict_price_with_comparables` TWICE:
   - **Franchise (Retail):** with `vin`, `miles`, `zip`, `dealer_type=franchise`
   - **Independent (Wholesale):** with `vin`, `miles`, `zip`, `dealer_type=independent`
   **UK**: Skip — predicted value will come from comp median in Step 3.

## Step 3: Market context

Call `mcp__marketcheck__search_active_cars` with:
- `make`, `model`, `year` (from decoded VIN)
- `zip` and `radius=75`
- `stats=price,miles`
- `rows=5`
- `sort_by=price`, `sort_order=asc`

## Step 4: Present results

```
PRICE CHECK: [Year Make Model Trim]
VIN: [VIN]
Mileage: [X miles]  |  Location: [Zip]

MARKET VALUES:
  Retail (Franchise) Market Price:    $XX,XXX
  Wholesale (Independent) Market Price: $XX,XXX
  Retail-Wholesale Spread:            $X,XXX (XX%)

MSRP (new): $XX,XXX  |  Retention: XX%

MARKET CONTEXT (within [radius] mi):
- Competing units: X
- Price range: $XX,XXX – $XX,XXX
- Average asking: $XX,XXX
- Lowest competitor: $XX,XXX at [Dealer Name]

COMPARABLE VEHICLES:
[Top 3-5 comparables from prediction with price, miles, dealer]

CONFIDENCE: [High/Medium/Low] (based on [N] comparables, min threshold: [min_comp_count])
```

If the user has a current asking price or subject price, compare it to the market values and provide positioning context (above/at/below retail market, above/at/below wholesale market).

**Methodology note:** Retail value based on franchise dealer comparables. Wholesale value based on independent dealer comparables. The appraiser selects the appropriate benchmark based on appraisal purpose.
