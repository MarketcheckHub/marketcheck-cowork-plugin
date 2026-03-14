---
name: pitch-deck-data
description: >
  This skill should be used when the user asks for "data for my pitch",
  "market stats for dealer meeting", "prepare talking points",
  "dealer presentation data", "meeting data for [state]",
  "local market stats", "market intelligence for sales call",
  "arm me with data for this meeting",
  or needs localized market data to reference in a dealer meeting
  to demonstrate expertise and value.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Pitch Deck Data — Market Intelligence for Dealer Meetings

## Profile
Load `~/.claude/marketcheck/lender-sales-profile.json` if exists. Extract: lending_type, target_states, price_range_min, price_range_max, country. If missing, ask for state. **US**: `get_sold_summary`, `search_active_cars`. **UK**: `search_uk_active_cars` only (supply data only — limited talking points). Confirm: "Using profile: [company], [lending_type]". All preference values from profile — do not re-ask.

## User Context
Lender sales rep preparing data points for a dealer meeting. The goal is to arm the rep with local market intelligence they can cite during the conversation to build credibility and frame their lending products as informed, data-backed solutions.

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

## Output
Formatted talking points section with specific numbers. Each point on its own line, ready to copy-paste. Include source citation: "Source: MarketCheck market data, [Month Year], [State]." Group into: MARKET OVERVIEW (3-4 points), PRICING TRENDS (2-3 points), OPPORTUNITY FRAMING (2-3 points). Total ~10 points maximum — concise enough for a sales conversation.
