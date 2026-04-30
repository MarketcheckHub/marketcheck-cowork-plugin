# Tier & Verdict Bands

The single source of truth for every threshold rendered by depreciation-tracker.
When a renderer needs to classify a number into a band, it reads the band
definition here. Module-level constants in the scripts mirror these values
verbatim — do not drift between this doc and the constants.

Adopted from the Q2=C decision in the approved plan: tiers in W3
(brand-rank), 5-band acceleration verdict in W1/W2/W5 Headlines.

## W1 — Acceleration Verdict (5-band)

Anchored on the **most-recent monthly depreciation rate** (rate between the
two newest priced periods, expressed as percent per month — positive means
price went down).

| Band | Range | Lender / OEM read |
|---|---|---|
| Strong Retention | rate < 0.3% (or appreciation; rate < 0) | Residual forecasts can hold; no incremental risk. |
| Stable | 0.3% ≤ rate < 0.6% | Tracking long-run norms; standard residual policy. |
| Slight Decline | 0.6% ≤ rate < 1.0% | Watch — review if it persists 2+ periods. |
| Moderate Depreciation | 1.0% ≤ rate < 1.5% | Tighten advance rates on this segment. |
| Accelerated Loss | rate ≥ 1.5% | Materially elevated risk; surface as alert. |

**Rationale.** 0.6%/month is the threshold the existing skill's
`outcomes.md` line 5 calls "depreciation accelerating beyond 2% monthly" —
flipped to its monthly equivalent (~0.5%, rounded to 0.6 for headroom).
1.5%/month maps to the prior skill's "ACCELERATING" flag. The 0.3%/month
threshold for Strong Retention is the canonical "value-leader" band per
NADA segment reports.

Constants live in `scripts/depreciation_curve.py:VERDICT_BANDS`.

## W3 — Brand Retention Tiers (4-tier)

Anchored on **retention %** = current_avg_sale_price / prior_avg_sale_price
× 100. Comparison window: 6 months back per W3 default (or user override).

| Tier | Range | Read |
|---|---|---|
| T1 | retention_pct ≥ 98% | Value-retention leaders; advance-rate-friendly. |
| T2 | 95% ≤ retention_pct < 98% | Sturdy; normal residual policy. |
| T3 | 90% ≤ retention_pct < 95% | Watch list. |
| T4 | retention_pct < 90% | Concentration-risk candidate. |

**Rationale.** Mirrors the existing skill's W3 tiers verbatim
(`skills/depreciation-tracker/SKILL.md` line 110 — Tier 1 / 2 / 3 / 4 with
the exact same boundaries). Codified here so the skill, scripts, and tests
all read the same numbers.

Constants live in `scripts/brand_retention.py:TIER_THRESHOLDS`.

## W2 — Segment Classifier (4-band)

Anchored on **price_change_pct** = (current - prior) / prior × 100 across
the W2 cross-period pair (default: prior period = 3 months back).

| Class | Range |
|---|---|
| appreciating | price_change_pct ≥ +1.0% |
| stable | -1.0% < price_change_pct < +1.0% |
| soft | -3.0% < price_change_pct ≤ -1.0% |
| accelerating_dep | price_change_pct ≤ -3.0% |

**Rationale.** ±1% maps to the existing skill's "stable" call. -3% is the
existing skill's "accelerating depreciation" flag. The "soft" middle band
is new — the existing skill collapsed it into "accelerating depreciation"
which obscures the moderate-vs-severe distinction.

Constants live in `scripts/segment_compare.py:SEGMENT_THRESHOLDS`.

## W4 — Geographic Classifier (3-band)

Anchored on **price index** = state_avg / national_avg × 100. Index = 100 is
exactly national average.

| Class | Range |
|---|---|
| premium | price_index > 105 |
| average | 95 ≤ price_index ≤ 105 |
| discount | price_index < 95 |

**Rationale.** ±5% from national matches the existing skill's W4 thresholds
(`skills/depreciation-tracker/SKILL.md` lines 127-130).

Constants live in `scripts/geo_variance.py`:
`GEO_PREMIUM_THRESHOLD=105.0`, `GEO_DISCOUNT_THRESHOLD=95.0`.

## W5 — MSRP Parity Status (3-band) + Direction (5-band)

Status — anchored on `price_over_msrp_percentage` for the current period:

| Status | Range |
|---|---|
| above | pct > 0 (above sticker) |
| at | -1.0 ≤ pct ≤ 0 |
| below | pct < -1.0 (below sticker — incentives active) |

Direction — anchored on `change_pct` = current_pct - prior_pct:

| Direction | Trigger |
|---|---|
| flipped_below | prior_pct ≥ 0 AND current_pct < 0 |
| flipped_above | prior_pct ≤ 0 AND current_pct > 0 |
| deepening | both same sign AND \|current\| > \|prior\| |
| narrowing | both same sign AND \|current\| < \|prior\| |
| stable | \|change_pct\| < 0.5% |

**Rationale.** Status `at` band uses ±0 to -1.0 because zero-or-positive
should always read as "demand-driven", and below -1% is the typical floor
for "incentive-driven" per the existing skill. Direction labels are
load-bearing for OEM incentive-effectiveness reads (the existing skill's W5
step 4 surfaces "flipped" and "deepening").

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

## Render rule for boundary values

When a value sits within 0.05 of any band edge, the renderer outputs the
percent with **two decimals** to make the band assignment visually
unambiguous. (Same convention as competitive-pricer-updated for sold-anchor
verdict edges.) Default body precision is 1 decimal.

## Drift discipline

These thresholds are the **single source** for the skill's classification
language. If any threshold is changed:

1. Update this file.
2. Update the corresponding module constant in the named script.
3. Update the matching test in `tests/test_*.py`.
4. Re-run the test suite — all three must agree before merge.
