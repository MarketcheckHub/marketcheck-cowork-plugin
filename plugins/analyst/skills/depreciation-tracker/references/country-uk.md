---
name: country-uk
description: US-only routing rule. The four depreciation workflows all depend on `get_sold_summary` which has no UK variant; halt before any MCP call when the profile country is not US.
type: reference
---

# UK routing — halt-only

The depreciation-tracker skill is **US-only**. Every workflow (W1 curve,
W2 segment trends, W3 brand residual, W5 MSRP parity) depends on
`get_sold_summary`, which has no UK equivalent in the MarketCheck MCP
server (`mcp_server_tool_docs/get_sold_summary.md` confirms: "US market
only. No UK variant.").

The UK MCP surface (`search_uk_active_cars` + `search_uk_recent_cars`)
does not expose sold-transaction aggregates — only per-listing data for
active and expired listings over a 90-day window. Without aggregated
sold-count + average-sale-price by month / segment / make, none of the
depreciation workflows can produce an honest investment signal.

## Halt message

When `profile.location.country != "US"`, halt before any MCP call:

> *"Depreciation tracking requires `get_sold_summary` which is US-only.
> The UK MarketCheck surface (`search_uk_active_cars` +
> `search_uk_recent_cars`) does not expose sold-transaction aggregates
> required for residual / depreciation investment signals. Canadian and
> other non-US markets have no MarketCheck sold-summary endpoint at all.
> Re-visit when MarketCheck ships non-US sold data."*

## Why no UK adaptation here

Other workflows in the broader plugin suite that operate on per-listing
data (active or recently-sold cars) can substitute `search_uk_*` for the
US-only tools, because per-listing data exists on the UK MCP surface.
Depreciation has no such substitute path — every workflow here depends on
aggregated sold-vehicle rollups, which the UK surface does not provide:

- W1 curve needs **multi-period aggregated sold prices** — `search_uk_recent_cars` has at most 90 days of expired-listing data, not the 12-month trajectory W1 draws. And expired listings are not realised sales — they are just listings that left the active index (sold OR withdrawn OR transferred).
- W2 segment trends need **body_type-level aggregations across periods** — `search_uk_*` returns per-listing rows; client-side aggregation over a 90-day rolling window is shape-incompatible with the multi-month fixed-window cuts the workflow renders.
- W3 brand residual needs **make-level retention computed over 6-month intervals** — same period-incompatibility as W2.
- W5 MSRP parity needs `price_over_msrp_percentage` rollups — only emitted by `get_sold_summary`, not by any UK tool.

## Future re-evaluation

If MarketCheck ships a UK sold-summary endpoint
(`get_uk_sold_summary` or `search_uk_recent_cars` with a `summary_by`
parameter), this file should be replaced with workflow-specific UK
adaptations. Until then, the halt message above is the entire non-US
behavior.
