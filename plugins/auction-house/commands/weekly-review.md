---
description: Weekly auction operations review — lane projection + consignment pipeline + buyer targeting refresh across target DMAs.
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__get_sold_summary", "mcp__marketcheck__predict_price_with_comparables"]
---

Full weekly review for auction house operations (~15 minutes).

## Step 0: Load profile

Read `~/.claude/marketcheck/auction-house-profile.json`. Extract all fields. If no profile, suggest `/auction-house:onboarding`.

## Step 1: Multi-agent launch (parallel)

Launch in parallel:
- **Agent A**: `auction-house:dma-scanner` — "DMA market intelligence for state=[primary state]. Date range: [prior month]. Sections: demand_snapshot, supply_health, top_models."
- **Agent B**: `auction-house:brand-market-analyst` — "Brand share and depreciation for state=[primary state]. Date range: [prior month]. Sections: brand_share, depreciation."

## Step 2: Consignment pipeline (inline while agents run)

Call `mcp__marketcheck__search_active_cars` with `state`, `car_type=used`, `seller_type=dealer`, `sort_by=dom`, `sort_order=desc`, `rows=30`.

For top 10 aged units (DOM > 60): call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=independent`. Calculate expected hammer = predicted × 0.92.

Group by dealer — identify top consignment prospects.

## Step 3: Buyer targeting refresh

Call `mcp__marketcheck__search_active_cars` with `state`, `car_type=used`, `seller_type=dealer`, `facets=dealer_id|0|30|2`, `stats=dom`, `rows=0`.

Identify dealers with avg DOM > 50 and 30+ units — these are this week's buyer prospects.

## Step 4: Compile weekly report

Format:
```
WEEKLY AUCTION REVIEW — Week of [Date]
═══════════════════════════════════════

MARKET OVERVIEW
[From dma-scanner: volume, ASP, DOM, days supply, trend]

LANE PROJECTION (next sale)
[Segment, D/S Ratio, Sell-Through Est, Recommended Units, Signal]

CONSIGNMENT PIPELINE
[Top 10 units: VIN, YMMT, DOM, Price, Expected Hammer, Dealer]
[Top 5 consignment prospect dealers]

BUYER PROSPECTS
[Top 10 dealers by buyer score: Name, Units, Avg DOM, Needs]

BRAND WATCH
[Top gainers/losers in share, depreciation alerts]

TOP 5 ACTIONS THIS WEEK
1. [Consignment outreach]
2. [Buyer targeting]
3. [Lane planning adjustment]
4. [Pricing/reserve recommendation]
5. [Market opportunity]
```
