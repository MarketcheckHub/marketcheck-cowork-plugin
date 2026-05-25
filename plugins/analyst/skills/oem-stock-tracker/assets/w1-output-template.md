# W1 Output Template — Single OEM Investment Signal

Single source of truth for W1's 11-section output. The model interpolates `<placeholder>` fields from `compute_oem_stats.py` and `aggregate_signals.py` outputs. Optional blocks marked `(OPTIONAL)` render only when the precondition holds.

**Naming convention:** lowercase `<placeholder>` references the corresponding field on the script outputs (verbatim numeric value). Uppercase labels like `<VERDICT>` render the resolved verdict word. Field paths are dotted (`<compute_oem_stats.headline.sold_count_total>` etc.).

**Field shorthand mapping** (Section 3 Leading Indicators table uses these short aliases for readability — every alias resolves to a specific field on `compute_oem_stats.leading_indicators_raw`):

| Short alias | Fully-qualified path |
|---|---|
| `vol` | `leading_indicators_raw.volume` |
| `asp` | `leading_indicators_raw.asp` |
| `msrp_gap` | `leading_indicators_raw.msrp_gap` |
| `days_supply` | `leading_indicators_raw.days_supply` |
| `market_share` | `leading_indicators_raw.market_share` |
| `dom` | `leading_indicators_raw.dom` |
| `ev` (Section 3 only) | `leading_indicators_raw.ev_transition` |
| `<X>_band` | `aggregate_signals.composite_slots.<X>` (rendered with emoji prefix per band) |

Outside Section 3, every placeholder is fully qualified (e.g., `<ev_block.transition.ticker_ev_asp>`, `<per_make_divergence[i].make_volume_band>`).

---

## SECTION 1 — Identity (always)

For OEM tickers (classification ∈ {`legacy`, `pure_play`}):
```
Analyzing **<ticker>** (<company_name>): <Make1, Make2, …> — <classification>
```

For brand-orphan (`classification == "brand_orphan"`):
```
Analyzing **<canonical_make>** — brand_orphan
```
No ticker parenthetical, no makes-list comma form (single make = the brand name itself).

---

## SECTION 2 — Composite verdict & headline (always)

One emoji + verdict word + ticker + month label + one-sentence thesis:

```
<VERDICT_EMOJI> <VERDICT> · <ticker> in <current_month.label>
<one-sentence thesis anchored on the dominant indicator>
```

Verdict emoji mapping:
- `BULLISH` → 🟢
- `BEARISH` → 🔴
- `NEUTRAL` → 🟡
- `MIXED` → ⚪
- `null` (no scoreable signals) → ⚫ render: `INSUFFICIENT DATA: <ticker> in <month_label> — no scoreable signals; rendering current-month KPIs only.`

For brand-orphan, replace `<ticker>` with `<canonical_make>` in this line.

The thesis is derived from `aggregate_signals.signal_drivers.strongest` (the indicator with highest score). Example: *"Volume momentum BULLISH (mom +2.9%, 3-mo trend +5.3%), but ASP softening into earnings."*

---

## SECTION 3 — Leading Indicators table (always)

Render exactly this Markdown table:

```
| Indicator                | Current (<current_month.label>) | Prior (<prior_month.label>) | 3-mo baseline | MoM Δ      | 3-mo Δ     | Band       |
|--------------------------|---------------------------------|------------------------------|---------------|------------|------------|------------|
| Volume                   | <vol.current>                   | <vol.prior>                  | <vol.baseline_3mo> total / <vol.baseline_3mo_avg_per_month> /mo | <vol.mom_pct ±%>  | <vol.trend_3mo_pct ±%>  | <volume_momentum_band> |
| Pricing — ASP            | $<asp.current>                  | $<asp.prior>                 | $<asp.baseline_3mo>            | <asp.mom_pct ±%>  | —⁵                      | <pricing_power_band>¹ |
| Pricing — MSRP gap       | <msrp_gap.current_pct ±%>       | <msrp_gap.prior_pct ±%>      | <msrp_gap.baseline_3mo_pct ±%> | <msrp_gap.delta_bps ±bps> | —⁵              | <pricing_power_band>¹ |
| Days Supply (new)        | <days_supply.current>           | —²                            | —²                             | —²                | —⁵                      | <days_supply_band> |
| Market share             | <market_share.current_pct ±%>   | <market_share.prior_pct ±%>  | <market_share.baseline_3mo_pct ±%> | <market_share.delta_bps ±bps> | —⁵          | <market_share_band> |
| DOM                      | <dom.current> days              | <dom.prior> days             | <dom.baseline_3mo> days        | <dom.delta_days ±days>  | —⁵                | <dom_band> |
| EV transition (legacy)³  | <ev.current_pct ±%>             | <ev.prior_pct ±%>            | <ev.baseline_3mo_pct ±%>       | <ev.delta_bps ±bps> | —⁵                      | <ev_transition_band> |
```

