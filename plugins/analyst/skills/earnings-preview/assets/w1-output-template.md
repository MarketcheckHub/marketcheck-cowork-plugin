# W1 Output Template — Earnings Preview Channel Check

Single source of truth for W1's output. The model interpolates `<placeholder>` fields from the orchestrator's single output envelope (`scripts/orchestrate.py` stdout). Optional blocks marked `(OPTIONAL)` render only when the precondition holds.

**Naming convention:** lowercase `<placeholder>` references the corresponding field on the orchestrator output (verbatim numeric value). Uppercase labels like `<VERDICT>` render the resolved verdict word. Field paths are dotted, all resolved against the single envelope — `<headline.sold_count_total>`, `<scores.volume_momentum.value>`, `<signal_drivers.strongest.slot>`, etc.

**Field shorthand mapping** (the Leading Indicators table uses these short aliases for readability — every alias resolves to a specific field on the orchestrator output):

| Short alias | Fully-qualified path |
|---|---|
| `vol` | `leading_indicators_raw.volume` |
| `asp` | `leading_indicators_raw.asp` |
| `msrp_gap` | `leading_indicators_raw.msrp_gap` |
| `dom` | `leading_indicators_raw.dom` |
| `ds_used` | `leading_indicators_raw.days_supply_used` |
| `ds_new` | `leading_indicators_raw.days_supply_new` |
| `ev` | `leading_indicators_raw.ev_share` |
| `mix` | `leading_indicators_raw.mix` |
| `<X>_band` | `composite_slots.<X>` (rendered with emoji prefix per band) |

Outside the Leading Indicators table, every placeholder is fully qualified.

**Quarter labels:** Every quarter reference uses `<windows.current_quarter.label>` (e.g., `"Q1 2026"`), `<windows.prior_quarter.label>` (`"Q4 2025"`), `<windows.year_ago_quarter.label>` (`"Q1 2025"`), `<windows.most_recent_complete_month.label>` (`"April 2026"`).

---

## SECTION 1 — Identity (always)

For OEM tickers (`entity_type == "oem"`, classification ∈ {`legacy`, `pure_play`}):
```
Analyzing **<ticker>** (<company_name>): <Make1, Make2, …> — <classification> OEM
```

For dealer-group tickers (`entity_type == "dealer_group"`, classification ∈ {`Used-only`, `New-only`, `Both`}):
```
Analyzing **<ticker>** (<canonical>) — dealer group, <classification> inventory
```

No brand-orphan / canonical-make form — per Phase 5 §5a, unknown tickers halt at `resolve_ticker`.

---

## SECTION 2 — Composite verdict & headline (always)

One emoji + verdict word + ticker + quarter label + one-sentence thesis:

```
<VERDICT_EMOJI> <VERDICT> · <ticker> heading into the print after <current_quarter.label>
<one-sentence thesis anchored on the dominant indicator>
```

Verdict emoji mapping:
- `BULLISH` → 🟢
- `BEARISH` → 🔴
- `NEUTRAL` → 🟡
- `MIXED` → ⚪
- `null` (no scoreable signals) → ⚫ render: `INSUFFICIENT DATA: <ticker> after <current_quarter.label> — no scoreable signals; rendering current-quarter KPIs only.`

The thesis is derived from `signal_drivers.strongest` (slot with highest score). Example: *"Volume momentum BULLISH (QoQ +9.2%, YoY +6.4%), but ASP softening into the print."*

**Degradation note (when any composite slot has `degraded_to`):**
```
> Note: <slot> evaluated on <degraded_to.replace("_only","")> alone — <year_ago_quarter.label> data unavailable (DQ event m).
```
Renders once per degraded slot, immediately below the thesis line.

---

## SECTION 3 — Leading Indicators table (always)

Render exactly this Markdown table:

