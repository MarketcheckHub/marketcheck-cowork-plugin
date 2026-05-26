---
name: facet-discovery
description: Recovery flow for `get_sold_summary` returning `make_model_not_found`. One-shot `search_active_cars` facet-discovery call to resolve the canonical casing, then re-issue the failed call. The lone reason this skill ever calls `search_active_cars`.
type: reference
---

# Facet discovery — `make_model_not_found` recovery

`get_sold_summary` does NOT expose facet discovery directly (no `facets`
parameter on its surface). The recovery path for a `make_model_not_found`
error is to facet-discover via `search_active_cars` and re-issue
`get_sold_summary` with the resolved casing.

This is the **only** reason this skill ever calls `search_active_cars`. The
hot path (every workflow's normal Wave A) does not touch it.

## When to run

Run a facet-discovery retry **once** per failing call when:

- A `get_sold_summary` call returns `error_type="make_model_not_found"` (per
  `parse_sold_summary.py` classifier).
- A user-typed `make` or `model` was used without a prior trusted source.

Do NOT retry more than once. If the second attempt also fails, omit the
affected period from the curve / table and emit DQ event (a).

## The discovery call

Issue against `search_active_cars` with the user's typed values plus
location anchors (if available), asking for the canonical facet values:

```
search_active_cars:
  car_type="used"                # always used; we only need facet values
  make=<MAKE-as-typed>           # known upstream; drop if model is the suspect
  facets="model|0|100"           # discover valid model values under make
  rows=0
  country="US"
  include_build_object=false
  include_dealer_object=false
  include_mc_dealership_object=false
  fetch_all_photos=false
  include_finance=false
  include_lease=false
  include_relevant_links=false
```

If the profile carries `tracked_states` with a single state, also pass
`state=<state>`; otherwise omit (national facets are richer).

Pipe through any facet-aware parser the skill has (this skill does not
maintain its own `parse_search.py`; if a future revision adds one, document
its contract in `script-contracts.md`). For v1.0.0, the model reads the
`data.facets.model` array directly from the JSON response — small payload,
no truncation risk.

## Resolving the correct value

- **Case mismatch.** User typed `"toyota"` but facet returns `"Toyota"`. Use
  the facet casing on the retry.
- **Punctuation mismatch.** User typed `"Mercedes Benz"` but facet has
  `"Mercedes-Benz"`. Use the facet value.
- **Cross-endpoint round-trip.** Live testing has shown the casing
  `search_active_cars`'s facet returns is accepted verbatim by
  `get_sold_summary`. Do not re-discover for `get_sold_summary`
  separately — cache and reuse.

## Cache the resolved tuple

Once facet discovery resolves `{make, model}`, cache it on the agent's
scratchpad. Subsequent `get_sold_summary` calls in the same workflow (every
period of a multi-period curve, every dimension of W2 / W3 / W5) use the
resolved values — never re-discover per call.

## Don't facet-discover what's already trusted

If a prior workflow step in this session already surfaced canonical
`{make, model}` (e.g., from a prior W3 brand-ranking row), trust those
values. Facet discovery is a one-shot recovery path, not a default
preflight.

## Not applicable to other facets

Depreciation-tracker does NOT pass `trim`, `body_type` (except as a single
filter on W2 segment calls — and W2 uses the public `body_type` enum
without discovery), `fuel_type_category` (uses the public enum: `EV` /
`ICE` / `Hybrid` / `Unknown` / `Other`), or `year` (not a parameter at all
on `get_sold_summary`). The only facet-discovery surface is `make,model` on
`get_sold_summary` errors.

## DQ event taxonomy

- **(a)** Original `get_sold_summary` call's `error_type` ("make_model_not_found").
- **(a1)** Facet-discovery retry — log: input typed value, facet-resolved value, retry outcome.
- **(c)** If the user-typed value matched a facet by fuzzy comparison and the user confirmed: log the input → confirmed canonical pair.
