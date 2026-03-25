---
name: territory-dashboard
description: >
  Coverage vs opportunity across target states. Triggers: "territory overview",
  "market penetration", "where should I focus", "state coverage dashboard",
  "territory report", "which states have the most opportunity",
  "compare my markets", "territory prioritization",
  coverage vs opportunity across target states.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Territory Dashboard — Coverage vs Opportunity Across States

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: target_states, price_range_min, price_range_max, preferred_year_range, max_mileage, approved_makes, preferred_dealer_types, min_dealer_inventory, country, zip, radius. If missing, ask for target states + lending criteria. **US**: `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (dealer counts only, no velocity). Confirm: "Using profile: [company], [lending_type], states: [list]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep or regional manager assessing where to focus their time. Need to know: which states have the most untapped dealer opportunities, how many units fit lending criteria per state, and where the velocity is highest.

## Gotchas

1. **US-only for velocity data.** `get_sold_summary` is US-only. For UK profiles, territory dashboard can only show active supply counts per region — no sold velocity, no monthly volume, no days supply. Clearly label UK output as "supply-only" and omit opportunity scores that depend on velocity.
2. **State-level facet limits.** The `dealer_id` facet in `search_active_cars` returns at most 50 dealers per call. If a state has hundreds of dealers in-criteria, the facet undercounts. Use the `num_found` total from stats as the true eligible-unit count, not the sum of facet buckets.
3. **Date range alignment.** Always use complete calendar months for sold data. Partial-month comparisons produce misleading volume trends. If today is March 14, "prior month" = Feb 1-28, NOT "last 30 days."
4. **Advance rate assumptions.** The 80% advance rate used in market sizing is an industry average. If the profile includes a specific `advance_rate`, use that instead. Never present the default as a fact — always label it "(assumed 80% advance rate)."
5. **Opportunity score is relative, not absolute.** Scores are ranked within the rep's territory only. A state scoring 90 in a weak territory may be worse than a state scoring 60 in a strong one. Always show raw metrics alongside scores.

## Workflow: Full Territory Dashboard

**Multi-agent approach:** Use the `territory-scanner` agent for cross-state scanning.

Use the Agent tool to spawn the `lender-sales:territory-scanner` agent with this prompt:

> Scan territory for lending opportunities. States=[target_states]. Price range=[min]-[max], year=[year_range], max_mileage=[max_mileage], approved_makes=[makes or "all"], dealer_type=[pref or omit], min_dealer_inventory=[min]. Date range: [first of prior month] to [last of prior month].

The agent returns per-state: eligible_dealers, eligible_units, monthly_volume, avg_dom, median_price, opportunity_score.

**If the territory-scanner agent is unavailable**, run the scan manually per state:

For EACH state in target_states:

a. **Active supply** — Call `mcp__marketcheck__search_active_cars` with `state=[ST]`, `car_type=used`, `seller_type=dealer`, `price_range=[min]-[max]`, `year=[year_range]`, `miles_range=0-[max_mileage]`, `facets=dealer_id|0|50|2`, `stats=price,dom`, `rows=0`. If `approved_makes` set, add `make=[comma-separated]`. If `preferred_dealer_types` set, add `dealer_type`.
   → **Extract only**: num_found (eligible_units), dealer count from facets, avg_price, median_price, avg_dom from stats. Discard full response.

b. **Sold velocity** — Call `mcp__marketcheck__get_sold_summary` with `state=[ST]`, `inventory_type=Used`, `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=5`, `date_from=[first of prior month]`, `date_to=[last of prior month]`. If `approved_makes` set, add `make=[comma-separated]`.
   → **Extract only**: total sold_count (monthly_volume), average_days_to_sell. Discard full response.

c. **Calculate opportunity_score** per state:
   - volume_norm = monthly_volume / max(monthly_volume across states) x 40
   - dealer_norm = eligible_dealers / max(eligible_dealers across states) x 30
   - turn_norm = (1 / avg_dom) / max(1/avg_dom across states) x 30
   - opportunity_score = volume_norm + dealer_norm + turn_norm (0-100 scale)

After receiving results (from agent or manual scan):

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

When user says "compare Texas vs California" — pull both states using the manual scan steps above (or from cached territory-scanner results). Present side-by-side:

```
── State Comparison ─────────────────────────────────────────
                        Texas           California
