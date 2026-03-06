---
description: One-time insurer profile setup — stores your identity, role, location, and insurance-specific preferences so all skills stop re-asking. Works for adjusters, underwriters, and claims managers.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Insurer onboarding for the MarketCheck insurance plugin. Collects role, identity, location, and insurance-specific preferences (claim types, total-loss thresholds, comparable radius), then persists them to `~/.claude/marketcheck/insurer-profile.json`. After onboarding, all plugin skills and commands read this profile automatically.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/insurer-profile.json`.

- If **insurer-profile.json exists and is valid JSON**: Show the current profile summary and ask: "A profile already exists for **[user.name]** ([insurer.role]). Do you want to update it or keep the current settings?"
  - If keep → stop
  - If update → proceed with current values shown as defaults
- If **does not exist** → proceed to Step 1

## Step 1: Collect identity

Ask:
- "What is your name?" → `user.name`
- "What insurance company or organization are you with?" → `user.company`

If $ARGUMENTS contains a value, use it as name or company as appropriate.

## Step 2: Collect role

Ask: "What best describes your role?"

| Role | Description |
|------|-------------|
| **Adjuster** | Field or desk adjuster handling claims valuations and settlements |
| **Underwriter** | Risk assessment, premium pricing, policy issuance |
| **Claims Manager** | Supervises claims operations, reserve management, litigation oversight |

Store the response as `insurer.role`.

If $ARGUMENTS contains keywords like "adjuster", "underwriter", "claims", auto-detect the role and confirm.

## Step 3: Collect claim types

Ask: "What types of claims do you primarily handle? (select all that apply)"

| Claim Type | Description |
|------------|-------------|
| **Total Loss** | Vehicle declared total loss — FMV-based settlement |
| **Diminished Value** | Post-repair value reduction claims |
| **Theft Recovery** | Stolen vehicle valuation (recovered or unrecovered) |

Store as `insurer.claim_types` array (e.g., `["total_loss", "diminished_value"]`).

Default: `["total_loss"]` if not specified.

## Step 4: Collect country

Ask: "Are you based in the **US** or **UK**?"

Accept: US, UK, United States, United Kingdom, America, Britain, England.

**Important:** Inform UK users: "The insurance plugin requires US data tools (ML pricing, sold analytics, VIN history). Most features are not available for the UK market."

Default: US.

## Step 5: Collect location

**US path:**
- "What is your primary ZIP code for claims?" (5-digit ZIP — this anchors comparable searches)
- "What state?" (2-letter code — derive from context if possible)
- Optionally ask for city

**UK path:**
- "What is your postcode?" (e.g., SW1A 1AA)
- "What region or county?" (e.g., Greater London, West Midlands)

## Step 6: Collect settlement preferences

Present all at once with defaults:

```
Settlement & Valuation Preferences (press enter to accept defaults):

- Total-loss threshold percentage: 75% (vehicle is total loss if repair cost exceeds this % of FMV)
- Default comparable search radius: 100 miles (wider than retail — insurance needs more comps for defensible settlements)
```

Store as:
- `insurer.total_loss_threshold_pct` (default: 75)
- `insurer.default_comp_radius` (default: 100)

Note: "The 75% threshold is a common industry default. Actual thresholds vary by state regulation and company policy. Adjust this to match your company's guidelines."

## Step 7: Write profile

Create the directory `~/.claude/marketcheck/` if it does not exist.

Write the following JSON to `~/.claude/marketcheck/insurer-profile.json`:

```json
{
  "schema_version": "1.0",
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]",
  "user": {
    "name": "[from Step 1]",
    "company": "[from Step 1]"
  },
  "insurer": {
    "role": "[adjuster|underwriter|claims_manager]",
    "claim_types": ["total_loss", "diminished_value", "theft_recovery"],
    "total_loss_threshold_pct": 75,
    "default_comp_radius": 100
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
    "default_radius_miles": 100
  }
}
```

**Rules:**
- Set null for location fields that don't apply (e.g., `zip: null` for UK, `postcode: null` for US).
- No `dealer` or `dealer_id` fields — insurers don't need them.
- The `default_radius_miles` in preferences should match `insurer.default_comp_radius`.

## Step 8: Confirm and suggest next steps

Display confirmation:

```
PROFILE SAVED — Insurance Professional
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Name] | [Role] — [Company]
[City], [State] [ZIP] | [Country]

Claim Types: [total_loss, diminished_value, theft_recovery]
Total-Loss Threshold: [X]%
Comparable Radius: [X] miles

Saved to: ~/.claude/marketcheck/insurer-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Total loss valuation for VIN [paste VIN]"  — full claims valuation with settlement range
  "Appraise VIN [paste VIN]"                  — comparable-backed insurance appraisal
  "Depreciation trend for Toyota RAV4"        — claim value trending
  "Market risk report"                        — insurance market intelligence
  "Batch value these VINs [paste list]"       — catastrophe event / portfolio revaluation

To update your profile later, run /onboarding again.
```

**For UK-based users**, append:
```
Note: UK market data includes active listings and recent cars.
Advanced features (ML pricing, sold analytics, VIN history) are US-only.
Most insurance valuation workflows require US data.
```

## Profile Reading Convention for All Skills

Every skill in the insurer plugin should follow this pattern at the top of its execution:

1. Read `~/.claude/marketcheck/insurer-profile.json`
2. If not found: suggest running `/onboarding` first
3. Extract `insurer.role` to determine output framing and terminology
4. Extract `insurer.claim_types` for workflow emphasis
5. Extract `insurer.total_loss_threshold_pct` and `insurer.default_comp_radius` for calculations
6. Confirm briefly: "Using profile: **[user.name]** ([role]), [location]"
