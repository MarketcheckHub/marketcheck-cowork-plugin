---
name: dealer-match-finder
description: >
  Find dealers matching lending sweet spot. Triggers: "find dealers to call",
  "dealer prospecting", "who should I pitch", "dealer matches in [state]",
  "find dealer prospects", "who fits my lending criteria",
  "dealer outreach list", "prospecting in my territory",
  "which dealers match my programs", identifying
  dealers whose inventory profile matches the lender's lending criteria.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Dealer Match Finder — Find Dealers Matching Your Lending Sweet Spot

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: target_states, price_range_min, price_range_max, preferred_year_range, max_mileage, preferred_dealer_types, approved_makes, approved_segments, min_dealer_inventory, country, zip, radius. If missing, ask minimum fields (state + price range). **US**: `search_active_cars`, `get_sold_summary`. **UK**: `search_uk_active_cars` only (inventory matching only, no velocity data). Confirm: "Using profile: [company], [lending_type], [state]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep looking for dealers to pitch lending products to. The best prospects are dealers whose inventory closely matches what the lender can finance — right price range, right vehicle types, sufficient volume.

## Gotchas

1. **Dealer facet cap of 50.** The `dealer_id` facet returns at most 50 dealers per call. In large states, this significantly undercounts. If exactly 50 dealers are returned, note "50+ dealers match — results may be truncated. Consider narrowing by ZIP+radius for a more complete local scan."
2. **Matching units vs total units requires two API calls.** The faceted search with price/year/mileage filters gives matching unit counts, but you need a SECOND call per dealer (without filters) to get total_count for computing Fit %. Do not assume matching = total.
3. **UK profiles — no velocity data.** `get_sold_summary` is US-only. For UK, skip opportunity estimates that depend on sold velocity. Present matching unit counts and fit scores only.
4. **Dealer deduplication.** The same dealership group may operate multiple rooftops that appear as separate dealer_ids. If two dealers share the same name stem but different cities, note them as potentially related.
5. **Penetration assumption of 20% is conservative.** For new dealer relationships, 10-15% is more realistic in year one. For established relationships, 25-35% is achievable. Label penetration assumptions clearly and note that estimates assume a mature relationship.

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

1. **Search for dealers with matching inventory** — Call `mcp__marketcheck__search_active_cars` with `state=[ST]` (or `zip=[ZIP]`+`radius=[R]`), `car_type=used`, `seller_type=dealer`, `price_range=[min]-[max]`, `year=[year_range]`, `miles_range=0-[max_mileage]`, `facets=dealer_id|0|50|2`, `stats=price`, `rows=0`. If `approved_makes` is set, add `make=[comma-separated]`. If `preferred_dealer_types` is not "both", add `dealer_type=[type]`.
   → **Extract only**: dealer_ids from facets with their matching unit counts, total num_found. Discard full response.
   - If exactly 50 dealers returned in facet, add truncation warning to output.

2. **Get total inventory per dealer** — For top 20 dealers by matching units (from step 1, filter: matching_units >= `min_dealer_inventory` or default 20), call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `facets=make|0|20|1,body_type|0|10|1`, `stats=price,dom`, `rows=0`.
   → **Extract only per dealer**: seller_name (from any listing metadata), city, state, total_count (num_found), avg_price and avg_dom from stats, make distribution and body_type distribution from facets. Discard full response.

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

## Output Template

```
── Dealer Match Finder: [State/ZIP] ── [Date] ──────────────

SEARCH CRITERIA
Price: $[min]-$[max] | Year: [min]-[max] | Max Miles: [max]
Makes: [list or "all"] | Dealer Type: [pref or "all"] | Min Lot: [min]

DEALER PROSPECT TABLE
Rank | Dealer Name      | City   | Total | In Criteria | Fit%  | Avg $   | DOM | Top Makes          | Score | Class
-----|------------------|--------|-------|-------------|-------|---------|-----|---------------------|-------|--------
1    | [Name]           | [City] |  XXX  |     XX      |  XX%  | $XX,XXX | XX  | Toyota, Honda, Ford |  XX   | STRONG
2    | [Name]           | [City] |  XXX  |     XX      |  XX%  | $XX,XXX | XX  | BMW, Mercedes       |  XX   | STRONG
...

MATCH CLASSIFICATION
STRONG (70-100):   [X] dealers — [Y] total lendable units
MODERATE (50-69):  [X] dealers — [Y] total lendable units
LIGHT (30-49):     [X] dealers — [Y] total lendable units

OPPORTUNITY ESTIMATE (20% penetration, 1.5% spread)
Total lendable units:                [Z]
Monthly origination estimate:        [N] units / $X,XXX,XXX
Annual revenue estimate:             $XXX,XXX

SUMMARY
[X] strong matches, [Y] moderate in [state].
Total lendable units: [Z]. Estimated monthly origination: [N] units.

TOP 5 RECOMMENDED CALLS
1. [Dealer] in [City] — [XX]% fit, [XX] qualifying units. Talking point: "[specific]"
2. ...

Source: MarketCheck inventory data, [Date].
```

## Output
Dealer prospect table: Rank, Dealer Name, City, Total Units, Units in Criteria, Fit %, Avg Price, Avg DOM, Top Makes, Match Score, Classification (STRONG/MODERATE/LIGHT). Summary: "[X] strong matches, [Y] moderate in [state]. Total lendable units: [Z]. Estimated monthly origination opportunity: [N] units." Top 5 recommended calls with talking points.

## Self-Check (before presenting to user)

1. **Match Score components add to 100?** Volume (0-30) + Fit (0-40) + Price Alignment (0-30) = 100 max. Verify each dealer's score equals the sum of its three components.
2. **Fit % uses matching_units / total_units?** Not matching_units / some-other-denominator. The denominator must come from the unfiltered per-dealer search (step 2), not the filtered market-wide search (step 1).
3. **Classification thresholds are consistent?** STRONG (70-100), MODERATE (50-69), LIGHT (30-49), below 30 excluded. Verify no dealer is misclassified.
4. **Min lot size filter applied?** Dealers with total_count below `min_dealer_inventory` should not appear. Small dealers are not worth the sales effort.
5. **Origination estimate labels the penetration assumption?** Always state "assumes 20% penetration" (or whatever rate was used). Do not present origination estimates as facts.
6. **Talking points per dealer are specific?** Each recommendation should reference that dealer's inventory data (fit %, top makes, DOM) — not generic pitches. A talking point for a Toyota-heavy dealer should differ from one for a luxury dealer.
