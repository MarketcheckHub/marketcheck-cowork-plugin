---
name: ev-transition-monitor
description: >
  This skill should be used when the user asks about "EV market update",
  "EV adoption rate", "EV vs ICE pricing", "electrification progress",
  "EV penetration by state", "EV price parity", "hybrid adoption",
  "EV launch planning", "regional EV heatmap", "EV competitive position",
  "which OEMs are winning EV", "EV days supply", "electric vehicle trends",
  "EV strategy", "electrification strategy",
  or needs help tracking electric vehicle market dynamics for
  OEM strategy, regional launch planning, or competitive EV positioning.
version: 0.1.0
---

# EV Transition Monitor — Electrification Strategy Intelligence for OEMs

## Manufacturer Profile (Load First)

Before running any workflow, check for a saved manufacturer profile:

1. Read `~/.claude/marketcheck/manufacturer-profile.json`
2. If the file **does not exist**: Ask: "Which brand(s) do you represent?", "Which states?", and "Which EV competitors to track?"
3. If the file **exists**, extract silently:
   - `brands` ← `manufacturer.brands` — your own brands
   - `states` ← `manufacturer.states` — geographic scope for adoption heatmap
   - `competitor_brands` ← `manufacturer.competitor_brands` — EV competitors to track
   - `country` ← `location.country` (this skill is **US-only**)
4. **Country check:** If `country=UK`, stop: "EV transition monitoring requires US sold data. Not available for UK."
5. Confirm briefly: "Using profile: **[user_name]** at **[company]** — Tracking EV progress for **[brands]** vs **[competitor_brands]**"

## User Context

The primary user is an **OEM product planner, EV strategy lead, regional manager, or brand strategist** tracking electrification progress for their own brand and competitive positioning against other EV players. This skill frames everything as ELECTRIFICATION STRATEGY — how well is your brand executing its EV transition, and how do you compare?

Each metric includes strategic implications for production planning, pricing, and regional launch decisions.

## Workflow: EV Market Scorecard

The comprehensive EV market analysis. Use for "EV market update" or "electrification progress."

### Step 1 — EV penetration rate (market-wide)

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `state`: from profile or user input (omit for national)
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `fuel_type_category`
- `ranking_measure`: `sold_count`
- `top_n`: 5

Repeat for total market (no fuel_type_category filter). Also repeat for prior month and 3 months ago.

Calculate:
- **EV Penetration %** = EV sold / total sold x 100
- **Hybrid Penetration %** = Hybrid sold / total sold x 100
- **Combined Electrified %** = (EV + Hybrid) / total x 100
- **MoM Change (bps)** = (current % - prior %) x 100
- **3-Month Trend (bps)** = (current % - 3mo %) x 100
- **Signal:** ACCELERATING if MoM > +20 bps AND 3mo > +50 bps; DECELERATING if MoM < -10 bps; PLATEAU if stable +/-10 bps for 2+ months

### Step 2 — Your brand's EV penetration vs competitors

Call `mcp__marketcheck__get_sold_summary` for each of your brands AND each competitor brand with:
- `make`: the brand
- `fuel_type_category`: `EV`
- Current and prior periods

Calculate for each brand:
- **Brand EV Penetration** = Brand's EV sold / Brand's total sold x 100
- **Brand EV Share of Market** = Brand's EV sold / Total EV sold x 100
- **MoM Change (bps)**
- **Your Position:** Are you ahead or behind competitors on EV penetration? By how much?

### Step 3 — EV vs ICE pricing parity

Call `mcp__marketcheck__get_sold_summary` for each fuel type:
- `fuel_type_category`: `EV` → get `average_sale_price`
- No filter (or `fuel_type_category`: `Gas`) → get `average_sale_price` for ICE

Repeat for prior periods.

Calculate:
- **EV Avg Price** vs **ICE Avg Price**
- **Price Gap $** = EV - ICE
- **Price Gap %** = (EV - ICE) / ICE x 100
- **Gap Trend** = is the gap narrowing or widening?
- **Your Brand EV Avg Price** vs market EV avg and competitor EV avg
- **Signal:** APPROACHING PARITY if gap < 15% and narrowing; STALLED if gap stable; DIVERGING if gap widening

Break down by segment if possible:
- SUV: EV vs ICE price
- Sedan: EV vs ICE price
- Pickup: EV vs ICE price

### Step 4 — EV days supply (production planning signal)

Call `mcp__marketcheck__search_active_cars` with:
- `fuel_type`: `Electric`
- `car_type`: `new`
- `stats`: `price,dom`
- `rows`: 0

For your brands specifically, also filter by `make`.

Plus sold data from Step 1 for volume.

Calculate:
- **Market EV New Days Supply** = active EV new / monthly EV new sold x 30
- **Your Brand EV Days Supply** = your active EV new / your monthly EV new sold x 30
- **Signal:** DEMAND > SUPPLY if < 30 days (ramp production); BALANCED if 30-60; SUPPLY BUILDING if > 60 (slow production or increase incentives); GLUT if > 90

### Step 5 — Brand-level EV share

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 15
- Current month AND prior month

