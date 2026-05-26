---
name: earnings-preview
description: Pre-earnings channel check for US auto-sector equities — OEMs (F, GM, TM, HMC, STLA, TSLA, RIVN, LCID, HYMTF, NSANY, MBGAF, BMWYY, VWAGY) and dealer-groups (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA). Use when an equity analyst asks "earnings preview for STLA", "pre-earnings channel check on Ford", "what will GM report", "how is CVNA tracking into the print", "channel signal on TSLA next quarter", or any single-ticker channel read ahead of a quarterly print. Produces a 4-tier verdict {BULLISH, BEARISH, NEUTRAL, MIXED} + null, anchored on multi-quarter QoQ + YoY analysis of Volume, ASP, MSRP gap, DOM, Days Supply (Used + New), EV share, and New/Used Mix. Calendar-quarter cadence — distinct from the monthly-cadence `oem-stock-tracker`. Halts on unknown tickers (no brand-orphan recovery). Prefer this skill for ticker-tied "going into the print" / "pre-earnings" / "channel check" / "earnings preview" requests.
version: 1.2.0
---

# Earnings-Preview Channel Check (Updated)

Equity-analyst-facing skill for **pre-earnings channel checks** on US publicly-traded auto-sector tickers — 13 OEMs and 8 dealer-groups (21 tickers total). The frame is *channel signal between earnings*: aggregate sold-vehicle data across the most recent three calendar quarters + live active inventory + EV slice + (for dealer-groups) New/Used mix tell you which way operational metrics are moving in the **last completed quarter** — typically 30-90 days before the company reports. Use the verdict to size pre-print conviction with full transparency on which metrics drove which signal.

Every numeric block — leading indicators, QoQ + YoY deltas, signal verdicts, per-make breakdown, EV transition, mix shift — is computed by Python scripts in this skill, not by the model. Same inputs always produce the same verdict.

## Before you start

