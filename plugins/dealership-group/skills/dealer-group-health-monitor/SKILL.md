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

Load the `marketcheck-profile.md` project memory file. If missing, ask for dealer group or ticker. Extract: `group_name`, `is_publicly_traded`, `ticker`, `country`. US-only (UK → stop). Confirm profile.

## User Context

Dealer group executive or equity analyst benchmarking publicly traded dealer groups (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA) on operational health and investment signals.

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

→ **Extract only**: target group's sold_count, average_sale_price, average_days_on_market. Discard full response.

### Step 3 — Prior month comparison

Repeat Step 2 for prior month.
→ **Extract only**: same fields as Step 2 for prior month. Discard full response.
Calculate:
- **Volume MoM %** = (current - prior) / prior x 100
- **ASP MoM %** = price change
- **DOM MoM change** = days change
- **Efficiency Score** = sold_count / average_days_on_market (higher = better capital efficiency)

### Step 4 — Active inventory health

Call `mcp__marketcheck__search_active_cars` with:
- `dealer_group`: the group name
- `car_type`: `used`
- `stats`: `price,dom`
- `rows`: 0

→ **Extract only**: total count, avg price (from stats), avg DOM (from stats). Discard full response. Repeat with `car_type=new`.

Calculate:
- **Days Supply (used)** = active used inventory / monthly used sold x 30
- **Days Supply (new)** = active new inventory / monthly new sold x 30
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

→ **Extract only**: per body_type/make — sold_count, average_sale_price, average_days_on_market. Discard full response.

## Output

```
DEALER GROUP HEALTH — [Group Name] ([Ticker])
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Period: [Current Month] vs [Prior Month]

OPERATIONAL KPIs
Metric                  | Current    | Prior Mo   | MoM Change | Signal
------------------------|------------|------------|------------|--------
Volume (units sold)     | XX,XXX     | XX,XXX     | +X.X%      | BULLISH/BEARISH
Avg Sale Price          | $XX,XXX    | $XX,XXX    | +X.X%      | signal
Avg Days on Market      | XX days    | XX days    | +X days    | signal
Efficiency Score        | XXX        | XXX        | +X.X%      | signal
(vol / DOM)             |            |            |            |

INVENTORY HEALTH
                    | Active Count | Days Supply | Trend       | Signal
--------------------|-------------|-------------|-------------|--------
Used Inventory      | XX,XXX      | XX days     | Building/Drawing | signal
New Inventory       | XX,XXX      | XX days     | Building/Drawing | signal

PEER COMPARISON (Top 8 Public Dealer Groups)
Rank | Group            | Ticker | Volume  | ASP     | DOM  | Efficiency | Signal
-----|------------------|--------|---------|---------|------|------------|--------
  1  | [Group]          | XX     | XX,XXX  | $XX,XXX | XX   | XXX        | —
  2  | [Group]          | XX     | XX,XXX  | $XX,XXX | XX   | XXX        | —
  ...
★ = [Target Group]

[If segment data available:]
TOP SEGMENTS (by volume)
Segment   | Volume  | % of Total | ASP       | DOM
----------|---------|------------|-----------|------
SUV       | XX,XXX  | XX%        | $XX,XXX   | XX
Pickup    | XX,XXX  | XX%        | $XX,XXX   | XX
Sedan     | XX,XXX  | XX%        | $XX,XXX   | XX

TOP BRANDS SOLD
Make      | Volume  | % of Total | ASP       | DOM
----------|---------|------------|-----------|------
Toyota    | XX,XXX  | XX%        | $XX,XXX   | XX
Ford      | XX,XXX  | XX%        | $XX,XXX   | XX

INVESTMENT THESIS SIGNAL: [BULLISH / BEARISH / MIXED / NEUTRAL]

Positive:
- [e.g., "Volume up 4.2% MoM outpacing industry growth of 1.8%"]
- [e.g., "DOM improvement of 3 days signals better inventory management"]

Negative:
- [e.g., "Days supply building to 52 — may require price reductions"]

Watchpoints:
- [e.g., "Used car ASP declining while volume rises — margin compression risk"]
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

## Workflow: Peer Group Comparison

Use when the user asks "compare AutoNation vs Lithia" or "rank the top dealer groups."

1. Pull all 8 publicly traded groups from `get_sold_summary` rankings
2. Rank on: Volume, ASP, DOM, Efficiency Score
3. Calculate a composite rank (average of individual ranks)
4. Present side-by-side comparison table
5. Identify which group is gaining/losing relative position

## Important Notes

- **US-only:** All data from `get_sold_summary` requires US market.
- The `dealership_group_name` field in MarketCheck may not exactly match the stock ticker name — use fuzzy matching if needed.
- Volume from MarketCheck represents listings activity, not necessarily closed transactions. Use as a proxy for retail velocity.
- DOM is a leading indicator of margin pressure — rising DOM precedes price cuts which precede margin compression in quarterly earnings.
- Efficiency Score (volume / DOM) is the single best proxy for operational health — it captures both demand (volume) and execution (speed).
