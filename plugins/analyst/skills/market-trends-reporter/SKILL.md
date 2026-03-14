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

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Trends Reporter — Market Intelligence for Sector Analysis

Generate investment-grade market trend analyses using real sold transaction data and live inventory signals. Every insight is mapped to stock tickers and framed with BULLISH / BEARISH / NEUTRAL / CAUTION investment signals.

## User Profile (Load First)

Load `~/.claude/marketcheck/analyst-profile.json` if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for geographic scope and focus. US-only. Confirm profile.

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

Financial analyst or sector strategist needing market trend intelligence for investment decisions. Every insight tied to stock tickers with explicit BULLISH/BEARISH/NEUTRAL/CAUTION investment signals.

## Workflow: Fastest and Slowest Depreciating Models (Residual Signal)

Identify which models are losing value fastest (or holding value best) and map to OEM tickers.

1. **Current period sold summary** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (current month), `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=50`, `state` if scoped.
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

2. **Prior period sold summary** — Repeat step 1 for same month one year ago (or per benchmark_period_months).
   → **Extract only**: make, model, average_sale_price, sold_count per entry. Discard full response.

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

1. **EV + ICE sold summary by segment** — Call `mcp__marketcheck__get_sold_summary` for each `fuel_type_category` (EV, ICE) x `body_type` (SUV, Sedan, Pickup) x period (current, prior). Use `ranking_dimensions=make,model`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`.
   → **Extract only**: average_sale_price, sold_count per fuel_type/body_type/period combo. Discard full response.

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

1. **Sold summary by state** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `make`, `model`, `inventory_type=Used`, `summary_by=state`, `limit=51`.
   → **Extract only**: per state — average_sale_price, sold_count. Discard full response.

2. Calculate:
   - **Price spread** between most and least expensive states
   - **State price index** = state avg / national avg × 100

3. Present with investment context:
   - Regional pricing variance affects dealer group earnings by geography
   - Large spreads indicate market inefficiency — relevant for CVNA and KMX (national pricing models) vs traditional dealers (local pricing)
   - State-level trends can signal regional economic health relevant to auto lending portfolios

## Workflow: New Car Markup and Discount Tracker (OEM Pricing Power Signal)

Identify which models sell above/below MSRP — the purest signal of supply/demand balance by OEM.

1. **Top markups + deepest discounts** — Call `mcp__marketcheck__get_sold_summary` with `date_from`/`date_to` (recent month), `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `top_n=20`. Run twice: `ranking_order=desc` (premiums), then `ranking_order=asc` (discounts).
   → **Extract only**: make, model, price_over_msrp_percentage, sold_count per entry. Discard full response.

2. **Brand-level pricing power** — Call with `ranking_dimensions=make`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `top_n=20`.
   → **Extract only**: make, price_over_msrp_percentage per brand. Discard full response.

3. Present with ticker-level aggregation:
   - **OEM Pricing Power Ranking** (by ticker):
     - Ticker | Makes | Avg % Over/Under MSRP | # Models Above MSRP | # Models Below | Signal
   - **Signal:** BULLISH if OEM's average is above MSRP (pricing power intact); BEARISH if below (incentive-dependent); trend direction matters most

4. Investment narrative: "TM and BMWYY are the only tickers with positive MSRP parity across their lineup — BULLISH for margins. STLA has the deepest average discount at -5.2% — BEARISH for per-unit gross profit. F crossed from above-MSRP to below on 3 models this month — margin compression signal."

5. For prior-period comparison, show trend and flag models that flipped from premium to discount territory — these are inflection points.

## Output

Present: investment signal headline with tickers, ranked data tables with sample sizes and ticker-level aggregation, BULLISH/BEARISH/NEUTRAL/CAUTION signals per finding, and portfolio implications (overweight/underweight recommendations). Cite data source and period.

## Important Notes

- **US-only:** Requires `get_sold_summary` for sold data.
- Always map brands to tickers. An analyst evaluating market trends is making stock-level decisions.
- Depreciation trends are LEADING indicators — they precede incentive changes, production adjustments, and earnings impacts by 1-2 quarters.
- The MSRP parity tracker is the purest signal of OEM pricing power — a shift from above-MSRP to below is a significant inflection point for the ticker.
- For comprehensive market intelligence, this skill combines well with the `market-momentum-report` for the broadest sector view.
