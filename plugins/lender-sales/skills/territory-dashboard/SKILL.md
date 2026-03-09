---
name: territory-dashboard
description: >
  This skill should be used when the user asks for a "territory overview",
  "market penetration", "where should I focus", "state coverage dashboard",
  "territory report", "which states have the most opportunity",
  "compare my markets", "territory prioritization",
  or needs to see coverage vs opportunity across their target states.
version: 0.1.0
---

# Territory Dashboard — Coverage vs Opportunity Across States

## Profile
Load `~/.claude/marketcheck/lender-sales-profile.json` if exists. Extract: target_states, price_range_min, price_range_max, preferred_year_range, max_mileage, approved_makes, preferred_dealer_types, min_dealer_inventory, country, zip, radius. If missing, ask for target states + lending criteria. **US**: `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (dealer counts only, no velocity). Confirm: "Using profile: [company], [lending_type], states: [list]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep or regional manager assessing where to focus their time. Need to know: which states have the most untapped dealer opportunities, how many units fit lending criteria per state, and where the velocity is highest.

## Workflow: Full Territory Dashboard

**Multi-agent approach:** Use the `territory-scanner` agent for cross-state scanning.

Use the Agent tool to spawn the `lender-sales:territory-scanner` agent with this prompt:

> Scan territory for lending opportunities. States=[target_states]. Price range=[min]-[max], year=[year_range], max_mileage=[max_mileage], approved_makes=[makes or "all"], dealer_type=[pref or omit], min_dealer_inventory=[min]. Date range: [first of prior month] to [last of prior month].

The agent returns per-state: eligible_dealers, eligible_units, monthly_volume, avg_dom, median_price, opportunity_score.

After receiving results:

1. **Rank states by opportunity** — Sort by opportunity_score descending.

2. **Calculate territory totals**:
   - Total eligible dealers across all states
   - Total eligible units
   - Total monthly volume
   - Weighted avg price and DOM

3. **Market sizing**:
   - Total lendable portfolio value = total_eligible_units × avg_price × avg_advance_rate (80%)
   - Monthly origination potential = total_eligible_units × (1 / avg_dom × 30) × penetration (20%)
   - Annual revenue estimate = monthly_originations × avg_loan_amount × net_spread (1.5%) × 12

4. **Priority classification**:
   - Top tertile by opportunity_score: **FOCUS** — maximize time here
   - Middle tertile: **MAINTAIN** — regular cadence
   - Bottom tertile: **OPPORTUNISTIC** — low-effort outreach only

## Workflow: State-vs-State Comparison

When user says "compare Texas vs California" — pull both from territory-scanner, present side-by-side with key differences highlighted.

## Output
Territory map table: State, Eligible Dealers, Eligible Units, Monthly Volume, Avg DOM, Median Price, Opportunity Score, Priority (FOCUS/MAINTAIN/OPPORTUNISTIC). Territory totals row. Market sizing: total portfolio value, monthly originations, annual revenue. Priority recommendations: "Spend 50% of time in [top states], 30% in [middle], 20% in [bottom]." Top 3 actions: specific state + dealer targeting recommendations.
