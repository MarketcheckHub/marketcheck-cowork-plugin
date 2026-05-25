---
name: market-share-analyzer
description: Real-time market-share investment signals for US auto-equity coverage from MarketCheck sold-transaction aggregates. Five US-only workflows — brand share by ticker, segment conquest by body_type, public-dealer-group benchmarking with efficiency, EV/Hybrid penetration with TSLA-vs-legacy breakdown, regional exposure heatmap with state-concentration risk — each producing BULLISH / BEARISH / NEUTRAL / CAUTION for 13 OEM tickers (F, GM, TM, HMC, STLA, TSLA, RIVN, LCID, HYMTF, NSANY, MBGAF, BMWYY, VWAGY) and 8 dealer-group tickers (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA). Use when an equity analyst, OEM analyst, sector strategist, or portfolio manager asks "market share", "who is winning in SUVs", "is [ticker] gaining share", "EV adoption by ticker", "ticker conquest", "top dealer groups by volume", "regional concentration", or any share / conquest / penetration question framed as an investment signal. Prefer oem-stock-tracker for single-OEM rollups, earnings-preview for pre-earnings. US-only.
version: 1.0.0
---

# Market Share Analyzer — Real-Time Share Investment Signals (Updated)

> **Date anchor:** Today's date comes from the `# currentDate` system
> context. Compute ALL relative dates from it via
> `scripts/compute_period_window.py --today <currentDate>`. Never use
> training-data dates.

Equity-analyst-facing skill that converts MarketCheck sold-transaction
aggregates into per-ticker market-share investment signals. Five
workflows map sold-volume trajectories — brand share, segment conquest,
dealer-group benchmarking, EV penetration, regional exposure — to a
deterministic `BULLISH / BEARISH / NEUTRAL / CAUTION` verdict per ticker
(rolled up from per-make findings via the
`references/ticker-mapping.md` 13-OEM + 8-dealer-group table). Every
numeric block — share %, bps deltas, volume change %, efficiency score,
EV mix, state-concentration index, verdict band — is computed by Python
scripts in `scripts/`, never by the model. Same inputs always produce
the same verdict.

The framing is *real-time competitive channel check for OEM tickers and
publicly-traded dealer-group tickers*: aggregated US sold-transaction
share moves give a 60-90 day lead vs traditional syndicated reports.

## Workflows

- **W1 — Brand Market Share** — "market share", "who is gaining share",
  "share change", "OEM ticker share signal". Per-make share + bps
  deltas rolled up to per-ticker BULLISH/BEARISH/NEUTRAL/CAUTION.
- **W2 — Segment Conquest Analysis** — "who is winning in SUVs",
  "segment leader", "ticker conquest in pickups". Body_type-scoped
  per-(make,model) share with ticker-level segment verdict.
- **W3 — Dealer Group Benchmarking** — "top dealer-group tickers by
  volume", "AN vs LAD efficiency", "benchmark KMX vs CVNA". Three-call
  merge (volume / DOM / avg-price) over a 3-month rolling window;
  per-ticker operational verdict (current-period only in v1.0.0).
- **W4 — EV Adoption Tracking** — "EV penetration", "TSLA share loss vs
  absolute volume", "EV transition by ticker". Six calls (EV / Hybrid /
  Total × current / prior) sub-batched into 2 waves of ≤5; per-ticker
  EV-mix verdict.
- **W5 — Regional Exposure Heatmap** — "regional concentration risk",
  "where does [ticker] sell best", "state-exposure scan for [ticker]".
  Per-state distribution for one make / ticker; flags concentration
  risk (top-3 states ≥ 50% national → CAUTION).

## Built-in OEM + dealer-group ticker mapping

The 13-OEM + 8-dealer-group ticker mapping used by every workflow lives
in `references/ticker-mapping.md`. SKILL.md does not re-state the
table.

## Before you start

