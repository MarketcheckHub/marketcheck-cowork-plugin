---
name: ev-lending-risk-monitor
description: >
  EV intelligence for lender sales reps. Triggers: "EV lending risk",
  "EV depreciation for lending", "should I lend on EVs",
  "EV market update for sales", "which EVs hold value",
  "EV vs ICE for lending", "EV lending programs",
  "EV residual value", "battery risk",
  understanding EV market dynamics for advising dealers
  on EV lending programs and managing EV lending risk.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# EV Lending Risk Monitor — EV Intelligence for Lender Sales Reps

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: target_states, country. If missing, ask for state. **US only** — requires `get_sold_summary`. Confirm: "Using profile: [company], [lending_type], [state]".

## User Context
Lender sales rep needs to understand EV market dynamics to: (1) advise dealers on which EV lending programs to promote, (2) identify which EV models are safe to lend on (strong residuals), and (3) flag high-risk EV segments. This is sales enablement, not portfolio risk management.

## Gotchas

1. **US-only workflow.** This skill requires `get_sold_summary` with `fuel_type_category=EV` which is US-only. For UK profiles, abort with: "EV lending risk monitor requires US sold data. For UK EV inventory counts, use the dealer-intelligence-brief skill instead."
2. **EV sample sizes are small.** In many states, monthly EV sold counts are in the low hundreds or less. Depreciation rates calculated from small samples are noisy. If any model has fewer than 10 sold units in the period, flag the metric as "low confidence" and do not classify it as SAFE/STANDARD/AVOID based on that alone.
3. **Fuel type filter naming.** Use `fuel_type_category=EV` for `get_sold_summary` but `fuel_type=Electric` for `search_active_cars`. These are different parameter names — do not mix them up.
4. **PHEVs are not EVs.** Plug-in hybrids have different depreciation curves. This skill covers BEVs (battery electric) only. Do not include PHEV data unless the user explicitly asks.
5. **Federal tax credit distortion.** EV transaction prices can be artificially depressed by $7,500 tax credit pass-throughs at point of sale. If EV prices look unusually low relative to MSRP, note this factor rather than interpreting it as poor residuals.

## Workflow: EV Market Scorecard for Sales

1. **EV penetration** — Call `mcp__marketcheck__get_sold_summary` with `state=[ST]`, `inventory_type=Used`, `fuel_type_category=EV`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=1`, `date_from=[first of prior month]`, `date_to=[last of prior month]`. Also call WITHOUT `fuel_type_category` for total market volume.
   → **Extract only**: EV sold_count, total sold_count. Calculate penetration % = EV_sold / total_sold x 100. Discard full response.

2. **EV vs ICE pricing by segment** — For SUV and Sedan body types, make 4 calls:
   - Call `mcp__marketcheck__get_sold_summary` with `state=[ST]`, `inventory_type=Used`, `fuel_type_category=EV`, `body_type=SUV`, `ranking_measure=average_sale_price`, `date_from=[first of prior month]`, `date_to=[last of prior month]`.
   - Same call with `body_type=Sedan`.
   - Same two calls WITHOUT `fuel_type_category` (all fuel types).
   → **Extract only**: avg_sale_price for EV-SUV, EV-Sedan, All-SUV, All-Sedan. Calculate EV premium per segment = (EV_avg - all_avg) / all_avg x 100. Discard full response.

3. **EV depreciation vs ICE** — Two time periods (current month and 3 months ago):
   - Call `mcp__marketcheck__get_sold_summary` with `state=[ST]`, `inventory_type=Used`, `fuel_type_category=EV`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`, `date_from=[first of prior month]`, `date_to=[last of prior month]`.
   - Same call with `date_from=[first of 3 months ago]`, `date_to=[last of 3 months ago]`.
   - Same two calls WITHOUT `fuel_type_category` for overall market baseline.
   → **Extract only**: per make/model — avg_sale_price for both periods. Calculate monthly depreciation rate = (old_price - new_price) / old_price / 3 x 100 for EV models and overall market. Discard full response.

4. **Top EV models by residual strength** — From step 3 data:
   - Rank EV models by retention (3-month price change %)
   - If model has < 10 sold units in either period, mark as "LOW CONFIDENCE"
   - Strong residuals (< 1%/month decline): **SAFE TO LEND** — standard advance rates, promote to dealers
   - Moderate (1-2%/month): **STANDARD TERMS** — normal lending parameters
   - Weak (> 2%/month): **REDUCED ADVANCE RATE or AVOID** — tighten LTV, shorter terms, or decline

