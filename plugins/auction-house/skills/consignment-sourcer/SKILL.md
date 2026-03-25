---
name: consignment-sourcer
description: >
  Find dealers with wholesale-ready inventory. Triggers: "find consignment leads",
  "who has aged inventory", "wholesale sourcing", "cars to bring to auction",
  "find vehicles to consign", "dealer wholesale opportunities",
  "aged inventory in my market", "who should I call for consignments",
  "sourcing for next sale", identifying dealers sitting on
  aged, overpriced inventory that should be wholesaled through auction.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Consignment Sourcer — Find Dealers with Wholesale-Ready Inventory

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, target_dmas, vehicle_segments, consigner_types, seller_fee_pct, buyer_fee_pct, country, radius. If missing, ask minimum fields (state or zip). **US**: `search_active_cars`, `predict_price_with_comparables`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (no ML pricing — use comp median; skip velocity workflows). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Auction house consignment rep or sales exec looking for dealers with aged, overpriced inventory they should wholesale through auction rather than continuing to retail. The goal is to fill upcoming auction lanes with quality consigned inventory.

## Gotchas

1. **DOM > 60 threshold is a starting point, not a rule** — In slow markets (luxury, EVs), 60 DOM is normal. In hot markets (trucks in TX), 30 DOM is already aged. Cross-reference the model's average DOM from `get_sold_summary` and flag units exceeding 1.5x the model's market average DOM, not just a flat 60-day cutoff.
2. **`predict_price_with_comparables` with `dealer_type=independent` is the wholesale proxy** — This is the closest approximation to wholesale/auction value. It is NOT actual auction data. Frame outputs as "estimated wholesale value" not "auction price." The 0.92 hammer factor is applied on top of this.
3. **Floor plan burn calculation** — The default $35/day is a US industry average. Actual floor plan costs vary by dealer size and lender. Use the profile's `floor_plan_per_day` if available. Calculate burn as: `$35/day x units x (avg_dom - 45)` where 45 is the "acceptable" DOM threshold. Only count excess days.
4. **Dealer clustering can miss multi-location groups** — Step 5 clusters by `seller_name`, but the same dealer group may have slightly different names across locations ("ABC Motors" vs "ABC Motors of Springfield"). Look for common prefixes in seller_name to identify likely groups.
5. **UK limitation** — UK profiles can find aged inventory via `search_uk_active_cars` sorted by DOM, but cannot price it (no `predict_price_with_comparables`). Use comp median from `search_uk_active_cars` with matching YMMT as a fallback. Skip overpriced% calculation and note "Wholesale pricing estimated from comp median — no ML prediction available for UK."

| Field | Source | Default |
|-------|--------|---------|
| State/ZIP, radius | Profile | — |
| Seller fee % | Profile | 3% |
| Buyer fee % | Profile | 5% |
| Vehicle segments | Profile | all |

## Workflow: Find Aged Inventory Across Market

Use this when the user says "who has aged inventory" or "find consignment leads."

1. **Search for aged inventory** — Call `mcp__marketcheck__search_active_cars` with `state=[XX]` (or `zip=[XXXXX]`, `radius=[N]`), `car_type=used`, `seller_type=dealer`, `sort_by=dom`, `sort_order=desc`, `rows=50`, `price_min=1`. If vehicle_segments specified, add `body_type=[segment]` filter. If profile has specific year preferences, add `year_from` and `year_to`.
   → **Extract only**: per vehicle — vin, year, make, model, trim, price, miles, dom, seller_name, seller_city, dealer_id. Skip any vehicle where price = 0 or null. Discard full response.

