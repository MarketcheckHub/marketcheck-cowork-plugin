# W5 — Regional Demand Heatmap

For "where does Toyota sell best," "F-150 demand by state," "regional demand patterns." Single `get_sold_summary` call (or two, if dual-period heatmap requested) for one make / model with `summary_by="state"` and no state filter — the response carries one row per state.

**US-only** — halt UK profiles.

## Required inputs

- **Make**: required. The skill cannot render a heatmap without a make filter (the response would be too large and the per-state ratios meaningless).
- **Model**: optional. When supplied, the heatmap shows per-state demand for that specific model; when omitted, it's brand-level (across all models for the make).
- **Period**: same monthly default as W1.
- **Inventory type**: same as W1.
- **Optional `--prior <prior-period-parsed>`**: when the user wants dual-period delta data (out of scope for the default rendering — see "Dual-period variant" below).

## Pre-check halts

Same as W1, plus:

| Trigger | Halt message |
|---|---|
| Make missing | "Which make? Regional heatmap requires a make filter (e.g. `Toyota`, `Ford`, `Tesla`)." |

## Wave A — 1 (or 2) `get_sold_summary` calls

```
get_sold_summary (current period):
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
→ parse_sold_summary.py --file <persisted-path>
```

When the user wants a dual-period heatmap (e.g. "show me how F-150 demand shifted by state from Q4 2025 to Q1 2026"), fire a second `get_sold_summary` for the prior period in the same wave. The current `compute_regional_heatmap.py` accepts an optional `--prior` flag but doesn't currently surface dual-period output; default to single-period rendering.

### Wall-clock budget

~12s for the wave.

## Pipeline

```
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w5_current.json > current_parsed.json

compute_regional_heatmap.py \\
  --current current_parsed.json \\
  --make <MAKE> \\
  [--model <MODEL>] \\
  [--top-n 10]
> heatmap.json

render_share_table.py --mode regional-heatmap --data heatmap.json
> heatmap_table.md
```

The compute script:
- **Filters by make (and optionally model)** at the row level — the parsed response may include multiple makes if `ranking_dimensions="make,model"` returned a top-N rollup that crossed makes. The script's `--make` filter is the authoritative scope.
- **Aggregates per state**: sum sold_count, weighted-mean avg_sale_price (weight = sold_count), weighted-mean avg_dom (same weight).
- **Computes ratios**: `pct_of_national_volume = state_volume / national_volume × 100`; `price_vs_national_ratio = state_avg_price / national_avg_price`.
- **Ranks states** by sold_count descending.
- **Surfaces top picks**: `top_volume_states` (top-N state names) and `bottom_growth_markets` (bottom-N state names — interpreted as "under-penetrated potential growth markets").

## Output rendering

1. **Headline**:
   *"For <make> <model>, <top_state> leads with <top_share>% of national volume at $<avg_price> (<ratio>× national average). Under-penetrated large markets: <bottom_3_states>."*
2. **Heatmap table** (rendered via `render_share_table.py --mode regional-heatmap`):
   `Rank | State | Sold Count | % of National | Avg Sale Price | Price vs National | Avg DOM`
3. **Top-10 markets paragraph** + **bottom-10 growth markets list**.
4. **Strategic implications** — pulled from `references/outcomes.md` action-to-outcome funnel scenario 4 (regional director allocation).
5. **Source line**.

## `--make` casing discipline

When the user types a make like "honda" (lowercase), the call may return `num_found == 0` because `get_sold_summary` matches makes case-sensitively against its index. The skill's facet-discovery retry (per `references/facet-discovery.md`) runs once on `make_model_not_found` to normalize casing — discover `make` via a one-shot `search_active_cars facets="make|0|100"` call, then re-issue with the resolved casing. Cache the resolved casing for the session.

## Failure recovery

| Case | Trigger | Behavior |
|---|---|---|
| `parse_sold_summary` `error_type=make_model_not_found` | Make casing mismatch | Retry once with facet-discovered casing. If still failing, halt with "Make `<make>` not recognized in `get_sold_summary`'s indexed values. Try a different spelling." |
| `compute_regional_heatmap` `error_type=no_data_for_make` | Empty rows after make filter | Halt with "No sold-summary data for `<make>` (`<model>` if model set) in `<period>`. Check make casing; widen the date window." |
| `parse_sold_summary` `error_type=network_5xx` | Upstream error | Halt with "Upstream data unavailable; retry in a few minutes." |
| Single-state response (e.g. only TX present) | Geographic concentration | Render normally; the `pct_of_national_volume` for the only state is 100%. No halt. Surface as a Key Signal *"Sales for `<make>` are concentrated in <state> for the period — limited regional spread."* |
| `top_n=50` per-state limit binding | Per-state response capped | Rare; the script uses sold_count from the rows that came back. Emit DQ event (e) noting *"Per-state response capped at top_n=50; rare states with > 50 model rows may be under-counted."* |
