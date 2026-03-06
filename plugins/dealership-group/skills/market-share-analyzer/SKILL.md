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
  using sold vehicle data for a multi-location dealer group.
version: 0.1.0
---

# Market Share Analyzer — Competitive Intelligence from Sold Data

Convert MarketCheck sold transaction data into real-time market share analytics. Track brand and model-level share, segment conquest patterns, dealer group performance, EV adoption curves, and regional demand distribution — all without waiting 60-90 days for traditional syndicated reports.

## Dealer Group Profile (Load First — Optional Context)

Before running any workflow, check for a saved dealer group profile:

1. Read `~/.claude/marketcheck/dealership-group-profile.json`.
2. If the file **exists**, use as optional context:
   - `group_name` ← `dealer_group.group_name`
   - `locations[]` ← `dealer_group.locations`
   - `preferences` ← `preferences`
3. **Location context**: Extract from the default location (or user-specified location):
   - `state` ← `location.state` — use as default geographic scope if user says "my market"
   - `franchise_brands` ← `location.franchise_brands` — use as default brand focus if user says "my brand"
   - `dealer_type` ← `location.dealer_type`
   - `country` ← `location.country`
4. If the file **does not exist**, ask for all fields as before — this skill works fine without a profile.
5. **Country note:** This skill requires `get_sold_summary` which is **US-only**. UK locations cannot use market share analysis. If `country == UK`, inform the user: "Market share analysis requires US sold transaction data and is not available for the UK market."
6. If profile exists and applicable, confirm: "Using profile context: **[group_name]** — **[state]**, **[franchise_brands]**"

## User Context

Before running any workflow, collect the following (auto-filled from dealer group profile where available):

- **Role**: Dealer group executive, OEM analyst, or market researcher
- **Geographic scope**: From location profile `location.state` if user says "my market", otherwise ask. National (omit state), single state (2-letter code), or multi-state (run each separately). For dealer groups, can aggregate across all locations' states.
- **Time period**: Specific month(s) for analysis. Always use first-of-month to last-of-month format. If the user asks for "quarterly" data, run three consecutive months and aggregate.
- **Comparison period**: Prior month, prior quarter, or year-over-year month (for share change calculation)
- **Brand focus** (optional): From location profile `location.franchise_brands` if available, otherwise ask
- **Segment focus** (optional): body_type or fuel_type_category
- **Inventory type**: New, Used, or Both (default Both)

If the user asks for "market share" without specifying a geographic scope, default to national and confirm.

## Workflow: Brand Market Share

Calculate market share by make for a given period and compare against a prior period to identify gainers and losers.

1. Call `mcp__marketcheck__get_sold_summary` for the **current period**:
   - `date_from`: first of target month
   - `date_to`: last of target month
   - `state`: user's state filter (omit for national)
   - `inventory_type`: as specified (or omit for both)
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`

2. Call `mcp__marketcheck__get_sold_summary` for the **prior period** with identical filters but adjusted dates.

3. Calculate for each make:
   - **Current Share %** = Make Sold Count / Total Sold Count x 100
   - **Prior Share %** = same calculation for prior period
   - **Share Change (bps)** = (Current Share % - Prior Share %) x 100 basis points
   - **Volume Change %** = (Current Sold - Prior Sold) / Prior Sold x 100

4. Present as a ranked table:
   - Columns: Rank, Make, Current Sold, Current Share %, Prior Sold, Prior Share %, Share Change (bps), Volume Change %
   - Sort by Current Share % descending
   - Highlight the group's franchise brands in bold
   - Flag makes gaining > 50 bps as "GAINING" and losing > 50 bps as "LOSING"

5. Add a summary paragraph: "The top 3 share gainers this period were [X], [Y], [Z], collectively picking up [N] basis points. The biggest losers were [A], [B], [C]. [Group's brand] moved from #X to #Y position with a [+/-N] bps shift."

## Workflow: Segment Conquest Analysis

Determine which brands are winning within specific vehicle segments (body types) and identify conquest opportunities.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `state`: user's state filter (omit for national)
   - `body_type`: user's target segment (e.g. `SUV`)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `15`

2. Repeat for the comparison period to calculate share change within the segment.

3. If the user wants multi-segment comparison, repeat step 1 for each body_type: `SUV`, `Sedan`, `Pickup`, `Hatchback`, `Coupe`, `Van/Minivan`.

4. For each segment, calculate:
   - **Segment leader** and their share %
   - **Group's brand rank** within the segment
   - **Gap to leader** in units and share points
   - **Fastest gaining model** in the segment (largest positive bps change)

5. Present per-segment tables:
   - Columns: Rank, Make, Model, Sold Count, Segment Share %, Prior Share %, Change (bps)
   - Also present a **Segment Summary** table: Segment, Leader, Leader Share %, Group Brand Rank, Group Brand Share %, Gap to Leader

6. Conquest insight with specific recommendations for each location's market.

## Workflow: Dealer Group Benchmarking

Rank dealer groups by sales volume and operational efficiency to identify top performers and laggards. Useful for comparing the user's group against public peers.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `state`: user's state filter (omit for national)
   - `ranking_dimensions`: `dealership_group_name`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`

2. Call `mcp__marketcheck__get_sold_summary` with same filters but:
   - `ranking_measure`: `average_days_on_market`
   - `ranking_order`: `asc`
   - `top_n`: `20`

