---
description: One-time auction house profile setup — stores your company identity, auction type, target DMAs, vehicle segments, and fee structure so all skills stop re-asking.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Collect auction house identity, role, target markets, and preferences. Persist to the `marketcheck-profile.md` project memory file.

## Step 0: Check for existing profile

Read the `marketcheck-profile.md` project memory file. Parse the JSON content after the `---` frontmatter delimiter. If valid JSON: show summary, ask update or keep. If keep, stop. If update, use current values as defaults.

## Step 1: Collect identity

- "What is your name?" -> `user.name`
- "What auction company do you work for?" -> `user.company`

Use $ARGUMENTS as name or company if provided.

## Step 2: Collect role

Ask: "What is your role?" -> `auction_house.role`:
- `sales_exec` — selling auction services to dealers, sourcing consignments
- `lane_manager` — planning lanes, optimizing sell-through rates
- `consignment_rep` — acquiring vehicles for auction from dealers, fleets, repos
- `regional_director` — overseeing multiple auction locations or DMAs

## Step 3: Collect auction type

Ask: "What type of auctions does your company run?" -> `auction_house.auction_type`:
- `physical` — in-lane, physical auction events
- `digital` — online-only auctions (simulcast, timed)
- `both` — hybrid physical + digital

## Step 4: Collect country

Ask: "US or UK?" Default US. Determines ZIP vs postcode, available tools (US=full, UK=limited).

## Step 5: Collect location

**US:** ZIP (5-digit), state (2-letter), optionally city.
**UK:** Postcode, region/county.

## Step 6: Target DMAs

Ask: "Which states or metro areas do you cover?" (comma-separated, or "national"). Store as `auction_house.target_dmas`. Examples: "TX, CA, FL" or "Dallas, Houston, Austin" or "national".

## Step 7: Vehicle segments

Ask: "Which vehicle segments do you specialize in?" Suggest: SUV, Sedan, Truck, Luxury, EV, Fleet, Salvage, Commercial, Motorcycle. Accept "all" for no filter. Store as `auction_house.vehicle_segments`.

## Step 8: Buyer and consigner focus

- "Do you primarily sell to franchise dealers, independent dealers, or both?" -> `auction_house.buyer_focus` (franchise|independent|both). Default: both.
- "What types of consignments do you typically handle?" Suggest: dealer_trade, fleet, repo, lease_return, rental, off-lease. Store as `auction_house.consigner_types`.

## Step 9: Auction metrics and fees

Present with defaults (accept all at once):
- Average weekly lanes per sale event: null (ask for estimate)
- Target sell-through percentage: 85%
- Buyer fee percentage: 5%
- Seller fee percentage: 3%
- Default search radius for market analysis: 100 mi

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
  "user_type": "auction_house",
  "created_at": "[ISO]", "updated_at": "[ISO]",
  "user": { "name": "", "company": "" },
  "auction_house": {
    "auction_type": "physical|digital|both",
    "role": "sales_exec|lane_manager|consignment_rep|regional_director",
    "target_dmas": [],
    "vehicle_segments": [],
    "avg_weekly_lanes": null,
    "buyer_focus": "franchise|independent|both",
    "consigner_types": [],
    "target_sell_through_pct": 85,
    "buyer_fee_pct": 5,
    "seller_fee_pct": 3
  },
  "location": {
    "country": "US|UK", "zip": null, "postcode": null,
    "state": null, "region": null, "city": null
  },
  "preferences": { "default_radius_miles": 100 }
}
```

Set null for non-applicable location fields.

## Step 11: Sync to session memory

Write a compact profile summary to your auto-memory file (`MEMORY.md`) so all future chat windows automatically know this user. Append or update the `## MarketCheck Profile` section:

```
## MarketCheck Profile: Auction House
- **User**: [name] | **Company**: [company] | **Role**: [role]
- **Auction Type**: [auction_type] | **Country**: [country] | **Location**: [zip/postcode], [state/region]
- **Target DMAs**: [target_dmas list] | **Segments**: [vehicle_segments or "All"]
- **Buyer Focus**: [buyer_focus] | **Consigner Types**: [consigner_types list]
- **Fees**: buyer=[buyer_fee]%, seller=[seller_fee]% | **Target Sell-Through**: [sell_through]%
- **Profile**: marketcheck-profile.md (project memory)
```

Do not overwrite other memory content.

## Step 12: Confirm and suggest next steps

Show profile summary with all key fields and saved path.

Next steps:
- "Find dealers to invite to our next sale in TX" — buyer targeting
- "Who has aged inventory in my market?" — consignment sourcing
- "What should I run in next week's lanes?" — lane planning
- "Market overview for California" — DMA intelligence

**UK users:** UK data is active listings and recent cars only. ML pricing, sold analytics, VIN history are US-only. Lane planning and demand analytics require US data.
