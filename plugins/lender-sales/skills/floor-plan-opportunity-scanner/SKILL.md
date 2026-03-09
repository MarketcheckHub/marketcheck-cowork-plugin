---
name: floor-plan-opportunity-scanner
description: >
  This skill should be used when the user asks about "floor plan prospects",
  "dealers with aging inventory", "who needs floor plan financing",
  "floor plan opportunities", "dealers burning floor plan",
  "aged inventory dealers", "high DOM dealers",
  "who is paying too much for floor plan",
  or needs help finding dealers with significant aging inventory
  that could benefit from competitive floor plan terms.
version: 0.1.0
---

# Floor Plan Opportunity Scanner — Find Dealers Needing Floor Plan Help

## Profile
Load `~/.claude/marketcheck/lender-sales-profile.json` if exists. Extract: target_states, preferred_dealer_types, min_dealer_inventory, country, zip, radius. If missing, ask for state. **US**: `search_active_cars`. **UK**: `search_uk_active_cars` only (DOM data available, full workflow works). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep specializing in floor plan financing, looking for dealers under floor plan pressure — high DOM inventory, many aged units, significant daily burn. These dealers are most receptive to competitive floor plan offers.

| Field | Source | Default |
|-------|--------|---------|
| Target state/ZIP | Profile or user input | — |
| Min lot size | Profile | 20 |
| Dealer type pref | Profile | both |

## Workflow: Find High-DOM Dealers

1. **Scan market for aging inventory concentration** — Call `mcp__marketcheck__search_active_cars` with `state` (or `zip`+`radius`), `car_type=used`, `seller_type=dealer`, `sort_by=dom`, `sort_order=desc`, `facets=dealer_id|0|50|2`, `stats=dom`, `rows=0`. If preferred_dealer_types set, add `dealer_type`.
   → **Extract only**: dealer_ids from facets with counts, avg_dom from stats. Discard full response.

2. **Profile top aging dealers** — For the top 20 dealers by unit count (with min_dealer_inventory filter), call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `stats=price,dom`, `rows=0`.
   → **Extract only per dealer**: seller_name, city, total_count, avg_price, avg_dom, median_dom. Discard full response.

3. **Count aged units per dealer** — For each dealer, call `mcp__marketcheck__search_active_cars` with `dealer_id=[id]`, `car_type=used`, `dom_range=60-999`, `rows=0`.
   → **Extract only**: aged_count (num_found). Discard full response.

4. **Calculate floor plan metrics per dealer**:
   - **Aged %** = aged_count / total_count × 100
   - **Estimated Floor Plan Burn** = total_count × avg_dom × $35/day (industry standard rate)
   - **Monthly Burn** = floor_plan_burn / (avg_dom / 30)
   - **Aged Unit Burn** = aged_count × (avg_aged_dom_estimate) × $35/day
   - **Savings Pitch** = "If we reduce your floor plan rate by $5/day across [total] units, you save $[savings]/month"
   - **Priority Score** = (aged_pct × 40) + (total_count_normalized × 30) + (avg_dom_percentile × 30)

5. **Classify prospects**:
   - Priority Score 70+: **HIGH PRIORITY** — Significant aging, large lot, likely paying high floor plan costs
   - Score 50-69: **MEDIUM PRIORITY** — Moderate aging, worth a pitch
   - Score < 50: **LOW PRIORITY** — Manageable aging

## Workflow: Quick Floor Plan Burden Check for One Dealer

1. Call `mcp__marketcheck__search_active_cars` with `dealer_id`, `car_type=used`, `stats=price,dom`, `rows=0`.
2. Call same with `dom_range=60-999`, `rows=0` for aged count.
3. Calculate burden and pitch.

## Output
Floor plan prospect table: Rank, Dealer Name, City, Total Units, Aged Units (60+ DOM), Aged %, Avg DOM, Est. Monthly Floor Burn, Priority Score, Savings Pitch. Summary: "[X] high-priority floor plan prospects with combined $[Y]/month in estimated floor plan burden." Top 5 outreach recommendations with specific savings pitch per dealer.
