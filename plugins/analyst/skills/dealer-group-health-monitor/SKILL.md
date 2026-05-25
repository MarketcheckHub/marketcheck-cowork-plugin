---
name: dealer-group-health-monitor
description: Investment signals on the operational health of publicly traded dealer-group stocks (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA). Use when an equity analyst asks "how is AutoNation doing", "LAD health check", "CarMax volume signal", "Carvana DOM trend", "is Lithia gaining share", "compare AutoNation vs Lithia", "top dealer groups by volume", "pre-earnings channel check on a dealer group", or any ticker-tied operational read with BULLISH / BEARISH / NEUTRAL / CAUTION / MIXED verdict expectations. Three workflows — single-group health check, head-to-head comparison, top-N leaderboard. Distinct from `group-dashboard` (multi-tracked portfolio view) and `group-benchmarking` (cross-group ranking without per-ticker verdicts). Prefer this for ticker-tied verdict requests; prefer `group-benchmarking` for "rank all 8 dealer groups" without per-ticker signals.
version: 1.0.0
---

# Dealer Group Health Monitor — Investment Signals (Updated)

Equity-analyst-facing skill for operational channel checks on US publicly-traded dealer-group stocks (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA) and the broader 471-group enum that backs `get_sold_summary`. Every numeric block — KPIs, MoM deltas, signal verdicts, peer rankings — is computed by Python scripts in this skill, not by the model. Same inputs always produce the same verdict.

The frame is *channel check between earnings*: aggregate sold-vehicle data + live active inventory tell you which way operational metrics are moving 30-90 days before management's quarterly print. Use the verdict to decide whether to buy/sell/hold the ticker into earnings, with full transparency on which metrics drove which signal.

## Before you start