3. Call `mcp__marketcheck__get_sold_summary` with same filters but:
   - `ranking_measure`: `average_sale_price`
   - `ranking_order`: `desc`
   - `top_n`: `20`

4. Merge the three result sets by dealership_group_name. Build a **Dealer Group Leaderboard**:
   - Columns: Rank (by volume), Dealer Group, Sold Count, Market Share %, Avg DOM, Avg Sale Price, Efficiency Score
   - **Efficiency Score** = Sold Count / Avg DOM (higher is better — moves more units faster)

5. If the user specifies a make, add a `make` filter to all calls to see dealer group performance within a single brand's network.

6. Highlight the user's own group in the leaderboard and provide comparative analysis.

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

2. Call `mcp__marketcheck__get_sold_summary` for **Hybrid sales** with `fuel_type_category`: `Hybrid`.

3. Call `mcp__marketcheck__get_sold_summary` for **total market** (no fuel_type_category filter):
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `sold_count`
   - `top_n`: `1` (we just need the total count)

4. Repeat steps 1-3 for the prior period to calculate trend.

5. Calculate:
   - **EV Penetration Rate** = EV Sold / Total Sold x 100
   - **Hybrid Penetration Rate** = Hybrid Sold / Total Sold x 100
   - **Combined Electrified Rate** = (EV + Hybrid) / Total x 100
   - **Period-over-period change** for each rate

6. Present:
   - **EV Penetration Summary**
   - **Top EV Models** table
   - **Top Hybrid Models** table
   - **EV Brand Share** table

## Workflow: Regional Demand Heatmap

Map sales volume and pricing by state for a specific make or model to reveal geographic demand patterns. Particularly useful for dealer groups operating in multiple states.

1. Call `mcp__marketcheck__get_sold_summary` with:
   - `date_from` / `date_to`: target period
   - `make`: user's target make (required for this workflow)
   - `model`: user's target model (optional)
   - `summary_by`: `state`
   - `limit`: `51` (all US states + DC)

2. If the user also wants pricing context, call `mcp__marketcheck__get_sold_summary` with:
   - Same filters plus `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_sale_price`
   - `summary_by`: `state`
   - `limit`: `51`

3. Calculate for each state:
   - **Volume rank** (which states buy the most)
   - **Price rank** (where is it cheapest vs most expensive)
   - **Price-to-national-average ratio**

4. Present as a **State-Level Demand Table** sorted by sold count descending. Highlight states where the group has locations.

5. Summary with recommendations for each location's market.

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Market Share % by Make | Brand's share of total sold units in period | Core competitive metric; 100 bps of national share ~ 15,000-17,000 annual units |
| Share Change (basis points) | QoQ or YoY movement in share | Early warning of competitive shifts; a 50+ bps decline sustained over 2 quarters signals structural issue |
| EV/Hybrid Penetration Rate | Electrified sales as % of total market | Tracks transition pace; critical for production planning and dealer allocation |
| Segment Share by Body Type | Brand's position within SUV, Sedan, Pickup etc. | Reveals where a brand is winning or losing; segment-level share is more actionable than total share |
| Dealer Group Volume Ranking | Top 20 groups by units sold | Identifies competitive positioning vs peer groups |
| Dealer Group Avg DOM | Operational efficiency by group | Groups with low DOM are more capital-efficient; DOM gap between top and bottom group often exceeds 20 days |
| Regional Volume Distribution | State-by-state unit sales | Reveals geographic concentration risk and under-penetrated growth markets |

## Action-to-Outcome Funnel

1. **Scenario: Group executive asks "How did we do vs AutoNation last quarter?"**
   Run *Dealer Group Benchmarking* nationally and for each state where the group operates. Show volume, DOM, and efficiency score side by side.

2. **Scenario: Group strategist asks "Which brands are gaining EV market share?"**
   Run *EV Adoption Tracking* for current and prior period. Show brand-level EV share change. Identify the top 3 brands accelerating EV volume.

3. **Scenario: Group executive asks "How do our franchise brands rank in their segments?"**
   Run *Segment Conquest Analysis* for each franchise brand. Show segment share, gap to leader, and growth trajectory.

4. **Scenario: Regional director asks "Where should we allocate more inventory?"**
   Run *Regional Demand Heatmap* for the group's brands. Identify states where the brand's share is below national average — cross-reference with group location states.

5. **Scenario: Market researcher asks "What does the competitive landscape look like in pickups?"**
   Run *Segment Conquest Analysis* with `body_type=Pickup`. Show top 15 models, share %, and share change. Layer in *Regional Demand Heatmap* for the top 3 pickup models.

## Output Format

- **Lead with the competitive headline.** Example: "Toyota holds 14.2% national market share in January 2026, up 35 bps from December."
- **Use ranked tables** for share data. Always include both absolute volume and share %.
- **Show share change in basis points** for precision.
- **Always include comparison period data.** Two periods make a trend.
- **For EV/Hybrid analysis**, always show penetration rate alongside absolute volume.
- **End with strategic implications** tailored to the dealer group context:
  - Which locations benefit from brand share gains
  - Where to shift inventory allocation
  - Cross-location opportunities identified
- **Cite the data period and geography** in every output.
