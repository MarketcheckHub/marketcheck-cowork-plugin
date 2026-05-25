# Output Template — Vehicle Appraiser

This file is the **single source of truth** for output block structure, the
8-column comp table schema, the appraisal value-band block, the Sold
Transaction Comparables schema, methodology phrasing, and the internal
self-check. W1 / W3 / W4 / W5 render through this template; W2 renders via
`assets/w2-output-template.md`.

Placeholders in angle brackets `<...>` are interpolated from the
parser / `comp_stats.py` / `compute_appraisal_band.py` /
`compute_regional_variance.py` outputs. Optional blocks are marked
`(OPTIONAL)` and only render when the precondition holds.

**Naming convention.** Lowercase placeholders like `<primary>`,
`<marketcheck_predict.nocpo_primary.marketcheck_price>`,
`<channel_stats.primary.n>` reference fields on the script output objects
— pull the exact numeric value. Uppercase labels like `<PRIMARY>` are
rendered F/I human labels — map `primary` → `"Franchise"` or
`"Independent"` based on `session.dealer_type_title`. Keep the two
namespaces distinct.

---

## First line (always)

```
Using profile: <dealer.name>, <ZIP or postcode>, <country>
```

---

## Vehicle Identification  (W1, W3, W5 — always; W4 omits since no subject)

```
VIN:           <VIN>                       (or "Source: user-supplied YMMT" when YMMT-only)
Year:          <year>
Make:          <make>
Model:         <model>
Trim:          <trim>
Body Type:     <body_type>
Drivetrain:    <drivetrain>
Engine:        <engine>
Transmission:  <transmission>
MSRP:          $<msrp>
Mileage:       <user-supplied miles> mi
Asking Price:  $<user_price>               (render "—" if not supplied)
CPO:           <Yes | No | unknown>
Condition:     <Clean | Average | Rough>   (render "Average (assumed)" if user didn't supply)
Purpose:       <Trade-in | Retail | Insurance | Wholesale>
```

**Null-field rule (hallucination guard):** render any field whose value parses as `null` / missing as literal `—`. Do NOT substitute plausible defaults from model knowledge.

---

## Headline  (always — leads every workflow except W5)

**Exactly one sentence.** Names the value range, the anchor source, and the confidence band.

```
W1 / W3:
  <purpose>-anchored value range $<low>–$<high> (mid $<mid>);
  <confidence> confidence (<comp_count_total> total comps: <n> active + <sold_count_used> sold-90d).
  Anchor: <anchor source label>.

W4 (regional):
  <year> <make> <model> [<trim>] across <N_markets> markets:
  <lowest_market.zip> cheapest at $<median>, <highest_market.zip> highest at $<median>;
  max spread <max_delta_pct>%.
```

Anchor source labels:
- `sold_90d` → `"<sold_count_used>-unit sold-90d trim median"`
- `active_comps` → `"<n>-comp active-listing distribution"`
- `predict_only` → `"MarketCheck Price ML prediction (active comp set thin)"`
- `null` → `"unavailable — see Insufficient Evidence note below"`

W5 has no Headline block — the Price Trajectory table is the W5 punchline.

---

## Market Snapshot  (W1, W3, W4 — always; W5 omits)

```
Radius:                <radius_mi> mi from <profile.location.city>
Active Comps:          <active_count>   (<kept_count> rendered after variant filters)
Sold (90d, local):     <sold_count_90d>
Months of Supply:      <mos>            (active / (sold_90d / 3))
Price-Drop Rate (visible):     <drops_in_set> of <n> (<drop_rate_visible*100>%)
Price-Drop Rate (market-wide): <drops_market_wide_count> of <active_count> (<drop_rate_market_wide*100>%)
State Baseline (<make> <model> across all trims & years in <STATE>, last 3 full months):
  avg sale $<avg_sale_price>  ·  avg DOM <avg_dom> days  ·  sold <sold_count>
```

**State Baseline scope note (always render below the block when the State Baseline rendered):**

