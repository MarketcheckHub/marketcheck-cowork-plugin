---
name: vehicle-appraiser
description: Defensible comparable-backed vehicle valuation with cited evidence. Returns a low/mid/high value range with confidence band anchored on sold-90d retail transactions when ≥5 comps are available; active-listing distribution is the fallback. Five appraisal workflows — Full Comparable Appraisal with VIN-cited comps, Trade-In Quick Appraisal for desk-side estimates, Wholesale-vs-Retail Spread (franchise vs independent channel), Regional Price Variance across multiple ZIPs / postcodes, and Historical Value Trajectory per VIN. Use when a trade-in appraiser, insurance adjuster, estate or probate appraiser, fleet manager, or independent appraisal firm asks "appraise this vehicle", "what's it worth", "trade-in value", "comparable analysis", "fair market value", "wholesale vs retail", "appraisal report", "how much should I offer", "vehicle valuation", "price trajectory", "depreciation rate", "regional value variance", "trade-in offer range", "insurance total-loss value", or "estate valuation".
version: 0.2.0
---

# Vehicle Appraiser

Given a VIN (or YMMT) + mileage + condition + purpose, score the vehicle's defensible value against the local active and sold market and emit a low/mid/high value range with confidence band, methodology citation, and the comparables (by VIN, miles, dealer, distance) that support the conclusion. The appraisal anchors on sold-90d retail transactions when ≥5 retail-sold comps are available (what buyers actually paid); the active-listing quartile distribution is the fallback bracket.

Five workflows map to distinct appraiser intents:

- **W1 — Full Comparable Appraisal** — *"appraise this vehicle, formal report"* (reference workflow; deep diagnostic for insurance total-loss, estate, fleet revaluation, defensible valuation; cites every comp by VIN, miles, dealer, distance; emits sold transaction evidence)
- **W2 — Trade-In Quick Appraisal** — *"what's it worth, customer at the desk"* (≤25s wall clock; predicted retail / wholesale / spread / offer range; top 5 comps; compact card output; routes to W1 for depth). **Subject is always Used** — the active comp pull is hardcoded `car_type="used"` because trade-in subjects are by definition the customer's existing used vehicle and the 78-85% wholesale-to-retail spread is a Used-car trade-in margin.
- **W3 — Wholesale-vs-Retail Spread** — *"how should I price this trade"* (franchise vs independent channel split; recommended offer range positioned between wholesale and retail, biased per purpose; recon-cost grossing-up when supplied). **Used-vehicle workflow** — halts when the **subject** is a new vehicle (decoded MSRP-anchored or user-stated); new vehicles sell at MSRP-anchored prices (no franchise/independent spread exists) and independent dealers cannot legally sell new vehicles of franchised brands.
- **W4 — Regional Price Variance** — *"compare value across markets"* (multi-ZIP / multi-postcode comparison, 2-6 markets; arbitrage flag at >5% delta; state-baseline context from `get_sold_summary` on US; no subject vehicle)
- **W5 — Historical Value Trajectory** — *"what's this VIN's price history"* (`get_car_history`-backed trajectory; cumulative depreciation rate; dealer-hop / sharp-drop / decertified red flags; optional ML fair-value when current odometer supplied). **US-only** — halts on UK profiles (no `get_car_history`).

## Before you start

1. **Load the profile.** Run `scripts/load_profile.py` (reads `marketcheck-profile.md`, parses YAML frontmatter + JSON body). Non-zero exit → halt and ask the user for the minimum inputs (ZIP or postcode + country). The skill works without a full profile; ZIP/postcode and country are the floor.

2. **Confirm the profile.** First user-facing line is always:
   `Using profile: <user.name or user.company>, <ZIP or postcode>, <country>`.
   Fall back to `Anonymous appraiser` when neither `user.name` nor `user.company` is populated.

3. **Branch on country.**
   - `country == "US"` → the workflows below.
   - `country == "UK"` → read `references/country-uk.md`. UK has no VIN decoder, no ML predictor, no `get_sold_summary`, no `get_car_history`. W3 and W5 halt on UK; W1, W2, W4 have UK adaptations.
   - Any other country → halt with: *"Vehicle Appraiser supports US and UK profiles only — contact support if other markets are needed."*

