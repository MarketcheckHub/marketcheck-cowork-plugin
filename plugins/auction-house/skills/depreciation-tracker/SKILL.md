---
name: depreciation-tracker
description: >
  Value erosion intelligence for auction timing. Triggers: "depreciation rate",
  "value retention", "which cars hold value", "which cars are losing value fastest",
  "depreciation curve for [model]", "residual trends",
  "fast depreciators", "consignment urgency by depreciation",
  understanding how quickly vehicles are losing value,
  which affects consignment timing and expected hammer prices.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Depreciation Tracker — Value Erosion Intelligence for Auction Timing

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: state/region, target_dmas, vehicle_segments, country. If missing, ask for state. **US**: `get_sold_summary`. **UK**: Not available (no sold data). Confirm: "Using profile: [company], [state]".

## User Context
Auction house professional tracking depreciation to optimize consignment timing and set realistic reserve expectations. Fast-depreciating vehicles need faster consignment-to-sale cycles. Slow depreciators can afford more time in the pipeline.

## Gotchas

1. **US-only skill** — Depreciation tracking requires `get_sold_summary` with date-ranged pricing. UK has no sold data. If a UK profile triggers this skill, respond: "Depreciation tracking is available for US markets only."
2. **Mix shift inflates apparent depreciation** — If cheaper trims gain market share over time, the average sale price drops even if per-trim values are stable. This is mix shift, not depreciation. For critical models, use `ranking_dimensions=make,model,trim` to isolate trim-level trends. Flag any model where trim composition changed significantly between periods.
3. **Seasonal patterns masquerade as depreciation** — Convertible and sports car prices drop in fall/winter and recover in spring. 4WD truck prices spike in winter. A 3-month comparison that spans a seasonal boundary will show false depreciation or appreciation. Always note the months being compared and flag known seasonal segments.
4. **Volume floor prevents noise** — Models with fewer than 50 sold units in a period produce unreliable averages. The workflow enforces `sold_count > 50` for both periods. Below this threshold, report "INSUFFICIENT VOLUME — trend unreliable" rather than computing a rate.
5. **Annualized rate assumes linear depreciation** — The formula `monthly_rate x 12` assumes constant monthly depreciation, which is rarely true (depreciation accelerates in the first year, then slows). Present the annualized rate as "at current pace" and caution that it is a projection, not a guarantee.

| Field | Source | Default |
|-------|--------|---------|
| State | Profile or user input | — |
| Vehicle segments | Profile | all |

## Workflow: Make/Model Depreciation Curve

Use this when the user asks "depreciation curve for [make/model]" or "how fast is [model] losing value."

