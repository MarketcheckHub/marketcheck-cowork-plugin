# W3 — Wholesale-vs-Retail Spread

Triggered by "wholesale vs retail", "what's the spread", "trade-in offer range", "how should I price this trade", "franchise vs independent", etc. **Single-VIN channel spread analysis** — emphasises the gap between franchise and independent dealer pricing as a proxy for the wholesale-to-retail margin, and emits a recommended trade-in offer range positioned within that spread.

W3 is **US-only by canonical path** — `dealer_type` is not exposed on the UK active-listing surface (per `mcp_server_tool_docs/search_uk_active_cars.md`), so the spread cannot be computed on UK profiles. Halt on UK with the canonical message in `references/country-uk.md`.

W3 is also **used-subject-only**. New vehicles sell at MSRP-anchored prices (no franchise-vs-independent retail spread exists), and independent dealers cannot legally sell new vehicles of franchised brands — the entire wholesale-to-retail spread concept and the 78-85% rule-of-thumb margin are Used-car semantics.

## Required inputs

- **VIN** (mandatory; 17 chars).
- **Mileage** (mandatory).
- **Asking price** is OPTIONAL — when supplied, the spread analysis includes a "your-price-vs-market" gap; when omitted, the workflow renders the spread + recommended offer range without the subject-comparison line.
- **Condition** (recommended).
- **Purpose** (recommended; defaults to `Trade-in` for W3 since the spread + offer math is fundamentally a trade-in question — overrides `session.purpose_default`).
- **Recon cost** (optional user input — appraiser profile does not carry it). Used to gross up the recommended trade-in offer when the user wants the post-recon floor protected.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | *"Wholesale-vs-Retail Spread workflow is US-only — `dealer_type` is not exposed on the UK active surface (per `mcp_server_tool_docs/search_uk_active_cars.md`)."* |
| `profile.location.country` not US | Halt per SKILL.md country routing. |
| **Subject is a new vehicle** — decoded current-or-next-model-year + `msrp` populated + miles ≤ 2,000, OR user-stated "appraising a new car" | *"Wholesale-vs-Retail Spread is a used-vehicle workflow. New vehicles sell at MSRP-anchored prices (no franchise-vs-independent retail spread exists), and independent dealers cannot legally sell new vehicles of franchised brands. For new-vehicle pricing, run W1 (`/full-appraisal`)."* |
| VIN malformed | *"VIN is malformed (must be 17 chars, no I/O/Q). Halt — please correct and re-run."* |
| Mileage missing | Halt with the standard predict-fallback warning. |

## Parallelization (W3)

W3 executes in **two waves**.

**Wall-clock budget:** Wave A ≈ 12-15s, Wave B ≈ 12-15s, total ≈ 25-30s.

## Wave A — Decode + dual-channel ML predict (mirror of W1 Wave A)

Identical to W1 Wave A. Up to 5 calls in parallel:

- `decode_vin_neovin(vin)`
- `predict_price_with_comparables(vin, miles, zip, dealer_type="franchise")` → role: `nocpo_franchise`
- `predict_price_with_comparables(vin, miles, zip, dealer_type="independent")` → role: `nocpo_independent`
- `predict_price_with_comparables(vin, miles, zip, dealer_type="franchise", is_certified=true)` — when CPO confirmed → role: `cpo_franchise`
- `predict_price_with_comparables(vin, miles, zip, dealer_type="independent", is_certified=true)` — when CPO confirmed → role: `cpo_independent`

**Subject `car_type` derivation**: from decoded year + MSRP signal. Used vehicles only — if the derivation yields `new`, halt per pre-check.

## Wave B — Channel-split active comp pulls + sold evidence

All calls fire in parallel:

```
search_active_cars (FRANCHISE listings):
  year, make, model, trim, zip, radius=<session.radius_mi_clamped>, car_type="used"
  dealer_type="franchise"
  sort_by="price", sort_order="asc"
  price_range="1-*"
  rows=10
  stats="price"
  include_dealer_object=true, include_build_object=true
  (other shaping knobs off)
→ parse_search.py --file <persisted-path>

search_active_cars (INDEPENDENT listings):
  same base + dealer_type="independent"
→ parse_search.py --file <persisted-path>

search_past_90_days (sold-90d trim median for the value floor):
  year, make, model, trim, zip, radius, car_type="used"
  rows=0, stats="price", price_range="1-*", sold=true
  (NO dealer_type — per references/sold-summary-safety.md the dealer_type filter
   suppresses valid data when combined with narrow make/model/state filters)
→ parse_search.py --file

search_past_90_days (sold transactions table — last 10 sold listings):
  year, make, model, trim, zip, radius, car_type="used"
  sold=true, price_range="1-*"
  sort_by="last_seen", sort_order="desc"
  rows=10
  include_dealer_object=true, include_build_object=true
→ parse_search.py --file

get_sold_summary (state baseline; same shape as W1 step 9):
  make, model, inventory_type="Used", state=<profile.location.state>,
  summary_by="state", ranking_measure="average_days_on_market",
  ranking_dimensions="make,model", top_n=5, limit=5000,
  date_from/date_to from compute_sold_summary_dates.py.
  NEVER pass dealer_type.
→ parse_sold_summary.py --aggregate-state <STATE>
```

