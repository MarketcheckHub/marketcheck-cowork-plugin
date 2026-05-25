---
name: _failure-recovery
description: Wave A1+A2 file-persistence pattern (Write→file per MCP call) + single orchestrator invocation; halt-vs-degrade rule (now implemented inside `orchestrate.py`). Load at preflight (BEFORE Wave A1 fires).
type: reference
---

# Failure recovery — canonical post-MCP pattern (REQUIRED preflight read)

The model's only post-MCP responsibility is: persist each MCP response to a deterministic scratch file, build a manifest, invoke `scripts/orchestrate.py` once. All parsing, merging, unwrapping, assembling, computing, and aggregating happen inside the orchestrator.

## The pattern — Write → file → manifest → orchestrate

For EVERY Wave A1 / Wave A2 MCP response:

```
Step 1. Receive the MCP response (either inline in the tool_result, or
        persisted-to-disk by the runtime when too large for the channel).

Step 2. Persist the response to a scratch file:
            PERSISTED → use the runtime's <path> directly in the manifest
                        entry's `file` field. No Write needed.
            INLINE    → Write(file_path = "/tmp/marketcheck/<sid>/<call-name>.json",
                              content   = <full MCP response string>)

Step 3. After ALL Wave A1 + Wave A2 calls return: build the manifest JSON
        listing pre-flight + each scratch file with metadata.
            Write(file_path = "/tmp/marketcheck/<sid>/manifest.json",
                  content   = <manifest-json-string>)

Step 4. Invoke the orchestrator:
            python scripts/orchestrate.py --manifest /tmp/marketcheck/<sid>/manifest.json

Step 5. Capture stdout — the structured envelope used for template rendering.
```

### `<session-id>` convention

Use the conversation/task id when known. Otherwise use `ep-<ticker>-<YYYY-MM-DD>` (e.g., `ep-f-2026-05-13` for a Ford run on 2026-05-13).

### `<call-name>` convention

Descriptive, deterministic naming so the model can pre-compute filenames before issuing each MCP call. The two-call date split adds an `_A` or `_B` suffix:

| Wave A1 / A2 call | `<call-name>` |
|---|---|
| Per-make sold (OEM), Call A (year-ago window) | `sold_<make_lower>_<channel>_A.json` (e.g., `sold_ford_new_A.json`) |
| Per-make sold (OEM), Call B (prior→mrcm) | `sold_<make_lower>_<channel>_B.json` |
| Per-make EV slice (legacy OEM), Call A | `ev_<make_lower>_<channel>_A.json` |
| Per-make EV slice (legacy OEM), Call B | `ev_<make_lower>_<channel>_B.json` |
| Single-group sold (dealer-group), Call A | `sold_<group_lower>_<channel>_A.json` (e.g., `sold_autonation_new_A.json`) |
| Single-group sold (dealer-group), Call B | `sold_<group_lower>_<channel>_B.json` |
| Single-group EV slice, Call A | `ev_<group_lower>_<channel>_A.json` |
| Single-group EV slice, Call B | `ev_<group_lower>_<channel>_B.json` |
| Per-make active inventory (single call, no split) | `active_<make_lower>_<channel>.json` |
| Single-group active inventory | `active_<group_lower>_<channel>.json` |
| Manifest | `manifest.json` (in the same scratch dir) |

Where `<group_lower>` is the canonical name lowercased and stripped of spaces / punctuation: `AutoNation Inc.` → `autonation`, `Group 1 Automotive Inc.` → `group1`, `Carmax` → `carmax`. Channels: `new`, `used`. Deterministic and short.

### Pre-create the scratch directory

Before firing Wave A1, create the directory once:

```bash
mkdir -p /tmp/marketcheck/<session-id>
```

Subsequent `Write` calls drop files into it; no need to `mkdir` again per call.

## Manifest schema

The manifest JSON the model writes after Wave A2 returns:

```json
{
  "session_id": "ep-f-2026-05-14",
  "scratch_dir": "/tmp/marketcheck/ep-f-2026-05-14",
  "pre_flight": {
    "windows":    <compute_quarter_windows output verbatim>,
    "resolution": <resolve_ticker output verbatim — ticker, entity_type,
                   classification, makes/canonical, company_name>
  },
  "wave_a1": {
    "sold": [
      {"make_or_group": "Ford", "channel": "new",  "split": "A",
       "file": "/tmp/marketcheck/<sid>/sold_ford_new_A.json", "mcp_error": null},
      {"make_or_group": "Ford", "channel": "new",  "split": "B",
       "file": "/tmp/marketcheck/<sid>/sold_ford_new_B.json", "mcp_error": null},
      ...
    ],
    "ev":   [{...}, ...]
  },
  "wave_a2": {
    "active": [
      {"make_or_group": "Ford", "channel": "new",
       "file": "/tmp/marketcheck/<sid>/active_ford_new.json", "mcp_error": null},
      ...
    ]
  }
}
```

