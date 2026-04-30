# UK Workflow Adaptation

The UK MarketCheck surface is smaller than the US surface: only two tools, no VIN decoder, no ML predictor, no sold-summary. This document is the authoritative workflow shape for a `country == "UK"` profile. Read it before making any MCP call when the profile's country is UK.

> **Testing note:** The UK branch should be exercised against a live UK profile separately from US validation runs. Fixture profiles + captured responses should live in `tests/fixtures/uk/` when added — the branch has not yet been validated end-to-end in the v5/v6 live-test series.

## Tool matrix

| Capability | US tool (not usable) | UK equivalent |
|---|---|---|
| Active-listing search | `search_active_cars` | `search_uk_active_cars` |
| Sold / recently-ended listing search | `search_past_90_days` | `search_uk_recent_cars` |
| VIN decode | `decode_vin_neovin` | **Not available — ask user for YMMT** |
| ML price prediction | `predict_price_with_comparables` | **Not available — use comp median** |
| State/region rollup | `get_sold_summary` | **Not available — skip the State Baseline line** |
| VIN history | `get_car_history` | **Not available — Trade-In workflow (W3) halts on UK** |

## Parameter shape differences

`search_uk_active_cars` and `search_uk_recent_cars` accept a different parameter surface from their US cousins:

- **Location is `postal_code` + `radius_miles`**, not `zip` + `radius`. Read the profile's `location.zip` field (which stores postcode for UK profiles) and pass it as `postal_code`. Fall back to `location.county` or `location.city` if postcode isn't present.
- **`variant` replaces `trim`.** Trim-equivalent line information sits in the `variant` facet; pass the user's variant string verbatim.
- **No `car_type` filter.** The UK endpoints return used listings by default; there is no `new` option on these tools.
- **No `dealer_type` filter.** Franchise vs independent distinction isn't exposed at the UK endpoint; render dual pricing is N/A for UK and skip the Same-Channel View section.
- **`price_range`, `miles_range`, `year_range` all use the same `"min-max"` string format as US.** Keep `price_range="1-*"` for the $0-filter convention.
- **Stats support is limited.** `search_uk_recent_cars` accepts `stats="price"` for the sold anchor; multi-field stats requests may be rejected — fall back to per-field calls, same pattern as US `search_past_90_days`.

## Truncation handling

`search_uk_active_cars` and `search_uk_recent_cars` have **not been empirically observed to truncate** as of 2026-04-23, but the recipe below is provided defensively — if upstream ever returns a large payload that doesn't fit inline, the US recipe works unchanged. Use the same Write-tool-then-parse-file pattern documented in `references/truncation-recovery.md`:

```
# agent saves the raw envelope to the run directory (run_id from session block)
Write(file_path="/tmp/marketcheck/<session.run_id>/uk_asc.json",
      content="<full envelope-wrapped response verbatim>")

# parse via --file (parse_search.py handles both US and UK listing shapes)
parse_search.py --file /tmp/marketcheck/<session.run_id>/uk_asc.json --subject-vin <VIN>
```

The same parsers (`parse_search.py`, `_common._maybe_unwrap`) handle UK responses and US responses identically — the envelope shape is the same. If the MCP runtime saves a truncation file to `tool-results/*.txt`, point `parse_search.py --file` at that path directly. No UK-specific adaptation of the recovery path is needed.

## Workflow shape for UK Price-Check (W1 analogue)

1. **Ask the user for YMMT + variant + mileage + asking price.** No VIN decode is available; the user supplies specs directly. Confirm back before proceeding.

2. **Active comp set (asc pull).**

   ```
   search_uk_active_cars:
     year, make, model, variant, postal_code, radius_miles=<clamped>
     price_range="1-*", sort_by="price", sort_order="asc", rows=20
     stats="price,miles"
     include_dealer_object=true (if supported)
     include_build_object=true  (if supported)
   → parse_search.py  --subject-vin <subject>
   ```

   Variant consistency is the server's responsibility — pass `variant`
   verbatim and trust the facet match. `body_type`, `drivetrain`, `engine`,
   and `transmission` (when UK listings carry them via the build object) are
   display-only spec metadata rendered on comp listings via the optional
   spec subtitle; they are never used as filters.

3. **Tail coverage desc pull.** Same rule as US — if `asc.num_found > 20`, issue a desc pull at `rows=10`, merge by VIN.

4. **Sold anchor.**

   ```
   search_uk_recent_cars:
     year, make, model, variant, postal_code, radius_miles=<clamped>
     stats="price", rows=0
   → parse_search.py
   ```

   Use `stats.price.median` as the **primary price anchor** when `num_found >= 5`. This substitutes for the US `predict_price_with_comparables.marketcheck_price`. When `num_found < 5`, fall back to the active comp median (step 2).

5. **Price-drop velocity.**

   ```
   search_uk_active_cars:
     same base filters + price_change="negative", rows=0
   → parse_search.py (use num_found for the "N of N have cut price" line)
   ```

6. **Compute stats.** Feed `comp_stats.py` with the merged active comps, the UK-sourced sold median, and `subject_is_certified=false` (CPO is a US concept; the UK "Approved Used" programs are manufacturer-specific and the skill does not model them).

7. **Render.** **First: Read `assets/output-template.md`** for block structure, 8-col comp schema, and verdict phrasing. Then apply these UK adaptations:
   - Headline names the sold anchor source as "UK recent-sales median of £X (N units)".
   - Price Position block shows a single "UK Market Price" row (no franchise / independent split).
   - Skip the Same-Channel View, CPO Premium, and State Baseline sections — they don't apply.
   - All money values use `£` instead of `$`.

## UK Market Distribution (W4 analogue)

Same shape as US W4 but with the UK tools and parameter names:

1. Facet-discover once via `search_uk_active_cars` (or trust user YMMT).
2. Stats-only `search_uk_active_cars × 2` (model-level + variant-level).
3. Stats-only `search_uk_recent_cars × 1` for the sold anchor.
4. Cheapest 8 + Most-expensive 5 via `search_uk_active_cars`.
5. Render without By-Channel, State Baseline.

## UK Competitor Price Movement (W5 analogue)

Same shape as US W5 — three MCP calls (drop scan + raise scan + denominator) via `search_uk_active_cars`. `price_change` filter works the same way. Dealer grouping works on the UK listing's `dealer_name`.

## UK Trade-In Price History (W3)

**Halt** with: `"Trade-In workflow is US-only (requires get_car_history, not available for UK)."`

## UK Batch Scan (W2)

Halt on the 5-VIN pre-check as usual — but substitute "provide me year/make/model/variant per unit + mileage + asking price" in place of the VIN decode step. Each unit's workflow then follows the UK W1 shape above.
