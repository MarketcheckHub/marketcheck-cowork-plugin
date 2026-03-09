---
name: lending-fit-analyzer
description: >
  This skill should be used when the user asks "how many units can I lend on",
  "lending fit for [dealer]", "coverage analysis", "what can I finance there",
  "LTV analysis for [dealer]", "overlay my criteria on this lot",
  "which units qualify", "portfolio fit check",
  or needs to see exactly how much of a dealer's inventory matches
  their lending criteria with LTV analysis.
version: 0.1.0
---

# Lending Fit Analyzer — Overlay Lending Criteria on a Dealer's Lot

## Profile
Load `~/.claude/marketcheck/lender-sales-profile.json` if exists. Extract: price_range_min, price_range_max, preferred_year_range, max_mileage, approved_makes, approved_segments, ltv_max_pct, country, zip, radius. If missing, ask minimum fields. **US**: `search_active_cars`, `predict_price_with_comparables`. **UK**: `search_uk_active_cars` only (no LTV check — skip predict calls). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep wants to precisely quantify how much of a dealer's lot they can finance. Used to prepare proposals, justify partnerships, and identify gap opportunities.

## Workflow: Full Fit Analysis

1. **Get total dealer inventory** — Call `mcp__marketcheck__search_active_cars` with `dealer_id` (or `source`), `car_type=used`, `rows=0`, `stats=price,miles,dom`, `facets=make|0|20|1,body_type|0|10|1,year|0|10|1`.
   → **Extract only**: total_count, stats (avg_price, median, min, max), facets. Discard full response.

2. **Get matching inventory** — Call `mcp__marketcheck__search_active_cars` with same dealer, `price_range=[min]-[max]`, `year=[year_range]`, `miles_range=0-[max_mileage]`, `rows=0`, `stats=price,miles`, `facets=make|0|20|1,body_type|0|10|1`.
   If `approved_makes` is set, add `make=[comma-separated]`. If `approved_segments` is set, add `body_type=[comma-separated]`.
   → **Extract only**: matching_count, stats, facets. Discard full response.

3. **LTV analysis** — For a representative sample (up to 10 units: 3 cheapest, 4 median, 3 most expensive from matching set), call `mcp__marketcheck__search_active_cars` with same dealer + criteria, `sort_by=price`, `sort_order=asc`, `rows=3` for cheap end; then `sort_order=desc`, `rows=3` for expensive end; then `rows=4`, `start=matching_count/2-2` for middle.
   For each sampled VIN, call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type` matching dealer type.
   → **Extract only per VIN**: listed_price, predicted_price. Calculate LTV = listed_price / predicted_price × 100. Discard full responses.

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

## Output
Fit report: Total Units, Matching Units, Coverage %, Avg Price (all), Avg Price (matching). LTV Distribution chart: Under 100%, 100-110%, 110-120%, Over 120%. Estimated portfolio value and monthly volume. Gap breakdown: why units don't qualify, with expansion suggestions. Matching inventory profile: top makes, body types, year range. Recommendation: "This dealer is a [STRONG/MODERATE/LIGHT] fit. [X]% of their lot qualifies. Recommended approach: [specific]."
