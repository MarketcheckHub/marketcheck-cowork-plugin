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
| `_common.py` | Shared helpers (`read_input`, `emit`, `classify_error`, `arg_value`, `arg_flag`) | (not directly invoked) | every parser |
| `compute_month_windows.py` | Emit calendar-month-aligned current/prior windows | `--today YYYY-MM-DD` | W1 / W2 / W3 pre-flight |
| `resolve_group_name.py` | Resolve user input → canonical name + ticker + classification | `--input "<text>"` (+ 3 optional file overrides) | W1 / W2 pre-flight |
| `parse_search.py` | Normalize `search_active_cars` responses (2 modes) | `--mode {stats\|facets}`, `--file <path>` | W1 / W2 active-inventory + recovery-branch facets |
| `parse_sold_summary.py` | Normalize `get_sold_summary` responses (3 aggregation modes) | `--aggregate-group <name>` ∣ `--aggregate-by-group` ∣ `--aggregate-by-dimension {body_type\|make}`, `--file <path>` | W1 / W2 / W3 sold-summary parsing |
| `compute_group_stats.py` | Compute headline + MoM + active-health + peer-rank | (stdin only) | W1 / W2 stats engine |
| `aggregate_signals.py` | Reduce per-metric values to BULLISH/BEARISH/NEUTRAL/MIXED verdict | (stdin only) | W1 verdict reduction |

## Conventions (all parsers)

- **Stdin-default.** Every parser reads its payload from stdin by default. Use the `--file <path>` flag ONLY when the MCP runtime saved an oversized response to disk and returned an `Output saved to <path>` error string — never create those files yourself. See `SKILL.md §Script invocation discipline`.
- **Truncation envelope.** When loaded via `--file`, the parser unwraps the `{"result": "<stringified JSON>"}` envelope automatically (via `_common._maybe_unwrap`). `get_sold_summary` is the only MCP tool whose payload is NOT envelope-wrapped — its raw `{success, service, data}` passes through transparently.
- **Canonical response shape.** Every parser emits a single JSON document with `ok: true|false` at top level. On `ok: false`, an `error_type` enum classifies the failure; the caller branches on it.
- **Process exit codes.** Validation errors (mutex flag conflicts, bad CLI args, missing required input) exit `1` with no JSON. Payload-level errors (network failures, schema misses, classifier hits) exit `0` with `{"ok": false, "error_type": "...", ...}` on stdout — the caller is expected to parse and branch.
- **Field naming.** Server-side quirks (`avg_msrp`, `sale_price_std_dev`) are normalized at parse time. The contract here is the **post-normalization** name (`average_msrp`, etc.).

## Overlap rule — where each kind of doc lives

| Topic | Canonical location |
|---|---|
| Script I/O shapes (stdin/stdout, CLI flags, error envelopes) | **This file** |
| Per-metric banding tables + verdict reduction algorithm | `references/signal-aggregation.md` |
| MCP tool parameter discipline (`get_sold_summary` always-set/never-set params, syndication-routing notes) | `references/sold-summary-safety.md` |
| Used-only / New-only / Both classification → channel call shape | `references/inventory-type-classification.md` |
| 471-entry canonical group enum | `references/dealership_group_enum.md` |
| 8-entry ticker ↔ canonical map | `references/ticker-mapping.md` |
| Wave structures (which calls fire in which order) | `references/w1-single-group.md`, `w2-compare-two.md`, `w3-top-n.md` |
| Output rendering rules | `assets/w*-output-template.md` |

This file points outward to those references where appropriate, never inward (no circular pointers).

---

## `_common.py`

**Purpose:** Shared library used by every parser. Not invoked directly. Documents the canonical envelope/error machinery so per-script error tables can stay short.

**Public helpers** (used by other scripts; the contract for these helpers is internal, not user-facing):

