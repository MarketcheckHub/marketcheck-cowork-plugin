#!/usr/bin/env python3
"""
compute_w3_rollup.py — Roll up the top-25 make leaderboard (from
parse_sold_summary --aggregate-by-dimension make) to tickers using the
OEM map, then emit a top-N leaderboard plus a deterministic
cohort headline observation. Used by W3 (US OEM Market Share Leaderboard).

Stdin JSON contract:
  {
    "dimension_values": [<dimension_value_record>, ...],     # parser output
    "top_n": 1..10                                            # user-chosen
  }

Each dimension_value_record (from parse_sold_summary --aggregate-by-dimension make):
  {
    "value": "Toyota",
    "total_sold_count": 252206,
    "weighted_avg_sale_price": 44934.06,
    "weighted_avg_days_on_market": 32.46,
    "share_pct": 22.15,
    ...
  }

Stdout (success):
  {
    "ok": true,
    "leaderboard": [
      {"rank": 1, "ticker": "TM", "company_name": "...", "makes": [...],
       "sold_count": ..., "share_pct": ..., "avg_asp": ..., "avg_dom": ...,
       "makes_in_top25": [...], "makes_outside_top25": []},
      ...
    ],
    "cohort_headline": {
      "top_ticker": "TM", "top_company_name": "...", "top_sold": ...,
      "top_makes_count": 2, "median_asp": ..., "median_dom": ...,
      "observation": "<one rendered sentence — deterministic rule>"
    },
    "split_ticker_footnotes": [<sentence>, ...],
    "dq_events": [<event>, ...]
  }

Cohort observation rule (deterministic, priority order):
  A. If top-2 share >= 50% of cohort  → "top-2 OEMs account for X% ..."
  B. Else if span_ratio > 5×          → "cohort spans Y× from #1 to #N ..."
  C. Else                              → "all N publicly traded / X private-only ..."

Tie-breaker: strict priority — A wins if its threshold is met regardless of B/C.

Exit codes:
  0  success or payload-level failure (parse the JSON)
  1  validation error
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import arg_value, emit
from resolve_oem import _parse_oem_map  # reuse the existing OEM-map loader


_REFERENCES_DIR = Path(__file__).parent.parent / "references"
_TICKER_MAP_DEFAULT = _REFERENCES_DIR / "ticker-mapping.md"


def _load_oem_map(ticker_file: Path) -> list[dict]:
    if not ticker_file.exists():
        return []
    content = ticker_file.read_text(encoding="utf-8")
    return _parse_oem_map(content)


def _build_make_to_ticker(oem_map: list[dict]) -> dict[str, dict]:
    """Reverse-lookup: make name (lowercased) → {ticker, company_name, classification, all_makes}."""
    out: dict[str, dict] = {}
    for row in oem_map:
        ticker = row["ticker"]
        company = row["company_name"]
        classification = row["classification"]
        all_makes = row["makes"]
        for make in all_makes:
            out[make.lower()] = {
                "ticker": ticker,
                "company_name": company,
                "classification": classification,
                "all_makes": all_makes,
            }
    return out


def _to_float(v) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _to_int(v) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _weighted_mean(values_weights: list[tuple[float | None, int | None]]) -> float | None:
    """Sold-count-weighted mean. Null values drop from both numerator AND denominator."""
    num = 0.0
    den = 0
    for v, w in values_weights:
        if v is None or w is None or w <= 0:
            continue
        num += v * w
        den += w
    return (num / den) if den > 0 else None


def _rollup_by_ticker(
    dimension_values: list[dict], make_to_ticker: dict[str, dict]
) -> tuple[list[dict], list[str], list[dict]]:
    """Group dimension_values by ticker. Returns:
       - tickers_list: list of per-ticker rollup dicts (sorted desc by sold)
       - brand_orphans: list of make names not found in the OEM map
       - cohort_makes: every make's per-make record (preserved for split-ticker detection)"""
    # cohort_total is the SUM of all top-25 makes' sold (the underlying denominator)
    by_ticker: dict[str, dict] = {}
    brand_orphans: list[str] = []
    cohort_makes: list[dict] = []

    for entry in dimension_values:
        make = entry.get("value")
        if not make:
            continue
        sold = _to_int(entry.get("total_sold_count")) or 0
        asp = _to_float(entry.get("weighted_avg_sale_price"))
        dom = _to_float(entry.get("weighted_avg_days_on_market"))
        cohort_makes.append({"make": make, "sold": sold, "asp": asp, "dom": dom})

        info = make_to_ticker.get(make.lower())
        if info is None:
            brand_orphans.append(make)
            continue

        ticker = info["ticker"]
        bucket = by_ticker.setdefault(ticker, {
            "ticker": ticker,
            "company_name": info["company_name"],
            "classification": info["classification"],
            "all_makes": info["all_makes"],
            "makes_in_top25": [],
            "sold_count": 0,
            "_asp_pairs": [],
            "_dom_pairs": [],
        })
        bucket["makes_in_top25"].append(make)
        bucket["sold_count"] += sold
        bucket["_asp_pairs"].append((asp, sold))
        bucket["_dom_pairs"].append((dom, sold))

    # Finalize each ticker rollup
    out: list[dict] = []
    for ticker_data in by_ticker.values():
        avg_asp = _weighted_mean(ticker_data["_asp_pairs"])
        avg_dom = _weighted_mean(ticker_data["_dom_pairs"])
        makes_in_top25 = ticker_data["makes_in_top25"]
        all_makes = ticker_data["all_makes"]
        makes_outside_top25 = [m for m in all_makes if m not in makes_in_top25]
        out.append({
            "ticker": ticker_data["ticker"],
            "company_name": ticker_data["company_name"],
            "classification": ticker_data["classification"],
            "makes": all_makes,
            "makes_in_top25": makes_in_top25,
            "makes_outside_top25": makes_outside_top25,
            "sold_count": ticker_data["sold_count"],
            "avg_asp": avg_asp,
            "avg_dom": avg_dom,
        })

    out.sort(key=lambda r: r["sold_count"], reverse=True)
    return out, brand_orphans, cohort_makes


