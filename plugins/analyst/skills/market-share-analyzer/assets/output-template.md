# Output Template — Market Share Analyzer (Analyst)

This file is the **single source of truth** for output block structure,
table schemas, period-comparison wording, ticker-overlay rules, and the
internal self-check across all 5 workflows (W1 Brand Share / W2 Segment
Conquest / W3 Dealer-Group Benchmarking / W4 EV Penetration / W5
Regional Exposure Heatmap).

Placeholders in angle brackets `<...>` are interpolated from `compute_*.py`
+ `aggregate_signals.py` outputs (the per-workflow JSON the agent reads).
Optional blocks are marked `(OPTIONAL)` and only render when their
precondition holds.

**Naming convention.** Lowercase placeholders like `<top_ticker>`,
`<current_share_pct>` reference fields on the compute / aggregate output
objects — pull the exact numeric value verbatim. Uppercase labels like
`<TICKER>` are user-facing render tokens (the ticker symbol).

---

## First two lines (always)

```
Using profile: <user.name or user.company>, <focus>, US national or <state>
Period: <period_label>     # e.g. "March 2026 vs February 2026" or "Q1 2026 vs Q4 2025"
```

When no profile is loaded:

```
No profile context — running in <state or US national> anonymous mode.
Period: <period_label>
```

---

## Headline (always — leads every workflow)

One sentence with the investment-signal punchline. Lead with the ticker
verdict + bps shift / leader / penetration rate / concentration. Per-
workflow phrasing examples:

- **W1**: *"TM holds 14.2% national share in March 2026, up 35 bps from
  February — BULLISH on revenue trajectory. HYMTF is the biggest gainer
  at +52 bps; STLA is the biggest loser at −41 bps."*
- **W2**: *"In the SUV segment, TM leads at 33.7% on 14,000 units —
  BULLISH; HMC sits at #2; STLA's Jeep volume gapped down −85 bps,
  BEARISH for STLA's gross-profit pool."*
- **W3**: *"AN leads dealer-group volume with 21,000 units; LAD moves
  units 10 days faster on average — operational moat for the LAD thesis;
  KMX (used-only) continues to gain absolute volume in the cohort."*
- **W4**: *"EVs represented 9.87% of national new-vehicle sales in
  March 2026, up 106 bps from February. Hybrids 4.48%; combined
  electrified rate 14.35%. TSLA absolute EV volume +12% even as TSLA EV
  share dropped 320 bps — NEUTRAL on the absolute, CAUTION on the share."*
- **W5**: *"For TM (Toyota RAV4), Texas leads with 24.2% of national
  volume at $31,000 (0.99× national average). Top-3 states 48% — NEUTRAL
  concentration; diversified national footprint."*

The headline reads from the `aggregate_signals.tickers[0]` (top by
current_sold_count) for W1/W2/W4, from `compute_dealer_group_leaderboard.
top_volume / top_efficiency` for W3, and from `aggregate_signals.tickers[0]`
+ `concentration_top3_pct` for W5.

---

## Main table (always — rendered via `render_share_table.py`)

Each workflow has its own canonical rendered table. Read them from the
renderer's stdout — copy verbatim into the report.

| Workflow | `--mode` | Columns |
|---|---|---|
| W1 | `brand-share` | Rank \| Make \| Current Sold \| Current Share % \| Prior Sold \| Prior Share % \| Share Change \| Volume Change \| Trend |
| W2 | `segment-conquest` | Rank \| Make \| Model \| Sold Count \| Segment Share % \| Prior Share % \| Share Change |
| W3 | `dealer-group-leaderboard` | Rank \| Dealer Group \| Sold Count \| Market Share % \| Avg DOM \| Avg Sale Price \| Efficiency Score |
| W4 | `ev-penetration` | (summary lines + Top EV Models + Top Hybrid Models tables) |
| W4 | `ev-brand-share` | Make \| EV Units \| Brand Total \| % of Brand Sales That Are EV |
| W5 | `regional-heatmap` | Rank \| State \| Sold Count \| % of National \| Avg Sale Price \| Price vs National \| Avg DOM |

**Bps formatting.** `share_change_bps` cells render as `+42 bps` /
`−189 bps` (U+2212 minus, integer rounded). Never render bps as a
percentage point ("+0.42%") — that defeats the purpose of basis points.

**Money formatting.** `$28,500` (US). Comma thousands; no decimals.

**Trend column.** Renders the literal string from
`compute_brand_share.makes[*].trend`: `GAINING`, `LOSING`, or `STABLE`.
The renderer doesn't add color or icons. (This is the per-make trend
classification; the per-ticker verdict band lives in the Ticker Impact
Summary block.)

