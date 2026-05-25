# W5 — MSRP Parity Tracker

Triggers: "which new cars are selling over sticker", "are markups coming
down", "incentive effectiveness", "MSRP parity tracker", "above sticker price".

## Required inputs

- **`inventory_type="New"`** — fixed; W5 is about new-vehicle MSRP parity.
  If the user supplies `Used`, halt-and-ask: *"MSRP Parity tracking is for
  new-vehicle pricing. Run W1 (depreciation curve) for used-vehicle
  trajectory."*
- **State** — required (default from profile).
- **`comparison_window`** — months back for the prior-period anchor.
  Default 3 months (per the existing skill); overridable.
- **`top_n_models`** — default 30.

## Pre-check halts

Same shape as W1, plus the inventory_type=Used redirect above.

## Parallelization (W5)

Single-wave workflow; 3 parallel `get_sold_summary` calls.

### Wave A — current parity + prior parity + current volume (parallel)

```
1. get_sold_summary:
     inventory_type="New"
     state=<state>
     ranking_dimensions="make,model"
     ranking_measure="price_over_msrp_percentage"
     ranking_order="desc"
     top_n=30, limit=5000
     summary_by="state"
     date_from/to = current period

2. Same as 1 but date_from/to = current - comparison_window months.

3. get_sold_summary:
     inventory_type="New"
     state=<state>
     ranking_dimensions="make,model"
     ranking_measure="sold_count"
     ranking_order="desc"
     top_n=30, limit=5000
     summary_by="state"
     date_from/to = current period
```

## Pipeline

```
parse_sold_summary.py × 3
msrp_parity.py < {current, prior, volumes} > parity.json
render_depreciation_table.py --mode parity --input parity.json
```

## Render

Per `assets/output-template.md` W5 column. Headline:

```
<count> models above sticker, <count> below. Largest current premium: <model> (+X.X% over MSRP).
Newly flipped below MSRP this period: <list>.
```

Surface deepening discounts as Key Signals (per `references/outcomes.md`
lines 22-23): *"<model> deepening discount: now selling at -X.X% vs -Y.Y%
prior period — incentive program biting / oversupply signal."*

## DQ event log discipline (W5)

- (a) MCP errors recovered.
- (e) Models present in current but not prior (or vice versa) — emit count.
- (g) `comparison_window` defaulted to 3 months because user didn't specify.
