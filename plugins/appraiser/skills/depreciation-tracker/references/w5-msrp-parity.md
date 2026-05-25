# W5 — MSRP Parity Tracker

Triggers: "which new cars are selling over sticker", "are markups coming
down", "incentive effectiveness", "MSRP parity tracker", "above sticker
price", "new-vehicle replacement-cost trend". The output gives the
appraiser a new-vehicle parity table — load-bearing for insurance
replacement-cost claims on recent new-vehicle losses and for trade-in
appraisals where the customer is buying a new vehicle whose market price
diverges from MSRP.

## Required inputs

- **`inventory_type="New"`** — fixed; W5 is about new-vehicle MSRP parity.
  If the user explicitly asks for "used-vehicle" or "depreciation curve",
  redirect to W1: *"MSRP Parity tracking is for new-vehicle pricing. Run W1
  (depreciation curve) for used-vehicle trajectory."*
- **State** — required (default from profile).
- **`comparison_window`** — months back for the prior-period anchor.
  Default 3 months; overridable.
- **`top_n_models`** — default 30.

## Pre-check halts

Same shape as W1.

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
funnel item 5): *"<model> deepening discount: now selling at -X.X% vs -Y.Y%
prior period — for new-vehicle insurance claim replacement-cost, anchor on
the prevailing transaction price (not MSRP) and cite the trend."*

## Comparison Context (W5-specific)

W5's Comparison Context anchors on the appraiser's specialization plus the
top-volume make in the user's state:

- `specialization == "insurance"` → spotlight any newly-flipped-below
  models among the top-10 by volume. *"<model> flipped to <pct>% over the
  comparison window — replacement-cost claims on this model in the last
  30 days should anchor on transaction price, not MSRP."*
- `specialization == "trade-in"` → spotlight any above-sticker models in
  the top-10 by volume. *"<model> commands +<pct>% over MSRP — when valuing
  a trade-in for a customer buying this model, the in-pocket transaction
  price (not MSRP) drives the deal economics."*
- `specialization == "estate_legal"` or `"fleet"` → render the volume
  ranking with no per-persona spotlight and emit DQ event (g) noting the
  specialization isn't materially applicable to W5.
- `specialization == "general"` or absent → render the insurance framing
  by default and emit DQ event (g) noting the default.

## DQ event log discipline (W5)

- (a) MCP errors recovered.
- (e) Models present in current but not prior (or vice versa) — emit count.
- (g) `comparison_window` defaulted to 3 months because user didn't specify.
- (g) Specialization defaulted to "general" because the profile didn't carry one.
