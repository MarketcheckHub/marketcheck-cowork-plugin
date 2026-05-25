# W2 — Trade-In Quick Appraisal

Triggered by "trade-in value", "what's it worth quick", "how much should I offer", "customer at the desk", etc. **Speed-pitch workflow** — the customer is sitting across the desk and the dealer needs a credible number in under 25 seconds.

W2 is **deliberately lighter than W1**. No desc tail-pull, no drop scan, no sold-90d stats trio, no `get_sold_summary`, no get_car_history, no Sold Transaction Comparables table. The dealer trades depth for throughput. For the formal report (insurance, fleet) and full sold transaction evidence, route to W1 (`/full-appraisal <VIN>`).

## Required inputs

- **VIN** (mandatory; 17 chars matching `^[A-HJ-NPR-Z0-9]{17}$` — no I/O/Q). YMMT-only is rejected (route to W1's YMMT branch or W4 for the model-level market).
- **Mileage** (mandatory — predict's silent fallback to `miles=50000` corrupts the trade-in number).
- **Asking price** is OPTIONAL for W2; absent → no "vs market" gap line, but predicted retail / wholesale / spread / offer range still render.
- **Condition** (recommended — `Clean` / `Average` / `Rough`; absent → assumed Average with a Key Signal note).
- **Purpose** is implicitly `Trade-in` for W2 (the workflow name says so); the agent does not prompt.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | Route to UK W2 adaptation per `references/country-uk.md`. |
| `profile.location.country == "CA"` | Halt per SKILL.md country routing. |
| VIN doesn't match `^[A-HJ-NPR-Z0-9]{17}$` | *"VIN is malformed (must be 17 chars, no I/O/Q). Halt — please correct and re-run."* |
| YMMT-only (no VIN) | *"W2 Trade-In Quick requires a VIN. For YMMT-only inquiries, run W1 (`/full-appraisal`) or W4 (`/regional-variance`)."* |
| Mileage missing | *"Trade-In Quick requires the current odometer reading. Predict's silent fallback to 50,000 miles produces misleading numbers."* |
| `profile.session.dealer_type_lower is None` | Halt per SKILL.md (franchise-or-independent prompt). |
| `car_type_resolved` is None | Halt-and-ask per SKILL.md. |

## CPO policy

A single up-front prompt before Wave A when `profile.dealer.cpo_program == true` AND user has not pre-stated CPO status: *"Is this unit currently CPO?"*

- Confirmed CPO → Wave A grows from 3 to 5 calls (decode + 4 predicts + 1 active comp pull).
- Confirmed non-CPO → Wave A stays at 3 calls. Emit DQ event (g) `"CPO branch skipped: user-confirmed non-CPO"`.

## Parallelization (W2)

W2 is a **single-wave workflow**. All 3-5 calls fire in one parallel batch.

**Wall-clock budget:** ~12-15s.

## Wave A — Per-VIN decode + dual ML predict + tight comp pull

```
decode_vin_neovin(vin)                                                                          # parse → role: specs
predict_price_with_comparables(vin, miles, zip=<profile.zip>, dealer_type=<dealer_type_lower>)         # parse → role: nocpo_primary
predict_price_with_comparables(vin, miles, zip=<profile.zip>, dealer_type=<dealer_type_opposite_lower>) # parse → role: nocpo_context

[when subject is CPO]
predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_lower>,          is_certified=true)  # role: cpo_primary
predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_opposite_lower>, is_certified=true)  # role: cpo_context

search_active_cars:
  year, make, model, trim                        (verbatim from cached parse_decode.specs — but in single-wave fashion we may not have decode yet,
                                                   so the agent fires WITH vin AND with the search-by-vin facet OR splits Wave A into a tiny 2-stage
                                                   pipeline: decode in microwave A1, then 2 predicts + comp pull in microwave A2.)
  zip=<profile.zip>, radius=<session.radius_mi_clamped>, car_type="used"   # HARDCODED — trade-in subjects are always Used by definition. A new-car franchise dealer (default_inventory_type=new) still takes used customer trade-ins; session.car_type_resolved describes the dealer's lot focus, NOT the trade-in subject's inventory type. The 78-85% wholesale-to-retail spread (output template) is a Used-car trade-in margin, so the comp set must also be Used.
  sort_by="price", sort_order="asc"
  price_range="1-*"
  rows=5
  stats="price,miles,dom_active"
  include_dealer_object=true
  include_build_object=true
  fetch_all_photos=false, include_mc_dealership_object=false,
  include_finance=false, include_lease=false, include_relevant_links=false
→ parse_search.py --file <persisted-path> --subject-vin <VIN>
```

**Implementation note on the decode-first dependency.** The active comp pull needs the YMMT from decode. Two options:

- **Option A (preferred when decode latency is dominant):** Fire decode + 2 predicts in parallel as Wave A1; on decode landing, fire the comp pull as Wave A2. Total wall clock = decode time (~12s) + comp time (~3-5s; comp call is fast at rows=5) ≈ 15-17s.
- **Option B (when decode hasn't fired yet but agent has cached YMMT from a prior session run):** Fire all calls in a single Wave A batch. ~12s wall clock.

Either way, W2's wall-clock budget stays under 25s.

## Persistence and truncation handling

`decode_vin_neovin` chronically truncates (~150KB envelopes); recover via `parse_decode.py --file`. `predict_price_with_comparables` chronically truncates (~100KB envelopes); recover via `parse_predict.py --file`. The active comp pull at rows=5 typically returns inline, but standard Write-recipe applies if it doesn't.

## Pipeline (post-wave)

```
parse_decode.py --file <decode.json>               → cached YMMT + display specs
parse_predict.py --file <predict-nocpo-primary.json> → nocpo_primary role
parse_predict.py --file <predict-nocpo-context.json> → nocpo_context role
[when CPO]
parse_predict.py --file <predict-cpo-primary.json>
parse_predict.py --file <predict-cpo-context.json>

parse_search.py --file <asc.json> --subject-vin <V>  → listings (≤5), num_found, server stats

build_comp_stats_input.py \
  --profile <load_profile output> \
  --asc-parsed <parse_search output> \
  --user-price <asking-price-or-empty>           # optional for W2 \
  --user-miles <miles>                            # required \
  --subject-vin <V> \
  --subject-cpo <true|false> \
  --trim-label "<year> <make> <model> <trim>" \
  --nocpo-primary-parsed <path> --nocpo-context-parsed <path> \
  [--cpo-primary-parsed <path> --cpo-context-parsed <path>] \
| comp_stats.py

# --merged, --sold-price, --sold-dom, --drops INTENTIONALLY OMITTED.
# build_comp_stats_input.py v1.5.0+ defaults these to W2-safe nulls (see
# competitive-pricer-updated reference for the contract).

echo '{"comp_stats": <comp_stats output>, "condition": "<...>", "purpose": "Trade-in"}' \
  | compute_appraisal_band.py
```

`comp_stats.py` falls back to `verdict_source = "quartile"` (sold-anchor gate is `sold_count_90d >= 5`); for W2 the verdict is unused — the appraiser-domain output is the value band from `compute_appraisal_band.py`.

## W2 wholesale-to-retail spread (the punchline)

The W2 card emits a **Recommended Trade-In Offer** range computed from the Predicted Retail Value (= `marketcheck_predict.nocpo_primary.marketcheck_price` on a franchise-primary profile) using a fixed retail-to-wholesale ratio.

The default ratio is **78–85% of franchise predicted retail** (industry rule-of-thumb; matches the target's `outcomes.md` and `SKILL.md:53,162`). This default is fixed in W2's render template (`assets/w2-output-template.md`).

For an Independent-primary profile, the predicted retail is the franchise predicted price (the *retail* benchmark for any segment), and the predicted wholesale is the independent predicted price.

When `comp_stats.marketcheck_predict.nocpo_primary` is null (predict role degraded), render the offer range as `unavailable (predict role degraded; route to W1 for full appraisal)`. Do NOT synthesize a number from the active comp set — the spread analysis depends on the ML predict.

## Output rendering

W2 renders via **`assets/w2-output-template.md`** — its own single-source-of-truth file. Block structure overview:

1. **Header** — `Using profile: ...` + Vehicle Identification compact line.
2. **Predicted Retail Value** + **Predicted Wholesale Value** + **Wholesale-to-Retail Spread** + **Recommended Trade-In Offer**.
3. **CPO Premium** sub-block (when applicable).
4. **Top 5 Retail Comparables** (8-col via `render_comp_set_table.py`, rows=5).
5. **Recommended Value (condition-adjusted)** — band block via `render_appraisal_value_band.py` (compact form).
6. **Confidence note** + caveats.
7. **Footer** — escape-hatch (route to W1 for sold-anchor depth) + self-check.

## Failure recovery and edge cases

| Case | Behavior |
|---|---|
| Decode `ok=false` | Halt the workflow with VIN-or-retry prompt. |
| One predict role `ok=false` | Render that role's value as `unavailable (<error_type>)`; continue. Spread + offer range degrade gracefully (use the surviving roles). |
| All 4 predicts `ok=false` | Halt with *"All ML predictions failed — route this VIN to W1 (`/full-appraisal`) which has comp-anchored fallbacks."* |
| Search `num_found=0` on the active comp pull | Render Top 5 Comparables as `(empty)`; W2 still emits the predicted retail / wholesale / spread / offer range from the predict roles; confidence drops to Low. |
| `num_found < 5` on the active comp pull | Render whatever rows came back; confidence drops to Low (unless predict roles got many comps via `comparables_n`); emit Key Signal noting the thin local market. |
| Subject VIN found in comp set (shadow) | parse_search excludes; emit DQ event (c) with shadow-dealer details inline in the W2 card. |
| Mileage missing | Halt at pre-check (covered above). |
| UK profile | Route to UK W2 adaptation per `references/country-uk.md`. |

---

## See also

- `assets/w2-output-template.md` — W2 render spec.
- `references/w1-full-appraisal.md` — full appraisal depth (sold-anchor + sold transaction comp table + state baseline).
- `references/cpo.md` — CPO call shape (the dual-prediction pattern is identical).
- `references/truncation-recovery.md` — `--file` recovery recipe for chronic-truncation tools.
