# W4 — Regional Price Variance

Triggered by "what's it worth in NY", "compare values across markets", "regional price difference", "fleet relocation analysis", "where is the cheapest market for this", "arbitrage opportunity", etc. **Multi-ZIP market comparison; no subject vehicle** — the question is about how a year/make/model/trim's market value differs across geographies.

W4 is the **arbitrage / fleet workflow**. Use it when the user wants to know if the same vehicle sells for materially more or less in another region — common for multi-state dealer groups, fleet relocations, or insurance-claim adjusters comparing regional norms.

**US-only by canonical path** — UK profiles route to the analogue in `references/country-uk.md` (multi-postcode `search_uk_active_cars`; no `get_sold_summary` so no State Baseline section).

## Required inputs

- **YMMT** at minimum: `{year, make, model}`. `trim` is **optional** (when supplied the comparison is trim-specific; when absent, model-level across all trims).
- **A list of ZIPs** to compare — minimum 2, maximum 6. Each ZIP defines one market.
- **No subject VIN, no asking price, no current odometer.** W4 describes markets, not a specific unit.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | Route to UK W4 adaptation per `references/country-uk.md`. |
| `profile.location.country == "CA"` | Halt per SKILL.md country routing. |
| `profile.preferences.default_inventory_type == "both"` | Halt-and-ask: *"Regional Price Variance for used or new?"* Apply for the rest of the session. |
| User supplied < 2 ZIPs | *"W4 needs at least 2 ZIPs to compare. Please supply 2-6 ZIP codes."* |
| User supplied > 6 ZIPs | *"W4 caps at 6 ZIPs inline (latency budget). For broader analyses, route the request to the dealership-group:cross-location-balancer skill."* |
| User supplied only year+make (no model) | *"W4 needs at minimum `{year, make, model}`."* |

## Wave A — Facet discovery (single call, optional)

Fires only when user-typed YMMT casing is untrusted. Cross-reference `references/facet-discovery.md`. If facet discovery returns 0 results in the user's primary ZIP, halt with *"No comps found for `<make> <model> <trim>` in `<primary ZIP>` within `<radius>` mi. Try widening, dropping trim, or check spelling."*

## Wave B — N parallel stats-only calls + state baseline

For each of the 2-6 user-supplied ZIPs, fire one stats-only `search_active_cars`:

```
search_active_cars:
  year, make, model[, trim]
  zip=<ZIP_i>, radius=100, car_type=<session.car_type_resolved>
  rows=0
  stats="price,miles"
  fetch_all_photos=false, include_mc_dealership_object=false,
  include_finance=false, include_lease=false, include_relevant_links=false,
  include_dealer_object=false, include_build_object=false
→ parse_search.py --file
```

