---
name: w5-msrp-parity
description: W5 — MSRP Parity Tracker. New-vehicle `price_over_msrp_percentage` rollup + above / at / below status + cross-period direction labels + per-ticker rollup. Single-wave (3 parallel `get_sold_summary` calls). Always `inventory_type="New"`.
type: reference
---

# W5 — MSRP Parity Tracker

Triggers: "which new cars are selling over sticker", "are markups coming
down", "incentive activity", "MSRP parity tracker", "above sticker pricing
power", "OEM pricing-power signal", "below MSRP flips".

## Required inputs

- **`inventory_type="New"`** — fixed; W5 is about new-vehicle MSRP parity.
  If the user supplies `Used`, halt-and-redirect: *"MSRP Parity tracking is
  for new-vehicle pricing. Run W1 (depreciation curve) for used-vehicle
  trajectory."*
- **State** — optional; default from `profile.analyst.tracked_states`. Empty → national rollup.
- **`comparison_window`** — months back for the prior-period anchor. Default = `profile.analyst.benchmark_period_months` (default 3 months); overridable. For v1.0.0 maps to the canonical `90d` token.
- **`top_n_models`** — default 30.

## Pre-check halts

| Trigger | Halt |
|---|---|
| `profile.location.country != "US"` | per `references/country-uk.md` |
| User-supplied `inventory_type=used` | Halt-and-redirect to W1. |

## Parallelization (W5)

Single-wave workflow; 3 parallel `get_sold_summary` calls (under the
5-concurrent ceiling).

### Wave A — current parity + prior parity + current volume (parallel)

```
1. get_sold_summary  (current parity, ranked):
     inventory_type="New"
     state=<state>            # omit for national
     ranking_dimensions="make,model"
     ranking_measure="price_over_msrp_percentage"
     ranking_order="desc"
     top_n=30, limit=5000
     summary_by="state"        # omit when state is omitted
     date_from=<periods["current"].date_from>
     date_to=<periods["current"].date_to>

2. Same as 1 but date_from/to = periods["90d"].{date_from, date_to}
   (or other canonical period matching `comparison_window`)

3. get_sold_summary  (current volume, ranked):
     inventory_type="New"
     state=<state>            # omit for national
     ranking_dimensions="make,model"
     ranking_measure="sold_count"
     ranking_order="desc"
     top_n=30, limit=5000
     summary_by="state"        # omit when state is omitted
     date_from=<periods["current"].date_from>
     date_to=<periods["current"].date_to>
```

Date windows come from `compute_period_windows.py --periods current,90d`
(or the matching canonical token for the chosen `comparison_window`).

## Pipeline

```
parse_sold_summary.py × 3        # stdin pipe per call

echo '{"current": {...}, "prior": {...}, "volumes": {...}}' \
  | python scripts/msrp_parity.py
  > parity.json

# Per-row investment-signal aggregation
echo '{"workflow": "w5",
       "rows": [
         {"make_model": "Honda Civic", "make": "Honda",
          "current_pct": ..., "status": "above", "direction": "narrowing"},
         ...
       ]}' \
  | python scripts/aggregate_signals.py
  > signal.json

render_depreciation_table.py --mode parity --input parity.json --currency '$'
```

## Render

Per `assets/output-template.md` W5 column. Headline:

```
<above_count> models above sticker (BULLISH pricing power), <below_count>
below (BEARISH incentive pressure). Largest current premium: <model>
[<TICKER>] (<+X.X>% over MSRP). Newly flipped below MSRP this period:
<list> [<tickers>].
```

When no flips, the second sentence becomes: `No models flipped above ↔
below MSRP this period.`

Surface deepening discounts as Key Signals:

> *"<model> [<TICKER>] deepening discount: now selling at <-X.X>% vs
> <-Y.Y>% prior period — incentive program biting or oversupply signal.
> BEARISH for the ticker's near-term gross margin."*

## Per-ticker rollup

Group rows by ticker (via `references/ticker-mapping.md`), then run the
headline-verdict reducer over the per-row bands within each ticker. For
multi-make tickers (STLA, GM, HMC, etc.), the rollup is determinative —
not the sum of "most common band" but the headline reducer's output.

The Ticker Impact Summary lists one row per ticker:

```
F     · <BULLISH | NEUTRAL | CAUTION | BEARISH | MIXED> · <rationale>
GM    · ...
STLA  · ...
...
```

## DQ event log discipline (W5)

- (a) MCP errors recovered.
- (d) Ticker mapping miss for any (make, model) in the ranking.
- (e) Models present in current but not prior (or vice versa) — emit count.
- (f) `comparison_window` defaulted to 3 months because user did not specify; non-canonical period requested and quantised to nearest token.
