---
name: signal-aggregation
description: Verdict-band rules that translate per-make / per-segment / per-dealer-group share-change bps + volume-change % into BULLISH / BEARISH / NEUTRAL / CAUTION per-ticker investment signals. Authoritative classification grid consumed by `scripts/aggregate_signals.py`.
type: reference
---

# Signal aggregation — verdict bands

Authoritative classification grid for the BULLISH / BEARISH / NEUTRAL /
CAUTION verdict bands this skill emits. The same grid lives in
`scripts/aggregate_signals.py:_classify_make` — when this file changes,
update the script in the same edit and re-run `tests/test_aggregate_signals.py`.

## Per-component classification

A "component" is one row in the per-make / per-segment / per-dealer-group
breakdown. For each component, two inputs drive the verdict:
- `share_change_bps` — current_share_pct − prior_share_pct, scaled to bps.
- `volume_change_pct` — (current_sold − prior_sold) / prior_sold × 100.

When `prior_share_pct` is None (no prior-period data) or `prior_sold` is
zero, the component is classified `NEUTRAL` with reason
`insufficient_data_for_verdict` regardless of the bps value.

| Condition (evaluated in order; first match wins)                                       | Verdict | Reason token                          |
|---|---|---|
| `share_change_bps >= +50` (regardless of volume)                                       | BULLISH | `share_change_bps>=+50`                |
| `share_change_bps <= -50` (regardless of volume)                                       | BEARISH | `share_change_bps<=-50`                |
| `share_change_bps >= +30` AND `volume_change_pct >= 0`                                 | BULLISH | `share_change_bps>=+30 and volume up`  |
| `share_change_bps <= -30` AND `volume_change_pct <= 0`                                 | BEARISH | `share_change_bps<=-30 and volume down`|
| `share_change_bps > +10` AND `volume_change_pct <= -5%`                                | CAUTION | `share_gain_with_volume_drop`          |
| `volume_change_pct <= -10%` (regardless of share direction)                            | CAUTION | `volume_change_pct<=-10%`              |
| `abs(share_change_bps) <= 30` AND `abs(volume_change_pct) <= 5%`                       | NEUTRAL | `within +/-30 bps and +/-5%`           |
| any other combination                                                                  | NEUTRAL | `default_band`                          |

### Investment-thesis interpretation

- **BULLISH** — the brand is gaining share AND not contracting volume.
  Both signals point in the same direction. Translates to revenue
  trajectory upside for the OEM ticker; positive read on the next
  earnings print.
- **BEARISH** — share is leaking AND volume is contracting. Both signals
  align downward. Negative revenue read; structural concerns when
  sustained over two periods.
- **CAUTION** — directional ambiguity. The two most common shapes:
  1. Share gaining but volume dropping (a contracting market the brand
     is over-indexed in — share gain is illusory because the cohort is
     shrinking faster than competitors).
  2. Volume dropping severely (>10%) regardless of share — even if share
     held, the absolute revenue line is moving the wrong way.
- **NEUTRAL** — within the noise band (|bps| ≤ 30 AND |vol| ≤ 5%); the
  print is in line with prior-period trend.

## Per-ticker rollup (multi-make tickers)

Single-make tickers (TSLA, RIVN, LCID, MBGAF) inherit their lone
component's verdict directly. Multi-make tickers (F, GM, TM, HMC, STLA,
HYMTF, NSANY, BMWYY, VWAGY) need a rollup rule because their per-make
verdicts can diverge.

Rollup is **sold_count-weighted strict majority**:

```
For each ticker T with components [m1, m2, ..., mN]:
  total_vol = sum(m.current_sold_count for m in T.components)
  bucket    = { B: sum(m.current_sold_count) for m if m.verdict==B }
  if any bucket B has vol > total_vol * 0.5:
    headline_verdict = B
  else:
    headline_verdict = CAUTION   # mixed-make divergence is itself a signal
```

### Why CAUTION on no-strict-majority

A multi-make ticker whose internal makes disagree (Chevy BULLISH +
Cadillac BEARISH + GMC NEUTRAL) is itself a meaningful read: the analyst
cannot take a clean directional view on the whole ticker. The headline
"CAUTION — mixed-make divergence" prompts the analyst to drill into the
per-make breakdown rather than acting on the ticker headline alone.

