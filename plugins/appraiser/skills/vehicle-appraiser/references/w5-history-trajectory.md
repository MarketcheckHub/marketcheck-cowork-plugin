# W5 — Historical Value Trajectory

Triggered by "what's the price history on this VIN", "show me this VIN's listing trajectory", "how has this vehicle depreciated over time", "previous listings", "depreciation rate for this VIN", "VIN history", etc. **US-only** — halt with *"Historical Trajectory workflow is US-only — `get_car_history` is not available for UK."* on a UK profile.

W5 is a **history viewer** workflow: surface the VIN's listing trajectory, dealer-hop pattern, sharp-drop and decertified red flags, total cumulative depreciation, and (optionally) a current ML fair-value prediction when the appraiser is also evaluating a current value. W5 does **not** compute appraisal band — for the comparable-backed value range, route the user to W1 (`/full-appraisal <VIN>`) once they have the current odometer.

W5 is especially useful for **appraiser due-diligence**: verifying that a vehicle's stated history (single-owner, dealer-maintained, never-totaled) matches the observed listing trajectory before issuing a defensible appraisal.

## Required inputs

- **VIN** (mandatory). Validate format on entry: 17 characters matching `^[A-HJ-NPR-Z0-9]{17}$` (excludes I / O / Q which are not used in real VINs). Halt at pre-check with *"VIN is malformed (must be 17 chars, no I/O/Q). Halt — please correct and re-run."* if invalid; **fire no MCP calls** until the format check passes.
- **Current odometer (miles)**: required **only when the optional ML fair-value branch is invoked** (see "User-flow gate" below).

## Pre-check halts

| Trigger | Halt message |
|---|---|
| `profile.location.country == "UK"` | *"Historical Trajectory workflow is US-only — `get_car_history` is not available for UK."* |
| `profile.location.country` not in (US, UK) | Halt per SKILL.md country routing. |
| VIN doesn't match `^[A-HJ-NPR-Z0-9]{17}$` | *"VIN is malformed (must be 17 chars, no I/O/Q). Halt — please correct and re-run."* |
| VIN missing entirely | *"W5 requires a VIN. Please supply the 17-char VIN you'd like to look up."* |

## Wave A — single parallel batch (2 calls, or 4 with optional fair-value branch)

All calls in Wave A take only the VIN (and miles + zip for predict). No cross-dependencies. Issue every call within the wave in a SINGLE batch (multiple MCP tool calls in the same response); wait for the whole wave to return before rendering.

### Step 1 — `get_car_history`

```
get_car_history(
  vin,
  sort_order="desc",
  page=1,                                              # pin to page 1 for deterministic ordering
  fields=parse_history.CANONICAL_FIELDS_PARAM
)
```

Pipe through `scripts/parse_history.py` (truncation envelope: `parse_history.py --file <path>`).

The explicit `fields=` enumerates Optional Fields per `mcp_server_tool_docs/get_car_history.md`; without it, `is_certified` / `dom_*` / `msrp` / `dealer_id` / `stock_no` / `vin` are silently stripped — breaking CPO detection (`cpo_ever` returns None) and reducing dealer-rooftop precision.

`page=1` pins ordering to the first page even when the upstream's silent default changes. The parser surfaces `num_found` separately from `listing_count`; when `num_found > listing_count`, the renderer flags a pagination gap (see "Pagination handling" below).

### Step 2 — `decode_vin_neovin`

```
decode_vin_neovin(vin)
```

Pipe through `scripts/parse_decode.py` for current specs (year/make/model/trim/body_type/drivetrain/engine/transmission/MSRP).

### Step 3 (optional) — dual-channel `predict_price_with_comparables`

**Trigger conditions** — fire step 3 ONLY when ALL of the following hold:
1. The user explicitly requests fair-value or current-value guidance ("what's it worth now", "is this a fair offer", "fair-value prediction") OR supplies `miles` up-front.
2. The user supplies the **current odometer reading** (miles). If miles is absent, halt with *"To run a current ML fair-value prediction, please provide the current odometer reading (miles). Predicting on stale historical mileage produces misleading values."* — never default to `listings[0].miles` from history.