> *State Baseline reflects state-wide sold velocity for the make/model — a broader cut than the trim-specific sold anchor used in the appraisal band. Use it for market-health context, not direct price comparability.*

If the State Baseline call degraded, omit both the line and the note.

---

## Price Distribution  (W1, W3, W4 — always)

Header line reconciles the distribution's computation scope with the rendered comp table's row count:

```
Price Distribution  (n=<quartile.n>; source: <stats_source>)

Min:        $<quartile.min>
P25:        $<quartile.p25>
Median:     $<quartile.median>
Mean:       $<quartile.mean>   (stddev: $<quartile.stddev>)
P75:        $<quartile.p75>
Max:        $<quartile.max>
```

When `stats_source == "client"`, emit a footnote: *"Client-computed over `<n>` visible comps; server-wide stats unavailable — percentiles and quartile bounds may understate the true spread."*

W4 renders one Price Distribution block **per market** (small table form).

---

## Active Mileage Distribution  (W1, W3 — always when mileage_distribution present)

Source: `comp_stats.mileage_distribution` (server-preferred, client fallback).

```
Min:        <mileage_distribution.min> mi
Median:     <mileage_distribution.median> mi
Mean:       <mileage_distribution.mean> mi
Max:        <mileage_distribution.max> mi
```

When `mileage_distribution.source == "client"`, emit a compact suffix on the block header: ` (client-computed over <n> visible comps)`.

---

## DOM Distribution  (W1, W3 — always)

Using the profile's DOM thresholds `{fresh_max_days, aging_max_days}`:

```
Fresh (0–<fresh_max_days>d):              <dom_buckets.fresh>  (<pct>%)
Aging (<fresh_max+1>–<aging_max_days>d):  <dom_buckets.aging>  (<pct>%)
Stale (<aging_max+1>+d):                  <dom_buckets.stale>  (<pct>%)
Unknown:                                  <dom_buckets.unknown>
```

Source field: `dom_active` only — never `dom_180` or `dom`.

---

## Predicted Prices (ML — MarketCheck)  (W1, W3 — always when ML predict ran; W5 only when fair-value branch fired)

Every "MarketCheck Price" line below renders a value sourced from the `predict_price_with_comparables` MCP call. The `MarketCheck` prefix is load-bearing — it distinguishes these MarketCheck-sourced numbers from the active-comp `Market Median` and the realised-sale `Sold-90d Trim Median`.

The default (non-CPO branch only) layout reads from `marketcheck_predict.<role>`:

```
Franchise MarketCheck Price (non-CPO):      $<marketcheck_predict.nocpo_primary.marketcheck_price>
  MC active comps:  n=<nocpo_primary.comparables_n> · median $<...comparables_price_stats.median> · IQR $<p25>–$<p75> · range $<min>–$<max>
  MC recent comps:  n=<nocpo_primary.recent_comparables_n> · median $<...recent_comparables_price_stats.median> · IQR $<p25>–$<p75> · range $<min>–$<max>

Independent MarketCheck Price (non-CPO):    $<marketcheck_predict.nocpo_context.marketcheck_price>
  MC active comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
  MC recent comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
```

**CPO subject additional lines.** When the subject is CPO, add two more MarketCheck Price lines + their sub-lines below the non-CPO pair:

```
Franchise MarketCheck Price (CPO):          $<marketcheck_predict.cpo_primary.marketcheck_price>
  MC active comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
  MC recent comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
Independent MarketCheck Price (CPO):        $<marketcheck_predict.cpo_context.marketcheck_price>
  MC active comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
  MC recent comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
```

Sub-line absence rule: if `<role>.comparables_price_stats` is `null`, render the count line only and omit the median/IQR/range portion.

---

## CPO Premium  (OPTIONAL — only when subject is CPO and all 4 predict roles populated)

