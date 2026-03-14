---
name: ev-lending-risk-monitor
description: >
  This skill should be used when the user asks about "EV lending risk",
  "EV depreciation for lending", "should I lend on EVs",
  "EV market update for sales", "which EVs hold value",
  "EV vs ICE for lending", "EV lending programs",
  "EV residual value", "battery risk",
  or needs to understand EV market dynamics specifically for
  advising dealers on EV lending programs and managing EV lending risk.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# EV Lending Risk Monitor — EV Intelligence for Lender Sales Reps

## Profile
Load `~/.claude/marketcheck/lender-sales-profile.json` if exists. Extract: target_states, country. If missing, ask for state. **US only** — requires `get_sold_summary`. Confirm: "Using profile: [company], [lending_type], [state]".

## User Context
Lender sales rep needs to understand EV market dynamics to: (1) advise dealers on which EV lending programs to promote, (2) identify which EV models are safe to lend on (strong residuals), and (3) flag high-risk EV segments. This is sales enablement, not portfolio risk management.

## Workflow: EV Market Scorecard for Sales

1. **EV penetration** — Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `fuel_type_category=EV`, `ranking_measure=sold_count`, current month. Also call without fuel_type filter for total market.
   → **Extract only**: EV sold_count, total sold_count. Calculate penetration %. Discard full response.

2. **EV vs ICE pricing by segment** — For SUV and Sedan body types:
   - Call `mcp__marketcheck__get_sold_summary` with `state`, `fuel_type_category=EV`, `body_type=[type]`, `ranking_measure=average_sale_price`.
   - Same call without fuel_type (ICE/all).
   → **Extract only**: avg_sale_price for EV and all. Calculate EV premium = (EV_avg - all_avg) / all_avg × 100. Discard full response.

3. **EV depreciation vs ICE** — Current period and 3 months ago:
   - `get_sold_summary` with `fuel_type_category=EV`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, current + 3mo ago.
   - Same without fuel_type filter.
   → **Extract only**: avg_sale_price for both periods. Calculate monthly depreciation rate for EV vs overall. Discard full response.

4. **Top EV models by residual strength** — From step 3 data:
   - Rank EV models by retention (3-month price change %)
   - Strong residuals (< 1%/month decline): SAFE TO LEND
   - Moderate (1-2%/month): STANDARD TERMS
   - Weak (> 2%/month): REDUCED ADVANCE RATE or AVOID

5. **EV supply health** — Call `mcp__marketcheck__search_active_cars` with `state`, `fuel_type=Electric`, `car_type=used`, `stats=price,dom`, `rows=0`.
   → **Extract only**: total active EV, median_price, avg_dom. Discard full response.
   - Days supply = active / (monthly EV sold / 30)

6. **Sales talking points for dealers**:
   - "EV represents [X]% of used sales in [state] — growing/declining"
   - "We have competitive EV lending programs for [models with strong residuals]"
   - "Avoid stocking [models with weak residuals] — our programs have tighter terms for those"
   - "EV days supply is [X] — [tight/balanced/building] meaning [pricing power/risk]"

## Output
EV Market Scorecard: penetration %, volume, trend. EV vs ICE pricing comparison by segment. Depreciation comparison (monthly rate, ratio). Top EV models ranked by residual strength (SAFE/STANDARD/AVOID). Supply health metrics. Dealer talking points for EV lending programs. Key message: "Promote lending on [safe models], use caution on [risky models], EV share is [growing/flat/declining]."
