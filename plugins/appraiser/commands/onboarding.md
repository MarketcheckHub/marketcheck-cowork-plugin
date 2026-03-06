---
description: One-time profile setup for auto appraisers — stores your identity, location, and appraisal preferences.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Collect identity, location, specialization, and appraisal preferences. Persist to `~/.claude/marketcheck/appraiser-profile.json`.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/appraiser-profile.json`. If valid JSON: show summary, ask update or keep. If keep, stop.

## Step 1: Collect identity

- "What is your name?" -> `user.name`
- "What company?" (optional) -> `user.company`

Use $ARGUMENTS as name or company if provided.

## Step 2: Collect country

Ask: "US or UK?" Determines ZIP vs postcode, available tools (US=full, UK=active+recent only).

## Step 3: Collect location

**US:** ZIP (5-digit), state (2-letter), optionally city.
**UK:** Postcode, region/county.

## Step 4: Collect specialization

Ask: "What type of appraisals?" -> `appraiser.specialization`:
- `trade-in` -- trade-in appraisals
- `insurance` -- insurance claims / total loss
- `estate_legal` -- estate or legal valuations
- `fleet` -- fleet / portfolio revaluation
- `general` -- mixed

## Step 5: Collect preferences

Present with defaults:
- Default search radius: 75 mi (UK: ~120 km)
- Min comparable count for confidence: 10

Store as `preferences.default_radius_miles` (75) and `appraiser.min_comp_count` (10).

## Step 6: Write profile

Create `~/.claude/marketcheck/` if needed. Write to `appraiser-profile.json`:

```json
{
  "schema_version": "2.0",
  "created_at": "[ISO]", "updated_at": "[ISO]",
  "user": { "name": "", "company": null },
  "appraiser": { "specialization": "", "min_comp_count": 10 },
  "location": {
    "country": "US|UK", "zip": null, "postcode": null,
    "state": null, "region": null, "city": null
  },
  "preferences": { "default_radius_miles": 75 }
}
```

Set null for non-applicable location fields. Preserve `created_at` on updates.

## Step 7: Confirm and suggest next steps

Show profile summary: name, company, specialization, location, radius, min comps.

Next steps:
- "Appraise VIN [paste VIN]" -- full comparable valuation
- "Quick trade-in estimate" -- 60-second desk estimate
- "Regional price variance" -- geographic value differences
- "Wholesale vs retail spread" -- market depth analysis

**UK appraisers:** UK data is active listings and recent cars only. ML pricing, sold analytics, VIN history are US-only.
