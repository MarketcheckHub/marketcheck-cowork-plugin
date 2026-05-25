---
name: signal-aggregation
description: Per-metric banding tables for the 8 underlying earnings-preview metrics, the volume_momentum composite combiner (QoQ + YoY), and the deterministic 4-tier reduction algorithm that produces a single headline verdict (BULLISH / BEARISH / NEUTRAL / MIXED + null). Implemented in scripts/aggregate_signals.py.
type: reference
---

# Signal aggregation

Codifies the earnings-preview banding (mirroring `oem-stock-tracker/references/signal-aggregation.md`'s discipline but tuned for **quarterly** cadence and the 8-metric earnings panel). Every numeric value flowing into the headline verdict passes through `aggregate_signals.py`, which uses the rules below.

## Per-metric banding (8 underlying metrics)

Boundary rule: **NEUTRAL is the closed interval `[LOW, HIGH]`** — both endpoints inclusive. The adjacent BULLISH or CAUTION band is **open on the side that touches NEUTRAL** (strict `<` or `>`). CAUTION is closed on the BEARISH-touching side. This eliminates "value falls into both bands" ambiguity at exact threshold values.

| Metric | Direction | BULLISH | NEUTRAL | CAUTION | BEARISH |
|---|---|---|---|---|---|
| Volume QoQ % | higher better | x > +7% | -3% ≤ x ≤ +7% | -7% ≤ x < -3% | x < -7% |
| Volume YoY % | higher better | x > +5% | -2% ≤ x ≤ +5% | -5% ≤ x < -2% | x < -5% |
| ASP QoQ % | higher better | x > +2% | -1% ≤ x ≤ +2% | -3% ≤ x < -1% | x < -3% |
| MSRP gap Δ (bps) | higher better | x > +90 | -90 ≤ x ≤ +90 | -200 ≤ x < -90 | x < -200 |
| Days Supply (used) | lower better | x < 35 | 35 ≤ x ≤ 55 | 55 < x ≤ 75 | x > 75 |
| Days Supply (new) | lower better | x < 50 | 50 ≤ x ≤ 80 | 80 < x ≤ 100 | x > 100 |
| DOM Δ (absolute days) | lower better | x < -5 | -5 ≤ x ≤ +5 | +5 < x ≤ +10 | x > +10 |
| EV share Δ (bps) | higher better | x > +100 | -50 ≤ x ≤ +100 | — | x < -50 |
| Mix Δ (pp) | higher better | x > +1.0 | -0.5 ≤ x ≤ +1.0 | -1.5 ≤ x < -0.5 | x < -1.5 |

**EV share omits the CAUTION band intentionally** — EV signal swings sharply (directional thesis), and a CAUTION band would dilute it. A degrading EV mix crosses straight from NEUTRAL into BEARISH at -50 bps.

**Volume is two rows, one composite slot.** Volume QoQ and Volume YoY are banded separately above, then fed into the `volume_momentum` combiner (see below). The two rows are NOT individually reduced into the headline verdict — only the composite slot is.

**Days Supply is two slots, not one.** Used and New ship as independent composite slots because the underlying inventory dynamics differ — Used DS reflects sourcing/wholesale pressure; New DS reflects OEM allocation. A ticker with `entity_type=dealer_group` may have both populated or only one (per `inventory-type-classification.md`). Each populated slot contributes independently.

### Worked endpoint examples (all tested in `test_aggregate_signals.py`)

- Volume QoQ = `+7.0%` → **NEUTRAL** (NEUTRAL upper inclusive); `+7.001%` → **BULLISH**.
- Volume QoQ = `-3.0%` → **NEUTRAL** (NEUTRAL lower inclusive); `-3.001%` → **CAUTION**.
- Volume QoQ = `-7.0%` → **CAUTION** (CAUTION lower inclusive); `-7.001%` → **BEARISH**.
- Volume YoY = `+5.0%` → **NEUTRAL**; `+5.001%` → **BULLISH**.
- Volume YoY = `-2.0%` → **NEUTRAL**; `-2.001%` → **CAUTION**.
- Volume YoY = `-5.0%` → **CAUTION**; `-5.001%` → **BEARISH**.
- ASP QoQ = `+2.0%` → **NEUTRAL**; `+2.001%` → **BULLISH**; `-1.0%` → **NEUTRAL**; `-1.001%` → **CAUTION**; `-3.0%` → **CAUTION**; `-3.001%` → **BEARISH**.
- MSRP gap Δ = `+90` bps → **NEUTRAL**; `+90.01` → **BULLISH**; `-90` → **NEUTRAL**; `-90.01` → **CAUTION**; `-200` → **CAUTION**; `-200.01` → **BEARISH**.
- Days Supply (used) = `35.0` → **NEUTRAL** (lower inclusive); `34.99` → **BULLISH**; `55.0` → **NEUTRAL**; `55.01` → **CAUTION**; `75.0` → **CAUTION**; `75.01` → **BEARISH**.
- Days Supply (new) = `50.0` → **NEUTRAL**; `49.99` → **BULLISH**; `80.0` → **NEUTRAL**; `80.01` → **CAUTION**; `100.0` → **CAUTION**; `100.01` → **BEARISH**.
- DOM Δ = `-5.0` days → **NEUTRAL**; `-5.01` → **BULLISH**; `+5.0` → **NEUTRAL**; `+5.01` → **CAUTION**; `+10.0` → **CAUTION**; `+10.01` → **BEARISH**.
- EV share Δ = `+100` bps → **NEUTRAL**; `+100.01` → **BULLISH**; `-50` → **NEUTRAL** (lower inclusive); `-50.01` → **BEARISH** (no CAUTION band).
- Mix Δ = `+1.0` pp → **NEUTRAL**; `+1.001` → **BULLISH**; `-0.5` → **NEUTRAL**; `-0.501` → **CAUTION**; `-1.5` → **CAUTION**; `-1.501` → **BEARISH**.

## Per-band scores

Each band maps to a numeric score for the reduction step:

- **BULLISH** = +2
- **NEUTRAL** = 0
- **CAUTION** = −1
- **BEARISH** = −2

The asymmetry (BULLISH +2 vs BEARISH −2, CAUTION −1) reflects that CAUTION is a *warning*, not a *bearish* signal — a caveat to monitor, not a sell trigger. Two CAUTION metrics shouldn't equal one BEARISH metric in the headline reduction.

## Composite slots (8 total)

The reducer operates over **up to 8 composite slots**. Exactly one slot is a combiner; the other seven are direct passthrough from the per-metric bands.

### `volume_momentum` — combines `volume_qoq` + `volume_yoy`

| `qoq_band` | `yoy_band` | `qoq_pct` | `yoy_pct` | Composite |
|---|---|---|---|---|
| BULLISH | BULLISH | — | — | **BULLISH** |
| BEARISH | BEARISH | — | — | **BEARISH** |
| any | any | > 0 | < 0 | **CAUTION** (short-term bounce on long-term decline) |
| any | any | < 0 | > 0 | **CAUTION** (short-term softness with long-term tailwind) |
| otherwise | | | | **NEUTRAL** |

**Rule:** BULLISH requires BOTH QoQ and YoY to be BULLISH; BEARISH requires BOTH to be BEARISH; CAUTION when the QoQ sign and YoY sign disagree; otherwise NEUTRAL.

**Degradation when one input is null.** When the year-ago quarter has no usable data (DQ event `(m)` from `compute_earnings_signals.py` — typically a newly-listed ticker), the YoY input is null. In that case:

- YoY null + QoQ present → composite degrades to QoQ-only: `band = qoq_band`, `score = qoq_score`, `degraded_to: "qoq_only"` is set on the slot.
- QoQ null + YoY present (defensive — rare) → composite degrades to YoY-only with `degraded_to: "yoy_only"`.
- Both null → slot is null (does not contribute to the reducer).

The `degraded_to` field is surfaced in W1 rationale so analysts can see when momentum is being judged on a single look-back.

### Other 7 slots — direct passthrough

These slots have a single underlying metric, so the composite-slot band/score equals the per-metric band/score:

- `asp` = `band_asp_qoq(asp.qoq_pct)`
- `msrp_gap` = `band_msrp_gap_bps(msrp_gap.qoq_delta_bps)`
- `dom` = `band_dom_delta_days(dom.qoq_delta_days)`
- `days_supply_used` = `band_days_supply_used(days_supply_used.current)` — null when `days_supply_used` block is null (OEM tickers, New-only dealer groups)
- `days_supply_new` = `band_days_supply_new(days_supply_new.current)` — null when `days_supply_new` block is null (Used-only dealer groups like KMX)
- `ev_share` = `band_ev_share_bps(ev_share.qoq_delta_bps)` — null when classification is pure_play OR when the entity has zero EV volume in both compared quarters
- `mix` = `band_mix_pp(mix.qoq_delta_pp)` — null for OEM tickers (Mix is dealer-group only — New vs Used share inside the entity)

## Headline-verdict reduction algorithm

First-match-wins over the populated composite slots:

1. Skip slots with `null` score (e.g., `ev_share` is null for pure_play classifications; `days_supply_new` is null for KMX; `mix` is null for OEMs).
2. Compute `mean(scores)` across contributing slots.
3. Count `n_bullish` (slots banded BULLISH) and `n_bearish` (slots banded BEARISH). CAUTION and NEUTRAL do not count toward either.
4. Decide in this order:
   - `n_bullish > 0 AND n_bearish > 0` → **MIXED**
   - `mean ≥ +1.0 AND n_bearish == 0` → **BULLISH**
   - `mean ≤ -1.0 AND n_bullish == 0` → **BEARISH**
   - else → **NEUTRAL**

**Edge case:** if no slots contribute (all null — e.g., a brand-new ticker with no prior-quarter data, after `compute_earnings_signals.py` has already halted upstream) → `verdict: null` with `reason: "no_scoreable_signals"`. The renderer emits `INSUFFICIENT DATA: …` instead of fabricating a verdict.

## Worked examples

### Strong bull — BULLISH (OEM, pure_play)

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | QoQ +12%, YoY +18% | BULLISH | +2 |
| asp | QoQ +3.0% | BULLISH | +2 |
| msrp_gap | QoQ Δ +120 bps | BULLISH | +2 |
| dom | QoQ Δ -6 days | BULLISH | +2 |
| days_supply_new | 42 | BULLISH | +2 |
| days_supply_used | null (OEM) | — | — |
| ev_share | null (pure_play) | — | — |
| mix | null (OEM) | — | — |

mean = +2.0 (over 5 contributing); n_bullish = 5; n_bearish = 0 → **BULLISH**.

### Margin pressure (vol up, pricing down) — MIXED (legacy OEM)

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | QoQ +8%, YoY +6% | BULLISH | +2 |
| asp | QoQ -3.5% | BEARISH | -2 |
| msrp_gap | QoQ Δ -150 bps | CAUTION | -1 |
| dom | QoQ Δ +2 days | NEUTRAL | 0 |
| days_supply_new | 70 | NEUTRAL | 0 |
| days_supply_used | null (OEM) | — | — |
| ev_share | QoQ Δ +30 bps | NEUTRAL | 0 |
| mix | null (OEM) | — | — |

mean = -0.17; n_bullish = 1; n_bearish = 1 → **MIXED** (rule 1 wins; the BULLISH+BEARISH pair short-circuits the mean check).

### Conservative middle (one strong metric, rest stable) — NEUTRAL (dealer group, Both)

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | QoQ +2%, YoY +1% | NEUTRAL | 0 |
| asp | QoQ +0.5% | NEUTRAL | 0 |
| msrp_gap | QoQ Δ +20 bps | NEUTRAL | 0 |
| dom | QoQ Δ -1 day | NEUTRAL | 0 |
| days_supply_used | 32 | BULLISH | +2 |
| days_supply_new | 65 | NEUTRAL | 0 |
| ev_share | QoQ Δ +40 bps | NEUTRAL | 0 |
| mix | QoQ Δ +0.4 pp | NEUTRAL | 0 |

mean = +0.25; n_bullish = 1; n_bearish = 0; mean < +1.0 → fails rule 2 → **NEUTRAL**. (One BULLISH out of 8 is not enough to anchor a BULLISH headline.)

### Across-the-board decline — BEARISH (legacy OEM)

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | QoQ -9%, YoY -7% | BEARISH | -2 |
| asp | QoQ -4.0% | BEARISH | -2 |
| msrp_gap | QoQ Δ -250 bps | BEARISH | -2 |
| dom | QoQ Δ +12 days | BEARISH | -2 |
| days_supply_new | 110 | BEARISH | -2 |
| days_supply_used | null (OEM) | — | — |
| ev_share | QoQ Δ -80 bps | BEARISH | -2 |
| mix | null (OEM) | — | — |

mean = -2.0; n_bullish = 0; n_bearish = 6 → **BEARISH**.

### YoY-degraded BULLISH (newly-listed ticker) — BULLISH

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | QoQ +14%, YoY **null** (degraded_to: qoq_only) | BULLISH | +2 |
| asp | QoQ +3% | BULLISH | +2 |
| msrp_gap | QoQ Δ +100 bps | BULLISH | +2 |
| dom | QoQ Δ -7 days | BULLISH | +2 |
| days_supply_new | 45 | BULLISH | +2 |

mean = +2.0; n_bullish = 5; n_bearish = 0 → **BULLISH**, with rationale carrying `volume_momentum.degraded_to = "qoq_only"` so the analyst sees momentum was judged on QoQ alone.

### Watch-list flicker (3 CAUTIONs, no BULLISH/BEARISH) — NEUTRAL

| Slot | Value | Band | Score |
|---|---|---|---|
| volume_momentum | QoQ +5%, YoY -3% | CAUTION (QoQ+/YoY−) | -1 |
| asp | QoQ -1.5% | CAUTION | -1 |
| msrp_gap | QoQ Δ -120 bps | CAUTION | -1 |
| dom | QoQ Δ +3 days | NEUTRAL | 0 |
| days_supply_new | 78 | NEUTRAL | 0 |
| ev_share | QoQ Δ +50 bps | NEUTRAL | 0 |

mean = -0.5; n_bullish = 0; n_bearish = 0; mean > -1.0 → **NEUTRAL** (rationale flags the 3 CAUTIONs as watch-list items).

## Signal drivers — strongest / weakest

After the reducer fires, `aggregate_signals.py` selects the slot that most drove the verdict:

- **strongest** = slot with the highest score among contributing slots (ties broken by Python `max` on insertion order: volume_momentum > asp > msrp_gap > dom > days_supply_used > days_supply_new > ev_share > mix). Always populated when at least one slot contributes.
- **weakest** = slot with the lowest score IF that score is CAUTION or BEARISH. **When the weakest slot is NEUTRAL or BULLISH, `weakest` is null** (per Phase 6 finding C12 — the Bear Case template handles `weakest=null` by suppressing the "biggest drag" line). This prevents the renderer from labelling a NEUTRAL slot as "the weakest signal," which reads as a manufactured negative.

Both records carry `{slot, band, score, value}` for downstream templating.

## Why the rule is conservative

Equity analysts read these signals with money on the line. A loose reducer that fired BULLISH on one strong metric would whipsaw — analysts would learn to ignore the headline. The mean ≥ +1.0 threshold requires either:
- 3+ BULLISH slots with no CAUTIONs (over a 5-slot OEM ticker; 4+ over an 8-slot dealer-group ticker), OR
- 2+ BULLISH plus enough NEUTRALs to keep the average above +1.0.

The MIXED rule (any BULLISH + any BEARISH) captures the "good on volume, bad on margin" pattern that's the actual story for many real earnings (e.g., F when truck volume is up but truck ASPs are softening; CVNA when used-vehicle gross is recovering but DOM is creeping).

## Per-make divergence rule

For multi-make OEM tickers (STLA, GM, F, TM, HMC, HYMTF, etc.), `aggregate_signals.py` additionally flags makes whose volume signal diverges sharply from the ticker composite.

**Rule:** For each entry in `per_make_raw`, band the make's `qoq_vol_pct` using the same Volume QoQ banding table; compute `gap = |make_volume_score − ticker_composite_score|` where `ticker_composite_score = scores.volume_momentum.score`. If `gap ≥ 2`, emit the entry to `per_make_divergence[]`. Empty array when no divergence OR when `per_make_raw` is null (single-make ticker, pure_play, or dealer-group).

**Why volume only (v1):** Volume divergence is the most analyst-relevant signal — "Jeep collapse while Ram is fine" inside STLA is a more actionable observation than "Jeep ASP softer than Ram." Expanding to per-metric divergence is a v1.1 candidate. Per-make rows are also re-emitted on the W1 surface so analysts can still inspect each make's QoQ/YoY/ASP/DOM directly even when no divergence fires.

DQ event `(l)` is logged whenever `per_make_divergence` is non-empty.

## Slot-population matrix by `ticker_classification` × `entity_type`

| Classification | volume_momentum | asp | msrp_gap | dom | days_supply_used | days_supply_new | ev_share | mix |
|---|---|---|---|---|---|---|---|---|
| OEM, legacy | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — |
| OEM, pure_play | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — |
| Dealer group, Both | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Dealer group, Used-only (KMX) | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — |
| Dealer group, New-only (none currently mapped) | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — |

A "—" cell means the slot is structurally null (the underlying data does not exist for that combination). A "✓" cell means the slot is populated when the underlying data is non-null. Pure_play `ev_share` is null because every vehicle is EV (delta is structurally undefined). Mix is null for OEMs because New-vs-Used share is not an OEM-level metric.

## Quarter-baseline columns are informational (not banded)

The W1 leading-indicators table exposes a "year-ago quarter" value for Volume (already banded via the `volume_momentum` YoY input) and, in row context, for ASP / MSRP gap / DOM / EV share / Mix as analyst reference. These year-ago values for non-Volume metrics are for analyst interpretation only — they do **NOT** have YoY bands and do **NOT** contribute to composite slots.

Volume's `yoy_pct` (which IS banded as the YoY input inside the `volume_momentum` combiner) remains the sole multi-quarter banded derivation. All other year-ago columns are reference context — the verdict still derives from QoQ bands (or, for Days Supply, the current absolute value from the extended `mrcm` window).

**Why not band them?** Adding `asp_yoy` / `dom_yoy` / `msrp_yoy` / `ev_yoy` / `mix_yoy` slots would expand the reducer from 8 → 13 composite slots, shifting the BULLISH threshold from 4-of-8 BULLISH slots (mean ≥ +1.0 ≈ 4 × 2 / 8) to 7-of-13 (≈ 7 × 2 / 13 = +1.08). This would silently drift the verdict math across the existing test suite and require re-tuning every banding worked example.

**If future analysis warrants banded YoY for additional metrics**, the expansion lives here and in `aggregate_signals.py` — NOT in templates. v1.1 candidate.
