---
name: script-contracts
description: Authoritative I/O contract (CLI flags, stdin shape, stdout shape, error envelopes, edge cases) for every Python script in scripts/. The script source is implementation detail; this file is the contract surface. Cross-checked against tests/test_*.py — if a contract here disagrees with a test assertion, the test wins.
type: reference
---

# Script contracts

Authoritative I/O contract for every script in `scripts/`. The script source is implementation detail and never needs to enter your context — `SKILL.md §Script invocation discipline` forbids the `Read` tool on `scripts/*.py`. Treat this file as the contract surface.

If a contract here disagrees with what `tests/test_<script>.py` asserts, the test wins — file a doc bug and update this file. Never read source to "verify" — that's the failure mode this file exists to prevent.

## Quick reference

| Script | Purpose | CLI flags | Used by |
|---|---|---|---|
| `_common.py` | Shared helpers (`read_input`, `emit`, `classify_error`, `arg_value`, `arg_flag`, `arg_value_multi`, `_maybe_unwrap`) | (not directly invoked) | every parser |
| `compute_month_windows.py` | Emit calendar-month-aligned current / prior / baseline_3mo windows | `--today YYYY-MM-DD`, `--baseline-months N` (default 3) | W1 / W2 / W3 pre-flight |
| `resolve_oem.py` | Resolve user input → ticker + company_name + makes + classification (pure_play / legacy) | `--input "<text>"` (+ 2 optional file overrides) | W1 / W2 pre-flight |
| `parse_search.py` | Normalize `search_active_cars` responses (stats / facets modes) | `--mode {stats\|facets}`, `--file <path>` | W1 / W2 active-inventory + brand-orphan recovery |
| `parse_sold_summary.py` | Normalize `get_sold_summary` responses (4 aggregation modes) | `--aggregate-make <make>` ∣ `--aggregate-make-by-window <make>` ∣ `--aggregate-by-dimension {body_type\|make} [--by-window]`, `--file <path>` | W1 / W2 / W3 sold-summary parsing |
| `compute_oem_stats.py` | Multi-make / multi-state numerical-aggregation engine. Emits raw values only (no bands). | (stdin only) | W1 / W2 |
| `aggregate_signals.py` | Bands + composite slots + verdict + per-make divergence | (stdin only) | W1 (verdict reduction) |

## Conventions (all parsers)

- **Stdin-default.** Every parser reads its payload from stdin by default. Use the `--file <path>` flag ONLY when the MCP runtime saved an oversized response to disk and returned an `Output saved to <path>` error string — never create those files yourself.
- **Truncation envelope.** When loaded via `--file`, the parser unwraps the `{"result": "<stringified JSON>"}` envelope automatically (via `_common._maybe_unwrap`). `get_sold_summary` is the only MCP tool whose payload is NOT envelope-wrapped — its raw `{success, service, data}` passes through transparently.
- **Canonical response shape.** Every parser emits a single JSON document with `ok: true|false` at top level. On `ok: false`, an `error_type` enum classifies the failure; the caller branches on it.
- **Process exit codes.** Validation errors (mutex flag conflicts, bad CLI args, missing required input) exit `1` with no JSON. Payload-level errors (network failures, schema misses, classifier hits) exit `0` with `{"ok": false, "error_type": "...", ...}` on stdout — the caller is expected to parse and branch.
- **Field naming.** Server-side quirks (`avg_msrp`, `sale_price_std_dev`) are normalized at parse time. The contract here is the **post-normalization** name (`average_msrp`, etc.).
- **No banding in upstream scripts.** `compute_oem_stats.py` emits raw numeric values only. Banding lives in `aggregate_signals.py` exclusively. This is the single-source-of-truth discipline that mirrors dealer-group-health-monitor.

## Overlap rule — where each kind of doc lives

| Topic | Canonical location |
|---|---|
| Script I/O shapes (stdin/stdout, CLI flags, error envelopes) | **This file** |
| Per-metric banding tables + composite combiners + verdict reduction algorithm | `references/signal-aggregation.md` |
| MCP tool parameter discipline (`get_sold_summary` always-set/never-set params, empirical findings) | `references/sold-summary-safety.md` |
| Sold-count-weighted multi-make aggregation math + null-handling discipline | `references/multi-make-aggregation.md` |
| 13-row OEM ticker map + 8-row dealer-group redirect | `references/ticker-mapping.md` |
| Pure_play / legacy / brand_orphan classification + EV detection rule | `references/oem-classification.md` |
| Wave structures (which calls fire in which order) | `references/w1-single-oem.md`, `w2-compare-oems.md`, `w3-market-share-leaderboard.md` |
| Output rendering rules | `assets/w*-output-template.md` |

