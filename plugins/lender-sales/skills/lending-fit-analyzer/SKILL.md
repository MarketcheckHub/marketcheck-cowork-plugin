---
name: lending-fit-analyzer
description: >
  Overlay lending criteria on a dealer's lot. Triggers: "how many units can I lend on",
  "lending fit for [dealer]", "coverage analysis", "what can I finance there",
  "LTV analysis for [dealer]", "overlay my criteria on this lot",
  "which units qualify", "portfolio fit check",
  seeing exactly how much of a dealer's inventory matches
  lending criteria with LTV analysis.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Lending Fit Analyzer — Overlay Lending Criteria on a Dealer's Lot

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: price_range_min, price_range_max, preferred_year_range, max_mileage, approved_makes, approved_segments, ltv_max_pct, country, zip, radius. If missing, ask minimum fields. **US**: `search_active_cars`, `predict_price_with_comparables`. **UK**: `search_uk_active_cars` only (no LTV check — skip predict calls). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep wants to precisely quantify how much of a dealer's lot they can finance. Used to prepare proposals, justify partnerships, and identify gap opportunities.

## Gotchas

1. **LTV direction matters.** LTV = listed_price / predicted_price x 100. Values OVER 100% mean the dealer is listing above market value (higher lender risk). Values UNDER 100% mean the dealer is listing below market (lower risk, easier to advance on). Do not invert this ratio.
2. **UK profiles — no LTV analysis.** `predict_price_with_comparables` is US-only. For UK dealers, skip step 3 (LTV analysis) entirely and present coverage % only. Note "LTV analysis unavailable for UK market" in the output.
3. **Sampling bias in LTV spot-check.** The 10-unit sample (3 cheapest, 4 median, 3 most expensive) is designed to capture the range, but may miss outliers. Always note the sample size and that LTV estimates are based on a representative sample, not a full-lot appraisal.
4. **Make/segment filters are AND conditions.** If both `approved_makes` and `approved_segments` are set, the search requires BOTH to match. This can dramatically reduce the matching count. Report the filter combination used so the user understands why coverage might be low.
5. **Gap analysis should be actionable.** Saying "200 units are outside price range" is less useful than "expanding your price ceiling from $55K to $65K would add 45 units (12% coverage gain)." Always quantify what loosening one constraint would yield.

## Workflow: Full Fit Analysis

1. **Get total dealer inventory** — Call `mcp__marketcheck__search_active_cars` with `dealer_id` (or `source`), `car_type=used`, `rows=0`, `stats=price,miles,dom`, `facets=make|0|20|1,body_type|0|10|1,year|0|10|1`.
   → **Extract only**: total_count, stats (avg_price, median, min, max), facets. Discard full response.

2. **Get matching inventory** — Call `mcp__marketcheck__search_active_cars` with same dealer, `price_range=[min]-[max]`, `year=[year_range]`, `miles_range=0-[max_mileage]`, `rows=0`, `stats=price,miles`, `facets=make|0|20|1,body_type|0|10|1`.
   If `approved_makes` is set, add `make=[comma-separated]`. If `approved_segments` is set, add `body_type=[comma-separated]`.
   → **Extract only**: matching_count, stats, facets. Discard full response.

3. **LTV analysis** — For a representative sample (up to 10 units: 3 cheapest, 4 median, 3 most expensive from matching set):
   - Call `mcp__marketcheck__search_active_cars` with same dealer + criteria, `sort_by=price`, `sort_order=asc`, `rows=3` for cheap end.
   - Call `mcp__marketcheck__search_active_cars` with same dealer + criteria, `sort_by=price`, `sort_order=desc`, `rows=3` for expensive end.
   - Call `mcp__marketcheck__search_active_cars` with same dealer + criteria, `rows=4`, `start=[matching_count/2 - 2]` for middle range.
   → **Extract only per listing**: vin, listed_price, miles, year, make, model.

   For each sampled VIN, call `mcp__marketcheck__predict_price_with_comparables` with `vin=[VIN]`, `miles=[miles]`, `zip=[dealer_zip]`, `dealer_type=[dealer's type]`.
   → **Extract only per VIN**: predicted_price, comp_count. Calculate LTV = listed_price / predicted_price x 100. If comp_count < 5, flag as "low confidence." Discard full responses.