1. **Profile load (inline, no script).** Read the
   `marketcheck-profile.md` project memory file. Parse YAML frontmatter
   and the JSON body. Frontmatter wins on conflict (it is the curated
   view); the JSON body provides fields the frontmatter omits. Extract:
   - `location.country` — required. If `country != "US"`, halt per
     `references/country-uk.md`. No UK / CA substitute path exists for
     any of the five workflows.
   - `analyst.tracked_tickers` — optional. When present, used to
     highlight the user's cohort in the Ticker Impact Summary block
     with a `★` prefix and surfaced in the Tracked-Ticker Movement
     narrative.
   - `analyst.tracked_makes` — optional. When the user did not name a
     make (W2 / W4 / W5) AND `tracked_makes` is non-empty, default to
     the union of `tracked_makes`.
   - `analyst.tracked_states` — optional. Empty → US national rollup
     (omit `state` on the call). Single value → pass that state.
     Multi-value → prompt the user once for which state to scope to
     (or "all").
   - `analyst.benchmark_period_months` — optional (default 3). Drives
     the W1 / W2 / W4 prior-period offset and window width — see
     `references/w1-brand-share.md §Period invocation patterns`. W3
     uses a fixed 3-month rolling window
     (`compute_sold_summary_dates.py`). W5 defaults to a single-month
     window.
   - `analyst.focus` — optional. Drives `references/outcomes.md`
     scenario routing. `focus=oem` leads the Investment Thesis with
     OEM-ticker exposure; `dealer_groups` leads with retail-stock
     thesis; `ev_transition` leads with W4; `lending` leads with the
     collateral-residual implication; `general` no reorder.

   If the profile is missing or unparseable → prompt the user for the
   minimum inputs per workflow (state, period, inventory_type). No
   halt.

2. **Confirm the profile.** First user-facing line is one of:
   - `Using profile: <user.name or user.company>, <focus>, <state or "US national">`
   - `No profile context — running in <state or US national> anonymous mode.`

3. **Compute date windows.** Run `scripts/compute_period_window.py
   --today <currentDate>` TWICE per workflow (once for current, once
   for prior); cache the returned values. Period invocation per
   workflow follows the table in
   `references/w1-brand-share.md §Period invocation patterns`. W3 runs
   `scripts/compute_sold_summary_dates.py --today <currentDate>` ONCE
   (fixed 3-month rolling). **Never hand-compute dates.** Mis-aligned
   dates pass local validation and return HTTP 422 from upstream.

4. **Resolve inventory_type.** Each workflow has a default channel —
   the analyst profile has no `default_inventory_type` field, so
   SKILL.md sets it per workflow:
   - **W1 / W2 / W5** → `inventory_type="Used"` (used-vehicle volume
     is a deeper read on consumer demand-side strength).
   - **W3** → primary pass `inventory_type="Used"` (covers all 8
     dealer-group tickers including KMX / CVNA used-only); optional
     `New` pass for the 6 franchise dealer-group tickers (AN / LAD /
     PAG / SAH / GPI / ABG). See
     `references/w3-dealer-group-benchmarking.md §Used vs New routing`.
   - **W4** → `inventory_type="New"` (EV adoption is a new-vehicle
     transition phenomenon).
   User can override with explicit "show me new sales" / "show me used"
   in the question.

5. **Generate the session run-id.** Inline:
   `run_id = f"msa-{int(time.time())}-{secrets.token_hex(4)}"`. All
   intermediate files go under `/tmp/marketcheck/<run_id>/`. The
   directory is created lazily; the agent uses `Write` to drop raw MCP
   responses there and `persist_response.py` to copy from arbitrary
   paths into it.

## Script invocation discipline

Scripts in `scripts/` are black boxes. Their complete I/O contract —
CLI flags, stdin shape, stdout shape, error envelopes, edge cases —
lives in `references/script-contracts.md`. Treat that file as
authoritative; the script source is implementation detail and never
needs to enter your context.

The 12 scripts: `_common.py`, `parse_sold_summary.py`,
`compute_period_window.py`, `compute_sold_summary_dates.py`,
`compute_brand_share.py`, `compute_segment_conquest.py`,
`compute_dealer_group_leaderboard.py`, `compute_ev_penetration.py`,
`compute_regional_heatmap.py`, `aggregate_signals.py`,
`render_share_table.py`, `persist_response.py`.

**Forbidden:**
- `Read` tool on any `scripts/*.py` file.
- `cat` / `head` / `tail` / `sed` / `awk` / `grep` on script source via
  Bash.
- Re-implementing script logic inline (no model-side share %, no
  inline bps math, no inline verdict classification, no hand-rolled
  efficiency_score, no hand-aggregated state weights). If the
  contract is missing a field, surface it as a doc bug — do not patch
  with hand-rolled code.

