---
name: run-list-analyzer
description: >
  Evaluate consigned VINs before sale day. Triggers: "evaluate run list",
  "check these consigned VINs", "predict which will sell",
  "sale day prep", "analyze my run list", "price the auction list",
  "how will these VINs do at auction", "expected hammer prices",
  "sell-through prediction", evaluating a batch of VINs
  already consigned for an upcoming auction event.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Run List Analyzer — Evaluate Consigned VINs Before Sale Day

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, buyer_fee_pct, seller_fee_pct, target_sell_through_pct, country. If missing, ask minimum fields (state or zip). **US**: `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (no VIN decode/ML pricing — use comp median for hammer estimate). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Lane manager or sales exec reviewing a run list of consigned VINs before sale day. Need to know: expected hammer price per unit, which will sell and which may no-sale, optimal lane sequencing, and event-level revenue forecast.

## Gotchas

1. **VIN decode failures** — Some VINs (especially older vehicles, rebuilds, or grey-market imports) will fail `decode_vin_neovin`. When a VIN fails to decode, ask the user for YMMT manually rather than skipping the vehicle. Flag it as "DECODE FAILED — specs from user input" in the output.
2. **`predict_price_with_comparables` returns retail, not wholesale** — The predicted price is the expected retail asking price. Auction hammer is typically 88-92% of independent retail. Always apply the 0.92 discount factor. Never present the raw predicted_price as the expected hammer.
3. **Miles are critical for prediction accuracy** — If the user provides VINs without mileage, the price prediction will use an average mileage assumption and accuracy drops significantly. Always ask for miles if not provided. Flag any VIN priced without actual miles as "ESTIMATED — actual mileage not provided."
4. **Run list size vs API rate** — Large run lists (50+ VINs) require many sequential API calls (decode + predict + supply + velocity per VIN). For lists > 30 VINs, use the `run-list-pricer` agent. For smaller lists, process inline. Never attempt to process 100+ VINs in a single conversation turn.
5. **Sell-through probability is a heuristic, not ML** — The HIGH/MEDIUM/LOW classification is based on D/S ratio thresholds, not a trained model. Always present it as "Estimated sell-through" not "Predicted sell-through probability." Actual sell-through depends on reserve price, condition, and bidder attendance — factors outside the data.

| Field | Source | Default |
|-------|--------|---------|
| State/ZIP | Profile | — |
| Buyer fee % | Profile | 5% |
| Seller fee % | Profile | 3% |
| Target sell-through % | Profile | 85% |

## Workflow: Evaluate Run List

**Multi-agent approach:** Use the `run-list-pricer` agent for batch VIN processing.

Use the Agent tool to spawn the `auction-house:run-list-pricer` agent with this prompt:

> Evaluate auction run list. VINs: [list of VINs with miles if available]. State=[state], zip=[zip], buyer_fee_pct=[fee], seller_fee_pct=[fee].

The agent will per-VIN:
1. Decode specs via `mcp__marketcheck__decode_vin_neovin` with `vin=[VIN]` → Extract: year, make, model, trim, body_type
2. Predict wholesale value via `mcp__marketcheck__predict_price_with_comparables` with `vin=[VIN]`, `miles=[miles]`, `zip=[zip]`, `dealer_type=independent` → Extract: predicted_price (this is retail independent — apply x0.92 for hammer)
3. Check local supply via `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `state=[XX]`, `car_type=used`, `stats=price,dom`, `rows=0`, `price_min=1` → Extract: num_found, median_price
4. Check velocity via `mcp__marketcheck__get_sold_summary` with `make=[make]`, `model=[model]`, `state=[XX]`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `date_from=[first of prior month]`, `date_to=[last of prior month]` → Extract: sold_count, average_days_on_market
5. Calculate: expected hammer, sell-through probability, fee revenue, lane position

## Workflow: Quick Single-VIN Check

Use this when the user asks "will this VIN sell" or "expected hammer for [VIN]."

1. **Decode** — Call `mcp__marketcheck__decode_vin_neovin` with `vin`. → **Extract only**: year, make, model, trim, body_type. Discard full response.

