---
name: weekly-dealer-review
description: >
  This skill should be used when the user asks for a "weekly review",
  "weekly inventory scan", "weekly stocking check", "full lot pricing scan",
  "hot list this week", "what should I stock this week", "weekly dealer report",
  "inventory review", "competitive scan", or needs a tactical weekly analysis
  covering full inventory pricing, stocking recommendations, and market demand.
version: 0.1.0
---

# Weekly Dealer Review — Full Inventory Scan + Stocking Intelligence

A tactical weekly analysis that prices every unit on the lot against the market, generates a stocking hot list for auction buying, and provides a market demand snapshot. Run this every Monday morning or before major auction days.

## Dealer Profile (Load First)

1. Read `~/.claude/marketcheck/dealer-profile.json`
2. If the file **does not exist**: Tell the user: "No dealer profile found. Run `/dealer-onboarding` to set up your dealer context once." Then stop.
3. If the file **exists**, extract all fields:
   - `dealer_id`, `dealer_name`, `dealer_type`, `franchise_brands`
   - `zip`/`postcode`, `state`/`region`, `country`
   - `radius`, `target_margin`, `recon_cost`, `floor_plan_per_day`, `max_dom`, `aging_threshold`
4. **Tool routing by country:**
   - **US**: All tools available — `search_active_cars`, `predict_price_with_comparables`, `get_sold_summary`, `decode_vin_neovin`
   - **UK**: `search_uk_active_cars`, `search_uk_recent_cars` only. Section 2 (Hot List) and Section 3 (Demand Snapshot) are **US-only** — skip for UK dealers and note this.
5. Confirm: "Running weekly review for **[dealer_name]**..."

## Section 1: Full Lot Competitive Scan

Price every unit on the dealer's lot against the market.

**Step 1 — Pull the dealer's inventory:**

Call `mcp__marketcheck__search_active_cars` (US) or `mcp__marketcheck__search_uk_active_cars` (UK) with:
- `dealer_id`: from profile (if available)
- `rows`: `50`
- `sort_by`: `dom`
- `sort_order`: `desc`
- `car_type`: `used`

If `dealer_id` is null, ask the user for their dealer website domain and search by `dealer_website` instead.

**Step 2 — Price each unit (US):**

For each VIN returned (prioritize the 25 highest-DOM units first):
- Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type`
- Record: predicted_price, comparable count

**Step 2 — Price each unit (UK):**

For each unit, call `mcp__marketcheck__search_uk_active_cars` with matching year/make/model within radius, `rows=10`, to get comp listings. Calculate median price from comps.

**Step 3 — Classify each unit:**

- **Below Market** (bottom quartile): Listed price < predicted price × 0.95 → consider raising
- **At Market** (middle 50%): Listed price within ±5% of predicted price → hold
- **Above Market** (top quartile): Listed price > predicted price × 1.05 → consider reducing

Sort by overpricing severity (most overpriced first — highest aging risk).

**Step 4 — Present:**

```
FULL LOT COMPETITIVE SCAN — [N] Units Analyzed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VIN (last 6) | Year Make Model | DOM | Your Price | Market Price | Gap % | Position | Action
-------------|-----------------|-----|------------|--------------|-------|----------|-------
[sorted by most overpriced first]

SUMMARY:
  🔴 [N] units ABOVE MARKET (avg [X]% overpriced) — reduce to recover ~$[X,XXX]
  🟢 [N] units AT MARKET — hold
  🔵 [N] units BELOW MARKET — consider raising [N] units to capture ~$[X,XXX]
```

## Section 2: Stocking Hot List (US Only)

Identify the top models to seek at auction this week.

**Step 1 — Get fastest-turning models:**

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile
- `inventory_type`: `Used`
- `dealer_type`: from profile
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `average_days_on_market`
- `ranking_order`: `asc`
- `top_n`: `20`
- `date_from` / `date_to`: most recent full month

**Step 2 — Get highest-volume sellers:**

Call `mcp__marketcheck__get_sold_summary` with same filters but:
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: `20`

**Step 3 — Cross-reference and check supply:**

For models appearing in both lists (fast turn + high volume), call `mcp__marketcheck__search_active_cars` with `make`, `model`, `zip`, `radius`, `car_type=used`, `stats=price`, `rows=0` to get supply count and median price.

**Step 4 — Calculate opportunity score and max buy price:**

- Demand-to-Supply Ratio = monthly sold / active supply
- Max Auction Buy Price = median_market_price × (1 - target_margin%) - recon_cost
- Opportunity Score = (D/S Ratio × 40) + (Turn Speed × 30) + (Volume × 30)

**Step 5 — Cross-reference with current lot:**

Check which hot list models the dealer already has in stock (from Section 1 data). Flag gaps: "You have 0 units of [Model X] — highest opportunity this week."

**Step 6 — Present:**

```
STOCKING HOT LIST — Top 10 Models to Seek ([State], [Month])
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rank | Make Model | Turn Days | Monthly Sold | Supply | D/S Ratio | Max Buy | On Your Lot?
-----|------------|-----------|-------------|--------|-----------|---------|-------------
[top 10 by opportunity score]
```

**UK dealers**: Skip this section. Note: "Hot List generation requires US sold data. Use the competitive scan above for UK pricing intelligence."

## Section 3: Market Demand Snapshot (US Only)

Show what's actually selling in the dealer's market.

**Step 1 — Top models by volume:**

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile
- `ranking_dimensions`: `make,model`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: `15`
- `date_from` / `date_to`: most recent full month

**Step 2 — Body type breakdown:**

Call `mcp__marketcheck__get_sold_summary` with:
- Same date/state filters
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: `10`

**Step 3 — Present:**

```
MARKET DEMAND — [State] — [Month Year]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Top 10 Selling Models:
Rank | Make Model | Sold Count | Avg Price | Avg DOM
-----|------------|------------|-----------|--------
[table]

Demand by Segment:
Body Type | Sold Count | Share %
----------|------------|--------
[table]
```

**UK dealers**: Skip this section. Note: "Market demand data requires US sold analytics."

## Final Output

Combine all sections into a single report:

```
WEEKLY DEALER REVIEW — [Dealer Name] — Week of [Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Section 1: Full Lot Competitive Scan]

[Section 2: Stocking Hot List — US only]

[Section 3: Market Demand Snapshot — US only]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOP 5 ACTIONS THIS WEEK:
1. [Highest-impact action with $ estimate]
2. [Second action]
3. [Third action]
4. [Fourth action]
5. [Fifth action]

Estimated total impact: $[X,XXX] in margin recovery + $[X,XXX] in stocking opportunity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For strategic monthly analysis (market share, depreciation, trends), ask for your "monthly review".
```
