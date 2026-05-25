# `get_sold_summary` safety rules

`get_sold_summary` has a thorny parameter surface and several silent-failure modes. This skill uses it for one purpose only: a state-level baseline of realised sale price + days-on-market for the appraised make/model, as defensibility context. Always follow these rules when issuing a call.

## Response shape

The response wraps rows inside a **doubly-nested** `data.data[]` array (not `data.results[]`):

```json
{
  "success": true,
  "service": "sold_summary",
  "data": {
    "success": true,
    "data": [
      {"month": "2026-02", "inventory_type": "Used", "state": "CA", "model": "Accord",
       "rank": 1, "sold_count": 2069, "average_sale_price": 19750.72,
       "avg_msrp": 20004.03, "sale_price_range": "34991.0",
       "sale_price_std_dev": "6978.24"}
    ]
  }
}
```

Field-name quirks (server's actual names):

- **`avg_msrp`** (not `average_msrp`)
- **`sale_price_range`** — a single string (e.g., `"34991.0"`), not a low/high pair
- **`sale_price_std_dev`** (not `standard_deviation`)
- **`rank`** — present on every row when `ranking_dimensions` is set

`get_sold_summary` is the **only** tool that is **NOT envelope-wrapped** — it returns raw JSON directly, no `{"result": "<stringified JSON>"}` wrapper. When extracting, detect by shape and skip the unwrap step.

## Always set these parameters explicitly

- **`inventory_type`** — MUST be `"Used"` or `"New"` (title case). Omitting defaults to `"New"` upstream, which silently returns new-inventory rollups for a used-vehicle valuation. Always set this based on `car_type_resolved` from the profile.
- **`state`** — REQUIRED. Read from `profile.location.state` (2-letter code, uppercase). Halt and ask the user if missing on a US profile.
- **`limit`** — Always set `5000` (the upstream maximum). The tool's default is `1000` and **silently truncates** multi-dimensional results. Multi-dim truncation is a past source of missing-row bugs and wrong medians.
- **`summary_by`** — `"state"` for the state baseline (the only summary-by this skill uses).
- **`ranking_measure`** — `"average_days_on_market"` for W1 state baseline. **NOT `"average_days_to_sell"`** (not a valid enum; will error).
- **`ranking_dimensions`** — `"make,model"` for a minimal 2-dimension rollup. Avoid the default `"make,model,body_type"` which inflates the result set and invites truncation. On a `validation_dimension_limit` error on retry, drop to `"make"` only.
- **`top_n`** — `5` is a reasonable cap.
- **`date_from` / `date_to`** — MUST be aligned to calendar-month boundaries: `date_from` = first day of a month, `date_to` = last day of a month. The tool's **local** validator does NOT check this. Mis-aligned days pass local validation and hit upstream, which rejects with HTTP 422. Format `YYYY-MM-DD`.

  **Compute the window inline against `# currentDate`** — first day of `current_month − 3` for `date_from`; last day of `current_month − 1` for `date_to`. This is the "last 3 full calendar months" window. Never use `today` as `date_to` — the current month is in progress and sold data lags.

  Worked example with `# currentDate = 2026-05-25`:
  ```
  date_from = 2026-02-01   (first day of (May - 3) = February)
  date_to   = 2026-04-30   (last day  of (May - 1) = April)
  ```

  Response rows are bucketed one-per-month (`"month": "YYYY-MM"`); with the 3-month window you get up to 3 rows per matching `state`/`make`/`model` combination. Aggregate in-prompt (see "Aggregating the result" below).

## Parameters to skip

- **`dealer_type`** — Live-call testing showed that including `dealer_type=Franchise|Independent` combined with a narrow `make`/`model`/`state` filter returns `data.data=[]` for non-defective queries. The dealer_type column is sparse in the upstream sold-summary index and acts as a near-total filter when pinned. **Decision:** do NOT pass `dealer_type` on the state baseline call. The state baseline describes the state's overall make/model sold velocity, not a dealer-type-specific cut.
- **`dealership_group_name`** — Only set if the user explicitly names a group AND that group is in the tool's hard-coded 471-entry enum. Otherwise skip silently.
- **`fuel_type_category`** — Skip unless the user explicitly filters by EV / Hybrid.
- **Advanced operator filters** (`sold_count=">100"`, etc.) — Skip. Not relevant to the appraisal state baseline.

## Error-handling branches

Branch on the error type returned by the tool (or inferred from the response shape):

| Error type | Meaning | Recovery |
|---|---|---|
| `make_model_not_found` | The make/model string doesn't match the tool's indexed values | Retry once with facet-discovered make/model casing (`references/facet-discovery.md`). If still failing, skip the state line with a DQ event (a). |
| `validation_dimension_limit` | `ranking_dimensions` rejected by the tool's local validator | Retry once with `ranking_dimensions="make"` only. |
| `validation` | Some other local validator rejected a parameter | Skip the state line, log a DQ event (a) with the specific validation message. Do NOT halt the workflow. |
| `network_422` | Upstream rejected the request body with HTTP 422 | **Most common root cause: non-month-aligned dates.** Verify both dates sit on month boundaries and that `date_to` is not in the current calendar month. If already aligned, skip the state line and log a DQ event (a). |
| `network_5xx` | Upstream error | Skip the state line, log a DQ event (a). |
| `unknown` | Unexpected shape | Skip the state line, log a DQ event (a). |

**Never halt the workflow on a `get_sold_summary` failure.** The State Baseline line is defensibility context; the rest of the appraisal proceeds without it.

## Aggregating the result

The response returns one row per `month` × `state` × `make` × `model` combination. To produce a single state baseline, aggregate the rows that match `profile.location.state` across the 3-month window using sold-count-weighted means:

```
state_rows = [r for r in data.data if r.state == STATE]

if sum(r.sold_count for r in state_rows) == 0:
    state_baseline = None
    state_baseline_skipped_reason = "all_zero"
else:
    total_sold = sum(r.sold_count for r in state_rows)
    weighted_avg_sale_price = sum(r.average_sale_price * r.sold_count for r in state_rows) / total_sold
    weighted_avg_dom        = sum(r.average_days_on_market * r.sold_count for r in state_rows) / total_sold
    months_included         = sorted(set(r.month for r in state_rows))
    state_baseline = {
      "state":                       STATE,
      "total_sold_count":            total_sold,
      "weighted_avg_sale_price":     weighted_avg_sale_price,
      "weighted_avg_days_on_market": weighted_avg_dom,
      "months_included":             months_included,
      "row_count_for_state":         len(state_rows),
    }
```

**Divide-by-zero guard:** when total `sold_count` across state rows is zero, set `state_baseline = None` with `state_baseline_skipped_reason = "all_zero"` and emit DQ event (e). Never compute a NaN-divided value.

**No-matching-rows guard:** when no row matches the state at all (rare — happens with thin markets), set `state_baseline = None` with `state_baseline_skipped_reason = "no_matching_rows"` and emit DQ event (e).

## Surfacing the result

Render in the Market Snapshot block of W1's output:

```
State Baseline (<make> <model> across all trims & years in <STATE>, last 3 full months):
  avg sale $<weighted_avg_sale_price>  ·  avg DOM <weighted_avg_dom> days  ·  sold <total_sold_count>
```

**Below the Market Snapshot block, emit this one-line note when the State Baseline rendered:**

> *State Baseline reflects state-wide sold velocity for the make/model — a broader cut than the trim-specific sold anchor in the Headline. Use it for defensibility context, not direct price comparability.*

Both the inline scope qualifier and the standalone note are required. Without them, a $X state average reads as a direct comparison against a trim-specific sold median on the same page.

## Scope disclosure

`get_sold_summary` has **no `trim` or `year` parameter** on the state rollup — the state-matching row aggregates all trims and all years of the given `make`/`model` in `state` across the date window. Passing `trim` or `year` is silently ignored. This is the tightest cut the tool surfaces at this endpoint.

Because the State Baseline's denominator is "all <make> <model> sold in <STATE> over 3 months" while the Headline's sold anchor is "<year> <make> <model> [<trim>] sold in the local radius over 90 days," the two dollar figures can differ by thousands — older / lower-trim units drag the state average down. A reader who treats the two as apples-to-apples gets misled — the scope qualifier and the standalone note above prevent that.

## Don't fabricate

If the call fails or returns no matching-state row, the State Baseline line is **omitted** — do not substitute a regional average, a national average, or the local 90-day median. The appraiser can tell the difference between "tracking the state" and "no state data available"; the whole point of surfacing the state baseline is authentic benchmarking, not a filled-in placeholder.
