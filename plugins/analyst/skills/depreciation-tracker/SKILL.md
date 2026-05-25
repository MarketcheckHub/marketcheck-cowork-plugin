---
name: depreciation-tracker
description: Residual-value investment signals for US automotive equity coverage. Four US-only workflows — make/model depreciation curve, body-type / fuel-type segment trends (EV vs ICE), brand residual ranking, and new-vehicle MSRP parity tracker — each producing a BULLISH / BEARISH / NEUTRAL / CAUTION verdict tied to affected OEM tickers. Use when an equity analyst, residual / collateral analyst, or portfolio manager asks "depreciation rate", "value retention", "residual value", "residual forecast", "how fast is it losing value", "which cars hold value", "EV depreciation", "price trend over time", "brand value ranking", "depreciation curve", "MSRP parity", "above sticker", "below sticker", "collateral erosion", "OEM residual exposure", or any depreciation / residual / parity question framed as an investment signal. Prefer pricing-power-tracker for new-vehicle pricing-power deep dives, ev-transition-monitor for EV cohort analysis, earnings-preview for pre-earnings channel checks. US-only.
version: 1.0.0
---

# Depreciation Tracker — Residual-Value Investment Signals (Updated)

> **Date anchor:** Today's date comes from the `# currentDate` system context.
> Compute ALL relative dates from it via `scripts/compute_period_windows.py`.
> Never use training-data dates.

Equity-analyst-facing skill that converts MarketCheck sold-vehicle aggregates
into residual-value investment signals. Four workflows map sold-transaction
trajectories — make/model depreciation, body-type / fuel-type segment trends,
brand-level retention tier, and new-vehicle MSRP parity — to a deterministic
BULLISH / BEARISH / NEUTRAL / CAUTION verdict per metric (rolled up to
BULLISH / BEARISH / NEUTRAL / MIXED at the headline). Every numeric block —
retention %, monthly rate, tier classification, parity direction, segment
classifier — is computed by Python scripts in `scripts/`, never by the
model. Same inputs always produce the same verdict.

The framing is *channel check for residual / OEM-margin / lending-stock
exposure*: aggregated sold prices tell you which way OEM pricing power and
lender-collateral values are moving weeks before management or the rating
agencies acknowledge it.

## Workflows

- **W1 — Make/Model Depreciation Curve** — "how fast is the RAV4 losing value", "depreciation signal for Ford trucks", "residual curve for a 2023 Tacoma". Multi-period sold-price trajectory (1yr / 6mo / 90d / 60d / current) + monthly + annualized depreciation rate + 4-band investment-signal verdict + curve-shape classifier (linear / accelerating / stabilizing). Used-vehicle workflow.
- **W2 — Segment Value Trends** — "are SUVs holding value better than sedans", "EV vs ICE depreciation — investment implications", "segment retention ranking". Body_type and/or fuel_type cross-period comparison, EV-vs-ICE delta with affected-ticker mapping, per-segment classifier (appreciating / stable / soft / accelerating_dep) → BULLISH / NEUTRAL / CAUTION / BEARISH.
- **W3 — Brand Residual Ranking** — "which brands hold value best", "rank OEMs by residual strength", "Toyota vs Honda retention". Per-make retention % over a 6-month window + 4-tier classification (T1 ≥ 98% → BULLISH; T2 [95, 98) → NEUTRAL; T3 [90, 95) → CAUTION; T4 < 90% → BEARISH) + tier-jump detection, tickers attached. Used-vehicle workflow.
- **W5 — MSRP Parity Tracker** — "which new cars are selling over sticker", "are markups coming down", "OEM pricing power signal", "incentive activity". New-vehicle `price_over_msrp_percentage` rollup + above / at / below status + cross-period direction (flipped_above / flipped_below / deepening / narrowing / stable), tickers aggregated for the OEM read. New-vehicle workflow.

(W4 — Geographic Depreciation Variance is intentionally **out of scope** for
the analyst port. The dealer-side workflow exists for sourcing arbitrage
which is not an analyst investment signal. The `tracked_states` profile field
lets W1/W2/W3/W5 scope state-locally when wanted.)

## Built-in OEM ticker ↔ make mapping

The 13-OEM mapping used by every workflow lives in
`references/ticker-mapping.md`. SKILL.md does not re-state the table.

## Before you start

