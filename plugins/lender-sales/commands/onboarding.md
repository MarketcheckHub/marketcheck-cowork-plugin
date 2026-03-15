---
description: One-time lender sales rep profile setup — stores your company identity, lending criteria, target states, and dealer preferences so all skills stop re-asking.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Collect lender sales rep identity, lending criteria, target markets, and preferences. Persist to the `marketcheck-profile.md` project memory file.

## Step 0: Check for existing profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter delimiter. If valid JSON: show summary, ask update or keep. If keep, stop. If update, use current values as defaults.

## Step 1: Collect identity

- "What is your name?" -> `user.name`
- "What lending company do you work for?" -> `user.company`

Use $ARGUMENTS as name or company if provided.

## Step 2: Collect role

Ask: "What is your role?" -> `lender_sales.role`:
- `sales_rep` — field sales, calling on dealers, pitching lending products
- `regional_manager` — overseeing sales reps across a territory
- `bdc_agent` — business development center, phone/digital outreach to dealers

## Step 3: Collect lending type

Ask: "What type of lending does your company specialize in?" -> `lender_sales.lending_type`:
- `retail` — consumer auto loans (direct or indirect through dealers)
- `floor_plan` — floor plan financing for dealer inventory
- `lease` — vehicle leasing programs
- `subprime` — subprime/non-prime consumer auto lending
- `captive` — captive finance arm of an OEM

## Step 4: Collect country

Ask: "US or UK?" Default US. Determines ZIP vs postcode, available tools (US=full, UK=limited).

## Step 5: Collect location

**US:** ZIP (5-digit), state (2-letter), optionally city.
**UK:** Postcode, region/county.

## Step 6: Target states

Ask: "Which states does your territory cover?" (comma-separated, or "national"). Store as `lender_sales.target_states`. Examples: "TX, CA, FL" or "national".

## Step 7: Lending criteria — vehicle parameters

Collect the lender's "sweet spot" for the types of vehicles they prefer to lend on:
- "What vehicle price range do you typically lend on?" -> `lender_sales.price_range_min` and `lender_sales.price_range_max`. Examples: "$15,000–$55,000" for prime, "$3,000–$18,000" for subprime.
- "Preferred model year range?" -> `lender_sales.preferred_year_range`. Default: "2019-2025".
- "Maximum mileage you'll lend on?" -> `lender_sales.max_mileage`. Default: 80,000.

## Step 8: Lending criteria — dealer and make preferences

- "Do you prefer franchise dealers, independent dealers, or both?" -> `lender_sales.preferred_dealer_types`. Default: both.
- "Any specific makes your programs favor? (or 'all')" -> `lender_sales.approved_makes`. Examples: "Toyota, Honda, Ford" or empty for all.
- "Any vehicle segments you specialize in? (or 'all')" -> `lender_sales.approved_segments`. Examples: "SUV, Sedan, Truck" or empty for all.

## Step 9: Risk and volume thresholds

Present with defaults (accept all at once):
- Maximum LTV percentage: 120%
- Minimum dealer lot size worth pursuing: 20 units
- Default search radius: 75 mi

## Step 10: Write profile

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
  "user_type": "lender_sales",
  "created_at": "[ISO]", "updated_at": "[ISO]",
  "user": { "name": "", "company": "" },
  "lender_sales": {
    "lending_type": "retail|floor_plan|lease|subprime|captive",
    "role": "sales_rep|regional_manager|bdc_agent",
    "target_states": [],
    "price_range_min": null,
    "price_range_max": null,
    "preferred_dealer_types": [],
    "approved_makes": [],
    "approved_segments": [],
    "ltv_max_pct": 120,
    "preferred_year_range": "2019-2025",
    "max_mileage": 80000,
    "min_dealer_inventory": 20
  },
  "location": {
    "country": "US|UK", "zip": null, "postcode": null,
    "state": null, "region": null, "city": null
  },
  "preferences": { "default_radius_miles": 75 }
}
```

Set null for non-applicable location fields.

## Step 11: Sync to session memory

Write a compact profile summary to your auto-memory file (`MEMORY.md`) so all future chat windows automatically know this user. Append or update the `## MarketCheck Profile` section:

```
## MarketCheck Profile: Lender Sales
- **User**: [name] | **Company**: [company] | **Role**: [role]
- **Lending Type**: [lending_type] | **Country**: [country] | **Location**: [zip/postcode], [state/region]
- **Target States**: [target_states or "National"] | **Dealer Pref**: [preferred_dealer_types]
- **Price Range**: $[min]–$[max] | **Years**: [year_range] | **Max Miles**: [max_mileage]
- **Approved Makes**: [approved_makes or "All"] | **Segments**: [approved_segments or "All"]
- **LTV Max**: [ltv_max]% | **Min Lot Size**: [min_dealer_inventory] units
- **Profile**: marketcheck-profile.md (project memory)
```

Do not overwrite other memory content.

## Step 12: Confirm and suggest next steps

Show profile summary with all key fields and saved path.

Next steps:
- "Find dealers to call in Texas" — dealer match prospecting
- "Tell me about [dealer name]" — dealer intelligence brief
- "Who needs floor plan help in my territory?" — floor plan opportunity scan
- "Territory overview" — coverage vs opportunity dashboard

**UK users:** UK data is active listings and recent cars only. ML pricing, sold analytics, and LTV analysis require US data.
