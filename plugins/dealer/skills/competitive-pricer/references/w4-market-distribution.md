# W4 — Market Price Distribution

Triggered by "what does the market look like for this model", "market distribution for 2022 Camry", "what's a 2022 RX going for", etc. **No subject vehicle** — the question is about the market itself: distribution, channel split, cheapest / most-expensive listings, state-level sold velocity baseline.

W4 is a **market-summary workflow**: model-or-trim-level Price/Mileage/DOM distribution + cheapest 8 + most-expensive 5 + by-channel split (franchise vs independent) + state-wide sold velocity. No verdict, no asking-price gap, no CPO Premium block.

**US-only** — UK profiles route to the W4 analogue in `references/country-uk.md` lines 95–103 (UK has no `get_sold_summary`; the State Baseline block is omitted; UK uses `search_uk_active_cars` + `search_uk_recent_cars` instead of US tools).

## Required inputs

- **YMMT** at minimum: `{year, make, model}` is required; `trim` is **optional** (when supplied, the distribution is trim-specific; when absent, model-level across all trims). Halt if the user supplies only year+make or year alone.
- **No subject VIN, no asking price, no current odometer.** W4 describes the market, not a specific unit.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | *"W4 (US flow) is unavailable on UK profiles. UK has its own W4 analogue — see `references/country-uk.md` lines 95–103: 2 stats-only `search_uk_active_cars` calls + cheapest 8 / most-expensive 5 listings via UK tools. No State Baseline (no `get_sold_summary` for UK)."* |
| `profile.location.country == "CA"` | Halt per SKILL.md rule 3 with the standard CA-not-supported message. |
| `profile.preferences.default_inventory_type == "both"` | Halt-and-ask per SKILL.md rule 4: *"Market distribution for used or new?"* Apply the answer for the rest of the session. |
| `profile.location.state` is null/empty (US) | Halt-and-ask: *"W4 needs the dealer's state for the State Baseline (`get_sold_summary`). Please update the profile with `state`."* |
| `profile.session.dealer_type_lower is None` | Halt per SKILL.md rule 4 with the standard franchise-or-independent prompt. |
| User supplied only year+make (no model) | Halt: *"W4 needs at minimum `{year, make, model}`."* |

## Wave A — facet discovery (single call, optional)

Fires only when user-typed YMMT casing is untrusted (no prior `decode_vin_neovin` or facet discovery in this session). Cross-reference `references/facet-discovery.md` line 73: *"User-typed free-form YMMT (e.g. 'honda accord sport') is NOT trusted-casing"*. Run discovery once to normalize casing before Wave B; cache the resolved tuple.

If facet discovery returns 0 results, halt with *"No comps found for `<make> <model> <trim>` within `<radius>` mi. Try widening radius, dropping trim, or check for typos in the model/trim string."*

## Wave B — 8 parallel calls (or 7 if no trim)

All independent (no cross-deps) — issue every call in a SINGLE batch (multiple MCP tool calls in the same response). Wall-clock ≈ 25s.

### 5.a Model-level stats-only `search_active_cars`
```
search_active_cars:
  year, make, model, zip, radius, car_type
  rows=0
  stats="price,miles"
  price_range="1-*"
  fetch_all_photos=false, include_mc_dealership_object=false,
  include_finance=false, include_lease=false, include_relevant_links=false,
  include_dealer_object=false, include_build_object=false
→ parse_search.py
```
Provides model-wide distribution scope context for the Headline.

### 5.b Trim-level stats-only `search_active_cars` (only when trim is known; skip when absent)
```
search_active_cars:
  year, make, model, trim, zip, radius, car_type
  rows=0
  stats="price,miles"
  price_range="1-*"
  (same shaping defaults as 5.a)
→ parse_search.py
```
Server-stats parity-check guard against 5.g cheapest-8's `stats=` block. When 5.b's `stats.price.median` differs from `comp_stats.quartile.median`, emit DQ event (e) "stats source drift between trim-level call and cheapest-8 call".

### 5.c Franchise channel stats-only `search_active_cars`
```
search_active_cars:
  year, make, model[, trim], zip, radius, car_type
  rows=0
  dealer_type="franchise"
  stats="price"
  price_range="1-*"
  (same shaping defaults)
→ parse_search.py
```
**Read directly by the renderer for the By-Channel View block.** Field source: `parse_search(5.c).stats.price.{median, count}`. With `price_range="1-*"`, `count == num_found` is guaranteed.