When triggered, fire BOTH dealer_type predicts in parallel inside Wave A (mirrors W1's dual-channel convention):

```
predict_price_with_comparables(vin, miles=<USER>, zip, dealer_type="franchise")   # role: nocpo_franchise
predict_price_with_comparables(vin, miles=<USER>, zip, dealer_type="independent") # role: nocpo_independent
```

Pipe each through `scripts/parse_predict.py`.

For pure history requests (no fair-value intent, no miles supplied), skip step 3 entirely and surface a Next-Step pointing to `/full-appraisal <VIN>` (W1) for full pricing.

### Parallelization

Steps 1–3 are independent. Issue them as a single Wave A batch:
- Without step 3: 2 calls in parallel (history + decode). Total ≈ 12s.
- With step 3: 4 calls in parallel (history + decode + 2 predicts). Total ≈ 12–15s.

## Truncation handling

Truncation signature: `Error: result (N chars) exceeds maximum allowed tokens. Output has been saved to <path>`. Default recovery: pass `--file <path>` to `parse_history.py`. Same recipe as W1's truncation handling — see `references/truncation-recovery.md`.

## Pagination handling

When `parse_history.num_found > listing_count`:
- **Render normally** — the parser still returns the first page's listings + flags computed over those listings.
- **Emit DQ event (b)** under Data Quality Notes: *"History pagination gap: `num_found=<N>` exceeds `listing_count=<n>` — first page shown; cumulative-change and dealer-hop counts reflect partial coverage."*
- **Surface as a Key Signals bullet**: *"⚠ History truncated to first page (`num_found=<N>`); `cum_change_pct` and `dealer_count` are partial-coverage signals — re-run with explicit pagination if the full trajectory is needed."*

W5 does **not** automatically chain page=2+. Most VINs have ≤25 history rows; auto-pagination is deferred.

## Cross-batch self-comp exclusion

**N/A for W5.** A `get_car_history` response contains rows for ONE VIN only — the subject VIN listed by various dealers over time. The parser's `vins_seen` is always `{subject_vin}` or `{}`; there are no auxiliary VINs in the history response.

When the user chains into W1 after W5 in the same session, the subject VIN goes via `--subject-vin` to W1's `parse_search.py` for shadow-listing detection.

## Render

Cross-reference: `assets/output-template.md` W5 section. Key blocks for W5:

1. **Vehicle Identification** — from step 2 parsed output (always when decode succeeded).
2. **Price Trajectory** — W5-specific table: `Date | Dealer | Type | Inv | Price | Miles | DOM | CPO?`. Source: `parse_history.listings[*]` (already sorted desc).
3. **Cumulative Depreciation Summary** — total cumulative price change, average per-listing-hop drop, total days on market across all listings, number of unique dealers (with `dealer_count_source` provenance label).
4. **Red Flags** — under trajectory: `multi_dealer_churn`, `sharp_drops`, `decertified` per parser-emitted `flags`; provenance label from `dealer_count_source`.
5. **Cumulative VIN aging** — `max(listings[*].dom_active)` — render only when at least one row has non-null `dom_active`.
6. **Listing-vs-transaction caveat** (always when `listing_count >= 2`).
7. **Dealer-hop dedup source** (always — sources from `dealer_count_source`).
8. **Current ML Fair Value** (when step 3 ran — both franchise and independent lines).
9. **Data Quality Notes** (if non-empty).
10. **Key Signals** (3–5 bullets, including any pagination warning).
11. **Next Steps** — always include *"Run `/full-appraisal <VIN>` against the current market for a comparable-backed value range with confidence band."*
12. **Self-check footer**.

CPO render rules and tri-state column behavior inherit from `assets/output-template.md` — including the "CPO history confirmed; current status unknown" caveat (when `cpo_ever is True AND current.is_certified is None`).

## Data Quality event log discipline for W5

Track and surface these events under Data Quality Notes when they fire:

- **(a)** MCP tool errors or non-200 responses recovered from — tool name, `error_type`, recovery path. Specifically: `parse_history` `ok=false`, `parse_decode` `ok=false`, `parse_predict` `ok=false`.
- **(b)** Truncation envelope unwraps — count of unwrapped responses across the wave's calls.
- **(b)** History pagination gap — `num_found > listing_count`.
- **(e)** Fallback source: `cum_change_pct` baseline shifted to oldest priced row (`<n>` rows had null prices) — fires when `dropped_null_price_count > 0`.
- **(e)** Fallback source: cumulative VIN aging unavailable (`dom_active` absent across all history rows) — fires when no row has a non-null `dom_active`.
- **(g)** Workflow branch skipped by design: predict (step 3 not invoked because user did not request fair-value); decode (step 2 was skipped or failed but trajectory still rendered).

## User-flow gate (step 3)

Step 3 is **opt-in**. The flowchart:

1. User invokes W5 → run steps 1 + 2 in Wave A.
2. After Wave A returns, parse the user's intent:
   - Pure history request ("show me this VIN's history", "what dealers has it been at") → render trajectory + flags + Next-Step pointing to `/full-appraisal <VIN>`. Done.
   - Fair-value or current-value intent ("what's it worth now", "is this a fair offer at $X") → check whether the user supplied current odometer.
     - Miles supplied → fire dual-channel predicts in a follow-up Wave A2 (or include in the original Wave A if known up-front). Render Current ML Fair Value block.
     - Miles missing → halt with the prompt; do not auto-default to history miles.

If miles is supplied up-front in the original W5 invocation, fire all 4 calls in a single Wave A (history + decode + 2 predicts).

## Failure recovery and edge cases

| Case | Trigger | Behavior |
|---|---|---|
| Malformed VIN | format check fails | Halt at pre-check. No MCP calls fired. |
| UK profile | `country == "UK"` | Halt at pre-check. |
| `parse_history` `ok=false` (truncation unrecoverable / shape error / 5xx) | Parser emits `{ok: false, error_type, error}` | Halt the workflow; render the error to the user; suggest re-run. Do NOT silently render an empty trajectory. |
| `listing_count == 0` | parser returns empty `listings` | Halt with *"No historical listings found for VIN — vehicle may be too new, dealer-only listed, or the VIN may be incorrect."* Render Vehicle Identification from step 2 if it succeeded. |
| `listing_count == 1` | Single listing only | Render single-row trajectory; suppress `cum_change_pct` (None); suppress `sharp_drops` (None); suppress `multi_dealer_churn` (1 dealer); render Key Signals: *"Only 1 historical listing found — trajectory analysis requires at least 2 listings."* |
| All listings null price | Every row has `price=None` | Render trajectory with `—` in Price column for every row; `cum_change_pct is None`; suppress `sharp_drops`; emit DQ event (e). |
| Truncation envelope on `get_car_history` | MCP returns `{result: <stringified-json>}` exceeding-tokens wrapper | `Write` to scratch path; `parse_history.py --file <path>`. Standard recipe per `references/truncation-recovery.md`. |
| `num_found > listing_count` | Pagination gap | Render trajectory + flags as normal; emit DQ event (b) + Key Signals bullet warning. |
| All-null `dom_active` across all rows | No row has cumulative aging data | Render *"Cumulative VIN aging: unavailable (`dom_active` absent across all history rows)"*; emit DQ event (e). |
| `dropped_null_price_count > 0` | `cum_change_pct` baseline shifted | Emit DQ event (e). |
| FSBO/auction-only history (no `seller_type=dealer`) | All rows non-dealer | Render trajectory with caveat: *"⚠ All history rows are non-dealer (FSBO / auction); dealer-hop and decertified flags use dealer-name semantics that may not apply to non-dealer sellers."* |
| Decode `ok=false` | Step 2 fails | Suppress Vehicle Identification block; render trajectory + flags from step 1; emit DQ event (a). |
| Predict `ok=false` (when step 3 fired) | One or both predicts fail | Suppress Current ML Fair Value block (or render the surviving channel only); render trajectory + flags from step 1; emit DQ event (a). |
| Step 3 invoked without miles | User asks for fair-value but no current odometer | Halt with the prompt. |
| `cpo_ever is True AND current.is_certified is None` | Vehicle CPO in history; current row's is_certified field absent | Render the caveat: *"⚠ This vehicle was CPO at one or more historical listings; the current listing's CPO status is unknown — confirm with the seller before pricing."* `decertified` flag does NOT fire (current is None, not explicitly False). |
