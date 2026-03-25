---
name: lane-planner
description: >
  Auction lane optimization by demand signals. Triggers: "what should I run this week",
  "lane planning", "auction lineup", "what sells at auction",
  "which categories to feature", "lane optimization",
  "sale day planning", "what segments have the best sell-through",
  "plan my lanes for next sale", deciding which vehicle
  categories to prioritize in upcoming auction events based on
  demand signals and sell-through predictions.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Lane Planner — Optimize Auction Lanes by Demand Signals

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, target_dmas, vehicle_segments, avg_weekly_lanes, target_sell_through_pct, buyer_fee_pct, seller_fee_pct, country, radius. If missing, ask minimum fields (state). **US**: `get_sold_summary`, `search_active_cars`. **UK**: `search_uk_active_cars` only (limited — no demand data, skip sell-through prediction). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Lane manager or sales exec planning which vehicle segments to feature in upcoming auction events. Goal: maximize sell-through rate and bidder engagement by featuring segments with strong demand and limited supply.

## Gotchas

1. **`get_sold_summary` date ranges are inclusive** — If you pass `date_from=2026-02-01` and `date_to=2026-02-28`, February 29 (leap year) is excluded. Always compute the correct last day of the month.
2. **Facet counts are approximate at high cardinality** — When using `facets=body_type|0|20|1` the counts are exact only when the total result set is under ~100k. For large states (TX, CA, FL) the body_type facet is fine, but `make|0|50|1` may show rounded counts. Never treat facet counts as exact inventory figures — label them "approx." when total exceeds 50k.
3. **`ranking_dimensions=body_type` can return inconsistent labels** — The API may return "Sport Utility Vehicle" vs "SUV" depending on source. Normalize all body_type values before comparing demand to supply: map "Sport Utility Vehicle" to "SUV", "Passenger Van" to "Van", "Crew Cab Pickup" to "Pickup", etc.
4. **D/S ratio is meaningless without volume floors** — A model with 3 sold and 1 active has D/S = 3.0 (looks HOT) but the sample is too small. Require minimum 20 sold in the period AND minimum 10 active supply before computing D/S. Below that, label the segment "INSUFFICIENT DATA" instead of assigning a demand signal.
5. **US-only limitation** — Lane planning requires `get_sold_summary` for demand data. UK profiles can only see current supply via `search_uk_active_cars`; skip sell-through prediction entirely and note "Demand data unavailable for UK — supply snapshot only."

| Field | Source | Default |
|-------|--------|---------|
| State/ZIP | Profile | — |
| Avg weekly lanes | Profile | ask |
| Target sell-through % | Profile | 85% |
| Buyer fee %, seller fee % | Profile | 5%, 3% |

## Workflow: Lane Lineup Recommendation

Use this when the user says "plan my lanes" or "what should I run this week."

1. **Get demand by segment (current month)** — Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=10`.
   → **Extract only**: per body_type — sold_count, average_sale_price, average_days_on_market. Discard full response.

2. **Get demand by segment (prior month for trend)** — Same call with date range shifted back one month.
   → **Extract only**: per body_type — sold_count. Discard full response.

3. **Get fastest-turning models** — Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_days_on_market`, `ranking_order=asc`, `top_n=20`, same date range as step 1.
   → **Extract only**: per make/model — average_days_on_market, sold_count. Discard full response.

