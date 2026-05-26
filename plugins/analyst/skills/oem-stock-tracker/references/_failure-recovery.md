---
name: _failure-recovery
description: Canonical Wave A1+A2 parser-invocation pattern, plus recovery flows for MCP error envelopes. Load at preflight (BEFORE Wave A1 fires) — this is the only way to invoke `parse_sold_summary.py` without silent heredoc truncation.
type: reference
---

# Parser invocation — canonical pattern (REQUIRED preflight read)

This is the **single canonical pattern** for invoking `parse_sold_summary.py` in Wave A1 and Wave A2. There is NO fallback to heredoc piping — heredoc silently truncates JSON > ~30 KB and the parser sees fewer rows than the response actually contains. Past sessions that used heredoc all produced wrong-data outputs (Lexus seg-mix dropped or fabricated).

## The pattern — Write → file → `parser --file`

For EVERY MCP response that needs parsing through `parse_sold_summary.py`:

```
Step 1. Receive the MCP response (either inline in the tool_result, or persisted-to-disk
        by the runtime when too large for the channel).

Step 2. Write the response to a scratch file:
            Write(file_path = "/tmp/marketcheck/<session-id>/<call-name>.json",
                  content   = <full MCP response string>)

Step 3. Invoke the parser with --file:
            python scripts/parse_sold_summary.py --<flag> <arg> \
              --file /tmp/marketcheck/<session-id>/<call-name>.json
```

### `<session-id>` convention

Use the conversation/task id when known. Otherwise use `oem-<ticker>-<YYYY-MM-DD>` (e.g., `oem-tm-2026-05-13` for a Toyota run on 2026-05-13).

### `<call-name>` convention

Descriptive name for the call. Deterministic so the model can pre-compute it before issuing the MCP call:

| Wave A1 / A2 call | `<call-name>` |
|---|---|
| Per-make sold (multi-month), one per make in `makes[]` | `sold_<make_lower>` (e.g., `sold_toyota`, `sold_lexus`) |
| Market leaderboard, current month | `market_current` |
| Market leaderboard, 3-month baseline (M=3) | `market_baseline_3mo` |
| Per-make EV slice (multi-month), one per make | `ev_<make_lower>` (e.g., `ev_toyota`, `ev_lexus`) |
| Pure-play EV market leaders (W1 only) | `ev_leaders` |
| Per-make segment mix (body_type), one per make | `seg_<make_lower>` (e.g., `seg_toyota`, `seg_lexus`) |
| Per-make active inventory — small response, see exception below | `active_<make_lower>` (rarely persisted) |
| Brand-orphan facet-discovery call | `make_facets` |

### Pre-create the scratch directory

Before firing Wave A1, create the directory once:

```bash
mkdir -p /tmp/marketcheck/<session-id>
```

Subsequent `Write` calls drop files into it; no need to mkdir again per call.

## Why heredoc is forbidden for `parse_sold_summary.py`

`parse_sold_summary` inputs range from ~1 KB (small EV slice) to ~1.5 MB (M=3 leaderboard). The shell heredoc pattern `cat <<'EOF' | parser ... EOF` is unreliable:

- Bash line-length limits truncate long single-line JSON.
- Embedded `EOF` markers (or quoting collisions) silently cut the content.
- The model can't tell from the tool result whether the heredoc fed the full input.

Confirmed regression (session `efbb7f24`, 2026-05-13): a 46,814-char Lexus seg-mix response was heredoc'd → only 4 of ~150 rows reached the parser. Lexus segment-mix was lost; rendered SUV share showed 39.65% (Toyota-only) instead of the true 45%.

The `Write` tool accepts arbitrary string content with no size limit. `Write → file → --file` is deterministic for every response size.

## Stdin pipe is acceptable for these scripts (small inputs only)

The Write→file pattern is mandated for `parse_sold_summary.py`. Other scripts accept stdin pipes for small inputs:

- `parse_search.py` — stats responses are ~1 KB; `cat <<'EOF' | parse_search.py` works fine. Facet responses are ~5-20 KB and also safe.
- `compute_oem_stats.py`, `aggregate_signals.py`, `compute_w3_rollup.py` — assembled JSON inputs are typically ≤ ~30 KB; stdin pipe works. If the assembled input ever exceeds ~30 KB (large multi-make case), use Write→file.
- `compute_month_windows.py`, `resolve_oem.py` — CLI args only, no stdin.

## MCP runtime persisted response — separate path

If the MCP tool returned `Error: result (N chars) exceeds maximum allowed tokens. Output saved to <path>`, the runtime already wrote the response to disk. **Use that path directly with `--file`:**

```bash
python scripts/parse_sold_summary.py --<flag> <arg> \
  --file <path-from-runtime-error-message>
```

Do NOT `Write` it again under a different name — that's wasted work and the runtime's path is fine.

## What NEVER to do

- **NEVER heredoc `parse_sold_summary.py` inputs.** Use Write→file.
- **NEVER set a parser-required input field to `null` and continue.** If `parse_sold_summary` for `seg_lexus` fails or you can't get its output, halt and surface the issue. `compute_oem_stats` validates inputs and refuses incomplete data via DQ events `(p)`–`(t)`, so this pattern is caught at the next boundary anyway — better to halt earlier.
- **NEVER hand-roll Python aggregation.** The parser is the source of truth for sold-count-weighted means and per-dimension rollups.
- **NEVER approximate or round numbers.** Every rendered cell traces to a parser/script output.
- **NEVER `Read` `scripts/*.py`.** The contract in `references/script-contracts.md` is authoritative.

## When the model is stuck — decision tree

```
Q: Did the MCP tool return inline (in tool_result content) OR persisted (Error: saved to <path>)?
   ↓
   PERSISTED → use the runtime path with --file. Done.
   INLINE    ↓
              Q: Is this a parse_sold_summary call?
                 ↓
                 YES → Write the inline response to /tmp/marketcheck/<session-id>/<call-name>.json,
                       then parse with --file. Always. Even if the response is small.
                 NO  → It's parse_search (stats or facets) or another small-input script.
                       Stdin pipe is fine if response is < ~30 KB.
                       If > 30 KB, use Write→file anyway (no downside).
```

There is no scenario where setting a parser-required field to `null` is the right call. If the documented pattern doesn't work for some reason, **halt and surface as a doc bug**.

## Implementation note for the model

When you receive an MCP tool result containing the response inline, the response is in your conversation context. The `Write` tool takes a string argument — you write that string verbatim to the file. No transformation. No "compute summary inline." Just verbatim Write, then parser --file.

For a typical W1 with 2 makes (e.g., Toyota + Lexus, legacy classification):

- Wave A1: 6 MCP calls → 6 `Write` calls → 6 parser invocations.
- Wave A2: 4 MCP calls → 2 `Write` (for seg) + 2 stdin-pipe (for active) → 4 parser invocations.
- Total: ~8 scratch files in `/tmp/marketcheck/<session-id>/`.

This adds ~8 tool calls to the wall clock vs. heredoc piping, but each is < 100ms and the gain is zero heredoc-truncation failures across the entire workflow.
