---
description: Quick DMA market overview — supply, demand, pricing, and top sellers for any state.
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__get_sold_summary"]
argument-hint: [state code, e.g. TX]
---

Quick market snapshot for a state or DMA (~2 minutes).

## Step 0: Parse input

Use $ARGUMENTS as state code. If not provided, use primary state from profile. If no profile, ask "Which state?"

## Step 1: Get supply snapshot

Call `mcp__marketcheck__search_active_cars` with `state`, `car_type=used`, `seller_type=dealer`, `facets=body_type|0|15|1,make|0|20|1`, `stats=price,dom,miles`, `rows=0`.

## Step 2: Get demand data

Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=10`, prior month dates.

## Step 3: Get top models

Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=10`, prior month dates.

## Step 4: Deliver snapshot

Format:
```
MARKET SNAPSHOT: [State] — Used Vehicles
════════════════════════════════════════

HEADLINE
  Active Supply:     [count]
  Sold (30d):        [count]
  Turnover Ratio:    [ratio]x
  Median Price:      $[price]
  Avg DOM:           [days]

SUPPLY BY SEGMENT
[Table: Segment, Count, %]

TOP 10 MODELS (by sales volume)
[Table: Rank, Model, Sold, Avg Price, Avg DOM]

DEMAND:SUPPLY SIGNALS
[Top under-supplied + over-supplied segments]

AUCTION OPPORTUNITY: [1-sentence summary]
```