**Why:** Each unread script saves ~100-500 lines of context. Reading
source tempts inline reimplementation, which silently diverges from the
script's real behavior and breaks the "same inputs always produce the
same verdict" guarantee that anchors this skill's value to equity
analysts.

**Right pattern (Write → file → `--file`):**
```
# Step 1: agent writes the raw MCP response to the run directory
Write(file_path="/tmp/marketcheck/<run_id>/w1_current.json",
      content="<full response verbatim>")

# Step 2: parse via --file
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w1_current.json
```

**Wrong patterns:**
```
Read(scripts/parse_sold_summary.py)              # forbidden — see contracts file
# Inline: "let me compute share% in NL"            # forbidden — bypass guarantee
# Discarding the MCP response after "extract only" # forbidden — truncation breaks this
```

The `--file <path>` flag on the parsers is the **primary** path for
this skill because `get_sold_summary` responses are typically too large
to safely heredoc through stdin and the runtime saves them to a path
the agent reads back. See `references/truncation-recovery.md`.

## Tool surface

This skill calls **one** MCP tool primarily:

- **`get_sold_summary`** — US-only sold-vehicle aggregates. Every
  workflow uses it. See `references/sold-summary-safety.md` for full
  parameter discipline.

And one tool **for recovery only**:

- **`search_active_cars`** — used ONLY for facet-discovery retry on
  `error_type=make_model_not_found`. See
  `references/facet-discovery.md`.

Tools deliberately not used:

- `decode_vin_neovin`, `predict_price_with_comparables`,
  `get_car_history`, `search_past_90_days`, `search_uk_*` — not used.

## Parallelization (universal contract)

Every workflow follows the wave-execution contract:

- **A wave is a batch of MCP calls fired in a single agent message**
  (multiple `tool_use` blocks). The runtime dispatches them
  concurrently.
- **Within a wave, calls share no cross-dependency** on each other's
  parsed output. Calls that need another call's output go in a later
  wave.
- **Wait for the entire wave** before issuing the next.
- **Never serialize calls within a wave** — a wave's wall clock is set
  by its slowest call.

**Upstream rate-limit ceiling: ≤5 concurrent `get_sold_summary` calls
per agent message.** The API at `api.marketcheck.com` returns HTTP 429
above that (see `references/sold-summary-safety.md §Upstream rate
limit`). Workflows that need more than 5 calls split into sequential
sub-batches of ≤5; within a sub-batch, calls fire in parallel.

Wall-clock budget at a glance:
- W1: Wave A ≈ 12s (2 parallel sold-summary calls).
- W2: Wave A ≈ 12s (2 parallel calls; multi-segment fan-out
  sub-batches into 2+ waves of ≤5).
- W3: Wave A ≈ 12-15s (3 parallel calls per inventory-type pass;
  Used + New optional split into Wave A + Wave B).
- W4: Wave A + Wave B ≈ 24-30s (6 total calls split 4+2 to respect the
  ≤5 ceiling).
- W5: Wave A ≈ 12s (1 call for single-make; up to 4 parallel calls
  for multi-make ticker fan-out).

Per-workflow wave structure lives in the per-workflow reference files.

## Truncation handling

Most calls in this skill DO truncate in practice — `get_sold_summary`
responses can be 50KB-200KB once `top_n=15-50` is set across multi-
month rollups. The recovery is the Write→file→`--file` recipe shown in
§Script invocation discipline:

- The MCP layer emits `Error: result (N chars) exceeds maximum allowed
  tokens. Output saved to <path>` for any response that exceeds the
  token budget.
- Pipe the saved path to `parse_sold_summary.py --file <path>`. The
  shared `_common._maybe_unwrap` helper handles the envelope.
- **`get_sold_summary` is the only MCP tool whose payload is NOT
  envelope-wrapped** (raw `{success, service, data}`);
  `parse_sold_summary.py` handles both shapes. See
  `references/script-contracts.md §parse_sold_summary` for the unwrap
  branch.
- Log DQ event (b) when a truncation envelope was unwrapped.

Per `references/truncation-recovery.md`: do NOT `cat` the saved file
into context, do NOT retry the original call without tightening
filters, do NOT assume the envelope's inner JSON is directly parseable.

## Sold-summary safety

Hard-won rules — full detail in `references/sold-summary-safety.md`.
Non-negotiables on every `get_sold_summary` call:

