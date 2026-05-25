---
name: w1-curve
description: W1 — Make/Model Depreciation Curve. Multi-period sold-price trajectory, monthly rate, 4-band investment-signal verdict + curve-shape classifier. Single-wave (5 parallel `get_sold_summary` calls). Used-vehicle workflow; halts and redirects to W5 on a new-vehicle request.
type: reference
---

# W1 — Make/Model Depreciation Curve

Triggers: "depreciation curve for <make> <model>", "how fast is the RAV4
losing value", "value retention curve for Ford trucks", "residual signal
for a 2023 Tacoma".

## Required inputs

- **`make`** + **`model`** (both required). Halt-and-ask if either missing.
- **No `year`** — `get_sold_summary` does not accept it. The curve aggregates
  across all model years per `references/sold-summary-safety.md`.
  Output renders an explicit scope qualifier.
- **No subject VIN** required. W1 has no subject vehicle in the
  per-listing sense.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country != "US"` | per `references/country-uk.md` |
| User-supplied `inventory_type=new` | *"Depreciation Curve is a used-vehicle workflow — new vehicles haven't depreciated yet; their pricing reflects MSRP, incentives, and supply rather than value retention. The output template's BULLISH / BEARISH bands key off monthly used-price decline. For new-vehicle MSRP-parity analysis run W5 (`/msrp-parity <make> <model>`) — the symmetric New-only workflow that surfaces incentive-bite and pricing-power signals."* |
| `make` or `model` missing | halt-and-ask |

## Parallelization (W1)

W1 is a single-wave workflow; 5 parallel `get_sold_summary` calls — under
the 5-concurrent upstream rate-limit ceiling.

### Wave A — Per-period sold-summary fan-out (parallel — 5 calls)

Launched once profile + make/model are in hand. All five calls share no
cross-dependency.

`get_sold_summary` × 5 — one per period (`current`, `60d`, `90d`, `6mo`,
`1yr`). Each call is parameterized identically except for `date_from` /
`date_to`, which come from `scripts/compute_period_windows.py` (run ONCE at
workflow entry):

```
get_sold_summary:
  make=<resolved_make>, model=<resolved_model>
  inventory_type="Used"
  state=<profile.location.state | profile.analyst.tracked_states[0]>  # omit for national
  summary_by="state"                                                   # omit when state is omitted
  ranking_dimensions="make,model"
  ranking_measure="average_sale_price"
  top_n=5
  limit=5000
  date_from=<period.date_from>
  date_to=<period.date_to>
```

**Do NOT pass `dealer_type`** (silent data suppression — see
`references/sold-summary-safety.md`).

Each parsed via `parse_sold_summary.py --aggregate-multi-period` (stdin).

### No Wave B

The dealer-side reference has a conditional Wave B for rep-VIN MSRP decode
to anchor retention vs MSRP. **The analyst port drops this path** for
v1.0.0:
- `anchor_mode="prior_period"` is hard-coded; W1 emits prior-period
  retention only.
- Sidesteps the chronic ~150KB `decode_vin_neovin` truncation envelope.
- Prior-period retention is still meaningful as an investment signal
  (BULLISH when retention is high vs the prior period; BEARISH when it
  drops sharply).

### Wall-clock budget (W1)

- Wave A ≈ 12-15s (5 parallel calls, slowest call sets the wall clock).
- Total ≈ 12-15s.

## Pipeline

```
parse_sold_summary.py × 5 --aggregate-multi-period     # via stdin pipe per call

# Build the per-period feed for the curve engine
periods_input = compose from compute_period_windows.json + each
                parse_sold_summary.multi_period_aggregate.overall block
                (one entry per period: label, months_offset_from_today,
                 month, weighted_avg_sale_price, total_sold_count)

echo '{"periods": [...], "msrp": null, "anchor_mode": "prior_period"}' \
  | python scripts/depreciation_curve.py
  > curve.json

# Investment signal — pass per-period metrics to aggregate_signals.py
echo '{"workflow": "w1",
       "metrics": {
         "monthly_rate_pct":    <recent_monthly_rate_pct>,
         "annualized_rate_pct": <annualized_recent>,
         "retention_pct_prior": <most_recent_period.retention_pct_prior>
       }}' \
  | python scripts/aggregate_signals.py
  > signal.json

render_depreciation_table.py --mode curve --input curve.json --currency '$'
```

(`curve.json` and `signal.json` are illustrative names; the agent passes the
output through stdin / stdout pipes without persisting unless the MCP
runtime forced a `--file <path>` save.)

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| Make/model missing | user input incomplete | Halt at pre-check; ask for both. |
| Non-US profile | country != US | Halt per `references/country-uk.md`. |
| User asks new-vehicle | explicit | Halt-and-redirect to W5. |
| `make_model_not_found` on any period | parser error_type | Retry once with facet-discovered casing per `references/facet-discovery.md`. If still failing, omit the period from the curve + emit DQ event (a). |
| `network_422` on any period | parse error | Verify dates from `compute_period_windows.py` are month-aligned; if so, omit period + emit DQ event (a). |
| `network_5xx` on any period | parse error | Omit period + emit DQ event (a). Do NOT retry — 429 amplification risk. |
| Truncation envelope on sold-summary | rare | `--file` recovery per SKILL.md §Truncation handling; emit DQ event (b). |
| Fewer than 2 priced periods after recovery | catastrophic data loss | `depreciation_curve.py` emits `ok=false / error_type=insufficient_periods`; render Headline as `"Insufficient sold data to build a depreciation curve for <make> <model>"` + Data Quality Notes; do NOT render the curve table. |
| All periods returned null `weighted_avg_sale_price` | zero sold counts | Same as above. |

## Render

Per `assets/output-template.md` W1 column. Headline phrasing (always prior-period anchor in v1.0.0):

```
<make> <model> [<TICKER or "[no tracked ticker]">] sold-summary average
dropped from $<oldest_avg> to $<newest_avg> over <months_span> months
(<recent_monthly_rate>%/month) — <BULLISH | BEARISH | NEUTRAL | CAUTION>.
```

When `verdict` from `depreciation_curve.py` is `null` (insufficient data),
the Headline becomes:

```
Insufficient sold data to build a depreciation curve for <make> <model>
in the <period_set> window — <n_priced>/5 periods returned priced rows.
```

The raw 5-band curve verdict (`Strong Retention` / etc.) is rendered in the
curve table's verdict cell as documented context; the analyst BULLISH /
BEARISH / NEUTRAL / CAUTION verdict from `aggregate_signals.py` is rendered
in the Headline and Ticker Impact Summary.

## DQ event log discipline (W1)

- (a) MCP errors / non-200 — sold-summary period failure.
- (a1) Facet-discovery retries when sold-summary returned `make_model_not_found`.
- (b) Truncation envelope unwraps via `--file`.
- (d) Ticker mapping miss for the make.
- (e) Anchor-mode fallback to prior_period because MSRP path is intentionally disabled in v1.0.0; emit on every W1 invocation as a documentation footnote.
- (f) Workflow branch skipped — N/A for W1 (no optional branches in this port).
- (g) Sub-batch split — N/A for W1 (5 calls = ceiling exactly).
