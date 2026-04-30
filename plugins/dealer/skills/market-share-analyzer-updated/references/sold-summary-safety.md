# `get_sold_summary` Safety Rules

`get_sold_summary` has a thorny parameter surface and several silent-failure modes that this skill has learnt the hard way. Always follow these rules when issuing a call, and always pipe the response through `scripts/parse_sold_summary.py` which encodes most of them.

## Response shape (as observed in live calls)

The response wraps rows inside a **doubly-nested** `data.data[]` array (not the `data.results[]` the public tool doc shows):

```json
{
  "success": true,
  "service": "sold_summary",
  "data": {
    "success": true,
    "data": [
      {"month": "2025-12", "inventory_type": "Used", "state": "TX", "model": "Accord",
       "rank": 1, "sold_count": 2069, "average_sale_price": 19750.72,
       "avg_msrp": 20004.03, "sale_price_range": "34991.0",
       "sale_price_std_dev": "6978.24", ...},
      ...
    ]
  }
}
```

Field-name quirks (server's actual names, not the doc's or the tool schema's guesses):
- **`avg_msrp`** (not `average_msrp`)
- **`sale_price_range`** — a single string (e.g. `"34991.0"`), not a low/high pair
- **`sale_price_std_dev`** (not `standard_deviation`)
- **`rank`** — present on every row when `ranking_dimensions` is set

`parse_sold_summary.py` normalises these to canonical names (`average_msrp`, `sale_price_range`, `sale_price_std_dev`) for downstream consumers.

`get_sold_summary` is the **only** tool that is **NOT envelope-wrapped** — it returns raw JSON directly, no `{"result": "<stringified JSON>"}` wrapper. `_common._maybe_unwrap` passes unwrapped dicts through transparently, so no special handling is needed.

## Always set these parameters explicitly

- **`inventory_type`** — MUST be `"Used"` or `"New"` (title case). Omitting defaults to `"New"` upstream, which silently returns new-inventory rollups for a used-car workflow. Always set this based on the session `car_type`.
- **`state`** — REQUIRED for the per-state baseline. Read from `profile.location.state` (2-letter code, uppercase). Halt and ask the user if missing in a US profile.
- **`limit`** — Always set `5000` (the upstream maximum). The tool's default is `1000` and **silently truncates** multi-dimensional results. Multi-dim truncation is a past source of missing-row bugs and wrong medians.
- **`summary_by`** — `"state"` for state-level baseline; `"city_state"` only when the user explicitly wants city-level (rare). The default is `"state"` but set it explicitly for clarity.
- **`ranking_measure`** — depends on the workflow:
  - Price-Check Single VIN (W1 step 8): `"average_days_on_market"` — the DOM baseline is the primary use. **NOT `"average_days_to_sell"`** (not a valid enum; will error).
  - Market Price Distribution (W4 step 3): `"sold_count"` — volume is the primary use.
- **`ranking_dimensions`** — `"make,model"` for a minimal 2-dimension rollup. Avoid the default `"make,model,body_type"` which inflates the result set and invites truncation. For `validation_dimension_limit` errors on retry, drop to `"make"` only.
- **`top_n`** — `5` is a reasonable cap; the tool will return the top-5 rows per group bucket.
- **`date_from` / `date_to`** — MUST be aligned to calendar-month boundaries: `date_from` = first day of a month, `date_to` = last day of a month. The tool's **local** validator does NOT check this — mis-aligned days (e.g. a rolling `today − 90 days`) pass local validation and hit upstream, which rejects with HTTP 422 (`parser emits `error_type="network_422"`). Observed live: `date_from=2026-01-22, date_to=2026-04-22` → 422; `date_from=2026-01-01, date_to=2026-03-31` → three month-bucket rows. Format `YYYY-MM-DD`.

  **Use `scripts/compute_sold_summary_dates.py` to compute the window.** The helper emits the prescribed "last 3 full calendar months" window, enforcing month-boundary alignment in code:

  ```
  $ python3 scripts/compute_sold_summary_dates.py --today 2026-04-23
  {"date_from":"2026-01-01","date_to":"2026-03-31","label":"last 3 full months",
   "months_included":["2026-01","2026-02","2026-03"],"today":"2026-04-23"}
  ```

  Never hand-compute or pass `today` as `date_to` — the current month is in progress and sold data lags.

  Response rows are bucketed one-per-month (`"month": "YYYY-MM"`); with the 3-month window you get up to 3 rows per matching `state`/`make`/`model` combination. Aggregation happens in code via `parse_sold_summary.py --aggregate-state <STATE>` (see "Surfacing the result").

## Parameters to skip

- **`dealer_type`** — Live-call testing showed that including `dealer_type=Franchise|Independent` combined with a narrow `make`/`model`/`state` filter returns `data.data=[]` for non-defective queries. Five distinct variant calls (different `ranking_measure`, `ranking_dimensions`, date ranges) all returned empty as long as `dealer_type` was passed; the same filters without `dealer_type` returned hundreds of rows. The dealer_type column is likely sparse in the upstream sold-summary index and acts as a near-total filter when pinned.

  **Decision:** do NOT pass `dealer_type` on the W1 State Baseline call. The State Baseline line describes the state's overall make/model sold velocity, not a dealer-type-specific cut — including it silently suppresses valid data without a signal to the caller.
- **`dealership_group_name`** — Only set if the user explicitly names a group AND that group is in the tool's hard-coded 471-entry enum. Pre-check against the list (see `mcp_server_tool_docs/get_sold_summary.md`) and skip silently if not present. The tool returns a very large error string containing the full enum list on mismatch; never surface that to the user.
- **`fuel_type_category`** — Skip unless the user explicitly filters by EV / Hybrid. The base-case call doesn't need it.
- **Advanced operator filters** (`sold_count=">100"`, etc.) — Skip. Not relevant to the price-check workflows.

## Error-handling branches

`parse_sold_summary.py` surfaces an `error_type` on failure. Branch on the value:

| `error_type` | Meaning | Recovery |
|---|---|---|
| `make_model_not_found` | The make/model string doesn't match the tool's indexed values | Retry once with facet-discovered make/model casing (per `references/facet-discovery.md`). If still failing, skip the state line with a Data Quality Notes event. |
| `validation_dimension_limit` | `ranking_dimensions` rejected by the tool's local validator | Retry once with `ranking_dimensions="make"` only. |
| `validation` | Some other local validator rejected a parameter | Skip the state line, log a Data Quality Notes event with the specific validation message. Do NOT halt the workflow. |
| `network_422` | Upstream rejected the request body with HTTP 422 | **Most common root cause: non-month-aligned `date_from`/`date_to`.** Verify both dates sit on month boundaries (first day / last day) and that `date_to` is not in the current calendar month before the call goes out. If the dates are already aligned, skip the state line and log a Data Quality Notes event — upstream rejection on a month-aligned window is rare and usually transient. |
| `network_5xx` | Upstream error | Skip the state line, log a Data Quality Notes event. The call can be retried once after a short pause, but given this is an enrichment-only signal, skipping is cheaper. |
| `unknown` | Parser hit an unexpected shape | Skip the state line, log a Data Quality Notes event with the raw payload snippet. |

**Never halt the whole workflow on a `get_sold_summary` failure.** The State Baseline line is enrichment; comp-set analysis and verdict rendering proceed without it.

## Surfacing the result

Use `parse_sold_summary.py --aggregate-state <STATE>` — the flag triggers in-code weighted-mean aggregation. Input: the raw sold-summary response (rows, month-bucketed). Output: the normalised `rows` array PLUS a `state_baseline` object with the weighted values for the specified state.

```
state_baseline = {
  "state":                       "<STATE>",
  "total_sold_count":            <sum of sold_count across months>,
  "weighted_avg_sale_price":     <weighted mean, weight = sold_count>,
  "weighted_avg_days_on_market": <weighted mean, same weight>,
  "months_included":             ["YYYY-MM", ...],
  "row_count_for_state":         <int — how many state-matching rows were found>
}
```

**Divide-by-zero guard (M8) — enforced in code.** When `sum(sold_count for state rows) == 0`, the aggregator emits `state_baseline: null` plus `state_baseline_skipped_reason: "all_zero"` (or `"no_matching_rows"` when no row matched the state). The renderer reads `state_baseline_skipped_reason` and emits a DQ event / skips the State Baseline line rather than rendering NaN. Never hand-compute or inline-math the aggregation — v4 attempted `python3 -c` here and was denied by the harness.

Surface in the Market Snapshot:

```
State Baseline ({STATE}, last 3 full months):  avg sale $XX,XXX  ·  avg DOM NN days  ·  sold_count: N
```

The label "last 3 full months" (not "last 90d") matches the actual window since the server returns full calendar months, not a rolling 90-day slice.

When no row exists for the dealer's state across any month in the window (rare — the tool occasionally returns only regional aggregates for thin markets), skip the line silently and log a Data Quality Notes event ("State baseline skipped: no row for <STATE> in response").

## State Baseline scope

`get_sold_summary` has **no `trim` or `year` parameter** on the state rollup — the state-matching row aggregates all trims and all years of the given `make`/`model` in `state` across the date window. That's the tightest cut the tool surfaces at this endpoint; passing `trim="350"` or `year=2022` is silently ignored (they're not in the parameter surface).

Because the State Baseline's denominator is "all Lexus RX sold in CA over 3 months" while the Headline's sold anchor is "2022 Lexus RX 350 sold in the local radius over 90 days," the two dollar figures can differ by thousands — older/lower-trim RXs drag the state average down. A reader who treats the two as apples-to-apples gets misled.

**Rendering obligation:** include the scope qualifier on the line itself —

```
State Baseline (<make> <model> across all trims & years in <STATE>, last 3 full months):
  avg sale $XX,XXX  ·  avg DOM NN days  ·  sold N
```

— and emit the one-line note below the Market Snapshot block when the State Baseline rendered:

> *State Baseline reflects state-wide sold velocity for the make/model — a broader cut than the trim-specific sold anchor in the Headline. Use it for market-health context, not direct price comparability.*

Both the qualifier and the note are required. Without them, the $X state average reads as a direct comparison against a trim-specific sold median on the same page.

## Don't fabricate

If the call fails or returns no matching-state row, the State Baseline line is **omitted** — do not substitute a regional average, a national average, or the local 90-day median. The user can tell the difference between "tracking the state" and "hotter than the state"; the whole point of surfacing the state baseline is authentic benchmarking, not a filled-in placeholder.
