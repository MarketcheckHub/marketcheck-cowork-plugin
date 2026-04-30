---
name: vehicle-appraiser-updated
description: Defensible comparable-backed valuation. Returns a low/mid/high value range with confidence band (Low <5 comps, Medium 5-14, High 15+) anchored on sold-90d transactions when ≥5 retail-sold comps are available; active comp distribution is the fallback. Covers five appraisal workflows — Full Comparable Appraisal (formal report with cited comps), Trade-In Quick Appraisal (≤25s wall clock for desk-side use), Wholesale-vs-Retail Spread (franchise vs independent dealer_type comparison + recommended trade-in offer), Regional Price Variance (multi-ZIP arbitrage map), and Historical Value Trajectory (per-VIN listing/price history with depreciation rate). Every output shows dual-channel franchise + independent predicted prices, sold-90d transaction evidence, CPO premium when applicable, and a methodology block citing every comparable used. Use when an appraiser, insurance adjuster, fleet analyst, used-car manager, or trade-in desk asks "appraise this vehicle", "what's it worth", "trade-in value", "fair market value", "wholesale vs retail", "appraisal report", "how much should I offer", "vehicle valuation", "comparable analysis", "price trajectory", "depreciation rate", "regional value variance", "trade-in offer range", "insurance total-loss value", or any defensible-valuation intent — or raises any appraisal-diagnostic intent without naming the skill.
version: 1.0.0
---

# Vehicle Appraiser

Given a VIN (or YMMT) + mileage + condition + purpose, score the vehicle's defensible value against the local market using ML prediction + live active comps + sold-90d retail-transaction evidence, then emit a low/mid/high value range with confidence band and full methodology citation. The appraisal anchors on sold-90d retail transactions when ≥5 retail-sold comps are available (what buyers actually paid); the active-listing quartile distribution is the fallback bracket.

Five workflows map to distinct appraisal intents:

- **W1 — Full Comparable Appraisal** — *"appraise this vehicle, formal report"* (reference workflow; deep diagnostic for insurance, fleet, total-loss; cites every comp by VIN, miles, dealer, distance; emits sold transaction evidence)
- **W2 — Trade-In Quick Appraisal** — *"what's it worth, customer at the desk"* (≤25s wall clock; predicted retail / wholesale / spread / offer range; top 5 comps; compact card output; routes to W1 for depth)
- **W3 — Wholesale-vs-Retail Spread** — *"how should I price this trade"* (franchise vs independent dealer_type split; recommended offer range positioned between wholesale and retail, biased per purpose; recon-cost grossing-up when supplied)
- **W4 — Regional Price Variance** — *"compare value across markets"* (multi-ZIP comparison, 2-6 ZIPs; arbitrage flag at >5% delta; state-baseline context from `get_sold_summary`; no subject vehicle)
- **W5 — Historical Value Trajectory** — *"what's this VIN's price history"* (`get_car_history`-backed trajectory; cumulative depreciation rate; dealer-hop / sharp-drop / decertified red flags; optional ML fair-value when current odometer supplied)

## Before you start

1. **Load the profile.** Run `scripts/load_profile.py` (reads `marketcheck-profile.md`, parses YAML frontmatter + JSON body). Non-zero exit → halt and ask the user for the minimum inputs (ZIP / postcode + country). The skill works without a full profile; ZIP and country are the floor.

2. **Confirm the profile.** First user-facing line is always: `Using profile: <dealer.name>, <ZIP or postcode>, <country>`.

3. **Branch on country.**
   - `country == "US"` → the workflows below.
   - `country == "UK"` → read `references/country-uk.md`. UK has no VIN decoder, no ML predictor, no `get_sold_summary`, no `get_car_history`. W3 and W5 halt on UK; W1, W2, W4 have UK adaptations.
   - `country == "CA"` → **halt** with: *"Vehicle Appraiser does not yet support Canada. The skill is US + UK only — contact support if CA workflows are needed."*
   - Any other country → halt with the same US-or-UK-only message.

4. **Compute session values.**
   - `radius_mi_clamped` — read verbatim from `profile.session.radius_mi_clamped` emitted by `scripts/load_profile.py`.
   - `state = profile.location.state` — required by `get_sold_summary` (W1, W3, W4); halt and ask if missing in a US profile when those workflows are invoked.
   - `dealer_type_lower` / `dealer_type_title` / `dealer_type_opposite_lower` — pre-computed in the profile `session` block. **If any is `None`, halt** before the first MCP call: *"Your profile has no dealer_type set. Are you a franchise or independent dealer?"*
   - `car_type = profile.preferences.default_inventory_type`:
     - `"used"` or `"new"` → use directly.
     - `"both"` → halt and ask: *"Appraisal for used or new?"* before any MCP call.
   - `dom_thresholds = profile.preferences.dom_thresholds` → drives the DOM Distribution buckets in W1 / W3.