This file points outward to those references where appropriate, never inward (no circular pointers).

## Generic `error_type` catalogue (extended by individual parsers)

| `error_type` | Meaning | Recovery |
|---|---|---|
| `network` | Generic network error reported upstream | Skip the call; log DQ event (a). |
| `network_422` | HTTP 422 — upstream rejected the request body | Most common root cause: non-month-aligned dates. Verify `compute_month_windows.py` was used. If aligned, skip + DQ event. |
| `network_5xx` | HTTP 500/502/503/504 — upstream server error | Skip + DQ event. |
| `unexpected_shape` | Payload top-level shape did not match expected `{success, service, data}` | Skip + DQ event with snippet. |
| `unknown` | Parser hit a shape it couldn't classify | Skip + DQ event with payload snippet. |
| `truncation_unrecovered` | Parser detected a truncation error string but no recovery path was available | Re-fire the upstream call with narrower filters. |

Per-script extensions are documented in each script's section below.

---

## `_common.py`

**Purpose:** Shared library used by every parser. Not invoked directly.

**Public helpers** (used by other scripts; the contract for these helpers is internal, not user-facing):

| Helper | Purpose |
|---|---|
| `read_input(argv)` | Read JSON from stdin or `--file <path>`; unwrap `{"result": "<stringified>"}` envelope transparently. Returns `(payload, source)`. |
| `emit(obj)` | Serialize an object to stdout as compact JSON. Used for every successful and error response. |
| `classify_error(payload)` | Inspect a payload for transport-level failure signatures. Returns `(error_type, error_message)` or `("", "")` on success. |
| `arg_value(argv, flag)` | Parse `--flag value` from argv. Returns the value string or `None`. |
| `arg_flag(argv, flag)` | Parse boolean `--flag` from argv. Returns `True` if present. |
| `arg_value_multi(argv, flag)` | Collect all occurrences of `--flag value`. Returns list of strings. |

**Used by:** every parser.
**Test verification:** indirectly via every `tests/test_<parser>.py`; no dedicated `tests/test_common.py`.

---

## `compute_month_windows.py`

**Purpose:** Emit calendar-month-aligned `current_month`, `prior_month`, and `baseline_3mo_window` for the W1 (3-window MoM + 3-mo trend) and W2/W3 (current month only) workflows.

**Strictly-before rule:** `current_month` is the calendar month that ended **strictly before** today. On May 31 → April. On June 1 → May. On May 1 → April. Sidesteps the race where `get_sold_summary` aggregates lag the calendar.

**Invocation:**
```bash
python scripts/compute_month_windows.py --today 2026-05-08
python scripts/compute_month_windows.py --today 2026-05-08 --baseline-months 6
```

