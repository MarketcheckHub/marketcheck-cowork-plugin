# W1 Output Template — Single Group Health Check

This template is the single source of truth for W1's output structure. The
model interpolates `<placeholder>` fields from `compute_group_stats.py` and
`aggregate_signals.py` outputs. Optional blocks marked `(OPTIONAL)` render
only when the precondition holds.

**Naming convention:** lowercase `<placeholder>` references the corresponding
field on the script outputs (verbatim numeric value). Uppercase labels like
`<VERDICT>` render the resolved verdict word.

---

## First line (always)

```
Analyzing <ticker> (<canonical>) — <classification>
```

Where:
- `<ticker>` is the resolved ticker (e.g., `KMX`) or — for groups not in the 8-name public set — render the canonical name only and skip the parenthetical.
- `<classification>` is `Used-only`, `New-only`, or `Both`.

---

## Headline (always)

One sentence. Format:

```
<VERDICT>: <ticker> in <month_label> — <one-sentence summary anchored on the headline metric>.
```

`<VERDICT>` is one of: `🟢 BULLISH`, `🔴 BEARISH`, `🟡 NEUTRAL`, `🟠 CAUTION` (per-metric, not headline), `⚪ MIXED`. The verdict word comes verbatim from `aggregate_signals.verdict`.

If `aggregate_signals.verdict` is `null` (no scoreable signals), render:
```
INSUFFICIENT DATA: <ticker> in <month_label> — no scoreable MoM signals available; rendering current-month KPIs only.
```

---

## Operational KPI table (always)

Render exactly this Markdown table:

```
| Metric                  | Current (<current_month.label>) | Prior (<prior_month.label>) | MoM       |
|-------------------------|---------------------------------|------------------------------|-----------|
| Volume (sold count)     | <headline.sold_count_total>     | <prior_total>                | <mom.volume_pct ±%> |
| Avg Sale Price          | $<headline.weighted_avg_sale_price> | $<prior_asp>             | <mom.asp_pct ±%>    |
| Avg Days on Market      | <headline.weighted_avg_days_on_market> days | <prior_dom> days   | <mom.dom_delta ±days> |
| Efficiency Score        | <headline.efficiency_score>     | <prior_eff>                  | <mom.efficiency_pct ±%> |
```

**Formatting rules:**
- Volume: integer with thousands separator (e.g., `11,500`).
- ASP: `$` prefix, no decimal places (e.g., `$24,800`). Use thousands separator.
- DOM: 1 decimal place + " days" suffix (e.g., `38.4 days`).
- Efficiency Score: 1 decimal place (e.g., `302.6`).
- MoM: signed percentage with 1 decimal (e.g., `+2.4%`, `-3.5%`); for DOM delta use signed days (e.g., `-1.5 days`).
- Render `—` (em-dash) when the value is null (e.g., MoM column when prior is 0).

---

## Inventory health (always when active data present)

```
**Inventory health (live):**
- Used: <num_found_used> active · avg $<active_avg_price_used> · avg DOM <active_avg_dom_used> days · Days Supply <days_supply_used>¹
- New:  <num_found_new>  active · avg $<active_avg_price_new>  · avg DOM <active_avg_dom_new>  days · Days Supply <days_supply_new>¹
```

Render only the channels populated in `active_health.{used,new}` (skip the row entirely when null). If both are null, omit the section.

**Footnote (always render when any Days Supply is shown):**
```
¹ <active_health.footnote>
```

---

## Peer ranking (when peer_rank is non-null)

```
**Peer ranking (vs. <peer_rank.of> publicly-traded dealer groups):**
- Volume:     #<by_volume.rank> of <peer_rank.of><,delta_to_next clause>
- ASP:        #<by_asp.rank>
- DOM:        #<by_dom.rank> (lower is better)
- Efficiency: #<by_efficiency.rank>
```

The `<delta_to_next clause>` renders only on `by_volume` when `delta_to_next_pct` is present:
- " · +<delta_to_next_pct>% ahead of #2" if the target is rank 1.
- Otherwise omit.

If `peer_rank` is `null` (target group not in top-20 leaderboard), render:
```
**Peer ranking:** below the top-20 cohort this month — limited cross-group context available.
```

---

## Peer KPIs table (when peer_rank.peers is non-empty)

Render a per-group KPI table for every public-traded peer that landed in the top-20 leaderboard. Sort order comes from `peer_rank.peers` (already desc by `sold_count`). **Bold the row where `is_target == true`.**

```
**Peer KPIs (<current_month.label>):**

| Group | Ticker | Volume | ASP | DOM | Efficiency |
|-------|--------|--------|-----|-----|------------|
| <canonical> | <ticker> | <sold_count> | $<weighted_avg_sale_price> | <weighted_avg_days_on_market> days | <efficiency_score> |
| ...one row per peer in peer_rank.peers... |
```

**Per-cell formatting (matches the KPI-table conventions):**
- Volume: thousands-separated integer (`11,500`); `—` when null.
- ASP: `$` prefix, no decimals, thousands separator (`$24,800`); `—` when null.
- DOM: 1 decimal + " days" (`38.4 days`); `—` when null.
- Efficiency: 1 decimal (`302.6`); `—` when null.
- Ticker: render as-is (`KMX`, `LAD`, `AN`, etc.). Should never be null in this table — every row's `ticker` is mapped from the 8-name public set.

**Target row:** wrap every cell in the target's row with `**` to bold it. The reader's eye should land on the target group immediately.

**Dropped-peers footnote (when `peer_rank.dropped` is non-empty):**

