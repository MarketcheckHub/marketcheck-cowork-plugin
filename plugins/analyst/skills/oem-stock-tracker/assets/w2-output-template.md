# W2 Output Template — Compare Two OEMs

Side-by-side comparison of two OEMs for the most recent complete calendar
month. **Static snapshot; no MoM** (per the W2 spec — MoM lives in W1).
**No 3-mo baseline.** **Verdicts driven by Days Supply + Market Share bands
only** since momentum metrics require multiple time windows W2 doesn't pull.

---

## First line (always)

For two OEM tickers:
```
Comparing <ticker_A> (<company_A>) vs. <ticker_B> (<company_B>) — <current_month.label>
```

If either is brand-orphan, use its `canonical_make` in place of the ticker parenthetical.

---

## Joint verdict headline (always)

```
<VERDICT_EMOJI_A> <VERDICT_A> · <ticker_A>  |  <VERDICT_EMOJI_B> <VERDICT_B> · <ticker_B>
```

Each verdict comes from its own `aggregate_signals.py` invocation. W2 verdicts are **derived solely from Days Supply + Market Share + (legacy only) EV transition bands** since MoM-bearing inputs are null. This is a documented limitation; render the footnote below the table.

---

## Side-by-side KPI table (always)

```
| Metric                      | <ticker_A> (<company_A>)         | <ticker_B> (<company_B>)         | Winner |
|-----------------------------|----------------------------------|----------------------------------|--------|
| Classification              | <classification_A>               | <classification_B>               | —      |
| Total volume (sold count)   | <sold_count_total_A>             | <sold_count_total_B>             | <higher> |
| Avg sale price              | $<weighted_avg_sale_price_A>     | $<weighted_avg_sale_price_B>     | <higher> |
| Avg days on market          | <weighted_avg_days_on_market_A> days | <weighted_avg_days_on_market_B> days | <lower> |
| MSRP positioning            | <msrp_gap.current_pct_A ±%>      | <msrp_gap.current_pct_B ±%>      | <higher> |
| Days Supply¹                | <days_supply_A>                  | <days_supply_B>                  | <lower> |
| Market share                | <market_share.current_pct_A ±%>  | <market_share.current_pct_B ±%>  | <higher> |
| EV % of total volume²       | <ev_block.transition.ticker_ev_pct_A ±%> | <ev_block.transition.ticker_ev_pct_B ±%> | <higher> |
| Active inventory (total)    | <total_active_count_A>           | <total_active_count_B>           | —      |
```

**Winner column rules:**
- Higher is better: Volume, ASP, MSRP positioning, Market share, EV % (for transition narrative), Active inventory (informational).
- Lower is better: DOM, Days Supply.
- Render `—` when both values are equal or one is null.
- Winner is the ticker (e.g., `F` or `GM`) — not the company name.

**Footnotes:**
1. `¹ Days Supply pairs live active inventory (today's snapshot) with the most-recent-complete-month sold velocity — a live-vs-historical mix. Uses the same inventory channel as the sold-data analysis (default new; "used" if user overrode).`
2. `² EV % renders for legacy / brand-orphan tickers only. For pure-play tickers (TSLA, RIVN, LCID), EV % is by definition 100%; the row uses "100% (pure-play)" as the value. When comparing pure-play vs legacy, the asymmetry is the headline.`

Apply same per-cell formatting rules as W1 (thousands separators in volume, `$` and no decimals on ASP, 1 decimal on DOM, signed % on percentages, bps on share / MSRP delta).

---

## Mix breakdown — body type (always when segment_mix has data)

```
**Top 3 body types per OEM (<current_month.label>):**

| Body type   | <ticker_A> volume | <ticker_A> share | <ticker_B> volume | <ticker_B> share |
|-------------|-------------------|------------------|-------------------|------------------|
| <body>      | <sold_A>          | <share_A>%       | <sold_B>          | <share_B>%       |
| ...up to 3 rows showing the UNION of top-3 body types from each OEM... |
```

Body types come from `compute_oem_stats.segment_mix` for each OEM. If either OEM's `segment_mix` is empty, that column renders `—`.

If both OEMs have empty `segment_mix`, omit the section entirely.

---

## EV per-make breakdown (when at least one OEM is legacy with non-zero EV)

```
**EV per-make breakdown:**

| OEM    | Make    | EV sold     | EV ASP     |
|--------|---------|-------------|------------|
| <ticker_A> | <make>  | <ev_sold>   | $<ev_asp>  |
| <ticker_B> | <make>  | <ev_sold>   | $<ev_asp>  |
```

For pure-play OEMs, all volume IS EV — render their entire `headline.sold_count_total` and `headline.weighted_avg_sale_price` in this table with make = the single make name (e.g., Tesla).

Omit the section when both OEMs have `ev_block.shape == "omitted"`.

---

## Pair-trade thesis (always — exactly 2 sentences)

**Fixed shape — exactly 2 sentences:**

1. **Cohort positioning.**
   `<ticker_A> leads on <metric_where_A_wins>; <ticker_B> leads on <metric_where_B_wins>.`

   Pick the metric where each ticker has the clearest advantage from the KPI table. If both metrics from the same ticker show advantage, prefer the verdict-driving slot (Days Supply or Market Share).

2. **Implication.**
   `<ticker_with_stronger_composite> has the cleaner operational read this month; consider <directional implication — e.g., "long <strong> / short <weak> on margin expansion thesis" OR "watch <weak> into the print for inventory writedown risk">.`

Halt with explicit pair-trade language **only when one ticker is clearly bullish and the other clearly bearish or mixed**. If both verdicts are NEUTRAL, render: *"Both OEMs read NEUTRAL this month; no operational basis for a pair trade — wait for earnings."*

**Anti-patterns (DO NOT do):**
- No specific dollar EPS forecasts.
- No price targets.
- No "buy / sell / hold" recommendation framing — keep the language *operational read* / *thesis*.

---

## Data Quality Notes (OPTIONAL — render when dq_events is non-empty)

Combine `dq_events` from both `compute_oem_stats.py` runs (deduplicate by ticker prefix).

Common W2 events:
- (c) Either ticker resolved via fuzzy match.
- (d) Active-inventory stats absent on one or more makes.
- (e) Days-Supply caveat (always).
- (g) Target ticker's makes absent from top-25.
- (k) EV block omitted for one OEM.

If empty, omit the section.

---

## Footer (always)

```
✓ Verified: both profiles, market-share parity, days-supply caveats, no MoM (single-snapshot).
```

---

## Self-check items (model runs silently — DO NOT render the checkbox grid)

1. Profile loaded; `country == "US"`.
2. Both inputs resolved to OEM tickers OR brand-orphans (different from each other).
3. Same-ticker halt fired BEFORE any MCP call if both inputs resolved to the same ticker.
4. Date windows: current_month only (no prior_month or baseline_3mo used in W2).
5. Every `get_sold_summary` call set `inventory_type` explicitly.
6. `compute_oem_stats.py` ran twice (once per OEM).
7. `aggregate_signals.py` ran twice (once per OEM).
8. Winner column applied direction rules correctly (higher-better vs lower-better per metric).
9. Pair-trade thesis is exactly 2 sentences.
10. Days Supply footnote rendered.
11. No MoM column rendered (W2 is single-snapshot by design).
