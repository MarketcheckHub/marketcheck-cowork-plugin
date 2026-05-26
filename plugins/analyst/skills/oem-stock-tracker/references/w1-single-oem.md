---
name: w1-single-oem
description: Workflow 1 — Single OEM Investment Signal. Full spec for the W1 Wave A1 + A2 structure, parser pipeline, stats assembly, and rendering.
type: reference
---

# W1 — Single OEM Investment Signal

Triggered when an equity analyst asks "how is Ford doing?", "investment signal for GM", "Toyota demand trends", "is Stellantis losing share", "pre-earnings channel check on TSLA", or any single-OEM-ticker operational read.

## Required inputs

| Input | Source | Required? |
|---|---|---|
| OEM ticker or brand name | User prompt | Yes |
| Profile (country, optional tracked_tickers) | `marketcheck-profile.md` | Optional — if absent, skill prompts |

The skill never crashes for missing inputs — it asks.

## Pre-flight (no MCP calls — local only)

1. Read `marketcheck-profile.md`. Extract `location.country`. Halt if not US.
2. Run `scripts/compute_month_windows.py --today <currentDate> --baseline-months 3`. Capture `current_month`, `prior_month`, `baseline_3mo_window`.
3. Run `scripts/resolve_oem.py --input "<user input>"`.
   - If `result.ok == true` → capture `ticker`, `company_name`, `makes[]`, `classification` (`legacy` or `pure_play`); proceed.
   - If `result.error_type == "dealer_group_redirect"` → halt with: *"`<TICKER>` is a dealer-group stock; route to `dealer-group-health-monitor`."*
   - If `result.error_type == "no_candidates"` → fall through to the **brand-orphan recovery branch** documented in `SKILL.md §Before you start` step 3. If that branch lands on a brand `<X>`, set `classification="brand_orphan"`, `ticker=null`, `company_name=<X>`, `makes=[<X>]`. If it fails, halt cleanly.
4. Determine `inventory_type` from user input (default `"New"`, `"Used"` on explicit override).
5. Confirm with user: *"Analyzing **<ticker>** (<company_name>): <comma-separated makes> — <classification>. Pulling <inventory_type> signals for <current_month.label> vs. <prior_month.label> with 3-month baseline <baseline_3mo_window.label>…"*

## Wave A1 — sold-vehicle data + market context (single agent message, all in parallel)

| # | Tool | Purpose | Fires when | Persistence risk |
|---|---|---|---|---|
| W1.A1.sold[k] | `get_sold_summary` | Per-make sold, multi-month (current + prior + 3-mo baseline) | always, once per make in `makes[]` | ~130 KB per make — **often persists**. Use `--file <runtime-saved-path>` per `_failure-recovery.md` Mode 1. |
| W1.A1.market_current | `get_sold_summary` | Top-25 makes leaderboard, current month | always | ~400-500 KB — **persists**. Use `--file`. |
| W1.A1.market_baseline_3mo | `get_sold_summary` | Top-25 makes leaderboard, 3-month baseline window (covers prior_month + 2 months back); replaces the old market_prior call. Yields per-make per-month buckets so prior + baseline_3mo aggregate both derive from this one call | always | ~1.5 MB raw MCP response — **persists**. Use `--file`. Parser output is lean post-H1 (~5-7 KB). |
| W1.A1.ev[k] | `get_sold_summary` | Per-make EV slice, multi-month | classification ∈ {legacy, brand_orphan}; once per make | ~60-80 KB per make — sometimes persists. Use `--file` if so. |
| W1.A1.ev_leaders | `get_sold_summary` | Top-10 EV makes leaderboard, multi-month | classification == "pure_play"; once | ~110 KB — persists. Use `--file`. |

**Wave A1 size:** legacy/brand_orphan → `2N + 2` calls; pure_play → `N + 3` calls.

### W1.A1.sold[k] — per-make sold (multi-month)

For each `make` in `makes[]`:

```python
get_sold_summary(
    make="<Make>",                                      # e.g., "Ford"
    inventory_type="New"|"Used",                        # default New, user-overrideable
    ranking_dimensions="make",
    ranking_measure="sold_count",
    top_n=1,
    limit=5000,
    summary_by="state",
    date_from="<baseline_3mo_window.date_from>",        # first of (current - 3 months)
    date_to="<current_month.date_to>",                  # last of current month
)
```

