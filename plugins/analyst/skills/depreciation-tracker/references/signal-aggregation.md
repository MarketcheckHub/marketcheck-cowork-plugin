---
name: signal-aggregation
description: Banding tables for per-metric signal classification (BULLISH / NEUTRAL / CAUTION / BEARISH) and the deterministic rule that reduces N per-metric bands to a single headline verdict (BULLISH / BEARISH / NEUTRAL / CAUTION / MIXED). Source of truth for `scripts/aggregate_signals.py`.
type: reference
---

# Signal aggregation

The investment-signal layer of the skill. Every numeric metric flowing into
the headline verdict passes through `scripts/aggregate_signals.py`, which
uses the rules below.

The metrics come from the four workflow-specific stats engines —
`depreciation_curve.py` (W1), `segment_compare.py` (W2),
`brand_retention.py` (W3), and `msrp_parity.py` (W5) — and the verdict labels
those engines emit (`Strong Retention` / `Slight Decline` / `T1` /
`appreciating` / `above` / etc.) are translated *here* into the analyst's
4-band per-metric scheme + 5-band headline scheme.

## Per-metric banding tables

Each metric maps to one of `BULLISH | NEUTRAL | CAUTION | BEARISH`.
Direction (higher-better vs. lower-better) is per-metric; tables make it
explicit.

### W1 — `monthly_rate_pct` (lower better, units = % per month)

| Band | Range |
|---|---|
| BULLISH | `rate < 0.3%` (or appreciation — rate < 0) |
| NEUTRAL | `0.3% ≤ rate < 0.6%` |
| CAUTION | `0.6% ≤ rate < 1.5%` |
| BEARISH | `rate ≥ 1.5%` |

**Rationale.** Boundaries adopted from the dealer-side reference's W1
5-band verdict (`references/tier-and-verdict-bands.md` of that skill). The
analyst 4-band scheme collapses the reference's `Slight Decline` (0.6-1.0)
and `Moderate Depreciation` (1.0-1.5) into a single CAUTION because both
warrant the same investment-thesis action: *monitor, but no immediate
re-rating*. The BEARISH threshold (≥1.5%) is preserved verbatim — this is
the rate at which the reference's `Accelerated Loss` band kicks in and is
the empirical "material residual erosion" line per the dealer-side
`outcomes.md`.

### W3 — `retention_pct` (higher better, units = %)

Anchored on retention % = current_avg_sale_price / prior_avg_sale_price ×
100. Comparison window: 6 months back (fixed for W3).

| Band | Range | Tier |
|---|---|---|
| BULLISH | retention_pct ≥ 98 | T1 |
| NEUTRAL | 95 ≤ retention_pct < 98 | T2 |
| CAUTION | 90 ≤ retention_pct < 95 | T3 |
| BEARISH | retention_pct < 90 | T4 |

**Rationale.** Tier thresholds preserved verbatim from the dealer-side
reference. The analyst-side mapping (T1 → BULLISH, T4 → BEARISH) is the
existing target's mapping (validated against the analyst plugin's onboarding
prose). T2 NEUTRAL and T3 CAUTION are the natural 4-band split.

### W2 — `price_change_pct` (higher better, units = %)

Anchored on price_change_pct = (current_avg - prior_avg) / prior_avg × 100
across the cross-period pair (default prior = 3 months back).

| Band | Range | Classification |
|---|---|---|
| BULLISH | price_change_pct ≥ +1.0 | appreciating |
| NEUTRAL | -1.0 < price_change_pct < +1.0 | stable |
| CAUTION | -3.0 < price_change_pct ≤ -1.0 | soft |
| BEARISH | price_change_pct ≤ -3.0 | accelerating_dep |

**Rationale.** Thresholds preserved from the dealer-side
`segment_compare.py`'s `SEGMENT_THRESHOLDS`. The mapping classification →
band is a one-to-one renaming.

### W5 — parity status × direction composite

W5 has two underlying labels: `status` (above / at / below) and `direction`
(flipped_above / flipped_below / deepening / narrowing / stable). The
investment-signal band reads both:

| Band | Trigger |
|---|---|
| BULLISH | `status == "above"` AND `direction != "flipped_below"` |
| NEUTRAL | `status == "at"` |
| CAUTION | `status == "below"` AND `direction ∈ {narrowing, stable, null}` |
| BEARISH | `status == "below"` AND `direction ∈ {deepening, flipped_below}` |

**Rationale.** Above-MSRP with non-flipping direction is the unambiguous
pricing-power BULLISH signal. At-MSRP is balanced (NEUTRAL). Below-MSRP
splits by direction: deepening discounts and fresh flips below sticker are
BEARISH (incentive bite, margin pressure intensifying), while narrowing or
stable below-MSRP is CAUTION (still incentive-driven but not worsening).

### Boundary rule (resolves AMB-04 from the dealer-side analysis)

NEUTRAL is the **closed interval** `[LOW, HIGH]` — both endpoints inclusive.
The adjacent BULLISH or CAUTION band is open on the side that touches
NEUTRAL (strict `<` or `>`). For lower-better metrics, CAUTION is closed
on the side that touches BEARISH and open on the side that touches NEUTRAL.

This eliminates "value falls into both bands" ambiguity at endpoints.

