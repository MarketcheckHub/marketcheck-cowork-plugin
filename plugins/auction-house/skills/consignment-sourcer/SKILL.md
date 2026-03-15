---
name: consignment-sourcer
description: >
  This skill should be used when the user asks to "find consignment leads",
  "who has aged inventory", "wholesale sourcing", "cars to bring to auction",
  "find vehicles to consign", "dealer wholesale opportunities",
  "aged inventory in my market", "who should I call for consignments",
  "sourcing for next sale", or needs help identifying dealers sitting on
  aged, overpriced inventory that should be wholesaled through auction.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Consignment Sourcer — Find Dealers with Wholesale-Ready Inventory

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, target_dmas, vehicle_segments, consigner_types, seller_fee_pct, buyer_fee_pct, country, radius. If missing, ask minimum fields (state or zip). **US**: `search_active_cars`, `predict_price_with_comparables`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (no ML pricing — use comp median; skip velocity workflows). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Auction house consignment rep or sales exec looking for dealers with aged, overpriced inventory they should wholesale through auction rather than continuing to retail. The goal is to fill upcoming auction lanes with quality consigned inventory.

| Field | Source | Default |
|-------|--------|---------|
| State/ZIP, radius | Profile | — |
| Seller fee % | Profile | 3% |
| Buyer fee % | Profile | 5% |
| Vehicle segments | Profile | all |

## Workflow: Find Aged Inventory Across Market

Use this when the user says "who has aged inventory" or "find consignment leads."

1. **Search for aged inventory** — Call `mcp__marketcheck__search_active_cars` with `state` (or `zip`+`radius`), `car_type=used`, `seller_type=dealer`, `sort_by=dom`, `sort_order=desc`, `rows=50`. If vehicle_segments specified, add `body_type` filter.
   → **Extract only**: per vehicle — vin, year, make, model, trim, price, miles, dom, seller_name, seller_city, dealer_id. Discard full response.

2. **Price the top candidates** — For the top 20 vehicles with DOM > 60, call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip` (vehicle's location or profile zip), `dealer_type=independent` (wholesale proxy).
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