```
CPO Premium (Franchise):     +$<marketcheck_predict.premium_primary>  (<pct_primary>%)
CPO Premium (Independent):   +$<marketcheck_predict.premium_context>  (<pct_context>%)
Certification Cost (you):    $<marketcheck_predict.certification_cost>
Net Margin from CPO:         +$<marketcheck_predict.net_margin_primary>  (<PRIMARY> channel)
```

> *Premium and Net Margin are computed from the MarketCheck Price values:
> `Premium = MC Price (CPO) − MC Price (non-CPO)`;
> `Net Margin from CPO = Premium − Certification Cost`.
> The labels above don't carry the `MarketCheck` prefix because Premium is a market concept, not a MarketCheck product.*

The block renders only when `marketcheck_predict.premium_primary` is non-null.

---

## Recommended Value (condition-adjusted)  (W1, W3 — always; W5 only when fair-value branch ran)

Render this block by invoking `scripts/render_appraisal_value_band.py`:

```
scripts/render_appraisal_value_band.py \
  --appraisal-band <compute_appraisal_band.py output path> \
  --currency '$|£'             # default '$'; agent passes from profile.location.country
```

The script reads `compute_appraisal_band.py` output and emits the
low/mid/high tuple, confidence label, anchor source label, condition
applied, purpose, and the methodology notes block. **Never hand-roll** the
band — every value must come from the script. When the script is bypassed,
prefix the rendered output with `⚠ appraisal band renderer bypassed; manual
cells may diverge from canonical formatting` and emit self-check warning #14.

---

## Wholesale-vs-Retail Spread + Recommended Trade-In Offer  (W3 — always)

```
Predicted Retail Value (Franchise):    $<marketcheck_predict.nocpo_primary.marketcheck_price OR nocpo_context if independent-primary>
Predicted Wholesale Value (Independent): $<the other channel>
Spread:                                +$<spread_$> (<spread_pct>%)

Recommended Trade-In Offer:            $<offer_low>–$<offer_high>
  (78–85% of Predicted Retail; biased per <purpose>: <bias note>)

[when recon_cost is supplied]
Post-recon offer floor:                $<offer_low - recon_cost>
  (gross-up to protect margin after $<recon_cost> recon)
```

Spread and offer formula sourced verbatim from `references/w3-wholesale-vs-retail.md` "spread + offer-range computation" section.

When either predict role is `null`, render the line as `unavailable (predict role degraded)` and direct the user to W1 in Key Signals.

---

## Active Retail Comparables  (W1, W3 — 8-col table; W4 only on request; W5 omits)

The 8-column comp table, rendered via `scripts/render_comp_set_table.py`. Same script and schema as the golden reference (mirror of `competitive-pricer-updated/assets/output-template.md`). Render rules:

```
| Dealer | Type | Price | Miles | DOM | Distance | vs Mkt Median | Price Change |
```

W3 renders **two** comp tables — one for franchise listings and one for independent listings — back-to-back with explicit subtitles.

`scripts/render_comp_set_table.py` invocation:
```
render_comp_set_table.py \
  --merged <merge_comps output path> \
  --comp-stats <comp_stats output path> \
  --user-price <asking_price | empty> \
  --currency '$|£'
```

---

## Sold Transaction Comparables  (W1, W3 — always when step-8 sold-listings call succeeded; the strongest evidence in any appraisal)

The 8-column sold-table, rendered via `scripts/render_sold_table.py`. Sorted descending by `last_seen_at_date` (most recent sales first).

```
| Dealer | Type | Sold Price | Miles | DOM | Distance | Sale Date | CPO? |
```

`scripts/render_sold_table.py` invocation:
```
render_sold_table.py \
  --sold <parse_search output path for the sold-listings call> \
  --currency '$|£' \
  [--max-rows 10]
```

Render the table with up to 10 rows by default. When the sold-listings call degraded, render the block as `Sold Transaction Comparables: unavailable (<error_type>)` and emit DQ event (a).

