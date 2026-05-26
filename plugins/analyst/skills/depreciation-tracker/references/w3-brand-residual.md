---
name: w3-brand-residual
description: W3 — Brand Residual Ranking. Per-make retention % over a fixed 6-month window + 4-tier classification + tier-jump detection + per-ticker rollup. Single-wave (3 parallel `get_sold_summary` calls).
type: reference
---

# W3 — Brand Residual Ranking

Triggers: "which brands hold value best", "rank OEMs by residual strength",
"brand retention ranking", "Toyota vs Honda retention", "which automakers
are losing the most value".

## Required inputs

- **State** — optional; default from `profile.analyst.tracked_states`. Empty → national rollup.
- **`comparison_window`** — fixed at 6 months for W3 (residual is a 6-month concept by industry convention; ignored if the user requests other windows — fall back and emit DQ event (f)).
- **`top_n_brands`** — default 25.

## Pre-check halts

| Trigger | Halt |
|---|---|
| `profile.location.country != "US"` | per `references/country-uk.md` |
| User-supplied `inventory_type=new` | *"Brand Residual is a used-vehicle workflow — residual value is the post-depreciation worth of a vehicle; new vehicles haven't reached residual yet. The W3 output's T1 (BULLISH) / T4 (BEARISH) tier verdicts are used-vehicle semantics. For new-vehicle pricing parity by brand, run W5 (`/msrp-parity`) — the symmetric New-only workflow."* |

## Parallelization (W3)

Single-wave workflow; 3 parallel `get_sold_summary` calls (under the
5-concurrent ceiling).

### Wave A — current prices + prior prices + current volumes (parallel)

```
1. get_sold_summary  (current avg prices, ranked):
     state=<state>            # omit for national
     inventory_type="Used"
     ranking_dimensions="make"
     ranking_measure="average_sale_price"
     ranking_order="desc"
     top_n=25, limit=5000
     summary_by="state"        # omit when state is omitted
     date_from=<periods["current"].date_from>
     date_to=<periods["current"].date_to>

2. Same as 1 but date_from/to = periods["6mo"].{date_from, date_to}

3. get_sold_summary  (current volume, ranked):
     state=<state>            # omit for national
     inventory_type="Used"
     ranking_dimensions="make"
     ranking_measure="sold_count"
     ranking_order="desc"
     top_n=25, limit=5000
     summary_by="state"        # omit when state is omitted
     date_from=<periods["current"].date_from>
     date_to=<periods["current"].date_to>
```

Date windows come from `compute_period_windows.py --periods current,6mo`.

## Pipeline

```
parse_sold_summary.py × 3        # stdin pipe per call

echo '{"current": {...}, "prior": {...}, "volumes": {...}}' \
  | python scripts/brand_retention.py
  > brand.json

# Per-make investment-signal aggregation
echo '{"workflow": "w3",
       "makes": [
         {"make": "Toyota", "retention_pct": ..., "tier": "T1"},
         ...
       ]}' \
  | python scripts/aggregate_signals.py
  > signal.json

render_depreciation_table.py --mode brand --input brand.json --currency '$'
```

## Render

Per `assets/output-template.md` W3 column. Headline:

```
T1 (BULLISH) leaders: <top-3 makes [tickers]>. Largest tier downgrade:
<make> [<TICKER>] dropped T<X> → T<Y> (<change_pct>% retention shift) —
<BEARISH | CAUTION> for the ticker. <count> tracked-cohort brands in T1;
<count> in T4.
```

Tier-jump detection: a brand's current-period tier is determined by W3's
fixed 6-month retention. A "tier change" event compares the brand's tier
this run vs a session-cached prior tier from a recent W3 run (if any). For
v1.0.0 the session cache is not persisted across invocations; tier-jump
detection compares the *retention pct vs the 6-month-prior retention* not
across W3 runs. The Headline cites the largest absolute retention change
between paired periods.

When the user's `tracked_tickers` cohort is supplied, the Comparison Context
renders the cohort's T1 / T2 / T3 / T4 distribution alongside the full
ranking.

## DQ event log discipline (W3)

- (a) MCP errors recovered.
- (d) Ticker mapping miss for any make in the ranking.
- (e) Brands present in current but not prior (or vice versa) — emit count.
- (f) `comparison_window` defaulted to 6 months (always for v1.0.0 — fixed).