4. **Get current supply snapshot** — Call `mcp__marketcheck__search_active_cars` with `state`, `car_type=used`, `seller_type=dealer`, `facets=body_type|0|20|1`, `stats=price,dom`, `rows=0`, `price_min=1`.
   → **Extract only**: per body_type — active supply count (from facets), median_price, avg_dom (from stats). Normalize body_type labels (see Gotcha #3). Discard full response.

5. **Calculate lane metrics per segment**:
   - **D/S Ratio** = monthly_sold / active_supply
   - **Volume Trend** = (current_month_sold - prior_month_sold) / prior_month_sold × 100
   - **Predicted Sell-Through %**:
     - D/S > 2.0 = 90-95% (HIGH demand)
     - D/S 1.0-2.0 = 75-90% (MODERATE)
     - D/S 0.5-1.0 = 60-75% (SOFT)
     - D/S < 0.5 = 40-60% (WEAK)
   - **Expected Hammer** = avg_sale_price × 0.88 (auction discount from retail)
   - **Revenue Per Unit** = expected_hammer × (buyer_fee_pct + seller_fee_pct) / 100
   - **Lane Revenue Forecast** = recommended_units × revenue_per_unit × predicted_sell_through / 100
   - **Demand Signal**: HOT (D/S > 2.0 + trend > 0), WARM (D/S 1.0-2.0), COOL (D/S < 1.0), DECLINING (any D/S + trend < -10%)

6. **Allocate lane slots** — If avg_weekly_lanes is known, distribute proportionally:
   - HOT segments: 40% of lanes
   - WARM segments: 35% of lanes
   - COOL segments: 15% of lanes
   - Specialty/niche: 10% of lanes
   - Round to whole numbers. If no lane count, recommend proportions only.

## Workflow: Model-Level Lane Planning

Use this when the user asks "which specific models should I feature" or "what are the hottest auction vehicles."

1. Run steps 1-3 from main workflow above.
2. For top 10 fastest-turning models, also call `mcp__marketcheck__search_active_cars` with `make`, `model`, `state`, `car_type=used`, `stats=price`, `rows=0`.
   → **Extract only**: total_count (supply), median_price. Discard full response.
3. Calculate per model: D/S ratio, predicted sell-through, expected hammer, fee revenue.
4. Rank by combined score: (D/S × 40) + (volume × 30) + (sell_through × 30).

## Output
Present lane lineup table: Segment/Model, Recommended Units, Predicted Sell-Through %, Avg Expected Hammer, Fee Revenue Estimate, Demand Signal (HOT/WARM/COOL/DECLINING), Volume Trend (arrow up/down/flat). Include event summary: "Recommended [X] total lanes. Predicted overall sell-through: [Y]%. Estimated total fee revenue: $[Z]." End with top 3 sourcing priorities ("source more SUVs — they'll move") and any segments to reduce ("avoid overloading sedans — soft demand").

### Output Template

```
-- Lane Lineup: [State] — Week of [Date] ------------------------------------------

| Segment   | Rec. Units | Est. Sell-Through | Avg Hammer | Fee Rev/Unit | Lane Rev | Signal    | Trend |
|-----------|------------|-------------------|------------|--------------|----------|-----------|-------|
| SUV       |         35 |              92%  |    $24,500 |       $1,960 |  $63,504 | HOT       |  +12% |
| Pickup    |         30 |              88%  |    $28,200 |       $2,256 |  $59,561 | HOT       |   +8% |
| Sedan     |         15 |              72%  |    $18,400 |       $1,472 |  $15,898 | COOL      |   -3% |
| ...       |        ... |               ... |        ... |          ... |      ... | ...       |   ... |

-- Event Summary ------------------------------------------------------------------
Total Lanes:            [X]
Predicted Sell-Through: [Y]%
Est. Total Fee Revenue: $[Z]

-- Sourcing Priorities -------------------------------------------------------------
1. Source more [segment] — [reason]
2. Source more [segment] — [reason]
3. Reduce [segment] — [reason]
```

## Self-Check (before presenting to user)

1. **Date math is correct** — Verify date_from and date_to produce complete calendar months (no partial months, no future dates). Confirm the "prior month" is truly the last complete month relative to today's date from `# currentDate`.
2. **D/S ratios have volume floors** — Every segment with a D/S ratio displayed has at least 20 sold units AND 10 active supply units. Any segment below these thresholds is labeled "INSUFFICIENT DATA" rather than given a demand signal.
3. **Body type labels are normalized** — No raw API labels like "Sport Utility Vehicle" appear; all are mapped to standard short labels (SUV, Pickup, Sedan, Coupe, Van, Wagon, Hatchback, Convertible).
4. **Lane allocations sum to total** — If avg_weekly_lanes is known, the recommended units per segment sum exactly to that total. No rounding errors that leave units unallocated.
5. **Fee revenue math checks out** — Verify: fee_revenue_per_unit = expected_hammer x (buyer_fee_pct + seller_fee_pct) / 100. Lane_revenue = rec_units x fee_revenue_per_unit x sell_through / 100. Spot-check at least two rows.
6. **No future data referenced** — All API calls use date ranges in the past. No call uses the current month if it is incomplete.
