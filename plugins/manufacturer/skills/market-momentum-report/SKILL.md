---
name: market-momentum-report
description: >
  This skill should be used when the user asks for a "market report",
  "sector overview", "monthly auto market", "market scorecard",
  "auto industry health", "market momentum", "strategic planning context",
  "which brands are winning", "pricing power index", "market context",
  or needs a comprehensive monthly overview of the US automotive market
  for strategic planning, product decisions, or industry reporting.
version: 0.1.0
---

# Market Momentum Report — Market Context for Strategic Planning

## Manufacturer Profile (Load First)

Load `~/.claude/marketcheck/manufacturer-profile.json` if exists. Extract: `brands` (highlight with star), `states`, `competitor_brands`, `country`. Works without profile (national overview). US-only; if UK, inform not available. Confirm profile.

## User Context

User is an OEM strategist or brand manager needing sector-level market context for strategic planning -- what is the overall market doing, and how does your brand fit within it?

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
- **Top 5 gainers** (largest positive bps change)
- **Top 5 losers** (largest negative bps change)
- **Your brand's position** in the ranking and whether gaining or losing
- **Competitor positions** and their direction

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
- **At MSRP** (within +/-1%): count
- **Below MSRP** (discounting): count and avg discount %

Highlight where YOUR brands and COMPETITOR brands fall in the pricing power spectrum.

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

Cross-reference with 3-month-ago data. Flag any of YOUR models or COMPETITOR models in the list.

### Step 5 — Regional price variance (optional, if state data available)

Call `mcp__marketcheck__get_sold_summary` with:
- `summary_by`: `state`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `desc`
- `top_n`: 10
→ **Extract only**: `state`, `average_sale_price`, `sold_count` per state. Discard full response.

Focus on states in the user's profile if available.

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

Present: macro signals table (volume, price, DOM, EV penetration, mix), winners/losers by share change (star your brands), pricing power index, depreciation alerts, optional regional snapshot, composite health signal (EXPANDING/STABLE/CONTRACTING/MIXED), and 3 strategic implications for your brand.

## Composite Health Signal Logic

- **EXPANDING:** Volume up > 2%, pricing stable or rising, days supply < 60
- **STABLE:** Volume +/-2%, pricing +/-1%, days supply 50-75
- **CONTRACTING:** Volume down > 2%, pricing falling, days supply > 75
- **MIXED:** Conflicting signals (e.g., volume up but days supply building)

## Important Notes

- **US-only:** Requires `get_sold_summary` for sold data.
- Use the most recent COMPLETE month. If today is March 5, "current month" = February.
- This is the broadest report — keep it scannable. OEM strategists need the market context in 30 seconds, then drill into brand-specific implications.
- Always bold or star your brands and highlight competitors in every table.
- Frame the final summary as strategic context: what does this market environment mean for YOUR brand's decisions?
- This report works well as a regular monthly deliverable. Suggest: "Want me to run this at the start of each month?"
