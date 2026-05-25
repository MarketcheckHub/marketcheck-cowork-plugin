---
name: script-contracts
description: Authoritative I/O contract (CLI flags, stdin shape, stdout shape, error envelopes, edge cases) for every Python script in scripts/. The script source is implementation detail; this file is the contract surface.
type: reference
---

# Script contracts

Authoritative I/O contract for every script in `scripts/`. The script source
is implementation detail and never needs to enter your context — SKILL.md
§Script invocation discipline forbids the `Read` tool on `scripts/*.py`.
Treat this file as the contract surface.

If a future test in `tests/` disagrees with what is documented here, the
test wins — file a doc bug and update this file. Never read source to
"verify" — that is the failure mode this file exists to prevent.

## Quick reference

| Script | Purpose | CLI flags | Used by |
|---|---|---|---|
| `_common.py` | Shared helpers (`read_input`, `emit`, `classify_error`, `arg_value`, `arg_flag`) | (not directly invoked) | every parser |
| `compute_period_windows.py` | Emit month-aligned date windows for the workflow's period set | `--today YYYY-MM-DD`, `--periods <csv-tokens>` | W1 / W2 / W3 / W5 pre-flight |
| `parse_sold_summary.py` | Normalise `get_sold_summary` responses (with optional aggregation modes) | `--file <path>`, `--aggregate-multi-period`, `--aggregate-state <STATE>` | every workflow |
| `depreciation_curve.py` | W1 curve stats engine — retention %, monthly rate, annualized rate, acceleration verdict, curve shape | (stdin only) | W1 |
| `brand_retention.py` | W3 brand-retention engine — retention %, T1-T4 tier, tier-jump detection | (stdin only) | W3 |
| `segment_compare.py` | W2 segment-trend engine — price/volume change %, segment classification | (stdin only) | W2 |
| `msrp_parity.py` | W5 MSRP-parity engine — status (above/at/below) + cross-period direction | (stdin only) | W5 |
| `aggregate_signals.py` | Map per-metric values to BULLISH / NEUTRAL / CAUTION / BEARISH bands + reduce to headline verdict | (stdin only) | every workflow's Ticker Impact Summary |
| `render_depreciation_table.py` | Markdown table renderer (4 modes) | `--mode {curve\|segment\|brand\|parity}`, `--input <path>`, `--currency`, `--max-rows` | every workflow |

## Conventions (all parsers)

- **Stdin-default.** Every parser reads its payload from stdin by default. Use the `--file <path>` flag ONLY when the MCP runtime saved an oversized response to disk and returned an `Output saved to <path>` error string — never create those files yourself. See SKILL.md §Script invocation discipline.
- **Truncation envelope.** When loaded via `--file`, the parser unwraps the `{"result": "<stringified JSON>"}` envelope automatically (via `_common._maybe_unwrap`). `get_sold_summary` is the only MCP tool whose payload is NOT envelope-wrapped — its raw `{success, service, data}` passes through transparently.
- **Canonical response shape.** Every parser emits a single JSON document with `ok: true|false` at top level. On `ok: false`, an `error_type` enum classifies the failure; the caller branches on it.
- **Process exit codes.** Validation errors (bad CLI args, missing required input) exit `1` with stderr message and no JSON. Payload-level errors (network failures, schema misses, classifier hits) exit `0` with `{"ok": false, "error_type": "...", ...}` on stdout — the caller is expected to parse and branch.
- **Field naming.** Server-side quirks (`avg_msrp`, `sale_price_std_dev`) are normalised at parse time. The contract here is the **post-normalisation** name (`average_msrp`, etc.).

## Overlap rule — where each kind of doc lives

| Topic | Canonical location |
|---|---|
| Script I/O shapes (stdin/stdout, CLI flags, error envelopes) | **This file** |
| Per-metric banding tables + verdict reduction algorithm | `references/signal-aggregation.md` |
| Tier / verdict threshold table (W1 acceleration, W3 retention tiers, W2 segment classifier, W5 parity status + direction) | `references/tier-and-verdict-bands.md` |
| MCP tool parameter discipline (`get_sold_summary` always-set/never-set params, rate-limit ceiling, 12-month date cap) | `references/sold-summary-safety.md` |
| `make_model_not_found` recovery flow | `references/facet-discovery.md` |
| OEM ticker ↔ make mapping table | `references/ticker-mapping.md` |
| Per-workflow wave structures (which calls fire in which order) | `references/w1-curve.md`, `w2-segment-trends.md`, `w3-brand-residual.md`, `w5-msrp-parity.md` |
| Output rendering rules (block stack, headline phrasing, money format, self-check checklist) | `assets/output-template.md` |