2. **Price the top candidates** — For the top 20 vehicles with DOM > 60 (or > 1.5x the model's market avg DOM — see Gotcha #1), call `mcp__marketcheck__predict_price_with_comparables` with `vin=[VIN]`, `miles=[miles]`, `zip=[zip from vehicle location or profile]`, `dealer_type=independent` (wholesale proxy). If miles is missing from listing, use the vehicle's model-year average from step 1 stats and flag as "ESTIMATED MILES."
   → **Extract only**: predicted_price per VIN. Discard full response.

3. **Check velocity for key models** — For unique make/model combinations from step 1 (top 5-8 models), call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `state`, `inventory_type=Used`, `ranking_measure=average_days_on_market`, `date_from` (first of prior month), `date_to` (last of prior month).
   → **Extract only**: average_days_on_market, sold_count per model. Discard full response.

4. **Calculate consignment metrics** — For each vehicle:
   - **Overpriced %** = (listed_price - predicted_independent) / predicted_independent × 100. Positive = dealer is asking more than wholesale market.
   - **Expected Hammer** = predicted_independent × 0.92 (auction discount from independent retail)
   - **Buyer Margin** = predicted_independent - expected_hammer (what the buyer gains)
   - **Seller Fee Revenue** = expected_hammer × seller_fee_pct
   - **Buyer Fee Revenue** = expected_hammer × buyer_fee_pct
   - **Total Auction Revenue** = seller_fee + buyer_fee
   - **Consignment urgency** = HIGH if DOM > 90 AND overpriced > 5%; MEDIUM if DOM > 60; LOW otherwise

5. **Cluster by dealer** — Group vehicles by seller_name. Dealers with 3+ aged units = high-value consignment prospects. Calculate per dealer:
   - Total aged units (DOM > 60)
   - Total estimated auction revenue (sum of fees)
   - Average overpriced %
   - Recommended pitch: "You have X units averaging Y days on lot and Z% above wholesale. Consigning through auction could recover $A vs continued retail decline."

## Workflow: Target Specific Dealer for Consignment

Use this when the user says "check [dealer name] for consignment opportunities."

1. **Get dealer inventory** — Call `mcp__marketcheck__search_active_cars` with `dealer_id` or `source` (domain), `car_type=used`, `sort_by=dom`, `sort_order=desc`, `rows=30`, `stats=price,dom`.
   → **Extract only**: per vehicle — vin, year, make, model, trim, price, miles, dom. Plus stats: total_count, avg_dom, avg_price. Discard full response.

2. **Price aged units** — For vehicles with DOM > 60 (up to 15), call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=independent`.
   → **Extract only**: predicted_price per VIN. Discard full response.

3. **Calculate per-unit and totals** using formulas from main workflow step 4.

4. **Generate consignment pitch** — Summarize: total aged units, estimated floor plan burn ($35/day × aged units × avg excess DOM), total potential auction recovery, recommended units to consign.

## Output
Present consignment prospect list grouped by dealer. Per dealer: dealer_name, city, total_aged_units, avg_dom, estimated_floor_burn/month, total_auction_revenue_potential. Per unit: VIN, YMMT, DOM, listed_price, expected_hammer, overpriced%, urgency. Include summary: "[X] dealers with [Y] wholesale-ready units totaling ~$[Z] in potential auction fees." End with top 5 consignment calls to make.

### Output Template

```
-- Consignment Sourcing: [State/Area] — [Date] ------------------------------------

-- Prospect #1: [Dealer Name], [City] ---------------------------------------------
Aged Units: [N]  |  Avg DOM: [XX] days  |  Est. Floor Burn: $[X,XXX]/month
Total Auction Revenue Potential: $[X,XXX]

| VIN (last 8)  | Year | Make   | Model  | DOM | Listed   | Est. Hammer | Overpriced % | Urgency |
|---------------|------|--------|--------|-----|----------|-------------|------------- |---------|
| ...AB1234     | 2021 | Honda  | Accord |  95 |  $24,500 |     $19,200 |        +28%  | HIGH    |
| ...CD5678     | 2020 | Toyota | Camry  |  72 |  $21,800 |     $18,100 |        +20%  | MEDIUM  |
| ...           |  ... | ...    | ...    | ... |      ... |         ... |          ... | ...     |

Pitch: "You have [N] units averaging [X] days on lot and [Y]% above wholesale.
        Consigning through auction could recover $[A] vs continued retail decline.
        Floor plan savings alone: $[B]/month."

-- Prospect #2: [Dealer Name], [City] ---------------------------------------------
[... same format ...]

-- Summary -------------------------------------------------------------------------
[X] dealers with [Y] wholesale-ready units
Total potential auction fees: ~$[Z]
Highest-urgency dealer: [Name] ([N] units, [X] avg DOM)

-- Top 5 Calls to Make ------------------------------------------------------------
1. [Dealer] — [N] aged units, $[X] floor burn/month, pitch: [one-liner]
2. ...
```

## Self-Check (before presenting to user)

1. **Overpriced % uses predicted_independent, not predicted_franchise** — The wholesale proxy is `dealer_type=independent`. Verify no overpriced calculation uses franchise pricing (which would understate overpricing).
2. **Expected hammer = predicted_independent x 0.92** — Spot-check at least 2 vehicles. Hammer should always be less than both listed_price and predicted_price.
3. **Floor burn math is correct** — Floor burn = $35/day x units x (avg_dom - 45). Only count excess days above the 45-day "acceptable" threshold. If profile has a custom floor_plan_per_day, use that instead of $35.
4. **No $0 or null prices in output** — Every vehicle in the output has a valid listed_price > 0 and a valid predicted_price. Vehicles with missing prices were filtered in step 1.
5. **Dealers are ranked by revenue potential** — The prospect list is ordered by total_auction_revenue_potential descending (highest-value prospects first). The "Top 5 Calls" matches the top 5 dealers by this metric.
6. **Urgency labels match criteria** — HIGH = DOM > 90 AND overpriced > 5%. MEDIUM = DOM > 60. LOW = everything else. Verify at least the first and last vehicle in each dealer group.