Calculate:
- **Brand EV Share %** = brand EV sold / total EV sold x 100
- **MoM Share Change (bps)**
- Highlight your brands with ★ and competitor brands
- **Signal per brand:** GAINING / LOSING / STABLE

### Step 6 — Regional EV adoption heatmap (launch planning)

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `summary_by`: `state`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 15

Calculate state-level EV penetration rate by also pulling total sold by state.

For your brand specifically, also calculate your brand's EV penetration per state.

Identify:
- **Highest EV adoption states** — priority markets for EV launches
- **Fastest growing EV states** — emerging opportunities
- **Your brand's EV strongholds** vs **underperforming states**
- **States where competitors lead EV** — conquest opportunities

## Output

```
EV TRANSITION MONITOR — Electrification Strategy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: [State or National] | Period: [Current Month] vs [Prior Month] vs [3mo Ago]
Your Brands: [brands] | Competitors: [competitor_brands]

YOUR EV POSITION
Your Brand EV Penetration: X.X% of your total sales (market avg: Y.Y%)
Your Brand EV Market Share: X.X% of all EVs sold
Position: [AHEAD / BEHIND / AT PAR] vs market average
Key Competitor: [Competitor] at X.X% EV penetration

MARKET ADOPTION METRICS
Metric                    | Current | Prior Mo | 3mo Ago | Trend      | Signal
--------------------------|---------|----------|---------|------------|--------
EV Penetration (% sales)  | X.X%    | X.X%     | X.X%    | +XX bps    | ACCELERATING
Hybrid Penetration        | X.X%    | X.X%     | X.X%    | +XX bps    | STABLE
Combined Electrified      | X.X%    | X.X%     | X.X%    | +XX bps    |
EV Volume (units)         | XX,XXX  | XX,XXX   | XX,XXX  | +X.X% MoM |

PRICE PARITY PROGRESS
                    | EV Avg      | ICE Avg     | Gap $    | Gap %   | Trend
--------------------|-------------|-------------|----------|---------|--------
All Segments        | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  | Narrowing
SUV                 | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  |
Sedan               | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  |
Pickup              | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  |
Your Brand EV Avg   | $XX,XXX     | vs Market EV $XX,XXX   | [Above/Below]

PRODUCTION PLANNING — EV DAYS SUPPLY
                    | Days Supply | vs Market   | Trend       | Signal
--------------------|-------------|-------------|-------------|--------
Your Brand EV New   | XX days     | Market: XX  | Building    | [signal]
Market EV New       | XX days     |             |             | [signal]
Your Brand EV Used  | XX days     | Market: XX  |             | [signal]

BRAND EV SHARE (who's winning the EV race)
Make      | EV Volume | EV Share % | MoM Change | Brand EV % | Signal
----------|-----------|-----------|------------|------------|--------
★ [Your]  | X,XXX     | X.X%       | +XX bps    | X.X%       | [signal]
Tesla     | XX,XXX    | XX.X%      | -XXX bps   | 100%       | LOSING SHARE
[Comp A]  | X,XXX     | X.X%       | +XX bps    | X.X%       | GAINING
[Comp B]  | X,XXX     | X.X%       | +XX bps    | X.X%       | GAINING

REGIONAL EV ADOPTION HEATMAP (launch planning)
State | Market EV % | Your Brand EV % | Competitor Lead | EV Volume | Trend
------|------------|-----------------|-----------------|-----------|------
CA    | XX.X%       | X.X%             | [who leads]     | XX,XXX    | +XX bps
WA    | X.X%        | X.X%             | [who leads]     | X,XXX     | +XX bps
TX    | X.X%        | X.X%             | [who leads]     | X,XXX     | +XX bps
...

Priority Markets for Your EV Launch/Expansion:
- [State A]: High EV adoption (X.X%), your brand underrepresented at Y.Y%. Estimated capture: N units/month.
- [State B]: Fastest growing EV market (+XX bps/mo). Early-mover advantage available.

ELECTRIFICATION STRATEGY IMPLICATIONS

For your brand:
- [e.g., "Your EV penetration at 4.2% of total sales is behind competitor A's 6.1%. Accelerate [model] production to close the gap."]
- [e.g., "Your EV days supply at 38 days is healthy — demand is absorbing production. Consider ramp."]

Competitive threats:
- [e.g., "[Competitor] gained 85 bps of EV share this month, primarily through [model] in the SUV segment."]
- [e.g., "Tesla's EV share dropped from X% to Y% — the share is flowing to legacy OEMs including your competitors."]

Regional launch opportunities:
- [e.g., "Washington state EV adoption is 12.3% but your brand has 0 EV sales there. Priority market for expansion."]
```

## Important Notes

- **US-only:** All data requires US `get_sold_summary`.
- Tesla dominates EV share nationally (~50-60%) — always contextualize your share and competitors' share as "ex-Tesla" if helpful.
- EV depreciation patterns differ significantly by brand — note this when discussing pricing.
- The EV-to-ICE price gap is the single most important metric for adoption forecasting. Once the gap drops below 10% in a segment, adoption typically accelerates nonlinearly.
- Frame everything for the manufacturer audience: production planning, allocation decisions, incentive strategy, regional launch timing.
- When showing regional data, always overlay your brand's performance against the market to identify gaps and opportunities.