| Helper | Purpose |
|---|---|
| `read_input(argv)` | Read JSON from stdin or `--file <path>`; unwrap `{"result": "<stringified>"}` envelope transparently. Returns `(payload, source)` where source is `"stdin"` or the file path. |
| `emit(obj)` | Serialize an object to stdout as compact JSON. Used for every successful and error response. |
| `classify_error(payload)` | Inspect a payload for transport-level failure signatures (HTTP status, network errors). Returns `(error_type, error_message)` or `("", "")` on success. |
| `arg_value(argv, flag)` | Parse `--flag value` from argv. Returns the value string or `None`. |
| `arg_flag(argv, flag)` | Parse boolean `--flag` from argv. Returns `True` if present. |

**Generic `error_type` catalogue** (extended by individual parsers):

| `error_type` | Meaning | Recovery |
|---|---|---|
| `network` | Generic network error reported upstream | Skip the call; log DQ event (a). |
| `network_422` | HTTP 422 — upstream rejected the request body | Most common root cause: non-month-aligned dates. Verify `compute_month_windows.py` was used. If aligned, skip + DQ event. |
| `network_5xx` | HTTP 500/502/503/504 — upstream server error | Skip + DQ event. Could be retried but skip is cheaper for an enrichment signal. |
| `unexpected_shape` | Payload top-level shape did not match expected `{success, service, data}` | Skip + DQ event with snippet. |
| `unknown` | Parser hit a shape it couldn't classify | Skip + DQ event with payload snippet. |
| `truncation_unrecovered` | Parser detected a truncation error string but no recovery path was available | Re-fire the upstream call with narrower filters. |

Per-script extensions are documented in each script's section below.

**Used by:** every parser.
**Test verification:** indirectly via every `tests/test_<parser>.py`; no dedicated `tests/test_common.py`.

---

## `compute_month_windows.py`

**Purpose:** Emit calendar-month-aligned `current_month` and `prior_month` windows for sold-summary calls. The "strictly-before" rule (`current_month` ended *before* today, not including today) sidesteps the race where `get_sold_summary` aggregates lag the calendar.

**Invocation:**
```bash
python scripts/compute_month_windows.py --today 2026-05-11
```

**Reads stdin?** No.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--today` | string `YYYY-MM-DD` | no | system date | Reference date used to compute windows |

**Output (stdout, JSON):**
```json
{
  "today": "2026-05-11",
  "current_month": {
    "date_from": "2026-04-01",     // first of calendar month
    "date_to":   "2026-04-30",     // last of calendar month
    "label":     "April 2026",
    "days_in_month": 30
  },
  "prior_month": {
    "date_from": "2026-03-01",
    "date_to":   "2026-03-31",
    "label":     "March 2026",
    "days_in_month": 31
  }
}
```

**Error envelopes:** None at the payload level. Malformed `--today` value exits `1` with stderr message and no JSON output.

**Edge cases:**
- First of month (e.g. `--today 2026-05-01`) → `current_month = April 2026` (April ended strictly before May 1).
- Last of month (`--today 2026-05-31`) → `current_month = April 2026` (May not yet ended at any time on May 31).
- First of next month (`--today 2026-06-01`) → `current_month = May 2026`.
- Year boundary (`--today 2026-01-01` or `2026-01-15`) → `current_month = December 2025`.
- Leap-year February (`--today 2024-03-05`) → `current_month.days_in_month = 29`.
- Non-leap February (`--today 2026-03-05`) → `current_month.days_in_month = 28`.

**Used by:** `SKILL.md §Before you start` step 2; W1 / W2 / W3 pre-flight in `references/w1-single-group.md`, `w2-compare-two.md`, `w3-top-n.md`.
**Test verification:** `tests/test_compute_month_windows.py` (10 tests).

---

## `resolve_group_name.py`

**Purpose:** Map a user-supplied group name or ticker symbol to the canonical 471-enum name, ticker, and inventory-type classification. Resolution proceeds in three tiers: exact match → ticker symbol (auto-uppercased) → fuzzy via `difflib.SequenceMatcher`. Below the fuzzy threshold (0.5), emits `error_type=no_candidates` which triggers the active-facets recovery branch documented in `SKILL.md §Before you start` step 3.

**Invocation:**
```bash
python scripts/resolve_group_name.py --input "LAD"
python scripts/resolve_group_name.py --input "AutoNation Inc."
python scripts/resolve_group_name.py --input "carmax"
```

**Reads stdin?** No.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--input` | string | yes | — | User-supplied group name or ticker. Empty / absent → `error_type=missing_input`. |
| `--enum-file` | path | no | `references/dealership_group_enum.md` | Override the 471-entry enum source |
| `--ticker-file` | path | no | `references/ticker-mapping.md` | Override the 8-row ticker map |
| `--classification-file` | path | no | `references/inventory-type-classification.md` | Override the Used-only / New-only lists |

