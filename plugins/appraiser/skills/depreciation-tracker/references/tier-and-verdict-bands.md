# Tier & Verdict Bands

The single source of truth for every threshold rendered by depreciation-tracker.
When a renderer needs to classify a number into a band, it reads the band
definition here. Module-level constants in the scripts mirror these values
verbatim — do not drift between this doc and the constants.

Audience reads are framed for the appraiser sub-personas: **trade-in
appraisers** (dealership desk), **insurance adjusters** (claim valuation,
total-loss settlement), **estate / probate appraisers**, and **fleet
managers** (portfolio revaluation).

## W1 — Acceleration Verdict (5-band)

Anchored on the **most-recent monthly depreciation rate** (rate between the
two newest priced periods, expressed as percent per month — positive means
price went down).

| Band | Range | Appraiser read |
|---|---|---|
| Strong Retention | rate < 0.3% (or appreciation; rate < 0) | Book values are tracking transaction reality; no trend adjustment needed against the source book. |
| Stable | 0.3% ≤ rate < 0.6% | Standard depreciation; no incremental adjustment beyond the book's published per-month assumption. |
| Slight Decline | 0.6% ≤ rate < 1.0% | Watch — apply a 1–2 month look-back trend on the book number if the deal is more than 30 days old. |
| Moderate Depreciation | 1.0% ≤ rate < 1.5% | Apply an ~12-18%/yr trend discount against book value when the appraisal is more than 60 days from book publication. |
| Accelerated Loss | rate ≥ 1.5% | Apply a ≥18%/yr trend discount against book values. For insurance claims, the prior-30-day transaction window is more defensible than book; cite three or more comps from `parse_sold_summary` directly. |

**Rationale.** 0.6%/month is the threshold the existing skill's
`references/outcomes.md` calls "depreciation accelerating beyond 2% monthly"
— flipped to its monthly equivalent (~0.5%, rounded to 0.6 for headroom).
1.5%/month maps to NADA's segment-tier "accelerating" flag. The 0.3%/month
threshold for Strong Retention is the canonical "value-leader" band per
NADA segment reports.

Constants live in `scripts/depreciation_curve.py:VERDICT_BANDS`.

## W3 — Brand Retention Tiers (4-tier)

Anchored on **retention %** = current_avg_sale_price / prior_avg_sale_price
× 100. Comparison window: 6 months back per W3 default (or user override).

| Tier | Range | Appraiser read |
|---|---|---|
| T1 | retention_pct ≥ 98% | Value-retention leaders. Apply the book's depreciation curve verbatim — no per-brand trend adjustment beyond it. |
| T2 | 95% ≤ retention_pct < 98% | Sturdy. Standard book-adjusted appraisal; no per-brand discount. |
| T3 | 90% ≤ retention_pct < 95% | Watch list. Apply a 1–2% trend discount against book for appraisals more than 60 days from book publication. |
| T4 | retention_pct < 90% | Concentration risk for fleet revaluation. For trade-in: drop bid 2–4% from book to absorb continued slide; for insurance total-loss: anchor on last-30-days comps rather than book. |

**Rationale.** Mirrors the band boundaries used by the broader skill family
(competitive-pricer, vehicle-appraiser, depreciation-tracker). Codified
here so the skill, scripts, and tests all read the same numbers.

Constants live in `scripts/brand_retention.py:TIER_THRESHOLDS`.

## W2 — Segment Classifier (4-band)

Anchored on **price_change_pct** = (current - prior) / prior × 100 across
the W2 cross-period pair (default: prior period = 3 months back).

| Class | Range | Appraiser read |
|---|---|---|
| appreciating | price_change_pct ≥ +1.0% | Adjust book values UP by the segment's appreciation rate when the source book is more than 30 days old. |
| stable | -1.0% < price_change_pct < +1.0% | No segment-level trend adjustment. |
| soft | -3.0% < price_change_pct ≤ -1.0% | Apply a 2–4% downward trend discount against book for vehicles in the segment. |
| accelerating_dep | price_change_pct ≤ -3.0% | Apply a ≥5% downward trend discount against book; for insurance claims, the last-30-days comp set is more defensible than book. |

