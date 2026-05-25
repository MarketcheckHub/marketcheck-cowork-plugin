#!/usr/bin/env python3
"""
parse_decode.py — Normalise a `decode_vin_neovin` response.

Usage:
  parse_decode.py                    # read tool response from stdin
  parse_decode.py --file <path>      # unwrap a truncation-envelope file

Emits on stdout:
  {
    "ok": true/false,
    "error_type": "...",
    "error": "...",
    "vin": "...",
    "specs": {
      "year": ..., "make": ..., "model": ..., "trim": ...,
      "body_type": ..., "drivetrain": ...,
      "engine": ..., "transmission": ...,
      "msrp": ...
    }
  }
"""

from __future__ import annotations

import sys
from typing import Any

from _common import read_input, emit, classify_error


# Spec field names from the live decode_vin_neovin response (verified 2026-04-28
# against VIN 2T2HZMAA7NC244003). Each list is single-element — earlier alternates
# (manufacturer, trim_variant, body_style, body_subtype, drive_train, driven_wheels,
# engine_description, base_msrp, starting_msrp) were speculative and never appeared
# on the wire. _first() still filters None / "" / "N/A" defensively.
SPECS_FIELDS = {
    "year":          ["year"],
    "make":          ["make"],
    "model":         ["model"],
    "trim":          ["trim"],
    "body_type":     ["body_type"],
    "drivetrain":    ["drivetrain"],
    "engine":        ["engine"],
    "transmission":  ["transmission"],
    "msrp":          ["msrp"],
}


def _first(d: dict[str, Any], keys: list[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, "", "N/A"):
            return d[k]
    return None


def extract_specs(payload: Any) -> dict[str, Any]:
    """Walk the payload looking for the first dict that carries the spec fields."""
    # Typical shape: {success: true, service: "vin_decoder", data: {...}}
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], dict):
            candidate = payload["data"]
        else:
            candidate = payload
        # Some versions wrap further under data.specifications or data.vehicle
        for subkey in ("specifications", "vehicle", "decoded", "result"):
            if isinstance(candidate.get(subkey), dict):
                candidate = candidate[subkey]
                break
        specs: dict[str, Any] = {}
        for out_key, candidates in SPECS_FIELDS.items():
            specs[out_key] = _first(candidate, candidates)
        # Year can come back as a string
        if specs["year"] is not None:
            try:
                specs["year"] = int(str(specs["year"])[:4])
            except (TypeError, ValueError):
                pass
        # MSRP can come back as a string with $ or ','
        if specs["msrp"] is not None:
            try:
                specs["msrp"] = float(str(specs["msrp"]).replace("$", "").replace(",", ""))
            except (TypeError, ValueError):
                specs["msrp"] = None
        return specs
    return {k: None for k in SPECS_FIELDS}


def main(argv: list[str]) -> int:
    payload, source = read_input(argv)
    etype, emsg = classify_error(payload)
    if etype:
        emit({"ok": False, "error_type": etype, "error": emsg, "source": source})
        return 0

    specs = extract_specs(payload)

    critical = ["year", "make", "model", "trim"]
    missing = [k for k in critical if specs.get(k) in (None, "")]
    if missing:
        emit({
            "ok": False,
            "error_type": "missing_specs",
            "error": f"VIN decode missing required fields: {missing}",
            "specs": specs,
            "source": source,
        })
        return 0

    # Pull VIN from original payload if present
    vin = None
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), dict):
            vin = payload["data"].get("vin") or payload.get("vin")
        vin = vin or payload.get("vin")

    emit({
        "ok": True,
        "vin": vin,
        "specs": specs,
        "source": source,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
