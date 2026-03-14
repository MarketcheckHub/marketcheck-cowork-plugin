---
description: Weekly territory review — coverage update + top 10 dealer prospects + floor plan opportunities + market trends across your territory.
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__get_sold_summary"]
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

Full weekly review for lender sales operations (~15 minutes).

## Step 0: Load profile

Read `~/.claude/marketcheck/lender-sales-profile.json`. Extract all fields. If no profile, suggest `/lender-sales:onboarding`.

## Step 1: Multi-agent launch (parallel)

Launch in parallel:
- **Agent A**: `lender-sales:territory-scanner` — "Scan territory. States=[target_states]. Price range=[min]-[max], year=[year_range], max_mileage=[max_mileage], approved_makes=[makes], min_dealer_inventory=[min]. Date range: [prior month]."
- **Agent B**: `lender-sales:brand-market-analyst` — "Brand volume and depreciation for state=[primary state]. Date range: [prior month]. Sections: brand_share, depreciation."

## Step 2: Top dealer prospects (inline while agents run)

For primary state: call `mcp__marketcheck__search_active_cars` with lending criteria filters + `facets=dealer_id|0|30|2`, `rows=0`.

For top 10 dealers by matching count: quick profile scan (total units, avg price, avg DOM).

## Step 3: Floor plan opportunities (inline)

Call `mcp__marketcheck__search_active_cars` with primary state, `car_type=used`, `seller_type=dealer`, `sort_by=dom`, `sort_order=desc`, `facets=dealer_id|0|15|2`, `stats=dom`, `rows=0`.

Identify top 5 dealers by avg DOM for floor plan pitch.

## Step 4: Compile weekly report

Format:
```
WEEKLY LENDER SALES REVIEW — Week of [Date]
═════════════════════════════════════════════

TERRITORY OVERVIEW
[From territory-scanner: State, Eligible Dealers, Eligible Units, Opportunity Score]
Total: [X] dealers, [Y] lendable units across [Z] states

TOP 10 DEALER PROSPECTS
[Table: Dealer, State, Matching Units, Avg Price, Avg DOM, Fit Score]

FLOOR PLAN OPPORTUNITIES
[Table: Dealer, Units, Avg DOM, Aged Units 60+, Est Monthly Burn]

BRAND & MARKET TRENDS
[From brand-market-analyst: top brands by volume, depreciation alerts]

TOP 5 ACTIONS THIS WEEK
1. [Best dealer to visit — why + talking points]
2. [Floor plan pitch target]
3. [Territory focus recommendation]
4. [Market trend to leverage]
5. [Follow-up from last week]
```
