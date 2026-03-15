---
name: pricing-power-tracker
description: >
  This skill should be used when the user asks about "pricing power",
  "discount rate", "discount trend", "MSRP vs sale price", "who's discounting",
  "incentive activity", "pricing erosion", "discount velocity",
  "which OEMs are discounting most aggressively", "pricing power over time",
  or needs help tracking how OEM/nameplate discount-to-MSRP trends evolve
  over multiple months as a leading indicator of margin pressure.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Pricing Power Tracker — Discount-to-MSRP Trend Intelligence for Investment Decisions

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for OEM/ticker and geography. US-only. Confirm profile.

## User Context

Financial analyst (equity researcher, hedge fund analyst, portfolio manager) needing to track pricing power trends over time. Discount-to-MSRP trajectory is a leading indicator of margin pressure — widening discounts signal incentive spend acceleration and earnings risk. This skill focuses exclusively on TRENDS over multiple periods, not snapshots.

## Built-in Ticker → Makes Mapping

```
OEM TICKERS:
F     → Ford, Lincoln
GM    → Chevrolet, GMC, Buick, Cadillac
TM    → Toyota, Lexus
HMC   → Honda, Acura
STLA  → Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati
TSLA  → Tesla
RIVN  → Rivian
LCID  → Lucid
HYMTF → Hyundai, Kia, Genesis
NSANY → Nissan, Infiniti
MBGAF → Mercedes-Benz
BMWYY → BMW, MINI, Rolls-Royce
VWAGY → Volkswagen, Audi, Porsche, Lamborghini, Bentley

DEALER GROUP TICKERS:
AN    → AutoNation
LAD   → Lithia Motors
PAG   → Penske Automotive
SAH   → Sonic Automotive
GPI   → Group 1 Automotive
ABG   → Asbury Automotive
KMX   → CarMax
CVNA  → Carvana
```

If the user provides a ticker, map it to makes. If the user provides a make name, reverse-map to the ticker. For dealer group tickers, note that pricing power analysis is most relevant for OEM tickers.

## Workflow 1: OEM Discount Rate Trend (Multi-Period)

Use when user asks "discount trend for Ford" or "pricing power over time for GM."

### Step 1 — Resolve entity and periods

Map ticker to makes. Determine 5 time periods:
- **Period 1 (current):** most recent complete month
- **Period 2:** 1 month prior
- **Period 3:** 2 months prior
- **Period 4:** 3 months prior
- **Period 5:** 6 months prior (from `benchmark_period_months` or default 6)

### Step 2 — Pull discount data per period

For EACH period, call `mcp__marketcheck__get_sold_summary` with:
- `make`: each make in the ticker's mapping
- `state`: from profile or user input (or omit for national)
- `inventory_type`: `New`
- `date_from` / `date_to`: the period's date range
- `ranking_dimensions`: `make`
- `ranking_measure`: `price_over_msrp_percentage`
- `top_n`: 1

→ **Extract only**: `price_over_msrp_percentage`, `sold_count` per make per period. Discard full response.

### Step 3 — Calculate trend metrics

- **Discount Rate per Period:** Average `price_over_msrp_percentage` across the ticker's makes (weighted by sold_count)
- **MoM Discount Change (bps):** (current_% - prior_%) × 100
- **3-Month Discount Velocity (bps/month):** (current_% - 3mo_%) / 3 × 100
- **6-Month Trajectory:** Direction of change from Period 5 → Period 1

### Step 4 — Signal assignment

| Signal | Threshold |
|--------|-----------|
| BULLISH | Discount narrowing >30 bps/month OR above-MSRP (positive price_over_msrp_percentage) |
| NEUTRAL | Discount stable within ±20 bps/month |
| CAUTION | Discount widening 20–50 bps/month |
| BEARISH | Discount widening >50 bps/month OR >5% below MSRP |

## Workflow 2: Nameplate Discount Ranking

Use when user asks "which Ford models are discounted most" or "nameplate pricing power."

### Step 1 — Pull nameplate-level data

Call `mcp__marketcheck__get_sold_summary` with:
- `make`: each make in the ticker's mapping
- `state`: from profile
- `inventory_type`: `New`
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `price_over_msrp_percentage`
- `ranking_order`: `asc` (deepest discounts first)
- `top_n`: 15

→ **Extract only**: `make`, `model`, `price_over_msrp_percentage`, `sold_count` per model. Discard full response.

### Step 2 — Identify pricing leaders and laggards

- **Pricing Leaders:** Models selling above MSRP (positive %) — strong demand, no incentive needed
- **Pricing Laggards:** Models >3% below MSRP — incentive-dependent, margin drag
- **Volume Impact:** Weight by sold_count to determine which models drive the ticker's aggregate discount

## Workflow 3: Within-Segment Comparison

Use when user asks "who has pricing power in SUVs" or "pickup truck discount comparison."

### Step 1 — Pull segment-specific data

For a given `body_type` (SUV, Pickup, Sedan, etc.), call `mcp__marketcheck__get_sold_summary` with:
- `body_type`: the target segment
- `state`: from profile
- `inventory_type`: `New`
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `price_over_msrp_percentage`
- `ranking_order`: `desc`
- `top_n`: 15

→ **Extract only**: `make`, `price_over_msrp_percentage`, `sold_count` per make. Discard full response.

### Step 2 — Rank by pricing power within segment

Map makes to tickers. Rank by `price_over_msrp_percentage` (highest = strongest pricing power). Flag tracked tickers. Identify segment leaders and laggards with investment signal per ticker.

## Workflow 4: Discount Velocity Alert

Use when user asks "which OEMs are discounting faster" or "pricing erosion acceleration."

### Step 1 — Pull two-period data for all OEMs

Call `mcp__marketcheck__get_sold_summary` for current month and 3 months ago with:
- `state`: from profile
- `inventory_type`: `New`
- `ranking_dimensions`: `make`
- `ranking_measure`: `price_over_msrp_percentage`
- `ranking_order`: `asc`
- `top_n`: 25

→ **Extract only**: `make`, `price_over_msrp_percentage`, `sold_count` per period. Discard full response.

### Step 2 — Calculate velocity and rank

- **Discount Velocity** = (current_% - 3mo_%) / 3 (bps per month)
- Rank all makes by velocity (most negative = fastest discounting)
- Map to tickers and aggregate

### Step 3 — Signal and alert

Flag tickers where discount velocity exceeds -50 bps/month as BEARISH. Present ranked table with velocity, current discount rate, and signal.

## Output

Present: discount trajectory chart data (5-period table with %, bps change, velocity), nameplate-level breakdown for target ticker, within-segment ranking, velocity alert table. Every metric includes BULLISH/BEARISH/NEUTRAL/CAUTION signal with rationale. Always tie to ticker and earnings implications (deeper discounting = lower gross margin per unit = earnings headwind).

## Important Notes

- This skill is **US-only**. All data from `get_sold_summary` requires US market data.
- `price_over_msrp_percentage` is only meaningful for **new** vehicles (`inventory_type=New`). Do not apply to used vehicles.
- Date ranges should use the most recent COMPLETE month.
- Low volume makes (<100 units/month) should be flagged with reduced confidence.
- Always cite actual numbers, not just signals. Analysts need to verify against their own models.
- Always map insights back to stock tickers.
- Differentiation from existing skills: `market-trends-reporter` and `depreciation-tracker` do point-in-time MSRP snapshots. This skill tracks the TRAJECTORY over 5+ periods and calculates velocity (rate of change of discount rate).
