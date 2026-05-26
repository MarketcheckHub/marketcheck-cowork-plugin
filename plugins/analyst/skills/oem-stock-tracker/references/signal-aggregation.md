---
name: signal-aggregation
description: Per-metric banding tables for the 7 underlying OEM metrics, the 2 composite-slot combiners (volume_momentum, pricing_power), and the deterministic reduction algorithm that produces a single headline verdict (BULLISH / BEARISH / NEUTRAL / MIXED). Implemented in scripts/aggregate_signals.py.
type: reference
---

# Signal aggregation

Codifies the OEM-specific banding (mirroring `dealer-group-health-monitor/references/signal-aggregation.md`'s discipline but with OEM thresholds). Every numeric value flowing into the headline verdict passes through `aggregate_signals.py`, which uses the rules below.

## Per-metric banding (7 underlying metrics)

Boundary rule: **NEUTRAL is the closed interval `[LOW, HIGH]`** — both endpoints inclusive. The adjacent BULLISH or CAUTION band is **open on the side that touches NEUTRAL** (strict `<` or `>`). CAUTION is closed on the BEARISH-touching side. This eliminates "value falls into both bands" ambiguity at exact threshold values.

| Metric | Direction | BULLISH | NEUTRAL | CAUTION | BEARISH |
|---|---|---|---|---|---|
| Volume MoM | higher better | x > +3% | -1% ≤ x ≤ +3% | -3% ≤ x < -1% | x < -3% |
| Volume 3-mo trend | higher better | x > +5% | -2% ≤ x ≤ +5% | -5% ≤ x < -2% | x < -5% |
| ASP MoM | higher better | x > +1% | -1% ≤ x ≤ +1% | -3% ≤ x < -1% | x < -3% |
| MSRP gap Δ (bps) | higher better | x > +50 | -50 ≤ x ≤ +50 | -150 ≤ x < -50 | x < -150 |
| Days Supply (new) | lower better | x < 50 | 50 ≤ x ≤ 80 | 80 < x ≤ 100 | x > 100 |
| Market share Δ (bps) | higher better | x > +30 | -30 ≤ x ≤ +30 | — | x < -30 |
| DOM Δ (absolute days) | lower better | x < -2 | -2 ≤ x ≤ +2 | +2 < x ≤ +5 | x > +5 |
| EV transition Δ (bps) | higher better | x > +50 | -50 ≤ x ≤ +50 | — | x < -50 |

**Market share and EV transition omit the CAUTION band intentionally** — these metrics swing more sharply (market share is a zero-sum game; EV transition is a directional thesis), and a CAUTION band would dilute the signal.

### Worked endpoint examples (all tested)

- Volume MoM = `+3.0%` → **NEUTRAL** (NEUTRAL upper inclusive); `+3.001%` → **BULLISH**.
- Volume MoM = `-1.0%` → **NEUTRAL** (NEUTRAL lower inclusive); `-1.001%` → **CAUTION**.
- Volume MoM = `-3.0%` → **CAUTION** (CAUTION lower inclusive); `-3.001%` → **BEARISH**.
- ASP MoM = `+1.0%` → **NEUTRAL**; `+1.001%` → **BULLISH**.
- MSRP gap Δ = `+50` bps → **NEUTRAL**; `+50.01` → **BULLISH**.
- Days Supply (new) = `50.0` → **NEUTRAL** (NEUTRAL lower inclusive); `49.99` → **BULLISH**.
- Days Supply (new) = `80.0` → **NEUTRAL**; `80.01` → **CAUTION**.
- Days Supply (new) = `100.0` → **CAUTION**; `100.01` → **BEARISH**.
- DOM Δ = `-2.0 days` → **NEUTRAL**; `-2.01` → **BULLISH**.
- DOM Δ = `+2.0` → **NEUTRAL**; `+2.01` → **CAUTION**.
- DOM Δ = `+5.0` → **CAUTION**; `+5.01` → **BEARISH**.
- Market share Δ = `+30 bps` → **NEUTRAL**; `+30.01` → **BULLISH**.
- Market share Δ = `-30 bps` → **NEUTRAL** (NEUTRAL lower-inclusive per closed-NEUTRAL convention); `-30.01 bps` → **BEARISH**.
- EV transition Δ = `+50 bps` → **NEUTRAL**; `+50.01` → **BULLISH**; `-50 bps` → **NEUTRAL** (lower-inclusive); `-50.01` → **BEARISH**.

## Per-band scores

Each band maps to a numeric score for the reduction step:

- **BULLISH** = +2
- **NEUTRAL** = 0
- **CAUTION** = −1
- **BEARISH** = −2

The asymmetry (BULLISH +2 vs BEARISH −2, CAUTION −1) reflects that CAUTION is a *warning*, not a *bearish* signal — a caveat to monitor, not a sell trigger. Two CAUTION metrics shouldn't equal one BEARISH metric in the headline reduction.

## Composite slot combiners (2 of the 6 slots)

The reducer operates over **6 composite slots**, not 7 metrics. Two slots combine pairs of underlying metrics:

### `volume_momentum` — combines `volume_mom` + `volume_trend`

| `mom_band` | `trend_band` | `mom_pct` | `trend_3mo_pct` | Composite |
|---|---|---|---|---|
| BULLISH | BULLISH | — | — | **BULLISH** |
| BEARISH | BEARISH | — | — | **BEARISH** |
| any positive-side | any negative-side | > 0 | < 0 | **CAUTION** (short-term bounce on long-term decline) |
| otherwise | | | | **NEUTRAL** |

**Rule:** BULLISH requires BOTH to be BULLISH; BEARISH requires BOTH to be BEARISH; CAUTION when the short-term sign disagrees with the long-term sign in the positive→negative direction; otherwise NEUTRAL.

### `pricing_power` — combines `asp` + `msrp_gap`

Three inputs are consulted: `asp.band`, `msrp_gap.band` (the delta direction), and `msrp_gap.current_pct` (the absolute position vs sticker).

| `asp.band` | `msrp_gap.current_pct` | `msrp_gap.band` | Composite |
|---|---|---|---|
| BULLISH | > 0 (above sticker) | — | **BULLISH** (ASP rising AND vehicles transacting above sticker) |
| BEARISH | < 0 (below sticker) | — | **BEARISH** (ASP falling AND deepening discounts below sticker) |
| NEUTRAL | — | CAUTION or BEARISH | **CAUTION** (ASP flat but margin pressure building) |
| otherwise | | | **NEUTRAL** |

**Rule:** BULLISH requires both ASP direction AND MSRP-current-position to align positively; BEARISH similarly aligned negatively; CAUTION when ASP is flat but the MSRP-delta direction is degrading; otherwise NEUTRAL.

### Other 4 slots — direct band passthrough

- `days_supply` = `band_days_supply(days_supply.current)`
- `market_share` = `band_market_share_delta(market_share.delta_bps)`
- `dom` = `band_dom_delta(dom.delta_days)`
- `ev_transition` = `band_ev_transition_delta(ev_transition.delta_bps)` (null when classification is pure_play OR when zero-EV legacy)

## Headline-verdict reduction algorithm

First-match-wins over the 6 composite slots:

1. Skip slots with `null` value (e.g., `ev_transition` is null for pure_play classifications, leaving 5 slots).
2. Compute `mean(scores)` across contributing slots.
3. Count `n_bullish` (slots banded BULLISH) and `n_bearish` (slots banded BEARISH). CAUTION and NEUTRAL do not count toward either.
4. Decide in this order:
   - `n_bullish > 0 AND n_bearish > 0` → **MIXED**
   - `mean ≥ +1.0 AND n_bearish == 0` → **BULLISH**
   - `mean ≤ -1.0 AND n_bullish == 0` → **BEARISH**
   - else → **NEUTRAL**

**Edge case:** if no slots contribute (all null — e.g., a brand-new ticker with no prior data) → `verdict: null` with `reason: "no_scoreable_signals"`. The renderer emits `INSUFFICIENT DATA: …` instead of fabricating a verdict.

## Worked examples

### Strong bull — BULLISH

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | MoM +4.8%, trend +6.5% | BULLISH | +2 |
| pricing_power | ASP +2.1%, MSRP gap current +1.5% | BULLISH | +2 |
| days_supply | 38 | BULLISH | +2 |
| market_share | +45 bps | BULLISH | +2 |
| dom | -4.0 days | BULLISH | +2 |
| ev_transition | +70 bps | BULLISH | +2 |

mean = +2.0; n_bullish = 6; n_bearish = 0 → **BULLISH**.

### Margin pressure (vol up, pricing down) — MIXED

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | MoM +5.0%, trend +6.0% | BULLISH | +2 |
| pricing_power | ASP -3.5%, MSRP gap current -3.0% | BEARISH | -2 |
| days_supply | 65 | NEUTRAL | 0 |
| market_share | +5 bps | NEUTRAL | 0 |
| dom | +1.0 day | NEUTRAL | 0 |
| ev_transition | +20 bps | NEUTRAL | 0 |

mean = 0.0; n_bullish = 1; n_bearish = 1 → **MIXED** (rule 3 wins).

### Conservative middle (one strong metric, rest stable) — NEUTRAL

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | MoM +1.5%, trend +2.0% | NEUTRAL | 0 |
| pricing_power | ASP +0.5%, MSRP gap flat | NEUTRAL | 0 |
| days_supply | 60 | NEUTRAL | 0 |
| market_share | +10 bps | NEUTRAL | 0 |
| dom | +0.5 days | NEUTRAL | 0 |
| ev_transition | +80 bps | BULLISH | +2 |

mean = +0.33; n_bullish = 1; n_bearish = 0; mean < +1.0 → fails rule 4 → **NEUTRAL**. (One BULLISH out of 6 is not enough to anchor a BULLISH headline.)

### Across-the-board decline — BEARISH

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | MoM -4.5%, trend -6.0% | BEARISH | -2 |
| pricing_power | ASP -3.5%, MSRP gap current -5.0% | BEARISH | -2 |
| days_supply | 105 | BEARISH | -2 |
| market_share | -45 bps | BEARISH | -2 |
| dom | +6.0 days | BEARISH | -2 |
| ev_transition | -60 bps | BEARISH | -2 |

mean = -2.0; n_bullish = 0; n_bearish = 6 → **BEARISH**.

### Watch-list flicker (4 CAUTIONs, no BULLISH/BEARISH) — NEUTRAL

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | MoM +1.0%, trend -1.5% | NEUTRAL | 0 |
| pricing_power | ASP -2.0%, MSRP gap current +0.5% (band CAUTION via msrp delta) | CAUTION | -1 |
| days_supply | 90 | CAUTION | -1 |
| market_share | -10 bps | NEUTRAL | 0 |
| dom | +3.5 days | CAUTION | -1 |
| ev_transition | +25 bps | NEUTRAL | 0 |

mean = -0.5; n_bullish = 0; n_bearish = 0; mean > -1.0 → **NEUTRAL** (with rationale flagging the 3 CAUTIONs).

### Pure-play with strong EV market position — BULLISH (5 slots, not 6)

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | MoM +8%, trend +12% | BULLISH | +2 |
| pricing_power | ASP +3%, MSRP gap current +2% | BULLISH | +2 |
| days_supply | 42 | BULLISH | +2 |
| market_share | +85 bps | BULLISH | +2 |
| dom | -5 days | BULLISH | +2 |
| ev_transition | **null** (pure_play) | — | — |

mean = +2.0 (over 5 contributing); n_bullish = 5; n_bearish = 0 → **BULLISH**.

## Why the rule is conservative

Equity analysts read these signals with money on the line. A loose reducer that fired BULLISH on one strong metric would whipsaw — analysts would learn to ignore the headline. The mean ≥ +1.0 threshold requires either:
- 3+ BULLISH slots with no CAUTIONs, OR
- 2+ BULLISH plus enough NEUTRALs to keep the average above +1.0.

The MIXED rule (any BULLISH + any BEARISH) captures the "good on volume, bad on margin" pattern that's the actual story for many real OEM earnings (e.g., F when truck volume is up but truck ASPs are softening).

## Per-make divergence rule

For multi-make tickers, `aggregate_signals.py` additionally flags makes whose volume signal diverges sharply from the ticker composite.

**Rule:** For each entry in `per_make_raw`, band the make's `mom_vol_pct` using the same Volume MoM banding table; compute `gap = |make_volume_score − ticker_composite_score|` where `ticker_composite_score = scores.volume_momentum.score`. If `gap ≥ 2`, emit the entry to `per_make_divergence[]`. Empty array when no divergence OR when `per_make_raw` is null (single-make ticker).

**Why volume only (v1):** Volume divergence is the most analyst-relevant signal — "Jeep collapse while Ram is fine" inside STLA is a more actionable observation than "Jeep ASP softer than Ram." Expanding to per-metric divergence is a v1.1 candidate.

DQ event (l) logged whenever `per_make_divergence` is non-empty.

## 3-month baseline columns are informational (not banded)

The W1 leading-indicators table exposes a "3-mo baseline" value for ASP, MSRP gap, DOM, EV transition, and market share (in addition to Volume which already has it). These values are for analyst interpretation only — they do **NOT** have bands and do **NOT** contribute to composite slots.

Volume's `trend_3mo_pct` (which IS banded as `volume_trend` inside the `volume_momentum` composite) remains the sole multi-month banded derivation. All other multi-month columns are reference context — the verdict still derives from MoM bands (or, for Days Supply, the current absolute value).

**Why not band them?** Adding `asp_trend` / `dom_trend` / `msrp_trend` / `ev_trend` / `market_share_trend` slots would expand the reducer from 6 → 11 composite slots, shifting the BULLISH threshold from 3-of-6 BULLISH slots (mean ≥ +1.0 = 3 × 2 / 6) to 6-of-11 (= 6 × 2 / 11 = +1.09). This would silently drift the verdict math across the existing 92-test suite and require re-tuning every banding worked example.

**If future analysis warrants banded 3-mo trends for additional metrics**, the expansion lives here and in `aggregate_signals.py` — NOT in templates. v2 candidate.
