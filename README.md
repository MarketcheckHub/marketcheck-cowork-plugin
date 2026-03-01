# MarketCheck Cowork Plugin for Claude Code

Automotive market intelligence suite for Claude Code — powered by the [MarketCheck API](https://www.marketcheck.com). 8 skills, 4 commands, and 1 batch-processing agent that turn real-time vehicle pricing, inventory, and transaction data into actionable intelligence for dealers, appraisers, brokers, lenders, OEM analysts, and market researchers.

## What It Does

This plugin connects Claude Code to MarketCheck's automotive data platform via MCP (Model Context Protocol), giving you conversational access to:

- **50M+ active and historical vehicle listings** across the US
- **Real-time price predictions** backed by comparable transactions
- **VIN decoding** down to trim, engine, drivetrain, and MSRP
- **Sold transaction data** for market share, demand analysis, and depreciation tracking
- **Dealer-level inventory intelligence** including days-on-market, price changes, and supply counts

Instead of writing API calls or navigating dashboards, you ask questions in plain English and get structured, data-backed answers.

---

## Installation

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI or VS Code extension)
- A MarketCheck API key — [get one here](https://www.marketcheck.com)
- Node.js 18+ (for the MCP client via npx)

### Step 1: Install the Plugin

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git
```

### Step 2: Connect the MCP Server

Run the setup command inside Claude Code:

```
/setup-mcp YOUR_API_KEY
```

This writes the MCP configuration so Claude Code can communicate with the MarketCheck API. The config uses the `@marketcheckhub/mcp-client` npm package, which connects to the remote MarketCheck MCP server — no local server to run or maintain.

Alternatively, you can manually add the following to your `~/.claude/.mcp.json` or project-level `.mcp.json`:

```json
{
  "mcpServers": {
    "marketcheck": {
      "command": "npx",
      "args": ["-y", "@marketcheckhub/mcp-client"],
      "env": {
        "MARKETCHECK_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

### Step 3: Restart Claude Code

The MCP server connects on startup. After configuring, restart Claude Code and verify by asking:

```
Price check VIN 1HGCV1F3XPA123456
```

---

## Skills

Skills are the core intelligence modules. They activate automatically when you ask questions in natural language — no slash commands needed. Each skill contains multiple workflows tailored to specific business scenarios.

### 1. Competitive Pricer

**Trigger phrases:** "price this car", "am I priced right", "competitive pricing", "who is undercutting me", "price my inventory"

Answers the question every dealer asks daily: *Is my price right?*

| Workflow | What It Does |
|----------|-------------|
| Price-Check a Single VIN | Decodes the VIN, predicts market value, pulls competing listings, calculates percentile rank, and delivers a Below/At/Above Market verdict |
| Batch Competitive Scan | Processes a list of VINs from your lot, scores each against the market, prioritizes overpriced units (aging risk) and underpriced units (margin opportunity) |
| Trade-In VIN Price History | Pulls the full listing timeline of a trade-in VIN across all dealers — price trajectory, dealer hops, days on market at each stop |
| Market Price Distribution | Statistical overview of a model in your market — mean, median, quartiles, min/max, and outlier detection |
| Competitor Price Movement | Finds which competitors dropped prices recently, identifies aggressive sellers, and flags units that now undercut your pricing |

**Key metrics:** Price-to-Market Ratio, Competitive Position Percentile, Competing Unit Count, Price Change Velocity

---

### 2. Vehicle Appraiser

**Trigger phrases:** "appraise this vehicle", "what's it worth", "trade-in value", "fair market value", "wholesale vs retail"

Builds defensible, comparable-backed valuations for trade-ins, acquisitions, insurance claims, and retail pricing.

| Workflow | What It Does |
|----------|-------------|
| Full Comparable Appraisal | Three-source valuation: algorithmic prediction + active retail comps + sold transaction evidence, synthesized into a recommended value range with confidence score |
| Trade-In Quick Appraisal | 60-second valuation for the customer sitting at the desk — predicted retail, estimated trade-in range, and top 5 comps |
| Regional Price Variance | Compares values across multiple ZIP codes or states to find geographic arbitrage opportunities |
| Wholesale vs Retail Spread | Calculates the gap between franchise retail and independent wholesale pricing for trade-in offer strategy |
| Historical Value Trajectory | Chronological listing history for a specific VIN — price at each dealer, DOM per stop, total depreciation |

**Key metrics:** Comparable Count, Retail-to-Wholesale Spread, Regional Variance, Valuation Confidence Score (High/Medium/Low)

---

### 3. Deal Finder

**Trigger phrases:** "find me the best deal", "cheapest option near me", "is this a good price", "should I buy now or wait", "compare deals"

Sources the best-priced vehicle, validates whether a deal is fair, and arms brokers with negotiation leverage.

| Workflow | What It Does |
|----------|-------------|
| Best Deal Search | Finds the lowest-priced matching vehicles in a market, scores them by price/miles/DOM/distance composite, and ranks the top options |
| Fair Price Validation | Takes a specific listing the customer found and validates it: below market (buy), at market (negotiate), or above market (pass/alternatives exist) |
| Negotiation Leverage Report | Builds a data brief for dealer negotiations — DOM leverage, price drop history, predicted fair value, and 3-5 competing units to cite by name |
| Finance/Lease Comparison | Compares financing and lease terms across dealers, calculates total cost of ownership for apples-to-apples comparison |
| Market Timing Advice | Analyzes supply-to-demand ratio and price trends to answer "should I buy now or wait" with data |

**Key metrics:** Price vs Market Average, DOM of Found Units, Supply Trend Direction, Finance Payment Range

---

### 4. Inventory Intelligence

**Trigger phrases:** "what should I stock", "what's selling in my area", "aging inventory alert", "turn rate by segment", "floor plan optimization"

Replaces gut-instinct buying with demand-to-supply ratios, aging alerts, and turn-rate benchmarks.

| Workflow | What It Does |
|----------|-------------|
| Market Demand Snapshot | Top-selling models and body types in your state for the most recent month, ranked by volume |
| What Should I Stock? (Demand-to-Supply Ratio) | Compares what's selling against what's currently listed — models with high demand and low supply are your stocking targets |
| Aging Inventory Alert | Finds units on your lot over 60 DOM, prices each against market value, calculates floor plan burn, and recommends reduce/wholesale/hold |
| Turn Rate by Segment | Benchmarks how quickly different body types and models move in your market — fastest and slowest turners |
| New vs Used Mix Analysis | Determines whether your lot is over-indexed on new or used relative to what the market is absorbing |

**Key metrics:** Demand-to-Supply Ratio, Average DOM by Segment, Aged Unit Count, Turn Rate, New vs Used Mix Alignment

---

### 5. Market Share Analyzer

**Trigger phrases:** "market share", "who is winning in SUVs", "competitor analysis", "EV adoption rate", "dealer group ranking", "brand performance comparison"

Competitive intelligence from sold transaction data — no waiting 60-90 days for syndicated reports.

| Workflow | What It Does |
|----------|-------------|
| Brand Market Share | Market share by make for any period, with share change in basis points vs prior period |
| Segment Conquest Analysis | Brand rankings within specific body types (SUV, Sedan, Pickup, etc.) — who is gaining, who is losing, and where the conquest opportunities are |
| Dealer Group Benchmarking | Ranks dealer groups by volume, average DOM, and average sale price with an efficiency score |
| EV Adoption Tracking | EV and hybrid penetration rates vs total market, broken down by brand and model |
| Regional Demand Heatmap | State-by-state sales volume and pricing for any make/model — reveals geographic demand patterns and under-penetrated markets |

**Key metrics:** Market Share % (with basis point changes), EV Penetration Rate, Segment Share, Dealer Group Efficiency Score, Regional Volume Distribution

---

### 6. Market Trends Reporter

**Trigger phrases:** "market trends", "fastest depreciating cars", "EV vs gas prices", "new car markups", "cheapest state to buy", "market report"

Generates publishable market trend analyses and consumer buying guides from real transaction data.

| Workflow | What It Does |
|----------|-------------|
| Fastest and Slowest Depreciating Models | Year-over-year price change by model — which cars are losing value fastest and which are holding strong |
| Best Deals Right Now | Vehicles with significant price reductions and high DOM, validated against predicted market value to confirm they are genuine below-market deals |
| EV vs ICE Price Parity Tracker | Tracks the price gap between electric and gas vehicles within the same segments, with convergence trend estimates |
| Regional Price Variance Story | Reveals where in the US a vehicle is cheapest and most expensive — actionable for cross-state purchase decisions |
| New Car Markup and Discount Tracker | Which new models are selling above MSRP (supply-constrained) and which require discounts (over-supplied) |

**Key metrics:** Depreciation Rate by Model, Deal Score, EV-to-ICE Price Gap, Regional Price Spread, Price-to-MSRP Ratio

---

### 7. Depreciation Tracker

**Trigger phrases:** "depreciation rate", "value retention", "residual value", "EV depreciation", "which cars hold value", "MSRP parity"

Vehicle value retention and depreciation intelligence for lenders, OEM analysts, and appraisers.

| Workflow | What It Does |
|----------|-------------|
| Make/Model Depreciation Curve | Multi-point depreciation curve from current month back to 1 year ago — retention %, monthly rate, annualized rate, and curve shape analysis |
| Segment Value Trends | Side-by-side depreciation comparison across body types and fuel types (EV vs ICE vs Hybrid) |
| Brand Residual Ranking | Ranks automakers by value retention with tier classification (Tier 1 through Tier 4) |
| Geographic Depreciation Variance | State-level price index showing where vehicles hold value best and worst |
| MSRP Parity Tracker | Tracks which new vehicles sell above or below sticker and how that gap is trending |

**Key metrics:** Monthly Depreciation Rate, Residual Retention %, Brand Tier Classification, Geographic Price Index, Price-Over-MSRP %

---

### 8. Stocking Guide

**Trigger phrases:** "what should I buy at auction", "auction run list check", "hot sellers in my area", "should I bid on this", "avoid list", "slow movers to avoid"

Auction buying intelligence purpose-built for independent dealers.

| Workflow | What It Does |
|----------|-------------|
| Pre-Auction VIN Check | For each VIN on the run list: decode, predict retail value, calculate max bid, check demand-to-supply, estimate floor plan cost, and deliver a BUY / CAUTION / PASS verdict |
| Hot List Generator | Top 10 models to actively seek at auction — ranked by an opportunity score combining turn rate, demand-to-supply ratio, and volume |
| Category Gap Finder | Compares your current inventory mix against market demand to find body types and makes you are under-stocked or over-stocked in |
| Avoid List (Slow Movers) | The models to stay away from — longest DOM, lowest volume, highest oversupply ratio, with estimated holding cost per unit |

**Key metrics:** Max Bid Price, Demand-to-Supply Ratio, Expected Turn Days, Projected Net Profit, Inventory Mix Alignment Score

---

## Slash Commands

Quick-access commands for the most common tasks. Type these directly in Claude Code.

| Command | Usage | What It Does |
|---------|-------|-------------|
| `/price-check` | `/price-check 1HGCV1F3XPA123456` or `/price-check 2023 Toyota RAV4` | Predicts market value, pulls competing listings, and returns a price-position verdict in under 30 seconds |
| `/vin-lookup` | `/vin-lookup 1HGCV1F3XPA123456` | Full VIN decode (specs, MSRP, engine, drivetrain), listing history across all dealers, and estimated current value |
| `/market-snapshot` | `/market-snapshot TX` | Top-selling models, segment demand, supply data, and demand-to-supply opportunities for a state |
| `/setup-mcp` | `/setup-mcp YOUR_API_KEY` | Configures the MarketCheck MCP connection — one-time setup |

---

## Agent: Portfolio Scanner

A batch-processing agent that systematically processes lists of VINs through pricing and market analysis workflows, then aggregates results into actionable summary reports.

**When to use:** Any time you have multiple VINs to process — auction run lists, portfolio revaluations, fleet appraisals, or lot-wide competitive pricing.

**Example prompts:**
- "Check these 10 VINs from tomorrow's auction run list"
- "Revalue these 20 VINs from our loan portfolio"
- "Price check my entire lot — here are 15 VINs"

**Output modes:**

| Use Case | Per-VIN Output | Summary Stats |
|----------|---------------|---------------|
| Auction Prep | Retail Value, Max Bid, Supply, DOM, BUY/CAUTION/PASS verdict | Total recommended buys, estimated profit potential |
| Portfolio Revalue | Current Value, LTV, Risk Flag (underwater / high risk) | % underwater, % at risk, average value change |
| Competitive Pricing | Listed Price, Market Value, Delta, Competitors, REDUCE/HOLD/RAISE action | Total overpriced units, estimated margin recovery |

The agent processes every VIN even if individual lookups fail, presents partial results, and always ends with the top 3 actions ranked by impact.

---

## Use Cases by Segment

### For Used Car Dealers

You attend auctions 2-3 times a week, manage 50-200 units on the lot, and need to make fast, profitable stocking and pricing decisions.

**Daily workflow:**
1. Before auction: `/price-check` each VIN on the run list, or hand the full list to the Portfolio Scanner for batch BUY/CAUTION/PASS verdicts
2. Weekly: "What's selling fast in my area?" to generate the Hot List of models to actively seek
3. Weekly: "Show me my aging inventory" to catch units over 60 DOM before they become floor plan sinkholes
4. Monthly: "What should I stock?" for demand-to-supply analysis that guides your buying mix

**Example conversations:**
```
You: Check these VINs from tomorrow's Manheim auction
     1HGCV1F3XPA012345
     2T3P1RFV8RW654321
     5YJ3E1EA8PF789012

Claude: [Decodes each VIN, predicts retail values, calculates max bids,
         checks local supply, and delivers BUY/CAUTION/PASS for each]

You: What's the hot list for Dallas this month?

Claude: [Top 10 models ranked by opportunity score with max auction buy prices]

You: Am I priced right on my 2022 RAV4 XLE? VIN is 2T3P1RFV8RW654321,
     I'm asking $29,500 in ZIP 75201

Claude: [Competitive analysis showing you are 4% above market with 23
         competing units. Recommends reducing to $28,200 based on 42 DOM.]
```

---

### For Auto Brokers & Buying Services

You source vehicles on behalf of clients and need to find the best deal, prove it is fair, and negotiate from a position of data strength.

**Typical workflow:**
1. Client requests a specific vehicle: "Find me the best deal on a 2024 RAV4 XLE near Phoenix"
2. Validate a listing the client found: "Is this a good price?" — get a buy/negotiate/pass recommendation
3. Prepare for negotiation: get DOM leverage, price history, competing units to cite by name
4. Advise on timing: "Should my client buy now or wait?" — supply-to-demand analysis with a clear recommendation

**Example conversations:**
```
You: Find the best deal on a 2024 Toyota RAV4 XLE Premium within 100 miles
     of Phoenix, budget $38,000

Claude: [Top 5 deals ranked by composite score. #1 at Camelback Toyota,
         $33,200, 52 DOM, 6.2% below market. Includes negotiation notes.]

You: My client found this one — VIN 2T3P1RFV8RW654321, listed at $35,800.
     Is it a fair deal?

Claude: [Predicted value $34,200. Listed price is 4.7% above market.
         3 cheaper alternatives within 50 miles. Verdict: NEGOTIATE —
         target $34,000 citing competing units.]
```

---

### For Appraisers & Insurance Adjusters

You need defensible valuations backed by cited comparables and transaction evidence, not black-box estimates.

**Typical workflow:**
1. Full comparable appraisal: three-source valuation (algorithmic + active comps + sold transactions) with every comparable cited by VIN
2. Quick trade-in number: 60-second valuation for a customer at the desk
3. Wholesale vs retail spread: gap analysis for trade-in offer strategy
4. Regional variance: understand how values differ across states for fleet or multi-location valuations

**Example conversations:**
```
You: Appraise this vehicle for an insurance claim — VIN 5YJ3E1EA8PF123456,
     28,400 miles, clean condition, ZIP 30309

Claude: [Full comparable appraisal with predicted value $35,200, active comp
         range $33,800-$37,100, sold transaction range $32,500-$36,400.
         18 active comps and 7 sold comps cited. Confidence: High.
         Recommended value: $34,500-$35,800.]

You: What's the wholesale vs retail spread on this?

Claude: [Franchise retail predicted: $35,200. Independent wholesale-proxy:
         $29,900. Spread: $5,300 (15.1%). Recommended trade-in offer range:
         $29,500-$31,000.]
```

---

### For Lenders & Portfolio Risk Managers

You manage auto loan portfolios and need to understand how collateral values are moving to set residual forecasts and manage exposure.

**Typical workflow:**
1. Track depreciation curves for models concentrated in your portfolio
2. Compare EV vs ICE depreciation rates to assess segment-level risk
3. Rank brands by residual retention to calibrate advance rates
4. Identify geographic value variance for state-level collateral adjustments
5. Batch-revalue a sample of VINs from the portfolio to spot underwater loans

**Example conversations:**
```
You: How fast is the Tesla Model Y depreciating? Show me the curve for the
     past year.

Claude: [Multi-point depreciation curve: 87.3% retention at 1 year,
         depreciating at 1.06% monthly — faster than the SUV segment
         average of 0.52%. Curve is accelerating.]

You: Revalue these 20 VINs from our Q1 portfolio sample
     [list of VINs]

Claude: [Portfolio Scanner processes each VIN. 3 flagged as underwater
         (LTV > 100%), 2 at high risk (LTV > 120%). Average portfolio
         value declined 8.2% from origination.]
```

---

### For OEM Analysts & Regional Directors

You need competitive intelligence, market share tracking, EV adoption data, and allocation recommendations — faster than syndicated reports deliver.

**Typical workflow:**
1. Monthly market share check: brand-level share with basis point changes vs prior period
2. Segment conquest analysis: who is winning in SUVs, pickups, sedans — and where the conquest opportunities are
3. EV penetration tracking: electrified sales as % of total market, broken down by brand
4. Regional demand heatmap: state-by-state volume and pricing to guide allocation decisions
5. Dealer group benchmarking: rank retail partners by volume, DOM, and efficiency

**Example conversations:**
```
You: How did Honda do vs Toyota in SUV market share last month nationally?

Claude: [Toyota holds 18.4% SUV segment share vs Honda at 11.2%. Toyota
         gained 45 bps driven by RAV4 (+2,100 units). Honda lost 30 bps.
         Gap widened to 7.2 percentage points.]

You: Which states should we allocate more CR-V inventory to?

Claude: [Regional demand heatmap shows CR-V is under-penetrated in Florida
         (6.1% segment share vs 11.2% national) and Georgia (7.3%).
         Increasing allocation by 200 units/month to these states could
         capture an estimated 450 additional sales based on current
         demand-to-supply ratios.]
```

---

### For Automotive Journalists & Market Researchers

You need timely, data-backed stories and trend analyses — not stale estimates or anecdotal observations.

**Typical workflow:**
1. "What are the fastest depreciating cars right now?" — year-over-year depreciation rankings with example current deals
2. "Is EV price parity getting closer?" — EV vs ICE gap by segment with convergence estimates
3. "Which new cars still have markups?" — MSRP parity tracking showing supply-constrained vs over-supplied models
4. "Where is the cheapest state to buy a used Tacoma?" — regional price variance with dollar savings calculations
5. Monthly market report: all five Market Trends Reporter workflows combined into a comprehensive briefing

**Example conversations:**
```
You: What are the fastest depreciating vehicles in the US right now?

Claude: [Top 15 by depreciation rate. Tesla Model S leads at -22.4% YoY,
         followed by BMW i4 at -19.8%. Example deals: 2022 Model S at
         $48,200 (was $94,990 MSRP). Best value holders: Toyota Tacoma
         at -3.1%, Porsche 911 at -4.2%.]

You: Give me a full monthly market report

Claude: [Executive summary + Depreciation Watch + Best Consumer Deals +
         EV Transition Update + Regional Pricing + New Car Markup Monitor.
         Structured with section headers and data citations.]
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Claude Code (CLI or VS Code)                   │
│                                                 │
│  ┌──────────────┐  ┌─────────────────────────┐  │
│  │  4 Commands   │  │  8 Skills               │  │
│  │  /price-check │  │  competitive-pricer     │  │
│  │  /vin-lookup  │  │  vehicle-appraiser      │  │
│  │  /market-     │  │  deal-finder            │  │
│  │   snapshot    │  │  inventory-intelligence │  │
│  │  /setup-mcp   │  │  market-share-analyzer  │  │
│  │               │  │  market-trends-reporter │  │
│  │               │  │  depreciation-tracker   │  │
│  │               │  │  stocking-guide         │  │
│  └──────┬───────┘  └────────────┬────────────┘  │
│         │                       │                │
│  ┌──────┴───────────────────────┴────────────┐  │
│  │  Portfolio Scanner Agent                   │  │
│  │  (batch VIN processing)                    │  │
│  └──────────────────┬────────────────────────┘  │
│                     │                            │
│  ┌──────────────────┴────────────────────────┐  │
│  │  MarketCheck MCP Server                    │  │
│  │  @marketcheckhub/mcp-client (via npx)      │  │
│  └──────────────────┬────────────────────────┘  │
└─────────────────────┼───────────────────────────┘
                      │ HTTPS
          ┌───────────┴───────────┐
          │  MarketCheck API       │
          │  mcp.marketcheck.com   │
          │                        │
          │  50M+ listings         │
          │  VIN decode            │
          │  Price prediction      │
          │  Sold transactions     │
          │  Active inventory      │
          └────────────────────────┘
```

---

## API Tools Available via MCP

Once connected, the plugin has access to these MarketCheck MCP tools:

| Tool | Purpose |
|------|---------|
| `decode_vin_neovin` | Decode any VIN to full specs — year, make, model, trim, MSRP, engine, drivetrain, fuel type |
| `predict_price_with_comparables` | ML-based price prediction for a VIN with comparable vehicle citations |
| `search_active_cars` | Search current active dealer listings with 30+ filters (YMMT, zip/radius, price, DOM, stats, facets) |
| `search_past_90_days` | Search recently sold/expired listings for transaction evidence |
| `get_car_history` | Full listing history for a VIN across all dealers over time |
| `get_sold_summary` | Aggregated sold transaction data — market share, volume rankings, average prices, DOM by any dimension |

---

## Getting Help

- **MarketCheck API docs:** [https://www.marketcheck.com](https://www.marketcheck.com)
- **Plugin issues:** [https://github.com/MarketcheckHub/marketcheck-cowork-plugin/issues](https://github.com/MarketcheckHub/marketcheck-cowork-plugin/issues)
- **API key:** Sign up at [https://www.marketcheck.com](https://www.marketcheck.com)

---

## License

MIT

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
