# W5 — Competitor Price Movement

Triggered by "who dropped their price", "who is undercutting me", "aggressive competitors near me", etc. The focus is on what other dealers did recently — not on pricing a specific subject.

**US-only by canonical path** — UK profiles route to the W5 analogue in `references/country-uk.md` lines 105–107 (UK uses `search_uk_active_cars` with same 3-call shape; `price_change` filter works the same way; UK has no `get_sold_summary`, so the response matrix's `MOS_TIGHT_THRESHOLD` override doesn't fire on UK).

**v1.8.0+** — W5 is now scripted end-to-end. Aggregations (dealer grouping, undercut detection, drop/raise rate, response matrix) come from `scripts/aggregate_w5_signals.py`. The 9-col Drop table comes from `scripts/render_comp_set_table.py --mode=9col-drops`. No LLM-side hand-rolling on any aggregate, threshold, or rendered cell — same discipline as W1/W4 post-revamp.

## Required inputs

- **YMMT** at minimum: `{year, make, model}`. `trim` is **optional** — see "Trim handling" below.
- **No subject VIN** required (W5 is competitive intelligence about other dealers).
- **User reference unit** is OPTIONAL but unlocks the response matrix:
  - `--user-reference-price <X>`: anchors the match/split/hold algorithm
  - `--user-reference-miles <X>`: enables mileage moat detection
  - `--user-reference-dom <X>`: enables DOM-delta urgency modulation
  - `--user-reference-cpo true|false`: enables bidirectional CPO adjustment
  - `--user-reference-vin <V>` and/or `--user-dealer-id <id>`: filter user's own listings from results
  - `--user-cost-floor <X>`: never recommend a suggested_price below this

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | *"W5 (US flow) is unavailable on UK profiles. UK has its own W5 analogue: 3 calls via `search_uk_active_cars` per `references/country-uk.md` lines 105–107; no `get_sold_summary`, so MoS-tight-market override doesn't fire on UK."* |
| `profile.location.country == "CA"` | Halt per SKILL.md rule 3. |
| `profile.preferences.default_inventory_type == "both"` | Halt-and-ask per SKILL.md rule 4. |
| `profile.session.dealer_type_lower is None` | Halt per SKILL.md rule 4. |

### Year fallback (v1.8.1+)

`year` is **optional** in v1.8.1+. When absent, default
`year_range='<current_year - 2>-<current_year>'` and pass to all Wave B
calls. Emit DQ event (g) *"Year inferred from last 3 model years (no
explicit year supplied)"* and surface as Key Signal at top of render. Pass
the `year_range_inferred=true` flag to `aggregate_w5_signals.py` (via
`--year-range-inferred true`) so the renderer can source the bullet from
its output passthrough.

### Radius reconciliation (v1.8.1+ doc note)

Radius reads `session.radius_mi_clamped` from the loaded profile (default
50 mi per `profile.preferences.default_radius_miles`). **Never hardcoded.**

## Wave A — facet discovery (single call, optional)

Fires only when user-typed YMMT casing is untrusted (no prior `decode_vin_neovin` or facet discovery in the session). Cross-reference `references/facet-discovery.md`. If facet discovery returns 0 results, halt.

### Wave A decode (v1.8.1+) — when `--user-reference-vin` supplied

When `--user-reference-vin <V>` is supplied, fire `decode_vin_neovin(<V>)`
in **parallel with** facet discovery (so Wave A grows from 0–1 calls to
1–2 calls; both run in a single batch). Pipe through `parse_decode.py`
and extract:

- `drivetrain` (e.g., "FWD" / "AWD" / "RWD" / "4WD")
- `fuel_type_category` (e.g., "Gasoline" / "Hybrid" / "EV" / "Diesel")

Pass both as facet filters on Wave B's 4 calls (5.a, 5.b, 5.c, 5.d) when
both fields are present. This eliminates sub-trim variant noise (e.g.,
Camry SE rolling ICE-FWD + AWD + Hybrid SE together) at the server level.

**Edge cases:**
- Decode `ok=false` (truncation, invalid VIN, 5xx) → fall back to no facet
  inheritance + emit DQ event (a) + Key Signal *"Reference VIN decode
  failed; Wave B fired without drivetrain/fuel_type filters."*
- Decode succeeds but drivetrain or fuel_type is null → pass only the
  fields that decoded; null fields are not added as filters.
- Truncation envelope on decode → standard `Write` + `--file <path>`
  recovery per `references/truncation-recovery.md`.