**Output on success (stdout, JSON):**
```json
{
  "ok": true,
  "input": "LAD",
  "resolution": "exact" | "ticker" | "fuzzy",
  "canonical": "Lithia Motors Inc.",       // string, always present on success
  "ticker": "LAD" | null,                  // null for the ~463 non-public canonical names
  "classification": "Used-only" | "New-only" | "Both",
  "candidates": [{"canonical": "...", "score": 0.92}, ...]   // top-N fuzzy candidates; usually [] on exact/ticker hits
}
```

**Output on failure (stdout, JSON):**
```json
{
  "ok": false,
  "error_type": "missing_input" | "no_candidates",
  "candidates": [...]                      // present on no_candidates; top-10 fuzzy by score, all below 0.5
}
```

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `missing_input` | `--input` absent or empty string | Re-prompt the user for a ticker / group name. |
| `no_candidates` | No fuzzy candidate scored ≥ 0.5 | Fall through to the **active-facets recovery branch** in `SKILL.md §Before you start` step 3. Do NOT call `get_sold_summary` directly with the unresolved name (returns ~10 KB error). |

**Edge cases:**
- Ticker input is auto-uppercased (`"cvna"` → `"CVNA"` → resolves to Carvana).
- Exact-match resolution is sensitive to trailing punctuation. `"AutoNation"` (no `Inc.`) resolves via **fuzzy** to `"AutoNation Inc."`, not exact.
- A canonical name not in the 8-row ticker map returns `ticker: null` (e.g., Hendrick Automotive Group, all ~462 private dealer groups).
- Five punctuation quirks resolve via exact match: `"#1 Cochran Automotive Group"`, `"Hall | Mileone Autogroup"`, `"Demontrond Auto Group's"`, `"Americas Car-mart, Inc."`, `"Asbury Automotive Group"` (no trailing period).
- Classification falls through to `"Both"` for any canonical name not in the Used-only (7 names) or New-only (2 names) lists.

**Used by:** `SKILL.md §Before you start` step 3; W1 / W2 pre-flight.
**Test verification:** `tests/test_resolve_group_name.py` (12 tests).

---

## `parse_search.py`

**Purpose:** Normalize `search_active_cars` MCP responses. Two operating modes:

- **stats mode** (default): the active-inventory health call (`mc_dealership_group_name=<canonical>`, `rows=0`, `stats=price,dom`). Emits `{num_found, stats_present, stats}`.
- **facets mode**: the recovery-branch facet-discovery call (`facets=mc_dealership_group_name|0|1000`, no group filter). Emits `{num_found, facet_field, facets}`.

**Invocation:**
```bash
# stats mode (default):
echo '<mcp-response>' | python scripts/parse_search.py
python scripts/parse_search.py --file <path>

# facets mode:
python scripts/parse_search.py --mode facets --file <path>
```

