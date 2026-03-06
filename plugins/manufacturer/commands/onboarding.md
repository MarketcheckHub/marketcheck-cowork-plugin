---
description: One-time profile setup for manufacturers and OEMs — stores your brand identity, competitive set, and regional focus.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or brand]
---

Manufacturer-specific onboarding for the MarketCheck plugin. Collects brand identity, competitive set, regional focus, and persists to `~/.claude/marketcheck/manufacturer-profile.json`. After onboarding, all manufacturer plugin skills and commands read this profile automatically.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/manufacturer-profile.json`.

- If **the file exists and is valid JSON**: Show the current profile summary and ask: "A manufacturer profile already exists for **[user.name]** at **[user.company]** representing **[manufacturer.brands]**. Do you want to update it or keep the current settings?"
  - If keep → stop
  - If update → proceed with current values shown as defaults
- If **the file does not exist** → proceed to Step 1

## Step 1: Collect identity

Ask:
- "What is your name?" → `user.name`
- "What company or organization are you with?" → `user.company`

If $ARGUMENTS contains a value, use it as name or company as appropriate and confirm.

## Step 2: Collect country

Ask: "Are you based in the **US**?"

Note: "MarketCheck automotive data is currently **US-only** for sold analytics. All skills use US market data."

Store as `location.country = "US"`.

## Step 3: Collect brand identity

Ask: "Which brand(s) do you represent? (e.g., Toyota, Lexus — comma-separated)"

Store as `manufacturer.brands` array. If the user provides a parent company name (e.g., "Toyota Motor"), map to individual brands: Toyota, Lexus.

## Step 4: Collect regional focus

Ask: "Which states or regions are you responsible for? (e.g., TX, CA, FL — or 'national' for all)"

- If "national" or "all" → store as `manufacturer.states: ["national"]`
- If specific states → store as array of 2-letter codes, e.g., `["TX", "CA", "FL"]`
- If the user provides a state name (e.g., "Texas"), convert to 2-letter code

Optionally ask: "What state are you based in?" → `location.state` (for default geographic context)

## Step 5: Collect competitive set

Ask: "Which competitor brands do you want to track? (e.g., Honda, Hyundai, Nissan — comma-separated)"

Store as `manufacturer.competitor_brands` array.

If the user is unsure, suggest: "Common competitors for [their brands] include [suggest 3-5 relevant brands based on segment overlap]."

## Step 6: Write profile

Create the directory `~/.claude/marketcheck/` if it does not exist.

Write the following JSON to `~/.claude/marketcheck/manufacturer-profile.json`:

```json
{
  "schema_version": "2.0",
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]",
  "user": {
    "name": "[from Step 1]",
    "company": "[from Step 1]"
  },
  "manufacturer": {
    "brands": ["Toyota", "Lexus"],
    "states": ["TX", "CA", "FL"],
    "competitor_brands": ["Honda", "Hyundai", "Nissan"]
  },
  "location": {
    "country": "US",
    "state": "[if provided, or null]"
  }
}
```

**Rules:**
- Always include all three top-level sections: `user`, `manufacturer`, `location`.
- `manufacturer.brands` must be an array of individual brand names (not parent company names).
- `manufacturer.states` must be an array of 2-letter state codes, or `["national"]`.
- `manufacturer.competitor_brands` must be an array of individual brand names.
- `location.state` is the user's home state (optional), separate from `manufacturer.states` which are their responsible territories.

## Step 7: Confirm and suggest next steps

Display:

```
PROFILE SAVED — Manufacturer
━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Name] | [Company]
Brands: [brands]
States: [states or "national"]
Competitors: [competitor_brands]

Saved to: ~/.claude/marketcheck/manufacturer-profile.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Try these next:
  "Market share for [first brand]"    — brand performance + share trends
  "EV adoption in my states"          — electrification progress
  "Competitor analysis"               — head-to-head brand comparison
  "Regional demand heatmap"           — state-level volume + pricing

To update your profile later, run /onboarding again.
```
