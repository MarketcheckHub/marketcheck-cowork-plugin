# Facet discovery retry

Per the MarketCheck server, `make`, `model`, `trim`, `body_type`, `fuel_type`, `drivetrain`, and similar facet-backed parameters are **exact-match against indexed values**. A mis-spelled or mis-cased value returns `num_found == 0` silently — no hint that the filter was wrong. Facet discovery is the one-shot recovery for that class of zero-result.

## When to run

Run a facet-discovery retry **once** per search call when:

- A filtered `search_active_cars` / `search_past_90_days` / `search_uk_active_cars` / `search_uk_recent_cars` returns `num_found == 0` AND the filter set included any of: `make`, `model`, `trim`, `variant` (UK).
- A `get_sold_summary` call returned a `make_model_not_found`-style error.

Do NOT retry more than once per call — repeated zero-result retries waste calls and budget.

## The discovery call

Issue a facet call with the SAME location filters (`zip` + `radius`) AND any facet values that were trusted upstream (e.g., the decoded `make` if only `model` / `trim` are suspect). Drop the facet values you're trying to resolve; keep the rest:

```
search_active_cars:
  zip, radius, car_type
  make=<MAKE>                       (known upstream of the zero result)
  facets="model|0|100,trim|0|200"   (discover valid values)
  rows=0
  include_build_object=false
  include_dealer_object=false
  include_mc_dealership_object=false
  fetch_all_photos=false
  include_finance=false
  include_lease=false
  include_relevant_links=false
```

The response's `data.facets.model` and `data.facets.trim` are arrays of `{item, count}` — the **canonical facet values** the server will accept on a filtered call. Read `data.facets.<field>` from the unwrapped response; the field passes through verbatim.

## Retry ordering when multiple facets could be wrong

Drop the most-specific filter first. Start by removing just `trim` (or `variant` on UK) — discover the trim facet under the known `{make, model}`. If that discovery call also returns zero, drop `model` too and discover `model` under `make`. Only drop `make` as a last resort: make mismatches are rare, and when they happen the user has typed a bad make string — ask rather than guess.

## Resolving the correct value

- **Case mismatch.** Decode returned `make="bmw"` but the facet returns `"BMW"`. Resolve with the casing the facet returned — pass `make="BMW"` on the retry.
- **Punctuation mismatch.** Decode returned `model="X5 M"` but facet has `"X5M"` (no space). Use the facet value.
- **Trim concatenation.** Decode returned `model="RX"` + `trim="350"` but facet has `model="RX"` + `trim="350 F Sport"`. If multiple trim facets match the user's spec, prefer the one whose `item` contains the user-stated distinguishing token (e.g., "F Sport"). If ambiguous, ask the appraiser to disambiguate.
- **Ordering.** Facet order is by count desc by default — the top entry is the most common, but not necessarily the user's target. Match by substring, don't blindly pick top-1.

## Cache the resolved tuple

Once facet discovery resolves `{make, model, trim}` (or `{make, model, variant}` on UK calls), cache it in your scratchpad. Subsequent calls in the same session (comp set, sold-90d, state baseline) should all use the resolved values — do not re-discover.

## For `get_sold_summary`'s `make_model_not_found`

The facet surface for `get_sold_summary` isn't exposed directly. Fall back to discovering via `search_active_cars` (as above) and then pass those resolved values to `get_sold_summary`. If the retry still fails with `make_model_not_found`, **skip the State Baseline line with a Data Quality Notes event** and continue. State baseline is enrichment — never halt a valuation for it.

**Round-trip confirmation:** the casing that `search_active_cars` facets return is accepted verbatim by `get_sold_summary` in live testing. Example:

```
decode_vin_neovin      → Lexus
search_active_cars     → Lexus (facet confirms)
get_sold_summary       → Lexus (accepts same casing)
```

The two endpoints draw from the same canonical make/model set, so a facet-discovered value resolves both paths. Don't re-facet-discover for `get_sold_summary` once `search_active_cars` has confirmed casing in the same session — cache and reuse.

## When to trust-verbatim vs. discover

A YMMT tuple `{make, model, trim}` is **trusted-casing** only when one of:

- **(a)** It came from a successful `decode_vin_neovin` with the canonical fields populated. The decoder returns canonical casing indexed by MarketCheck.
- **(b)** A prior facet-discovery call in the same session resolved the casing (cache the resolved tuple).

**User-typed free-form YMMT is NOT trusted-casing.** If the appraiser typed `"honda accord sport"` or `"2022 hondaa accord"`, run facet discovery on the first search call — do not assume the user's casing matches MarketCheck's indexed values. A mis-cased facet filter returns `num_found == 0` silently, costing a wasted call and a confused zero-result branch.

**Heuristic:** if the first filtered search was preceded by an explicit successful decode OR a prior facet discovery in the same conversation → safe to skip discovery. Otherwise → run discovery first.

## Don't facet-discover what decode already confirmed

If `decode_vin_neovin` succeeded and returned canonical `{make, model, trim}`, trust those values on the first filtered search. Only escalate to facet discovery on a zero-result *after* the decode-backed call. Avoid speculative facet calls — each one costs a request.

## Data Quality event logging

When a facet-discovery retry fires, emit DQ event (a1): *"facet-discovery retry: original `<filter_value>` resolved to `<canonical_value>` (tool: `<tool_name>`)"*. This distinguishes "empty market" (no retry possible) from "silently mis-cased filter" (resolved).
