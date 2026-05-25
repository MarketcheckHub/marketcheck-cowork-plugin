# W1 — Price-Check Single VIN (market context for an appraisal)

The defensibility workflow. Triggers on "price this car", "price check this VIN", "what's the market on this one", "is this asking price defensible", "compare pricing on this VIN", etc.

The goal is **not** to issue a verdict or recommended action. It is to surface a **defensible value range** anchored on realised sale prices (preferred when available) or the active-listing quartile distribution (fallback), with a comparable-citation table the appraiser can attach to their workpaper.

## Required inputs

- **VIN** (17 chars matching `^[A-HJ-NPR-Z0-9]{17}$`) — validate before any MCP call. Halt on malformed VIN per `references/profile-loading.md`.
- **Mileage** — required. Halt on missing mileage: *"Please supply the current odometer reading for this VIN. Predicting on the predictor's default 50,000-mile fallback corrupts the anchor."*
- **Asking price** — optional. The value range still renders without it, but the **Position vs Anchor** block (percentile + gap-to-median) is suppressed when the appraiser hasn't supplied one. Use the anchor + spread + comps as the standalone deliverable.

## YMMT-only branch (no VIN)

When the appraiser supplies `{year, make, model, trim}` without a VIN on a US profile:

- **Skip steps 1 and 2 entirely** — no decode (no VIN), no ML prediction (`predict_price_with_comparables` requires a VIN).
- Begin at step 4 (active comp set) using the user-supplied YMMT. **Run facet discovery first** (per `references/facet-discovery.md`) — user-typed YMMT is not trusted-casing.
- Anchor on `sold-90d median` when `sold_count_90d ≥ min_comp_count`; else fall back to active quartile median.
- In the output: skip the Franchise (Retail) MarketCheck Price and Independent (Wholesale-proxy) MarketCheck Price lines in the Wholesale-vs-Retail Spread block; render `Anchor: <sold-90d median>` instead; emit a caveat in Key Signals: *"No MarketCheck Price prediction available — anchored on realised sold-90d comp median."*
- CPO detection still works via active-listing `is_certified` and (optionally) `get_car_history`, so the CPO branch can still run if the appraiser confirms CPO status.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "CA"` | Standard CA-not-supported halt per SKILL.md. |
| `profile.location.country == "UK"` | Route to `references/country-uk.md` W1 adaptation. |
| `profile.location.state` missing on US | *"W1 needs your state (for the State Baseline). Please update your profile or supply a state code inline."* |
| `profile.preferences.default_inventory_type == "both"` | Halt-and-ask: *"Market context on used or new units?"* |
| VIN malformed | Standard VIN-format halt. |
| Mileage missing | *"Please supply the current odometer reading..."* (above). |

## Parallelization — three waves

W1 executes in three parallel waves under the universal wave contract (see SKILL.md). Each wave is a batch of MCP calls fired in a single agent message — multiple `tool_use` blocks in one assistant turn, dispatched concurrently. Wait for the full batch of `tool_result` messages before issuing the next wave.

### Wave A — immediate (no cross-dependencies)

Launched once inputs (VIN, miles, asking price, CPO-stated) + profile (ZIP, country, state) are in hand. Up to 5 calls in parallel:

- `decode_vin_neovin(vin)`
- `predict_price_with_comparables(vin, miles, zip, dealer_type=franchise)` → `nocpo_franchise`
- `predict_price_with_comparables(vin, miles, zip, dealer_type=independent)` → `nocpo_independent`
- `predict_price_with_comparables(vin, miles, zip, dealer_type=franchise,   is_certified=true)` → `cpo_franchise`   — **only if appraiser stated CPO before Wave A**
- `predict_price_with_comparables(vin, miles, zip, dealer_type=independent, is_certified=true)` → `cpo_independent` — same

Each predict call takes `vin` directly; none require decode output. The 4 predicts + decode run concurrently. When the appraiser did NOT state CPO, the two CPO predicts defer to Wave C.

### Wave B — after Wave A decode returns (uses cached YMMT)

Up to 7 calls in parallel, using `{year, make, model, trim}` from the decoded specs:

- `search_active_cars` asc (rows=20, sort_by=price, sort_order=asc, stats="price,miles,dom_active", price_range="1-*", include_dealer_object=true, include_build_object=true)
- `search_active_cars` desc (rows=10, sort_by=price, sort_order=desc, price_range="1-*", include_dealer_object=true, include_build_object=true) — **issued optimistically**. When `asc.num_found ≤ 20` the desc rows duplicate asc rows and dedupe cleanly; when `> 20` it provides tail coverage. Never serialize this decision.
- `search_active_cars` price_change="negative", rows=0 (all shaping knobs off) — market-wide drop count
- `search_past_90_days` stats="price", rows=0, price_range="1-*", sold=true — sold-anchor price stats
- `search_past_90_days` stats="miles", rows=0, price_range="1-*", sold=true — sold-anchor miles stats
- `search_past_90_days` stats="dom_active", rows=0, price_range="1-*", sold=true — sold-90d days-to-sell (PRIMARY) or stats="dom" as FALLBACK
- `get_sold_summary` (state-level baseline, see `references/sold-summary-safety.md` and "State sold velocity" step below)

### Wave C — conditional (rare)

Issued only when Wave B results trigger a branch:

- **CPO-ambiguous path**: when the appraiser did NOT state CPO AND Wave B's asc response has a shadow listing with `is_certified=1` (or the appraiser explicitly asks for a history probe), issue `get_car_history(vin, sort_order=desc, page=1, fields=<canonical-fields>)` + 2 CPO predicts (`is_certified=true`, one per dealer_type). See `references/cpo.md` for the canonical fields string.
- **Thin-market auto-widen**: when `asc.num_found < min_comp_count`, re-issue asc + desc at `radius = min(radius_mi_clamped * 1.5, 100)`. Emit DQ event (g): *"Thin-market auto-widen: radius extended from <X> mi to <Y> mi (asc.num_found < min_comp_count)."*
- **Facet-discovery retry**: when `asc.num_found == 0`, run facet discovery per `references/facet-discovery.md` and retry the failed call once.

### Wall-clock budget (W1)

Wave A ≈ 12–15s · Wave B ≈ 12–15s · Wave C usually skipped. Total MCP roundtrip ≈ 27–30s for the common path, vs. ~144s if serialized.

## Steps

### Step 1 — Decode the VIN

```
decode_vin_neovin(vin=<VIN>)
```

`decode_vin_neovin` responses chronically truncate (~150KB envelopes). The MCP tool will likely emit `Error: result (N chars) exceeds maximum allowed tokens. Output has been saved to <path>` on most real calls. Read the saved file, unwrap the `{"result": "..."}` envelope, `json.loads` the inner string. Extract: `year`, `make`, `model`, `trim`, `body_type`, `drivetrain`, `engine`, `transmission`, `msrp` (when present). Cache for the session. Discard the rest of the response.

Confirm the decoded specs back to the appraiser before proceeding.

### Step 2 — Dual-channel ML prediction

Two `predict_price_with_comparables` calls in parallel (or four when CPO is confirmed up-front — see CPO branch). Both take `vin` directly — no decode dependency.

```
predict_price_with_comparables(vin, miles, zip, dealer_type=franchise)    → nocpo_franchise
predict_price_with_comparables(vin, miles, zip, dealer_type=independent)  → nocpo_independent
```

`predict_price_with_comparables` responses chronically truncate (~100KB envelopes). Apply the `Write` → re-read → `json.loads` recipe from `references/truncation-recovery.md`. Response has **no `data` wrapper** — `predicted_price`, `predicted_msrp`, `active_set_comparables` live at the top level.

For each role, extract:

- `predicted_price` → rename to `marketcheck_price` for the rendering vocabulary.
- `predicted_price_lower_bound`, `predicted_price_upper_bound` — used to render the model's confidence interval inline with the MarketCheck Price.
- `active_set_comparables.length` → `comparables_n`.

**Appraiser-audience framing:**

- `nocpo_franchise.marketcheck_price` renders as **Franchise (Retail) MarketCheck Price**.
- `nocpo_independent.marketcheck_price` renders as **Independent (Wholesale-proxy) MarketCheck Price**.
- The dollar difference between the two is the **Wholesale-vs-Retail Spread**.

Both channels are presented with equal weight — appraisers select the appropriate benchmark for the valuation purpose (trade-in / retail / insurance claim).

### Step 3 — CPO branch (when applicable)

Gate + call shape per `references/cpo.md`. Summary:

- **Confirmed CPO** → fire `cpo_franchise` + `cpo_independent` predicts in Wave A (alongside the non-CPO pair).
- **CPO ambiguous via Wave B shadow** → fire `cpo_franchise` + `cpo_independent` predicts in Wave C.
- **Confirmed non-CPO** → skip the branch; emit DQ event (g): *"CPO branch skipped: appraiser stated non-CPO"*.

Compute the CPO Premium inline:

```
premium_franchise   = cpo_franchise.marketcheck_price   - nocpo_franchise.marketcheck_price
premium_independent = cpo_independent.marketcheck_price - nocpo_independent.marketcheck_price
```

Render via the CPO Premium block in `assets/output-template.md`. **No Net Margin from CPO line** — that requires a `cpo_certification_cost` field the appraiser plugin doesn't gather.

### Step 4 — Active comp set, asc pull

Inline-rendered envelope (NOT truncated to file) is the common case for `search_active_cars` at `rows=20`. Save via `Write` to scratch (per `references/truncation-recovery.md`) then unwrap + parse. **Never hand-key listings.**

```
search_active_cars:
  year, make, model, trim                (verbatim from cached decode specs)
  zip, radius=<radius_mi_clamped>, car_type=<car_type_resolved>
  sort_by="price", sort_order="asc"
  price_range="1-*", rows=20
  stats="price,miles,dom_active"
  include_dealer_object=true
  include_build_object=true
  (fetch_all_photos / include_mc_dealership_object /
   include_finance / include_lease / include_relevant_links = false)
