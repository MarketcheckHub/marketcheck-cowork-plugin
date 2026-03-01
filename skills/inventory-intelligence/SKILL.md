---
name: inventory-intelligence
description: >
  This skill should be used when the user asks to "what should I stock",
  "what's selling in my area", "market demand analysis", "aging inventory alert",
  "turn rate by segment", "slow movers on my lot", "inventory analysis",
  "demand vs supply ratio", "what to buy at auction", "floor plan optimization",
  "new vs used mix", "days on market by model", or needs help with
  data-driven stocking decisions, inventory aging analysis, or demand-to-supply
  intelligence for a dealership or OEM region.
version: 0.1.0
---

# Inventory Intelligence — Data-Driven Stocking & Aging Analysis

Turn sold market data and live supply counts into actionable stocking recommendations. Replace gut-instinct buying with demand-to-supply ratios, aging alerts, turn-rate benchmarks, and optimal new-vs-used mix targets.

## User Context

Before running any workflow, collect the following from the user:

- **Role**: Dealer (single rooftop or group) or OEM regional manager
- **Location**: State (2-letter code) and/or zip code for local market scoping
- **Dealer ID** (if dealer): Their MarketCheck dealer_id for lot-level queries
- **Franchise brand(s)**: The make(s) they sell or are responsible for
- **Timeframe**: Default to the most recent full month; ask if they want a custom date range (YYYY-MM-DD, first-of-month to last-of-month)
- **Inventory type focus**: New, Used, or Both (default Both)
- **Dealer type**: Franchise or Independent (default Franchise)

If any required field is missing, ask before proceeding. Do not guess dealer IDs or locations.

## Workflow: Market Demand Snapshot

Understand what is actually selling in the user's market before making any stocking decisions.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from`: first day of the target month (e.g. `2026-01-01`)
   - `date_to`: last day of the target month (e.g. `2026-01-31`)
   - `state`: user's 2-letter state code
   - `dealer_type`: user's dealer type (Franchise or Independent)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`

2. Call `mcp__marketcheck__get_sold_summary` with the same date and location filters, but:
   - `ranking_dimensions`: `body_type`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `10`

3. Present results as two ranked tables:
   - **Top 20 Models by Sales Volume** — columns: Rank, Make, Model, Sold Count, Avg Sale Price, Avg DOM
   - **Sales by Body Type** — columns: Body Type, Sold Count, Share of Total (%)

4. Highlight any body type or model where the user's franchise brand appears in the top 5, and flag segments where it does not appear (potential conquest or gap opportunities).

## Workflow: What Should I Stock? (Demand-to-Supply Ratio)

Compare what the market is buying against what dealers currently have listed. Vehicles with high demand and low supply represent stocking opportunities.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `state`: user's state
   - `dealer_type`: user's dealer type
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `30`

2. Call `mcp__marketcheck__search_active_cars` with:
   - `state`: user's state (or `zip` + `radius` if provided)
   - `car_type`: `used` (or `new` based on user focus)
   - `seller_type`: `dealer`
   - `dealer_type`: user's dealer type
   - `facets`: `make|0|50|2,model|0|50|2`
   - `rows`: `0` (we only need facet counts, not individual listings)

3. For each of the top 30 sold make/model combinations, look up the active supply count from the facet results.

4. Calculate **Demand-to-Supply Ratio** = Sold Count (monthly) / Active Supply Count.
   - Ratio > 1.5 = **Under-supplied** (strong stocking opportunity)
   - Ratio 0.8 - 1.5 = **Balanced**
   - Ratio < 0.8 = **Over-supplied** (avoid stocking more)

5. Present a single table sorted by demand-to-supply ratio descending:
   - Columns: Make, Model, Monthly Sold, Active Supply, D/S Ratio, Signal (Under-supplied / Balanced / Over-supplied)
   - Bold or call out the top 5 under-supplied models as priority acquisition targets.

## Workflow: Aging Inventory Alert

Identify units on the dealer's lot that have exceeded healthy DOM thresholds and assess their current market value.

1. Call `mcp__marketcheck__search_active_cars` with:
   - `dealer_id`: user's dealer ID
   - `dom_range`: `60-999`
   - `sort_by`: `dom`
   - `sort_order`: `desc`
   - `rows`: `25`
   - `car_type`: `used` (or `new` or both based on context)

2. For each returned VIN (up to 10 highest-DOM units), call `mcp__marketcheck__predict_price_with_comparables` with:
   - `vin`: the vehicle's VIN
   - `miles`: the vehicle's listed mileage
   - `zip`: the dealer's zip code
   - `dealer_type`: user's dealer type

3. Build an **Aging Inventory Report** table:
   - Columns: VIN (last 6), Year, Make, Model, Trim, DOM (days), Listed Price, Predicted Market Price, Price Gap ($), Price Gap (%), Recommendation
   - **Recommendation** logic:
     - Price Gap > +10% (overpriced): "Reduce price to market — estimated $X reduction"
     - Price Gap -5% to +10%: "At market — consider wholesale if DOM > 90"
     - Price Gap < -5% (underpriced): "Below market — review for quick retail sale"

4. Summarize total aged inventory exposure:
   - Count of units > 60 DOM, > 90 DOM, > 120 DOM
   - Estimated total floor plan interest burn (units x avg $30/day x avg DOM over 60)
   - Total overpricing gap across all aged units

## Workflow: Turn Rate by Segment

Benchmark how quickly different vehicle segments move in the local market to inform category-level stocking.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `state`: user's state
   - `dealer_type`: user's dealer type
   - `ranking_dimensions`: `body_type`
   - `ranking_measure`: `average_days_on_market`
   - `ranking_order`: `asc`
   - `top_n`: `10`