**Reads stdin?** Yes (default). Use `--file` for truncation-envelope unwrap.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--mode` | enum: `stats`, `facets` | no | `stats` | Output mode |
| `--file` | path | no | (read stdin) | Read payload from disk (unwraps envelope) |

**Output (stats mode, success):**
```json
{
  "ok": true,
  "num_found": 91041,
  "start": 0,                              // coerced from string ("0") to int
  "rows": 0,                               // coerced from string ("0") to int
  "stats_present": true,
  "stats": {
    "price": {
      "min": 7998,
      "max": 129998,
      "count": 91035,
      "missing": 6,
      "mean": 28786.9,
      "stddev": ...,
      "median": 26251.99,
      "percentiles": {"5.0": ..., "25.0": ..., "50.0": 26251.99, "75.0": ..., "90.0": ..., "95.0": ..., "99.0": ...}
    },
    "dom":   { ... same shape as price ... }
  }
}
```

**Output (stats mode, defensive fallback when `data.stats` is absent):**
```json
{
  "ok": true,
  "num_found": 1234,
  "start": 0,
  "rows": 0,
  "stats_present": false,
  "stats": null
}
```
Renderer should surface a DQ event (d) and skip Days Supply for that channel.

**Output (facets mode, success):**
```json
{
  "ok": true,
  "num_found": 6069613,
  "start": 0,
  "rows": 0,
  "facet_field": "mc_dealership_group_name",
  "facets": [
    {"item": "Lithia Motors Inc.", "count": 114368},
    {"item": "AutoNation Inc.",     "count":  98880},
    ...
  ]
}
```
Facets are sorted desc by `count`. Entries without `item`, with empty-string `item`, or non-dict entries are dropped. Missing `count` defaults to 0.

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `network` | Upstream reported `error_type: network` in the response | Skip + DQ event (a). |
| `network_5xx` | HTTP 5xx from upstream (status_code 500/502/503/504) | Skip + DQ event (a). |
| `unexpected_shape` | Payload had no `data` key, or `data` was not a dict | Skip + DQ event (a) with snippet. |
| `usage` | Invalid `--mode` value (not `stats` or `facets`) | Fix the invocation; do not retry without correction. |

**Edge cases:**
- Wire quirk: `data.start` and `data.rows` arrive as strings (`"0"`) on the syndication-routing path. Both are coerced to int. The parser also accepts int.
- Facets mode: requesting a facet field that isn't in `data.facets` (e.g., field is `make` but response has `mc_dealership_group_name`) → `facets: []` (not a crash, not an error).
- Facets mode: `data.facets == {}` → `facets: []`.
- Stats mode does NOT request facets — `data.facets` is ignored if present.

**Used by:** `SKILL.md §Tool surface`; W1 / W2 active-inventory parsing; SKILL.md "Before you start" step 3 recovery branch (facets mode).
**Test verification:** `tests/test_parse_search.py` (12 tests).

---

## `parse_sold_summary.py`

**Purpose:** Normalize `get_sold_summary` MCP responses. Three mutually-exclusive aggregation modes:

- **No flag (raw normalization):** emits `{ok, row_count, rows}` with field-name normalization applied per row.
- **`--aggregate-group <canonical>`:** filter rows to one group and emit weighted-mean `group_baseline`.
- **`--aggregate-by-group`:** bucket all rows by `dealership_group_name`, one aggregate per group.
- **`--aggregate-by-dimension <body_type|make>`:** bucket rows by `body_type` or `make`, one aggregate per distinct value with `share_pct`.

**Invocation:**
```bash
# raw normalization:
echo '<mcp-response>' | python scripts/parse_sold_summary.py

# single-group baseline (W1 / W2 target call):
echo '<mcp-response>' | python scripts/parse_sold_summary.py --aggregate-group "Lithia Motors Inc."

# per-group aggregates (W1 / W3 peer leaderboard):
echo '<mcp-response>' | python scripts/parse_sold_summary.py --aggregate-by-group

# per-dimension aggregates (W1 / W2 Wave B mix calls):
python scripts/parse_sold_summary.py --aggregate-by-dimension body_type --file <path>
python scripts/parse_sold_summary.py --aggregate-by-dimension make --file <path>
```

**Reads stdin?** Yes (default). Use `--file` for truncation-envelope unwrap.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--aggregate-group` | string | no | — | Single-group baseline (filters by canonical name). Mutex with the other two aggregation flags. |
| `--aggregate-by-group` | bool | no | false | Per-group aggregates. Mutex. |
| `--aggregate-by-dimension` | enum: `body_type`, `make` | no | — | Per-dimension aggregates. Mutex. |
| `--file` | path | no | (read stdin) | Read payload from disk (unwraps envelope) |

