---
description: Quick market demand snapshot for a state or region
allowed-tools: ["mcp__marketcheck__get_sold_summary", "mcp__marketcheck__search_active_cars"]
argument-hint: [state-code, e.g. "TX" or "CA"]
---

Quick market demand snapshot showing what's selling, what's sitting, and where the opportunities are. Takes 30 seconds.

## Step 1: Parse input

Check $ARGUMENTS:

- **If a 2-letter state code** (e.g., "TX", "CA"): Use it directly
- **If a state name** (e.g., "Texas"): Convert to 2-letter code
- **If empty**: Check dealer profile at `~/.claude/marketcheck/dealer-profile.json` for `location.state`. If no profile, ask: "Which state? (e.g., TX, CA, FL)"

## Step 2: Pull demand data

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: the state code
- `ranking_dimensions`: "make,model"
- `ranking_measure`: "sold_count"
- `ranking_order`: "desc"
- `top_n`: 15
- `date_from`: first day of previous month (YYYY-MM-01)
- `date_to`: last day of previous month

## Step 3: Pull segment data

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: same state
- `ranking_dimensions`: "body_type"
- `ranking_measure`: "sold_count"
- `ranking_order`: "desc"
- Same date range

## Step 4: Pull supply data

Call `mcp__marketcheck__search_active_cars` with:
- `state`: same state
- `facets`: "body_type|0|20|1,make|0|30|2"
- `rows`: 0

## Step 5: Present snapshot

```
MARKET SNAPSHOT: [State Name] — [Month Year]

TOP SELLING MODELS:
#  | Make Model          | Sold | Avg Price  | Avg DOM
1  | Toyota RAV4         | XXX  | $XX,XXX    | XX days
2  | Ford F-150          | XXX  | $XX,XXX    | XX days
...

SEGMENT DEMAND:
Body Type  | Sold  | Avg Price  | Active Supply | Demand/Supply
SUV        | X,XXX | $XX,XXX    | X,XXX         | X.Xx
Pickup     | X,XXX | $XX,XXX    | X,XXX         | X.Xx
Sedan      | X,XXX | $XX,XXX    | X,XXX         | X.Xx
...

HOT OPPORTUNITIES (high demand, low supply):
- [Body type/make-model with demand/supply ratio > 1.5]

OVERSUPPLIED (consider avoiding):
- [Body type/make-model with demand/supply ratio < 0.5]
```

End with: "Want to dig deeper into any segment? Try asking about specific makes, models, or body types."
