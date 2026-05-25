---
name: competitive-pricer
description: Scores a vehicle against the live local competitive set and returns a Below / Modestly Below / At / Modestly Above / Above Market verdict with a dollar-weighted next action. Covers five pricing workflows — single-VIN price check, batch lot scan (≤5 VINs), trade-in VIN price history with red-flag detection, model-level market distribution, and competitor price-movement / undercut scan. Every output shows dual-channel predicted prices (franchise AND independent), percentile rank, months-of-supply, DOM distribution, CPO premium when applicable, and an 8-column comp table. Use when a dealer, used-car manager, or appraiser asks "am I priced right on this VIN", "is this unit overpriced", "check my inventory pricing", "price my lot", "what's the history on this trade", "what does the market look like for [year make model]", "who dropped their price", "who is undercutting me", "how does this stack up", or "is my number right" — or raises any pricing-diagnostic intent without naming the skill.
version: 1.8.1
---

# Competitive Pricer

Given a VIN (or year-make-model-trim) and an asking price, score the price against the local competitive set using ML prediction + live active comps + sold-90d velocity, then emit a five-band verdict with a one-sentence dollar-weighted action. The verdict is anchored on realised sale prices when ≥5 trim-matched sold-90d comps are available (what buyers actually paid); the active-listing quartile distribution is the fallback when sold data is thin.

Five workflows map to distinct dealer intents:

- **W1 — Price-Check Single VIN** — "am I priced right on this one?" (reference workflow; every anchor, filter, and render rule lives here)
- **W2 — Batch Competitive Scan** — "check pricing on my front-line inventory" (≤5 VINs inline; halt and recommend `dealer:lot-pricer` above 5; quartile-anchored per-VIN verdicts against the local active-listing distribution)
- **W3 — Trade-In VIN Price History** — "what's the history on this trade?" (US-only) — surface the VIN's listing trajectory + dealer-hop / sharp-drop / decertified red flags; pagination-gap aware; dealer_id-primary churn count with name fallback; optional dual-channel ML fair value when the dealer supplies current odometer
- **W4 — Market Price Distribution** — "what does the market look like for this model?" (US-only) — surface model-or-trim-level price/mileage/DOM distribution + cheapest 8 / most-expensive 5 listings + by-channel split + state-level sold velocity baseline. No subject vehicle; no verdict.
- **W5 — Competitor Price Movement** — "who dropped their price / who is undercutting me?" (US-only canonical; UK W5 analogue in country-uk.md). Surface deepest drops by magnitude, dealer-grouping for inventory pressure, aggressive-raisers Key Signal, optional response matrix (match/split/hold) when user supplies a reference unit. 4 parallel Wave B calls; deterministic 8-axis decision algorithm; no LLM-side hand-rolling. v1.8.1+ adds Wave A decode (when reference VIN supplied) for drivetrain/fuel_type facet inheritance, year-range fallback, dealer-name normalization, multi-undercut Key Signal, and aggregate-level heterogeneity detection.

## Before you start

1. **Load the profile.** Run `scripts/load_profile.py` (reads `marketcheck-profile.md`, parses YAML frontmatter + JSON body). Non-zero exit → halt and ask the user for the minimum inputs (ZIP / postcode + country). Never proceed without a parsed profile.

2. **Confirm the profile.** First user-facing line is always: `Using profile: <dealer.name>, <ZIP or postcode>, <country>`.

3. **Branch on country.**
   - `country == "US"` → the workflows below.
   - `country == "UK"` → read `references/country-uk.md`. UK has no VIN decoder, no ML predictor, no `get_sold_summary`; `search_uk_active_cars` + `search_uk_recent_cars` are the only tools, comp median substitutes as the price anchor.
   - `country == "CA"` → **halt** with: *"Competitive Pricer does not yet support Canada. The skill is US + UK only — contact support if CA workflows are needed."* The loader normalises CA profile fields but the MCP tool surface is US-centric; continuing would produce cross-border-misleading results. Re-visit when `search_ca_*` tools ship.
   - Any other country → halt with the same US-or-UK-only message.

