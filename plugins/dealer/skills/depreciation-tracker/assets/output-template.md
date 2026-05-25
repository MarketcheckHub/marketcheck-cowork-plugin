# Output Template — Depreciation Tracker

This file is the **single source of truth** for output block structure,
table schemas, verdict / tier wording, and the internal self-check across
all five workflows. Every workflow renders by adapting this template — see
the "Render variations" matrix at the end for which blocks each workflow
uses.

Placeholders in angle brackets `<...>` are interpolated from the parser /
script outputs. Optional blocks are marked `(OPTIONAL)` and only render
when the precondition holds.

---

## First line (always)

```
Using profile: <dealer.name or "guest">, <state>, <country>
```

When there is no profile (depreciation-tracker accepts guest queries with
just a state), render: `Using profile context: <state>, US`.

---

## Analysis Summary (always)

```
Workflow:        W<N> — <name>   (e.g. "W1 — Make/Model Depreciation Curve")
Scope:           <make> <model>  |  <segment>  |  <STATE>  |  <inventory_type>
Year scope:      across all model years (per get_sold_summary scope)   ← W1, W4
Period:          <date_from> to <date_to>  (single period)             ← W4
                 OR
                 <oldest_period.label> to <newest_period.label>        ← W1 multi-period
                 (e.g. "1yr ago to current")
Prior anchor:    <prior_period_offset> months back                     ← W2 / W3 / W5
```

---

## Headline (always)

One sentence. Workflow-specific phrasing.

### W1 (Make/Model Depreciation Curve)

When `anchor_used == "msrp"`:

```
<make> <model> retained <retention_pct_msrp>% of MSRP after <months_offset> months,
depreciating at <recent_monthly_rate>%/month — <verdict>.
```

When `anchor_used == "prior_period"`:

```
<make> <model> sold-summary average dropped from $<oldest_avg> to $<newest_avg>
over <months_span> months (<recent_monthly_rate>%/month) — <verdict>.
```

`<verdict>` is one of the 5 W1 acceleration bands per
`references/tier-and-verdict-bands.md` — Strong Retention / Stable / Slight
Decline / Moderate Depreciation / Accelerated Loss.

### W2 (Segment Value Trends)

```
Across <STATE> over the last <prior_period_offset> months, the strongest-retention
segment is <top.key> ({+/-X.X}%); the weakest is <bottom.key> ({+/-X.X}%).
```

When fuel-type pass ran, append: `EV vs ICE: EV depreciated <pct>% vs ICE
<pct>% — <ratio>x faster than ICE.`

### W3 (Brand Residual Ranking)

```
T1 leaders: <top-3 makes>. Largest tier-jump down: <make> dropped from T<X> → T<Y>.
<count> brands in T1; <count> in T4.
```

### W4 (Geographic Depreciation Variance)

```
<make> <model> in <STATE> trades at <state_index>% of national average
($<state_avg> vs $<national_avg>); top premium markets: <top 3 states>;
top discount markets: <bottom 3 states>.
```

### W5 (MSRP Parity Tracker)

```
<above_count> models above sticker, <below_count> below. Largest current
premium: <model> (+X.X% over MSRP). Newly flipped below MSRP this period:
<list of make_models>.
```

When no flips, the second sentence becomes: `No models flipped above ↔
below MSRP this period.`

---

## Workflow Table (always — rendered via render_depreciation_table.py)

```
render_depreciation_table.py --mode <m> --input <path> --currency '$|£'
```

Modes by workflow:

| Workflow | --mode | Input source | Columns rendered |
|---|---|---|---|
| W1 | `curve` | depreciation_curve.py output | Period · Avg Sale Price · Sold Count · Retention % (vs MSRP — only when anchor_used="msrp") · Retention % (vs Prior) · Monthly Rate · Annualized Rate |
| W2 | `segment` | segment_compare.py output | Body_Type or Fuel_Type · Current Avg · Prior Avg · Price Δ% · Volume Δ% · Current Sold · Classification |
| W3 | `brand` | brand_retention.py output | Rank · Make · Current Avg · Prior Avg · Retention % · Volume · Tier |
| W4 | `geo` | geo_variance.py output | State · Avg Sale Price · Price Index · Premium/Discount $ · Sold Count · Classification |
| W5 | `parity` | msrp_parity.py output | Make/Model · Current % vs MSRP · Prior % · Δ % · Avg Price · Volume · Status · Direction |

