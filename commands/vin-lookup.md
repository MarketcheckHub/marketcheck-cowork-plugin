---
description: Decode a VIN and show its full spec sheet and market history
allowed-tools: ["mcp__marketcheck__decode_vin_neovin", "mcp__marketcheck__get_car_history", "mcp__marketcheck__predict_price_with_comparables"]
argument-hint: [VIN]
---

Full VIN lookup — decode the vehicle specs, pull its listing history, and estimate current market value. One command, complete picture.

## Step 1: Parse input

Check $ARGUMENTS:

- **If a 17-character string**: Use it as the VIN
- **If empty or invalid**: Ask: "Provide a 17-character VIN to decode"

## Step 2: Decode VIN

Call `mcp__marketcheck__decode_vin_neovin` with:
- `vin`: the VIN
- `include_generic`: true

## Step 3: Pull history

Call `mcp__marketcheck__get_car_history` with:
- `vin`: the VIN
- `sort_order`: "desc"

## Step 4: Estimate value

Call `mcp__marketcheck__predict_price_with_comparables` with:
- `vin`: the VIN
- `miles`: 50000 (note this is a default — actual mileage unknown)

## Step 5: Present results

```
VIN LOOKUP: [VIN]

VEHICLE SPECS:
Year: XXXX  |  Make: XXXXX  |  Model: XXXXX  |  Trim: XXXXX
Body: XXXXX  |  Doors: X  |  Drivetrain: XXX
Engine: X.XL [type] [cylinders]cyl [aspiration]  |  HP: XXX
Transmission: XXXXX
Fuel: XXXXX  |  MPG: XX city / XX hwy
MSRP (new): $XX,XXX

LISTING HISTORY:
Date       | Dealer              | Price    | Status   | DOM
YYYY-MM-DD | Dealer Name         | $XX,XXX  | Active   | XX
YYYY-MM-DD | Previous Dealer     | $XX,XXX  | Expired  | XX
...

Total market exposure: XX days across X dealers
Price journey: $XX,XXX → $XX,XXX ([+/-]XX%)

ESTIMATED CURRENT VALUE: $XX,XXX
(Based on 50K miles — provide actual mileage for a more accurate estimate)

TOP COMPARABLES:
[3-5 comparable vehicles with price, miles, dealer, location]
```

If no history is found, note: "No listing history found — this vehicle may not have been listed online recently."
