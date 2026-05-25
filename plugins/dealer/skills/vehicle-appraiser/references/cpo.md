# CPO Detection and Dual Prediction

CPO (Certified Pre-Owned) status materially changes the price anchor. A CPO unit usually sits 4–10% above its non-CPO equivalent because of the inspection + warranty bundle. The dealer's `cpo_certification_cost` from the profile is the out-of-pocket cost to certify; the CPO premium computed here answers "what does the market pay for that certification?"

For an appraisal, knowing the CPO premium matters in three places: (1) trade-in offer math (W3 — Wholesale-vs-Retail Spread), (2) the central appraisal value (W1 — Full Comparable Appraisal), and (3) the listing-history red flag (W5 — Historical Trajectory shows `decertified` when a vehicle was CPO at a prior listing but the current listing is non-CPO).

## Detection — decision tree (ordered by availability in the workflow)

CPO status needs to be decided **before** Wave A so the two CPO predict calls can ride along in the same parallel batch. Walk this tree top-to-bottom; stop at the first branch that produces a confident answer.

### 1. User explicitly states CPO status — STRONGEST, earliest signal

Check before any MCP call. If the user says "this one is certified" / "it's a CPO unit" / "I'm appraising a certified Accord", CPO is **confirmed**. If they say "not CPO" / "this one isn't certified", it's **explicitly non-CPO**. Trust the user — they're looking at the window sticker.

- **Confirmed CPO** → Wave A includes 4 predict calls (non-CPO × 2 + CPO × 2). Render the CPO Premium block.
- **Explicitly non-CPO** → Wave A includes 2 predict calls (non-CPO × 2 only). Skip CPO Premium. Emit DQ event (g) `"CPO branch skipped: user stated non-CPO"`.

### 2. Profile `cpo_program=true` AND user silent on CPO status — prompt before Wave A

The dealer can certify; that doesn't tell you whether *this* unit IS certified. In this case, **proactively prompt** before Wave A: *"Is this unit currently CPO?"* Apply the answer for the rest of the session.

- This gate is the reason `profile.dealer.cpo_program` exists. If the profile has no `cpo_program` field (or it's false), skip this prompt and let the post-hoc paths (3/4 below) handle detection.
- If the user declines to answer, default to **non-CPO** for Wave A (safer than over-fetching) and note `"CPO status unconfirmed"` in Key Signals so they see it.

### 3. Active listing for the subject VIN has `is_certified=1` (Wave B post-hoc signal)

After Wave B's asc pull returns, scan the comp set for a shadow listing of the subject VIN (parse_search's `filtered_out.self_vin_match > 0` flags this). If the shadow row has `is_certified == 1` (tri-state True), the subject is effectively CPO somewhere in the market. Issue the two CPO predicts in **Wave C**.

**On the wire**, `is_certified` is integer `1` / `0` / absent. `parse_search.py` normalises to tri-state:
- `is_certified == True` (wire: `1`) → CPO confirmed via shadow.
- `is_certified == False` (wire: `0`) → shadow listing explicitly non-CPO. Combined with user silence, treat the subject as non-CPO.
- `is_certified is None` (wire: field absent — very common; 31/50 rows on a live Honda Accord sample) → unknown. Fall through to rule 4.

`inventory_type` is **NOT** a CPO signal. It only carries `"used"` / `"new"` in real responses; `"certified"` never appears. Confirmed-CPO listings show `inventory_type: "used"` + `is_certified: 1`.

### 4. `get_car_history` shows historical CPO (Wave C probe)

When rules 1–3 all returned "unknown" and an appraisal decision depends on CPO status, issue `get_car_history(vin, fields="id,vin,price,miles,msrp,seller_name,dealer_id,city,state,zip,first_seen_at_date,last_seen_at_date,scraped_at_date,source,vdp_url,seller_type,inventory_type,is_certified,dom_active,dom_180,dom,stock_no,data_source")` in Wave C and check `parse_history.cpo_ever`. The explicit `fields=` is required: `is_certified` is an Optional Field per `mcp_server_tool_docs/get_car_history.md` and is silently stripped without it — the probe would then always return `cpo_ever=None` regardless of upstream data. Mirror the string verbatim from `parse_history.CANONICAL_FIELDS_PARAM`.

- `cpo_ever == True` → at least one past listing was CPO. Surface: *"This VIN was listed as CPO by a previous dealer — is this unit currently certified?"* The user's answer is the final word.
- `cpo_ever == False` → every past listing that carried the field was explicitly non-CPO. Treat subject as non-CPO; skip CPO branch silently.
- `cpo_ever is None` → no history row carried `is_certified` at all. Log DQ event *"CPO history signal unavailable for this VIN"*. If the decision still matters, prompt the user.

### `decertified` red flag

Fires only in W5 (Historical Trajectory), only when `cpo_ever == True` AND the current (most recent, post-sort) listing has `is_certified == False` (explicit 0, NOT None — absent is "unknown", not "confirmed non-CPO"). `parse_history.py` sorts desc internally so `listings[0]` is always the most recent regardless of upstream ordering.

### Anti-patterns — never do these

