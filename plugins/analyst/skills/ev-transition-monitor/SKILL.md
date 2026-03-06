---
name: ev-transition-monitor
description: >
  This skill should be used when the user asks about "EV market update",
  "EV adoption rate", "EV vs ICE pricing", "Tesla market position",
  "EV investment signal", "electric vehicle trends", "EV depreciation",
  "EV price parity", "hybrid adoption", "electrification progress",
  "EV days supply", "which OEMs are winning EV", "EV penetration by state",
  "EV investment thesis", "EV stock signal", "electrification transition risk",
  or needs help tracking electric vehicle market dynamics for investment
  thesis development and equity research.
version: 0.1.0
---

# EV Transition Monitor — EV Investment Thesis Intelligence

## User Profile (Load First)

Before running any workflow, check for a saved user profile:

1. Read `~/.claude/marketcheck/analyst-profile.json`.
2. If the file **does not exist**: This skill works without a profile. Ask: "Which aspect of the EV market?" and "Which state(s) or 'national'?" Suggest running `/onboarding` to set up a profile.
3. If the file **exists**, extract silently:
   - `analyst.tracked_tickers` — highlight relevant OEM tickers in results
   - `analyst.tracked_states`
   - `analyst.benchmark_period_months`
   - `location.country` (this skill is **US-only**)
4. **Country check:** If `country=UK`, stop: "EV transition monitoring requires US sold data. Not available for UK."
5. Confirm briefly: "Using profile: **[user.name]** ([user.company]), tracking [tickers]"

## User Context

The user is a **financial analyst** tracking EV pure-plays (TSLA, RIVN, LCID) or legacy OEM electrification progress for investment thesis development. Every metric is framed as an investment signal tied to stock tickers with BULLISH / BEARISH / NEUTRAL / CAUTION ratings.

## Built-in Ticker → Makes Mapping

```
EV PURE-PLAY TICKERS:
TSLA  → Tesla
RIVN  → Rivian
LCID  → Lucid

LEGACY OEM TICKERS (with EV exposure):
F     → Ford, Lincoln
GM    → Chevrolet, GMC, Buick, Cadillac
TM    → Toyota, Lexus
HMC   → Honda, Acura
STLA  → Chrysler, Dodge, Jeep, Ram
HYMTF → Hyundai, Kia, Genesis
NSANY → Nissan, Infiniti
MBGAF → Mercedes-Benz
BMWYY → BMW, MINI
VWAGY → Volkswagen, Audi, Porsche
```

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
- **Signal:** APPROACHING PARITY if gap < 15% and narrowing (BULLISH for EV adoption thesis); STALLED if gap stable; DIVERGING if gap widening (BEARISH for mass-market EV thesis)

Break down by segment if possible:
- SUV: EV vs ICE price
- Sedan: EV vs ICE price
- Pickup: EV vs ICE price

### Step 3 — EV depreciation vs ICE (residual risk signal)

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
- **Signal:** HIGH RISK if EV depreciation > 2x ICE — BEARISH for OEM residual exposure, lessors, and auto lender stocks; MODERATE if 1.3x-2x — CAUTION; NORMALIZING if < 1.3x — BULLISH for EV maturation thesis

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
- **Signal:** DEMAND > SUPPLY if < 30 days (BULLISH for EV OEMs — pricing power intact); BALANCED if 30-60; SUPPLY BUILDING if > 60 (BEARISH — production outpacing demand); GLUT if > 90 (BEARISH — expect incentive increases and margin pressure)

### Step 5 — Brand-level EV share (competitive positioning)

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
- Map each brand to its ticker
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
EV TRANSITION MONITOR — Investment Thesis View
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: [State or National] | Period: [Current Month] vs [Prior Month] vs [3mo Ago]
Tracked Tickers: [from profile]

ADOPTION METRICS (Sector Trajectory Signal)
Metric                    | Current | Prior Mo | 3mo Ago | Trend      | Signal
--------------------------|---------|----------|---------|------------|--------
EV Penetration (% sales)  | X.X%    | X.X%     | X.X%    | +XX bps    | ACCELERATING
Hybrid Penetration        | X.X%    | X.X%     | X.X%    | +XX bps    | STABLE
Combined Electrified      | X.X%    | X.X%     | X.X%    | +XX bps    |
EV Volume (units)         | XX,XXX  | XX,XXX   | XX,XXX  | +X.X% MoM |

