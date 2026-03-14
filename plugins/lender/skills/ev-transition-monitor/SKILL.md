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

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# EV Transition Monitor — Electric Vehicle Lending Risk Intelligence

## Lender Profile (Load First)

Load `~/.claude/marketcheck/lender-profile.json` if exists. Extract: `portfolio_focus`, `country`, `state`, `tracked_segments`, `risk_ltv_threshold`, `high_risk_ltv_threshold`. If missing, ask for EV focus area and geography. US-only. Confirm profile.

## User Context

Lender (residual analyst, portfolio risk manager, auto finance director) assessing EV residual risk, portfolio concentration exposure, and lending opportunity signals. Also serves lease residual committees and floor plan providers. Each metric includes an explicit lending risk signal.

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
→ **Extract only**: `sold_count` per fuel_type_category per period. Discard full response.

Calculate:
- **EV Penetration %** = EV sold / total sold x 100
- **Hybrid Penetration %** = Hybrid sold / total sold x 100 (if available)
- **Combined Electrified %** = (EV + Hybrid) / total x 100
- **MoM Change (bps)** = (current % - prior %) x 100
- **3-Month Trend (bps)** = (current % - 3mo %) x 100
- **Lending Signal:** GROWING OPPORTUNITY if MoM > +20 bps AND 3mo > +50 bps (increasing origination volume); STABLE MARKET if stable +/-10 bps; CONTRACTING if MoM < -10 bps (review EV lending appetite)

### Step 2 — EV vs ICE pricing parity

Call `mcp__marketcheck__get_sold_summary` for each fuel type:
- `fuel_type_category`: `EV` → get `average_sale_price`
- No filter (or `fuel_type_category`: `Gas`) → get `average_sale_price` for ICE

Repeat for prior periods.
→ **Extract only**: `average_sale_price` per fuel type per period. Discard full response.

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
→ **Extract only**: per make/model — `average_sale_price` per period. Discard full response.

Calculate:
- **EV Monthly Depreciation %** = (3mo_price - current_price) / 3mo_price / 3 x 100
- **ICE Monthly Depreciation %** = same for ICE
- **Depreciation Ratio** = EV rate / ICE rate (e.g., 2.1x means EVs depreciate 2.1x faster)
- **Residual Risk Signal:** HIGH RISK if EV depreciation > 2x ICE (set EV residuals 8-12% lower than ICE equivalents); ELEVATED if 1.3x-2x (set EV residuals 5-8% lower); NORMALIZING if < 1.3x (EV residuals approaching ICE parity)

### Step 4 — EV days supply

Call `mcp__marketcheck__search_active_cars` with:
- `fuel_type`: `Electric`, `car_type`: `new`, `stats`: `price,dom`, `rows`: 0

Plus sold data from Step 1 for volume.
→ **Extract only**: `num_found`, `stats.dom.mean`. Discard full response.

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
→ **Extract only**: per make — `sold_count` per period. Discard full response.

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
→ **Extract only**: per state — `sold_count`. Discard full response.

Calculate state-level EV penetration rate by also pulling total sold by state.

Identify: highest adoption states, fastest growing states, lowest adoption states. Map to lending implications — high-adoption states have better EV resale infrastructure and lower residual risk.

## Output

Present: EV lending risk headline, adoption/parity/depreciation/supply data tables with lending signals, brand EV share for portfolio concentration risk, and actionable lending policy recommendations (residual setting, advance rates, GAP requirements).

## Important Notes

- **US-only:** All data requires US `get_sold_summary`.
- Tesla dominates EV share nationally (~50-60%) — always contextualize portfolio concentration risk. A portfolio heavy in Tesla-collateralized loans has single-brand risk even within the EV segment.
- EV depreciation patterns differ significantly by brand: Tesla tends to hold value better than Nissan Leaf or Chevy Bolt. Break down by model when possible for accurate residual setting.
- The EV-to-ICE depreciation ratio is the single most important metric for EV lending risk. When the ratio drops below 1.3x, EV residuals are approaching ICE parity — this is the signal to normalize EV advance rates.
- EV battery degradation adds a non-linear depreciation component not captured in market price trends alone. For vehicles with >50K miles or >3 years old, consider an additional 2-3% residual haircut for battery risk.
