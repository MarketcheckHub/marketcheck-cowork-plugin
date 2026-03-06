---
name: group-dashboard
description: >
  This skill should be used when the user asks for a "group dashboard",
  "how are my stores doing", "multi-location report", "group performance",
  "all locations overview", "store health", "group inventory status",
  "consolidated lot report", "rooftop summary", or needs a unified view
  across all locations in a multi-store dealer group.
version: 0.1.0
---

# Group Dashboard — Multi-Location Dealer Group Overview

## User Profile (Required)

Load `~/.claude/marketcheck/dealership-group-profile.json`. If missing, prompt `/onboarding`. Extract: `group_name`, `locations[]` (dealer_id, name, dealer_type, zip, state), `is_publicly_traded`, `ticker`, `country`, `preferences`. Confirm: "Loading group dashboard for **[group_name]** ([N] locations)"

## User Context

Dealer group executive needing a single-screen view of all locations' health to identify which stores need immediate attention on aging, pricing, or operational outliers.

## Workflow: Group Health Dashboard

### Step 1 — Parallel inventory scan across all locations

Use the Agent tool to spawn the `dealership-group:group-scanner` agent with this prompt:

> Scan all locations for group health dashboard.
> Locations: [JSON array of {dealer_id, name, zip, state, dealer_type} for each location]
> Country: [country]
> Mode: facets_and_aging
> Aging threshold: [preferences.dom_aging_threshold or 60]
> Return per location: total_units, aged_units (DOM > threshold), avg_dom, top_makes (facets)

The group-scanner will spawn parallel lot-scanner agents, one per location, and aggregate results.
→ **Extract only**: per location — total_units, aged_units, avg_dom, top_makes facets. Discard full response.

### Step 2 — Calculate group metrics

From the scanner results, calculate per location:
- **Total units**
- **Aged units** (DOM > threshold)
- **Aged %** = aged / total x 100
- **Avg DOM**
- **Estimated daily floor plan burn** on aged units = aged_count x preferences.floor_plan_cost_per_day
- **Health Score** (0-100): Start at 100. Deduct: -2 per % of aged inventory (e.g., 15% aged = -30), -1 per day of avg DOM above 35 (e.g., avg DOM 50 = -15). Minimum 0.

Group totals:
- **Total units across group**
- **Total aged units**
- **Group aged %**
- **Group avg DOM** (weighted by units)
- **Total daily floor plan burn**

### Step 3 — Rank locations

Rank locations by:
1. **Worst health score** (lowest score = most attention needed)
2. **Most aged units** (absolute count)
3. **Highest avg DOM**

### Step 4 — Generate top 3 actions

Based on rankings, generate the 3 most impactful actions:
- If a location has aged % > 20%: "**[Location]** has [N] aged units ([X]%) — trigger price review. Burning $[X]/day in floor plan."
- If a location has avg DOM > 50: "**[Location]** avg DOM is [X] days — review merchandising and photo quality."
- If a location has aged % < 5% AND avg DOM < 25: "**[Location]** is turning fast — consider restocking. May be under-inventoried."
- If two locations have contrasting performance: "**[Location A]** has excess [segment] while **[Location B]** is under-stocked — consider a transfer."

## Output

```
GROUP DASHBOARD — [Group Name] ([N] locations)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[If publicly traded: Ticker: [TICKER]]

LOCATION HEALTH (sorted by health score)

Location                  | Units | Aged (60+) | Aged % | Avg DOM | Floor Plan Burn | Health
--------------------------|-------|-----------|--------|---------|-----------------|-------
[Location 1]              | XXX   | XX        | XX%    | XX days | $XXX/day        | XX/100
[Location 2]              | XXX   | XX        | XX%    | XX days | $XXX/day        | XX/100
[Location 3]              | XXX   | XX        | XX%    | XX days | $XXX/day        | XX/100
...

GROUP TOTALS
  Total Units:        X,XXX across [N] locations
  Total Aged:         XXX units (XX%)
  Group Avg DOM:      XX days
  Floor Plan Burn:    $X,XXX/day ($XX,XXX/month) on aged units

TOP 3 ACTIONS (by dollar impact)
1. [Action with specific location, unit count, and dollar impact]
2. [Action]
3. [Action]
```

## Health Score Interpretation

| Score | Status | Action |
|-------|--------|--------|
| 80-100 | Healthy | Monitor, consider restocking |
| 60-79 | Watch | Review pricing on aged units |
| 40-59 | Concern | Aggressive price reductions needed |
| 0-39 | Critical | Wholesale aged units, halt acquisitions |

## Important Notes

- This skill requires `dealer_id` for each location in the profile. Locations without a `dealer_id` will be skipped with a note.
- For US locations: full lot scanning with pagination. For UK locations: same scanning but with `search_uk_active_cars`.
- The group-scanner agent handles parallel execution — each location is scanned simultaneously for speed.
- This dashboard is designed for quick scanning. For deep analysis on a specific location, use the daily/weekly/monthly briefing skills with that location selected.
- If the group has more than 10 locations, show the 5 worst and 5 best by health score, with a "Show all" option.
