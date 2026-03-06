---
name: group-dashboard
description: >
  This skill should be used when the user asks for a "dealer group dashboard",
  "how are my tracked dealer groups doing", "dealer group stock overview",
  "dealer stock dashboard", "multi-group portfolio view",
  "publicly traded dealer health", "retail auto stock dashboard",
  or needs a unified view across all tracked publicly traded
  dealer group stocks in their portfolio.
version: 0.1.0
---

# Group Dashboard — Monitoring Tracked Dealer Group Stocks

## User Profile (Required)

Load `~/.claude/marketcheck/analyst-profile.json` (required). Extract: `tracked_tickers` (filter to dealer group: AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA), `tracked_states`, `benchmark_period_months`, `country`. If missing, prompt `/onboarding`. US-only. Confirm profile.

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

Financial analyst or portfolio manager monitoring a basket of publicly traded dealer group stocks. Quick-scan view of operational health signals across tracked groups for portfolio allocation decisions.

## Workflow: Dealer Group Stock Dashboard

### Step 1 — Pull dealer group rankings (current month)

Call `mcp__marketcheck__get_sold_summary` with:
- `ranking_dimensions`: `dealership_group_name`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 20
- `date_from` / `date_to`: current month
→ **Extract only**: `dealership_group_name`, `sold_count`, `average_sale_price`, `average_days_on_market` per group. Discard full response.

From results, extract data for each tracked dealer group ticker.

### Step 2 — Pull prior month for comparison

Repeat Step 1 for prior month. Calculate per group:
- **Volume MoM %**
- **ASP MoM %**
- **DOM MoM change**
- **Efficiency Score** = sold_count / average_days_on_market

### Step 3 — Active inventory health

For each tracked dealer group, call `mcp__marketcheck__search_active_cars` with:
- `dealer_group`: the group name
- `car_type`: `used`
- `stats`: `price,dom`
- `rows`: 0

Repeat with `car_type=new`.
→ **Extract only**: `num_found`, price and dom stats per car_type per group. Discard full response.

Calculate:
- **Days Supply (used and new)**
- **Inventory Build/Draw trend**

### Step 4 — Calculate investment health scores

For each dealer group, calculate a Health Score (0-100):
- Start at 100
- Volume MoM < -3%: -15 points
- Volume MoM -1% to -3%: -5 points
- ASP MoM < -3%: -10 points
- DOM increasing > 5 days: -15 points
- DOM increasing 2-5 days: -5 points
- Days Supply (used) > 75: -15 points
- Days Supply (used) > 55: -5 points
- Days Supply (new) > 100: -10 points

### Step 5 — Rank and generate signals

Rank tracked groups by Health Score. Generate per-group investment signal:
- **BULLISH:** Health Score > 80, volume growing, DOM declining
- **NEUTRAL:** Health Score 60-80, stable metrics
- **CAUTION:** Health Score 40-60, some metrics deteriorating
- **BEARISH:** Health Score < 40, multiple metrics declining

### Step 6 — Generate top 3 portfolio actions

Based on rankings, generate actionable signals:
- If a group has the highest health score: "[Ticker] showing strongest operational momentum — consider overweight"
- If a group has declining volume AND rising DOM: "[Ticker] showing demand softening — BEARISH signal for upcoming quarterly earnings"
- If two groups have contrasting performance: "Long [Ticker A] / Short [Ticker B] on operational divergence"

## Output

Present: portfolio health table sorted by signal strength (volume, ASP, DOM, efficiency, health score), inventory health with days supply, peer rankings, top 3 portfolio actions with data-backed rationale, and earnings preview per ticker.

## Health Score Interpretation

| Score | Status | Portfolio Action |
|-------|--------|-----------------|
| 80-100 | Strong | Overweight candidate |
| 60-79 | Stable | Hold / Market weight |
| 40-59 | Watch | Underweight candidate |
| 0-39 | Weak | Potential trim / short candidate |

## Important Notes

- This skill monitors TRACKED dealer group tickers from the analyst profile — not all 8 public groups (unless all are tracked).
- For a deeper dive into a single dealer group, use the `dealer-group-health-monitor` skill.
- **US-only:** All data from `get_sold_summary` requires US market.
- The dashboard is designed for quick scanning — fund managers need signals in 30 seconds.
- Efficiency Score (volume / DOM) is the single best proxy for operational health — it captures both demand and execution.
- Always frame metrics in terms of upcoming quarterly earnings impact.
