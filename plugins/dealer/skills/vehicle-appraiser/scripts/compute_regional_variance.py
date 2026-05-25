#!/usr/bin/env python3
"""
compute_regional_variance.py — Aggregate W4 (Regional Price Variance) signals
deterministically. Reads N stats-only `parse_search.py` outputs (one per ZIP)
and an optional `parse_sold_summary.py` rollup; emits a comparison table the
renderer reads verbatim.

For each ZIP:
  - num_found, median_price, mean_price, p25, p75 (from parse_search stats.price)
  - miles_median (when stats.miles is present)
  - delta_from_lowest_$ / delta_from_lowest_pct (positive — how much above the lowest market)
  - arbitrage_flag (true when delta_from_lowest_pct > threshold)

Also emits:
  - lowest_market / highest_market — picked among markets with non-zero num_found
  - max_delta_pct — the highest delta_from_lowest_pct across all markets

Usage:
  compute_regional_variance.py \\
    --zip-stats <ZIP1>:<path-to-parse_search-output1> \\
    --zip-stats <ZIP2>:<path-to-parse_search-output2> \\
    [--zip-stats <ZIP3>:<path3> ...]                         \\
    [--sold-summary <path-to-parse_sold_summary-output>] \\
    [--threshold-pct 5.0]

Exit codes:
  0  OK (signals JSON emitted on stdout)
  1  Malformed --zip-stats argument or unreadable file
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_THRESHOLD_PCT = 5.0


def _arg_value(argv: list[str], flag: str) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return None


def _arg_value_multi(argv: list[str], flag: str) -> list[str]:
    out: list[str] = []
    for i, token in enumerate(argv):
        if token == flag and i + 1 < len(argv):
            out.append(argv[i + 1])
    return out


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _load_json(path_str: str, label: str) -> dict[str, Any]:
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"compute_regional_variance: cannot read {label} {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"compute_regional_variance: {label} {path_str!r} not JSON: {exc}\n")
        raise SystemExit(1) from exc
    if not isinstance(payload, dict):
        sys.stderr.write(f"compute_regional_variance: {label} payload must be JSON object\n")
        raise SystemExit(1)
    return payload


def _market_row(zip_label: str, parsed: dict[str, Any]) -> dict[str, Any]:
    """Extract a single market's stats from a parse_search stats-only output."""
    num_found = int(parsed.get("num_found") or 0)
    stats = parsed.get("stats") if isinstance(parsed.get("stats"), dict) else {}
    price_stats = stats.get("price") if isinstance(stats.get("price"), dict) else {}
    miles_stats = stats.get("miles") if isinstance(stats.get("miles"), dict) else {}

    pcts = price_stats.get("percentiles") if isinstance(price_stats.get("percentiles"), dict) else {}
    p25 = _to_float(pcts.get("25.0"))
    p75 = _to_float(pcts.get("75.0"))

    return {
        "zip": zip_label,
        "num_found": num_found,
        "median_price": _to_float(price_stats.get("median")),
        "mean_price": _to_float(price_stats.get("mean")),
        "p25": p25,
        "p75": p75,
        "min_price": _to_float(price_stats.get("min")),
        "max_price": _to_float(price_stats.get("max")),
        "miles_median": _to_float(miles_stats.get("median")) if miles_stats else None,
        # delta + flag populated below once the lowest market is known
        "delta_from_lowest_$": None,
        "delta_from_lowest_pct": None,
        "arbitrage_flag": False,
    }


def _state_baselines(sold_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if sold_payload is None:
        return []
    rows = sold_payload.get("rows") if isinstance(sold_payload.get("rows"), list) else []
    out: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        out.append({
            "state": r.get("state"),
            "make": r.get("make"),
            "model": r.get("model"),
            "sold_count": r.get("sold_count"),
            "average_sale_price": r.get("average_sale_price"),
            "average_days_on_market": r.get("average_days_on_market"),
        })
    return out


def main(argv: list[str]) -> int:
    zip_stats_args = _arg_value_multi(argv, "--zip-stats")
    sold_summary_path = _arg_value(argv, "--sold-summary")
    threshold_raw = _arg_value(argv, "--threshold-pct")
    threshold_pct = _to_float(threshold_raw) if threshold_raw is not None else DEFAULT_THRESHOLD_PCT
    if threshold_pct is None:
        threshold_pct = DEFAULT_THRESHOLD_PCT

    if not zip_stats_args:
        sys.stderr.write("compute_regional_variance: at least one --zip-stats <ZIP>:<path> required\n")
        return 1

    markets: list[dict[str, Any]] = []
    for arg in zip_stats_args:
        if ":" not in arg:
            sys.stderr.write(
                f"compute_regional_variance: --zip-stats {arg!r} must be in <ZIP>:<path> format\n"
            )
            return 1
        zip_label, path_str = arg.split(":", 1)
        zip_label = zip_label.strip()
        path_str = path_str.strip()
        if not zip_label or not path_str:
            sys.stderr.write(f"compute_regional_variance: --zip-stats {arg!r} malformed\n")
            return 1
        parsed = _load_json(path_str, f"zip-stats[{zip_label}]")
        markets.append(_market_row(zip_label, parsed))

    # Pick lowest / highest markets (only among those with a non-null median)
    priced_markets = [m for m in markets if m["median_price"] is not None and m["median_price"] > 0]
    if priced_markets:
        lowest = min(priced_markets, key=lambda m: m["median_price"])
        highest = max(priced_markets, key=lambda m: m["median_price"])
        # Compute delta vs lowest
        baseline = lowest["median_price"]
        for m in markets:
            if m["median_price"] is None or baseline is None or baseline <= 0:
                continue
            diff = m["median_price"] - baseline
            pct = (diff / baseline) * 100.0
            m["delta_from_lowest_$"] = diff
            m["delta_from_lowest_pct"] = pct
            m["arbitrage_flag"] = pct > threshold_pct
        max_delta_pct = max(
            (m["delta_from_lowest_pct"] or 0.0) for m in markets if m["delta_from_lowest_pct"] is not None
        ) if any(m["delta_from_lowest_pct"] is not None for m in markets) else 0.0
        lowest_summary = {"zip": lowest["zip"], "median": lowest["median_price"]}
        highest_summary = {"zip": highest["zip"], "median": highest["median_price"]}
    else:
        lowest_summary = None
        highest_summary = None
        max_delta_pct = 0.0

    sold_payload = None
    if sold_summary_path:
        sold_payload = _load_json(sold_summary_path, "sold-summary")
    state_baselines = _state_baselines(sold_payload)

    out = {
        "ok": True,
        "markets": markets,
        "lowest_market": lowest_summary,
        "highest_market": highest_summary,
        "max_delta_pct": max_delta_pct,
        "threshold_pct": threshold_pct,
        "state_baselines": state_baselines,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"compute_regional_variance: unexpected error: {exc}\n")
        sys.exit(1)
