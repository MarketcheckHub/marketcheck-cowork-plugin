---
name: ev-transition-monitor
description: >
  This skill should be used when the user asks about "EV market update",
  "EV adoption rate", "EV vs ICE pricing", "Tesla market position",
  "EV lending risk", "electric vehicle trends", "EV depreciation",
  "EV price parity", "hybrid adoption", "electrification progress",
  "EV days supply", "which OEMs are winning EV", "EV penetration by state",
  "EV residual risk", "EV portfolio exposure", "EV collateral risk",
  or needs help tracking electric vehicle market dynamics for lending
  risk assessment and portfolio management.
version: 0.1.0
---

# EV Transition Monitor — Electric Vehicle Lending Risk Intelligence

## Lender Profile (Load First)

Before running any workflow, check for a saved lender profile:

1. Read `~/.claude/marketcheck/lender-profile.json`
2. If the file **does not exist**: This skill works without a profile. Ask: "Which aspect of the EV market?" and "Which state(s) or 'national'?"
3. If the file **exists**, extract silently:
   - `portfolio_focus` ← `lender.portfolio_focus` — determines output emphasis (leasing → residual focus, auto_loans → LTV focus, floor_plan → inventory risk focus)
   - `country` ← `location.country` (this skill is **US-only**)
   - `state` ← `location.state`
   - `tracked_segments` ← `lender.tracked_segments` — highlight EV if in tracked segments
   - `risk_ltv_threshold` ← `lender.risk_ltv_threshold`
   - `high_risk_ltv_threshold` ← `lender.high_risk_ltv_threshold`
4. **Country check:** If `country=UK`, stop: "EV transition monitoring requires US sold data. Not available for UK."
5. Confirm briefly: "Using profile: **[user.name]** (lender)"

## User Context

The primary user is a **lender** (residual value analyst, portfolio risk manager, or auto finance director) assessing EV residual risk, portfolio concentration exposure, and lending opportunity signals. Secondary users include **lease residual committees** setting EV-specific residual values and **floor plan providers** monitoring EV inventory risk on dealer lots.

Each metric includes an explicit signal with lending risk implications.

## Workflow: EV Market Scorecard

The comprehensive EV market analysis. Use for "EV market update" or "EV lending risk assessment."

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
- **EV Penetration %** = EV sold / total sold x 100
- **Hybrid Penetration %** = Hybrid sold / total sold x 100 (if available)
- **Combined Electrified %** = (EV + Hybrid) / total x 100
- **MoM Change (bps)** = (current % - prior %) x 100
- **3-Month Trend (bps)** = (current % - 3mo %) x 100
- **Lending Signal:** GROWING OPPORTUNITY if MoM > +20 bps AND 3mo > +50 bps (increasing origination volume); STABLE MARKET if stable +/-10 bps; CONTRACTING if MoM < -10 bps (review EV lending appetite)

### Step 2 — EV vs ICE pricing parity

Call `mcp__marketcheck__get_sold_summary` for each fuel type:
- `fuel_type_category`: `EV` -> get `average_sale_price`
- No filter (or `fuel_type_category`: `Gas`) -> get `average_sale_price` for ICE

Repeat for prior periods.

Calculate:
- **EV Avg Price** vs **ICE Avg Price**
- **Price Gap $** = EV - ICE
- **Price Gap %** = (EV - ICE) / ICE x 100
- **Gap Trend** = is the gap narrowing or widening?
- **Lending Signal:** APPROACHING PARITY if gap < 15% and narrowing (prepare for EV volume increase); STALLED if gap stable; DIVERGING if gap widening (EV remains niche — limited origination volume)

Break down by segment if possible:
- SUV: EV vs ICE price
- Sedan: EV vs ICE price
- Pickup: EV vs ICE price

### Step 3 — EV depreciation vs ICE (CRITICAL FOR LENDERS)

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
- **EV Monthly Depreciation %** = (3mo_price - current_price) / 3mo_price / 3 x 100
- **ICE Monthly Depreciation %** = same for ICE
- **Depreciation Ratio** = EV rate / ICE rate (e.g., 2.1x means EVs depreciate 2.1x faster)
- **Residual Risk Signal:** HIGH RISK if EV depreciation > 2x ICE (set EV residuals 8-12% lower than ICE equivalents); ELEVATED if 1.3x-2x (set EV residuals 5-8% lower); NORMALIZING if < 1.3x (EV residuals approaching ICE parity)

### Step 4 — EV days supply

Call `mcp__marketcheck__search_active_cars` with:
- `fuel_type`: `Electric`
- `car_type`: `new`
- `stats`: `price,dom`
- `rows`: 0

Plus sold data from Step 1 for volume.