(`radius=100` is the upstream max for `search_past_90_days`; we use the same value for the active calls so the ZIPs are compared on a consistent radius. Profile's `radius_mi_clamped` is ignored here — the user is asking for cross-market comparison, not their dealer-radius preference.)

In parallel, fire one `get_sold_summary` for the dealer's home state (or the state of the first ZIP if no dealer state):

```
get_sold_summary:
  make, model
  inventory_type="Used"  (or "New" per session)
  state=<dealer state OR first-ZIP state>
  summary_by="state"
  ranking_measure="average_sale_price"
  ranking_order="desc"
  ranking_dimensions="make,model"
  top_n=10                                       # show 10 highest-priced states for context
  limit=5000
  date_from / date_to from compute_sold_summary_dates.py
  (NEVER pass dealer_type)
→ parse_sold_summary.py --aggregate-state <STATE>
```

The state baseline is enrichment — its top-10 list shows which states command the highest sold prices, useful for "is this segment hot in TX?" intuition. When degraded, omit silently with a DQ event.

**Total Wave B calls:** N (one per ZIP) + 1 (sold summary) = 3-7 calls.
**Wall-clock budget:** ≈ 25s.

## Pipeline (post-wave)

```
parse_search.py --file <zip_1.json>     → stats-only output for ZIP 1
parse_search.py --file <zip_2.json>     → stats-only output for ZIP 2
... (one per ZIP)
parse_sold_summary.py --aggregate-state <STATE> < <get_sold_summary output> → state_baseline + rows

compute_regional_variance.py \
  --zip-stats "<ZIP_1>:<parse_search-output-1>" \
  --zip-stats "<ZIP_2>:<parse_search-output-2>" \
  ... \
  --sold-summary <parse_sold_summary output> \
  --threshold-pct 5.0
→ regional comparison JSON
```

`compute_regional_variance.py` emits:
- `markets[]` — one per ZIP with median, mean, p25, p75, miles_median, num_found, delta_from_lowest_$/pct, arbitrage_flag.
- `lowest_market` and `highest_market` — picked among non-empty markets.
- `max_delta_pct` — the largest spread in the comparison.
- `state_baselines[]` — pass-through from sold-summary (if supplied).

## Output rendering

W4 renders via `assets/output-template.md` with the W4-specific block list:

1. **Headline** — `<year> <make> <model> [<trim>] across <N> markets: <lowest_market.zip> cheapest at $<median>, <highest_market.zip> highest at $<median>; max spread <max_delta_pct>%.`
2. **Market Snapshot (per market)** — table with one row per ZIP: `ZIP | n | min | p25 | median | p75 | max | mean | miles_median | delta_$ | delta_pct | arbitrage?`. Render arbitrage_flag rows with a `⚡` marker.
3. **State Baseline (top 10 states by avg sale price)** — when sold-summary returned non-empty rows. Include the dealer's state row and call out where it ranks.
4. **By-Market Mileage Distribution** — small table showing `miles_median` per market so users can verify the comparison isn't apples-to-oranges (e.g., NYC's market is mostly low-mile units while Houston's is high-mile).
5. **Cheapest 8 listings (across the lowest market)** — optional 8-col via `render_comp_set_table.py`. Skipped if user didn't request listing-level detail (the W4 default is summary tables only).
6. **Methodology Notes** — list the threshold (5%), the radius (100mi each), the date window (`stats="price,miles"` is current snapshot, not historical), the arbitrage flag definition.
7. **Caveats** — markets with `num_found < 6` are flagged with a Low confidence note; mileage-distribution differences across markets can confound the price comparison.
8. **Data Quality Notes** (when non-empty).
9. **Key Signals** — at least one bullet for each market with `arbitrage_flag=true`. Example: *"<ZIP_X> is <delta_pct>% above the cheapest market (<ZIP_low>) — potential arbitrage / relocation value."*
10. **Self-check footer**.

**Omitted blocks** (no subject vehicle): Recommended Value (condition-adjusted), Predicted Prices, CPO Premium, Same-Channel View, Sold Transaction Comparables, Active Retail Comparables (per-market level — replaced by the per-market summary table).

## Failure recovery and edge cases

| Case | Behavior |
|---|---|
| UK profile | Route to UK W4 adaptation. |
| `< 2` or `> 6` ZIPs supplied | Halt at pre-check. |
| Free-form YMMT casing | Run Wave A facet discovery once. |
| Facet discovery 0 results in primary ZIP | Halt. |
| One ZIP returns `num_found=0` | Render that row as `(empty)`; exclude from `lowest_market` / `highest_market` selection (`compute_regional_variance.py` already handles this); emit Key Signal noting the empty market. |
| All ZIPs return `num_found=0` | Render the empty-state header (`Headline: no listings in any market`) and stop. |
| Thin market — `num_found < 6` for some ZIP | Render with a "Low-confidence-for-this-market" footnote; the median is still shown but flagged. |
| `get_sold_summary` `make_model_not_found` | Retry once with facet-discovered casing; if still failing, omit State Baseline; emit DQ event (a). |
| `get_sold_summary` other failure | Skip State Baseline; emit DQ event (a). Do NOT halt the workflow. |
| Truncation envelope on any call | Standard `Write` + `--file` recovery per `references/truncation-recovery.md`. |
