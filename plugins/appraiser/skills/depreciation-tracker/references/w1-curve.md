# W1 — Make/Model Depreciation Curve

Reference workflow. Triggers on "depreciation curve for <make> <model>", "how
fast is the RAV4 losing value", "value retention curve", "show me the
depreciation trajectory for ...". The output gives the appraiser a
defensible per-month decay rate to apply against book-based starting points
for trade-in offers, insurance claim settlements, or estate / probate
valuations.

## Required inputs

- **`make`** + **`model`** (both required). Halt-and-ask if either missing.
- **No `year`** — `get_sold_summary` does not accept year. The curve aggregates
  across all model years per `references/sold-summary-safety.md`. The output
  template renders an explicit scope qualifier; the appraiser applies the
  curve's verdict band against their year-specific book starting point.
- **No subject VIN** required. W1 has no subject vehicle in the per-VIN
  appraisal sense.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | per `references/country-uk.md` |
| `profile.location.country` not in {US, UK} | *"Depreciation Tracker does not yet support this country. The skill is US-only — `get_sold_summary` is the only sold-transaction-aggregate tool and has no non-US variant. Re-visit when MarketCheck ships sold data for additional markets."* |
| `profile.location.state` null/empty (US) | halt-and-ask the user's state |
| `make` or `model` missing | halt-and-ask |
| user explicitly named "new-car" / "MSRP parity" / "above sticker" | redirect to W5 — *"Depreciation Curve is a used-vehicle workflow; new vehicles haven't depreciated. For new-vehicle MSRP parity tracking, run W5 (MSRP Parity Tracker)."* |

## Parallelization (W1)

W1 runs in two waves under the universal wave contract.

### Wave A — Per-period sold-summary fan-out + rep-VIN search (parallel — 6 calls)

Launched once profile + make/model are in hand. All six calls share no
cross-dependency.

1. `get_sold_summary` × 5 — one per period (`current`, `60d`, `90d`, `6mo`,
   `1yr`). Each call is parameterized identically except for `date_from` /
   `date_to`, which come from `scripts/compute_period_windows.py` (run ONCE
   at workflow entry):

   ```
   get_sold_summary:
     make=<make>, model=<model>
     inventory_type="Used"
     state=<profile.location.state>
     summary_by="state"
     ranking_dimensions="make,model"
     ranking_measure="average_sale_price"
     top_n=5
     limit=5000
     date_from=<period.date_from>
     date_to=<period.date_to>
   ```

   **Do NOT pass `dealer_type`** (silent data suppression — see
   `references/sold-summary-safety.md`).

   Each parsed via `parse_sold_summary.py --aggregate-multi-period`.

2. `search_active_cars` (rows=1) — finds a representative listing whose VIN
   feeds Wave B's decode for the original MSRP:

   ```
   search_active_cars:
     make=<make>, model=<model>
     car_type=used
     zip=<profile.location.zip>, radius=<session.radius_mi_clamped>
     sort_by="msrp", sort_order="desc"
     price_range="1-*"
     rows=1
     include_dealer_object=false
     include_build_object=true       # we need build.year + build.msrp on the rep listing
     fetch_all_photos=false, include_mc_dealership_object=false,
     include_finance=false, include_lease=false, include_relevant_links=false
   ```

   Sort is `msrp desc` (not `price desc`) — picks a top-trim representative
   for a more reliable MSRP anchor. If the upstream rejects
   `sort_by="msrp"` (server-side facet check), fall back to
   `sort_by="price", sort_order="desc"` and emit DQ event (f).

   Parsed via `parse_search.py --file`. The parser's listing already
   exposes `msrp` flat at the listing root, so a decode may not even be
   needed when the rep listing carries MSRP. Wave B fires only when
   `parse_search.listings[0].msrp` is null.

### Wave B — Rep-VIN decode (conditional, 1 call)

Fires only when:
- Wave A's `parse_search` returned at least one listing AND
- That listing's `msrp` field is null.

```
decode_vin_neovin(vin=<rep_vin>)  →  parse_decode.py --file <decode.json>
```

Per `references/truncation-recovery.md`, decode chronically truncates
(~150KB envelopes); always recover via `--file`.

If decode succeeds → `msrp = parse_decode.specs.msrp`.
If decode `ok=false` OR `msrp` is null after decode → fall through to
`anchor_mode="prior_period"`; emit DQ event (a) for the failed decode
+ DQ event (g) for the anchor-mode fallback.

