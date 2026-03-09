---
name: run-list-analyzer
description: >
  This skill should be used when the user asks to "evaluate run list",
  "check these consigned VINs", "predict which will sell",
  "sale day prep", "analyze my run list", "price the auction list",
  "how will these VINs do at auction", "expected hammer prices",
  "sell-through prediction", or needs help evaluating a batch of VINs
  already consigned for an upcoming auction event.
version: 0.1.0
---

# Run List Analyzer — Evaluate Consigned VINs Before Sale Day

## Profile
Load `~/.claude/marketcheck/auction-house-profile.json` if exists. Extract: zip/postcode, state/region, buyer_fee_pct, seller_fee_pct, target_sell_through_pct, country. If missing, ask minimum fields (state or zip). **US**: `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (no VIN decode/ML pricing — use comp median for hammer estimate). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Lane manager or sales exec reviewing a run list of consigned VINs before sale day. Need to know: expected hammer price per unit, which will sell and which may no-sale, optimal lane sequencing, and event-level revenue forecast.

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
1. Decode specs via `decode_vin_neovin`
2. Predict wholesale value via `predict_price_with_comparables` (dealer_type=independent)
3. Check local supply via `search_active_cars`
4. Check velocity via `get_sold_summary`
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
