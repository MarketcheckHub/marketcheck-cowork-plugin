# Output Template — Competitive Pricer (Appraiser audience)

This file is the **single source of truth** for output block structure, the 8-column comparable citation table schema, value-range phrasing, null-field handling, and the internal self-check. Every workflow (W1 / W2 / W3) renders by adapting this template — see the "Render variations" section at the end for which blocks each workflow uses.

Placeholders in angle brackets `<...>` are interpolated from the in-prompt `stats` object the workflow assembles. Optional blocks are marked `(OPTIONAL)` and only render when the precondition holds.

**Naming convention.** Lowercase placeholders like `<anchor.value>`, `<active.quartile.median>` reference fields on the assembled `stats` object — pull the exact numeric value. Uppercase labels are human-readable section headings.

---

## First line (always)

```
Using profile: appraiser, <ZIP or postcode>, <country>
```

If the profile carries a name field, use it; otherwise the literal `appraiser` is a stable placeholder.

---

## Decoded Specs (W1 / W2)

```
Year:         <year>
Make:         <make>
Model:        <model>
Trim:         <trim>
Body Type:    <body_type>
Drivetrain:   <drivetrain>
Engine:       <engine>
Transmission: <transmission>
MSRP:         $<msrp>
VIN:          <VIN>
Mileage:      <user-supplied miles>
Asking Price: $<user_price>     (render "—" if not supplied)
```

For YMMT-entered W1 (no VIN, no decode), replace the VIN row with `Source: user-supplied YMMT` and omit `body_type`, `drivetrain`, `engine`, `transmission`, `MSRP` rows entirely.

**Null-field rule (hallucination guard):** render any field whose value parses as `null` / missing as literal `—`. Do NOT substitute plausible defaults from model knowledge — e.g., if `engine` decoded to null, do not fill in `"2.0L Turbo I4"` just because the trim sounded turbocharged. The decoder's silence is authoritative.

---

## Headline (W1 / W3)

### W1 Headline

**One sentence** by default. Names the **anchor source**, the **anchor value**, and (when an asking price was supplied) the **position vs anchor**.

```
<Year> <Make> <Model> <Trim> in <profile.location.state>:
anchored on <anchor.label> of $<anchor.value> (n=<anchor.n>).
[Asking price $<user_price> sits <gap_pct>% <above|below|aligned with> the anchor — <band-label>.]
```

Where `<anchor.label>` is one of:

- `"realised sold-90d trim median"` when `anchor.source == "sold-90d"`
- `"<anchor.n>-comp active-listing median"` when `anchor.source == "active-quartile"`

Band labels (replace the dealer-side verdict vocabulary):

- `|gap_pct| ≤ 3%` → **Aligned with anchor**
- `3% < |gap_pct| ≤ 8%` → **Modestly above / below anchor**
- `|gap_pct| > 8%` → **Materially above / below anchor**

When `user_price` is not supplied, omit the bracketed second sentence entirely.

**A second sentence is added ONLY when `mileage_advantage.tier == "moat"`** — subject is ≥20% under local comp median miles with ≥`min_comp_count` mileage-bearing comps. That second sentence is `mileage_advantage.moat_phrase` verbatim — a defensibility note the appraiser can copy into their workpaper:

> *"This unit has lower-than-typical miles — <delta_pct>% under the comparable median of <median_comp_miles> mi, which supports an upward adjustment to the value range."*

For `mileage_advantage.tier == "modest"` (10–20% under median) — no Headline second sentence; surface as a Key Signals bullet only.

**Gap precision rule.** Render `<gap_pct>` with **two decimals** when `|gap|` falls within 0.5% of any band boundary (±3% / ±8%); otherwise one decimal. The two-decimal form prevents visual ambiguity at the band edges — `−2.6%` hides whether the underlying number is −2.55% (Aligned) or −2.65% (still Aligned by ±3% rule). At 2dp, `−2.63%` is unambiguously inside the Aligned band.

### W3 Headline (no subject vehicle, no anchor band)

```
<Year> <Make> <Model> [<Trim>] in <profile.location.state>:
<quartile.n> active comps, median $<quartile.median>, p25–p75 $<quartile.p25>–$<quartile.p75>.
[State baseline: avg sale $<state_baseline.weighted_avg_sale_price>
                · avg DOM <state_baseline.weighted_avg_days_on_market> days
                · <state_baseline.total_sold_count> sold across the last <state_baseline.months_included.length> months.]
```

The State Baseline second sentence renders only when `state_baseline` is non-null. When trim is absent, label the scope `(model-level, all trims)`.

