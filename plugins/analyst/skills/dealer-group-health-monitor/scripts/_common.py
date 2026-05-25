"""
_common.py — shared helpers for the parser scripts.

Every parser supports:
  - reading the MCP response from stdin (default)
  - or reading from a truncation-envelope file via --file <path>
  - emitting a canonical JSON result on stdout
  - a consistent {ok, error_type, error, ...} response shape
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TRUNCATION_ERROR_TYPE = "truncation_unwrap_failed"


def read_input(argv: list[str]) -> tuple[Any, str | None]:
    """Read and parse a tool response payload.

    Returns (payload, source):
      payload  — the parsed JSON (dict / list / str / None)
      source   — "stdin" or "file:<path>" for logging
    """
    if "--file" in argv:
        idx = argv.index("--file")
        if idx + 1 >= len(argv):
            return None, "file:<missing>"
        path = Path(argv[idx + 1])
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            return {"__read_error__": str(exc)}, f"file:{path}"
        return _maybe_unwrap(raw), f"file:{path}"
    else:
        try:
            raw = sys.stdin.read()
        except Exception as exc:
            return {"__read_error__": str(exc)}, "stdin"
        return _maybe_unwrap(raw), "stdin"


def _maybe_unwrap(raw: str) -> Any:
    """Parse raw; if it's a truncation envelope {result: "<stringified json>"},
    unwrap it. Otherwise return the parsed payload as-is.

    NOTE on asymmetry: `get_sold_summary` is the only MCP tool that returns
    raw JSON WITHOUT the `{"result": "..."}` envelope — its payload arrives
    as the direct `{"success": true, "service": "sold_summary", "data": {...}}`
    shape. This function passes unwrapped payloads through transparently, so
    `parse_sold_summary.py` needs no special-case. Every other MCP response
    from this skill's toolset (decode_vin_neovin, predict_price_with_comparables,
    search_active_cars, search_past_90_days, get_car_history, and the UK
    equivalents) arrives envelope-wrapped. See `references/sold-summary-safety.md`
    and `references/truncation-recovery.md` for the full explanation.
    """
    raw = raw.strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Raw is not JSON — return it as a string so the parser can report
        return raw
    # Envelope unwrap: {"result": "<stringified JSON>"}
    if isinstance(payload, dict) and set(payload.keys()) == {"result"} and isinstance(payload["result"], str):
        try:
            return json.loads(payload["result"])
        except json.JSONDecodeError:
            # Envelope present but inner is not parseable
            return {"__envelope_unwrap_failed__": True, "result_preview": payload["result"][:500]}
    return payload


def emit(result: dict[str, Any]) -> None:
    json.dump(result, sys.stdout, indent=2, sort_keys=False, default=str)
    sys.stdout.write("\n")


def arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def arg_value_multi(argv: list[str], flag: str) -> list[str]:
    """Collect all occurrences: --flag v1 --flag v2, or --flag 'v1,v2'."""
    out: list[str] = []
    for i, token in enumerate(argv):
        if token == flag and i + 1 < len(argv):
            val = argv[i + 1]
            # Split comma-separated
            for piece in val.split(","):
                piece = piece.strip()
                if piece:
                    out.append(piece)
    return out


def arg_flag(argv: list[str], flag: str) -> bool:
    return flag in argv


def classify_error(payload: Any) -> tuple[str, str]:
    """Given a top-level payload, classify failure.

    Returns (error_type, error_message). Returns ("", "") on success.
    """
    if payload is None:
        return "empty_response", "No response body"
    if isinstance(payload, str):
        # Raw string — usually an MCP synthetic error or an upstream non-JSON error
        if "exceeds maximum allowed tokens" in payload:
            return "truncation_unrecovered", payload[:500]
        return "non_json", payload[:500]
    if isinstance(payload, dict):
        if payload.get("__read_error__"):
            return "io_error", payload["__read_error__"]
        if payload.get("__envelope_unwrap_failed__"):
            return TRUNCATION_ERROR_TYPE, "Truncation envelope present but inner payload unparseable"
        if payload.get("success") is False:
            status = payload.get("status_code")
            if isinstance(status, int):
                if status == 422:
                    return "network_422", json.dumps(payload)[:500]
                if 500 <= status < 600:
                    return "network_5xx", json.dumps(payload)[:500]
            if payload.get("error_type") == "network":
                return "network", payload.get("error", "")[:500]
            return "upstream", json.dumps(payload)[:500]
    return "", ""
