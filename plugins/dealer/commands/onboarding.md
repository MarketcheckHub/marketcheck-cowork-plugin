---
description: One-time dealer profile setup — stores your dealership identity, location, and preferences so all skills stop re-asking.
allowed-tools: ["Read", "Write", "AskUserQuestion", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [your name, company, or web domain]
---

Dealer onboarding for the MarketCheck dealer plugin. Collects dealership identity, location, type, and operational preferences, then persists them to `~/.claude/marketcheck/dealer-profile.json`. After onboarding, all plugin skills and commands read this profile automatically.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/dealer-profile.json`.

- If **the file exists and is valid JSON**: Show the current profile summary and ask: "A profile already exists for **[dealer.name]** ([dealer.dealer_type]). Do you want to update it or keep the current settings?"
  - If keep → stop
  - If update → proceed with current values shown as defaults
- If **the file does not exist** → proceed to Step 1

## Step 1: Collect identity

Ask:
- "What is your name?" → `user.name`
- "What is your dealership name?" (e.g., Toyota of Dallas) → `dealer.name`
- "What is your website domain where your inventory is listed?" (e.g., toyotaofdallas.com) → `dealer.web_domain`

If $ARGUMENTS contains a value, use it as name or domain as appropriate.

## Step 2: Collect country

Ask: "Are you based in the **US** or **UK**?"

Accept: US, UK, United States, United Kingdom, America, Britain, England.

If $ARGUMENTS contains a `.co.uk` domain, default to UK. Otherwise default to US.

This determines:
- ZIP vs postcode
- State vs region
- Which MCP tools are available (US has 7 tools; UK has 2)

## Step 3: Collect location

**US path:**
- "What is your ZIP code?" (5-digit ZIP)
- "What state?" (2-letter code — derive from context if possible)

**UK path:**
- "What is your postcode?" (e.g., SW1A 1AA)
- "What region or county?" (e.g., Greater London, West Midlands)

## Step 4: Auto-discover dealer_id

Attempt to find the dealer's MarketCheck ID using their web domain.

**US dealers:**
Call `mcp__marketcheck__search_active_cars` with:
- `dealer_website`: the web domain
- `zip`: from Step 3
- `radius`: 100
- `rows`: 5
- `seller_type`: dealer

**UK dealers:**
Call `mcp__marketcheck__search_uk_active_cars` with:
- `dealer_website`: the web domain
- `rows`: 5

**From the results:**
- If listings are returned, extract the `dealer_id` from the first result
- Show the matched dealer name and ask: "Is this your dealership? [Matched Name]"
- If confirmed → store with `dealer_id_source: "auto"`

**If no match by domain:**
- Try searching with the dealer name via `dealer_name` parameter
- If still no match → inform user: "Could not auto-discover your dealer ID. You can provide it manually if you know it, or skip for now."
- Store `dealer_id: null` with `dealer_id_source: "unknown"`

## Step 5: Dealer type and franchise info

- "Are you a **franchise** dealer or **independent**?" → `dealer.dealer_type`
- If franchise: "Which brands do you sell? (list all)" → `dealer.franchise_brands`
- If independent: set `franchise_brands` to empty array

## Step 6: CPO program

- "Do you offer a **Certified Pre-Owned (CPO)** program?" (yes/no)
- If yes: "What is your approximate certification cost per unit?" (default: $1,200)
- Store as `dealer.cpo_program` and `dealer.cpo_certification_cost`

## Step 7: Operational preferences

Present all at once with defaults:

```
Operational Preferences (press enter to accept defaults):

- Default search radius: 50 miles
- Target retail margin: 15%
- Average recon cost per unit: $1,500
- Floor plan cost per day: $35
- Max acceptable days on market: 45 days
- Aging inventory threshold: 60 days (units over this are flagged)
```

For UK dealers: "Default search radius: 50 miles (≈80 km)"

## Step 8: Write profile

Create the directory `~/.claude/marketcheck/` if it does not exist.

Write the following JSON to `~/.claude/marketcheck/dealer-profile.json`:

```json
{
  "schema_version": "1.0",
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]",
  "user": {
    "name": "[from Step 1]"
  },
  "dealer": {
    "name": "[from Step 1]",
    "dealer_id": "[from Step 4, or null]",
    "dealer_id_source": "[auto|manual|unknown]",
    "dealer_type": "[franchise|independent]",
    "franchise_brands": ["[from Step 5]"],
    "web_domain": "[from Step 1]",
    "cpo_program": false,
    "cpo_certification_cost": null
  },
  "location": {
    "country": "[US|UK]",
    "zip": "[US only]",
    "postcode": "[UK only]",
    "state": "[US only, 2-letter code]",
    "region": "[UK only]",
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

**Rules:**
- Set null for location fields that don't apply (e.g., `zip: null` for UK, `postcode: null` for US).
- Only populate fields that were collected. Use defaults for preferences if the user accepted them.

## Step 9: Confirm and suggest next steps

```
PROFILE SAVED — Dealer
━━━━━━━━━━━━━━━━━━━━━

[Name] | [dealer_type] — [brands or "independent"]
[City], [State] [ZIP] | [Country]
Domain: [web_domain] | Dealer ID: [dealer_id or "not discovered"]
CPO Program: [Yes ($X/unit) or No]

Preferences:
  Radius: [X] mi | Margin: [X]% | Recon: $[X] | Floor plan: $[X]/day
  Max DOM: [X] days | Aging: [X]+ days

Saved to: ~/.claude/marketcheck/dealer-profile.json
━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Run my daily briefing"        — aging alerts + competitor price drops
  "Weekly inventory review"      — full lot scan + stocking hot list
  "Price check VIN [paste VIN]"  — instant competitive pricing
  "What should I stock?"         — demand-to-supply analysis

To update your profile later, run /onboarding again.
```

**For UK-based dealers**, append:
```
Note: UK market data includes active listings and recent cars.
Advanced features (ML pricing, sold analytics, VIN history) are US-only.
```
