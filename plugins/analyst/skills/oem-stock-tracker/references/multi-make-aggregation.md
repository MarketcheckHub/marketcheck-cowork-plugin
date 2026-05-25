---
name: multi-make-aggregation
description: Sold-count-weighted-mean math for rolling up multi-state and multi-make get_sold_summary responses to a single ticker-level aggregate. Includes the null-priced-row handling discipline and the low-volume confidence-floor rule.
type: reference
---

# Multi-make aggregation math

Resolves AMB-06 (multi-make ASP/DOM aggregation unspecified) and AMB-15 (low-volume floor scope) from the original `oem-stock-tracker` skill analysis.

## Three layers of aggregation

A typical W1 sold-summary call returns rows at the **(state × month × make)** granularity. To produce a single ticker-level metric for a given window, three roll-ups apply:

1. **Within a make, across states** (e.g., Ford CA + Ford TX + ... → Ford-national for April).
2. **Within a ticker, across makes** (e.g., Ford + Lincoln → F-national for April).
3. **Within a ticker, across windows** (e.g., F-April + F-March + F-Feb + F-Jan → F multi-window).

All three roll-ups use the same primitive: **sold-count-weighted means** for value metrics (ASP, DOM, MSRP positioning, avg_msrp), and **sums** for count metrics (sold_count, total_sale_price).

## The weighted-mean formula

