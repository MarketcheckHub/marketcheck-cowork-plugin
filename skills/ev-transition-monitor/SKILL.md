---
name: ev-transition-monitor
description: >
  This skill should be used when the user asks about "EV market update",
  "EV adoption rate", "EV vs ICE pricing", "Tesla market position",
  "EV investment signal", "electric vehicle trends", "EV depreciation",
  "EV price parity", "hybrid adoption", "electrification progress",
  "EV days supply", "which OEMs are winning EV", "EV penetration by state",
  or needs help tracking electric vehicle market dynamics for investment
  decisions, OEM strategy, or lending risk assessment.
version: 0.1.0
---

# EV Transition Monitor — Electric Vehicle Market Intelligence for Investment & Strategy

## User Profile (Load First)

Before running any workflow, check for a saved user profile:

1. Read `~/.claude/marketcheck/user-profile.json`. If not found, fall back to `~/.claude/marketcheck/dealer-profile.json` (v1.0 legacy).
2. If the file **does not exist**: This skill works without a profile. Ask: "Which aspect of the EV market?" and "Which state(s) or 'national'?"
3. If the file **exists**, extract silently:
   - `user_type` — determines output framing (analyst → investment signals, lender → risk signals, manufacturer → competitive signals)
   - `country` ← `location.country` (this skill is **US-only**)
   - `state` ← `location.state` or `analyst.tracked_states`
   - If `analyst`: use `analyst.tracked_tickers` to highlight relevant OEMs
   - If `lender`: use `lender.tracked_segments` for focus areas
4. **Country check:** If `country=UK`, stop: "EV transition monitoring requires US sold data. Not available for UK."
5. Confirm briefly: "Using profile: **[user.name]** ([user_type])"

## User Context

The primary user is a **financial analyst** tracking EV pure-plays (TSLA, RIVN, LCID) or legacy OEM electrification progress. The secondary users are **lenders** assessing EV residual risk and **OEM strategists** monitoring competitive EV positioning.

Each metric includes an explicit signal with investment/risk implications.

## Workflow: EV Market Scorecard

The comprehensive EV market analysis. Use for "EV market update" or "EV investment signal."

### Step 1 — EV penetration rate

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `state`: from profile or user input (omit for national)
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `fuel_type_category`
- `ranking_measure`: `sold_count`
- `top_n`: 5

Repeat for total market (no fuel_type_category filter). Also repeat for prior month and 3 months ago.

Calculate:
- **EV Penetration %** = EV sold / total sold × 100
- **Hybrid Penetration %** = Hybrid sold / total sold × 100 (if available)
- **Combined Electrified %** = (EV + Hybrid) / total × 100
- **MoM Change (bps)** = (current % - prior %) × 100
- **3-Month Trend (bps)** = (current % - 3mo %) × 100
- **Signal:** ACCELERATING if MoM > +20 bps AND 3mo > +50 bps; DECELERATING if MoM < -10 bps; PLATEAU if stable ±10 bps for 2+ months

### Step 2 — EV vs ICE pricing parity

Call `mcp__marketcheck__get_sold_summary` for each fuel type:
- `fuel_type_category`: `EV` → get `average_sale_price`
- No filter (or `fuel_type_category`: `Gas`) → get `average_sale_price` for ICE

Repeat for prior periods.

Calculate:
- **EV Avg Price** vs **ICE Avg Price**
- **Price Gap $** = EV - ICE
- **Price Gap %** = (EV - ICE) / ICE × 100
- **Gap Trend** = is the gap narrowing or widening?
- **Signal:** APPROACHING PARITY if gap < 15% and narrowing; STALLED if gap stable; DIVERGING if gap widening

Break down by segment if possible:
- SUV: EV vs ICE price
- Sedan: EV vs ICE price
- Pickup: EV vs ICE price

### Step 3 — EV depreciation vs ICE

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `inventory_type`: `Used`
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `asc`
- `top_n`: 15
- Current month AND 3 months ago

Repeat without fuel_type filter for ICE comparison.

Calculate:
- **EV Monthly Depreciation %** = (3mo_price - current_price) / 3mo_price / 3 × 100
- **ICE Monthly Depreciation %** = same for ICE
- **Depreciation Ratio** = EV rate / ICE rate (e.g., 2.1x means EVs depreciate 2.1x faster)
- **Signal:** HIGH RISK if EV depreciation > 2x ICE (residual risk for lessors); MODERATE if 1.3x-2x; NORMALIZING if < 1.3x

### Step 4 — EV days supply

Call `mcp__marketcheck__search_active_cars` with:
- `fuel_type`: `Electric`
- `car_type`: `new`
- `stats`: `price,dom`
- `rows`: 0

Plus sold data from Step 1 for volume.

Calculate:
- **EV New Days Supply** = active EV new / monthly EV new sold × 30
- **EV Used Days Supply** = active EV used / monthly EV used sold × 30
- Compare to ICE equivalents
- **Signal:** DEMAND > SUPPLY if < 30 days; BALANCED if 30-60; SUPPLY BUILDING if > 60; GLUT if > 90

