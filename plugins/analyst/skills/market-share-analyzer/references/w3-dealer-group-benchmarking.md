---
name: w3-dealer-group-benchmarking
description: W3 — Dealer Group Benchmarking. Three parallel `get_sold_summary` calls (volume / DOM / avg-price) for the last 3 full calendar months; merge by `dealership_group_name`; map to public-dealer-group tickers (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA); compute efficiency score; emit leaderboard.
type: reference
---

# W3 — Dealer Group Benchmarking (Retail-Stock Operational Signal)

For "top dealer-group tickers by volume", "AN vs LAD efficiency",
"benchmark KMX vs CVNA". Issues 3 parallel `get_sold_summary` calls
(volume / DOM / avg-price) for the last 3 full calendar months, merges
by `dealership_group_name`, maps to the 8 public-dealer-group tickers,
computes efficiency score, emits a leaderboard.

**US-only** — halt non-US profiles per `references/country-uk.md`.

**Current-period only** — no prior-period comparison in v1.0.0. The W3
verdict is operational (volume rank, efficiency rank, DOM differential),
not directional — see `references/signal-aggregation.md §Dealer-group-mode
special case`.

## Required inputs

- **Geographic scope**: state or national (default: profile
  `analyst.tracked_states` if single value; ask if multi; national if
  empty).
- **Period**: 3 full calendar months by default (rolling quarter; via
  `compute_sold_summary_dates.py`). Single-month override accepted but
  the leaderboard is denser with a 3-month window.
