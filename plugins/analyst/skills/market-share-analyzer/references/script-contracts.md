---
name: script-contracts
description: Authoritative I/O contract (CLI flags, stdin shape, stdout shape, error envelopes, edge cases) for every Python script in scripts/. The script source is implementation detail; this file is the contract surface — SKILL.md §Script invocation discipline forbids the `Read` tool on `scripts/*.py`.
type: reference
---

# Script contracts

Authoritative I/O contract for every script in `scripts/`. The script
source is implementation detail and never needs to enter your context —
SKILL.md §Script invocation discipline forbids the `Read` tool on
`scripts/*.py`. Treat this file as the contract surface.

If a future test in `tests/` disagrees with what is documented here, the
test wins — file a doc bug and update this file. Never read source to
"verify" — that is the failure mode this file exists to prevent.

## Quick reference

| Script | Purpose | CLI flags | Used by |
|---|---|---|---|
| `_common.py` | Shared helpers (`read_input`, `emit`, `classify_error`, `arg_value`, `arg_flag`) | (not directly invoked) | every parser |
| `parse_sold_summary.py` | Normalise `get_sold_summary` responses (with optional aggregation modes) | `--file <path>`, `--aggregate-state <STATE>` | every workflow |
| `compute_period_window.py` | Emit a single month-aligned date window for a workflow's current OR prior period | `--today YYYY-MM-DD`, `--months-back N`, `--num-months M` | W1 / W2 / W4 / W5 pre-flight |
| `compute_sold_summary_dates.py` | Emit the canonical "last 3 full calendar months" window | `--today YYYY-MM-DD` | W3 pre-flight |
| `compute_brand_share.py` | W1 brand-share engine | `--current <path>`, `--prior <path>`, `--top-n N`, `--user-brand <make>` *(unused from analyst SKILL.md)*, `--state <STATE>` | W1 |
| `compute_segment_conquest.py` | W2 segment-conquest engine | `--current <path>`, `--prior <path>`, `--body-type <segment>`, `--top-n N`, `--user-brand <make>`, `--state <STATE>` | W2 |
| `compute_dealer_group_leaderboard.py` | W3 dealer-group leaderboard merge | `--volume <path>`, `--dom <path>`, `--avg-price <path>`, `--user-make <make>`, `--top-n N` | W3 |
| `compute_ev_penetration.py` | W4 EV-adoption engine | `--ev-current <path>`, `--ev-prior <path>`, `--hybrid-current <path>`, `--hybrid-prior <path>`, `--total-current <path>`, `--total-prior <path>`, `--top-n N`, `--state <STATE>` | W4 |
| `compute_regional_heatmap.py` | W5 regional-exposure heatmap | `--current <path>`, `--make <Make>`, `--model <Model>`, `--prior <path>`, `--top-n N` | W5 |
| `aggregate_signals.py` | Map per-make / per-segment / per-dealer-group findings → per-ticker BULLISH / BEARISH / NEUTRAL / CAUTION | `--mode {brand,segment,dealer-group,ev,regional}`, `--input <path>`, `--tracked-tickers <csv>`, `--focus <oem,dealer_groups,ev_transition,lending,general>` | every workflow's Ticker Impact Summary |
| `render_share_table.py` | Markdown table renderer (6 modes) | `--mode {brand-share,segment-conquest,dealer-group-leaderboard,ev-penetration,ev-brand-share,regional-heatmap}`, `--data <path>`, `--currency '$\|£'` *(`£` unreachable — US-only)* | every workflow |
| `persist_response.py` | Persist a raw MCP response to `/tmp/marketcheck/<run-id>/<name>.json` for `--file` piping | `--name <label>`, `--content-file <path>`, `--run-id <id>`, *(stdin alternative)* | every workflow's persistence step |

## Conventions (all parsers)

- **Stdin-default.** Every parser reads its payload from stdin by default.
  Use the `--file <path>` flag ONLY when the MCP runtime saved an
  oversized response to disk and returned an `Output saved to <path>`
  error string. See SKILL.md §Script invocation discipline.
- **Truncation envelope.** When loaded via `--file`, the parser unwraps
  the `{"result": "<stringified JSON>"}` envelope automatically (via
  `_common._maybe_unwrap`). `get_sold_summary` is the only MCP tool whose
  payload is NOT envelope-wrapped — its raw `{success, service, data}`
  passes through transparently.
- **Canonical response shape.** Every parser / compute / aggregate
  script emits a single JSON document with `ok: true|false` at top level.
  On `ok: false`, an `error_type` enum classifies the failure; the
  caller branches on it.
