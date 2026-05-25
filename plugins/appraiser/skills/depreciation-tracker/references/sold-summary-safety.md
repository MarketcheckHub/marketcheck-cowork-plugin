# `get_sold_summary` Safety Rules — Depreciation-Tracker Edition

The hard-won rules for the appraiser plugin's depreciation-tracker skill. The
non-negotiables are documented in `mcp_server_tool_docs/get_sold_summary.md`;
the additions specific to this skill are:

1. **Multi-period date windows** — every workflow except W4 fires multiple
   `get_sold_summary` calls, one per period. Date alignment must be enforced
   on every call.
2. **`year` and `trim` are NOT parameters** on `get_sold_summary` — the
   skill's W1 curve aggregates across all model years and all trims of the
   given make/model. The output template renders an explicit scope qualifier.

## Response shape (re-confirming the doc)

The response wraps rows inside a **doubly-nested** `data.data[]` array (not
the `data.results[]` the public tool doc shows):

```json
{
  "success": true,
  "service": "sold_summary",
  "data": {
    "success": true,
    "data": [
      {"month": "2025-12", "inventory_type": "Used", "state": "TX",
       "model": "Accord", "rank": 1, "sold_count": 2069,
       "average_sale_price": 19750.72, "avg_msrp": 20004.03,
       "sale_price_range": "34991.0", "sale_price_std_dev": "6978.24",
       "average_days_on_market": 38.1, "median_days_on_market": 35.0,
       "price_over_msrp_percentage": -1.27, ...},
      ...
    ]
  }
}
```

`parse_sold_summary.py` normalises the field-name quirks (`avg_msrp` →
`average_msrp`, `sale_price_std_dev` is preserved with its server name).

`get_sold_summary` is the **only** tool that is NOT envelope-wrapped — it
returns raw JSON directly. `_common._maybe_unwrap` passes unwrapped dicts
through transparently.

## Always set these parameters explicitly

- **`inventory_type`** — `"Used"` or `"New"` (title case). Omitting silently
  defaults to `"New"` upstream. The depreciation-tracker hardcodes the
  correct value per workflow (W1/W2/W3/W4 → `Used`; W5 → `New`); the
  appraiser profile carries no `default_inventory_type` field, so this is
  workflow-driven, not profile-driven.
