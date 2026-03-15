---
description: One-time dealer group profile setup — stores group identity, locations (with dealer IDs, ZIPs, brands), and preferences so all skills stop re-asking.
allowed-tools: ["Read", "Write", "AskUserQuestion", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [group name or web domain]
---

Collect group identity, location details for each rooftop, and group-level preferences. Persist to the `marketcheck-profile.md` project memory file.

## Step 0: Check for existing profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter delimiter. If valid JSON: show summary (group name, N locations), ask update or keep. If keep, stop.

## Step 1: Collect group identity

- "What is your name?" -> `user.name`
- "What company?" (optional) -> `user.company`
- "Dealer group name?" -> `dealer_group.group_name`
- "Publicly traded?" If yes: "Stock ticker?" -> `dealer_group.ticker`

Use $ARGUMENTS as group name or domain if provided.

## Step 2: Collect country

Ask: "US, UK, or mixed?" Determines ZIP vs postcode per location, available MCP tools (US=7, UK=2).

## Step 3: Add locations (loop)

For each location:

**3a: Identity** -- name -> `location.name`, web domain -> `location.web_domain`

**3b: Auto-discover dealer_id** -- Search by web domain.
**US:** `search_active_cars` with `dealer_website`, `rows=5`, `seller_type=dealer`. Extract `dealer_id`, confirm.
**UK:** `search_uk_active_cars` with `dealer_website`, `rows=5`.
No match by domain -> try `dealer_name`. Still none -> `dealer_id: null`, `dealer_id_source: "unknown"`.

**3c: Details** -- ZIP/postcode, state/region, franchise/independent, brands (if franchise).

After each: "Add another location?" Minimum 2 locations required.

## Step 4: Group-level preferences

Present with defaults:
- Search radius: 50 mi, margin: 15%, recon: $1,500/unit, floor plan: $35/day
- Max DOM: 45 days, aging threshold: 60 days
- CPO program? If yes: certification cost (default: $1,200)

## Step 5: Write profile

Write to the `marketcheck-profile.md` project memory file with this frontmatter:

```markdown
---
name: marketcheck-profile
description: Full MarketCheck user profile — identity, role, location, preferences. Read by all plugin skills and commands.
type: user
---
```

Then the profile JSON:

```json
{
  "schema_version": "1.0",
  "user_type": "dealer_group",
  "created_at": "[ISO]", "updated_at": "[ISO]",
  "user": { "name": "", "company": null },
  "dealer_group": {
    "group_name": "", "is_publicly_traded": false, "ticker": null,
    "locations": [{
      "name": "", "dealer_id": null, "dealer_id_source": "auto|manual|unknown",
      "web_domain": "", "dealer_type": "franchise|independent",
      "franchise_brands": [], "zip": null, "postcode": null,
      "state": null, "region": null, "country": "US|UK",
      "cpo_program": false, "cpo_certification_cost": null
    }],
    "default_location_index": 0
  },
  "preferences": {
    "default_radius_miles": 50, "target_margin_pct": 15,
    "recon_cost_estimate": 1500, "floor_plan_cost_per_day": 35,
    "max_acceptable_dom": 45, "dom_aging_threshold": 60
  }
}
```

Each location has its own dealer_id, dealer_type, franchise_brands, and location fields. Set null for non-applicable fields.

## Step 6: Sync to session memory

Write a compact profile summary to your auto-memory file (`MEMORY.md`) so all future chat windows automatically know this user. Append or update the `## MarketCheck Profile` section:

```
## MarketCheck Profile: Dealership Group
- **User**: [name] | **Group**: [group_name] | **Ticker**: [ticker or "Private"]
- **Locations** (N): [name1] ([dealer_id], [state]), [name2] ([dealer_id], [state]), ...
- **Country**: [country mix] | **Prefs**: radius=[radius]mi, margin=[margin]%, aging=[threshold]d
- **Profile**: marketcheck-profile.md (project memory)
```

Do not overwrite other memory content.

## Step 7: Confirm and suggest next steps

Show group summary: group name, N locations, ticker, per-location details, preferences.

Next steps:
- "Group dashboard" -- all locations at a glance
- "Compare my stores" -- benchmark rooftops
- "Run my daily briefing" -- per-location + group rollup
- "Transfer opportunities" -- cross-location inventory balance

**UK locations:** UK data is active listings and recent cars only. ML pricing, sold analytics, VIN history are US-only.
