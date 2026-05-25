# Output Template — W2 Trade-In Quick Appraisal

Single source of truth for the W2 (Trade-In Quick Appraisal) workflow's rendered output. The sister file `assets/output-template.md` covers W1 / W3 / W4 / W5; W2 has its own template because the compact card structure does not map cleanly onto W1's full report layout.

W2 is **speed-pitch**: ≤25s wall clock for desk-side use. The output is a single compact card with the predicted retail / wholesale / spread / offer range, top 5 retail comparables, and a confidence band. For sold-anchor depth, sold transaction evidence, days-to-sell context, and a full appraisal report, route the VIN to W1 via `/full-appraisal <VIN>`.

Placeholders in angle brackets `<...>` are interpolated from `parse_decode.py`, `parse_predict.py`, `parse_search.py`, `comp_stats.py`, and `compute_appraisal_band.py` outputs.

---

## First line (always)

```
Using profile: <dealer.name>, <ZIP or postcode>, <country>
```

---

## Card  (always)

```
─── Trade-In Quick Appraisal ───
Vehicle: <year> <make> <model> <trim>  ·  VIN: <vin>  ·  Mileage: <miles> mi
Asking Price: $<asking_price>  (when supplied; else "—")  ·  CPO: <yes|no>  ·  Channel: <PRIMARY> dealer

Predicted Retail Value (Franchise):     $<marketcheck_predict.nocpo_primary.marketcheck_price>   (n=<comparables_n> active + <sold_count_90d> sold-90d)
Predicted Wholesale Value (Independent): $<marketcheck_predict.nocpo_context.marketcheck_price>   (independent dealer_type proxy)
Wholesale-to-Retail Spread:             +$<spread_$>  (<spread_pct>%)
Recommended Trade-In Offer:             $<offer_low>–$<offer_high>           (78–85% of Predicted Retail)

[when CPO]
Predicted Retail Value (Franchise CPO):  $<marketcheck_predict.cpo_primary.marketcheck_price>
Predicted Wholesale Value (Indep. CPO):  $<marketcheck_predict.cpo_context.marketcheck_price>
CPO Premium (Franchise):                +$<premium_primary>  (<pct_primary, 1dp>%)
Net Margin from CPO (after $<certification_cost> cert):  +$<net_margin_primary>

Top 5 Retail Comparables (sorted by price ascending)
<8-col comp table via render_comp_set_table.py — rows=5>

Recommended Value (condition-adjusted)
<low/mid/high block via render_appraisal_value_band.py>

Confidence: <Low|Medium|High>  (<comp_count_total> total comps)
[when condition was assumed Average]
⚠ Condition was not supplied — band assumes Average. Condition adjustment can shift mid ±$1,500.

[when shadow listing detected — parse_search.filtered_out.self_vin_match > 0]
⚠ Shadow listing: subject VIN found at <shadow_dealer_name> ($<shadow_price>, dom <shadow_dom>, <shadow_distance> mi). Confirm consignment vs stale data.

Caveats:
- Pre-physical-inspection — final offer should adjust for accident history and reconditioning needs.
- Sold-90d evidence not pulled (W2 trade-off for speed). For real-transaction anchor, run /full-appraisal <VIN>.

Footer: For sold-anchor reconciliation, days-to-sell estimates, and full Sold Transaction Comparables table, route VIN to W1 (/full-appraisal).
✓ Verified: profile, dual pricing, MC predict block, 5-row comp table, confidence band, condition adjuster.
─────────────────────────────────────────────────
```

### Card field sources

| Field | Source |
|---|---|
| `<year> <make> <model> <trim>`, body/drivetrain/engine/transmission, `msrp` | `parse_decode.specs` |
| `vin`, `asking_price`, `miles`, CPO `yes/no` | user-supplied per-VIN inputs |
| `<PRIMARY>` / `<CONTEXT>` labels | `profile.session.dealer_type_title` |
| `Predicted Retail Value` | `comp_stats.marketcheck_predict.nocpo_primary.marketcheck_price` (when profile dealer_type is franchise — the franchise predict is always the retail benchmark) OR `nocpo_context` when profile dealer_type is independent |
| `Predicted Wholesale Value` | The other channel's predicted price |
| `Wholesale-to-Retail Spread` | Computed: `retail - wholesale` and `spread / retail * 100` |
| `Recommended Trade-In Offer` | `0.78 * retail` to `0.85 * retail` (industry rule-of-thumb) |
| `CPO Premium` lines | `comp_stats.marketcheck_predict.{premium_primary, premium_context, pct_primary, pct_context, net_margin_primary, certification_cost}` — never hand-computed |
| Top 5 Retail Comparables table | `render_comp_set_table.py` over the W2 active comp pull's parse_search output |
| Recommended Value block | `render_appraisal_value_band.py` over the `compute_appraisal_band.py` output |
| `Confidence` | `compute_appraisal_band.py` output `confidence` field |
| Shadow listing line | `parse_search.filtered_out.self_vin_match > 0` |

