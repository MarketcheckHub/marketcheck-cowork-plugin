---
name: country-uk
description: US-only halt-and-redirect message used when the loaded profile has `location.country != "US"`. Market-share investment signals depend on `get_sold_summary`, which has no UK or CA equivalent.
type: reference
---

# Country routing — US-only halt

This skill is **US-only**. Every workflow depends on `get_sold_summary`,
which has no UK or CA equivalent (per `mcp_server_tool_docs/get_sold_summary.md`
line 202 — *"US market only. No UK variant."*). The analyst plugin's
onboarding command stores `location.country = "US"` unconditionally
(`plugins/analyst/commands/onboarding.md` Step 2), so a non-US profile
landing in this skill is an unexpected state — either an in-progress
edit, a stale profile from a different plugin, or a manual override.

Either way: halt before issuing any MCP call and emit the user-facing
message below.

## Halt message — UK profile

> *Market-share investment-signal analysis requires US sold-transaction
> data and is not available for the UK market. The MarketCheck UK toolset
> (`search_uk_active_cars`, `search_uk_recent_cars`) does not expose
> make/model rollup, dealer-group rankings, fuel-type-category
> penetration aggregates, or per-state regional distribution — all of
> which the five workflows in this skill require.*
>
> *For UK competitive intelligence in a live-listing snapshot form, use
> `search_uk_active_cars` directly with `facets=` parameters (e.g.
> `facets="make|0|20|1,model|0|50|1"`); the resulting facet counts proxy
> for active-inventory mix but cannot substitute for sold-volume share.*
>
> *Analyst-plugin onboarding sets `country = "US"` unconditionally — if
> you see this message and you intended a US run, re-run
> `/onboarding` to refresh the profile.*

## Halt message — CA profile

> *Market-share investment-signal analysis is US-only — Canada has no
> `get_sold_summary` data surface. Re-visit when `get_ca_sold_summary`
> ships upstream.*

## Halt message — any other country

> *Market-share investment-signal analysis requires US sold-transaction
> data and is only available for the US market. Loaded profile has
> `location.country = "<COUNTRY>"`. If you intended a US run, re-run
> `/onboarding` to refresh the profile.*

## Why no fallback

The five workflows (Brand Market Share, Segment Conquest, Dealer Group
Benchmarking, EV Penetration, Regional Exposure Heatmap) all require:

- **Sold-volume aggregates** by make / model / body_type / dealership
  group / state — only `get_sold_summary` exposes these.
- **Period comparison** (current vs prior, MoM / QoQ bps shifts) — only
  sold-summary supports the `date_from` / `date_to` window.
- **Fuel-type-category rollup** (EV / Hybrid / ICE) — only sold-summary's
  `fuel_type_category` filter delivers this cleanly.
- **Dealer-group enum** (471-entry hard-coded list, US-only).

Active-listing UK searches (`search_uk_active_cars`) return inventory
snapshots, not sold-volume aggregates, and have no period-comparison
surface. They cannot substitute. Re-visit if a future
`get_uk_sold_summary` or `get_ca_sold_summary` ships.

## Halt-and-redirect script-side

The skill's "Before you start" step compares the loaded profile's
`location.country` against `"US"` immediately after `Read` of
`marketcheck-profile.md`. Non-US → emit the relevant halt message above
**before any MCP call**. No `parse_sold_summary` is invoked; no scratch
files are written. The user sees the halt message and exits cleanly.
