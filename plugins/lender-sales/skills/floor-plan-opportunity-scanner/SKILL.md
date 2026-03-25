---
name: floor-plan-opportunity-scanner
description: >
  Find dealers needing floor plan help. Triggers: "floor plan prospects",
  "dealers with aging inventory", "who needs floor plan financing",
  "floor plan opportunities", "dealers burning floor plan",
  "aged inventory dealers", "high DOM dealers",
  "who is paying too much for floor plan",
  finding dealers with significant aging inventory
  that could benefit from competitive floor plan terms.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Floor Plan Opportunity Scanner — Find Dealers Needing Floor Plan Help

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: target_states, preferred_dealer_types, min_dealer_inventory, country, zip, radius. If missing, ask for state. **US**: `search_active_cars`. **UK**: `search_uk_active_cars` only (DOM data available, full workflow works). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep specializing in floor plan financing, looking for dealers under floor plan pressure — high DOM inventory, many aged units, significant daily burn. These dealers are most receptive to competitive floor plan offers.

## Gotchas

1. **DOM reflects listing age, not floor plan age.** A vehicle's DOM in MarketCheck measures days since first listed online, not days since the dealer purchased it. Actual floor plan exposure may be longer (dealer held it before listing) or shorter (dealer relisted it). Use DOM as a proxy, but note the limitation.
2. **$35/day is a mid-market estimate.** Floor plan daily rates range from $25/day (prime dealer, prime lender) to $50+/day (subprime dealer, captive lender). If the profile includes `floor_plan_rate`, use it. Otherwise clearly label "(estimated at $35/day industry average)."
3. **New inventory has different floor plan economics.** New cars on franchise lots may be floored by the OEM captive at lower rates with longer free-carry periods. Always filter to `car_type=used` unless the user explicitly asks about new.
4. **Franchise vs independent floor plan dynamics differ.** Franchise dealers often have captive floor plan relationships that are hard to displace. Independent dealers are more receptive to competitive floor plan offers. Consider noting dealer_type in recommendations.
5. **High DOM is not always bad.** Specialty dealers (exotics, classics, lifted trucks) intentionally hold inventory longer. A 90-DOM exotic car dealer is not a floor plan prospect in the same way a 90-DOM mainstream used car dealer is. Look at the make/body_type distribution before classifying.

| Field | Source | Default |
|-------|--------|---------|
| Target state/ZIP | Profile or user input | — |
| Min lot size | Profile | 20 |
| Dealer type pref | Profile | both |

## Workflow: Find High-DOM Dealers

1. **Scan market for aging inventory concentration** — Call `mcp__marketcheck__search_active_cars` with `state=[ST]` (or `zip=[ZIP]`+`radius=[R]`), `car_type=used`, `seller_type=dealer`, `sort_by=dom`, `sort_order=desc`, `facets=dealer_id|0|50|2`, `stats=dom`, `rows=0`. If `preferred_dealer_types` is set and not "both", add `dealer_type=[type]`.
   → **Extract only**: dealer_ids from facets (with unit counts per dealer), avg_dom from stats, total num_found. Discard full response.
   - Note: the facet sorts dealers by total matching units, NOT by avg DOM. This is intentional — we want high-volume dealers first, then filter for aging.

2. **Profile top aging dealers** — For the top 20 dealers by unit count (filter: total_count >= `min_dealer_inventory`, default 20), call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `stats=price,dom`, `facets=make|0|10|1,body_type|0|5|1`, `rows=0`.
   → **Extract only per dealer**: seller_name, city, total_count (num_found), avg_price and avg_dom from stats, make distribution from facets. Discard full response.
   - Check make distribution: if dominated by exotic/luxury/classic makes, flag as "specialty dealer — may not be a floor plan prospect."

3. **Count aged units per dealer** — For each profiled dealer, call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `dom_range=60-999`, `rows=0`.
   → **Extract only**: aged_count (num_found). Discard full response.
   - Also run with `dom_range=90-999` and `dom_range=120-999` for tiered aging breakdown.

