# W4 — Geographic Depreciation Variance

Triggers: "where do Tacomas hold value best", "which states have the highest
used-car prices", "geographic price variance for <make> <model>", "state-level
arbitrage opportunity".

## Required inputs

- **`make`** + **`model`** (both required — geographic variance is per-vehicle).
- **No state** filter — the state IS the rollup dimension.
- **No `prior_period`** — W4 is a single-period snapshot, not a cross-period
  trend.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `country == "UK"` | per `references/country-uk.md` |
| `country == "CA"` | per SKILL.md |
| `make` or `model` missing | halt-and-ask |
| `inventory_type=both` | halt-and-ask |

## Parallelization (W4)

Single-wave workflow; 2 parallel `get_sold_summary` calls.

### Wave A — state-bucketed + national baseline (parallel)

```
1. get_sold_summary (state-bucketed):
     make=<make>, model=<model>
     inventory_type=<car_type>
     summary_by="state"
     ranking_dimensions="make,model"
     ranking_measure="average_sale_price"
     top_n=5, limit=5000
     date_from/to = current period (last full month per compute_sold_summary_dates.py)

2. get_sold_summary (national rollup):
     make=<make>, model=<model>
     inventory_type=<car_type>
     ranking_dimensions="make,model"
     ranking_measure="average_sale_price"
     top_n=5, limit=5000
     date_from/to = current period
     (no summary_by → returns one row per make/model rolled up across all states)
```

The two calls differ only in `summary_by`. Call 1 returns one row per state
(typically 30-50 rows for popular models); call 2 returns 1 row at the
national level.

## Pipeline

```
parse_sold_summary.py × 2 --aggregate-state <STATE> on call 1 (optional —
                            we use call 2 for national_avg, so call 1
                            doesn't need the state aggregate)
                            For call 2, no aggregation flags — read
                            rows[0].average_sale_price as national_avg.

geo_variance.py < {state_rows: <call-1 parsed>,
                   national_avg: <call-2 average_sale_price>}
                > geo.json

render_depreciation_table.py --mode geo --input geo.json
```

## Render

Per `assets/output-template.md` W4 column. Headline:

```
<make> <model> in <STATE> trades at <pct>% of national average ($<state_avg> vs $<national_avg>);
top premium markets: <top 3 states>; top discount markets: <bottom 3 states>.
```

For dealers near state borders, surface the cross-border arbitrage signal
in Key Signals when adjacent-state delta exceeds 10% (per the existing
skill's W4 step 4).

## DQ event log discipline (W4)

- (a) MCP errors recovered.
- (e) National baseline call returned empty rows; falls back to weighted
  mean of state-rollup rows (less precise; surface the fallback).
- (g) Inventory type defaulted from profile.
