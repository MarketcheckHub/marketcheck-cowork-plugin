# UK Workflow Adaptation

The UK MarketCheck surface is smaller than the US surface: only two tools, no VIN decoder, no ML predictor, no sold-summary, no per-VIN history. This document is the authoritative workflow shape for a `country == "UK"` profile. Read it before making any MCP call when the profile's country is UK.

> **Testing note:** The UK branch should be exercised against a live UK profile separately from US validation runs. Fixture profiles + captured responses should live in `tests/fixtures/uk/` when added.

## Tool matrix

| Capability | US tool (not usable) | UK equivalent |
|---|---|---|
| Active-listing search | `search_active_cars` | `search_uk_active_cars` |
| Sold / recently-ended listing search | `search_past_90_days` | `search_uk_recent_cars` |
| VIN decode | `decode_vin_neovin` | **Not available — ask user for YMMT + variant** |
| ML price prediction | `predict_price_with_comparables` | **Not available — use comp median** |
| State/region rollup | `get_sold_summary` | **Not available — skip the State Baseline line** |
| VIN history | `get_car_history` | **Not available — Historical Trajectory (W5) halts on UK** |
| `dealer_type` filter | yes | **Not exposed — Wholesale-vs-Retail (W3) halts on UK** |

## Per-workflow UK status

| Workflow | UK status | Notes |
|---|---|---|
| W1 — Full Comparable Appraisal | **Adapted** | Use comp median from `search_uk_active_cars` as anchor; `search_uk_recent_cars` for sold evidence; no State Baseline; no MarketCheck Price ML; no CPO Premium. |
| W2 — Trade-In Quick Appraisal | **Adapted** | Single wave: `search_uk_active_cars` (rows=10, stats="price,miles") → median + comp set. No predict, no dealer_type spread (W3 routes to W1 on UK anyway). |
| W3 — Wholesale-vs-Retail Spread | **HALT** | `dealer_type` filter is not exposed on the UK active surface (per `mcp_server_tool_docs/search_uk_active_cars.md`). Halt with: *"Wholesale-vs-Retail Spread workflow is US-only — `dealer_type` is not exposed on the UK active surface."* |
| W4 — Regional Price Variance | **Adapted** | Multi-postcode comparison via `search_uk_active_cars` × N. No `get_sold_summary` — omit the State Baseline section. |
| W5 — Historical Trajectory | **HALT** | `get_car_history` is not available for UK. Halt with: *"Historical Trajectory workflow is US-only — `get_car_history` is not available for UK."* |

## Parameter shape differences

`search_uk_active_cars` and `search_uk_recent_cars` accept a different parameter surface from their US cousins:

- **Location is `postal_code` + `radius_miles`**, not `zip` + `radius`. Read the profile's `location.zip` field (which stores postcode for UK profiles) and pass it as `postal_code`. Fall back to `location.county` or `location.city` if postcode isn't present.
- **`variant` replaces `trim`.** Trim-equivalent line information sits in the `variant` facet; pass the user's variant string verbatim.
- **No `car_type` filter.** The UK endpoints return used listings by default; there is no `new` option on these tools.
- **No `dealer_type` filter.** Franchise vs independent distinction isn't exposed at the UK endpoint; render dual pricing is N/A for UK and skip the Same-Channel View section.
- **`price_range`, `miles_range`, `year_range` all use the same `"min-max"` string format as US.** Keep `price_range="1-*"` for the $0-filter convention.
- **Stats support is limited.** `search_uk_recent_cars` accepts `stats="price"` for the sold anchor; multi-field stats requests may be rejected — fall back to per-field calls, same pattern as US `search_past_90_days`.

## Truncation handling

`search_uk_active_cars` and `search_uk_recent_cars` have **not been empirically observed to truncate** as of 2026-04-30, but the recipe below is provided defensively. Use the same Write-tool-then-parse-file pattern documented in `references/truncation-recovery.md`:

```
Write(file_path="/tmp/marketcheck/<session.run_id>/uk_asc.json",
      content="<full envelope-wrapped response verbatim>")

parse_search.py --file /tmp/marketcheck/<session.run_id>/uk_asc.json --subject-vin <VIN>
```

The same parsers (`parse_search.py`, `_common._maybe_unwrap`) handle UK responses and US responses identically — the envelope shape is the same.

## UK W1 — Full Comparable Appraisal (adapted)

1. **Ask the user for YMMT + variant + mileage + condition + purpose.** No VIN decode is available; the user supplies specs directly. Confirm back before proceeding.

2. **Active comp set (asc + desc).** Identical to US W1 step 4-5 except:
   - tool = `search_uk_active_cars`
   - `postal_code` instead of `zip`, `radius_miles` instead of `radius`
   - `variant` instead of `trim`

3. **Sold anchor.** Single call:

   ```
   search_uk_recent_cars:
     year, make, model, variant, postal_code, radius_miles=<clamped>
     stats="price", rows=0, sold=true (when supported), price_range="1-*"
   → parse_search.py
   ```

   Use `stats.price.median` as the **primary appraisal anchor** when `num_found >= 5`. Pass to `compute_appraisal_band.py` as `sold_median` + `sold_count_90d`. When `num_found < 5`, fall back to the active comp median (anchor_source = "active_comps").

4. **Compute stats + band** as usual via `comp_stats.py` → `compute_appraisal_band.py`. `subject_is_certified=false` always (CPO is a US concept; the UK "Approved Used" programs are manufacturer-specific and the skill does not model them).

5. **Render** via `assets/output-template.md` with these UK adaptations:
   - All money values use `£` instead of `$` (pass `--currency '£'` to every renderer script).
   - Predicted Prices block — **omitted** (no ML available).
   - CPO Premium block — **omitted**.
   - Same-Channel View block — **omitted** (no dealer_type).
   - State Baseline section — **omitted**.
   - Headline names the sold anchor source as "UK recent-sales median of £X (N units)".

## UK W2 — Trade-In Quick Appraisal (adapted)

Single Wave; ~12s wall clock.

```
search_uk_active_cars:
  year, make, model, variant, postal_code, radius_miles=<clamped>
  rows=10, stats="price,miles", sort_by="price", sort_order="asc"
  price_range="1-*"
  include_dealer_object=true, include_build_object=true
→ parse_search.py
```

Render the W2 card with:
- Predicted Retail Value: `stats.price.median`
- Wholesale Value: not directly computable (no dealer_type). Show "(unavailable on UK — see W4 for cross-postcode arbitrage)".
- Recommended Trade-In Offer: `0.78 × median` to `0.85 × median` (industry rule-of-thumb spread; same as US default).
- Top 5 retail comparables: render via `render_comp_set_table.py --currency '£'`.
- Confidence band per `compute_appraisal_band.py` rules — typically Low / Medium for UK because no sold-90d count is available (set `sold_count_90d=0`, anchor_source defaults to "active_comps").

## UK W4 — Regional Price Variance (adapted)

Same shape as US W4 but with the UK tools and parameter names:

1. Stats-only `search_uk_active_cars` × N (one per postcode).
2. **Skip** `get_sold_summary` — UK has no equivalent.
3. Aggregate via `compute_regional_variance.py` with `--sold-summary` omitted.
4. Render without State Baseline section.

## UK W3 / W5 — halt

Per the workflow status table above. The skill emits the canonical halt sentence and does not fire any MCP call.