2. Call `mcp__marketcheck__get_sold_summary` with:
   - Same date/location/dealer_type filters
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_days_on_market`
   - `ranking_order`: `asc`
   - `top_n`: `10`

3. Also call with `ranking_order`: `desc` and `top_n`: `10` to get the **slowest** turning models.

4. Present three tables:
   - **Turn Rate by Body Type** — columns: Body Type, Avg DOM, Sold Count, Interpretation
   - **Fastest Turning Models (Top 10)** — columns: Make, Model, Avg DOM, Sold Count
   - **Slowest Turning Models (Bottom 10)** — columns: Make, Model, Avg DOM, Sold Count

5. Provide a recommendation: "Focus acquisition on segments with Avg DOM < X days (market median). Avoid over-stocking in segments where Avg DOM exceeds Y days unless priced aggressively."

## Workflow: New vs Used Mix Analysis

Determine the optimal new-to-used inventory ratio based on what the market is actually absorbing.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `state`: user's state
   - `inventory_type`: `New`
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `10`

2. Call `mcp__marketcheck__get_sold_summary` with same filters but:
   - `inventory_type`: `Used`

3. Call `mcp__marketcheck__search_active_cars` for current supply:
   - `state`: user's state
   - `car_type`: `new`
   - `seller_type`: `dealer`
   - `facets`: `make|0|30|2`
   - `rows`: `0`

4. Repeat with `car_type`: `used`.

5. Calculate:
   - **Market Absorption Ratio**: New Sold / (New Sold + Used Sold) for the market
   - **Current Supply Ratio**: New Active / (New Active + Used Active) on lots
   - **Gap**: If supply ratio significantly exceeds absorption ratio, the market is over-indexed on new (or used)

6. Present as:
   - Summary box: "Market absorbed X% New / Y% Used last month. Dealers currently stock A% New / B% Used. Recommendation: [shift toward new/used/hold steady]."
   - Breakdown table by make with columns: Make, New Sold, Used Sold, New % of Sales, Current New Supply, Current Used Supply, Supply vs Demand Alignment

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Demand-to-Supply Ratio | Ratio per make/model in the user's market | Identifies under-served segments; each correct stocking decision can add $1,500-3,000 in front-end gross |
| Average DOM by Segment | Days on market for body type and make/model | Every day over 45 DOM costs ~$30 in floor plan interest; reducing avg DOM by 10 days saves ~$300/unit |
| Aged Unit Count (60+ / 90+ DOM) | Total units and estimated carrying cost | A 200-unit dealer with 15% aged inventory burns ~$13,500/month in excess floor plan |
| Turn Rate | Monthly sold / avg inventory level | Industry benchmark: 8-12 turns/year for used; dealers below 8 should investigate mix |
| New vs Used Mix Alignment | Current lot ratio vs market absorption ratio | Misaligned mix ties up capital; a 5-point shift toward market demand can improve turns by 0.5-1.0/year |
| Price-to-Market Gap on Aged Units | Listed price vs predicted market price | Overpriced aged units represent the largest single source of preventable loss |

## Action-to-Outcome Funnel

1. **Scenario: Dealer says "I don't know what to buy at auction this week."**
   Run *Market Demand Snapshot* then *What Should I Stock?* Present the top 5 under-supplied models with price guidance from `predict_price_with_comparables`. Recommend: "Target these models at auction. Acquire at or below predicted wholesale price for maximum margin."

2. **Scenario: Used Car Manager asks "What's sitting too long on my lot?"**
   Run *Aging Inventory Alert*. For each unit over 90 DOM with a positive price gap, recommend an immediate price reduction to predicted market value. For units with negative gap already, recommend wholesale exit. Quantify: "These 8 units are costing you approximately $7,200/month in floor plan interest."

3. **Scenario: GM asks "Should I be stocking more SUVs or sedans?"**
   Run *Turn Rate by Segment* + *New vs Used Mix Analysis*. Compare DOM and volume by body type. If SUVs turn in 28 days and sedans in 52 days in the local market, recommend shifting mix toward SUVs. Quantify the DOM savings and capital velocity improvement.

4. **Scenario: OEM Regional Manager asks "How are my dealers stocking compared to demand?"**
   Run *Market Demand Snapshot* filtered by the OEM's make, then *What Should I Stock?* across the region. Identify which models are under-represented on dealer lots relative to consumer demand. Provide dealer-level or state-level recommendations for allocation adjustments.

5. **Scenario: Dealer group CFO asks "Where is our floor plan exposure highest?"**
   Run *Aging Inventory Alert* across multiple dealer_ids. Aggregate the carrying cost exposure by rooftop. Rank locations by total aged-unit floor plan burn. Recommend priority actions for the top 3 most exposed stores.

## Output Format

- **Lead with the headline number.** Example: "Your market sold 1,247 used SUVs last month. You have 3 units in stock. Demand-to-supply ratio: 415:1."
- **Use tables** for ranked data (top models, body types, aging units). Keep tables to 10-20 rows max; offer to show more if needed.
- **Color-code signals** in text: use "UNDER-SUPPLIED", "BALANCED", "OVER-SUPPLIED" labels clearly.
- **Always include dollar impact** when discussing aging or stocking recommendations. Dealers think in dollars, not abstractions.
- **End with 3 specific action items** the user can execute today (e.g., "1. Reduce price on VIN ...X4532 by $2,100 to match market. 2. Target 2024 Toyota RAV4 at auction below $28,500. 3. Wholesale the 3 sedans over 120 DOM to free up $87,000 in floor plan.").
- **Cite the data period** in every output (e.g., "Based on January 2026 sold data for Texas franchise dealers").
