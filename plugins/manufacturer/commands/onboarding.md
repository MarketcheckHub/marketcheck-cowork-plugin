---
description: One-time profile setup for manufacturers and OEMs — stores your brand identity, competitive set, and regional focus.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or brand]
---

Collect brand identity, competitive set, regional focus. Persist to the `marketcheck-profile.md` project memory file.

## Step 0: Check for existing profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter delimiter. If valid JSON: show summary, ask update or keep. If keep, stop.

## Step 1: Collect identity

- "What is your name?" -> `user.name`
- "What company?" -> `user.company`

Use $ARGUMENTS as name or company if provided.

## Step 2: Country

US-only. MarketCheck sold analytics covers US market. Store `location.country = "US"`.

## Step 3: Brand identity

Ask: "Which brand(s) do you represent?" (comma-separated) -> `manufacturer.brands` array.
Map parent company names to individual brands (e.g., "Toyota Motor" -> Toyota, Lexus).

## Step 4: Regional focus

Ask: "Which states are you responsible for?" (comma-separated, or "national") -> `manufacturer.states`.
Convert state names to 2-letter codes.
Optionally ask: "What state are you based in?" -> `location.state`.

## Step 5: Competitive set

Ask: "Which competitor brands to track?" -> `manufacturer.competitor_brands` array.
If unsure, suggest 3-5 relevant competitors based on segment overlap.

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
  "user_type": "manufacturer",
  "created_at": "[ISO]", "updated_at": "[ISO]",
  "user": { "name": "", "company": "" },
  "manufacturer": {
    "brands": [], "states": [], "competitor_brands": []
  },
  "location": { "country": "US", "state": null }
}
```

`brands` and `competitor_brands` must be individual brand names (not parent companies). `states` must be 2-letter codes or `["national"]`.

## Step 7: Sync to session memory

Write a compact profile summary to your auto-memory file (`MEMORY.md`) so all future chat windows automatically know this user. Append or update the `## MarketCheck Profile` section:

```
## MarketCheck Profile: Manufacturer
- **User**: [name] | **Company**: [company]
- **Brands**: [brands list] | **States**: [states or "National"]
- **Competitors**: [competitor_brands list]
- **Profile**: marketcheck-profile.md (project memory)
```

Do not overwrite other memory content.

## Step 8: Confirm and suggest next steps

Show profile summary: name, company, brands, states, competitors.

Next steps:
- "Market share for [first brand]" -- brand performance + share trends
- "EV adoption in my states" -- electrification progress
- "Competitor analysis" -- head-to-head brand comparison
- "Regional demand heatmap" -- state-level volume + pricing
