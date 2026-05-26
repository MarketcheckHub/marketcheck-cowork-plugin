#!/usr/bin/env python3
"""
build_comp_stats_input.py — Assemble the stdin JSON for `comp_stats.py` from
the outputs of `load_profile.py`, `merge_comps.py`, the four `parse_search.py`
calls, and the (up to) four `parse_predict.py` outputs (PRIMARY/CONTEXT × non-CPO/CPO).

This removes the hand-construction step the skill used to do inline — an
error-prone ~20-field JSON build that both v4 and v5 had to improvise, with
at least one run (v4's F2) passing a pulled_count that had already been
pre-trimmed.

Usage:
  build_comp_stats_input.py \\
    --profile <load_profile.py output path>               \\
    --asc-parsed <parse_search asc output path>           \\
    --user-price <asking price>                           \\
    --user-miles <mileage>                                \\
    --subject-vin <17-char VIN>                           \\
    --subject-cpo true|false                              \\
    --trim-label "2022 Lexus RX 350"                      \\
    [--merged <merge_comps.py output path>]               \\
    [--sold-price <parse_search sold-90d price stats path>] \\
    [--sold-dom <parse_search sold-90d dom stats path>]   \\
    [--drops <parse_search drop-scan path>]               \\
    [--nocpo-primary-parsed <parse_predict.py output path>] \\
    [--nocpo-context-parsed <parse_predict.py output path>] \\
    [--cpo-primary-parsed   <parse_predict.py output path>] \\
    [--cpo-context-parsed   <parse_predict.py output path>] \\
    [--exclude-vin <V1> [--exclude-vin <V2> ...]]

Required: --profile, --asc-parsed.

Optional (v1.7.0+ — W1 always passes; W2/W4 omit selectively with safe defaults):
  --merged       — when omitted, synthesize from --asc-parsed:
                   merged = {"merged_listings": asc.listings, "pulled_count": asc.kept_count}.
                   W1 always passes --merged (from merge_comps.py); W2 omits it
                   because it doesn't fire a desc tail-pull. W4 always passes it
                   (from merge_comps.py over cheapest-8 + most-expensive-5).
  --sold-price   — when omitted, sold_count_90d=0, sold_median=None.
                   W1/W4 pass it from search_past_90_days stats="price"; W2 omits
                   because it doesn't fire sold-90d calls.
  --sold-dom     — when omitted, sold_dom_median=None, sold_dom_field=None.
                   W1 passes; W2/W4 omit (no dom-stats call in those flows).
  --drops        — when omitted, drops_market_wide_count=0.
                   W1 passes from search_active_cars price_change="negative";
                   W2/W4 omit (no drop-scan call).
  --user-price   — when omitted, user_price=None. comp_stats.py guards at lines
                   800, 811, 814, 877 — emits verdict / gap_vs_median /
                   primary_only.diff as null. W1/W2 always pass; W4 omits
                   (no subject vehicle).
  --user-miles   — when omitted, user_miles=None. Same pattern as --user-price.
  --subject-vin  — when omitted, subject_vin="". parse_search.py line 217 short-
                   circuits shadow-listing logic on empty subject_vin. W1/W2
                   always pass; W4 omits (no subject vehicle).
  --subject-cpo  — when omitted, subject_is_certified=False. Used only by the
                   CPO branch of comp_stats; W4 (no subject) renders no CPO
                   Premium block.

# Example: W4 (no subject vehicle) invocation —
#   build_comp_stats_input.py \\
#     --profile <profile.json> \\
#     --asc-parsed <cheapest-8.json>      # has stats="price,miles"
#     --merged <merged.json>              # cheapest-8 + most-expensive-5 deduped
#     --sold-price <sold-90d-price.json>  # from search_past_90_days
#     --trim-label "2022 Toyota Camry SE"

When all 4 optional flags ARE supplied (W1 path), output is byte-identical to
pre-v1.5.0 behavior — guarded by tests/test_build_comp_stats_input.py's
test_w1_existing_path_still_works_byte_identical against
tests/fixtures/w1_baseline_snapshot.json.

Each `--*-parsed` flag points at a parse_predict.py output JSON. The builder
reads each, extracts marketcheck_price + comparables_n + recent_comparables_n
+ comparables_price_stats + recent_comparables_price_stats, and packs the four
roles into a `marketcheck_predict_input` block on the comp_stats stdin JSON.
A parsed file with `ok=false` is treated as "this prediction call didn't
recover" — the role's input is null and a stderr WARNING is emitted.

Emits the full comp_stats stdin JSON on stdout. Pipe directly:

  build_comp_stats_input.py ... | comp_stats.py

Exit codes:
  0  OK (comp_stats JSON emitted)
  1  Missing or malformed required inputs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Single source for the insufficient-comps threshold — avoids drift between
# this builder and the consumer. Both scripts must use the same value; the
# canonical definition lives in comp_stats.py.
from comp_stats import DEFAULT_MIN_N


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
            for piece in argv[i + 1].split(","):
                piece = piece.strip()
                if piece:
                    out.append(piece)
    return out


def _to_float(raw: Any) -> float | None:
    """Coerce to float. Accepts str (from CLI flags, with $/commas), int, float,
    or None. Config-file values arrive as native JSON types (int/float) and must
    skip the str.replace call."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return None


