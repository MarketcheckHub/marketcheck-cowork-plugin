---
name: daily-dealer-briefing
description: >
  Morning operational health check. Triggers: "daily briefing",
  "morning check", "what needs attention today", "daily pricing check",
  "what's urgent on my lot", "daily dealer report", "start my day",
  "morning report", "daily ops", aging inventory and competitor price movements.
version: 0.1.0
---

# Daily Dealer Briefing — Morning Operational Health Check

A 5-minute morning briefing that surfaces the two things a dealer needs to act on immediately: **aging inventory bleeding floor plan** and **competitors who just dropped their prices**.

**Architecture:** This skill uses the `lot-scanner` agent (with pagination) to pull aging inventory, and the `lot-pricer` agent to price them — while competitor scanning runs in parallel inline.

## Dealer Profile (Load First)

→ Full procedure: read `_references/profile-loading.md`

Parse `marketcheck-profile.md` → extract: `dealer_id` (**required** — if null, tell user to update profile), `dealer_name`, `dealer_type`, `franchise_brands`, `zip`/`postcode`, `state`/`region`, `country`, `radius`, `aging_threshold` (default 60), `floor_plan_per_day` (default $35). If no profile: tell user to run `/onboarding`, stop.

**Country routing:** US = `lot-scanner` + `lot-pricer` agents + `search_active_cars`. UK = `lot-scanner` only (uses `search_uk_active_cars`), no `lot-pricer` (comp median inline), competitor scan via `search_uk_active_cars`. → Full matrix: `_references/country-routing.md`

→ Agent contracts (lot-scanner, lot-pricer): read `_references/agent-contracts.md`

Confirm: "Running daily briefing for **[dealer_name]**, [ZIP/Postcode]..."

## Dealer Group Support

If `user_type` is `dealer_group`:

1. Read `dealer_group.locations[]` from the profile
2. Ask the user: "Run daily briefing for which location? Or 'all' for group rollup?"
   - If a specific location: use that location's dealer_id, zip, state, dealer_type as the context and proceed with the standard daily briefing workflow
   - If 'all': run the standard daily briefing workflow for EACH location sequentially (or in parallel using lot-scanner agents per location), then append a GROUP ROLLUP section at the end

### Group Rollup Section (appended after all per-location briefings)

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

## Gotchas

- **`lot-scanner` may return partial results** — always check `pagination_status` in the agent response. If partial, warn the user that not all inventory was captured.
- **UK: no `lot-pricer` agent and no `market-demand-agent`** — price aged units inline using comp median from `search_uk_active_cars`. If `price_change` param is unsupported for UK, skip competitor price drop scan and note it.
- **`lot-pricer` output is TOON format** — parse the header line for field positions before extracting values.
- **Wave dependency is strict** — `lot-pricer` (Wave 2) cannot start until `lot-scanner` (Wave 1) returns. The competitor scan runs in parallel with Wave 1 (no dependency).
- **Top 15 cap on lot-pricer** — only pass the top 15 aged units (by DOM) to lot-pricer to keep agent response time reasonable.
- **"All clear" case** — if no units exceed the aging threshold AND no competitor price drops are found, output the short "all clear" format rather than empty tables.

## Execution: Multi-Agent Orchestration

### Wave 1 — Launch Simultaneously

Launch the `lot-scanner` agent AND start the competitor scan at the same time.

**Agent A: `lot-scanner` (aging filter)**

Use the Agent tool to spawn the `marketcheck-cowork-plugin:lot-scanner` agent with this prompt:

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

### Validate Wave 1
- [ ] `lot-scanner` returned `pagination_status=complete` — if `partial`, warn user in output
- [ ] Aging units list has `vin`, `dom`, `listed_price` for every row
- [ ] Competitor scan returned results — if empty for all brands, note "No recent competitor price drops detected"

### Wave 2 — After Lot Scanner Completes

Once `lot-scanner` returns the aging units:

**Agent B: `lot-pricer`** (US only)

Use the Agent tool to spawn the `marketcheck-cowork-plugin:lot-pricer` agent with this prompt:

> Price these aging vehicles: [pass the vehicle list from lot-scanner, up to top 15 by DOM]. zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold].

**UK dealers**: Instead of lot-pricer, price each aged unit inline by searching 10 comparable listings and calculating comp median.

### Validate Wave 2
- [ ] `lot-pricer` returned pricing for all passed VINs — if some failed, note count in output
- [ ] No `predicted_price = $0` or null in pricing output
- [ ] Every VIN in pricing output also appears in lot-scanner aging output

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

## Self-Check (before presenting to user)

- [ ] Tables have consistent column counts across all rows
- [ ] No $0 or null prices displayed in any table
- [ ] Date in header matches today's actual date
- [ ] Floor plan burn calculation uses the profile's `floor_plan_per_day`, not a hardcoded default
- [ ] Recommendations cite specific VINs and dollar amounts from the data (not generic advice)
- [ ] If group rollup: all locations are accounted for, group totals sum correctly
