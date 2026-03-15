---
name: group-benchmarking
description: >
  This skill should be used when the user asks to "compare my stores",
  "best performing location", "benchmark rooftops", "rank my locations",
  "which store is best", "location comparison", "store performance ranking",
  "rooftop efficiency", or needs to compare operational metrics across
  locations within a dealer group to identify best practices and underperformers.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Group Benchmarking — Rooftop-vs-Rooftop Performance Comparison

## User Profile (Required)

Load the `marketcheck-profile.md` project memory file. If missing, prompt `/onboarding`. Requires 2+ locations. Extract: `locations[]` (dealer_id, name, zip, state, dealer_type, franchise_brands), `preferences`, `country`. Confirm: "Benchmarking **[N]** locations for **[group_name]**"

## User Context

Dealer group executive (CEO, VP Ops, Regional Director) identifying top-performing and underperforming stores to surface best practices and flag intervention targets.

## Workflow: Rooftop Benchmarking

### Step 1 — Collect KPIs per location

For each location, use the Agent tool to spawn the `dealership-group:lot-scanner` agent in facets mode:

> Fetch inventory stats for dealer_id=[dealer_id], country=[country].
> Mode: full (with DOM stats)
> Return: total_units, avg_dom, median_dom, units_under_30_dom, units_30_60_dom, units_over_60_dom, avg_price

→ **Extract only**: per location — total_units, avg_dom, median_dom, units by DOM bucket, avg_price. Discard full response.

From the scanner results, calculate per location:
- **Total units** on lot
- **Avg DOM** across all units
- **Turn rate** = 30 / avg_dom (higher = faster turns)
- **Aged %** = units_over_60 / total x 100
- **Fresh %** = units_under_30 / total x 100 (recently acquired)
- **Avg listing price**

### Step 2 — Pricing efficiency (US only)

For each US location, use the Agent tool to spawn the `dealership-group:lot-pricer` agent on a SAMPLE of units (e.g., the 10 oldest and 5 newest per location):

> Price these vehicles: [sample VINs with miles and listed_price]
> zip: [location zip], dealer_type: [location dealer_type]

→ **Extract only**: per VIN — predicted_price, listed_price, gap %. Discard full response.

From results, calculate per location:
- **Avg price-to-market %** (are they priced competitively?)
- **Overpriced %** = units with gap > +5% / sampled units x 100
- **Underpriced %** = units with gap < -5% / sampled units x 100

### Step 3 — Market context per location (US only)

For each location, call `mcp__marketcheck__get_sold_summary` with:
- `state`: location's state
- `inventory_type`: `Used`
- `ranking_measure`: `average_days_on_market`
- `date_from` / `date_to`: prior month

→ **Extract only**: local market average_days_on_market per state. Discard full response.

Calculate:
- **DOM vs Market** = location avg DOM - local market avg DOM (negative = better than market)
- **Market-adjusted score** = accounts for the fact that some markets are inherently slower

### Step 4 — Rank locations on each KPI

Create rankings (1 = best):
1. **Turn Rate Rank** (highest turn rate = rank 1)
2. **Aged % Rank** (lowest aged % = rank 1)
3. **Pricing Efficiency Rank** (closest to market = rank 1)
4. **DOM vs Market Rank** (most below market = rank 1)
5. **Composite Rank** = average of all individual ranks

### Step 5 — Identify patterns

- **Best practices:** What is the #1 ranked location doing differently? (e.g., lower avg DOM, tighter pricing, better mix)
- **Underperformer root cause:** For the lowest-ranked location, identify the primary driver (pricing? aging? mix?)
- **Outliers:** Any location with a metric > 2 standard deviations from the group mean

## Output

```
GROUP BENCHMARKING — [Group Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[N] locations compared | Period: [Month Year]

PERFORMANCE RANKINGS (1 = best)

Location           | Units | Avg DOM | Turn Rate | Aged % | Price Eff | DOM vs Mkt | Composite
-------------------|-------|---------|-----------|--------|-----------|------------|----------
★ [Location 1]     | XXX   | XX      | X.XX      | X%     | +X.X%     | -X days    | 1
  [Location 2]     | XXX   | XX      | X.XX      | XX%    | +X.X%     | +X days    | 2
  [Location 3]     | XXX   | XX      | X.XX      | XX%    | +X.X%     | +X days    | 3
  ...
⚠ [Location N]     | XXX   | XX      | X.XX      | XX%    | +X.X%     | +X days    | N

★ = Top performer | ⚠ = Needs attention

GROUP AVERAGES
  Avg DOM: XX days | Turn Rate: X.XX | Aged %: XX% | Price-to-Market: +X.X%

KPI DEEP DIVE

Turn Rate:
  Best:  [Location] at X.XX (XX units sold per 30 days equivalent)
  Worst: [Location] at X.XX
  Gap:   X.XX (X.Xx difference — [worst] is turning XXx slower)

Aging:
  Best:  [Location] at X% aged (only X units over 60 days)
  Worst: [Location] at XX% aged (XX units — $X,XXX/day in floor plan)
  Gap:   XX percentage points

Pricing Efficiency:
  Best:  [Location] at +X.X% vs market (tight, competitive pricing)
  Worst: [Location] at +XX.X% (significantly overpriced, contributing to aging)

BEST PRACTICES (from top performer)
- [e.g., "[Location 1] prices within 3% of market on 90% of units — aggressive day-1 pricing prevents aging"]
- [e.g., "[Location 1] has only 4% aged inventory — suggests strong reconditioning-to-frontline speed"]

IMPROVEMENT OPPORTUNITIES (for bottom performers)
- [e.g., "[Location N] has 25% aged inventory costing $X,XXX/day. Immediate action: reduce prices on XX aged units by avg $X,XXX to reach market level"]
- [e.g., "[Location N-1] is priced XX% above market on average. Aligning to market could reduce avg DOM by XX days"]

RECOMMENDED ACTIONS
1. [Most impactful action with specific location, metric, and dollar impact]
2. [Second action]
3. [Third action]
```

## Important Notes

- This skill requires `dealer_id` for all locations. Locations without a dealer_id are excluded with a note.
- **US vs UK:** Full benchmarking (including pricing efficiency and market context) for US. UK locations get inventory metrics only (total, DOM, aging) without market pricing comparison.
- For groups with 10+ locations, consider grouping by state or region before ranking.
- The composite rank is a simple average — it weights all KPIs equally. If the user has a specific priority (e.g., "I care most about turn rate"), adjust the weighting.
- Sampling for pricing efficiency (Step 2) uses 15 units per location. For a more thorough analysis, suggest running `/weekly-review` on the underperforming location.
