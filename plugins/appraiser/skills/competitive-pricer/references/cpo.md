# CPO detection and dual-channel CPO prediction

CPO (Certified Pre-Owned) status materially changes the price anchor used by an appraisal. A CPO unit usually sits 4–10% above its non-CPO equivalent because of the inspection + warranty bundle. For an appraiser, the CPO Premium is a defensibility component — the recovered value the unit will realise as a CPO listing at a franchise rooftop.

The appraiser plugin's profile does **not** carry a `cpo_program` or `cpo_certification_cost` field — that's dealer-side context. The skill therefore does **not** compute a "Net Margin from CPO" line. It computes and renders **CPO Premium** only.

## Detection — decision tree

CPO status needs to be decided **before** the first wave of MCP calls so the two CPO predict calls (if needed) can ride along in the same parallel batch. Walk this tree top-to-bottom; stop at the first branch that produces a confident answer.

### 1. Appraiser explicitly states CPO status — strongest, earliest signal

Check before any MCP call. If the appraiser says *"this one is certified"* / *"it's a CPO unit"* / *"I'm appraising a certified Accord"*, CPO is **confirmed**. If they say *"not CPO"* / *"this one isn't certified"*, it's **explicitly non-CPO**. Trust the appraiser — they're looking at the window sticker or trade-in paperwork.

- **Confirmed CPO** → first wave includes 4 predict calls (non-CPO × 2 + CPO × 2). Render the CPO Premium block.
- **Explicitly non-CPO** → first wave includes 2 predict calls (non-CPO × 2 only). Skip CPO Premium. Emit DQ event (g): *"CPO branch skipped: appraiser stated non-CPO"*.

### 2. Active listing for the subject VIN has `is_certified == 1` (post-hoc signal)

After the active-comp pull returns, scan the comp set for a shadow listing of the subject VIN (the subject VIN appearing at a *different* dealer in the active set). If the shadow row has `is_certified == 1` (tri-state True on the wire), the subject is effectively CPO somewhere in the market. Issue the two CPO predicts in a follow-up wave.

**On the wire**, `is_certified` is integer `1` / `0` / absent. Normalise to tri-state during extraction:

- `is_certified == True` (wire: `1`) → CPO confirmed via shadow.
- `is_certified == False` (wire: `0`) → shadow listing explicitly non-CPO. Combined with appraiser silence, treat the subject as non-CPO.
- `is_certified is None` (wire: field absent) → unknown. Fall through to rule 3.

`inventory_type` is **NOT** a CPO signal. It only carries `"used"` / `"new"` in real responses; `"certified"` never appears. Confirmed-CPO listings show `inventory_type: "used"` + `is_certified: 1`.

### 3. `get_car_history` shows historical CPO

When rules 1 and 2 both returned "unknown" and a valuation decision depends on CPO status, issue `get_car_history(vin, sort_order=desc, page=1, fields=<canonical-fields>)` and check `is_certified` across the rows.

`cpo_ever` is the boolean derived from the history rows: `True` if any row has `is_certified == 1`; `False` if every row that carried the field had `is_certified == 0`; `None` if no row carried `is_certified`.

The explicit `fields=` parameter is required: `is_certified` is an Optional Field per `mcp_server_tool_docs/get_car_history.md` and is silently stripped without it — the probe would then always return `cpo_ever=None` regardless of upstream data. The canonical fields string is below.

#### Canonical `fields=` string (verbatim — keep in sync across this skill)

```
id,vin,price,miles,msrp,seller_name,dealer_id,city,state,zip,first_seen_at_date,last_seen_at_date,scraped_at_date,source,vdp_url,seller_type,inventory_type,is_certified,dom_active,dom_180,dom,stock_no,data_source
```

This string is mirrored in:
- `references/w2-trade-in-history.md` — step 1's `get_car_history` call.
- `references/w1-price-check.md` — Wave C CPO-ambiguous path (when used).
- This file's rule 3.

Keep all three in sync if changed.

### Interpretation

- `cpo_ever == True` → at least one past listing was CPO. Surface: *"This VIN was listed as CPO by a previous dealer — is this unit currently certified?"* The appraiser's answer is the final word.
- `cpo_ever == False` → every past listing that carried the field was explicitly non-CPO. Treat subject as non-CPO; skip CPO branch silently.
- `cpo_ever is None` → no history row carried `is_certified` at all. Emit DQ event (e): *"CPO history signal unavailable for this VIN"*. If the decision still matters, prompt the appraiser.

## The `decertified` red flag (W2 history)