**Footnotes:**
1. `¹ ASP and MSRP gap combine into one "Pricing Power" composite slot for the verdict reduction. Rendered as two rows for transparency.`
2. `² Prior-month Days Supply is unavailable in v1 — search_active_cars returns a live snapshot only; historical inventory data is not exposed by the MCP surface. The current Days Supply column uses today's snapshot.`
3. `³ EV transition row renders only when classification ∈ {legacy, brand_orphan} AND ev_block.shape == "transition". For pure-play tickers, the EV Market Leaders block (Section 7) substitutes.`
4. `⁵ 3-mo Δ is intentionally not rendered for ASP / MSRP gap / Days Supply / Market share / DOM / EV transition — the 3-mo baseline column is informational only (not banded). Volume's 3-mo Δ is the sole banded multi-month signal (contributes to volume_momentum). See references/signal-aggregation.md.`

**Per-cell formatting:**
- Volume `current/prior/baseline_3mo`: thousands-separated integer. `—` when null.
- `baseline_3mo_avg_per_month`: thousands-separated integer + " /mo" suffix.
- ASP `current/prior/baseline_3mo`: `$` prefix, no decimals, thousands separator. `—` when null.
- MSRP gap `current_pct/prior_pct/baseline_3mo_pct`: signed percentage with 2 decimals (e.g., `−3.50%`). `—` when null.
- Days Supply: integer (rounded from float).
- Market share `current_pct/prior_pct/baseline_3mo_pct`: 2-decimal percentage. `—` when null.
- DOM `current/prior/baseline_3mo`: 1-decimal + " days". `—` when null.
- EV transition `current_pct/prior_pct/baseline_3mo_pct`: signed percentage with 2 decimals. `—` when null.
- MoM Δ percentage: signed % with 1 decimal.
- bps delta: signed integer + " bps".
- Day delta: signed float with 1 decimal + " days".
- Band cell: render verbatim band string with emoji prefix (🟢 BULLISH / 🟡 NEUTRAL / 🟠 CAUTION / 🔴 BEARISH).

If `ev_transition` is `null` (pure-play or zero-EV legacy), omit row 7 entirely.

---

## SECTION 4 — Per-Make Breakdown (multi-make tickers only)

Render only when `compute_oem_stats.per_make_raw` is non-null (multi-make legacy ticker with N≥2).

```
**Per-make breakdown (<current_month.label>):**

| Make     | Volume      | ASP       | DOM        | MoM Vol   | 3-mo Vol  | Volume band  |
|----------|-------------|-----------|------------|-----------|-----------|--------------|
| <make>   | <sold_count_current>   | $<weighted_avg_sale_price_current>   | <weighted_avg_days_on_market_current> days   | <mom_vol_pct ±%>   | <trend_3mo_pct ±%>   | <volume_band> |
| ...one row per make in per_make_raw... |
```

**Internal divergence callout (when `aggregate_signals.per_make_divergence` is non-empty):**
```
> Internal divergence: <per_make_divergence[i].make> shows <per_make_divergence[i].make_volume_band> (score <per_make_divergence[i].make_volume_score>) — diverging from ticker composite (score <per_make_divergence[i].ticker_composite_score>) by <per_make_divergence[i].gap> score points. See per-make breakdown above.
```

Every field referenced here lives in the `per_make_divergence[i]` entry, which the script emits as `{make, make_volume_band, make_volume_score, ticker_composite_score, gap}`. Render one callout line per entry. Log DQ event (l).

If `per_make_raw` is null (pure-play / brand-orphan / single-make legacy), omit this section entirely.

---

## SECTION 5 — Inventory Health (always when active data present)

**If `compute_oem_stats.active_inventory_complete == false`**, prepend this callout (loud — bold + warning emoji):
```
> ⚠ **Active inventory incomplete** — excludes <comma-separated makes in compute_oem_stats.makes excluding makes_with_active>. Days Supply rollup reflects only <comma-separated makes_with_active>. See Data Quality Notes (event q).
```

```
**Active inventory (today's snapshot):**

| Make    | Active count | Avg list $    | Active DOM   | Days Supply⁴ |
|---------|--------------|---------------|--------------|--------------|
| <make>  | <active_count>     | $<active_avg_price>  | <active_dom> days | <days_supply>     |
| ...one row per entry in compute_oem_stats.active_inventory... |
```

**Footnote (always render when any Days Supply is shown):**
```
⁴ Days Supply pairs live active inventory (today's snapshot) with the most-recent-complete-month sold velocity — a live-vs-historical mix. Uses the same inventory channel as the sold-data analysis (default new; "used" if user overrode).
```

