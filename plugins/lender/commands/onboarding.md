---
description: One-time lender profile setup — stores your identity, company, portfolio focus, LTV thresholds, tracked segments, and location so all skills stop re-asking.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Lender onboarding for the MarketCheck plugin. Collects identity, company, portfolio focus, risk thresholds, tracked segments, and location, then persists them to `~/.claude/marketcheck/lender-profile.json`. After onboarding, all plugin skills and commands read this profile automatically.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/lender-profile.json` first.

- If **lender-profile.json exists and is valid JSON**: Show the current profile summary and ask: "A profile already exists for **[user.name]** at **[user.company]**. Do you want to update it or keep the current settings?"
  - If keep → stop
  - If update → proceed with current values shown as defaults
- If **does not exist** → proceed to Step 1

## Step 1: Collect identity

Ask:
- "What is your name?" → `user.name`
- "What company or organization are you with?" → `user.company`

If $ARGUMENTS contains a value, use it as name or company as appropriate.

## Step 2: Collect country

Ask: "Are you based in the **US** or **UK**?"

Accept: US, UK, United States, United Kingdom, America, Britain, England.

Default to US.

This determines:
- ZIP vs postcode
- State vs region
- Which MCP tools are available (US has full toolset; UK has limited tools)

## Step 3: Collect location

**US path:**
- "What is your ZIP code?" (5-digit ZIP)
- "What state?" (2-letter code — derive from context if possible)
- Optionally ask for city

**UK path:**
- "What is your postcode?" (e.g., SW1A 1AA)
- "What region or county?" (e.g., Greater London, West Midlands)

## Step 4: Collect portfolio focus

Ask: "What is your primary business focus?"

| Focus | Description |
|-------|-------------|
| **auto_loans** | Retail auto lending (direct or indirect) |
| **leasing** | Vehicle leasing / residual value management |
| **floor_plan** | Floor plan financing for dealer inventory |

Store as `lender.portfolio_focus`.

## Step 5: Collect LTV thresholds

Present with defaults:

```
Risk Thresholds (press enter to accept defaults):

- LTV warning threshold: 100% (flag when loan exceeds vehicle value)
- LTV high-risk threshold: 120% (flag as high risk)
```

Store as `lender.risk_ltv_threshold` and `lender.high_risk_ltv_threshold`.

## Step 6: Collect tracked segments

Ask: "Which vehicle segments do you want to track for risk monitoring?"

Suggest common segments: `SUV, Sedan, Truck, EV, Luxury, Subcompact`

Accept comma-separated list. Store as `lender.tracked_segments`.

## Step 7: Collect states of operation

Ask: "Which states do you operate in or want to monitor?" (comma-separated, or "national" for all)

Store as `lender.tracked_states`.

## Step 8: Write profile

Create the directory `~/.claude/marketcheck/` if it does not exist.

Write the following JSON to `~/.claude/marketcheck/lender-profile.json`:

```json
{
  "schema_version": "1.0",
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]",
  "user": {
    "name": "[from Step 1]",
    "company": "[from Step 1]"
  },
  "lender": {
    "portfolio_focus": "[auto_loans|leasing|floor_plan]",
    "risk_ltv_threshold": 100,
    "high_risk_ltv_threshold": 120,
    "tracked_segments": ["SUV", "Sedan", "Truck", "EV"],
    "tracked_states": ["TX", "CA", "FL"]
  },
  "location": {
    "country": "[US|UK]",
    "zip": "[US only, or null]",
    "postcode": "[UK only, or null]",
    "state": "[US only, 2-letter code, or null]",
    "region": "[UK only, or null]",
    "city": "[if known, or null]"
  },
  "preferences": {
    "default_radius_miles": 75
  }
}
```

**Rules:**
- Set null for location fields that don't apply (e.g., `zip: null` for UK, `postcode: null` for US).
- All lender-specific fields are populated; no dealer, analyst, or manufacturer sections.

## Step 9: Confirm and suggest next steps

Display:

```
PROFILE SAVED — Lender
━━━━━━━━━━━━━━━━━━━━━━

[Name] | [Company]
Focus: [portfolio_focus]
LTV Warning: [threshold]% | High-Risk: [threshold]%
Tracked Segments: [segments]
States: [states or "national"]
Location: [City], [State] [ZIP] | [Country]

Saved to: ~/.claude/marketcheck/lender-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Depreciation rate for Tesla Model 3"  — residual value tracking
  "EV vs ICE depreciation comparison"    — portfolio risk assessment
  "Revalue these VINs [paste list]"      — portfolio spot-check
  "Market momentum report"               — monthly sector overview
  "Collateral value for VIN [paste VIN]" — single-unit collateral check

To update your profile later, run /onboarding again.
```

**For UK-based users**, append:
```
Note: UK market data includes active listings and recent cars.
Advanced features (ML pricing, sold analytics, VIN history) are US-only.
```

## Profile Reading Convention for All Skills

Every skill in the lender plugin should follow this pattern at the top of its execution:

1. Read `~/.claude/marketcheck/lender-profile.json`
2. If not found: suggest running `/onboarding` first
3. Extract `lender.portfolio_focus` to determine output emphasis
4. Extract `lender.tracked_segments` for segment highlighting
5. Extract `lender.risk_ltv_threshold` and `lender.high_risk_ltv_threshold` for risk flagging
6. Confirm briefly: "Using profile: **[user.name]** ([user.company]), [location]"