```
| Indicator                | Current (<current_quarter.label>) | Prior (<prior_quarter.label>) | Year-ago (<year_ago_quarter.label>) | QoQ Δ | YoY Δ | Band |
|--------------------------|-----------------------------------|-------------------------------|--------------------------------------|-------|-------|------|
| Volume                   | <vol.current>                     | <vol.prior>                   | <vol.year_ago>                       | <vol.qoq_pct ±%>          | <vol.yoy_pct ±%>          | <volume_momentum_band> |
| Pricing — ASP            | $<asp.current>                    | $<asp.prior>                  | $<asp.year_ago>                      | <asp.qoq_pct ±%>          | <asp.yoy_pct ±%>          | <asp_band> |
| Pricing — MSRP gap       | <msrp_gap.current_pct ±%>         | <msrp_gap.prior_pct ±%>       | <msrp_gap.year_ago_pct ±%>           | <msrp_gap.qoq_delta_bps ±bps>  | <msrp_gap.yoy_delta_bps ±bps>  | <msrp_gap_band> |
| DOM (mean)               | <dom.current> days                | <dom.prior> days              | <dom.year_ago> days                  | <dom.qoq_delta_days ±days>     | <dom.yoy_delta_days ±days>     | <dom_band> |
| DOM (median)⁵            | <dom.median_current> days         | <dom.median_prior> days       | <dom.median_year_ago> days           | <dom.qoq_delta_median_days ±days> | <dom.yoy_delta_median_days ±days> | — |
| Days Supply (used)¹      | <ds_used.current> days            | —²                            | —²                                    | —²                              | —²                              | <days_supply_used_band> |
| Days Supply (new)¹       | <ds_new.current> days             | —²                            | —²                                    | —²                              | —²                              | <days_supply_new_band> |
| EV share³                | <ev.ev_pct_current ±%>            | <ev.ev_pct_prior ±%>          | <ev.ev_pct_year_ago ±%>              | <ev.qoq_delta_bps ±bps>        | <ev.yoy_delta_bps ±bps>        | <ev_share_band> |
| Mix (New % of total)⁴    | <mix.new_pct_current ±%>          | <mix.new_pct_prior ±%>        | <mix.new_pct_year_ago ±%>            | <mix.qoq_delta_pp ±pp>         | <mix.yoy_delta_pp ±pp>         | <mix_band> |
```

**Footnotes:**
1. `¹ Days Supply pairs LIVE active inventory (today's snapshot from search_active_cars) with the most-recent-complete-month sold velocity (<most_recent_complete_month.label>) — a live-vs-historical mix. The mrcm month may post-date the current_quarter end by design (e.g., current_quarter ends Mar 31 but mrcm is April). Days Supply is an absolute-level signal, not a Δ signal — the QoQ/YoY columns are not populated.`
2. `² Prior-quarter and year-ago Days Supply are unavailable — search_active_cars exposes only today's snapshot; historical active-inventory levels are not surfaced by the MCP. The QoQ / YoY columns are intentionally blank for Days Supply rows.`
3. `³ EV share = electrified-vehicle share of total volume (BEV + PHEV combined — see references/sold-summary-safety.md §EV slice). Row renders only when ev_block.shape == "transition". For pure_play tickers, the EV share slot is structurally null and this row is omitted.`
4. `⁴ Mix Δ measures the New% of total volume (dealer-group only). Row renders only when classification == "Both" — KMX (Used-only) and any New-only ticker have no mix to measure.`
5. `⁵ DOM (median) is the sold-count-weighted median across the cohort. More representative of "typical car sold" than the mean (which is right-skewed by long-tail aging). Display-only, not banded.`

**Per-cell formatting:**
- Volume `current/prior/year_ago`: thousands-separated integer. `—` when null.
- ASP `current/prior/year_ago`: `$` prefix, no decimals, thousands separator. `—` when null.
- MSRP gap `current_pct/prior_pct/year_ago_pct`: signed percentage with 2 decimals (e.g., `−3.50%`). `—` when null.
- DOM `current/prior/year_ago`: 1-decimal + " days". `—` when null.
- Days Supply `current`: integer rounded from float + " days". `—` when null.
- EV share `ev_pct_*`: 2-decimal percentage. `—` when null.
- Mix `new_pct_*`: 1-decimal percentage. `—` when null.
- QoQ Δ / YoY Δ percentage cells: signed % with 1 decimal.
- bps delta cells: signed integer + " bps".
- pp delta cells: signed float with 1 decimal + " pp".
- Day delta cells: signed float with 1 decimal + " days".
- Band cell: render verbatim band string with emoji prefix (🟢 BULLISH / 🟡 NEUTRAL / 🟠 CAUTION / 🔴 BEARISH / `—` null).