**Passing more than one aggregation flag exits 1** (mutex enforced).

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
      "city": null,
      "dealership_group_name": "Carmax",
      "make": null,
      "model": null,
      "body_type": null,
      "rank": 1,                                  // coerced to int
      "sold_count": 4500,                         // coerced to int
      "average_sale_price": 24850.50,             // coerced to float
      "total_sale_price": 111827250.0,
      "average_msrp": 26200.00,                   // server's `avg_msrp` → normalized
      "price_over_msrp_percentage": -5.15,
      "average_days_on_market": 38.2,
      "median_days_on_market": 35.0,
      "sale_price_range": "44990.0",              // remains a string (single value, not low/high)
      "sale_price_std_dev": 7234.55               // server's `sale_price_std_dev` coerced to float
    }
  ]
}
```

Field-name normalizations applied at parse time (server name → canonical name):
- `avg_msrp` → `average_msrp`
- `sale_price_std_dev` coerced from string to float
- `sale_price_range` left as string (server emits e.g. `"44990.0"`, NOT a low/high pair)
- `rank`, `sold_count` coerced to int
- All price/DOM fields coerced to float

**Output with `--aggregate-group <canonical>` (success):**
```json
{
  "ok": true,
  "row_count": 3,
  "rows": [...],                                  // raw rows still present
  "group_baseline": {
    "dealership_group_name": "Carmax",
    "total_sold_count": 11500,                    // sum of sold_count across matching rows
    "weighted_avg_sale_price": 24840.07,          // sum(asp * sc) / sum(sc) across matching rows
    "weighted_avg_days_on_market": 38.85,         // sum(dom * sc) / sum(sc)
    "row_count_for_group": 3,
    "months_included": ["2026-04"]
  }
}
```

**Output with `--aggregate-group` when nothing matches OR total is zero:**
```json
{
  "ok": true,
  "row_count": 3,
  "rows": [...],
  "group_baseline": null,
  "group_baseline_skipped_reason": "no_matching_rows" | "all_zero" | "no_canonical_provided"
}
```

**Output with `--aggregate-by-group`:**
```json
{
  "ok": true,
  "row_count": 11,
  "rows": [...],
  "groups": [
    {
      "dealership_group_name": "Carmax",
      "total_sold_count": 8300,
      "weighted_avg_sale_price": 25203.13,
      "weighted_avg_days_on_market": 39.71,
      "row_count": 2,                             // number of underlying rows for this group
      "months_included": ["2026-04"]
    },
    ...                                            // sorted desc by total_sold_count
  ]
}
```
Groups with total_sold_count == 0 are dropped entirely (never emitted as null records).

**Output with `--aggregate-by-dimension body_type` (or `make`):**
```json
{
  "ok": true,
  "row_count": 31,
  "rows": [...],
  "dimension": "body_type",
  "dimension_total_sold_count": 31700,
  "dimension_values": [
    {
      "value": "SUV",
      "total_sold_count": 15000,
      "weighted_avg_sale_price": 27170.0,
      "weighted_avg_days_on_market": 43.6,
      "row_count": 5,
      "months_included": ["2026-04"],
      "share_pct": 47.32                          // round(100 * total_sold / dimension_total, 2)
    },
    ...                                            // sorted desc by total_sold_count
  ]
}
```
Rows with a `null` or empty-string dimension value are skipped. Buckets whose summed sold_count is 0 are dropped (same divide-by-zero guard as `--aggregate-group`).

**Error envelopes (extends `_common`):**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `make_model_not_found` | Make/model string not in indexed values | Skip the affected mix call with DQ event. Don't retry. (Only relevant to Wave B mix calls.) |
| `validation_dimension_limit` | `ranking_dimensions` rejected by local validator | Retry once with `ranking_dimensions=dealership_group_name` only. |
| `validation` | Local validator rejected some parameter | Skip + DQ event with validation message. Do NOT halt the workflow. |
| `network_422` | Upstream HTTP 422 — usually non-month-aligned dates | Verify `compute_month_windows.py` window. If aligned, skip + DQ. |
| `network_5xx` | HTTP 5xx | Skip + DQ. |
| `invalid_dimension` | `--aggregate-by-dimension` got something other than `body_type` or `make` | Fix the invocation; do not retry without correction. Exit 0 with `ok: false`. |
| `truncation_unrecovered` | Truncation error string detected with no recovery path | Re-fire with narrower filters. |
| `unknown` | Parser hit unexpected shape | Skip + DQ event with snippet. |

**Never halt the whole workflow on a single `get_sold_summary` failure.** The workflow degrades gracefully — missing peer leaderboard means no peer rank but the headline still renders; missing prior month means MoM is null but current-month KPIs still render.

**Edge cases:**
- Response can wrap rows under `data.results[]` (public doc shape) OR `data.data[]` (live shape). Parser handles both.
- `get_sold_summary` is the only MCP tool whose payload is **NOT** envelope-wrapped — raw `{success, service, data}` is the live shape. The `--file` path still works (the runtime envelope is unwrapped if present).
- `sale_price_range` arrives as a single string (e.g. `"44990.0"`), NOT a `{low, high}` pair. Documented in `references/sold-summary-safety.md`.
- `--aggregate-by-dimension` is mutex with the other two aggregation flags. Passing multiple → exit 1.
- `--aggregate-by-dimension fuel_type_category` (not in the allowed set) → `ok: false`, `error_type: invalid_dimension`, exit 0.

**Used by:** `SKILL.md §Tool surface`; W1 / W2 / W3 sold-summary parsing.
**Test verification:** `tests/test_parse_sold_summary.py` (15 tests).

---

## `compute_group_stats.py`

**Purpose:** Compute the deterministic stats engine for one dealer group: combined-channel headline, MoM percentage changes, active-inventory health with Days Supply, and peer ranking against the public-traded subset of the leaderboard. Used by W1 (single-group health check) and W2 (head-to-head — though W2 uses a slimmer slice).

**Invocation:**
```bash
echo '<assembled-input>' | python scripts/compute_group_stats.py
```

**Reads stdin?** Yes. No CLI flags.

**Input contract (stdin, JSON):**
```json
{
  "group_canonical": "Lithia Motors Inc.",
  "ticker": "LAD" | null,
  "classification": "Used-only" | "New-only" | "Both",
  "current_month_window": {
    "date_from": "2026-04-01",
    "date_to":   "2026-04-30",
    "days_in_month": 30                          // required — Days Supply uses this
  },
  "current_month": {
    "used": <channel> | null,                    // null for New-only groups
    "new":  <channel> | null                     // null for Used-only groups
  },
  "prior_month": {
    "used": <channel> | null,
    "new":  <channel> | null
  },
  "active": {
    "used": <active> | null,
    "new":  <active> | null
  },
  "peer_leaderboard": [<group_record>, ...]      // may be []
}
```

Where:

```
<channel> = {
  "sold_count": <int>,                           // also accepts "total_sold_count" as a synonym
  "weighted_avg_sale_price": <float> | null,
  "weighted_avg_days_on_market": <float> | null
}