→ Returns ~212 rows (4 months × ~53 states × top_n=1 per state per month).

Pipe through:
```bash
Write(file_path="/tmp/marketcheck/<session-id>/sold_<make_lower>.json", content=<full response string>)
python scripts/parse_sold_summary.py --aggregate-make-by-window "<Make>" \
  --file /tmp/marketcheck/<session-id>/sold_<make_lower>.json
```

(Or if MCP runtime persisted the response: `python scripts/parse_sold_summary.py --aggregate-make-by-window "<Make>" --file <runtime-saved-path>`.)

Captures `make_by_window.months: {"YYYY-MM": <aggregate>, ...}`. `compute_oem_stats.py` will assign each month bucket to the `current` / `prior` / `baseline_3mo` window. **Pattern reference: `references/_failure-recovery.md` — load it before Wave A1.**

### W1.A1.market_current — market share top-25, current month

```python
get_sold_summary(
    # NO make filter
    inventory_type="New"|"Used",
    ranking_dimensions="make",
    ranking_measure="sold_count",
    ranking_order="desc",
    top_n=25,
    limit=5000,
    summary_by="state",
    date_from="<current_month.date_from>",
    date_to="<current_month.date_to>",
)
```

→ Returns ~1,325 rows (1 month × ~53 states × top_n=25).

Pipe through:
```bash
Write(file_path="/tmp/marketcheck/<session-id>/market_current.json", content=<full response string>)
python scripts/parse_sold_summary.py --aggregate-by-dimension make \
  --file /tmp/marketcheck/<session-id>/market_current.json
```

Captures `dimension_values: [{value, total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, share_pct, ...}, ...]` sorted desc by sold_count.

### W1.A1.market_baseline_3mo — market share top-25, baseline window (3 months covering prior + 2 months back)

**Replaces the old W1.A1.market_prior call.** Single multi-month call covering the entire baseline_3mo_window — gives prior-month data (for MoM delta_bps) AND baseline_3mo aggregate (for the 3-mo column) in ONE call. Net zero new MCP calls vs. the old `market_prior` setup.

```python
get_sold_summary(
    # NO make filter
    inventory_type="New"|"Used",
    ranking_dimensions="make",
    ranking_measure="sold_count",
    ranking_order="desc",
    top_n=25,
    limit=5000,
    summary_by="state",
    date_from="<baseline_3mo_window.date_from>",         # first of (current - 3 months)
    date_to="<baseline_3mo_window.date_to>",             # last day of prior_month (baseline ends at prior's end)
)
```

→ Returns ~3,975 rows (3 months × ~53 states × top_n=25). Within the 5,000-row cap but **frequently triggers truncation** at the MCP channel cap. The runtime emits `Error: result (N chars) exceeds maximum allowed tokens. Output saved to <path>` and saves to a file.

Pipe through (canonical Write→file pattern per `_failure-recovery.md`):
```bash
# If inline (rare for this call — usually persisted):
Write(file_path="/tmp/marketcheck/<session-id>/market_baseline_3mo.json", content=<response>)
python scripts/parse_sold_summary.py --aggregate-by-dimension make --by-window \
  --file /tmp/marketcheck/<session-id>/market_baseline_3mo.json

# If persisted by runtime (the common case for M=3 leaderboard):
python scripts/parse_sold_summary.py --aggregate-by-dimension make --by-window \
  --file <runtime-saved-path>
```

Captures `dimension_values: [{value, months: {"YYYY-MM": {total_sold_count}}, total_sold_count_all_months}, ...]` (lean post-H1 shape).

The script's `_compute_market_share` then:
- Extracts prior month's rows from per-make `months[<prior_yymm>]` for the MoM delta_bps (per-row in `top_10_makes` and ticker-level in `market_share.delta_bps`).
- Aggregates across the 3 months for `market_share.baseline_3mo_pct`.

### W1.A1.ev[k] — per-make EV slice (legacy / brand_orphan only)

For each `make` in `makes[]`:

```python
get_sold_summary(
    make="<Make>",
    fuel_type_category="EV",
    inventory_type="New"|"Used",
    ranking_dimensions="make",
    ranking_measure="sold_count",
    top_n=1,
    limit=5000,
    summary_by="state",
    date_from="<baseline_3mo_window.date_from>",
    date_to="<current_month.date_to>",
)
```