### Step 5 — Brand-level EV share

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 15
- Current month AND prior month

Calculate:
- **Brand EV Share %** = brand EV sold / total EV sold × 100
- **MoM Share Change (bps)**
- Highlight TSLA, RIVN, LCID vs legacy OEMs
- **Signal per brand:** GAINING / LOSING / STABLE

### Step 6 — Regional EV adoption (optional)

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `summary_by`: `state`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 15

Calculate state-level EV penetration rate by also pulling total sold by state.

Identify: highest adoption states, fastest growing states, lowest adoption states.

## Output

```
EV TRANSITION MONITOR
━━━━━━━━━━━━━━━━━━━━
Market: [State or National] | Period: [Current Month] vs [Prior Month] vs [3mo Ago]

ADOPTION METRICS
Metric                    | Current | Prior Mo | 3mo Ago | Trend      | Signal
--------------------------|---------|----------|---------|------------|--------
EV Penetration (% sales)  | X.X%    | X.X%     | X.X%    | +XX bps    | ACCELERATING
Hybrid Penetration        | X.X%    | X.X%     | X.X%    | +XX bps    | STABLE
Combined Electrified      | X.X%    | X.X%     | X.X%    | +XX bps    |
EV Volume (units)         | XX,XXX  | XX,XXX   | XX,XXX  | +X.X% MoM |

PRICE PARITY TRACKER
                    | EV Avg      | ICE Avg     | Gap $    | Gap %   | Trend
--------------------|-------------|-------------|----------|---------|--------
All Segments        | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  | Narrowing
SUV                 | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  |
Sedan               | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  |
Pickup              | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  |

DEPRECIATION COMPARISON (monthly rate)
                    | EV Rate   | ICE Rate  | Ratio   | Signal
--------------------|-----------|-----------|---------|--------
Used (all segments) | X.X%/mo   | X.X%/mo   | X.Xx    | [HIGH RISK / MODERATE / NORMALIZING]
Used SUV            | X.X%/mo   | X.X%/mo   | X.Xx    |
Used Sedan          | X.X%/mo   | X.X%/mo   | X.Xx    |

SUPPLY HEALTH
                    | Days Supply | vs ICE    | Trend       | Signal
--------------------|-------------|-----------|-------------|--------
EV New              | XX days     | XX days   | Building    | [signal]
EV Used             | XX days     | XX days   | Drawing     | [signal]

BRAND EV SHARE (who's winning the EV race)
Make      | EV Volume | EV Share % | MoM Change | Total Brand EV % | Signal
----------|-----------|-----------|------------|------------------|--------
Tesla     | XX,XXX    | XX.X%      | -XXX bps   | 100%             | LOSING SHARE
Hyundai   | X,XXX     | X.X%       | +XX bps    | X.X%             | GAINING
GM        | X,XXX     | X.X%       | +XX bps    | X.X%             | GAINING
Ford      | X,XXX     | X.X%       | +XX bps    | X.X%             | STABLE
BMW       | X,XXX     | X.X%       | +XX bps    | X.X%             | GAINING

[If regional data requested:]
TOP EV STATES (by penetration)
State | EV Penetration | National Avg | Delta | EV Volume | MoM Trend
------|---------------|-------------|-------|-----------|----------
CA    | XX.X%          | X.X%         | +X.X% | XX,XXX    | +XX bps
WA    | X.X%           | X.X%         | +X.X% | X,XXX     | +XX bps
...

INVESTMENT IMPLICATIONS

For EV pure-plays (TSLA, RIVN, LCID):
- [e.g., "Tesla losing EV share at -150 bps/mo as legacy OEMs gain. But total EV market growing faster, so absolute volume still up."]
- [e.g., "EV days supply at 45 — healthier than 3 months ago (62). Production discipline improving."]

For legacy OEM transition (F, GM, STLA):
- [e.g., "Ford EV penetration at 4.2% of its total sales, up from 3.1% 3 months ago. Transition accelerating but from low base."]

For lenders/lessors:
- [e.g., "EV depreciation running 1.8x ICE. Used EV residuals continue to erode. Lease residual settings for EVs should be 5-8% lower than ICE equivalents."]
- [e.g., "EV used supply building (72 days) — expect further pricing pressure on 2-3 year old EVs."]
```

## Important Notes

- **US-only:** All data requires US `get_sold_summary`.
- Tesla dominates EV share nationally (~50-60%) — always contextualize other OEMs' share as "ex-Tesla" if helpful.
- EV depreciation patterns differ significantly by brand: Tesla tends to hold value better than Nissan Leaf or Chevy Bolt. Break down by model when possible.
- The EV-to-ICE price gap is the single most important metric for adoption forecasting. Once the gap drops below 10% in a segment, adoption typically accelerates nonlinearly.
- For lender users (`user_type: lender`), emphasize depreciation and residual risk. For analyst users, emphasize market share and adoption rates. For manufacturer users, emphasize competitive EV positioning.