This file points outward to those references where appropriate, never inward.

---

## `_common.py`

**Purpose:** Shared library used by every parser. Not invoked directly. Documents the canonical envelope / error machinery so per-script error tables stay short.

**Public helpers:**

| Helper | Purpose |
|---|---|
| `read_input(argv)` | Read JSON from stdin or `--file <path>`; unwrap `{"result": "<stringified>"}` envelope transparently. Returns `(payload, source)` where `source` is `"stdin"` or `"file:<path>"`. |
| `emit(obj)` | Serialise an object to stdout as JSON (indent=2). Used for every successful and error response. |
| `classify_error(payload)` | Inspect a payload for transport-level failure signatures. Returns `(error_type, error_message)` or `("", "")` on success. |
| `arg_value(argv, flag)` | Parse `--flag value` from argv. Returns the value string or `None`. |
| `arg_value_multi(argv, flag)` | Collect all occurrences: `--flag v1 --flag v2`, or `--flag 'v1,v2'`. Returns a list. |
| `arg_flag(argv, flag)` | Parse boolean `--flag` from argv. Returns `True` if present. |

**Generic `error_type` catalogue** (extended by individual parsers):

| `error_type` | Meaning | Recovery |
|---|---|---|
| `empty_response` | Empty stdin or zero-byte file | Skip + DQ event (a). |
| `non_json` | Payload was a non-JSON string | Could be a tool-validation error string — branch via parser-specific classifier. |
| `truncation_unrecovered` | Payload contains the MCP "exceeds maximum allowed tokens" sentinel | Re-fire upstream call via `--file <path>` to the runtime-written file; log DQ event (b). |
| `io_error` | `--file <path>` could not be read | Skip + DQ event (a) with the OS error message. |
| `truncation_unwrap_failed` | Envelope `{"result": "..."}` was present but inner payload was not parseable | Re-fire with narrower filters / smaller `top_n`. |
| `network_422` | HTTP 422 — upstream rejected the request body | Most common root cause: non-month-aligned dates. Verify `compute_period_windows.py` was used. If aligned, skip + DQ event. |
| `network_5xx` | HTTP 500 / 502 / 503 / 504 | Skip + DQ event. Do not retry — a workflow-level retry amplifies rate-limit pressure. |
| `network` | Generic network error | Skip + DQ event (a). |
| `upstream` | `{success: false}` envelope from the service | Skip + DQ event (a) with serialised body. |

Per-script extensions are documented in each script's section below.

---

## `compute_period_windows.py`

**Purpose:** Emit calendar-month-aligned date windows for the workflow's period set. The `current` token resolves to the most-recent full calendar month (the in-progress month always lags in `get_sold_summary` aggregates).

**Invocation:**
```bash
python scripts/compute_period_windows.py --today 2026-05-25
python scripts/compute_period_windows.py --today 2026-05-25 --periods current,60d,90d,6mo,1yr
```

