---
description: Quick market demand snapshot for your brand across states or nationally
allowed-tools: ["mcp__marketcheck__get_sold_summary", "mcp__marketcheck__search_active_cars", "Read"]
argument-hint: [state-code, e.g. "TX" or "CA" or "national"]
---

Quick market demand snapshot showing what is selling, competitive positioning, and regional demand signals for your brand. Designed for OEM regional managers, brand strategists, and distributors who need a rapid competitive read on a specific geography. Takes 30 seconds.

## Step 0: Load profile

Read `~/.claude/marketcheck/manufacturer-profile.json`.

- If exists: extract `manufacturer.brands`, `manufacturer.competitor_brands`, `manufacturer.states`, `user.name`, `user.company` to highlight your brands and competitors in results
- If not found: ask "Which brand(s) do you represent?" and "Which competitors to track?" Suggest running `/onboarding` for persistent setup.

## Step 1: Parse input

Check $ARGUMENTS:

- **If a 2-letter state code** (e.g., "TX", "CA"): Use it directly
- **If a state name** (e.g., "Texas"): Convert to 2-letter code
- **If "national"**: Use national scope (omit state filter)
- **If empty**: Check profile for `manufacturer.states`. If available, use the first state. Otherwise ask: "Which state? (e.g., TX, CA, FL, or 'national')"

## Step 2: Pull your brand demand data

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: the state code (omit for national)
- `make`: your primary brand (first in brands)
- `ranking_dimensions`: "make,model"
- `ranking_measure`: "sold_count"
- `ranking_order`: "desc"
- `top_n`: 15
- `date_from`: first day of previous month (YYYY-MM-01)
- `date_to`: last day of previous month

## Step 3: Pull competitive share data

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: same state
- `ranking_dimensions`: "make"
- `ranking_measure`: "sold_count"
- `ranking_order`: "desc"
- `top_n`: 20
- Same date range

This gives market share for all brands including yours and competitors.

## Step 4: Pull segment data

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: same state
- `make`: your primary brand
- `ranking_dimensions`: "body_type"
- `ranking_measure`: "sold_count"
- `ranking_order`: "desc"
- Same date range

Repeat without `make` filter for total market segment breakdown.

## Step 5: Pull supply data

Call `mcp__marketcheck__search_active_cars` with:
- `state`: same state
- `make`: your primary brand
- `car_type`: "new"
- `facets`: "body_type|0|20|1,model|0|30|2"
- `rows`: 0

## Step 6: Present snapshot

```
MARKET SNAPSHOT: [State Name or National] — [Month Year]
Your Brand: [Brand] ★ | Competitors: [list]

YOUR BRAND'S COMPETITIVE STANDING:
Brand        | Sold  | Share % | Rank | Signal
-------------|-------|---------|------|--------
★ [Your Brand]| X,XXX | XX.X%   | #X   | [Your position]
[Comp A]     | X,XXX | XX.X%   | #X   |
[Comp B]     | X,XXX | XX.X%   | #X   |
[Comp C]     | X,XXX | XX.X%   | #X   |

YOUR TOP SELLING MODELS:
#  | Model               | Sold | Avg Price  | Avg DOM
1  | [Model A]           | XXX  | $XX,XXX    | XX days
2  | [Model B]           | XXX  | $XX,XXX    | XX days
...

SEGMENT DEMAND — Your Brand vs Market:
Body Type  | Your Sold | Market Sold | Your Share % | Active Supply | D/S Signal
SUV        | X,XXX     | XX,XXX      | XX.X%        | X,XXX         | [UNDER/BALANCED/OVER]
Pickup     | X,XXX     | XX,XXX      | XX.X%        | X,XXX         | [signal]
Sedan      | X,XXX     | XX,XXX      | XX.X%        | X,XXX         | [signal]
...

ALLOCATION SIGNALS:
- Under-supplied: [Models with D/S > 1.5 — increase allocation]
- Over-supplied: [Models with D/S < 0.8 — reduce or incentivize]

COMPETITIVE INTELLIGENCE:
- Your brand ranks #[X] in [State] with [XX.X]% share
- Nearest competitor [Brand] is [ahead/behind] by [X] units
- Segment with largest competitive gap: [body_type] — [Competitor] leads by [X] units
```

End with: "Want to dig deeper? Try 'competitor analysis', 'EV adoption in [state]', or 'regional demand heatmap'."