- **`state`** — required for state-anchored workflows (W1 W2 W3 W5; for W4
  it's the *target* of the rollup, not a filter). 2-letter uppercase code.
  Halt-and-ask if missing in a US profile.
- **`limit`** — always `5000`. Default `1000` silently truncates
  multi-dimensional results.
- **`summary_by`** — `"state"` for W1 W2 W3 W5 (single-state cuts); for W4
  also `"state"` (state is the rollup dimension itself) on the first call,
  and OMITTED on the W4 national-rollup call. `"city_state"` only on
  explicit user request.
- **`ranking_measure`** — depends on workflow:
  - W1 (Make/Model curve): `"average_sale_price"`
  - W2 (segment): `"average_sale_price"`
  - W3 (brand): `"average_sale_price"` for retention; one extra call with
    `"sold_count"` for volume context
  - W4 (geographic): `"average_sale_price"`
  - W5 (parity): `"price_over_msrp_percentage"`
- **`ranking_dimensions`** — minimal:
  - W1: `"make,model"` (both fixed by user input)
  - W2: `"body_type"` or `"fuel_type_category"` (one dimension at a time)
  - W3: `"make"`
  - W4: `"make,model"` with `summary_by="state"`
  - W5: `"make,model"`
  Avoid the default 3-dim (`"make,model,body_type"`) — inflates result set
  and invites truncation.
- **`top_n`** — 25 for W3 (top 25 brands), 30 for W5 (top 30 models), 5–10
  for W1/W2/W4 (single-cut rollups don't need a wide top-N).
- **`date_from` / `date_to`** — MUST sit on calendar-month boundaries:
  `date_from` = first day of a month; `date_to` = last day of a month;
  `date_to` must NOT be in the current calendar month (the upstream rejects
  with HTTP 422).

  **For depreciation-tracker, use the helpers:**
  - `scripts/compute_sold_summary_dates.py` — emits the prescribed "last 3
    full months" window (used by W4 single-period calls).
  - `scripts/compute_period_windows.py` — emits multiple month-aligned
    windows (used by W1 multi-period curve, W2/W3/W5 current-vs-prior pairs).

  Never hand-compute. Never pass `today` as `date_to` — sold data lags.

## Multi-period date discipline

W1, W2, W3, W5 fire multiple `get_sold_summary` calls back-to-back, each
covering a different lookback period. To prevent date drift across the
parallel batch:

1. Run `scripts/compute_period_windows.py --today <today> --periods <list>`
   ONCE at workflow entry. Cache the result.
2. Each call in Wave A reads its `date_from` / `date_to` from the cached
   periods array, indexed by label (`"current"` / `"60d"` / `"90d"` / etc.).
3. Never re-derive the window per call — drift between two calls in the
   same batch invalidates the cross-period diff.

## Parameters to skip

- **`dealer_type`** — DO NOT pass. Live-call testing showed
  `dealer_type=Franchise|Independent` combined with a narrow filter returns
  `data.data=[]` for non-defective queries. The depreciation-tracker
  intentionally omits dealer-type filtering from its input surface.
- **`dealership_group_name`** — only set if the user explicitly names a
  group AND it's in the 471-entry hard-coded enum.
- **`fuel_type_category`** — set ONLY when W2 runs the EV/Hybrid
  comparison. All other workflows leave it null.

## `year` and `trim` — NOT supported

`get_sold_summary` has no `year` or `trim` parameter. The state rollup
aggregates all years of the given make/model in the date window. **The
depreciation-tracker workflows do NOT prompt the user for year**; the
output renders a scope qualifier:

```
Year scope: across all model years (per get_sold_summary scope)
```

When the user asks "depreciation curve for a 2022 RAV4", the skill
renders the make-model curve and surfaces the all-years scope inline. The
appraiser's per-year trend adjustment is then made by the appraiser
applying the curve's verdict band to their book-value-based starting point.

## Error-handling branches

`parse_sold_summary.py` surfaces an `error_type` on failure. Branch on it:

| `error_type` | Recovery |
|---|---|
| `make_model_not_found` | Retry once with facet-discovered casing per `references/facet-discovery.md`; if still failing, omit the affected period from the curve and emit DQ event (a). |
| `validation_dimension_limit` | Retry once with `ranking_dimensions="make"` only. |
| `validation` | Skip the affected call, log DQ event (a). |
| `network_422` | Verify month-aligned dates; if already aligned, skip + log DQ event (a). |
| `network_5xx` | Skip + log DQ event (a). |
| `unknown` | Skip + log DQ event (a) with raw payload snippet. |

**A failure on ONE period of a multi-period workflow does NOT halt the
workflow.** Render the curve / table with the surviving periods; surface the
gap as a Key Signals warning so the appraiser knows which period was
imputed-from-fallback rather than measured.

## Upstream constraints (load-bearing)

- **Date-range ≤ 12 calendar months per call.** Upstream rejects with HTTP
  422 if `date_to − date_from > 12 calendar months`. The skill's longest
  single window is `1yr` (current month vs 12 months back); each window is
  exactly one calendar month wide, so this is structurally compliant.
- **≤ 5 concurrent `get_sold_summary` calls per agent message.** Upstream
  returns HTTP 429 on the 4th+ concurrent call. Every depreciation-tracker
  workflow fits within this: W1 Wave A = 5 sold + 1 search (6 total but only
  5 sold); W2 max 6 sold; W3 = 3 sold; W4 = 2 sold; W5 = 3 sold. W1 and W2's
  6-call waves are on the edge — if 429s appear, sub-batch into ≤3.

## Aggregation in code

W1 uses `parse_sold_summary.py --aggregate-multi-period`. Each call's output
emits `multi_period_aggregate.{months,overall}` which `depreciation_curve.py`
consumes. Never hand-compute monthly weighted means.

W2/W3/W5 read the normalized `rows[]` array directly into their respective
stats engines (`segment_compare.py`, `brand_retention.py`, `msrp_parity.py`).

W4 uses the standard `--aggregate-state <STATE>` flag for the *national*
baseline call (a single weighted mean across the whole state-rollup
response).

## Don't fabricate

If a period's call fails, **omit the period** from the curve / table —
do not substitute a regional average, the prior period's value, or a
fabricated zero. The renderer skips the row with an `—` cell or omits it
entirely depending on the workflow. A defensible appraisal demands every
data point be cited; fabricated cells break that contract.