4. **Compute session values.**
   - `radius_mi_clamped` — **read verbatim from `profile.session.radius_mi_clamped`** emitted by `scripts/load_profile.py` (which pre-clamps `min(default_radius_miles, 100)`, the `search_past_90_days` hard cap). Never re-derive inline. Thin comp sets degrade to a thin-market block rather than triggering a silent widen; per-workflow exceptions (e.g. premium-unit auto-widen) are documented in the relevant workflow reference.
   - `state = profile.location.state` — required by `get_sold_summary`; halt and ask if missing in a US profile.
   - `dealer_type_lower` / `dealer_type_title` / `dealer_type_opposite_lower` — the dealer's own type in two casings, plus the opposite (binary flip of `_lower`). `_lower` is the `dealer_type` arg on every PRIMARY call (`search_active_cars`, `predict_price_with_comparables`); `_opposite_lower` is the `dealer_type` arg on every CONTEXT call in the dual-prediction pattern (W1 step 2, W2 per-VIN, CPO branch). `_title` is used for the human-readable PRIMARY / SECONDARY label in rendered output (`Franchise` / `Independent`; see `assets/output-template.md`). All three are pre-computed in the profile `session` block by `scripts/load_profile.py` — read them verbatim, never re-derive per call. **If any of the three is `None` (profile has no dealer_type), halt before the first MCP call with: *"Your profile has no dealer_type set. Are you a franchise or independent dealer?"* Apply the answer for the rest of the session, suggest the user update their profile. Never proceed without a dealer_type — it anchors channel_stats, the dual-prediction pattern, and the CPO branch.**
   - `car_type = profile.preferences.default_inventory_type`:
     - `"used"` or `"new"` → use directly on every search.
     - `"both"` → **halt and ask the user: "Price check on used or new?"** before any MCP call. Apply the answer for the rest of the session. The skill never mixes new and used data in a single pricing section.
     - **If the user's answer is not exactly `used` or `new`** (e.g. "whichever", "both again", "either"), re-ask once with the same prompt. On a second non-answer, default to `"used"` and emit a Data Quality Notes event (f) noting the defaulted value.
   - `dom_thresholds = profile.preferences.dom_thresholds` → `fresh_max_days`, `aging_max_days`. Two thresholds define three buckets: **Fresh** (`0 ≤ dom ≤ fresh_max_days`), **Aging** (`fresh_max_days < dom ≤ aging_max_days`), **Stale** (`dom > aging_max_days`, open-ended — there is no `stale_max_days` and none is needed). Drives the DOM distribution block and age-based action recommendations. Default to `{fresh: 30, aging: 60}` if absent.

5. **Payload-shaping defaults** — every `search_active_cars` / `search_past_90_days` / UK-search call passes:
   - `fetch_all_photos=false`, `include_mc_dealership_object=false`, `include_finance=false`, `include_lease=false`, `include_relevant_links=false` — always off. Big-payload knobs; the skill never renders the fields they gate.
   - `include_build_object=true` on **listing-rendering fetches** (steps piped through `parse_search.py` that feed the 8-col table + `comp_stats.py`). The four spec fields (`body_type`, `drivetrain`, `engine`, `transmission`) live **exclusively** in the `build` sub-object — the listing root never carries them. `include_build_object=false` makes those fields definitively null on every comp row; the display-only spec subtitle won't render. `false` on stats-only (`rows=0`) calls where no listings are returned.
   - `include_dealer_object=true` on listing-rendering fetches (needed for the F/I Type column and `comp_stats.channel_stats`). `false` on stats-only calls.
   - `rows=<exactly what the output will render>` — never over-fetch.