**Row-rendering rules:**
- Omit the EV share row entirely when `ev_share` is null (pure_play OR zero-EV current quarter).
- Omit the Mix row entirely when `mix` is null (OEM tickers OR single-channel dealer-groups).
- Omit the Days Supply (used) row when `days_supply_used` is null (most OEMs, New-only dealer-groups).
- Omit the Days Supply (new) row when `days_supply_new` is null (KMX).
- Omit the DOM (median) row when `dom.median_current`, `median_prior`, AND `median_year_ago` are all null.

---

## SECTION 3.5 — Channel Split (multi-channel entities only)

Render only when both `channel_split.new` and `channel_split.used` are non-null OR exactly one is non-null. Omit entirely when both are null (entity is structurally single-channel and the breakout has no value).

For each non-null sub-block, render the mini-table below. The MSRP-gap row in the Used sub-table is labeled "(informational — depreciation indicator)" because for used vehicles the MSRP-gap captures depreciation from original MSRP rather than discount-from-sticker.

**New channel (<current_quarter.label>):**

```
| Metric    | Current                                       | Prior                                       | Year-ago                                       | QoQ Δ                                          | YoY Δ                                          |
|-----------|-----------------------------------------------|---------------------------------------------|------------------------------------------------|------------------------------------------------|------------------------------------------------|
| Volume    | <channel_split.new.volume.current>            | <channel_split.new.volume.prior>            | <channel_split.new.volume.year_ago>            | <channel_split.new.volume.qoq_pct ±%>          | <channel_split.new.volume.yoy_pct ±%>          |
| ASP       | $<channel_split.new.asp.current>              | $<channel_split.new.asp.prior>              | $<channel_split.new.asp.year_ago>              | <channel_split.new.asp.qoq_pct ±%>             | <channel_split.new.asp.yoy_pct ±%>             |
| MSRP gap  | <channel_split.new.msrp_gap.current_pct ±%>   | <channel_split.new.msrp_gap.prior_pct ±%>   | <channel_split.new.msrp_gap.year_ago_pct ±%>   | <channel_split.new.msrp_gap.qoq_delta_bps ±bps>| <channel_split.new.msrp_gap.yoy_delta_bps ±bps>|
| DOM       | <channel_split.new.dom.current> days          | <channel_split.new.dom.prior> days          | <channel_split.new.dom.year_ago> days          | <channel_split.new.dom.qoq_delta_days ±days>   | <channel_split.new.dom.yoy_delta_days ±days>   |
```

**Used channel (<current_quarter.label>):**

```
| Metric                       | Current                                        | Prior                                        | Year-ago                                        | QoQ Δ                                           | YoY Δ                                           |
|------------------------------|------------------------------------------------|----------------------------------------------|-------------------------------------------------|-------------------------------------------------|-------------------------------------------------|
| Volume                       | <channel_split.used.volume.current>            | <channel_split.used.volume.prior>            | <channel_split.used.volume.year_ago>            | <channel_split.used.volume.qoq_pct ±%>          | <channel_split.used.volume.yoy_pct ±%>          |
| ASP                          | $<channel_split.used.asp.current>              | $<channel_split.used.asp.prior>              | $<channel_split.used.asp.year_ago>              | <channel_split.used.asp.qoq_pct ±%>             | <channel_split.used.asp.yoy_pct ±%>             |
| MSRP gap (info — depreciation) | <channel_split.used.msrp_gap.current_pct ±%> | <channel_split.used.msrp_gap.prior_pct ±%>   | <channel_split.used.msrp_gap.year_ago_pct ±%>   | <channel_split.used.msrp_gap.qoq_delta_bps ±bps>| <channel_split.used.msrp_gap.yoy_delta_bps ±bps>|
| DOM                          | <channel_split.used.dom.current> days          | <channel_split.used.dom.prior> days          | <channel_split.used.dom.year_ago> days          | <channel_split.used.dom.qoq_delta_days ±days>   | <channel_split.used.dom.yoy_delta_days ±days>   |
```