def _to_bool(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in ("1", "true", "yes", "y", "cpo", "certified")


def _load_json(path_str: str | None, label: str, required: bool = True) -> dict[str, Any] | None:
    if not path_str:
        if required:
            sys.stderr.write(f"build_comp_stats_input: --{label} is required\n")
            raise SystemExit(1)
        return None
    path = Path(path_str)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"build_comp_stats_input: cannot read {label} file {path_str!r}: {exc}\n")
        raise SystemExit(1) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"build_comp_stats_input: {label} file {path_str!r} is not JSON: {exc}\n")
        raise SystemExit(1) from exc


def _dig(obj: Any, *keys: str, default: Any = None) -> Any:
    """obj.get(keys[0]).get(keys[1])... with None-tolerant traversal."""
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def _resolve(argv: list[str], flag: str, config: dict, key: str, default: Any = None) -> Any:
    """CLI flag wins; else config-file value; else default.

    Keeps flag precedence clear: the one-off `--subject-cpo true` override on
    a saved config file should not require editing the file. Returns the
    string form from the flag when present (argparse-style handling downstream),
    or the native JSON type from the config file.
    """
    val = _arg_value(argv, flag)
    if val is not None:
        return val
    if key in config and config[key] is not None:
        return config[key]
    return default


def _load_predict_role(
    argv: list[str], flag: str, config: dict, config_key: str, role_label: str,
) -> dict[str, Any] | None:
    """Read a parse_predict.py output JSON for one MarketCheck Price role.

    Returns the 5-field dict (marketcheck_price, comparables_n,
    recent_comparables_n, comparables_price_stats, recent_comparables_price_stats)
    when the parsed file is healthy; returns None and emits a stderr WARNING
    when the path is absent, the file is unreadable, or `ok` is false. The
    None propagates into `marketcheck_predict_input.<role>` and downstream
    `comp_stats.py` skips the role's derivations cleanly.

    `role_label` is the name used in stderr WARNING messages
    (`nocpo_primary` / `nocpo_context` / `cpo_primary` / `cpo_context`).
    """
    path = _resolve(argv, flag, config, config_key)
    if not path:
        return None
    parsed = _load_json(path, f"{role_label}-parsed", required=False)
    if not isinstance(parsed, dict):
        sys.stderr.write(
            f"build_comp_stats_input: WARNING — {role_label}-parsed file {path!r} "
            "is not a JSON object; treating as missing.\n"
        )
        return None
    if parsed.get("ok") is False:
        sys.stderr.write(
            f"build_comp_stats_input: WARNING — {role_label}-parsed reported "
            f"ok=false (error_type={parsed.get('error_type')!r}); treating as missing.\n"
        )
        return None
    mkt_price = _to_float(parsed.get("marketcheck_price"))
    if mkt_price is None:
        sys.stderr.write(
            f"build_comp_stats_input: WARNING — {role_label}-parsed has no "
            "marketcheck_price; treating as missing.\n"
        )
        return None
    return {
        "marketcheck_price": mkt_price,
        "comparables_n": parsed.get("comparables_n"),
        "recent_comparables_n": parsed.get("recent_comparables_n"),
        "comparables_price_stats": parsed.get("comparables_price_stats"),
        "recent_comparables_price_stats": parsed.get("recent_comparables_price_stats"),
    }