1. **Profile load (inline, no script).** Read the `marketcheck-profile.md` project memory file. Parse YAML frontmatter and the JSON body. Frontmatter wins on conflict (it is the curated view); the JSON body provides fields the frontmatter omits. Extract:
   - `location.country` — required. If country != `"US"`, halt per `references/country-uk.md`. No UK substitute path exists for any of the four workflows.
   - `analyst.tracked_tickers` — optional. When present, used as the comparison cohort in the Comparison Context block and to highlight subject vs. cohort in W3 / W5.
   - `analyst.tracked_makes` — optional. When the user did not name a make/model, default to the union of `tracked_makes` (W3) or to the top of the ranking (W5).
   - `analyst.tracked_states` — optional. Empty → national rollup (omit `state` on the call). Single value → pass that state. Multi-value → prompt the user once for which state to scope to (or "all").
   - `analyst.benchmark_period_months` — optional (default 3). Drives the W2 / W5 prior-period offset. W3 uses a fixed 6-month window (residual is a 6-month concept).
   - `analyst.focus` — optional. When `focus="lending"`, the Investment Thesis block leads with the lender / leasing-stock implication. When `focus="oem"`, it leads with the OEM-ticker implication.

   If the profile is missing or unparseable → prompt the user for a make/model (W1) OR a state (W2 / W3 / W5). No halt.

2. **Confirm the profile.** First user-facing line is always: `Using profile: <user.company or user.name>, <state | "national">, US`. When there is no profile, use `Using profile context: <derived state | "national">, US`.

