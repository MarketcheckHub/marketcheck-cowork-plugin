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
| `compute_quarter_windows.py` | Emit calendar-quarter-aligned current / prior / year-ago quarter windows + most-recent-complete-month | `--today YYYY-MM-DD` | W1 pre-flight |
| `resolve_ticker.py` | Resolve user input → ticker + canonical + entity_type + classification (OEM legacy/pure_play OR dealer-group Used-only/New-only/Both) | `--input "<text>"` (+ 2 optional file overrides) | W1 pre-flight |
| `parse_search.py` | Normalize `search_active_cars` responses (stats / facets modes) | `--mode {stats\|facets}`, `--file <path>` | invoked in-process by `orchestrate.py` (CLI preserved for ad-hoc + tests) |
| `parse_sold_summary.py` | Normalize `get_sold_summary` responses (6 aggregation modes; 2 new `_by_window` modes net-new for this skill) | `--aggregate-group <c>` ∣ `--aggregate-group-by-window <c>` ∣ `--aggregate-make <m>` ∣ `--aggregate-make-by-window <m>` ∣ `--aggregate-by-group` ∣ `--aggregate-by-dimension {body_type\|make}`, `--file <path>` | invoked in-process by `orchestrate.py` (CLI preserved) |
| `compute_earnings_signals.py` | Multi-quarter numerical-aggregation engine. Emits raw values only (no bands). Halts when current-quarter sold = 0. Exposes `compute(cfg: dict) -> dict` for in-process use. | (stdin only via `main`) | invoked in-process by `orchestrate.py` (CLI preserved) |
| `aggregate_signals.py` | Bands + composite slots + 4-tier verdict + signal drivers + per-make divergence. Exposes `aggregate(cfg: dict) -> dict` for in-process use. | (stdin only via `main`) | invoked in-process by `orchestrate.py` (CLI preserved) |
| `orchestrate.py` | End-to-end post-MCP pipeline driver: reads manifest, parses each scratch file, merges Call A+B months-maps, unwraps `make_by_window`/`group_by_window`, assembles compute input, runs compute + aggregate, emits the single envelope for template rendering | `--manifest <path>` | W1 (sole post-MCP entry point) |

## Conventions (all parsers)

- **Stdin-default.** Every parser reads its payload from stdin by default. Use the `--file <path>` flag ONLY when the MCP runtime saved an oversized response to disk and returned an `Output saved to <path>` error string — never create those files yourself. See `references/_failure-recovery.md §Write→file→--file pattern`.
- **Truncation envelope.** When loaded via `--file`, the parser unwraps the `{"result": "<stringified JSON>"}` envelope automatically (via `_common._maybe_unwrap`). `get_sold_summary` is the only MCP tool whose payload is NOT envelope-wrapped — its raw `{success, service, data}` passes through transparently.
- **Canonical response shape.** Every parser emits a single JSON document with `ok: true|false` at top level. On `ok: false`, an `error_type` enum classifies the failure; the caller branches on it.
- **Process exit codes.** Validation errors (mutex flag conflicts, bad CLI args) exit `1` with no JSON. Payload-level errors (network failures, schema misses) exit `0` with `{"ok": false, "error_type": "...", ...}` on stdout — the caller is expected to parse and branch. **`bad_stdin` also exits 0** (per SP6 stdin-parser convention) so callers can branch uniformly.
- **Field naming.** Server-side quirks (`avg_msrp`, `sale_price_std_dev`) are normalized at parse time. The contract here is the **post-normalization** name (`average_msrp`, etc.).
- **No banding in upstream scripts.** `compute_earnings_signals.py` emits raw numeric values only. Banding lives in `aggregate_signals.py` exclusively. This is the single-source-of-truth discipline that mirrors `oem-stock-tracker` and `dealer-group-health-monitor`.

## Overlap rule — where each kind of doc lives

| Topic | Canonical location |
|---|---|
| Script I/O shapes (stdin/stdout, CLI flags, error envelopes) | **This file** |
| Per-metric banding tables + composite combiner + verdict reduction algorithm | `references/signal-aggregation.md` |
| MCP tool parameter discipline (`get_sold_summary` always-set/never-set params, row-count budget for the extended mrcm-spanning window) | `references/sold-summary-safety.md` |
| 21-ticker map (13 OEM + 8 dealer-group), three-tier resolver discipline | `references/ticker-mapping.md` |
| OEM (pure_play / legacy) and dealer-group (Used-only / New-only / Both) classification | `references/inventory-type-classification.md` |
| Write→file→`--file` recovery pattern + `<session-id>` / `<call-name>` conventions + halt-vs-degrade rule | `references/_failure-recovery.md` |
| W1 wave structure (which calls fire in which order; Wave A1 + Wave A2 parallelism) | `references/w1-channel-check.md` |
| Output rendering rules (Bull/Bear/Headline, leading-indicators table, per-make rows, divergence section, signal drivers, C12 weakest=null fallback) | `assets/w1-output-template.md` |

This file points outward to those references where appropriate, never inward (no circular pointers).

## Generic `error_type` catalogue (extended by individual parsers)

| `error_type` | Meaning | Recovery |
|---|---|---|
| `network` | Generic network error reported upstream | Skip the call; log DQ event (a). |
| `network_422` | HTTP 422 — upstream rejected the request body | Most common root cause: non-month-aligned dates. Verify `compute_quarter_windows.py` was used. If aligned, skip + DQ event. |
| `network_5xx` | HTTP 500/502/503/504 — upstream server error | Skip + DQ event. |
| `unexpected_shape` | Payload top-level shape did not match expected `{success, service, data}` | Skip + DQ event with snippet. |
| `unknown` | Parser hit a shape it couldn't classify | Skip + DQ event with payload snippet. |
| `truncation_unrecovered` | Parser detected a truncation error string but no recovery path was available | Re-fire with narrower filters per `_failure-recovery.md`. |
| `bad_stdin` | Stdin was not valid JSON | Fix caller. Exits 0 (not 1) so callers can branch uniformly. |

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

