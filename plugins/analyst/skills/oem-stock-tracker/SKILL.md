---
name: oem-stock-tracker
description: Investment signals on the operational health of publicly traded US automotive OEMs (F, GM, TM, HMC, STLA, TSLA, RIVN, LCID, HYMTF, NSANY, MBGAF, BMWYY, VWAGY). Use when an equity analyst asks "how is Ford doing", "investment signal for GM", "Toyota demand trends", "is Stellantis losing share", "compare Ford vs GM", "top 5 US OEMs", "pre-earnings channel check on an OEM stock", "EV transition progress for Ford", "TSLA vs other EV makers", or any ticker-tied operational read with BULLISH / BEARISH / NEUTRAL / CAUTION / MIXED verdict expectations. Three workflows — single-OEM investment signal, head-to-head OEM comparison, US OEM market-share leaderboard. Distinct from `dealer-group-health-monitor` (covers dealer-group tickers AN/LAD/PAG/SAH/GPI/ABG/KMX/CVNA — this skill HALTS and redirects for those) and from `vehicle-appraiser` (per-VIN appraisal, not OEM signals). Prefer this skill for ticker-tied verdict requests on OEM manufacturer stocks.
version: 1.0.0
---

# OEM Stock Tracker — Investment Signals (Updated)

Equity-analyst-facing skill for operational channel checks on US publicly-traded automotive OEM stocks. Every numeric block — leading indicators, MoM deltas, signal verdicts, per-make breakdown, EV transition, market share — is computed by Python scripts in this skill, not by the model. Same inputs always produce the same verdict.

The frame is *channel check between earnings*: aggregate sold-vehicle data + live active inventory + market-share context tell you which way operational metrics are moving 30-90 days before management's quarterly print. Use the verdict to decide whether to buy/sell/hold the ticker into earnings, with full transparency on which metrics drove which signal.

## Before you start

