---
name: depreciation-tracker
description: >
  This skill should be used when the user asks about "depreciation rate",
  "value retention", "which cars hold value", "which cars are losing value fastest",
  "depreciation curve for [model]", "residual trends",
  "fast depreciators", "consignment urgency by depreciation",
  or needs to understand how quickly vehicles are losing value,
  which affects consignment timing and expected hammer prices.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Depreciation Tracker — Value Erosion Intelligence for Auction Timing

## Profile
Load `~/.claude/marketcheck/auction-house-profile.json` if exists. Extract: state/region, target_dmas, vehicle_segments, country. If missing, ask for state. **US**: `get_sold_summary`. **UK**: Not available (no sold data). Confirm: "Using profile: [company], [state]".

## User Context
Auction house professional tracking depreciation to optimize consignment timing and set realistic reserve expectations. Fast-depreciating vehicles need faster consignment-to-sale cycles. Slow depreciators can afford more time in the pipeline.

| Field | Source | Default |
|-------|--------|---------|
| State | Profile or user input | — |
| Vehicle segments | Profile | all |

## Workflow: Make/Model Depreciation Curve

Use this when the user asks "depreciation curve for [make/model]" or "how fast is [model] losing value."

1. **Get current period pricing** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `state`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `date_from` (first of current month - 1), `date_to` (last of current month - 1).
   → **Extract only**: average_sale_price, sold_count. Discard full response.

2. **Get 3-month-ago pricing** — Same call with dates shifted back 3 months.
   → **Extract only**: average_sale_price, sold_count. Discard full response.

3. **Get 6-month-ago pricing** — Same call with dates shifted back 6 months.
   → **Extract only**: average_sale_price, sold_count. Discard full response.

4. **Calculate depreciation metrics**:
   - **3-month change %** = (current - 3mo_ago) / 3mo_ago × 100
   - **Monthly rate** = 3-month change / 3
   - **Annualized rate** = monthly rate × 12
   - **Classification**:
     - Monthly rate > 2%: FAST DEPRECIATION — consign immediately, lower reserves
     - Monthly rate 1-2%: MODERATE — standard 2-week pipeline acceptable
     - Monthly rate < 1%: SLOW — can hold in pipeline, strong residuals

5. **Auction timing recommendation**:
   - FAST: "Every week this vehicle sits costs ~$[X] in value loss. Prioritize for next available sale."
   - MODERATE: "Standard 2-week consignment pipeline is acceptable. Expected value loss: ~$[X]."
   - SLOW: "This vehicle holds value well. No urgency on timing."

## Workflow: Fastest/Slowest Depreciators in Market

Use this when the user asks "which cars are losing value fastest" or "depreciation rankings."

1. **Current period** — Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=30`, current month.
   → **Extract only**: per model — average_sale_price, sold_count. Discard full response.

2. **3-month-ago period** — Same call with shifted dates.
   → **Extract only**: per model — average_sale_price, sold_count. Discard full response.

3. **Calculate and rank** — For models with 50+ sold in both periods:
   - Monthly depreciation rate = (current - 3mo) / 3mo / 3 × 100
   - Sort by rate: fastest depreciators first

4. **Segment-level view** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, current + 3mo ago.
   - Calculate per segment depreciation rate.

## Workflow: Brand Residual Ranking

1. Current + 6-month ago pricing by make via `get_sold_summary`.
2. Calculate 6-month retention % per brand.
3. Tier: Tier 1 (> 98% retention), Tier 2 (95-98%), Tier 3 (90-95%), Tier 4 (< 90%).

## Output
Depreciation curve table: Period, Avg Sale Price, Change %, Monthly Rate. Classification: FAST/MODERATE/SLOW with auction timing recommendation. For rankings: sorted table of models with depreciation rate, volume, and consignment urgency signal. Segment summary. Brand residual tiers.
