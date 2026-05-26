---
name: w2-segment-conquest
description: W2 — Segment Conquest Analysis. Body_type-scoped per-(make,model) share from two `get_sold_summary` calls; identifies segment leader, gap to leader, and fastest-gaining model. Rolled up to per-ticker verdict for the segment-level read.
type: reference
---

# W2 — Segment Conquest Analysis (Investment Positioning)

For "who is winning in SUVs", "segment leader", "ticker conquest in
pickups". Same shape as W1 but scoped to a single body_type, with
per-(make, model) granularity. The segment-level read is the actionable
read for buy-side: an OEM gaining national share but losing the
gross-profit-pool segment (e.g. SUVs / Pickups) is a more nuanced story
than the headline share alone.

**US-only** — halt non-US profiles per `references/country-uk.md`.

## Required inputs

- **Body type / segment**: one of `SUV`, `Sedan`, `Pickup`, `Hatchback`,
  `Coupe`, `Van/Minivan`, `Wagon`, `Convertible` (per
  `mcp_server_tool_docs/get_sold_summary.md` body_type values). Required.
- **Geographic scope**: state or national (default: profile
  `analyst.tracked_states` if single value; ask if multi; national if
  empty).
- **Current period** + **Prior period**: same period invocation patterns
  as W1 (see W1 §Period invocation patterns).
- **Inventory type**: default `Used`. User can override to `New`.

If the user wants a multi-segment view (compare SUV / Sedan / Pickup side
by side), repeat the workflow per segment — each segment gets its own
pair of calls. Sub-batch into waves of ≤5 calls per the ≤5-concurrent
ceiling (see SKILL.md §Parallelization).

## Pre-check halts

Same as W1, plus:

| Trigger | Halt message |
|---|---|
| Body type missing | "Which segment? Choose one of SUV / Sedan / Pickup / Hatchback / Coupe / Van/Minivan / Wagon / Convertible." |
| Body type unrecognized | "Body type `<value>` not recognized. Valid: SUV, Sedan, Pickup, Hatchback, Coupe, Van/Minivan, Wagon, Convertible." |

## Wave A — 2 parallel `get_sold_summary` calls

```
get_sold_summary (current period):
  date_from / date_to / inventory_type / state — same as W1
  body_type=<SUV|Sedan|Pickup|...>             # segment filter
  ranking_dimensions="make,model"              # per-model granularity within segment
  ranking_measure="sold_count"
  ranking_order="desc"
  top_n=15                                     # top 15 models in the segment
  summary_by="state"
  limit=5000
  # NO dealer_type

get_sold_summary (prior period):
  same shape, prior dates
```

### Wall-clock budget

~12s for the wave (2 parallel calls). For multi-segment fan-out (e.g. 4
segments × 2 periods = 8 calls), split into 2 sub-batches of ≤5 calls.

## Pipeline

```
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w2_current.json > current_parsed.json
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w2_prior.json   > prior_parsed.json

compute_segment_conquest.py \\
  --current current_parsed.json \\
  --prior   prior_parsed.json \\
  --body-type "SUV" \\
  [--top-n 15] \\
  [--state <STATE>]
> segment_conquest.json

aggregate_signals.py \\
  --mode segment \\
  --input segment_conquest.json \\
  [--tracked-tickers <profile.analyst.tracked_tickers>] \\
  [--focus <profile.analyst.focus>]
> segment_tickers.json

render_share_table.py --mode segment-conquest --data segment_conquest.json
> segment_table.md
```

## Output rendering

1. **Headline** — sourced from `compute_segment_conquest` +
   `aggregate_signals`:
   > *"In the <body_type> segment, <leader.ticker> (<leader.make>) leads
   > with <leader.share_pct>% on <leader.sold_count> units —
   > <leader.verdict>. <fastest_gainer.ticker> (<fastest_gainer.make>
   > <fastest_gainer.model>) gained the most ground at
   > <fastest_gainer.share_change_bps>."*

2. **Segment table** (per-model, via `render_share_table.py --mode
   segment-conquest`):
   ```
   Rank | Make | Model | Sold Count | Segment Share % | Prior Share % | Share Change
   ```

3. **Ticker Impact Summary table** (per-ticker rollup for this segment):
   ```
   Ticker | Makes in Segment | Current Sold | Current Share % | Share Change | Verdict
   ```

4. **Conquest insight paragraph** (always when `fastest_gainer` non-null):
   > *"<fastest_gainer.ticker> is the segment's fastest-gaining ticker via
   > <fastest_gainer.make> <fastest_gainer.model> at
   > <fastest_gainer.share_change_bps>. For tracked tickers exposed to
   > this segment: <tracked_ticker_segment_movement>."*

5. **Investment Thesis** — sourced from `references/outcomes.md` Scenario
   4 / 1 (per `focus` bias).

6. **Source line**.

## Multi-segment variant

When the user asks for all segments at once (e.g. "show me share across
every segment"), fan out 6 pairs of calls — one pair per body_type. Split
into 2 sub-batches of ≤5 calls per the rate-limit ceiling. Each pair
pipes to `compute_segment_conquest.py` independently. The renderer
concatenates per-segment tables with a leading **Segment Ticker Summary**
table:

```
Segment | Leader Ticker | Leader Share % | Fastest-Gainer Ticker | Gainer Share Change | Tracked Ticker Status
```

This is rendered manually by the agent from each segment's
`aggregate_signals` output (no dedicated render-mode for the summary
table; it's a small enough table to format inline).

## Failure recovery

Inherits W1's recovery table (same parser, same compute-script error
patterns), plus:

| Case | Trigger | Behavior |
|---|---|---|
| Body type returns zero matches | Empty rows for the chosen segment in the chosen state | Halt with "No `<body_type>` sold-summary data for `<state>` in `<period>`. Try a broader scope or a different segment." |
| `compute_segment_conquest` `error_type=no_current_data` | Same as W1's no_current_data | Halt with the no-data message. |
| Multi-segment fan-out partial failure | One of the N segment calls returned empty | That segment is omitted from the Segment Ticker Summary table; DQ event (a) logged. |
