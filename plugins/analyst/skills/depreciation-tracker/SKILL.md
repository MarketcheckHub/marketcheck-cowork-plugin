---
name: depreciation-tracker
description: >
  This skill should be used when the user asks about "depreciation rate",
  "value retention", "residual value", "how fast is it losing value",
  "which cars hold value", "EV depreciation", "price trend over time",
  "brand value ranking", "depreciation curve", "residual forecast",
  "MSRP parity", "price over sticker", "residual risk signal",
  "OEM residual exposure", "lending stock risk", "collateral erosion",
  or needs help with vehicle depreciation analysis framed as residual
  value signals for OEM stocks, auto lending stocks, and leasing companies.
version: 0.1.0
---

# Depreciation Tracker — Residual Value Signals for OEM & Lending Stocks

## User Profile (Load First)

Load `~/.claude/marketcheck/analyst-profile.json` if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `focus`, `country`. If missing, ask for make/model/segment focus. US-only. Confirm profile.

## User Context

Financial analyst evaluating residual value trends as investment signals for OEM stocks (pricing power, incentive spend), auto lending/leasing stocks (collateral erosion, residual exposure), and dealer group stocks (used car margins, inventory valuation). Every metric includes BULLISH/BEARISH/NEUTRAL/CAUTION signal tied to specific tickers.

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
```

## Workflow: Make/Model Depreciation Curve (Investment Signal)

Use this when a user asks "how fast is the RAV4 losing value" or "depreciation signal for Ford trucks."

1. **Get current period sold data** — Call `get_sold_summary` with `make`, `model`, `inventory_type=Used`, `date_from` (first of prior month), `date_to` (end of prior month). Include `state` if specified.
   → **Extract only**: average_sale_price, sold_count. Discard full response.

2. **Get historical sold data at multiple intervals** — Make separate calls to `get_sold_summary` for each lookback period:
   - **60 days ago**
   - **90 days ago**
   - **6 months ago**
   - **1 year ago**
   Record `average_sale_price` at each point. Adjust dates based on today's date.
   → **Extract only**: average_sale_price per interval. Discard full response.

3. **Get current active market asking price** — Call `search_active_cars` with `year`, `make`, `model`, `car_type=used`, `stats=price`, `rows=0`. Include `zip`/`state` if available.
   → **Extract only**: mean, median, min, max price stats. Discard full response.

4. **Get original MSRP baseline** — Call `search_active_cars` with same YMMT, `rows=1`, `sort_by=price`, `sort_order=desc`. Decode the VIN for MSRP. Fallback: highest 1-year-ago sold price.
   → **Extract only**: msrp from decode. Discard full response.

5. **Build the depreciation curve with investment signal** — Calculate at each time interval:
   - **Retention %** = (average_sale_price at interval / original MSRP) × 100
   - **Monthly depreciation rate** = (price change between consecutive intervals) / (months between intervals)
   - **Annualized depreciation rate** = monthly rate × 12
   - **Signal:**
     - **BEARISH** for OEM ticker: Monthly rate > 1.5% — "Accelerating depreciation suggests residual erosion; OEM may need production cuts or increased incentive spend"
     - **CAUTION**: Monthly rate 0.8-1.5% — "Moderate depreciation; watch for acceleration"
     - **NEUTRAL**: Monthly rate 0.3-0.8% — "Normal depreciation within historical range"
     - **BULLISH** for OEM ticker: Monthly rate < 0.3% or appreciating — "Strong residual retention signals pricing power and brand desirability"

## Workflow: Segment Value Trends (Sector Signal)

Use this when a user asks "are SUVs holding value better than sedans" or "EV depreciation vs ICE — investment implications."

1. **Get current period segment data** — Call `get_sold_summary` with `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `date_from` (first of prior month), `date_to` (end of prior month), `inventory_type=Used`, `top_n=10`.
   → **Extract only**: per body_type — average_sale_price, sold_count. Discard full response.

