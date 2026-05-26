# CPO Detection and Dual Prediction

CPO (Certified Pre-Owned) status materially changes the price anchor. A CPO unit usually sits 4–10% above its non-CPO equivalent because of the inspection + warranty bundle. Knowing the CPO premium matters for any appraisal because the comp set's CPO mix changes the apples-to-apples comparison; for an insurance total-loss valuation it changes the defensible value floor by thousands of dollars.

For an appraisal, the CPO premium matters in three places: (1) trade-in offer math (W3 — Wholesale-vs-Retail Spread), (2) the central appraisal value (W1 — Full Comparable Appraisal), and (3) the listing-history red flag (W5 — Historical Trajectory shows `decertified` when a vehicle was CPO at a prior listing but the current listing is non-CPO).

## Detection — decision tree (ordered by availability in the workflow)

CPO status needs to be decided **before** Wave A so the two CPO predict calls can ride along in the same parallel batch. Walk this tree top-to-bottom; stop at the first branch that produces a confident answer.

### 1. User explicitly states CPO status — STRONGEST, earliest signal

Check before any MCP call. If the user says "this one is certified" / "it's a CPO unit" / "I'm appraising a certified Accord", CPO is **confirmed**. If they say "not CPO" / "this one isn't certified", it's **explicitly non-CPO**. Trust the user — they're looking at the window sticker.

- **Confirmed CPO** → Wave A includes 4 predict calls (non-CPO × 2 + CPO × 2). Render the CPO Premium block.
- **Explicitly non-CPO** → Wave A includes 2 predict calls (non-CPO × 2 only). Skip CPO Premium. Emit DQ event (g) `"CPO branch skipped: user stated non-CPO"`.

### 2. Purpose-sensitive prompt (Insurance / Estate) — when subject is CPO-eligible

The appraiser profile does **not** carry a `cpo_program` field — appraisers don't certify vehicles, they value them. The proactive prompt fires on a different condition: when the appraisal `purpose` is `Insurance` or `Retail` (estate/fair-market-value), the subject is a used vehicle of a make that has an active CPO program, AND the user has not pre-stated CPO status, ask before Wave A:

> *"Is this unit currently CPO? CPO status materially affects the defensible value for insurance and estate appraisals."*

For Trade-in / Wholesale purposes the post-hoc paths (3/4 below) typically resolve it; the proactive prompt is reserved for purposes where the appraisal must be defensible against a third party.

If the user declines to answer, default to **non-CPO** for Wave A (safer than over-fetching) and note `"CPO status unconfirmed"` in Key Signals so they see it.

### 3. Active listing for the subject VIN has `is_certified=1` (Wave B post-hoc signal)

After Wave B's asc pull returns, scan the comp set for a shadow listing of the subject VIN (`parse_search`'s `filtered_out.self_vin_match > 0` flags this). If the shadow row has `is_certified == 1` (tri-state True), the subject is effectively CPO somewhere in the market. Issue the two CPO predicts in **Wave C**.

**On the wire**, `is_certified` is integer `1` / `0` / absent. `parse_search.py` normalises to tri-state:
- `is_certified == True` (wire: `1`) → CPO confirmed via shadow.
- `is_certified == False` (wire: `0`) → shadow listing explicitly non-CPO. Combined with user silence, treat the subject as non-CPO.
- `is_certified is None` (wire: field absent — very common; ~60% of rows on a live Honda Accord sample) → unknown. Fall through to rule 4.

`inventory_type` is **NOT** a CPO signal. It only carries `"used"` / `"new"` in real responses; `"certified"` never appears. Confirmed-CPO listings show `inventory_type: "used"` + `is_certified: 1`.

### 4. `get_car_history` shows historical CPO (Wave C probe)

When rules 1–3 all returned "unknown" and an appraisal decision depends on CPO status, issue `get_car_history(vin, fields=parse_history.CANONICAL_FIELDS_PARAM)` in Wave C and check `parse_history.cpo_ever`. The explicit `fields=` is required: `is_certified` is an Optional Field per `mcp_server_tool_docs/get_car_history.md` and is silently stripped without it — the probe would then always return `cpo_ever=None` regardless of upstream data. Mirror the string verbatim from `parse_history.CANONICAL_FIELDS_PARAM`.

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

The appraiser plugin is **channel-neutral** — both `franchise` and `independent` predicts always fire (no PRIMARY/CONTEXT swap based on a profile field).

```
# Standard dual prediction (always in Wave A)
predict_price_with_comparables(vin, miles, zip, dealer_type=franchise)    → nocpo_franchise
predict_price_with_comparables(vin, miles, zip, dealer_type=independent)  → nocpo_independent

# CPO branch (Wave A when user stated CPO; Wave C when detected post-hoc)
predict_price_with_comparables(vin, miles, zip, dealer_type=franchise,    is_certified=true)  → cpo_franchise
predict_price_with_comparables(vin, miles, zip, dealer_type=independent,  is_certified=true)  → cpo_independent
```

All four responses pipe through `parse_predict.py`. The `nocpo_franchise` / `nocpo_independent` / `cpo_franchise` / `cpo_independent` result handles are **role labels** in the skill's working memory — NOT call-site args.

## CPO Premium (computed, NOT hand-math)

> *Naming clarification.* `CPO Premium` is NOT a MarketCheck product — it is a market concept derived from the `marketcheck_price` values returned by `predict_price_with_comparables`. The `MarketCheck` prefix in this skill is reserved for the values that come **directly** from the predict MCP call. Premium is computed *from* those values; that doesn't make Premium a MarketCheck product. Render labels for Premium are unprefixed; surrounding context (the MC Price lines they sit beneath) makes the source obvious.

Premium derivation (per channel):

```
premium_franchise   = cpo_franchise.marketcheck_price   - nocpo_franchise.marketcheck_price
premium_independent = cpo_independent.marketcheck_price - nocpo_independent.marketcheck_price
pct_franchise       = premium_franchise   / nocpo_franchise.marketcheck_price   * 100
pct_independent     = premium_independent / nocpo_independent.marketcheck_price * 100
```

Render the optional CPO Premium block as:

```
CPO Premium (Franchise):    +$1,850   (3.9%)
CPO Premium (Independent):  +$1,400   (3.1%)
```

**No `Net Margin from CPO` line, no `Certification Cost (you)` line.** Those are dealer P&L concepts (certification cost − premium = net margin); appraisers do not certify vehicles, so the appraiser profile carries no `cpo_certification_cost` and the premium is the only metric rendered. If a previous-generation dealer-flavored output template is encountered with these lines, omit them on render.

`premium_franchise` and `premium_independent` are `null` when their respective CPO role is missing (CPO branch didn't run, or a prediction degraded). When either is null, skip the CPO Premium block entirely. The non-CPO roles' MarketCheck Price lines in `Predicted Prices` still render whatever populated.

## When the subject is NOT CPO but competitors are

The appraisal must not be polluted by CPO comps in the apples-to-apples comparison. When the subject is non-CPO and the active comp set has ≥2 CPO rows, surface a Key Signal noting the CPO share of the comp set so the appraiser can manually re-anchor against the non-CPO subset. (The deterministic per-channel CPO-strip is implemented in the reference's `comp_stats.py`; this skill version computes it at render time when the appraiser explicitly asks.)

## UK

CPO is a US concept in this skill. UK's "Approved Used" programmes are manufacturer-specific and not uniformly indexed — treat every UK subject as non-CPO and skip the CPO Premium block. If the user explicitly asks about Approved Used pricing, halt and explain the limitation.
