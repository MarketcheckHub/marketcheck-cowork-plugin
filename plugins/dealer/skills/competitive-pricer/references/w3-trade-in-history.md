# W3 — Trade-In VIN Price History

Triggered by "what's the history on this trade", "previous listings for VIN X", "show this VIN's price trajectory", etc. **US-only** — halt with *"Trade-In workflow is US-only (requires `get_car_history`, not available for UK)."* on a UK profile.

W3 is a **history viewer** workflow: surface the VIN's listing trajectory, dealer-hop pattern, sharp-drop and decertified red flags, and (optionally) a current ML fair-value prediction when the dealer is sizing a trade-in offer. W3 does **not** compute trade-in offer math (recon cost, target margin, target wholesale price); for that, route the user to `/price-check <VIN>` (W1) after they have the current odometer reading.

## Required inputs

- **VIN** (mandatory). Validate format on entry: 17 characters matching `^[A-HJ-NPR-Z0-9]{17}$` (excludes I / O / Q which are not used in real VINs). Halt at pre-check with *"VIN is malformed (must be 17 chars, no I/O/Q). Halt — please correct and re-run."* if invalid; **fire no MCP calls** until the format check passes.
- **Current odometer (miles)**: required **only when step 3 (predict) is invoked**. See section "Step 3 user-flow gate" below.

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | *"Trade-In workflow is US-only (requires `get_car_history`, not available for UK)."* |
| VIN doesn't match `^[A-HJ-NPR-Z0-9]{17}$` | *"VIN is malformed (must be 17 chars, no I/O/Q). Halt — please correct and re-run."* |
| VIN missing entirely | *"W3 requires a VIN. Please supply the 17-char VIN you'd like to look up."* |

## Wave A — single parallel batch (3 calls, or 4 with step 3)

All calls in Wave A take only the VIN (and miles + zip for predict). No cross-dependencies. Issue every call within the wave in a SINGLE batch (multiple MCP tool calls in the same response); wait for the whole wave to return before rendering.

### Step 1 — `get_car_history`
```
get_car_history(
  vin,
  sort_order="desc",
  page=1,                                              # NEW — pin to page 1 for deterministic ordering
  fields=CANONICAL_FIELDS_PARAM
)
```
Pipe through `scripts/parse_history.py` (truncation envelope: `parse_history.py --file <path>`).

The explicit `fields=` enumerates Optional Fields per `mcp_server_tool_docs/get_car_history.md`; without it, `is_certified` / `dom_*` / `msrp` / `dealer_id` / `stock_no` / `vin` are silently stripped — breaking CPO detection (`cpo_ever` returns None) and reducing dealer-rooftop precision.

`page=1` pins ordering to the first page even when the upstream's silent default changes. The parser surfaces `num_found` separately from `listing_count`; when `num_found > listing_count`, the renderer flags a pagination gap (see section "Pagination handling").

#### CANONICAL_FIELDS_PARAM (verbatim — keep in sync)

```
id,vin,price,miles,msrp,seller_name,dealer_id,city,state,zip,first_seen_at_date,last_seen_at_date,scraped_at_date,source,vdp_url,seller_type,inventory_type,is_certified,dom_active,dom_180,dom,stock_no,data_source
```

This string is mirrored in:
- `scripts/parse_history.py` constant `CANONICAL_FIELDS_PARAM` (lines 89–94).
- `references/w1-price-check.md` Wave C CPO-ambiguous path.
- `references/cpo.md` rule 4.

Keep all four in sync if changed.

### Step 2 — `decode_vin_neovin`
```
decode_vin_neovin(vin)
```
Pipe through `scripts/parse_decode.py` for current specs (year/make/model/trim/body_type/drivetrain/engine/transmission/MSRP).

### Step 3 (optional) — dual-channel `predict_price_with_comparables`

**Trigger conditions** — fire step 3 ONLY when ALL of the following hold:
1. The user explicitly requests fair-value or trade-in offer guidance. Trigger phrases: "what's a fair offer", "should I take this trade", "trade-in value", "what's it worth", "fair-value prediction", "predicted price", or the user supplies `miles` up-front.
2. The user supplies the **current odometer reading** (miles). If miles is absent, halt with *"To run a current ML fair-value prediction for this trade-in, please provide the current odometer reading (miles). Predicting on stale historical mileage produces misleading values."* — never default to `listings[0].miles` from history.