def main(argv: list[str]) -> int:
    # Optional JSON config file — every field below can be pre-filled there
    # and overridden individually by flags. Reduces a 16-flag call site to a
    # one-file-one-flag invocation for scripted callers.
    config_path = _arg_value(argv, "--config-file")
    config: dict[str, Any] = {}
    if config_path:
        try:
            config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"build_comp_stats_input: cannot load --config-file {config_path!r}: {exc}\n")
            return 1
        if not isinstance(config, dict):
            sys.stderr.write(f"build_comp_stats_input: --config-file {config_path!r} must contain a JSON object\n")
            return 1

    # Required paths (flag OR config): --profile, --asc-parsed
    profile = _load_json(_resolve(argv, "--profile", config, "profile"), "profile")
    asc = _load_json(_resolve(argv, "--asc-parsed", config, "asc_parsed"), "asc-parsed")
    # Optional paths (v1.5.0+; W1 supplies them; W2 omits with W2-safe defaults).
    # When omitted, downstream readers fall back to their `or {}` patterns and
    # emit zero/None defaults, matching the behavior pre-v1.5.0 of the W1 caller
    # who always passed all four. See module docstring for the per-flag default.
    merged = _load_json(_resolve(argv, "--merged", config, "merged"), "merged", required=False)
    sold_price = _load_json(_resolve(argv, "--sold-price", config, "sold_price"), "sold-price", required=False)
    sold_dom = _load_json(_resolve(argv, "--sold-dom", config, "sold_dom"), "sold-dom", required=False)
    drops = _load_json(_resolve(argv, "--drops", config, "drops"), "drops", required=False)

    # v1.5.0 W2 synth-from-asc fallback: when --merged is omitted (W2 doesn't
    # fire a desc tail-pull, so merge_comps has nothing to merge), synthesize
    # merged from the already-loaded --asc-parsed payload. The synth uses
    # asc.listings as merged_listings (already post-filter via parse_search's
    # --subject-vin / --exclude-vins) and asc.kept_count as pulled_count
    # (post-filter count, mirroring merge_comps's pulled_count semantic where
    # asc_n+desc_n is computed from the already-parse_search-filtered listings).
    if merged is None and isinstance(asc, dict):
        asc_listings = asc.get("listings") or []
        if not isinstance(asc_listings, list):
            asc_listings = []
        asc_kept = asc.get("kept_count")
        try:
            asc_kept = int(asc_kept) if asc_kept is not None else len(asc_listings)
        except (TypeError, ValueError):
            asc_kept = len(asc_listings)
        merged = {"merged_listings": asc_listings, "pulled_count": asc_kept}

    user_price = _to_float(_resolve(argv, "--user-price", config, "user_price"))
    user_miles = _to_float(_resolve(argv, "--user-miles", config, "user_miles"))
    subject_vin_raw = _resolve(argv, "--subject-vin", config, "subject_vin") or ""
    subject_vin = str(subject_vin_raw).upper().strip()
    subject_cpo_raw = _resolve(argv, "--subject-cpo", config, "subject_cpo")
    subject_cpo = _to_bool(subject_cpo_raw if isinstance(subject_cpo_raw, str) else str(subject_cpo_raw))
    trim_label = _resolve(argv, "--trim-label", config, "trim_label") or "this unit"
    # exclude_vins: flags use repeat-or-CSV form; config uses a JSON list.
    exclude_vins_flags = _arg_value_multi(argv, "--exclude-vin")
    exclude_vins_config = config.get("exclude_vins") or []
    if exclude_vins_flags:
        exclude_vins = [v.upper() for v in exclude_vins_flags]
    else:
        exclude_vins = [str(v).upper() for v in exclude_vins_config if v]

    # Optional MarketCheck Price predict outputs — one per role:
    #   (PRIMARY/CONTEXT) × (non-CPO/CPO). Each --*-parsed flag points at a
    #   parse_predict.py output JSON; the builder extracts marketcheck_price +
    #   comparables_n + recent_comparables_n + comparables_price_stats +
    #   recent_comparables_price_stats. Roles with no flag (or with a flag
    #   pointing at an ok=false parsed file) become null in marketcheck_predict_input.
    nocpo_primary_predict = _load_predict_role(
        argv, "--nocpo-primary-parsed", config, "nocpo_primary_parsed", "nocpo_primary"
    )
    nocpo_context_predict = _load_predict_role(
        argv, "--nocpo-context-parsed", config, "nocpo_context_parsed", "nocpo_context"
    )
    cpo_primary_predict = _load_predict_role(
        argv, "--cpo-primary-parsed", config, "cpo_primary_parsed", "cpo_primary"
    )
    cpo_context_predict = _load_predict_role(
        argv, "--cpo-context-parsed", config, "cpo_context_parsed", "cpo_context"
    )

    # v1.7.0 W4 plan: --subject-vin and --user-price are now optional. W1 + W2
    # callers always supply both (verdict computation depends on user_price);
    # W4 (Market Price Distribution) has no subject vehicle and supplies neither.
    # comp_stats.py guards user_price=None at lines 800, 811, 814, 877 — emits
    # verdict/gap_vs_median/primary_only.diff as null. parse_search.py guards
    # subject_vin="" at line 217 — short-circuits shadow-listing logic.
    # When both are supplied (W1/W2), behavior is byte-identical to pre-v1.7.0.

    # Partial-CPO warning: when subject is CPO but any of the four required
    # predict roles is missing, `comp_stats.py` emits `marketcheck_predict.premium_*`
    # as null and the CPO Premium block won't render. Surface missing roles on
    # stderr so the caller sees why, rather than hunting for the silent gap.
    # Non-fatal — the script continues.
    if subject_cpo:
        missing = [
            name for name, val in [
                ("--nocpo-primary-parsed", nocpo_primary_predict),
                ("--nocpo-context-parsed", nocpo_context_predict),
                ("--cpo-primary-parsed", cpo_primary_predict),
                ("--cpo-context-parsed", cpo_context_predict),
            ] if val is None
        ]
        if missing:
            sys.stderr.write(
                "build_comp_stats_input: WARNING — subject-cpo=true but missing "
                f"{', '.join(missing)}. comp_stats will emit marketcheck_predict.premium_*=null "
                "and the CPO Premium block will not render.\n"
            )

    # Profile-derived
    profile = profile or {}
    session = profile.get("session") or {}
    location = profile.get("location") or {}
    preferences = profile.get("preferences") or {}
    dealer = profile.get("dealer") or {}

    subject_dealer_type = (session.get("dealer_type_lower") or dealer.get("dealer_type") or "").lower() or None
    radius_mi = int(session.get("radius_mi_clamped") or preferences.get("default_radius_miles") or 50)
    city = location.get("city") or ""
    dom_thresholds = preferences.get("dom_thresholds") or {}
    fresh_max = int(dom_thresholds.get("fresh") or 30)
    aging_max = int(dom_thresholds.get("aging") or 60)
    cpo_cert_cost = dealer.get("cpo_certification_cost")
    try:
        cpo_cert_cost = float(cpo_cert_cost) if cpo_cert_cost is not None else None
    except (TypeError, ValueError):
        cpo_cert_cost = None

    # Merged output
    merged = merged or {}
    comps = merged.get("merged_listings") or []
    pulled_count = int(merged.get("pulled_count") or 0)

    # Asc parse_search (for active_count + server_stats)
    asc = asc or {}
    active_count = int(asc.get("num_found") or 0)
    server_stats = asc.get("stats") or {}

    # Sold-90d price stats. After upstream `price_range="1-*"` + `sold=true`
    # filters (per W1 step 7 / W4 step 4 spec), every matched record has
    # price ≥ 1 and is sold-classified, so `num_found == stats.price.count`
    # is guaranteed. The previous dual-tracking (sold_count_90d for MoS,
    # sold_n for the verdict gate) has been collapsed: comp_stats.py reads
    # sold_count_90d for both purposes. See references/w1-price-check.md
    # step 7 rationale paragraph for the filter semantics.
    sold_price = sold_price or {}
    sold_count_90d = int(sold_price.get("num_found") or 0)
    sold_price_stats = _dig(sold_price, "stats", "price", default={}) or {}
    sold_median_raw = sold_price_stats.get("median")
    try:
        sold_median = float(sold_median_raw) if sold_median_raw is not None else None
    except (TypeError, ValueError):
        sold_median = None

    # Sold-90d DOM stats — primary-with-fallback read.
    #
    # PRIMARY:  stats.dom_active.median — current-listing time-to-sell semantic,
    #           internally consistent with the dom_active-bucketed DOM Distribution.
    # FALLBACK: stats.dom.median — lifetime cross-dealer accumulator. Used only
    #           when upstream rejected stats=dom_active (older API versions).
    # The renderer reads `sold_dom_field` to choose the appropriate label
    # ("median days-to-sell" vs "median lifetime DOM") and emit a Data Quality
    # event when the fallback fires. See references/w1-price-check.md step 7c.
    sold_dom = sold_dom or {}
    sold_dom_stats_block = _dig(sold_dom, "stats", default={}) or {}
    if isinstance(sold_dom_stats_block, dict) and isinstance(sold_dom_stats_block.get("dom_active"), dict):
        sold_dom_stats = sold_dom_stats_block["dom_active"]
        sold_dom_field = "dom_active"
    elif isinstance(sold_dom_stats_block, dict) and isinstance(sold_dom_stats_block.get("dom"), dict):
        sold_dom_stats = sold_dom_stats_block["dom"]
        sold_dom_field = "dom"
    else:
        sold_dom_stats = {}
        sold_dom_field = None
    sold_dom_median_raw = sold_dom_stats.get("median")
    try:
        sold_dom_median = float(sold_dom_median_raw) if sold_dom_median_raw is not None else None
    except (TypeError, ValueError):
        sold_dom_median = None

    # Drop scan (num_found is the market-wide drop count)
    drops = drops or {}
    drops_market_wide_count = int(drops.get("num_found") or 0)

    # Assemble comp_stats input
    comp_stats_input: dict[str, Any] = {
        "user_price": user_price,
        "subject_vin": subject_vin,
        "subject_dealer_type": subject_dealer_type,
        "subject_is_certified": subject_cpo,
        "subject_miles": user_miles,
        "trim_label": trim_label,
        "radius_mi": radius_mi,
        "city": city,
        "comps": comps,
        "active_count": active_count,
        "pulled_count": pulled_count,
        "sold_count_90d": sold_count_90d,
        "sold_median": sold_median,
        "sold_dom_median": sold_dom_median,
        "sold_dom_field": sold_dom_field,  # "dom_active" (PRIMARY) | "dom" (FALLBACK) | None
        "drops_market_wide_count": drops_market_wide_count,
        "server_stats": server_stats,
        "fresh_max_days": fresh_max,
        "aging_max_days": aging_max,
        "min_n": DEFAULT_MIN_N,
        "exclude_vins": exclude_vins,
        # MarketCheck Price predict roles — each is the 5-field dict from
        # parse_predict.py (marketcheck_price + counts + price stats blocks),
        # or None when the role didn't run / didn't recover. Replaces the
        # legacy flat cpo_primary_price / nocpo_primary_price / etc. fields.
        "marketcheck_predict_input": {
            "nocpo_primary": nocpo_primary_predict,
            "nocpo_context": nocpo_context_predict,
            "cpo_primary":   cpo_primary_predict,
            "cpo_context":   cpo_context_predict,
            "certification_cost": cpo_cert_cost,
        },
    }

    json.dump(comp_stats_input, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors to caller
        sys.stderr.write(f"build_comp_stats_input: unexpected error: {exc}\n")
        sys.exit(1)