Currency is `$` for US, `£` for UK. Depreciation-tracker is US-only, so
always `$`.

Renderer reads pre-computed fields from each script's output JSON. Never
re-implement script logic during rendering. When the script fails or the
input JSON is malformed, the agent's output **must** prefix the table with
`⚠ table renderer bypassed; manual cells may diverge from canonical
formatting` and emit a self-check warning.

---

## Tier / Verdict Block (always)

W1 / W2 / W5 — surface the Headline's verdict / classification verbatim:

```
Verdict: **<5-band verdict>**   (most-recent monthly rate: <signed pct>)
Curve shape: **<shape>**         (longest-window monthly rate: <signed pct>)
```

W3 — tier counts:

```
Tier counts: T1 <count> · T2 <count> · T3 <count> · T4 <count>
```

W4 — geographic classification rollup:

```
Premium markets (>105 index):   <count>
Average markets (95–105):       <count>
Discount markets (<95):         <count>
```

W5 — direction tally:

```
Above sticker:    <count>
Below sticker:    <count>
Newly flipped below MSRP:  <list>
Newly flipped above MSRP:  <list>
Deepening discounts:       <list>
```

---

## Comparison Context (always)

At least one cross-axis comparison. Required even when the workflow is
single-cut:

- W1 — compare the subject's monthly rate to the W1 verdict-band median for
  this segment, OR (if available from a prior W2 run) to the body_type
  segment average.
- W2 — EV vs ICE explicit comparison; or top-vs-bottom segment delta.
- W3 — compare the user's profile `franchise_brands` (when supplied) to
  their tier rank in the table.
- W4 — compare profile state to national average + top-5 / bottom-5 spread.
- W5 — compare profile `franchise_brands` (when supplied) to the parity
  rankings.

When the comparison axis is missing (e.g., no franchise_brands in profile
for W3), surface a Data Quality (g) event documenting the deferred
comparison.

---

## Data Quality Notes (OPTIONAL — when non-empty)

Render as a compact bulleted list with typed prefixes `(a)` through `(g)`
matching the SKILL.md taxonomy. The typed prefix is **required** — without
it the audit log is only prose, not machine-readable.

```
Data Quality Notes
- (a) get_sold_summary <period_label> failed (network_422); period omitted from curve.
  Follow-up: investigate date alignment if this recurs.
- (a1) Facet-discovery retry: "toyota" → "Toyota" on get_sold_summary.
- (b) Truncation envelope for decode_vin_neovin unwrapped via --file.
- (e) MSRP-anchored retention unavailable (rep listing carried no MSRP and
  decode failed); fell back to prior-period anchor.
- (g) Wave B decode skipped because rep listing already carried MSRP.
```

If the event log is empty, **omit this section entirely** — do not render
an empty header.

---

## Key Signals (always — 3 to 5 bullets)

Workflow-specific bullets that highlight the non-obvious takeaway. Examples:

- W1: *"Annualized rate of 18.6% on this make/model exceeds the SUV
  segment average of 12.4% — concentration risk if your loan portfolio
  skews this model."*
- W2: *"⚠ EV portfolio risk: EVs depreciating 1.8× faster than ICE; consider
  EV-specific residual curves rather than blended auto residuals."*
  (per `references/outcomes.md` lines 14-15)
- W3: *"<make> dropped from T1 to T2 over 6 months (-2.3% retention); review
  concentration."*
- W4: *"<adjacent state> trades at 9% premium vs profile state — cross-border
  arbitrage opportunity for inventory sourcing."*
- W5: *"<model> deepening discount: now -4.2% vs -1.5% prior period — incentive
  bite or oversupply."*

Rules:
- W1 always surfaces the verdict band as the leading bullet.
- Every bullet must cite a number from the script outputs — never invent a
  metric.

---

## Recommendation (always — persona-tailored)

Tailor the recommendation to the user's role, drawing from
`references/outcomes.md` action-to-outcome funnel:

```
Lender:    <residual / advance-rate adjustment based on the verdict>
OEM:       <incentive / production / CPO-program implication>
Appraiser: <trend adjustment to apply when valuing this make/model>
```

Provide one sentence per persona. Quantify the business impact:
- "1% monthly acceleration on a $30K vehicle = $300/month additional
  exposure per loan" (per outcomes.md line 5).