- **Inventory type**: see "Used vs New routing" below.
- **Optional `make` filter**: scopes the leaderboard to a single brand's
  network ("how do AN, LAD, and Hendrick rank in **Toyota** sales
  specifically").

## Used vs New routing

The 8 dealer-group tickers have different new/used mix:

| Ticker | Operational model | Recommended `inventory_type` calls |
|---|---|---|
| AN, LAD, PAG, SAH, GPI, ABG | Franchise dealer-group (new + used) | **Two passes: `Used` + `New`**, render both |
| KMX | Used-only retail | **`Used` only** |
| CVNA | Pure-online used | **`Used` only** |

Default: when the user did not specify, run a `Used` pass (covers all 8
tickers). Offer a `New` pass when the user's `analyst.focus` is `oem` or
when the question mentions new-vehicle dynamics.

## Pre-check halts

Same as W1.

## Wave A — 3 parallel `get_sold_summary` calls (per inventory_type pass)

```
get_sold_summary (volume):
  date_from / date_to / inventory_type / state — shared
  [make=<MAKE>]                                # optional, when --user-make supplied
  ranking_dimensions="dealership_group_name"
  ranking_measure="sold_count"
  ranking_order="desc"
  top_n=20                                     # top 20 dealer groups (covers all 8 public tickers + private)
  summary_by="state"
  limit=5000
  # NO dealer_type

get_sold_summary (DOM):
  (same shape, EXCEPT)
  ranking_measure="average_days_on_market"
  ranking_order="asc"                          # lowest DOM first

get_sold_summary (avg price):
  (same shape, EXCEPT)
  ranking_measure="average_sale_price"
  ranking_order="desc"
```

Three calls fire in a single agent message; ~12-15s wall-clock; ≤5 ceiling
respected (3 calls).

When running both `Used` and `New` passes, that's 2 × 3 = 6 calls split
into 2 sub-batches of ≤5 (e.g. 3 Used calls in Wave A, then 3 New calls
in Wave B).

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

aggregate_signals.py \\
  --mode dealer-group \\
  --input leaderboard.json \\
  [--tracked-tickers <profile.analyst.tracked_tickers>] \\
  [--focus <profile.analyst.focus>]
> dealer_group_tickers.json

render_share_table.py --mode dealer-group-leaderboard --data leaderboard.json
> leaderboard_table.md
```

The compute script:
- **Aggregates by group**: sums `sold_count` from the volume input;
  weighted-mean `avg_dom` and `avg_sale_price` from the other two inputs
  (weight = `sold_count` per row).
- **Computes efficiency**: `efficiency_score = sold_count / avg_dom` per
  group (per existing target SKILL.md — "higher is better — moves more
  units faster"). Groups with `avg_dom == 0` or null get null efficiency.
- **Surfaces top picks**: `top_volume`, `top_efficiency`, `top_avg_price`
  — the three "best in class" group names.

`aggregate_signals.py --mode dealer-group` maps the 8 public-ticker group
names (AN / LAD / PAG / SAH / GPI / ABG / KMX / CVNA) via substring
match. Private dealer groups in the top-20 (e.g. Hendrick Automotive,
Berkshire Hathaway Automotive) appear in the leaderboard table but not
in the Ticker Impact Summary block — DQ event (d) is NOT raised for them
(this is by design — only the 8 public groups are investment-relevant).

## Output rendering

1. **Headline**:
   > *"<top_volume_ticker> leads dealer-group volume with
   > <count> units; <top_efficiency_ticker> moves units fastest at
   > <dom> avg DOM; <top_avg_price_ticker> commands the highest
   > average sale price at $<price>."*

2. **Leaderboard table** (per-group, via `render_share_table.py --mode
   dealer-group-leaderboard`):
   ```
   Rank | Dealer Group | Ticker | Sold Count | Market Share % | Avg DOM | Avg Sale Price | Efficiency Score
   ```

3. **Ticker Impact Summary table** (per-ticker, rendered inline from
   `aggregate_signals.tickers`):
   ```
   Ticker | Group Name | Current Volume | Current Share % | Avg DOM | Avg Sale Price | Efficiency Score | Verdict
   ```

   Verdict is NEUTRAL for all rows in v1.0.0 (W3 has no prior period);
   the operational signal lives in the volume vs efficiency contrast, not
   in the per-ticker verdict band.

4. **Top-volume / top-efficiency contrast paragraph**:
   > *"<top_volume_ticker> wins on raw scale, but <top_efficiency_ticker>
   > moves inventory <X> days faster on average — closing that DOM gap at
   > <top_volume_ticker>'s scale would free meaningful floor-plan capital
   > and is a recurring read on the <top_efficiency_ticker> operational
   > thesis."*

   `<X>` is `top_volume.avg_dom − top_efficiency.avg_dom`, computed at
   render time from the leaderboard rows.

5. **Investment Thesis** — sourced from `references/outcomes.md` Scenario
   3 (Public Dealer-Group Analyst). When `focus=dealer_groups`, lead with
   the tracked-ticker line.

6. **Source line**.

## `--user-make` scope variant

When the user asks "how do dealer-group tickers rank in **Toyota**?" —
re-issue the 3 calls with `make="Toyota"` filter on each. The leaderboard
then represents per-group Toyota volume (not total volume across all
brands). The `compute_dealer_group_leaderboard.py` script passes
`--user-make` through to the output's `scope.user_make` field; the
renderer surfaces this in the headline.

## Failure recovery

| Case | Trigger | Behavior |
|---|---|---|
| Any of the 3 parsed inputs `error_type=make_model_not_found` (only fires when `--user-make` set) | Make casing mismatch | Retry once with facet-discovered casing per `references/facet-discovery.md`. If still failing, halt the workflow. |
| Volume input `error_type=no_volume_data` | Empty `dealership_group_name` rows | Halt with "No dealer-group sold-summary data for `<period>` in `<state>`. Group rollups require non-empty `dealership_group_name`; if your filters are very narrow, widen them." |
| One of DOM/price inputs missing data | Group present in volume, absent in DOM/price | `efficiency_score` / `avg_sale_price` renders as `—` for that group; no halt. Log DQ event (e). |
| `parse_sold_summary` `validation_dimension_limit` | Tool rejects `dealership_group_name` as a dimension | Halt with parser error message + suggest manual workaround (`make` only). Rare. |
| Used+New both requested, one pass fails | Network / upstream error on one pass | Render the successful pass with a DQ event (a) noting the other pass was unavailable. |

## Why `dealership_group_name` is a hard ranking dimension

Per `mcp_server_tool_docs/get_sold_summary.md` — `dealership_group_name`
is one of four allowed `ranking_dimensions` values (alongside `make`,
`model`, `body_type`). The tool also exposes a `dealership_group_name`
*filter* which checks against a hard-coded 471-entry enum on the server
side. **Do NOT pass `dealership_group_name` as a filter** in W3 — the
`--user-make` path filters by `make`, not by group name. The enum check
is only relevant if a future workflow wants to drill into a specific
group's per-make split (out of scope for W3 v1.0.0).
