---
name: dealer-targeting
description: >
  This skill should be used when the user asks to "find dealers to invite",
  "who should I target", "buyer prospecting", "dealer outreach list",
  "find auction buyers", "who needs inventory in [state]",
  "dealer targeting for next sale", "build a buyer list",
  "which dealers are likely to buy", or needs help identifying
  dealers in a DMA who are likely buyers at upcoming auction events.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Dealer Targeting — Find Buyers for Upcoming Auctions

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, target_dmas, buyer_focus, vehicle_segments, country, radius. If missing, ask minimum fields (state or zip). **US**: `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (limited — no demand data, skip D/S ratio workflows). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Auction house sales exec looking to build a list of dealers likely to BUY at upcoming auction events. These are dealers who need inventory — either because their current stock is aging (they need to wholesale trades and restock) or because their inventory mix doesn't match local demand.

| Field | Source | Default |
|-------|--------|---------|
| State/ZIP, radius | Profile | — |
| Buyer focus (franchise/independent/both) | Profile | both |
| Vehicle segments | Profile | all |

## Workflow: DMA Buyer Prospect List

Use this when the user says "find dealers to invite" or "build a buyer list for [state]."

1. **Get dealer inventory distribution** — Call `mcp__marketcheck__search_active_cars` with `state` (or `zip`+`radius`), `car_type=used`, `seller_type=dealer`, `facets=dealer_id|0|50|2`, `stats=dom`, `rows=0`. If `buyer_focus` is not "both", add `dealer_type` filter.
   → **Extract only**: top 50 dealer_ids with their unit counts from facets. Discard full response.

2. **Get local demand signal** — Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=15`.
   → **Extract only**: per body_type — sold_count. Calculate total sold volume. Discard full response.

3. **Profile top dealers** — For the top 20 dealers by unit count from step 1, call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `facets=body_type|0|10|1`, `stats=price,dom`, `rows=3`, `sort_by=dom`, `sort_order=desc`.
   → **Extract only per dealer**: seller_name, city, state, total_count, avg_dom (from stats), body_type mix (from facets), top 3 aged units (VIN, year, make, model, DOM, price). Discard full response.

4. **Score each dealer** — For each dealer compute:
   - **Avg DOM Score** (0-40): Percentile rank of avg DOM among all 20 dealers × 40. Higher DOM = more likely to need fresh inventory from auction.
   - **Volume Score** (0-30): Percentile rank of total unit count × 30. Larger dealers = repeat auction buyers.
   - **Mix Gap Score** (0-30): Compare dealer's body_type distribution vs market demand distribution from step 2. Sum of absolute gaps / 2 × 30. Larger gap = dealer needs what they don't have.
   - **Buyer Score** = Avg DOM Score + Volume Score + Mix Gap Score (0-100)

5. **Classify dealers**:
   - Score 70-100: **HOT PROSPECT** — High aging + large lot + mix mismatch. Priority outreach.
   - Score 50-69: **WARM PROSPECT** — Moderate signals. Worth contacting.
   - Score 30-49: **WATCH LIST** — Low urgency but may be regular buyer.
   - Score < 30: **LOW PRIORITY** — Skip for now.

## Workflow: Segment-Specific Buyer Targeting

Use this when the user says "who needs SUVs" or "find truck buyers."

1. **Get demand for target segment** — Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `body_type=[segment]`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=15`, date range for prior month.
   → **Extract only**: top models by sold volume in that segment. Discard full response.

2. **Find dealers light on that segment** — Call `mcp__marketcheck__search_active_cars` with `state`, `car_type=used`, `seller_type=dealer`, `body_type=[segment]`, `facets=dealer_id|0|30|1`, `rows=0`.
   → **Extract only**: dealer_ids with their segment count. Discard full response.

3. **Cross-reference with total inventory** — For dealers from step 2, call `mcp__marketcheck__search_active_cars` with `dealer_id`, `car_type=used`, `rows=0`.
   → **Extract only**: total_count per dealer. Discard full response.

4. **Calculate segment gap** — For each dealer:
   - Dealer segment share = segment_count / total_count × 100
   - Market segment share = segment_sold / total_sold × 100 (from DMA data)
   - Gap = market share - dealer share
   - Dealers with gap > 10% AND total inventory > 30 = strong prospects for that segment

## Output
Present ranked dealer prospect table: Rank, Dealer Name, City, Total Units, Avg DOM, Buyer Score, Classification (HOT/WARM/WATCH), Likely Buying Needs (body types with gaps). Include summary: "[X] hot prospects, [Y] warm prospects in [state]. Top buying needs: [segments]." End with 3 specific outreach recommendations.