This is intentional asymmetry against the per-component grid: at the
component level NEUTRAL is the default; at the ticker level CAUTION is
the default-on-divergence, because divergence at the rollup level is more
informational than at the leaf level.

## Dealer-group-mode special case

W3 (Dealer Group Benchmarking) is current-period only — there is no
prior-period offset and therefore no `share_change_bps` or
`volume_change_pct` for the per-dealer-group components. The classifier
returns `NEUTRAL` with reason `insufficient_data_for_verdict` for every
dealer-group row.

The W3 Investment Thesis block instead conveys signal via:
- **Volume rank** — top-3 dealer-groups by `sold_count` for the period.
- **Efficiency rank** — top-3 by `efficiency_score = sold_count / avg_dom`.
- **DOM differential** — `top_volume.avg_dom − top_efficiency.avg_dom`
  expressed as days; large differentials signal operational moats.

These three reads stay current-period — converting them to BULLISH /
BEARISH requires period comparison, which is W3 future-work, not v1.0.0
scope.

## Regional-mode special case (W5)

W5 (Regional Exposure Heatmap) is per-make/-model and per-state. The
verdict for the ticker is driven by **state-concentration risk**:

| Condition                                          | Verdict | Reason token                       |
|---|---|---|
| top-3 states account for ≥ 50% of national volume  | CAUTION | `top3_states_concentration>=50%`   |
| top-3 states account for < 50% (diversified)       | NEUTRAL | `diversified_top3<50%`             |
| `total_volume == 0` (thin/zero data)               | NEUTRAL | `no_volume`                         |

This is concentration-risk-only — W5 does not opine on the ticker's
overall directional thesis. For that, the analyst should run W1
(Brand Share) on the same ticker.

## EV-mode special case (W4)

For the per-make EV brand share breakdown, the verdict band uses a
**proxy bps** derived from each brand's EV penetration rate against a
5% baseline:

```
share_bps_proxy = (brand_ev_pct - 5.0) * 100
```

A brand with 12% EV penetration produces `share_bps_proxy = +700` →
BULLISH. A brand with 1% EV penetration → `share_bps_proxy = -400` →
BEARISH. The 5% baseline is the rough US new-vehicle EV penetration
midpoint as of 2026. This is a v1.0.0 simplification — when reliable
prior-period EV share is available for every ticker, replace with the
direct bps delta and remove this proxy.

## Headline rollup outputs

The script emits a `headline_rollup` block at the end of every output:

```
"headline_rollup": {
  "top_bullish":    ["<ticker>", "<ticker>", "<ticker>"],
  "top_bearish":    ["<ticker>", "<ticker>", "<ticker>"],
  "tracked_signals": [{"ticker": "<T>", "verdict": "<BAND>",
                       "share_change_bps": <bps>}, ...] | null
}
```

`tracked_signals` is populated when `--tracked-tickers <list>` is passed
(typically from `analyst.tracked_tickers` profile field). The renderer
surfaces this as the **Ticker Impact Summary** block in the report; when
the user's tracked-tickers cohort has any non-NEUTRAL verdict, the
headline phrase calls out that ticker by name.

## Threshold rationale (calibration notes)

- **±30 bps** is the "meaningful share move" threshold per industry
  practice (a 30 bps quarterly shift ≈ 4,500-5,000 annual units at
  national volume — material to OEM revenue at the segment level).
- **±50 bps** is the "strong directional read" threshold; share moves of
  this magnitude on a one-month base usually persist for at least one
  more period.
- **±5% volume** is the "non-noise" envelope; smaller moves are
  attributable to month-end vs mid-month delivery timing, dealer-level
  reporting lag, and seasonal mix.
- **±10% volume** is the structural-shift threshold for CAUTION
  irrespective of share direction.

These thresholds are calibrated to monthly cadence. When the skill is
run with `benchmark_period_months >= 3` (quarterly comparison), the same
thresholds still apply — quarterly aggregates are smoother and the same
bps move is more meaningful, not less. Re-calibration is a follow-up if
analyst feedback shows the thresholds are too tight or too loose for the
quarterly cadence.