- Always set `inventory_type` (`Used` / `New`) explicitly. Omitting
  silently defaults to `"New"` upstream.
- Always set `limit=5000`. Default `1000` silently truncates multi-
  dimensional results.
- Always set minimal `ranking_dimensions` per workflow (W1=`make`,
  W2=`make,model`, W3=`dealership_group_name`, W4 per-fuel=`make,model`,
  W4 total=`make`, W5=`make,model`). Never default 3-dim
  `make,model,body_type`.
- Always set `summary_by="state"` explicitly, even when it's the
  default.
- **Never** pass `dealer_type` — combined with narrow filters, it
  silently suppresses valid data (verified live in dealer-side testing,
  see `references/sold-summary-safety.md`).
- Always month-align `date_from` / `date_to` via
  `compute_period_window.py` (or `compute_sold_summary_dates.py` for
  W3).
- Sub-batch any wave that would exceed 5 concurrent calls (HTTP 429
  ceiling).
- Branch on `parse_sold_summary.error_type` per the recovery table
  (`references/script-contracts.md §error_type enum`).

## Facet discipline

`get_sold_summary` does not expose a `facets` parameter. When a call
returns `error_type="make_model_not_found"`, recover via
`search_active_cars` facet discovery per
`references/facet-discovery.md`, then re-issue the failed call with
the resolved casing. Cache the resolved tuple — every period's call in
the same workflow uses the cached value.

`year` and `trim` are NOT parameters on `get_sold_summary` — they are
NOT facet-discoverable. The skill aggregates across all years and
trims; the output template renders an explicit scope qualifier.

## Data quality event log

Accumulate a running list of events across the workflow; render in a
"Data Quality Notes" section if non-empty:

- **(a)** MCP tool errors / non-200 responses recovered from — tool
  name, `error_type`, recovery path. Specifically for
  `parse_sold_summary` failures: `make_model_not_found`,
  `validation_dimension_limit`, `network_422`, `network_5xx`,
  `validation`, `unknown`.
- **(a1)** Facet-discovery retries — when a `get_sold_summary` call
  errored `make_model_not_found` and a `search_active_cars` facet
  lookup resolved the correct casing.
- **(b)** Truncation envelope unwraps via `--file <path>` — which
  parser, which tool.
- **(c)** Make / model resolution by fuzzy match (user-confirmed) — log
  input + canonical + match path.
- **(d)** Ticker mapping miss — a make surfaced by the data has no
  entry in `references/ticker-mapping.md` and is rendered as
  `[no tracked ticker]`.
- **(e)** Fallback source attribution — e.g., long-tail top-50 cap
  excluded ~2-5% of national volume; per-state response capped at
  top_n=50 for W5.
- **(f)** Parameter adaptations — e.g., `ranking_dimensions=make`
  passed after a `validation_dimension_limit` retry.
- **(g)** Workflow branch skipped by design — examples:
  - "Quarterly aggregation skipped: user supplied a single-month
    period."
  - "Dual-period heatmap skipped: --prior not supplied."
  - "W3 New pass skipped: user requested Used only."
  - "Tracked-ticker callouts skipped: profile has no
    `analyst.tracked_tickers`."

If the list is empty, omit the section entirely.

## Data quality rule

Treat every period's failure as recoverable, not fatal. A failed
`get_sold_summary` call on one period of a multi-call workflow omits
that period from the table — it does not halt the workflow. Surface
every degradation in the Data Quality Notes section.

---

## Workflow 1 — Brand Market Share

Per-make share + bps deltas rolled up to per-ticker BULLISH / BEARISH
/ NEUTRAL / CAUTION. Two parallel `get_sold_summary` calls (current +
prior period) in a single wave.

→ Full spec in **`references/w1-brand-share.md`**.

---

## Workflow 2 — Segment Conquest Analysis

Body_type-scoped per-(make,model) share with ticker-level segment
verdict. Two parallel calls per segment (multi-segment fan-out
sub-batches into 2+ waves of ≤5).

→ Full spec in **`references/w2-segment-conquest.md`**.

---

## Workflow 3 — Dealer Group Benchmarking

Three-call merge (volume / DOM / avg-price) over a 3-month rolling
window, mapped to the 8 public-dealer-group tickers (AN / LAD / PAG /
SAH / GPI / ABG / KMX / CVNA). Current-period only in v1.0.0; operational
signal lives in the volume vs efficiency contrast, not in directional
verdict bands.