1. **Profile load (inline, no script).** Read `marketcheck-profile.md` from the project root. Parse YAML frontmatter and the JSON body. Frontmatter wins on conflict (it's the curated view); JSON body provides fields the frontmatter omits. Extract:
   - `location.country` — always present in both shapes (frontmatter has it nested under `location:`; the JSON body may have it nested OR at top level — check both). **If country != "US", halt with: *"This skill is US-only; `get_sold_summary` has no UK variant."***
   - `analyst.tracked_tickers` — only present in analyst-shaped profiles. If non-empty AND the user prompted without a ticker, suggest the first one as a default.
   - `analyst.tracked_makes` — similarly, used to suggest a brand-orphan default when input is absent.
   - `analyst.tracked_states` — NOT used by this skill (state-scoped analysis is out of scope; the skill is national-only).
   - If the profile is missing or unparseable → prompt the user for the OEM ticker / brand directly. No halt.

2. **Date windows.** Run `scripts/compute_month_windows.py --today <currentDate> --baseline-months 3`. The script emits `current_month` (the calendar month that ended strictly before today), `prior_month` (the month before that), and `baseline_3mo_window` (a 3-month date range covering months −3, −2, −1 relative to current — used by a single multi-month `get_sold_summary` call per make).

3. **OEM resolution.** Run `scripts/resolve_oem.py --input "<user input>"`. Three-tier resolution: exact ticker → reverse make-name lookup → fuzzy via `difflib.SequenceMatcher` ≥0.5. Captures `ticker`, `company_name`, `makes[]`, `classification` (`legacy` or `pure_play`).

   Branches:
   - `ok=true` → continue with W1 (or W2 if user asked for comparison).
   - `error_type=dealer_group_redirect` → halt with: *"`<TICKER>` is a dealer-group stock; route to `dealer-group-health-monitor`."*
   - `error_type=no_candidates` → fall through to the **brand-orphan recovery branch**:
     1. Fire one `search_active_cars` facet-discovery call: `facets="make|0|100"`, `rows=0`, `country="US"`. Pipe through `parse_search.py --mode facets`. `100` is the doc-stated upper bound suited to the active US market's make universe (~80 makes).
     2. From the returned `facets[]` list, present the 3-5 make names with highest string similarity to the user's input.
     3. Show the user: *"We don't track a US-listed OEM matching `<input>`. The active US market has `<facet1>`, `<facet2>`, `<facet3>`. Pick one or give a different brand."*
     4. After the user picks a brand `<X>`, **construct the workflow context inline** with `classification="brand_orphan"`, `ticker=null`, `company_name=<X>`, `makes=[<X>]`. No second `resolve_oem.py` call.
     5. Log a DQ event (j): "Brand-orphan path taken — `<X>` resolved via active-market facets."
   - If recovery fails (no plausible matches OR user declines) → halt cleanly: *"`<input>` is not a US-listed OEM stock and isn't a recognizable make in the active US market. Try a different brand."*

4. **Channel selection.** Determine `inventory_type` from user input:
   - Default: `"New"` (TitleCase for `get_sold_summary`) / `"new"` (lowercase for `search_active_cars`).
   - If user says "Used" / "used" inventory: `"Used"` / `"used"`.
   - **The skill propagates this choice consistently to EVERY MCP call** — no hardcoding. See `references/sold-summary-safety.md §inventory_type / car_type discipline` for the full per-call audit.

5. **Confirm to user**: *"Analyzing **<ticker>** (<company_name>): <Make1, Make2, …> — <classification>. Pulling <inventory_type> signals for <current_month.label> vs. <prior_month.label> with 3-month baseline <baseline_3mo_window.label>…"*

6. **Preflight read — `references/_failure-recovery.md` (REQUIRED).** Load this file into working memory BEFORE firing Wave A1. It documents the **only canonical pattern** for invoking `parse_sold_summary.py` (Write→file→--file) and the recovery flow for MCP error envelopes. Without it loaded, the model defaults to heredoc-piping which silently truncates JSON > ~30 KB. Past sessions that skipped this read all produced wrong-data outputs.

## Script invocation discipline

Scripts in `scripts/` are black boxes. Their complete I/O contract — CLI flags, stdin shape, stdout shape, error envelopes, edge cases — lives in `references/script-contracts.md`. Treat that file as authoritative; the script source is implementation detail and never needs to enter your context.

The 8 scripts: `_common.py`, `compute_month_windows.py`, `resolve_oem.py`, `parse_search.py`, `parse_sold_summary.py`, `compute_oem_stats.py`, `aggregate_signals.py`, `compute_w3_rollup.py`.

**Forbidden:**
- `Read` tool on any `scripts/*.py` file.
- `cat` / `head` / `tail` / `sed` / `awk` / `grep` on script source via Bash.
- Reimplementing script logic inline (no model-side band classification, no inline weighted-mean math). If the contract is missing a field, surface it as a doc bug — do not patch with hand-rolled code.
- **Setting a parser-required input field to `null` and continuing the pipeline.** If a parser fails for any reason, surface as a doc bug and halt; never substitute `null` for missing data and rely on the script "skipping it." `compute_oem_stats` now refuses incomplete inputs with loud DQ events `(p)`–`(t)`, so this pattern is detected at boundary too.
- **Heredoc-piping (`cat <<'EOF' | parser`) for `parse_sold_summary.py` inputs.** Heredoc truncates silently on JSON > ~30 KB; you'll get partial data with no error. Use the Write→file pattern below instead.

### Canonical parser-invocation pattern (Wave A1 + A2 — `parse_sold_summary.py`)

```
1. Receive the MCP response (either inline in tool result, or persisted by runtime).
2. Write(/tmp/marketcheck/<session-id>/<call-name>.json, <response-string>).
3. python scripts/parse_sold_summary.py --<flag> <arg> --file /tmp/marketcheck/<session-id>/<call-name>.json
```

Why this is the **only** pattern for `parse_sold_summary.py`:
- `parse_sold_summary` inputs can be 1 KB (small per-make EV slice) up to 1.5 MB (M=3 leaderboard). Heredoc piping is unreliable above ~30 KB and crashes silently — the parser sees fewer rows than the response actually contains, and downstream rollups are wrong with no error.
- `Write` accepts arbitrary string content. `Write→file→--file` is deterministic and works for every response size.

`<session-id>` is the conversation/task id when known; else use `oem-<ticker>-<YYYY-MM-DD>`. `<call-name>` is descriptive — see `references/_failure-recovery.md` for the canonical naming.

### Parsers that accept stdin pipe (small inline responses only)

- `parse_search.py` (~1 KB stats responses) — `cat <<'EOF' | parse_search.py` is fine.
- `compute_month_windows.py`, `resolve_oem.py` (CLI args only, no stdin).
- `compute_oem_stats.py`, `aggregate_signals.py`, `compute_w3_rollup.py` (small assembled JSON inputs ≤ ~30 KB — usually safe via stdin, but Write→file is acceptable when uncertain).

### Wrong patterns

```bash
cat <<'EOF' | python scripts/parse_sold_summary.py ... EOF              # FORBIDDEN — heredoc truncates >30 KB silently
python scripts/<script>.py --file <invented-path>                       # Only --file paths that you Write yourself or that the MCP runtime emits
Read(scripts/parse_sold_summary.py)                                     # See references/script-contracts.md instead
# Hand-rolling a Python script to compute aggregates inline             # Solvable via Write→file→parser; never invent
# Approximating, eyeballing, or rounding numbers when a parser exists   # The parser is the source of truth
# Setting per_make[X].segment_mix = null because parser "failed"        # Write→file→parser ALWAYS works; halt before allowing null
```

All workflows complete in two waves (A1 + A2). Wave A1 + Wave A2 responses are written to `/tmp/marketcheck/<session-id>/` and parsed via `--file`. Scratch files are local to /tmp (session-scoped; auto-cleaned on reboot).

## Tool surface

This skill calls only two MCP tools:

- **`get_sold_summary`** — US-only sold-vehicle aggregates. Used for per-make sold (multi-month), market-share leaderboard, segment mix, and EV slice. See `references/sold-summary-safety.md` for parameter discipline (always-set: `inventory_type`, `limit=5000`, `summary_by="state"`, month-aligned dates; never-set: `state`, `dealer_type`). Empirical anchor: **`ranking_measure` controls sort order for `top_n` cut, NOT response columns** — every row carries sold_count, ASP, DOM, MSRP positioning, and avg_msrp simultaneously.

- **`search_active_cars`** — current-inventory snapshot. Used for active inventory + price/DOM stats per make (Days Supply input) and for the brand-orphan recovery facet-discovery call.

Tools deliberately not used: `decode_vin_neovin`, `predict_price_with_comparables`, `get_car_history`, `search_past_90_days`, `search_uk_*`. None are required for OEM-level analysis.

## Parallelization (universal contract — Wave A1 + A2 always)

Every workflow follows the wave-execution contract:

- **A wave is a batch of MCP calls fired in a single agent message** (multiple `tool_use` blocks). The runtime dispatches them concurrently.
- **Within a wave, calls share no cross-dependency** on each other's parsed output. Calls that need another call's output go in a later wave.
- **Wait for the entire wave** before issuing the next. Don't pipeline waves.
- **Wave A is ALWAYS split into A1 + A2** for runtime-concurrency-cap safety (this skill's W1 for STLA = 30 calls; splitting into two waves of ~16 + ~14 keeps each wave well within typical caps).
- **Never serialize calls within a wave** — a wave's wall clock is set by its slowest call.

Wall-clock budget at a glance:
- W1: ~25–30s (Wave A1 ~12-15s + Wave A2 ~12-15s).
- W2: ~25–35s (heavier; depends on N_A + N_B makes).
- W3: ~8–12s (single call).

If runtime caps concurrent `tool_use` blocks below a wave's size, the runtime silently serializes the overflow. Functionality preserved; wall clock grows. No special handling required.

Per-workflow wave structure lives in the per-workflow reference files.

## Truncation handling

Most calls in this skill don't truncate (payloads ~212-2650 rows, well below the 5000-row server cap and within in-context size). If any response truncates:

- The MCP layer emits `Error: result (N chars) exceeds maximum allowed tokens. Output saved to <path>`.
- Pipe the saved path to the relevant parser via `--file <path>`. The shared `_common._maybe_unwrap` helper handles the envelope.
- **`get_sold_summary` is the only tool whose payload is NOT envelope-wrapped** (raw JSON); `parse_sold_summary.py` handles both shapes. See `references/script-contracts.md §parse_sold_summary` for the unwrap branch and error-envelope catalogue.

## Workflow 1 — Single OEM Investment Signal

Triggered by "how is Ford doing", "investment signal for GM", "Toyota demand trends", "is Stellantis losing share", "pre-earnings channel check on TSLA". Pulls per-make sold (multi-month covering current + prior + 3-mo baseline) + active inventory + market-share top-25 (current + prior) + EV slice (legacy) OR EV market leaders (pure-play) + segment mix for one resolved OEM. Runs `compute_oem_stats.py` (raw aggregation) then `aggregate_signals.py` (bands + composites + verdict + divergence). Renders 11-section investment-signal report (BULLISH/BEARISH/NEUTRAL/CAUTION/MIXED) with composite verdict, leading indicators table, per-make breakdown, inventory health, market-share context, EV block, segment mix, signal drivers, and ticker-impact statement.

→ Full spec in **`references/w1-single-oem.md`**.

## Workflow 2 — Compare Two OEMs

Triggered by "compare Ford vs GM", "F vs TSLA head-to-head", "is GM outperforming Ford right now". Pairs two OEMs for a current-month snapshot. **No 3-mo baseline** (single-month static comparison; MoM lives in W1). Halts before any MCP call if both inputs resolve to the same ticker. Renders side-by-side KPI table + mix breakdown + 2-sentence pair-trade thesis.

→ Full spec in **`references/w2-compare-oems.md`**.

## Workflow 3 — US OEM Market Share Leaderboard

Triggered by "top 5 US OEMs by volume", "biggest OEMs this month", "US OEM market share leaderboard". Single sold-summary call with `top_n=25` (no make filter), sliced locally to the user's requested N (1-10, default 5). Rolls up makes by ticker via the 13-row OEM map. No per-row verdicts (no MoM data). Renders cohort headline + leaderboard table with ticker + contributing makes + sold + share %.

→ Full spec in **`references/w3-market-share-leaderboard.md`**.

## Output

Each workflow renders via its template in `assets/`. Templates are the **single source of truth** for block structure, table schemas, verdict wording, and self-check items. SKILL.md does not inline block definitions.

Render rules (all workflows):
- Volume: integer with thousands separator (`125,000`).
- ASP: `$` prefix, no decimals, thousands separator (`$48,200`).
- DOM: 1 decimal place + ` days` suffix (`84.2 days`).
- Efficiency Score: 1 decimal place.
- MoM percentage: signed % with 1 decimal (`+2.9%`, `-3.5%`).
- DOM delta: signed days (`-3.9 days`).
- bps delta (MSRP gap / market share / EV transition): signed integer + ` bps` (`+30 bps`, `-25 bps`).
- Render `—` (em-dash) when the value is null.

## Data Quality event log

Accumulate a running list across workflows; render in a "Data Quality Notes" section if non-empty. Every event has exactly ONE canonical emission location.

| Event | Trigger | Emitted by |
|---|---|---|
| (a) | MCP tool returned an error envelope | model logs (orchestration layer) |
| (b) | Truncation envelope unwrapped via `--file <path>` | `parse_sold_summary._maybe_unwrap` / `parse_search._maybe_unwrap` |
| (c) | `resolve_oem` resolution = fuzzy (user confirmed) | `resolve_oem.py` |
| (d) | Active-inventory `stats_present: false` | `compute_oem_stats._build_active_inventory` |
| (e) | Days-Supply footnote rendered (always when section renders) | template-side (W1/W2 templates) |
| (f) | Workflow branch skipped by design | model logs (W2 single-snapshot, W3 no-verdict, etc.) |
| (g) | Target ticker absent from market-share top-25 | `compute_oem_stats._compute_market_share` |
| (h) | Segment-mix channel returned zero-volume | `compute_oem_stats._build_segment_mix` |
| (i) | Low-volume make flagged (`sold_count_current < 100/month`) | `compute_oem_stats._build_per_make_raw` |
| (j) | Brand-orphan path (input → facet-discovery → no parent ticker) | model logs (W1 pre-flight) / `compute_w3_rollup` for top-25 orphans |
| (k) | EV slice skipped for pure-play OR returned zero for legacy → EV block omitted | `compute_oem_stats._build_ev_block` |
| (l) | Cross-make divergence (per-make volume band ≥2 score-points from ticker composite) | `aggregate_signals._detect_per_make_divergence` |
| (m) | Prior-month EV volume below 500 units nationally — Δ noisy | `compute_oem_stats._build_ev_block` |
| (n) | Zero-sold month in baseline for a make — baseline_3mo trend may underestimate | `compute_oem_stats._detect_zero_sold_baseline_months` |
| (o) | Legacy `market_top25.prior` shape used — orchestration spec drift | `compute_oem_stats._compute_market_share` |
| (p) | Partial segment-mix — one or more makes' segment_mix was null; rollup is incomplete | `compute_oem_stats._build_segment_mix` |
| (q) | Partial active inventory — one or more makes' active block was null; Days Supply rollup is incomplete | `compute_oem_stats._build_active_inventory` |
| (r) | Per-make breakdown excluded a make due to empty months (no sold data) | `compute_oem_stats._build_per_make_raw` |
| (s) | Zero-EV make excluded from EV per-make breakdown (informational, not a warning) | `compute_oem_stats._build_ev_block` |
| (t) | Math consistency mismatch — sum of per-make / seg-mix / active diverges from headline beyond threshold | `compute_oem_stats.main()` |
| (u) | Empty `market_top25.current` — leaderboard returned no rows; market-share verdict cannot be computed | `compute_oem_stats._compute_market_share` |

Skip the section when the list is empty.

## Self-check

Each workflow's template carries the self-check items. Run silently before returning; emit one of:

- **All checks pass** → one-line footer: `✓ Verified: profile, signal aggregation, market share context, days-supply caveat.` (W1) or equivalent per workflow.
- **Any check fails** → emit failures only, prefixed `⚠`, with a one-line note on what was corrected.
- **Never** render a pass-by-pass checkbox grid.

## What this skill does NOT do

- **Stock-price prediction or EPS forecasts.** This skill produces operational signals; converting those to price targets is the analyst's job.
- **Per-VIN appraisal** (route to `vehicle-appraiser`).
- **Per-listing detail** (route to `competitive-pricer`; `search_past_90_days` is not called by this skill).
- **UK / non-US analysis** (`get_sold_summary` is US-only).
- **State-scoped analysis** — the skill is national-only. State-scoped questions are out of scope.
- **Dealer-group ticker analysis** — `resolve_oem.py` halts with redirect to `dealer-group-health-monitor`.
- **Production / plant-level signals** — not exposed by the MCP surface.
- **3+ OEM comparison in a single render** — W2 is pairwise. For 3+ tickers, run W1 per ticker.
- **Used-EV resale analysis** — a niche v1.1 candidate. v1 treats EV slice with user's chosen channel.
- **CPO-specific analysis** — out of scope; `is_certified=true` is not used.
- **Composite cross-ticker scoring across all 13 OEMs** — out of scope; a separate `oem-benchmarking` skill could cover this in future.