4. **Compute session values.**
   - `radius_mi_clamped` — read verbatim from `profile.session.radius_mi_clamped` emitted by `scripts/load_profile.py` (clamped 25–150mi from `profile.preferences.default_radius_miles`).
   - `min_comp_count` — read verbatim from `profile.session.min_comp_count` (default 10). This is the appraiser-set threshold for `insufficient` recovery in the comp-set step; it overrides any hardcoded default.
   - `purpose_default` — read verbatim from `profile.session.purpose_default` (mapped from `appraiser.specialization`: trade-in→Trade-in, insurance→Insurance, estate_legal→Retail, fleet→Wholesale, general→Retail). When the user omits `purpose` on a workflow invocation, use this default and surface "Purpose: <purpose_default> (from specialization=<spec>)" in the output so the user can override.
   - `state = profile.location.state` — required by `get_sold_summary` (W1, W3, W4) on US profiles; halt and ask if missing in a US profile when those workflows are invoked.
   - `subject_car_type` — derived **per workflow invocation**, NOT from profile. For W1 / W3 / W5: from decoded specs (a recent-model-year VIN with low miles + an MSRP-anchored predict and no `dom_active` is treated as `new`; everything else is `used`). For W2: hardcoded `used`. For W4: ask the user when ambiguous.
   - `dom_thresholds` — static defaults used by the DOM Distribution block: `fresh=30`, `aging=60`, `stale>60`. The appraiser profile does not carry custom DOM thresholds.

5. **Payload-shaping defaults** — every `search_active_cars` / `search_past_90_days` / UK-search call passes:
   - `fetch_all_photos=false`, `include_mc_dealership_object=false`, `include_finance=false`, `include_lease=false`, `include_relevant_links=false` — always off.
   - `include_build_object=true` on listing-rendering fetches; `false` on stats-only (`rows=0`) calls.
   - `include_dealer_object=true` on listing-rendering fetches; `false` on stats-only calls.
   - `rows=<exactly what the output will render>` — never over-fetch.

6. **Working directory.** All intermediate files (raw MCP responses, parsed outputs) are written to `/tmp/marketcheck/<session.run_id>/`, where `session.run_id` is auto-generated by `scripts/load_profile.py` (format: `appraisal-<epoch>-<8hex>`). Each skill flow gets a unique `run_id`. The directory is created lazily by `persist_response.py`.

7. **Price-filter convention.** Every `search_*` call — sorted listing pulls (`rows≥1`) AND stats-only (`rows=0`) calls — passes `price_range="1-*"`. The API silently excludes null-price rows from `stats.price.{mean, median, percentiles}` but counts them in `num_found`, so without the filter every downstream consumer of `num_found` (regional variance per-market counts, appraisal-band sold count) is biased. `parse_search.py` also filters client-side on `price in {0, null, missing}`. The user never sees a $0 row.

8. **Session continuity.** Session values live in the profile's `session` block emitted by `scripts/load_profile.py`. Read them verbatim. If the conversation approaches compaction, re-run `scripts/load_profile.py --run-id <previously-emitted>` to preserve the scratch directory.

9. **Input-format parsing.** Mileage accepts plain integer or `96,619` form (strip commas). Asking price (when supplied for W3) accepts any of: `27000`, `$27000`, `$27,000`, `27,000`, `27k`, `27K`. Reject negative or zero values with a halt. Condition is one of `Clean` / `Average` / `Rough` (case-sensitive); unknown values default to `Average` with a Key Signal note. Purpose is one of `Trade-in` / `Retail` / `Insurance` / `Wholesale`; when missing, use `session.purpose_default`.

## Facet discipline

Pass decoded `make`, `model`, and `trim` **verbatim** to every search call — never concatenate. If decode returns `model="RX"` + `trim="350"`, pass those two strings, never `model="RX 350"`. If a first filtered search returns `num_found == 0`, read `references/facet-discovery.md` and retry once with a facet-discovery call. Cache the resolved `{make, model, trim}` tuple for the remaining calls in the session.

**User-typed free-form YMMT (e.g. "honda accord sport") is NOT trusted-casing.** Run facet discovery once to normalize casing before any filtered search.

## Truncation handling

Truncation signature: `Error: result (N chars) exceeds maximum allowed tokens. Output has been saved to <path>`. Default recovery: pass `--file <path>` to the relevant parser. Every parser unwraps the `{"result": ...}` envelope transparently. See `references/truncation-recovery.md` for the full recipe.

