# Envelope handling and truncation recovery

Two distinct concepts that get conflated. Handling them separately.

## The envelope is universal (almost)

Every `search_active_cars`, `search_past_90_days`, `decode_vin_neovin`, `predict_price_with_comparables`, and `get_car_history` response arrives wrapped as:

```json
{"result": "<stringified JSON of the real response>"}
```

This wrapping happens on **every** call — successful or truncated, 1KB or 150KB. It is the server's standard response shape, not a truncation signal.

**Exception:** `get_sold_summary` is the **only** tool that returns raw JSON without the envelope — the direct `{"success": true, "service": "sold_summary", "data": {...}}` shape. `_common._maybe_unwrap` detects the envelope by shape (`{"result": "<string>"}`) and passes unwrapped payloads through transparently, so no caller-side branching is needed.

## The truncation signal is separate

When the envelope's inner JSON exceeds the caller's token budget, the MCP tool emits a synthetic error string AND saves the full envelope to disk:

```
Error: result (124389 chars) exceeds maximum allowed tokens.
Output has been saved to /tmp/mcp-output/<uuid>.json
```

The saved file contains the same `{"result": "<stringified JSON>"}` envelope — just stored on disk instead of inlined. Log a Data Quality Notes event (type b — "truncation-envelope unwrap via file") when this path fires.

**Tools that chronically truncate in practice:**
- `decode_vin_neovin` — ~150KB envelopes on every real call
- `predict_price_with_comparables` — ~100KB envelopes on every real call (especially when W1 fires it 2–4 times)

Treat the `--file <path>` recovery as the **expected** path for these two tools, not an exception. `search_active_cars` / `search_past_90_days` / `get_car_history` truncate only when `rows` is set high; the default small-payload fetches arrive inline.

## Default recovery (every parser supports it)

Every parser in `scripts/` accepts a `--file <path>` flag. When passed, the parser:

1. Reads the file contents.
2. Attempts to unwrap the `{"result": "..."}` envelope and `json.loads` the inner string.
3. If unwrap succeeds, proceeds with the canonical field extraction as if the tool had returned the payload directly.
4. If unwrap fails (file corrupt, inner string not parseable), sets `ok=false` with `error_type="truncation_unwrap_failed"` so the caller can render a clean caveat.

So the default recovery is:

```
# MCP call returns the synthetic "saved to <path>" error
→ parser --file <path>
# Parser returns {ok: true, ...} in the vast majority of cases
```

Log a Data Quality Notes event (type b — "truncation-envelope unwrap") including which parser and which tool was truncated.

## Inline envelope-wrapped responses (NOT truncated to file)

`search_active_cars` and `search_past_90_days` routinely return inline — the MCP runtime doesn't save them to a file, they arrive in the agent's context as envelope-wrapped text (`{"result":"<stringified JSON>"}`). The parsers' stdin path (via `_common._maybe_unwrap`) handles envelope-wrapped stdin, so piping directly works in principle:

```
<mcp-response-text> | parse_search.py --subject-vin <VIN>
```

In practice, two things make that pipe unreachable from a Claude-Code agent:

1. An MCP response arrives as a tool message in the agent's conversation — there is no shell handle to pipe it into a subprocess's stdin.
2. Bash heredoc quote-escaping gets fragile above ~32KB, which real 20-listing asc responses routinely exceed.

**Prescribed recipe — primary path.** Write the raw response to disk with the Write tool, then invoke the parser with `--file`. **All paths are scoped to `<session.run_id>`** — read it from the profile's `session` block (auto-assigned by `scripts/load_profile.py`); never hardcode `appraisal-run` in agent flows.

```
# Step 1: agent saves the raw envelope to the run directory (Write tool)
Write(file_path="/tmp/marketcheck/<session.run_id>/asc.json",
      content="<full envelope-wrapped response verbatim>")

# Step 2: parse via --file
parse_search.py --file /tmp/marketcheck/<session.run_id>/asc.json --subject-vin <VIN>
```

The Write tool accepts large JSON content directly. The envelope unwrap happens transparently inside the parser's `--file` code path (see `_common._maybe_unwrap`). Do NOT trim, reshape, or hand-extract fields — pass the response verbatim.

**Alternative — `persist_response.py --content-file`.** If the raw response is already sitting on disk at some other path (e.g. a temp file from an earlier pass), route it through the run directory with `persist_response.py`:

```
persist_response.py --name asc --run-id "$RUN_ID" --content-file /tmp/some-other-path.json
# → echoes: /tmp/marketcheck/<session.run_id>/asc.json (byte-for-byte copy)
parse_search.py --file /tmp/marketcheck/<session.run_id>/asc.json --subject-vin <VIN>
```

`persist_response.py --content-file` copies verbatim — no trim, no reshape. **Always pass `--run-id <session.run_id>`** so the file lands in the same scratch directory as the rest of the flow's intermediate files. The backstop default subdirectory `appraisal-run` is preserved for callers that haven't yet wired up `session.run_id` but is **concurrent-unsafe** — two simultaneous flows fighting over `appraisal-run/asc.json` will silently swap responses.

**Banned path: hand-keying listings into a custom merge script.** Every form of this drops programmatic VIN dedup and `--subject-vin` shadow detection. The asc/desc responses must flow through `parse_search.py --file`, regardless of response size — use the Write-tool recipe above to get bytes onto disk.

## When the parser's ok=false

If `--file` recovery also fails (parser returns `ok=false` with `error_type=truncation_unwrap_failed`, or the critical field is missing after unwrap), render a caveat line for the affected block and continue with the rest of the workflow:

- Prediction call truncated → `"Franchise MarketCheck Price: unavailable (prediction call truncated; using comp median as anchor)"`
- Comp set call truncated → `"Active Retail Comparables: N rows rendered from partial response; full set unavailable"`
- Sold-90d call truncated → omit the sold-anchor and fall back to active-comp median; log a Data Quality Notes event

Do NOT halt the whole workflow. One truncated call should not kill four others' worth of usable data.

## Deep-truncation subagent template (manual use only)

In rare cases, a `search_active_cars` with a large `rows=` value returns a response so large that even the envelope file is unwieldy for the single model context. For those cases, the user can manually invoke a subagent to handle the file:

```
Agent({
  description: "Parse large truncated MCP response",
  subagent_type: "general-purpose",
  prompt: "Read /tmp/mcp-output/<uuid>.json (a MarketCheck MCP truncated response,
           envelope-wrapped as {\"result\": \"<stringified JSON>\"}).
           Run scripts/parse_search.py --file /tmp/mcp-output/<uuid>.json
           --exclude-vins <subject VIN + history VINs>.
           Report back: (a) the parsed listings count, (b) the first 15 listings
           formatted as TOON (include body_type/drivetrain/engine/transmission
           per listing when present for display-only use), (c) any filtered_out
           counts. Do not render the full raw response."
})
```

The subagent can absorb the large file in its isolated context and return only the parsed summary. This is manual — the main skill does not auto-dispatch subagents. Use only when the default `--file` path has returned an `ok=false` due to context pressure.

## What NOT to do

- **Do not `cat` the saved file into your context** — it defeats the point of the envelope.
- **Do not retry the original MCP call** without tightening filters — the same truncation will recur.
- **Do not assume the envelope's inner JSON is directly parseable** — it is stringified; it must be unwrapped via `json.loads` on the `result` key's value.
- **Do not fail silently** — always log a Data Quality Notes event when a truncation envelope was unwrapped.
