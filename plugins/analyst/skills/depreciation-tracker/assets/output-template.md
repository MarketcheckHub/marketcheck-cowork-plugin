# Output Template — Depreciation Tracker (Analyst)

This file is the **single source of truth** for output block structure,
table schemas, verdict / tier wording, ticker-overlay rules, and the
internal self-check across the four workflows. Every workflow renders by
adapting this template — see the "Render variations" matrix at the end.

Placeholders in angle brackets `<...>` are interpolated from the parser /
script outputs. Optional blocks are marked `(OPTIONAL)` and only render
when the precondition holds.

---

## First line (always)

```
Using profile: <user.company or user.name or "guest analyst">, <state | "national">, US
```

When there is no parseable profile, render: `Using profile context: <derived state | "national">, US`.

---

## Analysis Summary (always)

```
Workflow:        W<N> — <name>   (e.g. "W1 — Make/Model Depreciation Curve")
Scope:           <make> <model>  |  <segment>  |  <STATE | "national">  |  <inventory_type>
Year scope:      across all model years (per get_sold_summary scope)   ← W1
Period:          <oldest_period.label> to <newest_period.label>        ← W1 multi-period
                 (e.g. "1yr ago to current")
                 OR
                 <date_from> to <date_to>  (single period)             ← W3/W5 cross-period
Prior anchor:    <prior_period_offset> months back                     ← W2 / W3 / W5
```

---

## Headline (always)

One sentence. Workflow-specific phrasing.

### W1 (Make/Model Depreciation Curve) — always prior-period anchor in v1.0.0

```
<make> <model> [<TICKER>] sold-summary average dropped from $<oldest_avg>
to $<newest_avg> over <months_span> months (<recent_monthly_rate>%/month)
— <BULLISH | BEARISH | NEUTRAL | CAUTION>.
```

When `verdict` from `depreciation_curve.py` is `null` (insufficient data):

```
Insufficient sold data to build a depreciation curve for <make> <model>
in the <period_set> window — <n_priced>/5 periods returned priced rows.
```

The `<BULLISH | BEARISH | NEUTRAL | CAUTION>` value comes from
`aggregate_signals.py --workflow w1`; the raw 5-band curve label
(`Strong Retention` / etc.) is rendered in the curve table's verdict cell
as documented context.

### W2 (Segment Value Trends)

```
Across <STATE | "the national market"> over the last <N> months, the
strongest-retention segment is <top.key> (<+pct>%) — <BULLISH for
exposed tickers>; the weakest is <bottom.key> (<-pct>%) — <BEARISH/CAUTION
for exposed tickers>.
```

When the EV / ICE pass ran, append a second sentence:

```
EV vs ICE: EV moved <ev_pct>% vs ICE <ice_pct>% — EV depreciating <ratio>×
<faster|slower> than ICE.
```

### W3 (Brand Residual Ranking)

```
T1 (BULLISH) leaders: <top-3 makes [tickers]>. Largest tier downgrade:
<make> [<TICKER>] dropped T<X> → T<Y> (<change_pct>% retention shift) —
<BEARISH | CAUTION> for the ticker. <count> tracked-cohort brands in T1;
<count> in T4.
```

When the user's `tracked_tickers` is empty: replace "tracked-cohort brands"
with "<count> brands in the top-25 ranking".

### W5 (MSRP Parity Tracker)

```
<above_count> models above sticker (BULLISH pricing power), <below_count>
below (BEARISH incentive pressure). Largest current premium: <model>
[<TICKER>] (<+X.X>% over MSRP). Newly flipped below MSRP this period:
<list> [<tickers>].
```

When no flips: `No models flipped above ↔ below MSRP this period.`

---

## Workflow Table (always — rendered via render_depreciation_table.py)

```
render_depreciation_table.py --mode <m> --input <path> --currency '$'
```

Modes by workflow:

