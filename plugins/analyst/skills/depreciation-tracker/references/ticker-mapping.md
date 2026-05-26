---
name: ticker-mapping
description: 13-OEM ticker ↔ make map used by every workflow to translate per-make findings into per-ticker investment signals. Mirrors the analyst plugin's onboarding and the `oem-stock-tracker` skill.
type: reference
---

# OEM ticker ↔ make mapping

Every workflow in this skill surfaces findings at the `make` level (W1
narrows to a specific make + model; W2 surfaces segment + fuel cohorts;
W3 ranks brands; W5 ranks make + model parity). The Ticker Impact Summary
in the output template translates per-make findings into per-ticker
investment signals using the table below.

This is the same mapping prompted by `plugins/analyst/commands/onboarding.md`
and used by `oem-stock-tracker`. Keep them in lockstep.

## OEM tickers (13)

| Ticker | Makes covered |
|---|---|
| **F**     | Ford, Lincoln |
| **GM**    | Chevrolet, GMC, Buick, Cadillac |
| **TM**    | Toyota, Lexus |
| **HMC**   | Honda, Acura |
| **STLA**  | Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati |
| **TSLA**  | Tesla |
| **RIVN**  | Rivian |
| **LCID**  | Lucid |
| **HYMTF** | Hyundai, Kia, Genesis |
| **NSANY** | Nissan, Infiniti |
| **MBGAF** | Mercedes-Benz |
| **BMWYY** | BMW, MINI, Rolls-Royce |
| **VWAGY** | Volkswagen, Audi, Porsche, Lamborghini, Bentley |

## Reverse map (make → ticker)

| Make | Ticker | Make | Ticker | Make | Ticker |
|---|---|---|---|---|---|
| Acura | HMC | Alfa Romeo | STLA | Audi | VWAGY |
| Bentley | VWAGY | BMW | BMWYY | Buick | GM |
| Cadillac | GM | Chevrolet | GM | Chrysler | STLA |
| Dodge | STLA | Fiat | STLA | Ford | F |
| Genesis | HYMTF | GMC | GM | Honda | HMC |
| Hyundai | HYMTF | Infiniti | NSANY | Jeep | STLA |
| Kia | HYMTF | Lamborghini | VWAGY | Lexus | TM |
| Lincoln | F | Lucid | LCID | Maserati | STLA |
| Mercedes-Benz | MBGAF | MINI | BMWYY | Nissan | NSANY |
| Porsche | VWAGY | Ram | STLA | Rivian | RIVN |
| Rolls-Royce | BMWYY | Tesla | TSLA | Toyota | TM |
| Volkswagen | VWAGY | | | | |

## Casing and normalisation

- `get_sold_summary` returns makes in the casing it has indexed (typically
  title-case: `"Toyota"`, `"Mercedes-Benz"`).
- Hyphens, spaces, and punctuation must match exactly — `"Mercedes-Benz"` not
  `"Mercedes Benz"`, `"Alfa Romeo"` with the space, `"Rolls-Royce"` with the
  hyphen.
- Lookup is case-sensitive within `aggregate_signals.py`. The script first
  attempts an exact match, then a `strip().title()` retry. On miss, the
  make is bucketed under `[no tracked ticker]` and emits DQ event (d).

## Coverage gaps (deliberate)

Some makes that `get_sold_summary` indexes are NOT in the ticker table:

- **Subaru** — listed at FUJHY (foreign-listed ADR thinly traded; not on
  analyst plugin's default tracked-tickers list per onboarding).
- **Mazda** — listed at MZDAY (same reason).
- **Volvo** — Volvo Cars (VLVLY) and Volvo Group (VLVLY) trade separately;
  intentionally omitted to avoid ambiguity.
- **Polestar** — PSNY (US-listed); intentionally omitted at v1.0.0 —
  consider adding in a future revision if depreciation analysis for
  EV-specific newcomers becomes a regular ask.

A make's absence from the table is NOT an error — the renderer bucket it as
`[no tracked ticker]` and the workflow continues. If the user explicitly
asks about an unmapped make (e.g., "Subaru depreciation"), the skill still
renders the underlying data — only the ticker overlay is omitted.

## Per-ticker rollup rule

When a ticker covers multiple makes (e.g., STLA → 7 makes), the Ticker
Impact Summary aggregates by:

1. Collecting per-make / per-row bands for every make in the ticker's
   `makes covered` list.
2. Running the headline-verdict reducer (per `references/signal-aggregation.md`
   §Headline-verdict reduction) over the collected bands.
3. The per-ticker verdict is the reduced output, NOT a simple "any-BEARISH
   wins" or "most-common band" — this preserves the same determinism
   guarantee at the ticker level that the per-metric reducer provides at
   the workflow level.

Example: STLA with 4 BULLISH (Jeep, Ram, Dodge, Chrysler) + 1 BEARISH (Alfa
Romeo) + 2 NEUTRAL (Fiat, Maserati) → n_bullish = 4, n_bearish = 1 → MIXED
(rule 1 wins, not BULLISH despite the +0.86 mean).

## Drift discipline

If the analyst plugin's onboarding mapping changes (a ticker is added or a
make is reassigned), this file must update in lockstep, along with:
- `oem-stock-tracker/references/ticker-mapping.md` (if present)
- `plugins/analyst/commands/onboarding.md` (the prompt the user sees)
