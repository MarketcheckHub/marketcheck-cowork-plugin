# W3 — Market Price Distribution

Triggered by "what does the market look like for this model", "market distribution for 2022 Camry", "what's a 2022 RX going for", "give me market context for [YMMT]", etc. **No subject vehicle** — the question is about the market itself: distribution, channel split, cheapest / most-expensive listings, state-level sold velocity baseline.

W3 is a **market-summary workflow** for the appraiser: model-or-trim-level Price/Mileage/DOM distribution + cheapest 8 + most-expensive 5 + Wholesale-vs-Retail Channel View (franchise vs independent server-wide medians) + state-wide sold velocity. No subject vehicle, no asking-price gap, no CPO Premium block.

**US-only** — UK profiles route to the W3 analogue in `references/country-uk.md` (UK has no `get_sold_summary`; the State Baseline block is omitted; UK uses `search_uk_active_cars` + `search_uk_recent_cars` instead of US tools).

## Required inputs

- **YMMT** at minimum: `{year, make, model}` is required; `trim` is **optional** (when supplied, the distribution is trim-specific; when absent, model-level across all trims). Halt if the appraiser supplies only year+make or year alone.
- **No subject VIN, no asking price, no current odometer.** W3 describes the market, not a specific unit.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | Route to `country-uk.md` W3 analogue. |
| `profile.location.country == "CA"` | Standard CA halt per SKILL.md. |
| `profile.preferences.default_inventory_type == "both"` | Halt-and-ask per `references/profile-loading.md`. |
| `profile.location.state` missing on US | *"W3 needs your state for the State Baseline (`get_sold_summary`). Please update your profile or supply a state code inline."* |
| Year+make only (no model) | *"W3 needs at minimum {year, make, model} to describe the market."* |

## Wave A — facet discovery (single call, optional)

Fires only when user-typed YMMT casing is untrusted (no prior `decode_vin_neovin` or facet discovery in this session). Cross-reference `references/facet-discovery.md`. Run discovery once to normalize casing before Wave B; cache the resolved tuple.

If facet discovery returns 0 results, halt with: *"No comps found for <make> <model> [<trim>] within <radius> mi. Try widening radius, dropping trim, or check the spelling of the model/trim string."*

## Wave B — 7 parallel calls (or 6 if no trim)

All independent (no cross-dependencies) — issue every call in a SINGLE batch (multiple MCP tool calls in the same response). Wall-clock ≈ 25s.

### B.a Model-level stats-only `search_active_cars`

```
search_active_cars:
  year, make, model
  zip, radius=<radius_mi_clamped>, car_type=<car_type_resolved>
  rows=0
  stats="price,miles"
  price_range="1-*"
  fetch_all_photos=false, include_mc_dealership_object=false,
  include_finance=false, include_lease=false, include_relevant_links=false,
  include_dealer_object=false, include_build_object=false
```

Provides model-wide distribution scope for the Headline.

### B.b Trim-level stats-only `search_active_cars` (only when trim is known)

```
search_active_cars:
  year, make, model, trim
  zip, radius, car_type
  rows=0
  stats="price,miles"
  price_range="1-*"
  (same shaping defaults as B.a)
```

Server-stats parity-check guard against B.f cheapest-8's `stats=` block. When B.b's `stats.price.median` differs from the quartile median computed over B.f's visible set, emit DQ event (e): *"stats source drift between trim-level call and cheapest-8 call (<diff> $)"*.

### B.c Franchise channel stats-only `search_active_cars`

```
search_active_cars:
  year, make, model[, trim]
  zip, radius, car_type
  rows=0
  dealer_type="franchise"
  stats="price"
  price_range="1-*"
  (same shaping defaults)
```

**Read directly by the renderer** for the Franchise half of the Wholesale-vs-Retail Channel View block. With `price_range="1-*"`, `stats.price.count == num_found` is guaranteed.

### B.d Independent channel stats-only `search_active_cars`