def _compute_observation(
    leaderboard: list[dict], top_n: int, cohort_total: int
) -> str:
    """Deterministic three-tier observation rule. Priority: A > B > C."""
    N = min(top_n, len(leaderboard))
    if N == 0:
        return "Cohort is empty."

    # Rule A — top-2 share >= 50%
    if N >= 2 and cohort_total > 0:
        top2_sold = leaderboard[0]["sold_count"] + leaderboard[1]["sold_count"]
        top2_share = 100.0 * top2_sold / cohort_total
        if top2_share >= 50.0:
            t1 = leaderboard[0]["ticker"]
            t2 = leaderboard[1]["ticker"]
            return (
                f"The top 2 OEMs (`{t1}`, `{t2}`) account for "
                f"{top2_share:.1f}% of the top-{top_n} cohort volume."
            )

    # Rule B — span ratio > 5×
    if N >= 2:
        n1 = leaderboard[0]["sold_count"]
        nN = leaderboard[N - 1]["sold_count"]
        if nN > 0:
            ratio = n1 / nN
            if ratio > 5.0:
                return (
                    f"The cohort spans {ratio:.1f}× from #1 ({n1:,} units) to "
                    f"#{N} ({nN:,} units)."
                )

    # Rule C — public/private composition (every ticker in the OEM map IS US-listed)
    # Brand-orphan makes that didn't make it into a ticker are private/non-US.
    # In the leaderboard slice [0:N], all entries are by-ticker (public US-listed).
    # If brand-orphans exist outside the slice but ARE in the top-25 raw, we count
    # them at the cohort level — but the leaderboard's top-N slice itself is all public.
    # Refinement: counting private/non-US listed only makes sense if any top-N entry
    # is a brand-orphan, which by construction doesn't happen (orphans don't get a ticker).
    # So Rule C resolves to: "All N OEMs are publicly traded with US listings."
    return f"All {N} OEMs in the top-{top_n} are publicly traded with US listings."


def _build_split_ticker_footnotes(leaderboard_slice: list[dict]) -> list[str]:
    """Render one footnote per ticker that has makes outside the top-25."""
    footnotes: list[str] = []
    for entry in leaderboard_slice:
        outside = entry.get("makes_outside_top25") or []
        if outside:
            ticker = entry["ticker"]
            makes_str = ", ".join(outside)
            footnotes.append(
                f"{ticker}'s {makes_str} fell outside the top-25 leaderboard "
                f"this month; aggregate volume understates true volume by an "
                f"unknown amount."
            )
    return footnotes


