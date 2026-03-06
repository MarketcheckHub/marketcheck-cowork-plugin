---
description: Decode a VIN and show its full spec sheet, market history, and estimated value for insurance context
allowed-tools: ["mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__get_car_history", "mcp__marketcheck__predict_price_with_comparables"]
argument-hint: [VIN]
---

Full VIN lookup -- decode specs, pull listing history, estimate market value for insurance claims context.

## Step 0: Load insurer profile

Read `~/.claude/marketcheck/insurer-profile.json`. Note `location.zip`/`postcode` and `country`. If UK: "VIN lookup requires US data tools. Not available for UK vehicles." Stop.

## Step 1: Parse input

$ARGUMENTS contains 17-char string -> use as VIN. Otherwise ask for VIN.

## Step 2: Decode VIN

Call `decode_vin_neovin` with `vin`, `include_generic=true`.

## Step 3: Pull history

Call `get_car_history` with `vin`, `sort_order=desc`.

## Step 4: Estimate value

Call `predict_price_with_comparables` with `vin`, `miles=50000` (default -- actual unknown).

## Step 5: Present results

Show: vehicle specs, listing history table, total market exposure, price journey, estimated current value at 50K miles, top 3-5 comparables. If no history: note vehicle may not have been listed recently.
