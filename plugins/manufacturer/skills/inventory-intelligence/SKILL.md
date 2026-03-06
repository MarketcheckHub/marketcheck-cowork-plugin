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

# Inventory Intelligence — Regional Demand Intelligence for OEMs

Turn sold market data and live supply counts into regional demand intelligence for production guidance, allocation planning, and competitive market positioning. Replace quarterly reports with real-time demand-to-supply signals by state, segment, and model.

## Manufacturer Profile (Load First)

Before running any workflow, check for a saved manufacturer profile:

1. Read `~/.claude/marketcheck/manufacturer-profile.json`
2. If the file **does not exist**: Ask: "Which brand(s) do you represent?", "Which states?", and "Which competitors to track?" This skill works without a profile but is much more useful with one.
3. If the file **exists**, extract and use silently:
   - `brands` ← `manufacturer.brands` — your brands
   - `states` ← `manufacturer.states` — your responsible states
   - `competitor_brands` ← `manufacturer.competitor_brands` — competitive context
   - `country` ← `location.country`
4. **Country note:** This skill requires `get_sold_summary` and `search_active_cars` which are **US-only**. If `country == UK`, inform: "Regional demand intelligence requires US sold data. Not available for UK."
5. Confirm briefly: "Using profile: **[user_name]** — Regional demand for **[brands]** across **[states]**"

## User Context

The primary user is an **OEM regional manager, distributor, product planner, or allocation strategist** who needs to understand what is selling where, at what rate, and how supply compares to demand — to inform production guidance and inventory allocation decisions.

Before running workflows, collect:

- **Brand focus**: From profile `manufacturer.brands` — your brands
- **Geographic scope**: From profile `manufacturer.states` — your responsible states, or "national"
- **Timeframe**: Default to the most recent full month; ask if they want a custom date range
- **Inventory type**: New, Used, or Both (default Both)
- **Segment focus** (optional): body_type or specific models

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

2. Call `mcp__marketcheck__get_sold_summary` for competitors in the same states:
   - `make`: each competitor brand
   - Same date/state/dimension filters

3. Call `mcp__marketcheck__get_sold_summary` for segment breakdown:
   - `ranking_dimensions`: `body_type`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `10`
   - Filter by `make` for your brand, then repeat without make filter for total market

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

2. Call `mcp__marketcheck__search_active_cars` with:
   - `state`: your state(s)
   - `make`: your brand
   - `car_type`: `new` (or `used` based on focus)
   - `seller_type`: `dealer`
   - `facets`: `model|0|50|2`
   - `rows`: `0` (we only need facet counts)

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

2. Repeat without `make` filter to get market-wide turn rates for comparison.

3. Call for model-level turn rates:
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_days_on_market`
   - `ranking_order`: `asc` and then `desc`
   - `top_n`: `10` each

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

2. Repeat for each competitor brand.

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

2. Repeat with `inventory_type`: `Used`.

3. Repeat both calls for competitor brands.

4. Calculate:
   - **Your New/Used Ratio** = New Sold / (New + Used) for your brand
   - **Market New/Used Ratio** for the total market
   - **Competitor New/Used Ratios**

5. Present:
   - Summary: "In [State], your brand's new/used mix is X% / Y%. The market average is A% / B%. [Competitor] is at C% / D%."
   - If your used volume is disproportionately low: "Your brand has low used market presence — consider strengthening CPO programs to improve resale ecosystem and brand value retention."
   - If your new volume share exceeds used: "Strong new vehicle demand — production levels are well-matched to the market."

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Demand-to-Supply Ratio | Ratio per model in your states | D/S > 1.5 = increase allocation; D/S < 0.8 = reduce; each correct decision adds $1,500-3,000 margin per unit |
| Average DOM by Segment | Days on market for your models vs market | Every day over optimal DOM signals demand/supply imbalance; informs production pacing |
| State-Level Volume Share | Your share vs national average per state | Under-indexed states represent growth opportunities; 1% share improvement in a large state = thousands of units |
| Segment Demand Mix | Which body types sell most in which states | Informs model-specific allocation; wrong mix = aged inventory and incentive spend |
| New/Used Market Ratio | Balance of new vs used sales by market | Informs CPO strategy and production levels; healthy ecosystems have strong used markets |
| Competitive D/S Gap | Your D/S ratio vs competitor D/S in same segment | Reveals where competitors are better matching supply to demand |

## Action-to-Outcome Funnel

1. **Scenario: Regional manager asks "What's selling in my states?"**
   Run *Regional Demand Snapshot* for each state. Show top models, segment demand, and competitive context. Recommend: "SUVs dominate demand in Texas (X% of market). Your [Model] is #Y in the state but competitor [Model] leads. Focus allocation on [Model] to close the gap."

2. **Scenario: Allocation planner asks "Where should we send more inventory?"**
   Run *State-Level Demand Heatmap*. Identify under-indexed states where competitors outsell you. Cross-reference with *D/S Ratio*. Recommend: "You're under-indexed in Florida (X% share vs Y% national). D/S ratio of 2.1 on [Model] means demand significantly exceeds supply. Increase allocation by N units/month."

3. **Scenario: Product planner asks "Which segments should we prioritize?"**
   Run *Turn Rate by Segment* across your states. Identify segments turning fastest (strong demand) and slowest (weak demand). Recommend: "SUVs turn X days faster than sedans in your states. Consider shifting production mix toward SUV variants."

4. **Scenario: Strategy team asks "How does our supply match demand by model?"**
   Run *D/S Ratio* for all your models across your states. Present a production guidance table. Recommend: "3 models are under-supplied (D/S > 1.5) — ramp production. 2 models are over-supplied (D/S < 0.8) — reduce allocation or deploy targeted incentives."

## Output Format

- **Lead with the demand signal.** Example: "In Texas, your brand sold 4,200 SUVs last month — 18% market share. Competitor Honda sold 5,100 (22% share). Your demand-to-supply ratio of 1.8 suggests allocation should increase."
- **Use tables** for ranked data. Keep tables to 10-20 rows max.
- **Use "UNDER-SUPPLIED", "BALANCED", "OVER-SUPPLIED" labels** clearly.
- **Always include competitive context** — your numbers alone do not tell the story.
- **End with 3 specific allocation/production recommendations** the user can act on.
- **Cite the data period** in every output: "Based on [Month Year] sold data for [States/National]."