**Render rules:**
- Omit the entire section when both `channel_split.new` and `channel_split.used` are null.
- Omit only the New sub-table when `channel_split.new` is null (Used-only DG like KMX); render the Used sub-table standalone.
- Omit only the Used sub-table when `channel_split.used` is null (New-only DG); render the New sub-table standalone.
- Omit any individual cell as `—` when the underlying value is null.
- No band column — the Channel Split is display-only and does not contribute to the verdict (the headline-level Volume/ASP/MSRP-gap/DOM rows in §3 carry the bands).

**Footnote (always render when this section renders):**
```
⁶ Channel Split surfaces per-channel (New vs Used) views of Volume, ASP, MSRP-gap, and DOM that would otherwise be averaged in §3's combined view. Critical for entities where channel-divergent trends matter (Both dealer-groups, legacy OEMs with active Used markets). Used MSRP-gap is informational only — for used vehicles it measures depreciation from original MSRP rather than discount-from-sticker.
```

---

## SECTION 4 — Per-Make Breakdown (multi-make OEMs only)

Render only when `compute_earnings_signals.per_make_raw` is non-null (multi-make OEM ticker with N≥2 makes). Always omitted for dealer-group tickers and single-make OEM tickers (e.g., TSLA, RIVN, F has only Ford+Lincoln so it renders; STLA / GM / TM / HMC always render).

```
**Per-make breakdown (<current_quarter.label>):**

| Make    | Share % | Volume cur | Volume prior | Volume year-ago | QoQ Vol | YoY Vol | ASP cur | QoQ ASP | DOM cur | QoQ DOM Δ | MSRP gap Δ QoQ (New) | Volume band |
|---------|---------|------------|--------------|-----------------|---------|---------|---------|---------|---------|-----------|----------------------|-------------|
| <make>  | <share_pct>% | <sold_count_current> | <sold_count_prior> | <sold_count_year_ago> | <qoq_vol_pct ±%> | <yoy_vol_pct ±%> | $<weighted_avg_sale_price_current> | <qoq_asp_pct ±%> | <weighted_avg_days_on_market_current> days | <qoq_dom_delta_days ±days> | <qoq_msrp_gap_delta_bps ±bps> | <make_volume_band>⁵ |
| ...one row per make in per_make_raw (already sorted by sold_count_current desc by the script)... |
```

Per-cell formatting:
- `Share %`: 1-decimal percentage (e.g., `47.2%`).
- `Volume cur/prior/year-ago`: thousands-separated integer; `—` when null.
- `QoQ Vol`, `YoY Vol`, `QoQ ASP`, `YoY ASP`: signed % with 1 decimal; `—` when null.
- `ASP cur`: `$` prefix, no decimals, thousands separator.
- `DOM cur`: 1-decimal + ` days`; `—` when null.
- `QoQ DOM Δ`: signed days; `—` when null.
- `MSRP gap Δ QoQ (New)`: signed bps integer; `—` when null. New-channel-only because MSRP-gap is structurally a new-vehicle concept.

**Footnote 5:**
```
⁵ Per-make Volume band uses the same Volume QoQ banding table as the ticker composite. A make whose band score differs from the ticker composite by ≥ 2 score-points is flagged below as Internal divergence.
```

**Internal divergence callout (when `per_make_divergence` is non-empty):**
```
> Internal divergence: <per_make_divergence[i].make> shows <per_make_divergence[i].make_volume_band> (score <per_make_divergence[i].make_volume_score>) — diverging from ticker composite (score <per_make_divergence[i].ticker_composite_score>) by <per_make_divergence[i].gap> score points (QoQ <per_make_divergence[i].make_qoq_pct ±%>; YoY <per_make_divergence[i].make_yoy_pct ±%>).
```

