# Output Template — W2 Batch Competitive Scan

Single source of truth for the W2 (Batch Competitive Scan) workflow's rendered output. The sister file `assets/output-template.md` covers W1 / W3 / W4 / W5; W2 has its own template because the per-VIN card + portfolio rollup structure does not map cleanly onto W1's deep-diagnostic block layout.

W2 is **batch overview / triage**: 3–5 VINs at once, deterministic per-VIN verdict (quartile-anchored against the local active-listing distribution), portfolio rollup. For sold-anchored verdicts, `sold_dom_median` days-to-sell, MoS context, and full diagnostic depth, the dealer routes the VIN to W1 via `/price-check <VIN>`.

Placeholders in angle brackets `<...>` are interpolated from `parse_decode.py`, `parse_predict.py`, `parse_search.py`, and `comp_stats.py` outputs. Optional sub-blocks are marked `(OPTIONAL)` and only render when their precondition holds.

---

## First line (always)

```
Using profile: <dealer.name>, <ZIP or postcode>, <country>
Batch scope: <N_total> VINs · radius <radius_mi> mi · car_type <car_type>
```

If any VINs were dropped at pre-check (mileage missing, asking missing, or user explicitly skipped), include a third line:

```
Pre-check drops: <N_skipped> VIN(s) — see Data Quality Notes for details.
```

---

## Per-VIN card (rendered N_reported times — only for VINs that survived pre-check)

