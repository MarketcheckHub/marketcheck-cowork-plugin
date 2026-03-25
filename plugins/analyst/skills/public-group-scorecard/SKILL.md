---
name: public-group-scorecard
description: >
  Quintile scorecard for public dealer groups. Triggers: "dealer group scorecard",
  "quintile scorecard", "public dealer group ranking", "cohort benchmarking",
  "dealer group composite score", "quintile ranking", "scorecard report",
  "industry benchmarking for dealer groups", "how do dealer groups rank
  against the industry", scoring publicly traded dealer groups
  against the full 400+ dealer group industry cohort using the MarketCheck
  quintile methodology.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-19, then "most recent complete month" = February 2026 (2026-02-01 to 2026-02-28), "same month last year" = February 2025 (2025-02-01 to 2025-02-28), "Q1 current year" = 2026-01-01 to 2026-03-31, "Q4 prior year" = 2025-10-01 to 2025-12-31. Never use training-data dates.

# Public Dealer Group Quintile Scorecard

Score all 8 publicly traded US dealer groups on 6 operational KPIs against the full ~400 dealer group industry cohort. Each KPI is assigned a quintile (Q1-Q5) based on the group's position within the cohort distribution, then combined into a weighted composite score (1.0-5.0).

**Architecture:** This skill spawns the `cohort-benchmarking-agent` to fetch cohort data and compute quintile thresholds, then optionally fetches stock returns via WebFetch. The skill assembles the final scorecard with narrative summaries.

## User Profile (Required)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `country`. If missing, proceed with defaults (all 8 public groups, US). US-only skill.

## Built-in Coverage

```
Tickers: SAH, CVNA, PAG, KMX, GPI, LAD, AN, ABG
Groups:  Sonic Automotive, Carvana, Penske Automotive Group, CarMax,
         Group 1 Automotive, Lithia Motors, AutoNation, Asbury Automotive Group
```

## Workflow

### Step 1 — Compute Date Ranges

From `# currentDate`, compute:
- **Current month**: most recent fully completed month (date_from, date_to)
- **Prior year same month**: same month one year ago (date_from, date_to)
- **Q1 of trailing year**: Jan 1 – Mar 31 of the year that started ~12 months ago. If today is Mar 2026, Q1 = 2025-01-01 to 2025-03-31.
- **Q4 of trailing year**: Oct 1 – Dec 31 of the most recent completed Q4. If today is Mar 2026, Q4 = 2025-10-01 to 2025-12-31.

Confirm: "Generating Public Dealer Group Quintile Scorecard | Period: [current month] | YoY baseline: [prior year month] | DOM trend: Q1 [year] → Q4 [year]"

### Step 2 — Spawn Cohort Benchmarking Agent

Use the Agent tool to spawn the `marketcheck-cowork-plugin:cohort-benchmarking-agent` with this prompt:

> Benchmark these target groups against the full industry cohort:
> Target groups: AutoNation, Lithia Motors, Penske Automotive Group, Sonic Automotive, Group 1 Automotive, Asbury Automotive Group, CarMax, Carvana
>
> Date ranges:
> - current_month_from: [date] | current_month_to: [date]
> - prior_year_month_from: [date] | prior_year_month_to: [date]
> - q1_from: [date] | q1_to: [date]
> - q4_from: [date] | q4_to: [date]
>
> Return: quintile thresholds, per-group KPI values, quintile assignments, and composite scores for all 8 groups.

### Step 3 — Fetch Stock Returns (Optional)

For each ticker (SAH, CVNA, PAG, KMX, GPI, LAD, AN, ABG), attempt to fetch 12-month stock price returns using WebFetch. Try fetching from a financial data source.

If WebFetch is unavailable or fails, skip this column entirely and note: "Stock returns not available in this session." The scorecard is still valid without returns — they provide context but do not affect the composite score.

### Step 4 — Apply Special Cases

Before assembling the final output:
- **CVNA and KMX**: Verify they are assigned Q3 (neutral) on New Price/MSRP. They are pure used-vehicle retailers and should not be penalized for lacking new vehicle data.
- **GPI**: Add a footnote noting ~27% UK revenue exposure that is not captured in US-only MarketCheck data.
- **DOM data quality**: If any group shows implausible DOM readings (>300 days), flag as potential data artifact.