5. **EV supply health** — Call `mcp__marketcheck__search_active_cars` with `state=[ST]`, `fuel_type=Electric`, `car_type=used`, `seller_type=dealer`, `stats=price,dom`, `rows=0`.
   → **Extract only**: total active EV (num_found), median_price, avg_dom from stats. Discard full response.
   - Days supply = active_EV / (monthly_EV_sold / 30). Under 30 = very tight, 30-60 = healthy, over 60 = oversupplied (depreciation risk)

6. **Sales talking points for dealers**:
   - "EV represents [X]% of used sales in [state] — growing/declining"
   - "We have competitive EV lending programs for [models with strong residuals]"
   - "Avoid stocking [models with weak residuals] — our programs have tighter terms for those"
   - "EV days supply is [X] — [tight/balanced/building] meaning [pricing power/risk]"

## Output Template

```
── EV Lending Risk Scorecard: [State] ── [Month Year] ──────

EV MARKET OVERVIEW
EV Penetration:     X.X% of used market ([X] EV / [Y] total sold)
EV Trend:           [Growing/Flat/Declining] vs 3 months ago
Active EV Supply:   [X] units | Median $XX,XXX | Avg DOM XX days
EV Days Supply:     XX days ([tight/healthy/oversupplied])

EV vs ICE PRICING
               EV Avg         All Avg        EV Premium
SUV:           $XX,XXX        $XX,XXX        +X.X%
Sedan:         $XX,XXX        $XX,XXX        +X.X%

DEPRECIATION COMPARISON (monthly rate, 3-month window)
EV Market:     -X.X%/month
Overall Market: -X.X%/month
EV Depreciation Ratio: X.Xx faster than market

EV MODEL RESIDUAL RANKINGS
Model              | 3mo Change | Rate/mo | Confidence | Lending Tier
-------------------|-----------|---------|------------|------------------
Tesla Model Y      | -X.X%     | -X.X%  | HIGH       | SAFE TO LEND
Hyundai Ioniq 5    | -X.X%     | -X.X%  | HIGH       | STANDARD TERMS
[Model]            | -X.X%     | -X.X%  | LOW        | AVOID

DEALER TALKING POINTS
- "EV represents [X]% of used sales in [state] — [growing/declining]."
- "We have competitive EV lending programs for [safe models]."
- "Use caution stocking [risky models] — our programs have tighter terms."
- "EV days supply is [X] — [interpretation]."

KEY MESSAGE: Promote lending on [safe models], use caution on [risky models],
EV share is [growing/flat/declining].

Source: MarketCheck market data, [Month Year], [State].
```

## Output
EV Market Scorecard: penetration %, volume, trend. EV vs ICE pricing comparison by segment. Depreciation comparison (monthly rate, ratio). Top EV models ranked by residual strength (SAFE/STANDARD/AVOID). Supply health metrics. Dealer talking points for EV lending programs. Key message: "Promote lending on [safe models], use caution on [risky models], EV share is [growing/flat/declining]."

## Self-Check (before presenting to user)

1. **Used `fuel_type=Electric` for search_active_cars and `fuel_type_category=EV` for get_sold_summary?** These are different parameters — mixing them up returns wrong data or errors.
2. **Sample size flags present?** Any EV model with fewer than 10 sold units in either comparison period must be marked "LOW CONFIDENCE." Do not make SAFE/AVOID recommendations on thin data.
3. **Depreciation math is directional?** A negative 3-month change means prices fell (depreciation). Verify that "strong residuals" means prices held steady (small negative or positive change), not large declines.
4. **EV premium calculation is correct?** Premium = (EV_avg - all_avg) / all_avg x 100. If the result is negative, EVs are selling BELOW the overall market — note this as "EV discount" not "negative premium."
5. **No PHEV contamination?** Verify that only BEV (battery electric) data is included. If the API returns PHEVs in the EV category, note this limitation.
6. **Tax credit context included?** If any EV model shows unusually steep depreciation (>3%/month), mention that federal/state EV tax credits may distort transaction prices downward.