| Workflow | --mode | Input source | Columns rendered |
|---|---|---|---|
| W1 | `curve` | `depreciation_curve.py` output | Period · Avg Sale Price · Sold Count · Retention % (vs Prior) · Monthly Rate · Annualized Rate |
| W2 | `segment` | `segment_compare.py` output | Body_Type or Fuel_Type · Current Avg · Prior Avg · Price Δ% · Volume Δ% · Current Sold · Classification |
| W3 | `brand` | `brand_retention.py` output | Rank · Make · Current Avg · Prior Avg · Retention % · Volume · Tier |
| W5 | `parity` | `msrp_parity.py` output | Make/Model · Current % vs MSRP · Prior % · Δ % · Avg Price · Volume · Status · Direction |

Currency is always `$` (US-only).

Renderer reads pre-computed fields from each script's output JSON. Never
re-implement script logic during rendering. When the script fails or the
input JSON is malformed, the agent's output **must** prefix the table with
`⚠ table renderer bypassed; manual cells may diverge from canonical
formatting` and emit a self-check warning.

W1's `curve` mode in this analyst port omits the "Retention % (vs MSRP)"
column because `anchor_used == "prior_period"` is always set (the MSRP
anchor path was dropped from W1 in v1.0.0).

---

## Tier / Verdict Block (always)

W1 — surface the curve verdict + curve shape verbatim:

```
Verdict:      **<5-band curve label>**     (most-recent monthly rate: <signed pct>)
Curve shape:  **<accelerating | linear | stabilizing>**
              (longest-window monthly rate: <signed pct>)
Investment:   **<BULLISH | BEARISH | NEUTRAL | CAUTION>** for [<TICKER>]
```

W2 — surface segment classifier counts + headline investment signal:

```
Appreciating:    <count> segment(s)   (BULLISH)
Stable:          <count>               (NEUTRAL)
Soft:            <count>               (CAUTION)
Accelerating depreciation: <count>     (BEARISH)
Headline:        **<BULLISH | BEARISH | NEUTRAL | CAUTION | MIXED>**
```

W3 — tier counts + headline investment signal:

```
Tier counts:  T1 <count> · T2 <count> · T3 <count> · T4 <count>
Cohort tier:  <user's tracked_tickers reduced verdict> (if cohort supplied)
Headline:     **<BULLISH | BEARISH | NEUTRAL | CAUTION | MIXED>**
```

W5 — direction tally + headline investment signal:

```
Above sticker:    <count>     (BULLISH pricing power)
Below sticker:    <count>     (BEARISH incentive pressure)
Newly flipped below MSRP:  <list>
Newly flipped above MSRP:  <list>
Deepening discounts:       <list>
Headline:                  **<BULLISH | BEARISH | NEUTRAL | CAUTION | MIXED>**
```

---

## Ticker Impact Summary (always — analyst-native)

Per `references/ticker-mapping.md` and `references/signal-aggregation.md`,
group per-make / per-row bands by ticker, run the headline reducer per
ticker, and render one row per ticker.

```
| Ticker | Verdict | Rationale |
|---|---|---|
| F    | BULLISH | Ford / Lincoln retention in T1 cohort; monthly rate +0.18%/mo |
| GM   | NEUTRAL | Chevrolet T2, GMC T2, Buick T2, Cadillac T2; mean +0.4 |
| STLA | MIXED   | Jeep T1 BULLISH, but Alfa Romeo T4 BEARISH |
| TM   | BULLISH | Toyota T1, Lexus T1                                |
| ...  | ...     | ...                                                 |
```

When a row's make has no ticker entry, omit it from the per-ticker table
and surface in a "Other makes (no tracked ticker)" footnote line.

---

## Comparison Context (always)

At least one cross-axis comparison. Required even when the workflow is
single-cut:

- **W1** — compare the subject's monthly rate to the W1 verdict-band median for the ticker's other makes (e.g., if the subject is Toyota RAV4, compare to Toyota / Lexus aggregate). If `tracked_tickers` is non-empty, also surface the subject's rank within the cohort.
- **W2** — EV vs ICE explicit comparison; or top-vs-bottom segment delta.
- **W3** — compare the user's `tracked_tickers` cohort distribution to the full top-25 ranking; flag tickers where the cohort's tier distribution skews worse than the full ranking.
- **W5** — compare the subject brand's models' parity status to the cohort's overall direction tally.

