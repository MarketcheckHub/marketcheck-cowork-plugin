---
name: dealer-performance-intelligence
description: >
  This skill should be used when the user asks for a "performance report",
  "benchmark my group", "how do I compare to industry", "competitive analysis",
  "performance intelligence", "where am I winning", "where can I improve",
  "industry benchmarking", "dealer performance report", "how do we stack up",
  "competitive strengths", "improvement opportunities", or needs a comprehensive
  benchmarking report comparing their dealer group against the full 400+ dealer
  group industry cohort and named public peers.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Never use training-data dates.

# Dealer Performance Intelligence Report

Benchmark your dealer group's operational performance against the full ~400 US dealer group industry cohort. Identifies competitive strengths (where you outperform) and improvement opportunities (where targeted focus could drive gains), with named comparisons to the 8 publicly traded dealer groups.

**Architecture:** This skill uses a multi-agent Wave pattern. Wave 1 runs the cohort benchmarking agent and lot scanner in parallel. Wave 2 assembles the report.

## Dealer Group Profile (Load First)

Load the `marketcheck-profile.md` project memory file. If missing, prompt `/onboarding` and stop.

**Extract:** `dealer_group.group_name`, `dealer_group.locations[]` (all location details), `preferences.default_inventory_type` (default: `"used"`), `dealer_group.franchise_brands`, `dealer_type`.

**Target group identification:** The group name from the profile is used to search for this dealer in the MarketCheck cohort data. If the profile contains a `dealer_group_name_mc` field (the exact name as it appears in MarketCheck), use that. Otherwise try `group_name`.

Confirm: "Generating Performance Intelligence Report for [group name] | Locations: [N] | Brands: [list]"

## Named Public Peer Groups

These 8 publicly traded groups are always included as named comparison points:

```
SAH  → Sonic Automotive        | KMX  → CarMax
CVNA → Carvana                 | GPI  → Group 1 Automotive
PAG  → Penske Automotive Group | LAD  → Lithia Motors
AN   → AutoNation              | ABG  → Asbury Automotive Group
```

## Workflow

### Step 1 — Compute Date Ranges

From `# currentDate`, compute:
- **Current month**: most recent fully completed month
- **Prior year same month**: same month one year ago
- **Q1 of trailing year**: Jan 1 – Mar 31, ~12 months ago
- **Q4 of trailing year**: Oct 1 – Dec 31 of most recent completed Q4

### Wave 1 — Launch Simultaneously

**Agent A: `cohort-benchmarking-agent`**

Use the Agent tool to spawn the `marketcheck-cowork-plugin:cohort-benchmarking-agent` with:

> Benchmark these target groups against the full industry cohort:
> Target groups: [dealer group name from profile], AutoNation, Lithia Motors, Penske Automotive Group, Sonic Automotive, Group 1 Automotive, Asbury Automotive Group, CarMax, Carvana
>
> Date ranges:
> - current_month_from: [date] | current_month_to: [date]
> - prior_year_month_from: [date] | prior_year_month_to: [date]
> - q1_from: [date] | q1_to: [date]
> - q4_from: [date] | q4_to: [date]
>
> Return: quintile thresholds, per-group KPI values, quintile assignments, and composite scores.

**Agent B: `lot-scanner` (facets + stats mode)**

For each location in the profile, use the Agent tool to spawn `dealership-group:lot-scanner` with:

> Pull lot composition for dealer_id=[location's dealer_id], country=[location's country], mode=facets_only.
> Use rows=0 with facets=make|0|10|1,body_type|0|10|1 and stats=price,dom,miles.
> Also pull car_type=new and car_type=used separately to get new/used split.
> Return: total units, new count, used count, avg price, avg DOM (used vs new), avg mileage (used), top makes, body type mix.
> Location label: [location name].

### Wave 2 — Assemble Report (After Wave 1 Completes)

Using the cohort benchmarking results + lot scanner results:

#### Section 1: Performance Benchmarks at a Glance

Create a summary table of key KPIs with industry context:

```
KPI                    | [Group Name] | Industry P20 | Median | Industry P80 | Position
───────────────────────|──────────────|──────────────|────────|──────────────|──────────
Used Vehicle DOM       | [val] days   | [val]        | [val]  | [val]        | [quintile or %ile]
YoY Unit Volume Growth | [val]%       | [val]%       | [val]% | [val]%       | [position]
DOM Trend (Q1→Q4)      | [val] days   | [val]        | [val]  | [val]        | [position]
New Vehicle DOM        | [val] days   | --           | ~[val] | --           | [context]
New Price vs. MSRP     | [val]%       | [val]%       | [val]% | [val]%       | [position]
```

Highlight the 2-3 strongest KPIs as "Where [Group] is winning" and the 1-2 weakest as "Where there is opportunity to improve."

#### Section 2: Competitive Strengths

For each KPI where the target group outperforms the industry median (P50) or outperforms named public peers:

Write a focused paragraph covering:
1. **The metric and its value** — with specific comparison to industry median and named peers
2. **Why it matters** — operational and financial significance (floor plan costs, depreciation risk, volume trajectory)
3. **Named peer comparison** — compare directly to Carvana, CarMax, Sonic, etc. where relevant

Example structure: "Used vehicle velocity — faster than Carvana. [Group]'s used vehicles sell in an average of [X] days — faster than Carvana ([Y] days) and CarMax ([Z] days)..."

Include a horizontal bar comparison showing the target group vs. named peers for each strength metric.

#### Section 3: Improvement Opportunities

For each KPI where the target group underperforms the industry median:

Write a focused paragraph covering:
1. **The metric, its value, and the gap** — how far below median or P80
2. **What the data reveals** — specific insight from MarketCheck data (e.g., which model lines are aging, which trims are slow)
3. **Recommended action** — specific, data-driven recommendation the dealer can execute using MarketCheck weekly data

Use a callout box format for the recommended action.

#### Section 4: Inventory Mix Analysis

From the lot-scanner results:
- **New/used inventory ratio** vs. **new/used sales ratio** — identify misalignment
- **Used vehicle average mileage** vs. industry median (52,289 mi from methodology) and named peers
- **Body type distribution** — is stocking aligned with local demand?
- **New vehicle model mix** — which nameplates contribute most to new vehicle DOM?

#### Section 5: How MarketCheck Data Can Help

Brief section (2-3 bullet points) on how ongoing weekly data access enables:
- Weekly competitive position monitoring (DOM, pricing, velocity vs. peers)
- Model-level new vehicle aging identification (target the 20% of inventory driving the average up)
- Used vehicle sourcing quality benchmarking (mileage, price point vs. local competitors)

## Output Format

Present the full report with clear section headers. Use tables for benchmarks, narrative paragraphs for strengths/opportunities, and callout boxes for recommended actions.

The report should read as a standalone document that a dealer group executive or owner can review without needing additional context.

## Important Notes

- **US-only:** Cohort benchmarking uses US `get_sold_summary` data. UK locations receive inventory composition only.
- **Inventory type:** Respect `preferences.default_inventory_type` from profile. If set to "used," used vehicle KPIs are primary. If "new," emphasize new vehicle KPIs.
- The target group may not appear in the cohort data if MarketCheck uses a different group name. If not found, note this and use the lot-scanner data + active inventory stats to compute what's possible.
- **Strengths first, then opportunities.** Always lead with what the dealer does well — this is a benchmarking report, not an audit.
- Named peer comparisons should use the actual KPI values from the cohort agent, not placeholder data.
- For franchise dealers, the new vehicle price/MSRP metric is particularly relevant. For independent/used-only dealers, skip it and note the exclusion.
