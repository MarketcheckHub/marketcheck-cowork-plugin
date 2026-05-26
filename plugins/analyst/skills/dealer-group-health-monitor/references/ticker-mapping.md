---
name: ticker-mapping
description: 8-row map from US stock tickers to canonical dealership_group_name enum values. Used by resolve_group_name.py for ticker-symbol resolution and reverse-lookup (canonical → ticker).
type: reference
---

# Ticker → canonical dealership_group_name

The 8 publicly-traded US automotive retailers tracked by this skill. Each ticker maps to its **exact** canonical name in `dealership_group_enum.md` (verified character-for-character — including trailing periods, case, and the `Carmax` single-token quirk).

| Ticker | Canonical name | Notes |
|---|---|---|
| `AN`   | `AutoNation Inc.`              | trailing period |
| `LAD`  | `Lithia Motors Inc.`           | trailing period |
| `PAG`  | `Penske Automotive Group Inc.` | trailing period |
| `SAH`  | `Sonic Automotive Inc.`        | trailing period |
| `GPI`  | `Group 1 Automotive Inc.`      | leading digit + trailing period |
| `ABG`  | `Asbury Automotive Group`      | **no** trailing period (unlike siblings) |
| `KMX`  | `Carmax`                       | single token, NOT "CarMax" |
| `CVNA` | `Carvana`                      | — |

## Machine-readable form

`resolve_group_name.py` reads the table below (one mapping per line, `TICKER → canonical`):

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

The arrow separator is the literal three characters ` → ` (space, U+2192 RIGHT ARROW, space). The script splits on this separator. Tickers are uppercase; canonical names preserve the enum's exact casing.

## Reverse lookup

For W3 (top-N leaderboard), the renderer needs to display ticker symbols next to canonical names that appear in the leaderboard. A canonical name not in this 8-entry map renders without a ticker (the skill is only authoritative on these 8 public-traded names; the other 463 enum entries are private dealer groups).
