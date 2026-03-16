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

## Profile
Load the `marketcheck-profile.md` project memory file — **required** (if missing, tell user to run `/onboarding` and stop). Extract: dealer_id (required — if null, ask user to update), dealer_name, dealer_type, franchise_brands, zip/postcode, state/region, country, radius, aging_threshold (default 60), floor_plan_per_day (default $35). Also extract: `default_inventory_type` from preferences (`"used"` | `"new"` | `"both"`; default `"used"` if not set). Apply as `car_type` in all lot-scanner and search calls. Override if user explicitly states otherwise. Never mix new and used data in the same report section. **US**: `lot-scanner` + `lot-pricer` agents + `search_active_cars`. **UK**: `lot-scanner` agent only (comp median inline, no `lot-pricer`). Confirm: "Running daily briefing for [dealer_name], [ZIP]..."

## Execution: Multi-Agent Orchestration

### Wave 1 — Launch Simultaneously

Launch the `lot-scanner` agent AND start the competitor scan at the same time.

**Agent A: `lot-scanner` (aging filter)**

Use the Agent tool to spawn the `dealer:lot-scanner` agent with this prompt:

> Pull aging inventory for dealer_id=[dealer_id], country=[country], car_type=used, sort_by=dom, sort_order=desc, dom_range=[aging_threshold]-999. Paginate through all results. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, DOM.

**Inline: Competitor Price Drop Scan** (runs while lot-scanner works)

While waiting for the lot-scanner agent, run the competitor scan directly:

**US dealers:**

For each brand in `franchise_brands` (or top 3 makes from the dealer's brand mix if independent):

Call `mcp__marketcheck__search_active_cars` with:
- `make`: the brand
- `zip`: dealer's ZIP
- `radius`: dealer's radius
- `price_change`: `negative`
- `sort_by`: `price`
- `sort_order`: `asc`
- `rows`: `10`
- `car_type`: `used`
- `seller_type`: `dealer`
→ **Extract only**: per listing — dealer_name, make, model, price, price_change_amount, dom. Discard full response.

From results:
- Group by dealer — dealers with 3+ drops signal inventory pressure
- Flag **UNDERCUT** alerts: competitor units now priced below the dealer's equivalent

**UK dealers:**

Call `mcp__marketcheck__search_uk_active_cars` with similar filters. If `price_change` is not supported, skip and note: "Competitor price tracking not available for UK market."

### Wave 2 — After Lot Scanner Completes

Once `lot-scanner` returns the aging units:

**Agent B: `lot-pricer`** (US only)

Use the Agent tool to spawn the `dealer:lot-pricer` agent with this prompt:

> Price these aging vehicles: [pass the vehicle list from lot-scanner, up to top 15 by DOM]. zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold].

**UK dealers**: Instead of lot-pricer, price each aged unit inline by searching 10 comparable listings and calculating comp median.

### Assembly — Combine Results

Combine lot-pricer output + competitor scan results into the daily briefing.

## Output
Present: briefing header with dealer name and date, aging inventory table (VIN, YMMT, DOM, your price, market price, gap, action) sorted by highest DOM, floor plan burn total, competitor alerts table (model, competitor, their price, your price, gap, DOM) with UNDERCUT highlights, and TOP 3 ACTIONS TODAY with estimated dollar impact. If all clear, state "No aging units or competitor drops" with inventory health summary.