PRICE PARITY TRACKER (Adoption Catalyst Signal)
                    | EV Avg      | ICE Avg     | Gap $    | Gap %   | Trend     | Signal
--------------------|-------------|-------------|----------|---------|-----------|--------
All Segments        | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  | Narrowing | BULLISH/BEARISH
SUV                 | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  |           |
Sedan               | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  |           |
Pickup              | $XX,XXX     | $XX,XXX     | +$X,XXX | +XX.X%  |           |

DEPRECIATION COMPARISON (Residual Risk Signal)
                    | EV Rate   | ICE Rate  | Ratio   | Signal
--------------------|-----------|-----------|---------|--------
Used (all segments) | X.X%/mo   | X.X%/mo   | X.Xx    | [HIGH RISK / MODERATE / NORMALIZING]
Used SUV            | X.X%/mo   | X.X%/mo   | X.Xx    |
Used Sedan          | X.X%/mo   | X.X%/mo   | X.Xx    |

SUPPLY HEALTH (Production Discipline Signal)
                    | Days Supply | vs ICE    | Trend       | Signal
--------------------|-------------|-----------|-------------|--------
EV New              | XX days     | XX days   | Building    | [signal]
EV Used             | XX days     | XX days   | Drawing     | [signal]

BRAND EV SHARE (Competitive Positioning — who is winning the EV race)
Make      | Ticker | EV Volume | EV Share % | MoM Change | Total Brand EV % | Signal
----------|--------|-----------|-----------|------------|------------------|--------
Tesla     | TSLA   | XX,XXX    | XX.X%      | -XXX bps   | 100%             | LOSING SHARE
Hyundai   | HYMTF  | X,XXX     | X.X%       | +XX bps    | X.X%             | GAINING
GM        | GM     | X,XXX     | X.X%       | +XX bps    | X.X%             | GAINING
Ford      | F      | X,XXX     | X.X%       | +XX bps    | X.X%             | STABLE
BMW       | BMWYY  | X,XXX     | X.X%       | +XX bps    | X.X%             | GAINING

[If regional data requested:]
TOP EV STATES (by penetration)
State | EV Penetration | National Avg | Delta | EV Volume | MoM Trend
------|---------------|-------------|-------|-----------|----------
CA    | XX.X%          | X.X%         | +X.X% | XX,XXX    | +XX bps
WA    | X.X%           | X.X%         | +X.X% | X,XXX     | +XX bps
...

INVESTMENT IMPLICATIONS BY TICKER

For EV pure-plays (TSLA, RIVN, LCID):
- [Ticker]: [signal] — [e.g., "TSLA losing EV share at -150 bps/mo as legacy OEMs gain. But total EV market growing faster, so absolute volume still up. NEUTRAL for revenue, BEARISH for market dominance thesis."]

For legacy OEM transition (F, GM, STLA):
- [Ticker]: [signal] — [e.g., "F EV penetration at 4.2% of its total sales, up from 3.1% 3 months ago. Transition accelerating but from low base. BULLISH for long-term positioning, watch for EV margin dilution in near-term earnings."]

For auto lenders and lessors:
- [e.g., "EV depreciation running 1.8x ICE. Lease residual settings for EVs should be 5-8% lower than ICE equivalents. BEARISH for portfolios with high EV concentration."]
```

## Important Notes

- **US-only:** All data requires US `get_sold_summary`.
- Tesla dominates EV share nationally (~50-60%) — always contextualize other OEMs' share as "ex-Tesla" if helpful.
- EV depreciation patterns differ significantly by brand: Tesla tends to hold value better than Nissan Leaf or Chevy Bolt. Break down by model when possible.
- The EV-to-ICE price gap is the single most important metric for adoption forecasting. Once the gap drops below 10% in a segment, adoption typically accelerates nonlinearly — this is a key inflection point for the investment thesis.
- Always map makes to stock tickers. An analyst tracking EV transition is evaluating specific stock positions, not abstract brand preferences.
- For every metric, explicitly state the investment signal direction and which tickers are affected.
