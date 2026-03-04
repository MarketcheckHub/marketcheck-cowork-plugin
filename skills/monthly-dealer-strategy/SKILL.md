---
name: monthly-dealer-strategy
description: >
  This skill should be used when the user asks for a "monthly review",
  "monthly strategy", "monthly dealer report", "strategic review",
  "monthly market analysis", "end of month analysis", "what's my market
  doing this month", "monthly performance", "strategic briefing",
  or needs a comprehensive monthly analysis covering market share,
  depreciation trends, market conditions, and full inventory intelligence.
version: 0.1.0
---

# Monthly Dealer Strategy — Comprehensive Market Intelligence Report

A strategic monthly analysis that gives a dealer the complete picture: how their brand is performing in the market, which models are depreciating fastest, what the broader market trends look like, and a full inventory intelligence report. Run this on the first Monday of each month.

**Note: This skill is primarily US-focused.** Most sections require `get_sold_summary` which is US-only. UK dealers will receive Section 1 (inventory competitive scan from the weekly review data) and a supply-side market overview only.

## Dealer Profile (Load First)

1. Read `~/.claude/marketcheck/dealer-profile.json`
2. If the file **does not exist**: Tell the user: "No dealer profile found. Run `/dealer-onboarding` to set up your dealer context once." Then stop.
3. If the file **exists**, extract all fields:
   - `dealer_id`, `dealer_name`, `dealer_type`, `franchise_brands`
   - `zip`/`postcode`, `state`/`region`, `country`
   - `radius`, `target_margin`, `recon_cost`, `floor_plan_per_day`, `max_dom`, `aging_threshold`
4. **Tool routing by country:**
   - **US**: All tools available
   - **UK**: Only `search_uk_active_cars` and `search_uk_recent_cars`. Sections 1-4 are **US-only**. Section 5 (supply-side inventory scan) works for UK. Tell UK dealers: "The monthly strategy report relies on US sold transaction data for market share, depreciation, and trend analysis. For UK dealers, a competitive inventory scan is available."
5. Confirm: "Running monthly strategy report for **[dealer_name]**..."

## Section 1: Brand Performance in Your Market (US Only)

How is the dealer's brand performing relative to competitors in their state?

**Step 1 — Current month market share:**

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile
- `dealer_type`: from profile
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: `20`
- `date_from` / `date_to`: most recent full month

**Step 2 — Prior month for comparison:**

Repeat the same call with `date_from` / `date_to` set to the month before.

**Step 3 — Calculate share change:**

For each make:
- Current Share % = make's sold_count / total sold_count × 100
- Prior Share % = same calculation for prior month
- Share Change (bps) = (Current % - Prior %) × 100
- Volume Change % = (Current sold - Prior sold) / Prior sold × 100

**Step 4 — Present:**

```
1. BRAND PERFORMANCE — [State] — [Current Month] vs [Prior Month]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Make | Current Sold | Share % | Prior Share % | Change (bps) | Trend
-----|-------------|---------|---------------|-------------|------
[table — highlight dealer's franchise brands, flag GAINING (+50bps) or LOSING (-50bps)]

Your Brand Summary: [Brand] holds [X]% share in [State], [up/down] [X] bps month-over-month.
[Volume: X units sold, ranking #X in the state]
```

## Section 2: Depreciation Watch — Your Inventory (US Only)

Which models currently on the dealer's lot are depreciating fastest?

**Step 1 — Get dealer's current inventory makes/models:**

Call `mcp__marketcheck__search_active_cars` with:
- `dealer_id`: from profile
- `facets`: `make|0|10|1,model|0|20|1`
- `rows`: `0`

Extract the top 5 make/model combinations by count on the lot.

**Step 2 — Get depreciation data for each:**

For each of the top 5 models, call `mcp__marketcheck__get_sold_summary` with:
- `make`, `model`: the model
- `state`: from profile
- `inventory_type`: `Used`
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `top_n`: `1`
- Date ranges: current month AND 3 months prior

**Step 3 — Calculate depreciation rate:**

- Price Change $ = current avg_sale_price - prior avg_sale_price
- Monthly Depreciation Rate % = (Price Change / prior avg_sale_price) / 3 months × 100
- Flag models with monthly depreciation > 1.5% as **ACCELERATING DEPRECIATION**

**Step 4 — Present:**

