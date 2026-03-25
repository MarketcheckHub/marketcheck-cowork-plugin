---
name: market-share-analyzer
description: >
  Competitive positioning for investment analysis. Triggers: "market share",
  "who is winning in SUVs", "competitor analysis", "EV adoption rate",
  "dealer group ranking", "segment share breakdown", "brand performance comparison",
  "competitive positioning", "quarterly share change", "OEM share signal",
  "which brands are gaining share", "top dealer groups by volume",
  competitive intelligence and OEM benchmarking
  framed as investment analysis for equity research.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Share Analyzer — Competitive Positioning for Investment Analysis

Convert MarketCheck sold transaction data into real-time market share analytics for investment decisions. Track brand share, segment conquest patterns, EV penetration curves, and competitive positioning — all mapped to stock tickers with BULLISH / BEARISH / NEUTRAL / CAUTION signals.

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for geographic scope and focus. US-only. Confirm profile.

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

## User Context

Financial analyst or sector strategist needing competitive positioning data for stock-level investment decisions. Market share changes are leading indicators of revenue trajectory. Every output maps brands to tickers with investment signals.

## Workflow: Brand Market Share (Ticker-Level View)

Calculate market share by make, aggregate by ticker, and compare against a prior period.

1. Call `mcp__marketcheck__get_sold_summary` for the **current period**:
   - `date_from` / `date_to`: target month first-to-last day
   - `state`: user's state filter (omit for national)
   - `inventory_type`: as specified (or omit for both)
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   → **Extract only**: per make — `sold_count`, total `sold_count`. Discard full response.

2. Repeat for the **prior period** with identical filters but adjusted dates.
   → **Extract only**: per make — `sold_count`, total `sold_count`. Discard full response.

3. Calculate for each make, then aggregate by ticker:
   - **Current Share %** = Make Sold Count / Total Sold Count × 100
   - **Prior Share %** = same for prior period
   - **Share Change (bps)** = (Current Share % - Prior Share %) × 100
   - **Volume Change %** = (Current Sold - Prior Sold) / Prior Sold × 100

4. Present as a ranked table at the TICKER level:
   - Columns: Rank, Ticker, Makes, Current Sold, Current Share %, Prior Share %, Share Change (bps), Volume Change %, Signal
   - Signal: BULLISH if gaining > +30 bps AND volume up; BEARISH if losing > -30 bps AND volume down; CAUTION if share gaining but volume down; NEUTRAL if within ±30 bps

5. Investment summary: "The top share gainers this period were [Ticker1] (+XX bps), [Ticker2] (+XX bps). The biggest losers were [Ticker3] (-XX bps). For tracked tickers: [Ticker] moved from #X to #Y with [+/-N] bps — [BULLISH/BEARISH] for revenue trajectory."

## Workflow: Segment Conquest Analysis (Investment Positioning)

Determine which OEM tickers are winning within specific vehicle segments.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `state`: user's state filter (omit for national)
   - `body_type`: target segment (e.g. `SUV`)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `15`
   → **Extract only**: per make/model — `sold_count`. Discard full response.

2. Repeat for comparison period.
   → **Extract only**: per make/model — `sold_count`. Discard full response.

3. For each segment, calculate and map to tickers:
   - **Segment leader** and their ticker
   - **Tracked tickers' rank** within the segment
   - **Gap to leader** in bps
   - **Signal per ticker:** GAINING / LOSING / STABLE within segment

4. Investment insight: "In the SUV segment, TM gained 120 bps through RAV4 and Highlander. F lost share as Explorer volume declined. STLA SUVs (Jeep) saw the steepest share loss at -85 bps — BEARISH for STLA's North American revenue mix."

## Workflow: EV Market Share Tracking (Ticker View)

Monitor EV share by brand with investment signals.

1. Call `mcp__marketcheck__get_sold_summary` for **EV sales**:
   - `date_from` / `date_to`: target period
   - `state`: user's state filter (omit for national)
   - `fuel_type_category`: `EV`
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `15`
   → **Extract only**: per make/model — `sold_count`; plus total EV `sold_count`. Discard full response.

2. Repeat for total market (no fuel_type_category) and prior periods.
   → **Extract only**: per make/model — `sold_count`. Discard full response.

3. Calculate and map to tickers:
   - **EV Penetration Rate** with trend — sector-level adoption signal
   - **Brand EV Share** — who is winning the EV race (TSLA vs legacy)
   - **EV % of Each OEM's Total Sales** — transition progress by ticker
   - **Signal:** For TSLA: share loss rate and absolute volume. For legacy OEMs: transition pace vs peers.

4. Investment implications: "TSLA's EV share dropped from XX% to XX% as HYMTF and GM gained. However, total EV market grew XX%, so TSLA absolute volume is still up. For legacy OEMs: F at 4.2% EV penetration vs GM at 6.1% — GM has stronger transition momentum."

## Workflow: Dealer Group Market Share (Retail Stock Signal)

Rank publicly traded dealer groups by market share.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `ranking_dimensions`: `dealership_group_name`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   → **Extract only**: per group — `sold_count`. Discard full response.

2. Same filters but `ranking_measure`: `average_days_on_market`, `ranking_order`: `asc`. Also pull `average_sale_price`.
   → **Extract only**: per group — `average_days_on_market`, `average_sale_price`. Discard full response.

3. Build a **Dealer Group Stock Signal** table:
   - Columns: Rank, Group, Ticker, Volume, Share %, MoM Change, ASP, DOM, Efficiency Score
   - Map to tickers: AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA
   - Signal per group based on volume trend and efficiency

4. Investment summary: "AN leads in volume but LAD has the best efficiency score. KMX and CVNA are gaining share in used-only segment — different business model dynamics."

## Output

Present: competitive headline with tickers and share change in bps, ranked data tables with ticker mapping, comparison period trends, and investment implications by ticker (beneficiaries, at-risk, earnings impact).

## Important Notes

- **US-only:** Requires `get_sold_summary`.
- 100 bps of national market share translates to approximately 15,000-17,000 annual units — always contextualize share changes in volume terms.
- A 50+ bps decline sustained over 2 quarters signals a structural issue for the OEM ticker.
- Always aggregate makes to the ticker level. An analyst evaluating GM needs Chevrolet + GMC + Buick + Cadillac combined, not individual brand views.
- For EV share analysis, contextualize TSLA's share loss against total EV market growth — TSLA can lose share while growing volume if the market expands faster.