### 5.d Independent channel stats-only `search_active_cars`
```
search_active_cars:
  year, make, model[, trim], zip, radius, car_type
  rows=0
  dealer_type="independent"
  stats="price"
  price_range="1-*"
  (same shaping defaults)
→ parse_search.py
```
**Read directly by the renderer** for the independent half of the By-Channel View block. With `price_range="1-*"`, `count == num_found` is guaranteed.

### 5.e `get_sold_summary` (state baseline)
Per `references/sold-summary-safety.md` with **W4 deltas**:
- `ranking_measure="sold_count"` (per safety doc line 44)
- `ranking_dimensions="make,model"` (per line 45)

All other params per the canonical safety doc:
- `inventory_type="Used"` or `"New"` per session car_type
- `state=<profile.location.state>` (required)
- `summary_by="state"`
- `top_n=5`
- `limit=5000`
- `date_from` / `date_to` from `scripts/compute_sold_summary_dates.py` (last 3 full calendar months, month-aligned)
- **Do NOT pass `dealer_type`** (per safety doc line 63 — silently suppresses valid data)

→ `scripts/parse_sold_summary.py --aggregate-state <profile.location.state>`

The parser emits `state_baseline.{weighted_avg_sale_price, weighted_avg_days_on_market, total_sold_count, months_included, row_count_for_state}`. The renderer reads these for the State Baseline line — see Section "Render".

### 5.f `search_past_90_days` (sold-90d count for MoS denominator)
**Critical: enumerate full base filter set** (per SKILL.md "Comp-set integrity" rule line 77 — MoS numerator and denominator must share identical filters):
```
search_past_90_days:
  year, make, model, trim, zip, radius, car_type
  rows=0
  stats="price"
  price_range="1-*"
  sold=true
  (same shaping defaults as 5.a)
→ parse_search.py
```

`sold_count_90d = parse_search.num_found` — feeds MoS denominator (`active_count / (sold_count_90d / 3)`). With `price_range="1-*"` + `sold=true`, every matched record has `price ≥ 1` and is sold-classified, so `num_found == stats.price.count` is guaranteed.

When trim is absent, drop `trim` from the filter set; the MoS denominator is then "all sold cars of `<make> <model>` in radius" (model-wide).

### 5.g Cheapest 8 listings
```
search_active_cars:
  year, make, model[, trim], zip, radius, car_type
  sort_by="price", sort_order="asc"
  price_range="1-*"
  rows=8
  stats="price,miles"
  include_dealer_object=true
  include_build_object=true
  fetch_all_photos=false, include_mc_dealership_object=false,
  include_finance=false, include_lease=false, include_relevant_links=false
→ parse_search.py     # NO --subject-vin (W4 has no subject VIN)
                      # NO --exclude-vins (W4 has no VINs to exclude)
```

The added `stats="price,miles"` parameter (vs the W4 reference pre-v1.7.0) makes this call's parse_search output usable as `--asc-parsed` to `build_comp_stats_input.py` — its output carries both visible listings AND server stats over `num_found`.

### 5.h Most-expensive 5 listings
```
search_active_cars:
  year, make, model[, trim], zip, radius, car_type
  sort_by="price", sort_order="desc"
  price_range="1-*"
  rows=5
  include_dealer_object=true
  include_build_object=true
  (same shaping defaults as 5.g)
→ parse_search.py     # NO --subject-vin, NO --exclude-vins
```

## Total: 8 parallel calls Wave B (or 7 when trim absent)

Plus optional Wave A facet discovery (1 call) → max 9 calls total.

## Truncation handling

Cross-reference `references/truncation-recovery.md`. Recipe applies to all W4 calls; `Write` + `parse_search.py --file <path>` (or `parse_sold_summary.py --file <path>` for 5.e) recovery when the MCP returns a truncation envelope. Cheapest-8 / most-expensive-5 with `include_dealer_object=true, include_build_object=true` carry slightly more weight per row but are still small (≤8 + ≤5 listings) — truncation is rare but documented per W1 discipline.

## Pipeline