For any value metric `v` (e.g., `average_sale_price`) with corresponding weight `w` (the row's `sold_count`):

```
weighted_v = Σ(v_i × w_i) / Σ(w_i)
           for all rows i where v_i is non-null AND w_i > 0
```

**Critical:** null-valued `v_i` rows drop from **BOTH the numerator AND the denominator**:

```
For row i where v_i is null:
  - skip the row's contribution to Σ(v_i × w_i)         ← not added to numerator
  - skip the row's contribution to Σ(w_i) in this metric ← not added to denominator
```

This is different from naive "ignore null" which only skips the numerator — that would bias the mean toward zero. The discipline here is: **a null row contributes nothing to this metric's mean, neither in count nor in value.**

The row's `sold_count` (the weight) still contributes to the **`total_sold_count`** aggregate (so volume rollup is correct).

## Worked example — Ford Used March 2025, national

Empirical data from the live MCP (53 state rows). Excerpt:

| State | sold_count | average_sale_price | average_days_on_market |
|---|---|---|---|
| TX | 24,809 | 28,173.60 | 44.13 |
| CA | 11,865 | 25,533.93 | 57.45 |
| FL | 15,024 | 26,167.99 | 45.80 |
| ... | ... | ... | ... |
| MP | 1 | **null** | 4.00 |
| GU | 9 | 30,106.11 | 40.67 |
| AS | 11 | 29,404.55 | 92.73 |
| ... | ... | ... | ... |

Aggregating to Ford-national:
- `total_sold_count = 24809 + 11865 + 15024 + ... + 1 + 9 + 11 + ... ≈ 175,000`
- `weighted_avg_sale_price = Σ(ASP_i × sold_count_i) / Σ(sold_count_i where ASP_i is non-null)`
  - MP's 1-unit row drops from both numerator AND denominator of the weighted-ASP mean (because its ASP is null).
  - GU and AS contribute to both (non-null ASPs).
  - Result: weighted ASP ≈ $26,200 (close to the largest-state values weighted by their volume).
- `weighted_avg_days_on_market`:
  - MP's row HAS a non-null DOM (4.0), so it DOES contribute (but with weight 1, it has minimal influence on a sample of ~175,000).

## Multi-make ticker rollup — Ford (F = Ford + Lincoln)

After the first layer produces Ford-national and Lincoln-national aggregates, the second layer combines them:

```
F.total_sold_count = Ford.total_sold_count + Lincoln.total_sold_count
F.weighted_avg_sale_price = (Ford.weighted_ASP × Ford.sold + Lincoln.weighted_ASP × Lincoln.sold)
                          / (Ford.sold + Lincoln.sold)
```

Same null-handling discipline applies at this layer — if Lincoln returns a null `weighted_avg_sale_price` (rare, but possible if every Lincoln state-row had a null), Lincoln drops from BOTH numerator and denominator of the F-level weighted ASP, while Lincoln's `total_sold_count` still contributes to F's `total_sold_count`.

For STLA (7 makes): Chrysler + Dodge + Jeep + Ram + Fiat + Alfa Romeo + Maserati → STLA-national. Same math.

## Multi-window rollup — F multi-month

For W1's per-make sold call (4 months: current + prior + 2 baseline-of-3 months), the single MCP response contains ~212 rows (4 months × 53 states × 1 make at top_n=1).

`parse_sold_summary.py --aggregate-make-by-window <make>` groups rows by `month` first, then aggregates within each month (state-rollup, the first layer). Output:

```json
{
  "make": "Ford",
  "months": {
    "2026-04": {<aggregate>},
    "2026-03": {<aggregate>},
    "2026-02": {<aggregate>},
    "2026-01": {<aggregate>}
  }
}
```

Then `compute_oem_stats.py` does the second-layer (multi-make) rollup per window and the third-layer (multi-window) rollup for the baseline_3mo aggregate:

```
F.current   = combine(Ford.2026-04, Lincoln.2026-04)
F.prior     = combine(Ford.2026-03, Lincoln.2026-03)
F.baseline_3mo = combine(F.2026-03, F.2026-02, F.2026-01)
               = combine(Ford.{2026-03, 2026-02, 2026-01}, Lincoln.{2026-03, 2026-02, 2026-01})
```

The baseline_3mo rollup uses the same weighted-mean math — `total_sold_count` sums across the 3 months; ASP/DOM/MSRP positioning are weighted by `sold_count` across all (make × month) combinations.

## Low-volume floor (resolves AMB-15)

A make selling fewer than **100 units/month nationally** triggers a low-confidence flag in `compute_oem_stats.py` (DQ event (i)).

**Why 100:** A national monthly sold count below 100 has high variance — single-store inventory cycles or seasonal anomalies can swing the per-state weighted means by 5-10%. Above 100, the law of large numbers gives a stable signal.

**Scope:** national only. The skill is national-only by design (resolves AMB-07); no state-level threshold applies.

**Applied to:** each per-make per-window aggregate in `per_make_raw`. If a make's `sold_count_current < 100`, the DQ event (i) is logged with the make name and exact count. The signal is still computed, but the renderer footnotes it as low-confidence.

Examples of makes that may trigger:
- **Maserati** (STLA) — national monthly sold typically 50-200 units; can be below 100 in some months.
- **Alfa Romeo** (STLA) — similar.
- **Lucid** (LCID) — national monthly sold typically 100-300; near the threshold.
- **Lincoln** (F) — usually well above 100 (5,000-30,000/month nationally).

Common-sense check: the DQ event (i) means *"this signal is noisier than usual"*, not *"this signal is wrong"*. The aggregate verdict is still computed; the analyst is just warned to weight that make less heavily in their interpretation.

## Why we drop null-priced rows from BOTH numerator and denominator

A naive "skip nulls in numerator only" would compute:

```
naive_weighted_ASP = Σ(ASP_i × sold_count_i for non-null ASP_i)
                   / Σ(sold_count_i for ALL rows including null-ASP ones)
```

For Ford US national: 53 rows summing to ~175,000 sold, of which MP contributes 1 row with `sold_count=1, ASP=null`. The naive denominator (175,000) is ~unchanged. The numerator drops MP's contribution. So the naive mean is slightly biased low (by ~0.001%) — negligible at this scale.

But in pathological cases — e.g., a brand-orphan analysis on a brand where 70% of state rows have null ASP (very low-volume brand, sub-unit territories) — the naive denominator would be 3-4× the correct denominator, and the weighted ASP would land at ~25-30% of the true value. Disastrous for verdict signals.

The disciplined "drop from both" produces a correct weighted mean over the rows that actually have data:

```
disciplined_weighted_ASP = Σ(ASP_i × sold_count_i for non-null ASP_i)
                         / Σ(sold_count_i for non-null ASP_i ONLY)
```

This is the formula `parse_sold_summary.py` implements in `_aggregate_rows()`. Same discipline applies to DOM, median DOM, MSRP positioning, and avg_msrp.

## Test coverage for this math

`tests/test_parse_sold_summary.py` covers:
- Null-priced row dropped from both numerator and denominator (fixture: `sold_summary_null_price_territory.json`).
- Multi-month grouping correctness (fixture: `sold_summary_per_make_multi_month.json`).
- Multi-make rollup via downstream `compute_oem_stats.py` (fixtures: STLA-shaped inputs).

`tests/test_compute_oem_stats.py` covers:
- Per-make to ticker-level rollup (sold-count-weighted means).
- Multi-window rollup for baseline_3mo.
- Low-volume DQ event (i) triggered correctly.

If a test asserts a value that disagrees with the math above, **the test wins** — the math has been mis-implemented; file a doc bug and align the implementation with the test.
