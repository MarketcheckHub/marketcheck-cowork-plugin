# W1 — Full Comparable Appraisal

Reference workflow. Triggers on "appraise this vehicle", "what's it worth", "fair market value", "appraisal report", "insurance total-loss value", "insurance claim value", "defensible valuation", etc.

**Required inputs:** VIN (17 chars) or YMMT. Mileage (halt if missing — do not fall back to the predictor's 50000 default). Vehicle condition (`Clean` / `Average` / `Rough`; recommended; if missing, treat as `Average` and surface a Key Signal noting the assumption). Purpose (`Trade-in` / `Retail` / `Insurance` / `Wholesale`; recommended; if missing, treat as `Retail`).

**YMMT-only branch (no VIN):** when the user supplies `{year, make, model, trim}` without a VIN on a US profile — **skip steps 1 and 2 entirely** (no decode, no ML prediction — `predict_price_with_comparables` requires a VIN). Begin at step 4 using the user-supplied YMMT (run facet discovery first per `references/facet-discovery.md`). Anchor on sold-90d median when `sold_count_90d ≥ 5`; else fall back to active quartile median. **In the output: skip the Predicted Prices block; render only the active + sold-anchored sections.** CPO detection still works via active-listing `is_certified`, so the CPO branch can still run if the user confirms CPO status.

## Parallelization (W1)

W1 executes in three parallel waves under the universal wave contract (see SKILL.md). The specific calls per wave:

### Wave A — Immediate (no cross-dependencies)

Launched once user inputs (VIN, miles, condition, purpose, CPO-stated) + profile (ZIP, dealer_type) are in hand. Up to 5 calls in parallel:

- `decode_vin_neovin(vin)`
- `predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_lower>)`
- `predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_opposite_lower>)`
- `predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_lower>, is_certified=true)` — **only if the user stated CPO before MCP calls began**
- `predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_opposite_lower>, is_certified=true)` — same

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
- **Thin-market auto-widen**: when `asc.num_found < 15` AND subject is premium (`subject_msrp > 50000`), re-issue asc + desc at `radius=min(radius_mi_clamped * 1.5, 100)`. Emit DQ event (g) acknowledging the dealer-preference override.
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

2. **Dual ML prediction.**

   ```
   predict_price_with_comparables × 2 (PRIMARY then CONTEXT):
     primary:  vin, miles=<U>, zip=<profile>, dealer_type=<dealer_type_lower>
     context: same params, dealer_type=<dealer_type_opposite_lower>
   → scripts/parse_predict.py --file <saved-response-path>  (per call)
   ```

   `predict_price_with_comparables` responses chronically truncate. Pipe each saved response through `parse_predict.py --file`. The parser unwraps and extracts `marketcheck_price`, `comparables.{num_found, stats.price}`, `recent_comparables.{num_found, stats.price}` per role.

3. **CPO branch — gate + call shape** (see `references/cpo.md` for the full detection decision tree).

   Decision tree summary: user-stated → confirmed; profile.cpo_program=true + silent → prompt; shadow listing post-hoc → confirmed; get_car_history cpo_ever → final fallback. CPO branch fires 2 additional predict calls. Premium computed deterministically by `comp_stats.py`'s `marketcheck_predict` block (see `references/cpo.md`).

4. **Active comp set — asc pull (bottom of market).**

   > **‼️ Pipeline-bypass warning — read before issuing the asc call.**
   >
   > Use the prescribed Write-tool recipe (mirror of `references/truncation-recovery.md` lines 66–77):
   >
   > ```
   > Write(file_path="/tmp/marketcheck/<session.run_id>/asc.json", content="<full envelope-wrapped response>")
   > parse_search.py --file /tmp/marketcheck/<session.run_id>/asc.json --subject-vin <VIN>
   > ```

   ```
   search_active_cars:
     year, make, model, trim                (verbatim from cached specs)
     zip, radius=<session.radius_mi_clamped>, car_type=<session>
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

   Persist the desc response via the Write recipe. Then merge:

   ```
   scripts/merge_comps.py \
     --asc <path-to-parse_search-asc-output> \
     --desc <path-to-parse_search-desc-output> \
     --subject-vin <subject VIN>
   ```

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

   Use the same `{year, make, model, trim, car_type, zip, radius}` as step 4 — MoS numerator and denominator must match. With `sold=true + price_range="1-*"`, every matched record has `price ≥ 1` and is sold-classified.

8. **Sold transaction comparables — the appraisal evidence table.**

   ```
   search_past_90_days:
     year, make, model, trim, zip, radius, car_type           # follows session — matches step 7 above and step 9 below (consistent appraisal-subject inventory type)
     sold=true, price_range="1-*"
     sort_by="last_seen", sort_order="desc"
     rows=10
     include_dealer_object=true, include_build_object=true
     (other shaping knobs off)
   → parse_search.py --subject-vin <VIN>
   ```

   `car_type` follows session (matches step 7 above and step 9 below — the appraisal subject's inventory type drives all three sold-90d calls). For a new-vehicle appraisal subject, sold-90d transactions are typically thin or empty — the endpoint indexes expired/sold dealer listings, and new-vehicle inventory rarely flows through this channel. When `num_found == 0` on a new-vehicle appraisal, the renderer surfaces the new-vehicle-specific footnote per `assets/output-template.md §Sold Transaction Comparables` rather than the generic `unavailable` fallback.

   The 10 rows feed `render_sold_table.py` to render the **Sold Transaction Comparables** block — the strongest evidence in any appraisal because every row is a real transaction. The rendered table is sorted descending by `last_seen_at_date` (most recent sales first).

9. **State sold velocity** (see `references/sold-summary-safety.md`).

   ```
   get_sold_summary:
     make, model                            (verbatim)
     inventory_type="Used"                  (or "New" if car_type=new)
     state=<profile.location.state>         (required)
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

10. **Compute stats.**

    Use `scripts/build_comp_stats_input.py` to assemble the comp_stats stdin from Wave A + Wave B parsed outputs:

    ```
    scripts/build_comp_stats_input.py \
      --profile <load_profile output path> \
      --merged <merge_comps output path> \
      --asc-parsed <parse_search asc output path> \
      --sold-price <parse_search sold-90d stats=price path> \
      --sold-dom <parse_search sold-90d stats=dom_active path> \
      --drops <parse_search price_change=negative path> \
      --user-price <asking-price-or-empty> \
      --user-miles <mileage> \
      --subject-vin <17-char VIN> \
      --subject-cpo true|false \
      --trim-label "<year> <make> <model> <trim>" \
      [--nocpo-primary-parsed <path> --nocpo-context-parsed <path>] \
      [--cpo-primary-parsed <path>   --cpo-context-parsed <path>] \
    | scripts/comp_stats.py
    ```

    **Note: `--user-price` is OPTIONAL for W1.** When the appraisal is being run as a "what's it worth" inquiry without a competing asking price, omit `--user-price`. The renderer skips the verdict-style "vs market" gap line and renders only the appraisal value-band block.

11. **Compute the appraisal band.**

    ```
    echo '{"comp_stats": <comp_stats output>, "condition": "<Clean|Average|Rough>", "purpose": "<Trade-in|Retail|Insurance|Wholesale>"}' \
      | scripts/compute_appraisal_band.py
    ```

    The script picks the anchor (sold_90d / active_comps / predict_only / null), bucketed confidence (Low/Medium/High), and condition adjustment. See `compute_appraisal_band.py` module docstring for the full decision tree.

12. **Render.**

    Read `assets/output-template.md` into context — it is the single source of truth for block structure, table schemas, and self-check.

    Block order for W1:
    1. Vehicle Identification (decoded specs + user inputs)
    2. Headline (`<purpose>-anchored value range $<low>–$<high> (mid $<mid>); <confidence> confidence (<comp_count_total> total comps); Anchor: <anchor>`)
    3. Market Snapshot (incl. State Baseline + scope note + drop rates)
    4. Price Distribution (server-source over `quartile.n`)
    5. Active Mileage Distribution
    6. DOM Distribution
    7. Predicted Prices (ML — MarketCheck) — read `marketcheck_predict` block verbatim
    8. CPO Premium (when applicable)
    9. **Recommended Value (condition-adjusted)** — render via `render_appraisal_value_band.py`
    10. Active Retail Comparables (8-col via `render_comp_set_table.py`)
    11. **Sold Transaction Comparables** (8-col via `render_sold_table.py`)
    12. Same-Channel View (when applicable)
    13. Outliers (optional)
    14. Methodology Notes (read from `compute_appraisal_band.py` output `methodology_notes` array verbatim)
    15. Caveats
    16. Data Quality Notes (when non-empty)
    17. Key Signals (3-5 bullets including any sold-vs-active disagreement, mileage moat, MoS alert, missing-condition / missing-purpose flags)
    18. Self-check footer

## Failure recovery

| Case | Behavior |
|---|---|
| Decode `ok=false` | Halt and ask for valid VIN or YMMT. |
| Predict `ok=false` (one role) | Render that role's MarketCheck Price as `unavailable (<error_type>)`; continue. |
| All 4 predicts `ok=false` | Skip Predicted Prices + CPO Premium blocks; appraisal proceeds on comp-set + sold-90d evidence; emit DQ event (a). |
| Search `num_found = 0` on asc | Run facet-discovery retry once. Still 0 → degrade to `anchor_source="predict_only"` if ML available, else thin-market block. |
| Search `num_found < 6` (insufficient) | `comp_stats.insufficient = True`; appraisal band falls to `predict_only` anchor; render thin-market caveat + Low confidence. |
| Sold-90d call all degraded | `sold_count_90d=0, sold_median=None`; band falls to `active_comps`; emit DQ event (a). |
| Sold transaction table call (step 8) `ok=false` | Render the table as `(unavailable — sold-90d call truncated/errored)`; appraisal still renders (the stats-only sold calls in step 7 may have succeeded independently). |
| `get_sold_summary` degraded | Skip State Baseline section; emit DQ event (a). Never halt. |
| Truncation envelope | Standard `Write` + `--file` recovery per `references/truncation-recovery.md`. |
| Subject VIN found in comp set (shadow) | parse_search excludes; emit DQ event (c) with shadow-dealer details. |