## Comp-set integrity

Rules enforced on every comp-using workflow:

- **Subject VIN exclusion.** Always pass the subject VIN to `parse_search.py` via `--subject-vin`. Shadow listings (subject VIN at a different dealer) are caught and surfaced in DQ event (c).
- **Variant consistency** is the **server's** responsibility. Pass decoded `make`, `model`, `trim` verbatim and trust the server's facet match.
- **MoS matching filters.** When Months-of-Supply is computed (W1), the active-inventory call and the sold-90-day call MUST share identical `{year, make, model, trim, car_type, zip, radius}` filter sets.
- **`min_comp_count` threshold.** The appraiser's `profile.session.min_comp_count` (default 10) is the floor for `sufficient` comp coverage. When the filtered comp set has fewer rows, the appraisal band falls to `predict_only` (when ML available) or `null` (thin-market block).

## Parallelization (universal contract)

Every workflow follows the same wave-execution contract:

- **A wave is a batch of MCP calls fired in a single agent message** — multiple `tool_use` blocks in one assistant turn.
- **Within a wave, calls share no cross-dependency**. A call that needs another call's parsed output goes in a *later* wave.
- **Wait for the entire wave** before issuing the next.
- **Never serialize calls within a wave.** Each serial roundtrip is a ~12s latency add.

Wall-clock budget at a glance:
- W1 (3-wave): ~27–30s
- W2 (single-wave): ~12–15s
- W3 (2-wave): ~25–30s
- W4 (1–2 waves): ~25s
- W5 (single-wave): ~12s (history+decode) or ~15s (with optional fair-value branch)

Wave content lives in the per-workflow reference. Each `references/w<N>-*.md` defines its workflow's specific wave structure.

## Channel labeling

The appraiser plugin is **channel-neutral**: the profile does not carry a dealer-side `dealer_type`. W1 / W2 / W3 always fire **both** dealer-type predicts (franchise + independent) so the output can render the full retail/wholesale-proxy picture for any appraisal purpose. The `Franchise` predicted price is the retail benchmark; the `Independent` predicted price is the wholesale-proxy floor. There is no PRIMARY/CONTEXT badge — the appraiser reads both equally and selects the appropriate benchmark per appraisal purpose (Insurance/Estate → retail; Trade-in/Wholesale/Fleet → wholesale-proxy or spread midpoint).

## Data quality rule

Treat `dealer_type` as optional on listings. When `include_dealer_object=true` is passed and the field is still absent, render `—` in the Type column. Never heuristic-guess F vs I from the dealer name or domain.

---

## Workflow 1 — Full Comparable Appraisal

Reference workflow. Triggers: "appraise this vehicle", "appraisal report", "fair market value", "insurance total-loss value", "defensible valuation", "estate valuation". Score one VIN against the local active and sold market; emit a low/mid/high value range with confidence band, sold transaction evidence, methodology, and cited comparables.

→ Full spec in **`references/w1-full-appraisal.md`**.

---

## Workflow 2 — Trade-In Quick Appraisal

Triggers: "trade-in value", "what's it worth quick", "how much should I offer", "customer at the desk". Single-VIN, ≤25s wall clock. Predicted retail / predicted wholesale / spread / recommended offer range / top 5 comps / confidence band. CPO branch when applicable. **Halts and routes to W1** for sold-anchor depth or formal report. Renders via `assets/w2-output-template.md`.

→ Full spec in **`references/w2-trade-in-quick.md`**.

---

## Workflow 3 — Wholesale-vs-Retail Spread

Triggers: "wholesale vs retail", "what's the spread", "trade-in offer range", "franchise vs independent". **US-only** — halt on UK profiles (no `dealer_type` filter on UK active surface). **Used-subject-only** — halt when the subject is a new vehicle (decoded MSRP-anchored or user-stated). Single-VIN channel split: dual ML predicts (franchise + independent) + dual active comp pulls + sold-90d evidence. Emits the spread $/% line, recommended trade-in offer range (78-85% of franchise predicted retail; biased per purpose), optional recon-cost grossing-up. Two side-by-side comp tables (franchise / independent).

