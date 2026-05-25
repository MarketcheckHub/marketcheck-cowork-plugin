---
name: group-benchmarking
description: >
  Peer comparison of publicly traded dealer groups. Triggers: "compare dealer groups",
  "best performing dealer stock", "benchmark dealer group stocks",
  "rank dealer groups", "which dealer stock is best", "dealer group comparison",
  "dealer stock performance ranking", "peer comparison dealer groups",
  "AN vs LAD", "AutoNation vs Lithia", comparing operational
  metrics across publicly traded dealer groups for relative value
  investment analysis.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026 (`days_in_month` = 28), "three months ago" = December 2025. The `days_in_month` value is used by Step 3's Days Supply formula. Never use training-data dates.

> **`get_sold_summary` parameter safety:**
> - **Always set `inventory_type`** explicitly (`New` or `Used`) — omitting it defaults to `New`, returning zero results for used-vehicle queries
> - **Always set `limit: 5000`** — the default (1000) silently truncates when (months × states × ranking combos) exceeds 1000 rows
> - **For volume totals**, use `ranking_dimensions: dealership_group_name` (or the single relevant dimension) — never use the default `make,model,body_type` which creates ~150K rows for national 3-month queries
> - **Use separate calls** for totals vs breakdowns — don't combine in one call

# Group Benchmarking — Peer Comparison of Publicly Traded Dealer Groups

## User Profile (Required)

Load the `marketcheck-profile.md` project memory file if it exists. Extract from the analyst-shaped profile: `analyst.tracked_tickers` (filter to dealer-group tickers AN/LAD/PAG/SAH/GPI/ABG/KMX/CVNA) and `location.country`. Halt if `location.country != "US"` — this skill is US-only. If the profile is absent or unparseable, proceed with the full 8-ticker cohort.

## Built-in Ticker → Dealer Group Mapping

Use these canonical strings as the `dealership_group_name` (Step 1) and `mc_dealership_group_name` (Step 3) parameter values.