Skip a make's row entirely when `active_inventory` for that make is missing (DQ event (d) logged). If `active_inventory` is empty across all makes, omit the entire section with DQ event (d).

---

## SECTION 6 — Market Share Context (always)

```
**Top 10 US makes by sold volume (<current_month.label>):**

| Rank | Make         | Sold       | Share | Δ MoM bps |
|------|--------------|------------|-------|-----------|
| 1    | <make>       | <sold>     | <share_pct>% | <delta_bps ±bps> |
| ...one row per entry in market_context.top_10_makes... |
```

Rows where `is_target_make == true` should be **bolded** (wrap every cell in `**`).

Below the table:
```
> <ticker> aggregate share: <ticker_aggregate_share_pct>% across <count of target_makes_in_top25> makes in top-25 (<comma-separated target_makes_in_top25>).
```

**Split-ticker footnote (when `target_makes_outside_top25` is non-empty):**
```
> Note: <comma-separated target_makes_outside_top25> fell outside the top-25 leaderboard this month; <ticker>'s aggregate share understates true volume.
```

**Absent-ticker footnote (when `target_makes_in_top25` is empty):**
```
> Note: <ticker>'s makes are not in the current-month top-25. Market share signal flagged as DQ event (g).
```

---

## SECTION 7 — EV Transition OR EV Market Leaders (conditional)

### Variant A — Legacy with EV (`ev_block.shape == "transition"`)

```
**EV transition (<ticker>):**

| Metric                  | Current   | Prior    | Δ              |
|-------------------------|-----------|----------|----------------|
| EV % of total volume    | <ev_block.transition.ticker_ev_pct ±%>   | <ev_block.transition.ticker_ev_pct_prior ±%>  | <ev_block.transition.ticker_ev_pct_delta_bps ±bps>     |
| EV avg sale price       | $<ev_block.transition.ticker_ev_asp>     | $<ev_block.transition.ticker_ev_asp_prior>     | <ev_block.transition.ticker_ev_asp_mom_pct ±%>     |
| EV avg DOM              | <ev_block.transition.ticker_ev_dom> days | <ev_block.transition.ticker_ev_dom_prior> days | <ev_block.transition.ticker_ev_dom_delta_days ±days> |
| EV units sold           | <ev_block.transition.ticker_ev_sold>     | <ev_block.transition.ticker_ev_sold_prior>     | <ev_block.transition.ticker_ev_sold_mom_pct ±%>    |

**EV breakdown by make:**

| Make     | EV sold  | EV ASP   |
|----------|----------|----------|
| <make>   | <ev_sold>      | $<ev_asp>      |
| ...one row per entry in ev_block.transition.per_make_breakdown... |
```

Below the tables:
```
> <ev_block.transition.narrative_note>
```

### Variant B — Pure-play (`ev_block.shape == "market_leaders"`)

```
**EV market leaders (<current_month.label>):**

| Rank | Make    | EV sold     | EV share | EV ASP    |
|------|---------|-------------|----------|-----------|
| 1    | <make>  | <ev_sold>   | <ev_share_pct>% | $<ev_asp>     |
| ...one row per entry in ev_block.market_leaders... |
```

Bold the row where `make == <ticker's canonical make>` (e.g., bold the Tesla row for TSLA).

### Variant C — Omitted (`ev_block.shape == "omitted"`)

Omit this section entirely. Log DQ event (k).

---

## SECTION 8 — Segment Mix (always when segment_mix has data)

**If `compute_oem_stats.segment_mix_complete == false`**, prepend this callout (loud — bold + warning emoji):
```
> ⚠ **Segment mix incomplete** — excludes <comma-separated makes in compute_oem_stats.makes excluding makes_with_segment_mix>. Body-type rollup reflects only <comma-separated makes_with_segment_mix>. See Data Quality Notes (event p).
```

```
**Top 5 body types (<current_month.label>):**

| Body type   | Volume      | Share   | Avg ASP    | Avg DOM    |
|-------------|-------------|---------|------------|------------|
| <body_type> | <sold>      | <share_pct>% | $<asp>     | <dom> days |
| ...up to 5 rows from compute_oem_stats.segment_mix... |
```

Skip the section if `segment_mix` is empty (zero-volume across all body types — should be rare).

**Footnote 5 (always when this section renders):**
```
⁵ The segment-mix call uses top_n=5 per state, which captures the top 5 body types by sold-count per state. Low-volume body types (e.g., Coupe, Chassis Cab) accounting for ~1-3% of ticker volume may be excluded. This is a deliberate response-size trade-off; the math-consistency check (DQ event t) flags any deviation > 5% as a real data integrity issue.
```

---

## SECTION 9 — Signal Drivers (always when verdict is non-null)

