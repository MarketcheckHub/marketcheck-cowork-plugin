---
name: depreciation-tracker-updated
description: Quantifies vehicle depreciation, value retention, residual forecasts, segment trends, brand-tier rankings, geographic price variance, and new-vehicle MSRP parity from MarketCheck sold-transaction aggregates. Covers five US-only workflows — make/model depreciation curve with retention % vs MSRP and a 5-band acceleration verdict, body-type / fuel-type segment trends with EV-vs-ICE comparison, brand residual ranking with 4-tier classification (T1 ≥ 98% retention through T4 < 90%), state-level geographic price-index map, and new-vehicle MSRP parity tracker with status and direction labels. Every output is anchored on `get_sold_summary` aggregates (multi-period, weighted means, month-aligned date windows enforced in code), classified via deterministic Python scripts (never hand math), and rendered via `render_depreciation_table.py`. Use when a lender, residual analyst, portfolio risk manager, OEM analyst, appraiser, or auto-finance director asks "depreciation rate", "value retention", "residual value", "how fast is it losing value", "which cars hold value", "EV depreciation", "price trend over time", "brand value ranking", "depreciation curve", "residual forecast", "MSRP parity", "price over sticker", "incentive effectiveness", "geographic value variance", "which states have higher prices", "are markups coming down", "segment retention comparison", "brand tier", "above sticker", "below sticker", or any depreciation / residual / parity-tracking intent — or raises any value-retention or trend-adjusted-valuation question without naming the skill. **US-only**; halts UK profiles since `get_sold_summary` is unavailable for UK.
version: 1.0.0
---

# Depreciation Tracker

Given a make/model, segment, or geography, surface depreciation velocity,
value retention, brand tier, geographic variance, or new-vehicle MSRP parity
from MarketCheck sold-transaction aggregates. Five workflows mapped to
distinct user intents, every output anchored on `get_sold_summary` (the only
US tool that exposes aggregated sold-vehicle averages by month / segment /
region), classified via deterministic Python scripts.

Five workflows map to distinct user intents:

- **W1 — Make/Model Depreciation Curve** — "how fast is the RAV4 losing value?" — multi-period sold-price trajectory (1yr / 6mo / 90d / 60d / current) + retention % vs MSRP (with prior-period fallback) + 5-band acceleration verdict + curve-shape classifier (linear / accelerating / stabilizing).
- **W2 — Segment Value Trends** — "are SUVs holding value better than sedans?" — body_type and/or fuel_type cross-period comparison, EV-vs-ICE delta, classification per segment (appreciating / stable / soft / accelerating_dep).
- **W3 — Brand Residual Ranking** — "which brands hold value best?" — per-make retention % over a 6-month window, tier classification (T1 ≥ 98% / T2 ≥ 95% / T3 ≥ 90% / T4 < 90%), tier-jump detection.
- **W4 — Geographic Depreciation Variance** — "where do Tacomas hold value best?" — state-level price index vs national average, premium / average / discount classification per state, top-5 / bottom-5 spread.
- **W5 — MSRP Parity Tracker** — "are markups coming down?" — new-vehicle `price_over_msrp_percentage` rollup, above / at / below status per make-model, cross-period direction (flipped_below / flipped_above / deepening / narrowing / stable).

## Before you start

1. **Load the profile.** Run `scripts/load_profile.py` (reads `marketcheck-profile.md`, parses YAML frontmatter + JSON body). Non-zero exit → halt and ask the user for the minimum inputs (state + country). Profile is **optional** for guest queries that supply state directly; depreciation-tracker accepts standalone state-anchored questions without a full profile.

2. **Confirm the profile.** First user-facing line is always: `Using profile: <dealer.name>, <state>, <country>` — or `Using profile context: <state>, US` for guest queries.

3. **Branch on country.**
   - `country == "US"` → the workflows below.
   - `country == "UK"` → **halt** per `references/country-uk.md`. Every workflow depends on `get_sold_summary` which is US-only; no substitute path exists in the UK MCP surface.
   - `country == "CA"` → **halt** with: *"Depreciation Tracker does not yet support Canada. The skill is US-only — `get_sold_summary` is the only sold-transaction-aggregate tool and has no Canadian variant. Re-visit when MarketCheck ships CA sold data."*
   - Any other country → halt with the same US-only message.

4. **Compute session values.**
   - `state = profile.location.state` — required for every workflow. Halt and ask if missing in a US profile.
   - `car_type = profile.preferences.default_inventory_type`:
     - `"used"` or `"new"` → use directly. Maps to `inventory_type="Used"` / `"New"` (title case) on every `get_sold_summary` call.
     - `"both"` → **halt and ask**: *"Depreciation analysis on used or new vehicles?"* before any MCP call. Apply the answer for the rest of the session. The skill never mixes used and new in a single output.
     - **W5 (MSRP Parity) overrides this** — W5 is always `inventory_type="New"`. If `car_type` resolved to `"used"`, halt with W5 redirect message per `references/w5-msrp-parity.md`.
   - `franchise_brands = profile.dealer.franchise_brands` — used only as a Comparison Context highlight in W3 / W5 (the user's own brands' tier / parity status). Optional; absent → emit DQ event (g) and skip the highlight.