→ Full spec in **`references/w3-dealer-group-benchmarking.md`**.

---

## Workflow 4 — EV Adoption Tracking

Six `get_sold_summary` calls (EV / Hybrid / Total × current / prior)
sub-batched into 2 waves of ≤5. Outputs penetration percentages,
period-over-period bps shifts, top EV / Hybrid models, and the TSLA-vs-
legacy ticker breakdown.

→ Full spec in **`references/w4-ev-penetration.md`**.

---

## Workflow 5 — Regional Exposure Heatmap

Per-state distribution for one make / ticker; flags concentration risk
(top-3 states ≥ 50% national → CAUTION). Single-make: 1 call. Multi-
make ticker (e.g. GM): up to 4 parallel calls (≤5 ceiling).

→ Full spec in **`references/w5-regional-heatmap.md`**.

---

## Output

Every workflow renders via **`assets/output-template.md`**. That file
is the single source of truth for block structure, table schemas,
headline phrasing per workflow, Ticker Impact Summary block,
tracked-ticker movement narrative, Investment Thesis routing per
`focus`, and the self-check.

Render rules:

- **Main table** rendered via `render_share_table.py --mode <m>` (6
  modes: `brand-share` / `segment-conquest` /
  `dealer-group-leaderboard` / `ev-penetration` / `ev-brand-share` /
  `regional-heatmap`). Never hand-roll the table.
- **Headline** is one sentence per the per-workflow phrasing in the
  template. Lead with the top ticker's verdict + bps shift.
- **Ticker Impact Summary** required on every workflow — translates
  per-make / per-segment / per-dealer-group findings into per-ticker
  BULLISH / BEARISH / NEUTRAL / CAUTION via `aggregate_signals.py`.
  Full verdict-band grid in `references/signal-aggregation.md`.
- **Tracked-ticker movement narrative** required when
  `analyst.tracked_tickers` is set — the user's cohort gets a `★`
  prefix in the Ticker Impact Summary table and a one-line callout per
  tracked ticker.
- **Investment Thesis** persona-tailored per `analyst.focus` (routing
  table in `assets/output-template.md` and `references/outcomes.md`).

## Self-check

The verification checklist lives in `assets/output-template.md`. It is
an **internal guardrail** — the model runs each silently before
returning and does NOT render the full grid.

- **All applicable checks pass** → emit a single footer line listing
  5-7 items, e.g.:
  `✓ Verified: profile, US-only routing, sold-summary safety (limit=5000, inventory_type set), month-aligned dates, ticker rollup, verdict band consistent.`
- **Any check fails** → emit failures only, one per line, prefixed
  `⚠`, with a one-line note on what was corrected or caveated to
  compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox
  grid.

## What this skill does NOT do

- **Single-OEM operational rollup with volume + ASP + DOM +
  days-supply for one ticker.** Route to `oem-stock-tracker`.
- **Single dealer-group operational health check (AN, LAD, KMX, ...).**
  Route to `dealer-group-health-monitor`.
- **Pre-earnings channel check on an OEM or dealer-group ticker.**
  Route to `earnings-preview`.
- **EV-cohort deep dive (EV-cohort residuals, EV days-supply, EV-only
  DOM).** Route to `ev-transition-monitor`.
- **Cross-group ranking without per-ticker verdicts.** Route to
  `group-benchmarking`.
- **Quintile-based dealer-group cohort scorecard vs full 400+-group
  industry cohort.** Route to `public-group-scorecard`.
- **Multi-tracked-portfolio dashboard view.** Route to
  `group-dashboard`.
- **Depreciation rate, residual value, MSRP parity tracking.** Route to
  `depreciation-tracker`.
- **Sector-level monthly momentum reporting.** Route to
  `market-momentum-report` or `market-trends-reporter`.
- **Pricing-power / margin / DOM signals per ticker.** Route to
  `pricing-power-tracker`, `dom-monitor`, or `sourcing-quality-signal`.
- **UK / CA / non-US analysis.** `get_sold_summary` is US-only — see
  `references/country-uk.md` for the halt path.
- **Stock-price prediction or EPS forecasts.** This skill produces
  operational signals; converting those to price targets / EPS is the
  analyst's job.
