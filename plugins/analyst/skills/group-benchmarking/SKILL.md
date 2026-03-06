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

# Group Benchmarking — Peer Comparison of Publicly Traded Dealer Groups

## User Profile (Required)

This skill requires an analyst profile.

1. Read `~/.claude/marketcheck/analyst-profile.json`.
2. If the file **does not exist**: This skill works without a profile but benefits from one. Ask: "Which dealer group tickers do you want to compare?" Suggest running `/onboarding`.
3. If the file **exists**, extract:
   - `analyst.tracked_tickers` — filter to dealer group tickers (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA)
   - `analyst.tracked_states` — for regional context
   - `analyst.benchmark_period_months`
   - `location.country` (this skill is **US-only**)
4. Confirm: "Benchmarking publicly traded dealer groups for **[user.name]** ([user.company])"

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

The user is a **financial analyst** or **portfolio manager** performing relative value analysis across publicly traded dealer group stocks. The goal is to identify which dealer stocks have the strongest operational fundamentals (volume growth, inventory discipline, pricing efficiency) to inform long/short decisions, overweight/underweight calls, and earnings estimates.

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

```
DEALER GROUP PEER BENCHMARKING — Investment View
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All 8 Publicly Traded US Dealer Groups | Period: [Month Year]

PERFORMANCE RANKINGS (1 = best)

Ticker | Group              | Volume  | Vol MoM | Efficiency | DOM  | Days Supply | ASP MoM | Composite | Signal
-------|--------------------|---------|---------|-----------|----- |-------------|---------|-----------|--------
[#1]   | [Group]            | XX,XXX  | +X.X%   | XXX        | XX   | XX days     | +X.X%   | 1         | BULLISH
[#2]   | [Group]            | XX,XXX  | +X.X%   | XXX        | XX   | XX days     | +X.X%   | 2         | BULLISH
[#3]   | [Group]            | XX,XXX  | +X.X%   | XXX        | XX   | XX days     | -X.X%   | 3         | NEUTRAL
[#4]   | [Group]            | XX,XXX  | -X.X%   | XXX        | XX   | XX days     | +X.X%   | 4         | NEUTRAL
[#5]   | [Group]            | XX,XXX  | -X.X%   | XXX        | XX   | XX days     | -X.X%   | 5         | NEUTRAL
[#6]   | [Group]            | XX,XXX  | -X.X%   | XXX        | XX   | XX days     | -X.X%   | 6         | CAUTION
[#7]   | [Group]            | XX,XXX  | -X.X%   | XXX        | XX   | XX days     | -X.X%   | 7         | CAUTION
[#8]   | [Group]            | XX,XXX  | -X.X%   | XXX        | XX   | XX days     | -X.X%   | 8         | BEARISH

INDIVIDUAL KPI RANKINGS
                     | Volume | Vol Growth | Efficiency | DOM | Days Supply | ASP Trend
---------------------|--------|-----------|-----------|-----|-------------|----------
AN                   | 1      | 3         | 2         | 2   | 3           | 4
LAD                  | 2      | 1         | 1         | 1   | 2           | 3
PAG                  | 3      | 2         | 3         | 4   | 1           | 1
...

KPI DEEP DIVE

Volume Momentum:
  Leader:  [Ticker] at +X.X% MoM (XX,XXX units)
  Laggard: [Ticker] at -X.X% MoM (XX,XXX units)
  Gap:     XX percentage points — significant operational divergence

Inventory Discipline:
  Tightest: [Ticker] at XX days supply (lean, pricing power intact)
  Loosest:  [Ticker] at XX days supply (inventory building, potential writedown risk)

Efficiency (volume/DOM — best proxy for capital efficiency):
  Best:    [Ticker] at XXX (fast turns, high velocity)
  Worst:   [Ticker] at XXX
  Gap:     X.Xx difference — [worst] has materially lower capital efficiency

INVESTMENT THESIS BY TICKER

[Ticker 1] — [BULLISH/BEARISH/NEUTRAL]:
- [Specific data-backed thesis, e.g., "Volume growth of +4.2% outpaces industry +1.8%, DOM declining — revenue and margin expansion signal"]

[Ticker 2] — [BULLISH/BEARISH/NEUTRAL]:
- [Thesis]

...

RELATIVE VALUE OPPORTUNITIES

Best Momentum:     [Ticker] — improved from rank #X to #Y, accelerating on [metric]
Pair Trade Signal: Long [Ticker A] / Short [Ticker B] — operational divergence on [key metric]
Earnings Risk:     [Ticker] — [deteriorating metric] suggests [risk to consensus estimates]

SECTOR CONTEXT
- Industry total volume: XXX,XXX units ([+/-X.X%] MoM)
- How do the top 8 dealer groups perform vs the overall market?
- Combined dealer group share of total market: XX.X%
```

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