---

## Market Snapshot (W1 / W3)

```
Active Comps:          <active.merged_n> within <radius_mi_clamped> mi
                       (pulled <active.pulled_count>, deduped <active.overlap_count>, subject excluded <active.subject_vin_excluded>)
Sold-90d Comps:        <sold_90d.sold_count_90d> trim-matched realised sales
Median Sold-90d:       $<sold_90d.sold_median>     (sold_dom_field: <sold_90d.sold_dom_field>)
Median Days-to-Sell:   <sold_90d.sold_dom_median> days (over <sold_90d.sold_count_90d> realised sales)
Drop Rate (visible):   <active.drop_rate_visible>% of <active.merged_n> visible comps have a recent price drop
Drop Rate (market):    <active.drop_rate_market_wide>% of <active.merged_n_market_wide> total active comps have a recent price drop
State Baseline (<make> <model> across all trims & years in <state>, last 3 full months):
  avg sale $<weighted_avg_sale_price>  ·  avg DOM <weighted_avg_days_on_market> days  ·  sold <total_sold_count>
```

**Standalone note (always, when State Baseline rendered):**

> *State Baseline reflects state-wide sold velocity for the make/model — a broader cut than the trim-specific sold anchor in the Headline. Use it for defensibility context, not direct price comparability.*

When `state_baseline` is null, omit both the State Baseline line and the standalone note. When `state_baseline_skipped_reason` is set, log it as DQ event (e).

---

## Wholesale-vs-Retail Spread (W1, W2 step 3)

```
Franchise (Retail) MarketCheck Price:     $<nocpo_franchise.marketcheck_price>
  Confidence band:                        $<nocpo_franchise.lower_bound>–$<nocpo_franchise.upper_bound>
  Based on:                               <nocpo_franchise.comparables_n> active comps

Independent (Wholesale-proxy) MarketCheck Price:  $<nocpo_independent.marketcheck_price>
  Confidence band:                        $<nocpo_independent.lower_bound>–$<nocpo_independent.upper_bound>
  Based on:                               <nocpo_independent.comparables_n> active comps

Spread (Retail − Wholesale-proxy):        $<spread_franchise_vs_ind>  (<spread_pct>%)
```

The spread is the **wholesale-vs-retail gap** — the appraiser's primary use for the dual channels. A wide spread means the unit has a steeper trade-in / retail offer ladder than its peers; a narrow spread means the channels are converging.

**When a channel's MarketCheck Price is unavailable** (prediction call truncated unrecoverable or `ok=false`):

```
Franchise (Retail) MarketCheck Price:     —  (prediction call truncated; using comp median as anchor)
```

**When NEITHER channel produced a usable predicted price** (YMMT-only branch, or both calls failed), omit the entire Wholesale-vs-Retail Spread block and render in its place:

```
Anchor: $<anchor.value> (<anchor.label>)
```

---

## CPO Premium (W1, when CPO branch fired) (OPTIONAL)

```
CPO Premium

  Franchise (Retail):              +$<premium_franchise>     (+<pct_franchise>%)
  Independent (Wholesale-proxy):   +$<premium_independent>  (+<pct_independent>%)
```

**No "Net Margin from CPO" line.** That requires a `cpo_certification_cost` field the appraiser plugin's onboarding doesn't gather. The CPO Premium alone is the defensibility component for an appraisal.

Skip the entire block when both `premium_franchise is None` and `premium_independent is None`.

---

## Position vs Anchor (W1, when user_price supplied) (OPTIONAL)

```
Position vs Anchor (<anchor.label>):
  Anchor:               $<anchor.value>  (n=<anchor.n>)
  Subject:              $<user_price>
  Gap:                  $<gap>  (<gap_pct>%) — <band-label>
  Percentile rank:      <percentile> (<source: server/client>, <approx|exact>)
```

The block describes the asking price's position; it does NOT issue an action. The appraiser uses this to gauge defensibility — *"is this asking price reasonable given the anchor and the comp distribution?"*

**Percentile rendering — four states:**

1. `percentile_source == "server"`, `percentile_approx == False` → `<N>th percentile` (exact; covers all `active.merged_n`).
2. `percentile_source == "server"`, `percentile_approx == True` → `~<N>th percentile (approx)`.
3. `percentile_source == "client"`, `percentile_bounded` non-null → `<low>th – <high>th percentile (bounded — visible set only)`.
4. `percentile_source == "client"`, `percentile_bounded` null → `<N>th percentile (visible set)`.

---

## Price Distribution (W1 / W3)

