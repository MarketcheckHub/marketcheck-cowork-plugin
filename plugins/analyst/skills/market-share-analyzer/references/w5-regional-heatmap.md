---
name: w5-regional-heatmap
description: W5 — Regional Exposure Heatmap. Single `get_sold_summary` call (or two for dual-period) for one make / model with `summary_by="state"` and no state filter; flags state-concentration risk for the ticker (top-3 states ≥ 50% national volume → CAUTION).
type: reference
---

# W5 — Regional Exposure Heatmap (State-Concentration Risk)

For "where does Toyota sell best", "F-150 demand by state", "regional
macro overlay for GM", "ticker state-exposure scan". Single
`get_sold_summary` call (or two, if dual-period delta requested) for one
make / model with `summary_by="state"` and no state filter — the response
carries one row per state.

The analyst framing: state-concentration risk is an investment signal —
an OEM with > 50% of its national volume concentrated in its top-3
states is exposed to state-specific demand shocks (CAUTION). A
diversified geographic footprint (< 50% top-3) is NEUTRAL. The skill
does not opine on overall directional thesis here — that's W1 / W2.

**US-only** — halt non-US profiles per `references/country-uk.md`.

**Default `inventory_type = Used`** — used-vehicle distribution is a
deeper read on consumer demand-side concentration than the new-vehicle
allocation flow.

## Required inputs

- **Make**: required. The skill cannot render a heatmap without a make
  filter (the response would be too large and the per-state ratios
  meaningless).
- **Model**: optional. When supplied, the heatmap shows per-state demand
  for that specific model; when omitted, it's brand-level (across all
  models for the make).
- **Period**: same period invocation pattern as W1 (default
  `compute_period_window.py --months-back 1 --num-months 1`).
- **Inventory type**: default `Used`.
- **Optional `--prior <prior-period-parsed>`**: when the user wants
  dual-period delta data (out of scope for the default rendering — see
  "Dual-period variant" below).

## Pre-check halts

Same as W1, plus:

| Trigger | Halt message |
|---|---|
| Make missing | "Which make / ticker? Regional Exposure Heatmap requires a make filter (e.g. Ford, Toyota, Tesla). Pass the make directly OR a ticker (one of F / GM / TM / HMC / STLA / TSLA / RIVN / LCID / HYMTF / NSANY / MBGAF / BMWYY / VWAGY) which the skill resolves to its constituent makes." |

When the user supplies a ticker (e.g. `--ticker GM`), the skill expands
it to the constituent makes (Chevrolet, GMC, Buick, Cadillac) and
issues one heatmap call per make, then aggregates state-level volume
across the 4 makes for the consolidated ticker heatmap. (For a single-
make ticker like TSLA, this is one call.) Multi-make ticker fan-out
respects the ≤5-concurrent ceiling.

## Wave A — 1 (or up to 4) `get_sold_summary` calls

```
get_sold_summary (current period, per make in the ticker):
  date_from / date_to / inventory_type
  make=<MAKE>                                   # required (user input or facet-discovery)
  [model=<MODEL>]                               # optional
  ranking_dimensions="make,model"               # so per-state response carries make+model context
  ranking_measure="sold_count"
  ranking_order="desc"
  top_n=50                                      # per-state cap; rarely a binding limit since per-state volume is concentrated
  summary_by="state"                            # the W5 keystone — buckets per state
  limit=5000
  # NO state filter — we want all states in the response
  # NO dealer_type
```