**Reads stdin?** No.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--today` | string `YYYY-MM-DD` | no | system date | Reference date used to compute windows. |
| `--periods` | csv of tokens | no | `current,60d,90d,6mo,1yr` | Period set. Allowed tokens: `current`, `60d`, `90d`, `6mo`, `1yr`. |

**Output (stdout, JSON):**
```json
{
  "today": "2026-05-25",
  "periods": [
    {"label": "1yr",     "months_offset_from_today": 12, "date_from": "2025-05-01", "date_to": "2025-05-31", "month": "2025-05"},
    {"label": "6mo",     "months_offset_from_today":  6, "date_from": "2025-11-01", "date_to": "2025-11-30", "month": "2025-11"},
    {"label": "90d",     "months_offset_from_today":  3, "date_from": "2026-02-01", "date_to": "2026-02-28", "month": "2026-02"},
    {"label": "60d",     "months_offset_from_today":  2, "date_from": "2026-03-01", "date_to": "2026-03-31", "month": "2026-03"},
    {"label": "current", "months_offset_from_today":  1, "date_from": "2026-04-01", "date_to": "2026-04-30", "month": "2026-04"}
  ]
}
```

Periods are returned sorted oldest-first (largest `months_offset_from_today` first).

**Error envelopes:** None at the payload level. Malformed `--today` or unknown period token exits `1` with stderr message and no JSON on stdout.

**Edge cases:**
- `current` always resolves to the prior full calendar month (offset = 1), never the in-progress month.
- Year wrap is handled by the script's internal `_months_back` helper.

---

## `parse_sold_summary.py`

**Purpose:** Normalise a `get_sold_summary` response. Classifies errors so the caller can branch by `error_type`. On success, normalises rows to a canonical shape.

**Invocation:**
```bash
echo '<response>' | python scripts/parse_sold_summary.py
echo '<response>' | python scripts/parse_sold_summary.py --aggregate-multi-period
echo '<response>' | python scripts/parse_sold_summary.py --aggregate-state CA
python scripts/parse_sold_summary.py --file /path/to/saved.json
```

**Reads stdin?** Yes (default). Falls back to `--file <path>` for truncation recovery.

**CLI flags:**

| Flag | Type | Purpose |
|---|---|---|
| `--file <path>` | string | Read the response from a file (truncation-recovery path). |
| `--aggregate-multi-period` | bool | Group rows by `month` and emit `multi_period_aggregate.{months, overall}` with weighted means. Required by W1. |
| `--aggregate-state <STATE>` | string | Compute a weighted-mean `state_baseline` across rows matching `state`. Currently unused by this skill (no W4); preserved for future. |

The two aggregation flags are independent and may be combined.

**Output on success (stdout JSON):**
```json
{
  "ok": true,
  "row_count": <int>,
  "rows": [
    {
      "month": "2026-04",
      "inventory_type": "Used",
      "state": "CA",
      "city": null,
      "dealership_group_name": null,
      "make": "Toyota",
      "model": "RAV4",
      "body_type": null,
      "rank": 1,
      "sold_count": 1820,
      "average_sale_price": 27450.12,
      "total_sale_price": 49959218.40,
      "average_msrp": 30210.87,
      "price_over_msrp_percentage": -9.13,
      "average_days_on_market": 31.4,
      "median_days_on_market": 28.5,
      "sale_price_range": "...",
      "sale_price_std_dev": 4521.0
    }, ...
  ],
  "source": "stdin" | "file:<path>",
  "multi_period_aggregate": {                  // present only with --aggregate-multi-period
    "months": [
      {"month": "2026-04", "total_sold_count": 1820,
       "weighted_avg_sale_price": 27450.12,
       "weighted_avg_days_on_market": 31.4,
       "weighted_avg_msrp": 30210.87,
       "row_count": 1}, ...
    ],
    "overall": { ...same shape, "month": null... },
    "row_count_total": <int>
  },
  "state_baseline": { ... } | null,            // present only with --aggregate-state
  "state_baseline_skipped_reason": "..."       // present when state_baseline is null
}
```

**Output on error (stdout JSON):**
```json
{"ok": false, "error_type": "<see table>", "error": "<message>", "source": "..."}
```

**Sold-specific `error_type` extensions** (atop the `_common` catalogue):

| `error_type` | Meaning |
|---|---|
| `make_model_not_found` | Upstream returned no rows for the supplied make/model. Recover via `references/facet-discovery.md`. |
| `validation_dimension_limit` | `ranking_dimensions` exceeded server-side max. Retry with `ranking_dimensions="make"`. |
| `validation` | Plain-string `Error: ...` from the tool's local validator. |
| `unexpected_shape` | Payload's top-level shape did not match `{success, service, data}`. |
| `unknown` | Parser hit a shape it could not classify. |

**Edge cases:**
- `get_sold_summary` returns plain string `"Error: ..."` on local-validation failure (not JSON). The parser detects this and emits `error_type="validation"` (or a more specific subtype where the message text classifies).
- Divide-by-zero guard in `_aggregate_state_baseline` and `_aggregate_multi_period`: when `total_sold_count == 0`, weighted means emit `null` rather than `NaN`. The caller renders an `—` cell.

---

## `depreciation_curve.py`

**Purpose:** W1 stats engine. Reads the per-period sold-summary aggregates and emits the assembled curve.

**Anchor mode.** This analyst port runs in `anchor_mode="prior_period"` ONLY (the MSRP-anchor path was dropped in v1.0.0). The model passes `"anchor_mode": "prior_period"` and `"msrp": null` on every invocation. `retention_pct_msrp` is null on every row; the renderer omits the column.

**Invocation:**
```bash
echo '<config>' | python scripts/depreciation_curve.py
```

**Reads stdin?** Yes.

**CLI flags:** None.

**Input (stdin JSON):**
```json
{
  "periods": [
    {
      "label":                    "1yr" | "6mo" | "90d" | "60d" | "current",
      "months_offset_from_today": <int>,
      "month":                    "YYYY-MM",
      "weighted_avg_sale_price":  <float|null>,
      "total_sold_count":         <int>
    }, ...   (any order; engine sorts oldest-first internally)
  ],
  "msrp":        null,
  "anchor_mode": "prior_period"
}
```

**Output (stdout JSON, on success):**
```json
{
  "ok": true,
  "anchor_used": "prior_period",
  "anchor_value": null,
  "periods": [   (oldest-first)
    {
      "label":                <str>,
      "month":                <YYYY-MM | null>,
      "months_offset_from_today": <int>,
      "avg_price":            <float|null>,
      "sold_count":           <int>,
      "retention_pct_msrp":   null,
      "retention_pct_prior":  <float|null>,
      "monthly_rate_pct":     <float|null>,
      "annualized_rate_pct":  <float|null>
    }, ...
  ],
  "verdict":          "Strong Retention" | "Stable" | "Slight Decline" | "Moderate Depreciation" | "Accelerated Loss" | null,
  "curve_shape":      "accelerating" | "linear" | "stabilizing" | null,
  "recent_monthly_rate_pct":  <float|null>,
  "longest_monthly_rate_pct": <float|null>
}
```

**Note on verdict labels.** `depreciation_curve.py` emits the **5-band** label
preserved from the dealer-side script (`Strong Retention` / `Stable` /
`Slight Decline` / `Moderate Depreciation` / `Accelerated Loss`). The analyst-side
`aggregate_signals.py` translates these into the BULLISH / NEUTRAL / CAUTION /
BEARISH investment-signal bands per `references/signal-aggregation.md`. The
script's raw label is rendered in the curve table's "Verdict" cell as
documented context; the analyst-tier verdict is rendered in the Headline and
Ticker Impact Summary.

**Verdict bands** (per `references/tier-and-verdict-bands.md`):
- `Strong Retention`      monthly_rate < 0.3% (or appreciation, monthly_rate < 0)
- `Stable`                0.3% ≤ monthly_rate < 0.6%
- `Slight Decline`        0.6% ≤ monthly_rate < 1.0%
- `Moderate Depreciation` 1.0% ≤ monthly_rate < 1.5%
- `Accelerated Loss`      monthly_rate ≥ 1.5%

**Curve-shape classifier** (per `references/tier-and-verdict-bands.md`):
- `accelerating`  → recent_rate / longest_rate > 1.25
- `stabilizing`   → recent_rate / longest_rate < 0.75
- `linear`        → in between

**Failure modes:**
| `error_type` | Meaning | Recovery |
|---|---|---|
| `bad_stdin` | Stdin was not valid JSON | Re-issue with the corrected config. |
| `insufficient_periods` | Fewer than 2 priced periods after recovery | Render the Headline as the canonical insufficient-data prose; do not render the curve table. |

---

## `brand_retention.py`

**Purpose:** W3 stats engine. Reads current-period + prior-period sold-summary outputs (both keyed on `make`) plus optional volume context, and emits per-brand retention % + tier classification + tier-jump detection.

**Invocation:**
```bash
echo '<config>' | python scripts/brand_retention.py
```

**Input (stdin JSON):**
```json
{
  "current": {"rows": [ {"make": "...", "average_sale_price": <float>, "sold_count": <int>}, ... ]},
  "prior":   {"rows": [ ...same shape, 6 months back... ]},
  "volumes": {"rows": [ {"make": "...", "sold_count": <int>}, ... ]}   (optional)
}
```

**Output (stdout JSON):**
```json
{
  "ok": true,
  "tier_thresholds": {"T1": 98, "T2": 95, "T3": 90},
  "ranking": [
    {
      "rank":          <int>,
      "make":          "...",
      "current_avg":   <float|null>,
      "prior_avg":     <float|null>,
      "retention_pct": <float|null>,
      "volume":        <int>,
      "tier":          "T1" | "T2" | "T3" | "T4" | null
    }, ...   (sorted by retention_pct desc; null retention sorted last)
  ],
  "tier_counts": {"T1": <int>, "T2": <int>, "T3": <int>, "T4": <int>}
}
```

**Tier thresholds** (per `references/tier-and-verdict-bands.md`):
- T1: retention_pct ≥ 98
- T2: 95 ≤ retention_pct < 98
- T3: 90 ≤ retention_pct < 95
- T4: retention_pct < 90

Tier-jump detection lives in the renderer + the SKILL prose; the script
simply assigns a tier per current-period retention. The Headline cites the
largest absolute retention change between paired periods.

**Failure modes:** `bad_stdin` only. Empty inputs return `ok=true` with
empty `ranking` and zero `tier_counts`.

---

## `segment_compare.py`

**Purpose:** W2 stats engine. Reads current-period + prior-period sold-summary outputs (both keyed on a single dimension — `body_type`, `fuel_type_category`, `make`, or `model`) and emits per-row cross-period diffs with classifications.

**Invocation:**
```bash
echo '<config>' | python scripts/segment_compare.py
```

**Input (stdin JSON):**
```json
{
  "current": {"rows": [ {"<dimension>": "...", "average_sale_price": <float>, "sold_count": <int>}, ... ]},
  "prior":   {"rows": [ ...same shape... ]},
  "dimension": "body_type" | "fuel_type_category" | "make" | "model"
}
```

Both `current` and `prior` are typically the FULL `parse_sold_summary` output JSON; this script reads `rows` and ignores everything else.

**Output (stdout JSON):**
```json
{
  "ok": true,
  "dimension": "<dimension>",
  "rows": [
    {
      "key":                  <dimension value>,
      "current_avg":          <float|null>,
      "prior_avg":            <float|null>,
      "current_sold_count":   <int>,
      "prior_sold_count":     <int>,
      "price_change_pct":     <float|null>,
      "volume_change_pct":    <float|null>,
      "classification":       "appreciating" | "stable" | "soft" | "accelerating_dep" | null
    }, ...   (sorted by current_avg desc; null sorted last)
  ],
  "missing_in_prior":   [<key>, ...],
  "missing_in_current": [<key>, ...]
}
```

**Classification thresholds** (per `references/tier-and-verdict-bands.md`):
- `appreciating`      price_change_pct ≥ +1.0%
- `stable`            -1.0% < price_change_pct < +1.0%
- `soft`              -3.0% < price_change_pct ≤ -1.0%
- `accelerating_dep`  price_change_pct ≤ -3.0%

**Failure modes:** `bad_stdin` only.

---

## `msrp_parity.py`

**Purpose:** W5 stats engine. Reads current + prior sold-summary outputs (both keyed on `make,model` and ranked by `price_over_msrp_percentage`) plus optional volume context, and emits per-(make, model) parity status + cross-period direction.

**Invocation:**
```bash
echo '<config>' | python scripts/msrp_parity.py
```

**Input (stdin JSON):**
```json
{
  "current": {"rows": [ {"make":"...","model":"...","price_over_msrp_percentage":<float>,"average_sale_price":<float>,"sold_count":<int>}, ... ]},
  "prior":   {"rows": [...]},
  "volumes": {"rows": [ {"make":"...","model":"...","sold_count":<int>}, ... ]}   (optional)
}
```

**Output (stdout JSON):**
```json
{
  "ok": true,
  "rows": [
    {
      "make_model":     "Honda Civic",
      "make":           "Honda",
      "model":          "Civic",
      "current_pct":    <float|null>,
      "prior_pct":      <float|null>,
      "change_pct":     <float|null>,
      "current_avg_price": <float|null>,
      "volume":         <int>,
      "status":         "above" | "at" | "below" | null,
      "direction":      "flipped_above" | "flipped_below" | "deepening" | "narrowing" | "stable" | null
    }, ...   (sorted by current_pct desc; null sorted last)
  ],
  "highlights": {
    "above_sticker_count": <int>,
    "below_sticker_count": <int>,
    "flipped_below":  [<make_model>, ...],
    "flipped_above":  [<make_model>, ...],
    "deepening_discounts": [<make_model>, ...]
  }
}
```

**Status bands** (per `references/tier-and-verdict-bands.md`):
- `above`  price_over_msrp_percentage > 0
- `at`     -1.0 ≤ price_over_msrp_percentage ≤ 0
- `below`  price_over_msrp_percentage < -1.0

**Direction labels** (cross-period):
- `flipped_below`  prior_pct ≥ 0 AND current_pct < 0
- `flipped_above`  prior_pct ≤ 0 AND current_pct > 0
- `deepening`      both same sign AND |current| > |prior|
- `narrowing`      both same sign AND |current| < |prior|
- `stable`         |change_pct| < 0.5%

**Failure modes:** `bad_stdin` only.

---

## `aggregate_signals.py`

**Purpose:** Reduce per-workflow numeric values to a single headline verdict on the analyst's BULLISH / BEARISH / NEUTRAL / CAUTION / MIXED scale. Acts as the *bridge layer* between the workflow stats engines and the Ticker Impact Summary in the output template.

**Invocation:**
```bash
echo '<config>' | python scripts/aggregate_signals.py
```

**Reads stdin?** Yes. Input shape varies by workflow:

```json
// W1 (single make/model, single ticker)
{"workflow": "w1",
 "metrics": {
   "monthly_rate_pct":         <float|null>,
   "annualized_rate_pct":      <float|null>,
   "retention_pct_prior":      <float|null>
 }}

