---
name: w1-single-group
description: Workflow 1 — Single Group Health Check. Full spec for the W1 wave structure, parser pipeline, stats assembly, and rendering.
type: reference
---

# W1 — Single Group Health Check

Triggered when an equity analyst asks "how is AutoNation doing?", "LAD health check", "CarMax volume signal", or any single-ticker / single-name operational read.

## Required inputs

| Input | Source | Required? |
|---|---|---|
| Group name or ticker | User prompt | Yes |
| Profile (country, optional tracked_tickers) | `marketcheck-profile.md` | Optional — if absent, skill prompts for the group inline |

The skill never crashes for missing inputs — it asks.

## Pre-flight (no MCP calls — local only)

1. Read `marketcheck-profile.md`. Extract `location.country`. Halt if not US.
2. Run `scripts/compute_month_windows.py --today <currentDate>`. Capture the output JSON; the agent feeds `current_month` and `prior_month` windows into every sold-summary call.
3. Run `scripts/resolve_group_name.py --input "<user input>"`.
   - If `result.ok == false`, error_type=`no_candidates` → fall through to the **active-facets recovery branch** documented in SKILL.md "Before you start" step 3. If that branch also fails to land on an enum-resolvable name, halt cleanly (do NOT call `get_sold_summary` with a non-enum name).
   - If `result.ok == true`, capture `canonical`, `ticker` (may be null), `classification` (Used-only / New-only / Both).
4. Determine `primary_channel`:
   - `Used-only` → `Used`
   - `New-only` → `New`
   - `Both` → `Used` (canonical primary; secondary is `New`)
5. Confirm with user: *"Analyzing **<ticker>** (<canonical>) — <classification>. Pulling MoM signals for <current_month.label> vs. <prior_month.label>…"*

## Wave A — single agent message, all calls in parallel

Wave A fires every required MCP call in one parallel batch. Wall-clock ≈ 12-15s regardless of count.

| # | Tool | Purpose | Fires when |
|---|---|---|---|
| W1.A.1 | `get_sold_summary` | Target sold, current month, primary | always |
| W1.A.2 | `get_sold_summary` | Target sold, prior month, primary | always |
| W1.A.3 | `get_sold_summary` | Target sold, current month, secondary | classification = Both |
| W1.A.4 | `get_sold_summary` | Target sold, prior month, secondary | classification = Both |
| W1.A.5 | `get_sold_summary` | Peer leaderboard, current month, primary | always |
| W1.A.6 | `search_active_cars` | Target active, primary's `car_type` | always |
| W1.A.7 | `search_active_cars` | Target active, secondary's `car_type` | classification = Both |

**Wave A counts: 4 (Used-only or New-only) up to 7 (Both).**

### W1.A.1 / A.2 — Target sold (current and prior month)

```python
get_sold_summary(
    dealership_group_name="<canonical>",
    inventory_type="Used" | "New",          # primary
    ranking_dimensions="dealership_group_name",
    ranking_measure="sold_count",
    top_n=1,
    limit=5000,
    summary_by="state",
    date_from="<window.date_from>",
    date_to="<window.date_to>",
)
```

Pipe each response through `parse_sold_summary.py --aggregate-group "<canonical>"` per `SKILL.md §Script invocation discipline`. See `references/script-contracts.md §parse_sold_summary` for `group_baseline` shape and the `group_baseline_skipped_reason` branches.

Capture `group_baseline` from the parser output. This is the channel-level aggregate for that month.

### W1.A.3 / A.4 — Target sold, secondary (Both groups only)

Identical to A.1 / A.2 with `inventory_type` flipped to the secondary value.

### W1.A.5 — Peer leaderboard

```python
get_sold_summary(
    # NO dealership_group_name filter
    inventory_type="Used" | "New",          # primary
    ranking_dimensions="dealership_group_name",
    ranking_measure="sold_count",
    ranking_order="desc",
    top_n=20,
    limit=5000,
    summary_by="state",
    date_from="<current_month.date_from>",
    date_to="<current_month.date_to>",
)
```

Pipe through `parse_sold_summary.py --aggregate-by-group` per `SKILL.md §Script invocation discipline`. See `references/script-contracts.md §parse_sold_summary` for the `groups` array shape.

Capture the `groups` list (sorted desc by `total_sold_count`). Used for `peer_rank` computation.

### W1.A.6 / A.7 — Active inventory

