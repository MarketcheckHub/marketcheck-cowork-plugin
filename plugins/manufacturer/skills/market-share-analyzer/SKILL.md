---
name: market-share-analyzer
description: >
  This skill should be used when the user asks about "market share",
  "who is winning in SUVs", "competitor analysis", "brand performance comparison",
  "segment share breakdown", "conquest analysis", "regional demand heatmap",
  "quarterly share change", "which brands are gaining share",
  "how is my brand doing", "competitive intelligence", "share gains",
  "share losses", or needs help with competitive positioning, OEM benchmarking,
  segment-level market share tracking, or brand performance analysis
  using sold vehicle data.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Share Analyzer — Competitive Intelligence for OEMs & Brand Strategists

Convert MarketCheck sold transaction data into real-time competitive intelligence. Track your brand's market share vs competitors, segment conquest patterns, regional demand distribution, and EV adoption curves — all without waiting 60-90 days for traditional syndicated reports.

## Manufacturer Profile (Load First)

Load `~/.claude/marketcheck/manufacturer-profile.json` if exists. Extract: `brands`, `states`, `competitor_brands`, `country`, `user_name`, `company`. If missing, ask brand, states, and competitors. US-only (requires `get_sold_summary`); if UK, inform not available. Confirm profile.

## User Context

User is an OEM regional manager, brand strategist, or distributor needing competitive intelligence for allocation, incentive strategy, and product positioning.

| Field | Source |
|-------|--------|
| Geographic scope | Profile `manufacturer.states` or ask; default national |
| Time period | Month (first-to-last day); quarterly = 3 months aggregated |
| Comparison period | Prior month, prior quarter, or YoY |
| Brand focus | Profile `manufacturer.brands` (star as "YOUR BRANDS") |
| Competitor focus | Profile `manufacturer.competitor_brands` |
| Segment focus | Optional: body_type or fuel_type_category |
| Inventory type | New, Used, or Both (default Both) |

## Workflow: Brand Market Share

Calculate market share by make for a given period and compare against a prior period to identify gainers and losers. Frame as COMPETITIVE INTELLIGENCE — show own brand vs competitors.

1. Call `mcp__marketcheck__get_sold_summary` for the **current period**:
   - `date_from` / `date_to`: target month first-to-last day
   - `state`: user's state filter (omit for national)
   - `inventory_type`: as specified (or omit for both)
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   → **Extract only**: per make — `sold_count`, total `sold_count`. Discard full response.

2. Repeat for the **prior period** with identical filters but adjusted dates.
   → **Extract only**: per make — `sold_count`, total `sold_count`. Discard full response.

3. Calculate for each make:
   - **Current Share %** = Make Sold / Total Sold × 100
   - **Prior Share %** = same for prior period
   - **Share Change (bps)** = (Current % - Prior %) × 100
   - **Volume Change %** = (Current Sold - Prior Sold) / Prior Sold × 100

4. Present as a ranked table:
   - Columns: Rank, Make, Current Sold, Current Share %, Prior Sold, Prior Share %, Share Change (bps), Volume Change %
   - Sort by Current Share % descending
   - **Mark the user's own brands with a star and bold** (e.g., "**Toyota** ★")
   - **Highlight competitor brands** from profile in the table
   - Flag makes gaining > 50 bps as "GAINING" and losing > 50 bps as "LOSING"

5. Add a **Competitive Intelligence Summary**:
   - "YOUR BRANDS: [Brand] holds [X]% share (#Y position), [up/down] [N] bps from [comparison period]. [Second brand if applicable]."
   - "COMPETITORS: [Competitor A] at [X]% ([+/-N] bps), [Competitor B] at [X]% ([+/-N] bps). [Competitor A] is your closest threat in [state/national] market."
   - "SHARE SHIFT: The top 3 gainers were [X], [Y], [Z], collectively picking up [N] bps. Net share flow from your brands to competitors: [+/-N] bps."

## Workflow: Segment Conquest Analysis

Determine which brands are winning within specific vehicle segments (body types) and identify where your brand is gaining or losing ground.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `state`: user's state filter (omit for national)
   - `body_type`: target segment (e.g. `SUV`)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `15`
   → **Extract only**: per make/model — `sold_count`. Discard full response.

2. Repeat for comparison period.
   → **Extract only**: per make/model — `sold_count`. Discard full response.

3. If the user wants multi-segment comparison, repeat step 1 for each body_type: `SUV`, `Sedan`, `Pickup`, `Hatchback`, `Coupe`, `Van/Minivan`.

