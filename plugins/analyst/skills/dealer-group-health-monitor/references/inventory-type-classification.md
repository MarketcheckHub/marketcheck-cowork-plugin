---
name: inventory-type-classification
description: Static classification of dealer groups as Used-only, New-only, or Both (used + new). Drives whether downstream sold-summary calls fire 1× (single channel) or 2× (both channels).
type: reference
---

# Inventory-type classification

Most dealer groups (462 of 471 in the enum) sell both new and used vehicles. Two short exception lists override the default. The skill's `resolve_group_name.py` looks up the resolved canonical name against these lists; anything not on either list is classified `Both`.

## Used-only (7)

These groups operate as used-vehicle retailers exclusively. Sold-summary calls with `inventory_type=New` will return zero or near-zero rows for them — silently — which is the failure mode the original `dealer-group-health-monitor` got bitten by (AMB-03 in the original SKILL_ANALYSIS).

```
Carmax
Americas Car-mart, Inc.
Springs Automotive Group Platte Ave
Central TX Autos
Right Drive
Alsop Auto Group
Stewart Management Group Inc.
```

## New-only (2)

These groups sell almost exclusively new inventory (rare; most franchise groups have meaningful used volume too). Sold-summary calls with `inventory_type=Used` return near-zero rows.

```
Ed Bozarth Inc.
Herb Chambers Cos.
```

## Default: Both

Every other canonical name in `dealership_group_enum.md` (462 names) is classified `Both`. This covers all of the publicly-traded franchise groups (`AN`, `LAD`, `PAG`, `SAH`, `GPI`, `ABG`) plus the bulk of private dealer groups.

## How this drives call shapes

In W1 / W2, the classification determines `primary_channel` and (for Both groups) `secondary_channel`:

| Classification | primary_channel | secondary_channel | Wave A `get_sold_summary` calls per group |
|---|---|---|---|
| Used-only | Used | — | 2 (current month + prior month) |
| New-only | New  | — | 2 (current month + prior month) |
| Both     | Used | New | 4 (current+prior × Used+New) |

W3 ignores classification — it issues a single peer-leaderboard call with the user's chosen `inventory_type` (default Used) and aggregates per-group across the response.

## Worked example — Both group (resolves AMB-07)

User asks: *"How is AutoNation doing?"*

1. `resolve_group_name.py` resolves `AutoNation` → canonical `AutoNation Inc.`, ticker `AN`, classification **`Both`**.
2. W1 Wave A fires 7 parallel calls:
   - `get_sold_summary` × 4: target sold for primary (Used) current+prior, secondary (New) current+prior.
   - `get_sold_summary` × 1: peer leaderboard, primary (Used).
   - `search_active_cars` × 2: target active for `car_type=used` and `car_type=new`.
3. `compute_group_stats.py` sees both channels populated and computes:
   - `headline.sold_count_total = current.used.sold_count + current.new.sold_count` (combined).
   - Weighted ASP and DOM weight by per-channel sold_count across both channels.
   - `active_health.used` and `active_health.new` populated separately for the inventory-health block.

## Worked example — Used-only group

User asks: *"CarMax volume signal"*

1. `resolve_group_name.py` resolves `CarMax` (case-insensitive fuzzy) → canonical `Carmax`, ticker `KMX`, classification **`Used-only`**.
2. W1 Wave A fires 4 parallel calls:
   - `get_sold_summary` × 2: target sold for Used (primary) current + prior month.
   - `get_sold_summary` × 1: peer leaderboard, Used.
   - `search_active_cars` × 1: target active for `car_type=used`.
3. `compute_group_stats.py` sees `current_month.new = null`, `prior_month.new = null`, `active.new = null`. Headline `sold_count_total` = `current.used.sold_count` directly. Inventory-health rendering skips the New row entirely.