Fires only in W2 trade-in history, only when `cpo_ever == True` AND the **current** (most recent, post-sort-desc) listing has `is_certified == False` (explicit `0`, NOT `None` — absent is "unknown", not "confirmed non-CPO"). Surface as a red flag in the W2 Price Trajectory block:

> *"⚠ This VIN was previously listed as CPO and is currently listed as non-CPO. Verify the unit's current certification status before finalising the valuation — decertification reduces the recoverable premium."*

## Anti-patterns — never do these

- Never infer CPO from the dealer's name, domain, or website. CPO is a specific programmatic status, not a quality level.
- Never write strict-equality checks against `True` on the wire values — they miss integer-1 rows. Use truthy checks (`bool(raw.get("is_certified"))`) for "is CPO?" and explicit-zero checks (`raw.get("is_certified") == 0`) for "explicitly non-CPO?".
- Never treat `None` as `False` in any CPO column — render `—` instead. Unknown is a legitimate render state.
- Never substitute a model-knowledge guess for CPO status. If the user didn't say and the data doesn't say, prompt or treat as non-CPO with a caveat — never guess.

## The dual-channel CPO call pattern

When the subject is CPO, the skill issues **TWO MORE** `predict_price_with_comparables` calls beyond the standard dual prediction — one per dealer_type, both with `is_certified=true`.

```
# Standard dual prediction (always)
predict_price_with_comparables(vin, miles, zip, dealer_type=franchise)        → nocpo_franchise (retail anchor)
predict_price_with_comparables(vin, miles, zip, dealer_type=independent)      → nocpo_independent (wholesale-proxy anchor)

# CPO branch (when confirmed)
predict_price_with_comparables(vin, miles, zip, dealer_type=franchise,    is_certified=true)  → cpo_franchise
predict_price_with_comparables(vin, miles, zip, dealer_type=independent,  is_certified=true)  → cpo_independent
```

The four response role labels (`nocpo_franchise` / `nocpo_independent` / `cpo_franchise` / `cpo_independent`) are your working-memory handles — not call-site arguments. Each role's `predicted_price` is the **MarketCheck Price** for that role.

**Appraiser-audience framing.** Unlike the dealer-side skill which labels these as PRIMARY / CONTEXT based on the dealer's own type, the appraiser skill renders both channels with equal weight:

- **Franchise (Retail) MarketCheck Price** — the retail value the unit would realise if listed at a franchise rooftop.
- **Independent (Wholesale-proxy) MarketCheck Price** — a wholesale-oriented proxy useful for trade-in offer ranges.

Both are presented side-by-side with a spread line. The appraiser selects the appropriate benchmark for the valuation purpose (trade-in / retail / insurance claim).

## CPO Premium computation

Compute from the four MarketCheck Price values:

```
premium_franchise   = cpo_franchise.marketcheck_price   - nocpo_franchise.marketcheck_price
premium_independent = cpo_independent.marketcheck_price - nocpo_independent.marketcheck_price
pct_franchise       = premium_franchise / nocpo_franchise.marketcheck_price * 100
pct_independent     = premium_independent / nocpo_independent.marketcheck_price * 100
```

If either CPO role is missing (call failed / truncated unrecoverable), that channel's premium is `null`; render `—` in that row and emit a caveat.

## Render block — CPO Premium

When the CPO branch fired AND at least one premium value is non-null:

```
CPO Premium

  Franchise (Retail):     +$<premium_franchise>   (+<pct_franchise>%)
  Independent (Wholesale): +$<premium_independent> (+<pct_independent>%)
```

When neither premium is computable, skip the entire block.

**No "Net Margin from CPO" line.** That line requires the dealer's `cpo_certification_cost` from their profile, which the appraiser plugin's onboarding doesn't gather. If an appraiser needs net-margin context, they can route to the dealer-audience skill.

## When the subject is NOT CPO but competitors are

In the comp set, some comps may be CPO and others not. When rendering the comp set, surface this asymmetry as a Data Quality Notes event (c) when `comp_cpo_count / total_comps > 30%`: *"<N> of <M> comparables are CPO listings — non-CPO subjects should reference the non-CPO subset of comps for apples-to-apples context."*

The appraiser then has the choice to filter to non-CPO comps for the apples-to-apples comparison or treat the CPO comps as upper-bound context. The skill does NOT silently filter — the appraiser's defensibility benefits from seeing the full distribution.

## UK

CPO is a US concept in this skill. UK's "Approved Used" programmes are manufacturer-specific and not uniformly indexed — treat every UK subject as non-CPO and skip the CPO Premium block. If the appraiser explicitly asks about Approved Used pricing on UK, halt and explain the limitation.