When dual-period delta is requested ("how did F-150 state distribution
shift from Q4 2025 to Q1 2026"), fire a second call with the prior period
in the same wave. `compute_regional_heatmap.py` accepts an optional
`--prior` flag but doesn't currently surface dual-period output; default
to single-period rendering.

### Wall-clock budget

~12s for a single-make wave (1 call). Multi-make ticker fan-out:
~12-15s for up to 4 parallel calls (≤5 ceiling).

## Pipeline

```
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w5_<make>.json > <make>_parsed.json
# repeat per make in the ticker

compute_regional_heatmap.py \\
  --current <make1>_parsed.json \\
  --make <MAKE> \\
  [--model <MODEL>] \\
  [--top-n 10]
> heatmap.json
# When multi-make ticker: agent concatenates the parsed rows[] across makes
# into a single combined parsed file before piping to compute_regional_heatmap.

aggregate_signals.py \\
  --mode regional \\
  --input heatmap.json \\
  [--tracked-tickers <profile.analyst.tracked_tickers>] \\
  [--focus <profile.analyst.focus>]
> regional_tickers.json

render_share_table.py --mode regional-heatmap --data heatmap.json
> heatmap_table.md
```

The compute script:
- **Filters by make (and optionally model)** at the row level — the
  parsed response may include multiple makes if `ranking_dimensions=
  "make,model"` returned a top-N rollup that crossed makes. The script's
  `--make` filter is the authoritative scope.
- **Aggregates per state**: sum sold_count, weighted-mean
  avg_sale_price (weight = sold_count), weighted-mean avg_dom (same
  weight).
- **Computes ratios**: `pct_of_national_volume = state_volume /
  national_volume × 100`; `price_vs_national_ratio = state_avg_price /
  national_avg_price`.
- **Ranks states** by sold_count descending.
- **Surfaces top picks**: `top_volume_states` (top-N state names) and
  `bottom_growth_markets` (bottom-N state names — interpreted as
  "under-penetrated potential growth markets").

`aggregate_signals.py --mode regional` translates this into:
- **Concentration index** = sum of top-3 states' `pct_of_national_volume`.
- **Verdict** = `CAUTION` when concentration ≥ 50%, `NEUTRAL` otherwise.
- Single-ticker output (the make's ticker is the only one in scope).

## Output rendering

1. **Headline**:
   > *"For <ticker> (<make> <model>), <top_state> leads with
   > <top_share>% of national volume at $<avg_price> (<ratio>× national
   > average). Top-3 states account for <top3_pct>% — <verdict>
   > concentration risk for the <ticker> regional thesis."*

2. **Heatmap table** (per-state, via `render_share_table.py --mode
   regional-heatmap`):
   ```
   Rank | State | Sold Count | % of National | Avg Sale Price | Price vs National | Avg DOM
   ```

3. **Ticker Impact Summary block** (single-row, single ticker):
   ```
   Ticker | Concentration (top-3) | Top State | Volume Share % | Verdict | Reason
   ```

4. **Top markets paragraph + bottom growth markets list**:
   ```
   Top <top_n> markets by volume: <top_volume_states>.
   Bottom <top_n> markets (potential growth): <bottom_growth_markets>.
   ```

   When the user supplies `--model`, prepend "For <ticker> (<make>
   <model>), ..."; otherwise "For <ticker> (<make>), ...".

5. **Investment Thesis** — sourced from `references/outcomes.md` Scenario
   4 (Sector Strategist). When `focus=oem`, lead with the state-
   concentration line for the ticker's regional-macro overlay.

6. **Source line**.

## `--make` casing discipline

When the user types a make like "honda" (lowercase) or a ticker (e.g.
"GM"), the skill resolves:

- **Ticker → makes**: GM → Chevrolet, GMC, Buick, Cadillac (per
  `references/ticker-mapping.md`).
- **Make casing**: if the resolved make's casing doesn't match
  `get_sold_summary`'s indexed values, the call returns `num_found == 0`
  with `make_model_not_found`. Run facet-discovery once per
  `references/facet-discovery.md` — discover via
  `search_active_cars facets="make|0|100"` and re-issue with the resolved
  casing. Cache the resolved casing for the session.

## Failure recovery

| Case | Trigger | Behavior |
|---|---|---|
| `parse_sold_summary` `error_type=make_model_not_found` | Make casing mismatch | Retry once with facet-discovered casing. If still failing, halt with "Make `<make>` not recognized in `get_sold_summary`'s indexed values. Try a different spelling." |
| `compute_regional_heatmap` `error_type=no_data_for_make` | Empty rows after make filter | Halt with "No sold-summary data for `<make>` (`<model>` if model set) in `<period>`. Check make casing; widen the date window." |
| `parse_sold_summary` `error_type=network_5xx` | Upstream error | Halt with "Upstream data unavailable; retry in a few minutes." |
| Single-state response (e.g. only TX present) | Geographic concentration | Render normally; the `pct_of_national_volume` for the only state is 100%. No halt. Surface as Verdict=CAUTION with reason "single_state_concentration" and a Key Signal line: *"Sales for `<ticker>` are concentrated in <state> for the period — state-specific demand shocks are a meaningful catalyst."* |
| `top_n=50` per-state limit binding | Per-state response capped | Rare; the script uses sold_count from the rows that came back. Emit DQ event (e) noting *"Per-state response capped at top_n=50; rare states with > 50 model rows may be under-counted."* |
| Multi-make ticker, one make fails | One of (e.g.) 4 GM-bucket calls returned empty / errored | Render the ticker heatmap with the available makes; emit DQ event (a) for the missing make. Do NOT halt the workflow. |
