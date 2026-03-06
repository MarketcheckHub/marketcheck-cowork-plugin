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

# Market Momentum Report — Monthly Portfolio Risk & Opportunity Intelligence

## Lender Profile (Load First)

Before running any workflow, check for a saved lender profile:

1. Read `~/.claude/marketcheck/lender-profile.json`
2. If the file **does not exist**: This skill works without a profile. Produces a national market overview with lending risk signals.
3. If the file **exists**, extract silently:
   - `portfolio_focus` ← `lender.portfolio_focus` — determines output emphasis (leasing → residual focus, auto_loans → LTV/advance rate focus, floor_plan → inventory/supply focus)
   - `country` ← `location.country` (**US-only**)
   - `state` ← `location.state`
   - `tracked_segments` ← `lender.tracked_segments` — highlight these segments in all tables
   - `risk_ltv_threshold` ← `lender.risk_ltv_threshold`
   - `high_risk_ltv_threshold` ← `lender.high_risk_ltv_threshold`
4. **Country check:** If `country=UK`, stop: "Market momentum reporting requires US sold data. Not available for UK."
5. Confirm briefly: "Generating [State or National] lending risk momentum report for [Month Year]"

## User Context

The primary user is a **lender** (auto finance director, residual value committee member, or portfolio risk manager) needing a comprehensive sector-level view to inform lending policy, residual setting, and portfolio strategy. The secondary user is any auto lending professional wanting a monthly market pulse for credit committee presentations. This is the broadest skill — it covers the entire US auto market through a lending risk lens.

## Workflow: Monthly Market Momentum

### Step 1 — Macro signals (total market)

**Total volume:** Call `mcp__marketcheck__get_sold_summary` with:
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `inventory_type`
- `ranking_measure`: `sold_count`
- `top_n`: 5

Repeat for prior month and 3 months ago. Extract total sold (new + used), average sale price, average DOM.

Calculate:
- Total units MoM %
- Avg transaction price MoM %
- New vs Used mix shift
- Industry-wide average DOM trend

**EV penetration:** Call with `fuel_type_category=EV` for current and prior. Calculate penetration rate and bps change.

### Step 2 — Winners and losers (by market share)

Call `mcp__marketcheck__get_sold_summary` with:
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 25
- Current month AND prior month

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

Calculate monthly depreciation rate per segment. Flag segments with > 1.5%/month as "RESIDUAL RISK ACCELERATING — tighten advance rates."

Also identify the 5 fastest depreciating specific models (by make/model):
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `asc`
- `top_n`: 20

Cross-reference with 3-month-ago data.

### Step 5 — Regional collateral variance (optional, if state data available)

Call `mcp__marketcheck__get_sold_summary` with:
- `summary_by`: `state`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `desc`
- `top_n`: 10

Identify:
- Premium collateral markets (highest values)
- Discount collateral markets (lowest values)
- Collateral value spread (highest vs lowest)

### Step 6 — Supply health

Call `mcp__marketcheck__search_active_cars` with:
- `car_type`: `new`
- `stats`: `price,dom`
- `rows`: 0

And separately with `car_type=used`.

Calculate:
- Total active new inventory nationally (or by state)
- Total active used inventory
- Implied days supply for each
- MoM inventory build/draw trend

## Output

```
AUTO LENDING MARKET INTELLIGENCE — [Month Year]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: [State or National]

MACRO SIGNALS
Metric                    | Current    | Prior Mo   | 3mo Ago    | Trend      | Lending Signal
--------------------------|------------|------------|------------|------------|---------------
Total Sales Volume        | XXX,XXX    | XXX,XXX    | XXX,XXX    | +X.X% MoM | [signal]
Avg Transaction Price     | $XX,XXX    | $XX,XXX    | $XX,XXX    | +X.X% MoM | [signal]
Industry Days Supply      | XX days    |            |            |            | [signal]
  New                     | XX days    |            |            |            |
  Used                    | XX days    |            |            |            |
EV Penetration            | X.X%       | X.X%       | X.X%       | +XX bps    | [signal]
New / Used Mix            | XX% / XX%  | XX% / XX%  |            |            |

BRAND PERFORMANCE (portfolio risk/opportunity)
GAINING (improving residuals)                   LOSING (deteriorating residuals)
Make        | Share  | Change (bps)        Make        | Share  | Change (bps)
------------|--------|-------------        ------------|--------|-------------
[Brand 1]   | XX.X%  | +XXX bps            [Brand 1]   | XX.X%  | -XXX bps
[Brand 2]   | XX.X%  | +XX bps             [Brand 2]   | XX.X%  | -XX bps
[Brand 3]   | XX.X%  | +XX bps             [Brand 3]   | XX.X%  | -XX bps
[Brand 4]   | XX.X%  | +XX bps             [Brand 4]   | XX.X%  | -XX bps
[Brand 5]   | XX.X%  | +XX bps             [Brand 5]   | XX.X%  | -XX bps

PRICING POWER INDEX (New Vehicles — Residual Forecasting Signal)
Status          | # of Makes | Avg Premium/Discount | Lending Implication
----------------|-----------|---------------------|---------------------
Above MSRP      | XX        | +X.X%               | Lower residual risk — standard advance rates
At MSRP (±1%)   | XX        |                     | Balanced — standard assumptions
Below MSRP      | XX        | -X.X%               | Elevated residual risk — compressed origination values

Notable: [e.g., "Toyota, Porsche still above MSRP; Stellantis brands averaging -5.2% below — reduce residual forecasts for new Stellantis originations"]

*** RESIDUAL RISK ALERT ***
Fastest Depreciating Segments (monthly rate):
Segment     | Current Price | 3mo Ago    | Monthly Rate | Risk Signal
------------|-------------|------------|-------------|------------------
[Segment 1] | $XX,XXX      | $XX,XXX    | -X.X%/mo    | ACCELERATING — TIGHTEN ADVANCE RATES
[Segment 2] | $XX,XXX      | $XX,XXX    | -X.X%/mo    | NORMAL
...

Fastest Depreciating Models (highest residual risk):
Make Model       | Current Avg | 3mo Ago Avg | Drop $ | Monthly Rate | Action Required
-----------------|-------------|-------------|--------|--------------|----------------
[Model 1]        | $XX,XXX     | $XX,XXX     | -$X,XXX| -X.X%/mo     | Tighten advance rates
[Model 2]        | $XX,XXX     | $XX,XXX     | -$X,XXX| -X.X%/mo     | Monitor closely
...

[If tracked_segments from profile, highlight those segments specifically]

[If regional data:]
REGIONAL COLLATERAL SNAPSHOT
State | Avg Price | vs National | Volume  | Collateral Signal
------|-----------|-------------|---------|------------------
[top 5 highest collateral value states]
[top 5 lowest collateral value states]
Spread: $X,XXX between strongest and weakest collateral markets

PORTFOLIO RISK COMPOSITE: [FAVORABLE / STABLE / DETERIORATING / MIXED]

Summary (3 sentences):
[e.g., "The US auto market sold XXX,XXX units in [Month], up X.X% from prior month. Pricing power continues to erode with XX% of new vehicles now selling below MSRP, up from XX% three months ago — reduce residual forecasts on affected models. EV penetration reached X.X% but EV depreciation rates remain 1.8x ICE levels — maintain separate residual curves for EV portfolio segments."]

*** LENDING POLICY SIGNALS ***
1. Residual Setting: [Most actionable residual risk signal with data backing]
2. Advance Rates: [Segment/brand-specific advance rate recommendation]
3. Portfolio Exposure: [Concentration risk or opportunity signal]
```

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
