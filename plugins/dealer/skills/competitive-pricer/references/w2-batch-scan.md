# W2 — Batch Competitive Scan

Triggered by "check pricing on my front-line inventory", "batch price check these VINs", "price my lot" (≤5-VIN form), etc. **Batch overview / triage** workflow: 3–5 VINs at once, deterministic per-VIN verdict (quartile-anchored against the local active-listing distribution), portfolio rollup.

W2 is **deliberately lighter than W1**. No sold-90d calls, no `get_sold_summary`, no `get_car_history`, no drop scan, no desc tail-pull. The dealer trades depth for throughput: 5 VINs in ~25–30s vs. 5 sequential W1 runs at ~30s each. For sold-anchored verdicts, days-to-sell estimates, MoS context, market-wide drop signals, or full diagnostic depth on any specific VIN, the dealer routes to W1 via `/price-check <VIN>`.

**Required inputs (per VIN):**
- VIN (17 characters matching `^[A-HJ-NPR-Z0-9]{17}$` — no I/O/Q).
- Mileage (required; predict's silent fallback to `miles=50000` corrupts every prediction).
- Asking price (required; W2 is comparison-anchored — without an ask the per-VIN row collapses to "describe the market", which is W4's job).

YMMT-only inputs (year/make/model/trim without VIN) are **rejected** by W2 — route to W4 for the model-level market or to W1 with a VIN for per-unit pricing.

## Anchor & verdict-source contract

W2 uses **quartile-anchored verdicts** against the per-VIN active-listing distribution (`comp_stats.verdict_quartile`, sourced from server-wide `stats="price,miles,dom_active"` over the full `num_found` set). The 5 bands map to symmetric IQR-extension fences:

| Band | Range |
|---|---|
| Below Market | `x < p25 − 1.5·IQR` |
| Modestly Below Market | `p25 − 1.5·IQR ≤ x < p25` |
| At Market | `p25 ≤ x ≤ p75` |
| Modestly Above Market | `p75 < x ≤ p75 + 1.5·IQR` |
| Above Market | `x > p75 + 1.5·IQR` |

Where `p25, p75, IQR = p75 − p25` come from `comp_stats.quartile`.

**W2 does NOT use sold-anchor.** Sold-anchor requires `search_past_90_days stats="price"` which W2 doesn't fire (throughput trade). When the dealer needs sold-anchor reconciliation, route the specific VIN to W1.

## Pre-check (before any MCP call)

1. **Country gate.** If `profile.location.country == "UK"`, halt with: *"W2 batch scan is US-only — UK dealers should run W1 per-VIN. (UK has no `predict_price_with_comparables`, so W2's Wave A would degenerate.)"*

2. **VIN format validation.** Each input VIN must match `^[A-HJ-NPR-Z0-9]{17}$`. On failure, halt with: *"VIN-N is malformed (must be 17 chars, no I/O/Q). Halt — please correct and re-run."*

3. **Duplicate VIN check.** Upper-case all VINs; reject any duplicate with: *"Duplicate VIN in batch — please provide each VIN once."*

4. **YMMT-only rejection.** If any input row has YMMT without a VIN, halt with: *"W2 batch scan requires VINs (17-char). For YMMT-only inquiries, use W4 (`/market-distribution`) for the model market or W1 with a VIN for per-unit pricing."*

5. **Batch size gate.** If `len(unique_valid_VINs) > 5`, halt with: *"W2 caps at 5 VINs inline. For larger lot scans, use the `dealer:lot-pricer` agent (designed for 50–500-unit batches)."*

6. **Profile session check.** Read `profile.session.dealer_type_lower`, `dealer_type_opposite_lower`, `radius_mi_clamped`, `car_type_resolved`. If `dealer_type_lower is None`, halt with the standard SKILL.md prompt to update the profile. If `car_type_resolved == "both"`, halt and ask which to use (per SKILL.md Before-you-start step 4).

After the pre-check passes, proceed to the input-completeness prompts (next section) before Wave A.

## Pre-Wave-A: collect missing inputs + decide CPO per VIN

### Input completeness prompt (when miles or asking_price is missing on any VIN)

If any reported VIN is missing mileage or asking_price, prompt collectively up-front:

> *"VIN-2 is missing mileage. VIN-4 is missing asking price. Reply with the values (e.g. 'VIN-2 miles=45000; VIN-4 ask=27500'), or 'skip' to drop that VIN from the batch."*

Apply the answer per-VIN: VINs with all three fields proceed to Wave A; skipped VINs are noted in DQ event (d) and excluded from Wave A and the rollup. If after the prompt fewer than 1 valid VIN remains, halt the batch entirely with: *"No valid VINs remain after input validation."*

### CPO batch policy — single up-front collective prompt

When `profile.dealer.cpo_program == true` OR the user has not pre-stated CPO status for the batch, emit one collective prompt:

> *"Are any of these VINs currently CPO? Reply with 'all', 'none', or list the CPO VINs (e.g. VIN-1, VIN-3)."*

Apply the answer per-VIN: CPO VINs get 4 predict calls (non-CPO × 2 + CPO × 2) in Wave A; non-CPO VINs get 2 predict calls. Default to non-CPO for all VINs if the user skips the prompt or replies "none", and emit DQ event (g) per skipped VIN noting `"CPO branch skipped: user-confirmed non-CPO globally"`.

If `profile.dealer.cpo_program == false` (or unset) AND the user has pre-stated non-CPO globally (e.g. *"none of these are CPO"* in their initial request), skip the prompt entirely. This mirrors `references/cpo.md` rule 2 in batch form.

After both prompts return, the agent has a per-VIN `{vin, miles, asking_price, is_cpo}` tuple for every reported VIN. Wave A starts.

## Parallelization (W2)

W2 is a **2-wave workflow**, each wave dispatched as a single agent message containing N tool_use blocks (parallel across the batch).

**Wall-clock budget:**
- Wave A ≈ 12–15s (decode + predicts per VIN, all parallel)
- Wave B ≈ 12–15s (active comp set per VIN, all parallel — deduped by YMMT tuple)
- **Total ≈ 25–30s** regardless of batch size N (1–5)

If serialized: ~144s for N=5 non-CPO. The wave model is load-bearing.

## Wave A — Per-VIN decode + dual ML predict (+ optional CPO)

For each VIN in the batch (after pre-check + completeness prompts), fire in parallel:

```
decode_vin_neovin(vin)                                                                          # parse → role: specs
predict_price_with_comparables(vin, miles, zip=<profile.zip>, dealer_type=<dealer_type_lower>)         # parse → role: nocpo_primary
predict_price_with_comparables(vin, miles, zip=<profile.zip>, dealer_type=<dealer_type_opposite_lower>) # parse → role: nocpo_context

[when subject is CPO per the batch prompt]
predict_price_with_comparables(vin, miles, zip=<profile.zip>, dealer_type=<dealer_type_lower>,          is_certified=true)  # parse → role: cpo_primary
predict_price_with_comparables(vin, miles, zip=<profile.zip>, dealer_type=<dealer_type_opposite_lower>, is_certified=true)  # parse → role: cpo_context
```

Wave A is **identical to W1's Wave A**, fired once per VIN. For 5 VINs non-CPO: 15 parallel calls (5 × 3). For 5 VINs all-CPO: 25 parallel calls (5 × 5). Mixed batches scale proportionally.

**Decode caching across the batch.** If two batch VINs share a squish-VIN (same year + make + model + trim cohort), the agent MAY skip the duplicate decode call. In practice, dedupe is rare across small batches — fire one decode per VIN unless the agent has prior decoded specs cached from this session.

The four predict role labels (`nocpo_primary` / `nocpo_context` / `cpo_primary` / `cpo_context`) are the agent's working-memory handles; they keep their `primary` / `context` naming across CPO state per `references/cpo.md`. Each role's response is parsed via `parse_predict.py --file <persisted-path>`.

## Wave B — Per-VIN active comp set with stats

For each unique YMMT tuple in the batch (NOT each VIN — see dedup below), fire in parallel:

```
search_active_cars:
  year, make, model, trim                        (verbatim from cached parse_decode.specs)
  zip=<profile.zip>, radius=<session.radius_mi_clamped>, car_type=<session.car_type_resolved>
  sort_by="price", sort_order="asc"
  price_range="1-*"
  rows=10
  stats="price,miles,dom_active"                 ← server-wide aggregates over full num_found
  include_dealer_object=true
  include_build_object=true
  fetch_all_photos=false, include_mc_dealership_object=false,
  include_finance=false, include_lease=false, include_relevant_links=false
→ parse_search.py --file <persisted-path>
                  --subject-vin <this VIN>
                  --exclude-vins <other batch VINs as CSV>     ← cross-batch self-comp guard
```

### `stats="price,miles,dom_active"` rationale

W1 gets DOM context from `search_past_90_days stats="dom_active"` (sold-90d days-to-sell). W2 doesn't fire that call, so without `dom_active` in Wave B's stats list the only DOM signal is from the visible 10 rows' per-listing `dom_active` field — small-sample and bottom-of-distribution biased. Adding `dom_active` to the server stats request gives W2 a server-wide DOM aggregate (min / p25 / median / p75 / max) over the full `num_found` set, the active-side analog of what W1 gets from sold-90d.

`mcp_server_tool_docs/search_active_cars.md` line 158 confirms `stats=` accepts comma-separated fields. `parse_search.py` passes `data.stats` through verbatim (line 238), so no parser change. `comp_stats.py` reads `server_stats` as an open dict, so no comp_stats change either — the new `dom_active` block sits alongside `price` and `miles` and is read by the W2 renderer directly for the Active DOM line in the per-VIN card.

### Wave-B dedup by YMMT tuple

If two batch VINs share `{year, make, model, trim}` (e.g. two 2025 Camry LE), fire **one** search_active_cars call; reuse the parsed result for both. Cache key: `(year, make, model, trim)`, established once Wave A's parse_decode lands.

**Subject-VIN handling for shared YMMT batches.** Each VIN sharing a YMMT tuple has its own `--subject-vin` value. The cached search payload is reusable, but each VIN's per-VIN pipeline (parse_search → comp_stats) re-runs `parse_search.py --subject-vin <this VIN> --exclude-vins <others>` against the same persisted asc.json. This makes shadow-listing detection per-VIN even when the underlying search is shared.

### Cross-batch self-comp exclusion

Every Wave B search call passes `--exclude-vins` with the other batch VINs as a CSV. Without this, VIN-A's comp set could include VIN-B sitting two stalls over (the dealer's own unit), polluting the per-VIN percentile rank. `parse_search.py` line 199 supports CSV-form `--exclude-vins`.

When `parse_search.filtered_out.exclude_vin_match > 0`, log DQ event (d) at the rollup level (not per-VIN — the cross-batch exclusion is by-design, not surprising).

## Persistence and truncation handling

W2 fires N decodes + 2N or 4N predicts + N (or fewer with YMMT dedup) searches. For N=5 non-CPO: 15 Wave A responses + 5 Wave B responses = 20 MCP calls. Per `references/truncation-recovery.md`:
- `decode_vin_neovin` chronically truncates (~150KB envelopes) — every Wave A decode response will likely arrive as `Error: ... saved to <path>` and need `parse_decode.py --file` recovery.
- `predict_price_with_comparables` chronically truncates (~100KB envelopes) — same recovery via `parse_predict.py --file`.
- `search_active_cars` returns inline at `rows=10` for most YMMT tuples; occasional truncation at `rows=10 + stats=...` is possible — recover via `parse_search.py --file`.

### Per-VIN scratch path convention

Use `/tmp/marketcheck/<session.run_id>/<VIN>/` as the per-VIN sub-directory:

```
/tmp/marketcheck/<session.run_id>/<VIN>/decode.json
/tmp/marketcheck/<session.run_id>/<VIN>/predict-nocpo-primary.json
/tmp/marketcheck/<session.run_id>/<VIN>/predict-nocpo-context.json
/tmp/marketcheck/<session.run_id>/<VIN>/predict-cpo-primary.json     # only when CPO
/tmp/marketcheck/<session.run_id>/<VIN>/predict-cpo-context.json     # only when CPO
/tmp/marketcheck/<session.run_id>/<VIN>/asc.json                     # or shared with same-YMMT VINs
```

Per-VIN sub-directories prevent file collisions across batch members. The `<session.run_id>` value comes from `profile.session.run_id` (auto-assigned by `scripts/load_profile.py`) — read it verbatim, never hardcode `cpr-run`.

When YMMT dedup applies, the same `asc.json` may live under each batch member's sub-directory (or in a shared cache directory keyed by the YMMT tuple). The agent's choice — either works.

### Recipe (mirrors W1 step 4 pipeline-bypass warning)

```
# Step 1: persist the raw envelope-wrapped MCP response verbatim
Write(file_path="/tmp/marketcheck/<session.run_id>/<VIN>/decode.json",
      content="<full envelope-wrapped response>")

# Step 2: parse via --file (parsers' --file path unwraps the envelope)
parse_decode.py --file /tmp/marketcheck/<session.run_id>/<VIN>/decode.json
```

Same recipe applies to predict and asc responses. The `Write` tool accepts large JSON content directly. Do NOT trim, reshape, or hand-key listings into a custom merge script — every prior session that took those paths produced silent dedup or filter errors. The pipeline is deterministic for a reason.

## Per-VIN pipeline (post-waves)

For each reported VIN, run the deterministic pipeline:

```
parse_decode.py --file <decode.json>                         → cached YMMT tuple + display specs
parse_predict.py --file <predict-nocpo-primary.json>         → marketcheck_price, comp counts, comp price stats
parse_predict.py --file <predict-nocpo-context.json>
[when CPO]
parse_predict.py --file <predict-cpo-primary.json>
parse_predict.py --file <predict-cpo-context.json>
parse_search.py --file <asc.json> --subject-vin <V> --exclude-vins <V1,V2,V3,V4>
                                                             → listings (≤10), num_found, server stats, filtered_out

build_comp_stats_input.py \\
  --profile <load_profile output> \\
  --asc-parsed <parse_search output> \\
  --user-price <asking_price>     # required per pre-check \\
  --user-miles <miles>             # required per pre-check \\
  --subject-vin <V> \\
  --subject-cpo <true|false> \\
  --trim-label "<year> <make> <model> <trim>" \\
  --nocpo-primary-parsed <path> --nocpo-context-parsed <path> \\
  [--cpo-primary-parsed <path> --cpo-context-parsed <path>] \\
| comp_stats.py
```

**`--merged`, `--sold-price`, `--sold-dom`, `--drops` are intentionally omitted.** As of `build_comp_stats_input.py` v1.5.0, those four flags are optional with W2-safe defaults:

| Flag | When omitted, behavior |
|---|---|
| `--merged` | Synthesize from `--asc-parsed`: `merged = {"merged_listings": asc.listings, "pulled_count": asc.kept_count}`. |
| `--sold-price` | `sold_count_90d = 0`, `sold_median = None`. |
| `--sold-dom` | `sold_dom_median = None`, `sold_dom_field = None`. |
| `--drops` | `drops_market_wide_count = 0`. |

Downstream `comp_stats.py` reads these defaults and:
- Falls back to `verdict_source = "quartile"` (sold-anchor gate is `sold_count_90d >= 5`).
- Emits `mos = None`, `mos_tier = None` (divide-by-zero guard at line 826 of comp_stats).
- Skips sold-anchor verdict computation; `verdict_quartile` becomes the sole verdict source.

W1 still passes all 4 flags and continues to work byte-identically (regression-tested via `tests/test_build_comp_stats_input.py::test_w1_existing_path_still_works_byte_identical`).

## Failure recovery and edge cases

| Case | Trigger | Per-VIN behavior | Batch-level effect |
|---|---|---|---|
| Decode `ok=false` | `parse_decode` returns `ok=false` (truncation unrecoverable, malformed VIN, server 5xx) | Halt this VIN; emit DQ event (a) with VIN + error_type | Drop VIN from batch; rollup excludes it; continue with remaining VINs |
| Predict `ok=false` for one role | One of the 2-4 predicts returns `ok=false` | Render that price line as `<role>: unavailable (<error_type>)`; continue rendering other roles | VIN remains in batch; rollup uses available role medians |
| All 4 predicts `ok=false` | Every predict role failed | Halt this VIN; emit DQ event (a) | Drop VIN from batch |
| Search `num_found = 0` | No active comps in radius | Render Active Local Market block as `(empty)`; verdict block becomes `"Insufficient comps — no active matches in <radius>mi"` | VIN remains; rollup excludes from action priority |
| Search `num_found > 0` but `< 6` (thin market) | Sub-`min_n` active set | Verdict computes from server stats with `comp_stats.insufficient = true`; render `"Thin market: n=<num_found> < 6 comps; verdict deferred"` | VIN remains; rollup excludes from action priority |
| Subject VIN found in comp set (shadow) | `parse_search.filtered_out.self_vin_match > 0` | Render shadow-listing flag in per-VIN card (dealer name, distance, price, dom); VIN excluded from comp_stats automatically; emit DQ event (c) | Aggregate (c) at rollup |
| Cross-batch VIN in this VIN's comp set | `parse_search.filtered_out.exclude_vin_match > 0` | Logged in DQ event (d); excluded from comp_stats automatically | Aggregate (d) at rollup |
| Asking price absent | User did not supply `asking_price` for a VIN at the pre-check | Halt this VIN at pre-Wave-A completeness check; collect missing asks in collective prompt; if user skips, drop the VIN with DQ event (d) | VIN dropped — not counted in `N_total` reported (counted in skipped) |
| Mileage absent | User did not supply `miles` for a VIN at the pre-check | **Cannot proceed** — predict's silent fallback to `miles=50000` corrupts predictions. Halt this VIN at the pre-check; collect missing miles in collective prompt; if user skips, drop the VIN | VIN dropped if user skips |
| Malformed VIN | VIN doesn't match `^[A-HJ-NPR-Z0-9]{17}$` | Halt the batch with *"VIN-N is malformed (must be 17 chars, no I/O/Q). Halt — please correct and re-run."* | Halt at pre-check |
| YMMT-only (no VIN) | User supplied year/make/model/trim without VIN for a row | **Reject in W2**: emit halt with route to W4 / W1 | Halt the batch entry, do not run partial |
| UK profile | `profile.location.country == "UK"` | Halt with *"W2 batch scan is US-only — UK dealers should run W1 per-VIN."* | Halt at pre-check |
| Duplicate VIN in batch | Same 17-char VIN appears more than once after upper-casing | Halt with *"Duplicate VIN in batch — please provide each VIN once."* | Halt at pre-check |
| `>5` unique valid VINs | After dedupe and 17-char validation, more than 5 distinct VINs remain | Halt with `dealer:lot-pricer` recommendation | Halt at pre-check |
| Fewer than 1 valid VIN after pre-check | All VINs got skipped/dropped during the pre-check prompts | Halt the batch entirely with *"No valid VINs remain after input validation."* | Halt |

Today's W2 (pre-v1.5.0) had zero recovery guidance, leading to non-deterministic per-session behavior. The matrix above is mandatory reading for any agent running W2.

## Output rendering

W2 renders via **`assets/w2-output-template.md`** — that file is the W2 single-source-of-truth for block structure, per-VIN card layout, portfolio rollup, action templates, and self-check. The sister file `assets/output-template.md` covers W1 / W3 / W4 / W5 only.

Block structure overview (full spec in `assets/w2-output-template.md`):
1. **Header** — `Using profile: ...` + batch scope line + optional pre-check-drops line.
2. **Per-VIN card** (rendered N_reported times) — Decoded Specs → Predicted Prices (+ CPO Premium when CPO) → Active Local Market (Price / Miles / **DOM**) → Your Price vs Market → Verdict + Action → optional shadow flag.
3. **Portfolio Summary** — action priority, distribution counts, headroom-recovery, under-pricing exposure.
4. **Aggregated Data Quality Notes** (when non-empty) — events (a)–(g) collapsed across the batch.
5. **Footer** — escape-hatch (route to W1) + self-check line.

## Data Quality event log discipline for batches

W2's per-VIN flow generates many DQ events. Aggregation rules:

- **Per-VIN events (rendered inline in the per-VIN card):**
  - (c) Shadow listing for THIS VIN — render in the per-VIN card; also include in the aggregated (c) list.
  - Per-VIN failure modes (decode/predict/search ok=false) — render as `unavailable (<error_type>)` on the affected sub-block.

- **Batch-aggregated events (in the rollup's Data Quality Notes):**
  - (a) MCP tool errors recovered — total count + list of (VIN, tool, error_type).
  - (a1) Facet-discovery retries — for W2: skipped by design (when `num_found = 0`, the per-VIN verdict degrades to "Insufficient comps" rather than retrying with facet discovery).
  - (b) Truncation envelope unwraps — total count across decode / predict / search.
  - (c) Shadow listings — list of (VIN, dealer_name, distance_mi).
  - (d) Skipped VINs at pre-check — list of (VIN, reason).
  - (e) Fallback source attribution — count of per-VIN cards using client-bounded percentile (when `num_found < min_n`).
  - (g) Workflow branches skipped by design — fixed list per W2 architecture: sold-90d × 3, get_sold_summary, get_car_history, drop scan, desc tail-pull, facet-discovery retry. Plus per-VIN CPO branch decisions.

If the entire DQ event log is empty (rare), omit the Data Quality Notes section per the standard render rule. The per-VIN failure cases will populate at least one event in most real runs (truncation events alone average 3–5 per batch).

---

## See also

- `assets/w2-output-template.md` — W2 output spec (per-VIN card + portfolio rollup, action templates, render rules, self-check).
- `references/w1-price-check.md` — single-VIN deep diagnostic; the route the dealer takes when they need sold-anchor reconciliation, MoS context, or `sold_dom_median` days-to-sell on a specific VIN.
- `references/cpo.md` — CPO call shape (the dual-prediction pattern is identical to W1; only the batch-prompt timing is W2-specific).
- `references/truncation-recovery.md` — `--file` recovery recipe for chronic-truncation tools.
- `mcp_server_tool_docs/search_active_cars.md` — `stats=` parameter contract, per-call `rows` cap, server-side filter behavior.
- `references/facet-discovery.md` — NOT triggered by W2; included for completeness (W2 emits DQ event (a1) when `num_found = 0` rather than retrying).