```
Price Distribution (n=<quartile.n>, source: <stats_source>)
  Min:          $<min>
  p25:          $<p25>
  Median:       $<median>
  p75:          $<p75>
  Max:          $<max>
  Mean:         $<mean>
  Std Dev:      $<stddev>
```

When `active.merged_n` differs from the visible count rendered in the Comparable Citation table, header reads `n=<quartile.n> · <visible_n> in table`.

When `stats_source == "server"`, the distribution covers the full `num_found`; when `client`, it covers only the visible merged set (and the percentile block renders bounded states).

---

## Active Mileage Distribution (W1 / W3)

Sourced from the asc-pull `stats.miles` (W1) or B.f's `stats.miles` (W3) — NOT the sold-90d miles, which feeds only the mileage advantage check.

```
Active Mileage Distribution (n=<active_miles_n>)
  Min:          <min> mi
  p25:          <p25> mi
  Median:       <median> mi
  p75:          <p75> mi
  Max:          <max> mi
  Mean:         <mean> mi
  Subject:      <user_miles> mi     (when supplied)
```

When `user_miles` falls outside p5–p95, surface a Key Signals note: *"Subject mileage <user_miles> is at the <position> of the comp distribution — adjustment may be warranted."*

---

## DOM Distribution (W1 / W3)

Buckets via the `dom_thresholds` from `references/profile-loading.md` (default `{fresh: 30, aging: 60}`).

```
DOM Distribution (n=<active.merged_n>, field: dom_active)
  Fresh (0–<fresh_max>d):     <fresh_count>  (<fresh_pct>%)
  Aging (<fresh_max+1>–<aging_max>d):  <aging_count>  (<aging_pct>%)
  Stale (>= <aging_max+1>d):  <stale_count>  (<stale_pct>%)
  Unknown (dom_active null):  <unknown_count>  (<unknown_pct>%)
```

When `unknown_count / active.merged_n > 30%`, surface a Key Signals note: *"<unknown_pct>% of comps have no `dom_active` field — DOM signal is partial."*

---

## Wholesale-vs-Retail Channel View (W3)

```
Wholesale-vs-Retail Channel View
  Franchise (Retail)        (n=<B.c.stats.price.count>):    median $<B.c.stats.price.median>
  Independent (Wholesale-proxy) (n=<B.d.stats.price.count>): median $<B.d.stats.price.median>
  Channel Spread:           $<franchise_median − independent_median> (<pct>%)
```

When a channel's count is 0, render `<channel>: no listings` and emit DQ event (e).

This block is **W3 only**. W1's equivalent is the Wholesale-vs-Retail Spread block (subject-level, ML-predicted) above.

---

## Mileage Advantage (W1 — surface as Headline second sentence OR Key Signals bullet)

Render rule:

- `mileage_advantage.tier == "moat"` → appended to Headline as a second sentence (see Headline section).
- `mileage_advantage.tier == "modest"` → Key Signals bullet:
  *"⚪ Mileage modest advantage: subject is <delta_pct>% under the comparable median of <median_comp_miles> mi (n=<comp_n>)."*
- `mileage_advantage.tier == "none"` → no rendering.

---

## 8-Column Comparable Citation Table (W1 / W3)

This is the **defensibility evidence** — the comparable set the appraiser cites in the workpaper. Schema is fixed across workflows:

```
| Dealer           | Type     | Price    | Miles    | DOM  | Distance | vs Mkt Median | Price Drop?           |
|------------------|----------|----------|----------|------|----------|---------------|-----------------------|
| <dealer_name>    | <F/I/—>  | $<price> | <miles>  | <dom_active or —> | <distance_mi> | <gap_to_median>% | <price_drop or —>     |
```

**Column rules:**

- **Dealer**: `dealer_name` from the listing.
- **Type**: `F` if `dealer_type == "franchise"`, `I` if `dealer_type == "independent"`, `—` if null. Never guess from dealer name.
- **Price**: rounded to nearest dollar; always render even on $0 rows (which should already have been filtered by `price_range="1-*"` + client guard).
- **Miles**: rounded to nearest 100.
- **DOM**: `dom_active` from the listing. Render `—` when `dom_active` is null. Never substitute `dom` or `dom_180`.
- **Distance**: from the `dist` / `distance` server field, flattened to `distance_mi`.
- **vs Mkt Median**: `(price − active.quartile.median) / active.quartile.median * 100`, rendered with sign and 1dp.
- **Price Drop?**: signed dollar change from `price_change_amount` (`−$X`); when null, render `—`.