When the comparison axis is missing (e.g., no `tracked_tickers` in profile),
surface a Data Quality (f) event documenting the deferred comparison.

---

## Data Quality Notes (OPTIONAL — when non-empty)

Render as a compact bulleted list with typed prefixes `(a)` through `(g)`
matching the SKILL.md taxonomy. The typed prefix is **required** — without
it the audit log is only prose, not machine-readable.

```
Data Quality Notes
- (a) get_sold_summary <period_label> failed (network_422); period omitted from curve.
- (a1) Facet-discovery retry: "toyota" → "Toyota" on get_sold_summary.
- (b) Truncation envelope unwrapped via parse_sold_summary --file.
- (c) Make resolved by fuzzy match: "Mercedes Benz" → "Mercedes-Benz" (user-confirmed).
- (d) Ticker mapping miss for Subaru — bucketed as [no tracked ticker].
- (e) MSRP-anchor path disabled in v1.0.0; W1 uses prior-period anchor only.
- (f) Hybrid pass skipped because user did not request it.
- (g) Wave split into 2 sub-batches (3 + 3) due to 5-concurrent rate-limit ceiling.
```

If the event log is empty, **omit this section entirely** — do not render
an empty header.

---

## Key Signals (always — 3 to 5 bullets)

Workflow-specific bullets that highlight the non-obvious investment
takeaway. Examples:

- W1: *"Annualized rate of 18.6%/yr on this make/model exceeds the SUV segment average of 12.4%/yr — concentration risk if [TICKER]'s retail mix skews to this model."*
- W2: *"⚠ EV portfolio risk: EVs depreciating 1.8× faster than ICE; BEARISH on TSLA / RIVN / LCID and on legacy OEMs' EV portfolios."*
- W3: *"<make> [<TICKER>] dropped T1 → T2 over 6 months (-2.3% retention); BEARISH read on the ticker's used-vehicle gross margin contribution."*
- W5: *"<model> [<TICKER>] deepening discount: now -4.2% vs -1.5% prior period — incentive bite intensifying; BEARISH for near-term OEM gross margin."*

Rules:
- W1 always surfaces the BULLISH/BEARISH/NEUTRAL/CAUTION investment verdict as the leading bullet.
- Every bullet must cite a number from the script outputs — never invent a metric.
- When the workflow's findings produce a ticker-level MIXED verdict, dedicate one bullet to the split (which makes BULLISH vs which BEARISH).

---

## Investment Thesis (always — persona-tailored)

Tailor the thesis to the analyst's role. The skill renders one sentence
per persona. Surface the persona named in `profile.analyst.focus` first
(when set):

```
OEM equity (BULLISH/BEARISH for the ticker):
  <one sentence on residual / pricing-power / incentive-spend implication
   for the most-affected OEM ticker(s)>

Auto lending / leasing equity:
  <one sentence on collateral erosion / residual-restatement risk for the
   ALLY / COF / KMX-residuals / public leasing-stock cohort>

Dealer-group equity:
  <one sentence on used-car gross-margin implication for the AN / LAD / PAG
   / SAH / GPI / ABG / KMX / CVNA cohort, where used-vehicle GPU is a
   primary earnings driver>
```

When `profile.analyst.focus == "lending"`, the lending sentence leads.
When `focus == "oem"`, the OEM sentence leads (default ordering).
When `focus == "dealer_groups"`, the dealer-group sentence leads.

Quantify the business impact where possible:

- "1% monthly acceleration on a $30K vehicle = ~$300/month additional collateral exposure per loan."
- "Every 1% error on a 36-month lease residual = ~$100-150 in unrecovered value at turn-in."
- "Used-vehicle GPU swings of $300-500 per unit at scale dealer groups translate to ~$50-80M annual EBIT for an AN-scale operator."

