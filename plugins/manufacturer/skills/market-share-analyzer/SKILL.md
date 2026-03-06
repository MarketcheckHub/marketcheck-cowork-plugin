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

# Market Share Analyzer — Competitive Intelligence for OEMs & Brand Strategists

Convert MarketCheck sold transaction data into real-time competitive intelligence. Track your brand's market share vs competitors, segment conquest patterns, regional demand distribution, and EV adoption curves — all without waiting 60-90 days for traditional syndicated reports.

## Manufacturer Profile (Load First)

Before running any workflow, check for a saved manufacturer profile:

1. Read `~/.claude/marketcheck/manufacturer-profile.json`
2. If the file **exists**, extract and use silently:
   - `brands` ← `manufacturer.brands` — the user's own brand(s)
   - `states` ← `manufacturer.states` — geographic scope ("national" or specific states)
   - `competitor_brands` ← `manufacturer.competitor_brands` — key competitors to highlight
   - `country` ← `location.country`
   - `user_name` ← `user.name`
   - `company` ← `user.company`
3. If the file **does not exist**: Ask: "Which brand(s) do you represent?", "Which states or 'national'?", and "Which competitors should I track?" This skill works without a profile but is more powerful with one.
4. **Country note:** This skill requires `get_sold_summary` which is **US-only**. If `country == UK`, inform the user: "Market share analysis requires US sold transaction data and is not available for the UK market."
5. If profile exists, confirm: "Using profile: **[user_name]** at **[company]** — Brands: **[brands]**, Competitors: **[competitor_brands]**"

## User Context

The primary user is an **OEM regional manager, brand strategist, product planner, or distributor** who needs competitive intelligence to inform allocation decisions, incentive strategy, and product positioning.

Before running any workflow, collect the following (auto-filled from manufacturer profile where available):

- **Geographic scope**: From profile `manufacturer.states` if user says "my market" or "my states", otherwise ask. National (omit state), single state (2-letter code), or multi-state (run each separately)
- **Time period**: Specific month(s) for analysis. Always use first-of-month to last-of-month format (e.g., `2026-01-01` to `2026-01-31`). If the user asks for "quarterly" data, run three consecutive months and aggregate.
- **Comparison period**: Prior month, prior quarter, or year-over-year month (for share change calculation)
- **Brand focus**: From profile `manufacturer.brands` — always highlight these as "YOUR BRANDS"
- **Competitor focus**: From profile `manufacturer.competitor_brands` — always show these prominently
- **Segment focus** (optional): body_type (SUV, Sedan, Pickup, Hatchback, Coupe, Convertible, Van/Minivan, Wagon) or fuel_type_category (EV, Hybrid, ICE)
- **Inventory type**: New, Used, or Both (default Both)

If the user asks for "market share" without specifying a geographic scope, default to national and confirm.

## Workflow: Brand Market Share

Calculate market share by make for a given period and compare against a prior period to identify gainers and losers. Frame as COMPETITIVE INTELLIGENCE — show own brand vs competitors.

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
   - `body_type`: user's target segment (e.g. `SUV`)
   - `ranking_dimensions`: `make,model`
   - `ranking_measure`: `sold_count`
   - `ranking_order`: `desc`
   - `top_n`: `15`

2. Repeat for the comparison period to calculate share change within the segment.

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
   - `make`: user's own brand (from profile)
   - `model`: user's target model (optional — omit for brand-level view)
   - `summary_by`: `state`
   - `limit`: `51` (all US states + DC)

2. If the user also wants competitive context, repeat for each competitor brand.

