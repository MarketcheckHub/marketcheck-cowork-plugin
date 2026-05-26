---
name: signal-aggregation
description: Banding tables for per-metric signal classification (BULLISH/NEUTRAL/CAUTION/BEARISH) and the deterministic rule that reduces N per-metric bands to a single headline verdict (BULLISH/BEARISH/NEUTRAL/MIXED).
type: reference
---

# Signal aggregation

Codifies the original `dealer-group-health-monitor`'s Signal Logic table (which produced ambiguities AMB-01 and AMB-04 in the original `SKILL_ANALYSIS.md`). Every numeric value flowing into the headline verdict passes through `aggregate_signals.py`, which uses the rules below.

## Per-metric banding table

Each metric has 4 bands. Direction (higher-better vs. lower-better) is per-metric; the table makes it explicit.

| Metric | Direction | BULLISH | NEUTRAL | CAUTION | BEARISH |
|---|---|---|---|---|---|
| Volume MoM       | higher better | x > +3%  | -1% ≤ x ≤ +3% | -3% ≤ x < -1% | x < -3% |
| ASP MoM          | higher better | x > +1%  | -1% ≤ x ≤ +1% | -3% ≤ x < -1% | x < -3% |
| DOM Change       | lower  better | x < -2 days | -2 ≤ x ≤ +2 | +2 < x ≤ +5 | x > +5 days |
| Days Supply (used) | lower better | x < 35 | 35 ≤ x ≤ 55 | 55 < x ≤ 75 | x > 75 |
| Days Supply (new)  | lower better | x < 50 | 50 ≤ x ≤ 80 | 80 < x ≤ 100 | x > 100 |
| Efficiency MoM   | higher better | x > +5%  | -2% ≤ x ≤ +5% | -5% ≤ x < -2% | x < -5% |

## Boundary rule (resolves AMB-04)

NEUTRAL is the **closed interval** `[LOW, HIGH]` — both endpoints inclusive. The adjacent BULLISH or CAUTION band is open on the side that touches NEUTRAL (strict `<` or `>`).

For lower-better metrics, CAUTION is closed on the side that touches BEARISH and open on the side that touches NEUTRAL.

This eliminates the "value falls into both bands" ambiguity in the original Signal Logic table where `-3% to -1%` and `-1% to +3%` both nominally contain `-1%`.

### Worked endpoint examples (all tested)

- Volume MoM = `+3.0%` → NEUTRAL (NEUTRAL upper inclusive); `+3.001%` → BULLISH.
- Volume MoM = `-1.0%` → NEUTRAL (NEUTRAL lower inclusive); `-1.001%` → CAUTION.
- Volume MoM = `-3.0%` → CAUTION (CAUTION lower inclusive); `-3.001%` → BEARISH.
- Days Supply (used) = `35.0` → NEUTRAL; `34.99` → BULLISH; `55.0` → NEUTRAL; `55.01` → CAUTION; `75.0` → CAUTION; `75.01` → BEARISH.
- DOM Change = `-2.0` → NEUTRAL; `-2.01` → BULLISH; `+2.0` → NEUTRAL; `+2.01` → CAUTION; `+5.0` → CAUTION; `+5.01` → BEARISH.

## Per-band scores

Each band maps to a numeric score for the reduction step:

- **BULLISH** = +2
- **NEUTRAL** = 0
- **CAUTION** = -1
- **BEARISH** = -2

The asymmetry (BULLISH +2 but BEARISH -2; CAUTION -1) reflects that CAUTION is a *warning*, not a *bearish* signal — it's a caveat to monitor, not a sell trigger. Two CAUTION metrics shouldn't equal one BEARISH metric in the headline reduction.

## Headline-verdict reduction (resolves AMB-01)

The reducer takes per-metric bands → one of `BULLISH | BEARISH | NEUTRAL | MIXED`.

**Algorithm:**

1. Skip metrics with `null` values (e.g., `volume_pct = null` because prior_total was zero, or `days_supply_new = null` for Used-only groups). Every other metric contributes a band → score.
2. Compute `mean(scores)` across the contributing metrics.
3. Count `n_bullish` and `n_bearish`. CAUTION and NEUTRAL do not count toward either.
4. Decide in this order (first match wins):
   - `n_bullish > 0 AND n_bearish > 0` → **MIXED**
   - `mean ≥ +1.0 AND n_bearish == 0` → **BULLISH**
   - `mean ≤ -1.0 AND n_bullish == 0` → **BEARISH**
   - else → **NEUTRAL**

