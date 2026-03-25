---
name: market-momentum-report
description: >
  Monthly auto sector overview for investors. Triggers: "market report",
  "automotive market signal", "monthly auto market", "investment briefing auto sector",
  "sector overview", "auto industry health", "market scorecard",
  "which brands are winning", "pricing power index", "market momentum",
  US automotive market overview, investment decisions, industry reporting.
version: 0.1.0
---

# Market Momentum Report — Monthly Auto Sector Intelligence

## User Profile (Load First)

Before running any workflow, check for a saved user profile:

1. Read the `marketcheck-profile.md` project memory file.
2. If the file **does not exist**: This skill works without a profile. Produces a national market overview.
3. If the file **exists**, extract silently:
   - `user_type` — determines output framing
   - `country` ← `location.country` (**US-only**)
   - `state` ← `location.state` or `analyst.tracked_states`
   - If `analyst`: highlight `analyst.tracked_tickers` in results
4. **Country check:** If `country=UK`, stop: "Market momentum reporting requires US sold data. Not available for UK."
5. Confirm briefly: "Generating [State or National] market momentum report for [Month Year]"

## User Context

The primary user is a **macro analyst** or **fund manager** needing a comprehensive sector-level view. The secondary user is any automotive professional wanting a monthly market pulse. This is the broadest skill — it covers the entire US auto market, not a single OEM or dealer group.

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
- **Top 5 gainers** (largest positive bps change)
- **Top 5 losers** (largest negative bps change)

### Step 3 — Pricing power index

Call `mcp__marketcheck__get_sold_summary` with:
- `inventory_type`: `New`
- `ranking_dimensions`: `make`
- `ranking_measure`: `price_over_msrp_percentage`
- `ranking_order`: `desc`
- `top_n`: 20
- Current month

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

Calculate monthly depreciation rate per segment. Flag segments with > 1.5%/month as accelerating.

Also identify the 5 fastest depreciating specific models (by make/model):
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `asc`
- `top_n`: 20

Cross-reference with 3-month-ago data.

### Step 5 — Regional price variance (optional, if state data available)

Call `mcp__marketcheck__get_sold_summary` with:
- `summary_by`: `state`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `desc`
- `top_n`: 10

Identify:
- Most expensive states (premium markets)
- Cheapest states (value markets)
- Price spread (highest vs lowest)

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
AUTO SECTOR MONTHLY INTELLIGENCE — [Month Year]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: [State or National]

MACRO SIGNALS
Metric                    | Current    | Prior Mo   | 3mo Ago    | Trend      | Signal
--------------------------|------------|------------|------------|------------|--------
Total Sales Volume        | XXX,XXX    | XXX,XXX    | XXX,XXX    | +X.X% MoM | BULLISH
Avg Transaction Price     | $XX,XXX    | $XX,XXX    | $XX,XXX    | +X.X% MoM | NEUTRAL
Industry Days Supply      | XX days    |            |            |            | [signal]
  New                     | XX days    |            |            |            |
  Used                    | XX days    |            |            |            |
EV Penetration            | X.X%       | X.X%       | X.X%       | +XX bps    | ACCELERATING
New / Used Mix            | XX% / XX%  | XX% / XX%  |            |            |

WINNERS & LOSERS (by market share change)
GAINING                                    LOSING
Make        | Share  | Change (bps)        Make        | Share  | Change (bps)
------------|--------|-------------        ------------|--------|-------------
[Brand 1]   | XX.X%  | +XXX bps            [Brand 1]   | XX.X%  | -XXX bps
[Brand 2]   | XX.X%  | +XX bps             [Brand 2]   | XX.X%  | -XX bps
[Brand 3]   | XX.X%  | +XX bps             [Brand 3]   | XX.X%  | -XX bps
[Brand 4]   | XX.X%  | +XX bps             [Brand 4]   | XX.X%  | -XX bps
[Brand 5]   | XX.X%  | +XX bps             [Brand 5]   | XX.X%  | -XX bps

PRICING POWER INDEX (New Vehicles)
Status          | # of Makes | Avg Premium/Discount | Trend vs Prior Month
----------------|-----------|---------------------|---------------------
Above MSRP      | XX        | +X.X%               | [Fewer / More] brands above
At MSRP (±1%)   | XX        |                     |
Below MSRP      | XX        | -X.X%               | [Deeper / Shallower] discounts

Notable: [e.g., "Toyota, Porsche still above MSRP; Stellantis brands averaging -5.2% below"]

DEPRECIATION ALERT
Fastest Depreciating Segments (monthly rate):
Segment     | Current Price | 3mo Ago    | Monthly Rate | Signal
------------|-------------|------------|-------------|--------
[Segment 1] | $XX,XXX      | $XX,XXX    | -X.X%/mo    | ACCELERATING
[Segment 2] | $XX,XXX      | $XX,XXX    | -X.X%/mo    | NORMAL
...

Fastest Depreciating Models:
Make Model       | Current Avg | 3mo Ago Avg | Drop $ | Monthly Rate
-----------------|-------------|-------------|--------|------------
[Model 1]        | $XX,XXX     | $XX,XXX     | -$X,XXX| -X.X%/mo
[Model 2]        | $XX,XXX     | $XX,XXX     | -$X,XXX| -X.X%/mo
...

Implications: [e.g., "EV sedans depreciating at 2.8%/mo — lenders should reduce advance rates on EV sedan portfolios"]

[If regional data:]
REGIONAL SNAPSHOT
State | Avg Price | vs National | Volume  | EV Penetration
------|-----------|-------------|---------|---------------
[top 5 most expensive]
[top 5 cheapest]
Spread: $X,XXX between most and least expensive markets

MARKET HEALTH COMPOSITE: [EXPANDING / STABLE / CONTRACTING / MIXED]

Summary (3 sentences):
[e.g., "The US auto market sold XXX,XXX units in [Month], up X.X% from prior month. Pricing power continues to erode with XX% of new vehicles now selling below MSRP, up from XX% three months ago. EV penetration reached X.X%, marking the Nth consecutive month of growth, though EV depreciation rates remain 1.8x ICE levels."]

Key signals for investors:
1. [Most actionable signal with data backing]
2. [Second signal]
3. [Third signal]
```

## Composite Health Signal Logic

- **EXPANDING:** Volume up > 2%, pricing stable or rising, days supply < 60
- **STABLE:** Volume ±2%, pricing ±1%, days supply 50-75
- **CONTRACTING:** Volume down > 2%, pricing falling, days supply > 75
- **MIXED:** Conflicting signals (e.g., volume up but days supply building)

## Important Notes

- **US-only:** Requires `get_sold_summary` for sold data.
- Use the most recent COMPLETE month. If today is March 5, "current month" = February.
- This is the broadest report — keep it scannable. Executives and fund managers need the signal in 30 seconds.
- If the user has tracked tickers in their profile, bold or star those brands in the tables.
- This report works well as a regular monthly deliverable. Suggest: "Want me to run this at the start of each month?"

## Self-Check (before presenting to user)

- [ ] All major sectors covered (new, used, EV, segments)
- [ ] Month-over-month trends included for every metric
- [ ] Pricing power index calculated correctly
- [ ] Strategic implications tailored to user's role
- [ ] Data period cited
