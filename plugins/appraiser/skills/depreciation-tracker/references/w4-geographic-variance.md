# W4 — Geographic Depreciation Variance

Triggers: "where do Tacomas hold value best", "which states have the highest
used-car prices", "geographic price variance for <make> <model>",
"multi-state insurance claim variance", "fleet relocation appraisal". The
output gives the appraiser a state-level price index — load-bearing for
multi-state insurance claims, fleet relocation appraisals, and estate /
probate valuations that span jurisdictions.

## Required inputs

- **`make`** + **`model`** (both required — geographic variance is per-vehicle).
- **No state** filter — the state IS the rollup dimension.
- **No `prior_period`** — W4 is a single-period snapshot, not a cross-period
  trend.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `country == "UK"` | per `references/country-uk.md` |
| `country` not US | per W1 pre-check halts |
| `make` or `model` missing | halt-and-ask |

## Parallelization (W4)

Single-wave workflow; 2 parallel `get_sold_summary` calls.

### Wave A — state-bucketed + national baseline (parallel)

```
1. get_sold_summary (state-bucketed):
     make=<make>, model=<model>
     inventory_type="Used"
     summary_by="state"
     ranking_dimensions="make,model"
     ranking_measure="average_sale_price"
     top_n=5, limit=5000
     date_from/to = current period (last full month per compute_sold_summary_dates.py)

2. get_sold_summary (national rollup):
     make=<make>, model=<model>
     inventory_type="Used"
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

For appraisers handling multi-state insurance claims or fleet relocation,
surface adjacent-state variance ≥10% as a Key Signal:
*"Adjacent state <state> trades at <pct>% of national vs profile state
<state>'s <pct>% — for a multi-state claim or relocation appraisal, the
destination-state anchor adds $<delta> per vehicle vs the source-state
anchor."*

## Comparison Context (W4-specific)

W4's Comparison Context anchors on the appraiser's profile state vs the
national average + top-5/bottom-5 spread:

```
Profile state <state>: index <pct>%, classification <premium|average|discount>.
National average: $<national_avg>. Top-5 premium: <list>. Bottom-5 discount: <list>.
```

When the profile state lands within ±2% of national, append: *"Profile
state is essentially at the national anchor; book-without-geo-adjustment
is defensible."*

## DQ event log discipline (W4)

- (a) MCP errors recovered.
- (e) National baseline call returned empty rows; falls back to weighted
  mean of state-rollup rows (less precise; surface the fallback).
- (g) Inventory type hardcoded to Used per workflow.