**No user-brand bolding.** The analyst plugin has no
`dealer.franchise_brands` field. The `--user-brand` flag on
`render_share_table.py` is unreachable from this skill's flow.

---

## Ticker Impact Summary (always — rendered inline from `aggregate_signals.tickers`)

The defining analyst-skill block. After the per-make table, render a
per-ticker rollup table. Schema per workflow:

| Workflow | Ticker block schema |
|---|---|
| W1 | Ticker \| Makes \| Current Volume \| Current Share % \| Share Change \| Volume Change \| Verdict |
| W2 | Ticker \| Makes in Segment \| Current Sold \| Current Share % \| Share Change \| Verdict |
| W3 | Ticker \| Group Name \| Current Volume \| Current Share % \| Avg DOM \| Avg Sale Price \| Efficiency Score \| Verdict |
| W4 | Ticker \| EV Units \| Brand Total \| % EV Mix \| Verdict |
| W5 | Ticker \| Concentration (top-3) \| Top State \| Volume Share % \| Verdict \| Reason |

**Verdict rendering.** The Verdict column shows one of `BULLISH /
BEARISH / NEUTRAL / CAUTION` verbatim. Tickers in
`aggregate_signals.headline_rollup.tracked_signals` (i.e. the user's
tracked cohort) get a `★` prefix in the Ticker column.

**Sorting.** Tickers sorted by `current_sold_count` desc by default; for
W4 sort by `ev_units` desc.

**Empty Verdict.** When `aggregate_signals.tickers` is empty (no makes
in the response mapped to any ticker), render *(no tracked OEM tickers
in the response — see Data Quality Notes)* and emit DQ event (d).

---

## Tracked-ticker movement narrative (OPTIONAL — only when tracked_signals non-null)

When the user's profile has `analyst.tracked_tickers`, the skill renders
a one-liner per tracked ticker after the Ticker Impact Summary table:

```
Tracked tickers this period:
  ★ <TICKER1>: <verdict> (<share_change_bps>, <volume_change_pct>) — <verdict_reason>
  ★ <TICKER2>: <verdict> (<share_change_bps>, <volume_change_pct>) — <verdict_reason>
  ...
```

When a tracked ticker has no rows in the response (sub-top-50 share),
render:
```
  ★ <TICKER>: NEUTRAL — not in top-50 makes for the period (share too small to classify).
```

---

## Sub-blocks (per-workflow)

### W1 — Top gainers / losers (ticker-level)

Always after the Ticker Impact Summary table:

```
Top 3 ticker gainers this period:  <ticker1>, <ticker2>, <ticker3>
Top 3 ticker losers this period:   <ticker1>, <ticker2>, <ticker3>
```

Per-make gainers/losers (from `compute_brand_share.summary.top_3_gainers
/ top_3_losers`) optionally rendered as a one-line footnote when the
analyst asked for per-make detail.

### W2 — Conquest insight (always when fastest_gainer non-null)

```
<fastest_gainer_ticker> (<fastest_gainer.make> <fastest_gainer.model>)
gained the most ground at <fastest_gainer.share_change_bps>.
Tracked-ticker segment-exposure: <list of tracked tickers and their
per-segment current share %>.
```

### W3 — Top-volume vs top-efficiency contrast (always)

```
<top_volume_ticker> wins on raw scale, but <top_efficiency_ticker>
moves units <X> days faster on average — operational moat for the
<top_efficiency_ticker> thesis.
```

`<X>` is `top_volume.avg_dom − top_efficiency.avg_dom`, computed at
render time from the leaderboard rows.

### W4 — Period trend paragraph + TSLA-vs-legacy narrative

After the penetration block + Top EV/Hybrid Models + EV brand-share
table:

1. **Period trend paragraph**:
   *"EV penetration <accelerated|plateaued|slowed> from <prior_pct>% to
   <current_pct>% (<bps_signed>). EV unit volume <up|down> by
   <volume_change>%."*

   Choose `accelerated|plateaued|slowed` based on `deltas.ev_pct_change_bps`:
   - `> +50 bps` → "accelerated"
   - `−50 ≤ bps ≤ +50` → "plateaued"
   - `< −50 bps` → "slowed"

2. **TSLA-vs-legacy narrative** (always):
   *"For TSLA: <tsla_share>% of EV market (<tsla_share_change_bps>);
   absolute volume <up|down> <tsla_volume_pct>% — <tsla_verdict>. For
   legacy OEMs: <legacy_ticker> at <legacy_ev_pct>% EV mix
   (<legacy_share_change_bps>) — <legacy_verdict>."*

### W5 — Top markets paragraph + bottom growth markets

