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

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Market Share Analyzer — Competitive Intelligence from Sold Data

Convert MarketCheck sold transaction data into real-time market share analytics. Track brand and model-level share, segment conquest patterns, dealer group performance, EV adoption curves, and regional demand distribution — all without waiting 60-90 days for traditional syndicated reports.

## Dealer Group Profile (Load First -- Optional Context)

Load the `marketcheck-profile.md` project memory file. If exists, extract: `group_name`, `locations[]`, `preferences`; from default location: `state`, `franchise_brands`, `dealer_type`, `country`. If missing, ask for fields. US-only (`get_sold_summary`); UK → not available. Confirm profile.

## User Context

Dealer group executive, OEM analyst, or market researcher tracking brand/segment share, competitive positioning, and EV adoption from sold transaction data.

Auto-loaded from profile: `state` (geographic scope), `franchise_brands` (brand focus). Ask: time period (month range), comparison period, segment focus, inventory type (default Both). No geo specified → default national.

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
   - Highlight the group's franchise brands in bold
   - Flag makes gaining > 50 bps as "GAINING" and losing > 50 bps as "LOSING"

5. Add a summary paragraph: "The top 3 share gainers this period were [X], [Y], [Z], collectively picking up [N] basis points. The biggest losers were [A], [B], [C]. [Group's brand] moved from #X to #Y position with a [+/-N] bps shift."

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
   → **Extract only**: per make/model — `sold_count`. Discard full response.

2. Repeat for comparison period.
   → **Extract only**: per make/model — `sold_count`. Discard full response.

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
   → **Extract only**: per group — `sold_count`. Discard full response.

2. Same filters but `ranking_measure`: `average_days_on_market`, `ranking_order`: `asc`.
   → **Extract only**: per group — `average_days_on_market`. Discard full response.

3. Same filters but `ranking_measure`: `average_sale_price`, `ranking_order`: `desc`.
   → **Extract only**: per group — `average_sale_price`. Discard full response.

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
   → **Extract only**: per make/model — `sold_count`; plus total EV `sold_count`. Discard full response.

2. Same filters but `fuel_type_category`: `Hybrid`.
   → **Extract only**: per make/model — `sold_count`; plus total Hybrid `sold_count`. Discard full response.

3. Call for **total market** (no fuel_type_category): `ranking_dimensions`: `make`, `ranking_measure`: `sold_count`, `top_n`: `1`.
   → **Extract only**: total `sold_count`. Discard full response.

4. Repeat steps 1-3 for the prior period to calculate trend.
   → **Extract only**: same fields per period. Discard full response.

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
   - `make`: target make (required), `model`: optional
   - `summary_by`: `state`, `limit`: `51`
   → **Extract only**: per state — `sold_count`. Discard full response.

2. If pricing context needed, add `ranking_dimensions`: `make,model`, `ranking_measure`: `average_sale_price`, `summary_by`: `state`, `limit`: `51`.
   → **Extract only**: per state — `average_sale_price`. Discard full response.

3. Calculate for each state:
   - **Volume rank** (which states buy the most)
   - **Price rank** (where is it cheapest vs most expensive)
   - **Price-to-national-average ratio**

4. Present as a **State-Level Demand Table** sorted by sold count descending. Highlight states where the group has locations.

5. Summary with recommendations for each location's market.

## Output

Present: competitive headline with share % and bps change, ranked share tables (volume + share % + change bps), comparison period data for trend context, and strategic implications for the dealer group (allocation shifts, cross-location opportunities). Cite data period and geography.