### Wall-clock budget (W1)

- Wave A ≈ 12-15s
- Wave B ≈ 12-15s when fired; usually skipped when rep listing carries `msrp`
- Total ≈ 12-30s

## Pipeline

```
parse_sold_summary.py × 5 --aggregate-multi-period
parse_search.py × 1 --file <rep.json>
parse_decode.py × 1 --file <decode.json>            # conditional

# Build the per-period feed for the curve engine
periods_input = compose from compute_period_windows.json + each
                parse_sold_summary.multi_period_aggregate.overall block
                (one entry per period: label, months_offset_from_today,
                 month, weighted_avg_sale_price, total_sold_count)

depreciation_curve.py < {periods, msrp, anchor_mode="auto"}
                     > /tmp/marketcheck/<run_id>/curve.json

render_depreciation_table.py --mode curve
                              --input /tmp/marketcheck/<run_id>/curve.json
                              --currency '$'
```

## Anchor-mode resolution

`depreciation_curve.py` reads `anchor_mode="auto"` and resolves:

- `msrp` is set AND > 0 → `anchor_used="msrp"`. Each period's
  `retention_pct_msrp` = (avg_price / msrp) × 100. Renderer adds a
  "Retention % (vs MSRP)" column.
- `msrp` null/zero → `anchor_used="prior_period"`. `retention_pct_msrp` is
  null on every row; renderer omits the column. The "Retention % (vs Prior)"
  column always renders.

The skill always emits prior-period retention (always renderable from the
data); MSRP retention is additive when the decode-or-rep-listing path
supplies a non-null MSRP.

## Min-comp confidence caveat

When any period's `total_sold_count < profile.appraiser.min_comp_count`,
prefix that period's row in Key Signals with a thin-data caveat: *"period
<label> sample size <N> below min_comp_count <M>; treat as directional."*
The period stays in the table; the caveat is rendered in Key Signals so
the appraiser can decide whether to defer or quote-with-caveat.

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| Make/model missing | user input incomplete | Halt at pre-check; ask for both. |
| UK profile | country=UK | Halt per `references/country-uk.md`. |
| `make_model_not_found` on any period | parser error_type | Retry once with facet-discovered casing per `references/facet-discovery.md`. If still failing, omit the period from the curve + emit DQ event (a). |
| `network_422` on any period | parse error | Verify dates from `compute_period_windows.py` are month-aligned; if so, omit period + emit DQ event (a). |
| Rep listing search returns 0 | empty market | Skip Wave B decode; force `anchor_mode="prior_period"`; emit DQ event (g). |
| Rep listing carries `msrp` directly | parse_search exposes it | Skip Wave B decode entirely; use that MSRP. |
| Decode ok=false | truncation unrecoverable / 5xx | Fall to `anchor_mode="prior_period"`; emit DQ events (a) + (g). |
| Decode succeeds but `specs.msrp` null | NeoVIN gap | Same as above. |
| Truncation envelope on sold-summary | rare | `--file` recovery per `references/truncation-recovery.md`; emit DQ event (b). |
| Fewer than 2 priced periods after recovery | catastrophic data loss | `depreciation_curve.py` emits `ok=false / error_type=insufficient_periods`; render Headline as `"Insufficient sold data to build a depreciation curve for <make> <model>"` + Data Quality Notes; do not render the curve table. |
| All periods returned null `weighted_avg_sale_price` | zero sold counts | Same as above. |

## Render

Per `assets/output-template.md` W1 column. Headline phrasing:

```
<make> <model> retained <retention_pct_msrp>% of original MSRP after <months_offset_from_today> months,
depreciating at <recent_monthly_rate>%/month — <verdict>.
```

When `anchor_used == "prior_period"`:

```
<make> <model> sold-summary average dropped from $<oldest_avg> to $<newest_avg> over <months_span> months
(<recent_monthly_rate>%/month) — <verdict>.
```

Both end with one of the 5-band verdicts from `references/tier-and-verdict-bands.md`.

## DQ event log discipline (W1)

- (a) MCP errors / non-200 — sold-summary period failure, decode ok=false.
- (a1) Facet-discovery retries when sold-summary returned `make_model_not_found`.
- (b) Truncation envelope unwraps via `--file`.
- (e) Anchor-mode fallback when MSRP unavailable; period omitted from curve.
- (g) Workflow branches skipped — Wave B decode skipped because rep listing
  carried MSRP; or anchor_mode forced to prior_period because rep search
  returned 0.
