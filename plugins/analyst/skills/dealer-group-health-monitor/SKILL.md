---
name: dealer-group-health-monitor
description: >
  This skill should be used when the user asks about "dealer group stock",
  "how is AutoNation doing", "LAD health check", "publicly traded dealer analysis",
  "dealer group efficiency", "CarMax performance", "Carvana metrics",
  "dealer group benchmarking", "retail auto stock signal", "dealer group volume",
  or needs help monitoring the operational health and investment signals
  for publicly traded dealer groups and automotive retailers.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Dealer Group Health Monitor — Investment Signals for Publicly Traded Dealer Stocks

## User Profile (Load First)

Load `~/.claude/marketcheck/analyst-profile.json` if exists. Extract: `tracked_tickers`, `tracked_states`, `country`. If missing, ask for dealer group/ticker. US-only. Confirm profile.

## User Context

Equity analyst covering automotive retail stocks (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA). Each metric framed as investment signal with BULLISH/BEARISH/NEUTRAL/CAUTION ratings tied to stock tickers.

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

## Workflow: Single Dealer Group Health Check

Use when a user asks "How is AutoNation doing?" or "LAD health check."

### Step 1 — Resolve the entity

Map ticker or name to the dealer group. Confirm: "Analyzing **[Ticker]** ([Group Name])"

### Step 2 — Volume and efficiency (current month)

Call `mcp__marketcheck__get_sold_summary` with:
- `ranking_dimensions`: `dealership_group_name`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 20
- `date_from` / `date_to`: current month
→ **Extract only**: `dealership_group_name`, `sold_count`, `average_sale_price`, `average_days_on_market` per group. Discard full response.

Find the target group in results.

### Step 3 — Prior month comparison

Repeat Step 2 for prior month. Calculate:
- **Volume MoM %** = (current - prior) / prior × 100
- **ASP MoM %** = price change
- **DOM MoM change** = days change
- **Efficiency Score** = sold_count / average_days_on_market (higher = better capital efficiency)

### Step 4 — Active inventory health

Call `mcp__marketcheck__search_active_cars` with:
- `dealer_group`: the group name
- `car_type`: `used`
- `stats`: `price,dom`
- `rows`: 0

This gives total active used inventory count, avg price, avg DOM. Repeat with `car_type=new`.
→ **Extract only**: `num_found`, price and dom stats per car_type. Discard full response.

Calculate:
- **Days Supply (used)** = active used inventory / monthly used sold × 30
- **Days Supply (new)** = active new inventory / monthly new sold × 30
- **Inventory Build/Draw:** Compare current active count to prior month's — is inventory building or drawing down?

### Step 5 — Peer comparison

From the Step 2 results (which already include top 20 dealer groups), extract the top 8 publicly traded groups. Build a peer table with: volume, ASP, DOM, efficiency score.

Rank the target group against peers on each metric.

### Step 6 — Segment mix (optional, for deeper analysis)

Call `mcp__marketcheck__get_sold_summary` with:
- `dealership_group_name`: the group
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 10

And separately:
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 15
→ **Extract only**: `body_type`/`make`, `sold_count`, `average_sale_price` per entry. Discard full response.

This shows the group's brand and segment mix -- critical for understanding revenue composition and OEM dependency.

## Output

Present: investment thesis signal headline (BULLISH/BEARISH/MIXED/NEUTRAL) with ticker, operational KPIs table (volume, ASP, DOM, efficiency), inventory health (days supply, build/draw), peer comparison ranking, and earnings preview connecting operational data to stock implications.

## Signal Logic

| Metric | BULLISH | NEUTRAL | CAUTION | BEARISH |
|--------|---------|---------|---------|---------|
| Volume MoM | > +3% | -1% to +3% | -3% to -1% | < -3% |
| ASP MoM | > +1% | -1% to +1% | -3% to -1% | < -3% |
| DOM Change | < -2 days | -2 to +2 | +2 to +5 | > +5 days |
| Days Supply (used) | < 35 | 35-55 | 55-75 | > 75 |
| Days Supply (new) | < 50 | 50-80 | 80-100 | > 100 |
| Efficiency MoM | > +5% | -2% to +5% | -5% to -2% | < -5% |

## Workflow: Peer Group Comparison

Use when the user asks "compare AutoNation vs Lithia" or "rank the top dealer groups."

1. Pull all 8 publicly traded groups from `get_sold_summary` rankings
2. Rank on: Volume, ASP, DOM, Efficiency Score
3. Calculate a composite rank (average of individual ranks)
4. Present side-by-side comparison table with tickers
5. Identify which group is gaining/losing relative position
6. Deliver a relative thesis: "LAD has the strongest efficiency score, making it the best-positioned for margin expansion. AN leads in volume but DOM is rising — watch for inventory writedowns."

## Important Notes

- **US-only:** All data from `get_sold_summary` requires US market.
- The `dealership_group_name` field in MarketCheck may not exactly match the stock ticker name — use fuzzy matching if needed.
- Volume from MarketCheck represents listings activity, not necessarily closed transactions. Use as a proxy for retail velocity.
- DOM is a leading indicator of margin pressure — rising DOM precedes price cuts which precedes margin compression in quarterly earnings.
- Efficiency Score (volume / DOM) is the single best proxy for operational health — it captures both demand (volume) and execution (speed).
- Always tie metrics back to the stock ticker and expected earnings impact. Analysts think in tickers and quarterly cadence.
