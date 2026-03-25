---
name: dealer-intelligence-brief
description: >
  Dealer deep-dive for sales call prep. Triggers: "tell me about [dealer]",
  "dealer brief", "prep for dealer meeting", "dealer intelligence",
  "profile this dealer for a sales call", "what does [dealer] sell",
  "dealer inventory analysis", "meeting prep for [dealer]",
  deep-dive on a specific dealer to prepare for a
  sales call with inventory profile, lending fit, and talking points.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Dealer Intelligence Brief — Prep for a Dealer Sales Call

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: price_range_min, price_range_max, preferred_year_range, max_mileage, approved_makes, approved_segments, ltv_max_pct, lending_type, country, zip, radius. If missing, ask minimum fields. **US**: `search_active_cars`, `predict_price_with_comparables`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (inventory profile only, no LTV analysis). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep preparing for a dealer meeting. Need to know: what does this dealer sell, how much of it can we finance, what are their pain points (aging, floor plan burden), and what should I say in the meeting.

## Gotchas

1. **Dealer identification ambiguity.** Users may provide a dealer name, domain, or ID. Prefer `dealer_id` for precision. If only a name is given, use `search_active_cars` with `seller_name` to find the dealer_id first, but warn the user if multiple dealers match. If a domain is given, use `source=[domain]`.
2. **LTV spot-check is an estimate, not an appraisal.** `predict_price_with_comparables` returns a statistical prediction based on comparables, not a certified valuation. Always label LTV calculations as "estimated" and note the comp count backing each prediction. If a prediction returns fewer than 5 comps, flag it as "low confidence."
3. **Floor plan rate varies widely.** The $35/day default is an industry midpoint. Actual rates range from $25-$50/day depending on the lender and dealer tier. If the profile includes a `floor_plan_rate`, use that. Otherwise label as "(estimated at $35/day industry average)."
4. **UK profiles — no LTV analysis.** `predict_price_with_comparables` is US-only. For UK dealers, skip steps 4 and 6 (LTV calculations) and note "LTV analysis unavailable for UK market."
5. **New vs used inventory separation.** Always scope to `car_type=used` unless the user explicitly asks about new. Mixing new and used produces misleading DOM and pricing metrics.

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

## Output Template

```
── Dealer Intelligence Brief ── [Month Year] ───────────────

DEALER CARD
Name:           [Dealer Name]
Location:       [City], [State] [ZIP]
Type:           [Franchise/Independent]
Total Used Units: [XX]
Avg Price:      $XX,XXX
Avg DOM:        XX days
Lending Fit:    XX% ([X] of [Y] units qualify)

INVENTORY BREAKDOWN
Make Mix:       [Make1] XX%, [Make2] XX%, [Make3] XX%, Other XX%
Body Types:     [SUV] XX%, [Sedan] XX%, [Truck] XX%, Other XX%
Year Range:     [oldest]-[newest], median [year]
Price Range:    $X,XXX - $XX,XXX, median $XX,XXX

LENDING FIT ANALYSIS
Matching Units: [X] of [Y] (XX%)
Avg Listed Price (matching): $XX,XXX
Estimated Avg LTV:          XX.X% (based on [N]-unit sample)
LTV Distribution:
  Under 100% (under-advanced): X units
  100-110% (standard):         X units
  110-[max]% (elevated):       X units
  Over [max]% (exceeds limit): X units

AGING ANALYSIS
Units > 60 DOM:   [X] ([XX]% of lot)
Units > 90 DOM:   [X]
Units > 120 DOM:  [X]
Est. Floor Plan Burden: $X,XXX/month (aged units, est. $35/day)

TALKING POINTS
1. "[talking point with specific numbers]"
2. "[talking point with specific numbers]"
3. "[talking point with specific numbers]"
4. "[talking point with specific numbers]"
5. "[talking point with specific numbers]"

RECOMMENDED PRODUCTS
- [Product]: [reason based on data]
- [Product]: [reason based on data]

LOCAL MARKET CONTEXT
Top sellers in [state] last month: [Model1], [Model2], [Model3]

Source: MarketCheck market data, [Month Year].
```

## Output
Dealer brief card: Name, City, State, Total Units, Avg Price, Avg DOM, Lending Fit %. Inventory breakdown: make mix, body type mix, year mix. Lending fit analysis: matching units, avg LTV, LTV distribution. Aging analysis: aged units count, floor plan burden estimate. Top 5 talking points for the meeting. Recommended lending products. Local market context (what's selling).

## Self-Check (before presenting to user)

1. **Lending Fit % math is correct?** matching_units / total_units x 100. Verify the numerator comes from the filtered search (step 3) and denominator from the unfiltered search (step 1).
2. **LTV calculations use listed_price / predicted_price?** LTV = listed_price / predicted_price x 100. Values over 100% mean the dealer is listing above market. Verify this direction — do not invert the ratio.
3. **Floor plan burden uses correct units?** Burden = aged_count x excess_DOM x daily_rate. "Excess DOM" = avg_aged_dom - aging_threshold (e.g., 45 days). Do not use total DOM — only the portion beyond the threshold.
4. **Talking points are specific to THIS dealer?** Each point must reference a specific number from the analysis. Generic statements like "we have great rates" add no value.
5. **Product recommendations match the data?** If recommending floor plan, verify the dealer has significant aging. If recommending subprime, verify the dealer has older/cheaper inventory. Do not recommend products that contradict the inventory profile.
6. **Dealer name and location are correct?** Cross-check that the dealer_id returned inventory that matches the expected dealer name and city. Mismatched dealer_ids are a common source of embarrassing errors in sales calls.
