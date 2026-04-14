---
name: ev-transition-monitor
description: >
  EV investment thesis and equity research intelligence. Triggers: "EV market update",
  "EV adoption rate", "EV vs ICE pricing", "Tesla market position",
  "EV investment signal", "electric vehicle trends", "EV depreciation",
  "EV price parity", "hybrid adoption", "electrification progress",
  "EV days supply", "which OEMs are winning EV", "EV penetration by state",
  "EV investment thesis", "EV stock signal", "electrification transition risk",
  tracking electric vehicle market dynamics for investment
  thesis development and equity research.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

> **`get_sold_summary` parameter safety:**
> - **Always set `inventory_type`** explicitly (`New` or `Used`) — omitting it defaults to `New`, returning zero results for used-vehicle queries
> - **Always set `limit: 5000`** — the default (1000) silently truncates when (months × states × ranking combos) exceeds 1000 rows
> - **For volume totals**, use `ranking_dimensions: dealership_group_name` (or the single relevant dimension) — never use the default `make,model,body_type` which creates ~150K rows for national 3-month queries
> - **Use separate calls** for totals vs breakdowns — don't combine in one call

# EV Transition Monitor — EV Investment Thesis Intelligence

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for EV focus area and geography. US-only. Confirm profile.

## User Context

Financial analyst tracking EV pure-plays (TSLA, RIVN, LCID) or legacy OEM electrification progress for investment thesis development. Every metric framed as investment signal tied to stock tickers with BULLISH/BEARISH/NEUTRAL/CAUTION ratings.

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
- `inventory_type`: `New` (or `Used` if analyzing used EV market)
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `fuel_type_category`
- `ranking_measure`: `sold_count`
- `top_n`: 5
- `limit`: `5000`

Repeat for total market (no fuel_type_category filter, but keep `inventory_type` and `limit: 5000`). Also repeat for prior month and 3 months ago.
→ **Extract only**: `sold_count` per fuel_type_category per period. Discard full response.

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
- `inventory_type`: `New` (or `Used` — always set explicitly)
- `limit`: `5000`

Repeat for prior periods (same parameters).
→ **Extract only**: `average_sale_price` per fuel type per period. Discard full response.

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
- `limit`: `5000`
- Current month AND 3 months ago

Repeat without fuel_type filter for ICE comparison (keep `inventory_type: Used`, `limit: 5000`).
→ **Extract only**: per make/model — `average_sale_price` per period. Discard full response.

Calculate:
- **EV Monthly Depreciation %** = (3mo_price - current_price) / 3mo_price / 3 × 100
- **ICE Monthly Depreciation %** = same for ICE
- **Depreciation Ratio** = EV rate / ICE rate (e.g., 2.1x means EVs depreciate 2.1x faster)
- **Signal:** HIGH RISK if EV depreciation > 2x ICE — BEARISH for OEM residual exposure, lessors, and auto lender stocks; MODERATE if 1.3x-2x — CAUTION; NORMALIZING if < 1.3x — BULLISH for EV maturation thesis

### Step 4 — EV days supply

Call `mcp__marketcheck__search_active_cars` with:
- `fuel_type`: `Electric`, `car_type`: `new`, `stats`: `price,dom`, `rows`: 0

Plus sold data from Step 1 for volume.
→ **Extract only**: `num_found`, `stats.dom.mean`. Discard full response.

Calculate:
- **EV New Days Supply** = active EV new / monthly EV new sold × 30
- **EV Used Days Supply** = active EV used / monthly EV used sold × 30
- Compare to ICE equivalents
- **Signal:** DEMAND > SUPPLY if < 30 days (BULLISH for EV OEMs — pricing power intact); BALANCED if 30-60; SUPPLY BUILDING if > 60 (BEARISH — production outpacing demand); GLUT if > 90 (BEARISH — expect incentive increases and margin pressure)

### Step 5 — Brand-level EV share (competitive positioning)

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `inventory_type`: `New` (or `Used` — always set explicitly)
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 15
- `limit`: `5000`
- Current month AND prior month
→ **Extract only**: per make — `sold_count` per period. Discard full response.

Calculate:
- **Brand EV Share %** = brand EV sold / total EV sold × 100
- **MoM Share Change (bps)**
- Highlight TSLA, RIVN, LCID vs legacy OEMs
- Map each brand to its ticker
- **Signal per brand:** GAINING / LOSING / STABLE

### Step 6 — Regional EV adoption (optional)

Call `mcp__marketcheck__get_sold_summary` with:
- `fuel_type_category`: `EV`
- `inventory_type`: `New` (or `Used` — always set explicitly)
- `summary_by`: `state`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 15
- `limit`: `5000` (critical: `summary_by=state` multiplies rows by ~50 states)
→ **Extract only**: per state — `sold_count`. Discard full response.

Calculate state-level EV penetration rate by also pulling total sold by state.

Identify: highest adoption states, fastest growing states, lowest adoption states.

## Output

Present: EV investment thesis headline with ticker signals, adoption/parity/depreciation/supply data tables, brand EV share with ticker mapping for competitive positioning, and investment implications by ticker (EV pure-plays, legacy OEM transition progress, auto lender/lessor exposure).

## Important Notes

- **US-only:** All data requires US `get_sold_summary`.
- Tesla dominates EV share nationally (~50-60%) — always contextualize other OEMs' share as "ex-Tesla" if helpful.
- EV depreciation patterns differ significantly by brand: Tesla tends to hold value better than Nissan Leaf or Chevy Bolt. Break down by model when possible.
- The EV-to-ICE price gap is the single most important metric for adoption forecasting. Once the gap drops below 10% in a segment, adoption typically accelerates nonlinearly — this is a key inflection point for the investment thesis.
- Always map makes to stock tickers. An analyst tracking EV transition is evaluating specific stock positions, not abstract brand preferences.
- For every metric, explicitly state the investment signal direction and which tickers are affected.
