---
description: Decode a VIN and show its full spec sheet, market history, and current valuation
allowed-tools: ["mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__get_car_history", "mcp__marketcheck__predict_price_with_comparables"]
argument-hint: [VIN]
---

Full VIN lookup -- decode specs, pull listing history, estimate retail and wholesale values for appraisal context.

## Step 0: Load appraiser profile

Read the `marketcheck-profile.md` project memory file. Note `location.zip`/`postcode` and `country`. If UK: "VIN lookup requires US data tools. Use `/price-check` with year/make/model instead." Stop.

## Step 1: Parse input

$ARGUMENTS contains 17-char string -> use as VIN. Otherwise ask for VIN.

## Step 2: Decode VIN

Call `decode_vin_neovin` with `vin`, `include_generic=true`.

## Step 3: Pull history

Call `get_car_history` with `vin`, `sort_order=desc`.

## Step 4: Estimate value

Call `predict_price_with_comparables` TWICE:
- **Retail:** `vin`, `miles=50000`, `dealer_type=franchise`
- **Wholesale:** `vin`, `miles=50000`, `dealer_type=independent`

## Step 5: Present results

Show: vehicle specs, listing history table, total market exposure, price journey, estimated values (retail franchise + wholesale independent + spread), top 3-5 comparables, appraisal notes (red flags from history, confidence based on comp count). If no history: note vehicle may not have been listed recently.
