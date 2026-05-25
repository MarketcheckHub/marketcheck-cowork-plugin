---
name: w3-top-n
description: Workflow 3 — Top-N dealer group leaderboard for the most recent complete calendar month. Single MCP call; per-group aggregation done by parse_sold_summary.
type: reference
---

# W3 — Top-N Dealer Group Leaderboard

Triggered by "top 10 dealer groups by volume", "biggest dealer groups in <month>", "leaderboard of dealer-group sold counts". Distinct from `group-benchmarking` — that skill does composite-rank scoring across all 8 publicly-traded names; W3 is a volume leaderboard with no per-row verdict.

## Required inputs

| Input | Source | Required? |
|---|---|---|
| Top N (1 ≤ N ≤ 20) | User prompt | Yes — default 10 if unspecified |
| Inventory type (Used or New) | User prompt | Optional — default Used |
| Profile (country) | `marketcheck-profile.md` | Read for country gate |

## Pre-flight (no MCP calls — local only)

1. Read `marketcheck-profile.md`. Halt if `country != US`.
2. Run `compute_month_windows.py --today <currentDate>`. Capture `current_month`.
3. Determine N: parse from user prompt; default to 10 if unspecified.
4. **N > 20 halt:** if `N > 20`, halt with:
   *"This skill caps at top 20 groups per call (server-side `top_n` interacts with `limit=5000`). For broader lists, run multiple W3 invocations or use `group-benchmarking` for the full 8-group cohort."*
5. Determine `inventory_type`: ask the user "Used or New?" if unspecified; default Used. The single sold-summary call uses this verbatim.

## Wave A — single call

| # | Tool | Purpose |
|---|---|---|
| W3.A.1 | `get_sold_summary` | Top 20 groups by sold_count, current month, user-chosen inventory_type |

```python
get_sold_summary(
    # NO dealership_group_name filter — we want the full leaderboard
    inventory_type="Used" | "New",
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

Pipe through `parse_sold_summary.py --aggregate-by-group` per `SKILL.md §Script invocation discipline`. The parser buckets per-(group × state) rows by `dealership_group_name` into a `groups` array sorted desc by `total_sold_count`; see `references/script-contracts.md §parse_sold_summary` for the full output shape.

W3 total: **1 MCP call.**

## After Wave A — slice and resolve

1. Take the `groups` list from the parser. It contains up to 20 records, sorted desc by volume.
2. Slice to `groups[:N]` to honor the user's requested top N.
3. For each row, look up the ticker via `references/ticker-mapping.md`:
   - The 8 canonical names map to tickers (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA).
   - Other canonical names → ticker is null (private dealer group).
4. Compute per-row efficiency_score = `total_sold_count / weighted_avg_days_on_market` (skip when DOM is 0 or null).
5. Compute the cohort headline:
   - `top_group` = `groups[0].dealership_group_name`
   - `top_sold_count` = `groups[0].total_sold_count`
   - `median_asp` = median of `weighted_avg_sale_price` across the top-N rows
   - `median_dom` = median of `weighted_avg_days_on_market` across the top-N rows
   - `cohort_observation` per template guidance (top-2 share / spread ratio / volume distribution)

W3 deliberately does NOT compute `aggregate_signals` per row — no MoM data, no per-row verdicts. The template enforces this.

## Render

Use `assets/w3-output-template.md`. Render the leaderboard table with per-row formatting per the template (commas, $-signs, decimal precision).

## Wall-clock budget (W3)

- Pre-flight: ~1s.
- Wave A: ~6-10s (single call; smaller payload than W1/W2's parallel batches).
- Post-Wave-A: ~1s (parse + slice + ticker reverse-lookup).
- **Total ≈ 8-12s common path.**

## Edge cases

- **Top group has no MoM context.** This is by design; W3 is a snapshot. The cohort headline does not reference month-over-month change.
- **Some groups have null DOM.** efficiency_score is null for those rows; render as `—` in the Efficiency column.
- **User asks "top 5".** Slice to N=5 from the top-20 fetched. Don't re-issue with `top_n=5` — the additional 15 rows are essentially free at our `limit=5000` budget.
- **User asks "top 30".** Halt with the cap message (see pre-flight step 4).
- **Empty response (no rows for the chosen month/inventory_type).** Render: *"No sold-volume data for `<inventory_type>` in `<current_month.label>`. The most-recent-complete-month aggregates may still be propagating upstream — try again tomorrow."*

## DQ event triggers in W3

- **(b)** Truncation envelope unwrap (rare at top_n=20 with limit=5000, but the parser supports `--file` if it happens).
- **(j)** User requested N>20 → halted with cap explanation (this is a pre-flight halt; not a runtime DQ event but logged for completeness).
- **(a)** A.1 call returned an error → halt with the error message; W3 has no fallback (single-call workflow).

## What W3 deliberately does NOT do

- **No per-row verdicts** (BULLISH/BEARISH/etc.). No `aggregate_signals.py` invocation. Route to W1 for ticker-tied verdict requests; route to `group-benchmarking` for composite cross-group rank.
- **No active inventory.** Adding active-inventory calls would 1+N the call count (one per group up to 20). Out of W3's snapshot scope.
- **No MoM.** No prior-month call. The leaderboard is "this month" only.
- **No peer rankings within the leaderboard.** The leaderboard IS the ranking; we don't rank within the rank.