```
Top <top_n> markets by volume: <top_volume_states>.
Bottom <top_n> markets (potential growth): <bottom_growth_markets>.
Concentration index: top-3 states account for <top3_pct>% of national
volume — <concentration_verdict>.
```

When the user supplies `--model`, prepend "For <ticker> (<make>
<model>), ..."; otherwise "For <ticker> (<make>), ...".

---

## Investment Thesis (always — sourced from `references/outcomes.md`)

End every workflow with a 2-4 sentence Investment Thesis block tailored
to the analyst's `focus`. Use the scenario routing in
`references/outcomes.md` (see §Workflow → scenario routing). When
`focus` is unset, default to the workflow's default scenario.

| Workflow | Default scenario | Focus-bias override |
|---|---|---|
| W1 | Scenario 5 (Watchlist Monitor) | `oem` → 1; `dealer_groups` → 3 |
| W2 | Scenario 4 (Sector Strategist) | `oem` → 1; `ev_transition` → fold W4 |
| W3 | Scenario 3 (Public Dealer-Group Analyst) | (no change for `dealer_groups`); `general` → 5 |
| W4 | Scenario 2 (EV-Cohort Analyst) | `ev_transition` → 2; `oem` → 1 + 2 layered |
| W5 | Scenario 4 (Sector Strategist) | `oem` → 1 + state-concentration line |

Phrasing rules (also in `outcomes.md`):
- Lead with the verdict for the tickers in scope.
- Quantify the move (bps, volume %, units-equivalent via 100 bps ≈
  15-17K annual units).
- Anchor on a concrete catalyst when known; default to "the upcoming
  quarter" otherwise.
- Avoid EPS / price-target language — operational signal, not equity
  forecasting.

---

## Data Quality Notes (OPTIONAL — only when the event log is non-empty)

Use the typed prefix (a) – (g) per the SKILL.md taxonomy:

```
Data Quality Notes
- (a) MCP tool <tool_name> returned <error_type>; recovery: <path>.
  Follow-up: if recurring, escalate.
- (a1) Facet-discovery retry: <original_make> → <resolved_make> on get_sold_summary.
  Follow-up: cache the resolved casing for the session.
- (b) Truncation envelope unwrap via --file (rare on get_sold_summary; always log when fired).
- (d) Make `<make>` has no tracked ticker; excluded from Ticker Impact Summary.
  Follow-up: review references/ticker-mapping.md if make should be added.
- (e) Share computed over visible top-50 makes; long-tail (~2-5% of national volume) excluded.
  Follow-up: per-ticker share figures may be understated by an equivalent amount.
- (e) Per-state response capped at top_n=50 in regional heatmap; rare states with > 50 model rows may be under-counted.
- (f) Parameter adaptation: passed <used> in place of <preferred> (e.g. ranking_dimensions=make after dimension_limit error).
- (g) Workflow branch skipped by design: <branch_name> — <reason>. Examples:
    - "Quarterly aggregation skipped: user supplied a single-month period."
    - "Dual-period heatmap skipped: --prior not supplied."
    - "W3 New pass skipped: user requested Used only."
    - "Tracked-ticker callouts skipped: profile has no analyst.tracked_tickers."
```

If the event log is empty, **omit this section entirely** — do not
render an empty header.

---

## Source line (always — last data line before the self-check footer)

```
Source: MarketCheck sold-summary, <period_label>, <state or "US national">, <inventory_type>.
```

For multi-pass W3 (`Used + New`): render two source lines, one per pass.

---

## Self-check (internal — never render as a grid)

The 14-item verification checklist. Run each item silently before
returning the response. Render only the footer line.

1. **Profile loaded OR explicit "no profile context" line emitted** on
   the first line.
2. **Country routing applied.** `US` → workflows below; `UK` / `CA` /
   any other → halt with the `references/country-uk.md` message before
   any MCP call.
3. **Geography + period stamped on the first two lines** (state-or-
   national + `<period_label>`).
4. **`inventory_type` set explicitly on every `get_sold_summary` call.**
   Never omitted (default `"New"` silently).
5. **`limit=5000` on every call.** Never default 1000 (silent multi-dim
   truncation).
6. **`ranking_dimensions` minimal per workflow.** W1=`make`,
   W2=`make,model`, W3=`dealership_group_name`, W4 per-fuel=`make,model`,
   W4 total=`make`, W5=`make,model`. Never default 3-dim
   `make,model,body_type`.
7. **`summary_by="state"` set explicitly** on every call.
8. **`dealer_type` never set** (silent data suppression).
9. **`date_from` / `date_to` month-aligned via
   `compute_period_window.py` (W1/W2/W4/W5) or
   `compute_sold_summary_dates.py` (W3).** First-of-month start, last-
   of-month end. Never `today` as `date_to`.
