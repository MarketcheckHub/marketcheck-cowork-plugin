#!/usr/bin/env python3
"""
orchestrate.py — End-to-end post-MCP pipeline driver for W1.

Replaces the model-orchestrated per-call parse + merge + unwrap + assemble +
slice + compute + aggregate flow with a single in-process pipeline. The model
fires the MCP calls (still the model's job — MCP tool-use isn't accessible
from scripts), writes each response to a deterministic scratch file, builds
one manifest JSON, and invokes this script once.

Single CLI flag:
  python scripts/orchestrate.py --manifest /tmp/marketcheck/<sid>/manifest.json

Emits one structured JSON envelope on stdout matching every placeholder in
`assets/w1-output-template.md`. Exit 0 always (SP6 convention). No file writes.

Manifest schema:
  {
    "session_id":  "ep-f-2026-05-14",
    "scratch_dir": "/tmp/marketcheck/ep-f-2026-05-14",
    "pre_flight": {
      "windows":    <compute_quarter_windows output verbatim>,
      "resolution": <resolve_ticker output verbatim — ticker, entity_type,
                     classification, makes / canonical, company_name>
    },
    "wave_a1": {
      "sold": [
        {"make_or_group": "Ford", "channel": "new",  "split": "A",
         "file": "/tmp/.../sold_ford_new_A.json", "mcp_error": null},
        ...
      ],
      "ev":   [{...}, ...]
    },
    "wave_a2": {
      "active": [{"make_or_group": "Ford", "channel": "new",
                  "file": "/tmp/.../active_ford_new.json", "mcp_error": null},
                 ...]
    }
  }

`mcp_error` non-null → orchestrator logs DQ (a) and drops that call from the
merge. Per-call parser failures on non-current-quarter windows degrade
gracefully (DQ (a) + drop); failures that remove ALL current-quarter sold
data halt with `error_type: "no_current_quarter_data"` (forwarded from
`compute_earnings_signals`).

Output envelope (success):
  {
    "ok": true, "ticker": "F", "company_name": "Ford Motor Company",
    "canonical": null, "entity_type": "oem", "classification": "legacy",
    "makes": ["Ford","Lincoln"], "windows": {...},
    "headline": {...}, "leading_indicators_raw": {...},
    "per_make_raw": [...] | null,
    "active_inventory": {"used": ..., "new": ..., "footnote": "..."},
    "ev_block": {...}, "mix_block": {...} | null,
    "per_metric_bands": {...}, "composite_slots": {...}, "scores": {...},
    "verdict": "BULLISH"|"BEARISH"|"NEUTRAL"|"MIXED"|null,
    "mean_score": <float>|null, "n_bullish": <int>, "n_bearish": <int>,
    "rationale": "<string>", "reason": "no_scoreable_signals" /*null verdict*/,
    "signal_drivers": {"strongest": {...}|null, "weakest": {...}|null},
    "per_make_divergence": [...],
    "dq_events": [...]
  }

Halt envelope:
  {
    "ok": false,
    "error_type": "no_current_quarter_data" | "manifest_invalid" |
                  "missing_manifest" | "scratch_file_unreadable" |
                  "all_calls_failed" | "internal_error",
    "ticker": "F" /*when known*/,
    "windows": {...} /*when known*/,
    "dq_events": [...]
  }

DQ event ordering: orchestrator-emitted (a) per failed sold call → compute's
(i)(k)(m)(n)(r)(f)(d)(a) per code path → aggregate's (l) when per-make
divergence non-empty. Matches the legacy pipeline's emission order so output
remains bit-identical for any well-formed run.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

# Allow importing peer scripts from the same directory.
sys.path.insert(0, str(Path(__file__).parent))

from _common import _maybe_unwrap, classify_error, arg_value           # noqa: E402
from parse_sold_summary import (                                       # noqa: E402
    _normalize_row,
    _aggregate_make_by_window,
    _aggregate_group_by_window,
    _classify_sold_error,
)
from parse_search import _normalize_stats_block, _to_int as _ps_to_int  # noqa: E402
import compute_earnings_signals as _ces                                  # noqa: E402
import aggregate_signals as _agg                                         # noqa: E402


# ─── Manifest loading + validation ─────────────────────────────────────────


_REQUIRED_MANIFEST_KEYS = ("pre_flight", "wave_a1", "wave_a2")
_REQUIRED_PRE_FLIGHT_KEYS = ("windows", "resolution")
_REQUIRED_RESOLUTION_KEYS = ("ticker", "entity_type", "classification")


def _load_manifest(path: str | None) -> tuple[dict[str, Any] | None, str | None]:
    """Read and validate the manifest JSON. Returns (manifest, error_message)."""
    if not path:
        return None, "missing_manifest: --manifest flag absent"
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"missing_manifest: cannot read manifest at {path}: {exc}"
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"manifest_invalid: JSON parse failed: {exc}"
    if not isinstance(manifest, dict):
        return None, "manifest_invalid: top-level must be a JSON object"
    for key in _REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            return None, f"manifest_invalid: missing required key '{key}'"
    pre_flight = manifest.get("pre_flight") or {}
    for key in _REQUIRED_PRE_FLIGHT_KEYS:
        if key not in pre_flight:
            return None, f"manifest_invalid: missing required key 'pre_flight.{key}'"
    resolution = pre_flight.get("resolution") or {}
    for key in _REQUIRED_RESOLUTION_KEYS:
        if key not in resolution:
            return None, f"manifest_invalid: missing required key 'pre_flight.resolution.{key}'"
    return manifest, None


# ─── Scratch-file reading ──────────────────────────────────────────────────


def _read_scratch(path: str) -> tuple[Any, str | None]:
    """Read a scratch file. Returns (payload, error_message).

    Unwraps the {"result": "<stringified>"} truncation envelope automatically
    via `_common._maybe_unwrap`. `get_sold_summary` payloads (raw, not
    envelope-wrapped) pass through transparently.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot read scratch file {path}: {exc}"
    return _maybe_unwrap(raw), None