```
search_active_cars:
  year, make, model[, trim]
  zip, radius, car_type
  rows=0
  dealer_type="independent"
  stats="price"
  price_range="1-*"
  (same shaping defaults)
```

**Read directly by the renderer** for the Independent half. Same pattern as B.c.

### B.e `get_sold_summary` (state baseline)

Per `references/sold-summary-safety.md`:

```
get_sold_summary:
  make, model
  inventory_type="Used" or "New" per car_type_resolved
  state=<profile.location.state>
  summary_by="state"
  ranking_measure="sold_count"
  ranking_dimensions="make,model"
  top_n=5, limit=5000
  date_from / date_to               (compute against # currentDate per safety doc)
```

**Do NOT pass `dealer_type`** (per safety doc).

Aggregate the response rows into a single `state_baseline` per the in-prompt pseudo-code in the safety doc.

### B.f Cheapest 8 listings

```
search_active_cars:
  year, make, model[, trim]
  zip, radius, car_type
  sort_by="price", sort_order="asc"
  price_range="1-*"
  rows=8
  stats="price,miles"
  include_dealer_object=true
  include_build_object=true
  fetch_all_photos=false, include_mc_dealership_object=false,
  include_finance=false, include_lease=false, include_relevant_links=false
```

The added `stats="price,miles"` parameter makes this call's output usable as the canonical active-stats source — its output carries both visible listings AND server stats over `num_found`.

### B.g Most-expensive 5 listings

```
search_active_cars:
  year, make, model[, trim]
  zip, radius, car_type
  sort_by="price", sort_order="desc"
  price_range="1-*"
  rows=5
  include_dealer_object=true
  include_build_object=true
  (same shaping defaults as B.f)
```

## Total: 7 parallel calls (or 6 when trim absent), plus optional Wave A facet discovery (1 call) → max 8 calls.

## Truncation handling

Cross-reference `references/truncation-recovery.md`. Apply `Write` + re-read recipe to any W3 call that returns a truncation envelope. Cheapest-8 / most-expensive-5 with `include_dealer_object=true, include_build_object=true` carry slightly more weight per row but are still small (≤8 + ≤5 listings) — truncation is rare but documented.

## Render

Cross-reference `assets/output-template.md` W3 section. Block list (in render order):

1. **Headline** — market-summary sentence anchored on `quartile.{n, median, p25, p75}` and `state_baseline` (when present).
2. **Market Snapshot** — with State Baseline line + scope note per `references/sold-summary-safety.md`.
3. **Price Distribution** — server-sourced over B.f's `num_found`.
4. **Active Mileage Distribution** — server-sourced from B.f's `stats.miles`.
5. **DOM Distribution** — Fresh / Aging / Stale buckets per default thresholds (the appraiser plugin doesn't carry custom DOM thresholds; use `{fresh: 30, aging: 60}`).
6. **Wholesale-vs-Retail Channel View** — `Franchise (Retail) (n=<B.c.stats.price.count>): $<B.c.stats.price.median>` · `Independent (Wholesale-proxy) (n=<B.d.stats.price.count>): $<B.d.stats.price.median>`. Source is B.c and B.d **direct** (server-wide medians), NOT visible-set medians (which are sample-limited to 13 rows). When a channel's n is 0, render `<channel>: no listings` and emit DQ event (e): *"channel-stats source: no franchise/independent listings in radius"*.
7. **Cheapest 8 — 8-col Comparable Citation table** — render from B.f's listings (no `← You` marker since there's no subject).
8. **Most-Expensive 5 — 8-col Comparable Citation table** — same pattern, from B.g's listings.
9. **Outliers** — listings priced ≥ 2.0 standard deviations from the mean (z-scored against the full population via B.b or B.a server stats). When the outlier set is empty (the normal case for tight markets), render *"No price outliers detected (z < 2.0 against the distribution)."* — no DQ event.
10. **Data Quality Notes** — if non-empty.
11. **Key Signals** — 3–5 bullets covering market-health takeaways (channel skew, state baseline alignment, drop frequency context, etc.).
12. **Next Steps** — *"For a defensible valuation of a specific unit against this market, run `/price-check <VIN>` (W1) or `appraiser:vehicle-appraiser` for a full comparable-backed appraisal."*
13. **Self-check footer**.

