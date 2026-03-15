---
name: subprime-opportunity-finder
description: >
  This skill should be used when the user asks about "subprime dealers",
  "buy here pay here", "BHPH dealers", "older inventory dealers",
  "high mileage dealer prospects", "budget car dealers",
  "non-prime dealer prospects", "find dealers selling cheap cars",
  "who sells $5K-$15K cars", "independent dealer prospects for subprime",
  or needs to find dealers specializing in older, higher-mileage,
  lower-price vehicles that fit the subprime lending sweet spot.
version: 0.1.0
---

# Subprime Opportunity Finder — Dealers in the Subprime Lending Sweet Spot

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: target_states, price_range_min, price_range_max, preferred_year_range, max_mileage, country, zip, radius. If missing, ask for state. **US**: `search_active_cars`. **UK**: `search_uk_active_cars` (works for inventory scanning). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep from a subprime/non-prime lending company looking for independent dealers that specialize in older, higher-mileage, budget-priced vehicles. These are the natural partners for subprime lending programs.

| Field | Source | Default |
|-------|--------|---------|
| Target state/ZIP | Profile or user input | — |
| Subprime price range | Profile or use default | $3,000-$18,000 |
| Year range | Profile or use default | 2012-2020 |
| Mileage range | Default | 60,000-150,000 |

## Workflow: Find Subprime-Profile Dealers

1. **Search for subprime-segment inventory** — Call `mcp__marketcheck__search_active_cars` with `state` (or `zip`+`radius`), `price_range=3000-18000` (or user's subprime range), `year=2012-2020`, `miles_range=60000-150000`, `car_type=used`, `dealer_type=independent`, `seller_type=dealer`, `facets=dealer_id|0|50|2`, `stats=price,miles`, `rows=0`.
   → **Extract only**: dealer_ids from facets with unit counts, total matching units, avg_price, avg_miles from stats. Discard full response.

2. **Profile top subprime dealers** — For the top 15 dealers by matching unit count (minimum 10 units in range), call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `stats=price,miles,dom`, `facets=make|0|15|1,year|0|10|1`, `rows=0`.
   → **Extract only per dealer**: seller_name, city, total_count (all inventory), avg_price, avg_miles, avg_dom, make distribution, year distribution. Discard full response.

3. **Calculate subprime metrics per dealer**:
   - **Subprime Concentration** = subprime_matching_units / total_units × 100. Over 50% = dedicated subprime dealer.
   - **Avg Price** in subprime range — confirms lending sweet spot alignment
   - **Avg Year** — older = more subprime oriented
   - **Avg Mileage** — higher = more subprime oriented
   - **Turn Estimate** = based on avg_dom. Lower DOM = they move cars = more originations.
   - **Monthly Origination Est** = subprime_units × (30 / avg_dom) × penetration (30% for subprime — higher since limited financing options)
   - **Subprime Score** = (concentration × 40) + (volume × 30) + (turn_rate × 30)

4. **Classify**:
   - Score 70+: **CORE SUBPRIME** — Dedicated BHPH/subprime dealer, high volume, strong fit
   - Score 50-69: **PARTIAL SUBPRIME** — Mixed lot with significant subprime inventory
   - Score 30-49: **FRINGE** — Some qualifying units but not primary business

## Output
Subprime dealer prospect table: Rank, Dealer Name, City, Total Units, Subprime Units, Concentration %, Avg Price, Avg Miles, Avg Year, Avg DOM, Est Monthly Originations, Subprime Score, Classification. Summary: "[X] core subprime dealers with [Y] total lendable units. Estimated monthly origination opportunity: [Z] loans." Top 5 outreach recommendations.
