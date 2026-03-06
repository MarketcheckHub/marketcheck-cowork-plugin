---
description: Quick market demand snapshot for your brand across states or nationally
allowed-tools: ["mcp__marketcheck__get_sold_summary", "mcp__marketcheck__search_active_cars", "Read"]
argument-hint: [state-code, e.g. "TX" or "CA" or "national"]
---

Quick market demand snapshot -- competitive positioning and regional demand signals for your brand.

## Step 0: Load profile

Read `~/.claude/marketcheck/manufacturer-profile.json`. Extract `manufacturer.brands`, `competitor_brands`, `states`. If not found: ask for brands and competitors, suggest `/onboarding`.

## Step 1: Parse input

2-letter state code -> use directly. State name -> convert. "national" -> omit state filter. Empty -> check profile `manufacturer.states` (use first), else ask.

## Step 2: Pull your brand demand data

`get_sold_summary`: `state` (omit for national), `make` = primary brand, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=15`, `date_from`/`date_to` = previous month.

## Step 3: Pull competitive share data

`get_sold_summary`: same state, `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=20`, same date range. Gives market share for all brands.

## Step 4: Pull segment data

`get_sold_summary`: same state, `make` = primary brand, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, same date range. Repeat without `make` for total market.

## Step 5: Pull supply data

`search_active_cars`: same state, `make` = primary brand, `car_type=new`, `facets=body_type|0|20|1,model|0|30|2`, `rows=0`.

## Step 6: Present snapshot

Show: competitive standing table (brand, sold, share %, rank -- highlight your brands with star), your top selling models, segment demand (your brand vs market share, D/S signal: UNDER/BALANCED/OVER), allocation signals (under-supplied D/S > 1.5, over-supplied D/S < 0.8), competitive intelligence (rank, nearest competitor gap, segment with largest competitive gap).

End with: "Try 'competitor analysis', 'EV adoption in [state]', or 'regional demand heatmap'."
