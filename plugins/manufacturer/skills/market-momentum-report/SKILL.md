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

Before running any workflow, check for a saved manufacturer profile:

1. Read `~/.claude/marketcheck/manufacturer-profile.json`
2. If the file **does not exist**: This skill works without a profile. Produces a national market overview.
3. If the file **exists**, extract silently:
   - `brands` ← `manufacturer.brands` — highlight these in all tables with ★
   - `states` ← `manufacturer.states` — regional focus
   - `competitor_brands` ← `manufacturer.competitor_brands` — highlight in tables
   - `country` ← `location.country` (**US-only**)
4. **Country check:** If `country=UK`, stop: "Market momentum reporting requires US sold data. Not available for UK."
5. Confirm briefly: "Generating [State or National] market momentum report for [Month Year] — highlighting **[brands]** and competitors"

## User Context

The primary user is an **OEM strategist, product planner, or brand manager** needing a comprehensive sector-level view to contextualize their own brand's performance. This report provides the MARKET CONTEXT for strategic planning decisions — what is the overall market doing, and how does your brand fit within it?

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

Calculate monthly depreciation rate per segment. Flag segments with > 1.5%/month as accelerating.

Also identify the 5 fastest depreciating specific models (by make/model):
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `asc`
- `top_n`: 20

Cross-reference with 3-month-ago data. Flag any of YOUR models or COMPETITOR models in the list.

### Step 5 — Regional price variance (optional, if state data available)

Call `mcp__marketcheck__get_sold_summary` with:
- `summary_by`: `state`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `desc`
- `top_n`: 10

Focus on states in the user's profile if available.

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
AUTO SECTOR INTELLIGENCE — [Month Year]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: [State or National]
Your Brands: [brands] ★ | Competitors: [competitor_brands]

MACRO SIGNALS
Metric                    | Current    | Prior Mo   | 3mo Ago    | Trend      | Signal
--------------------------|------------|------------|------------|------------|--------
Total Sales Volume        | XXX,XXX    | XXX,XXX    | XXX,XXX    | +X.X% MoM | [signal]
Avg Transaction Price     | $XX,XXX    | $XX,XXX    | $XX,XXX    | +X.X% MoM | [signal]
Industry Days Supply      | XX days    |            |            |            | [signal]
  New                     | XX days    |            |            |            |
  Used                    | XX days    |            |            |            |
EV Penetration            | X.X%       | X.X%       | X.X%       | +XX bps    | [signal]
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

★ Your brand: [Brand] at XX.X% share ([+/-XX] bps) — [in gainers/losers/stable]
Competitors: [Comp A] at XX.X% ([+/-XX] bps), [Comp B] at XX.X% ([+/-XX] bps)

PRICING POWER INDEX (New Vehicles)
Status          | # of Makes | Avg Premium/Discount | Trend vs Prior Month
----------------|-----------|---------------------|---------------------
Above MSRP      | XX        | +X.X%               | [Fewer / More] brands above
At MSRP (±1%)   | XX        |                     |
Below MSRP      | XX        | -X.X%               | [Deeper / Shallower] discounts

★ Your brand: [Above/At/Below] MSRP at [X.X]%
Competitors: [Comp A] at [X.X]%, [Comp B] at [X.X]%

DEPRECIATION ALERT
Fastest Depreciating Segments (monthly rate):
Segment     | Current Price | 3mo Ago    | Monthly Rate | Signal
------------|-------------|------------|-------------|--------
[Segment 1] | $XX,XXX      | $XX,XXX    | -X.X%/mo    | ACCELERATING
[Segment 2] | $XX,XXX      | $XX,XXX    | -X.X%/mo    | NORMAL
...

Fastest Depreciating Models:
Make Model       | Current Avg | 3mo Ago Avg | Drop $ | Monthly Rate | Your Brand?
-----------------|-------------|-------------|--------|-------------|------------
[Model 1]        | $XX,XXX     | $XX,XXX     | -$X,XXX| -X.X%/mo    | [Yes/No]
[Model 2]        | $XX,XXX     | $XX,XXX     | -$X,XXX| -X.X%/mo    | [Yes/No]
...

[If regional data:]
REGIONAL SNAPSHOT
State | Avg Price | vs National | Volume  | EV Penetration
------|-----------|-------------|---------|---------------
[top 5 most expensive]
[top 5 cheapest]
Spread: $X,XXX between most and least expensive markets

MARKET HEALTH COMPOSITE: [EXPANDING / STABLE / CONTRACTING / MIXED]

Strategic Context for [Company]:
[e.g., "The US auto market sold XXX,XXX units in [Month], up X.X% from prior month. Your brand [gained/lost] share in an [expanding/contracting] market — [interpretation of what this means for your strategy]. EV penetration reached X.X%, and your brand's EV offering [is/is not] keeping pace with the segment."]

Key Implications for Your Brand:
1. [Most actionable strategic signal, e.g., "Market is expanding but your share is flat — competitors are capturing the growth"]
2. [Second signal, e.g., "Pricing power is eroding across the industry — your brand is still above MSRP but the cushion is shrinking"]
3. [Third signal, e.g., "The SUV segment is showing accelerating depreciation — review residual value support programs"]
```

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
