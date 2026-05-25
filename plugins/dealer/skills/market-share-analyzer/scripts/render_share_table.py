#!/usr/bin/env python3
"""
render_share_table.py — Render any of the 5 workflow tables from the
corresponding compute_*.py output. Closes the LLM-hand-rolling surface for
share / leaderboard / penetration / heatmap tables.

Modes:
  --mode brand-share              # input: compute_brand_share.py output
  --mode segment-conquest         # input: compute_segment_conquest.py output
  --mode dealer-group-leaderboard # input: compute_dealer_group_leaderboard.py output
  --mode ev-penetration           # input: compute_ev_penetration.py output (top EV models table)
  --mode ev-brand-share           # input: compute_ev_penetration.py output (per-brand EV share table)
  --mode regional-heatmap         # input: compute_regional_heatmap.py output

Usage:
  render_share_table.py --mode <mode> --data <compute_*.py output JSON path>
  [--currency '$|£']                # default '$'

Emits markdown table on stdout; the agent copies stdout verbatim into the
final report. When the input has `ok=false`, the script emits a single
caveat line `*(no data: <reason>)*` and exits 0. When the data block is
empty, emits `*(no data)*`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


MINUS = "−"
EM_DASH = "—"

VALID_MODES = (
    "brand-share",
    "segment-conquest",
    "dealer-group-leaderboard",
    "ev-penetration",
    "ev-brand-share",
    "regional-heatmap",
)


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _money(value: float | int | None, currency: str) -> str:
    if value is None:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{currency}{abs(int(round(value))):,}"
    return f"{currency}{int(round(value)):,}"


def _signed_bps(value: float | None) -> str:
    if value is None:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{abs(value):.0f} bps"
    return f"+{value:.0f} bps"


def _signed_pct(value: float | None) -> str:
    if value is None:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{abs(value):.1f}%"
    return f"+{value:.1f}%"


def _pct(value: float | None) -> str:
    if value is None:
        return EM_DASH
    return f"{value:.2f}%"


def _int(value: int | None) -> str:
    if value is None:
        return EM_DASH
    return f"{int(value):,}"


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _header_sep(n: int) -> str:
    return "|" + "|".join(["---"] * n) + "|"


def _load_data(path_str: str | None) -> dict[str, Any]:
    if not path_str:
        sys.stderr.write("render_share_table: --data is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"render_share_table: cannot read --data {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"render_share_table: --data {path_str!r} not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write("render_share_table: --data payload must be a JSON object\n")
        raise SystemExit(1)
    return payload


def _bold_if_user(text: str, is_user: bool) -> str:
    return f"**{text}**" if is_user else text


def render_brand_share(data: dict[str, Any], currency: str) -> list[str]:
    makes = data.get("makes") or []
    cols = ["Rank", "Make", "Current Sold", "Current Share %", "Prior Sold", "Prior Share %", "Share Change", "Volume Change", "Trend"]
    lines = [_row(cols), _header_sep(len(cols))]
    if not makes:
        lines.append("| *(no makes in current period)* |")
        return lines
    for m in makes:
        is_user = m.get("is_user_brand", False)
        cells = [
            str(m.get("rank", "")),
            _bold_if_user(str(m.get("make") or "—"), is_user),
            _int(m.get("current_sold_count")),
            _pct(m.get("current_share_pct")),
            _int(m.get("prior_sold_count")),
            _pct(m.get("prior_share_pct")),
            _signed_bps(m.get("share_change_bps")),
            _signed_pct(m.get("volume_change_pct")),
            m.get("trend") or "STABLE",
        ]
        lines.append(_row(cells))
    return lines


def render_segment_conquest(data: dict[str, Any], currency: str) -> list[str]:
    models = data.get("models") or []
    cols = ["Rank", "Make", "Model", "Sold Count", "Segment Share %", "Prior Share %", "Share Change"]
    lines = [_row(cols), _header_sep(len(cols))]
    if not models:
        lines.append("| *(no models in segment)* |")
        return lines
    for m in models:
        is_user = m.get("is_user_brand", False)
        cells = [
            str(m.get("rank", "")),
            _bold_if_user(str(m.get("make") or "—"), is_user),
            _bold_if_user(str(m.get("model") or "—"), is_user),
            _int(m.get("current_sold_count")),
            _pct(m.get("current_share_pct")),
            _pct(m.get("prior_share_pct")),
            _signed_bps(m.get("share_change_bps")),
        ]
        lines.append(_row(cells))
    return lines


def render_dealer_group_leaderboard(data: dict[str, Any], currency: str) -> list[str]:
    rows = data.get("leaderboard") or []
    cols = ["Rank", "Dealer Group", "Sold Count", "Market Share %", "Avg DOM", "Avg Sale Price", "Efficiency Score"]
    lines = [_row(cols), _header_sep(len(cols))]
    if not rows:
        lines.append("| *(no dealer groups)* |")
        return lines
    for r in rows:
        cells = [
            str(r.get("rank_by_volume", "")),
            str(r.get("dealership_group_name") or "—"),
            _int(r.get("sold_count")),
            _pct(r.get("market_share_pct")),
            (f"{r['avg_dom']:.1f}" if r.get("avg_dom") is not None else EM_DASH),
            _money(r.get("avg_sale_price"), currency),
            (f"{r['efficiency_score']:.1f}" if r.get("efficiency_score") is not None else EM_DASH),
        ]
        lines.append(_row(cells))
    return lines


def render_ev_penetration(data: dict[str, Any], currency: str) -> list[str]:
    """Renders the top-EV-models + top-Hybrid-models tables, plus a one-line
    penetration summary above each table."""
    cur = data.get("current_period") or {}
    pri = data.get("prior_period") or {}
    deltas = data.get("deltas") or {}
    out: list[str] = []
    out.append(
        f"EV Penetration: **{_pct(cur.get('ev_pct'))}** "
        f"(prior {_pct(pri.get('ev_pct'))}, {_signed_bps(deltas.get('ev_pct_change_bps'))})"
    )
    out.append(
        f"Hybrid Penetration: **{_pct(cur.get('hybrid_pct'))}** "
        f"(prior {_pct(pri.get('hybrid_pct'))}, {_signed_bps(deltas.get('hybrid_pct_change_bps'))})"
    )
    out.append(
        f"Combined Electrified: **{_pct(cur.get('combined_pct'))}** "
        f"(prior {_pct(pri.get('combined_pct'))}, {_signed_bps(deltas.get('combined_pct_change_bps'))})"
    )
    out.append("")
    out.append("**Top EV Models**")
    cols = ["Rank", "Make", "Model", "Sold Count", "Share of EV Pool %"]
    out.append(_row(cols))
    out.append(_header_sep(len(cols)))
    ev_models = data.get("top_ev_models") or []
    if not ev_models:
        out.append("| *(no EV models)* |")
    else:
        for m in ev_models:
            cells = [
                str(m.get("rank", "")),
                str(m.get("make") or "—"),
                str(m.get("model") or "—"),
                _int(m.get("sold_count")),
                _pct(m.get("share_of_pool_pct")),
            ]
            out.append(_row(cells))
    out.append("")
    out.append("**Top Hybrid Models**")
    out.append(_row(cols))
    out.append(_header_sep(len(cols)))
    hyb_models = data.get("top_hybrid_models") or []
    if not hyb_models:
        out.append("| *(no Hybrid models)* |")
    else:
        for m in hyb_models:
            cells = [
                str(m.get("rank", "")),
                str(m.get("make") or "—"),
                str(m.get("model") or "—"),
                _int(m.get("sold_count")),
                _pct(m.get("share_of_pool_pct")),
            ]
            out.append(_row(cells))
    return out


def render_ev_brand_share(data: dict[str, Any], currency: str) -> list[str]:
    rows = data.get("ev_brand_share") or []
    cols = ["Make", "EV Units", "Brand Total", "% of Brand Sales That Are EV"]
    lines = [_row(cols), _header_sep(len(cols))]
    if not rows:
        lines.append("| *(no EV brand data)* |")
        return lines
    for r in rows:
        cells = [
            str(r.get("make") or "—"),
            _int(r.get("ev_units")),
            _int(r.get("brand_total_units")),
            _pct(r.get("brand_ev_pct")),
        ]
        lines.append(_row(cells))
    return lines


def render_regional_heatmap(data: dict[str, Any], currency: str) -> list[str]:
    states = data.get("states") or []
    cols = ["Rank", "State", "Sold Count", "% of National", "Avg Sale Price", "Price vs National", "Avg DOM"]
    lines = [_row(cols), _header_sep(len(cols))]
    if not states:
        lines.append("| *(no state-level data)* |")
        return lines
    for s in states:
        ratio = s.get("price_vs_national_ratio")
        ratio_cell = f"{ratio:.2f}×" if ratio is not None else EM_DASH
        cells = [
            str(s.get("rank", "")),
            s.get("state") or "—",
            _int(s.get("sold_count")),
            _pct(s.get("pct_of_national_volume")),
            _money(s.get("avg_sale_price"), currency),
            ratio_cell,
            (f"{s['avg_dom']:.1f}" if s.get("avg_dom") is not None else EM_DASH),
        ]
        lines.append(_row(cells))
    return lines


_DISPATCH = {
    "brand-share": render_brand_share,
    "segment-conquest": render_segment_conquest,
    "dealer-group-leaderboard": render_dealer_group_leaderboard,
    "ev-penetration": render_ev_penetration,
    "ev-brand-share": render_ev_brand_share,
    "regional-heatmap": render_regional_heatmap,
}


def main(argv: list[str]) -> int:
    mode = _arg_value(argv, "--mode")
    data_path = _arg_value(argv, "--data")
    currency = _arg_value(argv, "--currency") or "$"

    if mode not in VALID_MODES:
        sys.stderr.write(f"render_share_table: invalid --mode {mode!r}; valid: {VALID_MODES}\n")
        return 1

    try:
        data = _load_data(data_path)
    except SystemExit:
        return 1

    if data.get("ok") is False:
        sys.stdout.write(f"*(no data: {data.get('error') or data.get('error_type') or 'unknown'})*\n")
        return 0

    renderer = _DISPATCH[mode]
    lines = renderer(data, currency)
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"render_share_table: unexpected error: {exc}\n")
        sys.exit(1)