```

**Why `stats="price,miles,dom_active"`.** With these three stats requested, the server returns aggregates over the full `num_found` (not just the visible 20 rows). The quartile / percentile in the Position-vs-Anchor block is server-stats-sourced (broader coverage), with the visible 20 rows powering only the rendered comparable citation table and the per-listing analyses.

**`dom_active`, not `dom`.** Each listing carries up to three DOM variants:

- `dom_active` — **the only field this skill uses** for Fresh/Aging/Stale bucketing and the DOM column.
- `dom_180` — 180-day gap tolerance. NOT used here.
- `dom` — lifetime, cross-dealer accumulator. NOT used here.

When `dom_active` is `None` on a listing, bucket it as **Unknown** and render the DOM column as `—`. Substituting `dom_180` or `dom` would mix seasonal-cycle / lifetime-VIN signals into a current-market bucket.

**Subject-VIN exclusion.** The subject VIN must never appear as its own comp. When `parse_search` would surface the subject VIN in the comp set (which means the subject is listed at a *different* dealer — a **shadow listing**), exclude it from the comp-stats input AND log DQ event (c) with the shadow-dealer name. The appraiser needs to know their VIN is out there elsewhere.

**On `num_found == 0`**, run a facet-discovery retry per `references/facet-discovery.md`. On still-zero, degrade the value range to a thin-market block.

### Step 5 — Active comp set, desc pull (tail coverage)

Issued optimistically in Wave B (NOT serialized on `asc.num_found > 20`). The cost of one extra call when `num_found ≤ 20` is cheaper than a full roundtrip's wait.

```
search_active_cars (same base filters as asc):
  sort_by="price", sort_order="desc", rows=10
  price_range="1-*"
  include_dealer_object=true, include_build_object=true