- **Process exit codes.** Validation errors (bad CLI args, missing
  required input) exit `1` with stderr message and no JSON. Payload-level
  errors (network failures, schema misses, classifier hits) exit `0` with
  `{"ok": false, "error_type": "...", ...}` on stdout — the caller is
  expected to parse and branch.
- **Field naming.** Server-side quirks (`avg_msrp`,
  `sale_price_std_dev`) are normalised at parse time. The contract here
  is the **post-normalisation** name (`average_msrp`, etc.).
- **Scratch directory.** All file paths are scoped under
  `/tmp/marketcheck/<run-id>/`. The `<run-id>` is generated inline by
  the SKILL.md (not by a script, since the analyst port loads the
  profile inline). Recommended pattern: `msa-<unix-epoch>-<8-hex>`.

## Per-script details

### `parse_sold_summary.py`

**Input** — stdin OR `--file <path>` containing the raw response from
`get_sold_summary` (either inline string OR truncation-envelope payload).

**Output (success)**:
```json
{
  "ok": true,
  "row_count": <int>,
  "rows": [<normalised row>, ...],
  "source": "stdin" | "file:<path>"
}
```

With `--aggregate-state <STATE>`:
```json
{
  ...,
  "state_baseline": {<weighted-mean baseline>} | null,
  "state_baseline_skipped_reason": "no_matching_rows" | "all_zero" | null
}
```

**Output (error)**: `{"ok": false, "error_type": "<enum>", "error": "<msg>", "source": "..."}`

**error_type enum** (branch on these):
- `make_model_not_found` — facet-discover and retry once
- `validation_dimension_limit` — drop `ranking_dimensions` to `make` and retry
- `validation` — skip line + DQ event
- `network_422` — verify date alignment, retry once
- `network_5xx` — halt with retry hint
- `truncation_unrecovered` — `--file` recovery failed (rare)
- `truncation_unwrap_failed` — envelope present but inner unparseable
- `unknown` / `empty_response` / `non_json` — log + skip

**Normalised row fields**: `month`, `inventory_type`, `state`, `city`,
`dealership_group_name`, `make`, `model`, `body_type`, `rank`,
`sold_count`, `average_sale_price`, `total_sale_price`, `average_msrp`,
`price_over_msrp_percentage`, `average_days_on_market`,
`median_days_on_market`, `sale_price_range`, `sale_price_std_dev`.

### `compute_period_window.py`

**Input** — argv only.

