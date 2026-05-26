#!/usr/bin/env python3
"""
persist_response.py — Persist an MCP response to disk for --file piping.

Many MCP calls return inline envelope-wrapped payloads that are too large to
safely heredoc through stdin to the parser scripts (bash quote-escaping gets
fragile above ~32KB). This helper reads the payload (stdin or a file),
writes it byte-for-byte to /tmp/marketcheck/<run-id>/<name>.json, and echoes
the path on stdout so the caller can feed it to the next parser via --file.

No trimming, no re-encoding, no envelope unwrap — the downstream parser's
--file path (via _common._maybe_unwrap) handles envelope shape. This script
exists solely to get the bytes onto disk without shell-escape friction.

Usage (PRIMARY — concurrent-safe; pass session.run_id from the loaded profile):
  # Stdin (bash-pipe callers):
  <mcp-response> | persist_response.py --name asc --run-id "$RUN_ID"
  # → echoes: /tmp/marketcheck/<RUN_ID>/asc.json

  # File-source (agent-friendly — the agent writes the raw response to a
  # temp file via the Write tool, then passes the path here):
  persist_response.py --name asc --run-id "$RUN_ID" --content-file /tmp/mcp-raw.json
  # → echoes: /tmp/marketcheck/<RUN_ID>/asc.json (contents copied verbatim)

  # Then:
  parse_search.py --file /tmp/marketcheck/<RUN_ID>/asc.json --subject-vin <VIN>

Without `--run-id`, the script falls back to the legacy default "cpr-run"
subdirectory — that path is **concurrent-UNSAFE** (two simultaneous flows
write to /tmp/marketcheck/cpr-run/asc.json and silently swap responses).
The skill flow always reads `session.run_id` from `load_profile.py` and
passes it explicitly; the legacy default exists only for backward compat.

Options:
  --name <label>            filename stem (required). The .json extension is added.
  --content-file <path>     read bytes from this file instead of stdin.
  --run-id <id>             subdirectory under /tmp/marketcheck/ (default: cpr-run; concurrent-unsafe)
"""

from __future__ import annotations

import sys
from pathlib import Path


# Backward-compat default; concurrent-UNSAFE. Always pass --run-id explicitly
# (use session.run_id from load_profile.py) when running from the skill flow.
DEFAULT_RUN_ID = "cpr-run"
BASE_DIR = Path("/tmp/marketcheck")


def _arg_value(argv: list[str], flag: str, default: str | None = None) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return default


def main(argv: list[str]) -> int:
    name = _arg_value(argv, "--name")
    if not name:
        sys.stderr.write("persist_response: --name is required\n")
        return 1

    # Guard against path traversal or directory tokens
    if "/" in name or ".." in name:
        sys.stderr.write(f"persist_response: invalid --name {name!r} (no slashes or .. allowed)\n")
        return 1

    run_id = _arg_value(argv, "--run-id", DEFAULT_RUN_ID) or DEFAULT_RUN_ID
    if "/" in run_id or ".." in run_id:
        sys.stderr.write(f"persist_response: invalid --run-id {run_id!r}\n")
        return 1

    run_dir = BASE_DIR / run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        sys.stderr.write(f"persist_response: cannot create {run_dir}: {exc}\n")
        return 1

    out_path = run_dir / f"{name}.json"

    content_file = _arg_value(argv, "--content-file")
    if content_file:
        src_path = Path(content_file)
        if not src_path.exists():
            sys.stderr.write(f"persist_response: --content-file not found: {content_file}\n")
            return 1
        try:
            raw = src_path.read_text(encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"persist_response: cannot read {content_file}: {exc}\n")
            return 1
    else:
        try:
            raw = sys.stdin.read()
        except Exception as exc:
            sys.stderr.write(f"persist_response: stdin read failed: {exc}\n")
            return 1

    try:
        out_path.write_text(raw, encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"persist_response: cannot write {out_path}: {exc}\n")
        return 1

    sys.stdout.write(str(out_path))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
