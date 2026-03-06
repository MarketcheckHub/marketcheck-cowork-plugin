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

## Dealer Profile (Load First)

1. Read `~/.claude/marketcheck/dealer-profile.json`.
2. If the file **does not exist**: Tell the user: "No dealer profile found. Run `/onboarding` to set up your dealer context once. The daily briefing needs your dealer ID, ZIP, and preferences to run." Then stop.
3. If the file **exists**, extract:
   - `dealer_id` ← `dealer.dealer_id` (**required** — if null, tell the user to update their profile with a dealer ID)
   - `dealer_name` ← `dealer.name`
   - `dealer_type` ← `dealer.dealer_type`
   - `franchise_brands` ← `dealer.franchise_brands`
   - `zip` or `postcode` ← `location.zip` (US) or `location.postcode` (UK)
   - `state` or `region` ← `location.state` (US) or `location.region` (UK)
   - `country` ← `location.country`
   - `radius` ← `preferences.default_radius_miles`
   - `aging_threshold` ← `preferences.dom_aging_threshold` (default 60)
   - `floor_plan_per_day` ← `preferences.floor_plan_cost_per_day` (default $35)
4. **Tool routing by country:**
   - **US**: `lot-scanner` + `lot-pricer` agents + `search_active_cars` for competitor scan
   - **UK**: `lot-scanner` agent (uses `search_uk_active_cars`). No `lot-pricer` (use comp median inline). Competitor scan via `search_uk_active_cars`.
5. Confirm: "Running daily briefing for **[dealer_name]**, [ZIP/Postcode]..."

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

## Output Format

```
DAILY DEALER BRIEFING — [Dealer Name] — [Today's Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AGING INVENTORY ([N] units over [threshold] days)

VIN (last 6) | Year Make Model | DOM | Your Price | Market Price | Gap | Action
-------------|-----------------|-----|------------|--------------|-----|--------
[table rows sorted by highest DOM first]

Floor Plan Burn (aged units): ~$[X,XXX] total ($[X]/day ongoing)

COMPETITOR ALERTS ([N] price drops in your market)

Model | Competitor Dealer | Their New Price | Your Price | Gap | Their DOM
------|-------------------|-----------------|------------|-----|----------
[table rows, UNDERCUT items highlighted]

Aggressive Competitors: [Dealer X] dropped [N] units — possible inventory pressure

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOP 3 ACTIONS TODAY:
1. [Most impactful action — e.g., "Reduce VIN ...X4532 by $2,100 to match market"]
2. [Second action]
3. [Third action]

Estimated impact: $[X,XXX] in floor plan savings + $[X,XXX] in margin recovery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For a full lot scan + stocking analysis, run /weekly-review
```

If there are **no aging units** and **no competitor drops**, say:

```
DAILY DEALER BRIEFING — [Dealer Name] — [Today's Date]

All clear. No units over [threshold]-day threshold. No competitor price drops detected.

Inventory health: [N] total units | Oldest: [X] days | Market: stable
```
