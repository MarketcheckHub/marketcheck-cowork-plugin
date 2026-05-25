---
name: w3-market-share-leaderboard
description: Workflow 3 — Top-N US OEM market-share leaderboard for the most recent complete calendar month. Single MCP call; per-make rollup to ticker via the 13-row OEM map.
type: reference
---

# W3 — US OEM Market Share Leaderboard

Triggered by "top 5 US OEMs by volume", "biggest OEMs this month", "US OEM market share leaderboard", "rank the top OEMs". Distinct from W1's market-share-context section (which is just one section of a single-OEM report) — W3 is the cohort-wide leaderboard with ticker rollup.

## Required inputs

| Input | Source | Required? |
|---|---|---|
| Top N (1 ≤ N ≤ 10) | User prompt | Yes — default 5 if unspecified |
| Inventory type (New or Used) | User prompt | Optional — default New |
| Profile (country) | `marketcheck-profile.md` | Read for country gate |

## Pre-flight (no MCP calls — local only)

1. Read `marketcheck-profile.md`. Halt if `country != US`.
2. Run `compute_month_windows.py --today <currentDate>`. Capture `current_month`. (Prior month and baseline not used by W3.)
3. Determine N: parse from user prompt; default to 5 if unspecified.
4. **N > 10 halt:** if `N > 10`, halt with:
   *"This skill caps W3 at top 10 OEMs (the underlying call returns top-25 makes; we roll up to ~10-12 distinct tickers + a handful of brand-orphan rows). For broader lists, run multiple W3 invocations with different inventory_type or use W1 per ticker."*
5. Determine `inventory_type`: ask the user "New or Used?" if unspecified; default New. The single sold-summary call uses this verbatim.

## Wave A — single call (no waves needed)

| # | Tool | Purpose |
|---|---|---|
| W3.A1 | `get_sold_summary` | Top-25 makes by sold_count, current month, user-chosen inventory_type |

```python
get_sold_summary(
    # NO make filter — we want the full top-25 leaderboard
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

→ Returns ~1,325 rows.

Pipe through:
```bash
Write(file_path="/tmp/marketcheck/<session-id>/market_current.json", content=<response>)
python scripts/parse_sold_summary.py --aggregate-by-dimension make \
  --file /tmp/marketcheck/<session-id>/market_current.json
```

Captures `dimension_values: [{value, total_sold_count, weighted_avg_sale_price, weighted_avg_days_on_market, share_pct, ...}, ...]` sorted desc by sold_count.

**W3 total: 1 MCP call.**

## After Wave A — pipe parser output to `compute_w3_rollup.py`

The rollup, ticker bucketing, share % computation, split-ticker footnotes, cohort medians, and the cohort observation are ALL emitted deterministically by `scripts/compute_w3_rollup.py`. No model-side computation.

```bash
# Assuming the parser output is in <parser-output>
echo '<parser-output>' | jq '{dimension_values}' | \
  python scripts/compute_w3_rollup.py --top-n <N>
```

Or piped fully:

```bash
echo '<sold-summary-response>' | \
  python scripts/parse_sold_summary.py --aggregate-by-dimension make | \
  jq '{dimension_values}' | \
  python scripts/compute_w3_rollup.py --top-n <N>
```

(If the sold-summary response was persisted by the runtime, use `--file <path>` on `parse_sold_summary.py` and pipe through `jq` as above.)

**`compute_w3_rollup.py` output shape** (see `references/script-contracts.md §compute_w3_rollup`):
- `leaderboard[]` — top-N tickers with `{rank, ticker, company_name, makes, makes_in_top25, makes_outside_top25, sold_count, share_pct, avg_asp, avg_dom}`. `share_pct` is computed against the cohort total (sum of ALL top-25 makes' sold).
- `cohort_headline` — `{top_ticker, top_company_name, top_sold, top_makes_count, median_asp, median_dom, observation}`. **`observation` is a single deterministic sentence** picked by the script's three-tier rule:
  - Rule A (priority): top-2 share ≥ 50% of cohort → "The top 2 OEMs (`X`, `Y`) account for Z% of the top-N cohort volume."
  - Rule B: span ratio > 5× → "The cohort spans X× from #1 (Y units) to #N (Z units)."
  - Rule C (default): "All N OEMs in the top-N are publicly traded with US listings."
- `split_ticker_footnotes[]` — one rendered sentence per ticker whose makes are partially outside the top-25.
- `dq_events[]` — including DQ event (j) for brand-orphan makes that didn't roll up to any ticker.

W3 deliberately does NOT compute `aggregate_signals` per row — no MoM data, no per-row verdicts.

## Render

Use `assets/w3-output-template.md`. Render the leaderboard table with per-row formatting per the template (commas, $-signs, decimal precision, ticker rollup, split-ticker footnote, dropped-tickers footnote).

## Wall-clock budget (W3)

- Pre-flight: ~1s.
- Wave A: ~6-10s (single call; smaller payload than W1/W2's parallel batches).
- Post-Wave-A: ~1s (parse + ticker rollup + slice + median computation).
- **Total ≈ 8–12s common path.**

## Edge cases

- **Top OEM has only some makes in the top-25.** Example: Stellantis has 7 makes; if only Jeep, Ram, Chrysler appear in the top-25 (the other 4 below the cutoff), STLA's aggregate UNDERSTATES its true share. Footnote logged via DQ event (g); template renders an asterisk + footnote.
- **Brand-orphan dominant in top-N.** If Subaru / Mazda / Mitsubishi take ranks #6-#8, those rows render with `ticker = "—"`. The cohort-headline observation may note "X non-mapped (private / non-US-listed) makes in top-N."
- **Empty response.** If `get_sold_summary` returns zero rows for the chosen month/inventory_type → render: *"No sold-volume data for `<inventory_type>` in `<current_month.label>`. The most-recent-complete-month aggregates may still be propagating upstream — try again tomorrow."*
- **User asks "top 12"** (or any N > 10) → halt with the cap explanation in pre-flight step 4.
- **User asks "top 1"** → render a single-row leaderboard with the leading ticker. Cohort observations may be terse (no top-2 share clause; spread ratio is undefined).

## DQ event triggers in W3

- **(a)** A.1 call returned an error → halt with the error message; W3 has no fallback (single-call workflow).
- **(b)** Truncation envelope unwrap (rare at top_n=25 with limit=5000; ~1,325 rows expected).
- **(g)** Split-ticker (some of a ticker's makes outside top-25) OR dropped tracked ticker (tracked ticker's makes entirely absent) → log per-occurrence; render the relevant footnote.

## What W3 deliberately does NOT do

- **No per-row verdicts** (BULLISH/BEARISH/etc.). No `aggregate_signals.py` invocation. Verdict-based ranking routes to W1 per ticker.
- **No active inventory.** Adding active-inventory calls would 1+N the call count (one per ticker × per make). Out of W3's snapshot scope.
- **No MoM deltas.** W3 fires only one sold-summary call (current month). Adding MoM would require a second prior-month call → would double the cost and overlap with W1.
- **No EV transition trends.** Same reason — no historical comparison call. Pure-play tickers (TSLA, RIVN, LCID) appear in the leaderboard ranked by total sold but with no EV-specific framing.
- **No per-make-within-ticker breakdown in the leaderboard rows.** The leaderboard summarizes by ticker; the "Makes" column lists the contributing makes inline (e.g., "Ford, Lincoln" for F). Detailed per-make analysis routes to W1.
