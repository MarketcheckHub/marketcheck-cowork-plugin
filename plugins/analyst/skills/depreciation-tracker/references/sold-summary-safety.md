---
name: sold-summary-safety
description: Parameter-discipline rules for every `get_sold_summary` call this skill fires. Always-set parameters, never-set parameters, the 5-concurrent rate-limit ceiling, the 12-month date-range cap, the silent-truncation defaults, and the `parse_sold_summary.error_type` recovery table.
type: reference
---

# `get_sold_summary` safety rules — Depreciation-Tracker (Analyst)

Adopted from the dealer-side `depreciation-tracker/references/sold-summary-safety.md`
with these analyst-specific differences:

1. **Single-tool surface.** This skill calls only `get_sold_summary` (no
   `search_active_cars` / `decode_vin_neovin` / `get_car_history`). The
   `make_model_not_found` recovery path is the lone exception — it fires one
   `search_active_cars` facet-discovery call per `references/facet-discovery.md`.
2. **Multi-period date windows.** W1 (5 periods), W2 / W5 (current + prior),
   W3 (current + 6-month-back). Every window's `date_from` / `date_to` comes
   from `compute_period_windows.py` — never hand-computed.
3. **Upstream rate-limit ceiling = 5 concurrent calls.** Workflows that
   would otherwise fire >5 in a single wave (W2 with EV+ICE+Hybrid passes)
   sub-batch into ≤5 per agent message and fire sub-batches sequentially.

## Response shape (re-confirming the tool doc)

The response wraps rows inside `data.results[]` OR `data.data[]` depending on
the upstream variant. `parse_sold_summary.py` handles both.

```json
{
  "success": true,
  "service": "sold_summary",
  "data": {
    "results": [
      {"month": "2026-04", "inventory_type": "Used", "state": "CA",
       "make": "Toyota", "model": "RAV4", "rank": 1, "sold_count": 1820,
       "average_sale_price": 27450.12, "avg_msrp": 30210.87,
       "price_over_msrp_percentage": -9.13,
       "average_days_on_market": 31.4, "median_days_on_market": 28.5, ...},
      ...
    ]
  }
}
```

`parse_sold_summary.py` normalises field-name quirks (`avg_msrp` →
`average_msrp`, `sale_price_std_dev` is preserved with its server name).

`get_sold_summary` is the **only** tool that is NOT envelope-wrapped — it
returns raw JSON directly. `_common._maybe_unwrap` passes unwrapped dicts
through transparently.

## Always set these parameters explicitly

- **`inventory_type`** — `"Used"` or `"New"` (title case). Omitting silently
  defaults upstream; a used-vehicle workflow that omits this rolls up the
  wrong inventory type. Per SKILL.md: W1 / W2 / W3 → `Used`; W5 → `New`.
- **`state`** — required when the user scoped to a single state, or
  `analyst.tracked_states` is a single value. Empty `tracked_states` → omit
  for a national rollup. 2-letter uppercase code.
- **`limit`** — always `5000`. Default `1000` silently truncates
  multi-dimensional results.
- **`summary_by`** — `"state"` when `state` is set; absent otherwise (a
  national rollup returns the single rolled-up row directly).
- **`ranking_measure`** — depends on workflow:
  - W1 (Make/Model curve): `"average_sale_price"`
  - W2 (segment): `"average_sale_price"`
  - W3 (brand): `"average_sale_price"` for retention; one extra call with
    `"sold_count"` for volume context.
  - W5 (parity): `"price_over_msrp_percentage"` for parity; one extra call
    with `"sold_count"` for volume context.
- **`ranking_dimensions`** — minimal per workflow:
  - W1: `"make,model"` (both fixed by user input).
  - W2: `"body_type"` OR `"fuel_type_category"` (one dimension per call;
    EV / ICE / Hybrid get separate calls with `fuel_type_category` set).
  - W3: `"make"`.
  - W5: `"make,model"`.
  Avoid the default 3-dim (`"make,model,body_type"`) — it inflates the
  result set and invites truncation.
- **`top_n`** — bounded per workflow: 5-10 for W1 / W2 (single-cut rollups);
  25 for W3 (top brands); 30 for W5 (top models).
- **`date_from` / `date_to`** — MUST sit on calendar-month boundaries:
  `date_from` = first day of a month; `date_to` = last day of a month;
  `date_to` must NOT be in the current calendar month (the upstream rejects
  with HTTP 422). Use `compute_period_windows.py`.

## Multi-period date discipline

W1 / W2 / W3 / W5 fire multiple `get_sold_summary` calls back-to-back, each
covering a different lookback period. To prevent date drift:

1. Run `python scripts/compute_period_windows.py --today <currentDate> --periods <list>` ONCE at workflow entry. Cache the result.
2. Each call in Wave A reads its `date_from` / `date_to` from the cached
   periods array, indexed by label (`current` / `60d` / `90d` / `6mo` / `1yr`).
3. Never re-derive the window per call — drift between two calls in the same
   batch invalidates the cross-period diff.

### Period customization (v1.0.0)

`compute_period_windows.py` ships with five canonical period tokens
(`current`, `60d`, `90d`, `6mo`, `1yr`). The analyst `benchmark_period_months`
profile preference defaults to 3 months — for v1.0.0 we use the `90d` token
as the W2 / W5 prior-period anchor (rendered to the user as "approximately 3
months back"). Custom offsets (e.g., `4mo`, `5mo`) are deferred to a future
revision; if a user explicitly asks for a non-canonical lookback, surface a
DQ event (f) and use the nearest canonical token.

W3's comparison window is fixed at `6mo` regardless of
`benchmark_period_months` — residual is a 6-month concept by industry
convention.

## Upstream rate limit (verified live 2026-05-14)

`api.marketcheck.com` returns HTTP 429 when more than 3-5 concurrent
`get_sold_summary` requests are in flight. The MCP wrapper does not enforce
this; only the upstream layer trips it, and the 429 body is the standard
httpx error string with no `Retry-After` header.

**Sub-batch decomposition rule:** any wave that needs more than 5 calls
splits into sequential sub-batches of ≤5 calls per agent message. Within a
sub-batch, calls fire in parallel. Between sub-batches, the agent waits for
all `tool_result` messages before issuing the next sub-batch.

429 retries within a workflow are forbidden — they amplify pressure. If a
429 hits despite sub-batching, drop the affected calls + emit DQ event (a)
and continue with surviving calls.

## Upstream date-range cap (verified live 2026-05-14)

`api/v1/sold-vehicles/summary` rejects requests where
`date_to − date_from > 12 calendar months` with HTTP 422 (body literally
`'422 unknown'`). Each call in this skill spans exactly one calendar month
via `compute_period_windows.py`, so this cap is implicitly honored.

## Parameters to skip

- **`dealer_type`** — DO NOT pass. Live-call testing showed `dealer_type=Franchise|Independent` combined with a narrow filter returns `data.data=[]` for non-defective queries. The depreciation-tracker intentionally omits dealer-type filtering.
- **`dealership_group_name`** — only set if the user explicitly names a group AND it's in the 471-entry hard-coded enum. Not used by any workflow in this skill.
- **`fuel_type_category`** — set ONLY when W2 runs the EV / ICE / Hybrid comparison. All other workflows leave it null.

## `year` and `trim` — NOT supported

`get_sold_summary` has no `year` or `trim` parameter. The state rollup
aggregates all years and trims of the given make/model in the date window.
**The depreciation-tracker workflows do NOT prompt the user for year**; the
output renders a scope qualifier:

```
Year scope: across all model years (per get_sold_summary scope)
```

When the user asks "depreciation curve for a 2022 RAV4", the skill renders
the make-model curve and surfaces the all-years scope inline.

## Error-handling branches

`parse_sold_summary.py` surfaces an `error_type` on failure. Branch on it:

| `error_type` | Recovery |
|---|---|
| `make_model_not_found` | Retry once with facet-discovered casing per `references/facet-discovery.md`; if still failing, omit the affected period from the curve / table and emit DQ event (a). |
| `validation_dimension_limit` | Retry once with `ranking_dimensions="make"` only. |
| `validation` | Skip the affected call, log DQ event (a). |
| `network_422` | Verify month-aligned dates; if already aligned, skip + log DQ event (a). |
| `network_5xx` | Skip + log DQ event (a). |
| `truncation_unrecovered` | Pipe the runtime-written file path to `parse_sold_summary.py --file <path>`; log DQ event (b). |
| `unknown` | Skip + log DQ event (a) with raw payload snippet. |

**A failure on ONE period of a multi-period workflow does NOT halt the
workflow.** Render the curve / table with the surviving periods; surface
the gap in Data Quality Notes.

## Aggregation in code

W1 uses `parse_sold_summary.py --aggregate-multi-period`. Each call's output
emits `multi_period_aggregate.{months, overall}` which `depreciation_curve.py`
consumes. Never hand-compute monthly weighted means.

W2 / W3 / W5 read the normalized `rows[]` array directly into their stats
engines (`segment_compare.py`, `brand_retention.py`, `msrp_parity.py`).

## Don't fabricate

If a period's call fails, **omit the period** from the curve / table — do
not substitute a regional average, the prior period's value, or a
fabricated zero. The renderer skips the row with an `—` cell or omits it
entirely depending on the workflow.
