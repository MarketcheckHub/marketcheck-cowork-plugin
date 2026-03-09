---
name: dealer-match-finder
description: >
  This skill should be used when the user asks to "find dealers to call",
  "dealer prospecting", "who should I pitch", "dealer matches in [state]",
  "find dealer prospects", "who fits my lending criteria",
  "dealer outreach list", "prospecting in my territory",
  "which dealers match my programs", or needs help identifying
  dealers whose inventory profile matches the lender's lending criteria.
version: 0.1.0
---

# Dealer Match Finder — Find Dealers Matching Your Lending Sweet Spot

## Profile
Load `~/.claude/marketcheck/lender-sales-profile.json` if exists. Extract: target_states, price_range_min, price_range_max, preferred_year_range, max_mileage, preferred_dealer_types, approved_makes, approved_segments, min_dealer_inventory, country, zip, radius. If missing, ask minimum fields (state + price range). **US**: `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (inventory matching only, no velocity data). Confirm: "Using profile: [company], [lending_type], [state]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep looking for dealers to pitch lending products to. The best prospects are dealers whose inventory closely matches what the lender can finance — right price range, right vehicle types, sufficient volume.

| Field | Source | Default |
|-------|--------|---------|
| Target state/ZIP | Profile or user input | — |
| Price range | Profile | $15K-$55K |
| Year range | Profile | 2019-2025 |
| Max mileage | Profile | 80,000 |
| Dealer type pref | Profile | both |
| Approved makes | Profile | all |
| Min lot size | Profile | 20 |

## Workflow: Territory-Wide Dealer Prospecting

Use this when the user says "find dealers to call in [state]" or "dealer prospects."

1. **Search for dealers with matching inventory** — Call `mcp__marketcheck__search_active_cars` with `state` (or `zip`+`radius`), `car_type=used`, `seller_type=dealer`, `price_range=[min]-[max]`, `year=[year_range]`, `miles_range=0-[max_mileage]`, `facets=dealer_id|0|50|2`, `stats=price`, `rows=0`. If approved_makes is set, add `make=[comma-separated]`. If preferred_dealer_types is not "both", add `dealer_type`.
   → **Extract only**: dealer_ids from facets with their matching unit counts. Discard full response.

2. **Get total inventory per dealer** — For top 20 dealers by matching units (from step 1), call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `facets=make|0|20|1,body_type|0|10|1`, `stats=price,dom`, `rows=0`.
   → **Extract only per dealer**: seller_name, city, state, total_count, avg_price (from stats), avg_dom, make distribution (from facets), body_type distribution. Discard full response.

3. **Calculate lending fit metrics** — For each dealer:
   - **Lending Fit %** = matching_units / total_units × 100
   - **Volume Score** (0-30) = min(30, total_units / max_lot_size_in_set × 30)
   - **Fit Score** (0-40) = lending_fit_pct / 100 × 40
   - **Price Alignment Score** (0-30) = 30 if dealer avg_price is within ±20% of lender midpoint ((min+max)/2), scaled down proportionally outside
   - **Dealer Match Score** = Volume + Fit + Price Alignment (0-100)
   - Filter: only dealers with total_count >= min_dealer_inventory

4. **Classify matches**:
   - Score 70-100: **STRONG MATCH** — High fit, right volume, sweet spot pricing
   - Score 50-69: **MODERATE MATCH** — Partial fit, worth a call
   - Score 30-49: **LIGHT MATCH** — Some units qualify, lower priority
   - Below 30: skip

5. **Estimate opportunity per dealer**:
   - Monthly origination estimate = matching_units × (1 / avg_dom × 30) × penetration_assumption (20%)
   - Revenue estimate = monthly_originations × avg_price × spread (1.5%)

## Workflow: Quick Single-State Scan

When the user says "quick scan of [state]" — run step 1 only, return top 10 dealers with matching unit counts. Skip detailed profiling.

## Output
Dealer prospect table: Rank, Dealer Name, City, Total Units, Units in Criteria, Fit %, Avg Price, Avg DOM, Top Makes, Match Score, Classification (STRONG/MODERATE/LIGHT). Summary: "[X] strong matches, [Y] moderate in [state]. Total lendable units: [Z]. Estimated monthly origination opportunity: [N] units." Top 5 recommended calls with talking points.