```
parse_search.py × 6           # 5.a, 5.b, 5.c, 5.d, 5.f, 5.g, 5.h (5.b skipped when trim absent)
parse_sold_summary.py --aggregate-state <STATE>   # 5.e

merge_comps.py --asc <cheapest-8.json> --desc <most-expensive-5.json> > merged.json
                              # Up to 13 listings deduped by VIN

build_comp_stats_input.py \
  --profile <load_profile output> \
  --asc-parsed <cheapest-8.json>      # has both listings AND server stats (since 5.g passes stats=)
  --merged <merged.json> \             # 13 listings deduped
  --sold-price <5.f sold-90d-price.json> \
  --trim-label "<year> <make> <model> <trim>"   # or "<year> <make> <model>" when trim absent
  # NOTE: NO --user-price (W4 has no subject)
  # NOTE: NO --subject-vin (W4 has no subject)
  # NOTE: NO --user-miles
  # NOTE: NO --sold-dom (no dom-stats call in W4)
  # NOTE: NO --drops (no drop scan in W4)
  # NOTE: NO --nocpo-* / --cpo-* (no ML predict in W4)
| comp_stats.py
```

`build_comp_stats_input.py` v1.7.0+ relaxes `--user-price` and `--subject-vin` to optional. With both omitted, the emitted comp_stats input has `user_price=null`, `subject_vin=""`, `subject_miles=null`, `subject_is_certified=false`. `comp_stats.py` guards user_price=None at lines 800, 811, 814, 877 — emits `verdict`, `verdict_quartile`, `verdict_sold_anchor`, `gap_vs_median`, `primary_only.diff/.pct` all as null. The renderer skips the Your Price Position and Verdict & Recommended Action blocks.

### Where each stats-only call's output flows in render

The canonical pipeline above only consumes `cheapest-8.json` + `merged.json` + `sold-90d-price.json` + `sold-summary-aggregate-state`. The other 4 stats-only calls (5.a, 5.b, 5.c, 5.d) feed the renderer DIRECTLY:

- **5.a model-level stats** — Headline scope qualifier (model-wide context line) + Market Snapshot's "Active Comps (model-level)" line. Field source: `parse_search(5.a).stats.price.{count, median}` and `parse_search(5.a).num_found`.
- **5.b trim-level stats** (when fired) — server-stats parity check. Renderer compares `parse_search(5.b).stats.price.median` against `comp_stats.quartile.median`; emits DQ event (e) on mismatch (defense-in-depth against server-side stats drift between separate calls).
- **5.c franchise channel stats** — By-Channel View block, franchise half. Field source: `parse_search(5.c).stats.price.{median, count}`. Server-wide median for the franchise channel.
- **5.d independent channel stats** — By-Channel View block, independent half. Same pattern as 5.c.

This hybrid render pattern (server-wide channel medians from 5.c/5.d direct + visible-set context from `comp_stats.channel_stats`) gives the user accurate market-wide channel signals while preserving the canonical `comp_stats` pipeline for everything else.

## Render

Cross-reference: `assets/output-template.md` — see render-variations matrix W4 column + W4 footnote (v1.7.0+) and W4 Headline variation. Block list (in render order):

1. **Headline** — market headline per the W4 variation in `output-template.md`. Source: `comp_stats.quartile.{n,median,p25,p75}` + `parse_sold_summary.state_baseline.{weighted_avg_sale_price,total_sold_count}`.
2. **Market Snapshot** with State Baseline line + scope note per `sold-summary-safety.md` lines 105–113.
3. **Price Distribution** — server-source over `quartile.n`.
4. **Active Mileage Distribution** — from `comp_stats.mileage_distribution`.
5. **DOM Distribution** — fresh / aging / stale buckets per profile thresholds, from `comp_stats.dom_buckets`.
6. **By-Channel View** — render `Franchise (n=<5.c.stats.price.count>): $<5.c.stats.price.median>  ·  Independent (n=<5.d.stats.price.count>): $<5.d.stats.price.median>`. Source is **5.c and 5.d direct** (server-wide medians), NOT `comp_stats.channel_stats` (which is sample-limited to 13 rows). When channel n is 0, render `<channel>: no listings` and emit DQ event (e) "channel-stats source: no franchise/independent listings in radius".
7. **Cheapest 8-col table** — render via `scripts/render_comp_set_table.py` from the cheapest-8 listings (no `← You` marker since user_price=None).
8. **Most-Expensive 8-col table** — same pattern, from the most-expensive-5 listings.
9. **Outliers** — from `comp_stats.outliers` (z-scored against full-population server stats).
10. **Data Quality Notes** (if non-empty).
11. **Key Signals** — 3–5 bullets covering market-health takeaways (drop rate, channel skew, MoS tier, etc.).
12. **Next Steps** (optional) — suggest `/price-check <VIN>` against this distribution for a specific unit.
13. **Self-check footer** — per shared template's items 1–14, with item 13 W4 N/A clause (v1.7.0+) acknowledging the no-subject pipeline.

