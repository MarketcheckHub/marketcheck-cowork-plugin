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

Before running any workflow, check for a saved user profile:

1. Read `~/.claude/marketcheck/analyst-profile.json`.
2. If the file **does not exist**: This skill works without a profile. Ask for make/model/segment focus. Suggest running `/onboarding` to set up a profile.
3. If the file **exists**, extract silently:
   - `analyst.tracked_tickers` — map to makes for default analysis targets
   - `analyst.tracked_makes` — direct vehicle brand focus
   - `analyst.tracked_states`
   - `analyst.benchmark_period_months`
   - `analyst.focus` — if `lending`, emphasize residual risk; if `oem`, emphasize pricing power
   - `location.country` (this skill is **US-only**)
4. **Country note:** This skill requires `get_sold_summary` and `search_active_cars` which are **US-only**. If `country == UK`, inform: "Depreciation tracking requires US sold transaction data and is not available for the UK market."
5. If profile exists, confirm: "Using profile: **[user.name]** ([user.company]), focus: [focus area]"

## User Context

The user is a **financial analyst** evaluating residual value trends as investment signals for:
- **OEM stocks** (F, GM, TM, etc.) — depreciation speed signals brand health, pricing power, and potential incentive spend requirements
- **Auto lending/leasing stocks** (ALD, ALLY, SC, etc.) — depreciation signals collateral erosion risk and residual value exposure
- **Dealer group stocks** (AN, LAD, KMX, etc.) — depreciation affects used car margins and inventory valuation

Every metric includes an explicit BULLISH / BEARISH / NEUTRAL / CAUTION signal with investment implications tied to specific tickers.

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

1. **Get current period sold data** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `date_from` set to the first of the current month minus 30 days, `date_to` set to the last day of that month. If the user specified a state, include `state`. Record the `average_sale_price` and `sold_count`.

2. **Get historical sold data at multiple intervals** — Make separate calls to `mcp__marketcheck__get_sold_summary` for each lookback period to build the curve:
   - **60 days ago**
   - **90 days ago**
   - **6 months ago**
   - **1 year ago**
   Record `average_sale_price` at each point. Adjust actual dates based on today's date.

3. **Get current active market asking price** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `car_type=used`, `stats=price`, `rows=0`. This gives the current asking price stats — the forward-looking indicator.

4. **Get original MSRP baseline** — Call `mcp__marketcheck__search_active_cars` with the same `year`, `make`, `model`, `rows=1`, `sort_by=price`, `sort_order=desc` to find a representative listing. Then call `mcp__marketcheck__decode_vin_neovin` with that listing's VIN to extract the original MSRP from the build data.

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

1. **Get current period segment data** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `inventory_type=Used`, `top_n=10`.

2. **Get prior period segment data** — Same call with dates shifted back 3 months.

3. **Get fuel type comparison** — Call for `fuel_type_category=EV` and ICE separately for current and prior period.

4. **Calculate segment trends with investment signals** — For each body type and fuel type:
   - **Period-over-period price change** with signal
   - **Volume change** with demand signal
   - Flag segments where price declined more than 3% as "ACCELERATING DEPRECIATION — BEARISH for OEMs heavy in this segment"
   - Map each segment to most-exposed tickers (e.g., Pickup depreciation → F, GM; EV depreciation → TSLA, RIVN, LCID)

5. **Deliver the segment comparison** — Present a ranked table from strongest retention to weakest. Highlight the EV vs ICE gap specifically with lending stock implications.

## Workflow: Brand Residual Ranking (OEM Stock Signal)

Use this when a user asks "which brands hold value best" or "rank OEMs by residual strength."

1. **Get current period brand prices** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `inventory_type=Used`, `top_n=25`.

2. **Get prior period brand prices** — Same call with dates shifted back 6 months.

3. **Get volume context** — Call with `ranking_measure=sold_count`.

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

1. **Get current MSRP parity data** — Call `mcp__marketcheck__get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=30`.

2. **Get prior period parity data** — Same call with dates shifted back 3 months.

3. **Classify parity status with investment signals** — For each make/model:
   - **Above MSRP** — BULLISH: demand exceeds supply, pricing power intact, positive for OEM margins
   - **At MSRP** (±1%) — NEUTRAL: balanced market
   - **Below MSRP** — BEARISH: incentive-dependent, margin pressure, signals OEM may need to increase incentive spend
   - Map to ticker and aggregate by OEM

4. **Present the parity report** with ticker-level summaries.

## Output Format

Always present results in this structure:

**Analysis Summary** — What was analyzed, time period, geography, and relevant tickers.

**Investment Signal Headline** — One sentence with ticker(s) and signal direction (e.g., "Ford (F) models have retained 87.3% of MSRP after 3 years, depreciating at 0.35%/month — BULLISH vs SUV segment average of 0.52% monthly. Signal: strong residual retention supports brand pricing power thesis for F.").

**Depreciation Curve / Trend Table** with signals per period.

**Ticker Impact Summary** — How depreciation trends affect each relevant ticker:
- OEM implications (incentive spend, production adjustments)
- Lending/leasing implications (residual exposure, advance rates)
- Dealer group implications (used car margins, inventory risk)

**Key Signals** — Bullet list with BULLISH/BEARISH/NEUTRAL/CAUTION per finding.

**Quantifiable Outcomes & KPIs**

| KPI | What to Show | Investment Impact |
|-----|-------------|-------------------|
| Monthly Depreciation Rate % | Price change velocity | 1%/month acceleration on $30K vehicle = $300/month additional residual exposure per unit for lessors |
| Residual Retention % | Current price / Original MSRP | Every 1% error on 36-month lease = ~$100-150 unrecovered value; multiply by OEM's lease portfolio size for stock impact |
| EV vs ICE Depreciation Ratio | Relative depreciation speed | If EVs depreciate 2x faster, OEM's EV lease book has outsized residual exposure |
| Brand Residual Ranking | Tier classification by retention | Tier changes trigger analyst downgrades; a Tier 1 → Tier 2 drop is a sell signal for residual-dependent OEMs |
| Price-Over-MSRP % | Transaction vs sticker | Positive = demand exceeding supply; negative = incentive dependency; direction change is the signal |

## Important Notes

- **US-only:** All data requires US sold transaction data.
- Always map depreciation findings back to stock tickers. An analyst needs to know "Ford (F) trucks depreciating at X%/month" not just "F-150 prices are falling."
- For EV vs ICE comparisons, explicitly call out implications for TSLA, RIVN, LCID as well as legacy OEMs with growing EV portfolios.
- Depreciation acceleration is a LEADING indicator — it precedes incentive spend increases (margin pressure), production cuts (revenue impact), and residual restatements (balance sheet hit). Frame accordingly.
- If a model is transitioning from above-MSRP to below-MSRP, this is a key inflection point — flag it prominently with the affected ticker.