```
2. DEPRECIATION WATCH — Models on Your Lot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Make Model | Units on Lot | Avg Price 3mo Ago | Avg Price Now | Monthly Depr. Rate | Alert
-----------|-------------|-------------------|---------------|--------------------|---------
[table — flag >1.5%/month as ⚠️ ACCELERATING]

Action: [Specific recommendations for fast-depreciating models — price aggressively or wholesale]
```

## Section 3: Market Trends (US Only)

What's happening in the broader market that affects the dealer?

**Step 1 — Fastest depreciating models statewide:**

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile
- `inventory_type`: `Used`
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_sale_price`
- `ranking_order`: `asc`
- `top_n`: `15`
- Date range: current month

Cross-reference with a 3-month-prior call to identify which models dropped most.

**Step 2 — MSRP parity for franchise brands (if applicable):**

If dealer is franchise, call `mcp__marketcheck__get_sold_summary` with:
- `make`: each franchise brand
- `inventory_type`: `New`
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `price_over_msrp_percentage`
- `ranking_order`: `desc`
- `top_n`: `10`

**Step 3 — Present:**

```
3. MARKET TRENDS — [State]
━━━━━━━━━━━━━━━━━━━━━━━━━

Fastest Depreciating Models (statewide):
Make Model | 3mo Ago Avg | Current Avg | Drop $ | Drop % | On Your Lot?
-----------|-------------|-------------|--------|--------|-------------
[top 10]

[If franchise:]
New Car MSRP Status — [Brand]:
Model | Avg Sale vs MSRP | Status
------|------------------|-------
[Above MSRP / At MSRP / Below MSRP for each model]
```

## Section 4: Full Inventory Intelligence (US Only)

Comprehensive demand-to-supply analysis for the dealer's market.

**Step 1 — Demand-to-Supply Ratios:**

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: `30`
- Date range: most recent full month

Call `mcp__marketcheck__search_active_cars` with:
- `state`: from profile
- `car_type`: `used`
- `seller_type`: `dealer`
- `facets`: `make|0|50|2,model|0|50|2`
- `rows`: `0`

Calculate D/S Ratio for each model. Flag Under-supplied (>1.5), Balanced (0.8-1.5), Over-supplied (<0.8).

**Step 2 — Aging summary:**

Call `mcp__marketcheck__search_active_cars` with:
- `dealer_id`: from profile
- `dom_range`: `60-999`
- `rows`: `0`
- `stats`: `price,dom`

Get count and total value of aged units. Calculate floor plan burn.

**Step 3 — Turn rate by segment:**

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `average_days_on_market`
- `ranking_order`: `asc`
- `top_n`: `10`

**Step 4 — Present:**

```
4. INVENTORY INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━

Demand-to-Supply — Top Opportunities:
Make Model | Monthly Sold | Active Supply | D/S Ratio | Signal
-----------|-------------|---------------|-----------|-------
[top 10 under-supplied]

Aging Summary:
  Units > 60 days: [N] ($[X,XXX] floor plan burn/month)
  Units > 90 days: [N]
  Units > 120 days: [N]

Turn Rate by Segment:
Body Type | Avg DOM | Sold Volume | Speed
----------|---------|-------------|------
[table with Fastest/Average/Slowest labels]
```

## Section 5: Supply-Side Market Overview (US + UK)

This section works for both US and UK dealers using active listing data.

**US:** Call `mcp__marketcheck__search_active_cars`
**UK:** Call `mcp__marketcheck__search_uk_active_cars`

With:
- `zip`/`postcode`: from profile
- `radius`: from profile
- `car_type`: `used`
- `facets`: `make|0|20|1,body_type|0|10|1`
- `stats`: `price,dom`
- `rows`: `0`

Present: total active supply, breakdown by body type and make, average asking price, average DOM.

## Final Output

```
MONTHLY DEALER STRATEGY REPORT — [Dealer Name] — [Month Year]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Section 1: Brand Performance]
[Section 2: Depreciation Watch]
[Section 3: Market Trends]
[Section 4: Inventory Intelligence]
[Section 5: Supply-Side Market Overview]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
30-DAY ACTION PLAN:
1. [Highest $ impact action]
2. [Second action]
3. [Third action]
4. [Fourth action]
5. [Fifth action]

Key Metrics to Watch Next Month:
- [Brand] market share: currently [X]% — target [X]%
- Aging units: currently [N] — target < [N]
- Average DOM: currently [X] days — target < [X] days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Report period: [Month Year] | Data source: MarketCheck | Market: [State/Region]
```