**Sort ascending by price** unless the workflow explicitly says otherwise (W3 Most-Expensive renders desc).

**Subject row marking (W1, when applicable):** the row in the comp table closest to the subject's `user_price` is marked with ` ← You` after the Dealer column when the subject is in the table. (The subject VIN itself is never in the comp table — it's excluded — but a comparable at a similar price gets the marker.)

**Hallucination guard:** every value in the table is read verbatim from the parsed listing. NEVER infer a missing `dealer_type` from the dealer name, NEVER fill in a missing `dom_active` from the listing's age, NEVER re-derive `price_change_amount` — read it from the parsed field.

**Filtered-out counts:** when the parser dropped rows for self-VIN, $0/null price, or invalid-price, surface a footnote under the table when the total is non-zero:

> *Filtered out: <self_vin_count> shadow listing(s), <invalid_price_count> invalid-price row(s).*

---

## Outliers (W1 / W3)

```
Outliers (z ≥ 2.0 against the trim/model distribution)
  <Dealer> · $<price> · <miles> mi · z=<z-score> · <reason hint when discernable from listing>
  ...
```

When no listings cross the z ≥ 2.0 threshold, render: *"No price outliers detected (z < 2.0 against the distribution)."* — no DQ event (this is the normal case for tight markets).

Reason hints are read from listing metadata where present (e.g., `salvage_title`, `auction_source`, `extreme_miles`). Never fabricate a reason.

---

## Price Trajectory (W2 only)

W2-specific 8-col table, sorted desc by `first_seen_at_date`:

```
| Date         | Dealer              | Type    | Inv   | Price    | Miles   | DOM      | CPO?  |
|--------------|---------------------|---------|-------|----------|---------|----------|-------|
| 2026-04-15   | <dealer_name>       | <F/I/—> | <inv> | $<price> | <miles> | <dom_active or —> | <yes/no/—> |
```

**CPO? column** — tri-state. `yes` when `is_certified == 1` (truthy on wire); `no` when explicitly `0`; `—` when absent. Per `references/cpo.md`, never collapse `None` to `no`.

**Inv column** — `inventory_type` from the listing ("used" / "new"). Never `"certified"` — see CPO doc.

---

## Red Flags (W2 only)

Render only when at least one flag fires:

```
Red Flags
  • Multi-dealer churn:   <dealer_count> distinct dealers across <listing_count> listings (provenance: <dealer_count_source>)
                          — investigate whether this VIN has been an auction return or condition-issue unit.
  • Sharp price drops:    <count> single-step drops ≥ 15% (largest: <pct>% from $<from> to $<to> between <date_from> and <date_to>)
  • Decertified:          previously listed as CPO; current listing is non-CPO. Confirm certification status before finalising.
```

When `cpo_ever == True AND current.is_certified is None`, render the CPO-uncertainty caveat from `references/cpo.md` in place of (or alongside) the Decertified line.

---

## Cumulative VIN aging (W2 only)

```
Cumulative VIN aging (max dom_active across history): <max_dom_active> days
```

When all rows have null `dom_active`: *"Cumulative VIN aging: unavailable (`dom_active` absent across all history rows)."* Emit DQ event (e).

---

## Listing-vs-transaction caveat (W2 only)

Render always when `listing_count >= 2`:

> *Note: history reflects listings (asking prices), not necessarily transactions. A price drop may or may not represent a realised sale.*

---

## Dealer-hop dedup source (W2 only)

Render always:

> *Dealer-hop count computed via `<dealer_count_source>` (per-row dealer identifier).*

---

## Data Quality Notes (all workflows)

Render only when `dq_events` is non-empty. Group by category:

```
Data Quality Notes

  (a) MCP recoveries
      - <tool_name>: <error_type> → recovered via <path>
  (a1) Facet-discovery retries
      - <tool>: <original_value> → <canonical_value>
  (b) Truncation envelope unwraps
      - <parser> on <tool>: 1 unwrap
  (c) Shadow listings
      - Subject VIN also listed at <dealer_name>, <distance> mi
  (d) Filtered-out counts
      - self-VIN: <n>, invalid-price: <n>
  (e) Fallback source attributions
      - <description>
  (f) Parameter substitutions
      - <description>
  (g) Workflow branches skipped by design
      - <description>
```

Categories with no events are omitted. If all categories are empty, the whole block is omitted (do not render an empty header).

---

## Key Signals (all workflows; 3–5 bullets max)

Audience-aligned takeaways for the appraiser — defensibility-relevant. Examples (not exhaustive):

