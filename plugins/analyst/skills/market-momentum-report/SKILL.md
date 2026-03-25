---
name: market-momentum-report
description: >
  Sector momentum for investment decisions. Triggers: "market report",
  "automotive market signal", "monthly auto market", "investment briefing auto sector",
  "sector overview", "auto industry health", "market scorecard",
  "which brands are winning", "pricing power index", "market momentum",
  "sector momentum", "auto sector thesis", "monthly sector intelligence",
  comprehensive monthly overview of the US automotive market
  for investment decisions and sector-level portfolio allocation.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Momentum Report — Sector Momentum for Investment Decisions

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_states`, `benchmark_period_months`, `country`. If missing, produces national overview. US-only. Confirm profile.

## User Context

Macro analyst, fund manager, or sector specialist needing comprehensive sector-level view of US auto market for investment decisions and portfolio allocation. Broadest skill -- covers entire US auto sector with BULLISH/BEARISH/NEUTRAL/CAUTION signals tied to auto-sector equities.

## Workflow: Monthly Sector Momentum

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

Calculate share % and bps change for each make. Map each make to its ticker. Identify:
- **Top 5 gainers** (largest positive bps change) — with ticker
- **Top 5 losers** (largest negative bps change) — with ticker

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
- **Above MSRP** (still commanding premiums): count and avg premium %
- **At MSRP** (within ±1%): count
- **Below MSRP** (discounting): count and avg discount %

Track overall: what % of new vehicles sell above/below MSRP? Compare to prior month.

### Step 4 — Depreciation alert

Call `mcp__marketcheck__get_sold_summary` with:
- `inventory_type`: `Used`
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `asc`
- `top_n`: 10
- Current month AND 3 months ago
→ **Extract only**: `body_type`, `average_sale_price` per period. Discard full response.

Calculate monthly depreciation rate per segment. Flag segments with > 1.5%/month as accelerating.

Also identify the 5 fastest depreciating specific models (by make/model):
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `asc`
- `top_n`: 20
→ **Extract only**: `make`, `model`, `average_sale_price` per period. Discard full response.

Cross-reference with 3-month-ago data. Map depreciating models to their OEM tickers.

### Step 5 — Regional price variance (optional, if state data available)

Call `mcp__marketcheck__get_sold_summary` with:
- `summary_by`: `state`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `desc`
- `top_n`: 10
→ **Extract only**: `state`, `average_sale_price`, `sold_count` per state. Discard full response.

Identify:
- Most expensive states (premium markets)
- Cheapest states (value markets)
- Price spread (highest vs lowest)

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

Present: sector health composite headline (EXPANDING/STABLE/CONTRACTING/MIXED), macro signals table, winners/losers by market share with tickers, pricing power index, depreciation alert with fastest depreciating segments/models mapped to tickers, and 3 key investor signals with portfolio implications.

## Composite Health Signal Logic

- **EXPANDING:** Volume up > 2%, pricing stable or rising, days supply < 60
- **STABLE:** Volume ±2%, pricing ±1%, days supply 50-75
- **CONTRACTING:** Volume down > 2%, pricing falling, days supply > 75
- **MIXED:** Conflicting signals (e.g., volume up but days supply building)

## Important Notes

- **US-only:** Requires `get_sold_summary` for sold data.
- Use the most recent COMPLETE month. If today is March 5, "current month" = February.
- This is the broadest report — keep it scannable. Fund managers need the signal in 30 seconds.
- If the user has tracked tickers in their profile, star those brands in the tables.
- Always map brands to tickers throughout. An analyst reads "Toyota (TM)" not just "Toyota."
- This report works well as a regular monthly deliverable. Suggest: "Want me to run this at the start of each month?"
