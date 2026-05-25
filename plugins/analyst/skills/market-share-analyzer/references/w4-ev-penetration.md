---
name: w4-ev-penetration
description: W4 — EV Adoption Tracking. Six parallel `get_sold_summary` calls (EV / Hybrid / Total × current / prior) sub-batched into 2 waves of ≤5 calls; yields EV / Hybrid / combined-electrified penetration % + bps deltas + per-ticker EV-mix breakdown.
type: reference
---

# W4 — EV Adoption Tracking (Sector-Transition Signal)

For "EV penetration rate", "TSLA share loss vs absolute volume", "which
OEM tickers are gaining EV share fastest". Six `get_sold_summary` calls
across two sub-batches — EV current/prior, Hybrid current/prior, Total
current/prior — yielding penetration percentages, period-over-period bps
shifts, and a per-ticker EV-mix breakdown for the TSLA-vs-legacy
narrative.

**US-only** — halt non-US profiles per `references/country-uk.md`.

**Default `inventory_type = New`** — EV adoption is a new-vehicle
transition phenomenon. User can override to `Used` (less common).

## Required inputs

- **Geographic scope**: state or national (default: profile
  `analyst.tracked_states` if single value; ask if multi; national if
  empty).
- **Current period** + **Prior period**: same period invocation patterns
  as W1.
- **Inventory type**: default `New`.

## Pre-check halts

Same as W1.

## Wave A + Wave B — 6 calls total, sub-batched into 2 waves of ≤5

The 6 calls split into 2 sub-batches because the upstream rate-limit
ceiling is ≤5 concurrent (`references/sold-summary-safety.md §Upstream
rate limit`).

**Wave A — 4 calls (fired in one agent message):**

```
EV current:
  date_from / date_to / inventory_type / state — shared
  fuel_type_category="EV"
  ranking_dimensions="make,model"
  ranking_measure="sold_count"
  ranking_order="desc"
  top_n=15
  summary_by="state"
  limit=5000
  # NO dealer_type

EV prior:
  same shape, prior dates

Hybrid current:
  same shape EXCEPT fuel_type_category="Hybrid"

Hybrid prior:
  same shape EXCEPT fuel_type_category="Hybrid", prior dates
```

**Wave B — 2 calls (fired in one agent message after Wave A completes):**

```
Total current (no fuel_type_category):
  date_from / date_to / inventory_type / state — shared
  # NO fuel_type_category — captures all sold volume
  ranking_dimensions="make"                    # rolled up by make for brand-level EV share later
  ranking_measure="sold_count"
  ranking_order="desc"
  top_n=50                                     # near-total US sold volume; long-tail caveat applies
  summary_by="state"
  limit=5000
  # NO dealer_type

Total prior:
  same shape, prior dates
```

### Total denominator

The two "Total" calls (Wave B) are the EV-penetration denominator:
- They use `top_n=50` (covers ~98% of US sales by make, same as W1's
  denominator approach).
- The compute script sums `sold_count` across all rows for the total —
  long-tail makes excluded.
- This is symmetric with W1's brand-share denominator: same call shape,
  same coverage caveat, same DQ event (e) "share computed over visible
  top-50 makes; long-tail excluded."

### Wall-clock budget

~12-15s per wave; total ~24-30s end-to-end for the 6 calls.

## Pipeline

```
# 6 parsers (in parallel after each wave returns)
parse_sold_summary.py --file <persisted-ev-current>    > ev_current.json
parse_sold_summary.py --file <persisted-ev-prior>      > ev_prior.json
parse_sold_summary.py --file <persisted-hybrid-current> > hybrid_current.json
parse_sold_summary.py --file <persisted-hybrid-prior>  > hybrid_prior.json
parse_sold_summary.py --file <persisted-total-current> > total_current.json
parse_sold_summary.py --file <persisted-total-prior>   > total_prior.json

compute_ev_penetration.py \\
  --ev-current     ev_current.json     --ev-prior     ev_prior.json \\
  --hybrid-current hybrid_current.json --hybrid-prior hybrid_prior.json \\
  --total-current  total_current.json  --total-prior  total_prior.json \\
  [--top-n 15] \\
  [--state <STATE>]
> ev_penetration.json

aggregate_signals.py \\
  --mode ev \\
  --input ev_penetration.json \\
  [--tracked-tickers <profile.analyst.tracked_tickers>] \\
  [--focus <profile.analyst.focus>]
> ev_tickers.json
```