Every field referenced here lives in the `per_make_divergence[i]` entry. Render one callout line per entry, ordered by `gap` descending. Log DQ event (l) once for the whole non-empty list.

If `per_make_raw` is null (dealer-group / single-make OEM), omit this section entirely.

---

## SECTION 5 — Inventory Health (always when any active data present)

Render the Days Supply block only when at least one of `active_inventory.used` / `active_inventory.new` is non-null.

```
**Active inventory (today's snapshot, paired with <most_recent_complete_month.label> sold velocity):**

| Channel | Active count | Avg list $ | P50 $ | P75 $ | P90 $ | Median $ | Avg DOM | DOM P50 | DOM P75 | DOM P90 | mrcm sold | Days Supply¹ |
|---------|--------------|------------|-------|-------|-------|----------|---------|---------|---------|---------|-----------|--------------|
| Used    | <active_inventory.used.num_found> | $<active_inventory.used.active_avg_price> | $<active_inventory.used.active_p50_price> | $<active_inventory.used.active_p75_price> | $<active_inventory.used.active_p90_price> | $<active_inventory.used.active_median_price> | <active_inventory.used.active_avg_dom> days | <active_inventory.used.active_p50_dom> | <active_inventory.used.active_p75_dom> | <active_inventory.used.active_p90_dom> | <active_inventory.used.mrcm_sold_count> | <ds_used.current> days |
| New     | <active_inventory.new.num_found>  | $<active_inventory.new.active_avg_price>  | $<active_inventory.new.active_p50_price>  | $<active_inventory.new.active_p75_price>  | $<active_inventory.new.active_p90_price>  | $<active_inventory.new.active_median_price>  | <active_inventory.new.active_avg_dom> days  | <active_inventory.new.active_p50_dom>  | <active_inventory.new.active_p75_dom>  | <active_inventory.new.active_p90_dom>  | <active_inventory.new.mrcm_sold_count>  | <ds_new.current> days  |
```

Per-cell formatting (additions):
- Price percentiles (P50/P75/P90) and Median: same as `Avg list $` — `$` prefix, no decimals, thousands separator. `—` when null.
- DOM percentiles (P50/P75/P90): integer + ` days`. `—` when null.
- `mrcm sold`: thousands-separated integer. `—` when null. This is the sold_count for the most-recent-complete-month that drove the Days Supply ratio.

**Channel-row rendering rules:**
- Omit the Used row when `active_inventory.used` is null OR when the entity has no Used channel by classification (New-only dealer-groups). Log DQ event (a) when the row is omitted due to a failed call (not when the entity structurally has no channel).
- Omit the New row when `active_inventory.new` is null OR when the entity has no New channel (KMX = Used-only). Log DQ event (a) on call failure.
- If both rows are omitted, skip the entire section.

**Footnote (always render when this section renders):**
```
¹ Days Supply = active_count × days_in_month / sold_count_mrcm. Pairs LIVE active inventory (today's snapshot) with the most-recent-complete-month sold velocity — a live-vs-historical mix. The mrcm month (<most_recent_complete_month.label>) may post-date the end of <current_quarter.label> — by design, since the freshest sold velocity is the most reliable denominator. See active_inventory.footnote on compute_earnings_signals output.
```

---

## SECTION 6 — EV Transition (conditional)

Render only when `ev_block.shape == "transition"` (legacy OEM with EV volume OR dealer-group with non-zero EV slice).