3. If the user also wants pricing context, call `mcp__marketcheck__get_sold_summary` with:
   - Same filters plus `ranking_dimensions`: `make,model`
   - `ranking_measure`: `average_sale_price`
   - `summary_by`: `state`
   - `limit`: `51`

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

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Market Share % by Make | Your brand's share of total sold units in period | Core competitive metric; 100 bps of national share ~ 15,000-17,000 annual units |
| Share Change (basis points) | QoQ or YoY movement in share | Early warning of competitive shifts; a 50+ bps decline sustained over 2 quarters signals structural issue |
| EV/Hybrid Penetration Rate | Your brand's electrified sales as % of total | Tracks electrification progress; critical for production planning and allocation |
| Segment Share by Body Type | Your brand's position within SUV, Sedan, Pickup etc. | Reveals where you are winning or losing; segment-level share is more actionable than total share |
| Regional Volume Distribution | State-by-state unit sales for your brand vs competitors | Reveals geographic strengths, competitive threat zones, and under-penetrated growth markets |
| Price-to-MSRP Ratio | Average sale price / MSRP by model | Models selling above MSRP signal constrained supply; below MSRP signals incentive dependency |
| Competitor Gap (units) | Unit volume difference between your brand and nearest competitor by segment/state | Quantifies the conquest opportunity; drives allocation and incentive targeting |

## Action-to-Outcome Funnel

1. **Scenario: Brand strategist asks "How did we do vs Honda last quarter?"**
   Run *Brand Market Share* for each of the last 3 months. Calculate quarterly aggregate. Compare your brands vs Honda: total volume, share %, share change. Drill into *Segment Conquest Analysis* for the body types where the gap is largest. Recommend: "You trailed Honda by X units nationally. The gap is concentrated in SUVs where CR-V and HR-V outsold your [models] by Y units. Recommend increasing incentive spend on [model] to close the segment gap."

2. **Scenario: Regional manager asks "Which of my states are underperforming?"**
   Run *Regional Demand Heatmap* for the user's brand across all their states. Compare to competitors in each state. Identify states where your brand's share is below its national average while competitor share is above. Recommend: "In Florida, your brand holds X% of SUV sales vs Y% nationally. [Competitor] holds Z% in Florida. Increasing allocation by N units/month could capture an estimated W additional sales."

3. **Scenario: Product planner asks "Are we winning the EV race in our segment?"**
   Run *EV Adoption Tracking* for current and prior period. Show your brand's EV share vs competitors. Identify which competitor EV models are gaining fastest. Recommend: "[Competitor] EV model gained X units this month in your core SUV segment. Your EV offering sold Y units. Price gap is $Z — consider incentive bridge or production ramp."

4. **Scenario: Distributor asks "Where should we allocate more inventory?"**
   Run *Regional Demand Heatmap* for the brand. Identify states where the brand's share of segment sales is below its national average — these are under-allocated markets. Cross-reference with *Segment Conquest Analysis* in those states. Recommend: "In Florida, your brand holds X% of SUV sales vs Y% nationally. Increasing allocation by Z units/month could capture an estimated W additional sales based on current demand-to-supply ratios."

5. **Scenario: Brand manager asks "What does the competitive landscape look like in pickups?"**
   Run *Segment Conquest Analysis* with `body_type=Pickup`. Show top 15 models, share %, and share change. Layer in *Regional Demand Heatmap* for your pickup models vs competitor pickups. Recommend: "Ford F-150 leads with X% segment share but lost Y bps. Your [model] holds Z% — the gap is concentrated in Texas and Michigan where targeted allocation could shift share."

## Output Format

- **Lead with your brand's competitive position.** Example: "YOUR BRAND holds 14.2% national market share in January 2026, up 35 bps from December — ranking #3 overall. Nearest competitor Honda is at 12.8% (-15 bps)."
- **Always highlight "Your Brands" with ★ in tables** and competitor brands with distinct markers.
- **Use ranked tables** for share data. Always include both absolute volume and share %. Raw counts without context are meaningless; percentages without counts lack scale.
- **Show share change in basis points** (not percentage points) for precision. A move from 14.2% to 14.5% is "+30 bps", not "+0.3%".
- **Always include comparison period data.** A single-period snapshot is a fact. Two periods make a trend. Always show at least current vs prior.
- **For EV/Hybrid analysis**, always show your brand's penetration alongside market average and competitor penetration.
- **End with strategic recommendations** tailored to the manufacturer role:
  - Allocation recommendations for under-penetrated markets
  - Incentive targeting for segments where competitors are gaining
  - Segment gaps where conquest is achievable
  - Production planning implications of share trends
- **Cite the data period and geography** in every output (e.g., "Source: MarketCheck sold data, January 2026, US national").
