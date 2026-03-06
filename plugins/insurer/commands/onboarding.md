---
description: One-time insurer profile setup — stores your identity, role, location, and insurance-specific preferences so all skills stop re-asking. Works for adjusters, underwriters, and claims managers.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Collect role, identity, location, and insurance-specific preferences. Persist to `~/.claude/marketcheck/insurer-profile.json`.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/insurer-profile.json`. If valid JSON: show summary, ask update or keep. If keep, stop.

## Step 1: Collect identity

- "What is your name?" -> `user.name`
- "What insurance company?" -> `user.company`

Use $ARGUMENTS as name or company if provided.

## Step 2: Collect role

Ask: "What best describes your role?" -> `insurer.role`:
- `adjuster` -- field or desk adjuster, claims valuations
- `underwriter` -- risk assessment, premium pricing
- `claims_manager` -- claims operations, reserve management

Auto-detect from $ARGUMENTS if keywords match.

## Step 3: Claim types

Ask: "What types of claims?" (select all) -> `insurer.claim_types` array:
- `total_loss` -- vehicle total loss, FMV-based settlement
- `diminished_value` -- post-repair value reduction
- `theft_recovery` -- stolen vehicle valuation

Default: `["total_loss"]`.

## Step 4: Collect country

Ask: "US or UK?" Default US. UK users: most insurance features require US data tools.

## Step 5: Collect location

**US:** ZIP (5-digit, anchors comp searches), state (2-letter), optionally city.
**UK:** Postcode, region/county.

## Step 6: Settlement preferences

Present with defaults:
- Total-loss threshold: 75% (repair cost exceeds this % of FMV = total loss)
- Default comp search radius: 100 mi (wider for defensible settlements)

Store as `insurer.total_loss_threshold_pct` (75) and `insurer.default_comp_radius` (100).

## Step 7: Write profile

Create `~/.claude/marketcheck/` if needed. Write to `insurer-profile.json`:

```json
{
  "schema_version": "1.0",
  "created_at": "[ISO]", "updated_at": "[ISO]",
  "user": { "name": "", "company": "" },
  "insurer": {
    "role": "adjuster|underwriter|claims_manager",
    "claim_types": ["total_loss"],
    "total_loss_threshold_pct": 75, "default_comp_radius": 100
  },
  "location": {
    "country": "US|UK", "zip": null, "postcode": null,
    "state": null, "region": null, "city": null
  },
  "preferences": { "default_radius_miles": 100 }
}
```

Set null for non-applicable location fields. `default_radius_miles` should match `default_comp_radius`.

## Step 8: Sync to session memory

Write a compact profile summary to your auto-memory file (`MEMORY.md`) so all future chat windows automatically know this user. Append or update the `## MarketCheck Profile` section:

```
## MarketCheck Profile: Insurer
- **User**: [name] | **Company**: [company] | **Role**: [role]
- **Country**: [country] | **Location**: [zip/postcode], [state/region]
- **Claim types**: [claim_types list] | **Total-loss threshold**: [threshold]%
- **Comp radius**: [radius]mi
- **Profile**: ~/.claude/marketcheck/insurer-profile.json
```

Do not overwrite other memory content.

## Step 9: Confirm and suggest next steps

Show profile summary: name, role, company, location, claim types, thresholds.

Next steps:
- "Total loss valuation for VIN [paste VIN]" -- full claims valuation
- "Appraise VIN [paste VIN]" -- comparable-backed appraisal
- "Depreciation trend for Toyota RAV4" -- claim value trending
- "Batch value these VINs [paste list]" -- catastrophe/portfolio revaluation

**UK users:** UK data is active listings and recent cars only. Most insurance workflows require US data.
