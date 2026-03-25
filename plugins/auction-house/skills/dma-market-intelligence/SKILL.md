---
name: dma-market-intelligence
description: >
  Comprehensive DMA overview for auction planning. Triggers: "market overview for [state]",
  "DMA health check", "market intelligence", "what's the market like in [area]",
  "state market snapshot", "market conditions in Texas",
  "how is the [state] wholesale market", "market report",
  comprehensive view of a target DMA including supply levels,
  demand velocity, pricing trends, top sellers, and key dealer groups.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# DMA Market Intelligence — Comprehensive Market Overview for Auction Planning

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, target_dmas, vehicle_segments, country, radius. If missing, ask for target state. **US**: `get_sold_summary`, `search_active_cars`. **UK**: `search_uk_active_cars` only (limited — supply snapshot only, no demand data). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Auction house sales exec or regional director assessing a DMA for auction potential. Need to understand: Is this market worth running sales in? What segments have demand? Who are the big players?

## Gotchas

1. **`dma-scanner` agent availability** — If the `auction-house:dma-scanner` agent is not available or fails, fall back to manual calls: run `get_sold_summary` for demand and `search_active_cars` with `facets` for supply. Do not error out — always have a manual fallback path.
2. **"State" is not "DMA"** — A DMA (Designated Market Area) is a metro-centric region, but MarketCheck API filters by `state`. Large states like Texas contain multiple DMAs (Dallas, Houston, San Antonio, Austin). When the user says "Dallas DMA," use `zip` + `radius=100` instead of `state=TX` to avoid mixing Houston data into Dallas analysis.
3. **Dealer group identification is approximate** — The `facets=dealer_id|0|50|2` call returns individual dealer locations, not parent groups. Multiple dealer_ids may belong to the same group (e.g., AutoNation has dozens of locations per state). Group-level intelligence requires manual recognition of known group names in seller_name fields.
4. **Volume trend requires two periods** — Never report "MoM trend" from a single month of data. Always pull at least current month and prior month. If the user asks for quarterly trends, pull 3+ months.
5. **UK limitation** — UK profiles get supply snapshot only via `search_uk_active_cars`. No demand velocity, no sold data, no market classification. Label the report "Supply Snapshot Only — demand data unavailable for UK market."

| Field | Source | Default |
|-------|--------|---------|
| Target state | User input or profile | — |
| Vehicle segments | Profile | all |

## Workflow: Full DMA Report

**Multi-agent approach:** Use the `dma-scanner` agent for comprehensive DMA analysis. If the agent is unavailable, fall back to the manual steps below.

Use the Agent tool to spawn the `auction-house:dma-scanner` agent with this prompt:

> DMA market intelligence for state=[state]. Date range: [first of prior month] to [last of prior month]. Sections: all.

The agent returns: demand snapshot, supply health, top models, top dealer groups.

**Manual fallback** (if agent is unavailable or for quick single-section runs):

- **Demand snapshot**: Call `mcp__marketcheck__get_sold_summary` with `state=[XX]`, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=15`, `date_from=[YYYY-MM-01]`, `date_to=[YYYY-MM-DD]`. Extract: per body_type sold_count, average_sale_price, average_days_on_market.
- **Supply health**: Call `mcp__marketcheck__search_active_cars` with `state=[XX]`, `car_type=used`, `seller_type=dealer`, `facets=body_type|0|20|1`, `stats=price,dom`, `rows=0`, `price_min=1`. Extract: total active supply (num_found), per body_type counts, avg_dom, avg_price.
- **Top models**: Call `mcp__marketcheck__get_sold_summary` with `state=[XX]`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=20`, same date range. Extract: per model sold_count, average_sale_price.
- **Top dealer groups**: Call `mcp__marketcheck__search_active_cars` with `state=[XX]`, `car_type=used`, `seller_type=dealer`, `facets=dealer_id|0|30|2`, `rows=0`. Then for top 10 dealer_ids, call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `rows=1` to get seller_name and city. Extract: dealer name, city, unit count.

After receiving agent results, synthesize:

1. **Market scorecard** — Headline metrics: total monthly sold volume, avg sale price, avg DOM, days supply, volume trend (MoM).

2. **Market classification**:
   - EXPANDING: Volume > +5% MoM, days supply < 50, ASP rising
   - STABLE: Volume ±5%, days supply 50-75, ASP flat
   - CONTRACTING: Volume < -5%, days supply > 75, ASP falling
   - MIXED: Conflicting signals