Then **two separate render calls** (the script renders top-EV-models +
top-Hybrid-models in one pass via `--mode ev-penetration`; the
brand-level EV share is a separate table via `--mode ev-brand-share`):

```
render_share_table.py --mode ev-penetration   --data ev_penetration.json > penetration_block.md
render_share_table.py --mode ev-brand-share   --data ev_penetration.json > brand_share_block.md
```

## Output rendering

1. **Headline**:
   > *"EVs represented <ev_pct>% of <state-or-US-national> new-vehicle
   > sales in <period>, <bps_signed> from <prior_period>. Hybrids were
   > <hybrid_pct>%; combined electrified rate <combined_pct>%
   > (<combined_bps_signed>). <verdict_on_dominant_ticker> for
   > <dominant_ticker>; <verdict_on_runner_up> for <runner_up>."*

2. **Penetration summary block** (rendered by `--mode ev-penetration` —
   three summary lines + top-EV-models table + top-Hybrid-models table).

3. **EV brand share table** (per-make, rendered by `--mode
   ev-brand-share`):
   ```
   Make | EV Units | Brand Total | % of Brand Sales That Are EV
   ```
   sorted by EV units desc.

4. **Ticker Impact Summary table** (per-ticker rollup of EV mix):
   ```
   Ticker | EV Units | Brand Total | % EV Mix | Verdict
   ```

   The verdict for TSLA, RIVN, LCID is "always BULLISH on absolute volume
   when EV volume is up — share loss only matters in the context of
   total-cohort growth" — handled by `aggregate_signals.py --mode ev`
   per `references/signal-aggregation.md §EV-mode special case`.

5. **Period trend paragraph**:
   > *"EV penetration <accelerated|plateaued|slowed> from <prior_pct>% to
   > <current_pct>% (<bps_signed>). EV unit volume <up|down> by
   > <volume_change>%. For TSLA: <tsla_share>% of EV market, <tsla_change>
   > vs <prior_period>; absolute TSLA EV volume <up|down> <tsla_volume_pct>%.
   > For legacy OEMs: <legacy_ticker> at <legacy_ev_pct>% EV mix —
   > <legacy_verdict>."*

6. **Investment Thesis** — sourced from `references/outcomes.md` Scenario
   2 (EV-Cohort Analyst).

7. **Source line**.

## Long-tail caveat

Same as W1 — the "Total" denominator uses `top_n=50`, so long-tail makes
(~2-5% of national volume) are excluded. The compute script doesn't flag
this automatically; the calling skill emits DQ event (e) once:

> *"Total-market denominator computed over visible top-50 makes; long-tail
> excluded. EV / Hybrid percentages may be ~2-5% understated."*

## Failure recovery

| Case | Trigger | Behavior |
|---|---|---|
| Any of the 6 parsed inputs `error_type=make_model_not_found` | Rare; usually only fires with explicit `make` filter (W4 has none) | Halt with the parser error. |
| Total-current empty (`compute_ev_penetration error_type=no_total_current_data`) | Both fuel-filtered + total calls returned 0 rows | Halt with "No sold-summary data for `<period>` in `<state>`. Check date alignment." |
| EV current empty but Total non-empty | EV market is empty for the state (e.g. WY, ND) | Render with `ev_pct = 0.0`; emit DQ event (e) "no EV sales recorded for `<state>` in `<period>`." |
| One Hybrid call fails | Tool error on Hybrid filter only | Render EV penetration only; mark Hybrid as `unavailable`; emit DQ event (a). |
| `fuel_type_category` rejected by tool | Rare upstream issue | Halt with the parser error (W4 cannot proceed without the fuel filter). |
| Wave B fires before Wave A returns | Wave-contract violation — concurrent waves | Treat as bug; do NOT sub-batch in parallel. |