2. **Predict wholesale** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=independent`. → **Extract only**: predicted_price. Discard full response.

3. **Supply check** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `state`, `car_type=used`, `stats=price,dom`, `rows=0`. → **Extract only**: num_found, median_price. Discard full response.

4. **Velocity check** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `state`, `inventory_type=Used`, `ranking_measure=sold_count`, date range for prior month. → **Extract only**: sold_count, average_days_on_market. Discard full response.

5. **Calculate**:
   - Expected Hammer = predicted_independent × 0.92
   - D/S Ratio = monthly_sold / active_supply
   - Sell-Through: HIGH (D/S > 2.0, 90%), MEDIUM (1.0-2.0, 75%), LOW (< 1.0, 60%)
   - Fee Revenue = expected_hammer × (buyer_fee + seller_fee) / 100

## Workflow: Lane Sequencing Recommendation

After all VINs are priced:
1. Sort by sell-through probability (HIGH first)
2. Within each tier, sort by expected hammer (highest first)
3. Recommend: run HIGH sell-through / high-value units in early lanes to build bidder energy
4. Put LOW sell-through units in later lanes — bidders already engaged, more likely to stretch
5. Flag "no-sale risk" units: expected hammer < $3,000 OR D/S < 0.5

## Output
Run list table: VIN, YMMT, Miles, Expected Hammer, Sell-Through (HIGH/MED/LOW), Lane Position (1-N), Fee Revenue, Flags. Event summary: Total Consigned, Predicted Sell Count, Predicted Gross Hammer, Predicted Total Fees, Predicted Sell-Through %, Revenue vs Target. Lane sequencing recommendation with rationale.

### Output Template

```
-- Run List Analysis: [Event Name/Date] — [N] Consigned VINs ----------------------

| Lane | VIN (last 8)  | Year | Make    | Model   | Trim     | Miles  | Est. Hammer | Sell-Through | Fee Rev  | Flags           |
|------|---------------|------|---------|---------|----------|--------|-------------|--------------|----------|-----------------|
|    1 | ...JK8A1234   | 2022 | Toyota  | RAV4    | XLE AWD  | 32,100 |     $26,800 | HIGH (92%)   |   $2,144 |                 |
|    2 | ...MN3B5678   | 2023 | Ford    | F-150   | XLT      | 18,400 |     $34,200 | HIGH (90%)   |   $2,736 |                 |
|  ... | ...           |  ... | ...     | ...     | ...      |    ... |         ... | ...          |      ... | ...             |
|   15 | ...QR9Z0000   | 2019 | Nissan  | Altima  | S        | 78,200 |      $9,800 | LOW (55%)    |     $784 | NO-SALE RISK    |

-- Event Summary -------------------------------------------------------------------
Total Consigned:           [N] units
Predicted Sell Count:      [X] units
Predicted Gross Hammer:    $[XXX,XXX]
Predicted Total Fees:      $[XX,XXX]  (buyer [X]% + seller [X]%)
Predicted Sell-Through:    [YY]%
Target Sell-Through:       [ZZ]%
Revenue vs Target:         [+/-]$[X,XXX] ([above/below] target)

-- Lane Sequencing Strategy --------------------------------------------------------
Lanes 1-[X]:   HIGH sell-through / high-value units — build bidder energy early
Lanes [X]-[Y]: MEDIUM sell-through — maintain momentum
Lanes [Y]-[N]: LOW sell-through — engaged bidders more likely to stretch

-- Flags ---------------------------------------------------------------------------
[N] units flagged NO-SALE RISK (hammer < $3,000 or D/S < 0.5)
[N] units priced without actual mileage (ESTIMATED)
[N] VINs failed to decode (specs from user input)
```

## Self-Check (before presenting to user)

1. **Every VIN has a hammer estimate** — No VIN should show "N/A" for expected hammer. If prediction failed, use comp median as fallback and flag "COMP-BASED ESTIMATE."
2. **Hammer = predicted_independent x 0.92** — Verify no row shows the raw predicted_price as the hammer. Spot-check at least 2 VINs.
3. **Fee revenue math** — fee_rev = expected_hammer x (buyer_fee_pct + seller_fee_pct) / 100. Total fees = sum of all per-unit fee_rev x sell_through_probability. Verify the event summary total matches the sum.
4. **Lane positions are sequential 1-N** — Every VIN has a unique lane number. HIGH sell-through units are in lower lane numbers (earlier). No gaps in sequencing.
5. **Sell-through percentages are from the heuristic** — HIGH = 90%, MEDIUM = 75%, LOW = 60%. These map to D/S ratio thresholds. Verify no "100%" or "0%" sell-through values appear.
6. **Miles were provided or flagged** — Any VIN where miles were not provided by the user is flagged "ESTIMATED — actual mileage not provided" in the Flags column.
