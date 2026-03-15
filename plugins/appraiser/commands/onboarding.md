---
description: One-time profile setup for auto appraisers — stores your identity, location, and appraisal preferences.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Collect identity, location, specialization, and appraisal preferences. Persist to the `marketcheck-profile.md` project memory file.

## Step 0: Check for existing profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter delimiter. If valid JSON: show summary, ask update or keep. If keep, stop.

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
  "schema_version": "2.0",
  "user_type": "appraiser",
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

## Step 7: Sync to session memory

Write a compact profile summary to your auto-memory file (`MEMORY.md`) so all future chat windows automatically know this user. Append or update the `## MarketCheck Profile` section:

```
## MarketCheck Profile: Appraiser
- **User**: [name] | **Company**: [company]
- **Specialization**: [specialization] | **Min comps**: [min_comp_count]
- **Country**: [country] | **Location**: [zip/postcode], [state/region]
- **Radius**: [radius]mi
- **Profile**: marketcheck-profile.md (project memory)
```

Do not overwrite other memory content.

## Step 8: Confirm and suggest next steps

Show profile summary: name, company, specialization, location, radius, min comps.

Next steps:
- "Appraise VIN [paste VIN]" -- full comparable valuation
- "Quick trade-in estimate" -- 60-second desk estimate
- "Regional price variance" -- geographic value differences
- "Wholesale vs retail spread" -- market depth analysis

**UK appraisers:** UK data is active listings and recent cars only. ML pricing, sold analytics, VIN history are US-only.