def _validate_input(cfg) -> tuple[bool, str | None, str | None]:
    if not isinstance(cfg, dict):
        return False, "bad_stdin", "<root>"
    dv = cfg.get("dimension_values")
    if not isinstance(dv, list) or len(dv) == 0:
        return False, "missing_required_field", "dimension_values"
    return True, None, None


def main(argv: list[str]) -> int:
    try:
        cfg = json.load(sys.stdin)
    except Exception as exc:
        emit({"ok": False, "error_type": "bad_stdin", "error": str(exc)})
        return 0

    ok, error_type, field = _validate_input(cfg)
    if not ok:
        emit({"ok": False, "error_type": error_type, "field": field,
              "error": f"compute_w3_rollup missing required field: {field}"})
        return 0

    # CLI override for top-N (defaults to 5 if not provided as either arg or stdin)
    top_n_arg = arg_value(argv, "--top-n")
    top_n_stdin = cfg.get("top_n")
    if top_n_arg is not None:
        try:
            top_n = int(top_n_arg)
        except ValueError:
            emit({"ok": False, "error_type": "invalid_top_n", "value": top_n_arg})
            return 0
    elif top_n_stdin is not None:
        top_n = int(top_n_stdin)
    else:
        top_n = 5

    if top_n < 1 or top_n > 10:
        emit({"ok": False, "error_type": "invalid_top_n",
              "error": "top_n must be 1-10", "value": top_n})
        return 0

    ticker_file_arg = arg_value(argv, "--ticker-file")
    ticker_file = Path(ticker_file_arg) if ticker_file_arg else _TICKER_MAP_DEFAULT
    oem_map = _load_oem_map(ticker_file)
    make_to_ticker = _build_make_to_ticker(oem_map)

    leaderboard, brand_orphans, cohort_makes = _rollup_by_ticker(
        cfg["dimension_values"], make_to_ticker
    )

    # cohort_total: sum across ALL top-25 raw makes (post-ticker-rollup total +
    # brand-orphan totals). Share % is computed against this.
    cohort_total = sum(m["sold"] for m in cohort_makes)

    # Compute share_pct per ticker against cohort total
    for entry in leaderboard:
        entry["share_pct"] = (
            round(100.0 * entry["sold_count"] / cohort_total, 2)
            if cohort_total > 0 else None
        )

    # Slice to top-N
    leaderboard_slice = leaderboard[:top_n]
    # Add rank
    for i, entry in enumerate(leaderboard_slice):
        entry["rank"] = i + 1

    # Cohort headline
    top_entry = leaderboard_slice[0] if leaderboard_slice else None
    if top_entry:
        # Cohort median ASP / DOM across the top-N entries (sold-count-weighted: NO,
        # the template explicitly says "cohort median" not "weighted average").
        asp_values = [e["avg_asp"] for e in leaderboard_slice if e["avg_asp"] is not None]
        dom_values = [e["avg_dom"] for e in leaderboard_slice if e["avg_dom"] is not None]
        median_asp = statistics.median(asp_values) if asp_values else None
        median_dom = statistics.median(dom_values) if dom_values else None

        observation = _compute_observation(leaderboard_slice, top_n, cohort_total)

        cohort_headline = {
            "top_ticker": top_entry["ticker"],
            "top_company_name": top_entry["company_name"],
            "top_sold": top_entry["sold_count"],
            "top_makes_count": len(top_entry["makes_in_top25"]),
            "median_asp": round(median_asp, 2) if median_asp is not None else None,
            "median_dom": round(median_dom, 1) if median_dom is not None else None,
            "observation": observation,
        }
    else:
        cohort_headline = None

    split_ticker_footnotes = _build_split_ticker_footnotes(leaderboard_slice)

    dq_events: list[str] = []
    if brand_orphans:
        dq_events.append(
            f"(j) Brand-orphan makes in the top-25 (no parent ticker): "
            f"{', '.join(brand_orphans)}. Not rolled up to any ticker."
        )

    # Strip internal fields before emitting
    for entry in leaderboard_slice:
        # Round avg_asp / avg_dom for stability
        if entry.get("avg_asp") is not None:
            entry["avg_asp"] = round(entry["avg_asp"], 2)
        if entry.get("avg_dom") is not None:
            entry["avg_dom"] = round(entry["avg_dom"], 1)

    emit({
        "ok": True,
        "leaderboard": leaderboard_slice,
        "cohort_headline": cohort_headline,
        "split_ticker_footnotes": split_ticker_footnotes,
        "dq_events": dq_events,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
