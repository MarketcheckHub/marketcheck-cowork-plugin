# W3 — Brand Residual Ranking

Triggers: "which brands hold value best", "brand retention ranking",
"automakers by residual value", "brand value tier", "per-brand trend
adjustment". The output gives the appraiser a per-brand trend-discount
table to apply against book values — T1 brands need no per-brand
adjustment; T4 brands warrant a 2–4% downward trend discount in current
appraisals.

## Required inputs

- **State** — required (default from profile).
- **`comparison_window`** — months back for the prior-period anchor.
  Default 6 months; overridable.
- **`top_n_brands`** — default 25.

## Pre-check halts

Same as W1, with one W3-specific intent-redirect:

| Trigger | Halt message |
|---|---|
| user explicitly named "new-car" / "MSRP parity" / "above sticker" | *"Brand Residual is a used-vehicle workflow — residual value is the post-depreciation worth of a vehicle; new vehicles haven't reached residual yet. For new-vehicle pricing parity by brand, run W5 (MSRP Parity Tracker)."* |

All other W1 pre-check rows (UK, missing state, etc.) apply unchanged.

## Parallelization (W3)

Single-wave workflow; 3 parallel `get_sold_summary` calls.

### Wave A — current prices + prior prices + current volumes (parallel)

```
1. get_sold_summary:
     state=<state>, inventory_type="Used"
     ranking_dimensions="make"
     ranking_measure="average_sale_price"
     ranking_order="desc"
     top_n=25, limit=5000
     summary_by="state"
     date_from/to = current period

2. Same as 1 but date_from/to = current - comparison_window months.

3. get_sold_summary:
     state=<state>, inventory_type="Used"
     ranking_dimensions="make"
     ranking_measure="sold_count"
     ranking_order="desc"
     top_n=25, limit=5000
     summary_by="state"
     date_from/to = current period
```

## Pipeline

```
parse_sold_summary.py × 3
brand_retention.py < {current, prior, volumes} > brand.json
render_depreciation_table.py --mode brand --input brand.json
```

## Render

Per `assets/output-template.md` W3 column. Headline:

```
T1 leaders: <top-3 makes>. Largest tier-jump down: <make> dropped from T<X> → T<Y>.
<count> brands in T1; <count> in T4.
```

Tier-jump detection: if a brand's prior-period retention placed it in a
different tier than current, that's a "movement" event. Surface up to 3
movers (largest absolute retention change) as Key Signals.

## Comparison Context (W3-specific)

W3's Comparison Context anchors on the appraiser's specialization plus the
top-volume make in the user's state (the make the appraiser is most likely
to see in the field):

- `specialization == "trade-in"` → highlight the top-volume make's tier
  and current trend rate. *"In <STATE>, the highest-volume make this
  period is <make> (<volume> sold) at <tier>. Trade-in appraisals should
  apply <tier-specific trend discount> against book."*
- `specialization == "insurance"` → flag any T4 brand among the top-5
  volume. *"<make> (T4) ranks #N by volume in <STATE> — total-loss
  settlements on this brand should cite last-30-days transaction comps
  rather than book."*
- `specialization == "estate_legal"` → flag T4 brands with deepening
  movement. *"<make> moved T<X> → T<Y> over the comparison window —
  estate valuations of these brands should note the trajectory."*
- `specialization == "fleet"` → flag tier movement among any brand at
  ≥10% of state volume. *"<make> (<X>% of state volume) moved T<X> → T<Y>
  — concentration-risk consideration for fleet revaluation."*
- `specialization == "general"` or absent → render the trade-in framing
  by default and emit DQ event (g) noting the default.

## DQ event log discipline (W3)

- (a) MCP errors recovered.
- (e) Brands present in current but not prior (or vice versa) — emit count.
- (g) `comparison_window` defaulted to 6 months because user didn't specify.
- (g) Specialization defaulted to "general" because the profile didn't carry one.
