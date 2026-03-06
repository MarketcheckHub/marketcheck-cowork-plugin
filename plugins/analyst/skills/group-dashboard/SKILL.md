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

This skill requires an analyst profile with tracked dealer group tickers.

1. Read `~/.claude/marketcheck/analyst-profile.json`.
2. If the file **does not exist**: "No profile found. Run `/onboarding` to set up your analyst profile with tracked tickers."
3. If the file **exists**, extract:
   - `analyst.tracked_tickers` — filter to dealer group tickers (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA)
   - `analyst.tracked_states`
   - `analyst.benchmark_period_months`
   - `location.country` (this skill is **US-only**)
4. If no dealer group tickers are in `tracked_tickers`: "Your profile tracks OEM tickers only. Add dealer group tickers (AN, LAD, PAG, etc.) via `/onboarding` to use the group dashboard."
5. Confirm: "Loading dealer group stock dashboard for **[user.name]** ([user.company]): tracking [dealer group tickers]"

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

The user is a **financial analyst** or **portfolio manager** monitoring a basket of publicly traded dealer group stocks. This dashboard provides a quick-scan view of operational health signals across all tracked dealer groups, enabling rapid identification of outperformers and underperformers for portfolio allocation decisions.

## Workflow: Dealer Group Stock Dashboard

### Step 1 — Pull dealer group rankings (current month)

Call `mcp__marketcheck__get_sold_summary` with:
- `ranking_dimensions`: `dealership_group_name`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 20
- `date_from` / `date_to`: current month

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

```
DEALER GROUP STOCK DASHBOARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analyst: [Name] | [Company]
Period: [Current Month] vs [Prior Month]

PORTFOLIO HEALTH (sorted by investment signal strength)

Ticker | Group              | Volume  | Vol MoM | ASP      | ASP MoM | DOM  | DOM Chg | Efficiency | Health | Signal
-------|--------------------|---------|---------|---------|---------|----- |---------|------------|--------|--------
AN     | AutoNation         | XX,XXX  | +X.X%   | $XX,XXX | +X.X%   | XX   | -X      | XXX        | XX/100 | BULLISH
LAD    | Lithia Motors      | XX,XXX  | +X.X%   | $XX,XXX | -X.X%   | XX   | +X      | XXX        | XX/100 | NEUTRAL
PAG    | Penske Automotive  | XX,XXX  | -X.X%   | $XX,XXX | -X.X%   | XX   | +X      | XXX        | XX/100 | CAUTION
...

INVENTORY HEALTH (Balance Sheet Proxy)
Ticker | Used Inventory | Used Days Supply | New Inventory | New Days Supply | Trend
-------|---------------|-----------------|--------------|----------------|------
AN     | XX,XXX        | XX days          | XX,XXX       | XX days         | Stable
LAD    | XX,XXX        | XX days          | XX,XXX       | XX days         | Building
...

PEER RANKINGS (1 = best among tracked groups)
Ticker | Volume Rank | Efficiency Rank | DOM Rank | Composite Rank
-------|------------|-----------------|----------|-----------------
AN     | 1          | 2               | 1        | 1
LAD    | 2          | 1               | 3        | 2
...

TOP 3 PORTFOLIO ACTIONS (by signal strength)
1. [Action with specific ticker and data-backed rationale]
2. [Action]
3. [Action]

EARNINGS PREVIEW
- [Ticker]: [e.g., "Volume momentum and improving DOM suggest revenue beat; watch ASP compression for margin guidance"]
- [Ticker]: [e.g., "Inventory building with rising DOM — expect cautious guidance on used car margins"]
```

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
