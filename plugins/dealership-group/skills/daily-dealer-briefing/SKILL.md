---
name: daily-dealer-briefing
description: >
  This skill should be used when the user asks for a "daily briefing",
  "morning check", "what needs attention today", "daily pricing check",
  "what's urgent on my lot", "daily dealer report", "start my day",
  "morning report", "daily ops", or needs a quick operational health check
  covering aging inventory and competitor price movements.
---

# Daily Dealer Briefing — Morning Operational Health Check

A 5-minute morning briefing that surfaces the two things a dealer needs to act on immediately: **aging inventory bleeding floor plan** and **competitors who just dropped their prices**.

**Architecture:** This skill uses the `lot-scanner` agent (with pagination) to pull aging inventory, and the `lot-pricer` agent to price them — while competitor scanning runs in parallel inline.

## Dealer Group Profile (Load First)

Load the `marketcheck-profile.md` project memory file. If missing, prompt `/onboarding` and stop.

**Extract ALL locations from `dealer_group.locations[]`.** For each location record: `name`, `dealer_id`, `dealer_type`, `franchise_brands`, `zip` (US) or `postcode` (UK), `state` (US) or `region` (UK), `web_domain`, `country`. Extract group-level preferences: `aging_threshold` (default 60), `floor_plan_cost_per_day` (default $35), `default_radius_miles`.

**Location scope:** If a specific location name is provided, match to `locations[].name` and run for that location only. If "all" or no argument, iterate through EVERY location — all execution steps below run for each location using **that location's own** `dealer_id`, `zip`/`postcode`, `state`/`region`, `dealer_type`, and `franchise_brands`. Never reuse one location's zip or state for a different location.

**Inventory type:** Read `preferences.default_inventory_type` from profile (`"used"` | `"new"` | `"both"`; default `"used"` if not set). Apply as `car_type` in all lot-scanner and search calls. If the user specifies a different type in their request, override the profile default. Never mix new and used data in the same report section.

**Tool routing per location:** US: `lot-scanner` + `lot-pricer` + `search_active_cars`. UK: `lot-scanner` only (comp median inline). Confirm: "Running daily briefing for: [location name(s)] | Inventory: [used/new/both]"

## Group Rollup Section (appended after all per-location briefings)

```
GROUP DAILY ROLLUP — [Group Name] ([N] locations)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Location         | Aged Units | Competitor Alerts | Floor Plan Burn | Top Action
-----------------|-----------|------------------|-----------------|----------
[Location 1]     | XX        | X                | $XXX/day        | [action]
[Location 2]     | XX        | X                | $XXX/day        | [action]
...

GROUP TOTAL: XX aged units | $X,XXX/day floor plan burn

TOP 3 GROUP-LEVEL ACTIONS:
1. [Highest-impact action across all locations]
2. [Second]
3. [Third]
```

## Execution: Multi-Agent Orchestration

### Wave 1 — Launch Simultaneously

Launch the `lot-scanner` agent AND start the competitor scan at the same time.

**Agent A: `lot-scanner` (aging filter)**

Use the Agent tool to spawn the `dealership-group:lot-scanner` agent with this prompt:

> Pull aging inventory for dealer_id=[dealer_id], country=[country], car_type=used, sort_by=dom, sort_order=desc, dom_range=[aging_threshold]-999. Paginate through all results. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, DOM.

**Inline: Competitor Price Drop Scan** (runs while lot-scanner works)

While waiting for the lot-scanner agent, run the competitor scan directly:

**US dealers:**

For each brand in `franchise_brands` (or top 3 makes from the location's brand mix if independent):

Call `mcp__marketcheck__search_active_cars` with:
- `make`: the brand
- `zip`: location's ZIP
- `radius`: from preferences
- `price_change`: `negative`
- `sort_by`: `price`
- `sort_order`: `asc`
- `rows`: `10`
- `car_type`: `used`
- `seller_type`: `dealer`

→ **Extract only**: per listing — price, price_change, dealer_name, make, model, DOM. Discard full response.

From results:
- Group by dealer — dealers with 3+ drops signal inventory pressure
- Flag **UNDERCUT** alerts: competitor units now priced below the location's equivalent

**UK dealers:**

Call `mcp__marketcheck__search_uk_active_cars` with similar filters. If `price_change` is not supported, skip and note: "Competitor price tracking not available for UK market."

### Wave 2 — After Lot Scanner Completes

Once `lot-scanner` returns the aging units:

**Agent B: `lot-pricer`** (US only)

Use the Agent tool to spawn the `dealership-group:lot-pricer` agent with this prompt:

> Price these aging vehicles: [pass the vehicle list from lot-scanner, up to top 15 by DOM]. zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold].

**UK dealers**: Instead of lot-pricer, price each aged unit inline by searching 10 comparable listings and calculating comp median.

### Assembly — Combine Results

Combine lot-pricer output + competitor scan results into the daily briefing.

## Output

Present: briefing headline with date and location, aging inventory table (VIN, YMMT, DOM, price, market price, gap), competitor alert table (model, dealer, price, gap), floor plan burn total, and top 3 actionable recommendations with dollar impact. If all clear, state so with inventory health summary.
