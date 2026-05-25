---
name: inventory-type-classification
description: Classification of each tracked ticker by inventory dynamics. Dealer-group tickers fall into Used-only / New-only / Both (per the source `dealer-group-health-monitor` taxonomy). OEM tickers fall into legacy / pure_play. Drives whether downstream calls fire 1× per channel or 2×, and whether the EV slice and Mix dimensions apply.
type: reference
---

# Inventory-type / entity classification

Five classes total drive the W1 wave-call shape:

| Entity type | Class | Meaning | Tracked tickers in this skill |
|---|---|---|---|
| dealer-group | `Used-only` | Almost-zero New rows; query Used only | KMX |
| dealer-group | `New-only` | Almost-zero Used rows; query New only | (none of the 8 tracked) |
| dealer-group | `Both` | Both channels meaningful | AN, LAD, PAG, SAH, GPI, ABG, **CVNA** |
| OEM | `legacy` | Multi-fuel; EV slice via `fuel_type_category="EV"` returns a subset | F, GM, TM, HMC, STLA, HYMTF, NSANY, MBGAF, BMWYY, VWAGY |
| OEM | `pure_play` | 100 % electrified; EV slice is redundant (total volume IS EV) | TSLA, RIVN, LCID |

`resolve_ticker.py` returns the resolved class on every successful lookup. Anything outside these 21 tickers halts (no `brand_orphan` recovery path — see §"What this skill does NOT do" in SKILL.md).

**Resolver-readable headings.** The dealer-group class headings below are at H2 with `Used-only` / `New-only` substring tokens — `resolve_ticker.py` consumes the fenced code blocks following those headings (substring match, case-insensitive). The OEM class is NOT read from this file — it comes from the 4th column of `references/ticker-mapping.md`'s OEM table.

## Used-only

These dealer groups operate as used-vehicle retailers exclusively. `get_sold_summary(inventory_type="New", dealership_group_name=…)` returns zero or near-zero rows — silently. This is the failure mode the predecessor `earnings-preview` skill reproduced when it omitted `inventory_type` from EV-slice calls.

Tracked tickers — Used-only (1):
```
KMX
```

Canonical name: `Carmax` (single-token, lowercase-x).

For `Used-only`: skip Mix dimension entirely (100 % Used by definition); skip New-side sold calls; skip New-side active calls.

## New-only

These dealer groups sell almost exclusively new inventory (rare for dealer groups; the source lists two private examples — `Ed Bozarth Inc.` and `Herb Chambers Cos.`). `get_sold_summary(inventory_type="Used", dealership_group_name=…)` returns near-zero rows.

Tracked tickers — New-only (0):
```
```

(No tracked ticker is currently New-only. The empty fenced block above preserves the resolver-parser contract for a future v1.1 extension.)

For `New-only`: skip Mix dimension entirely; skip Used-side sold calls; skip Used-side active calls.

## Both — default for dealer-groups

Default for any dealer-group canonical name not in either fenced block above. The resolver applies this default — no fenced block is required for the parser. Tracked tickers — `Both` (7):

```
AN
LAD
PAG
SAH
GPI
ABG
CVNA
```

(The fenced block here is documentation only — the resolver does not read it. Names not in the `Used-only` or `New-only` blocks default to `Both` in code.)

For `Both`: query both channels; Mix dimension applies (new % = `new_sold / (new_sold + used_sold) × 100`); EV slice fires on New (per franchise convention) — see §"How classification drives W1 call shape" below.

### CVNA — empirical caveat

CVNA (Carvana) is classified `Both` per the source taxonomy, but its New share is operationally ~0.4 % of total. Verified live 2026-05-13:

| Channel | National `sold_count`, April 2026 |
|---|---:|
| `inventory_type="New"` | ~194 units across 15 states (premium / luxury resale classified as new; ASPs $38K–$92K) |
| `inventory_type="Used"` | ~50,000+ units across 35+ states (the actual Carvana business) |

The skill defers to source: CVNA → `Both` → wave structure mirrors AN/LAD/etc.'s 5-call pattern (instead of KMX's 3-call pattern). The Mix dimension renders ~99.6 % Used (informative, not noise). The EV slice fires on New per the `Both` rule and will likely surface DQ event (i) "low-volume" — that's honest: Carvana's electrified signal really does live on the Used side, but v1 keeps the rule simple. A future v1.1 may add a per-ticker EV-channel override.

