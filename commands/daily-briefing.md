---
description: Morning operational health check — aging inventory alerts + competitor price drops (multi-agent)
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: []
---

Run the daily dealer briefing using parallel sub-agents for faster turnaround. This command triggers the `daily-dealer-briefing` skill.

## Step 1: Verify dealer profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter.

- If **missing**: "No dealer profile found. Run `/dealer-onboarding` first." Then stop.
- If **exists**: Extract `dealer_id`, `dealer_name`, `dealer_type`, `franchise_brands`, `zip`/`postcode`, `state`/`region`, `country`, `radius`, `aging_threshold`, `floor_plan_cost_per_day`.
- If `dealer_id` is null: "Your profile needs a dealer ID. Run `/dealer-onboarding` to update." Then stop.

**Speed rule — profile-read-once:** Pass the extracted profile fields (dealer_id, source, country, zip/postcode, state/region, radius, aging_threshold, dealer_type, franchise_brands) directly to all sub-agents in their prompt. Sub-agents should NOT re-read the profile.

Confirm: "Running daily briefing for **[dealer_name]**..."

## Step 2: Wave 1 — Lot scanner + competitor scan in parallel

**Agent A: `lot-scanner` (aging filter)**

Spawn `marketcheck-cowork-plugin:lot-scanner` with prompt:
> Pull aging inventory for dealer_id=[dealer_id], country=[country], car_type=used, sort_by=dom, sort_order=desc, dom_range=[aging_threshold]-999. Paginate through all results. Return every vehicle with VIN, year, make, model, trim, listed price, mileage, DOM.

**Inline: Competitor Price Drop Scan** (run while lot-scanner works)

**US:** For each brand in `franchise_brands`, call `mcp__marketcheck__search_active_cars` with `make`, `zip`, `radius`, `price_change=negative`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used`, `seller_type=dealer`. Group drops by dealer. Flag UNDERCUT alerts.

**UK:** Call `mcp__marketcheck__search_uk_active_cars` with similar filters. If `price_change` not supported, skip and note.

## Step 3: Wave 2 — Price aging units

After `lot-scanner` returns:

**Agent B: `lot-pricer`** (US only)

Spawn `marketcheck-cowork-plugin:lot-pricer` with prompt:
> Price these aging vehicles: [top 15 by DOM from lot-scanner]. zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[aging_threshold].

**UK:** Price inline using comp medians from `search_uk_active_cars`.

## Step 4: Assemble report

```
DAILY DEALER BRIEFING — [Dealer Name] — [Today's Date]
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
