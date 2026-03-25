---
name: dealer-targeting
description: >
  Find likely buyers for upcoming auctions. Triggers: "find dealers to invite",
  "who should I target", "buyer prospecting", "dealer outreach list",
  "find auction buyers", "who needs inventory in [state]",
  "dealer targeting for next sale", "build a buyer list",
  "which dealers are likely to buy", identifying
  dealers in a DMA who are likely buyers at upcoming auction events.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Dealer Targeting — Find Buyers for Upcoming Auctions

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, target_dmas, buyer_focus, vehicle_segments, country, radius. If missing, ask minimum fields (state or zip). **US**: `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (limited — no demand data, skip D/S ratio workflows). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Auction house sales exec looking to build a list of dealers likely to BUY at upcoming auction events. These are dealers who need inventory — either because their current stock is aging (they need to wholesale trades and restock) or because their inventory mix doesn't match local demand.

## Gotchas

1. **`facets=dealer_id|0|50|2` returns dealer_id + count only** — You do NOT get dealer name, city, or state from this facet call. You must make follow-up calls per dealer_id (step 3) to get seller_name and location details. Plan for 20 follow-up calls and manage token budget accordingly.
2. **High DOM does not always mean "needs fresh inventory"** — Some dealers (consignment lots, specialty/classic dealers) intentionally carry long-DOM inventory. Check the dealer's average price and body_type mix: if avg_price > $50k and body_types include "Coupe" or "Convertible," the dealer may be a specialty lot where high DOM is normal. Deprioritize these.
3. **Franchise vs Independent behavior differs** — Franchise dealers typically buy at auction to fill used inventory gaps (trade-in shortfalls). Independents buy at auction as their primary stocking channel. Weight franchise dealers higher on mix-gap score (they buy specific segments) and independents higher on volume score (they buy broadly).
4. **Mix gap can be misleading for niche dealers** — A luxury-only dealer will show a huge mix gap vs the general market (which is dominated by sedans and SUVs). This does not mean they will buy economy sedans at auction. Filter dealer prospects by their existing price tier: if dealer avg_price > $40k, compare their mix only against the luxury segment of market demand.
5. **UK limitation** — UK profiles can get dealer inventory profiles via `search_uk_active_cars` but cannot compute demand-side scores (no `get_sold_summary`). For UK, score dealers on inventory health metrics only (DOM, volume) and skip mix-gap scoring. Note "Buyer scoring based on inventory health only — demand data unavailable for UK."

| Field | Source | Default |
|-------|--------|---------|
| State/ZIP, radius | Profile | — |
| Buyer focus (franchise/independent/both) | Profile | both |
| Vehicle segments | Profile | all |

## Workflow: DMA Buyer Prospect List

Use this when the user says "find dealers to invite" or "build a buyer list for [state]."

1. **Get dealer inventory distribution** — Call `mcp__marketcheck__search_active_cars` with `state=[XX]` (or `zip=[XXXXX]`, `radius=[N]`), `car_type=used`, `seller_type=dealer`, `facets=dealer_id|0|50|2`, `stats=dom`, `rows=0`, `price_min=1`. If `buyer_focus` is `franchise` or `independent`, add `dealer_type=[focus]` filter.
   → **Extract only**: top 50 dealer_ids with their unit counts from facets (each facet bucket has `val` = dealer_id and `count` = number of listings). Note: this call does NOT return dealer names — names come from step 3. Discard full response.

2. **Get local demand signal** — Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=15`.
   → **Extract only**: per body_type — sold_count. Calculate total sold volume. Discard full response.

3. **Profile top dealers** — For the top 20 dealers by unit count from step 1, call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `facets=body_type|0|10|1`, `stats=price,dom`, `rows=3`, `sort_by=dom`, `sort_order=desc`, `price_min=1`. This is 20 sequential API calls — budget context tokens accordingly. For each call:
   → **Extract only per dealer**: seller_name (from first listing result), city (from first listing), state, total_count (num_found), avg_dom (from stats.dom.mean), body_type mix (from facets — each bucket gives body_type name and count), top 3 aged units (vin, year, make, model, dom, price from the 3 returned rows). Check for specialty dealer signals: if avg_price > $50k and body_types are luxury-skewed, flag as "SPECIALTY — verify fit" (see Gotcha #4). Discard full response.

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

### Output Template

```
-- Buyer Targeting: [State] — [Date] -----------------------------------------------

-- Dealer Prospect List (ranked by Buyer Score) ------------------------------------
| Rank | Dealer Name        | City       | Units | Avg DOM | Score | Class       | Buying Needs           |
|------|--------------------|------------|-------|---------|-------|-------------|------------------------|
|    1 | Smith Auto Group   | Dallas     |   145 |      52 |    87 | HOT         | SUV (-14%), Pickup (-9%) |
|    2 | Valley Motors      | Austin     |    88 |      48 |    73 | HOT         | SUV (-11%)             |
|    3 | Lone Star Cars     | Houston    |   210 |      38 |    62 | WARM        | Sedan (-8%)            |
| ...  | ...                | ...        |   ... |     ... |   ... | ...         | ...                    |

-- Summary -------------------------------------------------------------------------
Hot Prospects:  [X] dealers
Warm Prospects: [Y] dealers
Watch List:     [Z] dealers
Top Buying Needs Across Market: [segment1] ([N] dealers short), [segment2] ([N] dealers short)

-- Outreach Recommendations --------------------------------------------------------
1. [Dealer Name] — Score [XX]. [N] units, [X] avg DOM. Invite to [segment] lanes.
   Talking point: "You're light on [body_type] — we have [N] units running next [day]."
2. [Dealer Name] — Score [XX]. [Specific recommendation]
3. [Dealer Name] — Score [XX]. [Specific recommendation]

-- Segment-Specific Buyer Lists (if requested) ------------------------------------
[segment] buyers: [dealer1] (gap: -[X]%), [dealer2] (gap: -[X]%), ...
```

## Self-Check (before presenting to user)

1. **Buyer scores are 0-100** — Verify no score exceeds 100 or goes below 0. Score = DOM_Score (0-40) + Volume_Score (0-30) + Mix_Gap_Score (0-30).
2. **Classification matches score thresholds** — HOT = 70-100, WARM = 50-69, WATCH = 30-49, LOW PRIORITY = <30. Every dealer's label must match its score.
3. **Mix gap uses market demand, not supply** — The "market share" in the gap calculation comes from `get_sold_summary` (demand side), NOT from `search_active_cars` (supply side). Verify the denominator is total_sold, not total_active.
4. **Dealer names are resolved** — No dealer_id numbers appear in the output table. Every row has a human-readable dealer name from the step 3 follow-up calls.
5. **Buying needs are specific** — The "Buying Needs" column shows specific body types with gap percentages, not vague labels like "various" or "mixed." Each listed segment has a gap > 5%.
6. **Specialty dealers are flagged or filtered** — Any dealer with avg_price > $50k is either excluded from the general prospect list or annotated as "SPECIALTY" to prevent sending them economy-vehicle invitations.
