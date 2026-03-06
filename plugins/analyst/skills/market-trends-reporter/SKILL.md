---
name: market-trends-reporter
description: >
  This skill should be used when the user asks about "market trends",
  "fastest depreciating cars", "slowest depreciating models",
  "EV vs gas prices", "EV vs ICE price parity", "price trends by region",
  "new car markups", "new car discounts", "market report", "depreciation rankings",
  "what's happening in the auto market", "which cars are losing value fastest",
  "price drops this month", "regional price differences",
  "sector trend analysis", "auto market intelligence",
  or needs help with data-driven automotive market intelligence
  for sector analysis and investment research.
version: 0.1.0
---

# Market Trends Reporter — Market Intelligence for Sector Analysis

Generate investment-grade market trend analyses using real sold transaction data and live inventory signals. Every insight is mapped to stock tickers and framed with BULLISH / BEARISH / NEUTRAL / CAUTION investment signals.

## User Profile (Load First)

Before running any workflow, check for a saved user profile:

1. Read `~/.claude/marketcheck/analyst-profile.json`.
2. If the file **does not exist**: This skill works without a profile. Ask for geographic scope and focus. Suggest running `/onboarding` to set up a profile.
3. If the file **exists**, extract silently:
   - `analyst.tracked_tickers` — highlight in results
   - `analyst.tracked_makes` — brand focus
   - `analyst.tracked_states` — default geographic scope
   - `analyst.benchmark_period_months`
   - `location.country` (this skill is **US-only**)
4. **Country note:** If `country == UK`, inform: "Market trends reporting requires US sold transaction data and is not available for the UK market."
5. If profile exists, confirm: "Using profile: **[user.name]** ([user.company]), tracking [tickers]"

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

## User Context

The user is a **financial analyst** or **sector strategist** who needs market trend intelligence to inform investment decisions. Unlike consumer-facing trend reports, every insight is tied to stock tickers and includes explicit investment signals.

## Workflow: Fastest and Slowest Depreciating Models (Residual Signal)

Identify which models are losing value fastest (or holding value best) and map to OEM tickers.

1. Call `mcp__marketcheck__get_sold_summary` for the **current period**:
   - `inventory_type`: `Used`
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_sale_price`
   - `ranking_order`: `desc`
   - `top_n`: `50`
   - `state`: user's state filter (omit for national)

2. Repeat for the **prior period** (same month one year ago or 3 months ago per benchmark_period_months).

3. For each make/model, calculate:
   - **Depreciation Rate (%)** — only include models with 100+ units for statistical reliability
   - Map each model to its OEM ticker

4. Present two tables with tickers:
   - **Fastest Depreciating Models (Top 15)** — with ticker and investment signal
   - **Best Value-Holding Models (Bottom 15)** — with ticker

5. Investment narrative: "STLA models dominate the fast-depreciation list with 4 of the top 10 — BEARISH for STLA residual exposure. TM and TSLA models lead value retention — BULLISH for residual books."

6. For the top 3 fastest depreciating, pull current active listings as data points.

## Workflow: EV vs ICE Price Parity Tracker (Adoption Thesis Signal)

Track the price gap as a signal for EV adoption acceleration.

1. Call `mcp__marketcheck__get_sold_summary` for **EV** and **ICE** sales by body_type:
   - SUV, Sedan, Pickup segments
   - Current and prior periods

2. Calculate per body type:
   - **EV-to-ICE Price Gap ($)** and **(%)** with trend
   - **Year-over-Year Gap Change**
   - **Parity Signal:** APPROACHING PARITY (<15% gap, narrowing) = BULLISH for EV OEM tickers; STALLED = NEUTRAL; DIVERGING = BEARISH for mass-market EV thesis

3. Present with ticker implications:
   - Narrowing gap → BULLISH for TSLA, RIVN, LCID (addressable market expanding)
   - Widening gap → BEARISH for EV pure-plays (affordability barrier persists)
   - Segment-specific: "SUV parity approaching — BULLISH for GM (Equinox EV price point); Pickup gap still wide — CAUTION for F (Lightning pricing still premium)"

## Workflow: Regional Price Variance (Geographic Signal)

Reveal where specific vehicles are cheapest/most expensive for portfolio valuation context.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `make`, `model` from user
   - `summary_by`: `state`
   - `inventory_type`: `Used`
   - `limit`: `51`

2. Calculate:
   - **Price spread** between most and least expensive states
   - **State price index** = state avg / national avg × 100

3. Present with investment context:
   - Regional pricing variance affects dealer group earnings by geography
   - Large spreads indicate market inefficiency — relevant for CVNA and KMX (national pricing models) vs traditional dealers (local pricing)
   - State-level trends can signal regional economic health relevant to auto lending portfolios

## Workflow: New Car Markup and Discount Tracker (OEM Pricing Power Signal)

Identify which models sell above/below MSRP — the purest signal of supply/demand balance by OEM.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `inventory_type`: `New`
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `price_over_msrp_percentage`
   - `ranking_order`: `desc` (premiums) AND `asc` (discounts)
   - `top_n`: `20`

2. Also pull brand-level pricing power.

3. Present with ticker-level aggregation:
   - **OEM Pricing Power Ranking** (by ticker):
     - Ticker | Makes | Avg % Over/Under MSRP | # Models Above MSRP | # Models Below | Signal
   - **Signal:** BULLISH if OEM's average is above MSRP (pricing power intact); BEARISH if below (incentive-dependent); trend direction matters most

4. Investment narrative: "TM and BMWYY are the only tickers with positive MSRP parity across their lineup — BULLISH for margins. STLA has the deepest average discount at -5.2% — BEARISH for per-unit gross profit. F crossed from above-MSRP to below on 3 models this month — margin compression signal."

5. For prior-period comparison, show trend and flag models that flipped from premium to discount territory — these are inflection points.

## Output Format

- **Lead with the investment signal, not the data.** Example: "STLA models are depreciating 2x faster than TM — BEARISH signal for STLA residual exposure and future incentive spend requirements."
- **Always cite sample size.** Include sold count alongside price metrics for credibility.
- **Use ticker-level aggregation.** An analyst reads "GM" not "Chevrolet + GMC + Buick + Cadillac."
- **Include BULLISH/BEARISH/NEUTRAL/CAUTION signals** on every finding.
- **End with portfolio implications:** Which tickers to overweight/underweight based on trends.
- **Cite the data source and period** at the bottom of every output: "Source: MarketCheck transaction data, [Month Year], [Geography]."

## Important Notes

- **US-only:** Requires `get_sold_summary` for sold data.
- Always map brands to tickers. An analyst evaluating market trends is making stock-level decisions.
- Depreciation trends are LEADING indicators — they precede incentive changes, production adjustments, and earnings impacts by 1-2 quarters.
- The MSRP parity tracker is the purest signal of OEM pricing power — a shift from above-MSRP to below is a significant inflection point for the ticker.
- For comprehensive market intelligence, this skill combines well with the `market-momentum-report` for the broadest sector view.