```
> Note: <comma-separated names from peer_rank.dropped> fell below the top-20 leaderboard this month and are not shown.
```

If `dropped` is empty, omit the footnote entirely.

---

## Mix breakdown — body type and make (OPTIONAL — when Wave B mix data is present)

Render this section only when the user explicitly requested deeper analysis and Wave B fired. Skip the section entirely when Wave B did not fire, OR when both channels' mix calls returned `dimension_total_sold_count == 0` (errors or empty buckets).

For each populated channel (Used / New) — i.e. each channel where `dimension_values` is non-empty — render two tables back-to-back. Slice the parser's `dimension_values` at index 5 (top 5 buckets). If fewer than 5 distinct values exist after the parser's blank-skip / zero-sold-drop, render what's available.

```
## Mix breakdown — <current_month.label>

### <Channel> top body types

| Body type | Volume | Share | ASP | DOM |
|---|---|---|---|---|
| <value> | <thousands-sep int> | <X.X%> | $<thousands-sep, no decimals> | <X.X days> |
| ... (up to 5 rows in dimension_values order) |

### <Channel> top makes

| Make | Volume | Share | ASP | DOM |
|---|---|---|---|---|
| <value> | <thousands-sep int> | <X.X%> | $<thousands-sep, no decimals> | <X.X days> |
| ... (up to 5 rows in dimension_values order) |
```

For a `Both` classification, render two channel sub-sections back-to-back: `### Used top body types` / `### Used top makes` / `### New top body types` / `### New top makes` — four tables total.

**Per-cell formatting** (matches the main KPI table conventions):
- `Body type` / `Make` cell: render `value` verbatim.
- `Volume`: thousands-separated integer (`13,871`). Never null (zero-sold buckets are dropped upstream).
- `Share`: one decimal + `%` suffix (`51.3%`). Rounded from the parser's `share_pct` (which is already two-decimal).
- `ASP`: `$` prefix, no decimals, thousands separator (`$27,861`). Render `—` if `weighted_avg_sale_price` is null.
- `DOM`: 1 decimal + ` days` suffix (`42.9 days`). Render `—` if `weighted_avg_days_on_market` is null.

**Footer (when distinct values exceed 5):**
```
> Top 5 of <len(dimension_values)> distinct <body types | makes> shown. Remaining values are below the cutoff.
```

If `len(dimension_values) <= 5`, omit the footer.

**Per-channel skip rule:** when a channel's `dimension_total_sold_count == 0` (the mix call errored or returned no rows), skip that channel's two sub-sections entirely AND log DQ event (h). The other channel's tables still render if its data is present.

---

## Earnings preview (always when verdict is non-null)

**Exactly 3 sentences, fixed shape:**

1. **Verdict + ticker + headline metric.**
   `<VERDICT> on <ticker> heading into the next quarterly print: <one-clause summary of the dominant signal>.`

2. **Strongest metric.**
   `<strongest metric>: <metric value with units>, the <BULLISH|CAUTION|BEARISH> band.`

3. **Weakest metric.**
   `<weakest metric>: <metric value with units>, the <BULLISH|CAUTION|BEARISH> band — <implication for the quarter>.`

Drive the strongest/weakest selection from `aggregate_signals.scores` — strongest is the metric with the highest score (BULLISH ties broken by absolute value of the metric); weakest is the metric with the lowest score (BEARISH ties broken similarly).

**Anti-patterns (DO NOT do):**
- No free-form narrative beyond these 3 sentences.
- No predictions of stock-price movement.
- No specific dollar EPS forecasts.

---

## Data Quality Notes (OPTIONAL)

Render when DQ events accumulated. List events in order encountered, prefixed `⚠`:

```
**Data Quality Notes:**
- ⚠ <event description>
- ⚠ <event description>
```

Categories:
- (a) MCP tool errors recovered from
- (b) Truncation envelope unwraps via `--file`
- (c) Resolved-group-name fuzzy match (confirmed by user)
- (d) Active-inventory stats absent (syndication response missing data.stats)
- (e) Days-Supply asymmetry footnote rendered (always render when applicable)
- (f) Workflow branch skipped by design
- (g) Group missing from peer leaderboard
- (h) Wave B channel returned `dimension_total_sold_count == 0` (or errored) → mix sub-section skipped for that channel

If no events, omit the section entirely.

---

## Footer (always)

Self-check pass → emit one-line:
```
✓ Verified: profile, signal aggregation, peer ranking, days-supply caveat.
```

Self-check fail → emit only the failures, prefixed `⚠`:
```
⚠ Days Supply footnote omitted — added back inline.
```

---

## Self-check items (model runs silently)

Internal guardrail; do NOT render the checkbox grid.

1. Profile loaded; country == "US".
2. Group canonical name confirmed (in 471-enum).
3. Inventory classification correct.
4. Date windows month-aligned (no in-progress month).
5. Every `get_sold_summary` call set `inventory_type` explicitly.
6. Every `get_sold_summary` call set `limit=5000`.
7. No `state` parameter passed.
8. Wave A included every required call (parallel, not serialized).
9. `compute_group_stats` received the assembled JSON; `aggregate_signals` received `mom + active_health`.
10. Headline verdict came from `aggregate_signals.verdict` (not hand-picked).
11. Days Supply rendered with footnote when applicable.
12. Earnings preview is exactly 3 sentences.
13. Mix breakdown rendered iff Wave B fired AND at least one channel has `dimension_total_sold_count > 0`; each rendered channel shows up to 5 body_type rows + up to 5 make rows sourced from `parse_sold_summary.py --aggregate-by-dimension` (no inline model rollup).
