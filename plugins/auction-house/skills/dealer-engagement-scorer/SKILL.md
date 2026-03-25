---
name: dealer-engagement-scorer
description: >
  Deep-dive dealer profile for auction engagement. Triggers: "tell me about [dealer]",
  "dealer profile", "should I reach out to this dealer",
  "dealer engagement analysis", "profile this dealer",
  "is this dealer a good prospect", "dealer inventory analysis",
  "what does [dealer] need", deep-dive on one specific dealer
  to understand inventory health, likely buying needs,
  and consignment opportunities.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Dealer Engagement Scorer — Profile a Specific Dealer for Auction Engagement

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, buyer_fee_pct, seller_fee_pct, country, radius. If missing, ask minimum fields. **US**: `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (inventory profile only, no demand context). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Auction house sales exec evaluating whether a specific dealer is worth pursuing — as a buyer, consigner, or both. Need inventory health, aging analysis, and a clear recommendation for engagement approach.

## Gotchas

1. **`dealer_id` vs `source` (domain)** — If the user provides a dealer name, you need to find the dealer_id first. Use `search_active_cars` with the dealer's known domain (`source=example.com`) or city+state to locate listings and extract `dealer_id` from results. Do not guess dealer_id values.
2. **Stats on empty result sets** — If a dealer has zero used inventory (all new), `stats=price,dom` will return nulls. Check `num_found > 0` before computing any scores. If zero, report "No used inventory found — dealer may be new-only or recently cleared lot."
3. **Mix alignment requires matching taxonomies** — Dealer body_type distribution (from `facets`) and market demand (from `get_sold_summary` with `ranking_dimensions=body_type`) may use different labels. Normalize both sides before computing gaps (see lane-planner Gotcha #3).
4. **DOM is listing DOM, not lot age** — The `dom` field measures days since the listing appeared online, not how long the vehicle has physically been on the lot. A dealer who relists vehicles resets DOM to zero. Look for suspiciously low DOM on old model-year vehicles as a signal of relisting.
5. **US-only scored engagement** — UK profiles can get inventory profile via `search_uk_active_cars` but cannot compute mix alignment (no `get_sold_summary` demand data). For UK, produce the inventory health section only and note "Engagement scoring requires US market data."

## Workflow: Dealer Deep-Dive

1. **Get full inventory profile** — Call `mcp__marketcheck__search_active_cars` with `dealer_id` (or `source` for web domain), `car_type=used`, `facets=body_type|0|20|1,make|0|30|1,year|0|10|1`, `stats=price,dom,miles`, `rows=0`, `price_min=1`.
   → **Extract only**: total_count (this is `num_found`), facet breakdowns (body_type, make, year — name + count from each facet bucket), stats (avg_price, median_price, avg_dom, avg_miles from stats fields). If `num_found=0`, stop and report "No used inventory found for this dealer." Discard full response.

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

### Output Template

```
-- Dealer Profile: [Dealer Name] --------------------------------------------------
Location:          [City], [State]
Total Used Units:  [N]
Avg Price:         $[XX,XXX]    |  Avg DOM: [XX] days  |  Avg Miles: [XX,XXX]

-- Inventory Health ----------------------------------------------------------------
Health Score:      [XX]/100     |  Classification: [BUYER / CONSIGNER / DUAL / LOW PRIORITY]
Engagement Score:  [XX]/100

-- Inventory Mix vs Market Demand --------------------------------------------------
| Body Type | Dealer Units | Dealer % | Market Sold % | Gap    |
|-----------|-------------|----------|---------------|--------|
| SUV       |          25 |     42%  |          35%  |   +7%  |
| Sedan     |          10 |     17%  |          28%  |  -11%  |
| Pickup    |           8 |     13%  |          22%  |   -9%  |
| ...       |         ... |      ... |           ... |    ... |

-- Aged Inventory (Top 10 by DOM) --------------------------------------------------
| VIN (last 6) | Year | Make   | Model  | Trim   | Price    | Miles  | DOM |
|--------------|------|--------|--------|--------|----------|--------|-----|
| ...A12       | 2021 | Toyota | Camry  | SE     | $22,500  | 45,200 | 112 |
| ...          |  ... | ...    | ...    | ...    |      ... |    ... | ... |

-- Recommended Approach ------------------------------------------------------------
Type:   [BUYER / CONSIGNER / DUAL]
Pitch:  "[Specific talking points]"
Est. Revenue: $[X,XXX] (consignment fees) + $[X,XXX] (buyer fees) = $[X,XXX] total
```

## Self-Check (before presenting to user)

1. **Health score is 0-100** — Verify the score did not go negative (floor at 0). Confirm deductions: 2 pts per % of inventory over 60 DOM + 1 pt per day of avg DOM above 35.
2. **Engagement classification matches thresholds** — BUYER requires health > 70 AND gap > 10%. CONSIGNER requires health < 50 AND 5+ units over 60 DOM. DUAL requires health 50-70. LOW PRIORITY requires health > 80 AND gap < 10%. Verify the assigned label matches the computed scores.
3. **Mix gap percentages sum correctly** — Dealer % column should sum to 100%. Market Sold % column should sum to 100%. Gap = Market % - Dealer % for each row.
4. **Aged units list is sorted by DOM descending** — The top 10 units should have the highest DOM values. Confirm no unit with DOM < 60 appears above a unit with DOM > 60.
5. **Revenue estimate is realistic** — Consignment fee revenue should be based on expected hammer (not listed price). Buyer fee revenue is speculative — note it as "estimated based on typical purchase volume for this dealer size."
6. **No $0 prices displayed** — Any vehicle with price = 0 or null is excluded from aged inventory list and revenue calculations.