<active> = {
  "num_found": <int>,
  "stats": {
    "price": {"mean": <float>, ...} | null,      // only `mean` is used downstream
    "dom":   {"mean": <float>, ...} | null
  } | null
}

<group_record> = {                                // exactly the shape emitted by parse_sold_summary --aggregate-by-group
  "dealership_group_name": <string>,
  "total_sold_count": <int>,
  "weighted_avg_sale_price": <float>,
  "weighted_avg_days_on_market": <float>
}
```

**Output (stdout, JSON):**
```json
{
  "ok": true,
  "group_canonical": "Lithia Motors Inc.",
  "ticker": "LAD" | null,
  "classification": "Used-only" | "New-only" | "Both",

  "headline": {
    "sold_count_total":               <int> | null,
    "weighted_avg_sale_price":        <float> | null,
    "weighted_avg_days_on_market":    <float> | null,
    "efficiency_score":               <float> | null   // sold_count_total / DOM; null when DOM ≤ 0 or null
  },

  "mom": {
    "volume_pct":      <float> | null,           // (cur - prior) / prior * 100; null when prior is 0 or null
    "asp_pct":         <float> | null,
    "dom_delta":       <float> | null,           // cur_dom - prior_dom (units = days); null when either side null
    "efficiency_pct":  <float> | null
  },

  "active_health": {
    "used": {
      "num_found":          <int>,
      "days_supply":        <float> | null,      // num_found * days_in_month / sold_count; null when sold == 0
      "active_avg_price":   <float> | null,
      "active_avg_dom":     <float> | null
    } | null,
    "new":  { ... same shape ... } | null,
    "footnote": "Days Supply pairs live active inventory (today's snapshot) with the most-recent-complete-month sold velocity — a live-vs-historical mix."
  },

  "peer_rank": {
    "of": <int>,                                  // count of public-traded groups present in the leaderboard (≤ 8)
    "by_volume":     {"rank": <int>, "delta_to_next_pct": <float>?} | null,
    "by_asp":        {"rank": <int>} | null,
    "by_dom":        {"rank": <int>} | null,     // lower is better
    "by_efficiency": {"rank": <int>} | null,
    "peers": [
      {
        "canonical":                    <string>,
        "ticker":                       <string>,
        "is_target":                    <bool>,
        "sold_count":                   <int> | null,
        "weighted_avg_sale_price":      <float> | null,
        "weighted_avg_days_on_market":  <float> | null,
        "efficiency_score":             <float> | null
      },
      ...                                          // sorted desc by sold_count; bolded by renderer when is_target
    ],
    "dropped": [<canonical_name>, ...]            // public-traded names NOT in this leaderboard; alphabetized
  } | null
}
```

**`peer_rank` is null** when the target group is not present in the leaderboard (fell below top-20).

**`delta_to_next_pct`** on `by_volume` is populated when there is a next group below the target on the volume axis (any rank, not just rank 1). The renderer chooses whether to surface it (per the W1 template, only when target is rank 1 and the clause reads "ahead of #2").

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `bad_stdin` | Stdin was not valid JSON | Fix caller. |

(All other failure modes are graceful degradation — individual fields land as `null`, never NaN, never fabricated.)

**Edge cases (resolved as `null`):**
- `efficiency_score` is null when DOM ≤ 0 or null.
- `mom.volume_pct` / `mom.asp_pct` / `mom.efficiency_pct` are null when prior is 0 or null.
- `mom.dom_delta` is null when either side is null.
- `active_health.{used,new}.days_supply` is null when `sold_count` is 0, or `num_found` is null, or `days_in_month` is missing.
- `peer_rank` is null when target not in leaderboard, OR when leaderboard is `[]`.
- `peer_rank.by_<metric>` is null when no public-traded group has a non-null value for that metric.

**Internal mapping** — the 8-name public set used for `peer_rank` filtering and ticker assignment:

| Canonical | Ticker |
|---|---|
| AutoNation Inc. | AN |
| Lithia Motors Inc. | LAD |
| Penske Automotive Group Inc. | PAG |
| Sonic Automotive Inc. | SAH |
| Group 1 Automotive Inc. | GPI |
| Asbury Automotive Group | ABG |
| Carmax | KMX |
| Carvana | CVNA |

Authoritative source: `references/ticker-mapping.md`.

**Used by:** `references/w1-single-group.md` (full surface); `references/w2-compare-two.md` (slim slice — no MoM since W2 is single-month).
**Test verification:** `tests/test_compute_group_stats.py` (17 tests).

---

## `aggregate_signals.py`

**Purpose:** Reduce per-metric values from `compute_group_stats` into a single headline verdict (BULLISH / BEARISH / NEUTRAL / MIXED / null). Bands and reduction algorithm are domain rules — see `references/signal-aggregation.md` for the per-metric thresholds, score asymmetry, and worked examples. This file only documents the I/O contract.

**Invocation:**
```bash
echo '<mom-and-active-health>' | python scripts/aggregate_signals.py
```

**Reads stdin?** Yes. No CLI flags.

**Input contract (stdin, JSON — typically the `mom` + `active_health` slice of compute_group_stats output):**
```json
{
  "mom": {
    "volume_pct":     <float> | null,
    "asp_pct":        <float> | null,
    "dom_delta":      <float> | null,
    "efficiency_pct": <float> | null
  },
  "active_health": {
    "used": {"days_supply": <float> | null, ...} | null,    // other fields ignored
    "new":  {"days_supply": <float> | null, ...} | null,
    "footnote": "..."                                       // ignored
  }
}
```

Six metrics are scored: `volume_mom`, `asp_mom`, `dom_delta`, `days_supply_used`, `days_supply_new`, `efficiency_mom`. Any metric with a `null` input is skipped (does not contribute to the reduction).

**Output (stdout, JSON):**
```json
{
  "ok": true,
  "verdict": "BULLISH" | "BEARISH" | "NEUTRAL" | "MIXED" | null,
  "scores": {
    "volume_mom":       {"value": <float>, "band": "<band>", "score": <int>} | null,
    "asp_mom":          { ... } | null,
    "dom_delta":        { ... } | null,
    "days_supply_used": { ... } | null,
    "days_supply_new":  { ... } | null,
    "efficiency_mom":   { ... } | null
  },
  "mean_score":  <float> | null,
  "n_bullish":   <int>,
  "n_bearish":   <int>,
  "rationale":   "<string>"
}
```

Where `<band>` is `"BULLISH" | "NEUTRAL" | "CAUTION" | "BEARISH"` and the per-band scores are:

| Band | Score |
|---|---|
| BULLISH | +2 |
| NEUTRAL | 0 |
| CAUTION | -1 |
| BEARISH | -2 |

**No-scoreable-signals case** (every metric null):
```json
{
  "ok": true,
  "verdict": null,
  "scores": {...all null...},
  "mean_score": null,
  "n_bullish": 0,
  "n_bearish": 0,
  "rationale": "No scoreable signals — all metric values are null.",
  "reason": "no_scoreable_signals"
}
```

**Reduction algorithm (first-match-wins, fully documented in `references/signal-aggregation.md`):**
1. Skip metrics with null values.
2. Compute `mean(scores)` across contributing metrics.
3. `n_bullish > 0 AND n_bearish > 0` → MIXED
4. `mean ≥ +1.0 AND n_bearish == 0` → BULLISH
5. `mean ≤ -1.0 AND n_bullish == 0` → BEARISH
6. else → NEUTRAL

**Banding tables and worked examples:** `references/signal-aggregation.md`. This file does NOT duplicate them.

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `bad_stdin` | Stdin was not valid JSON | Fix caller. |

**Edge cases:**
- A null metric contributes neither to `mean_score` nor to `n_bullish`/`n_bearish` counters.
- `days_supply_used` / `days_supply_new` are read from `active_health.{used,new}.days_supply` when that channel block is non-null; otherwise the score is null.
- Boundary semantics are documented in detail in `references/signal-aggregation.md` ("Boundary rule (resolves AMB-04)" section).
- `rationale` is always non-empty when `verdict` is non-null.

**Used by:** `references/w1-single-group.md` (Wave A post-processing).
**Test verification:** `tests/test_aggregate_signals.py` (15 tests).

---

## Drift safeguard

When modifying any `scripts/*.py`, update this file in the same commit. The matching `tests/test_<script>.py` is the runtime verification — if a contract here disagrees with a test assertion, the test wins. Always cross-check the test before editing this file.

This is normative discipline, not enforcement. A future pre-commit hook could enforce co-modification, but is out of the current plan's scope.
