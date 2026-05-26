---
name: ticker-mapping
description: 21-ticker authoritative map — 13 publicly-traded automotive OEMs (with company name, makes, legacy/pure_play classification) + 8 publicly-traded dealer-group / auto-retail companies (with canonical `dealership_group_name` enum string). Read by `resolve_ticker.py`. The 4th column on OEM rows provides the legacy/pure_play classification; dealer-group `Used-only`/`New-only`/`Both` classification comes from `inventory-type-classification.md`.
type: reference
---

# Ticker map — 21 tracked tickers

The 13 US-listed automotive OEMs + the 8 US-listed dealer-group / auto-retail companies this skill produces pre-earnings verdicts for.

`resolve_ticker.py` resolves user input in three tiers: exact ticker match → reverse make / company / canonical-name lookup → fuzzy via `difflib.SequenceMatcher` ≥0.5. Below threshold → `error_type=no_candidates` → SKILL.md halts with *"not one of the 21 tracked tickers"* message. There is **NO brand-orphan recovery branch** (per design — see `references/inventory-type-classification.md §"Why brand_orphan is omitted"`).

## OEM tickers (13)

| Ticker | Company | Makes | Classification |
|---|---|---|---|
| `F`     | Ford Motor Company        | Ford, Lincoln                                          | legacy    |
| `GM`    | General Motors            | Chevrolet, GMC, Buick, Cadillac                        | legacy    |
| `TM`    | Toyota Motor Corporation  | Toyota, Lexus                                          | legacy    |
| `HMC`   | Honda Motor Company       | Honda, Acura                                           | legacy    |
| `STLA`  | Stellantis                | Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati | legacy    |
| `TSLA`  | Tesla                     | Tesla                                                  | pure_play |
| `RIVN`  | Rivian Automotive         | Rivian                                                 | pure_play |
| `LCID`  | Lucid Motors              | Lucid                                                  | pure_play |
| `HYMTF` | Hyundai Motor Company     | Hyundai, Kia, Genesis                                  | legacy    |
| `NSANY` | Nissan Motor Company      | Nissan, Infiniti                                       | legacy    |
| `MBGAF` | Mercedes-Benz Group       | Mercedes-Benz                                          | legacy    |
| `BMWYY` | BMW Group                 | BMW, MINI, Rolls-Royce                                 | legacy    |
| `VWAGY` | Volkswagen AG             | Volkswagen, Audi, Porsche, Lamborghini, Bentley        | legacy    |

PSNY (Polestar, NASDAQ since 2022) is tracked by `oem-stock-tracker` but **NOT** by this skill — preserved as a v1.1 candidate. Other EV ADRs (`NIO`, `XPEV`, `LI`, `VFS`) also out of scope for v1.

## Dealer-group tickers (8)

| Ticker | Canonical name (matches `dealership_group_name` enum exactly) | Classification | Notes |
|---|---|---|---|
| `AN`   | `AutoNation Inc.`              | Both       | trailing period |
| `LAD`  | `Lithia Motors Inc.`           | Both       | trailing period |
| `PAG`  | `Penske Automotive Group Inc.` | Both       | trailing period |
| `SAH`  | `Sonic Automotive Inc.`        | Both       | trailing period |
| `GPI`  | `Group 1 Automotive Inc.`      | Both       | leading digit + trailing period |
| `ABG`  | `Asbury Automotive Group`      | Both       | **no** trailing period (the franchise exception) |
| `KMX`  | `Carmax`                       | Used-only  | single token, NOT `CarMax` |
| `CVNA` | `Carvana`                      | Both       | New share ~0.4% of total per 2026-05-13 anchor — but classified `Both` per source |

## Machine-readable forms

`resolve_ticker.py` parses the two fenced code blocks below. Each row uses ` → ` (space, U+2192 RIGHT ARROW, space) as the separator. Tickers are uppercase; canonical names preserve the enum's exact casing.

### OEM map

Format per line: `TICKER → Company Name → Make1,Make2,… → classification`

```
F → Ford Motor Company → Ford,Lincoln → legacy
GM → General Motors → Chevrolet,GMC,Buick,Cadillac → legacy
TM → Toyota Motor Corporation → Toyota,Lexus → legacy
HMC → Honda Motor Company → Honda,Acura → legacy
STLA → Stellantis → Chrysler,Dodge,Jeep,Ram,Fiat,Alfa Romeo,Maserati → legacy
TSLA → Tesla → Tesla → pure_play
RIVN → Rivian Automotive → Rivian → pure_play
LCID → Lucid Motors → Lucid → pure_play
HYMTF → Hyundai Motor Company → Hyundai,Kia,Genesis → legacy
NSANY → Nissan Motor Company → Nissan,Infiniti → legacy
MBGAF → Mercedes-Benz Group → Mercedes-Benz → legacy
BMWYY → BMW Group → BMW,MINI,Rolls-Royce → legacy
VWAGY → Volkswagen AG → Volkswagen,Audi,Porsche,Lamborghini,Bentley → legacy
```

### Dealer-group map

Format per line: `TICKER → canonical_name` (2 columns; matches the `dealership_group_name` enum verbatim).

