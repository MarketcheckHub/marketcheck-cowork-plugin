---
description: One-time profile setup for auto appraisers — stores your identity, location, and appraisal preferences.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Appraiser onboarding for the MarketCheck appraiser plugin. Collects identity, location, specialization, and appraisal preferences, then persists them to `~/.claude/marketcheck/appraiser-profile.json`. After onboarding, all plugin skills and commands read this profile automatically.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/appraiser-profile.json`.

- If the file **exists and is valid JSON**: Show the current profile summary and ask: "A profile already exists for **[user.name]**. Do you want to update it or keep the current settings?"
  - If keep → stop
  - If update → proceed with current values shown as defaults
- If the file **does not exist** → proceed to Step 1

## Step 1: Collect identity

Ask:
- "What is your name?" → `user.name`
- "What company or organization are you with?" (optional) → `user.company`

If $ARGUMENTS contains a value, use it as name or company as appropriate.

## Step 2: Collect country

Ask: "Are you based in the **US** or **UK**?"

Accept: US, UK, United States, United Kingdom, America, Britain, England.

This determines:
- ZIP vs postcode
- State vs region
- Which MCP tools are available (US has full toolset; UK has active listings and recent cars only)

## Step 3: Collect location

**US path:**
- "What is your ZIP code?" (5-digit ZIP)
- "What state?" (2-letter code — derive from context if possible)
- Optionally ask for city

**UK path:**
- "What is your postcode?" (e.g., SW1A 1AA)
- "What region or county?" (e.g., Greater London, West Midlands)

## Step 4: Collect specialization

Ask: "What type of appraisals do you primarily do?"

| Option | Value |
|--------|-------|
| Trade-in appraisals | `trade-in` |
| Insurance claims / total loss | `insurance` |
| Estate or legal valuations | `estate_legal` |
| Fleet / portfolio revaluation | `fleet` |
| General / mixed | `general` |

Store as `appraiser.specialization`.

## Step 5: Collect preferences

Present with defaults:

```
Appraisal Preferences (press enter to accept defaults):

- Default search radius: 75 miles (wider for better comp coverage)
- Minimum comparable count for confidence: 10 (valuations with fewer comps are flagged as low-confidence)
```

For UK users: "Default search radius: 75 miles (~120 km)"

Store as:
- `preferences.default_radius_miles` (default: 75)
- `appraiser.min_comp_count` (default: 10)

## Step 6: Write profile

Create the directory `~/.claude/marketcheck/` if it does not exist.

Write the following JSON to `~/.claude/marketcheck/appraiser-profile.json`:

```json
{
  "schema_version": "2.0",
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]",
  "user": {
    "name": "[from Step 1]",
    "company": "[from Step 1, or null]"
  },
  "appraiser": {
    "specialization": "[trade-in|insurance|estate_legal|fleet|general]",
    "min_comp_count": 10
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
- Always set `created_at` and `updated_at` to the current ISO timestamp.
- If updating an existing profile, preserve `created_at` and update only `updated_at`.

## Step 7: Confirm and suggest next steps

Display:

```
PROFILE SAVED — Appraiser
━━━━━━━━━━━━━━━━━━━━━━━━━

[Name] | [Company]
Specialization: [type]
Location: [City], [State] [ZIP]
Radius: [X] miles | Min comps: [N]

Saved to: ~/.claude/marketcheck/appraiser-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Appraise VIN [paste VIN]"     — full comparable valuation
  "Quick trade-in estimate"      — 60-second desk estimate
  "Regional price variance"      — geographic value differences
  "Wholesale vs retail spread"   — market depth analysis

To update your profile later, run /onboarding again.
```

**For UK-based appraisers**, append:
```
Note: UK market data includes active listings and recent cars.
Advanced features (ML pricing, sold analytics, VIN history) are US-only.
```
