---
name: dealer-group-health-monitor
description: >
  Investment signals for publicly traded dealer groups. Triggers: "dealer group stock",
  "how is AutoNation doing", "LAD health check", "publicly traded dealer analysis",
  "dealer group efficiency", "CarMax performance", "Carvana metrics",
  "dealer group benchmarking", "retail auto stock signal", "dealer group volume",
  monitoring operational health and investment signals
  for publicly traded dealer groups and automotive retailers.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Dealer Group Health Monitor — Investment Signals for Publicly Traded Dealer Stocks

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_states`, `country`. If missing, ask for dealer group/ticker. US-only. Confirm profile.

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

## `get_sold_summary` Parameter Best Practices

> **CRITICAL — read before calling `get_sold_summary`:**
>
> Each response row is a unique **(month × state/city × ranking_dimension_combo)** tuple. Row count = (months in range) × (geographic groups from `summary_by`) × (unique combos of `ranking_dimensions`, capped by `top_n`). The `limit` parameter caps **rows returned**, not vehicles — truncation silently drops entire vehicle groups.
>
> | `ranking_dimensions` value | Typical unique combos | ×50 states ×1 month | Fits limit=1000? |
> |---|---|---|---|
> | `dealership_group_name` | 20 (top_n) | ~1,000 | Borderline |
> | `make` | ~40 | ~2,000 | **No** |
> | `make,model,body_type` (DEFAULT) | ~1,000+ | ~50,000 | **No — catastrophic** |
>
> **Rules for every `get_sold_summary` call in this skill:**
> 1. **Always set `inventory_type` explicitly** — backend defaults to `New` when omitted; used-car groups (KMX, CVNA) return **zero results** silently
> 2. **Always set `limit: 5000`** to avoid silent truncation
> 3. **For total volume of a specific group**: use `dealership_group_name` filter + `ranking_dimensions: dealership_group_name` + `limit: 5000`
> 4. **For peer ranking**: use `ranking_dimensions: dealership_group_name` + `top_n: 20` + `limit: 5000`
> 5. **For breakdowns**: use a separate call with the needed dimension + `limit: 5000`

## Workflow: Single Dealer Group Health Check

Use when a user asks "How is AutoNation doing?" or "LAD health check."

### Step 1 — Resolve the entity

Map ticker or name to the dealer group. Confirm: "Analyzing **[Ticker]** ([Group Name])"

Determine **inventory focus**:
- **Used-only groups** (KMX, CVNA): always use `inventory_type: Used`
- **Franchise groups** (AN, LAD, PAG, SAH, GPI, ABG): query New and Used separately, or Used for primary volume

### Step 2a — Target group volume (current month)

Get the **accurate total volume** for the target group with a dedicated call:

Call `mcp__marketcheck__get_sold_summary` with:
- `dealership_group_name`: the target group name
- `inventory_type`: `Used` (for KMX, CVNA) or `Used` then `New` separately (for franchise groups)
- `ranking_dimensions`: `dealership_group_name`
- `ranking_measure`: `sold_count`
- `top_n`: 1
- `limit`: 5000
- `date_from` / `date_to`: current month

→ **Sum `sold_count` across ALL returned rows** for the true total. Each row is one (month × state) combination.
→ Also extract: `average_sale_price`, `average_days_on_market` (weighted by sold_count across states).

### Step 2b — Peer ranking (current month)

Separately, get the peer leaderboard:

Call `mcp__marketcheck__get_sold_summary` with:
- `inventory_type`: `Used`
- `ranking_dimensions`: `dealership_group_name`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 20
- `limit`: 5000
- `date_from` / `date_to`: current month

→ **Extract**: `dealership_group_name`, `sold_count`, `average_sale_price`, `average_days_on_market` per group. Discard full response.

**Note:** Use the target group's volume from Step 2a (accurate total), NOT from this peer ranking call (which may show per-state rows that need summing).

### Step 3 — Prior month comparison

Repeat Step 2a for prior month. Calculate:
- **Volume MoM %** = (current - prior) / prior × 100
- **ASP MoM %** = price change
- **DOM MoM change** = days change
- **Efficiency Score** = sold_count / average_days_on_market (higher = better capital efficiency)

### Step 4 — Active inventory health

Call `mcp__marketcheck__search_active_cars` with:
- `mc_dealership_group_name`: the group name
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

From the Step 2b results (which include top 20 dealer groups), extract the top 8 publicly traded groups. Build a peer table with: volume, ASP, DOM, efficiency score.

Rank the target group against peers on each metric.

### Step 6 — Segment mix (optional, for deeper analysis)

Call `mcp__marketcheck__get_sold_summary` with:
- `dealership_group_name`: the group
- `inventory_type`: `Used` (for KMX, CVNA) or appropriate type
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 10
- `limit`: 5000

And separately:
- `dealership_group_name`: the group
- `inventory_type`: `Used` (for KMX, CVNA) or appropriate type
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 15
- `limit`: 5000
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

1. Pull all 8 publicly traded groups from `get_sold_summary` with:
   - `inventory_type`: `Used`
   - `ranking_dimensions`: `dealership_group_name`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: 20
   - `limit`: 5000
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
