---
name: pitch-deck-data
description: >
  Market intelligence for dealer meetings. Triggers: "data for my pitch",
  "market stats for dealer meeting", "prepare talking points",
  "dealer presentation data", "meeting data for [state]",
  "local market stats", "market intelligence for sales call",
  "arm me with data for this meeting",
  localized market data to reference in a dealer meeting
  to demonstrate expertise and value.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Pitch Deck Data — Market Intelligence for Dealer Meetings

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: lending_type, target_states, price_range_min, price_range_max, country. If missing, ask for state. **US**: `get_sold_summary`, `search_active_cars`. **UK**: `search_uk_active_cars` only (supply data only — limited talking points). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep preparing data points for a dealer meeting. The goal is to arm the rep with local market intelligence they can cite during the conversation to build credibility and frame their lending products as informed, data-backed solutions.

## Gotchas

1. **US-only for sold data.** `get_sold_summary` is US-only. For UK profiles, only supply-side talking points are available (active inventory counts, DOM, pricing from `search_uk_active_cars`). Clearly note that volume trend and velocity data are unavailable for UK.
2. **State vs ZIP scoping.** Talking points scoped to a state are broad. If the dealer operates in a metro area, consider using `zip` + `radius=50` for `search_active_cars` supply calls to make the data more locally relevant. Use state-level for `get_sold_summary` (which only supports state).
3. **Do not present raw API numbers as precision.** Round sold counts to nearest 100 for state-level data, nearest 10 for local. Round prices to nearest $100. Dealers will question exact numbers that imply false precision.
4. **Stale month risk.** If today is the 1st-5th of the month, prior month sold data may be incomplete. Use the month before that as the primary period, and note "(data may still be settling for [recent month])."
5. **Never reveal lender-internal metrics.** Talking points are for external use with dealers. Do not include penetration rates, spread assumptions, or internal scoring in the output.

## Workflow: Local Market Talking Points

1. **What's selling** — Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=10`, `date_from` (first of prior month), `date_to` (last of prior month).
   → **Extract only**: top 10 models with sold_count, average_sale_price. Discard full response.

2. **Volume trend** — Same call with date range shifted back one month. Compare total volume.
   → **Extract only**: total sold_count. Discard full response.

3. **Pricing trends** — Call `mcp__marketcheck__get_sold_summary` with `state`, `inventory_type=Used`, `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=8`, current + 3 months ago.
   → **Extract only**: per body_type — average_sale_price for both periods. Discard full response.

4. **Supply snapshot** — Call `mcp__marketcheck__search_active_cars` with `state`, `car_type=used`, `seller_type=dealer`, `stats=price,dom`, `rows=0`.
   → **Extract only**: total active, median_price, avg_dom. Discard full response.

5. **Calculate days supply** — active_inventory / (monthly_sold / 30). Under 45 = tight (dealers stocking aggressively), 45-75 = balanced, over 75 = building (dealers may slow purchases).

6. **Generate talking points** — Format as quotable statements:
   - "The [state] used car market moved [X] units last month, [up/down Y%] from the prior month."
   - "Average used vehicle transaction price is $[Z], [trending up/down/flat]."
   - "[Segment] is the fastest-turning category at [X] days on market."
   - "Top sellers right now are [Model 1], [Model 2], and [Model 3] — we have strong programs for all of these."
   - "Current inventory levels sit at [X] days supply — dealers [are stocking aggressively / have room to grow / may be cautious]."
   - "SUV transaction prices [rose/fell] [X]% over 3 months — [strong/weakening] residuals for your lending portfolio."
   - If lending_type is floor_plan: "Average DOM across the state is [X] days — every day above 30 is costing dealers money."

7. **Tailor to specific dealer (optional)** — If user specifies a dealer, add:
   - "[Dealer] has [X] units in our lending sweet spot"
   - "Their average DOM is [X] — [above/below] the state average"

## Output Template

```
── Pitch Data: [State] Market Intelligence ── [Month Year] ──

MARKET OVERVIEW
- "The [state] used car market moved ~[X] units last month, [up/down ~Y%] from [prior month]."
- "[Segment] is the fastest-turning category at [X] days on market."
- "Current inventory levels sit at [X] days supply — dealers [interpretation]."
- "Top sellers right now are [Model 1], [Model 2], and [Model 3]."

PRICING TRENDS
- "Average used vehicle transaction price is $[Z], [trending up/down/flat] over 3 months."
- "SUV transaction prices [rose/fell] [X]% over 3 months — [strong/weakening] residuals."
- "[Body type] pricing spread: $[low]-$[high], median $[mid]."

OPPORTUNITY FRAMING
- "We have strong programs for [top-selling models] — competitive rates for your buyers."
- "Every day above 30 DOM costs dealers money — our floor plan rates start at [X]."
- "[If specific dealer]: You have [X] units in our lending sweet spot ($[min]-$[max])."

Source: MarketCheck market data, [Month Year], [State].
```

## Output
Formatted talking points section with specific numbers. Each point on its own line, ready to copy-paste. Include source citation: "Source: MarketCheck market data, [Month Year], [State]." Group into: MARKET OVERVIEW (3-4 points), PRICING TRENDS (2-3 points), OPPORTUNITY FRAMING (2-3 points). Total ~10 points maximum — concise enough for a sales conversation.

## Self-Check (before presenting to user)

1. **All numbers are rounded appropriately?** State-level volumes rounded to nearest 100, local to nearest 10, prices to nearest $100. No false precision.
2. **Talking points are dealer-facing?** No internal lender metrics (penetration, spread, scoring) in the output. Everything should be something the rep can say out loud.
3. **Trend direction matches the data?** If volume went from 5,200 to 5,100, that is "roughly flat" or "down ~2%", not "declining sharply." Verify directional language matches magnitude.
4. **Days supply calculation is correct?** days_supply = active_inventory / (monthly_sold / 30). Under 45 = tight, 45-75 = balanced, over 75 = building. Verify the interpretation matches the number.
5. **Source citation is present?** Every output must end with "Source: MarketCheck market data, [Month Year], [State]."
6. **No more than 10 points total?** The rep needs a quick cheat sheet, not a research paper. If you generated more than 10, prune the weakest.