- Never infer CPO from the dealer's name, domain, or website. CPO is a specific programmatic status, not a quality level.
- Never write strict-equality checks against `True` on the wire values — they miss integer-1 rows. Use `bool(raw.get("is_certified"))` for truthy and `"is_certified" in raw and raw["is_certified"] == 0` for explicit-False.
- Never treat `None` as `False` in the CPO? column — render `—` instead. Unknown is a legitimate render state.

## The dual-prediction call pattern

When the subject is CPO, the skill issues **TWO MORE** `predict_price_with_comparables` calls beyond the standard dual prediction — one per dealer_type, both with `is_certified=true`.

`<dealer_type_lower>` and `<dealer_type_opposite_lower>` are both pre-computed in the profile `session` block by `scripts/load_profile.py`; read them verbatim, do not re-derive per call.

```
# Standard dual prediction (always in Wave A)
predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_lower>)           → nocpo_primary
predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_opposite_lower>)  → nocpo_context

# CPO branch (Wave A when user stated CPO; Wave C when detected post-hoc)
predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_lower>,          is_certified=true)  → cpo_primary
predict_price_with_comparables(vin, miles, zip, dealer_type=<dealer_type_opposite_lower>, is_certified=true)  → cpo_context
```

All four responses pipe through `parse_predict.py`. The `nocpo_primary` / `nocpo_context` / `cpo_primary` / `cpo_context` result handles are **role labels** in the skill's working memory — NOT call-site args, and they keep their `primary` / `context` naming across CPO state.

## CPO Premium + Net Margin (computed in `comp_stats.py`, NOT hand-math)

> *Naming clarification.* `CPO Premium` and `Net Margin from CPO` are NOT MarketCheck products — they are market/dealer concepts. The `MarketCheck` prefix in this skill is reserved for the values that come **directly** from the `predict_price_with_comparables` MCP call (the `MarketCheck Price` scalar and its comp counts/distributions). Premium is computed *from* MC Price values; that doesn't make Premium a MarketCheck product. Render labels for Premium / Net Margin are unprefixed; surrounding context (the MC Price lines they sit beneath) makes the source obvious.

Pipe each of the four parse_predict.py outputs (one per role) into `build_comp_stats_input.py` via the four `--{nocpo,cpo}-{primary,context}-parsed <path>` flags. The builder reads `marketcheck_price` + comp counts + price stats from each parsed file and packs them into `marketcheck_predict_input` on the comp_stats stdin. `comp_stats.py` then emits a consolidated `marketcheck_predict` block:

```json
marketcheck_predict = {
  "primary_label":      "Franchise" | "Independent",
  "context_label":      "Independent" | "Franchise",
  "nocpo_primary":      { marketcheck_price, comparables_n, recent_comparables_n,
                          comparables_price_stats, recent_comparables_price_stats } | null,
  "nocpo_context":      { ... } | null,
  "cpo_primary":        { ... } | null,
  "cpo_context":        { ... } | null,
  "premium_primary":    cpo_primary.marketcheck_price - nocpo_primary.marketcheck_price,
  "premium_context":    cpo_context.marketcheck_price - nocpo_context.marketcheck_price,
  "pct_primary":        premium_primary / nocpo_primary.marketcheck_price * 100,
  "pct_context":        premium_context / nocpo_context.marketcheck_price * 100,
  "certification_cost": profile.dealer.cpo_certification_cost,
  "net_margin_primary": premium_primary - certification_cost
}
```

The renderer reads `marketcheck_predict` verbatim. Never hand-compute the premium / net margin.

Render in the optional CPO Premium block:

```
CPO Premium (Franchise):   +$1,850  (3.9%)
CPO Premium (Independent): +$1,400  (3.1%)
Certification Cost (you):  $1,000   (from profile)
Net Margin from CPO:       +$850 per unit  (Franchise channel)
```

`marketcheck_predict.premium_primary` and `premium_context` are `null` when their respective CPO role is missing (CPO branch didn't run, or a prediction degraded). When either is null, skip the CPO Premium block entirely. The non-CPO roles' MarketCheck Price lines in `Predicted Prices` still render whatever populated.

## When the subject is NOT CPO but competitors are

`comp_stats.py`'s `channel_stats.primary_non_cpo` carves out CPO comps from the primary channel so the apples-to-apples comparison isn't polluted by a CPO cluster. Surfaces in the W1 / W3 Same-Channel View block.

`primary_non_cpo` is emitted **only** when:
- The subject is non-CPO, AND
- `primary.n >= 2`, AND
- `primary.cpo_count > 0`, AND
- After stripping CPO, the non-CPO slice still has `n >= 2`.

When the guard fires, `primary_non_cpo` is `null` and the Same-Channel View falls back to the full-primary median with a note. This prevents the false reading of "the appraisal aligns with franchise comps" when the franchise comps are 40% CPO and the subject isn't.

## UK

CPO is a US concept in this skill. UK's "Approved Used" programmes are manufacturer-specific and not uniformly indexed — treat every UK subject as non-CPO and skip the CPO Premium block. If the user explicitly asks about Approved Used pricing, halt and explain the limitation.
