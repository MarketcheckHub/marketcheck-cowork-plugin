# W1 — Brand Market Share

Reference workflow for "market share," "who is gaining," "which brands are losing share." Computes per-make share % and share-change in basis points (bps) by comparing two `get_sold_summary` calls — current period vs prior period.

**US-only** — halt UK profiles per `references/country-uk.md`.

## Required inputs

- **Geographic scope**: `state` (2-letter code) for state-level share, OR omit `state` for national. Default: `profile.location.state` if available, otherwise national.
- **Current period**: a single full calendar month (e.g. March 2026 → `2026-03-01` / `2026-03-31`). Default: last full month via `compute_period_window.py --months-back 1 --num-months 1`.
- **Prior period**: a single full calendar month (e.g. February 2026). Default: month before current via `compute_period_window.py --months-back 2 --num-months 1`.
- **Inventory type**: `Used` / `New`. Default: `profile.preferences.default_inventory_type`; halt-and-ask if `both`.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | per `references/country-uk.md` |
| `profile.location.country == "CA"` | "Market share analysis is US-only — Canada has no `get_sold_summary` data surface." |
| User-supplied dates not month-aligned | "Date window must be full calendar month(s). Got `<date_from>` to `<date_to>`. Use `compute_period_window.py` or supply month-aligned dates." |
| `inventory_type == "both"` and user silent | "Run brand-share for **used** or **new** sales? (Sold-summary doesn't mix the two cleanly.)" |

## Wave A — 2 parallel `get_sold_summary` calls

Per universal wave contract: both calls dispatched in a single agent message; wait for both before piping to the parsers + computer.

```
get_sold_summary (current period):
  date_from=<current.date_from>, date_to=<current.date_to>
  inventory_type=<Used|New>                      # always set explicitly
  state=<STATE>                                  # omit for national
  ranking_dimensions="make"                      # minimal; avoid default 3-dim
  ranking_measure="sold_count"
  ranking_order="desc"
  top_n=50                                       # Q1=A: top 50 makes covers ~98% of US sales
  summary_by="state"                             # default; per-state buckets within make rows
  limit=5000                                     # tool default 1000 silently truncates
  # NO dealer_type (per references/sold-summary-safety.md line 63 — silent suppression)
→ parse_sold_summary.py --file <persisted-path>

get_sold_summary (prior period):
  same shape, prior date_from / date_to
→ parse_sold_summary.py --file <persisted-path>
```

Persist each response via the Write tool to `/tmp/marketcheck/<session.run_id>/w1_current.json` and `w1_prior.json` (per `references/truncation-recovery.md`). `get_sold_summary` is the one tool in the toolset that returns raw JSON without an envelope; `_common._maybe_unwrap` passes the unwrapped payload through transparently, so the standard `parse_sold_summary.py --file <path>` recipe works.

### Wall-clock budget

~12s for the wave (2 parallel calls). Vs. ~24s serial.

## Pipeline

```
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w1_current.json > current_parsed.json
parse_sold_summary.py --file /tmp/marketcheck/<run_id>/w1_prior.json   > prior_parsed.json

compute_brand_share.py \\
  --current current_parsed.json \\
  --prior   prior_parsed.json \\
  [--top-n 20]                       # default 20 makes in the rendered table
  [--user-brand <make>]              # from profile.dealer.franchise_brands or user
  [--state <STATE>]                  # post-aggregation state filter
> brand_share.json

render_share_table.py --mode brand-share --data brand_share.json
> brand_share_table.md
```

## Quarterly variant

When the user asks for "Q1 2026" instead of a single month, fan out `get_sold_summary` × 3 monthly calls per period (Jan, Feb, Mar) in the same wave. The parser emits one rows array per call; `compute_brand_share.py` accepts `--current` / `--prior` as JSON files but doesn't currently sum across multiple parsers.

For now, per the plan, the agent concatenates the three monthly `rows[]` arrays into a single combined "current" file before piping to `compute_brand_share.py`:

```python
import json
combined = {"ok": True, "rows": []}
for f in ["jan_parsed.json", "feb_parsed.json", "mar_parsed.json"]:
    combined["rows"].extend(json.load(open(f))["rows"])
# Write combined to disk, then pipe to compute_brand_share.py
```

The aggregator handles cross-month / cross-state summing internally per-make.

## Long-tail caveat (Q1=A footnote)

When the calling skill set `top_n=50`, the share denominator is the sum of sold_count across the visible 50 makes. The long-tail (Maserati, Lotus, Ferrari, Lamborghini, etc.) is excluded — typically 2–5% of national volume. The script emits this as DQ event (e):

> *"Share computed over visible top-50 makes; long-tail makes excluded. True national volume is ~2–5% higher."*

The renderer surfaces this as a footnote under the brand-share table.

## Output rendering

The skill renders:

1. **Headline** — sourced from `compute_brand_share.summary`:
   *"<top_make> holds <top_share>% national market share in <month> <year>, <bps_signed> from <prior_month>. <top_gainer> is the biggest gainer at +<gainer_bps> bps."*
2. **Brand-share table** (rendered via `render_share_table.py --mode brand-share`):
   `Rank | Make | Current Sold | Current Share % | Prior Sold | Prior Share % | Share Change | Volume Change | Trend`
   User brand bolded.
3. **Top-3 gainers / Top-3 losers** — sourced from `compute_brand_share.summary.top_3_gainers` / `top_3_losers`.
4. **User-brand movement narrative** (when `summary.user_brand_movement` is non-null):
   *"<user_brand> moved from #<prior_rank> to #<current_rank> with a <bps_signed> shift."*
5. **Strategic implications** — pulled from `references/outcomes.md` action-to-outcome funnel scenario 1 (OEM brand manager).
6. **Source line**: `Source: MarketCheck sold data, <period>, <state-or-national>, <inventory_type>.`

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| `parse_sold_summary` `error_type=make_model_not_found` | facet mismatch (rare on top-N call) | Retry once with facet-discovered casing per `references/facet-discovery.md`. If still failing, halt the workflow with a user-facing error. |
| `parse_sold_summary` `error_type=validation_dimension_limit` | `ranking_dimensions` rejected | Retry once with `ranking_dimensions="make"` (already minimal — fall back to no `ranking_dimensions`). |
| `parse_sold_summary` `error_type=network_422` | mis-aligned dates upstream | Verify dates are month-aligned; re-issue. |
| `parse_sold_summary` `error_type=network_5xx` | upstream error | Halt with "Upstream data unavailable; retry in a few minutes." |
| `compute_brand_share` `error_type=no_current_data` | empty rows after filters | Halt with "No sold-summary data for `<period>` in `<state>`. Check date alignment or widen the geographic scope." |
| Both periods empty (rare) | Both `parse_sold_summary` returned 0 rows | Halt with the same no-data message; emit DQ event (a) per period. |
| User brand absent in top-50 of either period | Brand exists but is sub-top-50 | `summary.user_brand_movement.current_rank` / `prior_rank` is null; renderer prints *"<brand> not in top 50 makes for the period."* |