Note: this is a **2-column** format, distinct from `oem-stock-tracker/references/ticker-mapping.md §"Dealer-group redirect list"` which is a 1-column ticker-only list. This skill resolves dealer-group tickers (rather than redirecting them) and needs the canonical name at resolution time. Dealer-group classification (`Used-only` / `New-only` / `Both`) is NOT in this block — it comes from `inventory-type-classification.md`.

```
AN → AutoNation Inc.
LAD → Lithia Motors Inc.
PAG → Penske Automotive Group Inc.
SAH → Sonic Automotive Inc.
GPI → Group 1 Automotive Inc.
ABG → Asbury Automotive Group
KMX → Carmax
CVNA → Carvana
```

## Reverse lookup (make → ticker, canonical → ticker)

Each OEM make maps to exactly one ticker (no make appears in two OEMs):

| Make | Ticker | | Make | Ticker |
|---|---|---|---|---|
| Ford / Lincoln | `F` | | Toyota / Lexus | `TM` |
| Chevrolet / GMC / Buick / Cadillac | `GM` | | Honda / Acura | `HMC` |
| Chrysler / Dodge / Jeep / Ram / Fiat / Alfa Romeo / Maserati | `STLA` | | Tesla | `TSLA` |
| Rivian | `RIVN` | | Lucid | `LCID` |
| Hyundai / Kia / Genesis | `HYMTF` | | Nissan / Infiniti | `NSANY` |
| Mercedes-Benz | `MBGAF` | | BMW / MINI / Rolls-Royce | `BMWYY` |
| Volkswagen / Audi / Porsche / Lamborghini / Bentley | `VWAGY` | | | |

Each dealer-group canonical → unique ticker (8 entries above).

If a make does NOT appear (e.g., `Subaru`, `Mazda`, `Volvo`, `Mitsubishi`, `Polestar`), `resolve_ticker.py` falls through to fuzzy matching against the OEM map; below the 0.5 threshold it emits `error_type=no_candidates` and SKILL.md halts.

## Quirks / gotchas

- **`KMX`** canonical is `Carmax` (single token, lowercase-x, NOT `CarMax`). The 471-entry source enum (`mcp_server_tool_docs/get_sold_summary.md:73`) has this token form; case-sensitive.
- **`AN`, `LAD`, `PAG`, `SAH`, `GPI`** canonical names have a trailing period (`AutoNation Inc.`, etc.).
- **`ABG`** is the trailing-period exception: `Asbury Automotive Group` (no period).
- **`CVNA`, `KMX`** canonicals have no `Inc.` / `Corp.` suffix.
- **`STLA`** carries 7 makes — the most of any tracked OEM. Wave A1 for STLA = 21 calls (legacy × 7 makes × 3 calls each: New-sold, Used-sold, EV-slice). Wave A2 = 14 calls. Total 35. Wave A1+A2 split required per the runtime concurrency-cap rule in SKILL.md §Parallelization.
- **`MBGAF`** company name is `Mercedes-Benz Group` (not `Mercedes-Benz AG`, not `Daimler`). The single make is `Mercedes-Benz` (hyphenated).
- **`MINI`** canonical make is `MINI` (not `Mini` and not `MINI Cooper`).
- **`Rolls-Royce`** is hyphenated; both words capitalized.
- **`Alfa Romeo`** is space-separated; both words capitalized.
- **`Genesis`** is the standalone Hyundai-luxury sub-brand make (distinct from the older Hyundai Genesis Coupe model).
- **`TM`, `HMC`** fiscal year is April–March (Toyota Q1 FY = April–June = calendar Q2). Months align with calendar quarters; only the LABEL differs from management's reporting nomenclature. No special handling needed in v1.
- **`KMX`** fiscal year is March–February — the **only** tracked ticker whose fiscal months actually diverge from calendar months. SKILL.md surfaces a KMX-specific caveat in the confirmation header for this reason. Per-ticker fiscal-quarter override is a v1.1 candidate.
- **`CVNA`** new-vehicle share is operationally ~0.4% of total (verified 2026-05-13: ~194 units national in April 2026 vs. ~50,000+ Used). Classification per source is `Both`, so wave structure runs the New side anyway; Mix dimension renders ~99.6% Used (informative, not noise); EV slice on New likely fires DQ event (i) low-volume.

## Source of truth

The 8 dealer-group canonical strings must match the MarketCheck `dealership_group_name` enum exactly. Authoritative source: `mcp_server_tool_docs/get_sold_summary.md:73` and `dealer-group-health-monitor/references/dealership_group_enum.md` (471 entries; this skill bundles only the 8 publicly-traded names).

The 13 OEM makes must match the MarketCheck `make` field values exactly (the `get_sold_summary` API echoes `make` per row, and `resolve_ticker.py` uses those values for reverse lookup). Empirically verified during oem-stock-tracker plan preparation (March 2025 sold data) for: Ford, Chevrolet, Toyota, Honda, Tesla, BMW, Mercedes-Benz, Audi, Volkswagen.

If a future MCP server update changes a canonical name, a make's canonical name, or adds a new tracked ticker, update this file in lockstep with `inventory-type-classification.md` and re-run the test suite.