- "Every 1% error on a 36-month lease = ~$100-150 in unrecovered value at
  turn-in" (line 7).

---

## Self-check (internal — never render as a grid)

12-item verification checklist. Run each silently before returning.

1. **Profile loaded** — first line is `Using profile: ...` (or
   `Using profile context: ...` for guest queries).
2. **Country routing applied** — US → workflows; UK → halt per
   `references/country-uk.md`; CA → halt per SKILL.md.
3. **`inventory_type` explicitly set** on every `get_sold_summary` call
   (`Used` or `New`, never omitted).
4. **`limit=5000`** set on every `get_sold_summary` call.
5. **`ranking_dimensions` minimal** — never the default 3-dim
   (`make,model,body_type`); use the per-workflow value documented in
   `references/sold-summary-safety.md`.
6. **`dealer_type` NOT passed** on any `get_sold_summary` call (silent
   data-suppression hazard).
7. **Date windows month-aligned** — W1/W2/W3/W5 dates from
   `compute_period_windows.py`; W4 dates from `compute_sold_summary_dates.py`.
8. **Anchor source named in Headline** — W1 names "MSRP" or "prior-period".
9. **Tier thresholds consistent** with `references/tier-and-verdict-bands.md`
   (T1 ≥ 98, T2 ≥ 95, T3 ≥ 90, T4 < 90).
10. **Verdict band consistent** with `references/tier-and-verdict-bands.md`
    (5 bands; recent monthly rate determines W1 band).
11. **Data Quality event log** surfaced when non-empty; omitted when empty.
12. **Pipeline executed** — every rendered numeric block came from a Python
    script (no hand math). When the script was bypassed (script error,
    manual fallback, or hand-rolled cells), the rendered table **must**
    prefix with `⚠ pipeline bypassed; manual computations may diverge from
    canonical thresholds` and the footer must list this as a `⚠` line.

Render rule at response time:

- **All applicable checks pass** → emit a single footer line listing 5–7
  items exercised, e.g.:
  `✓ Verified: profile, US-only routing, sold-summary safety (limit=5000, inventory_type set), month-aligned dates, anchor source, tier/verdict band consistent.`
- **Any check fails** → emit failures only, one per line, prefixed `⚠`,
  with a one-line note on what was corrected or caveated to compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.

---

## Render variations matrix — which blocks per workflow

| Block | W1 | W2 | W3 | W4 | W5 |
|---|---|---|---|---|---|
| First line (`Using profile`) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Analysis Summary | ✓ | ✓ | ✓ | ✓ | ✓ |
| Year scope qualifier | ✓ | — | — | ✓ | — |
| Headline | ✓ | ✓ | ✓ | ✓ | ✓ |
| Workflow Table | ✓ (mode=curve) | ✓ (mode=segment, possibly ×2) | ✓ (mode=brand) | ✓ (mode=geo) | ✓ (mode=parity) |
| Tier / Verdict block | ✓ (verdict + curve shape) | ✓ (verdict per-pass) | ✓ (tier counts) | ✓ (premium/avg/discount counts) | ✓ (status + direction tallies) |
| Comparison Context | ✓ | ✓ | ✓ | ✓ | ✓ |
| Data Quality Notes | ✓ (when non-empty) | ✓ | ✓ | ✓ | ✓ |
| Key Signals | ✓ (3–5) | ✓ | ✓ | ✓ | ✓ |
| Recommendation | ✓ | ✓ | ✓ | ✓ | ✓ |
| Self-check footer | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Money format

- US profiles: `$` prefix, comma thousands, no decimals. `$28,500`.
- Percentages: one decimal in the body. **Two decimals in the Headline and
  Verdict block when the absolute value falls within 0.05% of any
  acceleration-band boundary** (0.3, 0.6, 1.0, 1.5). Avoids visual ambiguity
  at band edges. Examples: `+0.32%/month` in Headline when rate is 0.323;
  `+1.5%/month` (one decimal) when rate is 1.7 (well clear of any edge).
- Miles: comma thousands, no unit needed inside the table; suffix ` mi` in
  prose. `45,000` in the table; `45,000 mi` in narrative.

---

## Unsupported countries

- **UK**: halt per `references/country-uk.md`.
- **CA**: halt per SKILL.md country-routing rule. Re-evaluate when
  MarketCheck ships Canadian sold-summary data.