# ─── Per-call parsing ──────────────────────────────────────────────────────


def _normalize_rows_from_payload(payload: Any) -> list[dict[str, Any]] | str:
    """Extract + normalize rows from a `get_sold_summary` response payload.

    Returns the list of normalized rows on success, or an error-classification
    string on failure (one of: 'network', 'network_422', 'network_5xx',
    'unexpected_shape', 'truncation_unrecovered', 'validation',
    'make_model_not_found', 'unknown', 'empty_response').

    Mirrors the dispatch logic from `parse_sold_summary.main()` for the
    no-flag (raw) + post-aggregation entry path.
    """
    # Generic transport error check
    etype, _emsg = classify_error(payload)
    if etype:
        sold_type, _ = _classify_sold_error(payload)
        return sold_type or etype
    if isinstance(payload, str):
        sold_type, _ = _classify_sold_error(payload)
        return sold_type or "validation"

    data = payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]
    if not isinstance(data, dict):
        return "unexpected_shape"
    rows_raw = data.get("results") or data.get("rows") or data.get("data") or []
    if not isinstance(rows_raw, list):
        rows_raw = []
    return [_normalize_row(r) for r in rows_raw if isinstance(r, dict)]


def _parse_sold_call(
    entry: dict[str, Any], entity_type: str, target: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Parse one sold-call scratch file. Returns (inner_by_window_block, dq_event).

    `entry` is one element of `manifest.wave_a1.sold` or `wave_a1.ev`.
    Drives `_aggregate_make_by_window` (OEM) or `_aggregate_group_by_window`
    (dealer-group); extracts the inner `make_by_window` / `group_by_window`
    block (unwrap discipline). Returns None block + a DQ event string on
    parser failure or MCP error.
    """
    label = (
        f"{entry.get('make_or_group','?')}/{entry.get('channel','?')}"
        f"/{entry.get('split','?')}"
    )

    if entry.get("mcp_error"):
        return None, f"(a) MCP error on sold {label}: {entry.get('mcp_error')}"

    file_path = entry.get("file")
    if not file_path:
        return None, f"(a) Missing file path for sold {label} in manifest"

    payload, read_err = _read_scratch(file_path)
    if read_err is not None:
        return None, f"(a) Scratch read failure for sold {label}: {read_err}"

    rows_or_error = _normalize_rows_from_payload(payload)
    if isinstance(rows_or_error, str):
        return None, f"(a) Parser error for sold {label}: {rows_or_error}"

    rows = rows_or_error
    if entity_type == "oem":
        by_window, skipped_reason = _aggregate_make_by_window(rows, target)
        inner_key = "make_by_window"
    else:
        by_window, skipped_reason = _aggregate_group_by_window(rows, target)
        inner_key = "group_by_window"

    if by_window is None:
        # No rows matched, or all-zero — graceful drop, not an error.
        return None, f"(a) No usable rows for sold {label} ({skipped_reason}); dropped from merge"

    # by_window is the inner block already (the parser's _aggregate_*_by_window
    # returns the dict that would go under the `make_by_window` / `group_by_window`
    # key in the CLI emit). The "unwrap discipline" lives here.
    _ = inner_key  # for clarity / future use
    return by_window, None


def _parse_active_call(entry: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Parse one Wave A2 active-inventory scratch file.

    Returns a dict matching the shape that
    `compute_earnings_signals._build_active_inventory_channel` expects:
        {ok: True, num_found: int, stats_present: bool, stats: {...}|None}
    On failure: returns None + a DQ event string.
    """
    label = f"{entry.get('make_or_group','?')}/{entry.get('channel','?')}"
    if entry.get("mcp_error"):
        return None, f"(a) MCP error on active {label}: {entry.get('mcp_error')}"

    file_path = entry.get("file")
    if not file_path:
        return None, f"(a) Missing file path for active {label} in manifest"

    payload, read_err = _read_scratch(file_path)
    if read_err is not None:
        return None, f"(a) Scratch read failure for active {label}: {read_err}"

    # Transport-level error
    etype, _ = classify_error(payload)
    if etype:
        return None, f"(a) Active-inventory parser error for {label}: {etype}"
    if not isinstance(payload, dict):
        return None, f"(a) Unexpected payload shape for active {label}"
    data = payload.get("data")
    if not isinstance(data, dict):
        return None, f"(a) Missing data block for active {label}"

    num_found = _ps_to_int(data.get("num_found")) or 0
    stats_raw = data.get("stats") if isinstance(data.get("stats"), dict) else None
    if not stats_raw:
        return {
            "ok": True,
            "num_found": num_found,
            "stats_present": False,
            "stats": None,
        }, None
    stats = {
        "price": _normalize_stats_block(stats_raw.get("price")),
        "dom":   _normalize_stats_block(stats_raw.get("dom")),
    }
    return {
        "ok": True,
        "num_found": num_found,
        "stats_present": True,
        "stats": stats,
    }, None


# ─── A+B months-map merge ──────────────────────────────────────────────────


def _merge_months_maps(
    a_block: dict[str, Any] | None, b_block: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Merge two parser by-window blocks (Call A + Call B) into one.

    Each input has shape {make|group, row_count, months: {"YYYY-MM": agg}}.
    Months are disjoint by date-range design (A=year_ago_q 3mo; B=prior_q→mrcm
    ≤8mo). Dict union; defensive `_combine_monthly_aggs` if collision found.
    Returns None when both inputs are None.
    """
    if not a_block and not b_block:
        return None
    if not a_block:
        return b_block
    if not b_block:
        return a_block

    a_months = a_block.get("months") or {}
    b_months = b_block.get("months") or {}

    merged_months: dict[str, Any] = {}
    overlap_keys = set(a_months) & set(b_months)
    for k in a_months:
        merged_months[k] = a_months[k]
    for k, v in b_months.items():
        if k in overlap_keys:
            # Defensive: pool the two aggregates (should not happen by design).
            merged_months[k] = _ces._combine_monthly_aggs([a_months[k], v])
        else:
            merged_months[k] = v

    out = dict(a_block)
    out["months"] = merged_months
    out["row_count"] = (a_block.get("row_count") or 0) + (b_block.get("row_count") or 0)
    return out


# ─── Wave A1 assembly ──────────────────────────────────────────────────────


def _group_sold_calls(
    entries: list[dict[str, Any]], entity_type: str, target_for: callable,
    dq_events: list[str],
) -> dict[tuple[str, str], dict[str, dict | None]]:
    """Parse + group sold/ev entries by (make_or_group, channel) → {A, B} blocks.

    `target_for(entry) -> str` returns the canonical target name to filter
    rows against (the make name for OEM, the canonical group name for
    dealer-group). For dealer-groups, target_for must return the SAME canonical
    string for every entry (the resolution's `canonical` field).
    """
    grouped: dict[tuple[str, str], dict[str, dict | None]] = {}
    for entry in entries:
        target = target_for(entry)
        block, dq = _parse_sold_call(entry, entity_type, target)
        if dq:
            dq_events.append(dq)
        key = (entry.get("make_or_group"), entry.get("channel"))
        slot = entry.get("split", "A")
        grouped.setdefault(key, {"A": None, "B": None})[slot] = block
    return grouped


def _assemble_per_make(
    manifest: dict[str, Any], resolution: dict[str, Any], dq_events: list[str]
) -> dict[str, dict[str, Any]]:
    """Build the `per_make` dict for OEM tickers, matching
    `compute_earnings_signals` input contract.
    """
    makes = resolution.get("makes") or []
    sold_entries = manifest.get("wave_a1", {}).get("sold") or []
    ev_entries = manifest.get("wave_a1", {}).get("ev") or []
    active_entries = manifest.get("wave_a2", {}).get("active") or []

    # Group sold by (make, channel) → {A, B}; merge into single make_by_window block.
    sold_grouped = _group_sold_calls(
        sold_entries, "oem",
        target_for=lambda e: e.get("make_or_group"),
        dq_events=dq_events,
    )
    ev_grouped = _group_sold_calls(
        ev_entries, "oem",
        target_for=lambda e: e.get("make_or_group"),
        dq_events=dq_events,
    )

    # Parse active calls into a {(make, channel): block} map.
    active_map: dict[tuple[str, str], dict | None] = {}
    for entry in active_entries:
        block, dq = _parse_active_call(entry)
        if dq:
            dq_events.append(dq)
        active_map[(entry.get("make_or_group"), entry.get("channel"))] = block

    per_make: dict[str, dict[str, Any]] = {}
    for make in makes:
        sold_new = _merge_months_maps(
            sold_grouped.get((make, "new"), {}).get("A"),
            sold_grouped.get((make, "new"), {}).get("B"),
        )
        sold_used = _merge_months_maps(
            sold_grouped.get((make, "used"), {}).get("A"),
            sold_grouped.get((make, "used"), {}).get("B"),
        )
        ev_new = _merge_months_maps(
            ev_grouped.get((make, "new"), {}).get("A"),
            ev_grouped.get((make, "new"), {}).get("B"),
        )
        # EV may also be queried on "used" for some entities — try both.
        ev_used = _merge_months_maps(
            ev_grouped.get((make, "used"), {}).get("A"),
            ev_grouped.get((make, "used"), {}).get("B"),
        )
        ev_slice = ev_new or ev_used  # whichever channel was populated

        per_make[make] = {
            "sold_new_by_window":  sold_new,
            "sold_used_by_window": sold_used,
            "ev_slice_by_window":  ev_slice,
            "active_new":  active_map.get((make, "new")),
            "active_used": active_map.get((make, "used")),
        }
    return per_make


def _assemble_per_group(
    manifest: dict[str, Any], resolution: dict[str, Any], dq_events: list[str]
) -> dict[str, Any]:
    """Build the `per_group` dict for dealer-group tickers."""
    canonical = resolution.get("canonical")
    sold_entries = manifest.get("wave_a1", {}).get("sold") or []
    ev_entries = manifest.get("wave_a1", {}).get("ev") or []
    active_entries = manifest.get("wave_a2", {}).get("active") or []

    sold_grouped = _group_sold_calls(
        sold_entries, "dealer_group",
        target_for=lambda e: canonical,
        dq_events=dq_events,
    )
    ev_grouped = _group_sold_calls(
        ev_entries, "dealer_group",
        target_for=lambda e: canonical,
        dq_events=dq_events,
    )

    active_map: dict[str, dict | None] = {}
    for entry in active_entries:
        block, dq = _parse_active_call(entry)
        if dq:
            dq_events.append(dq)
        active_map[entry.get("channel")] = block

    # Dealer-group is single-entity; group key is (canonical, channel).
    # For sold/ev the canonical is constant, so use the channel from entry.
    def _merge_for_channel(group: dict, channel: str) -> dict | None:
        slots = group.get((canonical, channel)) or {}
        return _merge_months_maps(slots.get("A"), slots.get("B"))

    sold_new = _merge_for_channel(sold_grouped, "new")
    sold_used = _merge_for_channel(sold_grouped, "used")
    ev_new = _merge_for_channel(ev_grouped, "new")
    ev_used = _merge_for_channel(ev_grouped, "used")
    ev_slice = ev_new or ev_used

    return {
        "sold_new_by_window":  sold_new,
        "sold_used_by_window": sold_used,
        "ev_slice_by_window":  ev_slice,
        "active_new":  active_map.get("new"),
        "active_used": active_map.get("used"),
    }


# ─── Top-level pipeline ────────────────────────────────────────────────────


def _format_divergence_event(per_make_divergence: list[dict[str, Any]]) -> str:
    """Canonical format for the DQ (l) event when per-make divergence detected."""
    n = len(per_make_divergence)
    makes = ", ".join(d.get("make", "?") for d in per_make_divergence)
    return (
        f"(l) Cross-make divergence: {n} make(s) flagged ({makes}) — "
        "gap ≥ 2 score-points from ticker composite (see §4 Internal divergence)."
    )


def _run_pipeline(manifest: dict[str, Any]) -> dict[str, Any]:
    """Drive the full post-MCP pipeline. Returns the structured envelope."""
    pre_flight = manifest.get("pre_flight") or {}
    resolution = pre_flight.get("resolution") or {}
    windows = pre_flight.get("windows") or {}

    ticker = resolution.get("ticker")
    entity_type = resolution.get("entity_type")
    classification = resolution.get("classification")
    makes = resolution.get("makes") or []
    company_name = resolution.get("company_name")
    canonical = resolution.get("canonical")

    dq_events: list[str] = []

    # Build per_make or per_group from manifest.
    if entity_type == "oem":
        per_make = _assemble_per_make(manifest, resolution, dq_events)
        per_group = None
    elif entity_type == "dealer_group":
        per_make = None
        per_group = _assemble_per_group(manifest, resolution, dq_events)
    else:
        return {
            "ok": False,
            "error_type": "manifest_invalid",
            "detail": f"unknown entity_type: {entity_type!r}",
            "ticker": ticker,
            "windows": windows,
            "dq_events": dq_events,
        }

    # Check for total Wave A1 failure (no parseable sold data at all).
    has_any_sold = False
    if entity_type == "oem":
        for make_data in (per_make or {}).values():
            if make_data.get("sold_new_by_window") or make_data.get("sold_used_by_window"):
                has_any_sold = True
                break
    else:
        if (per_group or {}).get("sold_new_by_window") or (per_group or {}).get("sold_used_by_window"):
            has_any_sold = True

    if not has_any_sold:
        return {
            "ok": False,
            "error_type": "all_calls_failed",
            "ticker": ticker,
            "windows": windows,
            "dq_events": dq_events,
        }

    # Assemble compute_earnings_signals input.
    compute_input = {
        "ticker": ticker,
        "company_name": company_name,
        "canonical": canonical,
        "entity_type": entity_type,
        "classification": classification,
        "makes": makes,
        "windows": windows,
        "per_make": per_make,
        "per_group": per_group,
    }
    compute_out = _ces.compute(compute_input)

    # Halt branch — propagate compute's halt envelope.
    if not compute_out.get("ok"):
        # Merge orchestrator dq_events in front of compute dq_events.
        merged_dq = dq_events + (compute_out.get("dq_events") or [])
        halt = dict(compute_out)
        halt["dq_events"] = merged_dq
        halt["windows"] = halt.get("windows") or windows
        return halt

    # Slice + run aggregate_signals.
    agg_input = {
        "leading_indicators_raw": compute_out.get("leading_indicators_raw"),
        "per_make_raw":           compute_out.get("per_make_raw"),
        "ticker_classification":  classification,
    }
    agg_out = _agg.aggregate(agg_input)

    # Merge dq_events in canonical order: orchestrator → compute → (l) from
    # aggregate's per_make_divergence non-empty.
    final_dq = dq_events + (compute_out.get("dq_events") or [])
    per_make_divergence = agg_out.get("per_make_divergence") or []
    if per_make_divergence:
        final_dq.append(_format_divergence_event(per_make_divergence))

    # Assemble final envelope: pre-flight + compute fields + flattened aggregate.
    envelope: dict[str, Any] = {
        "ok": True,
        "ticker": ticker,
        "company_name": company_name,
        "canonical": canonical,
        "entity_type": entity_type,
        "classification": classification,
        "makes": makes,
        "windows": windows,
        "headline": compute_out.get("headline"),
        "leading_indicators_raw": compute_out.get("leading_indicators_raw"),
        "per_make_raw": compute_out.get("per_make_raw"),
        "active_inventory": compute_out.get("active_inventory"),
        "ev_block": compute_out.get("ev_block"),
        "mix_block": compute_out.get("mix_block"),
        # Flat aggregate fields:
        "per_metric_bands":    agg_out.get("per_metric_bands"),
        "composite_slots":     agg_out.get("composite_slots"),
        "scores":              agg_out.get("scores"),
        "verdict":             agg_out.get("verdict"),
        "mean_score":          agg_out.get("mean_score"),
        "n_bullish":           agg_out.get("n_bullish"),
        "n_bearish":           agg_out.get("n_bearish"),
        "rationale":           agg_out.get("rationale"),
        "signal_drivers":      agg_out.get("signal_drivers"),
        "per_make_divergence": per_make_divergence,
        "dq_events": final_dq,
    }
    if "reason" in agg_out:
        envelope["reason"] = agg_out["reason"]
    return envelope


# ─── CLI entry-point ───────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    """Read manifest, run pipeline, emit JSON to stdout. Always exit 0."""
    manifest_path = arg_value(argv, "--manifest")
    manifest, err = _load_manifest(manifest_path)
    if err is not None:
        error_type = err.split(":", 1)[0].strip()
        out = {
            "ok": False,
            "error_type": error_type,
            "detail": err,
        }
        json.dump(out, sys.stdout)
        sys.stdout.write("\n")
        return 0

    try:
        envelope = _run_pipeline(manifest)
    except Exception as exc:
        tb = traceback.format_exc(limit=10)
        out = {
            "ok": False,
            "error_type": "internal_error",
            "detail": f"{type(exc).__name__}: {exc}",
            "traceback": tb[-1500:],
        }
        json.dump(out, sys.stdout)
        sys.stdout.write("\n")
        return 0

    # Success or pipeline-level halt — both have envelope shape.
    if envelope.get("ok"):
        json.dump(envelope, sys.stdout, indent=2)
    else:
        json.dump(envelope, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