Calculate:
- **EV New Days Supply** = active EV new / monthly EV new sold x 30
- **EV Used Days Supply** = active EV used / monthly EV used sold x 30
- Compare to ICE equivalents
- **Lending Signal:** DEMAND > SUPPLY if < 30 days (residuals supported); BALANCED if 30-60; SUPPLY BUILDING if > 60 (residual pressure ahead); GLUT if > 90 (residual risk HIGH — tighten advance rates on EV originations)

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
- Highlight Tesla vs legacy OEMs for portfolio concentration assessment
- **Signal per brand:** GAINING / LOSING / STABLE

### Step 6 — Regional EV adoption (optional)

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `summary_by`: `state`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 15

Calculate state-level EV penetration rate by also pulling total sold by state.

Identify: highest adoption states, fastest growing states, lowest adoption states. Map to lending implications — high-adoption states have better EV resale infrastructure and lower residual risk.

## Output

```
EV TRANSITION MONITOR — LENDING RISK EDITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: [State or National] | Period: [Current Month] vs [Prior Month] vs [3mo Ago]

ADOPTION METRICS
Metric                    | Current | Prior Mo | 3mo Ago | Trend      | Lending Signal
--------------------------|---------|----------|---------|------------|---------------
EV Penetration (% sales)  | X.X%    | X.X%     | X.X%    | +XX bps    | GROWING OPPORTUNITY
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

*** RESIDUAL RISK COMPARISON (CRITICAL) ***
                    | EV Rate   | ICE Rate  | Ratio   | Risk Signal
--------------------|-----------|-----------|---------|------------------
Used (all segments) | X.X%/mo   | X.X%/mo   | X.Xx    | [HIGH RISK / ELEVATED / NORMALIZING]
Used SUV            | X.X%/mo   | X.X%/mo   | X.Xx    |
Used Sedan          | X.X%/mo   | X.X%/mo   | X.Xx    |

SUPPLY HEALTH
                    | Days Supply | vs ICE    | Trend       | Signal
--------------------|-------------|-----------|-------------|--------
EV New              | XX days     | XX days   | Building    | [signal]
EV Used             | XX days     | XX days   | Drawing     | [signal]

BRAND EV SHARE (portfolio concentration risk)
Make      | EV Volume | EV Share % | MoM Change | Signal
----------|-----------|-----------|------------|--------
Tesla     | XX,XXX    | XX.X%      | -XXX bps   | LOSING SHARE
Hyundai   | X,XXX     | X.X%       | +XX bps    | GAINING
GM        | X,XXX     | X.X%       | +XX bps    | GAINING
Ford      | X,XXX     | X.X%       | +XX bps    | STABLE
BMW       | X,XXX     | X.X%       | +XX bps    | GAINING

[If regional data requested:]
TOP EV STATES (by penetration — higher adoption = lower residual risk)
State | EV Penetration | National Avg | Delta | EV Volume | MoM Trend
------|---------------|-------------|-------|-----------|----------
CA    | XX.X%          | X.X%         | +X.X% | XX,XXX    | +XX bps
WA    | X.X%           | X.X%         | +X.X% | X,XXX     | +XX bps
...

*** LENDER RISK ASSESSMENT ***

Residual Setting Guidance:
- EV depreciation running X.Xx ICE rate. Lease residual settings for EVs should be X-X% lower than ICE equivalents.
- [e.g., "EV used supply at XX days — expect further pricing pressure on 2-3 year old EVs. Reduce residual forecasts by X% for upcoming lease maturities."]

Advance Rate Guidance:
- [e.g., "EV LTV risk is elevated due to faster depreciation. Recommend maximum advance rate of XX% for EV loans (vs XX% for ICE)."]
- [e.g., "Require GAP coverage on all EV loans with LTV > XX% at origination."]

Portfolio Exposure:
- [e.g., "Tesla represents XX% of total EV volume. Portfolio concentration in Tesla-collateralized loans should be monitored. Tesla residuals are [better/worse] than the EV average."]
- [e.g., "EV adoption growing fastest in [states] — these markets have better EV resale infrastructure and lower liquidation risk."]

Origination Opportunity:
- [e.g., "Price parity narrowing in [segment] — expect increased EV loan demand. Prepare competitive EV lending products with appropriate risk-adjusted pricing."]
```

## Important Notes

- **US-only:** All data requires US `get_sold_summary`.
- Tesla dominates EV share nationally (~50-60%) — always contextualize portfolio concentration risk. A portfolio heavy in Tesla-collateralized loans has single-brand risk even within the EV segment.
- EV depreciation patterns differ significantly by brand: Tesla tends to hold value better than Nissan Leaf or Chevy Bolt. Break down by model when possible for accurate residual setting.
- The EV-to-ICE depreciation ratio is the single most important metric for EV lending risk. When the ratio drops below 1.3x, EV residuals are approaching ICE parity — this is the signal to normalize EV advance rates.
- EV battery degradation adds a non-linear depreciation component not captured in market price trends alone. For vehicles with >50K miles or >3 years old, consider an additional 2-3% residual haircut for battery risk.