5. **Payload-shaping defaults** — every `search_active_cars` / `search_past_90_days` / UK-search call passes:
   - `fetch_all_photos=false`, `include_mc_dealership_object=false`, `include_finance=false`, `include_lease=false`, `include_relevant_links=false` — always off.
   - `include_build_object=true` on listing-rendering fetches; `false` on stats-only (`rows=0`) calls.
   - `include_dealer_object=true` on listing-rendering fetches; `false` on stats-only calls.
   - `rows=<exactly what the output will render>` — never over-fetch.

6. **Working directory.** All intermediate files (raw MCP responses, parsed outputs, merged comps, comp_stats I/O, appraisal-band I/O, regional-variance I/O) are written to `/tmp/marketcheck/<session.run_id>/`, where `session.run_id` is auto-generated by `scripts/load_profile.py`. Each skill flow gets a unique `run_id`. The directory is created lazily.

7. **Price-filter convention.** Every sorted listing search passes `price_range="1-*"`. `parse_search.py` also filters client-side on `price in {0, null, missing}`. The user never sees a $0 row.

8. **Session continuity.** Session values live in the profile's `session` block emitted by `scripts/load_profile.py`. Read them verbatim. If the conversation approaches compaction, re-run `scripts/load_profile.py --run-id <previously-emitted>` to preserve the scratch directory.

9. **Input-format parsing.** Mileage accepts plain integer or `96,619` form (strip commas). Asking price (when supplied for W3) accepts any of: `27000`, `$27000`, `$27,000`, `27,000`, `27k`, `27K`. Reject negative or zero values with a halt. Condition is one of `Clean` / `Average` / `Rough` (case-sensitive); unknown values default to `Average` with a Key Signal note.

## Facet discipline

Pass decoded `model` and `trim` **verbatim** to every search call — never concatenate. If decode returns `model="RX"` + `trim="350"`, pass those two strings, never `model="RX 350"`. If a first filtered search returns `num_found == 0`, read `references/facet-discovery.md` and retry once with a facet-discovery call. Cache the resolved `{make, model, trim}` tuple for the remaining calls in the session.

**User-typed free-form YMMT (e.g. "honda accord sport") is NOT trusted-casing.** Run facet discovery once to normalize casing before any filtered search.

## Truncation handling

Truncation signature: `Error: result (N chars) exceeds maximum allowed tokens. Output has been saved to <path>`. Default recovery: pass `--file <path>` to the relevant parser. Every parser unwraps the `{"result": ...}` envelope transparently. See `references/truncation-recovery.md` for the full recipe and the rare deep-truncation subagent template.

## Comp-set integrity

Rules enforced on every comp-using workflow:

- **Subject VIN exclusion.** Always pass the subject VIN to `parse_search.py` via `--subject-vin`. Shadow listings (subject VIN at a different dealer) are caught and surfaced in DQ event (c).
- **Variant consistency** is the **server's** responsibility. Pass decoded `make`, `model`, `trim` verbatim and trust the server's facet match.
- **MoS matching filters.** The active-inventory call and the sold-90-day call used for Months-of-Supply MUST share identical `{year, make, model, trim, car_type, zip, radius}` filter sets.
- **`min_n` threshold.** `comp_stats.py` returns `insufficient: true` when the filtered comp set has fewer than `min_n` rows (default 6). Below that threshold, the appraisal band falls to `predict_only` (when ML available) or null.

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
- W4 (1-2 waves): ~25s
- W5 (single-wave): ~12s (history+decode) or ~15s (with optional fair-value branch)

Wave content lives in the per-workflow reference. Each `references/w<N>-*.md` defines its workflow's specific wave structure.

## Data quality rule

Treat `dealer_type` as optional on listings. When `include_dealer_object=true` is passed and the field is still absent, render `—` in the Type column. Never heuristic-guess F vs I from the dealer name or domain.

---

## Workflow 1 — Full Comparable Appraisal

Reference workflow. Triggers: "appraise this vehicle", "appraisal report", "fair market value", "insurance total-loss value", "defensible valuation". Score one VIN against the local active and sold market; emit a low/mid/high value range with confidence band, sold transaction evidence, methodology, and cited comparables.

→ Full spec in **`references/w1-full-appraisal.md`**.

---

## Workflow 2 — Trade-In Quick Appraisal

Triggers: "trade-in value", "what's it worth quick", "how much should I offer", "customer at the desk". Single-VIN, ≤25s wall clock. Predicted retail / predicted wholesale / spread / recommended offer range / top 5 comps / confidence band. CPO branch when applicable. **Halts and routes to W1** for sold-anchor depth or formal report. Renders via `assets/w2-output-template.md` (separate from `assets/output-template.md`).