```

**Merge asc + desc.** Dedupe by VIN with desc-first on duplicates (desc rows carry the top-of-market listings, preferred when a mid-distribution VIN shows up in both). Exclude the subject VIN. Track `overlap_count` and `pulled_count = asc.kept_count + desc.kept_count`; `merged_n = pulled_count − overlap_count − subject_excluded`. **Do not hand-roll a custom merge** — follow the contract verbatim.

**Thin-market auto-widen:** if `asc.num_found < min_comp_count`, re-issue the asc + desc pair in Wave C at `radius = min(radius_mi_clamped * 1.5, 100)` and surface the widening in the Market Snapshot. Emit DQ event (g).

### Step 6 — Price-drop velocity (market-wide)

```
search_active_cars:
  same base filters + price_change="negative"
  rows=0
  include_dealer_object=false, include_build_object=false
  (all other shaping knobs = false)
```

Extract `num_found` as `drops_market_wide_count`. Compute two drop rates:

- `drop_rate_visible` = (count of visible comps in the merged set with non-null `price_change_amount < 0`) / `merged_n`
- `drop_rate_market_wide` = `drops_market_wide_count / asc.num_found`

The Market Snapshot block renders both — visible rate tells the appraiser what the rendered table shows; market-wide rate is the broader-market signal.

### Step 7 — Sold-90-day aggregates (three single-field stats calls)

`search_past_90_days` rejects multi-field stats calls — fire three single-field stats calls in parallel:

```
search_past_90_days × 3:
  base: year, make, model, trim (verbatim), zip, radius, car_type, rows=0,
        price_range="1-*", sold=true
  a. stats="price"        → stats.price.{min,max,mean,median} + num_found
  b. stats="miles"        → stats.miles.*
  c. stats="dom_active"   → stats.dom_active.*  (PRIMARY)
     stats="dom"          → stats.dom.*         (FALLBACK if upstream rejects "dom_active";
                                                 log DQ event (e) with field-source attribution)
