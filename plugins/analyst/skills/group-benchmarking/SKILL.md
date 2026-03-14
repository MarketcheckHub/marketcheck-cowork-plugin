---
name: group-benchmarking
description: >
  This skill should be used when the user asks to "compare dealer groups",
  "best performing dealer stock", "benchmark dealer group stocks",
  "rank dealer groups", "which dealer stock is best", "dealer group comparison",
  "dealer stock performance ranking", "peer comparison dealer groups",
  "AN vs LAD", "AutoNation vs Lithia", or needs to compare operational
  metrics across publicly traded dealer groups for relative value
  investment analysis.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Group Benchmarking — Peer Comparison of Publicly Traded Dealer Groups

## User Profile (Required)

Load `~/.claude/marketcheck/analyst-profile.json` if exists. Extract: `tracked_tickers` (filter to dealer group: AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA), `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for tickers to compare. US-only. Confirm profile.

## Built-in Ticker → Dealer Group Mapping

```
AN    → AutoNation
LAD   → Lithia Motors
PAG   → Penske Automotive Group
SAH   → Sonic Automotive
GPI   → Group 1 Automotive
ABG   → Asbury Automotive Group
KMX   → CarMax
CVNA  → Carvana
```

## User Context

Financial analyst or portfolio manager performing relative value analysis across publicly traded dealer group stocks. Goal: identify strongest operational fundamentals for long/short decisions, overweight/underweight calls, and earnings estimates.

## Workflow: Full Peer Benchmarking

### Step 1 — Collect KPIs for all 8 public dealer groups

Call `mcp__marketcheck__get_sold_summary` with:
- `ranking_dimensions`: `dealership_group_name`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 20
- `date_from` / `date_to`: current month

Also pull:
- `ranking_measure`: `average_days_on_market` (ranked `asc`)
- `ranking_measure`: `average_sale_price` (ranked `desc`)

Repeat all calls for prior month.
→ **Extract only**: `dealership_group_name`, `sold_count`, `average_sale_price`, `average_days_on_market` per group per period. Discard full response.

From results, extract data for all 8 publicly traded groups.

### Step 2 — Calculate per-group metrics

For each group:
- **Volume** and MoM change %
- **ASP** and MoM change %
- **DOM** and MoM change (days)
- **Efficiency Score** = sold_count / avg_dom (higher = better capital efficiency)
- **Efficiency MoM change %**

### Step 3 — Active inventory health

For each group, call `mcp__marketcheck__search_active_cars` with:
- `dealer_group`: the group name
- `car_type`: `used`, then `new`
- `stats`: `price,dom`
- `rows`: 0
→ **Extract only**: `num_found`, price and dom stats per car_type per group. Discard full response.

Calculate:
- **Days Supply (used)** = active used / monthly used sold × 30
- **Days Supply (new)** = active new / monthly new sold × 30

### Step 4 — Rank groups on each KPI

Create rankings (1 = best):
1. **Volume Rank** (highest volume = rank 1)
2. **Volume Growth Rank** (highest MoM % = rank 1)
3. **Efficiency Rank** (highest efficiency score = rank 1)
4. **DOM Rank** (lowest DOM = rank 1)
5. **Days Supply Rank** (lowest days supply = rank 1)
6. **ASP Trend Rank** (strongest ASP growth = rank 1)
7. **Composite Rank** = average of all individual ranks

### Step 5 — Identify investment signals

For each group:
- **BULLISH:** Composite rank top 3, improving on 3+ metrics, volume growth > industry average
- **NEUTRAL:** Mid-pack composite rank, stable metrics
- **CAUTION:** Composite rank bottom 3 but with some positive trends
- **BEARISH:** Composite rank bottom 2, deteriorating on 3+ metrics

### Step 6 — Relative value insights

Identify:
- **Best momentum:** Which group improved most in composite rank vs prior period?
- **Best value play:** Strongest operational metrics but may be undervalued
- **Deteriorating fundamentals:** Which group is declining fastest?
- **Pair trade opportunity:** Groups with diverging operational trajectories

## Output

Present: composite performance rankings table (all 8 groups with signals), individual KPI rankings, KPI deep dive (leader/laggard gaps), investment thesis per ticker, and relative value opportunities (best momentum, pair trade signal, earnings risk).

## Signal Logic

| Metric | BULLISH | NEUTRAL | CAUTION | BEARISH |
|--------|---------|---------|---------|---------|
| Volume MoM | > +3% | -1% to +3% | -3% to -1% | < -3% |
| ASP MoM | > +1% | -1% to +1% | -3% to -1% | < -3% |
| DOM Change | < -2 days | -2 to +2 | +2 to +5 | > +5 days |
| Days Supply (used) | < 35 | 35-55 | 55-75 | > 75 |
| Days Supply (new) | < 50 | 50-80 | 80-100 | > 100 |
| Efficiency MoM | > +5% | -2% to +5% | -5% to -2% | < -5% |

## Important Notes

- **US-only:** All data from `get_sold_summary` requires US market.
- The `dealership_group_name` field in MarketCheck may not exactly match — use fuzzy matching if needed.
- This benchmarking covers ALL 8 publicly traded groups regardless of which are in the analyst's tracked_tickers. The full peer set is needed for relative value analysis.
- Composite rank weights all KPIs equally by default. If the user has a specific priority (e.g., "I care most about efficiency"), adjust the weighting.
- Volume from MarketCheck represents listings activity, not closed transactions. Use as a proxy for retail velocity.
- Efficiency Score (volume / DOM) is the single best proxy for operational health and capital efficiency — it's the metric most correlated with gross profit per unit.
- DOM is a leading indicator of margin pressure — rising DOM precedes price cuts which precede margin compression in quarterly earnings.
- Always frame findings in terms of upcoming quarterly earnings and relative stock positioning.
