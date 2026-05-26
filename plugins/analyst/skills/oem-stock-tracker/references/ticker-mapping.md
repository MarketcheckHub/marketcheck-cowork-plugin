---
name: ticker-mapping
description: 13-row map from US-listed automotive OEM tickers to canonical company name + makes list. Plus the 8-row dealer-group ticker redirect list. Read by resolve_oem.py.
type: reference
---

# OEM ticker mapping

The 14 publicly-traded automotive OEMs tracked by this skill, plus the 8 dealer-group tickers that this skill REDIRECTS to `dealer-group-health-monitor`.

`resolve_oem.py` resolves user input in three tiers: exact ticker match → reverse make-name lookup → fuzzy `difflib.SequenceMatcher` ≥0.5. If input matches a dealer-group ticker, it returns `error_type=dealer_group_redirect`. If no candidate ≥0.5, it returns `error_type=no_candidates` and SKILL.md's recovery branch fires a facet-discovery call to confirm a brand-orphan match.

## OEM tickers — full table

| Ticker | Company name | Makes | Classification |
|---|---|---|---|
| `F`     | Ford Motor Company        | Ford, Lincoln                                                | legacy    |
| `GM`    | General Motors            | Chevrolet, GMC, Buick, Cadillac                              | legacy    |
| `TM`    | Toyota Motor Corporation  | Toyota, Lexus                                                | legacy    |
| `HMC`   | Honda Motor Company       | Honda, Acura                                                 | legacy    |
| `STLA`  | Stellantis                | Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati       | legacy    |
| `TSLA`  | Tesla                     | Tesla                                                        | pure_play |
| `RIVN`  | Rivian Automotive         | Rivian                                                       | pure_play |
| `LCID`  | Lucid Motors              | Lucid                                                        | pure_play |
| `PSNY`  | Polestar Automotive Holding UK PLC | Polestar                                            | pure_play |
| `HYMTF` | Hyundai Motor Company     | Hyundai, Kia, Genesis                                        | legacy    |
| `NSANY` | Nissan Motor Company      | Nissan, Infiniti                                             | legacy    |
| `MBGAF` | Mercedes-Benz Group       | Mercedes-Benz                                                | legacy    |
| `BMWYY` | BMW Group                 | BMW, MINI, Rolls-Royce                                       | legacy    |
| `VWAGY` | Volkswagen AG             | Volkswagen, Audi, Porsche, Lamborghini, Bentley              | legacy    |

## Dealer-group tickers — redirect list

These tickers are NOT analyzed by this skill. `resolve_oem.py` returns `error_type=dealer_group_redirect` for any match; SKILL.md halts with: *"`<TICKER>` is a dealer-group stock; route to `dealer-group-health-monitor`."*

| Ticker | Group |
|---|---|
| `AN`   | AutoNation             |
| `LAD`  | Lithia Motors          |
| `PAG`  | Penske Automotive      |
| `SAH`  | Sonic Automotive       |
| `GPI`  | Group 1 Automotive     |
| `ABG`  | Asbury Automotive      |
| `KMX`  | CarMax                 |
| `CVNA` | Carvana                |

## Machine-readable forms

`resolve_oem.py` parses the two tables below. Format: one mapping per line, separated by ` → ` (space, U+2192 RIGHT ARROW, space). Tickers are uppercase; company names and makes preserve case; makes are comma-separated.

### OEM map

```
F → Ford Motor Company → Ford,Lincoln → legacy
GM → General Motors → Chevrolet,GMC,Buick,Cadillac → legacy
TM → Toyota Motor Corporation → Toyota,Lexus → legacy
HMC → Honda Motor Company → Honda,Acura → legacy
STLA → Stellantis → Chrysler,Dodge,Jeep,Ram,Fiat,Alfa Romeo,Maserati → legacy
TSLA → Tesla → Tesla → pure_play
RIVN → Rivian Automotive → Rivian → pure_play
LCID → Lucid Motors → Lucid → pure_play
PSNY → Polestar Automotive Holding UK PLC → Polestar → pure_play
HYMTF → Hyundai Motor Company → Hyundai,Kia,Genesis → legacy
NSANY → Nissan Motor Company → Nissan,Infiniti → legacy
MBGAF → Mercedes-Benz Group → Mercedes-Benz → legacy
BMWYY → BMW Group → BMW,MINI,Rolls-Royce → legacy
VWAGY → Volkswagen AG → Volkswagen,Audi,Porsche,Lamborghini,Bentley → legacy
```

### Dealer-group redirect list

```
AN
LAD
PAG
SAH
GPI
ABG
KMX
CVNA
```

## Reverse lookup (make → ticker)

For W3 (market-share leaderboard) and brand-orphan disambiguation, the reverse lookup matters. Each make in the OEM map maps to exactly one ticker (no make appears under two OEMs). Examples:
- `Ford` → `F`
- `Lincoln` → `F`
- `Chevrolet` → `GM`
- `Cadillac` → `GM`
- `Toyota` → `TM`
- `Lexus` → `TM`
- `Audi` → `VWAGY`
- `Porsche` → `VWAGY`
- `MINI` → `BMWYY`
- `Rolls-Royce` → `BMWYY`
- `Genesis` → `HYMTF`
- `Infiniti` → `NSANY`

If a make does NOT appear in any OEM row (e.g., `Subaru`, `Mazda`, `Volvo`, `Mitsubishi`), the reverse lookup returns null. `resolve_oem.py` will then fall through to fuzzy matching (which will also miss for genuinely-unmapped brands), then emit `error_type=no_candidates` — triggering SKILL.md's brand-orphan recovery branch.

## Quirks / gotchas

- **`MBGAF` company name**: "Mercedes-Benz Group" (not "Mercedes-Benz AG", not "Daimler"). The single make is `Mercedes-Benz` (hyphenated).
- **`STLA` 7 makes**: Stellantis has the most makes in the map. Wave A1 for STLA = 16 calls; Wave A2 = 14 calls; total = 30 calls. Slowest legacy ticker.
- **Pure-play classification** (TSLA / RIVN / LCID): EV slice per-make is SKIPPED for these; substituted with one EV-market-leaders call. See `oem-classification.md`.
- **`MINI` and `MINI Cooper`**: the canonical make name in the MarketCheck enum is `MINI`. Don't include `Cooper` in the makes list.
- **`Rolls-Royce`**: hyphenated, both words capitalized.
- **`Alfa Romeo`**: space-separated, both words capitalized.
- **`Genesis`**: distinct from Hyundai's Genesis Coupe (the model). `Genesis` here is the brand (formerly Hyundai luxury sub-brand, now standalone make).
- **The 14-row OEM map covers the major US-listed automotive OEMs as of 2026-05.** Polestar (`PSNY`, NASDAQ since 2022) was added as pure_play. Other EV ADRs not yet in scope: Nio `NIO`, XPeng `XPEV`, Li Auto `LI`, VinFast `VFS`. Adding them is a follow-up task requiring only this file + `oem-classification.md`.

## Source of truth for canonical names

The make strings must match the MarketCheck `make` field values exactly (the `get_sold_summary` API echoes `make` per row, and we use those values for reverse lookup in W3). Empirically verified during plan preparation (March 2025 sold data) for: Ford, Chevrolet, Toyota, Honda, Tesla, BMW, Mercedes-Benz, Audi, Volkswagen.

If a future MCP server update changes a make's canonical name (e.g., `Mercedes-Benz` → `Mercedes`), update this file in lockstep with `oem-classification.md` and re-run the test suite.
