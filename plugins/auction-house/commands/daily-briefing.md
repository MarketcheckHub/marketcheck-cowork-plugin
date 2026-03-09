---
description: Morning operational scan — consignment leads + market price movements + lane pricing impact across your target DMAs.
allowed-tools: ["Read", "Agent", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__get_sold_summary"]
---

Quick morning scan for auction house operations (~5 minutes).

## Step 0: Load profile

Read `~/.claude/marketcheck/auction-house-profile.json`. Extract target_dmas, state, vehicle_segments, buyer_fee_pct, seller_fee_pct. If no profile, suggest `/auction-house:onboarding`.

## Step 1: New consignment leads (parallel)

Call `mcp__marketcheck__search_active_cars` with `state` (primary DMA), `car_type=used`, `seller_type=dealer`, `sort_by=dom`, `sort_order=desc`, `rows=15`, `stats=price,dom`. Focus on DOM > 75 — these are new wholesale-ready units appearing in the market.
→ **Extract only**: top 10 aged units with VIN, YMMT, DOM, price, dealer_name.

## Step 2: Market price movements

Call `mcp__marketcheck__search_active_cars` with `state`, `car_type=used`, `price_change=negative`, `sort_by=dom`, `sort_order=desc`, `rows=10`. These are dealers dropping prices — signal of wholesale motivation.
→ **Extract only**: YMMT, old price, new price, drop %, dealer_name, DOM.

## Step 3: Quick demand pulse

Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=5`, prior month dates.
→ **Extract only**: top 5 segments by volume.

## Step 4: Deliver briefing

Format:
```
DAILY AUCTION BRIEFING — [Date]
═══════════════════════════════

CONSIGNMENT LEADS (DOM > 75)
[Table: YMMT, DOM, Price, Dealer, City]

PRICE DROP ALERTS (dealers cutting prices)
[Table: YMMT, Was, Now, Drop%, Dealer, DOM]

DEMAND PULSE
[Top 5 segments by sold volume]

TOP 3 ACTIONS TODAY
1. [Most actionable consignment call]
2. [Price drop follow-up]
3. [Lane planning note]
```