**Reads stdin?** No.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--today` | string `YYYY-MM-DD` | no | system date | Reference date |
| `--baseline-months` | int | no | `3` | Number of months in the baseline window. Must be ≥1. |

**Output (stdout, JSON):**
```json
{
  "today": "2026-05-08",
  "current_month": {
    "date_from": "2026-04-01",
    "date_to":   "2026-04-30",
    "label":     "April 2026",
    "days_in_month": 30
  },
  "prior_month": {
    "date_from": "2026-03-01",
    "date_to":   "2026-03-31",
    "label":     "March 2026",
    "days_in_month": 31
  },
  "baseline_3mo_window": {
    "date_from": "2026-01-01",
    "date_to":   "2026-03-31",
    "label":     "January 2026 - March 2026",
    "months_count": 3
  }
}
```

**Error envelopes:** None at the payload level. Malformed `--today` value or `--baseline-months < 1` exits `1` with stderr message and no JSON output.

**Edge cases:**
- First of month (`--today 2026-05-01`) → `current_month = April 2026`.
- Last of month (`--today 2026-05-31`) → `current_month = April 2026`.
- First of next month (`--today 2026-06-01`) → `current_month = May 2026`.
- Year boundary (`--today 2026-01-15`) → `current_month = December 2025`; baseline = September 2025 - November 2025.
- Leap-year February (`--today 2024-03-05`) → `current_month.days_in_month = 29`.
- Non-leap February (`--today 2026-03-05`) → `current_month.days_in_month = 28`.
- `baseline_3mo_window` always ends at `prior_month.date_to` (= last day of month immediately before current_month) and starts `baseline_months` months earlier.

**Used by:** `SKILL.md §Before you start` step 2; W1 / W2 / W3 pre-flight.
**Test verification:** `tests/test_compute_month_windows.py`.

---

## `resolve_oem.py`

**Purpose:** Map a user-supplied OEM ticker / brand / company name to canonical (ticker, company_name, makes[], classification). Three-tier resolution: exact ticker → reverse make-name lookup → fuzzy via `difflib.SequenceMatcher` ≥0.5. Below threshold → `error_type=no_candidates` (triggers SKILL.md's brand-orphan recovery branch).

**Dealer-group redirect:** any input matching one of the 8 dealer-group tickers (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA) returns `error_type=dealer_group_redirect`.

**Brand-orphan handling:** NOT in this script. SKILL.md's recovery branch (after `no_candidates`) fires a `search_active_cars` facet-discovery call and constructs the workflow context inline.

**Invocation:**
```bash
python scripts/resolve_oem.py --input "F"
python scripts/resolve_oem.py --input "Ford"
python scripts/resolve_oem.py --input "TSLA"
python scripts/resolve_oem.py --input "AN"          # → dealer_group_redirect
python scripts/resolve_oem.py --input "Subaru"      # → no_candidates
```

**Reads stdin?** No.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--input` | string | yes | — | User-supplied ticker / make / company. Empty / absent → `error_type=missing_input`. |
| `--ticker-file` | path | no | `references/ticker-mapping.md` | Override the OEM ticker source |
| `--classification-file` | path | no | `references/oem-classification.md` | Override the pure-play list source (reserved for future use; v1 reads classification from the ticker-file's 4th column) |

**Output on success:**
```json
{
  "ok": true,
  "input": "Ford",
  "resolution": "exact" | "ticker" | "fuzzy",
  "ticker": "F",
  "company_name": "Ford Motor Company",
  "makes": ["Ford", "Lincoln"],
  "classification": "legacy" | "pure_play",
  "candidates": []
}
```

**Output on failure:**
```json
{
  "ok": false,
  "error_type": "missing_input" | "dealer_group_redirect" | "no_candidates",
  "candidates": [...]
}
```

For `dealer_group_redirect`, also includes:
- `matched_ticker`: the matched dealer-group ticker
- `redirect_to`: `"dealer-group-health-monitor"`

For `no_candidates`, `candidates` is the top-10 fuzzy candidates (all below 0.5).

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `missing_input` | `--input` absent or empty | Re-prompt the user |
| `dealer_group_redirect` | Input matched one of 8 dealer-group tickers | SKILL.md halts with redirect message |
| `no_candidates` | No fuzzy match ≥0.5 | SKILL.md's brand-orphan recovery branch |

**Edge cases:**
- Ticker input is auto-uppercased (`"tsla"` → `"TSLA"`).
- Reverse make lookup is case-insensitive (`"ford"` → `"F"`, `"PORSCHE"` → `"VWAGY"`).
- Company-name exact match also tried (`"Ford Motor Company"` → exact via lookup).
- Resolution is `"exact"` for direct ticker hits; `"ticker"` for reverse make/company hits; `"fuzzy"` for SequenceMatcher hits.
- `classification = "brand_orphan"` is NEVER returned by this script — SKILL.md constructs that classification inline after recovery succeeds.

**Used by:** `SKILL.md §Before you start` step 3; W1 / W2 pre-flight.
**Test verification:** `tests/test_resolve_oem.py`.

---

## `parse_search.py`

**Purpose:** Normalize `search_active_cars` MCP responses. Two operating modes:

- **stats mode** (default): the active-inventory health call (`make=<Make>`, `car_type=<new|used>`, `rows=0`, `stats=price,dom`, `price_range="1-*"`). Emits `{num_found, stats_present, stats}`.
- **facets mode**: the brand-orphan recovery facet-discovery call (`facets=make|0|100`, `rows=0`, `country=US`). Emits `{num_found, facet_field, facets}`.

**Invocation:**
```bash
echo '<mcp-response>' | python scripts/parse_search.py
python scripts/parse_search.py --file <path>
python scripts/parse_search.py --mode facets --file <path>
```

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--mode` | enum: `stats`, `facets` | no | `stats` | Output mode |
| `--file` | path | no | (read stdin) | Read payload from disk (unwraps envelope) |

**Output (stats mode, success):** See dealer-group's equivalent — same shape. Standard `data.stats.{price, dom}` with `mean`, `median`, `percentiles{}`, etc.

**Output (stats mode, defensive fallback when `data.stats` is absent):**
```json
{
  "ok": true,
  "num_found": 1234,
  "stats_present": false,
  "stats": null
}
```

**Output (facets mode, success):**
```json
{
  "ok": true,
  "num_found": 6069613,
  "facet_field": "make",
  "facets": [
    {"item": "Toyota", "count": 198500},
    {"item": "Ford",   "count":  95200},
    ...
  ]
}
```

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `network` / `network_5xx` | Upstream error | Skip + DQ event (a) |
| `unexpected_shape` | No `data` key or `data` not a dict | Skip + DQ event (a) |
| `usage` | Invalid `--mode` value | Fix invocation |

**Edge cases:**
- Wire quirk: `data.start` and `data.rows` may arrive as strings on syndication paths. Both coerced to int.
- Facets mode: requesting a different field than `make` is not supported in v1 (the recovery branch only ever asks for `make`).
- Stats mode does NOT request facets — `data.facets` is ignored if present.

**Used by:** W1 / W2 active-inventory parsing (stats); SKILL.md "Before you start" step 3 recovery branch (facets).
**Test verification:** `tests/test_parse_search.py`.

---

## `parse_sold_summary.py`

**Purpose:** Normalize `get_sold_summary` MCP responses. Four mutually-exclusive aggregation modes:

- **No flag (raw normalization):** emits `{ok, row_count, rows}` with field-name normalization applied per row.
- **`--aggregate-make <make>`:** filter rows to one make and emit a weighted-mean `make_baseline` (single-month or aggregated-across-months).
- **`--aggregate-make-by-window <make>`:** filter to one make and group rows by `month`. Emits a `make_by_window` block with `months: {"YYYY-MM": <aggregate>, ...}` map.
- **`--aggregate-by-dimension {body_type|make} [--by-window]`:** bucket all rows by the named dimension; emits per-bucket aggregates with `share_pct`. `--by-window` additionally groups each bucket by month.

**Invocation:**
```bash
echo '<mcp>' | python scripts/parse_sold_summary.py
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-make "Ford"
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-make-by-window "Ford"
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-by-dimension make
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-by-dimension make --by-window
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-by-dimension body_type
```

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--aggregate-make` | string | no | — | Single-make rollup (single or multi-month aggregated). Mutex with others. |
| `--aggregate-make-by-window` | string | no | — | Single-make rollup grouped by month. Mutex with others. |
| `--aggregate-by-dimension` | enum: `body_type`, `make` | no | — | Per-dimension aggregates. Mutex with others. |
| `--by-window` | bool | no | false | Additionally group dimension buckets by month. Only meaningful with `--aggregate-by-dimension`. |
| `--file` | path | no | (read stdin) | Read payload from disk (unwraps envelope) |

**Passing more than one aggregation flag exits 1 (mutex enforced). `--by-window` without `--aggregate-by-dimension` exits 1.**

**Output (no aggregation flag, raw normalization):**
```json
{
  "ok": true,
  "row_count": 3,
  "rows": [
    {
      "month": "2026-04",
      "inventory_type": "Used",
      "state": "TX",
      "make": "Ford",
      "rank": 1,
      "sold_count": 4500,
      "average_sale_price": 24850.50,
      "total_sale_price": 111827250.0,
      "average_msrp": 26200.00,
      "price_over_msrp_percentage": -5.15,
      "average_days_on_market": 38.2,
      "median_days_on_market": 35.0,
      "sale_price_range": "44990.0",
      "sale_price_std_dev": 7234.55,
      "fuel_type_category": "ICE" | null
    }
  ]
}
```

Field-name normalizations: `avg_msrp` → `average_msrp`, `sale_price_std_dev` coerced to float, `sale_price_range` left as string, `rank` / `sold_count` coerced to int.

**Output with `--aggregate-make <make>` (success):**
```json
{
  "ok": true,
  "row_count": N,
  "rows": [...],
  "make_baseline": {
    "make": "Ford",
    "total_sold_count": 30164,
    "weighted_avg_sale_price": 54028.0,
    "weighted_avg_days_on_market": 116.3,
    "weighted_median_days_on_market": 101.7,
    "weighted_price_over_msrp_percentage": -6.26,
    "weighted_avg_msrp": 57681.4,
    "row_count": 2,
    "months_included": ["2026-04"]
  }
}
```

**Output with `--aggregate-make` when nothing matches OR total is zero:**
```json
{
  "ok": true,
  "rows": [...],
  "make_baseline": null,
  "make_baseline_skipped_reason": "no_matching_rows" | "all_zero" | "no_make_provided"
}
```

**Output with `--aggregate-make-by-window <make>`:**
```json
{
  "ok": true,
  "rows": [...],
  "make_by_window": {
    "make": "Ford",
    "months": {
      "2026-04": {<aggregate>},
      "2026-03": {<aggregate>},
      "2026-02": {<aggregate>},
      "2026-01": {<aggregate>}
    },
    "row_count": N
  }
}
```

Each month aggregate has shape: `{total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, weighted_median_days_on_market, weighted_price_over_msrp_percentage, weighted_avg_msrp, row_count, months_included}`.

Zero-sold months are dropped from `months`. If no months match, returns `make_by_window_skipped_reason`.

**Output with `--aggregate-by-dimension <dim>`:**
```json
{
  "ok": true,
  "rows": [...],
  "dimension": "make",
  "by_window": false,
  "dimension_values": [
    {"value": "Toyota", "total_sold_count": 198500, "weighted_avg_sale_price": 35200, "weighted_avg_days_on_market": 62.3, "share_pct": 21.0, ...},
    ...
  ],
  "dimension_total_sold_count": 944762
}
```

Sorted desc by `total_sold_count`. Buckets with total_sold == 0 dropped.

**Output with `--aggregate-by-dimension <dim> --by-window`:**
```json
{
  "ok": true,
  "rows": [...],
  "dimension": "make",
  "by_window": true,
  "dimension_values": [
    {
      "value": "Toyota",
      "months": {"2026-04": {<aggregate>}, "2026-03": {<aggregate>}},
      "total_sold_count_all_months": 397500,
      "share_pct_all_months": 21.0,
      "row_count": 106
    },
    ...
  ],
  "dimension_total_sold_count_all_months": 1889524,
  "months_included": ["2026-03", "2026-04"]
}
```

**Error envelopes (extends `_common`):**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `make_model_not_found` | Make string not in indexed values | Skip the affected call + DQ event |
| `validation_dimension_limit` | `ranking_dimensions` rejected by local validator | Retry once with `ranking_dimensions=make` only |
| `validation` | Local validator rejected some parameter | Skip + DQ event |
| `network_422` | Upstream HTTP 422 — usually non-month-aligned dates | Verify `compute_month_windows.py` window; skip + DQ |
| `network_5xx` | HTTP 5xx | Skip + DQ |
| `invalid_dimension` | `--aggregate-by-dimension` got something other than `body_type` or `make` | Fix invocation; exit 0 with `ok: false` |
| `truncation_unrecovered` | Truncation error string detected with no recovery path | Re-fire with narrower filters |
| `unknown` | Parser hit unexpected shape | Skip + DQ event |

**Never halt the whole workflow on a single `get_sold_summary` failure.** Graceful degradation — missing market-share call means no share signal but the headline still renders; missing prior-month call means MoM is null but current-month KPIs still render.

**Edge cases:**
- Response can wrap rows under `data.results[]` (public doc shape) OR `data.data[]` (live shape) OR `data.rows[]`. Parser handles all three.
- `get_sold_summary` is the only MCP tool whose payload is **NOT** envelope-wrapped — raw `{success, service, data}` is the live shape.
- Null-priced rows (territories like MP) drop from BOTH numerator AND denominator of weighted-ASP mean. Same for null-DOM, null-MSRP-positioning. They still contribute to `total_sold_count`.
- `--by-window` without `--aggregate-by-dimension` → exit 1.
- Passing multiple aggregation flags → exit 1.

**Used by:** W1 / W2 / W3 sold-summary parsing.
**Test verification:** `tests/test_parse_sold_summary.py`.

---

## `compute_oem_stats.py`

**Purpose:** Multi-make / multi-state numerical-aggregation engine. Consumes assembled JSON from parsed Wave A1/A2 responses; emits raw numeric values only (no bands — banding lives in `aggregate_signals.py`).

**Invocation:**
```bash
echo '<assembled-input>' | python scripts/compute_oem_stats.py
```

**Reads stdin?** Yes. No CLI flags.

**Input contract (stdin, JSON):**
```json
{
  "ticker": "F" | null,
  "company_name": "Ford Motor Company",
  "classification": "legacy" | "pure_play" | "brand_orphan",
  "makes": ["Ford", "Lincoln"],
  "inventory_type": "New" | "Used",
  "windows": {
    "current_month":      {date_from, date_to, label, days_in_month},
    "prior_month":        {date_from, date_to, label, days_in_month},
    "baseline_3mo":       {date_from, date_to, label, months_count}
  },
  "per_make": {
    "<Make>": {
      "sold_by_window":      {"months": {"YYYY-MM": <aggregate>, ...}},
      "active":              {"num_found", "stats": {"price": {...}, "dom": {...}} | null} | null,
      "segment_mix":         [{value, total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, share_pct}, ...] | null,
      "ev_slice_by_window":  {"months": {"YYYY-MM": <aggregate>, ...}} | null
    }
  },
  "market_top25": {
    "current": [<dimension_value_record>, ...],              // single-month current
    // EITHER (W1 v1.1+):
    "baseline_3mo_by_window": [                              // multi-month from --by-window parser
      {value, months: {"YYYY-MM": <aggregate>, ...},
       total_sold_count_all_months, share_pct_all_months}, ...
    ],
    // OR (legacy / W2):
    "prior": [<dimension_value_record>, ...] | []            // single-month prior
  },
  // Script accepts EITHER shape — `baseline_3mo_by_window` takes priority when present
  // (used by W1.A1.market_baseline_3mo). The legacy `prior` shape remains supported
  // for backward compatibility with existing test fixtures and for W2 (which uses
  // a separate market_current call only, no baseline).
  "ev_market_leaders": {                       // pure-play only; null for legacy/brand-orphan
    "months": {<YYYY-MM>: [<dim_value_record>, ...]},
    "all_months": [<dim_value_record>, ...]
  } | null
}
```

**Output (stdout, JSON):**
```json
{
  "ok": true,
  "ticker": "F" | null,
  "company_name": "Ford Motor Company",
  "classification": "legacy" | "pure_play" | "brand_orphan",
  "inventory_type": "New" | "Used",
  "windows": {...},

  "headline": {
    "sold_count_total":            <int> | null,
    "weighted_avg_sale_price":     <float> | null,
    "weighted_avg_days_on_market": <float> | null,
    "efficiency_score":            <float> | null
  },

  "leading_indicators_raw": {
    "volume":        {current, prior, baseline_3mo, baseline_3mo_avg_per_month, mom_pct, trend_3mo_pct},
    "asp":           {current, prior, baseline_3mo, mom_pct},
    "msrp_gap":      {current_pct, prior_pct, baseline_3mo_pct, delta_bps},
    "days_supply":   {current, prior, mom_pct},                        // no baseline_3mo — live snapshot tool
    "market_share":  {current_pct, prior_pct, baseline_3mo_pct, delta_bps},
    "dom":           {current, prior, baseline_3mo, delta_days},
    "ev_transition": {current_pct, prior_pct, baseline_3mo_pct, delta_bps} | null
  },

  "per_make_raw": [
    {make, sold_count_current, sold_count_prior, sold_count_baseline_3mo,
     weighted_avg_sale_price_current, weighted_avg_days_on_market_current,
     mom_vol_pct, trend_3mo_pct}
  ] | null,                                    // null for N==1 (pure_play, brand_orphan)

  "active_inventory": [
    {make, active_count, active_avg_price, active_dom, days_supply}
  ],
  "total_active_count": <int>,                  // sum of active_inventory[].active_count (Gap W2-D)

  "market_context": {
    "top_10_makes": [{rank, make, is_target_make, sold, share_pct, delta_bps}],
    "ticker_aggregate_share_pct": <float> | null,
    "target_makes_in_top25": [<make>, ...],
    "target_makes_outside_top25": [<make>, ...]
  },

  "ev_block": {
    "shape": "transition" | "market_leaders" | "omitted",
    "transition": {
      ticker_ev_pct,           ticker_ev_asp,           ticker_ev_dom,           ticker_ev_sold,
      ticker_ev_asp_prior,     ticker_ev_dom_prior,     ticker_ev_sold_prior,                       // NEW (Gap 2)
      ticker_ev_asp_mom_pct,   ticker_ev_dom_delta_days, ticker_ev_sold_mom_pct,                    // NEW (Gap 2)
      per_make_breakdown[], narrative_note
    } | null,
    "market_leaders": [{rank, make, ev_sold, ev_share_pct, ev_asp}] | null
  },
  // For pure_play classification:
  //   - W1 (ev_market_leaders provided): shape="market_leaders", transition=null.
  //   - W2 (ev_market_leaders=null): shape="transition", transition synthesized from headline
  //     with ticker_ev_pct=100.0 (entire volume is EV by definition). Gap W2-A/B.

  "segment_mix": [{body_type, sold, share_pct, asp, dom}],
  "segment_mix_complete": true | false,                    // false if any make's segment_mix was null
  "makes_with_segment_mix": ["<make1>", "<make2>", ...],   // contributing makes only

  "active_inventory_complete": true | false,               // false if any make's active was null
  "makes_with_active": ["<make1>", "<make2>", ...],

  "total_active_count": int,                               // sum of active_inventory[*].active_count

  "dq_events": ["(c) ...", "(i) ...", "(k) ...", "(p) ...", "(q) ...", "(r) ...", "(s) ...", "(t) ...", "(u) ..."]
}
```

**New defensive DQ events (round 5 — silent-failure elimination):**

| Event | Trigger | Surfaces |
|---|---|---|
| `(p)` | One or more makes had `per_make[X].segment_mix = null`; rollup excludes them | `compute_oem_stats._build_segment_mix` |
| `(q)` | One or more makes had `per_make[X].active = null`; Days Supply rollup incomplete | `compute_oem_stats._build_active_inventory` |
| `(r)` | One or more makes excluded from `per_make_raw` due to empty months (no sold data) | `compute_oem_stats._build_per_make_raw` |
| `(s)` | Zero-EV makes excluded from EV per-make breakdown (informational, not warning) | `compute_oem_stats._build_ev_block` |
| `(t)` | Math consistency: sum-of-parts diverged from headline beyond threshold (0.1% for per-make/active, 5% for seg-mix) | `compute_oem_stats.main()` |
| `(u)` | `market_top25.current` was empty; market-share verdict cannot be computed | `compute_oem_stats._compute_market_share` |

**Input validation (deep, per `_validate_input` C-S8):**
- `windows.current_month` must be a dict with `date_from` + `date_to`.
- `per_make` must be a non-empty dict (for legacy/brand_orphan).
- Each `per_make[X]` must be a dict with `sold_by_window` (other fields may be null).
- `per_make[X].sold_by_window`, `.active`, `.ev_slice_by_window` if present must be `dict|null`.
- `per_make[X].segment_mix` if present must be `list|null`.
- `market_top25` must contain at least one of `current` / `baseline_3mo_by_window` / `prior`.
- Violations exit with `{ok: false, error_type: "missing_required_field" | "malformed_per_make_value" | "malformed_per_make_field", field: "<path>"}`.

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `bad_stdin` | Stdin was not valid JSON | Fix caller |

(All other failure modes are graceful degradation — individual fields land as `null`, never NaN, never fabricated.)

**Edge cases (resolved as `null`):**
- `headline.efficiency_score` is null when DOM ≤ 0 or null.
- `leading_indicators_raw.<metric>.mom_pct` / `trend_3mo_pct` are null when denominator is 0 or null.
- `leading_indicators_raw.dom.delta_days` is null when either side is null.
- `leading_indicators_raw.days_supply.prior` is always null in v1 (search_active_cars is a live-snapshot tool; historical inventory isn't exposed).
- `leading_indicators_raw.market_share.delta_bps` is null when either current or prior cohort total is 0.
- `leading_indicators_raw.ev_transition` is null for pure-play (ev_block.shape == "market_leaders") and zero-EV legacy (ev_block.shape == "omitted").
- `per_make_raw` is null when classification ∈ {pure_play, brand_orphan} OR when `len(makes) < 2`.
- `active_inventory` is `[]` when no makes returned active data; per-make entry is dropped silently when that make's `active` is null.
- Low-volume DQ event (i) fires for any per-make `sold_count_current < 100`.

**Used by:** W1 (full surface); W2 (slimmer slice — no MoM since W2 is single-month).
**Test verification:** `tests/test_compute_oem_stats.py`.

---

## `aggregate_signals.py`

**Purpose:** Reduce raw numeric values from `compute_oem_stats` into per-metric bands, composite slots, single headline verdict, signal drivers, and per-make divergence. Bands and reduction algorithm are domain rules — see `references/signal-aggregation.md` for the per-metric thresholds, composite combiners, and worked examples. This file documents the I/O contract only.

**Invocation:**
```bash
echo '<raw-values-and-classification>' | python scripts/aggregate_signals.py
```

**Reads stdin?** Yes. No CLI flags.

**Input contract:**
```json
{
  "leading_indicators_raw": {
    "volume":        {current, prior, baseline_3mo, baseline_3mo_avg_per_month, mom_pct, trend_3mo_pct},
    "asp":           {current, prior, baseline_3mo, mom_pct},
    "msrp_gap":      {current_pct, prior_pct, baseline_3mo_pct, delta_bps},
    "days_supply":   {current, prior, mom_pct},                        // no baseline_3mo — live snapshot tool
    "market_share":  {current_pct, prior_pct, baseline_3mo_pct, delta_bps},
    "dom":           {current, prior, baseline_3mo, delta_days},
    "ev_transition": {current_pct, prior_pct, baseline_3mo_pct, delta_bps} | null
  },
  "per_make_raw": [{make, mom_vol_pct, ...}, ...] | null,
  "ticker_classification": "legacy" | "pure_play" | "brand_orphan"
}
```

**Output:**
```json
{
  "ok": true,
  "ticker_classification": "legacy" | "pure_play" | "brand_orphan",
  "per_metric_bands": {
    "volume_mom":    "BULLISH" | "NEUTRAL" | "CAUTION" | "BEARISH" | null,
    "volume_trend":  "...",
    "asp":           "...",
    "msrp_gap":      "...",
    "days_supply":   "...",
    "market_share":  "...",
    "dom":           "...",
    "ev_transition": "..." | null
  },
  "composite_slots": {
    "volume_momentum": "BULLISH" | "NEUTRAL" | "CAUTION" | "BEARISH" | null,
    "pricing_power":   "...",
    "days_supply":     "...",
    "market_share":    "...",
    "dom":             "...",
    "ev_transition":   "..." | null
  },
  "verdict": "BULLISH" | "BEARISH" | "NEUTRAL" | "MIXED" | null,
  "scores": {<slot>: {"band": "<band>", "score": +2|-2|-1|0} | null, ...},
  "mean_score":  <float> | null,
  "n_bullish":   <int>,
  "n_bearish":   <int>,
  "rationale":   "<string>",
  "signal_drivers": {
    "strongest": {slot, band, score} | null,
    "weakest":   {slot, band, score} | null
  },
  "per_make_divergence": [
    {make, make_volume_band, make_volume_score, ticker_composite_score, gap}
  ]
}
```

**Per-band score:** BULLISH +2, NEUTRAL 0, CAUTION −1, BEARISH −2 (asymmetric — see signal-aggregation.md).

**No-scoreable-signals case** (every composite slot null):
```json
{
  "verdict": null,
  "rationale": "No scoreable signals — all composite slots are null.",
  "reason": "no_scoreable_signals"
}
```

**Reduction algorithm (first-match-wins, documented in signal-aggregation.md):**
1. Skip null composite slots.
2. mean = mean(scores) across contributing.
3. `n_bullish > 0 AND n_bearish > 0` → MIXED
4. `mean ≥ +1.0 AND n_bearish == 0` → BULLISH
5. `mean ≤ -1.0 AND n_bullish == 0` → BEARISH
6. else → NEUTRAL

**Per-make divergence rule:** For each `per_make_raw[i]`, band the make's `mom_vol_pct` using the volume-MoM banding table; compute `gap = |make_score − ticker_composite_score|` where `ticker_composite_score` is `scores.volume_momentum.score`. If `gap >= 2`, emit the entry. Empty array when no divergence OR when `per_make_raw` is null.

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `bad_stdin` | Stdin was not valid JSON | Fix caller |

**Edge cases:**
- A null underlying metric value → null band; that band does not contribute to composite slot evaluation (degraded mode).
- `ev_transition` always null for pure-play classification (no per-make EV slice fires).
- `days_supply.current` from compute_oem_stats — banding applied directly (not on `mom_pct` since prior is always null in v1).
- `per_make_divergence` empty when `ticker_composite_score` is null (no volume_momentum slot → can't compare).

**Used by:** W1 (verdict reduction).
**Test verification:** `tests/test_aggregate_signals.py`.

---

## Drift safeguard

When modifying any `scripts/*.py`, update this file in the same commit. The matching `tests/test_<script>.py` is the runtime verification — if a contract here disagrees with a test assertion, the test wins.

This is normative discipline, not enforcement.