**Omitted blocks** (W3 has no subject vehicle): Decoded Specs, Position vs Anchor, CPO Premium, Mileage Advantage.

## Trim-optional behavior

When YMMT lacks trim:

- Skip B.b (trim-level stats-only) → Wave B becomes 6 calls.
- B.f, B.g drop the `trim` filter (model-level scope).
- B.c, B.d already model-level (don't pass trim).
- Use B.a (model-level) stats for the Headline + Distributions scope.
- Label the Headline scope as `"<year> <make> <model> (model-level, all trims)"`.
- Emit DQ event (g): *"Trim-level stats-only call skipped by design (no trim filter supplied)."*

## Data Quality event log discipline for W3

- **(a)** MCP tool errors / non-200 responses — tool name, error_type, recovery path. Specifically: `get_sold_summary` make_model_not_found / validation_dimension_limit / network_422 / network_5xx / validation / unknown.
- **(a1)** Facet-discovery retries.
- **(b)** Truncation envelope unwraps via `Write` + re-read.
- **(d)** Non-zero `filtered_out` counts (invalid-price rows in cheapest-8, etc.).
- **(e)** Fallback source attribution — server-stats drift between B.b and B.f; channel n=0 in B.c or B.d; State Baseline `state_baseline_skipped_reason` when non-null.
- **(g)** Workflow branches skipped by design — trim-level call when trim absent; state baseline when error_type unrecoverable.

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| UK profile | `country == "UK"` | Route to `country-uk.md`. |
| CA profile | `country == "CA"` | Standard CA halt. |
| `car_type == "both"` | Profile has "both" | Halt-and-ask. |
| Missing state | `profile.location.state` null | Halt-and-ask. |
| Free-form YMMT casing | No prior decode / facet | Wave A facet discovery. |
| Facet discovery 0 results | `data.facets.<field>` empty | Halt with "No comps found... try widening radius / dropping trim". |
| `num_found == 0` on B.a (model-level) | Empty market | Halt with *"No active listings for <year> <make> <model> in <STATE> within <radius> mi."* |
| Thin market — `num_found < min_comp_count` on B.f | Sparse market | Render Headline + State Baseline (if available); skip Price/Mileage/DOM Distributions (label "Insufficient comps"); skip Outliers; emit DQ event (e). |
| Trim absent in YMMT | YMM only | Skip B.b; render model-level distribution; label Headline scope `(model-level, all trims)`; emit DQ event (g). |
| `get_sold_summary` error | Any error_type | Skip the State Baseline line + emit DQ event (a). Do NOT halt. |
| Truncation envelope on any Wave B call | MCP truncation wrapper | Standard `Write` + re-read recipe. |
| `parse_search` ok=false on cheapest-8 | Critical truncation / 5xx | Render the rest; render Cheapest 8 table as *"Cheapest 8: unavailable (<error_type>)"*; emit DQ event (a). |
| Outlier set empty | No z ≥ 2.0 listings | Render *"No price outliers detected (z < 2.0 against the distribution)."* — no DQ event. |
| `dealer_type` field missing on listings | Cheapest-8 / most-expensive-5 rows have null dealer_type | Channel split block uses B.c / B.d direct (unaffected); 8-col table renders `—` in Type column for null rows; emit DQ event (d) when count > 0. |

---

W3 emits NO subject-vehicle blocks (Position vs Anchor, CPO Premium, Mileage Advantage). For per-unit context against this distribution, route the appraiser to `/price-check <VIN>` (W1) or `appraiser:vehicle-appraiser`.
