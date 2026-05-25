# W2 — Trade-In VIN Price History

Triggered by "what's the history on this trade", "previous listings for VIN X", "show this VIN's price trajectory", "is this trade-in a clean unit", etc. **US-only** — halt on UK profiles with: *"Trade-in price history is US-only (requires `get_car_history`, not available for UK). For UK valuation context, run `/price-check` for the current market distribution or use `appraiser:vehicle-appraiser` for a full appraisal."*

W2 is a **history viewer** workflow for an appraiser: surface the VIN's listing trajectory, dealer-hop pattern, sharp-drop and decertified red flags, and (optionally) a current dual-channel ML fair-value when the appraiser is sizing a trade-in offer. W2 does **not** compute trade-in offer math (recon cost, target margin, target wholesale price); for that, route to `appraiser:vehicle-appraiser` or to W1 via `/price-check <VIN>` after the appraiser has the current odometer.

## Required inputs

- **VIN** (mandatory). Validate format on entry: `^[A-HJ-NPR-Z0-9]{17}$` per `references/profile-loading.md`. Fire no MCP calls until the format check passes.
- **Current odometer (miles)**: required **only when step 3 (predict) is invoked**. See "Step 3 user-flow gate" below.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | *"Trade-in price history is US-only (requires `get_car_history`, not available for UK). For UK valuation context, run `/price-check` for the current market distribution or use `appraiser:vehicle-appraiser` for a full appraisal."* |
| `profile.location.country == "CA"` | Standard CA-not-supported halt per SKILL.md. |
| VIN doesn't match `^[A-HJ-NPR-Z0-9]{17}$` | Standard VIN-format halt. |
| VIN missing entirely | *"W2 requires a VIN. Please supply the 17-char VIN whose price history you'd like to look up."* |

## Wave A — single parallel batch (2 calls, or 4 with step 3)

All calls in Wave A take only the VIN (and `miles` + `zip` for predict). No cross-dependencies. Issue every call within the wave in a SINGLE batch (multiple MCP tool calls in the same response); wait for the whole wave to return before rendering.

### Step 1 — `get_car_history`

```
get_car_history(
  vin,
  sort_order="desc",
  page=1,
  fields=<canonical-fields>
)
```

The explicit `fields=` enumerates Optional Fields per `mcp_server_tool_docs/get_car_history.md`; without it, `is_certified` / `dom_*` / `msrp` / `dealer_id` / `stock_no` / `vin` are silently stripped — breaking CPO detection (`cpo_ever` returns None) and reducing dealer-rooftop precision.

**Canonical fields string** (verbatim; see `references/cpo.md` for the master copy):

```
id,vin,price,miles,msrp,seller_name,dealer_id,city,state,zip,first_seen_at_date,last_seen_at_date,scraped_at_date,source,vdp_url,seller_type,inventory_type,is_certified,dom_active,dom_180,dom,stock_no,data_source
```

`page=1` pins ordering to the first page even when the upstream's silent default changes. Extract `num_found` (server-side total) separately from `listing_count` (length of returned `listings` array). When `num_found > listing_count`, the renderer flags a pagination gap (see "Pagination handling" below).

### Step 2 — `decode_vin_neovin`

```
decode_vin_neovin(vin)
```

Pipe through the standard truncation-envelope recovery. Extract current specs (year/make/model/trim/body_type/drivetrain/engine/transmission/msrp).

### Step 3 (optional) — dual-channel `predict_price_with_comparables`

**Trigger conditions** — fire step 3 ONLY when ALL of the following hold:

1. The appraiser explicitly requests fair-value or trade-in offer guidance. Trigger phrases: *"what's a fair offer"*, *"should I take this trade at $X"*, *"current fair value"*, *"trade-in value range"*, *"predicted price"*, or the appraiser supplies `miles` up-front.
2. The appraiser supplies the **current odometer reading** (miles). If miles is absent, halt with: *"To produce a current ML fair-value range for this trade-in, please provide the current odometer reading. Predicting on stale historical mileage produces misleading values."* — never default to `listings[0].miles` from history.