**Edge:** if no metrics contribute (all values null — e.g., a brand-new dealer group with no prior data), emit `verdict: null` with `reason: "no_scoreable_signals"`. The renderer drops the verdict line and surfaces a Data Quality event instead of fabricating a value.

## Worked examples

### Strong bull (BULLISH)
| Metric | Value | Band | Score |
|---|---|---|---|
| Volume MoM | +4.8% | BULLISH | +2 |
| ASP MoM    | +2.1% | BULLISH | +2 |
| DOM Change | -3.0 days | BULLISH | +2 |
| Days Supply (used) | 32 | BULLISH | +2 |
| Days Supply (new) | null (Used-only group) | — | — |
| Efficiency MoM | +6.5% | BULLISH | +2 |

mean = 2.0; n_bullish = 5; n_bearish = 0 → **BULLISH**.

### Cohort-best on volume but margin pressure (MIXED)
| Metric | Value | Band | Score |
|---|---|---|---|
| Volume MoM | +5.0% | BULLISH | +2 |
| ASP MoM    | -3.5% | BEARISH | -2 |
| DOM Change | +1.0 days | NEUTRAL | 0 |
| Days Supply (used) | 48 | NEUTRAL | 0 |
| Days Supply (new) | 75 | NEUTRAL | 0 |
| Efficiency MoM | +1.0% | NEUTRAL | 0 |

mean = 0.0; n_bullish = 1; n_bearish = 1 → **MIXED** (rule 1 wins).

### Conservative middle (NEUTRAL)
| Metric | Value | Band | Score |
|---|---|---|---|
| Volume MoM | +1.5% | NEUTRAL | 0 |
| ASP MoM    | +0.3% | NEUTRAL | 0 |
| DOM Change | +0.5 days | NEUTRAL | 0 |
| Days Supply (used) | 40 | NEUTRAL | 0 |
| Days Supply (new) | null | — | — |
| Efficiency MoM | +6.0% | BULLISH | +2 |

mean = 0.4; n_bullish = 1; n_bearish = 0; rule 2 needs mean ≥ +1.0 → fails → **NEUTRAL**. (One BULLISH metric out of 5 is not enough to anchor a BULLISH headline.)

### Across-the-board decline (BEARISH)
| Metric | Value | Band | Score |
|---|---|---|---|
| Volume MoM | -4.5% | BEARISH | -2 |
| ASP MoM    | -3.5% | BEARISH | -2 |
| DOM Change | +6.0 days | BEARISH | -2 |
| Days Supply (used) | 80 | BEARISH | -2 |
| Days Supply (new) | null | — | — |
| Efficiency MoM | -7.0% | BEARISH | -2 |

mean = -2.0; n_bullish = 0; n_bearish = 5 → **BEARISH**.

### Watch-list flicker (NEUTRAL with cautions)
| Metric | Value | Band | Score |
|---|---|---|---|
| Volume MoM | +1.0% | NEUTRAL | 0 |
| ASP MoM    | -2.0% | CAUTION | -1 |
| DOM Change | +3.0 days | CAUTION | -1 |
| Days Supply (used) | 60 | CAUTION | -1 |
| Days Supply (new) | null | — | — |
| Efficiency MoM | -3.0% | CAUTION | -1 |

mean = -0.8; n_bullish = 0; n_bearish = 0; mean > -1.0 → **NEUTRAL** (with a rationale that flags the four CAUTIONs).

## Why the rule is conservative

Per skill-creator's "explain the why" principle: equity analysts read these signals with money on the line. A loose reducer that fired BULLISH on one strong metric would whipsaw — analysts would learn to ignore the headline. The threshold (`mean ≥ +1.0`) requires either:
- 3+ BULLISH metrics with no CAUTIONs, OR
- 2+ BULLISH plus enough NEUTRALs to keep the average above +1.0.

The MIXED rule (any BULLISH + any BEARISH → MIXED) captures the "good on volume, bad on margin" pattern that's the actual story for many real dealer-group earnings.
