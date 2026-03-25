---
name: ev-transition-monitor
description: >
  EV market dynamics for OEM electrification strategy. Triggers: "EV market update",
  "EV adoption rate", "EV vs ICE pricing", "electrification progress",
  "EV penetration by state", "EV price parity", "hybrid adoption",
  "EV launch planning", "regional EV heatmap", "EV competitive position",
  "which OEMs are winning EV", "EV days supply", "electric vehicle trends",
  "EV strategy", "electrification strategy",
  tracking electric vehicle market dynamics for OEM strategy,
  regional launch planning, or competitive EV positioning.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# EV Transition Monitor — Electrification Strategy Intelligence for OEMs

## Manufacturer Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `brands`, `states`, `competitor_brands`, `country`. If missing, ask brand, states, and EV competitors. US-only; if UK, inform not available. Confirm profile.

## User Context

User is an OEM product planner, EV strategy lead, or regional manager tracking electrification progress and competitive EV positioning. Frame as ELECTRIFICATION STRATEGY with production, pricing, and launch implications.

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
→ **Extract only**: `sold_count` per fuel_type_category per period. Discard full response.

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
→ **Extract only**: `sold_count` (EV and total) per brand per period. Discard full response.

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
→ **Extract only**: `average_sale_price` per fuel type per period. Discard full response.

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
- `fuel_type`: `Electric`, `car_type`: `new`, `stats`: `price,dom`, `rows`: 0

For your brands specifically, also filter by `make`.
→ **Extract only**: `num_found`, `stats.dom.mean`. Discard full response.

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
→ **Extract only**: per make — `sold_count` per period. Discard full response.

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
→ **Extract only**: per state — `sold_count`. Discard full response.

Calculate state-level EV penetration rate by also pulling total sold by state.

For your brand specifically, also calculate your brand's EV penetration per state.

Identify:
- **Highest EV adoption states** — priority markets for EV launches
- **Fastest growing EV states** — emerging opportunities
- **Your brand's EV strongholds** vs **underperforming states**
- **States where competitors lead EV** — conquest opportunities

## Output

Present: your brand's EV position headline (penetration vs market/competitors), adoption metrics table, price parity progress by segment, days supply with production signals, brand EV share rankings, regional heatmap with launch priorities, and actionable electrification strategy recommendations.

## Important Notes

- **US-only:** All data requires US `get_sold_summary`.
- Tesla dominates EV share nationally (~50-60%) — always contextualize your share and competitors' share as "ex-Tesla" if helpful.
- EV depreciation patterns differ significantly by brand — note this when discussing pricing.
- The EV-to-ICE price gap is the single most important metric for adoption forecasting. Once the gap drops below 10% in a segment, adoption typically accelerates nonlinearly.
- Frame everything for the manufacturer audience: production planning, allocation decisions, incentive strategy, regional launch timing.
- When showing regional data, always overlay your brand's performance against the market to identify gaps and opportunities.
