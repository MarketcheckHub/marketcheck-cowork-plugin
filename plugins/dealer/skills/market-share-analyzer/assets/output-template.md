# Output Template — Market Share Analyzer

This file is the **single source of truth** for output block structure, table schemas, period-comparison wording, and the internal self-check across all 5 workflows (W1 Brand Share / W2 Segment Conquest / W3 Dealer Group Benchmarking / W4 EV Penetration / W5 Regional Heatmap).

Placeholders in angle brackets `<...>` are interpolated from `compute_*.py` outputs (the per-workflow JSON the agent reads). Optional blocks are marked `(OPTIONAL)` and only render when their precondition holds.

**Naming convention.** Lowercase placeholders like `<top_make>`, `<current_share_pct>` reference fields on the `compute_*.py` output objects — pull the exact numeric value verbatim. Uppercase labels like `<MAKE>` are user-facing render tokens (the make name as the user typed it or as it was facet-resolved).

---

## First two lines (always)

```
Using profile: <dealer.name>, <state or "national">, <country>
Period: <month YYYY> vs <prior month YYYY>     # e.g. "March 2026 vs February 2026"
```

When no profile is loaded:

```
No profile context — running in <state or national> anonymous mode.
Period: <month YYYY> vs <prior month YYYY>
```

---

## Headline (always — leads every workflow)

One sentence with the competitive punchline. Lead with the verdict + bps shift / leader / penetration rate. Examples per workflow:

- **W1**: *"Toyota holds 14.2% national market share in March 2026, up 35 bps from February. Honda is the biggest gainer at +52 bps."*
- **W2**: *"In the SUV segment, Toyota leads with 33.7% on 14,000 sold; Honda sits at #2, gap of 7,000 units to the leader."*
- **W3**: *"AutoNation Inc. leads dealer-group volume with 21,000 units; Lithia Motors moves units 10 days faster on average; Hendrick Automotive Group commands the highest average sale price at $34,143."*
- **W4**: *"EVs represented 9.87% of national sales in March 2026, up 106 bps from February. Hybrids were 4.48%; combined electrified rate 14.35%."*
- **W5**: *"For Toyota RAV4, Texas leads with 24.2% of national volume at $31,000 (0.99× national average). Under-penetrated large markets: Illinois, Pennsylvania, Georgia."*

The headline reads from `compute_*.py.summary` / `compute_*.py.leader` / `compute_*.py.current_period` / `compute_*.py.national` depending on workflow.

---

## Main table (always — rendered via `render_share_table.py`)

Each workflow has its own canonical rendered table. Read them from the renderer's stdout — copy verbatim into the report.

| Workflow | `--mode` | Columns |
|---|---|---|
| W1 | `brand-share` | Rank \| Make \| Current Sold \| Current Share % \| Prior Sold \| Prior Share % \| Share Change \| Volume Change \| Trend |
| W2 | `segment-conquest` | Rank \| Make \| Model \| Sold Count \| Segment Share % \| Prior Share % \| Share Change |
| W3 | `dealer-group-leaderboard` | Rank \| Dealer Group \| Sold Count \| Market Share % \| Avg DOM \| Avg Sale Price \| Efficiency Score |
| W4 | `ev-penetration` | (summary lines + Top EV Models + Top Hybrid Models tables) |
| W4 | `ev-brand-share` | Make \| EV Units \| Brand Total \| % of Brand Sales That Are EV |
| W5 | `regional-heatmap` | Rank \| State \| Sold Count \| % of National \| Avg Sale Price \| Price vs National \| Avg DOM |

**User-brand highlighting (W1, W2, W4 brand-share).** When the user's brand (from `profile.dealer.franchise_brands` or `--user-brand`) appears in the table, the renderer bolds the row's Make/Model cells (`**Toyota**`). This is a renderer-side concern; the agent does not re-bold.

**Bps formatting.** `share_change_bps` cells render as `+42 bps` / `−189 bps` (U+2212 minus, integer rounded). Never render bps as a percentage point ("+0.42%") — that defeats the purpose of basis points.

