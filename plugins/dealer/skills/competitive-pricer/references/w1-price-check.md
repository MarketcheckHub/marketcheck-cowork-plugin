# W1 — Price-Check Single VIN

Reference workflow. Triggers on "price this VIN", "am I priced right on this one", "check this unit's pricing", etc.

**Required inputs:** VIN (17 chars) or YMMT. Mileage (halt if missing — do not fall back to the predictor's 50000 default). Asking price (recommended; verdict still renders without it but percentile rank is `null`).

**YMMT-only branch (no VIN):** when the user supplies `{year, make, model, trim}` without a VIN on a US profile — **skip steps 1 and 2 entirely** (no decode, no ML prediction — `predict_price_with_comparables` requires a VIN). Begin at step 4 using the user-supplied YMMT (run facet discovery first per the Facet discipline section, since user-typed YMMT is not trusted-casing). Anchor on sold-90d median when `sold_count_90d ≥ 5`; else fall back to active quartile median. **In the output: skip the Franchise MarketCheck Price and Independent MarketCheck Price lines in Price Position; render `Anchor: <sold-90d median>` instead; and emit a caveat line "No MarketCheck Price prediction available — anchored on comp medians" in Key Signals.** CPO detection still works via active-listing `is_certified` and `get_car_history`, so the CPO branch (step 3) can still run if the user confirms CPO status.

## Parallelization (W1)

W1 executes in three parallel waves under the universal wave contract (see SKILL.md). The specific calls per wave:

### Wave A — Immediate (no cross-dependencies)

Launched once user inputs (VIN, miles, asking price, CPO-stated) + profile (ZIP, dealer_type) are in hand. Up to 5 calls in parallel:

- `decode_vin_neovin(vin)`
- `predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_lower>)`
- `predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_opposite_lower>)`
- `predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_lower>, is_certified=true)` — **only if the user stated CPO before MCP calls began**
- `predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_opposite_lower>, is_certified=true)` — same

Each predict call takes `vin` directly; none require decode output. The 4 predicts + decode run concurrently. When the user did NOT state CPO, the two CPO predicts defer to Wave C.

### Wave B — After Wave A decode returns (uses cached YMMT)

All 7 calls run in parallel, using `{year, make, model, trim}` from `parse_decode.py`:

- `search_active_cars` asc (rows=20, stats="price,miles", include_dealer_object=true, include_build_object=true, price_range="1-*")
- `search_active_cars` desc (rows=10, price_range="1-*", include_dealer_object=true, include_build_object=true) — **issued optimistically**. When `asc.num_found ≤ 20` the desc rows duplicate asc rows and dedupe cleanly in `merge_comps.py` for a 1-call cost; when `> 20` it provides the tail coverage. Never serialize this decision.
- `search_active_cars` price_change="negative", rows=0 (all shaping knobs off)
- `search_past_90_days` stats="price" rows=0
- `search_past_90_days` stats="miles" rows=0
- `search_past_90_days` stats="dom" rows=0
- `get_sold_summary` (state-level, dates from `scripts/compute_sold_summary_dates.py`)

### Wave C — Conditional (rare)

Issued only when Wave B results trigger a branch:

- **CPO-ambiguous path**: when the user did NOT state CPO AND Wave B's asc response has a shadow listing with `is_certified=1` (or `get_car_history` surfaces historical CPO), issue `get_car_history(vin, fields="id,vin,price,miles,msrp,seller_name,dealer_id,city,state,zip,first_seen_at_date,last_seen_at_date,scraped_at_date,source,vdp_url,seller_type,inventory_type,is_certified,dom_active,dom_180,dom,stock_no,data_source")` (if not yet called) + 2 more predict calls with `is_certified=true`. The explicit `fields=` is required — without it, `is_certified` is stripped (Optional Field per `mcp_server_tool_docs/get_car_history.md`) and `cpo_ever` returns None, defeating the probe. Mirror the string verbatim from `parse_history.CANONICAL_FIELDS_PARAM`. Parallel within Wave C.
- **Thin-market auto-widen**: when `asc.num_found < 15` AND subject is premium (`user_price > 40000` OR `msrp > 50000`), re-issue asc + desc at `radius=min(radius_mi_clamped * 1.5, 100)`. Emit DQ event (g) acknowledging the dealer-preference override.
- **Facet-discovery retry**: when `asc.num_found == 0`, run facet-discovery per `references/facet-discovery.md` and retry the failed call once.

### Wall-clock budget (W1)

Wave A ≈ 12–15s · Wave B ≈ 12–15s · Wave C usually skipped. Total MCP roundtrip ≈ 27–30s for the common path, vs. ~144s serial.

## Steps

1. **Decode the VIN.**

   ```
   decode_vin_neovin(vin=<VIN>)
   → scripts/parse_decode.py --file <saved-response-path>
   ```

   `decode_vin_neovin` responses chronically truncate (~150KB envelopes observed in practice) — the MCP tool will emit `Error: result (N chars) exceeds maximum allowed tokens. Output has been saved to <path>` on virtually every real call. Pipe the saved envelope path to `parse_decode.py --file`. The parser unwraps the envelope transparently.

   On `ok=false`, halt and ask for a valid VIN or YMMT (echo `error`). On `ok=true`, cache `specs.{year, make, model, trim, body_type, drivetrain, engine, transmission, msrp}` for the session. Confirm the decoded specs back to the user before proceeding.

2. **Dual ML prediction.**

   ```
   predict_price_with_comparables × 2 (PRIMARY then CONTEXT):
     primary:  vin, miles=<U>, zip=<profile>, dealer_type=<dealer_type_lower>
     context: same params, dealer_type=<dealer_type_opposite_lower>
   → scripts/parse_predict.py --file <saved-response-path>  (per call)
   ```

   `predict_price_with_comparables` responses chronically truncate (~100KB envelopes observed) — pipe the saved-response path to `parse_predict.py --file`. The parser unwraps transparently. Response has **no `data` wrapper** — `marketcheck_price, msrp, comparables, recent_comparables` live at top level; `comparables` and `recent_comparables` are each an object `{num_found, listings[], stats}` (not a bare array). Predict listings are **flatter than search listings**: spec metadata (body_type/drivetrain/engine/transmission), dealer_type, and is_certified are absent — so predict comps are NOT used by `channel_stats` or CPO detection (both flow from search comps).

   Extract `marketcheck_price` and **both comparable arrays as distinct universes** — `comparables` (the current active listings the ML used) and `recent_comparables` (a second set the ML surfaced as "recent"). **Empirical live-call result (verified 2026-04-22):** `recent_comparables.listings[*]` fields match active-listing shape (same `price`, `miles`, `dom`, `dealer_*` fields) with NO sold-timestamp (`sold_date` / `sold_at`) and NO realised-price (`sale_price`) fields. Treat `recent_comparables` as "recent comps" — asking-price snapshots, not realised sales. Render both counts in the Price Position block; never label them as "realised prices". Do NOT union them.

3. **CPO branch — gate + call shape** (see `references/cpo.md` for the full detection decision tree).

   **Gate (decide CPO status before issuing predicts):**
   - **User stated CPO before any MCP call** → CPO confirmed; issue the two CPO predicts as part of **Wave A** (alongside the non-CPO pair). No extra roundtrip.
   - **User silent + Wave B's asc pull returns a shadow VIN with `is_certified == 1`** → CPO confirmed post-hoc; issue the two CPO predicts in **Wave C**.
   - **User silent + shadow absent OR shadow `is_certified is None`** → CPO status ambiguous. Either (a) issue `get_car_history(vin)` in Wave C and check `cpo_ever`, OR (b) prompt the user *"Is this unit currently CPO?"* before running the CPO branch. Choice depends on whether a history call was already planned.
   - **User stated NOT CPO** → skip the CPO branch; emit DQ event (g) `"CPO branch skipped: user stated non-CPO"`.

   **Call shape** (per CPO dealer-type pair):

   ```
   predict_price_with_comparables × 2 with is_certified=true,
     one per dealer_type (lower + opposite_lower) → parse_predict.py
   CPO premium = cpo_primary.marketcheck_price − nocpo_primary.marketcheck_price
   ```

   Both CPO Premium and Net Margin from CPO are computed by `comp_stats.py`'s `marketcheck_predict` output (from the four MarketCheck Price values + the dealer's Certification Cost) — the renderer reads that consolidated block rather than hand-computing.

