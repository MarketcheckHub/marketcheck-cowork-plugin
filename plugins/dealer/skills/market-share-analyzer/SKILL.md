---
name: market-share-analyzer
description: >
  This skill should be used when the user asks about "market share",
  "who is winning in SUVs", "competitor analysis", "EV adoption rate",
  "dealer group ranking", "segment share breakdown", "brand performance comparison",
  "conquest analysis", "regional demand heatmap", "quarterly share change",
  "which brands are gaining share", "top dealer groups by volume",
  or needs help with competitive intelligence, OEM benchmarking,
  segment-level market share tracking, or EV penetration analysis
  using sold vehicle data.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Share Analyzer — Competitive Intelligence from Sold Data

Convert MarketCheck sold transaction data into real-time market share analytics. Track brand and model-level share, segment conquest patterns, dealer group performance, EV adoption curves, and regional demand distribution — all without waiting 60-90 days for traditional syndicated reports.

## Profile
Load `~/.claude/marketcheck/dealer-profile.json` if exists. Extract: state, franchise_brands, dealer_type, country. If missing, ask. US-only skill (`get_sold_summary`). If UK, inform: "Market share analysis requires US sold data and is not available for UK." Confirm: "Using profile context: [state], [franchise_brands]"

## User Context
Competitive intelligence from sold data — brand share, segment conquest, dealer group benchmarking, EV adoption, regional demand.

| Field | Source | Notes |
|-------|--------|-------|
| Geographic scope | Profile state or ask | National default if unspecified |
| Time period, comparison period | Ask | Month format: YYYY-MM-01 to YYYY-MM-DD; quarterly = 3 months aggregated |
| Brand focus, segment focus | Profile or ask | Optional |
| Inventory type | Ask | New/Used/Both (default Both) |

## Workflow: Brand Market Share

Calculate market share by make for a given period and compare against a prior period to identify gainers and losers.

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
   - Highlight the user's brand of interest in bold
   - Flag makes gaining > 50 bps as "GAINING" and losing > 50 bps as "LOSING"

5. Add a summary paragraph: "The top 3 share gainers this period were [X], [Y], [Z], collectively picking up [N] basis points. The biggest losers were [A], [B], [C]. [User's brand] moved from #X to #Y position with a [+/-N] bps shift."

## Workflow: Segment Conquest Analysis

Determine which brands are winning within specific vehicle segments (body types) and identify conquest opportunities.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `state`: user's state filter (omit for national)
   - `body_type`: target segment (e.g. `SUV`)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `15`
   → **Extract only**: per make/model — `sold_count`; plus total segment `sold_count`. Discard full response.

2. Repeat for comparison period.
   → **Extract only**: per make/model — `sold_count`; plus total segment `sold_count`. Discard full response.

3. If the user wants multi-segment comparison, repeat step 1 for each body_type: `SUV`, `Sedan`, `Pickup`, `Hatchback`, `Coupe`, `Van/Minivan`.

4. For each segment, calculate:
   - **Segment leader** and their share %
   - **User's brand rank** within the segment
   - **Gap to leader** in units and share points
   - **Fastest gaining model** in the segment (largest positive bps change)

5. Present per-segment tables:
   - Columns: Rank, Make, Model, Sold Count, Segment Share %, Prior Share %, Change (bps)
   - Also present a **Segment Summary** table: Segment, Leader, Leader Share %, User Brand Rank, User Brand Share %, Gap to Leader

6. Conquest insight: "In the SUV segment, [Brand A] gained 120 bps primarily through [Model X] (+3,200 units). [User's brand] lost share to [Brand A] and [Brand B]. To recapture, focus on [Model Y] which competes directly and currently has lower DOM."

## Workflow: Dealer Group Benchmarking

Rank dealer groups by sales volume and operational efficiency to identify top performers and laggards.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `state`: user's state filter (omit for national)
   - `ranking_dimensions`: `dealership_group_name`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`
   → **Extract only**: per group — `sold_count`. Discard full response.

2. Same filters but `ranking_measure`: `average_days_on_market`, `ranking_order`: `asc`.
   → **Extract only**: per group — `average_days_on_market`. Discard full response.

3. Same filters but `ranking_measure`: `average_sale_price`, `ranking_order`: `desc`.
   → **Extract only**: per group — `average_sale_price`. Discard full response.

4. Merge the three result sets by dealership_group_name. Build a **Dealer Group Leaderboard**:
   - Columns: Rank (by volume), Dealer Group, Sold Count, Market Share %, Avg DOM, Avg Sale Price, Efficiency Score
   - **Efficiency Score** = Sold Count / Avg DOM (higher is better — moves more units faster)

5. If the user specifies a make, add a `make` filter to all calls to see dealer group performance within a single brand's network.

6. Provide analysis: "AutoNation leads in volume with X units (Y% share) but Lithia has the lowest average DOM at Z days, suggesting faster inventory turns. For [Brand] specifically, the top 3 performing groups are..."

## Workflow: EV Adoption Tracking

Monitor electric and hybrid vehicle penetration rates over time against the total market.

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
   → **Extract only**: same fields per period. Discard full response.

5. Calculate:
   - **EV Penetration Rate** = EV Sold / Total Sold × 100
   - **Hybrid Penetration Rate** = Hybrid Sold / Total Sold × 100
   - **Combined Electrified Rate** = (EV + Hybrid) / Total × 100
   - **Period-over-period change** for each rate

6. Present:
   - **EV Penetration Summary**: "EVs represented X.X% of [state/national] sales in [month], [up/down] from Y.Y% in [comparison month]. Hybrids were Z.Z%."
   - **Top EV Models** table: Rank, Make, Model, Sold Count, Share of EV Segment %
   - **Top Hybrid Models** table: same structure
   - **EV Brand Share** table: Make, EV Units Sold, % of Brand's Total Sales That Are EV (shows which OEMs are most electrified)

## Workflow: Regional Demand Heatmap

Map sales volume and pricing by state for a specific make or model to reveal geographic demand patterns.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `make`: target make (required), `model`: optional
   - `summary_by`: `state`, `limit`: `51`
   → **Extract only**: per state — `sold_count`, `average_sale_price`, `average_days_on_market`. Discard full response.

2. If pricing context needed, add `ranking_dimensions`: `make,model`, `ranking_measure`: `average_sale_price`, `summary_by`: `state`, `limit`: `51`.
   → **Extract only**: per state — `average_sale_price`. Discard full response.

3. Calculate for each state:
   - **Volume rank** (which states buy the most of this make/model)
   - **Price rank** (where is it cheapest vs most expensive)
   - **Price-to-national-average ratio** = State Avg Price / National Avg Price

4. Present as a **State-Level Demand Table** sorted by sold count descending:
   - Columns: State, Sold Count, % of National Volume, Avg Sale Price, Price vs National Avg, Avg DOM
   - Top 10 states get detailed analysis
   - Bottom 10 states flagged as potential growth markets

5. If model specified, also pull `ranking_dimensions`: `make` for same body_type (no make/model filter) in top 3 states for competitive context.

6. Summary: "For [Make Model], Texas leads with X% of national volume at an average price $Y [above/below] the national average. The least penetrated large markets are [State A], [State B], [State C] — representing potential growth opportunities."

## Output
Present: competitive headline, ranked share tables (volume + share % + bps change), always include comparison period data, share change in basis points. For EV/Hybrid: penetration rate alongside volume. End with strategic implications tailored to dealer context. Cite data period and geography in every output.