→ Full spec in **`references/w2-trade-in-quick.md`**.

---

## Workflow 3 — Wholesale-vs-Retail Spread

Triggers: "wholesale vs retail", "what's the spread", "trade-in offer range", "franchise vs independent". **US-only** — halt on UK profiles. Single-VIN dealer_type split: dual ML predicts (franchise + independent) + dual active comp pulls + sold-90d evidence. Emits the spread $/% line, recommended trade-in offer range (78-85% of franchise predicted retail; biased per purpose), optional recon-cost grossing-up. Two side-by-side comp tables (franchise / independent).

→ Full spec in **`references/w3-wholesale-vs-retail.md`**.

---

## Workflow 4 — Regional Price Variance

Triggers: "compare values across markets", "regional price difference", "fleet relocation analysis", "arbitrage opportunity". **No subject vehicle, no asking price.** YMMT + 2-6 ZIPs. Wave B fires N stats-only `search_active_cars` (one per ZIP) + 1 `get_sold_summary` for state-baseline context. Aggregated via `compute_regional_variance.py`. Output: per-market summary table, arbitrage flags at >5% delta-from-lowest, top-10 states by avg sold price.

→ Full spec in **`references/w4-regional-variance.md`**.

---

## Workflow 5 — Historical Value Trajectory

Triggers: "price history", "VIN history", "depreciation rate", "show me this vehicle's listing trajectory". **US-only** — halt on UK profiles (no `get_car_history`). Single-wave: `get_car_history` + `decode_vin_neovin` + (optional, when miles supplied) 2 dual-channel `predict_price_with_comparables`. Output: chronological trajectory table + cumulative depreciation summary + red flags (multi-dealer churn, sharp drops, decertified) + optional Current ML Fair Value. Routes to W1 for full appraisal.

→ Full spec in **`references/w5-history-trajectory.md`**.

---

## Output

W1 / W3 / W4 / W5 render via `assets/output-template.md`. **W2 renders via `assets/w2-output-template.md`** — its own single-source-of-truth file with a compact card layout suited to desk-side use. Each template is the **single source of truth** for block structure, table schemas, methodology phrasing, and self-check rules for the workflows it covers.

Render rules:

- Standard 8-col table (`Dealer | Type | Price | Miles | DOM | Distance | vs Mkt Median | Price Change`) on every Active Retail Comparables render.
- Sold Transaction Comparables table uses the dedicated 8-col schema (`Dealer | Type | Sold Price | Miles | DOM | Distance | Sale Date | CPO?`) via `render_sold_table.py`.
- Sort ascending by price unless the workflow explicitly says otherwise (Sold Transaction Comparables is sorted descending by sale date — most recent first).
- Mark the row closest to the user's asking price (when supplied) with `← You` in the Active comp tables.
- Empty/missing `dealer_type` renders as `—`. Never guess.
- Filtered-out counts from `parse_search.py` / `comp_stats.py` (self-VIN, variant, invalid-price) surface as a footnote under the comp-set table if non-zero.

### Data Quality event log

Accumulate a running list of events across every workflow; feed it into the Data Quality Notes section at render time. Track:

- (a) **MCP tool errors or non-200 responses recovered from** — tool name, `error_type`, recovery path.
- (a1) **Facet-discovery retries** — when a filtered search returned 0 results and a facet lookup resolved the correct casing.
- (b) **Truncation-envelope unwraps** via `--file <path>` — which parser, which tool. Plus history pagination gap (W5).
- (c) **Subject VIN found in active comp set at a different dealer** (shadow listing) — dealer name + distance.
- (d) **Non-zero `filtered_out` counts** from parsers — totals by category (self-VIN, variant, invalid-price).
- (e) **Fallback source attribution** — when a computed stat used a secondary source.
- (f) **Parameter adaptations** — when a documented parameter wasn't accepted and a substitute was used.
- (g) **Workflow branch skipped by design** — an optional or conditional branch was not run. Examples: *"CPO branch skipped: user stated non-CPO"*, *"Sold transactions table skipped: insufficient sold-90d count"*, *"State baseline skipped: get_sold_summary degraded"*.

If the list is empty, omit the section entirely.

## Self-check

The 14-item verification checklist lives in `assets/output-template.md` (W1/W3/W4/W5) and `assets/w2-output-template.md` (W2). It is an **internal guardrail** — the model runs each check silently before returning and does NOT render the full checkbox grid to the reader.

- **All applicable checks pass** → emit a single footer line (5-7 of the items that were exercised).
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.

The two non-negotiable appraisal-domain rules in the self-check:

1. **Confidence band must match `comp_count_total`** (Low <5, Medium 5-14, High 15+).
2. **Low-confidence appraisals MUST render a value range, not a point estimate** — appraisers / insurance adjusters / fleet analysts depend on this guard for defensibility.