10. **Comparison period present** for W1, W2, W4. Single-period
    snapshots are not allowed for those three workflows. (W3 is
    current-period only by design; W5 is current-period default.)
11. **Share change rendered in basis points (`bps`)**, not percentage
    points. A move from 14.2% to 14.5% is `+30 bps`, never `+0.3%`.
12. **Volume + share % both shown** in every per-make / per-model row of
    the rendered table. Raw counts without context are meaningless;
    percentages without counts lack scale.
13. **Ticker Impact Summary block rendered.** Every workflow surfaces a
    per-ticker rollup with BULLISH / BEARISH / NEUTRAL / CAUTION
    verdicts. When `analyst.tracked_tickers` is set, the tracked cohort
    is called out with the `★` prefix.
14. **Compute + aggregate pipeline executed.** `parse_sold_summary.py`
    × N → `compute_<workflow>.py` → `aggregate_signals.py` →
    `render_share_table.py`. Hand-computed shares / efficiency /
    penetration / verdict values fail this check. When bypassed, prefix
    the report with `⚠ pipeline bypassed; numeric blocks computed by
    hand — values may diverge from canonical output`.
15. **Data Quality event log surfaced** when non-empty; omitted when
    empty.

(Item count: 15 — kept odd-numbered for easy "list of 15" verification.)

Render rule at response time:

- **All applicable checks pass** → emit a single footer line listing 5-7
  of the items that were exercised, e.g.:
  `✓ Verified: profile, US-only routing, sold-summary safety (limit=5000, inventory_type set), month-aligned dates, ticker rollup, verdict band consistent.`
- **Any check fails** → emit failures only, one per line, prefixed `⚠`,
  with a one-line note on what was corrected or caveated in the output
  to compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox
  grid.

---

## Render variations — which blocks per workflow

| Block                              | W1 | W2 | W3 | W4 | W5 |
|---|---|---|---|---|---|
| First-line profile/scope            | ✓  | ✓  | ✓  | ✓  | ✓  |
| Period stamp                        | ✓  | ✓  | ✓  | ✓  | ✓  |
| Headline                            | ✓  | ✓  | ✓  | ✓  | ✓  |
| Main table                          | ✓ (brand-share) | ✓ (segment-conquest) | ✓ (dealer-group) | ✓ (penetration) | ✓ (heatmap) |
| EV brand share table                | —  | —  | —  | ✓  | —  |
| Ticker Impact Summary               | ✓  | ✓  | ✓  | ✓  | ✓  |
| Tracked-ticker movement narrative   | ✓ (when applicable) | ✓ (when applicable) | ✓ (when applicable) | ✓ (when applicable) | ✓ (when applicable) |
| Top gainers/losers (ticker-level)   | ✓  | —  | —  | —  | —  |
| Conquest insight                    | —  | ✓ (when fastest_gainer non-null) | — | — | — |
| Top-volume vs top-efficiency        | —  | —  | ✓  | —  | —  |
| Period trend paragraph              | —  | —  | —  | ✓  | —  |
| TSLA-vs-legacy narrative            | —  | —  | —  | ✓  | —  |
| Top / bottom states paragraph       | —  | —  | —  | —  | ✓  |
| Investment Thesis                   | ✓  | ✓  | ✓  | ✓  | ✓  |
| Data Quality Notes                  | ✓ (if non-empty) | ✓ | ✓ | ✓ | ✓ |
| Source line                         | ✓  | ✓  | ✓  | ✓  | ✓  |
| Self-check footer                   | ✓  | ✓  | ✓  | ✓  | ✓  |

---

## Money / percentage / bps formatting

| Field type | Format | Example |
|---|---|---|
| Volume (sold count) | comma thousands, no decimals | `32,000` |
| Share %             | 2 decimals  | `14.23%` |
| Volume Change %     | 1 decimal, signed (U+2212 minus on negatives) | `+6.7%`, `−16.7%` |
| Share Change (bps)  | integer, signed (U+2212 minus on negatives) | `+42 bps`, `−189 bps` |
| Avg DOM             | 1 decimal | `38.5` |
| Avg Sale Price      | $ prefix, comma thousands, no decimals | `$31,857` |
| Efficiency Score    | 1 decimal | `528.8` |
| Price vs National   | 2 decimals + multiplier suffix | `1.03×`, `0.99×` |
| Top-3 concentration | 1 decimal + percent | `48.2%` |

The analyst plugin is US-only — UK currency / formatting is not used.
