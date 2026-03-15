---
description: One-time lender profile setup — stores your identity, company, portfolio focus, LTV thresholds, tracked segments, and location so all skills stop re-asking.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Collect identity, portfolio focus, risk thresholds, tracked segments, and location. Persist to the `marketcheck-profile.md` project memory file.

## Step 0: Check for existing profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter delimiter. If valid JSON: show summary, ask update or keep. If keep, stop.

## Step 1: Collect identity

- "What is your name?" -> `user.name`
- "What company?" -> `user.company`

Use $ARGUMENTS as name or company if provided.

## Step 2: Collect country

Ask: "US or UK?" Default US. Determines ZIP vs postcode, available tools (US=full, UK=limited).

## Step 3: Collect location

**US:** ZIP (5-digit), state (2-letter), optionally city.
**UK:** Postcode, region/county.

## Step 4: Portfolio focus

Ask: "Primary business focus?" -> `lender.portfolio_focus`:
- `auto_loans` -- retail auto lending (direct/indirect)
- `leasing` -- vehicle leasing / residual value management
- `floor_plan` -- floor plan financing for dealer inventory

## Step 5: LTV thresholds

Present with defaults:
- LTV warning threshold: 100% (flag when loan exceeds value)
- LTV high-risk threshold: 120%

Store as `lender.risk_ltv_threshold` and `lender.high_risk_ltv_threshold`.

## Step 6: Tracked segments

Ask: "Which vehicle segments to track for risk monitoring?" Suggest: SUV, Sedan, Truck, EV, Luxury, Subcompact. Store as `lender.tracked_segments`.

## Step 7: States of operation

Ask: "Which states do you operate in?" (comma-separated, or "national"). Store as `lender.tracked_states`.

## Step 8: Write profile

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
  "user_type": "lender",
  "created_at": "[ISO]", "updated_at": "[ISO]",
  "user": { "name": "", "company": "" },
  "lender": {
    "portfolio_focus": "auto_loans|leasing|floor_plan",
    "risk_ltv_threshold": 100, "high_risk_ltv_threshold": 120,
    "tracked_segments": [], "tracked_states": []
  },
  "location": {
    "country": "US|UK", "zip": null, "postcode": null,
    "state": null, "region": null, "city": null
  },
  "preferences": { "default_radius_miles": 75 }
}
```

Set null for non-applicable location fields.

## Step 9: Sync to session memory

Write a compact profile summary to your auto-memory file (`MEMORY.md`) so all future chat windows automatically know this user. Append or update the `## MarketCheck Profile` section:

```
## MarketCheck Profile: Lender
- **User**: [name] | **Company**: [company] | **Focus**: [portfolio_focus]
- **Country**: [country] | **Location**: [zip/postcode], [state/region]
- **LTV thresholds**: warning=[risk_ltv]%, high-risk=[high_risk_ltv]%
- **Segments**: [tracked_segments list] | **States**: [tracked_states or "National"]
- **Profile**: marketcheck-profile.md (project memory)
```

Do not overwrite other memory content.

## Step 10: Confirm and suggest next steps

Show profile summary: name, company, focus, LTV thresholds, tracked segments, states, location.

Next steps:
- "Depreciation rate for Tesla Model 3" -- residual value tracking
- "EV vs ICE depreciation comparison" -- portfolio risk assessment
- "Revalue these VINs [paste list]" -- portfolio spot-check
- "Collateral value for VIN [paste VIN]" -- single-unit check

**UK users:** UK data is active listings and recent cars only. ML pricing, sold analytics, VIN history are US-only.
