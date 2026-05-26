# UK workflow adaptation

The UK MarketCheck surface is smaller than the US surface: only two tools, no VIN decoder, no ML predictor, no sold-summary, no per-VIN history. This document is the authoritative workflow shape for a `country == "UK"` profile. Read it before making any MCP call when the profile's country is UK.

## Tool matrix

| Capability | US tool (not usable) | UK equivalent |
|---|---|---|
| Active-listing search | `search_active_cars` | `search_uk_active_cars` |
| Sold / recently-ended listing search | `search_past_90_days` | `search_uk_recent_cars` |
| VIN decode | `decode_vin_neovin` | **Not available — ask appraiser for YMMT + variant** |
| ML price prediction | `predict_price_with_comparables` | **Not available — use comp median as anchor** |
| State/region rollup | `get_sold_summary` | **Not available — omit the State Baseline line** |
| VIN history | `get_car_history` | **Not available — Trade-In History (W2) halts on UK** |

## Parameter shape differences

`search_uk_active_cars` and `search_uk_recent_cars` accept a different parameter surface from their US cousins:

- **Location is `postal_code` + `radius_miles`**, not `zip` + `radius`. Read the profile's `location.zip` (which stores postcode for UK profiles) and pass it as `postal_code`. Fall back to `location.county` or `location.city` if postcode isn't present.
- **`variant` replaces `trim`.** Trim-equivalent line information sits in the `variant` facet; pass the user's variant string verbatim.
- **No `car_type` filter.** UK endpoints return used listings by default; there is no `new` option.
- **No `dealer_type` filter.** Franchise vs independent distinction isn't exposed at the UK endpoint; the Wholesale-vs-Retail Spread block from W1 / W3 collapses to a single UK Market Price line.
- **`price_range`, `miles_range`, `year_range` use the same `"min-max"` string format as US.** Keep `price_range="1-*"` for the $0-filter convention.
- **Stats support is limited.** `search_uk_recent_cars` accepts `stats="price"` for the sold anchor; multi-field stats requests may be rejected — fall back to per-field calls.

## Truncation handling

`search_uk_active_cars` and `search_uk_recent_cars` have **not been empirically observed to truncate** in routine appraiser-scale calls (≤20 rows + small stats). If upstream ever returns a payload that doesn't fit inline, apply the same `Write` → re-read → `json.loads` recipe from `references/truncation-recovery.md` — the envelope shape is identical to US. No UK-specific adaptation needed.

## W1 — Single-VIN Price-Check (UK adaptation)

The UK W1 analogue is structurally similar to the US W1 but with the smaller toolset.

1. **Ask the appraiser for YMMT + variant + mileage + (optionally) asking price.** No VIN decode is available; the appraiser supplies specs directly. Confirm back before proceeding.

2. **Active comp set — asc pull (Wave A).**

   ```
   search_uk_active_cars:
     year, make, model, variant
     postal_code, radius_miles=<radius_mi_clamped>
     price_range="1-*"
     sort_by="price", sort_order="asc"
     rows=20
     stats="price,miles"
     include_dealer_object=true  (if supported)
     include_build_object=true   (if supported)
   ```

   Variant consistency is the server's responsibility — pass `variant` verbatim and trust the facet match. `body_type`, `drivetrain`, `engine`, and `transmission` (when UK listings carry them via the build object) are display-only spec metadata; they are never used as filters.

3. **Tail coverage — desc pull (Wave A).** Issue in parallel with asc. If `asc.num_found > 20`, the desc rows provide tail coverage; if `≤ 20`, the desc rows duplicate the asc rows and dedupe cleanly.

   ```
   search_uk_active_cars:
     (same base filters as asc)
     sort_by="price", sort_order="desc"
     rows=10
   ```

4. **Sold anchor (Wave A).**

   ```
   search_uk_recent_cars:
     year, make, model, variant
     postal_code, radius_miles=<radius_mi_clamped>
     stats="price"
     rows=0
     price_range="1-*"
   ```

   Use `stats.price.median` as the **primary price anchor** when `num_found >= min_comp_count`. This substitutes for the US `predict_price_with_comparables.predicted_price` in the Anchor / Value Range block. When `num_found < min_comp_count`, fall back to the active comp median (step 2).

5. **Merge asc + desc, exclude subject VIN.** Dedupe by VIN, desc-first on duplicates, subject VIN never appears in its own comp set.

6. **Compute stats.** Quartile / percentile / DOM buckets from the merged active comps. `subject_is_certified = false` always — CPO is a US concept; UK "Approved Used" is manufacturer-specific and the skill does not model it.

7. **Render.** Apply these UK adaptations to `assets/output-template.md`:
   - First line: `Using profile: appraiser, <postcode>, UK`.
   - Headline anchor source: *"UK recent-sales median of £<X> (<N> units)"* when sold-anchor fires; else *"active-listing median of £<X> (<N> comps)"*.
   - **Wholesale-vs-Retail Spread block** is replaced by a single **UK Market Price** line — no franchise/independent split.
   - **CPO Premium block** is omitted.
   - **State Baseline line** is omitted (no `get_sold_summary` for UK).
   - All money values use `£` instead of `$`.

## W2 — Trade-In VIN Price History (UK halt)

**Halt** on UK with: *"Trade-in price history is US-only (requires `get_car_history`, not available for UK). For UK valuation context, run `/price-check` for the current market distribution or use `appraiser:vehicle-appraiser` for a full appraisal."*

## W3 — Market Price Distribution (UK adaptation)

Same shape as US W3 but with the UK tools and parameter names:

1. Facet-discover once via `search_uk_active_cars` (or trust user YMMT + variant if it came from a prior decode this session — though decode is US-only, so trust is rare on UK).

2. Stats-only calls (Wave B, parallel):
   - `search_uk_active_cars` model-level stats (no `variant` filter)
   - `search_uk_active_cars` variant-level stats (when variant is known)
   - `search_uk_recent_cars` sold anchor (`stats="price"`, `rows=0`)
   - `search_uk_active_cars` cheapest 8 listings (`sort_by=price asc, rows=8`)
   - `search_uk_active_cars` most-expensive 5 listings (`sort_by=price desc, rows=5`)

3. Render with these adaptations:
   - **Wholesale-vs-Retail Spread block** is omitted (no `dealer_type` filter on UK).
   - **State Baseline line** is omitted.
   - Currency `£`.
   - 8-col comparable citation table renders the `Type` column as `—` for every row (no dealer_type on UK listings).

## Specialisation-driven hints

The UK appraiser audience often appraises imports, hand-builds, or low-volume variants. If `profile.specialization` is set (e.g., `"luxury"`, `"classic"`, `"import"`), surface a one-line footer note: *"Tuned for: <specialization>. Thin markets are common at this scope — interpret the value range with that in mind."*
