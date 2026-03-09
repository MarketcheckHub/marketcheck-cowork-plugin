---
name: dealer-intelligence-brief
description: >
  This skill should be used when the user asks to "tell me about [dealer]",
  "dealer brief", "prep for dealer meeting", "dealer intelligence",
  "profile this dealer for a sales call", "what does [dealer] sell",
  "dealer inventory analysis", "meeting prep for [dealer]",
  or needs a deep-dive on a specific dealer to prepare for a
  sales call with inventory profile, lending fit, and talking points.
version: 0.1.0
---

# Dealer Intelligence Brief — Prep for a Dealer Sales Call

## Profile
Load `~/.claude/marketcheck/lender-sales-profile.json` if exists. Extract: price_range_min, price_range_max, preferred_year_range, max_mileage, approved_makes, approved_segments, ltv_max_pct, lending_type, country, zip, radius. If missing, ask minimum fields. **US**: `search_active_cars`, `predict_price_with_comparables`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (inventory profile only, no LTV analysis). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep preparing for a dealer meeting. Need to know: what does this dealer sell, how much of it can we finance, what are their pain points (aging, floor plan burden), and what should I say in the meeting.

## Workflow: Full Dealer Brief

1. **Get full inventory profile** — Call `mcp__marketcheck__search_active_cars` with `dealer_id` (or `source` for domain), `car_type=used`, `facets=make|0|20|1,body_type|0|10|1,year|0|10|1`, `stats=price,dom,miles`, `rows=0`.
   → **Extract only**: total_count, avg_price, median_price, avg_dom, avg_miles, make distribution, body_type distribution, year distribution. Discard full response.

2. **Get aged inventory** — Call `mcp__marketcheck__search_active_cars` with same dealer, `sort_by=dom`, `sort_order=desc`, `rows=15`.
   → **Extract only**: per vehicle — vin, year, make, model, trim, price, miles, dom. Discard full response.

3. **Overlay lending criteria** — Call `mcp__marketcheck__search_active_cars` with same dealer, `price_range=[min]-[max]`, `year=[year_range]`, `miles_range=0-[max_mileage]`, `rows=0`, `stats=price`.
   → **Extract only**: matching_count, avg_price of matching units. Discard full response.

4. **LTV spot-check** — For the top 5 matching units by price (representative sample), call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip` (dealer's zip), `dealer_type` matching dealer's type.
   → **Extract only**: predicted_price per VIN. Calculate estimated LTV = listed_price / predicted_price × 100. Discard full response.

5. **Local market context** — Call `mcp__marketcheck__get_sold_summary` with `state` (dealer's state), `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=10`, prior month dates.
   → **Extract only**: top models by volume. Discard full response.

6. **Calculate dealer brief metrics**:
   - **Lending Fit %** = matching_units / total_units × 100
   - **Avg LTV** = average of spot-check LTVs. Flag units over ltv_max_pct.
   - **Floor Plan Burden Estimate**:
     - Aged units (DOM > 45) count
     - Estimated burden = aged_units × $35/day × (avg_aged_dom - 45)
   - **Aging Pressure**:
     - Units > 60 DOM, > 90 DOM, > 120 DOM
     - % of lot over 60 DOM

7. **Generate talking points**:
   - "You have [X] units in our lending sweet spot ($[min]-$[max], [year range])"
   - "Your average price of $[avg] aligns well with our programs"
   - If aging present: "Your [Y] units over 60 days cost roughly $[Z]/month in floor plan. We can help with competitive terms."
   - If lending_type is floor_plan: "We can floor [X] of your [total] units at [rate]"
   - If lending_type is retail: "We can finance [X] units for your customers with advance rates up to [ltv]%"
   - "The top sellers in your market are [models] — we have strong programs for those"

8. **Suggest products**:
   - High aging + high inventory → Floor plan financing
   - High fit % + moderate DOM → Retail lending / indirect program
   - Subprime inventory (older, higher miles) → Subprime programs
   - EV inventory → EV-specific lending programs

## Output
Dealer brief card: Name, City, State, Total Units, Avg Price, Avg DOM, Lending Fit %. Inventory breakdown: make mix, body type mix, year mix. Lending fit analysis: matching units, avg LTV, LTV distribution. Aging analysis: aged units count, floor plan burden estimate. Top 5 talking points for the meeting. Recommended lending products. Local market context (what's selling).
