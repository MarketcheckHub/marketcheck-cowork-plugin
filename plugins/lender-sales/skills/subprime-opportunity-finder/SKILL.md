---
name: subprime-opportunity-finder
description: >
  Dealers in the subprime lending sweet spot. Triggers: "subprime dealers",
  "buy here pay here", "BHPH dealers", "older inventory dealers",
  "high mileage dealer prospects", "budget car dealers",
  "non-prime dealer prospects", "find dealers selling cheap cars",
  "who sells $5K-$15K cars", "independent dealer prospects for subprime",
  finding dealers specializing in older, higher-mileage,
  lower-price vehicles that fit the subprime lending sweet spot.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Subprime Opportunity Finder — Dealers in the Subprime Lending Sweet Spot

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: target_states, price_range_min, price_range_max, preferred_year_range, max_mileage, country, zip, radius. If missing, ask for state. **US**: `search_active_cars`. **UK**: `search_uk_active_cars` (works for inventory scanning). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep from a subprime/non-prime lending company looking for independent dealers that specialize in older, higher-mileage, budget-priced vehicles. These are the natural partners for subprime lending programs.

## Gotchas

1. **Independent dealer bias.** Subprime inventory concentrates at independent dealers, but some franchise dealers have separate "value lot" operations. If user asks, run a second scan without `dealer_type=independent` to catch franchise dealers with subprime-profile inventory.
2. **Price floor matters.** Vehicles under $3,000 are often parts cars, salvage, or non-retail inventory. The default floor of $3,000 exists for a reason — do not lower it unless the user explicitly asks. These units are not lendable.
3. **BHPH dealers may not appear.** Buy-Here-Pay-Here dealers often do not list on major aggregators. The scan will find dealers who LIST subprime-profile vehicles online, which skews toward dealers seeking retail financing partners (exactly the right audience), but the total addressable market is larger.
4. **Mileage range is critical for risk.** Vehicles over 150,000 miles are typically outside even subprime lending guidelines. The default ceiling of 150,000 miles is a hard stop for most lenders — confirm with the user if they want to go higher.
5. **Dealer facet cap of 50.** The `dealer_id` facet returns at most 50 dealers. In large metro areas, this undercounts. If the scan returns exactly 50 dealers, note "50+ dealers found — results may be truncated. Consider narrowing by ZIP+radius."

| Field | Source | Default |
|-------|--------|---------|
| Target state/ZIP | Profile or user input | — |
| Subprime price range | Profile or use default | $3,000-$18,000 |
| Year range | Profile or use default | 2012-2020 |
| Mileage range | Default | 60,000-150,000 |

## Workflow: Find Subprime-Profile Dealers

1. **Search for subprime-segment inventory** — Call `mcp__marketcheck__search_active_cars` with `state=[ST]` (or `zip=[ZIP]`+`radius=[R]`), `price_range=3000-18000` (or profile's subprime range), `year=2012-2020`, `miles_range=60000-150000`, `car_type=used`, `dealer_type=independent`, `seller_type=dealer`, `facets=dealer_id|0|50|2`, `stats=price,miles`, `rows=0`.
   → **Extract only**: dealer_ids from facets with unit counts, total matching units (num_found), avg_price, avg_miles from stats. Discard full response.
   - If exactly 50 dealers returned in facet, note truncation warning.

2. **Profile top subprime dealers** — For the top 15 dealers by matching unit count (minimum 10 units in range), call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `stats=price,miles,dom`, `facets=make|0|15|1,year|0|10|1`, `rows=0`.
   → **Extract only per dealer**: seller_name, city, total_count (num_found for all inventory), avg_price, avg_miles, avg_dom from stats, make distribution and year distribution from facets. Discard full response.

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

## Output Template

```
── Subprime Opportunity Finder: [State/ZIP] ── [Date] ──────

MARKET SUMMARY
Total subprime-profile units found: [X]
Dealers with 10+ qualifying units:  [Y]
Avg price in range: $XX,XXX | Avg miles: XX,XXX | Avg year: XXXX

SUBPRIME DEALER PROSPECTS
Rank | Dealer Name      | City   | Total | Sub Units | Conc% | Avg $  | Avg Mi  | DOM | Est Mo Orig | Score | Class
-----|------------------|--------|-------|-----------|-------|--------|---------|-----|-------------|-------|------
1    | [Name]           | [City] |  XX   |    XX     |  XX%  | $X,XXX | XX,XXX  | XX  |    X.X      |  XX   | CORE
2    | [Name]           | [City] |  XX   |    XX     |  XX%  | $X,XXX | XX,XXX  | XX  |    X.X      |  XX   | CORE
...

CLASSIFICATIONS
CORE SUBPRIME (70+):    [X] dealers — dedicated BHPH/subprime, high volume
PARTIAL SUBPRIME (50-69): [X] dealers — mixed lot, significant subprime
FRINGE (30-49):         [X] dealers — some qualifying units

SUMMARY
[X] core subprime dealers with [Y] total lendable units.
Estimated monthly origination opportunity: [Z] loans.

TOP 5 OUTREACH RECOMMENDATIONS
1. [Dealer] in [City] — [specific reason, e.g., "XX units in sweet spot, XX% concentration, fast turn"]
2. ...

Source: MarketCheck inventory data, [Date].
```

## Output
Subprime dealer prospect table: Rank, Dealer Name, City, Total Units, Subprime Units, Concentration %, Avg Price, Avg Miles, Avg Year, Avg DOM, Est Monthly Originations, Subprime Score, Classification. Summary: "[X] core subprime dealers with [Y] total lendable units. Estimated monthly origination opportunity: [Z] loans." Top 5 outreach recommendations.

## Self-Check (before presenting to user)

1. **All dealers have minimum 10 qualifying units?** Do not include dealers below the threshold — they are not worth the sales call for subprime.
2. **Subprime Score components add to 100?** Concentration (40) + Volume (30) + Turn Rate (30) = 100 max. Verify each dealer's score is the sum of its components.
3. **Concentration % is subprime units / total units, not the reverse?** A dealer with 50 subprime units out of 80 total is 62.5% concentration. Verify direction.
4. **Monthly origination estimate uses 30% penetration?** Subprime penetration is higher than prime (30% vs 20%) because these dealers have fewer financing options. Confirm the right rate was used.
5. **Price range aligns with lending guidelines?** Verify that the search price_range matches the profile or the $3K-$18K default. Units outside the lender's actual guidelines should not be counted.
6. **No franchise dealers in results (unless explicitly requested)?** Default is `dealer_type=independent`. Confirm the filter was applied.