2. **Get prior period segment data** — Same call with dates shifted back 3 months (or user's chosen comparison window).
   → **Extract only**: per body_type — average_sale_price, sold_count. Discard full response.

3. **Get fuel type comparison** — Call `get_sold_summary` with `fuel_type_category=EV`, current period dates, `inventory_type=Used`. Repeat with `fuel_type_category=ICE`. Repeat both for prior period.
   → **Extract only**: average_sale_price, sold_count per fuel_type per period. Discard full response.

4. **Calculate segment trends with investment signals** — For each body type and fuel type:
   - **Period-over-period price change** with signal
   - **Volume change** with demand signal
   - Flag segments where price declined more than 3% as "ACCELERATING DEPRECIATION — BEARISH for OEMs heavy in this segment"
   - Map each segment to most-exposed tickers (e.g., Pickup depreciation → F, GM; EV depreciation → TSLA, RIVN, LCID)

5. **Deliver the segment comparison** — Present a ranked table from strongest retention to weakest. Highlight the EV vs ICE gap specifically with lending stock implications.

## Workflow: Brand Residual Ranking (OEM Stock Signal)

Use this when a user asks "which brands hold value best" or "rank OEMs by residual strength."

1. **Get current period brand prices** — Call `get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (end of prior month), `inventory_type=Used`, `top_n=25`.
   → **Extract only**: per make — average_sale_price. Discard full response.

2. **Get prior period brand prices** — Same call with dates shifted back 6 months.
   → **Extract only**: per make — average_sale_price. Discard full response.

3. **Get volume context** — Call `get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, current period dates, `inventory_type=Used`, `top_n=25`.
   → **Extract only**: per make — sold_count. Discard full response.

4. **Calculate brand retention scores with ticker mapping** — For each make:
   - **Retention %** = current average_sale_price / prior average_sale_price × 100
   - Map to ticker
   - Rank by retention % descending
   - Tier classification:
     - Tier 1 (>98% retention) — BULLISH: Strong residual retention = pricing power
     - Tier 2 (95-98%) — NEUTRAL: Normal depreciation
     - Tier 3 (90-95%) — CAUTION: Accelerating, watch for incentive spend
     - Tier 4 (<90%) — BEARISH: Significant residual erosion

5. **Present the brand ranking** with investment thesis per tier.

## Workflow: MSRP Parity Tracker (Pricing Power Signal)

Use this when a user asks "which new cars are selling over sticker" or "pricing power by OEM."

1. **Get current MSRP parity data** — Call `get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (end of prior month), `top_n=30`.
   → **Extract only**: per make/model — price_over_msrp_percentage. Discard full response.

2. **Get prior period parity data** — Same call with dates shifted back 3 months.
   → **Extract only**: per make/model — price_over_msrp_percentage. Discard full response.

3. **Classify parity status with investment signals** — For each make/model:
   - **Above MSRP** — BULLISH: demand exceeds supply, pricing power intact, positive for OEM margins
   - **At MSRP** (±1%) — NEUTRAL: balanced market
   - **Below MSRP** — BEARISH: incentive-dependent, margin pressure, signals OEM may need to increase incentive spend
   - Map to ticker and aggregate by OEM

4. **Present the parity report** with ticker-level summaries.

## Output

Present: investment signal headline with ticker and direction, depreciation curve/trend data table with signals, ticker impact summary (OEM, lending/leasing, dealer group implications), and key BULLISH/BEARISH/NEUTRAL/CAUTION signals per finding.

## Important Notes

- **US-only:** All data requires US sold transaction data.
- Always map depreciation findings back to stock tickers. An analyst needs to know "Ford (F) trucks depreciating at X%/month" not just "F-150 prices are falling."
- For EV vs ICE comparisons, explicitly call out implications for TSLA, RIVN, LCID as well as legacy OEMs with growing EV portfolios.
- Depreciation acceleration is a LEADING indicator — it precedes incentive spend increases (margin pressure), production cuts (revenue impact), and residual restatements (balance sheet hit). Frame accordingly.
- If a model is transitioning from above-MSRP to below-MSRP, this is a key inflection point — flag it prominently with the affected ticker.
