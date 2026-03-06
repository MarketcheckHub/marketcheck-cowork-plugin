---
description: One-time profile setup — stores your identity, role, location, and preferences so all skills stop re-asking. Works for dealers, dealer groups, appraisers, lenders, analysts, and manufacturers.
allowed-tools: ["Read", "Write", "AskUserQuestion", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__search_uk_active_cars"]
argument-hint: [your name, company, or web domain]
---

Universal onboarding for all MarketCheck plugin users. Collects role, identity, location, and role-specific preferences, then persists them to `~/.claude/marketcheck/user-profile.json`. After onboarding, all plugin skills and commands read this profile automatically.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/user-profile.json` first. If not found, also check `~/.claude/marketcheck/dealer-profile.json` (legacy v1.0).

- If **user-profile.json exists and is valid JSON**: Show the current profile summary and ask: "A profile already exists for **[user.name or dealer.name]** ([user_type]). Do you want to update it or keep the current settings?"
  - If keep → stop
  - If update → proceed with current values shown as defaults
- If **dealer-profile.json exists** (v1.0 legacy): Show: "Found a legacy dealer profile for **[dealer.name]**. I'll migrate it to the new format and add the new fields." Pre-fill all dealer fields from the legacy profile, then proceed to collect any new fields (CPO program, etc.).
- If **neither exists** → proceed to Step 1

## Step 1: Collect role

Ask: "What best describes your role?"

| Role | Description |
|------|-------------|
| **Dealer** | Single-location car dealer (franchise or independent) |
| **Dealer Group** | Multi-location dealer group (e.g., AutoNation, regional group) |
| **Appraiser** | Independent appraiser, insurance adjuster, or fleet analyst |
| **Lender** | Auto lender, lease company, or floor plan provider |
| **Analyst** | Financial analyst, equity researcher, or market intelligence |
| **Manufacturer** | OEM, brand regional manager, or distributor |

Store the response as `user_type`. This is the master routing field — it determines which onboarding steps to run and which skills surface as primary.

If $ARGUMENTS contains keywords like "dealer", "appraiser", "lender", "analyst", "OEM", "manufacturer", auto-detect the role and confirm.

## Step 2: Collect identity

Ask:
- "What is your name?" → `user.name`
- "What company or organization are you with?" (optional) → `user.company`

If $ARGUMENTS contains a value, use it as name or company as appropriate.

## Step 3: Collect country

Ask: "Are you based in the **US** or **UK**?"

Accept: US, UK, United States, United Kingdom, America, Britain, England.

If $ARGUMENTS contains a `.co.uk` domain, default to UK. Otherwise default to US.

This determines:
- ZIP vs postcode
- State vs region
- Which MCP tools are available (US has 7 tools; UK has 2)

## Step 4: Collect location

**US path:**
- "What is your ZIP code?" (5-digit ZIP)
- "What state?" (2-letter code — derive from context if possible)
- Optionally ask for city

**UK path:**
- "What is your postcode?" (e.g., SW1A 1AA)
- "What region or county?" (e.g., Greater London, West Midlands)

---

## Step 5: Role-specific collection

Branch based on `user_type` from Step 1:

### Path A: Dealer (single location)

**Step 5A-1: Dealer identity**
- "What is your dealership name?" (e.g., Toyota of Dallas)
- "What is your website domain where your inventory is listed?" (e.g., toyotaofdallas.com)

**Step 5A-2: Auto-discover dealer_id**

Attempt to find the dealer's MarketCheck ID using their web domain.

**US dealers:**
Call `mcp__marketcheck__search_active_cars` with:
- `dealer_website`: the web domain
- `zip`: from Step 4
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

**Step 5A-3: Dealer type and franchise brands**
- "Are you a **franchise** dealer or **independent**?"
- If franchise: "Which brands do you sell? (list all)"
- If independent: set `franchise_brands` to empty array

**Step 5A-4: CPO program**
- "Do you offer a **Certified Pre-Owned (CPO)** program?" (yes/no)
- If yes: "What is your approximate certification cost per unit?" (default: $1,200)
- Store as `dealer.cpo_program` and `dealer.cpo_certification_cost`

**Step 5A-5: Operational preferences**
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

---

### Path B: Dealer Group

**Step 5B-1: Group identity**
- "What is your dealer group name?" (e.g., AutoNation, Hendrick Automotive)
- "Is your group publicly traded?" (yes/no)
  - If yes: "What is your stock ticker?" (e.g., AN, LAD)

**Step 5B-2: Add locations**

Loop to collect locations. For each location:
- "Location name?" (e.g., AutoNation Toyota Dallas)
- "Website domain?" (e.g., autonationtoyotadallas.com)
- "ZIP code?" (US) or "Postcode?" (UK)
- "State?" (US) or "Region?" (UK)
- "Franchise or independent?"
- If franchise: "Which brands?"

For each location, attempt auto-discovery of `dealer_id` using the same logic as Path A Step 5A-2.

After each location: "Add another location? (yes/no)"

Minimum 2 locations required for dealer group.

**Step 5B-3: Group-level preferences**

Same as dealer preferences (Step 5A-5) — applied as defaults across all locations.

- "Do any of your locations offer **CPO programs**?" (yes/no)
  - If yes: "Average CPO certification cost per unit?" (default: $1,200)

---

### Path C: Appraiser

Minimal setup — appraisers don't need a dealer_id.

**Step 5C-1: Specialization**
- "What type of appraisals do you primarily do?" → `trade-in`, `insurance`, `estate/legal`, `fleet`, `general`

**Step 5C-2: Preferences**
```
Appraisal Preferences (press enter to accept defaults):

- Default search radius: 75 miles (wider for better comp coverage)
- Minimum comparable count for confidence: 10
```

---

### Path D: Lender

**Step 5D-1: Portfolio focus**
- "What is your primary focus?" → `auto_loans`, `leasing`, `floor_plan`

**Step 5D-2: Risk thresholds**
```
Risk Thresholds (press enter to accept defaults):

- LTV warning threshold: 100% (flag when loan exceeds vehicle value)
- LTV high-risk threshold: 120%
- Tracked vehicle segments: EV, Pickup, SUV (comma-separated)
```

---

### Path E: Analyst

**Step 5E-1: Focus area**
- "What is your primary analysis focus?" → `oem` (OEM/brand performance), `dealer_groups` (publicly traded dealer stocks), `ev_transition` (EV adoption & pricing), `lending` (residual/depreciation risk), `general` (broad market)

**Step 5E-2: Tracked entities**
- "Which stock tickers do you want to track?" (e.g., F, GM, TSLA, AN, LAD — comma-separated)
  - The plugin ships with built-in ticker→makes mappings; the user just enters tickers

**Step 5E-3: Geographic focus**
- "Which states or regions do you focus on?" (e.g., TX, CA, FL — or "national" for all)

**Step 5E-4: Benchmark period**
- "How many months of lookback for trend analysis?" (default: 3)

---

### Path F: Manufacturer

**Step 5F-1: Brand identity**
- "Which brand(s) do you represent?" (e.g., Toyota, Lexus)
- "Which states/regions are you responsible for?" (e.g., TX, CA, FL or "national")

**Step 5F-2: Competitive tracking**
- "Which competitor brands do you want to track?" (e.g., Honda, Hyundai)

---

## Step 6: Write profile

Create the directory `~/.claude/marketcheck/` if it does not exist.

Write the following JSON to `~/.claude/marketcheck/user-profile.json`:

```json
{
  "schema_version": "2.0",
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]",
  "user_type": "[dealer|dealer_group|appraiser|lender|analyst|manufacturer]",
  "user": {
    "name": "[from Step 2]",
    "company": "[from Step 2, or null]"
  },
  "dealer": {
    "name": "[from Step 5A-1, or null if not dealer]",
    "dealer_id": "[from Step 5A-2, or null]",
    "dealer_id_source": "[auto|manual|unknown]",
    "dealer_type": "[franchise|independent]",
    "franchise_brands": ["[from Step 5A-3]"],
    "web_domain": "[from Step 5A-1]",
    "cpo_program": false,
    "cpo_certification_cost": null
  },
  "dealer_group": {
    "group_name": "[from Step 5B-1, or null]",
    "is_publicly_traded": false,
    "ticker": "[or null]",
    "locations": [],
    "default_location_index": 0
  },
  "analyst": {
    "focus": "[oem|dealer_groups|ev_transition|lending|general, or null]",
    "tracked_tickers": [],
    "tracked_makes": "[auto-populated from ticker mapping]",
    "tracked_states": [],
    "benchmark_period_months": 3
  },
  "lender": {
    "portfolio_focus": "[auto_loans|leasing|floor_plan, or null]",
    "risk_ltv_threshold": 100,
    "high_risk_ltv_threshold": 120,
    "tracked_segments": []
  },
  "manufacturer": {
    "brands": [],
    "states": [],
    "competitor_brands": []
  },
  "appraiser": {
    "specialization": "[trade-in|insurance|estate_legal|fleet|general, or null]",
    "min_comp_count": 10
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
- Only populate sections relevant to the `user_type`. Set irrelevant sections to `null`.
- For dealer_group, the `dealer` section is `null` — individual locations are stored in `dealer_group.locations[]`.
- For analyst/lender/appraiser/manufacturer, `dealer` and `dealer_group` are `null`, and `preferences` uses role-appropriate defaults (e.g., appraiser gets wider radius).
- Set null for location fields that don't apply (e.g., `zip: null` for UK, `postcode: null` for US).

### Ticker → Makes Mapping (built-in, for analyst auto-population)

When an analyst enters tickers, auto-populate `tracked_makes` using this mapping:

```
F     → Ford, Lincoln
GM    → Chevrolet, GMC, Buick, Cadillac
TM    → Toyota, Lexus
HMC   → Honda, Acura
STLA  → Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati
TSLA  → Tesla
RIVN  → Rivian
LCID  → Lucid
HYMTF → Hyundai, Kia, Genesis
NSANY → Nissan, Infiniti
MBGAF → Mercedes-Benz
BMWYY → BMW, MINI, Rolls-Royce
VWAGY → Volkswagen, Audi, Porsche, Lamborghini, Bentley
AN    → AutoNation (dealer group — not a make)
LAD   → Lithia Motors (dealer group)
PAG   → Penske Automotive (dealer group)
SAH   → Sonic Automotive (dealer group)
GPI   → Group 1 Automotive (dealer group)
ABG   → Asbury Automotive (dealer group)
KMX   → CarMax (dealer/retailer)
CVNA  → Carvana (dealer/retailer)
```

For dealer group tickers (AN, LAD, etc.), store the group name in `tracked_makes` instead of vehicle makes — these are tracked via `get_sold_summary(ranking_dimensions=dealership_group_name)`.

## Step 7: Legacy profile migration

If a v1.0 `dealer-profile.json` was found in Step 0:
1. Write the new `user-profile.json` with all migrated fields
2. Keep the old `dealer-profile.json` as a backup (do not delete)
3. Note: "Legacy profile migrated. The old file has been kept as backup at `~/.claude/marketcheck/dealer-profile.json`."

## Step 8: Confirm and suggest next steps

Display role-appropriate confirmation:

### For Dealers (single)
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

Saved to: ~/.claude/marketcheck/user-profile.json
━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Run my daily briefing"        — aging alerts + competitor price drops
  "Weekly inventory review"      — full lot scan + stocking hot list
  "Price check VIN [paste VIN]"  — instant competitive pricing
  "What should I stock?"         — demand-to-supply analysis

To update your profile later, run /onboarding again.
```

### For Dealer Groups
```
PROFILE SAVED — Dealer Group
━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Group Name] | [N] locations | [Ticker or "private"]

Locations:
  1. [Name] — [City], [State] — [dealer_type] — ID: [dealer_id]
  2. [Name] — [City], [State] — [dealer_type] — ID: [dealer_id]
  ...

Saved to: ~/.claude/marketcheck/user-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Group dashboard"              — see all locations at a glance
  "Compare my stores"            — benchmark rooftops against each other
  "Run my daily briefing"        — per-location + group rollup
  "Transfer opportunities"       — find cross-location inventory balance

To update your profile later, run /onboarding again.
```

### For Analysts
```
PROFILE SAVED — Financial Analyst
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Name] | [Company]
Focus: [focus area]
Tracking: [tickers] → [makes]
States: [states or "national"]
Benchmark: [N] months lookback

