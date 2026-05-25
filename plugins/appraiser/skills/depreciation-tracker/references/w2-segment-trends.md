# W2 — Segment Value Trends

Triggers: "are SUVs holding value better than sedans", "EV vs ICE depreciation
comparison", "segment trends", "body type retention", "segment-level
trend adjustments". The output gives the appraiser a segment-level
trend-adjustment factor — useful for fleet portfolio revaluation, insurance
total-loss settlements on a vehicle in a fast-moving segment, and trade-in
desk decisions when book lags transaction reality.

## Required inputs

- No make/model required — W2 ranks segments, not specific vehicles.
- **`comparison`** — one of `body_type` (default) or `fuel_type` (EV vs ICE
  vs Hybrid). Or `both` to run two parallel passes.
- **State** — required (US-only, default from profile).
- **`prior_period_offset`** — months back for the prior-period anchor.
  Default 3 months back; overridable.

## Pre-check halts

Same as W1 except W2 has no make/model requirement.

## Parallelization (W2)

W2 is a single-wave workflow; up to 6 parallel `get_sold_summary` calls.

### Wave A — body_type and/or fuel_type cross-period (parallel)

For `comparison="body_type"` (2 calls: current + prior):

```
get_sold_summary × 2:
  state=<state>
  inventory_type="Used"
  ranking_dimensions="body_type"
  ranking_measure="average_sale_price"
  top_n=10
  limit=5000
  summary_by="state"
  date_from/to = current period (prior month) [call 1]
  date_from/to = prior period (3 months back) [call 2]
```

For `comparison="fuel_type"`:

EV: `fuel_type_category="EV"` × current + prior (2 calls)
ICE: `fuel_type_category="ICE"` × current + prior (2 calls)
Hybrid: optional, only fired when user asks. (2 calls)

When `comparison="both"`, fire body + EV + ICE = 6 calls.

Date windows come from `compute_period_windows.py` with custom periods —
typically `current,3mo`. For v1.0.0, W2 uses the existing `60d`/`90d`
constants where the rendered "prior period" is documented as "approximately
90 days back" — keeps the renderer stable while period-customization is
deferred.

## Pipeline

```
parse_sold_summary.py × N        # one per call
segment_compare.py < {current, prior, dimension="body_type"}     > body.json
segment_compare.py < {current, prior, dimension="fuel_type_category"} > fuel.json

render_depreciation_table.py --mode segment --input body.json
render_depreciation_table.py --mode segment --input fuel.json
```

## Render

Per `assets/output-template.md` W2 column. Headline phrasing:

```
Across <STATE> over the last 3 months, the strongest-retention segment is <top> ({+/-X.X}%);
the weakest is <bottom> ({+/-X.X}%).
EV vs ICE: EV depreciated <pct>% vs ICE <pct>% — <ratio>x faster than ICE.
```

When EV depreciation is ≥1.5× ICE depreciation, surface as a Key Signal:
*"⚠ Fleet revaluation note: EVs depreciating <ratio>× faster than ICE in
<STATE>; portfolios concentrated in EVs need EV-specific residual
adjustment, not blended book."* (Per `references/outcomes.md` line 2.)

## DQ event log discipline (W2)

- (a) MCP errors recovered.
- (e) Body-type missing-in-prior or missing-in-current — surface from
  `segment_compare.missing_in_*` arrays.
- (g) Hybrid pass skipped because user did not request it.