→ Full spec in **`references/w3-wholesale-vs-retail.md`**.

---

## Workflow 4 — Regional Price Variance

Triggers: "compare values across markets", "regional price difference", "fleet relocation analysis", "multi-state insurance claim", "arbitrage opportunity". **No subject vehicle, no asking price.** YMMT + 2-6 ZIPs (or postcodes on UK). Wave B fires N stats-only `search_active_cars` (one per market) + 1 `get_sold_summary` for state-baseline context on US. Halts at >6 markets — no off-ramp; user must split the request.

→ Full spec in **`references/w4-regional-variance.md`**.

---

## Workflow 5 — Historical Value Trajectory

Triggers: "price history", "VIN history", "depreciation rate for this VIN", "show me this vehicle's listing trajectory". **US-only** — halt on UK profiles (no `get_car_history`). Single-wave: `get_car_history` + `decode_vin_neovin` + (optional, when miles supplied) 2 dual-channel `predict_price_with_comparables`. Output: chronological trajectory table + cumulative depreciation summary + red flags (multi-dealer churn, sharp drops, decertified) + optional Current ML Fair Value. Routes to W1 for full appraisal.

→ Full spec in **`references/w5-history-trajectory.md`**.

---

## Output

W1 / W3 / W4 / W5 render via `assets/output-template.md`. **W2 renders via `assets/w2-output-template.md`** — its own single-source-of-truth file with a compact card layout suited to desk-side use. Each template is the **single source of truth** for block structure, table schemas, methodology phrasing, and self-check rules for the workflows it covers.

Render rules:

- Standard 8-col table (`Dealer | Type | Price | Miles | DOM | Distance | vs Mkt Median | Price Change`) on every Active Retail Comparables render.
- Sold Transaction Comparables table uses the dedicated 8-col schema (`Dealer | Type | Sold Price | Miles | DOM | Distance | Sale Date | CPO?`).
- Sort ascending by price unless the workflow explicitly says otherwise (Sold Transaction Comparables is sorted descending by sale date — most recent first).
- Mark the row closest to the user's asking price (when supplied) with `← You` in the Active comp tables.
- Empty/missing `dealer_type` renders as `—`. Never guess.
- Filtered-out counts from `parse_search.py` (self-VIN, exclude-VIN, invalid-price) surface as a footnote under the comp-set table if non-zero.
- **Null-field hallucination guard:** render any field whose value parses as `null` / missing as literal `—`. Do NOT substitute plausible defaults from model knowledge.

### Data Quality event log

Accumulate a running list of events across every workflow; feed it into the Data Quality Notes section at render time. Track:

- (a) **MCP tool errors or non-200 responses recovered from** — tool name, `error_type`, recovery path.
- (a1) **Facet-discovery retries** — when a filtered search returned 0 results and a facet lookup resolved the correct casing.
- (b) **Truncation-envelope unwraps** via `--file <path>` — which parser, which tool. Plus history pagination gap (W5).
- (c) **Subject VIN found in active comp set at a different dealer** (shadow listing) — dealer name + distance.
- (d) **Non-zero `filtered_out` counts** from parsers — totals by category (self-VIN, exclude-VIN, invalid-price).
- (e) **Fallback source attribution** — when a computed stat used a secondary source.
- (f) **Parameter adaptations** — when a documented parameter wasn't accepted and a substitute was used.
- (g) **Workflow branch skipped by design** — an optional or conditional branch was not run. Examples: *"CPO branch skipped: user stated non-CPO"*, *"Sold transactions table skipped: insufficient sold-90d count"*, *"State baseline skipped: get_sold_summary degraded"*.

If the list is empty, omit the section entirely.

## Self-check

The verification checklist lives in `assets/output-template.md` (W1/W3/W4/W5) and `assets/w2-output-template.md` (W2). It is an **internal guardrail** — the model runs each check silently before returning and does NOT render the full checkbox grid to the reader.

- **All applicable checks pass** → emit a single footer line (5–7 of the items that were exercised).
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.

The two non-negotiable appraisal-domain rules in the self-check:

1. **Confidence band must match `comp_count_total`** (Low <5, Medium 5–14, High 15+).
2. **Low-confidence appraisals MUST render a value range, not a point estimate** — appraisers, insurance adjusters, and fleet analysts depend on this guard for defensibility.
