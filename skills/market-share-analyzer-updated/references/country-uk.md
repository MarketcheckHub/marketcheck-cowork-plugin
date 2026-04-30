# UK Workflow Adaptation — Halt Only

This skill is **US-only**. Every workflow depends on `get_sold_summary`, which has no UK equivalent (per `mcp_server_tool_docs/get_sold_summary.md` line 202 — *"US market only. No UK variant."*).

When `profile.location.country == "UK"`, halt with the following user-facing message before any MCP call:

> *Market share analysis requires US sold transaction data and is not available for the UK market. The MarketCheck UK toolset (`search_uk_active_cars`, `search_uk_recent_cars`) does not expose make/model rollup, dealer-group rankings, or fuel-type-category penetration aggregates — all of which this skill needs.*
>
> *For UK competitive intelligence, use `search_uk_active_cars` directly with `facets=` parameters for live-listing market composition (e.g. `facets="make|0|20|1,model|0|50|1"`); the resulting facet counts proxy for "active inventory mix" but cannot substitute for sold-volume share.*

See `_references/country-routing.md` for the broader UK tool matrix.

## Why no fallback

The five workflows (Brand Market Share, Segment Conquest, Dealer Group Benchmarking, EV Adoption, Regional Heatmap) all require:

- **Sold-volume aggregates** by make / model / body_type / dealership_group / state — only `get_sold_summary` exposes these.
- **Period comparison** (current vs prior month, MoM bps shifts) — only sold-summary supports the `date_from` / `date_to` window.
- **Fuel-type-category rollup** (EV / Hybrid / ICE) — only sold-summary's `fuel_type_category` filter delivers this cleanly.

Active-listing UK searches (`search_uk_active_cars`) return inventory snapshots, not sold-volume aggregates, and have no period-comparison surface. They cannot substitute. Re-visit if a future `get_uk_sold_summary` ships.

## Halt-and-redirect script-side

The skill's `Before you start` step runs `country == "UK"` → halt before invoking any MCP. No `parse_sold_summary` is called; no fixtures are emitted. The user sees the halt message and exits cleanly.