Saved to: ~/.claude/marketcheck/user-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "How is Ford doing?"           — OEM investment signal for F
  "EV market update"             — EV adoption + pricing vs ICE
  "Monthly auto market report"   — sector-wide intelligence
  "AutoNation health check"      — dealer group stock signal

To update your profile later, run /onboarding again.
```

### For Lenders
```
PROFILE SAVED — Lender
━━━━━━━━━━━━━━━━━━━━━━

[Name] | [Company]
Focus: [portfolio_focus]
LTV Warning: [threshold]% | High-Risk: [threshold]%
Tracked Segments: [segments]

Saved to: ~/.claude/marketcheck/user-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Depreciation rate for Tesla Model 3"  — residual value tracking
  "EV vs ICE depreciation comparison"    — portfolio risk assessment
  "Revalue these VINs [paste list]"      — portfolio spot-check
  "Market momentum report"               — monthly sector overview

To update your profile later, run /onboarding again.
```

### For Appraisers
```
PROFILE SAVED — Appraiser
━━━━━━━━━━━━━━━━━━━━━━━━━

[Name] | [Company]
Specialization: [type]
Location: [City], [State] [ZIP]
Radius: [X] miles | Min comps: [N]

Saved to: ~/.claude/marketcheck/user-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Appraise VIN [paste VIN]"     — full comparable valuation
  "Quick trade-in estimate"      — 60-second desk estimate
  "Regional price variance"      — geographic value differences
  "Wholesale vs retail spread"   — market depth analysis

To update your profile later, run /onboarding again.
```

### For Manufacturers
```
PROFILE SAVED — Manufacturer
━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Name] | [Company]
Brands: [brands]
States: [states]
Competitors: [competitor_brands]

Saved to: ~/.claude/marketcheck/user-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Market share for [brand]"     — brand performance + share trends
  "EV adoption in my states"     — electrification progress
  "Competitor analysis"          — head-to-head brand comparison
  "Regional demand heatmap"      — state-level volume + pricing

To update your profile later, run /onboarding again.
```

**For UK-based users (any role)**, append:
```
Note: UK market data includes active listings and recent cars.
Advanced features (ML pricing, sold analytics, VIN history) are US-only.
```

## Profile Reading Convention for All Skills

Every skill in the plugin should follow this pattern at the top of its execution:

1. Read `~/.claude/marketcheck/user-profile.json`
2. If not found, read `~/.claude/marketcheck/dealer-profile.json` (v1.0 fallback)
3. If neither found: suggest running `/onboarding` first
4. Extract `user_type` to determine output formatting and terminology
5. Extract role-specific sections as needed
6. Confirm briefly: "Using profile: **[user.name]** ([user_type]), [location]"