**Omitted blocks** (no subject vehicle): Your Price Position, Verdict & Recommended Action, CPO Premium, Same-Channel View (replaced by By-Channel View).

## Trim-optional behavior

When YMMT lacks trim:
- Skip step 5.b (trim-level stats-only) → Wave B becomes 7 calls.
- 5.f, 5.g, 5.h drop the `trim` filter (model-level scope).
- 5.c, 5.d already model-level (don't pass trim).
- Use 5.a (model-level) stats for the Headline + Price/Mileage/DOM Distribution scope.
- Label the Headline scope as `"<year> <make> <model> (model-level, all trims)"`.
- Emit DQ event (g) "Trim-level stats-only call skipped by design (no trim filter supplied)."

## Data Quality event log discipline for W4

Track events per SKILL.md taxonomy (a/b/c/d/e/f/g):

- **(a)** MCP tool errors / non-200 responses — tool name, error_type, recovery path. Specifically: `parse_sold_summary` make_model_not_found / validation_dimension_limit / network_422 / network_5xx / validation / unknown.
- **(a1)** Facet-discovery retries — when 5.a/5.b returned `num_found=0` and a facet lookup resolved correct casing.
- **(b)** Truncation envelope unwraps via `--file <path>` — which parser, which tool.
- **(d)** Non-zero `filtered_out` counts from parse_search (e.g., invalid_price rows in cheapest-8).
- **(e)** Fallback source attribution — server-stats drift between 5.b and 5.g; channel n=0 in 5.c or 5.d; State Baseline `state_baseline_skipped_reason` when not null.
- **(g)** Workflow branches skipped by design: trim-level call when trim absent; sold-summary state baseline when out of state coverage.

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| UK profile | `country == "UK"` | Halt at pre-check (route to `country-uk.md` analogue). |
| CA profile | `country == "CA"` | Halt per SKILL.md rule 3. |
| `car_type == "both"` | Profile has both | Halt-and-ask per SKILL.md rule 4. |
| Missing state | `profile.location.state` null | Halt-and-ask. |
| Missing dealer_type | `profile.session.dealer_type_lower is None` | Halt per SKILL.md rule 4. |
| Free-form YMMT casing | No prior decode / facet | Run Wave A facet discovery once. |
| Facet discovery 0 results | `data.facets.<field>` empty | Halt with "No comps found... try widening radius / dropping trim". |
| `num_found == 0` on 5.a (model-level) | Empty market | Halt with "No active listings for `<year> <make> <model>` in `<STATE>` within `<radius>` mi". |
| Thin market — `num_found < 6` | < 6 active comps | Render Headline + State Baseline (if available); skip Price/Mileage/DOM Distributions (label "Insufficient comps"); skip Outliers; emit DQ event (e). |
| Trim absent in YMMT | YMM only | Skip 5.b; render model-level distribution; label Headline scope `(model-level, all trims)`; emit DQ event (g). |
| `get_sold_summary` make_model_not_found | parse error | Retry once with facet-discovered casing; if still failing, skip State Baseline + DQ event (a). |
| `get_sold_summary` validation_dimension_limit | parse error | Retry once with `ranking_dimensions="make"` only. |
| `get_sold_summary` network_422 | parse error | Verify month-aligned dates; retry once if dates off; otherwise skip State Baseline + DQ event (a). |
| `get_sold_summary` network_5xx / validation / unknown | parse error | Skip State Baseline; emit DQ event (a). Do NOT halt. |
| Truncation envelope on cheapest-8 / most-expensive-5 / stats-only | MCP truncation wrapper | `Write` + `parse_search.py --file <path>` per `truncation-recovery.md`. |
| `parse_search` ok=false on cheapest-8 | Critical truncation / 5xx | Render the rest; render Cheapest 8-col table as "Cheapest 8: unavailable (`<error_type>`)"; emit DQ event (a). |
| Outlier set empty | `comp_stats.outliers == []` | Render Outliers as *"No price outliers detected (z < 2.0 against trim distribution)."* — no DQ event (this is the normal case for tight markets). |
| `dealer_type` field missing on listings | parse_search returns null dealer_type | Channel split block uses 5.c/5.d direct (unaffected); 8-col table renders `—` in Type column for null rows; emit DQ event (d) when count > 0. |

---

W4 emits NO verdict, NO subject-vehicle blocks (Your Price Position, Verdict & Recommended Action, CPO Premium). For per-unit pricing against this distribution, route the user to `/price-check <VIN>` (W1).
