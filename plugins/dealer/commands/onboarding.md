---
description: One-time dealer profile setup — stores your dealership identity, location, and preferences so all skills stop re-asking.
allowed-tools: ["Read", "Write", "AskUserQuestion", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [your name, company, or web domain]
---

Collect dealership identity, location, type, and preferences. Persist to the `marketcheck-profile.md` project memory file.

## Step 0: Check for existing profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter. If valid JSON: show summary, ask update or keep. If keep, stop. If update, use current values as defaults.

## Step 1: Collect identity

- "What is your name?" -> `user.name`
- "What is your dealership name?" -> `dealer.name`
- "What is your website domain?" -> `dealer.web_domain`

Use $ARGUMENTS as name or domain if provided.

## Step 2: Collect country

Ask: "US or UK?" Default US. `.co.uk` domain -> default UK.
Determines: ZIP vs postcode, state vs region, available MCP tools (US=7, UK=2).

## Step 3: Collect location

**US:** ZIP (5-digit), state (2-letter).
**UK:** Postcode, region/county.

## Step 4: Auto-discover dealer_id

Search by web domain to find MarketCheck dealer ID.
**US:** `search_active_cars` with `dealer_website`, `zip`, `radius=100`, `rows=5`, `seller_type=dealer`. Extract `dealer_id` from first result, confirm with user.
**UK:** `search_uk_active_cars` with `dealer_website`, `rows=5`.
**No match by domain:** Try `dealer_name`. Still no match -> store `dealer_id: null`, `dealer_id_source: "unknown"`.

## Step 5: Dealer type and franchise info

- "Franchise or independent?" -> `dealer.dealer_type`
- If franchise: "Which brands?" -> `dealer.franchise_brands`
- If independent: `franchise_brands: []`

## Step 6: CPO program

- "Do you offer CPO?" -> `dealer.cpo_program`
- If yes: "Certification cost per unit?" (default: $1,200) -> `dealer.cpo_certification_cost`

## Step 7: Operational preferences

Present with defaults (accept all at once):
- Default search radius: 50 mi (UK: ~80 km)
- Target retail margin: 15%
- Recon cost/unit: $1,500
- Floor plan cost/day: $35
- Max acceptable DOM: 45 days
- Aging threshold: 60 days
- Default inventory type: ask "Do your reports focus on **used**, **new**, or **both**? (Default: used)" → `default_inventory_type: "used"|"new"|"both"`. All skills default to this; users can override per-run.

## Step 8: Write profile

Write to the `marketcheck-profile.md` project memory file with this frontmatter:

```
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
  "user_type": "dealer",
  "created_at": "[ISO]", "updated_at": "[ISO]",
  "user": { "name": "" },
  "dealer": {
    "name": "", "dealer_id": null, "dealer_id_source": "auto|manual|unknown",
    "dealer_type": "franchise|independent", "franchise_brands": [],
    "web_domain": "", "cpo_program": false, "cpo_certification_cost": null
  },
  "location": {
    "country": "US|UK", "zip": null, "postcode": null,
    "state": null, "region": null, "city": null
  },
  "preferences": {
    "default_radius_miles": 50, "target_margin_pct": 15,
    "recon_cost_estimate": 1500, "floor_plan_cost_per_day": 35,
    "max_acceptable_dom": 45, "dom_aging_threshold": 60,
    "default_inventory_type": "used"
  }
}
```

Set null for non-applicable location fields (zip=null for UK, postcode=null for US).

## Step 9: Sync to session memory

Write a compact profile summary to your auto-memory file (`MEMORY.md`) so all future chat windows automatically know this user. Append or update the `## MarketCheck Profile` section:

```
## MarketCheck Profile: Dealer
- **User**: [name] | **Dealership**: [dealer.name] | **Type**: [dealer_type]
- **Country**: [country] | **Location**: [zip/postcode], [state/region]
- **Dealer ID**: [dealer_id] ([source]) | **Domain**: [web_domain]
- **Brands**: [franchise_brands or "Independent"] | **CPO**: [yes/no]
- **Prefs**: radius=[radius]mi, margin=[margin]%, recon=$[recon], floor=$[floor]/day, aging=[threshold]d
- **Profile**: marketcheck-profile.md (project memory)
```

Do not overwrite other memory content.

## Step 10: Confirm and suggest next steps

Show profile summary with all key fields and saved path.

Next steps:
- "Run my daily briefing" -- aging alerts + competitor price drops
- "Weekly inventory review" -- full lot scan + stocking hot list
- "Price check VIN [paste VIN]" -- instant competitive pricing
- "What should I stock?" -- demand-to-supply analysis

**UK dealers:** Note UK data is active listings and recent cars only. ML pricing, sold analytics, VIN history are US-only.