// W3 (per-make rankings)
{"workflow": "w3",
 "makes": [
   {"make": "Toyota", "retention_pct": <float>, "tier": "T1" | "T2" | "T3" | "T4"}, ...
 ]}

// W2 (per-segment classifications)
{"workflow": "w2",
 "segments": [
   {"key": "SUV", "price_change_pct": <float>, "classification": "appreciating" | ...}, ...
 ],
 "dimension": "body_type" | "fuel_type_category"}

// W5 (per-(make,model) parity rows)
{"workflow": "w5",
 "rows": [
   {"make_model": "Honda Civic", "make": "Honda",
    "current_pct": <float>, "status": "above" | "at" | "below",
    "direction": "flipped_above" | "flipped_below" | "deepening" | "narrowing" | "stable" | null}, ...
 ]}
```

**Output (stdout JSON):**
```json
{
  "ok": true,
  "headline_verdict": "BULLISH" | "BEARISH" | "NEUTRAL" | "CAUTION" | "MIXED" | null,
  "per_metric": {                                // W1
    "monthly_rate_pct":     {"value": ..., "band": "...", "score": ...} | null,
    "annualized_rate_pct":  {"value": ..., "band": "...", "score": ...} | null,
    "retention_pct_prior":  {"value": ..., "band": "...", "score": ...} | null
  },
  "per_make": [                                  // W3
    {"make": "Toyota", "retention_pct": ..., "tier": "T1", "band": "BULLISH", "score": ...}, ...
  ],
  "per_segment": [                               // W2
    {"key": "SUV", "price_change_pct": ..., "classification": "...", "band": "BULLISH", "score": ...}, ...
  ],
  "per_row": [                                   // W5
    {"make_model": "Honda Civic", "current_pct": ..., "status": "...",
     "direction": "...", "band": "BULLISH", "score": ...}, ...
  ],
  "rationale": "...",
  "mean_score": <float|null>,
  "n_bullish": <int>,
  "n_bearish": <int>
}
```

The four shape variants are mutually exclusive — exactly one of `per_metric` / `per_make` / `per_segment` / `per_row` is present based on `workflow`.

**Banding rules** (per `references/signal-aggregation.md`):

- **`monthly_rate_pct`** (W1, lower-better, units = % per month):
  - BULLISH:  rate < 0.3 (or negative — appreciation)
  - NEUTRAL: 0.3 ≤ rate < 0.6
  - CAUTION: 0.6 ≤ rate < 1.5
  - BEARISH: rate ≥ 1.5

- **`retention_pct`** (W3, higher-better, units = %):
  - BULLISH (T1):  retention_pct ≥ 98
  - NEUTRAL (T2):  95 ≤ retention_pct < 98
  - CAUTION (T3):  90 ≤ retention_pct < 95
  - BEARISH (T4):  retention_pct < 90

- **`price_change_pct`** (W2, higher-better, units = %):
  - BULLISH:  price_change_pct ≥ +1.0
  - NEUTRAL: -1.0 < price_change_pct < +1.0
  - CAUTION: -3.0 < price_change_pct ≤ -1.0
  - BEARISH: price_change_pct ≤ -3.0

- **`parity_status`** (W5, status × direction composite):
  - BULLISH:  status == `above` (and direction != `flipped_below`)
  - NEUTRAL:  status == `at`
  - CAUTION:  status == `below` with direction `narrowing` or `stable`
  - BEARISH:  status == `below` with direction `deepening` or `flipped_below`

**Reduction rule** (resolves AMB-01 from the dealer-side analysis):
1. Skip metrics / rows with `null` values.
2. Compute `mean(scores)` across contributing entries.
3. Count `n_bullish` / `n_bearish`. CAUTION and NEUTRAL do not count.
4. First-match-wins:
   - `n_bullish > 0 AND n_bearish > 0` → **MIXED**
   - `mean ≥ +1.0 AND n_bearish == 0`  → **BULLISH**
   - `mean ≤ -1.0 AND n_bullish == 0`  → **BEARISH**
   - At least one CAUTION + no BULLISH and no BEARISH → **CAUTION**
   - Else → **NEUTRAL**
5. If no metrics contribute → `verdict: null` with `reason: "no_scoreable_signals"`.

**Per-band scores:** BULLISH = +2; NEUTRAL = 0; CAUTION = -1; BEARISH = -2. Asymmetry reflects that CAUTION is a *watch* signal, not a *sell* trigger.

**Failure modes:** `bad_stdin` (stdin not valid JSON), `bad_workflow` (`workflow` field missing or not in `{w1,w2,w3,w5}`).

---

## `render_depreciation_table.py`

**Purpose:** Markdown-table renderer for every workflow. Reads each script's pre-computed JSON output and emits the canonical markdown table verbatim. Closes the rendering-bypass surface.

**Invocation:**
```bash
python scripts/render_depreciation_table.py --mode curve   --input /path/to/curve.json   --currency '$'
python scripts/render_depreciation_table.py --mode segment --input /path/to/seg.json     --currency '$'
python scripts/render_depreciation_table.py --mode brand   --input /path/to/brand.json   --currency '$'
python scripts/render_depreciation_table.py --mode parity  --input /path/to/parity.json  --currency '$'
```

**CLI flags:**

| Flag | Type | Required | Purpose |
|---|---|---|---|
| `--mode <m>` | enum (`curve\|segment\|brand\|parity`) | yes | Selects renderer. |
| `--input <path>` | string | yes | JSON output from the matching stats engine. |
| `--currency` | string | no | `$` (default) or `£`. Depreciation-tracker is US-only → always `$`. |
| `--max-rows N` | int | no | Truncate `rows` / `periods` / `ranking` to the first N items before render. |

**Output:** Markdown table on stdout. Exit `1` on missing or malformed input.

**Column schemas by mode:**

| Mode | Columns |
|---|---|
| `curve` | Period · Avg Sale Price · Sold Count · Retention % (vs Prior) · Monthly Rate · Annualized Rate |
| `segment` | Body_Type (or Fuel_Type_Category etc., per `payload.dimension`) · Current Avg · Prior Avg · Price Δ% · Volume Δ% · Current Sold · Classification |
| `brand` | Rank · Make · Current Avg · Prior Avg · Retention % · Volume · Tier |
| `parity` | Make/Model · Current % vs MSRP · Prior % · Δ % · Avg Price · Volume · Status · Direction |

The `curve` mode omits the "Retention % (vs MSRP)" column when `payload.anchor_used == "prior_period"` (always the case in v1.0.0 of the analyst port).

The `geo` mode that exists in the dealer-side renderer is **inactive** in this analyst port (no W4); the script still recognises the mode for forward compatibility but is never invoked.

**Edge case:** when the input JSON has `ok=false`, the renderer emits the table from the surviving fields where possible and warns `*(no rows)*` for empty sections. The caller should also surface the `error_type` in the Headline / Data Quality section per the recovery table in `references/sold-summary-safety.md`.
