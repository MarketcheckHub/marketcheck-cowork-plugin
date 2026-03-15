---
description: Decode a VIN and show its full spec sheet, market history, and collateral valuation
allowed-tools: ["mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__get_car_history", "mcp__marketcheck__predict_price_with_comparables"]
argument-hint: [VIN]
---

Full VIN lookup -- decode specs, pull listing history, estimate market value for collateral assessment.

## Step 0: Load lender profile

Read the `marketcheck-profile.md` project memory file. Note `location.zip`/`postcode`, `country`, `risk_ltv_threshold`, `high_risk_ltv_threshold` for LTV flagging. If UK: "VIN lookup requires US data tools. Use `/price-check` with year/make/model instead." Stop.

## Step 1: Parse input

$ARGUMENTS contains 17-char string -> use as VIN. Otherwise ask for VIN.

## Step 2: Decode VIN

Call `decode_vin_neovin` with `vin`, `include_generic=true`.

## Step 3: Pull history

Call `get_car_history` with `vin`, `sort_order=desc`.

## Step 4: Estimate value

Call `predict_price_with_comparables` with `vin`, `miles=50000` (default -- actual unknown).

## Step 5: Present results

Show: vehicle specs, listing history table, total market exposure, price journey, collateral valuation (estimated retail value at 50K miles), top 3-5 comparables. If no history: note vehicle may not have been listed recently.