1. **Get current period pricing** — Call `mcp__marketcheck__get_sold_summary` with `make=[make]`, `model=[model]`, `state=[XX]`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `date_from=[YYYY-MM-01]` (first of prior complete month), `date_to=[YYYY-MM-DD]` (last of prior complete month). Never use the current incomplete month.
   → **Extract only**: average_sale_price, sold_count. If sold_count < 50, flag "LOW VOLUME — trend may be unreliable" (see Gotcha #4). Discard full response.

2. **Get 3-month-ago pricing** — Same call with `date_from` and `date_to` shifted back exactly 3 months. Example: if current period = Feb 2026, then 3-month-ago = Nov 2025.
   → **Extract only**: average_sale_price, sold_count. Discard full response.

3. **Get 6-month-ago pricing** — Same call with `date_from` and `date_to` shifted back exactly 6 months. Example: if current period = Feb 2026, then 6-month-ago = Aug 2025.
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

1. **Current period** — Call `mcp__marketcheck__get_sold_summary` with `state=[XX]`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=30`, `date_from=[first of prior complete month]`, `date_to=[last of prior complete month]`.
   → **Extract only**: per model — make, model, average_sale_price, sold_count. Discard full response.

2. **3-month-ago period** — Same call with `date_from` and `date_to` shifted back 3 months.
   → **Extract only**: per model — make, model, average_sale_price, sold_count. Discard full response.

3. **Calculate and rank** — For models present in BOTH periods with 50+ sold in EACH period:
   - Monthly depreciation rate = (current_avg - 3mo_avg) / 3mo_avg / 3 x 100
   - Sort by rate: fastest depreciators first (most negative monthly rate at top)
   - Models below the 50-sold threshold in either period: exclude and note "[N] models excluded — insufficient volume"

4. **Segment-level view** — Call `mcp__marketcheck__get_sold_summary` with `state=[XX]`, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `date_from=[current period]`, `date_to=[current period end]`. Then same call with 3-month-ago dates.
   - Calculate per segment depreciation rate. Note seasonal segments (see Gotcha #3).

## Workflow: Brand Residual Ranking

1. **Current period by brand** — Call `mcp__marketcheck__get_sold_summary` with `state=[XX]`, `inventory_type=Used`, `ranking_dimensions=make`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=25`, `date_from=[first of prior complete month]`, `date_to=[last of prior complete month]`.
   → **Extract only**: per make — average_sale_price, sold_count. Discard full response.

2. **6-month-ago period by brand** — Same call with dates shifted back 6 months.
   → **Extract only**: per make — average_sale_price, sold_count. Discard full response.

3. **Calculate 6-month retention %** per brand = (current_avg / 6mo_ago_avg) x 100. Only include brands with 100+ sold in both periods.

4. **Tier assignment**: Tier 1 (> 98% retention), Tier 2 (95-98%), Tier 3 (90-95%), Tier 4 (< 90%).

## Output
Depreciation curve table: Period, Avg Sale Price, Change %, Monthly Rate. Classification: FAST/MODERATE/SLOW with auction timing recommendation. For rankings: sorted table of models with depreciation rate, volume, and consignment urgency signal. Segment summary. Brand residual tiers.

### Output Template — Single Model Curve

```
-- Depreciation Curve: [Year] [Make] [Model] — [State] ----------------------------

| Period          | Avg Sale Price | vs Current | Monthly Rate | Volume |
|-----------------|--------------- |------------|------------- |--------|
| [Current month] |        $28,400 |        --  |          --  |    320 |
| [3 months ago]  |        $29,800 |      -4.7% |      -1.57%  |    295 |
| [6 months ago]  |        $31,200 |      -9.0% |      -1.50%  |    310 |

Classification:    MODERATE DEPRECIATION
Monthly Rate:      -1.5% (at current pace)
Annualized Rate:   -18.0% (projection — assumes linear, see caveats)
Weekly Value Loss:  ~$107

-- Auction Timing Recommendation ---------------------------------------------------
"Standard 2-week consignment pipeline is acceptable. Expected value loss during
pipeline: ~$214. No urgency premium needed on reserves."
```

### Output Template — Market Rankings

```
-- Fastest/Slowest Depreciators: [State] — [Month Year] ---------------------------

FASTEST DEPRECIATORS (consign immediately):
| Rank | Make/Model          | Monthly Rate | 3mo Change | Volume | Urgency          |
|------|---------------------|------------- |------------|--------|------------------|
|    1 | [Make] [Model]      |      -2.8%   |      -8.4% |    180 | CONSIGN NOW      |
|    2 | [Make] [Model]      |      -2.3%   |      -6.9% |    220 | CONSIGN NOW      |
| ...  | ...                 |          ... |        ... |    ... | ...              |

SLOWEST DEPRECIATORS (strong residuals, can hold):
| Rank | Make/Model          | Monthly Rate | 3mo Change | Volume | Urgency          |
|------|---------------------|------------- |------------|--------|------------------|
|    1 | [Make] [Model]      |      -0.3%   |      -0.9% |    410 | NO RUSH          |
| ...  | ...                 |          ... |        ... |    ... | ...              |

-- Segment Summary -----------------------------------------------------------------
| Segment  | Monthly Rate | 3mo Change | Seasonal Flag |
|----------|------------- |------------|---------------|
| SUV      |      -1.2%   |      -3.6% |               |
| Pickup   |      -0.8%   |      -2.4% | Winter demand |
| ...      |          ... |        ... | ...           |

-- Brand Residual Tiers -----------------------------------------------------------
Tier 1 (> 98%): [brands]
Tier 2 (95-98%): [brands]
Tier 3 (90-95%): [brands]
Tier 4 (< 90%): [brands]
```

## Self-Check (before presenting to user)

1. **Date periods are complete calendar months** — No partial months, no future months. The "current period" is the last fully complete month, not the current calendar month.
2. **Volume thresholds enforced** — Single-model curves require 50+ sold per period. Market rankings require 50+ sold in BOTH periods. Brand tiers require 100+ sold in both periods. Models below thresholds are excluded, not shown with asterisks.
3. **Monthly rate sign is correct** — Depreciation should produce a NEGATIVE monthly rate. A positive rate means appreciation (prices going up). If most models show appreciation, note this is unusual and may indicate a supply shortage or seasonal effect.
4. **Annualized rate caveat is present** — Every annualized rate must include the disclaimer "at current pace" or "assumes linear progression." Never present annualized rates as guaranteed outcomes.
5. **Seasonal flags are applied** — If the analysis spans Oct-Mar, flag 4WD/AWD and truck segments. If Apr-Sep, flag convertibles and sports cars. The Seasonal Flag column should never be entirely empty.
6. **US-only confirmation** — If the profile country is UK, the skill should have exited with "Depreciation tracking is available for US markets only." Verify no UK data was accidentally processed.
