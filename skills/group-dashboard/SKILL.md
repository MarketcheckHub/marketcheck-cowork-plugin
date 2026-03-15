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

This skill requires a dealer group profile with multiple locations.

1. Read the `marketcheck-profile.md` project memory file.
2. Check `user_type`:
   - If `dealer_group`: use `dealer_group.locations[]` — this is the primary path
   - If `dealer` (single location): inform the user: "This skill is for multi-location dealer groups. You have a single-location profile. Use `/daily-briefing` or `/weekly-review` for your store."
   - If neither exists: "No profile found. Run `/onboarding` and select 'Dealer Group' to set up your locations."
3. Extract:
   - `group_name` ← `dealer_group.group_name`
   - `locations[]` ← `dealer_group.locations` (each with dealer_id, name, dealer_type, zip, state)
   - `is_publicly_traded` ← `dealer_group.is_publicly_traded`
   - `ticker` ← `dealer_group.ticker`
   - `country` ← `location.country`
   - `preferences` ← `preferences` (group-level defaults)
4. Confirm: "Loading group dashboard for **[group_name]** ([N] locations)"

## User Context

The primary user is a **dealer group executive** (VP Operations, Regional Director, GM of a multi-rooftop group) who needs a single-screen view of all locations' health. The goal is to identify which stores need attention NOW — aging inventory, pricing problems, or operational outliers.

## Workflow: Group Health Dashboard

### Step 1 — Parallel inventory scan across all locations

Use the Agent tool to spawn the `marketcheck-cowork-plugin:group-scanner` agent with this prompt:

> Scan all locations for group health dashboard.
> Locations: [JSON array of {dealer_id, name, zip, state, dealer_type} for each location]
> Country: [country]
> Mode: facets_and_aging
> Aging threshold: [preferences.dom_aging_threshold or 60]
> Return per location: total_units, aged_units (DOM > threshold), avg_dom, top_makes (facets)

The group-scanner will spawn parallel lot-scanner agents, one per location, and aggregate results.

### Step 2 — Calculate group metrics

From the scanner results, calculate per location:
- **Total units**
- **Aged units** (DOM > threshold)
- **Aged %** = aged / total × 100
- **Avg DOM**
- **Estimated daily floor plan burn** on aged units = aged_count × preferences.floor_plan_cost_per_day
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
