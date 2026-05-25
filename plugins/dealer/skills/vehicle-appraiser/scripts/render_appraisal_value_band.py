#!/usr/bin/env python3
"""
render_appraisal_value_band.py — Deterministic markdown renderer for the
appraisal value-band block. Closes the hand-rolling surface for the
"Recommended Value (condition-adjusted)" block in the same way
`render_comp_set_table.py` closed it for the comp table.

Reads the JSON output of `compute_appraisal_band.py` and emits a markdown
block on stdout with the low/mid/high tuple, confidence, anchor source,
condition (when applied), and methodology notes. Never recomputes — every
displayed value is read verbatim from the input.

Usage:
  render_appraisal_value_band.py \\
    --appraisal-band <path-to-compute_appraisal_band-output> \\
    [--currency '$|£']

Exit codes:
  0  OK (markdown emitted on stdout)
  1  Missing or malformed input
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


MINUS = "−"      # U+2212
EM_DASH = "—"   # U+2014


# Anchor-source rendered labels
ANCHOR_LABELS = {
    "sold_90d": "sold-90d trim median",
    "active_comps": "active-listing distribution",
    "predict_only": "MarketCheck Price ML prediction",
}


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _money(value: float | None, currency: str) -> str:
    if value is None:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{currency}{abs(int(round(value))):,}"
    return f"{currency}{int(round(value)):,}"


def _load_json(path_str: str | None, label: str) -> dict[str, Any]:
    if not path_str:
        sys.stderr.write(f"render_appraisal_value_band: --{label} is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(
            f"render_appraisal_value_band: cannot read {label} {path_str!r}: {exc}\n"
        )
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            f"render_appraisal_value_band: {label} {path_str!r} not JSON: {exc}\n"
        )
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"render_appraisal_value_band: {label} payload must be JSON object\n")
        raise SystemExit(1)
    return payload


def _render_band(payload: dict[str, Any], currency: str) -> list[str]:
    band = payload.get("band")
    confidence = payload.get("confidence") or "Unknown"
    anchor_source = payload.get("anchor_source")
    comp_count_total = payload.get("comp_count_total") or 0
    sold_count_used = payload.get("sold_count_used") or 0
    condition_applied = payload.get("condition_applied")
    purpose = payload.get("purpose")
    notes = payload.get("methodology_notes") if isinstance(payload.get("methodology_notes"), list) else []
    insufficient_reason = payload.get("insufficient_reason")

    lines: list[str] = ["## Recommended Value (condition-adjusted)"]
    lines.append("")

    if band is None:
        # Thin-market degraded block
        lines.append("**Insufficient evidence — value band unavailable.**")
        lines.append("")
        if insufficient_reason:
            lines.append(f"> {insufficient_reason}")
            lines.append("")
        lines.append(f"Confidence: {confidence} ({comp_count_total} total comps).")
        if notes:
            lines.append("")
            lines.append("Methodology:")
            for note in notes:
                lines.append(f"- {note}")
        return lines

    low = band.get("low")
    mid = band.get("mid")
    high = band.get("high")

    anchor_label = ANCHOR_LABELS.get(anchor_source, anchor_source or "unknown")

    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Low (p25 bracket) | {_money(low, currency)} |")
    lines.append(f"| Mid (anchor) | {_money(mid, currency)} |")
    lines.append(f"| High (p75 bracket) | {_money(high, currency)} |")
    lines.append("")

    summary = (
        f"**Anchor:** {anchor_label}"
        f"  ·  **Confidence:** {confidence} ({comp_count_total} total comps"
    )
    if anchor_source == "sold_90d":
        summary += f": {sold_count_used} sold-90d"
    summary += ")."
    lines.append(summary)

    if condition_applied:
        lines.append("")
        lines.append(f"Condition adjustment applied: **{condition_applied}**.")
    if purpose:
        lines.append("")
        lines.append(f"Appraisal purpose: **{purpose}**.")

    if notes:
        lines.append("")
        lines.append("Methodology:")
        for note in notes:
            lines.append(f"- {note}")

    return lines


def main(argv: list[str]) -> int:
    band_path = _arg_value(argv, "--appraisal-band")
    currency = _arg_value(argv, "--currency") or "$"

    payload = _load_json(band_path, "appraisal-band")
    lines = _render_band(payload, currency)
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"render_appraisal_value_band: unexpected error: {exc}\n")
        sys.exit(1)
