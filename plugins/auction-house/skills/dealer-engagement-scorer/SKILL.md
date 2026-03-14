---
name: dealer-engagement-scorer
description: >
  This skill should be used when the user asks to "tell me about [dealer]",
  "dealer profile", "should I reach out to this dealer",
  "dealer engagement analysis", "profile this dealer",
  "is this dealer a good prospect", "dealer inventory analysis",
  "what does [dealer] need", or needs a deep-dive on one specific dealer
  to understand their inventory health, likely buying needs,
  and consignment opportunities.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Dealer Engagement Scorer — Profile a Specific Dealer for Auction Engagement

## Profile
Load `~/.claude/marketcheck/auction-house-profile.json` if exists. Extract: zip/postcode, state/region, buyer_fee_pct, seller_fee_pct, country, radius. If missing, ask minimum fields. **US**: `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (inventory profile only, no demand context). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Auction house sales exec evaluating whether a specific dealer is worth pursuing — as a buyer, consigner, or both. Need inventory health, aging analysis, and a clear recommendation for engagement approach.

## Workflow: Dealer Deep-Dive

1. **Get full inventory profile** — Call `mcp__marketcheck__search_active_cars` with `dealer_id` (or `source` for web domain), `car_type=used`, `facets=body_type|0|20|1,make|0|30|1,year|0|10|1`, `stats=price,dom,miles`, `rows=0`.
   → **Extract only**: total_count, facet breakdowns (body_type, make, year), stats (avg_price, median_price, avg_dom, avg_miles). Discard full response.

2. **Get aged inventory** — Call `mcp__marketcheck__search_active_cars` with same dealer filter, `sort_by=dom`, `sort_order=desc`, `rows=10`.
   → **Extract only**: per vehicle — vin, year, make, model, trim, price, miles, dom. Discard full response.

3. **Get local market demand** — Call `mcp__marketcheck__get_sold_summary` with `state` (dealer's state from results), `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=10`.
   → **Extract only**: per body_type — sold_count. Discard full response.

4. **Score and classify**:

   **Inventory Health Score** (0-100):
   - Start at 100
   - Deduct 2 points per % of inventory over 60 DOM
   - Deduct 1 point per day of avg DOM above 35
   - Minimum 0

   **Mix Alignment**:
   - Compare dealer body_type % vs market sold body_type %
   - Total gap = sum of |dealer_share - market_share| / 2
   - Gap > 15% = significant misalignment

   **Engagement Classification**:
   - **BUYER** — Health score > 70, mix gap > 10% (healthy lot but needs different inventory → will buy at auction to restock)
   - **CONSIGNER** — Health score < 50, 5+ units over 60 DOM (aging lot → should wholesale through auction)
   - **DUAL** — Health score 50-70, has both aging units AND mix gaps (both buy and sell at auction)
   - **LOW PRIORITY** — Health score > 80, mix gap < 10% (well-run lot, low urgency)

   **Engagement Score** (0-100):
   - Buyer potential: (mix_gap_percentile × 30) + (volume × 20)
   - Consigner potential: (aged_units_percentile × 30) + (overpriced_pct × 20)
   - Combined: max(buyer, consigner)

5. **Generate recommended approach**:
   - BUYER: "Invite to upcoming [segment] lanes. They need [body_types] based on market demand."
   - CONSIGNER: "Pitch consignment for [X] aged units. Estimated floor plan savings: $[Y]/month."
   - DUAL: "Combined approach — consign [X] aged units, invite to buy [segments]."

## Output
Dealer profile card: name, city, state, total_units, avg_price, avg_dom, health_score, engagement_type, engagement_score. Inventory mix breakdown (body_type with dealer % vs market %). Aged units list (top 10 by DOM with price and miles). Recommended approach with specific talking points. Estimated auction revenue potential (consignment fees + buyer fees from expected purchases).