**Rationale.** ±1% maps to NADA's "stable" call. -3% is NADA's "accelerating
depreciation" flag. The "soft" middle band is new — older skill variants
collapsed it into "accelerating depreciation" which obscures the
moderate-vs-severe distinction.

Constants live in `scripts/segment_compare.py:SEGMENT_THRESHOLDS`.

## W4 — Geographic Classifier (3-band)

Anchored on **price index** = state_avg / national_avg × 100. Index = 100 is
exactly national average.

| Class | Range | Appraiser read |
|---|---|---|
| premium | price_index > 105 | Multi-state insurance claim: cite the destination-state index for replacement-cost calculations rather than national book. |
| average | 95 ≤ price_index ≤ 105 | National book is defensible without geographic adjustment. |
| discount | price_index < 95 | Trade-in appraisals defending against a customer's higher-state-print expectation: cite the source-state index. Insurance claims in this state: the national book may overstate replacement cost. |

**Rationale.** ±5% from national matches the industry-standard geographic
band for residual reporting.

Constants live in `scripts/geo_variance.py`:
`GEO_PREMIUM_THRESHOLD=105.0`, `GEO_DISCOUNT_THRESHOLD=95.0`.

## W5 — MSRP Parity Status (3-band) + Direction (5-band)

Status — anchored on `price_over_msrp_percentage` for the current period:

| Status | Range | Appraiser read |
|---|---|---|
| above | pct > 0 (above sticker) | New-vehicle replacement-cost on a recent insurance claim: trans-price above MSRP — use the transaction percentile as floor, not book MSRP. |
| at | -1.0 ≤ pct ≤ 0 | Balanced market; book MSRP is defensible. |
| below | pct < -1.0 (below sticker — incentives active) | Replacement-cost should reflect prevailing transaction price, not MSRP; cite the incentive level in the appraisal notes. |

Direction — anchored on `change_pct` = current_pct - prior_pct:

| Direction | Trigger | Appraiser read |
|---|---|---|
| flipped_below | prior_pct ≥ 0 AND current_pct < 0 | Incentive program just started biting; replacement-cost trend is now downward — call out in the appraisal notes for any new-vehicle claim. |
| flipped_above | prior_pct ≤ 0 AND current_pct > 0 | Supply constraint just emerged; replacement-cost trend is now upward. |
| deepening | both same sign AND \|current\| > \|prior\| | Trend is accelerating in the current direction. |
| narrowing | both same sign AND \|current\| < \|prior\| | Trend is reverting toward parity. |
| stable | \|change_pct\| < 0.5% | No incremental adjustment. |

**Rationale.** Status `at` band uses ±0 to -1.0 because zero-or-positive
should always read as "demand-driven", and below -1% is the typical floor
for "incentive-driven" per industry residual reporting. Direction labels
are load-bearing for new-vehicle insurance replacement-cost defenses.

Constants live in `scripts/msrp_parity.py`:
`PARITY_AT_LOWER=-1.0`, `DIRECTION_STABLE_THRESHOLD=0.5`.

## Curve-shape classifier (W1, secondary)

Anchored on the ratio of recent monthly rate to longest-window monthly rate.

| Shape | Trigger | Appraiser read |
|---|---|---|
| accelerating | recent_rate / longest_rate > 1.25 | Recent deceleration of book values has surpassed the long-run rate; trust last-30-days comps over book for fresh appraisals. |
| stabilizing | recent_rate / longest_rate < 0.75 | Depreciation is decelerating; the book's long-run assumption may now over-discount. |
| linear | in between | Long-run trend is intact; book is defensible. |

Constants live in `scripts/depreciation_curve.py`:
`CURVE_ACCEL_RATIO=1.25`, `CURVE_STABILIZE_RATIO=0.75`.

## Render rule for boundary values

When a value sits within 0.05 of any band edge, the renderer outputs the
percent with **two decimals** to make the band assignment visually
unambiguous. Default body precision is 1 decimal.

## Drift discipline

These thresholds are the **single source** for the skill's classification
language. If any threshold is changed:

1. Update this file.
2. Update the corresponding module constant in the named script.
3. Update the matching test in `tests/test_*.py`.
4. Re-run the test suite — all three must agree before merge.