5. **Skip these inputs (intentionally removed from the input surface).**
   - **`year`** — `get_sold_summary` does not accept it. The skill aggregates across all model years; output renders an explicit scope qualifier per `references/sold-summary-safety.md`.
   - **`trim`** — same as `year`; not a parameter on `get_sold_summary`.
   - **`dealer_type`** — passing `Franchise|Independent` to `get_sold_summary` silently suppresses valid data per `references/sold-summary-safety.md`. The skill never passes it.

6. **Payload-shaping defaults** — every `get_sold_summary` call passes:
   - `limit=5000` — the upstream max. Default `1000` silently truncates multi-dimensional results.
   - `inventory_type` — explicit `"Used"` or `"New"`; never omitted (omitting silently defaults to `"New"`).
   - `summary_by="state"` (or absent for W4 national-baseline call) — explicit, never relying on default.
   - `ranking_dimensions` — minimal per workflow (see `references/sold-summary-safety.md` table).
   - `top_n` — bounded per workflow (5–30, never the default).

   `search_active_cars` (W1 step 2 only) passes:
   - `fetch_all_photos=false`, `include_mc_dealership_object=false`, `include_finance=false`, `include_lease=false`, `include_relevant_links=false`, `include_dealer_object=false` — always off. The W1 rep-VIN search renders nothing from these.
   - `include_build_object=true` — needed to read `msrp` flat off the listing root via parse_search.

7. **Working directory.** All intermediate files (raw MCP responses, parsed outputs, curve / segment / brand / geo / parity inputs) are written to `/tmp/marketcheck/<session.run_id>/`, where `session.run_id` is auto-generated by `scripts/load_profile.py` (`cpr-<epoch>-<8-hex>` format). Read it from `profile.session.run_id`; never hardcode `cpr-run`. Concurrent skill flows get distinct `run_id` values, so two simultaneous depreciation queries never collide.

8. **Date windows.**
   - W1 (5-period curve) and W2 / W3 / W5 (current + prior pairs): derive every `date_from` / `date_to` from `scripts/compute_period_windows.py` — run ONCE at workflow entry, cache the periods array, and read each call's window from the cached entry.
   - W4 (single-period snapshot): use `scripts/compute_sold_summary_dates.py` for the canonical "last 1 full month" window.
   - **Never hand-compute dates.** Mis-aligned dates pass local validation and return HTTP 422 from upstream per `references/sold-summary-safety.md`.

9. **Session continuity.** Session values (`run_id`, `car_type_resolved`, `state`) live in the profile's `session` block emitted by `scripts/load_profile.py`. Read them verbatim. After compaction, re-run `scripts/load_profile.py --run-id <previously-emitted>` to preserve the scratch directory across the re-load.

## Truncation handling

`decode_vin_neovin` (W1 step 3 conditional) chronically truncates (~150KB envelopes); always recover via `parse_decode.py --file <path>`. `get_sold_summary` rarely truncates with the prescribed parameter set, but the recipe still applies — see `references/truncation-recovery.md`.

If a parser reports `ok=false` (critical field missing even after unwrap), do NOT halt the workflow for one failed call. Render a caveat for the affected period / row + emit DQ event (a) and continue.

## Sold-summary safety

Hard-won rules — see `references/sold-summary-safety.md`. The non-negotiables:
- Always set `inventory_type` (`Used` / `New`) explicitly.
- Always set `limit=5000`.
- Always pass minimal `ranking_dimensions` (workflow-specific; see safety doc).
- **Never** pass `dealer_type` (silent data suppression).
- Always month-align `date_from` / `date_to` via the helper scripts.
- Branch on `parse_sold_summary.error_type` per the recovery table.

## Facet discipline

`get_sold_summary` does not expose a `facets` parameter. When a call returns `error_type="make_model_not_found"`, recover via `search_active_cars` facet discovery per `references/facet-discovery.md`, then re-issue the failed call with the resolved casing. Cache the resolved tuple — every period's call in the same workflow uses the cached value.

`year` and `trim` are NOT parameters on `get_sold_summary` — they are NOT facet-discoverable. The skill aggregates across all years and trims; rendered scope qualifier in the Analysis Summary.

## Parallelization (universal contract)

Every workflow follows the wave-execution contract:

- A wave is a batch of MCP calls fired in a single agent message — multiple `tool_use` blocks dispatched concurrently. The agent emits all calls in the wave together, then waits for the full batch of `tool_result` messages before issuing the next wave.
- Within a wave, calls share no cross-dependency on each other's output.
- Wave A / Wave B labels are workflow-local. Most depreciation-tracker workflows have just Wave A; W1 has a conditional Wave B for the rep-VIN decode.
- Wave content lives in the per-workflow reference. Each `references/wN-*.md` defines its specific waves and call list.

Wall-clock budgets:
- W1: Wave A ≈ 12-15s · Wave B ≈ 12-15s (when fired) · Total ≈ 12-30s
- W2 / W3 / W5: single-wave ≈ 12-15s
- W4: single-wave ≈ 12s

Serialized, every workflow would run ~24-90s. The wave model is load-bearing.

## Data quality rule

Treat every period's failure as recoverable, not fatal. A failed `get_sold_summary` call on one period of a multi-period curve omits that period from the table — it does not halt the workflow. Surface every degradation in the Data Quality Notes section.

## Data Quality event log

Accumulate a running list of events; feed it into the Data Quality Notes section at render time. Track:

- **(a)** MCP tool errors / non-200 responses recovered from — tool name, `error_type`, recovery path. Specifically for `parse_sold_summary` failures: `make_model_not_found`, `validation_dimension_limit`, `network_422`, `network_5xx`, `validation`, `unknown`.
- **(a1)** Facet-discovery retries — when a `get_sold_summary` call errored with `make_model_not_found` and a `search_active_cars` facet lookup resolved the correct casing.
- **(b)** Truncation envelope unwraps via `--file <path>` — which parser, which tool.
- **(e)** Fallback source attribution — e.g., MSRP-anchored retention unavailable; National baseline call returned empty rows; period omitted from curve.
- **(f)** Parameter adaptations — when a documented parameter wasn't accepted and a substitute was used.
- **(g)** Workflow branch skipped by design — e.g., Wave B decode skipped because rep listing carried MSRP; Hybrid pass not requested in W2; comparison_window defaulted because user didn't specify.

If the list is empty, omit the section entirely.

---

## Workflow 1 — Make/Model Depreciation Curve

Reference workflow. Multi-period sold-price trajectory + 5-band acceleration verdict + retention % (MSRP-anchored when available; prior-period anchor as fallback). Wave A fires 5 `get_sold_summary` calls (one per period) + 1 `search_active_cars` (rep-VIN); Wave B conditionally decodes the rep-VIN to extract MSRP.

→ Full spec in **`references/w1-curve.md`**.

---

## Workflow 2 — Segment Value Trends

Body_type and/or fuel_type cross-period comparison. EV-vs-ICE explicit pass when requested. Single-wave; 2-6 parallel `get_sold_summary` calls.

→ Full spec in **`references/w2-segment-trends.md`**.

---

## Workflow 3 — Brand Residual Ranking

Per-make retention % over a 6-month window + 4-tier classification + tier-jump detection. Single-wave; 3 parallel `get_sold_summary` calls (current avg + prior avg + current volume).

→ Full spec in **`references/w3-brand-residual.md`**.

---

## Workflow 4 — Geographic Depreciation Variance

State-level price index vs national average + premium / average / discount classification. Single-wave; 2 parallel `get_sold_summary` calls (state-bucketed + national rollup).

→ Full spec in **`references/w4-geographic-variance.md`**.

---

## Workflow 5 — MSRP Parity Tracker

New-vehicle `price_over_msrp_percentage` rollup + above / at / below status + cross-period direction labels. Single-wave; 3 parallel `get_sold_summary` calls (current parity + prior parity + current volume). Always `inventory_type="New"`.

→ Full spec in **`references/w5-msrp-parity.md`**.

---

## Output

Every workflow renders via **`assets/output-template.md`**. That file is the single source of truth for block structure, table schemas, headline phrasing per workflow, tier and verdict bands, and the self-check.

Render rules:

- **Workflow Table** rendered via `scripts/render_depreciation_table.py --mode <m>` (5 modes: `curve` / `segment` / `brand` / `geo` / `parity`). Never hand-roll the table — re-implementing parser/script logic during rendering is a rendering bypass.
- **Headline** is one sentence (per-workflow phrasing in the template). When the verdict / classification band sits within 0.05% of a boundary, render the percent at two decimals.
- **Comparison Context** required on every workflow — at least one cross-axis comparison.
- **Recommendation** persona-tailored (lender / OEM / appraiser) per `references/outcomes.md` action-to-outcome funnel; quantify business impact where possible.

## Self-check

The 12-item verification checklist lives in `assets/output-template.md`. It is an **internal guardrail** — the model runs each silently before returning and does NOT render the full grid.

- **All applicable checks pass** → emit a single footer line, e.g. `✓ Verified: profile, US-only routing, sold-summary safety (limit=5000, inventory_type set), month-aligned dates, anchor source, tier/verdict band consistent.` Abbreviate to 5–7 items; drop N/A from the summary.
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated to compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.