```
**EV transition (<ticker>):**

| Metric                  | Current (<current_quarter.label>) | Prior (<prior_quarter.label>) | Year-ago (<year_ago_quarter.label>) | QoQ Δ | YoY Δ |
|-------------------------|------------------------------------|--------------------------------|--------------------------------------|-------|-------|
| EV % of total volume    | <ev.ev_pct_current ±%>             | <ev.ev_pct_prior ±%>           | <ev.ev_pct_year_ago ±%>              | <ev.qoq_delta_bps ±bps>          | <ev.yoy_delta_bps ±bps>          |
| EV avg sale price       | $<ev_block.transition.ev_asp_current> | $<ev_block.transition.ev_asp_prior> | $<ev_block.transition.ev_asp_year_ago> | <ev_block.transition.qoq_asp_delta_pct ±%> | <ev_block.transition.yoy_asp_delta_pct ±%> |
| EV avg DOM              | <ev_block.transition.ev_dom_current> days | <ev_block.transition.ev_dom_prior> days | <ev_block.transition.ev_dom_year_ago> days | <ev_block.transition.qoq_dom_delta_days ±days> | <ev_block.transition.yoy_dom_delta_days ±days> |
| EV units sold           | <ev_block.transition.ev_sold_current> | <ev_block.transition.ev_sold_prior> | <ev_block.transition.ev_sold_year_ago> | <ev_block.transition.qoq_sold_delta_pct ±%> | <ev_block.transition.yoy_sold_delta_pct ±%> |
```

**Footnote 6:**
```
⁶ EV detail metrics (ASP, DOM, units sold) span Current / Prior / Year-ago, mirroring the share-percent row above. The share-percent row is the banded signal (ev_share band); the ASP / DOM / units rows are display-only context for the electrification narrative.
```

For pure_play tickers (`ev_block.shape == "skipped"` with `skipped_reason == "pure_play_volume_is_ev"`), omit this section entirely. The pure_play story is already told by Volume — the entire volume IS EV by definition. Log DQ event (k).

For zero-EV cases (`ev_block.shape == "skipped"` with `skipped_reason == "no_ev_volume"`), omit this section. Log DQ event (k).

---

## SECTION 7 — Mix (dealer-group "Both" tickers only)

Render only when `classification == "Both"` AND `mix_block` is non-null. KMX (Used-only) and any New-only ticker have no mix to measure — section omitted entirely.

```
**Mix shift — New % of total volume:**

- Current (<current_quarter.label>): <mix.new_pct_current ±%> (Used: <100 − mix.new_pct_current ±%>)
- Prior   (<prior_quarter.label>):   <mix.new_pct_prior ±%>
- Year-ago (<year_ago_quarter.label>): <mix.new_pct_year_ago ±%>
- QoQ Δ: <mix.qoq_delta_pp ±pp>
- YoY Δ: <mix.yoy_delta_pp ±pp>
- Band: <mix_band>
```

**Narrative line (one sentence below the bullet list):**
- If `mix_band == BULLISH`: `New-vehicle share is gaining (+<qoq_delta_pp> pp QoQ) — higher-margin New mix is supportive for gross profit per unit.`
- If `mix_band == BEARISH`: `New-vehicle share is collapsing (<qoq_delta_pp> pp QoQ) — used-mix shift is dilutive to gross profit per unit.`
- If `mix_band == CAUTION`: `New-vehicle share is softening (<qoq_delta_pp> pp QoQ) — watch for margin pressure on the print.`
- If `mix_band == NEUTRAL`: `New / Used mix is stable QoQ; no incremental mix-driven margin signal.`

---

## SECTION 8 — Bull Case (always when verdict is non-null — exactly 3 sentences)

**Fixed shape — exactly 3 sentences:**

1. **Strongest indicator framing.**
   `<signal_drivers.strongest.slot humanized> at <strongest.value with units> — the <strongest.band> band — is the most supportive indicator for <ticker> heading into the next print.`

2. **One supporting BULLISH or NEUTRAL slot (model selects from `scores`).**
   `<supporting slot humanized> remains <band>, reinforcing the upside thesis.`

3. **Forward-looking implication.**
   `A BULLISH-leaning channel check would translate into upside on volume / gross-profit indicators when the company reports — though the verdict itself comes from <n_bullish> BULLISH slots and a mean score of <mean_score>.`

