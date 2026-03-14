---
name: inventory-intelligence
description: >
  This skill should be used when the user asks to "what should I stock",
  "what's selling in my area", "market demand analysis", "aging inventory alert",
  "turn rate by segment", "slow movers on my lot", "inventory analysis",
  "demand vs supply ratio", "what to buy at auction", "floor plan optimization",
  "new vs used mix", "days on market by model", or needs help with
  data-driven stocking decisions, inventory aging analysis, or demand-to-supply
  intelligence for a dealership location within the group.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Inventory Intelligence — Data-Driven Stocking & Aging Analysis

Turn sold market data and live supply counts into actionable stocking recommendations. Replace gut-instinct buying with demand-to-supply ratios, aging alerts, turn-rate benchmarks, and optimal new-vs-used mix targets.

## Dealer Group Profile (Load First)

Load `~/.claude/marketcheck/dealership-group-profile.json`. If missing, prompt `/onboarding` and ask minimum fields. Extract from location: `dealer_id`, `source` (web domain), `dealer_type`, `franchise_brands`, `zip`, `state`; from profile: `country`, `dom_aging_threshold`. US: all tools. UK: `search_uk_active_cars` + `search_uk_recent_cars` only (skip Market Demand, Turn Rate, New vs Used Mix, D/S Ratio). Confirm location.

## User Context

Inventory director or location GM making data-driven stocking decisions using demand-to-supply ratios, aging alerts, and turn-rate benchmarks.

Auto-loaded from profile: `state`, `dealer_id`, `source` (web domain), `franchise_brands`, `dealer_type`. Ask: timeframe (default: last full month), inventory type (New/Used/Both). For lot-level workflows: use `dealer_id` first; if null, use `source` (web domain); if both null, ask the user.

## Workflow: Market Demand Snapshot

Understand what is actually selling in the location's market before making any stocking decisions.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target month first-to-last day
   - `state`: selected location's state code
   - `dealer_type`: selected location's dealer type (Franchise or Independent)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   → **Extract only**: per make/model — `sold_count`, `average_sale_price`, `average_days_on_market`. Discard full response.

2. Call `mcp__marketcheck__get_sold_summary` with the same date and location filters, but:
   - `ranking_dimensions`: `body_type`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `10`
   → **Extract only**: per body_type — `sold_count`, share %. Discard full response.

3. Present results as two ranked tables:
   - **Top 20 Models by Sales Volume** — columns: Rank, Make, Model, Sold Count, Avg Sale Price, Avg DOM
   - **Sales by Body Type** — columns: Body Type, Sold Count, Share of Total (%)

4. Highlight any body type or model where the location's franchise brand appears in the top 5, and flag segments where it does not appear (potential conquest or gap opportunities).

## Workflow: What Should I Stock? (Demand-to-Supply Ratio)

Compare what the market is buying against what dealers currently have listed. Vehicles with high demand and low supply represent stocking opportunities.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `state`: selected location's state
   - `dealer_type`: selected location's dealer type
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `30`
   → **Extract only**: per make/model — `sold_count`. Discard full response.

2. Call `mcp__marketcheck__search_active_cars` with:
   - `state`: selected location's state (or `zip` + `radius` if provided)
   - `car_type`: `used` (or `new` based on user focus)
   - `seller_type`: `dealer`
   - `dealer_type`: selected location's dealer type
   - `facets`: `make|0|50|2,model|0|50|2`
   - `rows`: `0`
   → **Extract only**: per make/model — active count from facets. Discard full response.

3. For each of the top 30 sold make/model combinations, look up the active supply count from the facet results.

4. Calculate **Demand-to-Supply Ratio** = Sold Count (monthly) / Active Supply Count.
   - Ratio > 1.5 = **Under-supplied** (strong stocking opportunity)
   - Ratio 0.8 - 1.5 = **Balanced**
   - Ratio < 0.8 = **Over-supplied** (avoid stocking more)

5. Present a single table sorted by demand-to-supply ratio descending:
   - Columns: Make, Model, Monthly Sold, Active Supply, D/S Ratio, Signal (Under-supplied / Balanced / Over-supplied)
   - Bold or call out the top 5 under-supplied models as priority acquisition targets.

