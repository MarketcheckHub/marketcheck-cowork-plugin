---
name: claims-valuation
description: >
  This skill should be used when the user asks about "total loss valuation",
  "claims value", "settlement offer", "salvage estimate", "insurance claim pricing",
  "total loss threshold", "what's the claim worth", "settlement range",
  "pre-loss value", "diminished value", "total loss determination",
  or needs help with insurance claim vehicle valuation, total-loss
  determination, settlement pricing, or salvage value estimation.
version: 0.1.0
---

# Claims Valuation — Insurance Total-Loss & Settlement Pricing

## Insurer Profile (Load First)

1. Read `~/.claude/marketcheck/insurer-profile.json`.
2. If exists, extract: location (zip/state), preferences (total_loss_threshold_pct, default_comp_radius).
3. If not found: ask for ZIP code to proceed. Suggest running `/onboarding` first.
4. **Country check:** US-only. UK not supported (requires predict_price and sold data).
5. Confirm: "Using profile: **[user.name]**, [ZIP], [State]"

## User Context

The primary user is an **insurance adjuster** or **total-loss specialist** who needs a defensible, comparable-backed fair market value (FMV) to determine if a vehicle is a total loss and, if so, what the settlement offer should be. The valuation must be supportable in dispute resolution.

## Workflow: Total-Loss Determination & Settlement

### Step 1 — Vehicle identification

Collect from user:
- VIN (required)
- Current odometer reading (required)
- Pre-loss condition: Clean, Average, Rough (required)
- Date of loss (optional, defaults to today)
- Any pre-existing damage or modifications

Call `mcp__marketcheck__decode_vin_neovin` with the VIN to get exact specs: year, make, model, trim, body type, drivetrain, engine, transmission, original MSRP.

### Step 2 — Fair Market Value (FMV) determination

Make THREE pricing calls:
1. `mcp__marketcheck__predict_price_with_comparables` with VIN, miles, ZIP, `dealer_type=franchise` → Franchise retail FMV
2. `mcp__marketcheck__predict_price_with_comparables` with VIN, miles, ZIP, `dealer_type=independent` → Independent retail FMV
3. If vehicle was CPO (`is_certified` in history or user states): additional call with `is_certified=true`

**Pre-loss FMV** = average of franchise and independent predicted prices, adjusted by condition:
- Clean: use the higher of the two predictions
- Average: use the average
- Rough: use the lower, minus 5%

### Step 3 — Comparable evidence (wide radius)

Pull active retail comparables:
- `mcp__marketcheck__search_active_cars` with YMMT, ZIP, `radius=100`, `miles_range=<odo-15000>-<odo+15000>`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=20`

Pull sold transaction evidence (strongest for disputes):
- `mcp__marketcheck__search_past_90_days` with same YMMT filters, `sold=true`

### Step 4 — Total-loss determination

Calculate:
- **Repair cost threshold** = FMV x total_loss_threshold_pct (default 75%)
- If estimated repair cost > threshold → **TOTAL LOSS**
- If not provided, just present the threshold: "This vehicle is a total loss if repair costs exceed $XX,XXX (75% of FMV)"

### Step 5 — Settlement range

Calculate three tiers:
- **Low settlement** = 25th percentile of sold transaction prices (condition-adjusted)
- **Mid settlement** = Pre-loss FMV from Step 2
- **High settlement** = 75th percentile of sold transaction prices

### Step 6 — Salvage value estimate

Salvage value is typically 15-25% of pre-loss FMV depending on damage severity:
- Minor (cosmetic): 25% of FMV
- Moderate (mechanical): 20% of FMV
- Severe (structural/flood): 15% of FMV
- If user provides actual salvage bid, use that instead

**Net claim cost** = Settlement offer - Salvage value

## Output

```
INSURANCE CLAIMS VALUATION
━━━━━━━━━━━━━━━━━━━━━━━━━
Claim Date: [date] | Adjuster: [user.name]

VEHICLE IDENTIFICATION
VIN:     [full VIN]
Vehicle: [Year Make Model Trim]
Body: [type] | Drivetrain: [AWD/FWD/RWD] | Engine: [spec]
Odometer: [miles] | Pre-Loss Condition: [Clean/Average/Rough]
Original MSRP: $XX,XXX

PRE-LOSS FAIR MARKET VALUE
Franchise Retail Value:     $XX,XXX  (N comps)
Independent Retail Value:   $XX,XXX  (N comps)
Condition-Adjusted FMV:     $XX,XXX
[If CPO: CPO Value: $XX,XXX | CPO Premium: +$X,XXX]

TOTAL-LOSS THRESHOLD
Threshold: $XX,XXX (75% of FMV)
Determination: [TOTAL LOSS / NOT TOTAL LOSS / PENDING REPAIR ESTIMATE]

SETTLEMENT RANGE
Low:   $XX,XXX  (25th percentile of sold transactions)
Mid:   $XX,XXX  (condition-adjusted FMV — recommended)
High:  $XX,XXX  (75th percentile of sold transactions)

SALVAGE VALUE ESTIMATE
Estimated Salvage: $X,XXX ([damage level] — XX% of FMV)
Net Claim Cost:    $XX,XXX (settlement - salvage)

COMPARABLE EVIDENCE — Active Retail (N units within 100mi)
VIN (last 6) | Year Trim | Miles  | Price   | Dealer           | Distance
-------------|-----------|--------|---------|------------------|---------
[top 10 by relevance]

COMPARABLE EVIDENCE — Sold Transactions (N units, past 90 days)
VIN (last 6) | Year Trim | Miles  | Sold $  | Dealer           | Sale Date
-------------|-----------|--------|---------|------------------|----------
[top 10 by relevance]

METHODOLOGY
- FMV based on MarketCheck ML price prediction calibrated to [N] comparable vehicles
- Sold transaction evidence from past 90 days provides the strongest settlement support
- Condition adjustment applied: [Clean/Average/Rough] → [+X% / baseline / -X%]
- Search radius: 100 miles from [ZIP] to ensure adequate comparable pool

CAVEATS
- [Any factors not accounted for: accident history, aftermarket mods, regional anomalies]
- [If low comp count: "Limited comparable data — widen search or consider additional sources"]
```

## Workflow: Batch Claims Processing

For multiple VINs (e.g., hail damage event, flood):

1. Accept list of VINs with miles and condition
2. Use the `insurer:portfolio-scanner` agent to process each VIN
3. Present summary: total claim exposure, average FMV, total-loss count, salvage estimate
4. Ranked table of all vehicles with FMV and settlement recommendation

## Workflow: Diminished Value

For vehicles that were repaired (not total-loss) and the claimant wants diminished value:

1. Get pre-loss FMV (same as Steps 1-2 above)
2. Estimate post-repair diminished value: typically 10-25% of FMV depending on repair severity
3. Show: "Pre-loss FMV: $XX,XXX → Post-repair diminished value: $X,XXX-$X,XXX"

## Important Notes

- **US-only:** Requires `predict_price_with_comparables` and `search_past_90_days`.
- Always cite specific comparable VINs — adjusters need to defend valuations.
- Sold transaction data is the strongest evidence in settlement disputes.
- The 75% total-loss threshold is a common default — actual thresholds vary by state and insurer. Use profile value if available.
- For disputed settlements, recommend expanding the search radius to 150-200 miles and including older sold data.