Slot name display (humanize):
- `volume_momentum` → "Volume Momentum"
- `asp` → "ASP (pricing)"
- `msrp_gap` → "MSRP gap"
- `dom` → "DOM (days on market)"
- `days_supply_used` → "Days Supply (Used)"
- `days_supply_new` → "Days Supply (New)"
- `ev_share` → "EV share"
- `mix` → "New/Used mix"

If `verdict == BEARISH` AND no slot is BULLISH OR NEUTRAL → replace Section 8 with the single line:
```
**Bull Case:** No supportive indicator surfaced this quarter — every contributing slot landed CAUTION or BEARISH.
```

---

## SECTION 9 — Bear Case (always when verdict is non-null — exactly 3 sentences; **C12 weakest=null fallback applies**)

**Standard shape (when `signal_drivers.weakest` is non-null — i.e., at least one CAUTION or BEARISH slot exists):**

1. **Weakest indicator framing.**
   `<weakest.slot humanized> at <weakest.value with units> — the <weakest.band> band — is the biggest drag on <ticker> heading into the next print.`

2. **One supporting BEARISH or CAUTION slot (model selects from `scores`).**
   `<supporting slot humanized> additionally lands <band>, compounding the downside.`

3. **Forward-looking implication.**
   `A BEARISH-leaning channel check would translate into pressure on volume / gross-profit indicators when the company reports — though the verdict itself comes from <n_bearish> BEARISH slots and a mean score of <mean_score>.`

**C12 fallback — when `signal_drivers.weakest` is null** (every non-BULLISH slot landed NEUTRAL — no genuine downside exists):

Replace Section 9 with the single line:
```
**Bear Case:** No CAUTION or BEARISH indicator surfaced this quarter — every contributing slot landed NEUTRAL or BULLISH. The "biggest drag" framing is suppressed to avoid manufacturing a downside that the data does not support.
```

This C12 fallback closes the Phase 6 finding: if the renderer were to report "Weakest: <slot> NEUTRAL (score 0)", an analyst would read it as a downside warning even though NEUTRAL is by definition the safe band. Suppressing the line preserves signal honesty.

---

## SECTION 10 — Signal Drivers (always when verdict is non-null)

```
**Signal drivers:**
- Strongest: <signal_drivers.strongest.slot humanized> — <strongest.band> (score <strongest.score>)
[only render the next line when signal_drivers.weakest is non-null:]
- Weakest:   <signal_drivers.weakest.slot humanized> — <weakest.band> (score <weakest.score>)
- Composite: <n_bullish> BULLISH, <n_bearish> BEARISH, mean score <mean_score> → <VERDICT>
- <rationale>
```

When `signal_drivers.weakest` is `null` (C12 fallback case), the "Weakest" line is omitted entirely. Reporting "Weakest: X NEUTRAL (score 0)" misleads the analyst into thinking there's a downside — the script suppresses it; the template must follow.

---

## SECTION 11 — Earnings-Preview Statement (always when verdict is non-null — exactly 3 sentences)

**Fixed shape — exactly 3 sentences:**

1. **Verdict + ticker + dominant signal.**
   `<VERDICT> on <ticker> heading into the next quarterly print: <one-clause summary of the dominant signal — typically the signal_drivers.strongest with its value>.`

2. **Strongest metric (mirrors Bull Case sentence 1 but tighter).**
   `<strongest slot humanized>: <value with units>, the <strongest.band> band.`

3. **Weakest metric (or C12 fallback).**
   - Standard form: `<weakest slot humanized>: <value with units>, the <weakest.band> band — <one-clause implication for the quarter>.`
   - C12 fallback (when `weakest` is null): `No CAUTION or BEARISH slot surfaced — the verdict reflects a clean composite.`

**Anti-patterns (DO NOT do):**
- No free-form narrative beyond these 3 sentences.
- No stock-price-target predictions.
- No specific dollar EPS forecasts.
- No "buy / sell / hold" recommendations.
- No comparison to consensus estimates (this skill does not have access to street estimates).
- No predictions about earnings beat/miss probability — the channel check is one input among many.

---

## SECTION 12 — Data Quality Notes (OPTIONAL — render when dq_events is non-empty)

