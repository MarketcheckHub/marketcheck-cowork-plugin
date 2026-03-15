---
name: cross-location-balancer
description: >
  This skill should be used when the user asks about "transfer opportunities",
  "balance inventory", "which store needs what", "inter-store transfer",
  "move vehicles between locations", "inventory balancing", "rebalance my lot",
  "cross-location optimization", or needs to identify vehicles that should be
  moved from one dealer location to another for faster turns.
version: 0.1.0
---

# Cross-Location Balancer — Inter-Store Inventory Transfer Recommendations

## User Profile (Required)

This skill requires a dealer group profile with at least 2 locations.

1. Read the `marketcheck-profile.md` project memory file.
2. Check `user_type`:
   - If `dealer_group`: use `dealer_group.locations[]` — requires minimum 2 locations
   - If `dealer` or other: "This skill is for multi-location dealer groups. Run `/onboarding` as a Dealer Group."
3. Extract:
   - `locations[]` with dealer_id, name, zip, state, dealer_type for each
   - `preferences` for group defaults
   - `country` ← `location.country`
4. Confirm: "Analyzing transfer opportunities across **[N]** locations"

## User Context

The primary user is a **dealer group operations manager** or **inventory director** who manages vehicle allocation across multiple rooftops. The problem: one store has a surplus of SUVs sitting 60+ days while another store 50 miles away is short on SUVs and losing customers. A $200 transport cost to move the vehicle saves $2,000+ in aging floor plan costs.

## Workflow: Transfer Opportunity Analysis

### Step 1 — Get each location's inventory mix

For each location, use the Agent tool to spawn the `marketcheck-cowork-plugin:lot-scanner` agent:

> Fetch inventory facets for dealer_id=[dealer_id], country=[country].
> Mode: facets_only
> Facets: make|0|20|1, model|0|30|1, body_type|0|10|1
> Also get: total_count, and aging facets if available

This returns each location's inventory breakdown by make/model and body type without listing every vehicle.

### Step 2 — Get local demand for each location's market

For each location (US only), call `mcp__marketcheck__get_sold_summary` with:
- `state`: the location's state
- `zip`: the location's zip (with radius)
- `inventory_type`: `Used`
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 10
- `date_from` / `date_to`: prior month

This shows what SELLS in each location's local market.

### Step 3 — Calculate location-level gaps

For each location:
- **Dealer mix %** = units in category / total units × 100
- **Market demand %** = sold in category / total sold × 100
- **Gap** = Market demand % - Dealer mix %
- Positive gap = location is UNDER-STOCKED in this category (needs more)
- Negative gap = location is OVER-STOCKED (has too many)

### Step 4 — Match senders with receivers

Cross-reference all locations to find transfer pairs:
- **Sender:** Location A has gap < -5% in a category (over-stocked) AND aged units in that category
- **Receiver:** Location B has gap > +5% in the same category (under-stocked)

For each potential transfer:
- **Transport cost estimate** = distance between locations × $1.50/mile (or flat rate if adjacent)
- **Expected DOM improvement** = difference in avg DOM for that category between locations
- **Floor plan savings** = expected DOM improvement × $[floor_plan_cost/day]
- **Net benefit** = floor plan savings - transport cost

Only recommend transfers where net benefit > $500.

### Step 5 — Identify specific units to transfer

For the top transfer opportunities, get the specific aged units from the sender location:
- Units in the over-stocked category with DOM > aging_threshold
- Sort by DOM descending (move the oldest first)

## Output

```
CROSS-LOCATION TRANSFER RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Group Name] | [N] locations analyzed

INVENTORY MIX BY LOCATION
Category    | [Location 1]      | [Location 2]      | [Location 3]      | Market Demand
            | Count (Share)     | Count (Share)      | Count (Share)     | (Share)
------------|-------------------|-------------------|-------------------|-------------
SUV         | XX (XX%)          | XX (XX%)          | XX (XX%)          | XX%
Pickup      | XX (XX%)          | XX (XX%)          | XX (XX%)          | XX%
Sedan       | XX (XX%)          | XX (XX%)          | XX (XX%)          | XX%
...

RECOMMENDED TRANSFERS (sorted by net benefit)

Transfer 1: [Category] from [Location A] → [Location B]
  Units to move: [N] (oldest first)
  Reason: [A] has XX% surplus, [B] has XX% deficit in [category]
  Transport cost: ~$XXX
  Expected DOM improvement: XX days faster at [B]
  Floor plan savings: ~$X,XXX
  Net benefit: $X,XXX
  Specific units:
    VIN (last 8) | Year Make Model | DOM at [A] | Listed Price
    -------------|-----------------|-----------|-------------
    [unit 1]     | 22 RAV4 XLE     | 72 days   | $28,500
    [unit 2]     | 21 CR-V EX      | 65 days   | $26,200

Transfer 2: ...

TRANSFER SUMMARY
  Total recommended transfers: [N] units
  Total transport cost: ~$X,XXX
  Total expected floor plan savings: ~$XX,XXX
  Net benefit: ~$XX,XXX over [X] months
```

## Important Notes

- This skill requires `dealer_id` for all locations — locations without a dealer_id are skipped.
- **US-only for demand data:** Demand analysis uses `get_sold_summary`. UK locations can still be analyzed for inventory mix but without market demand comparison.
- Transport cost is estimated. Actual costs depend on the group's logistics setup.
- Only recommend transfers for aged units (DOM > threshold) — don't move fresh inventory.
- If two locations are in different states, note potential registration and title considerations.
- For groups with 5+ locations, focus on the 3 highest-impact transfer pairs to keep it actionable.
