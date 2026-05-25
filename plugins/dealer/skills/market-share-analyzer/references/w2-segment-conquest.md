# W2 — Segment Conquest Analysis

For "who's winning in SUVs," "segment leader," "conquest opportunity in pickups." Same shape as W1 but scoped to a single body_type, with per-(make, model) granularity.

**US-only** — halt UK profiles.

## Required inputs

- **Body type / segment**: one of `SUV`, `Sedan`, `Pickup`, `Hatchback`, `Coupe`, `Van/Minivan`, `Wagon`, `Convertible` (per `mcp_server_tool_docs/get_sold_summary.md` body_type values). Required.
- **Geographic scope**: state or national (default: profile state, then national).
- **Current period** + **Prior period**: same month-aligned defaults as W1 (`compute_period_window.py --months-back 1` and `--months-back 2`).
- **Inventory type**: same as W1.

If the user wants a multi-segment view (compare SUV / Sedan / Pickup side by side), repeat the workflow per segment — each segment gets its own pair of calls.

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
→ parse_sold_summary.py --file <persisted-path>

get_sold_summary (prior period):
  same shape, prior dates
→ parse_sold_summary.py --file <persisted-path>
```

### Wall-clock budget

~12s for the wave.

## Pipeline

```
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w2_current.json > current_parsed.json
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w2_prior.json   > prior_parsed.json

compute_segment_conquest.py \\
  --current current_parsed.json \\
  --prior   prior_parsed.json \\
  --body-type "SUV" \\
  [--user-brand <make>] \\
  [--top-n 15] \\
  [--state <STATE>]
> segment_conquest.json

render_share_table.py --mode segment-conquest --data segment_conquest.json
> segment_table.md
```

`compute_segment_conquest.py` rolls up the per-(make,model) rows two ways:
- Per-make rollup → identifies segment leader, user-brand rank, gap to leader.
- Per-model rollup → feeds the rendered table + identifies the fastest gainer.

## Output rendering

1. **Headline**:
   *"In the <body_type> segment, <leader.make> leads with <leader.share_pct>% on <leader.sold_count> sold. <user_brand> sits at #<rank>, gap of <gap_units> units to the leader."*
2. **Segment table** (rendered via `render_share_table.py --mode segment-conquest`):
   `Rank | Make | Model | Sold Count | Segment Share % | Prior Share % | Share Change`
3. **Conquest insight paragraph** (always when `fastest_gainer` non-null):
   *"<fastest_gainer.make> <fastest_gainer.model> gained the most ground at <fastest_gainer.bps_signed>. To recapture share, <user_brand> should focus on the model that competes directly with <fastest_gainer.model>."*
4. **Strategic implications** — pulled from `references/outcomes.md` action-to-outcome funnel scenarios 1, 4, 5 (OEM brand manager, regional director, market researcher).
5. **Source line**.

## Multi-segment variant

When the user asks for all segments at once (e.g. "show me share across every segment"), fan out 6 pairs of calls — one pair per body_type — in a single wave (12 parallel calls). Each pair pipes to `compute_segment_conquest.py` independently. The renderer concatenates per-segment tables with a leading **Segment Summary** table:

```
Segment | Leader | Leader Share % | <user_brand> Rank | <user_brand> Share % | Gap to Leader
```

This is rendered manually by the agent from each segment's `compute_segment_conquest` output (no dedicated render-mode for the summary table; it's a small enough table to format inline).

## Failure recovery

Inherits W1's recovery table (same parser, same compute-script error patterns), plus:

| Case | Trigger | Behavior |
|---|---|---|
| Body type returns zero matches | Empty rows for the chosen segment in the chosen state | Halt with "No `<body_type>` sold-summary data for `<state>` in `<period>`. Try a broader scope or a different segment." |
| `compute_segment_conquest` `error_type=no_current_data` | Same as W1's no_current_data | Halt with the no-data message. |
