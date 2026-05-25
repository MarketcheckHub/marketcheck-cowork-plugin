# Truncation Recovery — Depreciation-Tracker Edition

The MCP server returns large responses inside a `{"result": "<stringified
JSON>"}` envelope; some responses are large enough that the agent's
tool_result string is truncated mid-payload. Recovery is via the canonical
`--file` parser pattern.

## Tools that can truncate in this skill

- `decode_vin_neovin` — chronic truncation (~150KB envelopes). W1 Wave B
  (rep-VIN MSRP decode) hits this. Always recover via
  `parse_decode.py --file <path>`.
- `search_active_cars` — used in W1 Wave A (rep-VIN selection, `rows=1`,
  no dealer/build objects except `include_build_object=true`). Small payload
  — truncation is rare but the recipe still applies if it fires.
- `get_sold_summary` — observed truncation is rare with the prescribed
  parameter set (`limit=5000`, `ranking_dimensions` minimal,
  `top_n` ≤ 30). When it does fire, recover via
  `parse_sold_summary.py --file <path>`.
- `get_car_history` — NOT used in depreciation-tracker.
- `predict_price_with_comparables` — NOT used.

## Envelope shape

Every search and decode response is envelope-wrapped:
`{"result": "<stringified JSON>"}`. `_common._maybe_unwrap` handles this.
`get_sold_summary` is the **exception** — it returns raw JSON without the
envelope, but `_maybe_unwrap` passes unwrapped payloads through
transparently.

## Default recovery (every parser supports it)

```
# 1. agent saves the raw envelope to the run directory (Write tool)
Write(file_path="/tmp/marketcheck/<session.run_id>/<name>.json",
      content="<full envelope-wrapped response verbatim>")

# 2. parse via --file
<parser>.py --file /tmp/marketcheck/<session.run_id>/<name>.json [<flags>]
```

**Always read `session.run_id` from the loaded profile** — it's auto-assigned
by `scripts/load_profile.py` as `dt-<epoch>-<8hex>`. Concurrent skill
invocations get distinct run_ids; never hardcode `dt-run` (the legacy
backward-compat default is concurrent-UNSAFE).

For each MCP call in this skill, the canonical `<name>` token:

| Workflow | Call | `<name>` token |
|---|---|---|
| W1 | `get_sold_summary` per period | `sold-<period-label>` (e.g., `sold-current`, `sold-60d`) |
| W1 | `search_active_cars` rep-VIN | `asc-rep` |
| W1 | `decode_vin_neovin` | `decode` |
| W2 | `get_sold_summary` body current/prior | `sold-body-<period>` |
| W2 | `get_sold_summary` fuel current/prior | `sold-fuel-<period>` |
| W3 | `get_sold_summary` brand current/prior + volume | `sold-brand-<period>`, `sold-brand-vol` |
| W4 | `get_sold_summary` state-bucketed | `sold-geo-state` |
| W4 | `get_sold_summary` national baseline | `sold-geo-national` |
| W5 | `get_sold_summary` parity current/prior + volume | `sold-parity-<period>`, `sold-parity-vol` |

The token convention keeps `/tmp/marketcheck/<run_id>/` directory listings
human-debuggable.

## When the parser's ok=false

If `--file` recovery still fails (parser returns `ok=false` with
`error_type=truncation_unwrap_failed`, or the critical field is missing
after unwrap), surface a DQ event (a) and continue with the surviving
periods. Do NOT halt the workflow for one truncated call. The appraiser
receives a curve with one period gapped, which is a more defensible output
than nothing at all.

## Banned paths

- **Do not `cat` the saved file into your context.** Defeats the point of
  the envelope.
- **Do not retry the original MCP call** without tightening filters or
  reducing `top_n` — the same truncation will recur.
- **Do not assume the envelope's inner JSON is directly parseable** — it
  is stringified; must be unwrapped via `json.loads` on the `result` key's
  value.
- **Do not fail silently** — always log DQ event (b) when a truncation
  envelope was unwrapped via `--file`.