4. **Active comp set — asc pull (bottom of market).**

   > **‼️ Pipeline-bypass warning — read before issuing the asc call.**
   >
   > **All scratch paths are scoped to `<session.run_id>`** — a unique ID auto-assigned by `scripts/load_profile.py` and emitted in the profile's `session` block (see SKILL.md step 6). Concurrent skill flows get distinct `run_id` values, so two simultaneous price-checks never collide on `/tmp/marketcheck/`. Read `session.run_id` from the loaded profile before issuing any `Write`; do NOT hardcode `cpr-run`.
   >
   > The asc / desc / drops / sold-90d responses arrive **inline** (untruncated) in the agent's context as envelope-wrapped JSON. The deterministic pipeline (`parse_search.py` → `merge_comps.py` → `comp_stats.py`) **must** ingest these responses; hand-reasoning over the raw MCP output silently turns deterministic numeric blocks (verdict band, DOM buckets, channel medians, drop count, percentile) into stochastic model output that diverges run-to-run.
   >
   > **Required recipe** (mirror of `references/truncation-recovery.md` lines 66–77):
   >
   > ```
   > # 1. Save the raw MCP response verbatim — Write tool, NOT cat / heredoc / hand-key.
   > Write(file_path="/tmp/marketcheck/<session.run_id>/asc.json", content="<full envelope-wrapped response>")
   >
   > # 2. Parse via --file (the parsers' --file path unwraps the {"result": ...} envelope).
   > parse_search.py --file /tmp/marketcheck/<session.run_id>/asc.json --subject-vin <VIN>
   > ```
   >
   > The Write tool accepts large JSON content directly; envelope unwrap is automatic. **Do not trim, reshape, summarize, or hand-key listings into a custom merge script** — every prior session that took those paths produced silent dedup errors (v4 over-excluded 4 rows; v6 hand-keyed 30 listings into a fabricated `build_merged.py`). Two recent sessions skipped the pipeline entirely and produced a near-inverted DOM distribution and an off-by-one verdict band.
   >
   > If the bypass nonetheless happens (e.g. truncation-recovery already ran and the response is partial), the rendered output **must** prefix the report with `⚠ pipeline bypassed; numeric blocks computed by hand — values may diverge from canonical output` and emit self-check warning #13 (see `assets/output-template.md`).
   >
   > **Rendering bypasses (v1.5.1+; same warning applies).** The pipeline above ends at `comp_stats.py`. The 26-row × 8-col Competitive Set table (spec subtitle + table) is rendered downstream by `scripts/render_comp_set_table.py` — invoke it and copy stdout verbatim into the W1 report. Hand-rolling the table risks the same class of bug as hand-merging: re-implementing parser-supplied calculations during cell rendering. Specifically forbidden:
   >
   > - **Reading raw MCP field names** (`dealer.name`, `dist`). The parser flattens to `dealer_name`, `distance_mi`. See `assets/output-template.md` Parser field map for the complete binding.
   > - **Re-implementing `parse_search.py:96–104`** to compute Price Change. Read `price_change_amount` from the parsed listing — it's pre-computed and handles every edge case (zero `ref_price`, missing `price_change_percent`, sign near zero). One prior session re-implemented this formula and produced a fabricated `−$13,807` figure on a listing whose canonical change was `−$27,807`.
   > - **Hand-keying table rows** from the merged JSON. Use `render_comp_set_table.py`. When the script fails to run, the agent's rendered output **must** prefix the table with `⚠ table renderer bypassed; manual cells may diverge from canonical formatting` and emit self-check warning #14. Do NOT silently hand-roll cells.
   >
   > The same logic extends to other rendered blocks (Headline, Market Snapshot, Distributions, Your Price Position, Same-Channel View, Outliers, Key Signals, Verdict): **never re-derive a number that comp_stats already emits.** The blocks not yet covered by a dedicated renderer script (everything except the comp set table in v1.5.1) are scalar-binding from comp_stats output — read the field by name, never recompute. v1.6.0 may add per-block renderer scripts if recurrent bypass evidence accumulates.

   **DOM field semantics (read before bucketing or rendering the DOM column).**

   Each listing carries up to three DOM variants. They are NOT interchangeable — each measures a different market-presence question:

   - `dom_active`  — Recent market presence (≤ 30-day gap tolerance). **The only field this skill uses for Fresh/Aging/Stale bucketing and the DOM column.**
   - `dom_180`     — 180-day gap tolerance. Captures seasonal cycles. NOT used here; do not fall back to it.
   - `dom`         — Lifetime, cross-dealer accumulator. NOT used here; do not fall back to it.

   When `dom_active` is `None` (the field is absent on the wire), bucket the listing as **`Unknown`** and render the DOM column as `—`. Substituting `dom_180` or `dom` would mix seasonal-cycle / lifetime-VIN signals into a current-market bucket and silently break the report. One prior session's near-inverted DOM distribution (Fresh/Aging/Stale = 26/26/48% vs. canonical 65/13/22%) came from reading the wrong field. The fix is `dom_active` only — even when it forces some Unknown counts.

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
       [--exclude-vins <VIN1,VIN2,...>]   # only when W3 (history) has run
                                          # AND returned non-shadow dealer-hop VINs
   ```

   **Persisting the response for `parse_search.py --file`.** See the Pipeline-bypass warning above for the prescribed Write-tool recipe. The `--file` path unwraps the `{"result": ...}` envelope automatically via `_common._maybe_unwrap`. **Do NOT hand-key listings into a custom merge script** — that path loses programmatic VIN dedup and is banned; see the merge step below.

   **`--subject-vin` vs `--exclude-vins`:** `--subject-vin` carries the user's own VIN (shadow-listing detection); matches count as `filtered_out.self_vin_match` and trigger DQ event (c). `--exclude-vins` is for other VINs the skill wants to drop (past dealer-hop VINs from a prior W3 trade-in-history call); matches count as `exclude_vin_match` and trigger DQ event (d). **W1 does not call `get_car_history`** — so in the standard W1 flow, pass only `--subject-vin`. The history-VIN case only applies when W1 is chained after W3 in the same session.

   On `num_found == 0`, run a facet-discovery retry per `references/facet-discovery.md`. On still-zero, degrade the verdict to "insufficient comps — report price vs ML prediction only".

5. **Active comp set — asymmetric desc pull (tail coverage).**

   Issued optimistically in **Wave B** (see "Parallelization (W1)" section above) alongside the asc pull — do NOT serialize on `asc.num_found > 20` waiting to decide. The cost of one extra call when `num_found ≤ 20` is cheaper than a full roundtrip's worth of inference time.

   **Why tail coverage is needed.** A single `sort_by=price, sort_order=asc, rows=20` fetch silently drops the high-priced tail when `num_found > 20`. Server-side `stats="price,miles"` still gives an honest *numeric* quartile / percentile rank over the full `active_count` (`comp_stats.py` emits `stats_source="server"`), but the server aggregates don't return the actual tail listings — so the W1-rendered Competitive Set table, CPO premium (peers cluster at the top), `channel_stats` (franchise / independent split), `mileage_moat`, and the Outliers block all bias or degrade when only the bottom rows are visible. The percentile-bounded guard is a residual fallback for when `server_stats` is absent or `count < min_n`; it is no longer the primary motivation for the desc pull.

   ```
   search_active_cars (same base filters as asc):
     sort_by="price", sort_order="desc", rows=10
     price_range="1-*"
     include_dealer_object=true, include_build_object=true
   → parse_search.py --subject-vin <subject VIN>
   ```

   Persist the desc response the same way as asc (Write tool → `/tmp/marketcheck/<session.run_id>/desc.json` → `parse_search.py --file`). See `references/truncation-recovery.md`.

   **Merge asc + desc** via `scripts/merge_comps.py`:

   ```
   scripts/merge_comps.py \
     --asc <path-to-parse_search-asc-output> \
     --desc <path-to-parse_search-desc-output> \
     --subject-vin <subject VIN>
   → {merged_listings[], asc_n, desc_n, pulled_count, overlap_count, subject_vin_excluded, merged_n}
   ```

   `merge_comps.py` deduplicates by VIN (desc-first on duplicates per the tail-coverage semantic — desc rows carry the top-of-market listings, preferred when a mid-distribution VIN shows up in both) and emits `pulled_count = asc_n + desc_n` (raw), `merged_n = pulled_count − overlap_count − subject_vin_excluded` (unique comps). Pass `merged_listings` to `comp_stats.py` as `comps` and `pulled_count` as-is. **Do not hand-merge**: the v4 run routed dedup through `comp_stats.exclude_vins` and ended up over-excluding (n=21 instead of n=25); v5 hand-merged correctly but with no named script; v6 hand-keyed 30 listings into a custom Python script, reintroducing the same class of error. The merge is now prescribed.

   **Thin-market auto-widen:** if `asc.num_found < 15` AND (`user_price > 40000` OR `specs.msrp > 50000`), re-issue the asc + desc pair in **Wave C** at `radius = min(session.radius_mi_clamped * 1.5, 100)` and surface the widening in the Market Snapshot. Emit DQ event (g) acknowledging the radius override of dealer preference.

6. **Price-drop velocity (market-wide).**

   ```
   search_active_cars:
     same base filters + price_change="negative"
     rows=0                                # stats-only call
     include_dealer_object=false           # shaping knobs off (no listings returned)
     include_build_object=false
     (all other shaping knobs = false)
   → parse_search.py
   ```

   Pass `num_found` to `comp_stats.py` as `drops_market_wide_count`. `comp_stats` emits both `drop_rate_visible` (visible comps with price drops) and `drop_rate_market_wide` (market-wide drop count / active_count). The Market Snapshot renders both — visible rate tells the reader what the rendered table shows; market-wide rate is the broader-market signal.

7. **Sold-90-day aggregates — three single-field stats calls** (`search_past_90_days` rejects multi-field stats).

   ```
   search_past_90_days × 3:
     base: year, make, model, trim (verbatim), zip, radius, car_type, rows=0,
           price_range="1-*", sold=true
     a. stats="price"        → stats.price.{min,max,mean,median} + num_found
     b. stats="miles"        → stats.miles.*
     c. stats="dom_active"   → stats.dom_active.*  (PRIMARY — current-listing time-to-sell;
                                                    matches the dom_active-bucketed DOM Distribution)
        stats="dom"          → stats.dom.*         (FALLBACK — only if upstream rejects "dom_active";
                                                    log DQ event (e) with field-source attribution)
   → parse_search.py per call
   ```

   **Why `price_range="1-*"` + `sold=true` are load-bearing.** `sold=true` narrows the upstream's per-record classification from "all expired listings" (which include wholesale-out, withdrawn, and transferred records — ~10% of expired records) to records the upstream classifies as actually sold to retail customers. This makes the variable name `sold_count_90d` literally accurate and tightens `sold_median` to retail clearance prices specifically — the verdict anchor's whole purpose. `price_range="1-*"` filters out null/$0-priced records server-side. With this filter every matched record has `price ≥ 1`, so `stats.price.missing == 0` and `num_found == stats.price.count` is guaranteed. The skill previously tracked two counts (`sold_count_90d` = num_found for MoS, `sold_n` = stats.price.count for the verdict gate); after these filters the two collapse to a single value, so `sold_n` has been dropped from the comp_stats schema. `comp_stats.py` reads `sold_count_90d` for both the MoS denominator (`active_count / (sold_count_90d / 3)`) and the verdict gate (`sold_count_90d >= 5` to fire sold_anchor; else fall back to quartile). See `mcp_server_tool_docs/search_past_90_days.md` for the upstream parameter contract.

   **Why dom_active for sold-90d.** The Recommended Action's *"Local sold-90d median days-to-sell"* claim describes how long a *fresh listing* on the user's lot will likely take to sell. Lifetime `dom` aggregates inflate that median by 30–50% on markets where VINs bounce dealers (one sold-90d response in this dataset returned `stats.dom.{min: 8, max: 677, median: 59, stddev: 103.57}` — a 22-month accumulator on the max).  Aggregating over `dom_active` gives the actual current-listing duration, internally consistent with the Fresh/Aging/Stale buckets that read the same field per listing. `build_comp_stats_input.py` reads `stats.dom_active.median` as PRIMARY and falls back to `stats.dom.median` if upstream returned no `dom_active` block; it emits `sold_dom_field` ∈ `{"dom_active", "dom", null}` so the renderer can label appropriately.

   Use the same `{year, make, model, trim, car_type, zip, radius}` as step 4 — MoS numerator and denominator must match.

8. **State sold velocity** (see `references/sold-summary-safety.md`).

   ```
   get_sold_summary:
     make, model                            (verbatim)
     inventory_type="Used"                  (or "New" if car_type=new)
     state=<profile.location.state>         (required)
     summary_by="state"
     ranking_measure="average_days_on_market"   (NOT "average_days_to_sell")
     ranking_dimensions="make,model"            (minimal; avoid default 3-dim)
     top_n=5, limit=5000
     date_from / date_to — computed by `scripts/compute_sold_summary_dates.py`
   → scripts/parse_sold_summary.py --aggregate-state <profile.location.state>
   ```

   **Dates: use `compute_sold_summary_dates.py`** — it emits month-aligned `date_from` (first of `current_month − 3`) and `date_to` (last of `current_month − 1`) for the "last 3 full months" window. Never hand-compute or pass `today` as `date_to` — the current month is in progress and sold data lags. The tool's local validator does NOT check alignment; mis-aligned days pass local validation and return `error_type="network_422"` from upstream. See `references/sold-summary-safety.md` for the full gotcha.

   **Pass `--aggregate-state <STATE>` to `parse_sold_summary.py`** — the parser's aggregation flag computes the weighted-mean State Baseline in code: `state_baseline = {state, total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, months_included, row_count_for_state}`. This replaces the prior hand-computation path and enforces the M8 divide-by-zero guard (rows where every `sold_count == 0` emit `state_baseline: null` with `state_baseline_skipped_reason: "all_zero"`, not a fabricated mean).

   **Do NOT pass `dealer_type`.** Live-call testing showed that including `dealer_type=Franchise|Independent` combined with a narrow `make`/`model`/`state` slice returns `data.data=[]` for non-defective queries. The State Baseline line is about the state's overall make/model sold velocity, not a dealer-type-specific cut; the filter silently suppresses valid data. See `references/sold-summary-safety.md` for the gotcha details.

   On parser `ok=false`, branch on `error_type`:
   - `make_model_not_found` → retry once with facet-discovered make/model casing (`references/facet-discovery.md`); if still failing, skip the state line with a Data Quality Notes event.
   - `validation_dimension_limit` → retry once with `ranking_dimensions="make"` only.
   - `network_422` → verify `date_from`/`date_to` are month-aligned and `date_to` is not in the current month; if already aligned, skip the state line and log a Data Quality Notes event.
   - `network_5xx` / `validation` / `unknown` → skip the state line, log a Data Quality Notes event, continue. State baseline is enrichment — never halt the whole workflow for it.

   **State baseline aggregation is now in code.** `parse_sold_summary.py --aggregate-state <STATE>` emits a `state_baseline` block (see above). The renderer reads that object directly — no hand math. When the call degrades, `state_baseline` is null and the renderer skips the line.

   **Scope disclosure.** `get_sold_summary` does not accept `trim` or `year` on the state rollup — the returned row is `make` + `model` + `state` across **all trims and all years** within the date window. That's the tightest cut this endpoint supports. The rendered State Baseline line MUST carry the scope qualifier inline — `State Baseline (<make> <model> across all trims & years in <STATE>, last 3 full months): ...` — and a one-line note below the Market Snapshot block reminds the reader it's state-wide velocity, not direct price comparability against the Headline's trim-specific sold anchor. Without the qualifier, a $27K state average reads as a direct comparison to a $38K trim-specific sold median, which misleads.

9. **Compute stats.**

   Use `scripts/build_comp_stats_input.py` to assemble the 20+ field stdin JSON for `comp_stats.py` from the parsed outputs of Waves A/B + profile. Do NOT hand-build the input JSON — the script enforces field-name consistency and prevents the pulled_count / comps-list mismatches v4 and v5 both hit.

   ```
   scripts/build_comp_stats_input.py \
     --profile <load_profile output path> \
     --merged <merge_comps output path> \
     --asc-parsed <parse_search asc output path> \
     --sold-price <parse_search sold-90d stats=price path> \
     --sold-dom <parse_search sold-90d stats=dom_active path (PRIMARY) or stats=dom path (FALLBACK)> \
     --drops <parse_search price_change=negative path> \
     --user-price <asking price> \
     --user-miles <mileage> \
     --subject-vin <17-char VIN> \
     --subject-cpo true|false \
     --trim-label "<year> <make> <model> <trim>" \
     [--nocpo-primary-parsed <parse_predict-output-path> --nocpo-context-parsed <path>] \
     [--cpo-primary-parsed <path>   --cpo-context-parsed <path>] \
   | scripts/comp_stats.py
   ```

   Each `--*-parsed` flag points at a parse_predict.py output JSON. The builder reads each, extracts `marketcheck_price` + `comparables_n` + `recent_comparables_n` + `comparables_price_stats` + `recent_comparables_price_stats`, and packs the four roles into `marketcheck_predict_input` on the comp_stats stdin. `comp_stats.py` then emits the consolidated `marketcheck_predict` block (per-role MarketCheck Price + comp counts + comp price-distribution stats, plus derived CPO Premium and Net Margin from CPO computed from those MC Price values) which the renderer reads verbatim.

   Field sources (for reference):
   - `user_price, user_miles, subject_vin, subject_cpo, trim_label` — CLI args
   - `subject_dealer_type, radius_mi, city, fresh_max_days, aging_max_days, cpo_certification_cost` — profile
   - `comps, pulled_count` — merge_comps output
   - `active_count, server_stats` — asc-parsed output
   - `sold_count_90d = sold_price.num_found`, `sold_median = sold_price.stats.price.median` (with `price_range="1-*" + sold=true`, `num_found == stats.price.count`; the previously-separate `sold_n` field is dropped — `sold_count_90d` serves both the MoS denominator and verdict-gate roles)
   - `sold_dom_median = sold_dom.stats.dom_active.median` (PRIMARY) OR `sold_dom.stats.dom.median` (FALLBACK)
   - `sold_dom_field = "dom_active" | "dom" | null` — emitted by `build_comp_stats_input.py` and passed through `comp_stats.py`; drives the renderer's label choice ("median days-to-sell" vs "median lifetime DOM")
   - `drops_market_wide_count = drops.num_found`

   Key output fields consumed at render time:
   - `stats_source` → `"server"` or `"client"`. Surface this in the Data Quality Notes event log and (optionally) in the Price Distribution block header so the reader knows whether the distribution is computed over the full active set or only the visible subset.
   - `insufficient` → if true, render a thin-market block, skip the quartile verdict.
   - `percentile`, `percentile_source`, `percentile_approx`, `percentile_bounded` — percentile rank rendering is four-state:
     1. `percentile_source=="server"`, `percentile_approx=False` → render `<N>th percentile` (exact; server percentiles cover all `active_count`).
     2. `percentile_source=="server"`, `percentile_approx=True` → render `~<N>th percentile (approx)` (server count thin or user_price is outside p5..p99 edge region).
     3. `percentile_source=="client"`, `percentile_bounded` non-null → render `<low>th – <high>th percentile (bounded — visible set only)` with a footnote.
     4. `percentile_source=="client"`, `percentile_bounded` null → render `<N>th percentile (visible set)`.
   - `sold_dom_median` → drives the data-backed "days to sell" phrasing in the Recommended Action block (H6). Never invent DOM predictions from model knowledge.
   - `drop_rate_visible` / `drop_rate_market_wide` → Market Snapshot renders BOTH lines (visible and market-wide) so the reader sees both scopes.
   - `channel_stats.{primary, secondary, primary_non_cpo}` → drives the Same-Channel View section.
   - `verdict_source` → `"sold_anchor"` when `sold_count_90d >= 5` else `"quartile"`. The Verdict block MUST name the anchor.
   - `verdict_sold_anchor` vs `verdict_quartile` → when they disagree, prefer `sold_anchor` and surface the disagreement in Key Signals.
   - `mileage_moat.{tier, is_moat, moat_phrase, delta_pct, median_comp_miles}` — tiered output:
     - `tier == "moat"` (delta_pct ≥ 20%, ≥5 comps with miles, subject strictly under median): `is_moat == true` and `moat_phrase` carries a listing-copy-ready sentence. Append `moat_phrase` as a second sentence on the Headline.
     - `tier == "modest"` (10% ≤ delta_pct < 20%): no Headline phrase; render as a Key Signals bullet per the output template's Key Signals rules (uses `delta_pct` and `median_comp_miles`).
     - `tier == "none"` (delta_pct < 10%, insufficient comps, or subject at/above median): no rendering.
     The 20% moat threshold and 10% modest-tier threshold live in `comp_stats.py._mileage_moat`; they are the only mileage cutoffs consumed by this skill.
   - `primary_only.{source, n, median, diff, pct}` → drives the `Gap vs <PRIMARY>-Only Median` line in Your Price Position. `comp_stats.py` picks the source (primary_non_cpo when subject is non-CPO AND primary_non_cpo.n ≥ 2; otherwise primary); the renderer reads `primary_only.diff` / `primary_only.pct` verbatim and does NOT re-compute against `channel_stats.primary` or `channel_stats.primary_non_cpo` directly. When `primary_only is None` (primary.n < 2), omit the line entirely.
   - `dom_buckets` → Fresh / Aging / Stale counts using the profile's `fresh_max_days` / `aging_max_days`.

10. **Render the output.** **First: Read `assets/output-template.md` into context** — it is the single source of truth for block structure, the 8-col table schema, verdict phrasing, percentile render states, and the self-check. Then render per the template: Decoded Specs, Headline, Market Snapshot (incl. State Baseline + BOTH price-drop rates: visible and market-wide; State Baseline line carries the "all trims & years" scope qualifier inline with a one-line note below the block reminding the reader it's state-wide velocity context, not direct price comparability), Price Distribution (header reconciles `quartile.n` vs. `n` when they differ — e.g. `n=26 · 25 in table` — and includes `stats_source`), **Active Mileage Distribution** (sourced from step 4 asc `stats.miles` — NOT step 7b's sold-90d miles; sold-90d miles feeds only the mileage_moat check), DOM Distribution, Your Price Position (four-state percentile rendering per above; `Gap vs <PRIMARY>-Only Median` reads `primary_only` verbatim — render only when `primary_only` is non-null), optional CPO Premium block, Competitive Set (8-col), Same-Channel View (when applicable), Outliers, Data Quality Notes (only if non-empty), Key Signals (surface mileage modest-tier bullet when `mileage_moat.tier == "modest"`), Verdict & Recommended Action (always name the anchor source; action phrasing anchored on `sold_dom_median`), Self-check footer.