→ Same shape as `sold[k]` but filtered to EV rows. Returns ≤212 rows; often fewer for low-EV-volume makes.

Pipe through:
```bash
Write(file_path="/tmp/marketcheck/<session-id>/ev_<make_lower>.json", content=<response>)
python scripts/parse_sold_summary.py --aggregate-make-by-window "<Make>" \
  --file /tmp/marketcheck/<session-id>/ev_<make_lower>.json
```

### W1.A1.ev_leaders — EV market leaders (pure_play only)

```python
get_sold_summary(
    # NO make filter
    fuel_type_category="EV",
    inventory_type="New"|"Used",
    ranking_dimensions="make",
    ranking_measure="sold_count",
    ranking_order="desc",
    top_n=10,
    limit=5000,
    summary_by="state",
    date_from="<prior_month.date_from>",                # M=2 covers prior + current
    date_to="<current_month.date_to>",
)
```

→ Returns ~1,060 rows.

Pipe through:
```bash
Write(file_path="/tmp/marketcheck/<session-id>/ev_leaders.json", content=<response>)
python scripts/parse_sold_summary.py --aggregate-by-dimension make --by-window \
  --file /tmp/marketcheck/<session-id>/ev_leaders.json
```

Captures `dimension_values: [{value, months: {YYYY-MM: {total_sold_count}}, total_sold_count_all_months}, ...]` (lean shape).

## Wave A2 — active inventory + segment mix (single agent message, all in parallel)

| # | Tool | Purpose | Fires when | Persistence risk |
|---|---|---|---|---|
| W1.A2.active[k] | `search_active_cars` | Per-make active inventory + price/DOM stats | always, once per make | ~1 KB — never persists. Stdin pipe always works. |
| W1.A2.seg[k] | `get_sold_summary` | Per-make body_type segment mix, current month | always, once per make | At `top_n=10`: ~115 KB **persists**; at `top_n=4-5`: ~50 KB often inline. **Recommend `top_n=4-5`** (body-type cardinality is ~5-7). If persists, use `--file`; if inline-too-large, use `Write` + `--file` per `_failure-recovery.md` Mode 2. |

**Wave A2 size:** `2N` calls.

### W1.A2.active[k] — per-make active inventory

For each `make` in `makes[]`:

```python
search_active_cars(
    make="<Make>",
    car_type="new"|"used",                              # lowercased inventory_type
    stats="price,dom",
    rows=0,
    price_range="1-*",
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

Pipe through:
```bash
echo '<response>' | python scripts/parse_search.py
# (parse_search responses are ~1 KB — heredoc/stdin pipe is fine for this script only)
```

Captures `{num_found, stats_present, stats: {price, dom}}`.

### W1.A2.seg[k] — per-make segment mix (body_type)

For each `make` in `makes[]`:

```python
get_sold_summary(
    make="<Make>",
    inventory_type="New"|"Used",
    ranking_dimensions="body_type",
    ranking_measure="sold_count",
    top_n=5,                                            # tightened from 10; body-type cardinality is ~5-7. Halves response size.
    limit=5000,
    summary_by="state",
    date_from="<current_month.date_from>",
    date_to="<current_month.date_to>",
)
```

→ Returns ~530 rows (1 month × ~53 states × top_n=10).

Pipe through:
```bash
Write(file_path="/tmp/marketcheck/<session-id>/seg_<make_lower>.json", content=<response>)
python scripts/parse_sold_summary.py --aggregate-by-dimension body_type \
  --file /tmp/marketcheck/<session-id>/seg_<make_lower>.json