**When no reference VIN supplied:** Wave B fires without
drivetrain/fuel_type filters (existing v1.8.0 behavior). The
`aggregate_w5_signals.py` heterogeneity detection
(`heterogeneity.is_heterogeneous`) is the safety-net signal — surfaces a
Key Signal warning that aggregate signals span variants.

## Wave B — 4 parallel calls (NEW: was 3; v1.8.0 adds sold-90d for MoS)

All independent (no cross-deps) — issue every call in a SINGLE batch. Wall-clock ≈ 25s.

### 5.a Price-Drop scan (corrected sort per C4)

```
search_active_cars:
  year, make, model[, trim]
  zip, radius=<session.radius_mi_clamped>, car_type=<session.car_type_resolved>
  price_change="negative"
  price_range="1-*"
  sort_by="price_change_percent", sort_order="asc"           # deepest drops first (signed; -15% < -5%)
  rows=20
  include_dealer_object=true, include_build_object=true
  fetch_all_photos=false, include_mc_dealership_object=false,
  include_finance=false, include_lease=false, include_relevant_links=false
→ parse_search.py    # NO --subject-vin (W5 has no subject)
                     # NO --exclude-vins (handled by aggregate_w5_signals self-exclusion flags)
```

Each normalised listing carries `price_change_percent` (signed % from listing root) and `price_change_amount` (signed $ derived by `parse_search.py` lines 88–104). **No per-VIN history lookup needed** — drop signals are baked into the active listing.

### 5.b Price-Raise scan (corrected sort per C4)

```
search_active_cars:
  (same base as 5.a)
  price_change="positive"
  sort_by="price_change_percent", sort_order="desc"          # most-positive first (biggest raises first)
  rows=10
  include_dealer_object=true, include_build_object=true
  (same shaping defaults as 5.a)
→ parse_search.py
```

### 5.c Denominator (active stats)

```
search_active_cars:
  year, make, model[, trim]
  zip, radius, car_type
  rows=0
  stats="price,miles"
  price_range="1-*"                                          # critical: num_found feeds drop_rate / raise_rate denominators (aggregate_w5_signals.py:567-575); without the filter, null-price rows inflate active_count and the rates are biased downward
  include_dealer_object=false, include_build_object=false   # rows=0 → stats-only call
  (same shaping defaults)
→ parse_search.py
```

`num_found` powers the drop_rate / raise_rate denominators. `stats.price.{min,max,median,mean,stddev}` powers the Condensed Market Snapshot.

### 5.d Sold-90d count for MoS (NEW in v1.8.0)

```
search_past_90_days:
  year, make, model[, trim]
  zip, radius, car_type
  rows=0
  stats="price"
  price_range="1-*", sold=true                             # mirrors W1 line 204 — apples-to-apples MoS
  include_dealer_object=false, include_build_object=false
  (same shaping defaults)
→ parse_search.py
```

`sold_count_90d = parse_search.num_found` → MoS denominator. Without this call, the response matrix's `MOS_TIGHT_THRESHOLD` override can't fire.

## Pipeline

```
parse_search.py × 4   # one per 5.a–5.d → step1.json, step2.json, step3.json, step4.json

aggregate_w5_signals.py \
  --drops step1.json \
  --raises step2.json \
  --denominator step3.json \
  --sold-90d step4.json \
  [--user-reference-price <X>] \
  [--user-reference-miles <X>] \
  [--user-reference-dom <X>] \
  [--user-reference-cpo true|false] \
  [--user-reference-vin <V>] \
  [--user-dealer-id <id>] \
  [--user-dealer-name <name>] \                              # v1.8.1+ — fallback when listing.dealer_id is null
  [--user-cost-floor <X>] \
  [--year-range-inferred true|false] \                       # v1.8.1+ — agent passes when year-fallback fired
  > w5-signals.json

render_comp_set_table.py \
  --merged step1.json \                                     # Drop table source: deepest-drops listings
  --user-price ""                                           # W5 has no subject; no ← You marker
  --mode 9col-drops \
  --currency '$' \
  --max-rows 20 \
  > drop_table.md
```

**No `comp_stats.py`, no `merge_comps.py`, no `build_comp_stats_input.py`** — W5 has no subject vehicle and no quartile/verdict computation. The `aggregate_w5_signals.py` script supplies all the signals the renderer needs.

## Trim handling

Branch on user intent at invocation:

| User signal | Behavior |
|---|---|
| User explicitly mentions a trim ("who dropped on my Camry **SE**") | Pass `trim` to all 4 Wave B calls. |
| User supplies a reference unit with a known trim | Use the reference unit's trim. |
| User asks broadly ("what's happening in the **Camry market**") OR omits trim | Skip `trim` filter; render at model-level. Emit Key Signal *"Rendered at model level across all trims; for trim-specific competitor intelligence, re-invoke with trim."* |
| Ambiguous | Halt-and-ask once: *"Pull competitor moves for `<year> <make> <model>` (all trims) or just `<a specific trim if known>`?"* |

## Truncation handling

Cross-reference `references/truncation-recovery.md`. Same `Write` + `parse_search.py --file <path>` recovery as other workflows. Drop scan with `rows=20, include_dealer_object=true, include_build_object=true` is the most likely truncation candidate. DQ event (b) when triggered.

## Render

Cross-reference `assets/output-template.md` "W5 render spec (Competitor Price Movement)" section (lines 1024+). Block list:

1. Headline (W5-specific market-activity form, sourced from `aggregate_w5_signals`)
2. Condensed Market Snapshot (active + drop_rate + raise_rate + MoS)
3. Aggressive-Competitor grouping (lead block; reads `inventory_pressure_dealers` + `deepest_drops`)
4. Drop table (9-col, rendered via `render_comp_set_table.py --mode=9col-drops`)
5. Aggressive-Raisers Key Signal (when `aggressive_raisers` non-empty)
6. Undercut list + Response Matrix (when `response_matrix_fired == true`; per-row `axes_used` audit)
7. Key Signals (3–5 bullets)
8. Next Steps (always; pointer to `/price-check <VIN>` or `/market-distribution`)
9. Self-check footer

