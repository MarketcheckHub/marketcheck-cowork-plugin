# W1 — Full Comparable Appraisal

Reference workflow. Triggers on "appraise this vehicle", "what's it worth", "fair market value", "appraisal report", "insurance total-loss value", "insurance claim value", "estate valuation", "defensible valuation", etc.

**Required inputs:** VIN (17 chars) or YMMT. Mileage (halt if missing — do not fall back to the predictor's 50000 default). Vehicle condition (`Clean` / `Average` / `Rough`; recommended; if missing, treat as `Average` and surface a Key Signal noting the assumption). Purpose (`Trade-in` / `Retail` / `Insurance` / `Wholesale`; recommended; if missing, use `session.purpose_default` derived from `appraiser.specialization` per `scripts/load_profile.py`).

**YMMT-only branch (no VIN):** when the user supplies `{year, make, model, trim}` without a VIN on a US profile — **skip steps 1 and 2 entirely** (no decode, no ML prediction — `predict_price_with_comparables` requires a VIN). Begin at step 4 using the user-supplied YMMT (run facet discovery first per `references/facet-discovery.md`). Anchor on sold-90d median when `sold_count_90d ≥ 5`; else fall back to active quartile median. **In the output: skip the Predicted Prices block; render only the active + sold-anchored sections.** CPO detection still works via active-listing `is_certified`, so the CPO branch can still run if the user confirms CPO status.

## Parallelization (W1)

W1 executes in three parallel waves under the universal wave contract (see SKILL.md). The specific calls per wave:

### Wave A — Immediate (no cross-dependencies)

Launched once user inputs (VIN, miles, condition, purpose, CPO-stated) + profile (ZIP) are in hand. Up to 5 calls in parallel:

- `decode_vin_neovin(vin)`
- `predict_price_with_comparables(vin, miles, zip, dealer_type="franchise")`
- `predict_price_with_comparables(vin, miles, zip, dealer_type="independent")`
- `predict_price_with_comparables(vin, miles, zip, dealer_type="franchise", is_certified=true)` — **only if the user stated CPO before MCP calls began**
- `predict_price_with_comparables(vin, miles, zip, dealer_type="independent", is_certified=true)` — same

The appraiser plugin is channel-neutral: both franchise and independent predicts always fire. The franchise predicted price is the retail benchmark; the independent predicted price is the wholesale-proxy.

### Wave B — After Wave A decode returns (uses cached YMMT)

All 8 calls run in parallel, using `{year, make, model, trim}` from `parse_decode.py`:

- `search_active_cars` asc (rows=20, stats="price,miles", include_dealer_object=true, include_build_object=true, price_range="1-*")
- `search_active_cars` desc (rows=10, price_range="1-*", include_dealer_object=true, include_build_object=true) — **issued optimistically**
- `search_active_cars` price_change="negative", rows=0 (all shaping knobs off)
- `search_past_90_days` stats="price" rows=0
- `search_past_90_days` stats="miles" rows=0
- `search_past_90_days` stats="dom_active" rows=0
- `search_past_90_days` (sold listings for the Sold Transaction Comparables table) `sort_by="last_seen", sort_order="desc", rows=10, sold=true, include_dealer_object=true, include_build_object=true, price_range="1-*"`
- `get_sold_summary` (state-level, dates from `scripts/compute_sold_summary_dates.py`)

### Wave C — Conditional (rare)

Issued only when Wave B results trigger a branch:

- **CPO-ambiguous path**: when user did NOT state CPO AND Wave B's asc response has a shadow listing with `is_certified=1` → issue `get_car_history(vin, fields=parse_history.CANONICAL_FIELDS_PARAM)` (if not yet called) + 2 more predict calls with `is_certified=true`.
- **Thin-market auto-widen**: when `asc.num_found < session.min_comp_count`, re-issue asc + desc at `radius=min(radius_mi_clamped * 1.5, 150)`. Emit DQ event (g) acknowledging the widen.
- **Facet-discovery retry**: when `asc.num_found == 0`, run facet-discovery per `references/facet-discovery.md` and retry the failed call once.

### Wall-clock budget (W1)

Wave A ≈ 12–15s · Wave B ≈ 12–15s · Wave C usually skipped. Total MCP roundtrip ≈ 27–30s for the common path.

## Steps

1. **Decode the VIN.**

   ```
   decode_vin_neovin(vin=<VIN>)
   → scripts/parse_decode.py --file <saved-response-path>
   ```

   `decode_vin_neovin` responses chronically truncate. Pipe through `parse_decode.py --file`. On `ok=false`, halt and ask for a valid VIN or YMMT. On `ok=true`, cache `specs.{year, make, model, trim, body_type, drivetrain, engine, transmission, msrp}` for the session. Confirm the decoded specs back to the user before proceeding.

   **Subject `car_type` derivation:** from the decoded year + MSRP signal. A current-or-next-model-year VIN with `msrp` populated and miles ≤ 2,000 is treated as `new`; everything else is `used`. The derivation is overridden by an explicit user statement ("appraising a new XC90 demo") at any point.

2. **Dual ML prediction.**

   ```
   predict_price_with_comparables × 2 (franchise then independent):
     franchise:   vin, miles=<U>, zip=<profile>, dealer_type=franchise
     independent: same params, dealer_type=independent
   → scripts/parse_predict.py --file <saved-response-path>  (per call)
   ```

   `predict_price_with_comparables` responses chronically truncate. Pipe each saved response through `parse_predict.py --file`. The parser unwraps and extracts `marketcheck_price`, `comparables.{num_found, stats.price}`, `recent_comparables.{num_found, stats.price}` per call.

3. **CPO branch — gate + call shape** (see `references/cpo.md` for the full detection decision tree).

   Decision tree summary: user-stated → confirmed; purpose-sensitive (Insurance/Estate) + CPO-eligible subject + silence → prompt; shadow listing post-hoc → confirmed; `get_car_history.cpo_ever` → final fallback. CPO branch fires 2 additional predict calls. Premium = CPO predict − Non-CPO predict (per channel); no Net Margin or Certification Cost line — appraisers don't certify.

4. **Active comp set — asc pull (bottom of market).**

   > **‼️ Pipeline-bypass warning — read before issuing the asc call.**
   >
   > Use the prescribed Write-tool recipe (mirror of `references/truncation-recovery.md`):
   >
   > ```
   > Write(file_path="/tmp/marketcheck/<session.run_id>/asc.json", content="<full envelope-wrapped response>")
   > parse_search.py --file /tmp/marketcheck/<session.run_id>/asc.json --subject-vin <VIN>
   > ```

   ```
   search_active_cars:
     year, make, model, trim                (verbatim from cached specs)
     zip, radius=<session.radius_mi_clamped>, car_type=<derived>
     sort_by="price", sort_order="asc"
     price_range="1-*", rows=20
     stats="price,miles"
     include_dealer_object=true
     include_build_object=true
     (fetch_all_photos / include_mc_dealership_object /
      include_finance / include_lease / include_relevant_links = false)
   → parse_search.py:
       --subject-vin <subject VIN>
   ```

   On `num_found == 0`, run a facet-discovery retry per `references/facet-discovery.md`. On still-zero, the appraisal degrades to `anchor_source = "predict_only"` (when ML available) or `null` (thin market block).

5. **Active comp set — asymmetric desc pull (tail coverage).**

   Issued optimistically in Wave B alongside the asc pull.

   ```
   search_active_cars (same base filters as asc):
     sort_by="price", sort_order="desc", rows=10
     price_range="1-*"
     include_dealer_object=true, include_build_object=true
   → parse_search.py --subject-vin <subject VIN>
   ```

   Persist the desc response via the Write recipe. Then combine the asc + desc rows into a single comp set (dedup by VIN, preserve server stats from the asc call).

6. **Price-drop velocity (market-wide).**

   ```
   search_active_cars:
     same base filters + price_change="negative"
     rows=0
     include_dealer_object=false, include_build_object=false
   → parse_search.py
   ```

7. **Sold-90-day aggregates — three single-field stats calls.**

   ```
   search_past_90_days × 3:
     base: year, make, model, trim (verbatim), zip, radius, car_type, rows=0,
           price_range="1-*", sold=true
     a. stats="price"        → stats.price.{min,max,mean,median} + num_found
     b. stats="miles"        → stats.miles.*
     c. stats="dom_active"   → stats.dom_active.*  (PRIMARY)
        stats="dom"          → stats.dom.*         (FALLBACK)
   ```

   Use the same `{year, make, model, trim, car_type, zip, radius}` as step 4. With `sold=true + price_range="1-*"`, every matched record has `price ≥ 1` and is sold-classified.

8. **Sold transaction comparables — the appraisal evidence table.**

   ```
   search_past_90_days:
     year, make, model, trim, zip, radius, car_type           # matches steps 4 & 7
     sold=true, price_range="1-*"
     sort_by="last_seen", sort_order="desc"
     rows=10
     include_dealer_object=true, include_build_object=true
     (other shaping knobs off)
   → parse_search.py --subject-vin <VIN>
   ```

   For a new-vehicle appraisal subject, sold-90d transactions are typically thin or empty — the endpoint indexes expired/sold dealer listings, and new-vehicle inventory rarely flows through this channel. When `num_found == 0` on a new-vehicle appraisal, the renderer surfaces the new-vehicle-specific footnote per `assets/output-template.md §Sold Transaction Comparables` rather than the generic `unavailable` fallback.

   The 10 rows feed the **Sold Transaction Comparables** block — the strongest evidence in any appraisal because every row is a real transaction. The rendered table is sorted descending by `last_seen_at_date` (most recent sales first).

9. **State sold velocity** (see `references/sold-summary-safety.md`).

   ```
   get_sold_summary:
     make, model                            (verbatim)
     inventory_type="Used"                  (or "New" if subject car_type=new)
     state=<profile.location.state>         (required for US; halt-and-ask if missing)
     summary_by="state"
     ranking_measure="average_days_on_market"
     ranking_dimensions="make,model"
     top_n=5, limit=5000
     date_from / date_to — computed by `scripts/compute_sold_summary_dates.py`
   → scripts/parse_sold_summary.py --aggregate-state <profile.location.state>
   ```

   **Do NOT pass `dealer_type`** per `references/sold-summary-safety.md` — combining narrow make/model/state filters with `dealer_type` returns silently empty results.

   **Use `compute_sold_summary_dates.py`** for month-aligned dates.

   On parser `ok=false`, branch on `error_type` per the table in `references/sold-summary-safety.md`. Never halt the whole workflow for State Baseline failure.

10. **Compute the appraisal band.**

    Read the parsed outputs from steps 2–9 and apply the anchor decision tree:

    ```
    if sold_90d.num_found >= 5:
        anchor_source = "sold_90d"
        anchor_value  = sold_90d.stats.price.median
    elif asc_active.kept_count >= session.min_comp_count:
        anchor_source = "active_comps"
        anchor_value  = asc_active.stats.price.median       # server-computed
    elif marketcheck_price_franchise is not None:
        anchor_source = "predict_only"
        anchor_value  = marketcheck_price_franchise
    else:
        anchor_source = "null"
        anchor_value  = None
    ```

    The low / mid / high tuple is then bracketed around the anchor:

    ```
    if anchor_source == "sold_90d":
        low, mid, high = sold_90d.stats.price.p25, anchor_value, sold_90d.stats.price.p75
    elif anchor_source == "active_comps":
        low, mid, high = asc_active.stats.price.p25, anchor_value, asc_active.stats.price.p75
    elif anchor_source == "predict_only":
        # ±7% bracket on the predict, widened to ±10% for Low confidence
        low  = anchor_value * 0.93
        high = anchor_value * 1.07
        mid  = anchor_value
    else:
        low = mid = high = None
    ```

    Then apply condition + purpose adjustments to the bracket:

    ```
    if condition == "Clean":   shift_pct = +0.025
    if condition == "Rough":   shift_pct = -0.045
    if condition == "Average": shift_pct =  0.0

    # Purpose biases the rendered range within the bracket:
    if purpose == "Insurance":   bias_to = "high"   # defensible high-floor
    if purpose == "Trade-in":    bias_to = "low"    # negotiating floor
    if purpose == "Wholesale":   bias_to = "low"    # auction floor
    if purpose == "Retail":      bias_to = "mid"    # fair-market center (estate / general)
    ```

    Confidence band:

    ```
    comp_count_total = asc_active.kept_count + sold_90d.num_found
    if comp_count_total >= 15:   confidence = "High"
    elif comp_count_total >= 5:  confidence = "Medium"
    else:                        confidence = "Low"
    ```

    **Low-confidence appraisals MUST render a range, not a point estimate.** This is the non-negotiable defensibility guard.

11. **Render.**

    Read `assets/output-template.md` into context — it is the single source of truth for block structure, table schemas, and self-check.

    Block order for W1:
    1. Vehicle Identification (decoded specs + user inputs)
    2. Headline (`<purpose>-anchored value range $<low>–$<high> (mid $<mid>); <confidence> confidence (<comp_count_total> total comps); Anchor: <anchor>`)
    3. Market Snapshot (incl. State Baseline + scope note + drop rates)
    4. Price Distribution (server-source over the comp set)
    5. Active Mileage Distribution
    6. DOM Distribution (using static defaults: fresh ≤30d / aging 31–60d / stale 61+d)
    7. Predicted Prices (ML — MarketCheck) — read both franchise + independent verbatim
    8. CPO Premium (when applicable)
    9. **Recommended Value (condition-adjusted)** — low / mid / high band
    10. Active Retail Comparables (8-col standard table)
    11. **Sold Transaction Comparables** (8-col schema with Sale Date + CPO?)
    12. Outliers (optional — `|price - mean| > 2σ` rows)
    13. Methodology Notes
    14. Caveats (purpose-specific)
    15. Data Quality Notes (when non-empty)
    16. Key Signals (3–5 bullets including any sold-vs-active disagreement, missing-condition flag, MoS alert)
    17. Self-check footer

## Failure recovery

| Case | Behavior |
|---|---|
| Decode `ok=false` | Halt and ask for valid VIN or YMMT. |
| Predict `ok=false` (one channel) | Render that channel's MarketCheck Price as `unavailable (<error_type>)`; continue. |
| All 4 predicts `ok=false` | Skip Predicted Prices + CPO Premium blocks; appraisal proceeds on comp-set + sold-90d evidence; emit DQ event (a). |
| Search `num_found = 0` on asc | Run facet-discovery retry once. Still 0 → degrade to `anchor_source="predict_only"` if ML available, else thin-market block. |
| Search `num_found < session.min_comp_count` | Insufficient comp set; appraisal band falls to `predict_only` anchor when ML available; render thin-market caveat + Low confidence. |
| Sold-90d call all degraded | `sold_count_90d=0, sold_median=None`; band falls to `active_comps`; emit DQ event (a). |
| Sold transaction table call (step 8) `ok=false` | Render the table as `(unavailable — sold-90d call truncated/errored)`; appraisal still renders. |
| `get_sold_summary` degraded | Skip State Baseline section; emit DQ event (a). Never halt. |
| Truncation envelope | Standard `Write` + `--file` recovery per `references/truncation-recovery.md`. |
| Subject VIN found in comp set (shadow) | `parse_search` excludes; emit DQ event (c) with shadow-dealer details. |
| Missing `profile.location.state` on US | Halt-and-ask for state before issuing step 9; the rest of the workflow can still proceed without it (State Baseline becomes a DQ event). |