3. **Compute date windows.** Run `scripts/compute_period_windows.py --today <currentDate>` ONCE at workflow entry. Cache the returned `periods` array; each call's `date_from` / `date_to` comes from the cached entry. Period set per workflow:
   - W1 → default 5-period: `current,60d,90d,6mo,1yr`.
   - W2 / W5 → `current,<benchmark_period_months>mo` (default `current,3mo`; the script's existing `90d` token approximates "3 months back" for v1.0.0 — see `references/sold-summary-safety.md §Period customization` for the policy and future extension).
   - W3 → `current,6mo` (fixed; residual is a 6-month concept).
   - **Never hand-compute dates.** Mis-aligned dates pass local validation and return HTTP 422 from upstream.

4. **Resolve inventory_type.** Each workflow has a fixed channel — the analyst profile has no `default_inventory_type` field, so SKILL.md sets it per workflow:
   - W1 / W2 / W3 → `inventory_type="Used"` (depreciation / retention are used-vehicle semantics).
   - W5 → `inventory_type="New"` (MSRP parity is a new-vehicle concept).
   - If the user explicitly asks for the opposite channel on a Used-only workflow, halt-redirect to W5 (and vice versa).

## Script invocation discipline

Scripts in `scripts/` are black boxes. Their complete I/O contract — CLI
flags, stdin shape, stdout shape, error envelopes, edge cases — lives in
`references/script-contracts.md`. Treat that file as authoritative; the
script source is implementation detail and never needs to enter your
context.

The 9 scripts: `_common.py`, `compute_period_windows.py`,
`parse_sold_summary.py`, `depreciation_curve.py`, `brand_retention.py`,
`segment_compare.py`, `msrp_parity.py`, `aggregate_signals.py`,
`render_depreciation_table.py`.

**Forbidden:**
- `Read` tool on any `scripts/*.py` file.
- `cat` / `head` / `tail` / `sed` / `awk` / `grep` on script source via Bash.
- Re-implementing script logic inline (no model-side weighted-mean math, no
  inline tier-classification, no inline parity-direction inference). If the
  contract is missing a field, surface it as a doc bug — do not patch with
  hand-rolled code.

**Why:** Each unread script saves ~100-500 lines of context. Reading source
tempts inline reimplementation, which silently diverges from the script's
real behavior and breaks the "same inputs always produce the same verdict"
guarantee that anchors this skill's value to equity analysts.

**Right pattern (stdin pipe, no scratch file):**
```bash
echo '<mcp-response-string>' | python scripts/<script>.py [--flags]
```

**Wrong patterns:**
```bash
Write(/tmp/marketcheck/<run_id>/sold-current.json, <response>)   # forbidden — no scratch files
python scripts/<script>.py --file /tmp/...                       # forbidden when small enough to inline
Read(scripts/parse_sold_summary.py)                              # forbidden — see contracts file
```

The `--file <path>` flag on the parsers exists ONLY for the rare case where
the MCP runtime itself saves an oversized response to disk and returns an
`Output saved to <path>` error string. In that case — and only that case —
pipe the runtime-written path to `--file`. You never create those files
yourself.

Other skills in the broader plugin suite use a `/tmp/marketcheck/<run_id>/`
scratch dir because their VIN-level batch payloads need cross-wave state
survival. **This skill is different.** All workflows complete in a single
wave (W1 dropped its optional rep-VIN + decode pass); payloads are
aggregated and small; intermediate state never needs to leave the model's
context.

## Tool surface

This skill calls **one** MCP tool:

- **`get_sold_summary`** — US-only sold-vehicle aggregates. Every workflow uses it. See `references/sold-summary-safety.md` for parameter discipline (always-set: `inventory_type`, `limit=5000`, month-aligned `date_from` / `date_to`, minimal `ranking_dimensions`; never-set: `dealer_type` — silent data suppression).

Tools deliberately not used:

- `decode_vin_neovin` — would only be needed for the W1 MSRP-anchor path; that path was dropped in this port (prior-period retention is sufficient as an investment signal and sidesteps the chronic ~150KB decode-envelope truncation).
- `search_active_cars` — no per-listing data is needed by any of the four workflows. (Used only for `make_model_not_found` facet-discovery recovery; see `references/facet-discovery.md`.)
- `predict_price_with_comparables`, `get_car_history`, `search_past_90_days`, `search_uk_*` — not used.

## Parallelization (universal contract)

Every workflow follows the wave-execution contract:

- **A wave is a batch of MCP calls fired in a single agent message** (multiple `tool_use` blocks). The runtime dispatches them concurrently.
- **Within a wave, calls share no cross-dependency** on each other's parsed output. Calls that need another call's output go in a later wave.
- **Wait for the entire wave** before issuing the next.
- **Never serialize calls within a wave** — a wave's wall clock is set by its slowest call.

**Upstream rate-limit ceiling: ≤5 concurrent `get_sold_summary` calls per agent message.** The API at `api.marketcheck.com` returns HTTP 429 above that (verified live 2026-05-14; see `references/sold-summary-safety.md §Upstream rate limit`). Workflows that need more than 5 calls split into sequential sub-batches of ≤5; within a sub-batch, calls fire in parallel.

Wall-clock budget at a glance:
- W1: Wave A ≈ 12-15s (5 parallel sold-summary calls — under the rate-limit ceiling).
- W2: Wave A ≈ 12-15s (body cross-period = 2 calls; optional EV/ICE/Hybrid passes add up to 6 more calls — sub-batched if total > 5).
- W3: Wave A ≈ 12-15s (current + prior + volume = 3 parallel).
- W5: Wave A ≈ 12-15s (current + prior + volume = 3 parallel).

Per-workflow wave structure lives in the per-workflow reference files.

## Truncation handling

Most calls in this skill do not truncate (aggregated rollups, small payloads with `top_n ≤ 30`). If any response truncates:

- The MCP layer emits `Error: result (N chars) exceeds maximum allowed tokens. Output saved to <path>`.
- Pipe the saved path to `parse_sold_summary.py --file <path>`. The shared `_common._maybe_unwrap` helper handles the envelope.
- **`get_sold_summary` is the only MCP tool whose payload is NOT envelope-wrapped** (raw `{success, service, data}`); `parse_sold_summary.py` handles both shapes. See `references/script-contracts.md §parse_sold_summary` for the unwrap branch.
- Log DQ event (b) when a truncation envelope was unwrapped.

## Sold-summary safety

Hard-won rules — full detail in `references/sold-summary-safety.md`. Non-negotiables on every `get_sold_summary` call:
- Always set `inventory_type` (`Used` / `New`) explicitly. Omitting silently defaults to upstream's default channel.
- Always set `limit=5000`. Default `1000` silently truncates multi-dimensional results.
- Always set minimal `ranking_dimensions` per workflow (see safety doc; avoid the default 3-dim `make,model,body_type`).
- **Never** pass `dealer_type` (silent data suppression — verified live).
- Always month-align `date_from` / `date_to` via `compute_period_windows.py`.
- Sub-batch any wave that would exceed 5 concurrent calls (upstream HTTP 429 ceiling).
- Branch on `parse_sold_summary.error_type` per the recovery table.

## Facet discipline

`get_sold_summary` does not expose a `facets` parameter. When a call returns `error_type="make_model_not_found"`, recover via `search_active_cars` facet discovery per `references/facet-discovery.md`, then re-issue the failed call with the resolved casing. Cache the resolved tuple — every period's call in the same workflow uses the cached value.

`year` and `trim` are NOT parameters on `get_sold_summary` — they are NOT facet-discoverable. The skill aggregates across all years and trims; the output template renders an explicit scope qualifier.

## Data quality event log

Accumulate a running list of events across the workflow; render in a "Data Quality Notes" section if non-empty:

- **(a)** MCP tool errors / non-200 responses recovered from — tool name, `error_type`, recovery path. Specifically for `parse_sold_summary` failures: `make_model_not_found`, `validation_dimension_limit`, `network_422`, `network_5xx`, `validation`, `unknown`.
- **(a1)** Facet-discovery retries — when a `get_sold_summary` call errored `make_model_not_found` and a `search_active_cars` facet lookup resolved the correct casing.
- **(b)** Truncation envelope unwraps via `--file <path>` — which parser, which tool.
- **(c)** Make / model resolution by fuzzy match (user-confirmed) — log input + canonical + match path.
- **(d)** Ticker mapping miss — a make surfaced by the data has no entry in `references/ticker-mapping.md` and is rendered as `[no tracked ticker]`.
- **(e)** Fallback source attribution — e.g., period omitted from curve; prior-period anchor used because MSRP path is intentionally disabled.
- **(f)** Workflow branch skipped by design — Hybrid pass not requested in W2; `benchmark_period_months` defaulted because the user did not specify.
- **(g)** Sub-batch split — wave exceeded the 5-concurrent ceiling and was split into N sub-batches.

If the list is empty, omit the section entirely.

## Data quality rule

Treat every period's failure as recoverable, not fatal. A failed `get_sold_summary` call on one period of a multi-period curve omits that period from the table — it does not halt the workflow. Surface every degradation in the Data Quality Notes section.

---

## Workflow 1 — Make/Model Depreciation Curve

Multi-period sold-price trajectory + 4-band investment-signal verdict (anchored on the most-recent monthly depreciation rate) + curve-shape classifier (linear / accelerating / stabilizing). 5 parallel `get_sold_summary` calls in a single wave. **Used-vehicle workflow** — halts on user-supplied `inventory_type=new` and redirects to W5 (MSRP Parity).

→ Full spec in **`references/w1-curve.md`**.

---

## Workflow 2 — Segment Value Trends

Body_type and/or fuel_type cross-period comparison. EV-vs-ICE explicit pass when requested. Hybrid optional (only when the user asks). Single-wave with up to 6 parallel calls (body cross-period = 2; EV cross-period = 2; ICE cross-period = 2; Hybrid cross-period = 2 if requested) — sub-batched into 2 sub-batches when the total exceeds 5.

→ Full spec in **`references/w2-segment-trends.md`**.

---

## Workflow 3 — Brand Residual Ranking

Per-make retention % over a fixed 6-month window + 4-tier classification + tier-jump detection + ticker overlay. Single-wave; 3 parallel `get_sold_summary` calls (current avg + prior avg + current volume). **Used-vehicle workflow** — halts on user-supplied `inventory_type=new` and redirects to W5 (MSRP Parity).

→ Full spec in **`references/w3-brand-residual.md`**.

---

## Workflow 5 — MSRP Parity Tracker

New-vehicle `price_over_msrp_percentage` rollup + above / at / below status + cross-period direction labels + ticker overlay. Single-wave; 3 parallel `get_sold_summary` calls (current parity + prior parity + current volume). Always `inventory_type="New"`. (Workflow number is preserved from the reference's W1-W5 layout; W4 is intentionally absent.)

→ Full spec in **`references/w5-msrp-parity.md`**.

---

## Output

Every workflow renders via **`assets/output-template.md`**. That file is the
single source of truth for block structure, table schemas, headline phrasing
per workflow, tier / verdict bands, ticker-overlay rules, and the
self-check.

Render rules:

- **Workflow Table** rendered via `scripts/render_depreciation_table.py --mode <m>` (4 modes: `curve` / `segment` / `brand` / `parity`). Never hand-roll the table.
- **Headline** is one sentence (per-workflow phrasing in the template). When the recent monthly rate sits within 0.05% of any acceleration-band boundary, render the percent at two decimals.
- **Ticker Impact Summary** required on every workflow — translate per-make / per-segment / per-model findings into per-ticker BULLISH / BEARISH / NEUTRAL / CAUTION via `aggregate_signals.py`.
- **Comparison Context** required on every workflow — at least one cross-axis comparison; use `tracked_tickers` cohort when available.
- **Investment Thesis** persona-tailored (OEM ticker holder / auto lending / leasing equity / dealer-group equity) per the template; quantify business impact where possible.

## Self-check

The verification checklist lives in `assets/output-template.md`. It is an
**internal guardrail** — the model runs each silently before returning and
does NOT render the full grid.

- **All applicable checks pass** → emit a single footer line listing 5-7 items, e.g.:
  `✓ Verified: profile, US-only routing, sold-summary safety (limit=5000, inventory_type set), month-aligned dates, ticker overlay, verdict band consistent.`
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated to compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.

## What this skill does NOT do

- **Per-VIN appraisal or pricing.** Out of scope — this skill operates on `get_sold_summary` aggregates, not per-listing or per-VIN data.
- **EV-only deep cohort analysis.** W2's EV-vs-ICE pass is a cross-segment delta; for an EV-cohort investment narrative route to `ev-transition-monitor`.
- **Single-OEM verdict with full operational rollup (volume, ASP, DOM, days-supply).** Route to `oem-stock-tracker`.
- **Pre-earnings channel check on an OEM or dealer-group ticker.** Route to `earnings-preview`.
- **Geographic depreciation variance / regional residual exposure.** Intentionally out of scope (see top of file).
- **UK / non-US analysis.** `get_sold_summary` is US-only.
- **Stock-price prediction or EPS forecasts.** This skill produces operational signals; converting those to price targets is the analyst's job.