1. **Profile load (inline, no script).** Read `marketcheck-profile.md` from the project root. Parse YAML frontmatter and the JSON body. Frontmatter wins on conflict (it's the curated view); JSON body provides fields the frontmatter omits. Extract:
   - `location.country` — always present in both shapes (frontmatter has it nested under `location:`; the JSON body may have it nested OR at top level — check both). **If country != "US", halt with: *"This skill is US-only; `get_sold_summary` has no UK variant and dealer-group / OEM ticker coverage is US-listings only."***
   - `analyst.coverage_tickers` — only present in analyst-shaped profiles. If non-empty AND the user prompted without a ticker, suggest the first one as a default.
   - `analyst.focus_segments`, `analyst.signal_preferences` — informational; do NOT alter signal math. Captured for narrative tone only.
   - If the profile is missing or unparseable → prompt the user for the ticker directly. No halt.

2. **Quarter windows.** Run `scripts/compute_quarter_windows.py --today <currentDate>`. The script emits `current_quarter` (the latest calendar quarter that ended strictly before today), `prior_quarter` (the quarter before that), `year_ago_quarter` (same calendar quarter from one year earlier), and `most_recent_complete_month` (the mrcm — may post-date current_quarter end; paired with live active inventory for Days Supply).

3. **Ticker resolution.** Run `scripts/resolve_ticker.py --input "<user input>"`. Three-tier resolution: exact ticker → reverse make/canonical-name lookup → fuzzy via `difflib.SequenceMatcher` ≥0.5. Captures `ticker`, `entity_type` (`oem` | `dealer_group`), `classification` (OEM: `legacy` | `pure_play`; dealer-group: `Used-only` | `New-only` | `Both`), plus `company_name` + `makes[]` (OEM) OR `canonical` (dealer-group).

   Branches:
   - `ok=true` → continue with W1.
   - `error_type=missing_input` → re-prompt the user.
   - `error_type=no_candidates` → **HALT cleanly** with the candidate list. Per Phase 5 §5a, this skill does NOT attempt brand-orphan recovery for unknown tickers — the universe of tracked tickers is the 21-row map in `references/ticker-mapping.md`, and anything outside that map is out of scope. The user-facing message: *"`<input>` doesn't resolve to a tracked ticker. Tracked: <13 OEM tickers>, <8 dealer-group tickers>. Closest fuzzy matches: <top-3 candidates>. Pick a tracked ticker or use a different skill."*

4. **Channel selection (automatic from classification).** Do NOT prompt the user — channel coverage is determined by ticker classification. The mapping:

   | Classification | Fetch New channel? | Fetch Used channel? | Fetch EV slice? |
   |---|---|---|---|
   | OEM `legacy` | Yes | Yes | Yes (BEV+PHEV via `fuel_type_category="EV"`) |
   | OEM `pure_play` (TSLA, RIVN, LCID) | Yes | Yes | No (volume IS EV) |
   | Dealer-group `Both` (AN, LAD, PAG, SAH, GPI, ABG, CVNA) | Yes | Yes | Yes |
   | Dealer-group `Used-only` (KMX) | No | Yes | Yes |
   | Dealer-group `New-only` (none currently mapped) | Yes | No | Yes |

   See `references/inventory-type-classification.md` for the full table and CVNA empirical caveat (CVNA = `Both` per source despite ~0.4% New share, verified 2026-05-13).

5. **Confirm to user** (one-line status, no question):
   - OEM form: *"Analyzing **<ticker>** (<company_name>): <makes> — <classification> OEM. Pulling channel signals across <year_ago_quarter.label>, <prior_quarter.label>, <current_quarter.label>, with Days Supply paired to <most_recent_complete_month.label>…"*
   - Dealer-group form: *"Analyzing **<ticker>** (<canonical>) — dealer group, <classification> inventory. Pulling channel signals across …"*

6. **Preflight read — `references/_failure-recovery.md` (REQUIRED).** Load this file into working memory BEFORE firing Wave A1. It documents the Write→file pattern for persisting MCP responses + the single orchestrator invocation that drives all post-MCP processing. Without it loaded, the model may default to heredoc-piping the responses, which silently truncates JSON > ~30 KB.

## Script invocation discipline

Scripts in `scripts/` are black boxes. Their complete I/O contract — CLI flags, stdin shape, stdout shape, error envelopes, edge cases — lives in `references/script-contracts.md`. Treat that file as authoritative; the script source is implementation detail and never needs to enter your context.

The 8 scripts: `_common.py`, `compute_quarter_windows.py`, `resolve_ticker.py`, `parse_search.py`, `parse_sold_summary.py`, `compute_earnings_signals.py`, `aggregate_signals.py`, `orchestrate.py`.

**Forbidden:**
- `Read` tool on any `scripts/*.py` file.
- `cat` / `head` / `tail` / `sed` / `awk` / `grep` on script source via Bash.
- Reimplementing script logic inline (no model-side band classification, no inline weighted-mean math, no model-side QoQ/YoY computation, no months-map merge, no make_by_window unwrap, no JSON assembly). The orchestrator owns all of these. If the contract is missing a field, surface it as a doc bug — do not patch with hand-rolled code.
- **Invoking `parse_sold_summary.py` / `compute_earnings_signals.py` / `aggregate_signals.py` directly in W1.** The orchestrator owns these calls. They retain CLI behavior for ad-hoc debugging + tests; the W1 model flow never invokes them.
- **Heredoc-piping (`cat <<'EOF' | ...`) for MCP responses being written to scratch files.** Heredoc truncates silently on JSON > ~30 KB. Use `Write` with the response content as `content`.

### Canonical orchestrator-invocation pattern (post-MCP)

```
1. For each Wave A1/A2 MCP response:
   - PERSISTED (runtime saved to <path>) → use that path directly in the manifest entry.
   - INLINE (response in tool_result) → Write(/tmp/marketcheck/<sid>/<call-name>.json, <response>).
2. After Wave A2 returns: build a manifest JSON listing pre-flight + each scratch file.
   Write(/tmp/marketcheck/<sid>/manifest.json, <manifest-JSON>)
3. python scripts/orchestrate.py --manifest /tmp/marketcheck/<sid>/manifest.json
4. Capture stdout: the structured envelope used for template rendering.
```

The orchestrator does ALL of: per-call parsing, Call A + Call B months-map merge, unwrap discipline, channel-null assignment per classification, compute_earnings_signals invocation, aggregate_signals invocation, dq_events accumulation. The model never sees intermediate parser outputs.

`<session-id>` is the conversation/task id when known; else use `ep-<ticker>-<YYYY-MM-DD>` (e.g., `ep-f-2026-05-14`). `<call-name>` follows the convention in `references/_failure-recovery.md §<call-name> conventions`.

### Scripts directly invoked by the model

Only the pre-flight scripts:
- `compute_quarter_windows.py` (CLI args only) — Step 2.
- `resolve_ticker.py` (CLI args only) — Step 3.
- `orchestrate.py` (CLI `--manifest <path>`) — once, after Wave A2.

`parse_sold_summary.py`, `parse_search.py`, `compute_earnings_signals.py`, `aggregate_signals.py` are owned by `orchestrate.py` (it imports their helper functions in-process). The model never invokes them in W1.

### Wrong patterns

```bash
cat <<'EOF' | python scripts/parse_sold_summary.py ... EOF              # FORBIDDEN — orchestrator owns this; never invoked directly
python scripts/parse_sold_summary.py --file ...                         # FORBIDDEN in W1 — orchestrator imports the parser helpers
python scripts/compute_earnings_signals.py < ...                        # FORBIDDEN in W1 — orchestrator calls compute() in-process
python scripts/aggregate_signals.py < ...                               # FORBIDDEN in W1 — orchestrator calls aggregate() in-process
python scripts/<script>.py --file <invented-path>                       # Only --file paths that you Write yourself or that the MCP runtime emits
Read(scripts/parse_sold_summary.py)                                     # See references/script-contracts.md instead
# Hand-rolling a Python script to compute aggregates inline             # Solvable via orchestrate.py; never invent
# Approximating, eyeballing, or rounding numbers when a parser exists   # The orchestrator output is the source of truth
# Computing QoQ / YoY % in the model from headline numbers              # orchestrator's leading_indicators_raw is the source of truth
```

All workflows complete in two waves (A1 + A2). Wave A1 + Wave A2 responses are written to `/tmp/marketcheck/<session-id>/` and consumed by `orchestrate.py` via the manifest. Scratch files are local to /tmp (session-scoped; auto-cleaned on reboot).

## Tool surface

This skill calls only two MCP tools:

- **`get_sold_summary`** — US-only sold-vehicle aggregates. Used for per-make/per-group sold (two-call split: year-ago_quarter window + prior_quarter→mrcm window, each ≤8 months to stay under the upstream 12-month cap) and EV slice (same split). See `references/sold-summary-safety.md` for parameter discipline:
  - **Always set:** `inventory_type` (TitleCase: `"New"` or `"Used"`), `limit=5000`, `summary_by="state"`, month-aligned dates, `ranking_dimensions="make"` (OEM) or `"dealership_group_name"` (dealer-group).
  - **Never set:** `state` (skill is national-only), `dealer_type`, `is_certified` (CPO out of scope), `model` / `trim` / `body_type` (ticker-level only).
  - Row-count budget: two-call split — Call A (3 months) ≈ 159 rows ≈ 15-30 KB; Call B (≤8 months) ≈ ~318-424 rows ≈ 50-100 KB. Both SAFE within the 5000-row cap and the 12-month date-range cap.
  - **Upstream date-range cap (12 months)**: the API rejects spans > 12 months with HTTP 422 (body `'422 unknown'`). Empirically verified 2026-05-14. No client-side validator catches this — discovered only at runtime. The two-call split is mandatory; do not collapse into a single multi-quarter call.
  - **Upstream rate limit (≤5 concurrent)**: the API rate-limits with HTTP 429 when more than 3-5 concurrent calls are in flight. Empirically observed 2026-05-14 (GM trace: 3 succeed, 4+ trip 429). The conservative default is **5 concurrent per sub-batch** — see §Parallelization below and `references/sold-summary-safety.md §Upstream rate limit` for the canonical rule + fallback to 3 if 5 still trips 429. 429 retries are forbidden within a workflow run.
  - Empirical anchor: **`ranking_measure` controls sort order for `top_n` cut, NOT response columns** — every row carries sold_count, ASP, DOM, MSRP positioning, and avg_msrp simultaneously.

- **`search_active_cars`** — current-inventory snapshot. Used for live active inventory + price/DOM stats (Days Supply num_found input). For OEMs: filter by `make`. For dealer-groups: filter by `mc_dealership_group_name="<canonical>"`. Never filtered by `state` (skill is national-only).

Tools deliberately not used: `decode_vin_neovin`, `predict_price_with_comparables`, `get_car_history`, `search_past_90_days`, `search_uk_*`. None are required for ticker-level channel checks.

## Parallelization (universal contract — Wave A1 + A2 always)

The workflow follows the wave-execution contract with sub-batching for rate-limit safety:

- **A wave is decomposed into sub-batches of at most 5 concurrent `tool_use` blocks per agent message** (current rate-limit-safe default chosen 2026-05-14 per `references/sold-summary-safety.md §Upstream rate limit`; fallback to 3 if 5 still trips 429).
- **Sub-batches fire SEQUENTIALLY with an explicit 6-second sleep between them** (per upstream rate-limiter recovery window — see `references/sold-summary-safety.md §Inter-batch delay`). After each sub-batch's tool_results return, issue `Bash(sleep 6)` as a standalone agent message before the next sub-batch. The first sub-batch in a Wave skips the sleep; the Wave A1 → Wave A2 boundary DOES get a 6-second sleep. "Natural round-trip pause" is NOT sufficient — empirically ~1-2s, below the rate-limiter recovery window.
- **Calls WITHIN a sub-batch fire in PARALLEL** via the single agent message's multiple `tool_use` blocks. Calls within a sub-batch share no cross-dependency on each other's parsed output.
- **Wait for the entire wave** (all sub-batches) before issuing the next wave. Don't pipeline waves.
- **Wave A is ALWAYS split into A1 + A2.** Wave A1 = sold-vehicle data (two-call date-split per channel); Wave A2 = active inventory.
- **429 retries are FORBIDDEN within the same workflow.** If a call returns 429, log DQ event (a) and continue with the rest of the sub-batch. The inter-batch delay is preventive; the no-retry rule is the backstop when prevention fails.

Wall-clock budget at a glance (per-sub-batch MCP round-trip ~6-8s + 6s inter-batch sleep):
- W1, TSLA / RIVN / LCID (pure_play 1 make, 1+1 sub-batches): ~21-27s.
- W1, KMX (Used-only DG, 1+1 sub-batches): ~21-27s.
- W1, Both DG (AN/LAD/PAG/SAH/GPI/ABG/CVNA, 2+1 sub-batches): ~32-44s.
- W1, F / TM / HMC / NSANY (legacy 2 makes, 3+1 sub-batches): ~43-58s.
- W1, BMWYY / HYMTF (legacy 3 makes, 4+2 sub-batches): ~60-80s.
- W1, GM (legacy 4 makes, 5+2 sub-batches): ~81-106s.
- W1, VWAGY (legacy 5 makes, 6+2 sub-batches): ~95-125s.
- W1, STLA (legacy 7 makes, 9+3 sub-batches): ~156-186s.

The sub-batching + delay cost is real on multi-make tickers but unavoidable until the upstream API allows higher concurrency or a server-side aggregation tool is added (out of scope — upstream repo). The +6s per gap buys near-zero 429 leakage; the trade-off favors verdict accuracy over wall-clock.

Per-workflow wave structure and per-ticker sub-batch tables live in `references/w1-channel-check.md`.

## Truncation handling

Wave A1's longer (≤8-month Call B) sold-summary responses often exceed the in-context response cap (~30 KB) — the MCP runtime persists those responses to disk and returns a path. The model:

- Sees `Error: result (N chars) exceeds maximum allowed tokens. Output saved to <path>` instead of the JSON.
- Uses the runtime's `<path>` directly in the manifest entry's `file` field — no Write needed.
- The orchestrator's per-file reading handles the truncation envelope via `_common._maybe_unwrap` automatically.
- **`get_sold_summary` is the only tool whose payload is NOT envelope-wrapped** (raw JSON); the orchestrator handles both shapes transparently.

See `references/_failure-recovery.md` for the canonical handling flow.

## Workflow 1 — Earnings-Preview Channel Check

The only workflow in this skill. Pulls per-make (OEM) or per-group (dealer-group) sold data across `year_ago_quarter`, `prior_quarter`, `current_quarter`, and `most_recent_complete_month` via **two sold-summary calls per channel** (Call A: year-ago window 3 mo; Call B: prior→mrcm window ≤8 mo) — the split is required to stay under the upstream API's 12-month date-range cap. EV slice uses the same split. Plus live active inventory in Wave A2. After Wave A2, the model invokes `scripts/orchestrate.py` once with a manifest JSON; the orchestrator parses each scratch file, merges Call A + Call B months-maps, unwraps the inner `make_by_window`/`group_by_window` blocks, assembles the compute input, runs `compute_earnings_signals.compute()` (multi-quarter aggregation, no banding) then `aggregate_signals.aggregate()` (per-metric bands + 8 composite slots + 4-tier verdict + per-make divergence), and emits a single structured envelope. The model then renders the 12-section earnings-preview report (BULLISH / BEARISH / NEUTRAL / MIXED / null) with composite verdict, leading-indicators table (QoQ + YoY columns + band), optional per-make breakdown, inventory-health (Days Supply Used + New), EV transition (legacy / Both only), Mix (dealer-group Both only), Bull Case, Bear Case, signal drivers, and 3-sentence earnings-preview statement.

→ Full spec in **`references/w1-channel-check.md`**.

## Output

W1 renders via `assets/w1-output-template.md`. The template is the **single source of truth** for block structure, table schemas, verdict wording, footnote rules, the Bear-Case `weakest=null` fallback (closes Phase 6 finding C12), and self-check items. SKILL.md does not inline block definitions.

Render rules:
- Volume: integer with thousands separator (`125,000`).
- ASP: `$` prefix, no decimals, thousands separator (`$48,200`).
- DOM: 1 decimal place + ` days` suffix (`84.2 days`).
- DOM (median): same as DOM (`38.0 days`); display-only, no band.
- Active inventory percentiles (P50/P75/P90/Median): same as the mean of that field — price → `$` + integer + thousands separator (`$28,900`); DOM → integer + ` days` (`52 days`).
- mrcm sold: thousands-separated integer (`4,234`).
- Days Supply: integer + ` days` (`62 days`).
- share_pct: 1-decimal percentage (`47.2%`).
- QoQ / YoY percentage: signed % with 1 decimal (`+2.9%`, `-3.5%`).
- DOM delta: signed days (`-3.9 days`).
- bps delta (MSRP gap / EV share): signed integer + ` bps` (`+90 bps`, `-150 bps`).
- pp delta (Mix): signed float + ` pp` (`+0.8 pp`, `-1.2 pp`).
- Band cells: verbatim band string with emoji prefix (🟢 BULLISH / 🟡 NEUTRAL / 🟠 CAUTION / 🔴 BEARISH).
- Verdict emoji: BULLISH → 🟢, BEARISH → 🔴, NEUTRAL → 🟡, MIXED → ⚪, null → ⚫.
- Render `—` (em-dash) when the value is null.

## Halt conditions

The workflow has exactly one post-MCP halt path beyond pre-flight gating:

| Halt | Where | Surface |
|---|---|---|
| `country != "US"` | Pre-flight step 1 | One-line message; no MCP calls fired |
| `resolve_ticker.error_type == "no_candidates"` | Pre-flight step 3 | One-line message with closest fuzzy candidates; no MCP calls fired |
| orchestrator output's `error_type == "no_current_quarter_data"` | After Wave A1 + Wave A2 | Render the halt block from `assets/w1-output-template.md §Halt rendering` |
| orchestrator output's `error_type ∈ {"manifest_invalid", "all_calls_failed", "scratch_file_unreadable", "missing_manifest", "internal_error"}` | After orchestrator invocation | One-line error to the user; no template render — investigate root cause |

**Every other failure degrades gracefully** (orchestrator handles internally per `references/_failure-recovery.md §Halt vs degrade`):
- Missing prior_quarter sold → `qoq_pct` fields null; verdict reduces over remaining slots.
- Missing year_ago_quarter sold → `yoy_pct` fields null; `volume_momentum.degraded_to: "qoq_only"`; DQ event (m).
- Missing one channel's active call → that channel's Days Supply null; the other channel still bands; DQ event (a).
- Missing mrcm sold → both Days Supply slots null; verdict reduces over remaining slots.
- Missing EV slice on a non-pure_play ticker → `ev_share` slot null; DQ event (k).

The graceful-degradation rules apply to genuinely-missing data — the orchestrator surfaces DQ events for each degradation.

## Data Quality event log

Accumulate a running list across the workflow; render in a "Data Quality Notes" section if non-empty. Every event has exactly ONE canonical emission location.

| Event | Trigger | Emitted by |
|---|---|---|
| (a) | MCP tool returned an error envelope (network, 422, 5xx, 429, unexpected_shape) OR a scratch file referenced by the manifest could not be read | `orchestrate.py` (per-call parser layer) |
| (b) | Truncation envelope unwrapped via runtime path | `_common._maybe_unwrap` (called inside orchestrator) |
| (c) | `resolve_ticker` resolution = fuzzy | `resolve_ticker.py` |
| (d) | Active-inventory `stats_present: false` — `num_found` rendered; price/DOM stats skipped for that channel | `compute_earnings_signals._build_active_inventory_channel` |
| (f) | Mix dimension skipped (Used-only / New-only DG OR OEM ticker — Mix is dealer-group `Both` only) | `compute_earnings_signals._build_mix_block` + OEM branch |
| (i) | Low-volume slice flagged (current-quarter sold < 100 for any per-make or EV slice) | `compute_earnings_signals._build_*` |
| (k) | EV slice skipped (pure_play OR zero current-quarter EV volume) → EV block omitted | `compute_earnings_signals._build_ev_block` |
| (l) | Cross-make divergence (per-make Volume QoQ band ≥2 score-points from ticker composite) | `orchestrate.py` (canonical formatter for `aggregate.per_make_divergence` non-empty) |
| (m) | Year-ago quarter has no usable data → `yoy_*` fields null; `volume_momentum.degraded_to: "qoq_only"` | `compute_earnings_signals._compute_*_block` |
| (n) | Prior quarter has no usable data → `qoq_*` fields null; `volume_momentum.degraded_to: "yoy_only"` (rare; defensive) | `compute_earnings_signals._compute_*_block` |
| (r) | Per-make breakdown excluded a make — no current-quarter sold data OR no data assembled | `compute_earnings_signals._build_per_make_raw` |

Skip the section when the list is empty.

## Self-check

The W1 template carries the 19-item self-check (covering quarter alignment, Option-A row budget, mrcm pairing, `weakest=null` suppression, no consensus/buy-sell-hold language). Run silently before returning; emit one of:

- **All checks pass** → one-line footer: `✓ Verified: ticker resolution, quarter windows, signal aggregation, Days Supply mrcm pairing, weakest=null suppression rule.`
- **Any check fails** → emit failures only, prefixed `⚠`, with a one-line note on what was corrected.
- **Never** render a pass-by-pass checkbox grid.

## What this skill does NOT do

- **Stock-price prediction or EPS forecasts.** This skill produces operational channel signals; converting those to price targets or EPS estimates is the analyst's job.
- **Comparison to street estimates / consensus.** The skill has no access to sell-side estimates. The verdict is a standalone channel-derived signal, not a consensus-relative one.
- **Buy / sell / hold recommendations.** Verdict is BULLISH / BEARISH / NEUTRAL / MIXED / null — no trading recommendation language anywhere in the output.
- **Brand-orphan / unknown ticker recovery.** Per Phase 5 §5a, unknown tickers halt at `resolve_ticker`. The universe of tracked tickers is the 21-row map in `references/ticker-mapping.md`. For monthly-cadence broader-make analysis, route to `oem-stock-tracker`.
- **Monthly-cadence MoM analysis.** Earnings-preview is quarterly cadence by design — the frame is "into the next print." For 30-day MoM signal on OEMs, use `oem-stock-tracker`.
- **Per-VIN appraisal** (route to `vehicle-appraiser`).
- **Per-listing detail** (route to `competitive-pricer`; `search_past_90_days` is not called by this skill).
- **UK / non-US analysis** (`get_sold_summary` is US-only; tracked tickers are US-listings).
- **State-scoped analysis** — the skill is national-only. State-scoped questions are out of scope.
- **CPO-specific analysis** — out of scope; `is_certified=true` is not used.
- **Multi-ticker comparison in a single render** — W1 is single-ticker. For head-to-head comparison of two OEMs, use `oem-stock-tracker W2`. For a portfolio sweep across multiple coverage tickers, use the `analyst:portfolio-scanner` agent which calls this skill per ticker.
- **Composite cross-ticker scoring across all 21 tickers** — out of scope; a separate cohort/cohort-percentile skill could cover this in future.
- **Quarterly cadence for monthly metrics**: ASP, MSRP gap, DOM, EV share, and Mix all derive from quarterly aggregates — there is no MoM intra-quarter breakdown in this skill.