- *"Anchor is realised sold-90d median (n=<sold_count_90d>) — high defensibility against this benchmark."*
- *"Active comp count (n=<merged_n>) below `min_comp_count` (<min_comp_count>) — value range is in a thin-market band; consider widening the radius if the subject is high-value."*
- *"Channel spread is wide ($<X>, <pct>%) — wholesale-to-retail ladder is steep; trade-in offer should reflect this."*
- *"<unknown_pct>% of comps have no `dom_active` — DOM signal is partial."*
- *"Subject mileage is at the <position> of the comp distribution — adjustment recommended."*
- *"⚠ History truncated to first page (num_found=<N>) — partial-coverage trajectory."*

Pick the most defensibility-relevant 3–5 signals; do not exceed 5.

---

## Next Steps (W2 / W3 — optional)

Always include for W2 and W3. For W1, render only when a follow-up workflow makes sense (e.g., the appraiser ran W1 YMMT-only and a VIN-driven re-run would tighten the anchor).

```
Next Steps

  • For a full comparable-backed appraisal with confidence band and methodology notes,
    run `appraiser:vehicle-appraiser`.
  • For current market context against a specific VIN, run `/price-check <VIN>` (W1).
  • To decode a VIN and see its full spec sheet, run `/vin-lookup <VIN>`.
```

Tailor the bullets to what the just-finished workflow surfaced. For example, W2's Next Steps emphasises the W1 + vehicle-appraiser routes since W2 stopped short of a value range. W3's emphasises W1 since W3 had no subject.

---

## Self-check footer (all workflows)

This is an **internal guardrail** — the model runs each check silently before returning and emits a one-line footer summarizing pass status. Do NOT render the full checkbox grid.

**Checks (silent):**

1. Profile loaded and confirmed in first line.
2. Country branch applied (US/UK halt-and-route, CA halt).
3. `price_range="1-*"` set on every search call.
4. `inventory_type` set explicitly on every `get_sold_summary` call (when fired).
5. `default_inventory_type` honored (not hardcoded); "both" halted-and-asked.
6. Dual-channel pricing rendered for every workflow that produces a subject-level prediction.
7. 8-col comparable citation table schema followed.
8. `dom_active` used for DOM bucketing; `dom` / `dom_180` not substituted.
9. CPO branch follows `references/cpo.md` (truthy/explicit-zero/null tri-state).
10. Null fields rendered as `—`; no model-knowledge substitution.
11. Subject VIN excluded from its own comp set (when subject is provided).
12. Data Quality Notes block omitted when empty.

**Footer rendering:**

- **All applicable checks pass** → one-line footer, e.g. `✓ Verified: profile, dual pricing, 8-col schema, $0 filter, dom_active, no null-substitution.` Abbreviate to 5–7 items; drop N/A from the summary.
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated in the output to compensate.

**Never** render N/A items. **Never** render a pass-by-pass checkbox grid. The grid is the model's silent guardrail, not the appraiser's deliverable.

---

## Render variations matrix

Which blocks each workflow uses:

| Block | W1 | W2 | W3 |
|---|---|---|---|
| First line (profile) | ✓ | ✓ | ✓ |
| Decoded Specs | ✓ | ✓ | — |
| Headline | ✓ (subject form) | — | ✓ (market form) |
| Market Snapshot | ✓ | — | ✓ |
| Wholesale-vs-Retail Spread | ✓ | ✓ (step 3 only) | — |
| CPO Premium | ✓ (when CPO) | — | — |
| Position vs Anchor | ✓ (when user_price) | — | — |
| Price Distribution | ✓ | — | ✓ |
| Active Mileage Distribution | ✓ | — | ✓ |
| DOM Distribution | ✓ | — | ✓ |
| Wholesale-vs-Retail Channel View | — | — | ✓ |
| Mileage Advantage | ✓ | — | — |
| 8-col Comparable Citation | ✓ | — | ✓ (cheapest + most-expensive) |
| Outliers | ✓ | — | ✓ |
| Price Trajectory | — | ✓ | — |
| Red Flags | — | ✓ | — |
| Cumulative VIN aging | — | ✓ | — |
| Listing-vs-transaction caveat | — | ✓ | — |
| Dealer-hop dedup source | — | ✓ | — |
| Data Quality Notes | ✓ (if non-empty) | ✓ (if non-empty) | ✓ (if non-empty) |
| Key Signals | ✓ | ✓ | ✓ |
| Next Steps | ✓ (conditional) | ✓ | ✓ |
| Self-check footer | ✓ | ✓ | ✓ |