Eligible Dealers:       XX              XX
Eligible Units:         X,XXX           X,XXX
Monthly Volume:         X,XXX           X,XXX
Avg DOM:                XX days         XX days
Median Price:           $XX,XXX         $XX,XXX
Opportunity Score:      XX/100          XX/100
Priority:               FOCUS           MAINTAIN
Days Supply:            XX              XX
```

Highlight the winning state per metric with a `*` marker.

## Output Template

```
── Territory Dashboard: [Company] ── [Month Year] ──────────

State  | Dealers | Units | Mo Vol | Avg DOM | Med Price | Score | Priority
-------|---------|-------|--------|---------|-----------|-------|----------
TX     |   XX    | X,XXX | X,XXX  |  XX     | $XX,XXX   |  XX   | FOCUS
FL     |   XX    | X,XXX | X,XXX  |  XX     | $XX,XXX   |  XX   | FOCUS
CA     |   XX    | X,XXX | X,XXX  |  XX     | $XX,XXX   |  XX   | MAINTAIN
...
TOTAL  |  XXX    | XX,XXX| XX,XXX |  XX     | $XX,XXX   |  --   | --

── Market Sizing (assumed 80% advance rate, 20% penetration) ──
Total Lendable Portfolio Value:    $XXX,XXX,XXX
Monthly Origination Potential:     XXX units / $X,XXX,XXX
Annual Revenue Estimate (1.5% spread): $X,XXX,XXX

── Priority Allocation ──
FOCUS (50% of time):          [state list]
MAINTAIN (30%):               [state list]
OPPORTUNISTIC (20%):          [state list]

── Top 3 Actions ──
1. [Specific state + dealer targeting recommendation]
2. [Specific state + dealer targeting recommendation]
3. [Specific state + dealer targeting recommendation]

Source: MarketCheck market data, [Month Year]
```

## Output
Territory map table: State, Eligible Dealers, Eligible Units, Monthly Volume, Avg DOM, Median Price, Opportunity Score, Priority (FOCUS/MAINTAIN/OPPORTUNISTIC). Territory totals row. Market sizing: total portfolio value, monthly originations, annual revenue. Priority recommendations: "Spend 50% of time in [top states], 30% in [middle], 20% in [bottom]." Top 3 actions: specific state + dealer targeting recommendations.

## Self-Check (before presenting to user)

1. **All target states accounted for?** Every state in the profile's `target_states` list must appear in the output table. If a state returned zero results, show it with zeros and a note ("no matching inventory found") rather than omitting it.
2. **Opportunity scores sum correctly?** Verify that volume_norm + dealer_norm + turn_norm = opportunity_score for each state. Scores must be 0-100.
3. **Tertile classification is correct?** With N states, top third = FOCUS, middle third = MAINTAIN, bottom third = OPPORTUNISTIC. With fewer than 3 states, assign based on absolute score (70+ FOCUS, 40-69 MAINTAIN, <40 OPPORTUNISTIC).
4. **Market sizing math is consistent?** Total portfolio = units x avg_price x advance_rate. Monthly originations = units x (30/avg_dom) x penetration. Annual revenue = monthly_orig x avg_loan x spread x 12. Cross-check that annual revenue is plausible (not billions for a single rep).
5. **Date ranges are labeled?** Output must state the exact date range used for sold data (e.g., "February 2026") so the rep knows the data freshness.
6. **No UK velocity data presented?** If country=UK, confirm that monthly volume, opportunity scores, and market sizing sections are omitted or clearly marked as unavailable.
