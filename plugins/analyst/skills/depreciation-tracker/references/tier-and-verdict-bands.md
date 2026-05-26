---
name: tier-and-verdict-bands
description: Single source of truth for every numeric threshold across all four workflows. Mirrors the dealer-side reference's same-named file, with the analyst-side translation to BULLISH / NEUTRAL / CAUTION / BEARISH layered in via `references/signal-aggregation.md`.
type: reference
---

# Tier & Verdict Bands

The single source of truth for every threshold rendered by depreciation-tracker.
When a renderer needs to classify a number into a band, it reads the band
definition here. Module-level constants in the scripts mirror these values
verbatim — do not drift between this doc and the constants.

This file owns the **raw classifier labels** emitted by the stats engines
(`Strong Retention`, `appreciating`, `T1`, `above`, `flipped_below`, etc.).
`references/signal-aggregation.md` owns the translation from those raw
labels into the analyst's investment-signal bands (BULLISH / NEUTRAL /
CAUTION / BEARISH).

## W1 — Acceleration Verdict (5-band, raw)

Anchored on the **most-recent monthly depreciation rate** (rate between the
two newest priced periods, expressed as percent per month — positive means
price went down).

| Band | Range | Maps to (per signal-aggregation.md) |
|---|---|---|
| Strong Retention | rate < 0.3% (or appreciation — rate < 0) | BULLISH |
| Stable | 0.3% ≤ rate < 0.6% | NEUTRAL |
| Slight Decline | 0.6% ≤ rate < 1.0% | CAUTION |
| Moderate Depreciation | 1.0% ≤ rate < 1.5% | CAUTION |
| Accelerated Loss | rate ≥ 1.5% | BEARISH |

**Rationale.** Boundaries preserved verbatim from the dealer-side reference.
The analyst 4-band investment-signal scheme collapses `Slight Decline` and
`Moderate Depreciation` into a single CAUTION because both warrant the same
investment-thesis action: *monitor, but no immediate re-rating*. The raw
5-band label is preserved in the curve table for context.

Constants live in `scripts/depreciation_curve.py:VERDICT_BANDS`.

## W3 — Brand Retention Tiers (4-tier)

Anchored on **retention %** = current_avg_sale_price / prior_avg_sale_price
× 100. Comparison window: 6 months back (fixed).

| Tier | Range | Maps to (per signal-aggregation.md) |
|---|---|---|
| T1 | retention_pct ≥ 98 | BULLISH |
| T2 | 95 ≤ retention_pct < 98 | NEUTRAL |
| T3 | 90 ≤ retention_pct < 95 | CAUTION |
| T4 | retention_pct < 90 | BEARISH |

**Rationale.** Mirrors the dealer-side reference's W3 tiers verbatim (and
matches the existing analyst-side target's tier boundaries). The
investment-signal mapping (T1 → BULLISH, T4 → BEARISH) is the existing
target's mapping.

Constants live in `scripts/brand_retention.py:TIER_THRESHOLDS`.

## W2 — Segment Classifier (4-band)

Anchored on **price_change_pct** = (current - prior) / prior × 100 across
the cross-period pair (default prior = 3 months back via `90d` token).

| Class | Range | Maps to |
|---|---|---|
| appreciating | price_change_pct ≥ +1.0% | BULLISH |
| stable | -1.0% < price_change_pct < +1.0% | NEUTRAL |
| soft | -3.0% < price_change_pct ≤ -1.0% | CAUTION |
| accelerating_dep | price_change_pct ≤ -3.0% | BEARISH |

**Rationale.** Thresholds preserved verbatim from dealer-side reference.

Constants live in `scripts/segment_compare.py:SEGMENT_THRESHOLDS`.

## W5 — MSRP Parity Status (3-band) + Direction (5-band)

Status — anchored on `price_over_msrp_percentage` for the current period:

| Status | Range |
|---|---|
| above | pct > 0 (above sticker) |
| at | -1.0 ≤ pct ≤ 0 |
| below | pct < -1.0 (below sticker — incentives active) |

Direction — anchored on `change_pct = current_pct - prior_pct`:

| Direction | Trigger |
|---|---|
| flipped_below | prior_pct ≥ 0 AND current_pct < 0 |
| flipped_above | prior_pct ≤ 0 AND current_pct > 0 |
| deepening | both same sign AND \|current\| > \|prior\| |
| narrowing | both same sign AND \|current\| < \|prior\| |
| stable | \|change_pct\| < 0.5% |

**Investment-signal mapping** (per `references/signal-aggregation.md`):

| status × direction | Band |
|---|---|
| above × any (except flipped_below) | BULLISH |
| at × any | NEUTRAL |
| below × {narrowing, stable, null} | CAUTION |
| below × {deepening, flipped_below} | BEARISH |
| above × flipped_below (rare; means just flipped *to* above and *back*) | BEARISH (treat as the worse of the two readings) |

**Rationale.** Status `at` band uses -1.0 to 0 because zero-or-positive
should always read as "demand-driven", and below -1% is the typical floor
for "incentive-driven" per the dealer-side reference. Direction labels are
load-bearing for the BEARISH / CAUTION split.

Constants live in `scripts/msrp_parity.py`:
`PARITY_AT_LOWER=-1.0`, `DIRECTION_STABLE_THRESHOLD=0.5`.

## Curve-shape classifier (W1, secondary)

Anchored on the ratio of recent monthly rate to longest-window monthly rate.

| Shape | Trigger |
|---|---|
| accelerating | recent_rate / longest_rate > 1.25 |
| stabilizing | recent_rate / longest_rate < 0.75 |
| linear | in between |

Constants live in `scripts/depreciation_curve.py`:
`CURVE_ACCEL_RATIO=1.25`, `CURVE_STABILIZE_RATIO=0.75`.

The curve shape is rendered as a secondary caveat in the Headline — it does
NOT contribute to the headline-verdict reduction. Useful for narrative:
"BULLISH on retention BUT curve is accelerating; watch the next print."

## Render rule for boundary values

When a value sits within 0.05 of any band edge, the renderer outputs the
percent with **two decimals** to make the band assignment visually
unambiguous. Default body precision is 1 decimal.

Example: `+0.32%/month` in the Headline when the raw rate is 0.323;
`+1.5%/month` (one decimal) when the rate is 1.7 (well clear of any edge).

## Drift discipline

These thresholds are the **single source** for the skill's classification
language. If any threshold is changed:

1. Update this file.
2. Update the corresponding module constant in the named script.
3. Update `references/signal-aggregation.md` if the BULLISH / NEUTRAL /
   CAUTION / BEARISH mapping shifts.
4. Update any future test in `tests/`.
5. Re-run the test suite — all must agree before merge.
