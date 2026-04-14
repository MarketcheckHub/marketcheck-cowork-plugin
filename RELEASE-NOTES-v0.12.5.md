# Release Notes — v0.12.5

**Date:** 2026-04-14
**Scope:** All 9 plugins (analyst, dealer, dealership-group, manufacturer, lender, appraiser, insurer, auction-house, lender-sales)

## Summary

Fix silent data truncation bug in `get_sold_summary` API calls across all skills, agents, and commands. This release adds explicit `limit`, `inventory_type`, and `ranking_dimensions` parameters to every `get_sold_summary` call specification to prevent silent result truncation and empty responses.

## Root Cause

A user QC check on a CarMax (KMX) pre-earnings report revealed the `get_sold_summary` tool returned **70,540** sold vehicles instead of the expected **~138,000** — a 49% undercount. Investigation traced the issue to three dangerous silent defaults in the backend API:

1. **`limit` defaults to 1000** — each response row is a (month x state x ranking_dimension_combo) tuple. A 3-month, 42-state, 15-make query produces ~2,025 rows, but only 1,000 are returned. The remaining ~1,025 rows (containing ~68,000 vehicle sales) are silently dropped.

2. **`inventory_type` defaults to "New"** — used-car dealers (CarMax, Carvana) return **zero results** when `inventory_type` is omitted, with no error message.

3. **`ranking_dimensions` defaults to "make,model,body_type"** — creates ~150,000 rows for national 3-month queries, making `limit=1000` catastrophically insufficient.

## Diagnostic Evidence

| Test | Parameters | Rows | Total Sold |
|------|-----------|------|-----------|
| Reproduce bug | `ranking_dimensions=make, top_n=15, limit=1000 (default)` | **1,000 (limit hit)** | **70,661** |
| Fix limit | `ranking_dimensions=make, top_n=50, limit=5000` | 3,813 | 138,112 |
| Minimal grouping | `ranking_dimensions=dealership_group_name, limit=5000` | 126 | **138,448** |
| Omit inventory_type | No `inventory_type` param | 0 | **0 (empty!)** |

Remaining gap between API (138,448) and Looker export (163,845) explained by scope differences: Looker Look #566 includes Canada (`country IN ('CA','US')`) and extends 10 extra days through March 10 vs the API's Feb 28 cutoff.

## Changes

### All Skills (~70 SKILL.md files)
- Added `get_sold_summary` parameter safety callout block after date anchor
- Added explicit `limit: 5000` to every `get_sold_summary` call specification
- Added explicit `inventory_type` (`New` or `Used`) to calls that were missing it
- Noted KMX/CVNA as used-only groups requiring `inventory_type: Used`

### All Agents (~25 agent .md files)
- Added parameter safety callout block
- Added explicit `limit: 5000` and `inventory_type` to all call specifications

### Key Skill Fixes (analyst plugin)
- **earnings-preview**: Added dealer-group-aware volume workflow (Step 1b) with dedicated `ranking_dimensions: dealership_group_name` call for accurate totals; separate make-breakdown call; explicit inventory_type handling for used-only groups (KMX, CVNA)
- **dealer-group-health-monitor**: Split volume into Step 2a (dedicated target group call) and Step 2b (peer ranking); explicit `limit: 5000` and `inventory_type` on all calls
- **market-share-analyzer**: Added `limit: 5000` to all 4 workflow call specs; explicit `inventory_type` guidance
- **group-benchmarking / group-dashboard**: Added `limit: 5000` and `inventory_type: Used` with KMX/CVNA notes
- **public-group-scorecard**: Added parameter safety to cohort agent spawn prompt
- **oem-stock-tracker**: Added `limit: 5000` and explicit `inventory_type` to Steps 2-8

### Best Practices (added to every file)
```
> get_sold_summary parameter safety:
> - Always set inventory_type explicitly (New or Used) — omitting defaults to New, zero results for Used queries
> - Always set limit: 5000 — default 1000 silently truncates multi-dimensional results
> - For volume totals, use ranking_dimensions: dealership_group_name (minimal rows)
> - Use separate calls for totals vs breakdowns
```

### Version Bumps
All 9 plugin.json files bumped from v0.12.3 to v0.12.5.

## Ranking Dimensions Cardinality Reference

| `ranking_dimensions` | Unique combos (CarMax) | x42 states x3 months | Fits limit=1000? |
|---|---|---|---|
| `dealership_group_name` | 1 | ~126 | Yes |
| `make` | ~40 | ~5,040 | No |
| `make,body_type` | ~200 | ~25,200 | No |
| `make,model,body_type` (DEFAULT) | ~1,000+ | ~126,000 | No (catastrophic) |

## Backend Recommendation (not in this release)

The backend API at `mc-api.marketcheck.com/api/v1/sold-vehicles/summary` should add `total_rows_available` to response metadata so callers can detect when truncation has occurred.
