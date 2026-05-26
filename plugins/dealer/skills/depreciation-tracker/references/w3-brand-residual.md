# W3 — Brand Residual Ranking

Triggers: "which brands hold value best", "brand retention ranking",
"automakers by residual value", "brand value tier".

## Required inputs

- **State** — required (default from profile).
- **`comparison_window`** — months back for the prior-period anchor.
  Default 6 months (per the existing skill); overridable.
- **`top_n_brands`** — default 25.

## Pre-check halts

Same as W1, with one W3-specific halt-message override:

| Trigger | Halt message |
|---|---|
| `profile.preferences.default_inventory_type == "new"` | *"Brand Residual is a used-vehicle workflow — residual value is the post-depreciation worth of a vehicle; new vehicles haven't reached residual yet. The W3 output template's 'T1 leaders' / 'tier-jump' verdict bands and 'retention %' headline phrasing are Used-vehicle semantics. For new-vehicle pricing parity by brand, run W5 (`/msrp-parity`) — the symmetric New-only workflow."* |

All other W1 pre-check rows (UK, CA, `both`, missing state / make / model) apply unchanged.

## Parallelization (W3)

Single-wave workflow; 3 parallel `get_sold_summary` calls.

### Wave A — current prices + prior prices + current volumes (parallel)

```
1. get_sold_summary:
     state=<state>, inventory_type=<car_type>
     ranking_dimensions="make"
     ranking_measure="average_sale_price"
     ranking_order="desc"
     top_n=25, limit=5000
     summary_by="state"
     date_from/to = current period

2. Same as 1 but date_from/to = current - comparison_window months.

3. get_sold_summary:
     state=<state>, inventory_type=<car_type>
     ranking_dimensions="make"
     ranking_measure="sold_count"
     ranking_order="desc"
     top_n=25, limit=5000
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

## DQ event log discipline (W3)

- (a) MCP errors recovered.
- (e) Brands present in current but not prior (or vice versa) — emit count.
- (g) `comparison_window` defaulted to 6 months because user didn't specify.
