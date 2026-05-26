---
name: competitive-pricer
description: Comparable-backed market price context for appraisers and adjusters. Anchored on realised sold prices when ≥minimum_comps trim-matched sold-90d comps exist; active-listing quartile distribution is the fallback. Three workflows — single-VIN price check (dual-channel ML prediction, sold-anchor or quartile value range, 8-column comparable citation table, CPO premium and state baseline when applicable); trade-in VIN price history (listing trajectory, dealer-hop / sharp-drop / decertified flags, optional fair-value); model-level market distribution (price/mileage/DOM stats, cheapest 8 + most-expensive 5, wholesale-vs-retail channel split). Use when asked "price this car", "market price for this", "compare pricing", "price check VIN", "what's the market on this", "what's the history on this trade", "what does the market look like for [year make model]", "how does this stack up", "is this asking price defensible", "price positioning analysis", or any comparable-backed valuation-context intent.
version: 0.2.0
---

# Competitive Pricer — Market Price Context for Appraisals

Given a VIN (or year-make-model-trim) and optionally an asking price, anchor a defensible value range on the local market using ML prediction + active comps + sold-90d realised prices, then surface the comparable citation table the appraiser can attach to their workpaper. The value range is anchored on realised sold prices when ≥`minimum_comps` trim-matched sold-90d comps are available (what buyers actually paid); the active-listing quartile distribution is the fallback when sold data is thin.

Three workflows map to distinct appraiser intents:

- **W1 — Price-Check Single VIN** — "is this asking price defensible?" / "what's the market on this VIN?" (reference workflow; every anchor, filter, and render rule lives here)
- **W2 — Trade-In VIN Price History** — "what's the history on this trade?" (US-only) — surface the VIN's listing trajectory + dealer-hop / sharp-drop / decertified red flags; pagination-gap aware; optional dual-channel ML fair-value when the appraiser supplies current odometer
- **W3 — Market Price Distribution** — "what does the market look like for this model?" (US canonical; UK analogue in `references/country-uk.md`) — surface model-or-trim-level price/mileage/DOM distribution + cheapest 8 + most-expensive 5 listings + by-channel split (franchise vs independent) + state-level sold velocity baseline. No subject vehicle; no anchor band.

This skill is **agent-driven** — there are no Python scripts. Every parsing step, every envelope unwrap, every comp-merge, every quartile / percentile / mileage-advantage calculation is performed by the model in-prompt following the contracts in the per-workflow references. The contracts are tight on purpose: defensibility against dispute requires that every rendered number is traceable to its source response, never to hand-fabricated values.

## Before you start

1. **Load the profile.** Read `marketcheck-profile.md` (project memory file). Parse the YAML frontmatter for the structured fields, then parse the JSON body for the canonical values. Per `references/profile-loading.md`, the appraiser plugin's profile carries: `location.{country, zip, state}`, `specialization` (optional), `default_radius_miles` (default 75), `minimum_comps` (default 6), `preferences.default_inventory_type` (when present). If the profile file does not exist, halt: *"I don't see your appraiser profile. Run `/onboarding` to set up your profile, or supply ZIP + country inline for this run."*

2. **Confirm the profile.** First user-facing line is always: `Using profile: <name-if-present-else-appraiser>, <ZIP or postcode>, <country>`.

3. **Branch on country.**
   - `country == "US"` → the workflows below.
   - `country == "UK"` → read `references/country-uk.md`. UK has no VIN decoder, no ML predictor, no `get_sold_summary`, no `get_car_history`; `search_uk_active_cars` + `search_uk_recent_cars` are the only tools, comp median substitutes as the price anchor.
   - `country == "CA"` → **halt** with: *"Competitive Pricer does not yet support Canada. The skill is US + UK only — contact support if CA workflows are needed."*
   - Any other country → halt with the same US-or-UK-only message.

