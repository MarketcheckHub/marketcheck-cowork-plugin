---
name: inventory-intelligence
description: >
  Inventory aging and demand-to-supply intelligence. Triggers: "what should I stock",
  "what's selling in my area", "market demand analysis", "aging inventory alert",
  "turn rate by segment", "slow movers on my lot", "inventory analysis",
  "demand vs supply ratio", "what to buy at auction", "floor plan optimization",
  "new vs used mix", "days on market by model", data-driven stocking decisions,
  inventory aging analysis, demand-to-supply intelligence.
version: 0.1.0
---

# Inventory Intelligence — Data-Driven Stocking & Aging Analysis

Turn sold market data and live supply counts into actionable stocking recommendations. Replace gut-instinct buying with demand-to-supply ratios, aging alerts, turn-rate benchmarks, and optimal new-vs-used mix targets.

## Dealer Profile (Load First)

→ Full procedure: read `_references/profile-loading.md`

Parse `marketcheck-profile.md` → extract: `dealer_id`, `dealer_type`, `franchise_brands`, `zip`/`postcode`, `state`/`region`, `country`, `dom_aging_threshold`. If missing: tell user to run `/onboarding`.

**Country routing:** US = all tools. UK = `search_uk_active_cars` only. `get_sold_summary` NOT available — skip Market Demand Snapshot, D/S Ratio, Turn Rate, New vs Used Mix. Only Aging Inventory Alert works for UK. → Full matrix: `_references/country-routing.md`

→ Agent contracts (lot-scanner, lot-pricer): read `_references/agent-contracts.md`

Confirm: "Using profile: **[dealer.name]**, [State/Region], [Country]"

## User Context

The following fields are loaded from the dealer profile. Only ask if no profile exists:

- **Role**: Dealer (single rooftop or group) or OEM regional manager — ask if unclear
- **Location**: Auto-loaded from profile (`state` for US, `region` for UK)
- **Dealer ID**: Auto-loaded from profile (used for lot-level queries)
- **Franchise brand(s)**: Auto-loaded from profile
- **Timeframe**: Default to the most recent full month; ask if they want a custom date range
- **Inventory type focus**: New, Used, or Both (default Both) — ask if unclear
- **Dealer type**: Auto-loaded from profile

Do not guess dealer IDs or locations. If the profile has `dealer_id: null`, ask before running lot-level workflows (Aging Inventory Alert, Category Gap).

## Gotchas

- **`seller_type=dealer`** is hardcoded in supply queries — this intentionally excludes private sellers and auction listings to give an accurate dealer-competitive supply count.
- **UK: only Aging Inventory Alert works** — Market Demand Snapshot, D/S Ratio, Turn Rate, and New vs Used Mix all require `get_sold_summary` which is US-only. Inform UK dealers immediately.
- **Facet syntax**: `make|0|50|2` means "facet on make, offset 0, up to 50 buckets, minimum 2 documents per bucket." The min_count of 2 filters out singleton listings.
- **`dealer_id: null` blocks lot-level workflows** — Aging Inventory Alert and Category Gap require a dealer_id. If the profile has `dealer_id: null`, ask before running these workflows.
- **Custom date ranges need validation** — default to the most recent full month. If the user requests a custom range, ensure dates use first-of-month to last-of-month format (e.g., `2026-01-01` to `2026-01-31`).
- **D/S Ratio thresholds differ from stocking-guide** — here, ratio > 1.5 = Under-supplied, 0.8-1.5 = Balanced, < 0.8 = Over-supplied (stocking-guide uses higher thresholds for bid decisions).

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

**Multi-agent approach:** Use the `lot-scanner` and `lot-pricer` agents for complete, paginated results.

**Step 1 — Pull aged inventory (paginated):**

Use the Agent tool to spawn the `marketcheck-cowork-plugin:lot-scanner` agent with this prompt:

> Pull aging inventory for dealer_id=[dealer_id], country=[country], car_type=used, sort_by=dom, sort_order=desc, dom_range=[dom_aging_threshold]-999. Paginate through all results.

This ensures ALL aged units are captured, not just the first 25.

**Step 2 — Price aged units (US only):**

After lot-scanner returns, use the Agent tool to spawn the `marketcheck-cowork-plugin:lot-pricer` agent with this prompt:

> Price these aging vehicles: [pass vehicle list from lot-scanner]. zip=[zip], dealer_type=[dealer_type], floor_plan_per_day=[floor_plan_per_day], aging_threshold=[dom_aging_threshold].

**UK dealers:** Price inline using comp medians from `search_uk_active_cars`.

### Validate (after Step 2)
- [ ] `lot-scanner` returned `pagination_status=complete` — if `partial`, warn user in output
- [ ] `lot-pricer` returned pricing for all passed VINs — if some failed, note count in output
- [ ] No `predicted_price = $0` or null in pricing output
- [ ] Every VIN in pricing output matches a VIN from lot-scanner aging results

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

## KPIs & Business Impact

→ After assembling results, read `references/outcomes.md` to frame recommendations with quantified business impact, KPI benchmarks, and action-to-outcome guidance.

## Output Format

- **Lead with the headline number.** Example: "Your market sold 1,247 used SUVs last month. You have 3 units in stock. Demand-to-supply ratio: 415:1."
- **Use tables** for ranked data (top models, body types, aging units). Keep tables to 10-20 rows max; offer to show more if needed.
- **Color-code signals** in text: use "UNDER-SUPPLIED", "BALANCED", "OVER-SUPPLIED" labels clearly.
- **Always include dollar impact** when discussing aging or stocking recommendations. Dealers think in dollars, not abstractions.
- **End with 3 specific action items** the user can execute today (e.g., "1. Reduce price on VIN ...X4532 by $2,100 to match market. 2. Target 2024 Toyota RAV4 at auction below $28,500. 3. Wholesale the 3 sedans over 120 DOM to free up $87,000 in floor plan.").
- **Cite the data period** in every output (e.g., "Based on January 2026 sold data for Texas franchise dealers").

## Self-Check (before presenting to user)

- [ ] Tables have consistent column counts
- [ ] No $0 or null prices displayed
- [ ] D/S ratios calculated as sold/supply (NOT supply/sold)
- [ ] "UNDER-SUPPLIED" / "BALANCED" / "OVER-SUPPLIED" labels match the threshold definitions
- [ ] Data period cited in every output section
- [ ] Action items include specific dollar amounts and vehicle identifiers
- [ ] Aging alert floor plan burn uses profile's cost/day, not hardcoded $30
