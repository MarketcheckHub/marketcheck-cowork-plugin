---
name: oem-stock-tracker
description: >
  This skill should be used when the user asks about "OEM stock signal",
  "how is Ford doing", "Toyota demand trends", "brand health check",
  "investment signal for [OEM]", "pricing power analysis", "days supply",
  "OEM market share trends", "brand volume momentum", "inventory build",
  or needs help tracking leading indicators for publicly traded automotive
  OEMs to support equity research and investment decisions.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# OEM Stock Tracker — Leading Indicators for Automotive Investment Decisions

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for OEM/ticker and geography. US-only. Confirm profile.

## User Context

Financial analyst (equity researcher, hedge fund analyst, portfolio manager) needing leading indicators for investment decisions on publicly traded automotive OEMs. Each metric includes BULLISH/BEARISH/NEUTRAL/CAUTION signal tied to stock tickers.

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

If the user provides a ticker, map it to makes using this table. If the user provides a make name (e.g., "Ford"), reverse-map to the ticker. For dealer group tickers, redirect to the `dealer-group-health-monitor` skill.

## Workflow: OEM Investment Signal

Use this when a user asks "How is Ford doing?" or "Investment signal for GM" or "Toyota demand trends."

### Step 1 — Resolve the entity

Map the user's input (ticker or brand name) to the list of makes using the built-in mapping. Confirm: "Analyzing **[Ticker]** ([Company Name]): [Make1, Make2, ...]"

Determine date ranges:
- **Current month:** first day of the most recent complete month → last day
- **Prior month:** the month before current
- **Baseline (3 months ago):** from `analyst.benchmark_period_months` or default 3

### Step 2 — Volume momentum

For EACH make in the ticker's mapping, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the make
- `state`: from profile or user input (or omit for national)
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 1

Repeat for prior month and 3-month-ago period.
→ **Extract only**: `sold_count` per make per period. Discard full response.

Sum sold_count across all makes for the ticker.

Calculate:
- **MoM Volume Change %** = (current - prior) / prior × 100
- **3-Month Trend %** = (current - 3mo_ago) / 3mo_ago × 100
- **Signal:** BULLISH if MoM > +3% AND 3mo > +5%; BEARISH if MoM < -3% AND 3mo < -5%; NEUTRAL if mixed; CAUTION if MoM positive but 3mo negative (short-term bounce)

### Step 3 — Pricing power

For each make, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the make
- `state`: from profile or user input
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `average_sale_price`
- `top_n`: 1

Repeat for prior month.
→ **Extract only**: `average_sale_price` per make per period. Discard full response.

Also call for new vehicles specifically to get MSRP positioning:
- `inventory_type`: `New`
- `ranking_measure`: `price_over_msrp_percentage`
→ **Extract only**: `price_over_msrp_percentage` per make per period. Discard full response.

Calculate:
- **Avg Sale Price Change %** = MoM change in average_sale_price
- **Price vs MSRP %** = price_over_msrp_percentage (positive = above sticker, negative = discounting)
- **MSRP Trend (bps)** = (current MSRP % - prior MSRP %) × 100
- **Signal:** BULLISH if price rising AND above MSRP; BEARISH if price falling AND below MSRP (deepening discounts); CAUTION if price stable but MSRP shifting negative

### Step 4 — Inventory health (Days Supply)

Call `mcp__marketcheck__search_active_cars` with:
- `make`: each make
- `state` (via `seller_state`) or national
- `car_type`: `new`
- `stats`: `price,dom`
- `rows`: 0

This gives total active NEW inventory count and average DOM.
→ **Extract only**: `num_found`, dom stats per make. Discard full response.

Call `mcp__marketcheck__get_sold_summary` for the same make/state/period to get monthly sold volume.
→ **Extract only**: `sold_count` per make. Discard full response.

Calculate:
- **Days Supply** = (Active Inventory Count / Monthly Sold Count) × 30
- **Signal:** BULLISH if < 45 days (tight supply, pricing power); NEUTRAL if 45-75 days; BEARISH if > 75 days (building inventory, production cuts likely); CAUTION if rising rapidly (>15% MoM increase)

### Step 5 — Market share

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile or user input
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 25