(Quantitative anchors lifted from depreciation-tracker domain conventions
documented in the dealer-side reference's `outcomes.md`.)

---

## Self-check (internal — never render as a grid)

12-item verification checklist. Run each silently before returning.

1. **Profile loaded** — first line is `Using profile: ...` (or `Using profile context: ...` when no profile).
2. **Country routing applied** — US → workflows; non-US → halt per `references/country-uk.md`.
3. **`inventory_type` explicitly set** on every `get_sold_summary` call (`Used` or `New`, never omitted).
4. **`limit=5000`** set on every `get_sold_summary` call.
5. **`ranking_dimensions` minimal** — never the default 3-dim (`make,model,body_type`); use the per-workflow value documented in `references/sold-summary-safety.md`.
6. **`dealer_type` NOT passed** on any `get_sold_summary` call (silent data-suppression hazard).
7. **Date windows month-aligned** — every call's dates come from `compute_period_windows.py`.
8. **Sub-batch ceiling honored** — any wave > 5 calls split into ≤5 per agent message (W2 EV+ICE+Hybrid only).
9. **Tier / verdict thresholds consistent** with `references/tier-and-verdict-bands.md`.
10. **Investment-signal mapping consistent** with `references/signal-aggregation.md` — every BULLISH / BEARISH / NEUTRAL / CAUTION call routed through `aggregate_signals.py`.
11. **Ticker overlay applied** — every per-make / per-row finding mapped via `references/ticker-mapping.md`; unmapped makes surfaced as `[no tracked ticker]` + DQ event (d).
12. **Pipeline executed** — every rendered numeric block came from a Python script (no hand math). When the script was bypassed (script error, manual fallback, or hand-rolled cells), the rendered table **must** prefix with `⚠ pipeline bypassed; manual computations may diverge from canonical thresholds` and the footer must list this as a `⚠` line.

Render rule at response time:

- **All applicable checks pass** → emit a single footer line listing 5-7 items exercised, e.g.:
  `✓ Verified: profile, US-only routing, sold-summary safety (limit=5000, inventory_type set), month-aligned dates, ticker overlay, verdict band consistent.`
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated to compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.

---

## Render variations matrix — which blocks per workflow

| Block | W1 | W2 | W3 | W5 |
|---|---|---|---|---|
| First line (`Using profile`) | ✓ | ✓ | ✓ | ✓ |
| Analysis Summary | ✓ | ✓ | ✓ | ✓ |
| Year scope qualifier | ✓ | — | — | — |
| Headline | ✓ | ✓ | ✓ | ✓ |
| Workflow Table | ✓ (mode=curve) | ✓ (mode=segment, possibly ×2) | ✓ (mode=brand) | ✓ (mode=parity) |
| Tier / Verdict block | ✓ | ✓ | ✓ | ✓ |
| Ticker Impact Summary | ✓ | ✓ | ✓ | ✓ |
| Comparison Context | ✓ | ✓ | ✓ | ✓ |
| Data Quality Notes | ✓ (when non-empty) | ✓ | ✓ | ✓ |
| Key Signals | ✓ (3-5) | ✓ | ✓ | ✓ |
| Investment Thesis | ✓ | ✓ | ✓ | ✓ |
| Self-check footer | ✓ | ✓ | ✓ | ✓ |

---

## Money format

- US analyst profiles: `$` prefix, comma thousands, no decimals. `$28,500`.
- Percentages: one decimal in the body. **Two decimals in the Headline and Verdict block when the absolute value falls within 0.05% of any acceleration-band boundary** (0.3, 0.6, 1.0, 1.5). Avoids visual ambiguity at band edges. Examples: `+0.32%/month` in Headline when rate is 0.323; `+1.5%/month` (one decimal) when rate is 1.7 (well clear of any edge).
- Tickers always in upper case, brackets around: `[F]`, `[TM]`, `[STLA]`.
- Missing ticker rendered: `[no tracked ticker]`.

---

## Unsupported countries

- **All non-US (UK, CA, others)**: halt per `references/country-uk.md`. No workflow can produce honest output because `get_sold_summary` has no non-US variant.
