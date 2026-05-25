# W4 — EV Adoption Tracking

For "EV penetration rate," "Hybrid adoption," "which brands are most electrified." Six parallel `get_sold_summary` calls — EV current/prior, Hybrid current/prior, Total current/prior — yielding penetration percentages and period-over-period bps shifts.

**US-only** — halt UK profiles.

**Q3=A: separate "no fuel filter" call per period** for the total-market denominator (see "Total denominator" below).

## Required inputs

- **Geographic scope**: state or national (default: profile state, then national).
- **Current period** + **Prior period**: same monthly defaults as W1.
- **Inventory type**: same as W1.

## Pre-check halts

Same as W1.

## Wave A — 6 parallel `get_sold_summary` calls

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
→ parse_sold_summary.py --file <persisted-path>

EV prior:
  same shape, prior dates
→ parse_sold_summary.py --file <persisted-path>

Hybrid current:
  same shape EXCEPT fuel_type_category="Hybrid"
→ parse_sold_summary.py --file <persisted-path>

Hybrid prior:
  same shape, prior dates, fuel_type_category="Hybrid"
→ parse_sold_summary.py --file <persisted-path>

Total current (Q3=A: separate call without fuel_type_category):
  date_from / date_to / inventory_type / state — shared
  # NO fuel_type_category — captures all sold volume
  ranking_dimensions="make"                    # rolled up by make for brand-level EV share later
  ranking_measure="sold_count"
  ranking_order="desc"
  top_n=50                                     # near-total US sold volume; long-tail caveat applies
  summary_by="state"
  limit=5000
  # NO dealer_type
→ parse_sold_summary.py --file <persisted-path>

Total prior:
  same shape, prior dates
→ parse_sold_summary.py --file <persisted-path>
```

Six parallel calls in a single wave; ~15s wall-clock.

### Total denominator (Q3=A)

The two "Total" calls are the EV-penetration denominator. Per the plan's Q3=A:
- They use `top_n=50` (covers ~98% of US sales by make, same as W1's denominator approach).
- The compute script sums `sold_count` across all rows for the total — long-tail makes excluded.
- This is symmetric with W1's brand-share denominator: same call shape, same coverage caveat, same DQ event (e) "share computed over visible top-50 makes; long-tail excluded."

## Pipeline

```
# 6 parsers
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
```

Then **two separate render calls** (the script renders top-EV-models + top-Hybrid-models in one pass via `--mode ev-penetration`; the brand-level EV share is a separate table via `--mode ev-brand-share`):

```
render_share_table.py --mode ev-penetration   --data ev_penetration.json > penetration_block.md
render_share_table.py --mode ev-brand-share   --data ev_penetration.json > brand_share_block.md
```

## Output rendering

1. **Headline**:
   *"EVs represented <ev_pct>% of <state-or-national> sales in <month>, <bps_signed> from <prior_month>. Hybrids were <hybrid_pct>%; combined electrified rate <combined_pct>% (<combined_bps_signed>)."*
2. **Penetration summary block** (rendered by `--mode ev-penetration` — three summary lines + top-EV-models table + top-Hybrid-models table).
3. **EV brand share table** (rendered by `--mode ev-brand-share`):
   `Make | EV Units | Brand Total | % of Brand Sales That Are EV` — sorted by EV units desc.
4. **Period trend paragraph**:
   *"EV penetration <accelerated|plateaued|slowed> from <prior_pct>% to <current_pct>% (<bps_signed>). EV unit volume <change_direction> by <volume_change>%."*
5. **Strategic implications** — pulled from `references/outcomes.md` action-to-outcome funnel scenario 2 (analyst).
6. **Source line**.

## Failure recovery

| Case | Trigger | Behavior |
|---|---|---|
| Any of the 6 parsed inputs `error_type=make_model_not_found` | Rare; usually only fires with explicit `make` filter (W4 has none) | Halt with the parser error. |
| Total-current empty (`compute_ev_penetration error_type=no_total_current_data`) | Both fuel-filtered + total calls returned 0 rows | Halt with "No sold-summary data for `<period>` in `<state>`. Check date alignment." |
| EV current empty but Total non-empty | EV market is empty for the state (e.g. WY, ND) | Render with `ev_pct = 0.0`; emit DQ event (e) "no EV sales recorded for `<state>` in `<period>`." |
| One Hybrid call fails | Tool error on Hybrid filter only | Render EV penetration only; mark Hybrid as `unavailable`; emit DQ event (a). |
| `fuel_type_category` rejected by tool | Rare upstream issue | Halt with the parser error (W4 cannot proceed without the fuel filter). |

## Long-tail caveat

Same as W1 — the "Total" denominator uses `top_n=50`, so long-tail makes (~2–5% of national volume) are excluded. The compute script doesn't flag this automatically; the calling skill emits DQ event (e) once: *"Total-market denominator computed over visible top-50 makes; long-tail excluded. EV/Hybrid percentages may be ~2-5% understated."*
