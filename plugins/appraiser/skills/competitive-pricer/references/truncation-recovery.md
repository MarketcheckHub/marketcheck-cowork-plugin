# Envelope handling and truncation recovery

Two distinct concepts. Handling them separately.

## The envelope is universal (almost)

Every `search_active_cars`, `search_past_90_days`, `decode_vin_neovin`, `predict_price_with_comparables`, and `get_car_history` response arrives wrapped as:

```json
{"result": "<stringified JSON of the real response>"}
```

This wrapping happens on **every** call — successful or truncated, 1KB or 150KB. It is the server's standard response shape, not a truncation signal.

**Exception:** `get_sold_summary` is the **only** tool that returns raw JSON without the envelope — the direct `{"success": true, "service": "sold_summary", "data": {...}}` shape. When parsing, detect by shape: if the response is a string wrapped in `{"result": "<string>"}`, unwrap with `json.loads` on the `result` key; otherwise pass through.

## The truncation signal is separate

When the envelope's inner JSON exceeds the caller's token budget, the MCP tool emits a synthetic error string AND saves the full envelope to disk:

```
Error: result (124389 chars) exceeds maximum allowed tokens.
Output has been saved to /tmp/mcp-output/<uuid>.json
```

The saved file contains the same `{"result": "<stringified JSON>"}` envelope — just stored on disk instead of inlined. Log a Data Quality Notes event (b) — "truncation-envelope unwrap via file" — when this path fires.

**Tools that chronically truncate in practice:**

- `decode_vin_neovin` — ~150KB envelopes on every real call
- `predict_price_with_comparables` — ~100KB envelopes on every real call (especially when W1 fires this tool 2–4 times for the dual-channel + CPO branch)

Treat the saved-to-file recovery as the **expected** path for these two tools, not an exception. `search_active_cars` / `search_past_90_days` / `get_car_history` truncate only when `rows` is set high; the default small-payload fetches arrive inline.

## Inline envelope-wrapped responses

`search_active_cars` and `search_past_90_days` routinely return inline — the MCP runtime doesn't save them to a file. They arrive in the conversation context as envelope-wrapped JSON text.

For inline responses, the recipe is:

1. Read the `result` key's string value from the response.
2. `json.loads` that string to get the real payload.
3. Extract the canonical fields you need (see "Canonical field extraction" below).
4. **Save the unwrapped payload to disk via the `Write` tool** at `/tmp/marketcheck/<session-scratch>/<role>.json` — both as a working-set checkpoint AND so any subsequent re-read uses the unwrapped form, not the envelope.

The scratch directory pattern is `/tmp/marketcheck/<scratch-id>/` where `<scratch-id>` is a short identifier you pick at the start of the workflow (e.g., `cpr-<epoch-seconds>`). Files are session-local and regenerated each run.

## Truncated-to-file responses

When the MCP tool returns the synthetic "saved to <path>" error:

1. Read the file at `<path>`. It contains the same `{"result": "<stringified JSON>"}` envelope.
2. Unwrap and parse the inner string as in the inline case.
3. Extract canonical fields.
4. If unwrap fails (file corrupt, inner string not parseable), render a caveat line for the affected block and continue:
   - Prediction call truncated → `"Franchise (Retail) MarketCheck Price: unavailable (prediction call truncated; using comp median as anchor)"`
   - Comp set call truncated → `"Comparable set: N rows rendered from partial response; full set unavailable"`
   - Sold-90d call truncated → omit the realised-sales anchor; log a DQ event (b)

Do NOT halt the whole workflow for one truncated call. One truncated call should not kill four others' worth of usable data.

## Canonical field extraction

Per response, extract ONLY the fields the workflow needs — never carry the full envelope downstream. Discard the rest.

### `decode_vin_neovin`
Keep: `year`, `make`, `model`, `trim`, `body_type`, `drivetrain`, `engine`, `transmission`, `msrp` (when present). These nine fields fully drive Decoded Specs and downstream search filters.