```

**Why `price_range="1-*"` + `sold=true` are load-bearing.** `sold=true` narrows from "all expired listings" (which include wholesale-out, withdrawn, and transferred records — ~10% of expired records) to records the upstream classifies as actually sold. `price_range="1-*"` filters out null/$0-priced records server-side. With both filters, every matched record has `price ≥ 1`, so `num_found == stats.price.count` is guaranteed.

Extract: `sold_count_90d = stats.price.count` (== `num_found`); `sold_median = stats.price.median`; `sold_mean = stats.price.mean`; `sold_dom_median = stats.dom_active.median` (or `stats.dom.median` fallback); `sold_dom_field` ∈ `{"dom_active", "dom", null}`.

Use the same `{year, make, model, trim, car_type, zip, radius}` filter set as step 4.

**Anchor selection:** if `sold_count_90d ≥ min_comp_count`, the **anchor** is `sold_median` (the realised-sales anchor). Otherwise the anchor is `quartile.median` from the merged active comps (the active-quartile fallback). The Headline names the anchor source.

### Step 8 — State sold velocity

Per `references/sold-summary-safety.md`:

```
get_sold_summary:
  make, model                       (verbatim)
  inventory_type="Used"             (or "New" if car_type=new)
  state=<profile.location.state>    (required)
  summary_by="state"
  ranking_measure="average_days_on_market"
  ranking_dimensions="make,model"
  top_n=5, limit=5000
  date_from / date_to               (compute against # currentDate per safety doc)
```

Aggregate the response rows that match the state into a single `state_baseline = {state, total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, months_included, row_count_for_state}` per the in-prompt aggregation pseudo-code in the safety doc.

**Do NOT pass `dealer_type`.** Per safety doc — including it silently suppresses valid data.

On parser error, branch per the error-type table in the safety doc. Skip the state baseline line on any unrecoverable error; never halt the workflow for it.

**Scope disclosure.** Render the State Baseline with the scope qualifier inline: *"State Baseline (<make> <model> across all trims & years in <STATE>, last 3 full months): avg sale $X · avg DOM N days · sold N"*. Emit the one-line standalone note below the Market Snapshot when the State Baseline rendered.

### Step 9 — Compute the stats block

Combine the parsed outputs into a single in-prompt `stats` object that the renderer consumes:

```
stats = {
  subject:                    { vin, year, make, model, trim, body_type, drivetrain, engine, transmission,
                                msrp, user_price, user_miles, user_cpo },
  marketcheck_predict: {
    nocpo_franchise:          { marketcheck_price, lower_bound, upper_bound, comparables_n } | null,
    nocpo_independent:        { ... } | null,
    cpo_franchise:            { ... } | null,
    cpo_independent:          { ... } | null,
    premium_franchise:        cpo_franchise.marketcheck_price - nocpo_franchise.marketcheck_price | null,
    premium_independent:      cpo_independent.marketcheck_price - nocpo_independent.marketcheck_price | null,
    pct_franchise:            premium_franchise / nocpo_franchise.marketcheck_price * 100 | null,
    pct_independent:          premium_independent / nocpo_independent.marketcheck_price * 100 | null,
    spread_franchise_vs_ind:  nocpo_franchise.marketcheck_price - nocpo_independent.marketcheck_price,
    spread_pct:               spread_franchise_vs_ind / nocpo_independent.marketcheck_price * 100
  },
  active: {
    merged_n, pulled_count, asc_n, desc_n, overlap_count, subject_vin_excluded, shadow_dealers,
    quartile:                 { n, min, p25, median, p75, max },
    server_stats:             { price:{min,max,median,mean,stddev,count}, miles:{...}, dom_active:{...} },
    drop_rate_visible, drop_rate_market_wide, drops_market_wide_count,
    dom_buckets:              { fresh, aging, stale, unknown }
  },
  sold_90d: {
    sold_count_90d, sold_median, sold_mean, sold_dom_median, sold_dom_field
  },
  state_baseline:             { state, total_sold_count, weighted_avg_sale_price,
                                weighted_avg_days_on_market, months_included, row_count_for_state } | null,
  state_baseline_skipped_reason: "all_zero" | "no_matching_rows" | "<error_type>" | null,
  anchor: {
    source:                   "sold-90d" | "active-quartile",
    value:                    sold_median if sold_count_90d >= min_comp_count else quartile.median,
    n:                        sold_count_90d if sold_anchor else quartile.n,
    label:                    "realised sold-90d trim median" if sold_anchor else "active-listing median"
  },
  position_vs_anchor: {  # only when user_price is supplied
    gap:                      user_price - anchor.value,
    gap_pct:                  gap / anchor.value * 100,
    percentile:               <inline computation against server_stats or visible quartile>,
    percentile_source:        "server" | "client",
    percentile_approx:        true | false,
  },
  mileage_advantage: {  # tiered output; see "Mileage advantage" below
    tier:                     "moat" | "modest" | "none",
    is_moat,
    moat_phrase,
    delta_pct,
    median_comp_miles
  },
  thin_market:                true if active.merged_n < min_comp_count else false,
  dq_events:                  [ (type, message) … ]
}
```

This object is the **single source the renderer reads**. The model assembles it once after the waves return and renders the output blocks by reading named fields. Do NOT re-derive any field during rendering.

### Step 10 — Render

Read `assets/output-template.md` first — it is the single source of truth for block structure, the 8-column comparable citation table schema, value-range phrasing, null-field rule, and the self-check. Render the W1 block set per the template.

## Mileage advantage

A defensibility signal — when the subject's mileage is materially under the median comp mileage, it justifies an upward adjustment.

- `tier == "moat"`: `delta_pct ≥ 20%`, `merged_n ≥ min_comp_count` (comps with miles), subject strictly under median. Renders a second sentence on the Headline: *"This unit has lower-than-typical miles — <delta_pct>% under the comparable median of <median_comp_miles> mi, which supports an upward adjustment to the value range."*
- `tier == "modest"`: `10% ≤ delta_pct < 20%`. Renders as a Key Signals bullet only — no Headline second sentence.
- `tier == "none"`: `delta_pct < 10%`, insufficient comps, or subject at/above median. No rendering.

The 20% / 10% thresholds are constants in this skill. They mirror the reference's `comp_stats._mileage_moat` thresholds; do not tune them inline.

## Anchor band labels (replaces dealer-side "verdict bands")

When the appraiser supplies an asking price, the **Position vs Anchor** block names the position. Bands:

- `|gap_pct| ≤ 3%` → **Aligned with anchor**
- `3% < |gap_pct| ≤ 8%` → **Modestly above / below anchor**
- `|gap_pct| > 8%` → **Materially above / below anchor**

These are **descriptive labels**, not action verdicts. The block reads:

```
Position vs Anchor (<anchor.label>):
  Anchor:               $<anchor.value>  (n=<anchor.n>)
  Subject:              $<user_price>
  Gap:                  $<gap> (<gap_pct>%) — <band label>
  Percentile rank:      <percentile> (<source: server/client>, <approx/exact>)
```

The appraiser uses this to decide whether the asking price is defensible given the anchor — not whether to issue a price action.

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| Profile country == CA / other | — | Standard halt per SKILL.md. |
| Profile country == UK | — | Route to `country-uk.md` W1 adaptation. |
| Profile state missing (US) | — | Halt-and-ask. |
| Mileage missing | — | Halt-and-ask. |
| VIN malformed | — | Standard VIN-format halt. |
| Decode `ok=false` | Truncation unrecoverable / shape error / 5xx | Continue — render Decoded Specs as `Source: user-supplied YMMT` if known; otherwise halt and ask for YMMT. |
| Predict `ok=false` for one role | Truncation unrecoverable on one of the 2-4 predicts | Render that channel's MarketCheck Price as `—` with a caveat; continue with the surviving channel. |
| All 4 predicts `ok=false` | Every predict role failed | Render Anchor on sold-90d median (if available) or quartile median; emit caveat: *"MarketCheck Price predictions unavailable; anchored on <source>."* |
| `asc.num_found == 0` | Empty market on first call | Facet-discovery retry per `references/facet-discovery.md`. On still-zero, render thin-market block, skip quartile / percentile, surface only the predict / sold-anchor lines. |
| `asc.num_found < min_comp_count` (thin market) | Sub-min_comp active set | Trigger thin-market auto-widen in Wave C (subject premium gating not applied here — the appraiser plugin doesn't carry `msrp` thresholds). Then render thin-market block if still < min_comp_count. |
| Subject VIN found in active comp set (shadow listing) | `subject_vin` in merged set | Exclude from quartile/percentile; emit DQ event (c) with shadow-dealer name(s); render a Key Signal note: *"⚠ Subject VIN is also listed at <other dealer>, <distance> mi away — verify this isn't a duplicate listing of the appraisal target."* |
| Sold-90d call truncated unrecoverable | — | `sold_count_90d = 0`, anchor falls back to active quartile; render caveat. |
| State baseline call failed | Any error_type per safety doc | Skip the State Baseline line, render DQ event (a). |
| Pagination on `get_sold_summary` rows | — | Not applicable — the limit=5000 + tight ranking_dimensions cap is sufficient for state baseline. |

## Data Quality event log discipline for W1

Track and surface these events under the Data Quality Notes block when they fire:

- **(a)** MCP tool errors / non-200 responses recovered from — tool name, error_type, recovery path.
- **(a1)** Facet-discovery retries — original value, resolved value, tool.
- **(b)** Truncation envelope unwraps — count + per parser (decode / predict / search).
- **(c)** Subject VIN found in active comp set at a different dealer — dealer name + distance.
- **(d)** Non-zero filtered-out counts (self-VIN match, $0 rows, invalid-price rows) — totals by category.
- **(e)** Fallback source attribution — e.g., sold-90d `dom` used because upstream rejected `dom_active`; State Baseline skipped reason.
- **(f)** Parameter substitution — e.g., `price_range="1-*"` used in place of `price_min=1`.
- **(g)** Workflow branches skipped by design — *"CPO branch skipped: appraiser stated non-CPO"*; *"Thin-market auto-widen not triggered: num_found ≥ min_comp_count"*; etc.

If the list is empty, omit the Data Quality Notes section entirely (do not render an empty header).
