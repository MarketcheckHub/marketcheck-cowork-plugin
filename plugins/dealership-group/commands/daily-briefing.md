---
description: Morning operational health check — aging inventory alerts + competitor price drops, per-location and group rollup (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [location name or "all"]
---

Run the daily dealer briefing using parallel sub-agents for faster turnaround. This command triggers the `daily-dealer-briefing` skill. Supports per-location briefing or group rollup across all locations.

## Step 1: Verify dealer group profile

Read `~/.claude/marketcheck/dealership-group-profile.json`.

- If **missing**: "No dealer group profile found. Run `/onboarding` first." Then stop.
- If **exists**: Extract `dealer_group.group_name`, `dealer_group.locations[]`, and `preferences`.

## Step 2: Determine scope

Check $ARGUMENTS:

- If a location name is provided: match it to `locations[].name` and use that location
- If "all" or empty: ask "Run daily briefing for which location? Or 'all' for group rollup?"
  - If specific location: use that location's dealer_id, zip, state, dealer_type
  - If 'all': run for EACH location, then append GROUP ROLLUP

For the selected location(s), extract: `dealer_id`, `name`, `dealer_type`, `franchise_brands`, `zip`/`postcode`, `state`/`region`, `country`.

- If `dealer_id` is null for a location: note "Location [name] has no dealer ID — skipping. Run `/onboarding` to update." Skip that location.

Confirm: "Running daily briefing for **[location name or group name (all)]**..."

## Step 3: Per-location briefing — Wave 1

For each location being briefed:

**Agent A: `lot-scanner` (aging filter)**

Spawn `dealership-group:lot-scanner` with prompt:
> Pull aging inventory for dealer_id=[dealer_id], country=[country], car_type=used, sort_by=dom, sort_order=desc, dom_range=[aging_threshold]-999. Paginate through all results. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, DOM.

**Inline: Competitor Price Drop Scan** (run while lot-scanner works)

**US:** For each brand in the location's `franchise_brands`, call `mcp__marketcheck__search_active_cars` with `make`, `zip`, `radius`, `price_change=negative`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used`, `seller_type=dealer`. Group drops by dealer. Flag UNDERCUT alerts.

**UK:** Call `mcp__marketcheck__search_uk_active_cars` with similar filters. If `price_change` not supported, skip and note.

## Step 4: Per-location briefing — Wave 2

After `lot-scanner` returns:

**Agent B: `lot-pricer`** (US only)

Spawn `dealership-group:lot-pricer` with prompt:
> Price these aging vehicles: [top 15 by DOM from lot-scanner]. zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold].

**UK:** Price inline using comp medians from `search_uk_active_cars`.

## Step 5: Assemble per-location report

```
DAILY DEALER BRIEFING — [Location Name] — [Today's Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AGING INVENTORY ([N] units over [threshold] days)
[Table: VIN | Year Make Model | DOM | Your Price | Market Price | Gap | Action]
Floor Plan Burn: ~$[X,XXX] total ($[X]/day ongoing)

COMPETITOR ALERTS ([N] price drops in your market)
[Table: Model | Competitor | Their Price | Your Price | Gap | Their DOM]

TOP 3 ACTIONS TODAY:
1-3. [Actions with $ estimates]

Estimated impact: $[X,XXX] in floor plan savings + $[X,XXX] in margin recovery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If all clear: "No units over [threshold]-day threshold. No competitor price drops detected."

## Step 6: Group rollup (if "all" locations)

After all per-location briefings complete, append:

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