4. **Calculate floor plan metrics per dealer**:
   - **Aged %** = aged_count / total_count × 100
   - **Estimated Floor Plan Burn** = total_count × avg_dom × $35/day (industry standard rate)
   - **Monthly Burn** = floor_plan_burn / (avg_dom / 30)
   - **Aged Unit Burn** = aged_count × (avg_aged_dom_estimate) × $35/day
   - **Savings Pitch** = "If we reduce your floor plan rate by $5/day across [total] units, you save $[savings]/month"
   - **Priority Score** = (aged_pct × 40) + (total_count_normalized × 30) + (avg_dom_percentile × 30)

5. **Classify prospects**:
   - Priority Score 70+: **HIGH PRIORITY** — Significant aging, large lot, likely paying high floor plan costs
   - Score 50-69: **MEDIUM PRIORITY** — Moderate aging, worth a pitch
   - Score < 50: **LOW PRIORITY** — Manageable aging

## Workflow: Quick Floor Plan Burden Check for One Dealer

1. Call `mcp__marketcheck__search_active_cars` with `dealer_id`, `car_type=used`, `stats=price,dom`, `rows=0`.
2. Call same with `dom_range=60-999`, `rows=0` for aged count.
3. Calculate burden and pitch.

## Output Template

```
── Floor Plan Opportunity Scanner: [State/ZIP] ── [Date] ───

MARKET AGING OVERVIEW
Total dealers scanned:        [X]
Dealers with significant aging: [Y] (60+ DOM aged units > 20% of lot)
Market avg DOM:               XX days

FLOOR PLAN PROSPECT TABLE
Rank | Dealer Name      | City   | Type | Total | 60+d | 90+d | 120+d | Aged% | Avg DOM | Mo Burn   | Score | Priority
-----|------------------|--------|------|-------|------|------|-------|-------|---------|-----------|-------|--------
1    | [Name]           | [City] | I    |  XX   |  XX  |  XX  |  XX   |  XX%  |  XX     | $XX,XXX   |  XX   | HIGH
2    | [Name]           | [City] | F    |  XX   |  XX  |  XX  |  XX   |  XX%  |  XX     | $XX,XXX   |  XX   | HIGH
...

PRIORITY BREAKDOWN
HIGH PRIORITY (70+):   [X] dealers — $XX,XXX combined monthly burn
MEDIUM PRIORITY (50-69): [X] dealers — $XX,XXX combined monthly burn
LOW PRIORITY (<50):    [X] dealers

SUMMARY
[X] high-priority floor plan prospects with combined $[Y]/month
in estimated floor plan burden.

TOP 5 OUTREACH RECOMMENDATIONS
1. [Dealer] — "If we reduce your rate by $5/day across [X] units, you save $[Y]/month."
2. ...

Source: MarketCheck inventory data, [Date]. Floor plan rates estimated at $35/day.
```

## Output
Floor plan prospect table: Rank, Dealer Name, City, Total Units, Aged Units (60+ DOM), Aged %, Avg DOM, Est. Monthly Floor Burn, Priority Score, Savings Pitch. Summary: "[X] high-priority floor plan prospects with combined $[Y]/month in estimated floor plan burden." Top 5 outreach recommendations with specific savings pitch per dealer.

## Self-Check (before presenting to user)

1. **Aged % calculation is correct?** aged_count / total_count x 100. Verify aged_count came from the `dom_range=60-999` filtered search, not from a manual estimate.
2. **Monthly burn formula is correct?** Monthly burn = total_count x avg_dom x $35 / (avg_dom / 30). Simplifies to: total_count x 30 x $35. But for aged units specifically: aged_count x avg_aged_excess x $35/day. Make sure you are computing what you claim to compute.
3. **Savings pitch is realistic?** A $5/day reduction is typical for competitive displacement. Verify the savings = $5 x total_units x 30 days. Do not promise savings on units that would not be floored.
4. **Specialty dealers flagged?** If a dealer's make distribution is dominated by exotics, classics, or luxury brands (Porsche, Ferrari, Land Rover, etc.), flag as "specialty — verify floor plan appetite before calling."
5. **Tiered aging breakdown present?** Show 60+, 90+, and 120+ counts separately. A dealer with 30 units at 61 DOM is very different from one with 30 units at 121 DOM.
6. **Min lot size filter applied?** Dealers below `min_dealer_inventory` (default 20) should not appear in results. Small lots are not worth the sales effort for floor plan.