### `predict_price_with_comparables`
Keep: `predicted_price` (rename to `marketcheck_price` for parity with the comparable-set vocabulary), `predicted_price_lower_bound`, `predicted_price_upper_bound`, `active_set_comparables.length` (call this `comparables_n`), and `active_set_comparables[*].{vin, price, miles, dom_active, dealer_name, dealer_type, distance, is_certified}` if rendering comps. Discard `predicted_price_rmse`, `model_version`, and other model metadata.

### `search_active_cars`
Keep `num_found`, `stats.{price, miles, dom_active}.{min, max, mean, median, count, percentiles}` (when `stats=` was passed), and per-listing fields: `vin`, `price`, `miles`, `dom_active`, `dealer.name → dealer_name`, `dealer.dealer_type → dealer_type`, `dealer.city → dealer_city`, `dist → distance_mi`, `is_certified`, plus from `build.{body_type, drivetrain, engine, transmission}` for the display-only spec subtitle.

**Per-listing computed fields** (the model derives these in-prompt before rendering):

- `price_change_amount` = signed dollar change from `ref_price` to current `price`. When `ref_price` is null or zero, set to `null`.
- `price_change_percent` = pulled from the listing root when present; otherwise derived from `price_change_amount / ref_price`. Treat sign-near-zero (`abs(percent) < 0.5%`) as effectively no change.

Filter rows where `price` is null, zero, or missing — **never render a $0 row to the user**. The `price_range="1-*"` filter on the call already excludes most of these, but apply the client-side guard for defence-in-depth.

### `search_past_90_days`
Keep `num_found`, `stats.{price, miles, dom_active}.{min, max, mean, median}`, per-listing fields as above when listings are returned. Used for the realised-sale anchor and the days-to-sell context.

### `get_car_history`
Keep `num_found`, `listing_count` (= length of `listings` array on the page), and per-listing fields: `vin`, `price`, `miles`, `msrp`, `seller_name → dealer_name`, `dealer_id`, `city`, `state`, `zip`, `first_seen_at_date`, `last_seen_at_date`, `scraped_at_date`, `source`, `vdp_url`, `seller_type`, `inventory_type`, `is_certified`, `dom_active`, `dom_180`, `dom`, `stock_no`, `data_source`. **The `fields=` request parameter must enumerate this list verbatim** — without it, the server strips `is_certified` / `dom_*` / `msrp` / `dealer_id` / `stock_no` / `vin` (Optional Fields per `mcp_server_tool_docs/get_car_history.md`). See `references/cpo.md` for the full string.

### `get_sold_summary`
Keep `data.data[*].{month, inventory_type, state, model, sold_count, average_sale_price, avg_msrp, sale_price_range, sale_price_std_dev, rank}`. See `references/sold-summary-safety.md` for the response-shape quirks (doubly-nested `data.data[]`, `avg_msrp` not `average_msrp`).

## Banned paths

- **Do NOT `cat` the saved file into context.** It defeats the point of the envelope. Read the file once, unwrap, extract canonical fields, persist the unwrapped extract.
- **Do NOT retry the original MCP call without tightening filters.** The same truncation will recur.
- **Do NOT assume the envelope's inner JSON is directly parseable.** It is stringified; it must be JSON-parsed after extracting the `result` key.
- **Do NOT fail silently.** Always log a Data Quality Notes event (b) when a truncation envelope was unwrapped.
- **Do NOT hand-key listings into a custom merge step.** When asc + desc need to be merged, dedupe by VIN (desc-first on duplicates per the tail-coverage semantic), exclude the subject VIN, count `overlap_count` and `pulled_count` honestly. The vocabulary lives in `references/w1-price-check.md` "Merge asc + desc" section.
- **Do NOT hand-fabricate values to fill the envelope's gap.** If the prediction call returned `null` for `predicted_price`, render `—` and emit a caveat. Never substitute model knowledge for a missing predicted price.

## Why this discipline

The reference skill (`plugins/dealer/skills/competitive-pricer`) ships deterministic Python scripts that enforce these contracts in code. This skill is agent-driven — the model is the parser. That means **the model is the only enforcement** for these rules. One slip into hand-keying, hand-merging, or hand-fabricating a number that should have come from the response is one defensibility hole an appraiser cannot afford in dispute.