## `compute_quarter_windows.py`

**Purpose:** Emit calendar-quarter-aligned `current_quarter`, `prior_quarter`, `year_ago_quarter`, and `most_recent_complete_month` windows for W1's multi-quarter analysis and Days Supply calculation.

**Strictly-before rule (at quarter level):** `current_quarter` is the latest calendar quarter that ended **strictly before today**. On 2026-05-13 → Q1 2026 (Jan-Mar — Q2 not yet ended). On 2026-04-01 → Q1 2026. On 2026-03-31 → Q4 2025 (Q1 not yet ended). On 2026-07-01 → Q2 2026.

**Most-recent-complete-month is independent.** `most_recent_complete_month` follows the monthly strictly-before rule (matches oem-tracker exactly). On 2026-05-13 → April 2026; on 2026-04-01 → March 2026. `current_quarter.date_to` and `most_recent_complete_month.date_to` can differ (mrcm may post-date the quarter end — by design, since Days Supply needs the freshest sold velocity to pair with today's live active inventory).

**Invocation:**
```bash
python scripts/compute_quarter_windows.py                    # uses system date
python scripts/compute_quarter_windows.py --today 2026-05-13 # fixed date
```

**Reads stdin?** No.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--today` | string `YYYY-MM-DD` | no | system date | Reference date |

**Output (stdout, JSON):**
```json
{
  "today": "2026-05-13",
  "current_quarter": {
    "date_from":       "2026-01-01",
    "date_to":         "2026-03-31",
    "label":           "Q1 2026",
    "days_in_quarter": 90,
    "months":          ["2026-01", "2026-02", "2026-03"]
  },
  "prior_quarter": {
    "date_from":       "2025-10-01",
    "date_to":         "2025-12-31",
    "label":           "Q4 2025",
    "days_in_quarter": 92,
    "months":          ["2025-10", "2025-11", "2025-12"]
  },
  "year_ago_quarter": {
    "date_from":       "2025-01-01",
    "date_to":         "2025-03-31",
    "label":           "Q1 2025",
    "days_in_quarter": 90,
    "months":          ["2025-01", "2025-02", "2025-03"]
  },
  "most_recent_complete_month": {
    "date_from":     "2026-04-01",
    "date_to":       "2026-04-30",
    "label":         "April 2026",
    "days_in_month": 30
  }
}
```

**Error envelopes:** None at the payload level. Malformed `--today` value exits `1` with stderr message and no JSON output.

**Edge cases:**
- Leap-year Q1 (`--today 2024-05-13`) → `current_quarter.days_in_quarter = 91`.
- Year-boundary (`--today 2026-01-15`) → `current_quarter = Q4 2025`; year_ago = Q4 2024; mrcm = December 2025.
- Quarter-start (`--today 2026-04-01`) → `current_quarter = Q1 2026`; mrcm = March 2026 (just barely complete).
- Quarter-end (`--today 2026-03-31`) → `current_quarter = Q4 2025` (Q1 not yet ended at any time on Mar 31); mrcm = February 2026.
- `months` array is always 3 entries (`YYYY-MM`) — used by the orchestrator to filter `parse_sold_summary --aggregate-*-by-window` monthly aggregates into the quarter buckets.

**Used by:** `SKILL.md §Before you start` step 2.
**Test verification:** `tests/test_compute_quarter_windows.py`.

---

## `resolve_ticker.py`

**Purpose:** Map a user-supplied input to canonical metadata for either an OEM ticker or a dealer-group ticker — 21 total (13 OEM + 8 dealer-group). Three-tier resolution: exact ticker → reverse make/canonical-name lookup → fuzzy via `difflib.SequenceMatcher` ≥0.5. Below threshold → `error_type=no_candidates` (HALT, no brand-orphan recovery — per Phase 5 §5a).

**Per Phase 5 §5a, this skill does NOT do brand-orphan recovery.** Unknown tickers halt the workflow.

**Invocation:**
```bash
python scripts/resolve_ticker.py --input "F"
python scripts/resolve_ticker.py --input "Ford"
python scripts/resolve_ticker.py --input "Ford Motor Company"
python scripts/resolve_ticker.py --input "AutoNation"        # fuzzy → AN
python scripts/resolve_ticker.py --input "carmax"            # fuzzy → KMX
python scripts/resolve_ticker.py --input "CVNA"              # exact → CVNA (Both, dealer_group)
python scripts/resolve_ticker.py --input "Subaru"            # → no_candidates
```

**Reads stdin?** No.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--input` | string | yes | — | User-supplied ticker / make / company. Empty / absent → `error_type=missing_input`. |
| `--ticker-file` | path | no | `references/ticker-mapping.md` | Override the ticker source. Resolver parses two H3 fenced code blocks: `### OEM map` (4-col `TICKER → Company → makes → classification`) and `### Dealer-group map` (2-col `TICKER → canonical`). |
| `--classification-file` | path | no | `references/inventory-type-classification.md` | Override the inventory classification source. Resolver parses three H2 sections (`## Used-only`, `## New-only`, `## Both`) plus two more (`## pure_play OEMs`, `## legacy OEMs`). |

**Output on success (OEM):**
```json
{
  "ok": true,
  "input":   "Ford",
  "resolution": "exact" | "reverse" | "fuzzy",
  "ticker":  "F",
  "company_name": "Ford Motor Company",
  "canonical":    null,
  "entity_type":  "oem",
  "makes": ["Ford", "Lincoln"],
  "classification": "legacy" | "pure_play",
  "candidates": []
}
```

**Output on success (dealer_group):**
```json
{
  "ok": true,
  "input": "AutoNation",
  "resolution": "reverse",
  "ticker": "AN",
  "company_name": null,
  "canonical":    "AutoNation Inc.",
  "entity_type":  "dealer_group",
  "makes":        [],
  "classification": "Used-only" | "New-only" | "Both",
  "candidates": []
}
```

**Output on failure:**
```json
{
  "ok": false,
  "error_type": "missing_input" | "no_candidates",
  "candidates": [...]
}
```

For `no_candidates`, `candidates` is the top-10 fuzzy candidates (all below the 0.5 threshold) — informational, not actionable.

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `missing_input` | `--input` absent or empty | Re-prompt the user |
| `no_candidates` | No fuzzy match ≥0.5 | **HALT** per Phase 5 §5a — no brand-orphan recovery in this skill |

**Edge cases:**
- Ticker input is auto-uppercased (`"f"` → `"F"`, `"cvna"` → `"CVNA"`).
- Reverse lookup is case-insensitive (`"ford"` → `"F"`, `"AUTONATION"` → `"AN"`).
- Resolution is `"exact"` for direct ticker hits; `"reverse"` for case-insensitive make/canonical-name hits; `"fuzzy"` for SequenceMatcher hits.
- Fuzzy threshold is 0.5 — known limitation: `"Polestar"` resolves to `"Stellantis"` at exactly 0.5 due to shared S-T-E-L. Documented as test boundary in `test_resolve_ticker.py`.
- `entity_type` is `"oem"` for the 13 OEM tickers; `"dealer_group"` for the 8 dealer-group tickers.
- Classification field meaning varies by `entity_type`: OEMs get `legacy` / `pure_play`; dealer-groups get `Used-only` / `New-only` / `Both`. **The classification string itself is sufficient to disambiguate entity_type when reading downstream.**
- CVNA classified as `Both` per source (empirically verified 2026-05-13: ~0.4% New share of total volume — small but non-zero, so source taxonomy wins).

**Used by:** `SKILL.md §Before you start` step 3.
**Test verification:** `tests/test_resolve_ticker.py`.

---

## `parse_search.py`

**Purpose:** Normalize `search_active_cars` MCP responses. Two operating modes:

- **stats mode** (default): the active-inventory call. Emits `{num_found, stats_present, stats}`. Used to derive `num_found` for the Days Supply formula (active inventory snapshot).
- **facets mode**: facet-discovery call. Emits `{num_found, facet_field, facets}`. **Not used by W1 in this skill** (no brand-orphan recovery), but kept for parity with oem-tracker.

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

**Output (stats mode, success):**
```json
{
  "ok": true,
  "num_found": 1234,
  "stats_present": true,
  "stats": {
    "price": {"mean": 28450, "median": 26900, "percentiles": {...}, ...},
    "dom":   {"mean": 38.2, "median": 35.0, "percentiles": {...}, ...}
  }
}
```

**Output (stats mode, defensive fallback when `data.stats` is absent):**
```json
{
  "ok": true,
  "num_found": 1234,
  "stats_present": false,
  "stats": null
}
```

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `network` / `network_5xx` / `network_422` | Upstream error | Skip the call + DQ event `(a)` — Days Supply degrades to null |
| `unexpected_shape` | No `data` key or `data` not a dict | Skip + DQ event |
| `usage` | Invalid `--mode` value | Fix invocation |

**Edge cases:**
- Wire quirk: `data.start` and `data.rows` may arrive as strings on syndication paths. Both coerced to int.
- Stats mode does NOT request facets — `data.facets` is ignored if present.

**Used by:** W1 active-inventory parsing for Days Supply (stats mode).
**Test verification:** Not directly tested in this skill (test_parse_search.py is reused byte-identical from oem-tracker and is already covered there).

---

## `parse_sold_summary.py`

**Purpose:** Normalize `get_sold_summary` MCP responses. Six mutually-exclusive aggregation modes — four preserved from prior skills, two new for this skill.

| Flag | What it produces |
|---|---|
| (no flag) | Raw row normalization (`rows: [...]`). |
| `--aggregate-group <canonical>` | Single-group (dealer-group) rollup (single or multi-month aggregated). Mirrors `--aggregate-make` for dealer-group canonical names. |
| `--aggregate-group-by-window <canonical>` | **NEW.** Single-group rollup grouped by month. Emits `group_by_window.months: {"YYYY-MM": <agg>, ...}`. |
| `--aggregate-make <make>` | Single-make rollup (single or multi-month aggregated). |
| `--aggregate-make-by-window <make>` | **NEW.** Single-make rollup grouped by month. Emits `make_by_window.months: {"YYYY-MM": <agg>, ...}` — mirrors oem-tracker's pattern. |
| `--aggregate-by-group` | All-groups passthrough (preserved; W1 does not currently invoke). |
| `--aggregate-by-dimension {body_type\|make}` | Per-dimension aggregates (preserved; W1 does not currently invoke). `--by-window` additionally groups each bucket by month. |

**Invocation:**
```bash
echo '<mcp>' | python scripts/parse_sold_summary.py
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-group "Carmax"
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-group-by-window "Carmax" --file <path>
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-make "Ford" --file <path>
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-make-by-window "Ford" --file <path>
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-by-group
echo '<mcp>' | python scripts/parse_sold_summary.py --aggregate-by-dimension body_type
```

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--aggregate-group` | string | no | — | Single-group rollup. Mutex with other aggregation flags. |
| `--aggregate-group-by-window` | string | no | — | **NEW.** Per-month group rollup. Mutex. |
| `--aggregate-make` | string | no | — | Single-make rollup. Mutex. |
| `--aggregate-make-by-window` | string | no | — | **NEW.** Per-month make rollup. Mutex. |
| `--aggregate-by-group` | bool | no | false | All-groups passthrough. Mutex. |
| `--aggregate-by-dimension` | enum: `body_type`, `make` | no | — | Per-dimension aggregates. Mutex. |
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
      "dealership_group_name": "AutoNation Inc." | null,
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

**Output with `--aggregate-make-by-window <make>`:**
```json
{
  "ok": true,
  "row_count": N,
  "rows": [...],
  "make_by_window": {
    "make": "Ford",
    "months": {
      "2026-03": {<aggregate>},
      "2026-02": {<aggregate>},
      "2026-01": {<aggregate>}
    },
    "row_count": N
  }
}
```

Each month aggregate has shape: `{total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, weighted_median_days_on_market, weighted_price_over_msrp_percentage, weighted_avg_msrp, row_count, months_included}`. Zero-sold months are dropped. If no months match → `make_by_window_skipped_reason: "no_matching_rows"`.

**Output with `--aggregate-group-by-window <canonical>`:**
```json
{
  "ok": true,
  "row_count": N,
  "rows": [...],
  "group_by_window": {
    "group": "AutoNation Inc.",
    "months": {
      "2026-03": {<aggregate>},
      "2026-02": {<aggregate>},
      "2026-01": {<aggregate>}
    },
    "row_count": N
  }
}
```

Identical shape to `--aggregate-make-by-window` but the bucketing key is `dealership_group_name` instead of `make`. **The canonical name must exactly match the `canonical` field from `resolve_ticker` output** (e.g., `"AutoNation Inc."`, not `"AutoNation"`).

**Output with `--aggregate-group <canonical>`:**
```json
{
  "ok": true,
  "row_count": N,
  "rows": [...],
  "group_baseline": {
    "group": "AutoNation Inc.",
    "total_sold_count": ...,
    "weighted_avg_sale_price": ...,
    ...
  }
}
```

Identical aggregate shape to `make_baseline` but keyed off `dealership_group_name`.

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

Sorted desc by `total_sold_count`. Buckets with `total_sold == 0` dropped.

**Error envelopes (extends `_common`):**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `make_model_not_found` | Make string not in indexed values | Skip the affected call + DQ event |
| `validation_dimension_limit` | `ranking_dimensions` rejected by local validator | Retry once with `ranking_dimensions=make` only |
| `validation` | Local validator rejected some parameter | Skip + DQ event |
| `network_422` | Upstream HTTP 422 — usually non-month-aligned dates or row-budget-exceeded | Verify `compute_quarter_windows.py` windows + `sold-summary-safety.md` row-count budget; skip + DQ |
| `network_5xx` | HTTP 5xx | Skip + DQ |
| `invalid_dimension` | `--aggregate-by-dimension` got something other than `body_type` or `make` | Fix invocation; exit 0 with `ok: false` |
| `truncation_unrecovered` | Truncation error string detected with no recovery path | Re-fire with narrower filters per `_failure-recovery.md` |
| `unknown` | Parser hit unexpected shape | Skip + DQ event |
| `bad_stdin` | Stdin wasn't valid JSON | Fix caller |

**Never halt the whole workflow on a single `get_sold_summary` failure.** Graceful degradation per `_failure-recovery.md §Halt-vs-degrade rule`: missing prior-quarter sold → QoQ null; missing year-ago sold → YoY null + `volume_momentum.degraded_to: "qoq_only"`; missing mrcm sold → Days Supply null. **HALT** only when current-quarter sold returns zero across all channels (handled downstream in `compute_earnings_signals.py`).

**Edge cases:**
- Response can wrap rows under `data.results[]` (public doc shape) OR `data.data[]` (live shape) OR `data.rows[]`. Parser handles all three.
- `get_sold_summary` is the only MCP tool whose payload is **NOT** envelope-wrapped — raw `{success, service, data}` is the live shape; parser treats a dict payload without `data` as zero-rows (not unexpected_shape).
- Null-priced rows (territories like MP) drop from BOTH numerator AND denominator of weighted-ASP mean. Same for null-DOM, null-MSRP-positioning. They still contribute to `total_sold_count`.
- `--by-window` without `--aggregate-by-dimension` → exit 1.
- Passing multiple aggregation flags → exit 1.

**Used by:** W1 sold-summary parsing — all four `*_by_window` calls use the new modes; the active-inventory pairing for Days Supply uses no-flag mode to extract mrcm-month rows.
**Test verification:** `tests/test_parse_sold_summary.py`.

---

## `compute_earnings_signals.py`

**Purpose:** Multi-quarter numerical-aggregation engine. Consumes assembled JSON built by the orchestrator from Wave A1 + Wave A2 parser outputs; emits raw numeric values for the 8 leading indicators (no bands — banding lives in `aggregate_signals.py`).

**Invocation:**
```bash
echo '<assembled-input>' | python scripts/compute_earnings_signals.py
```

**Reads stdin?** Yes. No CLI flags.

**Input contract (stdin, JSON) — common fields:**
```json
{
  "ticker":         "F" | "AN" | ...,
  "company_name":   "Ford Motor Company" | null,        // OEM only
  "canonical":      "AutoNation Inc." | null,           // dealer_group only
  "entity_type":    "oem" | "dealer_group",
  "classification": "legacy" | "pure_play" |
                    "Used-only" | "New-only" | "Both",
  "makes":          ["Ford", "Lincoln"] | [],           // OEM only; [] for dealer_group
  "windows": <compute_quarter_windows output verbatim>,
  ...
}
```

**Input contract — OEM (`entity_type=oem`):**
```json
{
  ...,
  "per_make": {
    "<Make>": {
      "sold_new_by_window":  <parser-output.make_by_window> | null,   // UNWRAPPED inner block: {make, row_count, months}
      "sold_used_by_window": <same> | null,
      "ev_slice_by_window":  <same> | null,             // null for pure_play
      "active_new":          <parse_search stats output> | null,
      "active_used":         <same> | null
    }
  },
  "per_group": null
}
```

**Input contract — dealer-group (`entity_type=dealer_group`):**
```json
{
  ...,
  "per_make": null,
  "per_group": {
    "sold_new_by_window":  <parser-output.group_by_window> | null,    // UNWRAPPED inner block: {group, row_count, months}
    "sold_used_by_window": <same> | null,                // null for New-only (none currently mapped)
    "ev_slice_by_window":  <same> | null,
    "active_new":          <parse_search stats output> | null,
    "active_used":         <same> | null
  }
}
```

**Critical unwrap step.** `parse_sold_summary --aggregate-make-by-window` emits `{ok: true, row_count: N, rows: [...], make_by_window: {make, row_count, months: {...}}}`. **The orchestrator MUST extract the inner `make_by_window` value** and pass only that as `sold_new_by_window` — NOT the full parser envelope. Same for `--aggregate-group-by-window` (extract `group_by_window`). The script reads `by_window.get("months")` directly, so an un-unwrapped payload makes the script see no months at all and the workflow halts with `no_current_quarter_data`. This unwrap discipline matches the `oem-stock-tracker` orchestrator pattern.

Each `*_by_window` block carries `months: {"YYYY-MM": <agg>, ...}` where each aggregate has the fields documented under `parse_sold_summary` above. Critically, the months map MUST include the three months of `current_quarter`, the three of `prior_quarter`, the three of `year_ago_quarter`, AND `most_recent_complete_month` (the mrcm month is used for Days Supply only and may sit outside `current_quarter` — see `sold-summary-safety.md §Row-count budget`).

**Output (success):**
```json
{
  "ok": true,
  "ticker": "F",
  "company_name": "Ford Motor Company",
  "canonical": null,
  "entity_type": "oem",
  "classification": "legacy",
  "windows": {...},

  "headline": {
    "sold_count_total":            <int> | null,        // current_quarter, both channels combined
    "weighted_avg_sale_price":     <float> | null,
    "weighted_avg_days_on_market": <float> | null,
    "efficiency_score":            <float> | null
  },

  "leading_indicators_raw": {
    "volume":   {current, prior, year_ago, qoq_pct, yoy_pct},
    "asp":      {current, prior, year_ago, qoq_pct, yoy_pct},
    "msrp_gap": {current_pct, prior_pct, year_ago_pct, qoq_delta_bps, yoy_delta_bps},
    "dom":      {current, prior, year_ago, qoq_delta_days, yoy_delta_days},
    "days_supply_used": {num_found, sold_count_mrcm, days_in_month, current} | null,
    "days_supply_new":  {num_found, sold_count_mrcm, days_in_month, current} | null,
    "ev_share":         {ev_pct_current, ev_pct_prior, ev_pct_year_ago,
                         qoq_delta_bps, yoy_delta_bps,
                         ev_asp_current, ev_dom_current, ev_sold_current} | null,
    "mix":              {new_pct_current, new_pct_prior, new_pct_year_ago,
                         qoq_delta_pp, yoy_delta_pp} | null
  },

  "per_make_raw": [
    {make, sold_count_current, sold_count_prior, sold_count_year_ago,
     weighted_avg_sale_price_current, weighted_avg_days_on_market_current,
     qoq_vol_pct, yoy_vol_pct, qoq_asp_pct, qoq_dom_delta_days}
  ] | null,                                              // null for dealer_group OR single-make OEMs

  "active_inventory": {
    "used": {<parse_search stats output>} | null,
    "new":  {<parse_search stats output>} | null,
    "footnote": "Days Supply pairs live active inventory (today's snapshot) with the most-recent-complete-month sold velocity — a live-vs-historical mix."
  },

  "ev_block":  {<shape, transition, skipped_reason>},   // see _build_ev_block
  "mix_block": {<new_pct_current, ..., qoq_delta_pp, yoy_delta_pp>} | null,

  "dq_events": ["(a) ...", "(i) ...", "(k) ...", "(l) ...", "(m) ...", ...]
}
```

**Output (halt — current quarter has no sold data):**
```json
{
  "ok": false,
  "error_type": "no_current_quarter_data",
  "ticker": "F",
  "dq_events": [...]
}
```

This is the ONE genuine halt condition this script raises (per Phase 5 §5b). All other null inputs degrade gracefully.

**Days Supply formula (preserved across this codebase):**
```
days_supply = num_found × days_in_month / sold_count_mrcm
```
where:
- `num_found` is the LIVE active-inventory count (today's snapshot from `search_active_cars`)
- `days_in_month` and `sold_count_mrcm` come from `most_recent_complete_month` (NOT from `current_quarter`)
- Returns null when `sold_count_mrcm ≤ 0` (divide-by-zero guard) OR when either side is null
- The `active_inventory.footnote` makes the live-vs-historical pairing explicit on every render

**EV block — `_build_ev_block` shapes:**

| `shape` | When | `transition` | Other fields |
|---|---|---|---|
| `"transition"` | Non-pure_play AND current-quarter EV volume > 0 | populated dict | `skipped_reason: null` |
| `"skipped"` | Pure_play (volume IS EV) | null | `skipped_reason: "pure_play_volume_is_ev"` + DQ (k) |
| `"skipped"` | No EV volume in current quarter | null | `skipped_reason: "no_ev_volume"` + DQ (k) |

When `shape == "transition"`, `leading_indicators_raw.ev_share` is populated; otherwise it's null and `aggregate_signals.py` treats the `ev_share` slot as structurally null.

**Mix block — `_build_mix_block`:**

| Trigger | Output |
|---|---|
| `entity_type == "oem"` | Always returns null (Mix is dealer-group-only) |
| `classification == "Used-only"` (KMX) | Returns null (no New side to mix) |
| `classification == "New-only"` | Returns null (no Used side to mix) |
| Both channels populated | Returns `{new_pct_current, new_pct_prior, new_pct_year_ago, qoq_delta_pp, yoy_delta_pp}` |

**DQ event catalogue (extends prior skills):**

| Event | Trigger | Surfaces |
|---|---|---|
| `(a)` | Active-inventory call failed | Days Supply degraded for that channel |
| `(i)` | Low-volume slice (<100 sold) for any metric | Noisier-than-usual flag in narrative |
| `(k)` | EV slice skipped (pure_play OR no current-quarter EV) | `ev_share` slot null |
| `(l)` | Per-make divergence detected (gap ≥ 2 score-points) | Logged by `aggregate_signals.py` when `per_make_divergence` non-empty |
| `(m)` | Year-ago quarter has no usable data → `yoy_*` fields null | `volume_momentum.degraded_to: "qoq_only"` |
| `(n)` | Prior-quarter sold has no usable data → `qoq_*` fields null | `volume_momentum.degraded_to: "yoy_only"` (rare; defensive) |

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `bad_stdin` | Stdin was not valid JSON | Fix caller |
| `no_current_quarter_data` | `headline.sold_count_total` is null or 0 | **HALT** — single legitimate halt path per Phase 5 §5b |
| `missing_required_field` / `malformed_input` | Deep input validation failure | Fix caller |

All other failure modes degrade — individual fields land as `null`, never NaN, never fabricated.

**Edge cases (resolved as `null`):**
- `headline.efficiency_score` is null when DOM ≤ 0 or null.
- `leading_indicators_raw.<metric>.qoq_pct` / `yoy_pct` are null when prior or year-ago denominator is 0 or null.
- `leading_indicators_raw.dom.{qoq,yoy}_delta_days` null when either side is null.
- `leading_indicators_raw.days_supply_used` / `days_supply_new` null when `sold_count_mrcm ≤ 0` OR active fetch failed.
- `leading_indicators_raw.ev_share` null for pure_play OR zero-EV current quarter.
- `leading_indicators_raw.mix` null for OEMs OR for single-channel dealer-group classifications (Used-only, New-only).
- `per_make_raw` null when `entity_type == "dealer_group"` OR when `len(makes) < 2`.

**v1.2 output additions (display-only, not banded by `aggregate_signals.py`):**

| Field | Where | Purpose |
|---|---|---|
| `leading_indicators_raw.channel_split.{new,used}.{volume,asp,dom,msrp_gap}` | Top-level under `leading_indicators_raw` | Per-channel views of the four headline metrics (current/prior/year_ago + QoQ/YoY deltas — same shape as `_compute_*_block` output). `new` null for Used-only DG; `used` null for New-only DG; both populated for legacy / pure_play / Both. Used-channel MSRP-gap is informational (depreciation indicator). |
| `leading_indicators_raw.dom.{median_current, median_prior, median_year_ago, qoq_delta_median_days, yoy_delta_median_days}` | Inside the existing `dom` block alongside mean fields | Sold-count-weighted median DOM trajectory. More representative than mean (right-skewed distribution). |
| `active_inventory.{used,new}.{active_p50_price, active_p75_price, active_p90_price, active_median_price, active_p50_dom, active_p75_dom, active_p90_dom, active_median_dom, mrcm_sold_count}` | Inside each channel's active_inventory block | Active-listing price + DOM percentiles + median (P50/P75/P90), pooled by num_found-weighted mean for multi-make OEM. `mrcm_sold_count` is the sold count for the most-recent-complete-month that drove the Days Supply ratio. |
| `ev_block.transition.{ev_asp_prior, ev_asp_year_ago, ev_dom_prior, ev_dom_year_ago, ev_sold_prior, ev_sold_year_ago, qoq_asp_delta_pct, yoy_asp_delta_pct, qoq_dom_delta_days, yoy_dom_delta_days, qoq_sold_delta_pct, yoy_sold_delta_pct}` | Inside `ev_block.transition` alongside `ev_pct_*` and `ev_*_current` | Prior + year-ago trajectory for EV ASP, DOM, units — completes the trajectory the share-percent row already shows. |
| `per_make_raw[i].{share_pct, sold_count_prior, sold_count_year_ago, qoq_asp_pct, yoy_asp_pct, qoq_dom_delta_days, yoy_dom_delta_days, qoq_msrp_gap_delta_bps, yoy_msrp_gap_delta_bps}` | Inside each per-make row alongside existing fields | Per-make share-of-ticker + ASP/DOM/MSRP-gap trajectory. MSRP-gap deltas are New-channel-only. Rows are sorted by `sold_count_current` desc. |

None of these fields are read by `aggregate_signals.py` — they're rendered directly by the template. The verdict / band logic is unchanged.

**Used by:** invoked in-process by `orchestrate.py` via `compute(cfg: dict) -> dict`. CLI `main()` preserved for ad-hoc use + tests.
**Test verification:** `tests/test_compute_earnings_signals.py` (226 baseline + 9 v1.2 tests = 235).

---

## `aggregate_signals.py`

**Purpose:** Reduce raw numeric values from `compute_earnings_signals` into per-metric bands, 8 composite slots, a 4-tier headline verdict, signal drivers, and per-make divergence. Bands and reduction algorithm are domain rules — see `references/signal-aggregation.md` for the per-metric thresholds, composite combiner, and worked examples. This file documents the I/O contract only.

**Invocation:**
```bash
echo '<compute_earnings_signals slice>' | python scripts/aggregate_signals.py
```

**Reads stdin?** Yes. No CLI flags.

**Input contract:**
```json
{
  "ticker_classification": "legacy" | "pure_play" |
                           "Used-only" | "New-only" | "Both",
  "leading_indicators_raw": {
    "volume":           {current, prior, year_ago, qoq_pct, yoy_pct},
    "asp":              {current, prior, year_ago, qoq_pct, yoy_pct},
    "msrp_gap":         {current_pct, ..., qoq_delta_bps, yoy_delta_bps},
    "dom":              {current, prior, year_ago, qoq_delta_days, yoy_delta_days},
    "days_supply_used": {current, ...} | null,
    "days_supply_new":  {current, ...} | null,
    "ev_share":         {qoq_delta_bps, ...} | null,
    "mix":              {qoq_delta_pp, ...} | null
  },
  "per_make_raw": [{make, qoq_vol_pct, yoy_vol_pct, ...}, ...] | null
}
```

**Output:**
```json
{
  "ok": true,
  "ticker_classification": "...",
  "per_metric_bands": {
    "volume_qoq":      "BULLISH" | "NEUTRAL" | "CAUTION" | "BEARISH" | null,
    "volume_yoy":      "..." | null,
    "asp":             "..." | null,
    "msrp_gap":        "..." | null,
    "dom":             "..." | null,
    "days_supply_used":"..." | null,
    "days_supply_new": "..." | null,
    "ev_share":        "..." | null,
    "mix":             "..." | null
  },
  "composite_slots": {
    "volume_momentum": "BULLISH" | "NEUTRAL" | "CAUTION" | "BEARISH" | null,
    "asp":             "..." | null,
    "msrp_gap":        "..." | null,
    "dom":             "..." | null,
    "days_supply_used":"..." | null,
    "days_supply_new": "..." | null,
    "ev_share":        "..." | null,
    "mix":             "..." | null
  },
  "scores": {
    "<slot>": {"value": ..., "band": "<band>", "score": +2|-2|-1|0,
               "degraded_to": "qoq_only" | "yoy_only" | <absent>} | null
  },
  "verdict":     "BULLISH" | "BEARISH" | "NEUTRAL" | "MIXED" | null,
  "mean_score":  <float> | null,
  "n_bullish":   <int>,
  "n_bearish":   <int>,
  "rationale":   "<string>",
  "signal_drivers": {
    "strongest": {slot, band, score, value} | null,
    "weakest":   {slot, band, score, value} | null     // null when min-score slot is NEUTRAL/BULLISH (C12)
  },
  "per_make_divergence": [
    {make, make_volume_band, make_volume_score,
     make_qoq_pct, make_yoy_pct,
     ticker_composite_score, gap}
  ]
}
```

**Per-band score:** BULLISH +2, NEUTRAL 0, CAUTION −1, BEARISH −2 (asymmetric — see `signal-aggregation.md §Per-band scores`).

**No-scoreable-signals case** (every composite slot null):
```json
{
  "verdict": null,
  "rationale": "No scoreable signals — all composite slots are null.",
  "reason": "no_scoreable_signals"
}
```

**Reduction algorithm (first-match-wins, documented in `signal-aggregation.md`):**
1. Skip null composite slots.
2. `mean = mean(scores)` across contributing slots.
3. `n_bullish > 0 AND n_bearish > 0` → **MIXED**
4. `mean ≥ +1.0 AND n_bearish == 0` → **BULLISH**
5. `mean ≤ -1.0 AND n_bullish == 0` → **BEARISH**
6. else → **NEUTRAL**

**`volume_momentum` composite combiner** (from `signal-aggregation.md`): BULLISH iff both QoQ and YoY are BULLISH; BEARISH iff both BEARISH; CAUTION when QoQ sign disagrees with YoY sign; otherwise NEUTRAL. **Degradation:** when YoY is null (newly-listed ticker — DQ event (m)), the slot becomes QoQ-only with `degraded_to: "qoq_only"`; symmetric for QoQ-null → `"yoy_only"`.

**Per-make divergence rule:** For each `per_make_raw[i]`, band the make's `qoq_vol_pct` using the Volume QoQ banding table; compute `gap = |make_score − ticker_composite_score|` where `ticker_composite_score = scores.volume_momentum.score`. If `gap ≥ 2`, emit the entry. Empty array when no divergence OR when `per_make_raw` is null (dealer-group or single-make OEM).

**Signal drivers — `weakest=null` fallback (Phase 6 C12):** When the lowest-scoring slot is banded NEUTRAL or BULLISH (no real downside to surface), `signal_drivers.weakest` is null. The Bear Case section of `assets/w1-output-template.md` handles this by suppressing the "biggest drag" line entirely.

**Error envelopes:**

| `error_type` | Meaning | Recovery |
|---|---|---|
| `bad_stdin` | Stdin was not valid JSON | Fix caller |

**Edge cases:**
- A null underlying metric value → null per-metric band; that slot does not contribute to the reducer.
- `ev_share` always null for pure_play classification (no EV slice fires).
- `mix` always null for OEM classification.
- `days_supply_used` always null when entity has no Used channel (some New-only dealer groups — none currently mapped); `days_supply_new` always null for KMX (Used-only).
- `days_supply_*` banding is applied directly to `.current` (not on a Δ — Days Supply is an absolute-level signal).
- `per_make_divergence` empty when `volume_momentum.score` is null (cannot compute a gap).

**Used by:** invoked in-process by `orchestrate.py` via `aggregate(cfg: dict) -> dict`. CLI `main()` preserved for ad-hoc use and tests. Feeds the W1 output template's verdict, score table, and signal drivers/divergence sections.
**Test verification:** `tests/test_aggregate_signals.py`.

---

## `orchestrate.py`

**Purpose:** End-to-end post-MCP pipeline driver. Replaces five model-orchestrated steps (per-call parse → Call A+B months-map merge → unwrap `make_by_window`/`group_by_window` envelope → assemble compute input → slice for aggregate) with a single in-process pipeline. The model fires Wave A1/A2 MCP calls + writes each response to disk, builds one manifest JSON, and invokes this script once.

This skill uses a single-orchestrator post-MCP pattern; sibling analyst skills (`oem-stock-tracker`, `dealer-group-health-monitor`) currently use the model-orchestrated multi-script pattern. Refactoring those is out of scope.

**Invocation:**
```bash
python scripts/orchestrate.py --manifest /tmp/marketcheck/<sid>/manifest.json
```

**Reads stdin?** No. Reads the manifest file at the path passed via `--manifest`; the manifest references per-call scratch files on disk.

**CLI flags:**

| Flag | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `--manifest` | path | yes | — | JSON manifest listing pre-flight outputs + per-call scratch files |

**Side effects:** None. Read-only — writes nothing to disk. Emits JSON to stdout. Exit 0 always (SP6 convention).

**Manifest schema:**
```json
{
  "session_id": "ep-f-2026-05-14",
  "scratch_dir": "/tmp/marketcheck/ep-f-2026-05-14",
  "pre_flight": {
    "windows":    <compute_quarter_windows output verbatim>,
    "resolution": <resolve_ticker output verbatim — ticker, entity_type,
                   classification, makes/canonical, company_name>
  },
  "wave_a1": {
    "sold": [
      {"make_or_group": "Ford", "channel": "new",  "split": "A",
       "file": "/tmp/.../sold_ford_new_A.json", "mcp_error": null}, ...
    ],
    "ev":   [{"make_or_group": "Ford", "channel": "new", "split": "A",
              "file": "...", "mcp_error": null}, ...]
  },
  "wave_a2": {
    "active": [{"make_or_group": "Ford", "channel": "new",
                "file": "/tmp/.../active_ford_new.json", "mcp_error": null}, ...]
  }
}
```

`mcp_error` non-null → the orchestrator logs DQ event (a) for that call and drops it from the merge.

**Output (success):**
```jsonc
{
  "ok": true,
  // Pre-flight passthrough
  "ticker": "F", "company_name": "Ford Motor Company", "canonical": null,
  "entity_type": "oem", "classification": "legacy", "makes": ["Ford","Lincoln"],
  "windows": { /* verbatim */ },
  // Forwarded verbatim from compute_earnings_signals
  "headline": {...}, "leading_indicators_raw": {...},
  "per_make_raw": [...] | null,
  "active_inventory": {"used": ..., "new": ..., "footnote": "..."},
  "ev_block": {...}, "mix_block": {...} | null,
  // Forwarded flat from aggregate_signals (no nested envelope)
  "per_metric_bands": { /* 9 keys */ },
  "composite_slots":  { /* 8 keys */ },
  "scores":           { /* 8 slots */ },
  "verdict": "BULLISH"|"BEARISH"|"NEUTRAL"|"MIXED"|null,
  "mean_score": <float>|null, "n_bullish": <int>, "n_bearish": <int>,
  "rationale": "<string>", "reason": "no_scoreable_signals" /*null verdict only*/,
  "signal_drivers": {"strongest": {...}|null, "weakest": {...}|null},
  "per_make_divergence": [...],
  // Merged DQ log
  "dq_events": [
    // Ordered: orchestrator-emitted (a) per failed sold-call →
    //          compute-emitted (i)(k)(m)(n)(r)(f)(d)(a) per code-path →
    //          aggregate-emitted (l) when per-make divergence non-empty.
  ]
}
```

**Halt envelope** (`ok: false`):
```jsonc
{
  "ok": false,
  "error_type": "no_current_quarter_data" | "manifest_invalid" |
                "missing_manifest" | "scratch_file_unreadable" |
                "all_calls_failed" | "internal_error",
  "ticker": "F" /*when known*/,
  "windows": {...} /*when known*/,
  "dq_events": [...],
  "detail": "<string>" /*for manifest_invalid / internal_error*/
}
```

**Error envelopes:**

| `error_type` | Trigger | Recovery |
|---|---|---|
| `missing_manifest` | `--manifest` flag absent OR file unreadable | Fix caller (model must Write manifest before invoking) |
| `manifest_invalid` | JSON parse failure OR missing required key (`pre_flight`, `wave_a1`, `wave_a2`, `pre_flight.windows`, `pre_flight.resolution.{ticker,entity_type,classification}`) | Fix manifest construction; `detail` field names the missing key |
| `scratch_file_unreadable` | Manifest references a path that fails to open AND the call is critical (current-quarter sold) | Per-call read failures are logged as DQ (a) and dropped from merge; halt only if removal cascades to no current-quarter data |
| `all_calls_failed` | Every sold-call entry either has `mcp_error` set OR fails to parse | Investigate MCP service; halt cleanly with dq_events showing per-call failures |
| `no_current_quarter_data` | Forwarded from `compute_earnings_signals` — `headline.sold_count_total` is null or 0 | Halt; render the halt block from the output template |
| `internal_error` | Uncaught Python exception (KeyError, AttributeError, etc.) — orchestrator wraps `_run_pipeline` in top-level try/except | Investigate; `traceback` field carries truncated stack |

**Edge cases:**
- `mcp_error` entries in the manifest never raise — they emit a DQ (a) event and skip the merge for that call.
- A persisted-to-disk MCP response: use the runtime's `<path>` directly in the manifest entry's `file` field (don't re-Write).
- The orchestrator's per-file reading transparently unwraps the `{"result": "<stringified>"}` truncation envelope via `_common._maybe_unwrap`. `get_sold_summary` payloads (raw, not envelope-wrapped) pass through.
- DQ event (l) is formatted by `orchestrate._format_divergence_event` with the canonical string `"(l) Cross-make divergence: <N> make(s) flagged (<names>) — gap ≥ 2 score-points from ticker composite (see §4 Internal divergence)."`. Pre-refactor, the model composed this at template render time.

**Used by:** W1 — single post-MCP entry point. Drives the entire pipeline from parsed MCP responses → structured envelope ready for template interpolation.

**Test verification:** `tests/test_orchestrate.py` (14 tests covering all 5 ticker classifications, halt path, DQ event ordering, manifest validation, and helper-function unit tests).

---

## Drift safeguard

When modifying any `scripts/*.py`, update this file in the same commit. The matching `tests/test_<script>.py` is the runtime verification — if a contract here disagrees with a test assertion, the test wins.

**Orchestrator-specific drift safeguard:** `orchestrate.py` imports module-level helpers from peer scripts (`parse_sold_summary._aggregate_make_by_window`, `_aggregate_group_by_window`, `_normalize_row`, `_classify_sold_error`; `parse_search._normalize_stats_block`, `_to_int`; `compute_earnings_signals.compute` + `_combine_monthly_aggs`; `aggregate_signals.aggregate`; `_common._maybe_unwrap`, `classify_error`, `arg_value`). When renaming any of these in their host scripts, also update the `orchestrate.py` import lines.

This is normative discipline, not enforcement.
