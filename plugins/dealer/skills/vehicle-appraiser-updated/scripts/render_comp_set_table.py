#!/usr/bin/env python3
"""
render_comp_set_table.py — Deterministically render the spec subtitle + the
Competitive Set table from the parser/comp_stats outputs. Closes the
rendering-bypass surface that v4/v5/v6 closed on the ingestion side via
merge_comps.py.

Two render modes (v1.8.0+):
  --mode 8col-comp   (DEFAULT — W1, W4 schema)
    | Dealer | Type | Price | Miles | DOM | Distance | vs Mkt Median | Price Change |
    Reads `--comp-stats` for quartile.median (vs Mkt Median col).
    Honors `--user-price` for the ← You marker.

  --mode 9col-drops  (NEW — W5 Drop table)
    | Dealer | Type | Old Price | New Price | Drop $ | Drop % | Miles | DOM | Distance |
    Computes Old Price = price - price_change_amount (pre-computed by parse_search).
    Drop $ = -price_change_amount (positive magnitude for drops).
    Drop % = -price_change_percent (positive magnitude for drops).
    Rows with price_change_percent == 0 render Old/Drop cols as — and sort last.
    No ← You marker (W5 has no subject vehicle).
    No vs Mkt Median (W5 has no comp_stats.quartile).

The renderer reads PRE-COMPUTED parser fields per `assets/output-template.md`
"Parser field map":
  - dealer_name, dealer_type, is_certified
  - price, miles, dom_active, distance_mi
  - price_change_amount  (PRE-COMPUTED — NEVER re-implement parse_search.py:88-104)
  - price_change_percent
  - body_type, drivetrain, engine, transmission

Field-source rules (L1, L2 of the v1.8.0 W5 plan):
  - DOM column reads listings[*].dom_active directly (NEVER `dom`/`dom_180`/`dom_lifetime`).
  - Distance column reads listings[*].distance_mi (pre-flattened by parse_search.py:152).

Usage:
  render_comp_set_table.py \\
    --merged <merge_comps output path> \\
    --comp-stats <comp_stats output path | empty for 9col-drops mode> \\
    --user-price <asking_price | empty for null> \\
    [--mode '8col-comp|9col-drops']  (default: 8col-comp)
    [--currency '$|£']  \\
    [--max-rows N]

Emits the spec subtitle (when applicable) + markdown table on stdout.

Exit codes:
  0  OK (markdown emitted on stdout)
  1  Missing or malformed required inputs (clear error on stderr)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# ─── Constants ────────────────────────────────────────────────────────────

# Unicode minus sign (U+2212) — visually distinct from ASCII hyphen-minus.
# Used in money / percent / vs-Mkt-Median rendering for negatives.
MINUS = "−"

# Em-dash for null/missing cells (U+2014).
EM_DASH = "—"

# Ellipsis for truncated dealer names (U+2026).
ELLIPSIS = "…"

# Down-and-right arrow for per-row spec subtitle indent (U+21B3).
SPEC_ARROW = "↳"

# Left arrow for the ← You marker (U+2190).
LEFT_ARROW = "←"

# Truncation: dealer name is truncated to 30 chars total when len > 30.
# Algorithm: name[:29] + ELLIPSIS = 30 chars. CPO suffix appended AFTER.
DEALER_MAX_CHARS = 30

# Render modes (v1.8.0+). DEFAULT preserves the W1/W4 8-col legacy schema.
MODE_8COL_COMP = "8col-comp"
MODE_9COL_DROPS = "9col-drops"
VALID_MODES = (MODE_8COL_COMP, MODE_9COL_DROPS)

# 8-col table header (W1/W4 schema; default).
COLUMNS_8COL = ["Dealer", "Type", "Price", "Miles", "DOM", "Distance", "vs Mkt Median", "Price Change"]

# 9-col table header (W5 Drop table schema).
COLUMNS_9COL_DROPS = ["Dealer", "Type", "Old Price", "New Price", "Drop $", "Drop %", "Miles", "DOM", "Distance"]

# Legacy alias — preserved for any consumer importing COLUMNS directly.
COLUMNS = COLUMNS_8COL


# ─── Argparse-lite helpers (match other scripts' style) ───────────────────

def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _to_float(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).replace(",", "").replace("$", "").replace("£", ""))
    except (TypeError, ValueError):
        return None


def _to_int(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _load_json(path_str: str | None, label: str) -> dict[str, Any]:
    if not path_str:
        sys.stderr.write(f"render_comp_set_table: --{label} is required\n")
        raise SystemExit(1)
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"render_comp_set_table: cannot read {label} file {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"render_comp_set_table: {label} file {path_str!r} is not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"render_comp_set_table: {label} payload must be a JSON object\n")
        raise SystemExit(1)
    return payload


# ─── Cell formatters ──────────────────────────────────────────────────────

def _money(value: float | None, currency: str, signed: bool = False) -> str:
    """Format a dollar amount with comma thousands and U+2212 minus on
    negatives. Returns EM_DASH for None / 0 (when signed). For unsigned
    positives, no leading '+'."""
    if value is None:
        return EM_DASH
    if signed and value == 0:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{currency}{abs(int(round(value))):,}"
    if signed:
        return f"+{currency}{int(round(value)):,}"
    return f"{currency}{int(round(value)):,}"


def _percent(value: float | None, signed: bool = True) -> str:
    """Format a percent with U+2212 minus on negatives. 1 decimal."""
    if value is None:
        return EM_DASH
    if value < 0:
        return f"{MINUS}{abs(value):.1f}%"
    if signed:
        return f"+{value:.1f}%"
    return f"{value:.1f}%"


def _truncate_dealer_name(name: str | None, is_certified: Any) -> str:
    """Truncate to 30 chars then append CPO suffix if certified.
    Algorithm: when len(name) > DEALER_MAX_CHARS, replace with name[:29] + …
    (29 + 1 = 30 total). Then append ' (CPO)' iff is_certified is True
    (False / None render no marker per tri-state)."""
    if name is None:
        rendered = EM_DASH
    else:
        rendered = str(name)
        if len(rendered) > DEALER_MAX_CHARS:
            rendered = rendered[:DEALER_MAX_CHARS - 1] + ELLIPSIS
    if is_certified is True:
        rendered = f"{rendered} (CPO)"
    return rendered


def _type_cell(dealer_type: str | None) -> str:
    if dealer_type == "franchise":
        return "F"
    if dealer_type == "independent":
        return "I"
    return EM_DASH


def _miles_cell(miles: float | None) -> str:
    if miles is None:
        return EM_DASH
    return f"{int(round(miles)):,}"


def _dom_cell(dom_active: int | None) -> str:
    if dom_active is None:
        return EM_DASH
    return str(int(dom_active))


def _distance_cell(distance_mi: float | None) -> str:
    if distance_mi is None:
        return EM_DASH
    return f"{distance_mi:.2f} mi"


def _vs_mkt_median_cell(price: float | None, median: float | None, currency: str) -> str:
    """Per-row signed diff against quartile.median. Render — when median is null."""
    if price is None or median is None:
        return EM_DASH
    diff = price - median
    if diff == 0:
        return EM_DASH
    return _money(diff, currency, signed=True)


def _price_change_cell(amount: float | None, percent: float | None, currency: str) -> str:
    """Read price_change_amount (PRE-COMPUTED by parser per parse_search.py:96-104).
    Never re-implement. Render '—' when amount is None / 0."""
    if amount is None or amount == 0:
        return EM_DASH
    money = _money(amount, currency, signed=True)
    pct = _percent(percent, signed=True) if percent is not None else EM_DASH
    return f"{money} ({pct})"


# ─── 9-col W5 Drop-table cell formatters ──────────────────────────────────

def _old_price_cell(price: float | None, amount: float | None, currency: str) -> str:
    """Old Price = price - price_change_amount.
    `amount` is signed (negative for drops, positive for raises).
    For a drop: price=27500, amount=-500 → Old Price=$28,000.
    Render — when price or amount is None, OR when amount==0 (no change history)."""
    if price is None or amount is None or amount == 0:
        return EM_DASH
    old = price - amount
    return _money(old, currency)


def _drop_money_cell(amount: float | None, currency: str) -> str:
    """Drop $ = -price_change_amount.
    For a drop where amount=-500: Drop $ = +500 → renders as '$500' (positive magnitude).
    For a raise where amount=+200: Drop $ = -200 → renders as '−$200' (negative; raise in a drop column).
    Render — when amount is None or 0."""
    if amount is None or amount == 0:
        return EM_DASH
    drop = -amount
    if drop < 0:
        return f"{MINUS}{currency}{abs(int(round(drop))):,}"
    return f"{currency}{int(round(drop)):,}"


def _drop_percent_cell(percent: float | None) -> str:
    """Drop % = -price_change_percent.
    For a drop where pct=-15.0: Drop % = +15.0 → renders as '15.0%'.
    For a raise where pct=+5.0: Drop % = -5.0 → renders as '−5.0%'.
    Render — when percent is None or 0."""
    if percent is None or percent == 0:
        return EM_DASH
    drop = -percent
    if drop < 0:
        return f"{MINUS}{abs(drop):.1f}%"
    return f"{drop:.1f}%"


# ─── Spec-subtitle rendering ──────────────────────────────────────────────

SPEC_FIELDS = ["body_type", "drivetrain", "engine", "transmission"]


def _spec_field_distinct_non_null(rows: list[dict], field: str) -> list[str]:
    """Return distinct non-null values for a spec field across rendered rows."""
    seen: list[str] = []
    for r in rows:
        v = r.get(field)
        if v is None or v == "":
            continue
        sv = str(v)
        if sv not in seen:
            seen.append(sv)
    return seen


def _detect_heterogeneity(rows: list[dict]) -> tuple[bool, dict[str, list[str]]]:
    """Return (any_field_heterogeneous, per_field_distinct_values).
    A field is heterogeneous if it has >1 distinct non-null value."""
    per_field: dict[str, list[str]] = {}
    any_het = False
    for f in SPEC_FIELDS:
        per_field[f] = _spec_field_distinct_non_null(rows, f)
        if len(per_field[f]) > 1:
            any_het = True
    return any_het, per_field


def _spec_subtitle_homogeneous(per_field: dict[str, list[str]]) -> str | None:
    """Build the modal-spec line. Omit fields that are null on every row.
    Return None when all 4 fields are null on every row."""
    parts: list[str] = []
    for f in SPEC_FIELDS:
        vals = per_field[f]
        if vals:  # at least one non-null value exists
            parts.append(vals[0])
    if not parts:
        return None
    return f"Spec (all comps): {' · '.join(parts)}"


def _spec_subtitle_per_row(row: dict[str, Any]) -> str | None:
    """Per-row subtitle. Omit null fields silently. Return None when all 4
    fields on this row are null."""
    parts: list[str] = []
    for f in SPEC_FIELDS:
        v = row.get(f)
        if v is None or v == "":
            continue
        parts.append(str(v))
    if not parts:
        return None
    return f"  {SPEC_ARROW} {' · '.join(parts)}"


# ─── Main render ──────────────────────────────────────────────────────────

def _render_table(
    rows: list[dict[str, Any]],
    median: float | None,
    user_price: float | None,
    currency: str,
    closest_idx: int | None,
    heterogeneous: bool,
    mode: str = MODE_8COL_COMP,
) -> list[str]:
    """Build the markdown table lines (header + alignment row + body).

    `mode` selects the column schema:
      MODE_8COL_COMP  → 8-col W1/W4 schema (vs Mkt Median + Price Change cols)
      MODE_9COL_DROPS → 9-col W5 schema (Old/New Price + Drop $ + Drop %; no ← You marker)

    For 9col-drops mode: `median`, `user_price`, `closest_idx` are unused.
    """
    if mode == MODE_9COL_DROPS:
        return _render_table_9col_drops(rows, currency, heterogeneous)
    return _render_table_8col_comp(rows, median, currency, closest_idx, heterogeneous)


def _render_table_8col_comp(
    rows: list[dict[str, Any]],
    median: float | None,
    currency: str,
    closest_idx: int | None,
    heterogeneous: bool,
) -> list[str]:
    """8-col W1/W4 schema. Identical to pre-v1.8.0 behavior — byte-equivalent."""
    lines: list[str] = []
    lines.append("| " + " | ".join(COLUMNS_8COL) + " |")
    lines.append("|" + "|".join(["---"] * len(COLUMNS_8COL)) + "|")
    for i, r in enumerate(rows):
        price = _to_float(r.get("price"))
        miles = _to_float(r.get("miles"))
        dom_active = _to_int(r.get("dom_active"))  # L1 fix: NEVER `dom`/`dom_180`/`dom_lifetime`
        distance_mi = _to_float(r.get("distance_mi"))  # L2 fix: pre-flattened by parse_search.py:152
        amount = _to_float(r.get("price_change_amount"))
        percent = _to_float(r.get("price_change_percent"))

        dealer = _truncate_dealer_name(r.get("dealer_name"), r.get("is_certified"))
        type_cell = _type_cell(r.get("dealer_type"))
        price_cell = _money(price, currency)
        if closest_idx == i:
            price_cell = f"{price_cell} {LEFT_ARROW} You"
        miles_cell = _miles_cell(miles)
        dom_cell = _dom_cell(dom_active)
        dist_cell = _distance_cell(distance_mi)
        vs_med_cell = _vs_mkt_median_cell(price, median, currency)
        change_cell = _price_change_cell(amount, percent, currency)

        lines.append(
            f"| {dealer} | {type_cell} | {price_cell} | {miles_cell} | "
            f"{dom_cell} | {dist_cell} | {vs_med_cell} | {change_cell} |"
        )
        if heterogeneous:
            sub = _spec_subtitle_per_row(r)
            if sub:
                lines.append(sub)
    return lines


def _render_table_9col_drops(
    rows: list[dict[str, Any]],
    currency: str,
    heterogeneous: bool,
) -> list[str]:
    """9-col W5 Drop-table schema. Old/New price + Drop $ + Drop %; no ← You marker.
    Rows with price_change_percent==0 have Old/Drop cells rendered as — and are
    sorted to the bottom (caller is expected to already have sorted them last;
    this function trusts the order)."""
    lines: list[str] = []
    lines.append("| " + " | ".join(COLUMNS_9COL_DROPS) + " |")
    lines.append("|" + "|".join(["---"] * len(COLUMNS_9COL_DROPS)) + "|")
    for r in rows:
        price = _to_float(r.get("price"))
        miles = _to_float(r.get("miles"))
        dom_active = _to_int(r.get("dom_active"))  # L1 fix: dom_active only
        distance_mi = _to_float(r.get("distance_mi"))  # L2 fix
        amount = _to_float(r.get("price_change_amount"))
        percent = _to_float(r.get("price_change_percent"))

        dealer = _truncate_dealer_name(r.get("dealer_name"), r.get("is_certified"))
        type_cell = _type_cell(r.get("dealer_type"))
        old_price_cell = _old_price_cell(price, amount, currency)
        new_price_cell = _money(price, currency)
        drop_money = _drop_money_cell(amount, currency)
        drop_pct = _drop_percent_cell(percent)
        miles_cell = _miles_cell(miles)
        dom_cell = _dom_cell(dom_active)
        dist_cell = _distance_cell(distance_mi)

        lines.append(
            f"| {dealer} | {type_cell} | {old_price_cell} | {new_price_cell} | "
            f"{drop_money} | {drop_pct} | {miles_cell} | {dom_cell} | {dist_cell} |"
        )
        if heterogeneous:
            sub = _spec_subtitle_per_row(r)
            if sub:
                lines.append(sub)
    return lines


def _find_closest_idx(rows: list[dict], user_price: float | None) -> int | None:
    """Among the rendered rows (post-sort), find the index of the row whose
    price is closest to user_price. First-row tiebreak. Returns None when
    user_price is None."""
    if user_price is None:
        return None
    best_idx: int | None = None
    best_diff: float | None = None
    for i, r in enumerate(rows):
        p = _to_float(r.get("price"))
        if p is None:
            continue
        d = abs(p - user_price)
        if best_diff is None or d < best_diff:
            best_diff = d
            best_idx = i
    return best_idx


def main(argv: list[str]) -> int:
    merged_path = _arg_value(argv, "--merged")
    comp_stats_path = _arg_value(argv, "--comp-stats")
    user_price_raw = _arg_value(argv, "--user-price")
    currency = _arg_value(argv, "--currency") or "$"
    max_rows_raw = _arg_value(argv, "--max-rows")
    mode = _arg_value(argv, "--mode") or MODE_8COL_COMP

    if mode not in VALID_MODES:
        sys.stderr.write(f"render_comp_set_table: invalid --mode {mode!r}; valid: {VALID_MODES}\n")
        return 1

    merged = _load_json(merged_path, "merged")

    # comp-stats is required for 8col-comp (median for vs Mkt Median col).
    # In 9col-drops mode, comp-stats is optional (no median used). Skip the
    # required-flag check when in 9col-drops mode AND no path supplied.
    if mode == MODE_9COL_DROPS and not comp_stats_path:
        comp_stats: dict[str, Any] = {}
    else:
        comp_stats = _load_json(comp_stats_path, "comp-stats")

    user_price = _to_float(user_price_raw) if user_price_raw not in (None, "") else None
    max_rows = _to_int(max_rows_raw)

    listings_raw = merged.get("merged_listings") or []
    if not isinstance(listings_raw, list):
        listings_raw = []
    rows = [r for r in listings_raw if isinstance(r, dict) and _to_float(r.get("price")) is not None]

    # Sort rule depends on mode:
    # - 8col-comp: ascending by price (existing W1/W4 behavior)
    # - 9col-drops: trust caller's order (typically deepest-drop-first per W5
    #   step 1's sort_by="price_change_percent"), but PUT zero-pct rows LAST
    #   per output-template.md line 1037 ("Rows with price_change_percent==0
    #   render old/drop as — and go below real drops with a footnote").
    if mode == MODE_9COL_DROPS:
        # Stable partition: real drops (price_change_percent != 0) first,
        # zero-pct rows last. Preserve caller's order within each partition.
        def _is_real_drop(r: dict) -> bool:
            pct = _to_float(r.get("price_change_percent"))
            return pct is not None and pct != 0
        real_drops = [r for r in rows if _is_real_drop(r)]
        zero_pct_rows = [r for r in rows if not _is_real_drop(r)]
        rows = real_drops + zero_pct_rows
    else:
        rows.sort(key=lambda r: _to_float(r.get("price")) or 0.0)

    if max_rows is not None and max_rows >= 0:
        rows = rows[:max_rows]

    out_lines: list[str] = []

    # Schema for empty-case header.
    cols = COLUMNS_9COL_DROPS if mode == MODE_9COL_DROPS else COLUMNS_8COL

    # Empty case
    if not rows:
        out_lines.append("| " + " | ".join(cols) + " |")
        out_lines.append("|" + "|".join(["---"] * len(cols)) + "|")
        out_lines.append("| *(no comps in this radius)* |")
        sys.stdout.write("\n".join(out_lines) + "\n")
        return 0

    # Heterogeneity / spec subtitle
    heterogeneous, per_field = _detect_heterogeneity(rows)
    if not heterogeneous:
        homo = _spec_subtitle_homogeneous(per_field)
        if homo is not None:
            out_lines.append(homo)
            out_lines.append("")  # blank line between subtitle and table

    # Median for vs Mkt Median (8col-comp only; ignored in 9col-drops mode)
    quartile = comp_stats.get("quartile") if isinstance(comp_stats.get("quartile"), dict) else {}
    median = _to_float(quartile.get("median"))

    # Closest-to-user index (8col-comp only; ignored in 9col-drops mode)
    closest_idx = _find_closest_idx(rows, user_price) if mode == MODE_8COL_COMP else None

    # Table
    out_lines.extend(_render_table(rows, median, user_price, currency, closest_idx, heterogeneous, mode))

    # 9col-drops mode: footnote when zero-pct rows are present
    if mode == MODE_9COL_DROPS:
        zero_count = sum(1 for r in rows if (_to_float(r.get("price_change_percent")) or 0) == 0)
        if zero_count > 0:
            out_lines.append("")
            out_lines.append(
                f"*{zero_count} rows had no `price_change_percent` (server "
                "returned no change history); rendered as `—` and sorted last.*"
            )

    sys.stdout.write("\n".join(out_lines) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors to caller
        sys.stderr.write(f"render_comp_set_table: unexpected error: {exc}\n")
        sys.exit(1)
