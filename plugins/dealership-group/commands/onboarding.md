---
description: One-time dealer group profile setup — stores group identity, locations (with dealer IDs, ZIPs, brands), and preferences so all skills stop re-asking.
allowed-tools: ["Read", "Write", "AskUserQuestion", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [group name or web domain]
---

Dealer group onboarding for the MarketCheck dealership-group plugin. Collects group identity, location details for each rooftop, and group-level preferences, then persists them to `~/.claude/marketcheck/dealership-group-profile.json`. After onboarding, all plugin skills and commands read this profile automatically.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/dealership-group-profile.json`.

- If **the file exists and is valid JSON**: Show the current profile summary and ask: "A dealer group profile already exists for **[dealer_group.group_name]** ([N] locations). Do you want to update it or keep the current settings?"
  - If keep → stop
  - If update → proceed with current values shown as defaults
- If **does not exist** → proceed to Step 1

## Step 1: Collect group identity

Ask:
- "What is your name?" → `user.name`
- "What company or organization are you with?" (optional) → `user.company`
- "What is your dealer group name?" (e.g., AutoNation, Hendrick Automotive) → `dealer_group.group_name`
- "Is your group publicly traded?" (yes/no)
  - If yes: "What is your stock ticker?" (e.g., AN, LAD) → `dealer_group.ticker`

If $ARGUMENTS contains a value, use it as group name or domain as appropriate.

## Step 2: Collect country

Ask: "Are your locations based in the **US** or **UK**? (or mixed?)"

Accept: US, UK, United States, United Kingdom, America, Britain, England, mixed.

This determines:
- ZIP vs postcode per location
- State vs region per location
- Which MCP tools are available (US has 7 tools; UK has 2)

## Step 3: Add locations (loop)

Loop to collect locations. For each location:

**Step 3a: Location identity**
- "Location name?" (e.g., AutoNation Toyota Dallas) → `location.name`
- "Website domain?" (e.g., autonationtoyotadallas.com) → `location.web_domain`

**Step 3b: Auto-discover dealer_id**

Attempt to find the location's MarketCheck dealer ID using their web domain.

**US locations:**
Call `mcp__marketcheck__search_active_cars` with:
- `dealer_website`: the web domain
- `rows`: 5
- `seller_type`: dealer

**UK locations:**
Call `mcp__marketcheck__search_uk_active_cars` with:
- `dealer_website`: the web domain
- `rows`: 5

**From the results:**
- If listings are returned, extract the `dealer_id` from the first result
- Show the matched dealer name and ask: "Is this your dealership? [Matched Name]"
- If confirmed → store with `dealer_id_source: "auto"`

**If no match by domain:**
- Try searching with the location name via `dealer_name` parameter
- If still no match → inform user: "Could not auto-discover dealer ID for [location name]. You can provide it manually if you know it, or skip for now."
- Store `dealer_id: null` with `dealer_id_source: "unknown"`

**Step 3c: Location details**
- "ZIP code?" (US) or "Postcode?" (UK) → `location.zip` or `location.postcode`
- "State?" (US, 2-letter code) or "Region?" (UK) → `location.state` or `location.region`
- "Franchise or independent?" → `location.dealer_type`
- If franchise: "Which brands does this location sell? (list all)" → `location.franchise_brands`
- If independent: set `location.franchise_brands` to empty array

After each location: "Add another location? (yes/no)"

Minimum 2 locations required for dealer group. If user stops at 1, warn: "Dealer group requires at least 2 locations. Add another?"

## Step 4: Group-level preferences

Present all at once with defaults:

```
Group Preferences (press enter to accept defaults):

- Default search radius: 50 miles
- Target retail margin: 15%
- Average recon cost per unit: $1,500
- Floor plan cost per day: $35
- Max acceptable days on market: 45 days
- Aging inventory threshold: 60 days (units over this are flagged)
```

Also ask:
- "Do any of your locations offer **CPO programs**?" (yes/no)
  - If yes: "Average CPO certification cost per unit?" (default: $1,200)

## Step 5: Write profile

Create the directory `~/.claude/marketcheck/` if it does not exist.

Write the following JSON to `~/.claude/marketcheck/dealership-group-profile.json`:

```json
{
  "schema_version": "1.0",
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]",
  "user": {
    "name": "[from Step 1]",
    "company": "[from Step 1, or null]"
  },
  "dealer_group": {
    "group_name": "[from Step 1]",
    "is_publicly_traded": false,
    "ticker": "[or null]",
    "locations": [
      {
        "name": "[location name]",
        "dealer_id": "[auto-discovered or manual or null]",
        "dealer_id_source": "[auto|manual|unknown]",
        "web_domain": "[domain]",
        "dealer_type": "[franchise|independent]",
        "franchise_brands": ["Brand1", "Brand2"],
        "zip": "[US only]",
        "postcode": "[UK only]",
        "state": "[US only, 2-letter]",
        "region": "[UK only]",
        "country": "[US|UK]",
        "cpo_program": false,
        "cpo_certification_cost": null
      }
    ],
    "default_location_index": 0
  },
  "preferences": {
    "default_radius_miles": 50,
    "target_margin_pct": 15,
    "recon_cost_estimate": 1500,
    "floor_plan_cost_per_day": 35,
    "max_acceptable_dom": 45,
    "dom_aging_threshold": 60
  }
}
```

**Rules:**
- Each location in `locations[]` has its own dealer_id, dealer_type, franchise_brands, and location details.
- Set null for location fields that don't apply (e.g., `zip: null` for UK locations, `postcode: null` for US locations).
- `default_location_index` starts at 0 (first location added).

## Step 6: Confirm and suggest next steps

```
PROFILE SAVED — Dealer Group
━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Group Name] | [N] locations | [Ticker or "private"]

Locations:
  1. [Name] — [City], [State] — [dealer_type] — ID: [dealer_id or "not discovered"]
  2. [Name] — [City], [State] — [dealer_type] — ID: [dealer_id or "not discovered"]
  ...

Preferences:
  Radius: [X] mi | Margin: [X]% | Recon: $[X] | Floor plan: $[X]/day
  Max DOM: [X] days | Aging: [X]+ days

Saved to: ~/.claude/marketcheck/dealership-group-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Group dashboard"              — see all locations at a glance
  "Compare my stores"            — benchmark rooftops against each other
  "Run my daily briefing"        — per-location + group rollup
  "Transfer opportunities"       — find cross-location inventory balance
  "Price check VIN [paste VIN]"  — instant competitive pricing

To update your profile later, run /onboarding again.
```

**For UK-based locations**, append:
```
Note: UK market data includes active listings and recent cars.
Advanced features (ML pricing, sold analytics, VIN history) are US-only.
```
