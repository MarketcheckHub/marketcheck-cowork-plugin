---
name: w1-brand-share
description: W1 — Brand Market Share workflow. Per-make share %, share-change bps, volume-change % from two `get_sold_summary` calls (current + prior period). Rolled up to per-ticker BULLISH / BEARISH / NEUTRAL / CAUTION via `aggregate_signals.py --mode brand`.
type: reference
---

# W1 — Brand Market Share (Ticker-Level Investment Signal)

Reference workflow for "market share", "who is gaining", "which OEM
tickers are losing share". Computes per-make share % and share-change in
basis points (bps) by comparing two `get_sold_summary` calls — current
period vs prior period — then rolls per-make findings up to per-ticker
BULLISH / BEARISH / NEUTRAL / CAUTION via `aggregate_signals.py`.

**US-only** — halt non-US profiles per `references/country-uk.md`.

## Required inputs

- **Geographic scope**: `state` (2-letter code) for state-level share, OR
  omit `state` for national. Default: `analyst.tracked_states` if single
  value; ask user if multi-value; national if empty.
- **Current period**: a single calendar month OR a `benchmark_period_months`-
  wide window via `compute_period_window.py`. When
  `analyst.benchmark_period_months = 1`, that's "last full month vs
  prior full month". When `= 3` (the onboarding default), that's
  "current rolling quarter vs prior rolling quarter".
- **Prior period**: same period length offset back by that many months.
- **Inventory type**: default `Used` (used-vehicle volume is a deeper
  read on consumer demand-side strength than the new-vehicle allocation
  flow). User can override to `New`.

### Period invocation patterns

| `benchmark_period_months` | Current invocation | Prior invocation |
|---|---|---|
| 1 (MoM) | `--months-back 1 --num-months 1` | `--months-back 2 --num-months 1` |
| 3 (QoQ — default) | `--months-back 1 --num-months 3` | `--months-back 4 --num-months 3` |
| 6 | `--months-back 1 --num-months 6` | `--months-back 7 --num-months 6` |

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country != "US"` | per `references/country-uk.md` |
| User-supplied dates not month-aligned | "Date window must be full calendar month(s). Got `<date_from>` to `<date_to>`. Use `compute_period_window.py` or supply month-aligned dates." |

## Wave A — 2 parallel `get_sold_summary` calls

Per universal wave contract (SKILL.md §Parallelization): both calls
dispatched in a single agent message; wait for both before parsing.

```
get_sold_summary (current period):
  date_from=<current.date_from>, date_to=<current.date_to>
  inventory_type=<Used|New>                      # always set explicitly
  state=<STATE>                                  # omit for national
  ranking_dimensions="make"                      # minimal; avoid default 3-dim
  ranking_measure="sold_count"
  ranking_order="desc"
  top_n=50                                       # top 50 makes covers ~98% of US sales
  summary_by="state"                             # explicit, even though default
  limit=5000                                     # tool default 1000 silently truncates
  # NO dealer_type (per references/sold-summary-safety.md — silent suppression)

get_sold_summary (prior period):
  same shape, prior date_from / date_to
```

Both responses → `Write` to `/tmp/marketcheck/<run_id>/w1_current.json`
and `w1_prior.json` → `parse_sold_summary.py --file <path>`.

### Wall-clock budget

~12s for the wave (2 parallel calls); under the ≤5 concurrent ceiling.

## Pipeline

```
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w1_current.json > current_parsed.json
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w1_prior.json   > prior_parsed.json

compute_brand_share.py \\
  --current current_parsed.json \\
  --prior   prior_parsed.json \\
  [--top-n 20]                       # default 20 makes in the rendered table
  [--state <STATE>]                  # post-aggregation state filter
> brand_share.json

aggregate_signals.py \\
  --mode brand \\
  --input brand_share.json \\
  [--tracked-tickers <profile.analyst.tracked_tickers>] \\
  [--focus <profile.analyst.focus>]
> brand_share_tickers.json

render_share_table.py --mode brand-share --data brand_share.json
> brand_share_table.md
```

## Long-tail caveat

When the calling skill set `top_n=50`, the share denominator is the sum
of `sold_count` across the visible 50 makes. The long-tail (Maserati,
Lotus, Ferrari, etc.) is excluded — typically 2-5% of national volume.
Emit DQ event (e):

> *"Share computed over visible top-50 makes; long-tail makes excluded.
> True national volume is ~2-5% higher; per-ticker share figures are
> understated by an equivalent amount."*

The renderer surfaces this as a footnote under the brand-share table.

## Output rendering

The skill renders (via `assets/output-template.md`):

1. **Headline** — sourced from `compute_brand_share.summary` +
   `aggregate_signals.tickers` (top ticker):
   > *"<top_ticker> holds <top_ticker.current_share_pct>% national share
   > in <period> (<bps_signed> vs <prior_period>) — <top_ticker.verdict>
   > on revenue trajectory. <top_bullish_ticker> is the biggest gainer at
   > <bps_signed>."*

2. **Brand-share table** (per-make, via `render_share_table.py --mode
   brand-share`):
   ```
   Rank | Make | Current Sold | Current Share % | Prior Sold | Prior Share % | Share Change | Volume Change | Trend
   ```

3. **Ticker Impact Summary table** (per-ticker, rendered inline from
   `aggregate_signals.tickers`):
   ```
   Ticker | Makes | Current Volume | Current Share % | Share Change | Volume Change | Verdict
   ```

4. **Top-3 gainers / Top-3 losers** at the ticker level (from
   `aggregate_signals.headline_rollup`).

5. **Tracked-ticker movement narrative** (when
   `aggregate_signals.headline_rollup.tracked_signals` is non-null):
   per-tracked-ticker one-liner with verdict reason.

6. **Investment Thesis** — sourced from `references/outcomes.md`
   Scenario 1 / 5 (per `focus` bias).

7. **Source line**: `Source: MarketCheck sold-summary, <period>,
   <state-or-US national>, <inventory_type>.`

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| `parse_sold_summary` `error_type=make_model_not_found` | facet mismatch (rare on top-N call) | Retry once with facet-discovered casing per `references/facet-discovery.md`. If still failing, halt the workflow with a user-facing error. |
| `parse_sold_summary` `error_type=validation_dimension_limit` | `ranking_dimensions` rejected | Retry once with `ranking_dimensions="make"` (already minimal — fall back to no `ranking_dimensions`). |
| `parse_sold_summary` `error_type=network_422` | mis-aligned dates upstream | Verify dates are month-aligned via `compute_period_window.py`; re-issue. |
| `parse_sold_summary` `error_type=network_5xx` | upstream error | Halt with "Upstream data unavailable; retry in a few minutes." |
| `compute_brand_share` `error_type=no_current_data` | empty rows after filters | Halt with "No sold-summary data for `<period>` in `<state>`. Check date alignment or widen the geographic scope." |
| Both periods empty (rare) | Both `parse_sold_summary` returned 0 rows | Halt with the same no-data message; emit DQ event (a) per period. |
| Tracked ticker absent from top-50 in both periods | Ticker exists but sub-top-50 | `aggregate_signals.tickers` omits it; renderer prints "<ticker> not in top-50 makes for the period — share too small to classify." |
| Make resolves to no ticker in mapping | Long-tail OEM not in 13-ticker table | DQ event (d) — "Make `<make>` has no tracked ticker; excluded from Ticker Impact Summary." |