```
AN    → AutoNation Inc.
LAD   → Lithia Motors Inc.
PAG   → Penske Automotive Group Inc.
SAH   → Sonic Automotive Inc.
GPI   → Group 1 Automotive Inc.
ABG   → Asbury Automotive Group       # no trailing period
KMX   → Carmax                        # single token in API (not "CarMax")
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
- `top_n`: 50 (ensures all 8 public groups land in the response even in lower-volume months; flag any missing group as N/A downstream)
- `date_from` / `date_to`: current month
- `inventory_type`: `Used` (KMX and CVNA are Used-only; for franchise groups AN/LAD/PAG/SAH/GPI/ABG, ALSO run a separate `New` call — required for the New-side metrics in Steps 2-4)
- `limit`: `5000`

Also pull:
- `ranking_measure`: `average_days_on_market` (ranked `asc`) — keep `limit: 5000` and `inventory_type: Used`
- `ranking_measure`: `average_sale_price` (ranked `desc`) — keep `limit: 5000` and `inventory_type: Used`

Repeat all calls for prior month (same parameters).
→ **Extract only**: `dealership_group_name`, `sold_count`, `average_sale_price`, `average_days_on_market` per group per period. Discard full response.

From results (rows are per-(group × state)), aggregate per group across state rows — sum `sold_count`; weight-average `average_sale_price` and `average_days_on_market` by `sold_count` — for all 8 publicly traded groups.

### Step 2 — Calculate per-group metrics

For each group:
- **Volume** and MoM change %
- **ASP** and MoM change %
- **DOM** and MoM change (days)
- **Efficiency Score** = sold_count / avg_dom (higher = better capital efficiency)
- **Efficiency MoM change %**

Cohort baseline (used by Step 5 verdict logic):
- **Industry mean Volume MoM %** = arithmetic mean of Volume MoM across the 8 groups (exclude any group with a null/missing Volume MoM).

### Step 3 — Active inventory health

For each group, call `mcp__marketcheck__search_active_cars` with:
- `mc_dealership_group_name`: the group name
- `car_type`: `used`, then `new`
- `stats`: `price,dom`
- `rows`: 0
→ **Extract only**: `num_found`, price and dom stats per car_type per group. Discard full response.

Calculate (using `days_in_month` from the date anchor — 28-31 per the actual calendar month):
- **Days Supply (used)** = `num_found` (used) / monthly used sold × `days_in_month`
- **Days Supply (new)** = `num_found` (new) / monthly new sold × `days_in_month`

> Days Supply pairs live active inventory (today's snapshot) with the most-recent-complete-month sold velocity — a live-vs-historical mix. If a call returns `num_found` but no `data.stats` block (rare on the syndication-routed path), render `num_found` only and skip that group's Days Supply with a brief footnote in the output.

### Step 4 — Rank groups on each KPI

Create rankings (1 = best):
1. **Volume Rank** (highest volume = rank 1)
2. **Volume Growth Rank** (highest MoM % = rank 1)
3. **Efficiency Rank** (highest efficiency score = rank 1)
4. **DOM Rank** (lowest DOM = rank 1)
5. **Days Supply (used) Rank** (lowest = rank 1)
6. **Days Supply (new) Rank** (lowest = rank 1; skip for KMX and CVNA — Used-only)
7. **ASP Trend Rank** (strongest ASP growth = rank 1)
8. **Composite Rank** = arithmetic mean of ranks 1-7 (for groups missing a rank — e.g., KMX/CVNA on Days Supply (new) — average over the ranks they do have)

Then repeat the same rankings using prior-month metrics to produce a **prior-period Composite Rank** per group, and compute **Composite Rank MoM change** per group (current rank − prior rank; a negative number means the group improved).

### Step 5 — Identify investment signals

For each group, classify each per-group metric (Volume MoM, ASP MoM, DOM Change, Days Supply (used), Days Supply (new), Efficiency MoM) into a band per the **Signal Logic** table below. Count `n_bullish` = metrics in the BULLISH band; `n_bearish` = metrics in the BEARISH band. Skip metrics with null values.

Apply in order (first match wins — no group falls into more than one band):
- **BEARISH:** Composite rank 7 or 8 AND `n_bearish` ≥ 3
- **CAUTION:** Composite rank ≥ 6 AND `n_bearish` ≥ 1 (and not already BEARISH)
- **BULLISH:** Composite rank 1-3 AND `n_bullish` ≥ 3 AND Volume MoM > industry mean Volume MoM (from Step 2)
- **NEUTRAL:** otherwise

### Step 6 — Relative value insights

Identify:
- **Best momentum:** Group with the largest improvement (most negative **Composite Rank MoM change** from Step 4)
- **Best value play:** Strongest operational metrics but may be undervalued
- **Deteriorating fundamentals:** Which group is declining fastest?
- **Pair trade opportunity:** Groups with diverging operational trajectories

## Output

Present: composite performance rankings table (all 8 groups with signals), individual KPI rankings, KPI deep dive (leader/laggard gaps), investment thesis per ticker, and relative value opportunities (best momentum, pair trade signal, earnings risk).

## Signal Logic

| Metric | BULLISH | NEUTRAL | CAUTION | BEARISH |
|--------|---------|---------|---------|---------|
| Volume MoM | x > +3% | -1% ≤ x ≤ +3% | -3% ≤ x < -1% | x < -3% |
| ASP MoM | x > +1% | -1% ≤ x ≤ +1% | -3% ≤ x < -1% | x < -3% |
| DOM Change | x < -2 days | -2 ≤ x ≤ +2 | +2 < x ≤ +5 | x > +5 days |
| Days Supply (used) | x < 35 | 35 ≤ x ≤ 55 | 55 < x ≤ 75 | x > 75 |
| Days Supply (new) | x < 50 | 50 ≤ x ≤ 80 | 80 < x ≤ 100 | x > 100 |
| Efficiency MoM | x > +5% | -2% ≤ x ≤ +5% | -5% ≤ x < -2% | x < -5% |

> Boundary rule: NEUTRAL is closed on both sides (`≤`); adjacent bands are open on the side that touches NEUTRAL (strict `<` or `>`). This eliminates the "value falls into two bands at the boundary" ambiguity.

## Important Notes

- **US-only:** All data from `get_sold_summary` requires US market.
- **Canonical-name fidelity:** The `dealership_group_name` (Step 1) and `mc_dealership_group_name` (Step 3) parameters require the exact canonical strings from the Built-in Ticker → Dealer Group Mapping above. Quirks: `Carmax` is a single token (not `CarMax`); `Asbury Automotive Group` has no trailing period; the other six end in `Inc.`.
- This benchmarking covers ALL 8 publicly traded groups regardless of which are in the analyst's `analyst.tracked_tickers`. The full peer set is needed for relative value analysis.
- Composite rank weights all KPIs equally by default. If the user has a specific priority (e.g., "I care most about efficiency"), adjust the weighting.
- Volume from MarketCheck represents listings activity, not closed transactions. Use as a proxy for retail velocity.
- Efficiency Score (volume / DOM) is the single best proxy for operational health and capital efficiency — it's the metric most correlated with gross profit per unit.
- DOM is a leading indicator of margin pressure — rising DOM precedes price cuts which precede margin compression in quarterly earnings.
- Always frame findings in terms of upcoming quarterly earnings and relative stock positioning.