`mcp_error` is non-null when the MCP call itself returned an error envelope (the call never produced a parseable response). The orchestrator logs DQ event (a) for that entry and drops it from the merge, deferring the halt-vs-degrade decision until after the full merge is complete.

## Why heredoc is forbidden for MCP responses

`Write` accepts arbitrary string content with no practical size limit. The shell heredoc pattern `Write(..., content=$(cat <<'EOF' ... EOF))` is unreliable above ~30 KB:

- Bash line-length limits truncate long single-line JSON.
- Embedded `EOF` markers (or quoting collisions) silently cut the content.
- The model can't tell from the tool result whether the heredoc fed the full input.

Always pass the response content as a string parameter to `Write` directly, never via a shell heredoc.

## MCP runtime persisted response — separate path

If the MCP tool returned `Error: result (N chars) exceeds maximum allowed tokens. Output saved to <path>`, the runtime already wrote the response to disk. **Use that path directly in the manifest entry's `file` field:**

```json
{"make_or_group": "Ford", "channel": "new", "split": "B",
 "file": "<path-from-runtime-error-message>", "mcp_error": null}
```

Do NOT `Write` it again under a different name — that's wasted work and the runtime's path works fine.

## What NEVER to do

- **NEVER invoke `parse_sold_summary.py` / `compute_earnings_signals.py` / `aggregate_signals.py` directly in W1.** The orchestrator owns them. Direct invocation defeats the determinism + context-savings discipline.
- **NEVER substitute `null` for a missing scratch file in the manifest.** The orchestrator surfaces `scratch_file_unreadable` errors cleanly; halt over substituting.
- **NEVER hand-roll Python aggregation.** The orchestrator is the source of truth for sold-count-weighted means and per-dimension rollups.
- **NEVER approximate or round numbers.** Every rendered cell traces to the orchestrator's stdout.
- **NEVER `Read` `scripts/*.py`.** The contract in `references/script-contracts.md` is authoritative.

## Halt vs degrade rule

The orchestrator implements this table internally; the model surfaces its output verbatim. Per-call failure does NOT halt the whole workflow by default. Distinguish three failure scopes, in order of severity:

### Halt conditions (current-quarter data lost for the headline)

The workflow CANNOT produce a headline verdict without current-quarter sold data for the target ticker. Halt cleanly with the listed message in these scenarios:

| Condition | Halt message |
|---|---|
| **All-makes current-quarter New-sold AND Used-sold fail** for an OEM ticker | *"No current-quarter sold data for any of `<ticker>`'s makes — cannot produce headline. Try again later or check MCP service status."* |
| **All-makes current-quarter sold fails** for an OEM ticker on the channel applicable to its classification (legacy: at least one of New / Used per make; pure_play: same) | Same |
| **Single-group current-quarter sold fails** for a dealer-group ticker (on its primary channel — Used for `Used-only`, New for `New-only`, OR both for `Both`) | *"No current-quarter sold data for `<canonical>` — cannot produce headline. Try again later or check MCP service status."* |
| **For `Both` dealer-group: BOTH New-side AND Used-side current-quarter sold fail** | Same |
| **For `Both` dealer-group: ONLY ONE side current-quarter sold fails** | Do NOT halt — render the available side with a degradation note. Mix dimension goes `null`; DQ event (r) logged. |
| Active-inventory call fails for the only channel an entity uses (Used-only KMX, or all makes for an OEM) | *"No active-inventory data available — Days Supply dimension cannot be computed; other dimensions render with a (d) data-quality note."* (Soft halt: workflow proceeds but Days Supply is omitted from the verdict.) |
| Profile load fails AND no ticker provided as input | Prompt user for the ticker; no halt. |
| Country gate fails (`country != "US"`) | *"This skill is US-only; the MCP sold-summary surface has no UK variant."* |
| Ticker unresolved (`error_type=no_candidates`) | *"`<X>` is not one of the 21 tracked tickers — add via `references/ticker-mapping.md` if you want to extend coverage."* |

The orchestrator forwards `compute_earnings_signals`'s `no_current_quarter_data` halt envelope verbatim; the model recognizes `ok: false` + `error_type` and renders the halt block from the template.

### Degrade conditions (signal goes null, workflow continues)

For everything else, the orchestrator drops the affected dimension or slot to `null` and continues. The reducer skips null slots in the mean-score calculation; the verdict is computed over the remaining non-null slots.