### CPO sub-block — render conditions

Render the CPO Premium / Net Margin lines under Predicted Prices **only when**:
- Subject is CPO (per the pre-Wave-A CPO prompt), AND
- All 4 predict roles (`nocpo_primary`, `nocpo_context`, `cpo_primary`, `cpo_context`) returned `ok=true`, AND
- `comp_stats.marketcheck_predict.premium_primary` is non-null.

When any of those preconditions fail, omit the CPO Premium line and emit DQ event (a) noting the affected role's `error_type`.

### Confidence band

Read `compute_appraisal_band.py` output `confidence`:
- `Low` (< 5 total comps) — render the band as a wide range, render the confidence label, and emit a Key Signal: *"Low confidence — recommend widening radius or routing to W1 for sold-anchor depth before quoting."*
- `Medium` (5–14 total comps) — render the band normally; the rule-of-thumb 78–85% offer range still applies.
- `High` (15+ total comps) — render the band normally; emit a Key Signal noting the strong comp coverage.

### Money format

US profiles: `$` prefix, comma thousands, no decimals (e.g. `$28,500`). UK profiles: `£` prefix, same format. Percentages: 1 decimal place.

---

## Failure modes  (per-card render handling)

| Case | Effect on the card |
|---|---|
| Decode `ok=false` | Halt the workflow before rendering. |
| One predict role `ok=false` | Render that line as `unavailable (<error_type>)`; spread / offer range degrade accordingly (use surviving roles); Key Signal points to W1. |
| All 4 predicts `ok=false` | Halt the workflow with a "route to W1" message. |
| Search `num_found=0` | Top 5 Retail Comparables renders `(empty)`; predicted retail / wholesale / spread / offer still render from predict roles; confidence drops to Low. |
| `num_found < 5` | Render whatever rows came back; confidence drops to Low (unless predict roles got many comps via `comparables_n`). |
| Shadow listing detected | Inline `⚠ Shadow listing` line in the card. |
| UK profile | Route to UK W2 adaptation per `references/country-uk.md`. |
| Mileage missing at pre-check | Halt before any MCP call. |

---

## Self-check  (internal — never render as a grid)

Run each item silently before returning the response. Render only the footer line (or `⚠` warnings).

1. Profile loaded and confirmed on first line.
2. Country-routing applied (US tools used; UK profiles routed to country-uk.md adaptation).
3. Dual pricing shown — both Franchise and Independent MarketCheck Prices rendered (and CPO equivalents when subject is CPO).
4. CPO branch decision documented per VIN — DQ event (g) entry shows whether CPO predicts ran.
5. Pre-Wave-A completeness check enforced — VIN format valid, miles supplied, profile dealer_type present.
6. Subject VIN excluded from comp set — `parse_search.filtered_out.self_vin_match` was processed; shadow listing flagged.
7. Server-stats anchor verified — `parse_search.stats.price` and `parse_search.stats.dom_active` present; falls back to client-bounded percentile only when `num_found < min_n`.
8. Pipeline executed — `parse_search.py` → `build_comp_stats_input.py` → `comp_stats.py` → `compute_appraisal_band.py` ran. Hand-computed bands fail this check.
9. Action template (the 78–85% offer range) used the prescribed formula; no free-form offer math.
10. Confidence band matches `comp_count_total` (Low <5, Medium 5-14, High 15+).
11. Footer renders ONE block (single self-check footer at the end of the card, not multiple).

If all applicable checks pass → emit the `✓ Verified:` summary line in the Footer.

If any check fails → emit `⚠ <failure description>` lines in the Footer (one per failure), and add an explanatory note: *"⚠ Some checks failed — see Caveats and Data Quality Notes for diagnostic details."*

Never render a pass-by-pass checkbox grid. The 11-item self-check is an internal guardrail.