**New-vehicle appraisals — empty result is expected, not a degradation.** When `car_type=new` AND `num_found == 0` AND no `error_type` is set (i.e., the call succeeded but the new-vehicle inventory class produced no sold-90d transactions for the YMMT), render the block as: *"Sold Transaction Comparables: N/A — new-vehicle sold-90d transactions are rare on this endpoint (expired/sold dealer listings are dominated by used inventory). Rely on Predicted Retail (above) for new-vehicle valuation."* and do NOT emit a DQ event (a). This is the documented thin-data path for new-vehicle subjects, not a data-quality failure.

---

## Same-Channel View  (OPTIONAL — W1, W3; only when `channel_stats.primary.n >= 2`)

Mirror of golden `competitive-pricer-updated/assets/output-template.md` Same-Channel View section. Two layouts depending on whether `primary_non_cpo` is present.

**Layout A — `primary_non_cpo` present:**
```
Same-Channel View (<PRIMARY>)
  All <PRIMARY> comps:           median $<primary.stats.median> (n=<primary.n>, <primary.cpo_count> CPO)
  <PRIMARY> non-CPO only:        median $<primary_non_cpo.stats.median> (n=<primary_non_cpo.n>)
  Your appraisal vs non-CPO:     <signed $diff> (<pct>%)
```

**Layout B — `primary_non_cpo` is None:**
```
Same-Channel View (<PRIMARY>)
  All <PRIMARY> comps:                median $<primary.stats.median> (n=<primary.n>, <primary.cpo_count> CPO)
  Your appraisal vs all-<PRIMARY>:    <signed $diff> (<pct>%)
```

`<signed $diff>` is computed from `band.mid - <primary.stats.median>` (signed). When the appraisal `band` is null, render the diff line as `—`.

---

## Outliers  (OPTIONAL — when `comp_stats.outliers` non-empty)

```
| VIN | Dealer | Price | z-score |
|-----|--------|-------|---------|
| <VIN>    | <Dealer> | $<price> | <z>   |
```

A listing is an outlier when `|price − mean| > 2 × stddev`. Surfaced so the appraiser can decide whether to discard (salvage titles, exotic trims, data-quality artifacts) before citing in the appraisal report.

---

## Methodology Notes  (W1, W3, W4, W5 — always)

Read from `compute_appraisal_band.py` output's `methodology_notes` array verbatim:

```
Methodology:
- <each note from compute_appraisal_band.py methodology_notes>
- ...
```

For W3, append spread methodology notes:
- Default offer-range derivation (78-85% of franchise predicted retail).
- Purpose-biased adjustment when applied (e.g., "Insurance bias: clamped to sold-median ±5%").
- Recon cost grossing-up when applicable.

For W4, append: regional variance threshold (5% default) and arbitrage-flag rule.

For W5, append: trajectory + flag derivation rules from `parse_history.py`.

---

## Caveats  (W1, W3, W5 — always; W4 typically omits)

```
Caveats:
- Accident history not accounted for — confirm via Carfax / AutoCheck before final offer.
- Aftermarket modifications not accounted for — document any in the appraisal narrative.
- Regional demand anomalies (sports / luxury / EV segments) can shift the value 5-10% beyond the band.
- <purpose-specific caveats>:
    - Insurance: this band is an active-market estimate; for total-loss settlement, consult sold-90d transactions directly.
    - Trade-in: the recommended offer is pre-physical-inspection; condition adjustment may shift the offer ±$1500-3000.
    - Wholesale: auction prices typically run 5-10% below retail wholesale due to fee structure.
```

---

## Data Quality Notes  (OPTIONAL — only when the event log is non-empty)

Compact bulleted list with typed prefixes `(a)` through `(g)` matching SKILL.md's Data Quality event log taxonomy. The typed prefix is required.