When triggered, fire BOTH dealer_type predicts in parallel inside Wave A (mirrors W1's dual-channel convention):

```
predict_price_with_comparables(vin, miles=<USER>, zip, dealer_type=franchise)    → nocpo_franchise
predict_price_with_comparables(vin, miles=<USER>, zip, dealer_type=independent)  → nocpo_independent
```

For pure history requests (no fair-value intent, no miles supplied), skip step 3 entirely and surface a Next-Step pointing to `/price-check <VIN>` (W1) for full pricing or `appraiser:vehicle-appraiser` for a full appraisal.

### Parallelization

Steps 1–3 are independent (each takes only the VIN + zip + miles, never each other's parsed output). Issue them as a single Wave A batch:

- Without step 3: 2 calls in parallel (history + decode). Total ≈ 12s.
- With step 3: 4 calls in parallel (history + decode + 2 predicts). Total ≈ 12–15s.

## Truncation handling

`get_car_history` does not chronically truncate at default `rows`, but `decode_vin_neovin` and `predict_price_with_comparables` do. Apply the standard recovery from `references/truncation-recovery.md` — `Write` the envelope to scratch, re-read, unwrap, parse.

## Pagination handling

When `get_car_history.num_found > listing_count`:

- **Render normally** — first-page listings drive the trajectory + flags.
- **Emit DQ event (b)** under Data Quality Notes: *"History pagination gap: num_found=<N> exceeds listing_count=<n> — first page shown; cumulative-change and dealer-hop counts reflect partial coverage."*
- **Surface as a Key Signals bullet**: *"⚠ History truncated to first page (num_found=<N>); cumulative price change and dealer-hop count are partial-coverage signals — request the full trajectory if needed."*

W2 does **not** automatically chain page=2+. Most VINs have ≤25 history rows; auto-pagination is deferred.

## Cross-batch self-comp exclusion

**N/A for W2.** A `get_car_history` response contains rows for ONE VIN only — the subject VIN listed by various dealers over time. There are no auxiliary VINs in the history response to exclude.

When the appraiser chains into W1 after W2 in the same session, the subject VIN goes via shadow-listing detection in W1's active-comp parser — that's where the cross-workflow VIN exclusion lives.

## Step 3 user-flow gate

Step 3 is **opt-in**. The flowchart:

1. Appraiser invokes W2 → run steps 1 + 2 in Wave A.
2. After Wave A returns, parse the appraiser's intent:
   - Pure history request (*"show me this VIN's history"*, *"what dealers has it been at"*) → render trajectory + flags + Next-Step pointing to `/price-check <VIN>` (W1) and `appraiser:vehicle-appraiser`. Done.
   - Fair-value or trade-in offer intent (*"what's it worth"*, *"should I take this trade at $X"*) → check whether the appraiser supplied current odometer.
     - Miles supplied → fire dual-channel predicts in a follow-up wave (or include in the original Wave A if known up-front). Render Current Wholesale-vs-Retail Spread block.
     - Miles missing → halt with the C4 prompt; do not auto-default to history miles.

If miles is supplied up-front in the original W2 invocation, fire all 4 calls in a single Wave A (history + decode + 2 predicts).

## Derived signals from the history

From the parsed `listings` (sorted desc by `first_seen_at_date`):

- **`dealer_count`** — distinct dealers the VIN has been listed at. Compute via `dealer_id` primary; when `dealer_id` is `None` on a row, fall back to `dealer_name` (often the same dealer with a missing ID). Emit `dealer_count_source ∈ {"dealer_id", "dealer_name", "mixed"}` for provenance.
- **`multi_dealer_churn`** — `True` when `dealer_count > 2 AND listing_count >= 4`. Indicates the VIN has bounced through multiple dealers — a possible problem unit (auction return, condition issue) the appraiser should investigate.
- **`sharp_drops`** — list of `(date_from, date_to, drop_pct)` tuples where consecutive listings show a single-step price drop ≥ 15%. Indicates either a problem unit or a forced sale at one dealer.
- **`decertified`** — fires when `cpo_ever == True` AND the most recent listing has `is_certified == False` (explicit `0`, NOT `None`). See `references/cpo.md`.
- **`cum_change_pct`** — `(latest_price - earliest_priced_price) / earliest_priced_price * 100`. When some rows have null prices, drop them from the cumulative calc and emit DQ event (e) noting the baseline shift to the oldest priced row.
- **`cumulative_vin_aging`** — `max(listings[*].dom_active)`. Renders only when at least one row has a non-null `dom_active`. When all are null, render *"Cumulative VIN aging: unavailable (dom_active absent across all history rows)"* and emit DQ event (e).

## Render

Cross-reference `assets/output-template.md` W2 section. Key blocks for W2:

- **Decoded Specs** (from step 2).
- **Price Trajectory** — W2-specific 8-col table: `Date | Dealer | Type | Inv | Price | Miles | DOM | CPO?` — one row per history listing, sorted desc by first-seen date.
- **Red Flags** — `multi_dealer_churn`, `sharp_drops`, `decertified` (per `references/cpo.md`). Dealer-hop provenance label from `dealer_count_source`.
- **Cumulative VIN aging** — `max(dom_active)`.
- **Listing-vs-transaction caveat** — always when `listing_count >= 2`: *"Note: history reflects listings (asking prices), not necessarily transactions. A price drop may or may not represent a realised sale."*
- **Dealer-hop dedup source** — always: *"Dealer-hop count computed via `<dealer_count_source>` (per-row dealer identifier)."*
- **Current Wholesale-vs-Retail Spread** — when step 3 ran. Both Franchise (Retail) and Independent (Wholesale-proxy) MarketCheck Prices side-by-side with the spread.
- **Data Quality Notes** — if non-empty.
- **Key Signals** — 3–5 bullets, including any pagination warning.
- **Next Steps** — always include *"For a full comparable-backed appraisal range, run `appraiser:vehicle-appraiser`. For current market context against this VIN, run `/price-check <VIN>` (W1)."*
- **Self-check footer**.

CPO render rules and tri-state column behavior inherit from `references/cpo.md` and `assets/output-template.md`.

## Data Quality event log discipline for W2

- **(a)** MCP tool errors / non-200 responses recovered from — tool name, error_type. Specifically: `get_car_history` shape errors, decode `ok=false`, predict `ok=false` (when step 3 fired).
- **(b)** Truncation envelope unwraps — count of unwrapped responses across the wave's calls.
- **(b)** History pagination gap — `num_found > listing_count` (see "Pagination handling").
- **(e)** Fallback source: `cum_change_pct` baseline shifted to oldest priced row (when null-priced rows were dropped from the cumulative calc).
- **(e)** Fallback source: cumulative VIN aging unavailable (`dom_active` absent across all history rows).
- **(g)** Workflow branch skipped by design: predict step (step 3 not invoked); CPO branch skipped (appraiser stated non-CPO).

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| Malformed VIN | VIN doesn't match `^[A-HJ-NPR-Z0-9]{17}$` | Standard VIN-format halt. No MCP calls fired. |
| UK profile | `country == "UK"` | Halt at pre-check with the UK-not-supported message. |
| CA profile | `country == "CA"` | Standard CA halt. |
| `get_car_history` `ok=false` (truncation unrecoverable / shape error / 5xx) | Critical history call failed | Halt with the error; suggest re-run. Do NOT silently render an empty trajectory. |
| `listing_count == 0` | Empty history | Halt with *"No historical listings found for VIN — vehicle may be too new, dealer-only listed, or the VIN may be incorrect."* Render Decoded Specs from step 2 if it succeeded; suppress trajectory + flags. |
| `listing_count == 1` | Single listing | Render single-row trajectory; suppress `cum_change_pct` (None); suppress `sharp_drops` (None); suppress `multi_dealer_churn` (1 dealer); Key Signals: *"Only 1 historical listing found — trajectory analysis requires at least 2 listings."* |
| All listings null price | Every row has `price=None` | Render trajectory with `—` in Price column; `cum_change_pct is None`; suppress `sharp_drops`; emit DQ event (e). |
| Truncation envelope on `get_car_history` | MCP returns truncation wrapper | Standard `Write` + re-read recipe. |
| `num_found > listing_count` | Pagination gap | Render trajectory + flags as normal; emit DQ event (b) + Key Signals bullet. |
| All-null `dom_active` | No cumulative aging data | Render *"Cumulative VIN aging: unavailable (dom_active absent across all history rows)"*; emit DQ event (e). |
| FSBO/auction-only history | All rows have `seller_type ∈ {fsbo, auction}` | Render trajectory with caveat: *"⚠ All history rows are non-dealer (FSBO / auction); dealer-hop and decertified flags use dealer-name semantics that may not apply to non-dealer sellers."* Flags still fire (data is valid for the rows present). |
| Decode `ok=false` | Step 2 fails | Suppress Decoded Specs block; render trajectory + flags from step 1; emit DQ event (a). |
| Predict `ok=false` (step 3) | One or both predicts failed | Suppress Current Wholesale-vs-Retail Spread block (or render the surviving channel only); render trajectory + flags from step 1; emit DQ event (a). |
| Step 3 invoked without `miles` | Appraiser asks for fair-value but didn't supply odometer | Halt with: *"To produce a current ML fair-value range for this trade-in, please provide the current odometer reading."* |
| `cpo_ever == True AND current.is_certified is None` | Vehicle CPO in history; current row is_certified absent | Render under the trajectory: *"⚠ This vehicle was CPO at one or more historical listings; the current listing's CPO status is unknown — confirm with the seller before finalising the valuation."* `decertified` flag does NOT fire (current is None, not explicitly False). |
