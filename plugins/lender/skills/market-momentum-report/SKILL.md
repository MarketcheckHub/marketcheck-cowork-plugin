---
name: market-momentum-report
description: >
  This skill should be used when the user asks for a "market report",
  "automotive market signal", "monthly auto market", "portfolio risk briefing",
  "sector overview", "auto industry health", "market scorecard",
  "which brands are winning", "pricing power index", "market momentum",
  "lending risk overview", "residual risk summary", "collateral market health",
  or needs a comprehensive monthly overview of the US automotive market
  for lending risk assessment, residual forecasting, or portfolio management.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Momentum Report — Monthly Portfolio Risk & Opportunity Intelligence

## Lender Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `portfolio_focus`, `country`, `state`, `tracked_segments`, `risk_ltv_threshold`, `high_risk_ltv_threshold`. If missing, produces national overview. US-only. Confirm profile.

## User Context

Lender (auto finance director, residual value committee member, portfolio risk manager) needing a comprehensive sector-level view for lending policy, residual setting, and portfolio strategy. Broadest skill — covers entire US auto market through a lending risk lens.

## Workflow: Monthly Market Momentum

### Step 1 — Macro signals (total market)

**Total volume:** Call `mcp__marketcheck__get_sold_summary` with:
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `inventory_type`
- `ranking_measure`: `sold_count`
- `top_n`: 5

Repeat for prior month and 3 months ago.
→ **Extract only**: `sold_count`, `average_sale_price`, `average_days_on_market` per inventory_type per period. Discard full response.

Calculate:
- Total units MoM %
- Avg transaction price MoM %
- New vs Used mix shift
- Industry-wide average DOM trend

**EV penetration:** Call with `fuel_type_category=EV` for current and prior. Calculate penetration rate and bps change.
→ **Extract only**: `sold_count` for EV per period. Discard full response.

### Step 2 — Winners and losers (by market share)

Call `mcp__marketcheck__get_sold_summary` with:
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 25
- Current month AND prior month
→ **Extract only**: `make`, `sold_count` per period. Discard full response.

Calculate share % and bps change for each make. Identify:
- **Top 5 gainers** (largest positive bps change) — brands with improving residual outlook
- **Top 5 losers** (largest negative bps change) — brands with deteriorating residual outlook

### Step 3 — Pricing power index

Call `mcp__marketcheck__get_sold_summary` with:
- `inventory_type`: `New`
- `ranking_dimensions`: `make`
- `ranking_measure`: `price_over_msrp_percentage`
- `ranking_order`: `desc`
- `top_n`: 20
- Current month
→ **Extract only**: `make`, `price_over_msrp_percentage` per brand. Discard full response.

Categorize:
- **Above MSRP** (still commanding premiums): count and avg premium % — lower residual risk
- **At MSRP** (within +/-1%): count — standard residual assumptions
- **Below MSRP** (discounting): count and avg discount % — elevated residual risk on new originations

Track overall: what % of new vehicles sell above/below MSRP? Compare to prior month.

### Step 4 — Residual risk alert (depreciation)

Call `mcp__marketcheck__get_sold_summary` with:
- `inventory_type`: `Used`
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `asc`
- `top_n`: 10
- Current month AND 3 months ago
→ **Extract only**: `body_type`, `average_sale_price` per period. Discard full response.

Calculate monthly depreciation rate per segment. Flag segments with > 1.5%/month as "RESIDUAL RISK ACCELERATING -- tighten advance rates."

Also identify the 5 fastest depreciating specific models (by make/model):
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `asc`
- `top_n`: 20
→ **Extract only**: `make`, `model`, `average_sale_price` per period. Discard full response.

Cross-reference with 3-month-ago data.

### Step 5 — Regional collateral variance (optional, if state data available)

Call `mcp__marketcheck__get_sold_summary` with:
- `summary_by`: `state`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `desc`
- `top_n`: 10
→ **Extract only**: `state`, `average_sale_price`, `sold_count` per state. Discard full response.

Identify:
- Premium collateral markets (highest values)
- Discount collateral markets (lowest values)
- Collateral value spread (highest vs lowest)

### Step 6 — Supply health

Call `mcp__marketcheck__search_active_cars` with:
- `car_type`: `new`, `stats`: `price,dom`, `rows`: 0

And separately with `car_type=used`.
→ **Extract only**: `num_found`, `stats.dom.mean` per car_type. Discard full response.

Calculate:
- Total active new inventory nationally (or by state)
- Total active used inventory
- Implied days supply for each
- MoM inventory build/draw trend

## Output

Present: portfolio risk composite headline (FAVORABLE/STABLE/DETERIORATING/MIXED), macro signals table, brand performance gainers/losers, pricing power index, residual risk alert with fastest depreciating segments/models, and 3 lending policy signals (residual setting, advance rates, portfolio exposure).

## Composite Health Signal Logic (Lending Context)

- **FAVORABLE:** Volume up > 2%, pricing stable or rising, days supply < 60, depreciation rates below segment averages — residual risk low, standard lending parameters appropriate
- **STABLE:** Volume +/-2%, pricing +/-1%, days supply 50-75 — maintain current lending parameters
- **DETERIORATING:** Volume down > 2%, pricing falling, days supply > 75, depreciation accelerating — tighten advance rates, reduce residual forecasts, increase monitoring frequency
- **MIXED:** Conflicting signals (e.g., volume up but days supply building and depreciation accelerating) — differentiate by segment

## Important Notes

- **US-only:** Requires `get_sold_summary` for sold data.
- Use the most recent COMPLETE month. If today is March 5, "current month" = February.
- This is the broadest report — keep it scannable. Credit committees and auto finance directors need the signal in 30 seconds.
- If the user has tracked segments in their profile, highlight those segments prominently and call out any risk signals specific to their portfolio focus.
- Frame every metric through a lending lens: volume = origination demand, pricing = collateral value, depreciation = residual risk, supply = liquidation risk.
- This report works well as a regular monthly deliverable. Suggest: "Want me to run this at the start of each month for your credit committee?"