```
Data Quality Notes
- (a) MCP tool <tool_name> returned <error_type>; recovery: <path>.
- (b) Truncation envelope for <tool_name> unwrapped via --file.
- (c) Subject VIN found at <dealer_name> (<distance> mi) — shadow listing excluded.
- (d) Filtered: self_vin_match=<n>, exclude_vin_match=<n>, invalid_price=<n>.
- (e) Fallback source: <stat> derived from <secondary source> because <reason>.
- (f) Parameter adaptation: passed <used> in place of <preferred>.
- (g) Workflow branch skipped by design: <branch_name> — <reason>.
```

If empty, omit the section entirely.

---

## Key Signals  (always — 3 to 5 bullets)

Short bullets that highlight the non-obvious takeaways. Examples:

```
- Sold-90d median ($36,400) sits 4% below active median ($38,000) — buyers are paying less than asking. Anchor on sold for trade-in math.
- 32% mileage advantage vs the local comp median — lean into this in the listing copy.
- 3 same-segment franchise dealers within 20mi all raised prices last week — supply tightening.
- Confidence is Low (4 total comps) — recommend a physical inspection or a 30-mile radius widen before quoting.
- Condition was not supplied — band assumes Average; condition adjustment can shift mid ±$1,500.
```

Rules:
- Surface a sold-vs-active disagreement when `verdicts_disagree == true`.
- Surface a CPO-premium alert when net margin after cert cost is negative.
- Surface an MoS alert when `mos > 4` (heavy supply) or `mos < 1.5` (tight supply).
- Surface a mileage moat when `mileage_moat.tier == "moat"` (Headline already carries the phrase).
- Surface a missing-condition flag when condition was assumed Average.

---

## Self-check  (internal — never render as a grid)

The 14-item verification checklist. Run each item silently before returning. Render only the footer line.

1. Profile loaded and confirmed on first line.
2. Country-routing applied (US tools / UK tools / CA halt / other halt).
3. Dual pricing shown (franchise + independent), with `dealer_type_title` marking PRIMARY.
4. CPO detection ran; CPO Premium block rendered when applicable.
5. `car_type` respected — session value taken from profile; "both" halted and asked.
6. Subject VIN excluded from the comp set (W1, W3).
7. MoS filters match — numerator (active) and denominator (sold 90d) share `{year, make, model, trim, car_type, zip, radius}`.
8. No `$0` rows in any rendered table — `price_range="1-*"` + client-side filter.
9. Confidence band matches `comp_count_total` (Low <5, Medium 5-14, High 15+).
10. **Low-confidence appraisals render a RANGE, not a point estimate.** Domain-specific guard.
11. 8-column standard schema used on every Active Retail Comparables render; sold transactions table uses the dedicated 8-col schema (`Sold Price` + `Sale Date` + `CPO?`).
12. Data Quality event log surfaced when non-empty; omitted when empty.
13. Pipeline executed for every numeric block: `parse_search → merge_comps → build_comp_stats_input → comp_stats → compute_appraisal_band` for W1/W2/W3; `compute_regional_variance` for W4; `parse_history` for W5. Hand-rolled blocks must carry the `⚠ pipeline bypassed` warning.
14. Comp tables came from `render_comp_set_table.py`; sold table came from `render_sold_table.py`; appraisal band came from `render_appraisal_value_band.py`.

Render rule at response time:

- **All applicable checks pass** → emit a single footer line listing 5–7 of the items that were exercised, e.g.:
  `✓ Verified: profile, dual pricing, sold-anchor band, sold transaction table, methodology notes, no $0 rows.`
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.

---

## Render variations — which blocks per workflow