**Flags**:
- `--today YYYY-MM-DD` (optional; default = system date — the skill MUST
  pass `--today <currentDate>` from the system context, never rely on
  the system clock inside the model's environment)
- `--months-back N` (required; ≥ 1)
- `--num-months M` (required; ≥ 1)

**Semantics**:
- `date_to = last day of (current_month − N)`
- `date_from = first day of (current_month − N − M + 1)`
- For W1/W2/W4 single-month current: `--months-back 1 --num-months 1`.
- For W1/W2/W4 single-month prior (MoM): `--months-back 2 --num-months 1`.
- For quarterly current (when `benchmark_period_months = 3`):
  `--months-back 1 --num-months 3`.
- For quarterly prior (when `benchmark_period_months = 3`):
  `--months-back 4 --num-months 3`.

**Output**:
```json
{
  "date_from": "YYYY-MM-DD",
  "date_to":   "YYYY-MM-DD",
  "label":     "<human label>",
  "months_included": ["YYYY-MM", ...],
  "today":     "YYYY-MM-DD",
  "months_back": <int>,
  "num_months":  <int>
}
```

### `compute_sold_summary_dates.py`

**Input** — argv only.

**Flags**:
- `--today YYYY-MM-DD` (optional; default = system date — same caveat as
  `compute_period_window.py`)

**Output**: hardcoded to "last 3 full calendar months" window — never
includes the current in-progress month. Used by W3 for the dealer-group
leaderboard's denser 3-month rolling window.

### `compute_brand_share.py`

**Input flags**: `--current <parse_sold_summary path>` (required),
`--prior <parse_sold_summary path>` (required), `--top-n N` (default 20),
`--user-brand <make>` (unused from analyst SKILL.md flow — analyst has
no franchise_brand field), `--state <STATE>` (post-aggregation state
filter).

**Output keys**: `ok`, `scope`, `totals`, `makes[]` (per-make rows with
share %, bps, volume change, trend), `summary` (top_3_gainers,
top_3_losers, user_brand_movement).

**error_type enum**: `no_current_data`.

### `compute_segment_conquest.py`

**Input flags**: `--current` (required), `--prior` (required),
`--body-type` (required; e.g. "SUV"), `--user-brand`, `--top-n`,
`--state`.

**Output keys**: `ok`, `scope`, `totals`, `leader`, `user_brand_rank`,
`user_brand_share_pct`, `gap_to_leader_units`, `gap_to_leader_share_pts`,
`fastest_gainer`, `models[]`.

### `compute_dealer_group_leaderboard.py`

**Input flags**: `--volume` (required; `ranking_measure=sold_count`),
`--dom` (required; `ranking_measure=average_days_on_market`),
`--avg-price` (required; `ranking_measure=average_sale_price`),
`--user-make`, `--top-n`.

**Output keys**: `ok`, `scope`, `totals`, `leaderboard[]` (each row:
rank_by_volume, dealership_group_name, sold_count, market_share_pct,
avg_dom, avg_sale_price, efficiency_score), `top_volume`,
`top_efficiency`, `top_avg_price`.

**efficiency_score** = `sold_count / avg_dom`; null when `avg_dom <= 0`.

### `compute_ev_penetration.py`

**Input flags**: `--ev-current` (required), `--ev-prior` (required),
`--hybrid-current` (required), `--hybrid-prior` (required),
`--total-current` (required; no `fuel_type_category` on the source call),
`--total-prior` (required), `--top-n`, `--state`.

**Output keys**: `ok`, `scope`, `current_period`, `prior_period`,
`deltas` (ev_pct_change_bps, hybrid_pct_change_bps, combined_pct_change_bps,
ev_volume_change_pct, hybrid_volume_change_pct), `top_ev_models[]`,
`top_hybrid_models[]`, `ev_brand_share[]`.

### `compute_regional_heatmap.py`

**Input flags**: `--current` (required), `--make` (required), `--model`,
`--prior`, `--top-n` (default 10).

**Output keys**: `ok`, `scope`, `national`, `states[]` (rank, state,
sold_count, pct_of_national_volume, avg_sale_price, avg_dom,
price_vs_national_ratio), `top_volume_states`, `bottom_growth_markets`.

### `aggregate_signals.py`

**Input flags**:
- `--mode {brand,segment,dealer-group,ev,regional}` (required)
- `--input <compute_*.py output path>` (required)
- `--tracked-tickers <csv>` (optional; from `profile.analyst.tracked_tickers`)
- `--focus <oem|dealer_groups|ev_transition|lending|general>` (optional;
  from `profile.analyst.focus`)

**Output keys**: `ok`, `mode`, `scope`, `tickers[]` (per-ticker rows
with `ticker`, `audience_class`, `makes_contributing`,
`current_sold_count`, `current_share_pct`, `prior_share_pct`,
`share_change_bps`, `volume_change_pct`, `verdict`, `verdict_reason`,
`is_tracked`, `per_make_breakdown[]`), `headline_rollup`
(`top_bullish[]`, `top_bearish[]`, `tracked_signals[]`).

**Verdict bands** — full grid: `references/signal-aggregation.md`.

### `render_share_table.py`

**Input flags**:
- `--mode {brand-share, segment-conquest, dealer-group-leaderboard, ev-penetration, ev-brand-share, regional-heatmap}` (required)
- `--data <compute_*.py output path>` (required)
- `--currency '$|£'` (default `$`; `£` is unreachable in this skill —
  analyst plugin is US-only)

**Output**: markdown table on stdout. The agent copies stdout verbatim
into the final report. When input has `ok=false`, emits a single caveat
line `*(no data: <reason>)*` and exits 0.

### `persist_response.py`

**Input flags**:
- `--name <label>` (required; filename stem)
- `--content-file <path>` (optional; reads from file instead of stdin)
- `--run-id <id>` (required from this skill's flow; the legacy
  `cpr-run` default is concurrent-unsafe)

**Output**: echoes the persisted path on stdout (e.g.
`/tmp/marketcheck/<run-id>/<name>.json`). The caller pipes that path to
`parse_sold_summary.py --file <path>`.

## Overlap rule — where each kind of doc lives

- **What params to set on a MCP call** → tool-doc layer
  (`mcp_server_tool_docs/<tool>.md`) for the server's accepted enum /
  default / silent-failure surface; this skill's
  `references/sold-summary-safety.md` for the workflow-specific always-set
  / never-set rules.
- **What a script accepts on stdin / argv and emits on stdout** → this
  file.
- **What a workflow does end-to-end** → `references/w<N>-*.md`.
- **How the model phrases the output** → `assets/output-template.md`.
- **How verdict bands are computed** → `references/signal-aggregation.md`.
- **Which scenarios drive Investment Thesis phrasing** →
  `references/outcomes.md`.
- **How the model handles truncation / facet-discovery / country
  routing** → the three reference docs of those names.

If you find yourself wanting to add a fact to two of those layers, the
fact lives in the lowest layer that fits — only `SKILL.md` may
"announce" facts that are detailed elsewhere.
