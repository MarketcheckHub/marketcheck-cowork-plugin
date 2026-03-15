---
description: Morning check — new dealer prospects + market price shifts affecting LTV + territory pulse across your target states.
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__get_sold_summary"]
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

Quick morning scan for lender sales operations (~5 minutes).

## Step 0: Load profile

Read the `marketcheck-profile.md` project memory file. Extract target_states, price_range, year_range, max_mileage, approved_makes, preferred_dealer_types, lending_type. If no profile, suggest `/lender-sales:onboarding`.

## Step 1: New high-inventory dealers

Call `mcp__marketcheck__search_active_cars` with primary state, `car_type=used`, `seller_type=dealer`, `price_range=[min]-[max]`, `year=[year_range]`, `miles_range=0-[max_mileage]`, `facets=dealer_id|0|20|2`, `stats=price`, `rows=0`.

Identify dealers with 30+ matching units — these are today's outreach targets.
→ **Extract only**: top 10 dealers by matching unit count.

## Step 2: Market pricing pulse

Call `mcp__marketcheck__get_sold_summary` with primary state, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `top_n=5`, prior month dates.
→ **Extract only**: top 5 segments with ASP. Note any significant shifts.

## Step 3: Floor plan pressure check

Call `mcp__marketcheck__search_active_cars` with primary state, `car_type=used`, `seller_type=dealer`, `sort_by=dom`, `sort_order=desc`, `rows=5`, `stats=dom`.
→ **Extract only**: 5 highest-DOM dealers for floor plan follow-up.

## Step 4: Deliver briefing

Format:
```
DAILY LENDER SALES BRIEFING — [Date]
═════════════════════════════════════

TOP DEALER PROSPECTS (matching your criteria)
[Table: Dealer, City, Matching Units, Avg Price]

MARKET PRICING PULSE
[Segment, Avg Price, Trend]

FLOOR PLAN LEADS (highest DOM dealers)
[Table: Dealer, Total Units, Avg DOM, Est. Monthly Burn]

TOP 3 ACTIONS TODAY
1. [Best dealer to call — why]
2. [Floor plan pitch opportunity]
3. [Market trend to mention in calls]
```
