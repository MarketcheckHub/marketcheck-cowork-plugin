---
description: Quick price check on a VIN or vehicle
allowed-tools: ["mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__get_car_history"]
argument-hint: [VIN or "year make model"]
---

Quick competitive price check on a single vehicle. Returns predicted market value, competing listings, and a price-position verdict in under 30 seconds.

## Step 1: Parse input

Check $ARGUMENTS:

- **If a 17-character VIN**: Use it directly
- **If year/make/model text** (e.g., "2023 Toyota RAV4"): Note that price prediction requires a VIN. Search for matching active listings instead using `mcp__marketcheck__search_active_cars` with the provided year, make, model, and ask the user for their zip code.
- **If empty**: Ask: "Provide a VIN (17 characters) or describe the vehicle (e.g., '2023 Toyota RAV4')"

## Step 2: Decode & Price

1. Call `mcp__marketcheck__decode_vin_neovin` with the VIN to get full specs (year, make, model, trim, MSRP, engine, transmission)
2. Ask for mileage if not provided (default: 50,000)
3. Ask for location zip code if not provided
4. Call `mcp__marketcheck__predict_price_with_comparables` with:
   - `vin`: the VIN
   - `miles`: user's mileage
   - `zip`: user's zip code
   - `dealer_type`: "franchise" (default)

## Step 3: Market context

Call `mcp__marketcheck__search_active_cars` with:
- `make`, `model`, `year` (from decoded VIN)
- `zip` and `radius=50`
- `stats=price,miles`
- `rows=5`
- `sort_by=price`, `sort_order=asc`

## Step 4: Present results

```
PRICE CHECK: [Year Make Model Trim]
VIN: [VIN]
Mileage: [X miles]  |  Location: [Zip]

PREDICTED MARKET VALUE: $XX,XXX
MSRP (new): $XX,XXX  |  Retention: XX%

MARKET CONTEXT (within 50 mi):
- Competing units: X
- Price range: $XX,XXX – $XX,XXX
- Average asking: $XX,XXX
- Lowest competitor: $XX,XXX at [Dealer Name]

COMPARABLE VEHICLES:
[Top 3-5 comparables from prediction with price, miles, dealer]

VERDICT: [Priced RIGHT / ABOVE market by $X / BELOW market by $X]
```

If the user has a current asking price, compare it to the predicted value and provide a specific recommendation (hold, reduce by $X, or room to raise).