4. **Calculate fit metrics**:
   - **Coverage %** = matching_count / total_count × 100
   - **LTV Distribution** from sampled units:
     - Under 100% (under-advanced): count and %
     - 100-110% (standard): count and %
     - 110-[ltv_max]% (elevated): count and %
     - Over [ltv_max]% (exceeds limit): count and %
   - **Estimated Portfolio Value** = matching_count × avg_matching_price × estimated_advance_rate (based on avg LTV)
   - **Monthly Volume Estimate** = matching_count × (1 / avg_dom × 30) × penetration (20%)

5. **Gap analysis** — What's NOT covered and why:
   - Units outside price range: count and avg price
   - Units too old: count and avg year
   - Units too high mileage: count and avg miles
   - Units with wrong make: count (if make filter applied)
   - Suggest: "If you expanded price range to $[X], you'd pick up [Y] more units"

## Workflow: Quick Coverage Check

When user says "quick fit check" — run steps 1-2 only, return coverage % and matching count. Skip LTV sampling.

## Output Template

```
── Lending Fit Report: [Dealer Name] ── [Date] ─────────────

COVERAGE SUMMARY
Total Used Units:       [X]
Matching Units:         [Y]
Coverage:               XX.X%
Fit Classification:     [STRONG (>60%) / MODERATE (30-60%) / LIGHT (<30%)]

CRITERIA APPLIED
Price:    $[min] - $[max]
Year:     [min_year] - [max_year]
Mileage:  0 - [max_mileage]
Makes:    [list or "all"]
Segments: [list or "all"]

PRICING COMPARISON
                All Inventory    Matching Only
Avg Price:      $XX,XXX          $XX,XXX
Median Price:   $XX,XXX          $XX,XXX

LTV ANALYSIS (based on [N]-unit sample)
Under 100% (under-advanced):    X units (XX%) — low risk
100-110% (standard):            X units (XX%) — normal
110-[max]% (elevated):          X units (XX%) — monitor
Over [max]% (exceeds limit):    X units (XX%) — DECLINE

Avg Estimated LTV:              XXX.X%
LTV Range:                      XX% - XXX%

PORTFOLIO ESTIMATE
Estimated Portfolio Value:       $X,XXX,XXX (matching units x avg price x [advance_rate]%)
Monthly Volume Estimate:         XX units ([matching] x 30/[avg_dom] x 20% penetration)

GAP ANALYSIS — Why [Z] units don't qualify:
- Outside price range:  [X] units (avg $XX,XXX) → expanding to $[Y] adds [N] units
- Too old:              [X] units (avg [year]) → expanding to [year] adds [N] units
- Too high mileage:     [X] units (avg XX,XXX mi) → expanding to [mi] adds [N] units
- Wrong make:           [X] units (if make filter applied)

MATCHING INVENTORY PROFILE
Top Makes:    [Make1] XX%, [Make2] XX%, [Make3] XX%
Body Types:   [Type1] XX%, [Type2] XX%
Year Range:   [oldest]-[newest]

RECOMMENDATION
This dealer is a [STRONG/MODERATE/LIGHT] fit. [X]% of their lot qualifies.
Recommended approach: [specific action based on data].

Source: MarketCheck inventory data, [Date].
```

## Output
Fit report: Total Units, Matching Units, Coverage %, Avg Price (all), Avg Price (matching). LTV Distribution chart: Under 100%, 100-110%, 110-120%, Over 120%. Estimated portfolio value and monthly volume. Gap breakdown: why units don't qualify, with expansion suggestions. Matching inventory profile: top makes, body types, year range. Recommendation: "This dealer is a [STRONG/MODERATE/LIGHT] fit. [X]% of their lot qualifies. Recommended approach: [specific]."

## Self-Check (before presenting to user)

1. **Coverage % math is correct?** matching_units / total_units x 100. Verify matching_units comes from the filtered search and total_units from the unfiltered search. They should not be equal unless coverage is 100%.
2. **LTV ratio direction is correct?** LTV = listed_price / predicted_price x 100. Over 100% = listing above market (higher risk). Under 100% = listing below market. Verify you did not invert this.
3. **Gap analysis numbers add up?** The sum of "outside price range" + "too old" + "too high mileage" + "wrong make" should approximately equal (total_units - matching_units). They may not sum exactly due to overlap, but should be in the right ballpark. Note overlaps if significant.
4. **Expansion suggestions are quantified?** Each gap category should include "expanding [criteria] to [value] would add [N] units." This requires additional API calls — if not made, note as "estimate" or omit.
5. **LTV sample is representative?** Confirm you sampled from cheap, median, and expensive ends. If the matching set has fewer than 10 units, sample all of them.
6. **Fit classification matches thresholds?** STRONG (>60%), MODERATE (30-60%), LIGHT (<30%). Verify the label matches the actual coverage %.
