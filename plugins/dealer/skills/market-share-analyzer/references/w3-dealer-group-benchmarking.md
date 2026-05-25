# W3 — Dealer Group Benchmarking

For "who is the top dealer group," "AutoNation vs Lithia," "rank dealer groups by efficiency." Issues 3 parallel `get_sold_summary` calls (volume / DOM / avg price) for the current period, merges by `dealership_group_name`, computes efficiency score, emits a leaderboard.

**US-only** — halt UK profiles.

**Q2=A: current-period only.** No prior-period comparison; the existing target SKILL.md leaves W3 single-period and the user kept that scope. Re-evaluate if prior-period demand emerges later.

## Required inputs

- **Geographic scope**: state or national (default: profile state, then national).
- **Period**: 3 full calendar months by default (rolling quarter; via `compute_sold_summary_dates.py`). Single-month override accepted but the leaderboard is denser with a 3-month window.
- **Inventory type**: same as W1.
- **Optional `make` filter**: scopes the leaderboard to a single brand's network ("how do AutoNation, Lithia, and Hendrick rank in **Toyota** sales specifically").

## Pre-check halts

Same as W1.

## Wave A — 3 parallel `get_sold_summary` calls

```
get_sold_summary (volume):
  date_from / date_to / inventory_type / state — shared
  [make=<MAKE>]                                # optional, when --user-make supplied
  ranking_dimensions="dealership_group_name"
  ranking_measure="sold_count"
  ranking_order="desc"
  top_n=20                                     # top 20 dealer groups
  summary_by="state"
  limit=5000
  # NO dealer_type
→ parse_sold_summary.py --file <persisted-path>

get_sold_summary (DOM):
  (same shape, EXCEPT)
  ranking_measure="average_days_on_market"
  ranking_order="asc"                          # lowest DOM first
→ parse_sold_summary.py --file <persisted-path>

get_sold_summary (avg price):
  (same shape, EXCEPT)
  ranking_measure="average_sale_price"
  ranking_order="desc"
→ parse_sold_summary.py --file <persisted-path>
```

Three calls fire in a single agent message; ~12–15s wall-clock.

## Pipeline

```
parse_sold_summary.py --file <persisted-volume>    > volume_parsed.json
parse_sold_summary.py --file <persisted-dom>       > dom_parsed.json
parse_sold_summary.py --file <persisted-price>     > price_parsed.json

compute_dealer_group_leaderboard.py \\
  --volume volume_parsed.json \\
  --dom    dom_parsed.json \\
  --avg-price price_parsed.json \\
  [--user-make <make>] \\
  [--top-n 20]
> leaderboard.json

render_share_table.py --mode dealer-group-leaderboard --data leaderboard.json
> leaderboard_table.md
```

The compute script:
- **Aggregates by group**: sums sold_count from the volume input; weighted-mean avg_dom and avg_sale_price from the other two inputs (weight = sold_count per row).
- **Computes efficiency**: `efficiency_score = sold_count / avg_dom` per group (per existing target SKILL.md:135 — "higher is better — moves more units faster"). Groups with `avg_dom == 0` or null get null efficiency.
- **Surfaces top picks**: `top_volume`, `top_efficiency`, `top_avg_price` — the three "best in class" group names.

## Output rendering

1. **Headline**:
   *"<top_volume> leads dealer-group volume with <count> units (<share>%); <top_efficiency> moves units fastest at <dom> avg DOM; <top_avg_price> commands the highest average sale price at $<price>."*
2. **Leaderboard table** (rendered via `render_share_table.py --mode dealer-group-leaderboard`):
   `Rank | Dealer Group | Sold Count | Market Share % | Avg DOM | Avg Sale Price | Efficiency Score`
3. **Top-volume / top-efficiency contrast paragraph**:
   *"<top_volume> wins on raw scale, but <top_efficiency> moves inventory <X> days faster on average — closing that DOM gap at <top_volume>'s scale would free roughly $<floor_plan_savings> in annual floor-plan capital."* (Floor-plan-savings calc is illustrative; the script doesn't compute it. Phrase it qualitatively unless the user supplies `floor_plan_per_day`.)
4. **Strategic implications** — pulled from `references/outcomes.md` action-to-outcome funnel scenario 3 (dealer group CEO).
5. **Source line**.

## `--user-make` scope variant

When the user asks "how do dealer groups rank in **Toyota**?" — re-issue the 3 calls with `make="Toyota"` filter on each. The leaderboard then represents per-group Toyota volume (not total volume across all brands). The `compute_dealer_group_leaderboard.py` script passes `--user-make` through to the output's `scope.user_make` field; the renderer optionally surfaces this in the headline.

## Failure recovery

| Case | Trigger | Behavior |
|---|---|---|
| Any of the 3 parsed inputs `error_type=make_model_not_found` (only fires when `--user-make` set) | Make casing mismatch | Retry once with facet-discovered casing per `references/facet-discovery.md`. If still failing, halt the workflow. |
| Volume input `error_type=no_volume_data` | Empty `dealership_group_name` rows | Halt with "No dealer-group sold-summary data for `<period>` in `<state>`. Group rollups require non-empty `dealership_group_name`; if your filters are very narrow, widen them." |
| One of DOM/price inputs missing data | Group present in volume, absent in DOM/price | `efficiency_score` / `avg_sale_price` renders as `—` for that group; no halt. Log DQ event (e). |
| `parse_sold_summary` validation_dimension_limit | Tool rejects `dealership_group_name` as a dimension | Halt with parser error message + suggest manual workaround (`make` only). Rare. |

## Why `dealership_group_name` is a hard ranking dimension

Per `mcp_server_tool_docs/get_sold_summary.md` line 48 — `dealership_group_name` is one of four allowed `ranking_dimensions` values (alongside `make`, `model`, `body_type`). The tool also exposes a `dealership_group_name` *filter* (line 42) which checks against a hard-coded 471-entry enum on the server side. **Do NOT pass `dealership_group_name` as a filter** in W3 — the `--user-make` path filters by `make`, not by group name. The enum check is only relevant if a future workflow wants to drill into a specific group's per-make split (out of scope for W3).