4. **Compute session values once.** Cache in scratchpad for the remainder of the workflow:
   - `radius_mi_clamped` = `min(default_radius_miles or 75, 100)` (the 100-mile cap is the `search_past_90_days` hard cap; enforce uniformly so the active comp set and the sold-90d comp set share scope).
   - `min_comp_count` = `minimum_comps or 6` (thin-market gate AND sold-anchor / quartile-anchor selection threshold).
   - `state = profile.location.state` — required by `get_sold_summary` (W1, W3); halt and ask if missing in a US profile.
   - `car_type_resolved` = `profile.preferences.default_inventory_type` when present:
     - `"used"` or `"new"` → use directly on every search.
     - `"both"` → **halt and ask: "Market context on used or new units?"** Apply the answer for the rest of the session.
     - If the appraiser's answer is not exactly `used` or `new`, re-ask once. On a second non-answer, default to `"used"` and emit DQ event (f).
     - When `default_inventory_type` is **absent from the profile**, default to `"used"` and emit DQ event (g): *"Inventory-type defaulted to 'used' (no preference in profile)."*
   - `dom_thresholds` defaulted to `{fresh: 30, aging: 60}` (the appraiser onboarding doesn't gather custom thresholds).
   - `specialization_note` — render in the footer when `profile.specialization` is set.

5. **Payload-shaping defaults** — every `search_active_cars` / `search_past_90_days` / UK-search call passes:
   - `fetch_all_photos=false`, `include_mc_dealership_object=false`, `include_finance=false`, `include_lease=false`, `include_relevant_links=false` — always off. Big-payload knobs; the skill never renders the fields they gate.
   - `include_build_object=true` on **listing-rendering fetches** (calls that produce the 8-col comparable citation table). The spec fields (`body_type`, `drivetrain`, `engine`, `transmission`) live **exclusively** in the `build` sub-object — the listing root never carries them. `include_build_object=false` makes those fields definitively null on every comp row. Set `false` on stats-only (`rows=0`) calls where no listings are returned.
   - `include_dealer_object=true` on listing-rendering fetches (needed for the F/I Type column and dealer-name binding). `false` on stats-only calls.
   - `rows=<exactly what the output will render>` — never over-fetch.

6. **Working directory.** Save unwrapped MCP envelopes and intermediate JSON to `/tmp/marketcheck/<scratch-id>/` where `<scratch-id>` is a short identifier the model picks at workflow start (e.g., `cpr-<epoch-seconds>`). Files are session-local and regenerated each run. The `Write` tool handles large JSON content directly; do NOT `cat` or heredoc large envelopes.

7. **Price-filter convention.** Every `search_*` call — sorted listing pulls (`rows≥1`) AND stats-only (`rows=0`) calls — passes `price_range="1-*"`. The API silently excludes null-price rows from `stats.price.{mean, median, percentiles}` but counts them in `num_found`, so without the filter every downstream consumer of `num_found` (active and sold-90d scope counts, drop/raise rates, market-record counts) is biased. Also filter client-side on `price in {0, null, missing}` as defence-in-depth. The user never sees a $0 row.

8. **Input-format parsing.** Per `references/profile-loading.md`: user-supplied asking price accepts any of `27000`, `$27000`, `$27,000`, `27,000`, `27k`, `27K`. Currency symbols and commas are stripped; trailing `k`/`K` multiplies by 1000. Reject negative or zero values. Mileage accepts plain integer or `96,619` form (strip commas).

9. **VIN format validation.** Every workflow that takes a VIN validates `^[A-HJ-NPR-Z0-9]{17}$` before any MCP call. On failure, halt with *"VIN is malformed (must be 17 chars, no I/O/Q). Please correct and re-run."*

## Facet discipline

Pass decoded `model` and `trim` **verbatim** to every search call — never concatenate. If decode returns `model="RX"` + `trim="350"`, pass those two strings, never `model="RX 350"`. If a first filtered search returns `num_found == 0`, read `references/facet-discovery.md` and retry once with a facet-discovery call. Cache the resolved `{make, model, trim}` tuple in your scratchpad for the remaining calls in the session — don't re-discover per call.

**Trust-verbatim is casing-sensitive.** A YMMT tuple is "trusted-casing" only when (a) it came from a successful `decode_vin_neovin` call with canonical fields populated, or (b) a prior facet-discovery call in the same session resolved the casing. **User-typed free-form YMMT (e.g. "honda accord sport") is NOT trusted-casing** — run facet discovery once to normalize casing before any filtered search. Details in `references/facet-discovery.md`.

## Truncation handling

Truncation signature: `Error: result (N chars) exceeds maximum allowed tokens. Output has been saved to <path>`. The saved file wraps the real response as `{"result": "<stringified JSON>"}`.

Default recovery per `references/truncation-recovery.md`:

1. Read the file at `<path>`.
2. Unwrap the `{"result": "..."}` envelope.
3. `json.loads` the inner string.
4. Extract only the canonical fields the workflow consumes; discard the rest.

`decode_vin_neovin` and `predict_price_with_comparables` truncate chronically (~150KB / ~100KB envelopes). Treat `--file <path>` recovery as the expected path for these two tools, not an exception. `search_active_cars` / `search_past_90_days` / `get_car_history` truncate only at higher `rows` settings; the default small-payload fetches arrive inline.

If unwrap fails (file corrupt, inner string unparseable), render a caveat line for the affected block and continue. Do NOT halt the whole workflow for one failed call.

**Banned paths.** Do NOT `cat` saved files into context. Do NOT retry the original MCP call without tightening filters. Do NOT hand-key listings into a custom merge step. Do NOT re-derive a `price_change_amount` or any pre-computed field — read the parsed value. Do NOT substitute model-knowledge values when the parsed field is null — render `—`.

## Comp-set integrity

Rules enforced on every comp-using workflow:

- **Subject VIN exclusion.** When the workflow has a subject VIN (W1), exclude it from the merged comp set. The subject must never appear as its own comp. A **shadow listing** — the subject VIN appearing at a *different* dealer in the active comp set — is exactly what this filter catches; log DQ event (c) with the shadow-dealer names when this fires.

- **Variant consistency** is the **server's** responsibility. Pass decoded `make`, `model`, `trim` verbatim and trust the server's facet match to return the correct line-variant. Decoded `body_type`, `drivetrain`, `engine`, `transmission` are display-only spec metadata — never used as filters, never passed as API params.

- **Scope-matching filters (active vs sold-90d).** When the workflow needs sold-90d AND active counts to be apples-to-apples (W1's sold-anchor selection, the days-to-sell context), the two calls MUST share identical `{year, make, model, trim, car_type, zip, radius}` filter sets. Numerator and denominator must be drawn from the same scope.

- **`min_comp_count` threshold.** When the merged comp set has fewer than `min_comp_count` rows (default 6 from the appraiser profile's `minimum_comps`), the quartile / percentile blocks are suppressed and the renderer emits a thin-market block instead. The same threshold gates the sold-anchor / quartile-anchor selection: sold-anchor fires when `sold_count_90d >= min_comp_count`.

## Parallelization (universal wave contract)

Every workflow follows the same wave-execution contract, regardless of which calls it issues:

- **A wave is a batch of MCP calls fired in a single agent message** — multiple `tool_use` blocks in one assistant turn, dispatched concurrently by the runtime. The agent emits all calls in the wave together, then waits for the full batch of `tool_result` messages before issuing the next wave.
- **Within a wave, calls share no cross-dependency** on each other's output. A call that needs another call's parsed output (e.g., a search filtered on the decoded YMMT) goes in a *later* wave, not the same one. Calls that take only user inputs + profile + their own VIN argument can fit Wave A.
- **Wait for the entire wave** before issuing the next. Don't pipeline waves.
- **Never serialize calls within a wave.** Each serial roundtrip is a ~12s latency add. Five serialized MCP calls cost ~60s; the same five fired together cost ~12s. The wave model is what keeps the workflow inside its budget.
- **Wave A / Wave B / Wave C are workflow-local labels**, not a global call manifest. Each `references/w<N>-*.md` defines its workflow's specific wave structure.

Latency budget at a glance (specific call lists in each workflow's reference):

- Single-wave workflows (W2 trade-in history without step 3): ~12s
- Two-wave workflows (W3 market distribution): ~25s
- Three-wave workflows (W1 single-VIN price-check, with conditional Wave C): ~27–30s common path

## Data quality rule

Treat `dealer_type` as optional on listings. When `include_dealer_object=true` is passed and the field is still absent, render `—` in the Type column. Never heuristic-guess F vs I from the dealer name or domain. Null `dealer_type` is a legitimate render state — never invented.

Treat `is_certified` as **tri-state** on the wire: `1` (truthy CPO), `0` (explicit non-CPO), or absent (unknown). See `references/cpo.md`.

Treat `dom_active` as the ONLY DOM field this skill reads. Substituting `dom_180` (180-day gap tolerance) or `dom` (lifetime accumulator) silently mixes seasonal-cycle / cross-dealer signals into a current-market bucket. When `dom_active` is null on a listing, bucket as **Unknown** and render the DOM column as `—`.

---

## Workflow 1 — Price-Check Single VIN

Reference workflow. Triggers: "price this VIN", "is this asking price defensible", "what's the market on this one", "compare pricing on this VIN", "price positioning analysis", etc. Score one VIN against the local active and sold market; produce a sold-anchored value range + comparable citation table the appraiser attaches to their workpaper.

→ Full spec in **`references/w1-price-check.md`**.

---

## Workflow 2 — Trade-In VIN Price History

Triggers: "what's the history on this trade", "previous listings for VIN X", "show this VIN's price trajectory", etc. **US-only** — halt on UK profiles. **History viewer** workflow: surface the VIN's listing trajectory + dealer-hop / sharp-drop / decertified red flags. Optional dual-channel ML fair-value when the appraiser supplies current odometer.

→ Full spec in **`references/w2-trade-in-history.md`**.

---

## Workflow 3 — Market Price Distribution

Triggers: "what does the market look like for this model", "market distribution for 2022 Camry", etc. **US canonical; UK analogue in `references/country-uk.md`.** No subject vehicle — describes the market itself: model-or-trim-level distribution (Price / Mileage / DOM), by-channel split (franchise vs independent medians from dedicated stats-only calls), cheapest 8 + most-expensive 5 listings, state-level sold velocity baseline (US only).

→ Full spec in **`references/w3-market-distribution.md`**.

---

## Output

All workflows render via **`assets/output-template.md`** — the **single source of truth** for block structure, the 8-column comparable citation table schema, value-range phrasing, percentile rendering states, null-field rule, and the self-check. Do not inline block definitions in workflow references; the template owns them.

Cross-workflow render rules:

- **Standard 8-col comparable citation table** (`Dealer | Type | Price | Miles | DOM | Distance | vs Mkt Median | Price Drop?`) on every competitive-listing render, regardless of workflow.
- Sort ascending by price unless the workflow explicitly says otherwise (Most-Expensive in W3 renders desc).
- Mark the row closest to the subject's asking price with `← You` (W1 with `user_price` only).
- Empty/missing `dealer_type` renders as `—`. Never guess.
- Filtered-out counts (self-VIN, $0/null, invalid-price) surface as a footnote under the comp-set table when non-zero.
- The Position vs Anchor band labels (Aligned / Modestly above-below / Materially above-below) are **descriptive**, not action verdicts — appraisers do not issue price actions.

### Data Quality event log

Accumulate a running list of events across the workflow; feed it into the Data Quality Notes section at render time. Track:

- **(a)** MCP tool errors or non-200 responses recovered from — tool name, error_type, recovery path.
- **(a1)** Facet-discovery retries — original filter value, resolved value, tool.
- **(b)** Truncation-envelope unwraps via the `Write` + re-read recipe — which parsing step, which tool.
- **(c)** Subject VIN found in active comp set at a different dealer (shadow listing) — dealer name + distance.
- **(d)** Non-zero filtered-out counts — totals by category (self-VIN match, invalid-price, $0/null).
- **(e)** Fallback source attribution — when a computed stat used a secondary source (e.g., `dom` median used because upstream rejected `dom_active`; State Baseline `state_baseline_skipped_reason`).
- **(f)** Parameter adaptations — when a documented parameter wasn't accepted and a substitute was used (e.g., `price_range="1-*"` in place of `price_min=1`).
- **(g)** Workflow branch skipped by design — an optional or conditional branch was not run because its gate was not met. Examples: *"CPO branch skipped: appraiser stated non-CPO"* · *"Thin-market auto-widen not triggered: num_found ≥ min_comp_count"* · *"Inventory-type defaulted to 'used' (no preference in profile)."*

If the list is empty, omit the Data Quality Notes section entirely (do not render an empty header).

## Self-check

The 12-item silent verification checklist lives in `assets/output-template.md`. It is an **internal guardrail** — the model runs each check silently before returning and emits a single footer line summarising pass status; it does NOT render the full checkbox grid.

- **All applicable checks pass** → one-line footer, e.g. `✓ Verified: profile, dual-channel pricing, 8-col schema, $0 filter, dom_active, no null-substitution.` Abbreviate to 5–7 items; drop N/A from the summary.
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated in the output to compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.
