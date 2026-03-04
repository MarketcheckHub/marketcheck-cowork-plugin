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

# Market Share Analyzer — Competitive Intelligence from Sold Data

Convert MarketCheck sold transaction data into real-time market share analytics. Track brand and model-level share, segment conquest patterns, dealer group performance, EV adoption curves, and regional demand distribution — all without waiting 60-90 days for traditional syndicated reports.

## Dealer Profile (Load First — Optional Context)

Before running any workflow, check for a saved dealer profile:

1. Read `~/.claude/marketcheck/dealer-profile.json`
2. If the file **exists**, use as optional context:
   - `state` ← `location.state` — use as default geographic scope if user says "my market"
   - `franchise_brands` ← `dealer.franchise_brands` — use as default brand focus if user says "my brand"
   - `dealer_type` ← `dealer.dealer_type`
   - `country` ← `location.country`
3. If the file **does not exist**, ask for all fields as before — this skill works fine without a profile.
4. **Country note:** This skill requires `get_sold_summary` which is **US-only**. UK dealers cannot use market share analysis. If `country == UK`, inform the user: "Market share analysis requires US sold transaction data and is not available for the UK market."
5. If profile exists and applicable, confirm: "Using profile context: **[state]**, **[franchise_brands]**"

## User Context

Before running any workflow, collect the following (auto-filled from dealer profile where available):

- **Role**: OEM/manufacturer analyst, dealer group strategist, or market researcher
- **Geographic scope**: From profile `location.state` if user says "my market", otherwise ask. National (omit state), single state (2-letter code), or multi-state (run each separately)
- **Time period**: Specific month(s) for analysis. Always use first-of-month to last-of-month format (e.g., `2026-01-01` to `2026-01-31`). If the user asks for "quarterly" data, run three consecutive months and aggregate.
- **Comparison period**: Prior month, prior quarter, or year-over-year month (for share change calculation)
- **Brand focus** (optional): From profile `dealer.franchise_brands` if available, otherwise ask
- **Segment focus** (optional): body_type (SUV, Sedan, Pickup, Hatchback, Coupe, Convertible, Van/Minivan, Wagon) or fuel_type_category (EV, Hybrid, ICE)
- **Inventory type**: New, Used, or Both (default Both)

If the user asks for "market share" without specifying a geographic scope, default to national and confirm.

## Workflow: Brand Market Share

Calculate market share by make for a given period and compare against a prior period to identify gainers and losers.

1. Call `mcp__marketcheck__get_sold_summary` for the **current period**:
   - `date_from`: first of target month (e.g. `2026-01-01`)
   - `date_to`: last of target month (e.g. `2026-01-31`)
   - `state`: user's state filter (omit for national)
   - `inventory_type`: as specified (or omit for both)
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `20`

2. Call `mcp__marketcheck__get_sold_summary` for the **prior period** with identical filters but adjusted `date_from` / `date_to` (e.g., prior month or same month prior year).

3. Calculate for each make:
   - **Current Share %** = Make Sold Count / Total Sold Count x 100
   - **Prior Share %** = same calculation for prior period
   - **Share Change (bps)** = (Current Share % - Prior Share %) x 100 basis points
   - **Volume Change %** = (Current Sold - Prior Sold) / Prior Sold x 100

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
   - `body_type`: user's target segment (e.g. `SUV`)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `15`

2. Repeat for the comparison period to calculate share change within the segment.

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

2. Call `mcp__marketcheck__get_sold_summary` for **Hybrid sales**:
   - Same filters but `fuel_type_category`: `Hybrid`

3. Call `mcp__marketcheck__get_sold_summary` for **total market** (no fuel_type_category filter):
   - `ranking_dimensions`: `make`
   - `ranking_measure`: `sold_count`
   - `top_n`: `1` (we just need the total count)

4. Repeat steps 1-3 for the prior period (prior month or same month last year) to calculate trend.

5. Calculate:
   - **EV Penetration Rate** = EV Sold / Total Sold x 100
   - **Hybrid Penetration Rate** = Hybrid Sold / Total Sold x 100
   - **Combined Electrified Rate** = (EV + Hybrid) / Total x 100
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
   - `make`: user's target make (required for this workflow)
   - `model`: user's target model (optional — omit for brand-level view)
   - `summary_by`: `state`
   - `limit`: `51` (all US states + DC)

2. If the user also wants pricing context, call `mcp__marketcheck__get_sold_summary` with:
   - Same filters plus `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_sale_price`
   - `summary_by`: `state`
   - `limit`: `51`

3. Calculate for each state:
   - **Volume rank** (which states buy the most of this make/model)
   - **Price rank** (where is it cheapest vs most expensive)
   - **Price-to-national-average ratio** = State Avg Price / National Avg Price

4. Present as a **State-Level Demand Table** sorted by sold count descending:
   - Columns: State, Sold Count, % of National Volume, Avg Sale Price, Price vs National Avg, Avg DOM
   - Top 10 states get detailed analysis
   - Bottom 10 states flagged as potential growth markets

