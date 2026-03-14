---
name: inventory-intelligence
description: >
  This skill should be used when the user asks about "regional demand",
  "what's selling in my states", "demand analysis", "demand-to-supply ratio",
  "turn rate by segment", "inventory analysis", "production guidance",
  "state-level demand", "supply intelligence", "new vs used mix",
  "segment demand heatmap", "allocation planning", "regional demand intelligence",
  or needs help with regional demand analysis, supply-demand ratios,
  segment turn rates, or production and allocation guidance for OEMs.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Inventory Intelligence — Regional Demand Intelligence for OEMs

Turn sold market data and live supply counts into regional demand intelligence for production guidance, allocation planning, and competitive market positioning. Replace quarterly reports with real-time demand-to-supply signals by state, segment, and model.

## Manufacturer Profile (Load First)

Load `~/.claude/marketcheck/manufacturer-profile.json` if exists. Extract: `brands`, `states`, `competitor_brands`, `country`. If missing, ask brand, states, and competitors. US-only (requires `get_sold_summary` and `search_active_cars`); if UK, inform not available. Confirm profile.

## User Context

User is an OEM regional manager, distributor, or allocation strategist needing demand-vs-supply intelligence for production guidance and inventory allocation.

| Field | Source |
|-------|--------|
| Brand focus | Profile `manufacturer.brands` |
| Geographic scope | Profile `manufacturer.states` or "national" |
| Timeframe | Most recent full month (default); ask for custom |
| Inventory type | New, Used, or Both (default Both) |
| Segment focus | Optional: body_type or specific models |

## Workflow: Regional Demand Snapshot

Understand what is selling in your states — by model, segment, and volume — to inform allocation decisions.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from`: first day of the target month
   - `date_to`: last day of the target month
   - `state`: user's state (run for each state if multiple)
   - `make`: your brand (from profile)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   → **Extract only**: per model — `sold_count`, `average_sale_price`, `average_days_on_market`. Discard full response.

2. Call `mcp__marketcheck__get_sold_summary` for competitors in the same states:
   - `make`: each competitor brand
   - Same date/state/dimension filters
   → **Extract only**: per model — `sold_count`, `average_sale_price`. Discard full response.

3. Call `mcp__marketcheck__get_sold_summary` for segment breakdown:
   - `ranking_dimensions`: `body_type`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `10`
   - Filter by `make` for your brand, then repeat without make filter for total market
   → **Extract only**: per body_type — `sold_count` per brand and total market. Discard full response.

4. Present results as:
   - **Your Brand Top 20 Models by Sales Volume in [State]** — columns: Rank, Model, Sold Count, Avg Sale Price, Avg DOM
   - **Segment Demand in [State]** — columns: Body Type, Your Brand Sold, Total Market Sold, Your Brand Share %, Competitor Share %
   - Highlight segments where your brand underperforms the market share — these are allocation opportunities
   - Highlight segments where competitors are outselling you — competitive threats

## Workflow: Demand-to-Supply Ratio (Production Guidance)

Compare what the market is buying against what is currently available. High demand + low supply = increase production/allocation. Low demand + high supply = reduce allocation or increase incentives.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `state`: your state(s)
   - `make`: your brand
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `30`
   → **Extract only**: per model — `sold_count`. Discard full response.

2. Call `mcp__marketcheck__search_active_cars` with:
   - `state`: your state(s)
   - `make`: your brand
   - `car_type`: `new` (or `used` based on focus)
   - `seller_type`: `dealer`
   - `facets`: `model|0|50|2`
   - `rows`: `0`
   → **Extract only**: per model — active count from facets. Discard full response.

3. For each model, calculate **Demand-to-Supply Ratio** = Sold Count (monthly) / Active Supply Count.
   - Ratio > 1.5 = **Under-supplied** (increase allocation — demand exceeds supply)
   - Ratio 0.8 - 1.5 = **Balanced** (maintain current allocation)
   - Ratio < 0.8 = **Over-supplied** (reduce allocation or increase incentives)

4. Repeat for competitor brands to see their D/S ratios for comparison.

5. Present a single table sorted by D/S ratio descending:
   - Columns: Model, Monthly Sold, Active Supply, D/S Ratio, Signal (Under-supplied / Balanced / Over-supplied), Competitor D/S for Same Segment
   - **Production Guidance**: "Increase allocation for [Model A] (D/S 2.3) — demand significantly exceeds supply. Reduce allocation for [Model B] (D/S 0.5) — 90+ day supply on dealer lots."

## Workflow: Turn Rate by Segment

Benchmark how quickly different vehicle segments move in your states to inform segment-level production and allocation.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `state`: your state(s)
   - `make`: your brand
   - `ranking_dimensions`: `body_type`
   - `ranking_measure`: `average_days_on_market`
   - `ranking_order`: `asc`
   - `top_n`: `10`
   → **Extract only**: per body_type — `average_days_on_market`, `sold_count`. Discard full response.

2. Repeat without `make` filter to get market-wide turn rates for comparison.
   → **Extract only**: per body_type — `average_days_on_market`. Discard full response.

3. Call for model-level turn rates:
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_days_on_market`
   - `ranking_order`: `asc` and then `desc`
   - `top_n`: `10` each
   → **Extract only**: per make/model — `average_days_on_market`, `sold_count`. Discard full response.

