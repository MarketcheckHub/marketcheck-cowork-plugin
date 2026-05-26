# W3 Output Template — US OEM Market Share Leaderboard

Single-call leaderboard of US OEMs by sold-vehicle volume in the most
recent complete calendar month. **No per-row signal verdicts** —
leaderboard role only. Verdict aggregation is W1's job.

---

## First line (always)

```
Top <N> US OEMs by <inventory_type> sold volume — <current_month.label>
```

Where:
- `<N>` is the user-requested top-N (1-10; default 5).
- `<inventory_type>` is the user-chosen channel ("New" by default; "Used" on explicit override).

---

## Cohort headline (always — 1 sentence)

```
<cohort_headline.top_ticker> (<cohort_headline.top_company_name>) leads with <cohort_headline.top_sold> units sold across <cohort_headline.top_makes_count> makes; the cohort median ASP is $<cohort_headline.median_asp>, median DOM <cohort_headline.median_dom> days. <cohort_headline.observation>
```

Every field above is emitted by `scripts/compute_w3_rollup.py`. The `observation` is a single deterministic sentence picked by the script's three-tier rule (Rule A: top-2 share ≥ 50% → Rule B: span > 5× → Rule C: public-listing default). The template renders verbatim — no model-side selection.

---

## Leaderboard table (always)

```
| Rank | Ticker  | Company                  | Makes                          | Sold count    | Share % | Avg ASP     | Avg DOM     |
|------|---------|--------------------------|--------------------------------|---------------|---------|-------------|-------------|
| 1    | TM      | Toyota Motor Corporation | Toyota, Lexus                  | 198,500       | 21.0%   | $35,200     | 62.3 days   |
| 2    | F       | Ford Motor Company       | Ford, Lincoln                  | 124,500       | 13.2%   | $48,200     | 84.2 days   |
| ...one row per ticker in user's top-N (≤ 10)... |
```

**Per-cell formatting rules:**
- Rank: integer 1 to N.
- Ticker: render verbatim (e.g., `F`, `GM`, `TSLA`).
- Company: render full company name from ticker-mapping.md.
- Makes: comma-separated list. If only SOME of a ticker's makes appeared in the top-25 underlying response, append a footnote marker: `Ford, Lincoln*` and render the split-ticker footnote below.
- Sold count: thousands-separated integer.
- Share %: 2-decimal percentage. Share computed against the SUM of all top-25 makes (post-rollup-by-ticker).
- Avg ASP: `$` prefix, no decimals, thousands separator. Sold-count-weighted average of the ticker's makes' ASPs.
- Avg DOM: 1-decimal + " days". Sold-count-weighted average.

---

## Split-ticker footnote (when at least one ticker had makes outside the top-25)

```
> * <ticker_X>'s <make_Y> fell outside the top-25 leaderboard this month; <ticker_X>'s aggregate volume understates true volume by an unknown amount.
> * <ticker_Z>'s <make_W>, <make_Q> fell outside the top-25 leaderboard this month; aggregate volume similarly understated.
```

One bullet per affected ticker. Log DQ event (g) for each.

If all makes for all tickers in the top-N are accounted for in the top-25, omit the footnote.

---

## Dropped-tickers footnote (when tracked tickers from profile are absent from the top-25)

```
> Note: <comma-separated tickers from analyst.tracked_tickers> are tracked in your profile but did not appear in the current-month top-25 makes (their makes fell below the cohort cutoff).
```

If the user's profile has `tracked_tickers` set AND any of those tickers' makes are NOT in the top-25 response, render this footnote. Log DQ event (g) per missing ticker.

Skip this footnote when no profile tracked_tickers OR when all tracked tickers' makes are in the top-25.

---

## Public-private split (OPTIONAL when N ≥ 5)

```
**Public-traded tickers in the top <N>:** <list of tickers + ranks>
**Non-mapped makes in the top <N>:** <count of makes belonging to no OEM ticker> (e.g., Subaru, Mazda, Mitsubishi) — render as orphan rows in the leaderboard (ticker column shows `—`, company column shows the make name).
```

This frames the leaderboard for the equity-analyst persona — it's important whether the top-N is dominated by tracked OEMs (TM, F, GM, etc.) or by non-mapped brands (Subaru, Mazda) that would route to W1's brand-orphan path.

---

## Data Quality Notes (OPTIONAL — render when dq_events is non-empty)

Common W3 events:
- (a) Single MCP call returned an error.
- (b) Truncation envelope unwrap (rare at top_n=25 with limit=5000; 1,325 rows expected).
- (g) Split-ticker (per the footnote above) and/or dropped tracked tickers.

If empty, omit.

---

## Footer (always)

```
✓ Verified: leaderboard scope (top-25 underlying makes), ticker rollup, split-ticker footnotes.
```

---

## What W3 deliberately does NOT render

- **Per-row BULLISH/BEARISH/NEUTRAL/MIXED verdicts.** That's W1/W2 territory; W3 has no MoM data to anchor on. Verdict-based ranking should route to W1 per ticker.
- **MoM deltas.** W3 fires only one sold-summary call (current month). Adding MoM would require a second prior-month call → would double the cost and overlap with W1.
- **Days Supply.** Without per-make active-inventory calls, Days Supply isn't computable. Route to W1 for individual-ticker inventory health.
- **EV transition.** Not part of leaderboard scope. Pure-play tickers (TSLA, RIVN, LCID) appear in the leaderboard ranked by total sold but with no EV-specific framing.

---

## Self-check items (model runs silently — DO NOT render the checkbox grid)

1. Profile loaded; `country == "US"`.
2. N parsed from user input; clamped to 1 ≤ N ≤ 10 (skill cap; underlying call returns top-25 makes).
3. `inventory_type` set explicitly ("New" default; "Used" on user override).
4. Single `get_sold_summary` call fired with `ranking_dimensions=make, top_n=25, no make filter, limit=5000`.
5. Per-make response rolled up to tickers via the 13-row OEM map.
6. Split-ticker footnote rendered when any mapped ticker's makes spanned in/out of top-25.
7. Dropped-tickers footnote rendered when profile tracked_tickers absent from top-25.
8. No verdict / band rendering anywhere (no MoM, no `aggregate_signals` invocation).