5. If the user specifies a model, also call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions`: `make` for the same body_type (without the make/model filter) in the top 3 states to show competitive context: "In Texas, [Model] sold X units but [Competitor] sold Y units in the same segment."

6. Summary: "For [Make Model], Texas leads with X% of national volume at an average price $Y [above/below] the national average. The least penetrated large markets are [State A], [State B], [State C] — representing potential growth opportunities."

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Market Share % by Make | Brand's share of total sold units in period | Core competitive metric; 100 bps of national share ~ 15,000-17,000 annual units |
| Share Change (basis points) | QoQ or YoY movement in share | Early warning of competitive shifts; a 50+ bps decline sustained over 2 quarters signals structural issue |
| EV/Hybrid Penetration Rate | Electrified sales as % of total market | Tracks transition pace; critical for production planning and dealer allocation |
| Segment Share by Body Type | Brand's position within SUV, Sedan, Pickup etc. | Reveals where a brand is winning or losing; segment-level share is more actionable than total share |
| Dealer Group Volume Ranking | Top 20 groups by units sold | Identifies which retail partners drive volume; informs co-op allocation and incentive design |
| Dealer Group Avg DOM | Operational efficiency by group | Groups with low DOM are more capital-efficient; DOM gap between top and bottom group often exceeds 20 days |
| Regional Volume Distribution | State-by-state unit sales | Reveals geographic concentration risk and under-penetrated growth markets |
| Price-to-MSRP Ratio | Average sale price / MSRP by model | Models selling above MSRP signal constrained supply; below MSRP signals incentive dependency |

## Action-to-Outcome Funnel

1. **Scenario: OEM brand manager asks "How did we do vs Toyota last quarter?"**
   Run *Brand Market Share* for each of the last 3 months. Calculate quarterly aggregate. Compare Toyota vs the user's brand: total volume, share %, share change. Drill into *Segment Conquest Analysis* for the body types where the gap is largest. Recommend: "You trailed Toyota by X units nationally. The gap is concentrated in SUVs where RAV4 and Highlander outsold your [models] by Y units. Focus incentive spend on [model] to close the segment gap."

2. **Scenario: Analyst asks "Which brands are gaining EV market share?"**
   Run *EV Adoption Tracking* for current and prior period. Show brand-level EV share change. Identify the top 3 brands accelerating EV volume. Recommend: "Tesla's EV share dropped from X% to Y% as [Brand A] and [Brand B] launched [models]. Hyundai/Kia combined now represent Z% of EV sales, up from W% a year ago."

3. **Scenario: Dealer group CEO asks "How do we rank against Lithia and Hendrick?"**
   Run *Dealer Group Benchmarking* nationally and for the user's primary state. Show volume, DOM, and efficiency score side by side. Recommend: "You rank #X in volume but #Y in efficiency. Lithia moves units 8 days faster on average. Closing that DOM gap across your 45 rooftops would free approximately $Z in annual floor plan savings."

4. **Scenario: OEM regional director asks "Where should we allocate more inventory?"**
   Run *Regional Demand Heatmap* for the OEM's brand. Identify states where the brand's share of segment sales is below its national average — these are under-allocated markets. Cross-reference with *Segment Conquest Analysis* in those states. Recommend: "In Florida, your brand holds X% of SUV sales vs Y% nationally. Increasing allocation by Z units/month could capture an estimated W additional sales based on current demand-to-supply ratios."

5. **Scenario: Market researcher asks "What does the competitive landscape look like in pickups?"**
   Run *Segment Conquest Analysis* with `body_type=Pickup`. Show top 15 models, share %, and share change. Layer in *Regional Demand Heatmap* for the top 3 pickup models. Recommend: "Ford F-150 still leads with X% segment share but lost Y bps to Chevrolet Silverado and Ram 1500. The share shift is most pronounced in Texas and Michigan."

## Output Format

- **Lead with the competitive headline.** Example: "Toyota holds 14.2% national market share in January 2026, up 35 bps from December. Honda is the biggest gainer at +52 bps."
- **Use ranked tables** for share data. Always include both absolute volume and share %. Raw counts without context are meaningless; percentages without counts lack scale.
- **Show share change in basis points** (not percentage points) for precision. A move from 14.2% to 14.5% is "+30 bps", not "+0.3%".
- **Always include comparison period data.** A single-period snapshot is a fact. Two periods make a trend. Always show at least current vs prior.
- **For EV/Hybrid analysis**, always show penetration rate alongside absolute volume. "50,000 EVs sold" means nothing without knowing it is 7.2% of the total market.
- **End with strategic implications** tailored to the user's role:
  - For OEMs: allocation recommendations, incentive targeting, segment gaps
  - For dealer groups: competitive positioning, brand mix optimization
  - For analysts: trend narratives, inflection points, forecast implications
- **Cite the data period and geography** in every output (e.g., "Source: MarketCheck sold data, January 2026, US national, all dealer types").