#### Worked endpoint examples (all checked)

- `monthly_rate_pct = 0.3` → NEUTRAL (NEUTRAL lower inclusive); `0.299` → BULLISH.
- `monthly_rate_pct = 0.6` → CAUTION (CAUTION lower inclusive); `0.599` → NEUTRAL.
- `monthly_rate_pct = 1.5` → BEARISH (BEARISH lower inclusive); `1.499` → CAUTION.
- `retention_pct = 98.0` → BULLISH (T1 lower inclusive); `97.99` → NEUTRAL (T2).
- `retention_pct = 95.0` → NEUTRAL (T2 lower inclusive); `94.99` → CAUTION (T3).
- `retention_pct = 90.0` → CAUTION (T3 lower inclusive); `89.99` → BEARISH (T4).
- `price_change_pct = +1.0` → BULLISH (BULLISH lower inclusive); `+0.999` → NEUTRAL.
- `price_change_pct = -1.0` → CAUTION (CAUTION upper inclusive); `-0.999` → NEUTRAL.
- `price_change_pct = -3.0` → BEARISH (BEARISH upper inclusive); `-2.999` → CAUTION.

## Per-band scores

Each band maps to a numeric score for the reduction step:

- **BULLISH** = +2
- **NEUTRAL** = 0
- **CAUTION** = -1
- **BEARISH** = -2

Asymmetry (BULLISH +2 but BEARISH -2; CAUTION -1) reflects that CAUTION is
a *watch* signal, not a *sell* trigger — it is a caveat to monitor, not an
investment-thesis flip. Two CAUTIONs should not equal one BEARISH in the
headline reduction.

## Headline-verdict reduction (resolves AMB-01 from the dealer-side analysis)

The reducer takes per-metric bands → one of `BULLISH | BEARISH | NEUTRAL |
CAUTION | MIXED`. (CAUTION is added to the headline scheme — beyond the
dealer-group-health-monitor's 4-headline-band scheme — because
depreciation workflows surface non-bullish-non-bearish *watch* signals more
often than dealer-group operational metrics do.)

**Algorithm:**

1. Skip metrics / rows with `null` values.
2. Compute `mean(scores)` across contributing entries.
3. Count `n_bullish` and `n_bearish`. CAUTION and NEUTRAL do not count.
4. Count `n_caution`.
5. Decide in this order (first match wins):
   - `n_bullish > 0 AND n_bearish > 0` → **MIXED**
   - `mean ≥ +1.0 AND n_bearish == 0`  → **BULLISH**
   - `mean ≤ -1.0 AND n_bullish == 0`  → **BEARISH**
   - `n_caution > 0 AND n_bullish == 0 AND n_bearish == 0` → **CAUTION**
   - Else → **NEUTRAL**
6. If no entries contribute → `verdict: null` with
   `reason: "no_scoreable_signals"`. The renderer drops the verdict line
   and surfaces a Data Quality event instead of fabricating a value.

## Worked examples

### W1 BULLISH (strong retention)
| Metric | Value | Band | Score |
|---|---|---|---|
| monthly_rate_pct | 0.15 | BULLISH | +2 |
| annualized_rate_pct | 1.8 | BULLISH | +2 (proportional, same band as monthly) |
| retention_pct_prior | 99.2 | BULLISH | +2 |

mean = +2.0; n_bullish = 3; n_bearish = 0 → **BULLISH**.

### W3 MIXED (cohort split)
Per-make rows reduce: one make BULLISH (T1), two NEUTRAL (T2), one BEARISH (T4).

n_bullish = 1; n_bearish = 1 → **MIXED** (rule 1 wins).

### W2 CAUTION (segment softening, no BEARISH)
Per-segment classifications: SUV NEUTRAL (+0.4%), Sedan CAUTION (-1.8%), Pickup CAUTION (-2.1%), Coupe NEUTRAL (+0.1%).

n_bullish = 0; n_bearish = 0; n_caution = 2; mean = -0.5 → **CAUTION**.

### W5 BEARISH (incentive bite)
Per-row: 6 rows BELOW with `deepening`/`flipped_below` direction = BEARISH; 2 NEUTRAL.

n_bullish = 0; n_bearish = 6; mean = -1.5 → **BEARISH**.

## Per-ticker rollup (Ticker Impact Summary)

After the per-metric / per-row reduction yields the headline verdict,
the renderer produces a **Ticker Impact Summary** by:

1. Looking up each affected `make` in `references/ticker-mapping.md`.
2. Grouping per-row bands by ticker (a ticker may map to multiple makes:
   `STLA → Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati`).
3. Running the reducer **again** within each ticker's group to produce a
   per-ticker verdict.
4. Rendering a row per ticker: `<TICKER> · <verdict> · <one-sentence rationale>`.

Makes with no matching ticker render as `[no tracked ticker]` and contribute
to a separate "Other makes" row — emit DQ event (d).

## Drift discipline

These thresholds are the **single source** for the skill's
classification language. If any threshold is changed:

1. Update this file.
2. Update the corresponding band function in `scripts/aggregate_signals.py`.
3. Update `references/tier-and-verdict-bands.md` (the dealer-side mirror).
4. Update any future test in `tests/`.
