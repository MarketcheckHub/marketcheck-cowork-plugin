---
name: lane-planner
description: >
  This skill should be used when the user asks "what should I run this week",
  "lane planning", "auction lineup", "what sells at auction",
  "which categories to feature", "lane optimization",
  "sale day planning", "what segments have the best sell-through",
  "plan my lanes for next sale", or needs help deciding which vehicle
  categories to prioritize in upcoming auction events based on
  demand signals and sell-through predictions.
version: 0.1.0
---

# Lane Planner — Optimize Auction Lanes by Demand Signals

## Profile
Load `~/.claude/marketcheck/auction-house-profile.json` if exists. Extract: zip/postcode, state/region, target_dmas, vehicle_segments, avg_weekly_lanes, target_sell_through_pct, buyer_fee_pct, seller_fee_pct, country, radius. If missing, ask minimum fields (state). **US**: `get_sold_summary`, `search_active_cars`. **UK**: `search_uk_active_cars` only (limited — no demand data, skip sell-through prediction). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Lane manager or sales exec planning which vehicle segments to feature in upcoming auction events. Goal: maximize sell-through rate and bidder engagement by featuring segments with strong demand and limited supply.

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

4. **Get current supply snapshot** — Call `mcp__marketcheck__search_active_cars` with `state`, `car_type=used`, `seller_type=dealer`, `facets=body_type|0|20|1`, `stats=price,dom`, `rows=0`.
   → **Extract only**: per body_type — active supply count (from facets), median_price, avg_dom (from stats). Discard full response.

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
Present lane lineup table: Segment/Model, Recommended Units, Predicted Sell-Through %, Avg Expected Hammer, Fee Revenue Estimate, Demand Signal (HOT/WARM/COOL/DECLINING), Volume Trend (↑/↓/→). Include event summary: "Recommended [X] total lanes. Predicted overall sell-through: [Y]%. Estimated total fee revenue: $[Z]." End with top 3 sourcing priorities ("source more SUVs — they'll move") and any segments to reduce ("avoid overloading sedans — soft demand").