```python
search_active_cars(
    mc_dealership_group_name="<canonical>",
    car_type="used" | "new",                 # primary's lowercase form
    stats="price,dom",
    rows=0,
    price_range="1-*",                       # exclude null-price rows from num_found — see sold-summary-safety.md §search_active_cars
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

Pipe through `parse_search.py` per `SKILL.md §Script invocation discipline`. See `references/script-contracts.md §parse_search` for the stats-mode output shape and the `stats_present: false` defensive fallback.

Capture `num_found` and `stats.{price, dom}` blocks (or `stats_present: false` per the defensive branch).

## After Wave A — assemble compute_group_stats input

The model assembles a single JSON document from the Wave A parser outputs. The shape below shows W1's workflow-specific assembly with placeholders; for the full per-field type schema (including null semantics and synonyms like `sold_count` ↔ `total_sold_count`), see `references/script-contracts.md §compute_group_stats`.

```json
{
  "group_canonical": "<canonical>",
  "ticker": "<ticker | null>",
  "classification": "<Used-only | New-only | Both>",
  "current_month_window": <full current_month block from compute_month_windows>,
  "current_month": {
    "used": <A.1 group_baseline | null>,
    "new":  <A.3 group_baseline | null>
  },
  "prior_month": {
    "used": <A.2 group_baseline | null>,
    "new":  <A.4 group_baseline | null>
  },
  "active": {
    "used": <A.6 {num_found, stats} | null>,
    "new":  <A.7 {num_found, stats} | null>
  },
  "peer_leaderboard": <A.5 groups list>
}
```

For Used-only / New-only groups, the unused channel is `null`. The script handles all three classifications.

Pipe to:
```
compute_group_stats.py < <assembled-input>
```

Capture the full output object (`headline`, `mom`, `active_health`, `peer_rank`).

The `peer_rank` object carries:
- `of` — count of public-traded groups present in the leaderboard (≤ 8).
- `by_volume` / `by_asp` / `by_dom` / `by_efficiency` — target's rank on each metric (and `delta_to_next_pct` on volume when target ranks #1).
- `peers` — full per-group KPI rows for every public-traded peer in the leaderboard, sorted desc by `sold_count`. Each row: `{canonical, ticker, is_target, sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, efficiency_score}`. The template renders this as a side-by-side peer KPI table with the target row bolded.
- `dropped` — sorted list of public-traded canonical names that did NOT land in the top-20 leaderboard this month. Rendered as a footnote when non-empty.

## After compute_group_stats — aggregate signals

Pipe `mom + active_health` blocks into `aggregate_signals.py`. The slice below shows the W1 pipe; the full input/output contract (including the `no_scoreable_signals` reason and per-band score mapping) lives in `references/script-contracts.md §aggregate_signals`.

```json
{
  "mom":           <compute_group_stats output mom>,
  "active_health": <compute_group_stats output active_health>
}
```

```
aggregate_signals.py < <mom-and-health>
```

Capture `verdict`, `scores`, `mean_score`, `n_bullish`, `n_bearish`, `rationale`.

## Wave B (optional) — segment mix deep-dive

Fires only when the user explicitly asks for "what makes is selling" / "body type breakdown" / "deeper analysis".

| # | Tool | Purpose | Fires when |
|---|---|---|---|
| W1.B.1 | `get_sold_summary` | body_type mix, primary inventory_type, current month | optional deep-dive |
| W1.B.2 | `get_sold_summary` | make mix, primary inventory_type, current month | optional deep-dive |
| W1.B.3 | `get_sold_summary` | body_type mix, secondary inventory_type | classification=Both AND deep-dive |
| W1.B.4 | `get_sold_summary` | make mix, secondary inventory_type | classification=Both AND deep-dive |

Each call uses `top_n=10` (body_type) or `top_n=15` (make), `ranking_dimensions=body_type` or `=make`, the filtered `dealership_group_name=<canonical>` param (applied at the MCP call), and `limit=5000`.

### Wave B parsing — `--aggregate-by-dimension`

After each Wave B response returns, pipe it through `parse_sold_summary.py` with the new aggregation mode (one flag value per dimension):

```bash
echo '<mcp-response>' | python scripts/parse_sold_summary.py --aggregate-by-dimension body_type
echo '<mcp-response>' | python scripts/parse_sold_summary.py --aggregate-by-dimension make
```

The flag is mutually exclusive with `--aggregate-group` and `--aggregate-by-group`. Wave B mix payloads truncate frequently — when they do, the runtime returns `Error: result (N chars) exceeds maximum allowed tokens. Output saved to <path>`. In that case, pipe the saved path to the parser:

```bash
python scripts/parse_sold_summary.py --file <saved-path> --aggregate-by-dimension body_type
```

Each parser call emits a `dimension_values` array sorted desc by `total_sold_count`, with per-bucket fields `{value, total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, share_pct, row_count, months_included}` plus a top-level `dimension_total_sold_count`. Rows with blank/null dimension values are skipped; buckets with `total_sold == 0` are dropped (the same divide-by-zero discipline as `--aggregate-group`).

Feed the parsed `dimension_values` directly into the W1 output template's **Mix breakdown** section (`assets/w1-output-template.md`). The template renders the top 5 of each dimension as a 5-column table (Body type / Make · Volume · Share · ASP · DOM) per channel.

## Render

Use `assets/w1-output-template.md` verbatim. Interpolate fields from:
- `compute_month_windows` → `<current_month.label>`, `<prior_month.label>`
- `resolve_group_name` → `<canonical>`, `<ticker>`, `<classification>`
- `compute_group_stats` → headline + MoM + active_health + peer_rank values
- `aggregate_signals` → `verdict`, `scores`, `rationale`

## Wall-clock budget (W1)

- Pre-flight (no MCP): ~1s (3 quick local script calls).
- Wave A: ~12-15s (4-7 parallel calls; the slowest call sets the wall clock).
- Post-Wave-A scripts: ~1s (`compute_group_stats` + `aggregate_signals`).
- **Total ≈ 15-18s common path.**

If serialized: ~50-90s. The wave model is load-bearing.

## DQ event triggers in W1

- **(a)** Any of the 7 calls returns an error envelope → log; if A.1/A.2 fails, the whole headline fails (halt with explanation); other failures degrade gracefully (skip the affected metric).
- **(c)** `resolve_group_name` returned `resolution=fuzzy` → log the user's input and the resolved canonical.
- **(d)** A.6 or A.7 returned `stats_present: false` → log; render `num_found` only with no Days Supply for that channel.
- **(e)** Days Supply rendered → footnote always rendered (live-vs-historical mix).
- **(g)** Target group not in A.5's top-20 leaderboard → `peer_rank` is `null`; render "below the top-20 cohort this month".
- **(h)** Wave B fires but a channel's mix call returns `dimension_total_sold_count == 0` (or the call errored) → log; the renderer skips that channel's mix sub-section in the Mix breakdown.
