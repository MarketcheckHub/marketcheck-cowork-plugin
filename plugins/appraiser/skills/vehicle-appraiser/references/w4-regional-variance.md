# W4 — Regional Price Variance

Triggered by "what's it worth in NY", "compare values across markets", "regional price difference", "multi-state insurance claim", "fleet relocation analysis", "where is the cheapest market for this", "arbitrage opportunity", etc. **Multi-ZIP market comparison; no subject vehicle** — the question is about how a year/make/model/trim's market value differs across geographies.

W4 is the **arbitrage / fleet / multi-state-claims workflow**. Use it when the user wants to know if the same vehicle sells for materially more or less in another region — common for multi-state insurance adjusters, estate executors with property across jurisdictions, fleet relocations, and independent appraisal firms comparing regional norms.

**US-only by canonical path** — UK profiles route to the analogue in `references/country-uk.md` (multi-postcode `search_uk_active_cars`; no `get_sold_summary` so no State Baseline section).

## Required inputs

- **YMMT** at minimum: `{year, make, model}`. `trim` is **optional** (when supplied the comparison is trim-specific; when absent, model-level across all trims).
- **A list of ZIPs / postcodes** to compare — minimum 2, maximum 6. Each ZIP defines one market.
- **No subject VIN, no asking price, no current odometer.** W4 describes markets, not a specific unit.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | Route to UK W4 adaptation per `references/country-uk.md`. |
| `profile.location.country` not in (US, UK) | Halt per SKILL.md country routing. |
| User supplied < 2 ZIPs | *"W4 needs at least 2 ZIPs to compare. Please supply 2-6 ZIP codes."* |
| User supplied > 6 ZIPs | *"W4 caps at 6 ZIPs inline (latency budget). For broader analyses, please split the request into multiple W4 runs of 2-6 ZIPs each."* |
| User supplied only year+make (no model) | *"W4 needs at minimum `{year, make, model}`."* |

**Subject `car_type` derivation:** the user is asking about a market, not a specific unit. Default to `car_type="used"` for the comparison. If the user explicitly asks "new only" or "used only", honor it. If they're ambiguous and the YMMT is current-or-next-model-year, ask: *"Compare used inventory or new inventory across these markets?"*

## Wave A — Facet discovery (single call, optional)

Fires only when user-typed YMMT casing is untrusted. Cross-reference `references/facet-discovery.md`. If facet discovery returns 0 results in the user's primary ZIP, halt with *"No comps found for `<make> <model> <trim>` in `<primary ZIP>` within `<radius>` mi. Try widening, dropping trim, or check spelling."*

## Wave B — N parallel stats-only calls + state baseline

For each of the 2-6 user-supplied ZIPs, fire one stats-only `search_active_cars`:

```
search_active_cars:
  year, make, model[, trim]
  zip=<ZIP_i>, radius=100, car_type=<derived>
  rows=0
  stats="price,miles"
  price_range="1-*"                          # per-ZIP num_found is rendered and feeds lowest/highest market selection; without the filter, null-price rows inflate the per-market count
  fetch_all_photos=false, include_mc_dealership_object=false,
  include_finance=false, include_lease=false, include_relevant_links=false,
  include_dealer_object=false, include_build_object=false
→ parse_search.py --file
```