6. **Working directory.** All intermediate files (raw MCP responses, parsed outputs, merged comps, comp_stats I/O) are written to `/tmp/marketcheck/<session.run_id>/`, where `session.run_id` is auto-generated by `scripts/load_profile.py` on first invocation and emitted in the profile's `session` block. Each skill flow gets a unique `run_id` (`cpr-<epoch>-<8-hex>` format), so two concurrent invocations never collide on shared paths. The directory is created lazily — `persist_response.py` calls `mkdir -p` on its first write, or the agent can `Write` files there directly (`mkdir -p` is idempotent). Files are session-local and regenerated each run. Always read `session.run_id` from the loaded profile when assembling paths; never hardcode the legacy `cpr-run` subdirectory.

7. **Price-filter convention.** Every `search_*` call — sorted listing pulls (`rows≥1`) AND stats-only (`rows=0`) calls — passes `price_range="1-*"`. The API silently excludes null-price rows from `stats.price.{mean, median, percentiles}` but counts them in `num_found`, so without the filter every downstream consumer of `num_found` (MoS denominator `sold_count_90d`, drop/raise rates in `aggregate_w5_signals.py`, market-record counts) is biased. `parse_search.py` also filters client-side on `price in {0, null, missing}`. The user never sees a $0 row.

8. **Session continuity.** Session values (`dealer_type_lower` / `_title` / `_opposite_lower`, `radius_mi_clamped`, `profile_path`, `run_id`) live in the profile's `session` block emitted by `scripts/load_profile.py`. Read them verbatim; never re-derive inline. If the conversation approaches compaction, re-run `scripts/load_profile.py` — values are idempotent and deterministic from the profile, so a re-read is safe at any step. **The exception is `session.run_id`** — re-running `load_profile.py` would emit a *new* random value, orphaning the scratch directory the earlier `Write` calls used. To preserve scratch-directory continuity across a re-load (e.g., after compaction), pass `--run-id <previously-emitted>` to `load_profile.py`; the same value flows back into `session.run_id`. The path-traversal-safe override mirrors the existing `--car-type-override` pattern.

9. **Input-format parsing.** User-supplied asking price accepts any of: `27000`, `$27000`, `$27,000`, `27,000`, `27k`, `27K`. Currency symbols and commas are stripped; trailing `k`/`K` multiplies by 1000. Reject negative or zero values with a halt. Mileage accepts plain integer or `96,619` form (strip commas).

## Facet discipline

Pass decoded `model` and `trim` **verbatim** to every search call — never concatenate. If decode returns `model="RX"` + `trim="350"`, pass those two strings, never `model="RX 350"`. If a first filtered search returns `num_found == 0`, read `references/facet-discovery.md` and retry once with a facet-discovery call. Cache the resolved `{make, model, trim}` tuple in your scratchpad for the remaining calls in the session — don't re-discover per call.

**Trust-verbatim is casing-sensitive.** A YMMT tuple is "trusted-casing" only when (a) it came from a successful `decode_vin_neovin` + `parse_decode` with `ok=true`, or (b) a prior facet-discovery call in the same session resolved the casing. **User-typed free-form YMMT (e.g. "honda accord sport") is NOT trusted-casing** — run facet discovery once to normalize casing before any filtered search. Details in `references/facet-discovery.md`.

## Truncation handling

Truncation signature: `Error: result (N chars) exceeds maximum allowed tokens. Output has been saved to <path>`. The saved file wraps the real response as `{"result": "<stringified JSON>"}`.

Default recovery: pass `--file <path>` to the relevant parser. Every parser (`parse_decode.py`, `parse_predict.py`, `parse_search.py`, `parse_sold_summary.py`, `parse_history.py`) unwraps the envelope and extracts canonical fields.

If a parser reports `ok=false` (critical field missing even after unwrap), render a caveat line for the affected block (e.g. `"Franchise MarketCheck Price: unavailable (prediction call truncated; using comp median as anchor)"`) and continue. Do NOT halt the whole workflow for one failed call. `references/truncation-recovery.md` documents the rare deep-truncation subagent template.

