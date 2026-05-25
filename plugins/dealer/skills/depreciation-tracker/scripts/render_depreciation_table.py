#!/usr/bin/env python3
"""
render_depreciation_table.py — Markdown table renderer for the
depreciation-tracker workflows. Closes the rendering-bypass surface by reading
each script's pre-computed JSON output and emitting the canonical markdown
table verbatim.

Five render modes:
  --mode curve     reads depreciation_curve.py output → W1 curve table
  --mode segment   reads segment_compare.py output    → W2 segment table
  --mode brand     reads brand_retention.py output    → W3 brand ranking table
  --mode geo       reads geo_variance.py output       → W4 geographic table
  --mode parity    reads msrp_parity.py output        → W5 MSRP parity table

Usage:
  render_depreciation_table.py --mode <m> --input <path> [--currency '$|£']
                               [--max-rows N]

Exit codes:
  0  OK (markdown emitted on stdout)
  1  Missing or malformed required inputs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


MINUS = "−"
EM_DASH = "—"


VALID_MODES = ("curve", "segment", "brand", "geo", "parity")


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _money(value: float | None, currency: str) -> str:
    if value is None:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{currency}{abs(int(round(value))):,}"
    return f"{currency}{int(round(value)):,}"


def _money_signed(value: float | None, currency: str) -> str:
    if value is None:
        return EM_DASH
    if value == 0:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{currency}{abs(int(round(value))):,}"
    return f"+{currency}{int(round(value)):,}"


def _pct(value: float | None, signed: bool = False, decimals: int = 1) -> str:
    if value is None:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{abs(value):.{decimals}f}%"
    if signed:
        return f"+{value:.{decimals}f}%"
    return f"{value:.{decimals}f}%"


def _int_cell(value: int | None) -> str:
    if value is None:
        return EM_DASH
    return f"{int(value):,}"


def _load_json(path_str: str | None, label: str) -> dict[str, Any]:
    if not path_str:
        sys.stderr.write(f"render_depreciation_table: --{label} is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"render_depreciation_table: cannot read {label} {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"render_depreciation_table: {label} {path_str!r} is not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"render_depreciation_table: {label} payload must be a JSON object\n")
        raise SystemExit(1)
    return payload


def _render_curve(payload: dict[str, Any], currency: str) -> str:
    anchor_used = payload.get("anchor_used") or "prior_period"
    headers = ["Period", "Avg Sale Price", "Sold Count"]
    if anchor_used == "msrp":
        headers.append("Retention % (vs MSRP)")
    headers += ["Retention % (vs Prior)", "Monthly Rate", "Annualized Rate"]

    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    rows = payload.get("periods") or []
    for r in rows:
        cells = [
            r.get("label") or EM_DASH,
            _money(_to_float(r.get("avg_price")), currency),
            _int_cell(_to_int(r.get("sold_count"))),
        ]
        if anchor_used == "msrp":
            cells.append(_pct(_to_float(r.get("retention_pct_msrp"))))
        cells.append(_pct(_to_float(r.get("retention_pct_prior"))))
        cells.append(_pct(_to_float(r.get("monthly_rate_pct")), signed=True, decimals=2))
        cells.append(_pct(_to_float(r.get("annualized_rate_pct")), signed=True, decimals=1))
        lines.append("| " + " | ".join(cells) + " |")

    if not rows:
        lines.append("| *(no priced periods)* |")

    extras = []
    verdict = payload.get("verdict")
    if verdict:
        extras.append(f"Verdict: **{verdict}**  (most-recent monthly rate: {_pct(_to_float(payload.get('recent_monthly_rate_pct')), signed=True, decimals=2)})")
    shape = payload.get("curve_shape")
    if shape:
        extras.append(f"Curve shape: **{shape}**  (longest-window monthly rate: {_pct(_to_float(payload.get('longest_monthly_rate_pct')), signed=True, decimals=2)})")
    if extras:
        lines.append("")
        lines.extend(extras)
    return "\n".join(lines)


def _render_segment(payload: dict[str, Any], currency: str) -> str:
    dim = payload.get("dimension") or "segment"
    headers = [dim.title(), "Current Avg", "Prior Avg",
               "Price Δ%", "Volume Δ%", "Current Sold", "Classification"]
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    rows = payload.get("rows") or []
    for r in rows:
        lines.append("| " + " | ".join([
            r.get("key") or EM_DASH,
            _money(_to_float(r.get("current_avg")), currency),
            _money(_to_float(r.get("prior_avg")), currency),
            _pct(_to_float(r.get("price_change_pct")), signed=True),
            _pct(_to_float(r.get("volume_change_pct")), signed=True),
            _int_cell(_to_int(r.get("current_sold_count"))),
            r.get("classification") or EM_DASH,
        ]) + " |")
    if not rows:
        lines.append("| *(no rows)* |")
    return "\n".join(lines)


def _render_brand(payload: dict[str, Any], currency: str) -> str:
    headers = ["Rank", "Make", "Current Avg", "Prior Avg", "Retention %",
               "Volume", "Tier"]
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    rows = payload.get("ranking") or []
    for r in rows:
        lines.append("| " + " | ".join([
            str(r.get("rank") or EM_DASH),
            r.get("make") or EM_DASH,
            _money(_to_float(r.get("current_avg")), currency),
            _money(_to_float(r.get("prior_avg")), currency),
            _pct(_to_float(r.get("retention_pct"))),
            _int_cell(_to_int(r.get("volume"))),
            r.get("tier") or EM_DASH,
        ]) + " |")
    if not rows:
        lines.append("| *(no rows)* |")
    counts = payload.get("tier_counts") or {}
    if counts:
        lines.append("")
        lines.append(
            "Tier counts: T1 " + str(counts.get("T1", 0))
            + " · T2 " + str(counts.get("T2", 0))
            + " · T3 " + str(counts.get("T3", 0))
            + " · T4 " + str(counts.get("T4", 0))
        )
    return "\n".join(lines)


def _render_geo(payload: dict[str, Any], currency: str) -> str:
    headers = ["State", "Avg Sale Price", "Price Index",
               "Premium/Discount $", "Sold Count", "Classification"]
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    rows = payload.get("rows") or []
    for r in rows:
        lines.append("| " + " | ".join([
            r.get("state") or EM_DASH,
            _money(_to_float(r.get("avg_price")), currency),
            _pct(_to_float(r.get("price_index")), signed=False, decimals=1),
            _money_signed(_to_float(r.get("premium_dollars")), currency),
            _int_cell(_to_int(r.get("sold_count"))),
            r.get("classification") or EM_DASH,
        ]) + " |")
    if not rows:
        lines.append("| *(no rows)* |")
    nat = _to_float(payload.get("national_avg"))
    if nat is not None:
        lines.append("")
        lines.append(f"National baseline: {_money(nat, currency)}")
    return "\n".join(lines)


def _render_parity(payload: dict[str, Any], currency: str) -> str:
    headers = ["Make/Model", "Current % vs MSRP", "Prior %", "Δ %",
               "Avg Price", "Volume", "Status", "Direction"]
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    rows = payload.get("rows") or []
    for r in rows:
        lines.append("| " + " | ".join([
            r.get("make_model") or EM_DASH,
            _pct(_to_float(r.get("current_pct")), signed=True),
            _pct(_to_float(r.get("prior_pct")), signed=True),
            _pct(_to_float(r.get("change_pct")), signed=True),
            _money(_to_float(r.get("current_avg_price")), currency),
            _int_cell(_to_int(r.get("volume"))),
            r.get("status") or EM_DASH,
            r.get("direction") or EM_DASH,
        ]) + " |")
    if not rows:
        lines.append("| *(no rows)* |")
    hi = payload.get("highlights") or {}
    extras = []
    if hi.get("flipped_below"):
        extras.append("Flipped below MSRP: " + ", ".join(hi["flipped_below"]))
    if hi.get("flipped_above"):
        extras.append("Flipped above MSRP: " + ", ".join(hi["flipped_above"]))
    if hi.get("deepening_discounts"):
        extras.append("Deepening discounts: " + ", ".join(hi["deepening_discounts"]))
    if extras:
        lines.append("")
        lines.extend(extras)
    return "\n".join(lines)


_RENDERERS = {
    "curve":   _render_curve,
    "segment": _render_segment,
    "brand":   _render_brand,
    "geo":     _render_geo,
    "parity":  _render_parity,
}


def main(argv: list[str]) -> int:
    mode = _arg_value(argv, "--mode")
    input_path = _arg_value(argv, "--input")
    currency = _arg_value(argv, "--currency") or "$"
    max_rows_raw = _arg_value(argv, "--max-rows")
    max_rows = _to_int(max_rows_raw)

    if mode not in VALID_MODES:
        sys.stderr.write(
            f"render_depreciation_table: invalid --mode {mode!r}; valid: {VALID_MODES}\n"
        )
        return 1

    payload = _load_json(input_path, "input")

    if max_rows is not None and max_rows >= 0:
        for arr_field in ("periods", "rows", "ranking"):
            if isinstance(payload.get(arr_field), list):
                payload[arr_field] = payload[arr_field][:max_rows]

    rendered = _RENDERERS[mode](payload, currency)
    sys.stdout.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors to caller
        sys.stderr.write(f"render_depreciation_table: unexpected error: {exc}\n")
        sys.exit(1)