**Omitted blocks** (W5 has no subject vehicle): Decoded Specs, Your Price Position, Verdict & Recommended Action, CPO Premium, Same-Channel View, Price/Mileage/DOM Distributions, Outliers (the visible 20-row drop set is what the user wants — outlier flagging via z-score against the full population isn't useful here).

## Field-source rules (L1, L2 — explicit per v1.5.1+ rendering discipline)

- **DOM column** (rendered in the Drop table) reads `parse_search(5.a).listings[*].dom_active` directly. NEVER `dom`, `dom_180`, or `dom_lifetime`.
- **Distance column** reads `parse_search(5.a).listings[*].distance_mi` (pre-flattened by `parse_search.py` line 152 from raw `dist`/`distance` server fields).
- **Old Price** = `price - price_change_amount` (both pre-computed by `parse_search.py` lines 88–104; renderer does NOT re-implement).
- **Drop $** = `−price_change_amount`; **Drop %** = `−price_change_percent`. Renderer reads parser-emitted values verbatim.

## Decision algorithm (response matrix)

When `--user-reference-price` is supplied, `aggregate_w5_signals.py` invokes the 8-axis decision algorithm for each undercut listing. Outputs `recommendation` (HOLD / SPLIT / MATCH / MATCH-AGGRESSIVE), `reason`, `suggested_price`, and `axes_used` (audit trail).

The 8 axes:
- `raw_gap_pct` = (user_price − competitor_price) / user_price × 100  (>0 = we're priced above)
- `cpo_adjustment_pct` = ±CPO_PREMIUM_PCT (6.0%) when CPO mismatch exists, else 0
- `mileage_delta_pct` = (competitor_miles − user_miles) / user_miles × 100  (>0 = we have lower miles → moat)
- `dom_delta` = user_dom − competitor_dom  (>0 = we've been sitting longer)
- `mos` = active_count / (sold_count_90d / 3)  (tight-market indicator)
- `competitor_in_pressure` = competitor.dealer_id in inventory_pressure_dealers
- `adjusted_gap_pct` = raw_gap_pct − cpo_adjustment_pct − (MILEAGE_MOAT_PREMIUM_PCT if mileage moat fires else 0)
- `user_cost_floor` = optional margin protection

Decision tree (apply in order, first match wins):

1. **Skip non-undercuts** (raw_gap_pct ≤ 0): not in undercut_flags.
2. **Outlier ceiling** (raw_gap_pct > 50%): HOLD with data-error caveat.
3. **CPO premium** (user_cpo + adj ≤ noise): HOLD ("Our CPO justifies the premium").
4. **Mileage moat** (delta ≥ 20% + adj ≤ noise): HOLD ("Our unit has lower miles").
5. **Tight market** (mos < 1.5): HOLD ("Demand-driven, no pressure to chase").
6. **Noise floor** (adj ≤ 2%): HOLD.
7. **Split floor** (2% < adj ≤ 5%): SPLIT (midpoint), unless cost-floor breach → HOLD.
8. **Match floor** (adj > 5%): MATCH (full match), with two refinements:
   - Inventory pressure: SPLIT (broader pattern, not isolated drop)
   - Competitor aging > 60d AND we're not: MATCH-AGGRESSIVE
   - Cost-floor breach: HOLD

All thresholds are constants in `aggregate_w5_signals.py` with multi-line rationale docstrings (sourced from automotive industry norms: NADA / Cox Automotive market reports, retail margin conventions, CPO premium research).

## Data Quality event log discipline for W5

- **(a)** MCP tool errors / non-200 responses recovered from — tool name, error_type.
- **(a1)** Facet-discovery retries.
- **(b)** Truncation envelope unwraps via `--file <path>`.
- **(d)** Non-zero `filtered_out` counts from parse_search (e.g., invalid_price rows).
- **(e)** Fallback source attribution (e.g., MoS unavailable when sold-90d call failed).
- **(g)** Workflow branches skipped by design (e.g., trim-level filter when trim absent; response matrix when no reference price).

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| UK profile | `profile.location.country == "UK"` | Halt with route to `country-uk.md` lines 105–107. |
| CA profile | `profile.location.country == "CA"` | Halt per SKILL.md rule 3. |
| `car_type == "both"` | Profile has both | Halt-and-ask per SKILL.md rule 4. |
| Missing `dealer_type` | Profile has none | Halt per SKILL.md rule 4. |
| Free-form YMMT (untrusted casing) | No prior decode/facet | Run Wave A facet discovery once. |
| Facet discovery 0 results | `data.facets.<field>` empty | Halt with "No comps found... try widening radius / dropping trim". |
| Drop scan `num_found == 0` | No dealer dropped recently | Render Headline + Condensed Snapshot; skip Drop table; emit Key Signal *"No price drops detected in the local market for `<YMMT>` in the last 30d."* |
| Thin denominator (`num_found < 6`) | Sparse market overall | Render Headline + Condensed Snapshot; skip Drop table; emit DQ event (e). |
| Trim absent in YMMT | YMM only supplied | Skip `trim` filter on all Wave B calls; render at model-level; emit DQ event (g). |
| Missing `dealer_name` field on listings | parse_search returns null `dealer_name` | aggregate_w5_signals tolerates: groups null-named rows under `<unknown dealer>`; emit DQ event (d) with count. |
| Null `price_change_percent` across all rows | Server returned drop-classified rows but with no pct field | Drop table renders rows with `—` in Old/Drop columns; emit DQ event (e). |
| Truncation envelope on any of 4 Wave B calls | MCP returns `{"result": ...}` truncation wrapper | `Write` + `parse_search.py --file <path>` recovery per `references/truncation-recovery.md`. DQ event (b). |
| Raise scan `num_found == 0` | No recent raises | Skip Aggressive-Raisers Key Signal; raise_rate = 0 in Headline. |
| `aggregate_w5_signals.py` `ok=false` or non-zero exit | Script error or malformed input | Halt with the script's emitted error; do NOT attempt to hand-roll the aggregations. |
| User VIN supplied but doesn't appear in drop scan | `--user-reference-vin` set but not in step1 results | Acceptable; `self_excluded_drops` is empty; response matrix still fires per supplied reference price. |
| sold-90d call (5.d) `ok=false` | Truncation, 5xx, or YMMT mismatch | `mos = null` in aggregate_w5_signals output; response matrix's tight-market override doesn't fire (HOLD path 5 in algorithm). The rest of W5 still renders. DQ event (a). |
| User cost floor breach | Suggested price < user_cost_floor | Algorithm overrides recommendation to HOLD with cost-floor reason. |
| Outlier raw_gap_pct (> 50%) | Likely data error or trim mismatch | Algorithm overrides to HOLD with outlier reason; suggested_price = null. |
| All undercut flags eliminated by self-exclusion | All drops were user's own | undercut_flags = []; response_matrix_fired stays true; render block notes "All drops in scope are your own listings." |

---

The match/split/hold algorithm is **deterministic** — same inputs always produce same recommendation. Thresholds are constants in `scripts/aggregate_w5_signals.py` with rationale docstrings; tunable via single-line edits.