```

## After Wave A1 + A2 — assemble compute_oem_stats input

The model assembles a single JSON document from the parser outputs:

```json
{
  "ticker": "<ticker | null>",
  "company_name": "<company_name>",
  "classification": "<classification>",
  "makes": ["<Make1>", "<Make2>", ...],
  "inventory_type": "New" | "Used",
  "windows": <full output from compute_month_windows>,    // emits both `baseline_3mo` and the alias `baseline_3mo_window` — passthrough is safe
  "per_make": {
    "<Make>": {
      "sold_by_window": <W1.A1.sold[k] parser output.make_by_window>,
      "active": <W1.A2.active[k] parser output.{num_found, stats}>,
      "segment_mix": <W1.A2.seg[k] parser output.dimension_values>,
      "ev_slice_by_window": <W1.A1.ev[k] parser output.make_by_window>  // null for pure_play
    }
  },
  "market_top25": {
    "current":                <W1.A1.market_current parser output.dimension_values>,
    "baseline_3mo_by_window": <W1.A1.market_baseline_3mo parser output.dimension_values>
  },
  "ev_market_leaders": <W1.A1.ev_leaders parser output>  // null for legacy/brand_orphan
}
```

**`market_top25` shape note:** the `current` field is single-month flat (an array of `{value, total_sold_count, share_pct, ...}` records). The `baseline_3mo_by_window` field is multi-month nested (an array of `{value, total_sold_count_all_months, months: {YYYY-MM: {total_sold_count}, ...}}` records — the post-trim lean shape from `parse_sold_summary --by-window`). `compute_oem_stats._compute_market_share` extracts the prior month's per-make rows from the nested `months` map and computes the 3-mo baseline share from the cross-month aggregate. The legacy `market_top25.prior` key (single-month flat) is still accepted for backward compatibility but emits DQ event (o) — orchestration spec drift.

Pipe to:
```bash
echo '<assembled>' | python scripts/compute_oem_stats.py
```

Capture the full output object: `headline`, `leading_indicators_raw`, `per_make_raw`, `active_inventory`, `market_context`, `ev_block`, `segment_mix`, `dq_events`.

## After compute_oem_stats — aggregate signals

Slice the output for `aggregate_signals.py`:

```json
{
  "leading_indicators_raw": <from compute_oem_stats>,
  "per_make_raw": <from compute_oem_stats>,
  "ticker_classification": "<classification>"
}
```

Pipe:
```bash
echo '<slice>' | python scripts/aggregate_signals.py
```

Capture: `verdict`, `per_metric_bands`, `composite_slots`, `scores`, `mean_score`, `n_bullish`, `n_bearish`, `rationale`, `signal_drivers`, `per_make_divergence`.

## Render

Use `assets/w1-output-template.md` verbatim. Interpolate fields from:
- `compute_month_windows` → `<current_month.label>`, `<prior_month.label>`, `<baseline_3mo_window.label>`
- `resolve_oem` (or inline brand-orphan construction) → `<ticker>`, `<company_name>`, `<makes>`, `<classification>`
- `compute_oem_stats` → `headline`, `leading_indicators_raw`, `per_make_raw`, `active_inventory`, `market_context`, `ev_block`, `segment_mix`, `dq_events`
- `aggregate_signals` → `verdict`, `per_metric_bands`, `composite_slots`, `signal_drivers`, `rationale`, `per_make_divergence`

## Wall-clock budget (W1)

- Pre-flight: ~2s (3 local script calls).
- Wave A1: ~12-15s (parallel; sets by the slowest call).
- Wave A2: ~12-15s.
- Post-Wave-A2 scripts: ~2s (`compute_oem_stats` + `aggregate_signals`).
- **Total ≈ 25–30s common path.**

If serialized (no parallelism): 60-90s. The wave model is load-bearing.

## DQ event triggers in W1

- **(a)** Any of the ~16-30 calls returns an error envelope → log; if A1.sold[k] fails for all makes, halt; otherwise degrade gracefully.
- **(c)** `resolve_oem` returned `resolution=fuzzy` → log input + resolved canonical + score.
- **(d)** A2.active[k] returned `stats_present: false` → log; render `num_found` only.
- **(e)** Days Supply rendered → footnote always rendered.
- **(f)** Wave B not used in W1 (segment mix is in Wave A2 now).
- **(g)** Target ticker's makes absent from market-share top-25 → log.
- **(h)** A2.seg[k] returned zero rows → log; render `—` for that make's segment-mix contribution.
- **(i)** Low-volume make (sold_count_current < 100) → log; reduce confidence.
- **(j)** Brand-orphan path taken → log (in pre-flight, before Wave A1).
- **(k)** EV slice skipped for pure_play OR returned zero across all makes for legacy → log + EV block omitted.
- **(l)** Cross-make divergence flagged (`aggregate_signals.per_make_divergence` non-empty) → log + render divergence callouts in Section 4.