(`radius=100` is the upstream max for `search_past_90_days`; the same value is used for the active calls so the ZIPs are compared on a consistent radius. Profile's `radius_mi_clamped` is ignored here — the user is asking for cross-market comparison, not their local-radius preference.)

In parallel, fire one `get_sold_summary` for the appraiser's home state (or the state of the first ZIP if no profile state):

```
get_sold_summary:
  make, model
  inventory_type="Used"  (or "New" per derived car_type)
  state=<profile state OR first-ZIP state>
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
```

Then at render time, compute per the formula below:

```
markets[i] = {
  zip: <ZIP_i>,
  n: parse_search.num_found,
  median: parse_search.stats.price.median,
  mean: parse_search.stats.price.mean,
  p25: parse_search.stats.price.p25,
  p75: parse_search.stats.price.p75,
  min: parse_search.stats.price.min,
  max: parse_search.stats.price.max,
  miles_median: parse_search.stats.miles.median,
}

lowest_market  = min(markets, key=lambda m: m.median)  # filter out empty markets
highest_market = max(markets, key=lambda m: m.median)

# Per-market delta-from-lowest (each market's median compared to the lowest market's median)
for m in markets:
  m.delta_$   = m.median - lowest_market.median
  m.delta_pct = m.delta_$ / lowest_market.median * 100
  m.arbitrage = (m.delta_pct > 5.0)

max_delta_pct = max(m.delta_pct for m in markets)
```

## Output rendering

W4 renders via `assets/output-template.md` with the W4-specific block list:

1. **Headline** — `<year> <make> <model> [<trim>] across <N> markets: <lowest_market.zip> cheapest at $<median>, <highest_market.zip> highest at $<median>; max spread <max_delta_pct>%.`
2. **Market Snapshot (per market)** — table with one row per ZIP: `ZIP | n | min | p25 | median | p75 | max | mean | miles_median | delta_$ | delta_pct | arbitrage?`. Render arbitrage rows with a `⚡` marker.
3. **State Baseline (top 10 states by avg sale price)** — when sold-summary returned non-empty rows. Include the appraiser's state row (if available) and call out where it ranks.
4. **By-Market Mileage Distribution** — small table showing `miles_median` per market so users can verify the comparison isn't apples-to-oranges (e.g., NYC's market is mostly low-mile units while Houston's is high-mile).
5. **Cheapest 8 listings (across the lowest market)** — optional 8-col standard table. Skipped if user didn't request listing-level detail (the W4 default is summary tables only).
6. **Methodology Notes** — list the threshold (5%), the radius (100mi each), the date window (`stats="price,miles"` is current snapshot, not historical), the arbitrage flag definition.
7. **Caveats** — markets with `num_found < session.min_comp_count` are flagged with a Low confidence note; mileage-distribution differences across markets can confound the price comparison.
8. **Data Quality Notes** (when non-empty).
9. **Key Signals** — at least one bullet for each market with `arbitrage=true`. Example: *"<ZIP_X> is <delta_pct>% above the cheapest market (<ZIP_low>) — potential arbitrage / relocation value."*
10. **Self-check footer**.

**Omitted blocks** (no subject vehicle): Recommended Value (condition-adjusted), Predicted Prices, CPO Premium, Sold Transaction Comparables, Active Retail Comparables (per-market level — replaced by the per-market summary table).

## Failure recovery and edge cases

| Case | Behavior |
|---|---|
| UK profile | Route to UK W4 adaptation. |
| `< 2` or `> 6` ZIPs supplied | Halt at pre-check. |
| Free-form YMMT casing | Run Wave A facet discovery once. |
| Facet discovery 0 results in primary ZIP | Halt. |
| One ZIP returns `num_found=0` | Render that row as `(empty)`; exclude from `lowest_market` / `highest_market` selection; emit Key Signal noting the empty market. |
| All ZIPs return `num_found=0` | Render the empty-state header (`Headline: no listings in any market`) and stop. |
| Thin market — `num_found < session.min_comp_count` for some ZIP | Render with a "Low-confidence-for-this-market" footnote; the median is still shown but flagged. |
| `get_sold_summary` `make_model_not_found` | Retry once with facet-discovered casing; if still failing, omit State Baseline; emit DQ event (a). |
| `get_sold_summary` other failure | Skip State Baseline; emit DQ event (a). Do NOT halt the workflow. |
| Truncation envelope on any call | Standard `Write` + `--file` recovery per `references/truncation-recovery.md`. |
| Missing `profile.location.state` on US | Use the state of the first ZIP for the `get_sold_summary` call; emit DQ event (g) noting the substitution. |