**Money formatting.** `$28,500` for US, `£18,250` for UK (UK is halted by this skill, but the renderer accepts `--currency '£'` for parity with the golden's UK path). Comma thousands; no decimals.

**Trend column.** Renders the literal string from `compute_brand_share.makes[*].trend`: `GAINING`, `LOSING`, or `STABLE`. The renderer doesn't add color or icons.

---

## Sub-blocks (per-workflow)

### W1 — Top gainers / losers / user-brand movement

Always after the brand-share table:

```
Top 3 share gainers this period:  <gainer1>, <gainer2>, <gainer3>  (collectively +<sum_bps> bps)
Top 3 share losers this period:   <loser1>, <loser2>, <loser3>     (collectively <sum_bps_signed>)
```

When `user_brand_movement` is non-null:

```
<user_brand> moved from #<prior_rank> to #<current_rank> (<bps_signed>).
```

When `user_brand_movement` is non-null but `prior_rank is None` (brand wasn't in top-N prior period):

```
<user_brand> entered the top-<top_n> at #<current_rank> this period (<bps_signed>) — wasn't ranked prior.
```

### W2 — Conquest insight (always when fastest_gainer non-null)

```
<fastest_gainer.make> <fastest_gainer.model> gained the most ground at <bps_signed>.
To recapture share, <user_brand> should focus on the model that competes directly with <fastest_gainer.model>.
```

When `--user-brand` is unset, drop the second sentence.

### W3 — Top-volume vs top-efficiency contrast (always)

```
<top_volume> wins on raw scale, but <top_efficiency> moves units <X> days faster on average.
Closing that DOM gap at <top_volume>'s scale would be a meaningful capital-efficiency win.
```

`<X>` is `top_volume.avg_dom − top_efficiency.avg_dom`, computed at render time from the leaderboard rows.

### W4 — EV brand share table + period trend paragraph

After the penetration block + Top EV/Hybrid Models, render:

1. **EV brand share table** (via `render_share_table.py --mode ev-brand-share`).
2. **Period trend paragraph**:
   *"EV penetration <accelerated|plateaued|slowed> from <prior_pct>% to <current_pct>% (<bps_signed>). EV unit volume <up|down> by <volume_change>%."*

Choose `accelerated|plateaued|slowed` based on `deltas.ev_pct_change_bps`:
- `> 50 bps` → "accelerated"
- `−50 ≤ bps ≤ 50` → "plateaued"
- `< −50 bps` → "slowed"

### W5 — Top markets paragraph + bottom growth markets

```
Top <top_n> markets by volume: <top_volume_states>.
Bottom <top_n> markets (potential growth): <bottom_growth_markets>.
```

When the user supplies `--model`, prepend "For <make> <model>, ..."; otherwise "For <make>, ...".

---

## Strategic Implications (always — sourced from `references/outcomes.md`)

End every workflow with a 2–4 sentence strategic-implications block tailored to the user's role. Use the action-to-outcome scenarios in `references/outcomes.md`:

| Workflow | Source scenario |
|---|---|
| W1 (brand share) | Scenario 1 (OEM brand manager) — focus on share gap concentration + segment-level recommendation |
| W2 (segment conquest) | Scenarios 1 + 4 + 5 — segment-level competitive dynamics + allocation + landscape narrative |
| W3 (dealer-group benchmarking) | Scenario 3 (dealer group CEO) — volume vs efficiency tradeoff |
| W4 (EV adoption) | Scenario 2 (analyst) — penetration trend + brand-share dynamics in EV |
| W5 (regional heatmap) | Scenario 4 (regional director) — under-allocated markets + cross-reference with segment data |

For OEMs: allocation recommendations, incentive targeting, segment gaps.
For dealer groups: competitive positioning, brand-mix optimization.
For analysts: trend narratives, inflection points, forecast implications.

---

## Data Quality Notes (OPTIONAL — only when the event log is non-empty)

Use the typed prefix (a) – (g) per the SKILL.md taxonomy:

```
Data Quality Notes
- (a) MCP tool <tool_name> returned <error_type>; recovery: <path>.
  Follow-up: if recurring, escalate.
- (a1) Facet-discovery retry: <original_make> → <resolved_make> on get_sold_summary.
  Follow-up: cache the resolved casing for the session; consider profile update.
- (b) Truncation envelope unwrap via --file (rare on get_sold_summary; always log when fired).
- (e) Share computed over visible top-50 makes; long-tail (~2-5% of national volume) excluded.
  Follow-up: numbers are slightly understated; rerun with top_n=100 if precision matters.
- (e) Per-state response capped at top_n=50 in regional heatmap; rare states with > 50 model rows may be under-counted.
- (e) State Baseline / channel-stats source unavailable for <reason>.
- (f) Parameter adaptation: passed <used> in place of <preferred> (e.g. ranking_dimensions=make after dimension_limit error).
- (g) Workflow branch skipped by design: <branch_name> — <reason>. Examples:
    - "Quarterly aggregation skipped: user supplied a single-month period."
    - "Dual-period heatmap skipped: --prior not supplied."
    - "User-brand highlighting skipped: profile has no franchise_brands."
```

If the event log is empty, **omit this section entirely** — do not render an empty header.

---

## Source line (always — last data line before the self-check footer)

```
Source: MarketCheck sold data, <period>, <state or "US national">, <inventory_type>.
```

Where `<period>` is the rendered period stamp (e.g. `March 2026 vs February 2026`) and `<inventory_type>` is `Used` / `New`.

---

## Self-check (internal — never render as a grid)

The 13-item verification checklist. Run each item silently before returning the response. Render only the footer line.

1. **Profile loaded OR explicit "no profile context" line emitted** on the first line.
2. **Country routing applied.** US → workflows below; UK → halt with the `references/country-uk.md` message; CA → halt; other → halt.
3. **Geography + period stamped on the first two lines** (state-or-national + month-and-prior).
4. **`inventory_type` set explicitly on every `get_sold_summary` call.** Never omitted (default "New" silently).
5. **`limit=5000` on every call.** Never default 1000 (silent multi-dim truncation).
6. **`ranking_dimensions` minimal per workflow.** W1 = `make`, W2 = `make,model`, W3 = `dealership_group_name`, W4 (per-fuel) = `make,model`, W4 (total) = `make`, W5 = `make,model`. Never default 3-dim `make,model,body_type`.
7. **`date_from` / `date_to` month-aligned.** First-of-month start, last-of-month end. Never `today` as `date_to`.
8. **Comparison period present** for W1, W2, W4. Single-period snapshots are not allowed for those three workflows. (W3 and W5 default to current-only.)
9. **Share change rendered in basis points (`bps`)**, not percentage points. A move from 14.2% to 14.5% is `+30 bps`, never `+0.3%`.
10. **Volume + share % both shown** in every per-make / per-model row of the rendered table. Raw counts without context are meaningless; percentages without counts lack scale.
11. **User brand highlighted** when `profile.dealer.franchise_brands` is populated. The renderer bolds matching rows.
12. **Compute pipeline executed** for every workflow. `parse_sold_summary.py` × N → `compute_<workflow>.py` → `render_share_table.py`. Hand-computed shares / efficiency / penetration values fail this check. When bypassed, prefix the report with `⚠ pipeline bypassed; numeric blocks computed by hand — values may diverge from canonical output`.
13. **Data Quality event log surfaced** when non-empty; omitted when empty.

Render rule at response time:

- **All applicable checks pass** → emit a single footer line listing 5–7 of the items that were exercised, e.g.:
  `✓ Verified: profile, geography + period, bps formatting, comparison period, dual columns, pipeline executed.`
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated in the output to compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.

---

## Render variations — which blocks per workflow

| Block                       | W1 | W2 | W3 | W4 | W5 |
|---|---|---|---|---|---|
| First-line profile/scope     | ✓  | ✓  | ✓  | ✓  | ✓  |
| Period stamp                 | ✓  | ✓  | ✓  | ✓  | ✓  |
| Headline                     | ✓  | ✓  | ✓  | ✓  | ✓  |
| Main table                   | ✓ (brand-share) | ✓ (segment-conquest) | ✓ (dealer-group) | ✓ (penetration) | ✓ (heatmap) |
| EV brand share table         | —  | —  | —  | ✓  | —  |
| Top gainers/losers           | ✓  | —  | —  | —  | —  |
| User-brand movement          | ✓ (when applicable) | — | — | — | — |
| Conquest insight             | —  | ✓ (when fastest_gainer non-null) | — | — | — |
| Top-volume vs top-efficiency | —  | —  | ✓  | —  | —  |
| Period trend paragraph       | —  | —  | —  | ✓  | —  |
| Top markets / bottom markets | —  | —  | —  | —  | ✓  |
| Strategic Implications       | ✓  | ✓  | ✓  | ✓  | ✓  |
| Data Quality Notes           | ✓ (if non-empty) | ✓ | ✓ | ✓ | ✓ |
| Source line                  | ✓  | ✓  | ✓  | ✓  | ✓  |
| Self-check footer            | ✓  | ✓  | ✓  | ✓  | ✓  |

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

UK profiles are halted by this skill; UK formatting is not used. The `--currency '£'` flag on `render_share_table.py` exists for parity with the golden but is unreachable in this skill's flow.