4. For each segment, calculate:
   - **Segment leader** and their share %
   - **Your brand's rank** within the segment
   - **Gap to leader** in units and share points
   - **Fastest gaining model** in the segment (largest positive bps change)
   - **Which competitor brands are gaining on you** in this segment

5. Present per-segment tables:
   - Columns: Rank, Make, Model, Sold Count, Segment Share %, Prior Share %, Change (bps)
   - Mark your brands with ★, highlight competitors
   - Also present a **Segment Summary** table: Segment, Leader, Leader Share %, Your Brand Rank, Your Brand Share %, Gap to Leader, Top Competitor Threat

6. Conquest insight: "In the SUV segment, [Competitor A] gained 120 bps primarily through [Model X] (+3,200 units), directly taking share from your [Model Y]. To recapture, consider incentive targeting on [Model Y] which competes directly and currently has higher DOM."

## Workflow: EV Adoption Tracking

Monitor electric and hybrid vehicle penetration rates for your brand vs competitors.

1. Call `mcp__marketcheck__get_sold_summary` for **EV sales**:
   - `date_from` / `date_to`: target period
   - `state`: user's state filter (omit for national)
   - `fuel_type_category`: `EV`
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `15`
   → **Extract only**: per make/model — `sold_count`; plus total EV `sold_count`. Discard full response.

2. Same filters but `fuel_type_category`: `Hybrid`.
   → **Extract only**: per make/model — `sold_count`; plus total Hybrid `sold_count`. Discard full response.

3. Call for **total market** (no fuel_type_category): `ranking_dimensions`: `make`, `ranking_measure`: `sold_count`, `top_n`: `1`.
   → **Extract only**: total `sold_count`. Discard full response.

4. Repeat steps 1-3 for the prior period to calculate trend.

5. Calculate:
   - **EV Penetration Rate** = EV Sold / Total Sold x 100
   - **Hybrid Penetration Rate** = Hybrid Sold / Total Sold x 100
   - **Combined Electrified Rate** = (EV + Hybrid) / Total x 100
   - **Your Brand EV Penetration** = Your Brand EV Sold / Your Brand Total Sold x 100
   - **Competitor EV Penetration** for each competitor brand
   - **Period-over-period change** for each rate

6. Present:
   - **Your EV Position**: "Your brand's EV penetration is X.X% of your total sales, [above/below] the market average of Y.Y%. [Competitor A] is at Z.Z%."
   - **Top EV Models** table: Rank, Make, Model, Sold Count, Share of EV Segment % — highlight your models and competitor models
   - **EV Brand Share** table: Make, EV Units Sold, % of Brand's Total Sales That Are EV, Market EV Share %

## Workflow: Regional Demand Heatmap

Map your brand's sales volume and pricing by state to reveal geographic strengths and growth opportunities.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `make`: your brand (from profile), `model`: optional
   - `summary_by`: `state`, `limit`: `51`
   → **Extract only**: per state — `sold_count`, `average_sale_price`, `average_days_on_market`. Discard full response.

2. If competitive context needed, repeat for each competitor brand.
   → **Extract only**: per state — `sold_count` per competitor. Discard full response.

3. If pricing context needed, add `ranking_dimensions`: `make,model`, `ranking_measure`: `average_sale_price`, `summary_by`: `state`, `limit`: `51`.
   → **Extract only**: per state — `average_sale_price`. Discard full response.

4. Calculate for each state:
   - **Volume rank** (which states buy the most of your brand)
   - **Your brand share in each state** vs national average
   - **Price rank** (where is it cheapest vs most expensive)
   - **Price-to-national-average ratio** = State Avg Price / National Avg Price
   - **Competitor comparison** in top states

5. Present as a **State-Level Demand Table** sorted by sold count descending:
   - Columns: State, Your Brand Sold, Your Brand Share %, Competitor A Sold, Competitor B Sold, Avg Sale Price, Price vs National Avg, Avg DOM
   - Top 10 states = your stronghold markets
   - Bottom 10 states = potential growth markets
   - States where competitors outsell you significantly = competitive threat zones

6. Summary: "For [Your Brand], Texas leads with X% of your national volume at an average price $Y [above/below] the national average. Your weakest large markets are [State A], [State B], [State C] — where [Competitor A] holds a [X]-unit advantage. Increasing allocation to these states could capture an estimated [N] additional sales based on current demand-to-supply ratios."

## Output

Present: competitive position headline (your brand share, rank, bps change vs competitors), ranked share tables with star on your brands (volume + share % + bps change), key competitive signals, and strategic recommendations (allocation, incentive targeting, segment conquest opportunities). Cite data period and geography.
