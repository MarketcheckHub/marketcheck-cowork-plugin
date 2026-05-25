---
name: w2-segment-trends
description: W2 — Segment Value Trends. Body_type and/or fuel_type cross-period comparison with EV-vs-ICE investment-signal mapping. Up to 6 parallel calls; sub-batches to ≤5 per agent message when the EV / ICE / Hybrid full set is requested.
type: reference
---

# W2 — Segment Value Trends

Triggers: "are SUVs holding value better than sedans", "EV vs ICE
depreciation — investment implications", "segment trends", "body type
retention", "which body types are softening".

## Required inputs

- No make/model required — W2 ranks segments, not specific vehicles.
- **`comparison`** — one of `body_type` (default) or `fuel_type` (EV vs ICE
  vs optional Hybrid). Or `both` to run two parallel passes.
- **`prior_period_offset`** — months back for the prior-period anchor.
  Default = `profile.analyst.benchmark_period_months` (default 3 months);
  overridable. For v1.0.0 maps to the canonical `90d` token.
- **State** — optional; default from `profile.analyst.tracked_states` (single
  value → pass; multi → prompt the user once for which state or "national";
  empty → national rollup, omit `state`).

## Pre-check halts

| Trigger | Halt |
|---|---|
| `profile.location.country != "US"` | per `references/country-uk.md` |
| User-supplied `inventory_type=new` | Halt-and-redirect to W5 (segment trends are a used-vehicle workflow). |

## Parallelization (W2)

W2 is a single-wave workflow with sub-batching when needed.

### Wave A — body_type and/or fuel_type cross-period (parallel)

Call shape (each):

```
get_sold_summary:
  state=<state>     # omit when "national"
  inventory_type="Used"
  ranking_dimensions="body_type"     # OR "make,model" for fuel-cohort passes
  ranking_measure="average_sale_price"
  top_n=10
  limit=5000
  summary_by="state"                  # omit when state is omitted
  date_from=<period.date_from>
  date_to=<period.date_to>
  fuel_type_category=<EV|ICE|Hybrid>  # only set when running a fuel pass
```

Call inventory by `comparison`:

- `comparison="body_type"` (2 calls): current + prior body_type cross-period.
- `comparison="fuel_type"` (4 calls): EV current + EV prior + ICE current + ICE prior.
- `comparison="fuel_type"` + Hybrid requested (6 calls): adds Hybrid current + Hybrid prior.
- `comparison="both"` (6 calls): body cross-period (2) + EV cross-period (2) + ICE cross-period (2).
- `comparison="both"` + Hybrid (8 calls): adds Hybrid cross-period.

### Sub-batching rule

Upstream rate limit = 5 concurrent. When the total exceeds 5, split into
sub-batches of ≤5 per agent message and fire sub-batches sequentially.

| Total calls | Sub-batch plan |
|---|---|
| 2-5 | 1 sub-batch |
| 6 | 2 sub-batches: (3, 3) |
| 8 | 2 sub-batches: (4, 4) |

Wait for all `tool_result` messages in each sub-batch before issuing the
next. Log DQ event (g) when sub-batching occurred.

Date windows come from `compute_period_windows.py --periods current,90d`
(or `current,<benchmark_period_months>mo` when the canonical-token version
is available; v1.0.0 caps at `90d`).

## Pipeline

```
parse_sold_summary.py × N        # one per call, via stdin pipe

# Body-type cross-period
echo '{"current": {...}, "prior": {...}, "dimension": "body_type"}' \
  | python scripts/segment_compare.py
  > body.json

# Fuel-type cross-period (one block per fuel category)
echo '{"current": {...}, "prior": {...}, "dimension": "fuel_type_category"}' \
  | python scripts/segment_compare.py
  > fuel.json

# Investment-signal aggregation per segment
echo '{"workflow": "w2",
       "segments": [
         {"key": "SUV", "price_change_pct": ..., "classification": "..."},
         ...
       ],
       "dimension": "body_type"}' \
  | python scripts/aggregate_signals.py
  > signal-body.json

render_depreciation_table.py --mode segment --input body.json --currency '$'
render_depreciation_table.py --mode segment --input fuel.json --currency '$'
```

## Render

Per `assets/output-template.md` W2 column. Headline phrasing:

```
Across <STATE | "the national market"> over the last <N> months, the
strongest-retention segment is <top.key> (<+pct>%) — <BULLISH for tickers
heavy in <top.key>>; the weakest is <bottom.key> (<-pct>%) — <BEARISH/CAUTION
for tickers heavy in <bottom.key>>.
```

When the EV / ICE pass ran, append a second sentence:

```
EV vs ICE: EV moved <ev_pct>% vs ICE <ice_pct>% — EV depreciating <ratio>×
<faster|slower> than ICE.
```

When EV depreciation is ≥1.5× ICE depreciation, surface as a Key Signal:

> *"⚠ EV portfolio risk: EVs depreciating <ratio>× faster than ICE; consider
> EV-specific residual curves rather than blended auto residuals. BEARISH
> read on TSLA / RIVN / LCID and on legacy OEMs' EV portfolios (F / GM /
> HYMTF / STLA EVs)."*

(Per the dealer-side `outcomes.md` and the analyst plugin's
`ev-transition-monitor` framing.)

## Per-segment ticker overlay

Map per-segment findings to tickers via these conventions (additive to
`references/ticker-mapping.md` make-level lookups):

| Body_type | Tickers most exposed |
|---|---|
| Pickup | F, GM, STLA |
| Sedan | TM, HMC, HYMTF |
| SUV | TM, HMC, F, GM, STLA (cross-OEM) |
| Coupe | varies — render the underlying make-level breakdown |
| Hatchback | HYMTF, VWAGY |

For fuel cohorts the mapping is direct: EV → TSLA, RIVN, LCID + legacy
OEM EV portfolios; ICE → all legacy OEMs.

## DQ event log discipline (W2)

- (a) MCP errors recovered.
- (e) Body-type missing-in-prior or missing-in-current — surface from `segment_compare.missing_in_*` arrays.
- (f) Hybrid pass skipped because user did not request it; `benchmark_period_months` defaulted because user did not specify.
- (g) Sub-batch split — log the (N, M) sub-batch sizes when total > 5.