| Condition | Behaviour |
|---|---|
| **Some-makes current-quarter sold fails** (OEM with N≥2 makes, e.g. F=Ford+Lincoln, GM=4 makes, STLA=7 makes) | Drop the affected make(s) from the per-make rollup; ticker-level headline proceeds with remaining makes. Log DQ event (r) listing the dropped make(s). |
| **Prior-quarter sold fails** (current-quarter present) | QoQ deltas (Volume, ASP, MSRP-gap, DOM, EV-share, Mix) → null. `volume_momentum` composite degrades to YoY-only. Log DQ event (a). |
| **Year-ago sold fails OR all year-ago volumes are zero** (current present, prior present) | YoY deltas → null. `volume_momentum` composite degrades to QoQ-only. Common for newly-listed tickers (RIVN/LCID < 1 year old). Log DQ event (m). |
| **EV-slice call returns `make_model_not_found` for a specific make** (legacy OEM with diverse EV coverage) | Drop that make from the EV per-make breakdown; ticker-level EV-share rollup proceeds. Log DQ event (k) for that make. |
| **EV-slice call returns `sold_count=0` across ALL makes for a legacy OEM** | EV block omitted entirely from the output. Log DQ event (k). |
| **Wave A2 active call returns `stats_present: false`** | `num_found` rendered; Days Supply skipped for that channel; DQ event (d). |
| **Truncation envelope on any call** | Use saved `<path>` with `--file`. DQ event (b). |
| **Divide-by-zero in Days Supply** (sold_count_most_recent_month = 0) | `days_supply = null`; band null; slot skipped from reducer. DQ event (n). |
| **Single-make of a multi-make OEM has `sold_count_current < 100/month`** (per `multi-make-aggregation.md` low-volume threshold) | Compute proceeds; per-make breakdown shows that make with a "(i) low-volume" footnote. DQ event (i). |

### Why this asymmetry

Equity analysts using this skill have money on the line. A headline verdict computed from missing current-quarter data would whipsaw. Halt is the right move when the foundation is gone. But once current-quarter is in hand, every additional signal that fails just degrades the richness of the verdict — it does not invalidate it. A 4-slot verdict (no YoY, no EV) is still actionable; a 0-slot verdict is not.

## When the model is stuck — decision tree

```
For each MCP response in Wave A1/A2:
  Q: Was the response delivered inline (in tool_result content) OR persisted by
     the runtime ("Error: result exceeds maximum allowed tokens.
     Output saved to <path>")?
     ↓
     PERSISTED → use runtime's <path> directly in the manifest entry's "file" field.
                 No Write needed. Done.
     INLINE    → Write(/tmp/marketcheck/<sid>/<call-name>.json, <response-content>).
                 Use that path in the manifest entry's "file" field.

After Wave A1 + A2 returns:
  Write(/tmp/marketcheck/<sid>/manifest.json, <manifest-JSON>)
  python scripts/orchestrate.py --manifest /tmp/marketcheck/<sid>/manifest.json
  Capture stdout — this is the single structured envelope.

If the orchestrator's stdout has ok: false:
  error_type == "no_current_quarter_data" → render the halt block from template
                                              §Halt rendering.
  error_type ∈ {"manifest_invalid", "all_calls_failed",
                "scratch_file_unreadable", "missing_manifest",
                "internal_error"}             → surface a one-line error to the user;
                                                 no template render. Investigate
                                                 root cause.
```

There is no scenario where setting a parser-required field to `null` is the right call. If the documented pattern doesn't work for some reason, **halt and surface as a doc bug**.

## Implementation note for the model

When you receive an MCP tool result containing the response inline, the response is in your conversation context. The `Write` tool takes a string argument — you write that string verbatim to the file. No transformation. No "compute summary inline." Just verbatim Write, then list it in the manifest.

For a typical W1 with F (legacy OEM, 2 makes = Ford + Lincoln):

- Wave A1: 12 MCP calls (2 makes × 3 channels × 2 splits) → 12 Writes (or fewer if some responses are runtime-persisted) → 1 orchestrator invocation.
- Wave A2: 4 MCP calls (2 makes × 2 channels) → 4 Writes (responses are small, ~1KB).
- Total: ~16 scratch files + 1 manifest in `/tmp/marketcheck/<session-id>/`.

For STLA (legacy OEM, 7 makes):

- Wave A1: 42 calls (7 makes × 3 channels × 2 splits) → 42 Writes → 1 orchestrator invocation.
- Wave A2: 14 calls (7 makes × 2 channels) → 14 Writes.
- Total: ~56 scratch files + 1 manifest.

This Write overhead is ~50-100 ms per file; for STLA that's ~3-6 seconds. Trade-off accepted: correctness over speed. The orchestrator invocation itself takes ~1-2 seconds (pure Python, no I/O beyond reading the scratch files).