## Comp-set integrity

Rules enforced on every comp-using workflow:

- **Subject VIN exclusion.** Always pass the subject VIN to `parse_search.py` via `--exclude-vins`, and again to `comp_stats.py` via `exclude_vins`. The user's own unit must never appear as its own comp. A **shadow listing** — the subject VIN appearing at a *different* dealer in the active comp set — is exactly what this filter catches; `parse_search` counts such hits in `filtered_out.self_vin`. When that count is non-zero, log a Data Quality Notes event (c) with the shadow-dealer names so the user knows their VIN is out there elsewhere.

- **Variant consistency** is the **server's** responsibility, not the skill's. Pass decoded `make`, `model`, and `trim` verbatim and trust the server's facet match to return the correct line-variant. Decoded `body_type`, `drivetrain`, `engine`, and `transmission` are carried on each normalised listing as **display-only** metadata (rendered on comp listings and in the subject's Decoded Specs block when present) — they are NOT used as filters, NOT passed as API params, and NOT consumed by `comp_stats.py`.

- **MoS matching filters.** The active-inventory call and the sold-90-day call used for Months-of-Supply MUST share identical `{year, make, model, trim, car_type, zip, radius}` filter sets. Numerator and denominator must be apples-to-apples.

- **`min_n` threshold.** `comp_stats.py` returns `insufficient: true` when the filtered comp set has fewer than `min_n` rows (default **6**). Below that threshold, the quartile verdict is skipped and the renderer emits a thin-market block instead. The single source for this constant is `comp_stats.DEFAULT_MIN_N`; `build_comp_stats_input.py` imports and forwards it into every `comp_stats` invocation, so both scripts cannot drift. Override via the `min_n` field in the comp_stats input JSON if a workflow needs a tighter or looser gate (rare).

## Parallelization (universal contract)

Every workflow follows the same wave-execution contract, regardless of which calls it issues:

- **A wave is a batch of MCP calls fired in a single agent message** — multiple `tool_use` blocks in one assistant turn, dispatched concurrently by the runtime. The agent emits all calls in the wave together, then waits for the full batch of `tool_result` messages before issuing the next wave.
- **Within a wave, calls share no cross-dependency** on each other's output. A call that needs another call's parsed output (e.g. a search filtered on the decoded YMMT) goes in a *later* wave, not the same one. Calls that take only user inputs + profile + their own VIN argument can fit Wave A.
- **Wait for the entire wave** before issuing the next. Don't pipeline waves. Each wave's parser fan-out (Write → `parse_*.py --file`) runs locally between waves and adds <1s; that's not a wave of its own.
- **Never serialize calls within a wave.** Each serial roundtrip is a ~12s latency add. Five serialized MCP calls cost ~60s; the same five fired together cost ~12s. The whole point of the wave model is that the slowest call in a wave sets the wave's wall clock.
- **Wave A / Wave B / Wave C are workflow-local labels**, not a global call manifest. Wave A is "first parallel batch in this workflow," Wave B is "second," Wave C is "third (rare conditional)." Some workflows have one wave; some have three. The label numbers don't carry meaning across workflows.
- **Wave content lives in the per-workflow reference.** Each `references/w<N>-*.md` defines its workflow's specific wave structure: which calls go in which wave, what conditions trigger conditional waves, what the wall-clock budget is. SKILL.md does NOT enumerate any workflow's calls — read the reference for the workflow you're running.

Latency budget at a glance (real workflow ranges; specific call lists in references):
- Single-wave workflows (W3 trade-in history): ~12s
- Two-wave workflows (W2 batch scan, W4 market distribution, W5 competitor movement v1.8.0+): ~25s
- Three-wave workflows (W1 single-VIN price-check, with conditional Wave C): ~27–30s common path