Repeat for prior month.
→ **Extract only**: `make`, `sold_count` per period. Discard full response.

Calculate the OEM's aggregate share across its makes:
- **Current Share %** = sum of OEM's makes sold / total sold × 100
- **Prior Share %** = same for prior month
- **Share Change (bps)** = (current - prior) × 100
- **Signal:** BULLISH if gaining > +30 bps; BEARISH if losing > -30 bps; NEUTRAL if within ±30 bps

### Step 6 — DOM trend (demand softness)

From the sold data in Step 2/3, extract `average_days_on_market` for each period.

Calculate:
- **DOM MoM Change %** = (current_dom - prior_dom) / prior_dom × 100
- **Signal:** BULLISH if DOM falling (selling faster); BEARISH if DOM rising > 10% (demand softening); NEUTRAL if stable

### Step 7 — EV transition (if applicable)

If the OEM sells EVs (Tesla, Rivian, Lucid, or legacy OEMs with EV models):

Call `mcp__marketcheck__get_sold_summary` with:
- `make`: the OEM's makes
- `fuel_type_category`: `EV`
- Current and prior periods
→ **Extract only**: `sold_count`, `average_sale_price` per period. Discard full response.

Calculate:
- **EV % of OEM's total sales** = EV sold / total OEM sold × 100
- **EV MoM change (bps)** = trend direction
- **EV avg price** and MoM change

For EV pure-plays (TSLA, RIVN, LCID), this IS the entire analysis. For legacy OEMs, it shows transition progress.

### Step 8 — Segment mix

Call `mcp__marketcheck__get_sold_summary` with:
- `make`: each of the OEM's makes
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `sold_count`
- Current period
→ **Extract only**: `body_type`, `sold_count`, `average_sale_price` per segment. Discard full response.

Calculate share by segment (Pickup, SUV, Sedan, EV, etc.) and pricing trend per segment.

## Output

Present: composite investment thesis headline (BULLISH/BEARISH/MIXED/NEUTRAL) with ticker, leading indicators table (volume, ASP, MSRP positioning, days supply, market share, DOM), EV transition metrics if applicable, segment mix, and ticker impact statement connecting data to earnings implications.

## Signal Classification Logic

For the composite thesis:
- **BULLISH:** 4+ of 6 leading indicators are BULLISH, none are BEARISH
- **BEARISH:** 4+ are BEARISH or CAUTION, volume AND pricing power both negative
- **MIXED:** Conflicting signals (volume up but pricing down, or vice versa)
- **NEUTRAL:** Most indicators stable, no strong directional signal

Always provide the specific data that drives each signal — analysts need to verify the reasoning, not just the conclusion. Always tie the conclusion back to the stock ticker and expected earnings impact.

## Multi-OEM Comparison

If the user asks "compare Ford vs GM" or "which OEM is winning":

1. Run the full workflow for each OEM
2. Present a side-by-side comparison table:
   ```
   Metric              | Ford (F) | GM (GM) | Advantage
   --------------------|----------|---------|----------
   Volume MoM          | +3.8%    | +1.2%   | Ford
   Pricing Power       | -0.9%    | +0.3%   | GM
   Days Supply         | 72       | 58      | GM
   Market Share Change  | +30 bps  | -15 bps | Ford
   EV Penetration      | 4.2%     | 6.1%    | GM
   ```
3. Deliver a relative thesis: "Ford (F) has stronger volume momentum but GM has better inventory discipline and faster EV adoption. For a long/short pair trade, consider long GM / short F on margin expansion thesis."

## Important Notes

- This skill is **US-only**. All data comes from `get_sold_summary` and `search_active_cars` which require US market data.
- Date ranges should use the most recent COMPLETE month. If today is March 5, use February as "current month."
- If a make has very low volume (< 100 units/month nationally), note low sample size and reduce confidence.
- For EV pure-plays (TSLA, RIVN, LCID), skip the EV Transition section (all their sales are EV) and instead focus on total volume, pricing, and DOM.
- Always cite the actual numbers, not just signals. An analyst needs to cross-reference against their own models.
- Always map insights back to stock tickers. A financial analyst thinks in tickers, not brand names.
