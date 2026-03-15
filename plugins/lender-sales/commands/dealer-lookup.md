---
description: Quick dealer profile by name, domain, or dealer ID — inventory summary, lending fit, and aging analysis.
allowed-tools: ["Read", "mcp__marketcheck__search_active_cars", "mcp__marketcheck__predict_price_with_comparables"]
argument-hint: [dealer name, domain, or dealer_id]
---

Quick dealer lookup for lender sales reps (~2 minutes).

## Step 0: Parse input

Use $ARGUMENTS as dealer identifier. Determine type:
- Numeric → dealer_id
- Contains `.` → web domain (use as `source` filter)
- Otherwise → dealer name (search by `dealer_name`)

## Step 1: Load profile

Read the `marketcheck-profile.md` project memory file. Extract lending criteria. If no profile, proceed with defaults.

## Step 2: Get dealer inventory

Call `mcp__marketcheck__search_active_cars` with appropriate dealer filter, `car_type=used`, `facets=make|0|15|1,body_type|0|10|1`, `stats=price,dom,miles`, `rows=0`.

## Step 3: Lending criteria overlay

Call `mcp__marketcheck__search_active_cars` with dealer filter + `price_range=[min]-[max]`, `year=[year_range]`, `miles_range=0-[max_mileage]`, `rows=0`, `stats=price`.

## Step 4: Aged units count

Call `mcp__marketcheck__search_active_cars` with dealer filter, `dom_range=60-999`, `rows=0`.

## Step 5: Deliver summary

Format:
```
DEALER LOOKUP: [Dealer Name]
═════════════════════════════

Location:        [City, State]
Total Units:     [count]
Avg Price:       $[price]
Avg DOM:         [days]
Avg Miles:       [miles]

LENDING FIT
  Matching Units: [count] ([%] of lot)
  Avg Match Price: $[price]

INVENTORY MIX
  Top Makes: [list]
  Top Segments: [list]

AGING
  Units > 60 DOM: [count]
  Est. Floor Burn: $[amount]/month

VERDICT: [STRONG/MODERATE/LIGHT] fit — [1-sentence recommendation]
```

Suggest: "Want a full brief? Say 'prep me for a meeting with [dealer]'"