Every reported VIN has a valid VIN, mileage, and asking_price (guaranteed by W2's pre-Wave-A completeness check; see `references/w2-batch-scan.md` section C). The per-VIN card is a fixed structure with one optional sub-block (CPO Premium when subject is CPO).

```
─── [<i>/<N_reported>] <year> <make> <model> <trim>  ·  VIN: <vin> ───
Asking: $<asking_price>  ·  Mileage: <miles> mi  ·  Channel: <PRIMARY> dealer  ·  CPO: <yes|no>

Decoded Specs
  Body <body_type> · Drive <drivetrain> · Engine <engine> · Trans <transmission> · MSRP $<msrp>

Predicted Prices (ML)
  <PRIMARY>   non-CPO:    $<nocpo_primary.marketcheck_price>   (comp_n=<comparables_n>, recent_n=<recent_comparables_n>)
  <CONTEXT>   non-CPO:    $<nocpo_context.marketcheck_price>   (comp_n=<n>, recent_n=<n>)
  [when CPO]
  <PRIMARY>   CPO:        $<cpo_primary.marketcheck_price>     (comp_n=<n>, recent_n=<n>)
  <CONTEXT>   CPO:        $<cpo_context.marketcheck_price>     (comp_n=<n>, recent_n=<n>)
  CPO Premium (<PRIMARY>): +$<premium_primary>  (<pct_primary, 1dp>%)  ·  Net Margin (after $<certification_cost> cert): +$<net_margin_primary>

Active Local Market (n=<active_count>; source: server)
  Price:    min $<price.min> | p25 $<price.p25> | median $<price.median> | p75 $<price.p75> | max $<price.max>  (mean $<price.mean>, sd $<price.stddev>)
  Miles:    min <miles.min> | median <miles.median> | mean <miles.mean> | max <miles.max>
  DOM:      min <dom_active.min> | p25 <dom_active.p25> | median <dom_active.median> | p75 <dom_active.p75> | max <dom_active.max>  (active server-wide; current-listing time-on-lot)

Your Price vs Market
  vs <PRIMARY> ML:        <±$diff>  (<±pct, 1dp>%)
  vs Active Median:       <±$diff>  (<±pct, 1dp>%)
  Percentile (active):    <Nth percentile>  (<exact|approx|bounded> · server)

Verdict: <Below / Modestly Below / At / Modestly Above / Above Market>
  Anchored on active-listing quartile distribution (n=<active_count>).
Action: <one-line band-template recommendation — see "Action templates" below>

[when shadow listing detected — parse_search.filtered_out.self_vin_match > 0]
⚠ Shadow listing: subject VIN found at <shadow_dealer_name> ($<shadow_price>, dom <shadow_dom>, <shadow_distance> mi). Confirm consignment vs stale data.
─────────────────────────────────────────────────
```

### Card field sources

| Field | Source |
|---|---|
| `<year> <make> <model> <trim>`, `body_type`, `drivetrain`, `engine`, `transmission`, `msrp` | `parse_decode.specs` |
| `vin`, `asking_price`, `miles`, CPO `yes/no` | user-supplied per-VIN inputs |
| `<PRIMARY>` / `<CONTEXT>` labels | `profile.session.dealer_type_title` (mapped to "Franchise" / "Independent") |
| `nocpo_primary.marketcheck_price`, `comparables_n`, `recent_comparables_n` etc. | `parse_predict.py` outputs (one per role) |
| `cpo_primary.marketcheck_price` etc. | `parse_predict.py` outputs (CPO branch) |
| `CPO Premium`, `Net Margin (after cert)` | `comp_stats.marketcheck_predict.{premium_primary, pct_primary, net_margin_primary, certification_cost}` — **never hand-computed** (cpo.md ban) |
| `Active Local Market` Price block | `parse_search.stats.price` (server-wide aggregate over `num_found`) |
| `Active Local Market` Miles block | `parse_search.stats.miles` (server-wide) |
| `Active Local Market` DOM block | `parse_search.stats.dom_active` (server-wide; `dom_active` semantic per `references/w1-price-check.md` step 4 — current-listing time-on-lot) |
| `vs <PRIMARY> ML` | `(asking_price − nocpo_primary.marketcheck_price) / nocpo_primary.marketcheck_price * 100` (mechanical, deterministic) |
| `vs Active Median` | `comp_stats.gap_vs_median.{diff, pct}` |
| `Percentile (active)` | `comp_stats.percentile`, `percentile_source`, `percentile_approx`, `percentile_bounded` |
| `Verdict` | `comp_stats.verdict_quartile` (W2 always uses quartile anchor; sold-anchor inputs are nulled by design) |
| `Action` | one of 5 quartile-anchored band templates below |
| Shadow listing line | `parse_search.filtered_out.self_vin_match > 0`; dealer/price/dom from the matched-shadow listing's pre-filter row |

### CPO Premium sub-block — render conditions

Render the CPO Premium / Net Margin lines under Predicted Prices **only when**:
- Subject is CPO (per the pre-Wave-A CPO batch prompt's per-VIN answer), AND
- All 4 predict roles (`nocpo_primary`, `nocpo_context`, `cpo_primary`, `cpo_context`) returned `ok=true`, AND
- `comp_stats.marketcheck_predict.premium_primary` is non-null.

When any of those preconditions fail, omit the CPO Premium line and emit DQ event (a) noting the affected role's `error_type`. The other Predicted Prices lines render whatever is available (degraded gracefully per `references/cpo.md` lines 128–133).

### Percentile rendering — four-state, driven by comp_stats fields

| `percentile_source` | `percentile_approx` | `percentile_bounded` | Render |
|---|---|---|---|
| `server` | `False` | `null` | `<N>th percentile (exact, server over <active_count> comps)` |
| `server` | `True` | `null` | `~<N>th percentile (approx, server over <active_count> comps)` + footnote: *"Approx: user_price falls outside the server's known p5–p99 breakpoints; interpolation is coarse in this regime."* |
| `client` | (any) | non-null | `<low>th – <high>th percentile (bounded — visible <n> of <active_count>)` + footnote: *"Server stats unavailable for this VIN's market; rank bounded over visible <n> comps. True rank lies within the displayed range."* |
| `client` | (any) | `null` | `<N>th percentile (visible set, n=<n>)` |

For W2, `percentile_source = "server"` is the common path (because Wave B always passes `stats="price,miles,dom_active"`). Client/bounded states fire only when `num_found < min_n` (thin market).

### Spec subtitle on the `Decoded Specs` line — heterogeneity rule

W2's Decoded Specs is a single line; no per-row spec subtitles (since W2 doesn't render a comp table per VIN). The four spec fields (`body_type`, `drivetrain`, `engine`, `transmission`) come from `parse_decode.specs` and are pinned at decode time — they are NOT used as filter parameters and NOT compared across comps.

### Money format

US profiles: `$` prefix, comma thousands, no decimals (e.g. `$28,500`). UK profiles: `£` prefix, same format. Percentages: 1 decimal place in the body, 2 decimals only when within 0.5% of a band boundary (W1's near-edge convention; rarely needed in W2 since the action templates always include `<diff_to_median>` directly).

---

## Portfolio Summary (always — at the end of the run)

```
═══════════ Portfolio Summary ═══════════
VINs scanned:   <N_total>     Skipped at pre-check:  <N_skipped>   Reported:  <N_reported>

Action priority (largest absolute gap first):
  1. <vin>: <verdict>, <±$gap_vs_ml_primary> vs <PRIMARY> ML — <action sentence>
  2. <vin>: ...
  ...

Distribution (quartile-anchored against per-VIN active set):
  Above market   (above upper IQR fence):     <count_above>      VINs
  Modestly Above (p75 < x ≤ upper fence):     <count_mod_above>  VINs
  At market      (p25 ≤ x ≤ p75):              <count_at>         VINs
  Modestly Below (lower fence ≤ x < p25):      <count_mod_below>  VINs
  Below market   (below lower IQR fence):     <count_below>      VINs

[render only when count_above + count_mod_above >= 1]
Estimated headroom-recovery (overpriced units adjusted to <PRIMARY> ML):
  Total upside: $<headroom_sum>   ·   Average per VIN: $<headroom_avg>   ·   N-units: <count_above + count_mod_above>

[render only when count_below + count_mod_below >= 1]
Estimated under-pricing exposure (underpriced units below <PRIMARY> ML):
  Total: $<underpricing_sum>   ·   Average per VIN: $<underpricing_avg>   ·   N-units: <count_below + count_mod_below>
```

### Rollup formulas

- **Action priority sort**: descending by `abs(asking_price - nocpo_primary.marketcheck_price)`. Every reported VIN has an `asking_price` (guaranteed by pre-check).
- **Headroom-recovery formula**: `sum_over_VINs(asking_price - nocpo_primary.marketcheck_price)` where the per-VIN verdict is in `{Above Market, Modestly Above Market}`. Both bands cross the p75 IQR fence and represent units a market-participant buyer would discount to clear.
- **Under-pricing exposure formula**: `sum_over_VINs(nocpo_primary.marketcheck_price - asking_price)` where the per-VIN verdict is in `{Below Market, Modestly Below Market}`. Both bands sit below p25 and represent margin left on the table.
- **Average per VIN**: total ÷ N-units, rounded to nearest dollar.
- **N-units**: count of VINs included in that direction's sum.

When a direction's count is zero, omit the entire sub-block (don't render `Total: $0`).

---

## Aggregated Data Quality Notes (OPTIONAL — only when non-empty)

W2's per-VIN flow generates many DQ events (truncation unwraps, shadow listings, etc.). Aggregate them across the batch rather than rendering per-VIN copies:

```
Data Quality Notes
- (a) MCP tool errors recovered: <total_count> across <vin1, vin2, ...>. <details by tool/error_type>
- (a1) Facet-discovery retries: skipped by design (W2 doesn't run facet retry; emits this event when num_found=0 on any VIN's search — those VINs' verdict blocks render as "Insufficient comps").
- (b) Truncation envelope unwraps: <total_count> across decode (<n>), predict (<n>), search (<n>).
- (c) Shadow listings detected: <list of (VIN, dealer_name, distance_mi)>.
- (d) Dropped at pre-check: <list of (VIN, reason)>. Reasons: missing_mileage, missing_asking, malformed, user_skip.
- (e) Fallback source: <count> per-VIN cards used client-bounded percentile because num_found < 6.
- (g) Workflow branches skipped by design (W2 architectural):
    - sold-90d × 3 calls (verdict source is quartile, not sold_anchor)
    - get_sold_summary state baseline
    - get_car_history (CPO post-hoc detection)
    - drop scan (price_change="negative")
    - desc tail-pull (W2 trusts server stats over full num_found)
    - facet-discovery retry on num_found==0 (per-VIN verdict degrades to "Insufficient comps")
    - per-VIN CPO branch decisions: <list of (VIN, run|skipped, reason)>
```

If the event log is empty, omit the entire section (do not render an empty header). Per-VIN rendering of (c) shadow flags happens inline in the per-VIN card; the aggregated (c) line above is for the rollup summary.

---

## Footer

```
Per-VIN verdicts are quartile-anchored against the local active-listing distribution. For sold-anchor reconciliation, days-to-sell estimates, Months-of-Supply context, market-wide drop-rate signals, or full per-VIN diagnostic depth, route the VIN through W1: `/price-check <VIN>`.

✓ Verified: profile, dual pricing per VIN, server-stats anchor, subject-VIN exclusion, cross-batch exclude_vins, quartile bands.
```

When any per-VIN failure tripped the self-check (decode failed, all 4 predicts ok=false, etc.), replace the `✓ Verified:` line with one or more `⚠` lines, one per failure:

```
⚠ VIN <vin>: <failure description>
⚠ VIN <vin>: <failure description>
```

The footer is **one block per batch**, not per VIN. All per-VIN failures aggregate into the warning lines above.

---

## Action templates (quartile-anchored — distinct from W1's sold_anchor templates)

| Verdict | Action template |
|---|---|
| Below Market | `"Raise to ~$<p25> to clear the IQR floor — current ask is below the lower fence ($<lower_fence>); buyers will assume a defect or hidden cost."` |
| Modestly Below Market | `"Hold or raise toward $<median> — under-priced by $<diff_to_median> vs the local median; you're priced to move."` |
| At Market | `"Hold — centered in the IQR ($<p25>–$<p75>). <X>% of visible comps have price-dropped recently — monitor."`  *(omit the drop-rate clause when `drops_in_set == 0`)* |
| Modestly Above Market | `"Consider $<diff_to_median> cut toward median ($<median>) — ask sits above p75 ($<p75>) but within the upper IQR fence."` |
| Above Market | `"Cut to upper fence ($<upper_fence>) or below — current ask is beyond the IQR, signals over-pricing."` |

### Template field sources

- `p25 / median / p75 / max / mean / stddev` come from `comp_stats.quartile`.
- `lower_fence = p25 − 1.5·IQR`, `upper_fence = p75 + 1.5·IQR` (mirrors `comp_stats.IQR_FENCE_MULTIPLIER = 1.5`). These are computed client-side at render time from `comp_stats.quartile.p25` and `comp_stats.quartile.p75` — the renderer does not invent IQR multipliers.
- `diff_to_median = abs(asking_price − comp_stats.quartile.median)`.
- `<X>% (drop-rate clause)` = `comp_stats.drop_rate_visible * 100`, rounded to the nearest integer percent. The clause is omitted when `comp_stats.drops_in_set == 0`.

Templates **never reference `sold_dom_median`** because W2 doesn't fetch sold-90d data. The escape-hatch in the Footer ("route the VIN through W1") tells the dealer where to find days-to-sell context if they need it. Never invent a days-to-sell number from model knowledge.

### Thin-market degraded action

When `comp_stats.insufficient == true` (i.e. `active_count < min_n`, default 6), skip the Verdict + Action block entirely for that VIN and render:

```
Verdict: Insufficient comps — n=<active_count> < <min_n> in <radius_mi>mi radius.
Action: Re-check pricing once local supply rebuilds; or route this VIN to W1 (`/price-check <VIN>`) for a sold-anchor verdict that's less sensitive to active comp thinness.
```

This matches the thin-market degraded path in `comp_stats.py`.

---

## DOM "Active" line under Active Local Market — render details

The new `DOM:` line under the Active Local Market block reads `parse_search.stats.dom_active` (server-wide aggregate over the full `num_found` set, not just the visible 10 rows). The line is W2-specific (W1 doesn't render this — W1 has Sold-90d DOM via `search_past_90_days stats="dom_active"` instead).

When the server response omits `stats.dom_active` (rare; happens when `search_active_cars` returned an error for the stats compute), render:

```
DOM:      unavailable (server stats absent — see DQ event (e))
```

Then emit DQ event (e): *"Fallback source: dom_active server stats absent for VIN <vin>; per-listing dom_active still available in the comp set."*

Never substitute `dom_180` or lifetime `dom` here — those are different market-presence semantics (seasonal cycle and cross-dealer accumulator respectively, per `references/w1-price-check.md` step 4). The `Active DOM` line is `dom_active` only.

---

## Render variations within W2

W2 has only one workflow shape (batch overview), so the render structure is fixed. Variations are limited to:

| Condition | Effect |
|---|---|
| Subject is CPO | CPO Premium sub-block under Predicted Prices renders |
| Subject is non-CPO | CPO Premium sub-block omitted (only non-CPO Predicted Prices lines) |
| Shadow listing detected for this VIN | `⚠ Shadow listing` line at the bottom of the per-VIN card |
| `num_found < min_n` for this VIN | Verdict block degrades to "Insufficient comps" |
| Pre-check drops > 0 | Header gets a third line; rollup includes `Skipped at pre-check` count; DQ event (d) lists the dropped VINs |
| Any per-VIN check fails (decode/predict/search ok=false) | Per-VIN card renders the affected sub-blocks as `unavailable (<error_type>)`; Self-check footer shifts from `✓` to `⚠` lines |

W2 does **NOT** have:
- Same-Channel View block (W1 only — W2 doesn't render `channel_stats` since the per-VIN card is space-constrained for batch readability)
- Outliers block (W1 only)
- Market Snapshot block (subsumed by per-VIN Active Local Market line)
- Headline (the per-VIN "Verdict + Action" lines fill that role)
- Per-VIN comp table (omitted to keep the per-VIN card compact; dealer can route to W1 for full comp table)
- Drop-rate market-wide line (W2 doesn't fire the drop-scan call)
- State Baseline (W2 doesn't fire `get_sold_summary`)
- MoS line (W2 doesn't fire sold-90d)

These omissions are by design — the dealer's mental model for W2 is "walk-around triage", not "stethoscope per VIN". When they need depth on a specific VIN, the Footer points them at W1.

---

## Self-check (internal — never render as a grid)

Run each item silently before returning the response. Render only the footer line (or `⚠` warnings).

1. **Profile loaded and confirmed on first line.**
2. **Country-routing applied.** US tools used; UK profiles halted at pre-check.
3. **Dual pricing shown per VIN** — both `<PRIMARY>` and `<CONTEXT>` non-CPO MarketCheck Prices rendered (and CPO equivalents when subject is CPO).
4. **CPO branch decision documented per VIN** — DQ event (g) entry shows which VINs ran CPO predicts and why.
5. **Pre-Wave-A completeness check enforced** — every reported VIN has a valid 17-char VIN, miles, and asking_price.
6. **Subject VIN excluded from comp set per VIN** — `parse_search.filtered_out.self_vin_match` was processed for each search; shadow listings flagged.
7. **Cross-batch exclusion applied** — every VIN's search passed `--exclude-vins <other batch VINs>`.
8. **Server-stats anchor verified** — `parse_search.stats.price` and `parse_search.stats.dom_active` present in every per-VIN search; falls back to client-bounded percentile only when `num_found < min_n`.
9. **Quartile verdict source** — every per-VIN `comp_stats.verdict_source == "quartile"` (sold-anchor inputs nulled by design).
10. **Pipeline executed for every VIN** — `parse_search.py` → `build_comp_stats_input.py` → `comp_stats.py` ran for every reported VIN. Hand-computed verdicts, percentiles, or gap_vs_median values would fail this check.
11. **Shadow listings emit DQ event (c)** — every per-VIN card with a shadow flag has a corresponding (c) entry in the rollup's aggregated Data Quality Notes.
12. **Action template matches verdict band** — the Action sentence uses the band's prescribed template (no free-form Action text).
13. **Footer renders one block** — single self-check footer at the end of the rollup, not per-VIN.

If all applicable checks pass → emit the `✓ Verified:` summary line in the Footer.

If any check fails → emit `⚠ VIN <vin>: <failure>` lines in the Footer (one per failure), and add an explanatory note: *"⚠ Some per-VIN checks failed — see Data Quality Notes for diagnostic details."*

Never render a pass-by-pass checkbox grid. The 13-item self-check is an internal guardrail.
