# Facet Discovery — Depreciation-Tracker Edition

`get_sold_summary` does NOT expose facet discovery directly (no `facets`
parameter on its surface). The recovery path for `make_model_not_found`
errors is to facet-discover via `search_active_cars` and re-issue
`get_sold_summary` with the resolved casing.

## When to run

Run a facet-discovery retry **once** per failing call when:

- A `get_sold_summary` call returns `error_type="make_model_not_found"`
  (per `parse_sold_summary.py` classifier).
- A user-typed `make` or `model` was used without a prior decoded result.

Do NOT retry more than once. If the second attempt also fails, omit the
affected period from the curve / table and emit DQ event (a).

## The discovery call

Issue against `search_active_cars` with the user's typed values plus
location anchors, asking for the canonical facet values:

```
search_active_cars:
  zip=<profile.zip>, radius=<session.radius_mi_clamped>
  car_type=<session.car_type_resolved>
  make=<MAKE-as-typed>           # known upstream; drop if model is suspect too
  facets="model|0|100"           # discover valid model values under make
  rows=0
  include_build_object=false
  include_dealer_object=false
  include_mc_dealership_object=false
  fetch_all_photos=false
  include_finance=false
  include_lease=false
  include_relevant_links=false
```

Pipe through `parse_search.py --file <path>`. The parser's `facets` field
passes `data.facets` through verbatim (with isinstance guard).

## Resolving the correct value

- **Case mismatch.** User typed `"toyota"` but facet returns `"Toyota"`. Use
  the facet casing on the retry.
- **Punctuation mismatch.** User typed `"Mercedes Benz"` but facet has
  `"Mercedes-Benz"`. Use the facet value.
- **Cross-endpoint round-trip.** In live-call testing, the casing
  `search_active_cars`'s facet returns is accepted verbatim by
  `get_sold_summary`. Don't re-discover for `get_sold_summary` separately —
  cache and reuse.

## Cache the resolved tuple

Once facet discovery resolves `{make, model}`, cache it on the agent's
scratchpad. Subsequent `get_sold_summary` calls in the same workflow (every
period of a multi-period curve, every dimension of W2/W3) use the resolved
values — never re-discover per call.

## Don't facet-discover what's already trusted

If a prior workflow step in this session already resolved the casing (e.g.,
W1's rep-VIN decode succeeded and emitted canonical `{make, model}`), trust
those values. Facet discovery is a one-shot recovery path, not a default
preflight.

## Not applicable to other facets

Depreciation-tracker does NOT pass `trim`, `body_type` (except as a single
filter on W2 segment calls — and W2 uses the public `body_type` enum without
discovery), `fuel_type_category` (uses the public enum: `EV` / `ICE` /
`Hybrid` / `Unknown` / `Other`), or `year` (not a parameter at all). The
only facet-discovery surface is `make,model` on `get_sold_summary`
errors.