5 calls in Wave B.

## Pipeline (post-waves)

The W3 pipeline mirrors W1's, plus the channel-split comp tables (franchise vs independent rendered separately rather than merged).

## W3 spread + offer-range computation

Computed at render time (pure scalar arithmetic over fields the pipeline already emits):

```
predicted_retail    = nocpo_franchise.marketcheck_price       (franchise predicted)
predicted_wholesale = nocpo_independent.marketcheck_price     (independent predicted)
spread_$            = predicted_retail - predicted_wholesale
spread_pct          = spread_$ / predicted_retail * 100

# Default offer range (Trade-in / Wholesale purpose): 78-85% of predicted_retail
offer_low_default  = 0.78 * predicted_retail
offer_high_default = 0.85 * predicted_retail

# Purpose-biased adjustment:
#   Trade-in / Wholesale → use the default 78-85%
#   Insurance → bias toward sold-90d median (a more defensible insurance value):
#     offer_low  = max(0.78 * predicted_retail, sold_median - 5%)  if sold_median present
#     offer_high = min(0.85 * predicted_retail, sold_median + 5%)
#   Retail (estate / general / fair-market value) → bias toward midpoint:
#     offer_low  = predicted_wholesale
#     offer_high = (predicted_wholesale + 0.85*predicted_retail) / 2

# Recon cost grossing-up (when recon_cost is supplied):
#   The offer range above is BEFORE recon. Subtract recon_cost from offer_low to
#   show the post-recon floor:
#     offer_low_post_recon = offer_low - recon_cost
```

When franchise OR independent predicted roles are missing (predict ok=false), the spread and offer range degrade to `unavailable (predict role degraded)` and the renderer points the user at W1 for the comp-anchored fallback. **Never** synthesize a spread from active comp medians — the channel medians from the dedicated franchise + independent search calls are inputs to the renderer's per-channel comp tables, but they're sample-limited (rows=10 each) and noisy compared to the server-wide ML predict.

## Output rendering

W3 renders via `assets/output-template.md` with these block additions / variations:

Block list for W3 (in render order):
1. **Vehicle Identification**
2. **Headline** — `Wholesale-to-retail spread $<spread_$> (<spread_pct>%); recommended trade-in offer $<offer_low>–$<offer_high>; <confidence> confidence (<comp_count_total> total comps).`
3. **Market Snapshot** + State Baseline
4. **Price Distribution** + **Mileage Distribution** + **DOM Distribution** (over the merged franchise+independent comp set)
5. **Predicted Prices (ML — MarketCheck)** — Franchise + Independent (+ CPO when applicable)
6. **CPO Premium** (when applicable) — `+$<premium>  (<pct>%)` per channel, no Net Margin line
7. **Recommended Value (condition-adjusted)**
8. **Wholesale-vs-Retail Spread + Recommended Trade-In Offer** — the W3 punchline block. Renders the spread $/% line, the offer range (default and post-recon when applicable), and a one-line note explaining the purpose-biased adjustment.
9. **Active Retail Comparables (Franchise)** — 8-col standard table over the franchise-only listings.
10. **Active Retail Comparables (Independent)** — 8-col standard table over the independent-only listings.
11. **Sold Transaction Comparables** — 8-col schema (Dealer | Type | Sold Price | Miles | DOM | Distance | Sale Date | CPO?).
12. **Outliers** (optional).
13. **Methodology Notes** — appraisal band notes + spread methodology + recon adjustment when applicable.
14. **Caveats** (purpose-aware).
15. **Data Quality Notes** (when non-empty).
16. **Key Signals** — at least one bullet calling out which channel is more representative for this segment.
17. **Self-check footer**.

## Failure recovery and edge cases

| Case | Behavior |
|---|---|
| UK profile | Halt at pre-check. |
| New-vehicle subject | Halt at pre-check; route to W1. |
| Decode `ok=false` | Halt the workflow. |
| Both franchise + independent predicts `ok=false` | Spread block renders `unavailable`; render the rest of the appraisal (sold-anchor / active-quartile fallback); emit Key Signal directing to W1. |
| One channel's predict `ok=false` | Render the surviving channel; spread block renders `unavailable (one channel degraded)`; emit DQ event (a). |
| Franchise listings call `num_found=0` | Render `(empty)` for the franchise table; flag in Key Signals (e.g. "no franchise listings within radius — this is an independent-only segment"). |
| Independent listings call `num_found=0` | Mirror — render `(empty)` for the independent table. |
| Sold-90d call degraded | Skip the sold-anchor; band falls to `active_comps`; emit DQ event. |
| `get_sold_summary` degraded | Skip State Baseline; emit DQ event. |
| Asking price absent | Skip the "your price vs spread" line; render the rest. |
| Recon cost absent | Skip the post-recon offer-low line; render the default offer range only. |
| Missing `profile.location.state` | Halt-and-ask for state before issuing the `get_sold_summary` call; the spread analysis can still render without State Baseline. |
