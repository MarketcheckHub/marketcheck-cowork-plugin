---
description: Quick market demand snapshot for a state or region
allowed-tools: ["mcp__marketcheck__get_sold_summary", "mcp__marketcheck__search_active_cars"]
argument-hint: [state-code, e.g. "TX" or "CA"]
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

Quick market demand snapshot -- what's selling, what's sitting, where the opportunities are.

## Step 1: Parse input

2-letter state code -> use directly. State name -> convert to code. Empty -> check `dealer-profile.json` for `location.state`, else ask.

## Step 2: Pull demand data

`get_sold_summary`: `state`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=15`, `date_from`/`date_to` = previous month.

## Step 3: Pull segment data

`get_sold_summary`: same state, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, same date range.

## Step 4: Pull supply data

`search_active_cars`: `state`, `facets=body_type|0|20|1,make|0|30|2`, `rows=0`.

## Step 5: Present snapshot

Show: top selling models table (make/model, sold count, avg price, avg DOM), segment demand vs supply table (body type, sold, avg price, active supply, demand/supply ratio), hot opportunities (D/S > 1.5), oversupplied warnings (D/S < 0.5). End with: "Want to dig deeper into any segment?"
