---
name: ticker-mapping
description: 13-OEM + 8-dealer-group ticker mapping used by every workflow to translate per-make / per-dealer-group findings into per-ticker investment signals. Mirrors plugins/analyst/commands/onboarding.md Step 4 and is loaded as a constant table inside `scripts/aggregate_signals.py`.
type: reference
---

# Ticker ↔ make / dealer-group mapping

Every workflow in this skill surfaces findings at the `make` level (W1
brand share; W2 per-(make,model) within a segment; W4 brand EV share; W5
per-make regional distribution) or at the `dealership_group_name` level
(W3). The Ticker Impact Summary in the output template translates those
findings into per-ticker BULLISH / BEARISH / NEUTRAL / CAUTION investment
signals using the tables below.

This is the same mapping prompted by `plugins/analyst/commands/onboarding.md`
Step 4 and used by `oem-stock-tracker`,
`dealer-group-health-monitor`, and the ticker constants in
`scripts/aggregate_signals.py`. **Keep all four sources in lockstep when
the mapping changes.**

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

Volume coverage: the 13 OEM tickers above account for ~92-95% of US
new-vehicle sold-summary volume in 2025-2026. Makes that fall outside
this mapping (e.g. Maserati outside STLA's coverage, exotic / niche
imports like Lotus or Ferrari) are listed in the per-make table but
attached to `[no tracked ticker]` and logged as DQ event (d) per
`SKILL.md §Data quality event log`.

## Dealer-group tickers (8)

| Ticker | Dealer-group name (substring match against `dealership_group_name`) |
|---|---|
| **AN**   | AutoNation |
| **LAD**  | Lithia Motors (also "Lithia") |
| **PAG**  | Penske Automotive (also "Penske") |
| **SAH**  | Sonic Automotive (also "Sonic") |
| **GPI**  | Group 1 Automotive (also "Group 1") |
| **ABG**  | Asbury Automotive (also "Asbury") |
| **KMX**  | CarMax |
| **CVNA** | Carvana |

Matching rule (`scripts/aggregate_signals.py:_group_to_ticker`): case-insensitive
substring match against the row's `dealership_group_name`. The
`get_sold_summary` server returns the group_name verbatim from a
hard-coded 471-entry enum — substring match is robust to minor punctuation
variations ("Penske Automotive Group" vs "Penske Auto Group").

KMX and CVNA are **used-vehicle-only** operators; only W3's `inventory_type=
"Used"` call returns rows for them. The franchise dealer-group tickers
(AN, LAD, PAG, SAH, GPI, ABG) sell both new and used — for those, W3 fires
separate `Used` and `New` calls and the renderer surfaces both lines.

## How the per-ticker rollup works

When multiple makes belonging to the same ticker (e.g. Chevy + GMC + Buick
+ Cadillac all roll up to **GM**) end up with different per-make verdicts,
the rollup is sold_count-weighted majority:

- Strict majority (> 50% of ticker's total volume) on `BULLISH` →
  ticker headline is `BULLISH`. Same for `BEARISH` and `NEUTRAL`.
- No strict majority → ticker headline is `CAUTION` (mixed-make
  divergence is itself an investment signal — "GM's Cadillac is gaining
  share fast, but Chevy is losing — directional bet ambiguous").

Full classification grid: `references/signal-aggregation.md`.

## When a make spans more than one ticker

Currently no make appears in two ticker buckets — the table above is a
disjoint partition of the covered US auto-OEM make universe. If a future
spin-off or acquisition creates a multi-ticker make (e.g. if a sub-brand
is carved out), the bookkeeping is handled by adding it to one ticker
only; the make would need to be excluded from the other ticker's bucket
in the same edit.

## Maintenance

When this table changes:
1. Update this file.
2. Update the `OEM_TICKERS` / `DEALER_GROUP_TICKERS` dicts in
   `scripts/aggregate_signals.py`.
3. Update `plugins/analyst/commands/onboarding.md` Step 4.
4. Audit `oem-stock-tracker/references/ticker-mapping.md` and
   `dealer-group-health-monitor/references/ticker-mapping.md`
   for the same change.
