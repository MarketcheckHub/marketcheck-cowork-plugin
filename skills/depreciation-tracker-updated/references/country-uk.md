# UK Routing — Halt-Only

The depreciation-tracker skill is **US-only**. Every workflow (W1 curve, W2
segment trends, W3 brand residual, W4 geographic variance, W5 MSRP parity)
depends on `get_sold_summary`, which has no UK equivalent in the MarketCheck
MCP server (`mcp_server_tool_docs/get_sold_summary.md` line 202: "US market
only. No UK variant.").

The UK MCP surface (`search_uk_active_cars` + `search_uk_recent_cars`) does
not expose sold-transaction aggregates — it only surfaces per-listing data
for active and expired listings over a 90-day window. Without aggregated
sold-count + average-sale-price by month/segment/region, none of the five
depreciation workflows can produce honest output.

## Halt message

When `profile.location.country == "UK"`, halt before any MCP call:

> *"Depreciation tracking requires `get_sold_summary` which is US-only. The
> UK MarketCheck surface (`search_uk_active_cars` + `search_uk_recent_cars`)
> does not expose sold-transaction aggregates. Re-visit when MarketCheck
> ships UK sold data."*

## Why no UK adaptation here

`competitive-pricer-updated/references/country-uk.md` documents adaptations
for W1 (Price Check), W4 (Market Distribution), and W5 (Competitor Movement)
because those workflows can substitute `search_uk_*` listing data for the
US-only tools. Depreciation has no such substitute path:

- W1 curve needs **multi-period aggregated sold prices** — `search_uk_recent_cars`
  has at most 90 days of expired-listing data, not the 12-month curve W1
  draws. And expired listings are not realised sales — they are just listings
  that left the active index (sold OR withdrawn OR transferred).
- W2 segment trends need **body_type-level aggregations across periods** —
  `search_uk_*` returns per-listing rows; client-side aggregation over a
  90-day rolling window is shape-incompatible with the multi-month
  fixed-window cuts the workflow renders.
- W3 brand residual needs **make-level retention computed over 6-month
  intervals** — same period-incompatibility as W2.
- W4 geographic variance needs **state-level rollups** — UK has no state
  field; the equivalent admin geography (county / region) doesn't have an
  aggregator endpoint.
- W5 MSRP parity needs `price_over_msrp_percentage` rollups — only emitted
  by `get_sold_summary`, not by any UK tool.

## Future re-evaluation

If MarketCheck ships a UK sold-summary endpoint (`get_uk_sold_summary` or
`search_uk_recent_cars` with a `summary_by` parameter), this file should be
replaced with workflow-specific UK adaptations parallel to
`competitive-pricer-updated/references/country-uk.md`. Until then, the halt
message above is the entire UK behavior.

## Test profile

When validating UK behavior, `tests/fixtures/uk/` should hold a UK profile
that exercises the halt message. As of the v1.0.0 release, no live UK
testing has been done — the halt path is verified only via unit tests
(no live-call series).