When triggered, fire BOTH dealer_type predicts in parallel inside Wave A (mirrors W1's dual-channel convention):

```
predict_price_with_comparables(vin, miles=<USER>, zip, dealer_type=<dealer_type_lower>)         # PRIMARY
predict_price_with_comparables(vin, miles=<USER>, zip, dealer_type=<dealer_type_opposite_lower>) # CONTEXT
```
Pipe each through `scripts/parse_predict.py`.

For pure history requests (no fair-value intent, no miles supplied), skip step 3 entirely and surface a Next-Step pointing to `/price-check <VIN>` for full pricing.

### Parallelization

Steps 1–3 are independent (each takes only the VIN + zip + miles, never each other's parsed output). Issue them as a single Wave A batch:
- Without step 3: 2 calls in parallel (history + decode). Total ≈ 12s.
- With step 3: 4 calls in parallel (history + decode + 2 predicts). Total ≈ 12–15s.

## Truncation handling

Truncation signature: `Error: result (N chars) exceeds maximum allowed tokens. Output has been saved to <path>`. The saved file wraps the real response as `{"result": "<stringified JSON>"}`.

Default recovery: pass `--file <path>` to `parse_history.py`. The parser unwraps the envelope and extracts canonical fields. Same recipe as W1's truncation handling — see `references/truncation-recovery.md` for the deep recipe and the rare deep-truncation subagent template.

## Pagination handling

When `parse_history.num_found > listing_count`:
- **Render normally** — the parser still returns the first page's listings + flags computed over those listings.
- **Emit DQ event (b)** under Data Quality Notes: *"History pagination gap: `num_found=<N>` exceeds `listing_count=<n>` — first page shown; cumulative-change and dealer-hop counts reflect partial coverage."*
- **Surface as a Key Signals bullet**: *"⚠ History truncated to first page (`num_found=<N>`); `cum_change_pct` and `dealer_count` are partial-coverage signals — re-run with explicit pagination if the full trajectory is needed."*

W3 does **not** automatically chain page=2+. Most VINs have ≤25 history rows; auto-pagination is deferred. If a future use case demands full coverage on long histories, W3 grows a Wave B for sequential page fetches.

## Cross-batch self-comp exclusion

**N/A for W3.** A `get_car_history` response contains rows for ONE VIN only — the subject VIN listed by various dealers over time. The parser's `vins_seen` is always `{subject_vin}` or `{}`; there are no auxiliary VINs in the history response.

When the user chains into W1 after W3 in the same session, the subject VIN goes via `--subject-vin` to W1's `parse_search.py` for shadow-listing detection. There is no `--exclude-vins` payload to forward from W3 (history rows don't contain other VINs).

## Render

Cross-reference: `assets/output-template.md` W3 section. Key blocks for W3:
- **Decoded Specs** (from step 2 parsed output)
- **Price Trajectory** (W3-specific table — `Date | Dealer | Type | Inv | Price | Miles | DOM | CPO?`)
- **Red Flags** (under trajectory: `multi_dealer_churn`, `sharp_drops`, `decertified` per parser-emitted `flags`; provenance label from `dealer_count_source`)
- **Cumulative VIN aging** (`max(listings[*].dom_active)` — render only when at least one row has non-null `dom_active`)
- **Listing-vs-transaction caveat** (always when `listing_count >= 2`)
- **Dealer-hop dedup source** (always — sources from `dealer_count_source`)
- **Current ML fair value** (when step 3 ran — both PRIMARY and CONTEXT lines)
- **Data Quality Notes** (if non-empty — see "DQ event log discipline" below)
- **Key Signals** (3–5 bullets, including any pagination warning)
- **Next Steps** — always include *"Run `/price-check <VIN>` against the current market to decide a fair offer."*
- **Self-check footer** (per shared template's items 1–12; 13–14 are N/A for W3)

CPO render rules and tri-state column behavior inherit from `assets/output-template.md` lines 879–910 — including the new "CPO history confirmed; current status unknown" caveat (when `cpo_ever is True AND current.is_certified is None`).

## Data Quality event log discipline for W3

Track and surface these events under Data Quality Notes when they fire:

- **(a)** MCP tool errors or non-200 responses recovered from — tool name, `error_type`, recovery path. Specifically: `parse_history` `ok=false`, `parse_decode` `ok=false`, `parse_predict` `ok=false`.
- **(b)** Truncation envelope unwraps — count of unwrapped responses across the wave's calls.
- **(b)** History pagination gap — `num_found > listing_count` (see section "Pagination handling").
- **(e)** Fallback source: `cum_change_pct` baseline shifted to oldest priced row (`<n>` rows had null prices) — fires when `dropped_null_price_count > 0`.
- **(e)** Fallback source: cumulative VIN aging unavailable (`dom_active` absent across all history rows) — fires when no row has a non-null `dom_active`.
- **(g)** Workflow branch skipped by design: predict (step 3 not invoked because user did not request fair-value); decode (step 2 was skipped or failed but trajectory still rendered).

## Step 3 user-flow gate

Step 3 is **opt-in**. The flowchart:

1. User invokes W3 → run steps 1 + 2 in Wave A.
2. After Wave A returns, parse the user's intent:
   - Pure history request ("show me this VIN's history", "what dealers has it been at") → render trajectory + flags + Next-Step pointing to `/price-check <VIN>`. Done.
   - Fair-value or trade-in offer intent ("what's it worth", "should I take this trade at $X") → check whether the user supplied current odometer.
     - Miles supplied → fire dual-channel predicts in a follow-up Wave A2 (or include in the original Wave A if known up-front). Render ML Fair Value block.
     - Miles missing → halt with the C4 prompt; do not auto-default to history miles.

If miles is supplied up-front in the original W3 invocation, fire all 4 calls in a single Wave A (history + decode + 2 predicts).

## Failure recovery and edge cases

W3 must handle each case below deterministically. Behavior is enumerated rather than improvised:

| Case | Trigger | Behavior |
|---|---|---|
| Malformed VIN | VIN doesn't match `^[A-HJ-NPR-Z0-9]{17}$` | Halt at pre-check with *"VIN is malformed (must be 17 chars, no I/O/Q). Halt — please correct and re-run."* No MCP calls fired. |
| UK profile | `profile.location.country == "UK"` | Halt at pre-check with *"Trade-In workflow is US-only (requires `get_car_history`, not available for UK)."* |
| `parse_history` `ok=false` (truncation unrecoverable / shape error / 5xx) | Parser emits `{ok: false, error_type, error}` | Halt the workflow; render the error message to the user; suggest re-run. Do NOT silently proceed to render an empty trajectory. |
| `listing_count == 0` | `parse_history` returns empty `listings` | Halt with *"No historical listings found for VIN — vehicle may be too new, dealer-only listed, or the VIN may be incorrect."* Render Decoded Specs from step 2 if it succeeded; suppress trajectory + flags. |
| `listing_count == 1` | Single listing only | Render single-row trajectory; suppress `cum_change_pct` (None); suppress `sharp_drops` (None); suppress `multi_dealer_churn` (1 dealer); render Key Signals: *"Only 1 historical listing found — trajectory analysis requires at least 2 listings."* |
| All listings null price | Every row has `price=None` | Render trajectory with `—` in Price column for every row; `cum_change_pct is None`; suppress `sharp_drops`; emit DQ event (e) "all history rows had null prices — cumulative change analysis unavailable." |
| Truncation envelope on `get_car_history` | MCP returns `{result: <stringified-json>}` exceeding-tokens wrapper | `Write` to scratch path; `parse_history.py --file <path>`. Standard recipe per `references/truncation-recovery.md`. |
| `num_found > listing_count` | Pagination gap | Render trajectory + flags as normal; emit DQ event (b) "history pagination gap: `num_found=X` > `listing_count=Y` — first page shown" + Key Signals bullet warning that `cum_change_pct` and `dealer_count` reflect partial coverage. |
| All-null `dom_active` across all rows | No row has cumulative aging data | Render *"Cumulative VIN aging: unavailable (`dom_active` absent across all history rows)"*; emit DQ event (e) "fallback source: dom_active server field absent." |
| `dropped_null_price_count > 0` | `cum_change_pct` baseline shifted | Emit DQ event (e) "cum_change_pct baseline shifted to oldest priced row (`<n>` null-priced rows)." |
| FSBO/auction-only history (no `seller_type=dealer`) | All rows have `seller_type ∈ {fsbo, auction}` | Render trajectory with caveat: *"⚠ All history rows are non-dealer (FSBO / auction); dealer-hop and decertified flags use dealer-name semantics that may not apply to non-dealer sellers."* Flags still fire (data is valid for the rows present). |
| Decode `ok=false` | Step 2 fails | Suppress Decoded Specs block; render trajectory + flags from step 1; emit DQ event (a). |
| Predict `ok=false` (when step 3 fired) | Step 3 fails (one or both predicts) | Suppress ML Fair Value block (or render the surviving channel only); render trajectory + flags from step 1; emit DQ event (a). |
| Step 3 invoked without `--miles` | User asks for fair-value but did not supply current odometer | Halt with *"To run a current ML fair-value prediction for this trade-in, please provide the current odometer reading (miles). Predicting on stale historical mileage produces misleading values."* |
| `cpo_ever is True AND current.is_certified is None` | Vehicle CPO in history; current row is_certified field absent | Render the L5 caveat under the trajectory: *"⚠ This vehicle was CPO at one or more historical listings; the current listing's CPO status is unknown — confirm with the seller before pricing."* `decertified` flag does NOT fire (current is None, not explicitly False). |