## pure_play OEMs

For pure-play OEM tickers, the per-make sold call IS the EV signal (their entire volume is electrified). The per-make EV slice probe is **skipped** in Wave A1 — it would re-query the same data.

Tracked tickers — `pure_play` (3):

```
TSLA
RIVN
LCID
```

(This fenced block is documentation only — the resolver reads `pure_play` from the 4th column of `references/ticker-mapping.md`'s OEM table. Synced manually with that file.)

For `pure_play`: EV slice skipped; Mix dimension still applies (TSLA has a meaningful used market via direct CPO; RIVN/LCID used markets are nascent — DQ event (i) may fire on Mix for those).

## legacy OEMs — default

Default for any OEM ticker not in the `pure_play` list above. Tracked tickers — `legacy` (10): `F, GM, TM, HMC, STLA, HYMTF, NSANY, MBGAF, BMWYY, VWAGY`.

For `legacy`: per-make sold returns total volume; per-make EV slice probes fire (one call per make in `makes[]` × `fuel_type_category="EV"`). If ALL probe responses for the ticker's makes return `sold_count = 0` → EV block omitted with DQ event (k).

## Why `brand_orphan` is omitted

Both reference skills (`oem-stock-tracker/references/oem-classification.md:40-64` and `dealer-group-health-monitor/SKILL.md:25-33`) implement a brand-orphan recovery path via `search_active_cars` facet-discovery for unknown inputs. This skill **deliberately does not** — the 21-ticker map is fixed; unknown input halts with: *"`<X>` is not one of the 21 tracked tickers — add via `references/ticker-mapping.md` if you want to extend coverage."*

If a future v1.1 expands ticker coverage, `parse_search.py --mode facets` is already byte-identical-reused from the OEM tracker and would just need a SKILL.md recovery branch added. The classification machinery here already supports adding entries — append a ticker symbol to the relevant fenced block above.

## How classification drives W1 call shape

The full per-class wave structure is enumerated in `references/w1-channel-check.md`. Summary view:

Wave A1 sold + EV are split into TWO calls per channel (Call A: year-ago 3 mo; Call B: prior→mrcm ≤8 mo) to stay under the upstream 12-month date-range cap.

| Ticker class | Wave A1 sold calls | Wave A1 EV slice | Wave A2 active | Total calls |
|---|---|---|---|---|
| Used-only dealer-group (KMX) | 2 (Used × A/B) | 2 (EV-Used × A/B) | 1 (Used) | **5** |
| Both dealer-group (AN, LAD, PAG, SAH, GPI, ABG, CVNA) | 4 (New × A/B + Used × A/B) | 2 (EV-New × A/B per franchise rule) | 2 (New + Used) | **8** |
| New-only dealer-group (none current) | 2 (New × A/B) | 2 (EV-New × A/B) | 1 (New) | **5** |
| legacy OEM, N makes | 4N (New × A/B + Used × A/B per make) | 2N (EV × A/B per make) | 2N (New + Used per make) | **8N** |
| pure_play OEM, N makes | 4N (New × A/B + Used × A/B per make) | 0 (skipped — volume IS EV) | 2N (New + Used per make) | **6N** |

Worst case: STLA (legacy, 7 makes) = **56 calls**. Wave A1 sub-batched at ≤5 concurrent per the runtime concurrency-cap rule in SKILL.md §Parallelization.

## Worked examples

### Used-only path (KMX)

User asks: *"CarMax earnings preview"*

1. `resolve_ticker.py` resolves `CarMax` → `KMX` → entity_type `dealer_group`, canonical `Carmax`, classification `Used-only`.
2. Wave A1 fires 4 calls (2 dimensions × 2 splits):
   - `get_sold_summary(dealership_group_name="Carmax", inventory_type="Used", date_from=year_ago_q.date_from, date_to=year_ago_q.date_to)` — Call A
   - `get_sold_summary(..., date_from=prior_q.date_from, date_to=max(current_q.date_to, mrcm.date_to))` — Call B
   - Same A/B pair for the EV slice with `fuel_type_category="EV"`.
3. Wave A2 fires 1 call: `search_active_cars(mc_dealership_group_name="Carmax", car_type="used", stats="price,dom", rows=0, price_range="1-*", …)`.
4. `compute_earnings_signals.py` computes Volume QoQ + YoY, Pricing (ASP-substitute since MSRP gap is undefined for used), Days Supply (Used only), DOM, EV share — 5 slots. Mix is skipped (`null`).
5. `aggregate_signals.py` reduces over 5 non-null slots.

### Both path (AN)

User asks: *"AutoNation earnings preview"*

1. `resolve_ticker.py` resolves `AutoNation` → `AN` → entity_type `dealer_group`, canonical `AutoNation Inc.`, classification `Both`.
2. Wave A1 fires 6 calls (3 dimensions × 2 splits): New-sold A/B + Used-sold A/B + EV-slice A/B (on New, per the `Both` franchise rule).
3. Wave A2 fires 2 calls in parallel: New-active + Used-active.
4. `compute_earnings_signals.py` computes Volume QoQ + YoY (combined channels), Pricing (`price_over_msrp_percentage` Δ bps, banded), Days Supply New + Used (two slots), DOM, EV share, Mix — up to 7 slots.

### Both path with empirical caveat (CVNA)

User asks: *"Carvana pre-earnings check"*

1. Wave structure identical to AN above (5 calls).
2. New-side data is real but small (~0.4 % of total per 2026-05-13 anchor). Mix renders ~99.6 % Used. EV slice on New likely fires DQ event (i) low-volume. Days Supply New: small `num_found` paired with small monthly `sold_count` — ratio may be unstable; rendered with the (i) annotation.
3. The verdict reducer treats null / low-volume slots per the standard degrade rule — Mix still contributes (a high-Used mix is itself a signal), EV may be null and skipped.

### legacy OEM path (F, N=2 makes)

User asks: *"What will Ford report?"*

1. `resolve_ticker.py` resolves `F` → entity_type `oem`, makes `[Ford, Lincoln]`, classification `legacy`.
2. Wave A1 fires 12 calls (2 makes × 3 dimensions × 2 splits: New-sold A/B, Used-sold A/B, EV-slice A/B per make).
3. Wave A2 fires 4 calls (2 per make: New-active, Used-active).
4. Total 10 — single wave fine for F.
5. Per-make rollup combines Ford + Lincoln via sold-count-weighted means (see `oem-stock-tracker/references/multi-make-aggregation.md` for the math).

### pure_play OEM path (TSLA, N=1)

User asks: *"Tesla heading into earnings"*

1. `resolve_ticker.py` resolves `TSLA` → entity_type `oem`, makes `[Tesla]`, classification `pure_play`.
2. Wave A1 fires 4 calls (1 make × 2 channels × 2 splits): New-sold A/B + Used-sold A/B. **EV slice is SKIPPED** (Tesla's volume is EV by definition).
3. Wave A2 fires 2 calls: New-active + Used-active.
4. Total 6 calls.
5. EV block in output template renders as "Pure-play — entire volume is electrified" (no `delta_bps`; informational only).

## Resolver-parser contract

`resolve_ticker.py` reads this file at startup via the `--classification-file` flag (default `references/inventory-type-classification.md`). It scans **every H2 heading** for substring tokens (case-insensitive):

- `Used-only` / `Used only` → consume the next fenced code block; one ticker per line goes to dealer-group class `Used-only`
- `New-only` / `New only` → same for class `New-only`
- Any other H2 (e.g., `## Both — default`, `## pure_play OEMs`, `## How classification drives W1 call shape`, `## Worked examples`) → ignored by the dealer-group classifier

OEM `legacy` / `pure_play` classification is **NOT read from this file** — it comes from the 4th column of `references/ticker-mapping.md`'s OEM table. The `pure_play` fenced block above is documentation only; sync manually with the ticker-mapping file when updating.

Tickers not found in any classification block default to:
- `Both` if entity_type is `dealer_group` (lookup via ticker-mapping)
- `legacy` if entity_type is `oem` AND the 4th column says `legacy`

If a future MCP server update changes a group's actual inventory dynamics (e.g., Carmax launches a new-car arm), update this file and re-run the test suite.