All would run in 60–144s if their calls were serialized. Every wave is load-bearing to that budget.

## Data quality rule

Treat `dealer_type` as optional on listings. When `include_dealer_object=true` is passed and the field is still absent, render `—` in the Type column. Never heuristic-guess F vs I from the dealer name or domain. `parse_search.py` returns `null` for absent dealer_type; the renderer translates that to `—`.

---

## Workflow 1 — Price-Check Single VIN

Reference workflow. Triggers: "price this VIN", "am I priced right on this one", "check this unit's pricing", "is my number right", etc. Score one VIN against the local active and sold market; produce a sold-anchored verdict + recommended action.

→ Full spec in **`references/w1-price-check.md`**.

---

## Workflow 2 — Batch Competitive Scan

Triggers: "check pricing on my front-line inventory", "batch price check these VINs". Up to 5 VINs inline; halt and recommend `dealer:lot-pricer` above that. **Batch overview / triage** workflow: deterministic per-VIN verdict (quartile-anchored against the local active-listing distribution via `comp_stats.verdict_quartile`), portfolio rollup with action-priority sort. Wave A is identical to W1's Wave A (decode + 2 predicts ± 2 CPO predicts per VIN); Wave B is one `search_active_cars` per unique YMMT tuple with `stats="price,miles,dom_active"`. CPO detection happens via a single up-front collective prompt for the whole batch. No sold-90d, no `get_sold_summary`, no `get_car_history`, no drop scan, no desc tail-pull — for those depths route the specific VIN to W1 via `/price-check <VIN>`. Renders via `assets/w2-output-template.md` (separate from `assets/output-template.md`).

→ Full spec in **`references/w2-batch-scan.md`**.

---

## Workflow 3 — Trade-In VIN Price History

Triggers: "what's the history on this trade", "previous listings for VIN X". **US-only** — halt on UK profiles. **History viewer** workflow: surface the VIN's listing trajectory + dealer-hop / sharp-drop / decertified red flags. Wave A is a single parallel batch — `get_car_history` (with `page=1` + canonical `fields=`) + `decode_vin_neovin`. When the user supplies current odometer and asks for fair-value, Wave A grows by 2 dual-channel `predict_price_with_comparables` calls (PRIMARY + CONTEXT). Dealer-hop count uses `dealer_id`-primary semantics with `dealer_name` fallback (provenance surfaced via `dealer_count_source`). Pagination gaps (`num_found > listing_count`) and null-price baseline shifts are surfaced as DQ events. Renders via `assets/output-template.md` W3 section. W3 does NOT compute trade-in offer math; for full pricing depth route the VIN through W1 via `/price-check <VIN>`.

→ Full spec in **`references/w3-trade-in-history.md`**.

---

## Workflow 4 — Market Price Distribution

Triggers: "what does the market look like for this model", "market distribution for 2022 Camry". **US-only** — halt on UK profiles (route to `references/country-uk.md` W4 analogue at lines 95–103). No subject vehicle — describes the market itself: model-or-trim-level distribution (Price/Mileage/DOM), by-channel split (franchise vs independent medians sourced server-wide from dedicated stats-only calls), cheapest 8 + most-expensive 5 listings, outliers, state-level sold velocity baseline. Wave B is 8 parallel calls (or 7 when trim absent), plus optional Wave A facet discovery. `build_comp_stats_input.py` runs without `--user-price` / `--subject-vin` (relaxed in v1.7.0); `comp_stats.py` emits verdict / gap_vs_median fields as null and the renderer skips the Your Price Position + Verdict blocks. Renders via `assets/output-template.md`.

→ Full spec in **`references/w4-market-distribution.md`**.

---

## Workflow 5 — Competitor Price Movement