4. Present three tables:
   - **Your Brand Turn Rate by Segment** — columns: Body Type, Your Avg DOM, Market Avg DOM, Difference, Your Sold Count
   - **Your Fastest Turning Models** — columns: Model, Avg DOM, Sold Count (demand is strong)
   - **Your Slowest Turning Models** — columns: Model, Avg DOM, Sold Count (may need incentives or allocation reduction)

5. Recommendation: "Your SUVs turn in X days vs market average of Y days — [faster/slower] than competitors. Your [Model] turns fastest at Z days, suggesting under-allocation. [Model B] is slowest at W days — consider incentive support or allocation reduction."

## Workflow: State-Level Demand Heatmap

Map demand across all your responsible states to identify allocation priorities.

1. For your brand, call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `make`: your brand
   - `summary_by`: `state`
   - `limit`: `51`
   → **Extract only**: per state — `sold_count`, `average_sale_price`. Discard full response.

2. Repeat for each competitor brand.
   → **Extract only**: per state — `sold_count`. Discard full response.

3. For each state, calculate:
   - **Your brand volume and share**
   - **Competitor volume and share**
   - **Your share vs national average** (over-indexed or under-indexed?)
   - **Demand-to-supply ratio** by state

4. Present:
   - **State Demand Table**: State, Your Brand Sold, Your Share %, National Avg Share %, Over/Under Index, Top Competitor Sold, Competitor Share %
   - Sort by your brand volume descending
   - Flag states where you are under-indexed (share < national avg) as **GROWTH OPPORTUNITIES**
   - Flag states where competitors outsell you as **COMPETITIVE THREATS**

5. **Allocation Recommendation**: "Your brand is under-indexed in [State A] (X% vs Y% national) while [Competitor] holds Z%. Increasing allocation by N units/month could capture estimated W additional sales. Your strongest state is [State B] at XX% share — maintain or grow."

## Workflow: New vs Used Market Mix

Understand the new-to-used sales ratio in your states to inform production vs CPO strategy.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: most recent full month
   - `state`: your state(s)
   - `make`: your brand
   - `inventory_type`: `New`
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `sold_count`
   - `top_n`: `10`
   → **Extract only**: per make — `sold_count`. Discard full response.

2. Repeat with `inventory_type`: `Used`.
   → **Extract only**: per make — `sold_count`. Discard full response.

3. Repeat both calls for competitor brands.
   → **Extract only**: per make — `sold_count` per inventory type. Discard full response.

4. Calculate:
   - **Your New/Used Ratio** = New Sold / (New + Used) for your brand
   - **Market New/Used Ratio** for the total market
   - **Competitor New/Used Ratios**

5. Present:
   - Summary: "In [State], your brand's new/used mix is X% / Y%. The market average is A% / B%. [Competitor] is at C% / D%."
   - If your used volume is disproportionately low: "Your brand has low used market presence — consider strengthening CPO programs to improve resale ecosystem and brand value retention."
   - If your new volume share exceeds used: "Strong new vehicle demand — production levels are well-matched to the market."

## Output

Present: demand signal headline with competitive context, ranked data tables (D/S ratios, turn rates, state heatmap) with UNDER-SUPPLIED/BALANCED/OVER-SUPPLIED labels, and 3 specific allocation/production recommendations citing the data period.