```
**Signal drivers:**
- Strongest: <signal_drivers.strongest.slot> — <slot_band> (score <slot_score>)
[only render the next line when signal_drivers.weakest is non-null:]
- Weakest:   <signal_drivers.weakest.slot> — <slot_band> (score <slot_score>)
- Composite: <n_bullish> BULLISH, <n_bearish> BEARISH, mean score <mean_score> → <VERDICT>
- <aggregate_signals.rationale>
```

When `aggregate_signals.signal_drivers.weakest` is `null` (no CAUTION/BEARISH slot exists — all non-BULLISH slots are NEUTRAL), the "Weakest" line is omitted entirely. Reporting "Weakest: X NEUTRAL (score 0)" misleads the analyst into thinking there's a downside, so the script suppresses it.

Slot name display (humanize):
- `volume_momentum` → "Volume Momentum"
- `pricing_power` → "Pricing Power"
- `days_supply` → "Days Supply"
- `market_share` → "Market Share"
- `dom` → "DOM trend"
- `ev_transition` → "EV transition"

---

## SECTION 10 — Ticker-Impact Statement (always when verdict is non-null — exactly 3 sentences)

**Fixed shape — exactly 3 sentences:**

1. **Verdict + ticker + dominant signal.**
   `<VERDICT> on <ticker> heading into the next quarterly print: <one-clause summary of the dominant signal — typically the signal_drivers.strongest with its value>.`

2. **Strongest metric.**
   `<strongest slot humanized>: <value with units>, the <strongest.band> band.`

3. **Weakest metric.**
   `<weakest slot humanized>: <value with units>, the <weakest.band> band — <one-clause implication for the quarter>.`

For brand-orphan, replace `<ticker>` with `<canonical_make>` (no quarterly print framing since there's no public ticker).

**Anti-patterns (DO NOT do):**
- No free-form narrative beyond these 3 sentences.
- No stock-price-target predictions.
- No specific dollar EPS forecasts.
- No "buy / sell / hold" recommendations.

---

## SECTION 11 — Data Quality Notes (OPTIONAL — render when dq_events is non-empty)

```
**Data Quality Notes:**
- ⚠ <event verbatim from compute_oem_stats.dq_events>
- ⚠ <event>
```

**Rendering rules (strict — no paraphrasing):**
- Each event is rendered VERBATIM from `compute_oem_stats.dq_events` (and any other script's dq_events the model accumulated). Do NOT paraphrase, abbreviate, or compose new wording.
- Use the ⚠ prefix for warning events: (a), (b), (d), (g), (h), (i), (j), (k), (l), (m), (n), (o), (p), (q), (r), (t), (u).
- Use a neutral bullet (no emoji) for informational events: (c), (e), (f), (s).
- Events (a)-(u) are documented in SKILL.md §Data Quality event log; the model must NOT invent new event codes or repurpose existing ones (e.g., using (h) "zero-volume" to label a parser failure is WRONG — use (p) instead).

If `dq_events` is empty, omit this section entirely.

---

## Footer (always)

Self-check pass → emit one line:
```
✓ Verified: profile, signal aggregation, market share context, per-make rollup, days-supply caveat.
```

Self-check fail → emit only the failures, prefixed `⚠`:
```
⚠ Days Supply footnote omitted — added back inline.
```

---

## Self-check items (model runs silently — DO NOT render the checkbox grid)

1. Profile loaded; `country == "US"`.
2. OEM `resolve_oem.py` returned a valid ticker / company / makes / classification, OR brand-orphan path completed with user confirmation.
3. Date windows month-aligned (no in-progress month); baseline_3mo_window covers months −1, −2, −3 relative to current.
4. Every `get_sold_summary` call sent `inventory_type` explicitly (TitleCase: "New" or "Used") — never omitted.
5. Every `get_sold_summary` call sent `limit=5000`.
6. No `state` parameter passed on any call (skill is national-only).
7. Wave A1 fired in parallel; Wave A2 followed in parallel; no within-wave serialization.
8. `compute_oem_stats.py` received the assembled JSON; `aggregate_signals.py` received the raw leading_indicators + per_make_raw + classification.
9. Verdict came verbatim from `aggregate_signals.verdict` (not hand-picked).
10. Per-make breakdown rendered iff `per_make_raw` is non-null (multi-make legacy ticker).
11. Days Supply footnote rendered (footnote (e)).
12. Ticker-impact statement is exactly 3 sentences in the prescribed shape.
13. EV block matches `ev_block.shape` (transition / market_leaders / omitted).
14. DQ events list matches the `compute_oem_stats.dq_events` + `aggregate_signals` (divergence) outputs.
15. No band string in the output was inferred by the model — all bands come from `aggregate_signals.per_metric_bands` / `composite_slots`.