| Block | W1 | W3 | W4 | W5 |
|---|---|---|---|---|
| Vehicle Identification | ✓ | ✓ | — | ✓ |
| Headline | ✓ | ✓ | ✓ (regional) | — |
| Market Snapshot | ✓ | ✓ | ✓ (per-market) | — |
| Price Distribution | ✓ | ✓ | ✓ (per-market) | — |
| Mileage Distribution | ✓ | ✓ | ✓ (per-market) | — |
| DOM Distribution | ✓ | ✓ | — | — |
| Predicted Prices (ML) | ✓ | ✓ | — | ✓ (when fair-value branch) |
| CPO Premium | ✓ (if CPO) | ✓ (if CPO) | — | — |
| Recommended Value (condition-adjusted) | ✓ | ✓ | — | ✓ (when fair-value branch) |
| Wholesale-vs-Retail Spread + Recommended Offer | — | ✓ | — | — |
| Active Retail Comparables | ✓ | ✓ (×2) | — | — |
| Sold Transaction Comparables | ✓ | ✓ | — | — |
| Same-Channel View | ✓ | ✓ | — | — |
| Outliers | ✓ | ✓ | ✓ | — |
| Price Trajectory (W5-only) | — | — | — | ✓ |
| Cumulative Depreciation Summary (W5-only) | — | — | — | ✓ |
| Cumulative VIN aging (W5-only) | — | — | — | ✓ |
| Methodology Notes | ✓ | ✓ | ✓ | ✓ |
| Caveats | ✓ | ✓ | (optional) | ✓ |
| Data Quality Notes | ✓ (if non-empty) | ✓ (if non-empty) | ✓ (if non-empty) | ✓ (if non-empty) |
| Key Signals | ✓ | ✓ | ✓ | ✓ |
| Next Steps | (optional) | (optional) | (optional) | ✓ (always — points to W1) |
| Self-check footer | ✓ | ✓ | ✓ | ✓ |

---

## Money format

- US profiles: `$` prefix, comma thousands, no decimals. `$28,500`.
- UK profiles: `£` prefix, comma thousands, no decimals. `£18,250`.
- Percentages: one decimal place.
- Miles: comma thousands, no unit needed inside the Miles column; suffix ` mi` elsewhere in narrative prose. `32,100` in the table; `32,100 mi` in the Market Snapshot.

## Unsupported countries

**CA (Canada):** Not supported by this skill. The skill's `Before you start` country routing halts on `country == "CA"` with a user-facing message rather than producing misleading cross-border results.

---

## Price Trajectory  (W5-only — always when `listing_count >= 1`)

W5-specific table:

```
Price Trajectory
| Date | Dealer | Type | Inv | Price | Miles | DOM | CPO? |
|------|--------|------|-----|-------|-------|-----|------|
| <last_seen_at_date> | <dealer_name> | F/I/— | new/used/— | $<price> | <miles> | <dom> | Y/N/— |
...
```

**Inv column** — `new` / `used` / `—` based on `inventory_type`.

**Type column** — `F` / `I` / `—` based on `dealer_type` (history rows commonly lack this; default `—`).

**CPO? column tri-state rule:**
- `is_certified == True` → `Y`
- `is_certified == False` → `N`
- `is_certified is None` → `—`

When `cpo_ever is None`, render a caveat below the table: *"CPO history signal unavailable for this VIN — confirm CPO status with the user before pricing."*

When `cpo_ever is True AND current.is_certified is None`, render: *"⚠ This vehicle was CPO at one or more historical listings; the current listing's CPO status is unknown — confirm with the seller before pricing."*

---

## Cumulative Depreciation Summary  (W5-only)

```
Cumulative VIN aging:        <max(dom_active across listings)> days
Total cumulative price change: <cum_change_pct>%   (positive = depreciated; negative = appreciated)
Average drop per listing-hop:  $<avg_drop> over <listing_count - 1> hops
Distinct dealers:              <dealer_count>   (provenance: <dealer_count_source>)
```

When `dealer_count_source == "dealer_name"`, append the caveat: *"(name-based count; dealer_id unavailable in history rows — count may be inflated by name variations)."*

When `dealer_count_source == "mixed"`, append: *"(mixed coverage; some history rows lack dealer_id and may be name-merged or under-merged)."*

**Listing-vs-transaction caveat (always render when `listing_count >= 2`):**
> *Prices reflect listing asks across rooftops, not realized sale prices — a 15% cumulative drop indicates asking-price softening, not buyer-paid drops.*