1. **Profile load (inline, no script).** Read `marketcheck-profile.md` from the project root. Parse YAML frontmatter and the JSON body. Frontmatter wins on conflict (it's the curated view); JSON body provides fields the frontmatter omits. Extract:
   - `location.country` — always present in both shapes (frontmatter has it nested under `location:`; the JSON body may have it nested OR at top level — check both). **If country != "US", halt with: *"This skill is US-only; get_sold_summary has no UK variant."***
   - `analyst.tracked_tickers` — only present in analyst-shaped profiles. If non-empty, suggest one as a default when prompting.
   - `location.state` — used as a hint for state-scoped sub-questions; not required.
   - If the profile is missing or unparseable → prompt the user for the ticker/group directly. No halt.

2. **Date windows.** Run `scripts/compute_month_windows.py --today <currentDate>`. The script emits `current_month` (the calendar month that ended strictly before today) and `prior_month` (the month before that). Strictly-before sidesteps the race where `get_sold_summary` aggregates lag the calendar.

3. **Group resolution.** Run `scripts/resolve_group_name.py --input "<user input>"`. Order: enum exact-match → ticker symbol → fuzzy via `difflib.SequenceMatcher`. Captures `canonical`, `ticker` (may be null), `classification` (Used-only / New-only / Both).

   On `error_type=no_candidates`, fall through to the **recovery branch** before halting:

   - Fire one `search_active_cars` facet-discovery call: `facets="mc_dealership_group_name|0|1000"`, `rows=0`, `country="US"`. Pipe through `parse_search.py --mode facets`. `1000` is the doc-stated upper bound for the facet `limit` and covers the full active-facet universe (~400 names) — top-20 only catches the giants and misses the long-tail of regional / private groups.
   - From the returned `facets[]` list, present the 3-5 names closest to the user's input. Use the model's own string-similarity judgment — these are live-market group names, not the bundled enum.
   - Show the user: *"We don't have sold-summary aggregates for any close match to `<input>`. The active market has `<facet1>`, `<facet2>`, `<facet3>`. Retry with one of those, or give a different group."*
   - When the user picks a name, re-run `resolve_group_name.py --input "<picked>"`. If it now resolves (exact match against the bundled enum), proceed. If it still misses, halt with: *"`<picked>` exists in active inventory but isn't in the sold-summary enum — no MoM aggregates are available for this group. Try a different name."* Do NOT bypass `resolve_group_name.py` to call `get_sold_summary` directly; the tool returns a ~10 KB error string on enum miss.
   - Log a DQ event `(c) resolved-group-name fuzzy match (recovery via active-facets)` with the input, the facet candidates shown, and the user's pick.

   The recovery branch fires only on the cold path. The hot path (exact / ticker / fuzzy success above 0.5) skips it entirely — no extra MCP call.

## Script invocation discipline

Scripts in `scripts/` are black boxes. Their complete I/O contract — CLI flags, stdin shape, stdout shape, error envelopes, edge cases — lives in `references/script-contracts.md`. Treat that file as authoritative; the script source is implementation detail and never needs to enter your context.

The 7 scripts: `_common.py`, `compute_month_windows.py`, `resolve_group_name.py`, `parse_search.py`, `parse_sold_summary.py`, `compute_group_stats.py`, `aggregate_signals.py`.

**Forbidden:**
- `Read` tool on any `scripts/*.py` file.
- `cat` / `head` / `tail` / `sed` / `awk` / `grep` on script source via Bash.
- Reimplementing script logic inline (no model-side `_aggregate_for_group`, no inline weighted-mean math). If the contract is missing a field, surface it as a doc bug — do not patch with hand-rolled code.

**Why:** Each unread script saves ~100–500 lines of context. Reading source tempts inline reimplementation, which silently diverges from the script's real behavior and breaks the "same inputs always produce the same verdict" guarantee that anchors this skill's value to equity analysts.

**Right pattern (stdin pipe, no scratch file):**
```bash
echo '<mcp-response-string>' | python scripts/<script>.py --<flag> <arg>
```

**Wrong patterns:**
```bash
Write(/tmp/marketcheck/lad/a1_used_apr.json, <response>)   # forbidden — no scratch files
python scripts/<script>.py --file /tmp/...                  # forbidden when small enough to inline
Read(scripts/parse_sold_summary.py)                          # forbidden — see contracts file
```

The `--file <path>` flag on the parsers exists ONLY for the rare case where the MCP runtime itself saves an oversized response to disk and returns an `Output saved to <path>` error string. In that case — and only that case — pipe the runtime-written path to `--file`. You never create those files yourself.

The gold-standard `competitive-pricer` skill DOES use a `/tmp/marketcheck/<run_id>/` scratch dir because its VIN-level batch payloads need cross-wave state survival. **This skill is different.** All workflows complete in a single wave; payloads are aggregated and small; intermediate state never needs to leave the model's context.

## Tool surface

This skill calls only two MCP tools:

- **`get_sold_summary`** — US-only sold-vehicle aggregates. Used for target-group sold counts, peer leaderboards, and segment mix breakdowns. See `references/sold-summary-safety.md` for parameter discipline (always-set: `inventory_type`, `limit=5000`, month-aligned dates; never-set: `state` for our use, `dealer_type`).

- **`search_active_cars`** — current-inventory snapshot. Used for active count + price/DOM stats per group. The `mc_dealership_group_name` filter triggers syndication-route routing (per the doc warning); empirically verified on 2026-05-08 that `data.stats.{price,dom}` returns the standard shape. `parse_search.py` includes a defensive fallback for the absent-stats case.

Tools deliberately not used: `decode_vin_neovin`, `predict_price_with_comparables`, `get_car_history`, `search_past_90_days`, `search_uk_*`. None are required for group-level analysis.

## Parallelization (universal contract)

Every workflow follows the wave-execution contract:

- **A wave is a batch of MCP calls fired in a single agent message** (multiple `tool_use` blocks). The runtime dispatches them concurrently.
- **Within a wave, calls share no cross-dependency** on each other's parsed output. Calls that need another call's output go in a later wave.
- **Wait for the entire wave** before issuing the next. Don't pipeline waves.
- **Never serialize calls within a wave** — a wave's wall clock is set by its slowest call. Five serialized MCP calls cost ~60s; the same five fired together cost ~12s.

Wall-clock budget at a glance:
- W1: ~15-18s (single Wave A, 4-7 calls; optional Wave B adds ~12s).
- W2: ~16-19s (single Wave A, 8-12 calls).
- W3: ~8-12s (single call).

Per-workflow wave structure lives in the per-workflow reference files.

## Truncation handling

Most calls in this skill don't truncate (small payloads — `rows=0` stats-only or single-month aggregated rollups). If any response truncates:

- The MCP layer emits `Error: result (N chars) exceeds maximum allowed tokens. Output saved to <path>`.
- Pipe the saved path to the relevant parser via `--file <path>`. The shared `_common._maybe_unwrap` helper handles the envelope.
- **`get_sold_summary` is the only tool whose payload is NOT envelope-wrapped** (raw JSON); `parse_sold_summary.py` handles both shapes. See `references/script-contracts.md §parse_sold_summary` for the unwrap branch and error-envelope catalogue.

## Workflow 1 — Single Group Health Check

Triggered by "how is AutoNation doing", "LAD health check", "CarMax volume signal". Pulls current-month + prior-month sold data + active inventory + peer leaderboard for one resolved group, computes MoM deltas + active-health metrics + peer rank, applies the deterministic 6-band signal aggregation, renders an investment-signal report (BULLISH/BEARISH/NEUTRAL/CAUTION/MIXED) with KPI table, inventory health, peer ranking, and 3-sentence earnings preview.

→ Full spec in **`references/w1-single-group.md`**.

## Workflow 2 — Compare Two Groups

Triggered by "compare AutoNation vs Lithia", "AN vs LAD head-to-head". Pairs two dealer groups for a current-month snapshot. No prior-month / MoM (single-month static comparison). Halts before any MCP call if both inputs resolve to the same group. Renders side-by-side KPI table + mix breakdown + 2-sentence relative thesis.

→ Full spec in **`references/w2-compare-two.md`**.

## Workflow 3 — Top-N Leaderboard

Triggered by "top 10 dealer groups by volume", "biggest dealer groups in <month>". Single sold-summary call with `top_n=20`, sliced locally to the user's requested N (1-20). No per-row verdicts (no MoM data). Renders cohort headline + leaderboard table + public-private split.

→ Full spec in **`references/w3-top-n.md`**.

## Output

Each workflow renders via its template in `assets/`. Templates are the **single source of truth** for block structure, table schemas, verdict wording, and self-check items. SKILL.md does not inline block definitions.

Render rules (all workflows):
- Volume: integer with thousands separator (`11,500`).
- ASP: `$` prefix, no decimals, thousands separator (`$24,800`).
- DOM: 1 decimal place + " days" suffix (`38.4 days`).
- Efficiency Score: 1 decimal place.
- MoM: signed percentage with 1 decimal (`+2.4%`, `-3.5%`); for DOM delta use signed days (`-1.5 days`).
- Render `—` (em-dash) when the value is null.

## Data Quality event log

Accumulate a running list across workflows; render in a "Data Quality Notes" section if non-empty:

- **(a)** MCP tool errors recovered from — tool name + error_type + recovery path.
- **(b)** Truncation-envelope unwraps via `--file <path>` — which parser, which tool.
- **(c)** Resolved-group-name fuzzy match (confirmed by user) — log input + canonical + score.
- **(d)** Active-inventory stats absent (syndication response missing `data.stats`) — render `num_found` only.
- **(e)** Days-Supply asymmetry footnote rendered (always render when applicable; the footnote text is in the template).
- **(f)** Workflow branch skipped by design (e.g., Wave B not requested by user).
- **(g)** Group missing from peer leaderboard (target fell below top-20).

Skip the section when the list is empty.

## Self-check

Each workflow's template carries the self-check items. Run silently before returning; emit one of:

- **All checks pass** → one-line footer: `✓ Verified: profile, signal aggregation, peer ranking, days-supply caveat.` (W1) or equivalent per workflow.
- **Any check fails** → emit failures only, prefixed `⚠`, with a one-line note on what was corrected.
- **Never** render a pass-by-pass checkbox grid.

## What this skill does NOT do

- **Inventory build/draw** (no historical-inventory data source available from the MCP surface; AMB-02 from the original skill's analysis was unfixable — dropped).
- **VIN-level pricing or appraisal** (route to `competitive-pricer` or `vehicle-appraiser`).
- **UK / non-US analysis** (`get_sold_summary` is US-only).
- **Composite cross-group rank scoring** across all 8 public groups (route to `group-benchmarking`).
- **Multi-tracked-group portfolio overview** across an analyst's watchlist (route to `group-dashboard`).
- **Stock-price prediction or EPS forecasts.** This skill produces operational signals; converting those to price targets is the analyst's job.