3. **Auction strategy implications**:
   - EXPANDING: Increase sale frequency, more lanes, aggressive consignment sourcing
   - STABLE: Maintain current pace, focus on lane optimization
   - CONTRACTING: Reduce lanes, focus on high-demand segments only, lower reserves
   - MIXED: Segment-specific strategy

4. **Top dealer groups** — Frame as both potential consigners (they wholesale trades) AND buyers (they restock from auction). Note which groups are likely auction participants.

5. **Segment opportunity map** — Which segments to source for (high D/S) vs avoid (low D/S). Connect to lane planning.

## Workflow: Multi-DMA Comparison

Use this when the user says "compare Texas vs California" or "which of my markets is strongest."

1. Run `dma-scanner` agent for each state in parallel.
2. Compare: total volume, ASP, DOM, days supply, growth rate.
3. Rank markets by auction opportunity score = (volume × 40) + (1/days_supply × 30) + (growth_rate × 30).

## Output
Market scorecard table: metric, value, trend signal. Demand by segment with D/S ratios. Top 10 models table. Top 10 dealer groups table (flagged as potential consigners or buyers). Market classification with auction strategy. 3 actionable recommendations.

### Output Template

```
-- DMA Market Intelligence: [State] — [Month Year] --------------------------------

-- Market Scorecard ----------------------------------------------------------------
| Metric              | Value        | Trend     | Signal      |
|---------------------|------------- |-----------|-------------|
| Monthly Sold Volume |       12,450 |    +6% MoM | EXPANDING  |
| Avg Sale Price      |      $27,800 |    +2% MoM | RISING     |
| Avg Days on Market  |           38 |    -3 days | IMPROVING  |
| Days Supply         |           42 |           | HEALTHY     |
| Active Listings     |       17,200 |           |             |

Classification: [EXPANDING / STABLE / CONTRACTING / MIXED]

-- Demand by Segment ---------------------------------------------------------------
| Segment  | Sold/Mo | Active Supply | D/S Ratio | Signal |
|----------|---------|---------------|-----------|--------|
| SUV      |   4,200 |         5,100 |      0.82 | WARM   |
| Pickup   |   3,100 |         3,400 |      0.91 | WARM   |
| Sedan    |   2,800 |         4,500 |      0.62 | COOL   |
| ...      |     ... |           ... |       ... | ...    |

-- Top 10 Models by Volume ---------------------------------------------------------
| Rank | Make/Model       | Sold/Mo | Avg Price  | Avg DOM |
|------|------------------|---------|------------|---------|
|    1 | Toyota RAV4      |     820 |    $29,400 |      28 |
| ...  | ...              |     ... |        ... |     ... |

-- Top 10 Dealer Groups ------------------------------------------------------------
| Rank | Dealer Group     | City        | Active Units | Likely Role        |
|------|------------------|-------------|------------- |--------------------|
|    1 | AutoNation       | Dallas      |          420 | BUYER + CONSIGNER  |
| ...  | ...              | ...         |          ... | ...                |

-- Auction Strategy ----------------------------------------------------------------
[Strategy recommendation based on market classification]

-- Recommendations -----------------------------------------------------------------
1. [Actionable recommendation]
2. [Actionable recommendation]
3. [Actionable recommendation]
```

## Self-Check (before presenting to user)

1. **Two periods of data for trends** — MoM trend requires both current and prior month data. Never calculate a trend from a single data point. If only one month was retrieved, label trend as "N/A — single period."
2. **D/S ratios use matching geographies** — Demand (sold) and supply (active) must be from the same state/zip+radius. Mixing state-level sold with zip-level supply produces invalid D/S ratios.
3. **Market classification matches criteria** — EXPANDING requires volume > +5% MoM AND days supply < 50 AND ASP rising. Verify all three conditions are met before labeling. If conditions conflict, classify as MIXED.
4. **Days supply formula is correct** — Days supply = (active_listings / monthly_sold) x 30. Verify the number is reasonable (typically 30-90 for used vehicles). Values below 15 or above 120 suggest a data issue.
5. **Dealer groups are labeled correctly** — Dealers with high DOM (> market avg) and large lots are likely CONSIGNERS. Dealers with low DOM and mix gaps are likely BUYERS. Dealers with both signals are BUYER + CONSIGNER.
6. **No UK demand data presented** — If country is UK, confirm the output clearly states "Supply Snapshot Only" and no sold volume, D/S ratios, or market classification are shown.