## Workflow: Aging Inventory Alert

Identify units on the selected location's lot that have exceeded healthy DOM thresholds and assess their current market value.

**Multi-agent approach:** Use the `lot-scanner` and `lot-pricer` agents for complete, paginated results.

**Step 1 — Pull aged inventory (paginated):**

Use the Agent tool to spawn the `dealership-group:lot-scanner` agent with this prompt:

> Pull aging inventory for dealer_id=[dealer_id] (or source=[web_domain] if dealer_id unavailable), country=[country], car_type=used, sort_by=dom, sort_order=desc, dom_range=[dom_aging_threshold]-999. Paginate through all results.

This ensures ALL aged units are captured, not just the first 25.

**Step 2 — Price aged units (US only):**

After lot-scanner returns, use the Agent tool to spawn the `dealership-group:lot-pricer` agent with this prompt:

> Price these aging vehicles: [pass vehicle list from lot-scanner]. zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[dom_aging_threshold].

**UK dealers:** Price inline using comp medians from `search_uk_active_cars`.

**Step 3 — Build the report** from lot-pricer output:

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
   - `state`: selected location's state
   - `dealer_type`: selected location's dealer type
   - `ranking_dimensions`: `body_type`
   - `ranking_measure`: `average_days_on_market`
   - `ranking_order`: `asc`
   - `top_n`: `10`
   → **Extract only**: per body_type — `average_days_on_market`, `sold_count`. Discard full response.

2. Call `mcp__marketcheck__get_sold_summary` with:
   - Same date/location/dealer_type filters
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_days_on_market`
   - `ranking_order`: `asc`
   - `top_n`: `10`
   → **Extract only**: per make/model — `average_days_on_market`, `sold_count`. Discard full response.

3. Also call with `ranking_order`: `desc` and `top_n`: `10` to get the **slowest** turning models.
   → **Extract only**: per make/model — `average_days_on_market`, `sold_count`. Discard full response.

4. Present three tables:
   - **Turn Rate by Body Type** — columns: Body Type, Avg DOM, Sold Count, Interpretation
   - **Fastest Turning Models (Top 10)** — columns: Make, Model, Avg DOM, Sold Count
   - **Slowest Turning Models (Bottom 10)** — columns: Make, Model, Avg DOM, Sold Count

5. Provide a recommendation: "Focus acquisition on segments with Avg DOM < X days (market median). Avoid over-stocking in segments where Avg DOM exceeds Y days unless priced aggressively."

## Workflow: New vs Used Mix Analysis

Determine the optimal new-to-used inventory ratio based on what the market is actually absorbing.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `state`: selected location's state
   - `inventory_type`: `New`
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `10`
   → **Extract only**: per make — `sold_count`. Discard full response.

2. Call `mcp__marketcheck__get_sold_summary` with same filters but:
   - `inventory_type`: `Used`
   → **Extract only**: per make — `sold_count`. Discard full response.

3. Call `mcp__marketcheck__search_active_cars` for current supply:
   - `state`: selected location's state
   - `car_type`: `new`
   - `seller_type`: `dealer`
   - `facets`: `make|0|30|2`
   - `rows`: `0`
   → **Extract only**: per make — active count from facets. Discard full response.

4. Repeat with `car_type`: `used`.
   → **Extract only**: per make — active count from facets. Discard full response.

5. Calculate:
   - **Market Absorption Ratio**: New Sold / (New Sold + Used Sold) for the market
   - **Current Supply Ratio**: New Active / (New Active + Used Active) on lots
   - **Gap**: If supply ratio significantly exceeds absorption ratio, the market is over-indexed on new (or used)

6. Present as:
   - Summary box: "Market absorbed X% New / Y% Used last month. Dealers currently stock A% New / B% Used. Recommendation: [shift toward new/used/hold steady]."
   - Breakdown table by make with columns: Make, New Sold, Used Sold, New % of Sales, Current New Supply, Current Used Supply, Supply vs Demand Alignment

## Output

Present: headline number (e.g., D/S ratio or aged unit count with dollar impact), ranked data tables (models, body types, aging units), clear signal labels (UNDER-SUPPLIED / BALANCED / OVER-SUPPLIED), and 3 specific actionable items with dollar estimates. Cite data period.