Triggers: "who dropped their price", "who is undercutting me", "aggressive competitors near me". **US-only by canonical path** — UK W5 analogue in `references/country-uk.md` lines 105–107. **No subject vehicle** — surface recent price drops, raises, dealer-grouping for inventory pressure, aggressive-raisers Key Signal, and an optional response matrix (match/split/hold) when the user supplies a reference unit. Wave B is 4 parallel calls (drop scan + raise scan + denominator + sold-90d for MoS), plus optional Wave A facet discovery. The 9-col Drop table is rendered via `render_comp_set_table.py --mode=9col-drops` (v1.8.0+); aggregations + 8-axis decision algorithm come from `aggregate_w5_signals.py`. No LLM-side hand-rolling on any aggregate. Deterministic, testable, audit-trail-emitting.

→ Full spec in **`references/w5-competitor-movement.md`**.

---

## Output

W1 / W3 / W4 / W5 render via `assets/output-template.md`. **W2 renders via `assets/w2-output-template.md`** — its own single-source-of-truth file with a different block structure (per-VIN card + portfolio rollup) suited to batch-overview triage. Each template is the **single source of truth** for block structure, table schemas, verdict wording, and self-check rules for the workflows it covers. Do not inline block definitions here.

Render rules:

- Standard 8-col table (`Dealer | Type | Price | Miles | DOM | Distance | vs Mkt Median | Price Drop?`) on every competitive-listing render, regardless of workflow.
- Sort ascending by price unless the workflow explicitly says otherwise (Most-Expensive in W4, aggressive-raiser list in W5).
- Mark the row closest to the user's asking price with `← You`.
- Empty/missing `dealer_type` renders as `—`. Never guess.
- Filtered-out counts from `parse_search.py` / `comp_stats.py` (self-VIN, variant, invalid-price) surface as a footnote under the comp-set table if non-zero.

### Data Quality event log

Accumulate a running list of events across every workflow; feed it into the Data Quality Notes section at render time. Track:

- (a) **MCP tool errors or non-200 responses recovered from** — tool name, `error_type`, recovery path.
- (a1) **Facet-discovery retries** — when a filtered search returned 0 results and a facet lookup resolved the correct casing. Log the original filter value, the resolved value, and the tool. Distinguishes "empty market" (no retry possible) from "silently mis-cased filter" (resolved).
- (b) **Truncation-envelope unwraps** via `--file <path>` — which parser, which tool.
- (c) **Subject VIN found in active comp set at a different dealer** (shadow listing) — dealer name + distance; confirm exclusion from `comp_stats` input.
- (d) **Non-zero `filtered_out` counts** from parsers — totals by category (self-VIN, variant, invalid-price).
- (e) **Fallback source attribution** — when a computed stat used a secondary source (e.g. mileage distribution derived from `predict_price_with_comparables.recent_comparables` because `search_past_90_days` rejected a multi-token `stats=`).
- (f) **Parameter adaptations** — when a documented parameter wasn't accepted and a substitute was used (e.g. `price_range="1-*"` in place of `price_min=1`).
- (g) **Workflow branch skipped by design** — an optional or conditional branch was not run because its gate was not met. Include the branch name and the reason. Examples: *"CPO branch skipped: user stated non-CPO"* · *"Thin-market auto-widen not triggered: num_found ≥ 15"* · *"Shadow-listing follow-up: no shadows detected"* · *"Same-Channel View skipped: channel_stats.primary.n < 2"*. Keeps the audit trail complete without forcing non-events into the (a) MCP-error category.

If the list is empty, omit the section entirely (do not render an empty header).

## Self-check

The 12-item verification checklist lives in `assets/output-template.md`. It is an **internal guardrail** — the model runs each check silently before returning and does NOT render the full checkbox grid to the reader.

- **All applicable checks pass** → emit a single footer line, e.g. `✓ Verified: profile, dual pricing, 8-col schema, MoS filters, no $0 rows, percentile direction.` Abbreviate to 5–7 items; drop N/A from the summary.
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated in the output to compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.
