# W3 Output Template — Top-N Dealer Group Leaderboard

Single-call leaderboard of dealer groups by sold-vehicle volume in the most
recent complete calendar month. **No per-row signal verdicts** — leaderboard
role only (verdict aggregation is W1 / W2's job).

---

## First line (always)

```
Top <N> dealer groups by <inventory_type> sold volume — <current_month.label>
```

Where `<inventory_type>` is the user-chosen value (Used or New); default Used.

---

## Cohort headline (always — 1 sentence)

```
<top_group> leads with <top_sold_count> units sold; the cohort median ASP is $<median_asp>, median DOM <median_dom> days. <one observation about cohort spread>.
```

The observation is one of:
- "The top 2 groups (`<top1>`, `<top2>`) account for <pct>% of cohort volume." (when top-2 share is meaningful)
- "The cohort spans <ratio>× from #1 (<n1> units) to #N (<nN> units)." (when ratio > 5)
- Otherwise, a brief note on the volume distribution.

---

## Leaderboard table (always)

```
| Rank | Ticker | Group                       | Sold count | Avg ASP | Avg DOM | Efficiency |
|------|--------|------------------------------|-----------:|--------:|--------:|-----------:|
| 1    | KMX    | Carmax                      | 11,500     | $24,800 | 38.0    | 302.6      |
| 2    | CVNA   | Carvana                     | 4,000      | $24,290 | 28.95   | 138.2      |
| 3    | AN     | AutoNation Inc.             | 2,900      | $28,000 | 51.0    | 56.9       |
...
```

**Formatting rules (same as W1/W2):**
- Sold count: integer with thousands separator.
- ASP: `$` prefix, no decimal places, thousands separator.
- DOM: 1-2 decimal places + " days" implied.
- Efficiency: 1 decimal place.
- Ticker column: empty string for canonical names not in the 8-name public ticker map.
- Rank column: 1 to N where N is the user-requested top-N (≤ 20).

---

## Public-private split (OPTIONAL when N ≥ 5)

```
**Public-traded names in the top <N>:** <list of tickers + ranks>
**Private dealer groups in the top <N>:** <count>
```

This frames the leaderboard for the equity-analyst persona — it's important whether the leaderboard is dominated by Carvana/Carmax or by private operators.

---

## Data Quality Notes (OPTIONAL)

Same as W1's DQ block. Common W3 events:
- (b) Truncation envelope unwrap (if the 20-group response truncated; rare at top_n=20).
- (j) User requested N > 20 → halted with cap explanation; this template renders the top 20 cohort instead.

---

## What W3 deliberately does NOT render

- **Per-row BULLISH/BEARISH/NEUTRAL/MIXED verdicts.** That's W1/W2 territory; W3 has no MoM data to anchor on. Verdict-based ranking should route to `group-benchmarking` (sibling skill) or to a W1 invocation per ticker.
- **MoM deltas.** W3 fires only one sold-summary call (current month). Adding MoM would require a second prior-month call per group → would explode cost and overlap with `group-benchmarking`.
- **Days Supply.** Without a per-group active-inventory call, Days Supply isn't computable. Route to W1 for individual-group inventory health.

---

## Footer (always)

```
✓ Verified: leaderboard scope, top-N slicing, public-private split.
```
