---
description: One-time dealer profile setup — alias for /onboarding (which now supports all roles)
allowed-tools: ["Read", "Write", "AskUserQuestion", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [dealer name or web domain]
---

**This command is an alias for `/onboarding`.** It pre-selects `user_type: "dealer"` and runs the same universal onboarding flow.

Run the `/onboarding` command with the dealer role pre-selected. Follow the exact same steps documented in `commands/onboarding.md`, but skip the role selection question (Step 1) and default to `user_type: "dealer"`.

If the user provides $ARGUMENTS, pass them through to the onboarding flow.

### Legacy Note

This command originally wrote to the `marketcheck-profile.md` project memory file (v1.0 schema). The new onboarding writes to the `marketcheck-profile.md` project memory file (v2.0 schema). If a v1.0 profile exists, the onboarding flow will offer to migrate it.

## Step 0: Check for existing profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter delimiter.

- If the file **exists and is valid JSON**: Show the current profile summary and ask: "A dealer profile already exists for **[dealer.name]**. Do you want to update it or keep the current settings?"
  - If keep → stop
  - If update → proceed with current values shown as defaults
- If the file **does not exist** or is invalid → proceed to Step 1

## Step 1: Collect country

Ask: "Is your dealership in the **US** or **UK**?"

Accept: US, UK, United States, United Kingdom, America, Britain, England.

If $ARGUMENTS contains a `.co.uk` domain, default to UK. Otherwise default to US.

This is the first branch point — it determines:
- ZIP vs postcode
- State vs region
- Which MCP tools are available (US has 7 tools; UK has 2)

## Step 2: Collect dealer name and web domain

- "What is your dealership name?" (e.g., Toyota of Dallas, CarMax Austin)
- "What is your website domain where your inventory is listed?" (e.g., toyotaofdallas.com, carmax.com)

If $ARGUMENTS contains a value that looks like a domain (contains a dot), use it as the web domain. If it looks like a name, use it as the dealer name.

## Step 3: Collect location

**US path:**
- "What is your dealership's ZIP code?" (5-digit ZIP)
- Optionally ask for city and state, or derive from subsequent API responses

**UK path:**
- "What is your dealership's postcode?" (e.g., SW1A 1AA)
- "What region or county is your dealership in?" (e.g., Greater London, West Midlands)

## Step 4: Auto-discover dealer_id

Attempt to find the dealer's MarketCheck ID automatically using their web domain.

**US dealers:**
Call `mcp__marketcheck__search_active_cars` with:
- `dealer_website`: the web domain from Step 2
- `zip`: from Step 3
- `radius`: 100
- `rows`: 5
- `seller_type`: dealer

**UK dealers:**
Call `mcp__marketcheck__search_uk_active_cars` with:
- `dealer_website`: the web domain from Step 2 (if the parameter is supported)
- `rows`: 5

**From the results:**
- If listings are returned, extract the `dealer_id` from the first result
- Show the matched dealer name from the listing and ask: "Is this your dealership? [Matched Name]"
- If confirmed → store the `dealer_id` with `dealer_id_source: "auto"`

**If no match by domain:**
- Try searching with the dealer name: `dealer_name` parameter with the name from Step 2
- If still no match → inform the user: "Could not auto-discover your dealer ID. You can provide it manually if you know it, or skip for now. Some features like lot-level inventory scans will ask for it later."
- Store `dealer_id: null` with `dealer_id_source: "manual"` or `"unknown"`

## Step 5: Collect dealer type and franchise brands

- "Are you a **franchise** dealer or **independent**?"
- If franchise: "Which brands do you sell? (e.g., Toyota, Honda, Ford — list all that apply)"
- If independent: set `franchise_brands` to empty array

## Step 6: Collect preferences (with defaults)

Present all at once with defaults. The user can accept defaults by pressing enter or provide custom values:

```
Operational Preferences (press enter to accept defaults):

- Default search radius: 50 miles
- Target retail margin: 15%
- Average recon cost per unit: $1,500
- Floor plan cost per day: $35
- Max acceptable days on market: 45 days
- Aging inventory threshold: 60 days (units over this are flagged)
```

For UK dealers, adjust the radius prompt: "Default search radius: 50 miles (≈80 km)"

## Step 7: Write profile



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
  "user_type": "dealer",
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]",
  "dealer": {
    "name": "[from Step 2]",
    "dealer_id": "[from Step 4, or null]",
    "dealer_id_source": "[auto|manual|unknown]",
    "dealer_type": "[franchise|independent]",
    "franchise_brands": ["[from Step 5]"],
    "web_domain": "[from Step 2]"
  },
  "location": {
    "country": "[US|UK]",
    "zip": "[US only, from Step 3]",
    "postcode": "[UK only, from Step 3]",
    "state": "[US only, 2-letter code]",
    "region": "[UK only, from Step 3]",
    "city": "[if known]"
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

Set null for fields that don't apply (e.g., `zip: null` for UK dealers, `postcode: null` for US dealers).

## Step 8: Confirm and suggest next steps

Display:

```
DEALER PROFILE SAVED
━━━━━━━━━━━━━━━━━━━

Dealer:     [Name] ([dealer_type] — [brands or "independent"])
Location:   [City], [State/Region] [ZIP/Postcode]
Country:    [US/UK]
Domain:     [web_domain]
Dealer ID:  [dealer_id or "not discovered — some features will ask"]

Preferences:
  Radius: [X] miles  |  Margin: [X]%  |  Recon: $[X]/unit
  Floor plan: $[X]/day  |  Max DOM: [X] days  |  Aging flag: [X]+ days

Saved to: marketcheck-profile.md (project memory)

━━━━━━━━━━━━━━━━━━━
All skills now use this context automatically.

Try these next:
  "Run my daily briefing"        — aging alerts + competitor price drops
  "Weekly inventory review"      — full lot scan + stocking hot list
  "Price check VIN [paste VIN]"  — instant competitive pricing
  "What should I stock?"         — demand-to-supply analysis

To update your profile later, run /dealer-onboarding again.
```

**For UK dealers**, add a note:

```
Note: UK market data includes active listings and recent cars.
Advanced features (ML pricing, sold analytics, VIN history) are US-only.
```