```
**Data Quality Notes:**
- ⚠ <event verbatim from compute_earnings_signals.dq_events>
- ⚠ <event verbatim from aggregate_signals if any (per-make divergence event (l) lives here)>
```

**Rendering rules (strict — no paraphrasing):**
- Each event is rendered VERBATIM from the script outputs. Do NOT paraphrase, abbreviate, or compose new wording.
- Use the ⚠ prefix for warning events: (a), (i), (k), (l), (m), (n).
- Events are documented in `SKILL.md §Data Quality event log` and `references/script-contracts.md`; the model must NOT invent new event codes or repurpose existing ones.

If `dq_events` is empty AND `per_make_divergence` is empty, omit this section entirely.

---

## Footer (always)

Self-check pass → emit one line:
```
✓ Verified: ticker resolution, quarter windows, signal aggregation, Days Supply mrcm pairing, weakest=null suppression rule.
```

Self-check fail → emit only the failures, prefixed `⚠`:
```
⚠ Days Supply footnote omitted — added back inline.
```

---

## Halt rendering (when the orchestrator returns ok=false)

When the orchestrator output's `ok == false`, the W1 surface renders ONLY this halt block — sections 1-12 are suppressed:

```
🛑 HALT — <ticker>

<one-sentence reason from orchestrator output's error_type>:
- `no_current_quarter_data`: "No sold volume returned for <current_quarter.label>. The earnings-preview channel check requires at least one sold transaction in the current quarter to derive a verdict."

**Data Quality Notes:**
- ⚠ <each event verbatim from orchestrator output's dq_events>
```

Per Phase 5 §5b, `no_current_quarter_data` is the only legitimate halt path. All other failures (missing prior/year-ago, missing mrcm, missing one channel) degrade gracefully and Section 2's verdict / `volume_momentum.degraded_to` flag carries the signal.

---

## Self-check items (model runs silently — DO NOT render the checkbox grid)

1. Profile loaded; `country == "US"` (skill is US-only per analyst plugin scope).
2. `resolve_ticker.py` returned a valid ticker + entity_type + classification — OR halted with `no_candidates` (in which case the workflow stops, this template is never invoked).
3. Quarter windows quarter-aligned (no in-progress quarter); `most_recent_complete_month` follows the monthly strictly-before rule (may post-date `current_quarter.date_to`).
4. Every `get_sold_summary` call sent `inventory_type` explicitly (TitleCase: `"New"` or `"Used"`) — never omitted.
5. Every `get_sold_summary` call sent `limit=5000`.
6. Every `get_sold_summary` call's date span is ≤8 months (Call A = year_ago_quarter only, 3 months; Call B = prior_quarter → mrcm, ≤8 months — both under the upstream 12-month cap).
7. No `state` parameter passed on any call (skill is national-only).
8. Wave A1 fired in sub-batches of ≤5 concurrent `tool_use` blocks per agent message (per upstream rate-limit 429); sub-batches sequential; calls within a sub-batch parallel; Wave A2 same rule.
9. `orchestrate.py` received a manifest enumerating all Wave A1 + A2 file paths + pre-flight context; stdout carries the structured envelope used for template rendering.
10. Verdict came verbatim from the orchestrator output's `verdict` field (not hand-picked).
11. Per-make breakdown rendered iff `per_make_raw` is non-null (multi-make OEM ticker).
12. Days Supply footnote rendered when any Days Supply value was shown.
13. Mix section rendered iff `classification == "Both"` AND `mix_block` is non-null.
14. EV section rendered iff `ev_block.shape == "transition"`.
15. Bear Case used the C12 fallback when `signal_drivers.weakest` is null.
16. Earnings-Preview Statement is exactly 3 sentences in the prescribed shape (or 2 if Bull Case fallback fired).
17. DQ events list rendered verbatim from the orchestrator output's `dq_events` array; no events fabricated by the model.
18. No band string in the output was inferred by the model — all bands come from the orchestrator output's `per_metric_bands` / `composite_slots`.
19. No comparison to consensus estimates or buy/sell/hold recommendations anywhere in the output.