### Step 5 — Assemble Scorecard Output

Present the scorecard in this format:

```
MarketCheck Investment Funds Practice
PUBLIC DEALER GROUP QUINTILE SCORECARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KPI performance vs. ~[N] dealer group cohort
Trailing analysis: [period description]

Q5 Top 20% of cohort | Q4 60-80th pct | Q3 40-60th pct | Q2 20-40th pct | Q1 Bottom 20%

QUINTILE THRESHOLDS (from [N]-group cohort)
KPI              | P20      | Median   | P80      | Direction
─────────────────|──────────|──────────|──────────|──────────
Inv. Turns       | [val]    | [val]    | [val]    | Higher ↑
YoY Growth       | [val]%   | [val]%   | [val]%   | Higher ↑
New Pr/MSRP      | [val]%   | [val]%   | [val]%   | Higher ↑
L-to-S Spread    | [val]%   | [val]%   | [val]%   | Lower ↓
Avg DOM          | [val]d   | [val]d   | [val]d   | Lower ↓
DOM Trend        | [val]d   | [val]d   | [val]d   | Lower ↓

SCORECARD
Dealer           | Turns | YoY  | Pr/MSRP | L→S  | DOM  | Trend | Score    | Rank | 12-mo Return
─────────────────|───────|──────|─────────|──────|──────|───────|──────────|──────|─────────────
[ticker/name]    | Q[n]  | Q[n] | Q[n]    | Q[n] | Q[n] | Q[n]  | [x.xx]/5 | #[n] | [+/-xx.x%]
[sorted by composite score descending]
```

### Step 6 — Generate Narrative Summaries

For each of the 8 dealer groups, write a 3-5 sentence narrative summary following this structure:

**[TICKER] — [Full Name]  MC: [composite]/5  12-mo: [return or "N/A"]**

The narrative should cover:
1. **Headline positioning**: Where the group ranks and its standout KPIs (best and worst quintiles)
2. **Operational signal**: What the data says about operational health (velocity, pricing power, volume trajectory)
3. **Watch items or risks**: Any KPIs in Q1-Q2 that warrant attention, data quality notes, or factors outside MarketCheck's scope
4. **Stock-vs-fundamentals divergence** (if stock returns available): Note cases where strong operations + weak stock (or vice versa) signal potential mispricing

Sort narratives by composite score (highest first).

### Step 7 — Methodology Notes

Append at the end:

```
METHODOLOGY
- Composite = (Turns × 0.20) + (YoY × 0.20) + (NewPr × 0.15) + (LtoS × 0.15) + (DOM × 0.20) + (Trend × 0.10)
- Quintile thresholds derived from [N] active dealer groups in MarketCheck data
- CVNA and KMX assigned Q3 on New Price/MSRP (business model exclusion for pure used-only retailers)
- Inventory Turns approximated as monthly sold count / active inventory count
- Listing-to-Sale Spread = (avg active listing price - avg sold price) / avg listing price
- DOM Trend = Q4 avg DOM - Q1 avg DOM (negative = improving velocity)
- Stock returns are price returns sourced via web lookup [or "not available"]
```

## Weight Allocation

| KPI | Weight | Direction |
|-----|--------|-----------|
| Inventory Turns | 20% | Higher = better |
| YoY Unit Growth | 20% | Higher = better |
| New Price/MSRP | 15% | Higher = better |
| L-to-S Spread | 15% | Lower = better |
| Avg DOM | 20% | Lower = better |
| DOM Trend | 10% | Lower (more negative) = better |

## Important Notes

- **US-only:** All data from `get_sold_summary` requires US market.
- This scorecard covers ALL 8 publicly traded dealer groups regardless of which are in the analyst's tracked_tickers. The full peer set is needed for relative value analysis.
- The cohort benchmarking agent handles all data fetching and aggregation. This skill's role is orchestration, special-case handling, narrative generation, and formatting.
- If the cohort agent returns fewer than 200 groups, note the reduced cohort size prominently. Quintile boundaries are less reliable with small cohorts.
- Always frame the scorecard in terms of investment signal quality — this is for institutional investors, not operational managers.
