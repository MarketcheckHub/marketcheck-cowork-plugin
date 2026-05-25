---
name: oem-classification
description: OEM classification (pure_play / legacy / brand_orphan) and the data-driven EV-detection rule. Determines whether the EV-slice probe fires per-make (legacy) or substitutes an EV-market-leaders block (pure-play), and how the brand-orphan path is handled.
type: reference
---

# OEM classification

Three classifications drive W1's call-shape branching. Two are returned by `resolve_oem.py`; the third is constructed inline by SKILL.md after the brand-orphan recovery branch.

## `pure_play` — EV-only OEMs (4 tickers)

```
TSLA → Tesla
RIVN → Rivian Automotive
LCID → Lucid Motors
PSNY → Polestar Automotive Holding UK PLC
```

For pure-play tickers:
- The per-make sold call IS the EV slice (their entire volume is EV by definition).
- The **per-make EV probe call is SKIPPED** in Wave A1 — it would return the same data as the sold call (redundant) and waste a call.
- An **EV market leaders** substitute call fires in Wave A1: `get_sold_summary(fuel_type_category="EV", ranking_dimensions="make", top_n=10, date_from=<prior_month.date_from>, date_to=<current_month.date_to>)` — gives a top-10 EV-maker leaderboard for context.
- The output template renders an **EV Market Leaders mini-leaderboard** (TSLA's rank vs Ford EV, Chevy Bolt, etc.) INSTEAD of the EV Transition block.
- DQ event (k) is logged: "EV slice skipped for pure-play; EV market leaders substituted."

## `legacy` — multi-fuel OEMs (10 tickers)

```
F, GM, TM, HMC, STLA, HYMTF, NSANY, MBGAF, BMWYY, VWAGY
```

For legacy tickers:
- The per-make sold call returns total volume (all fuel types).
- The **per-make EV slice probe** fires in Wave A1 for EACH make: `get_sold_summary(make=<make>, fuel_type_category="EV", ranking_dimensions="make", top_n=1, M=4)`.
- If ALL probe responses for the ticker's makes return `sold_count = 0` across all months → the EV block is OMITTED from output, DQ event (k) logged: "Legacy OEM has zero EV volume; EV block omitted."
- Otherwise the EV block renders as a **transition** view (EV % of total volume, EV ASP, EV DOM, per-make EV breakdown, transition narrative note).

## `brand_orphan` — unmapped brands (constructed by SKILL.md)

When `resolve_oem.py` returns `error_type=no_candidates` (user typed a brand not in the 13-row OEM map and not within fuzzy threshold), SKILL.md fires a facet-discovery recovery call (`search_active_cars` with `facets="make|0|100"`), presents 3-5 closest brand-name matches to the user, and on user confirmation constructs the workflow context inline:

```json
{
  "classification": "brand_orphan",
  "ticker": null,
  "company_name": "<user-confirmed brand name>",
  "makes": ["<same brand name>"]
}
```

For brand-orphan:
- Treated **like legacy with N=1** for call shape — the EV slice probe fires.
- If the EV probe returns zero, EV block omitted (DQ event (k)).
- `per_make_raw` is NULL in output (N=1 means no per-make breakdown to render).
- Output template renders identity line WITHOUT a ticker (no parenthetical):
  ```
  Analyzing **<brand>** — brand_orphan
  ```
  versus the OEM ticker case:
  ```
  Analyzing **F** (Ford Motor Company): Ford, Lincoln — legacy
  ```
- DQ event (j) logged: "Brand-orphan path taken — `<brand>` resolved via active-market facets, no parent OEM ticker."

## Why pure-play and brand-orphan get different treatment

Pure-play tickers (TSLA / RIVN / LCID) are 100% EV by definition — running an EV slice on Tesla returns Tesla's full volume, which we already have. Substituting with an EV-market-leaders call provides actually-useful information (where TSLA sits vs other EV makers).

Brand-orphan tickers might be EV-heavy (e.g., a future Polestar handling), EV-light (e.g., Mazda has minimal EV volume), or mixed. The data-driven probe is the right approach — let the response decide whether the EV block renders or omits.

## EV-detection rule (resolves AMB-12)

For legacy and brand_orphan classifications, run the per-make EV slice probe. After parsing:

```python
ev_total_volume = sum(
    ticker.per_make[make].ev_slice.current.sold_count
    for make in ticker.makes
    if ticker.per_make[make].ev_slice is not None
)

if ev_total_volume == 0:
    # All makes returned zero EV volume.
    ev_block.shape = "omitted"
    dq_events.append("(k) EV slice returned zero across all makes; EV block omitted.")
else:
    ev_block.shape = "transition"
    # ... render transition block with per-make breakdown
```

For pure-play, skip the probe entirely:

```python
if classification == "pure_play":
    # Don't fire the per-make EV slice call. Fire the EV market leaders substitute instead.
    ev_block.shape = "market_leaders"
    dq_events.append("(k) EV slice skipped for pure-play; EV market leaders substituted.")
```

## Source of truth

This file is the single source of truth for `pure_play_tickers` and (implicitly) `legacy_tickers` (= OEM map − pure_play_tickers). `resolve_oem.py` reads this file via the `--classification-file` flag (default: this file's path).

If a future ticker is reclassified (e.g., RIVN becomes "diversified" because they start selling ICE delivery vans), update this file and re-run the test suite.

## Machine-readable form

`resolve_oem.py` reads the pure-play list from this file. Format: one ticker per line, no whitespace.

```
TSLA
RIVN
LCID
PSNY
```

All other tickers in `ticker-mapping.md`'s OEM map default to `legacy`.
