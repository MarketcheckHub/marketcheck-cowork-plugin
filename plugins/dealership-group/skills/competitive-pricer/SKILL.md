---
name: competitive-pricer
description: >
  This skill should be used when the user asks to "price this car",
  "am I priced right", "competitive pricing", "price check VIN",
  "who is undercutting me", "market price for this", "price my inventory",
  "compare my price", or needs help with pricing strategy, price positioning,
  competitive price analysis, or identifying pricing opportunities in their market.
version: 0.1.0
---

# Competitive Pricer — Real-Time Price Positioning Against Your Market

## Dealer Group Profile (Load First)

Before running any workflow, check for a saved dealer group profile:

1. Read `~/.claude/marketcheck/dealership-group-profile.json`.
2. If the file **does not exist**: Tell the user: "No dealer group profile found. Run `/onboarding` to set up your group context once." Then ask for the minimum required fields (ZIP, radius) to proceed with this one request.
3. If the file **exists**, determine which location to use:
   - Use `dealer_group.locations[dealer_group.default_location_index]` as the default location
   - If the user specifies a location name, find the matching location from `dealer_group.locations[]`
   - Extract from the selected location:
     - `zip` ← location's `zip`
     - `state` ← location's `state`
     - `dealer_id` ← location's `dealer_id`
     - `dealer_type` ← location's `dealer_type`
     - `franchise_brands` ← location's `franchise_brands`
   - Extract from profile:
     - `radius` ← `preferences.default_radius_miles`
     - `country` ← `location.country`
     - `cpo_program` ← `dealer_group.cpo_program`
     - `cpo_certification_cost` ← `dealer_group.cpo_certification_cost`
4. **Tool routing by country:**
   - **US**: Use `mcp__marketcheck__search_active_cars`, `mcp__marketcheck__decode_vin_neovin`, `mcp__marketcheck__predict_price_with_comparables`, `mcp__marketcheck__get_car_history`
   - **UK**: Use `mcp__marketcheck__search_uk_active_cars` for listing searches, `mcp__marketcheck__search_uk_recent_cars` for sold/recent data. VIN decode and ML price prediction are **not available** for UK — skip decode steps (ask user for Year/Make/Model/Trim) and use comp median price instead of predicted price.
5. Confirm briefly: "Using location: **[location name]**, [ZIP], [Country]"
6. **Dual pricing setup:** For all pricing workflows, the skill reports BOTH franchise and independent market prices. The location's own `dealer_type` determines the PRIMARY comparison. The other type provides SECONDARY context.

## CPO Detection

When pricing a vehicle, determine if it is Certified Pre-Owned (CPO):

1. **From inventory scan:** If the vehicle listing includes `is_certified=true`, it is CPO.
2. **From user input:** If the user states the vehicle is certified or CPO.
3. **From VIN history:** If `get_car_history` shows the vehicle listed as certified.

When a vehicle IS CPO:

- Call `predict_price_with_comparables` with `is_certified=true` for the CPO market price
- Also call WITHOUT `is_certified` (or with `is_certified=false`) for the non-CPO market price
- Search comps with `is_certified=true` filter for apples-to-apples CPO comparables
- Calculate and display the CPO premium:

```
CPO Market Price:      $XX,XXX  (based on N certified comps)
Non-CPO Market Price:  $XX,XXX  (based on N total comps)
CPO Premium:           +$X,XXX  (+X.X%)
Your Price:            $XX,XXX  (CPO unit)
Gap vs CPO Market:     -$XXX    (X.X% below CPO market — competitively priced)
```

When a vehicle is NOT CPO, skip the CPO-specific calls and price normally.

## User Context

The primary user is a **dealer group manager** (used car manager, pricing analyst, or GM at one of the group's locations) who needs to know whether their asking prices are competitive, where they stand relative to nearby sellers, and where margin is being left on the table or lost to aging inventory.

The following fields are loaded from the dealer group profile. Only ask if no profile exists:

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or Year/Make/Model/Trim | Always ask (vehicle-specific) |
| Auto | ZIP code (market center) | Profile location's `zip` |
| Auto | Search radius in miles | Profile `preferences.default_radius_miles` |
| Recommended | Mileage of the subject vehicle | Always ask (vehicle-specific) |
| Auto | Dealer type filter | Profile location's `dealer_type` |
| Optional | Target price or current asking price | Always ask if relevant |

If the user provides a VIN, always start with a decode to confirm specs before pricing (US only — UK dealers provide specs manually).

## Workflow: Price-Check a Single VIN

Use this when a dealer says "price check this VIN" or "am I priced right on this one."

1. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to confirm year, make, model, trim, body type, drivetrain, engine, and transmission. Present the decoded specs to the user for confirmation.

2. **Get predicted market prices (dual)** — Make TWO calls to `mcp__marketcheck__predict_price_with_comparables`:
   - **Primary:** with `vin`, `miles`, `zip`, `dealer_type` matching the source location's type (from profile). This is the primary comparison.
   - **Secondary:** with the same parameters but `dealer_type` set to the OTHER type (franchise<>independent). This provides market context.
   Record both predicted prices and their comparable VINs.

2a. **CPO pricing (if applicable)** — If the vehicle is CPO (detected per CPO Detection section above), make additional calls with `is_certified=true` for both franchise and independent predictions. Report CPO market price separately from non-CPO market price, and show the CPO premium.

3. **Pull competing active listings** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from step 1), `zip`, `radius=50`, `sort_by=price`, `sort_order=asc`, `rows=15`, `car_type=used`. This returns the competitive set. Additionally, call `mcp__marketcheck__search_active_cars` with the same parameters but add `dealer_type` matching the source location's type to get a filtered competitive set from SAME-type dealers only.

4. **Calculate price position** — Compare the dealer's asking price (or predicted price) against the competitive set:
   - Percentile rank (e.g., "Your price is lower than 72% of competing units")
   - Distance to the cheapest and most expensive unit
   - Median and mean market price
   - Number of competing units within +/- 5% of the subject price

5. **Deliver the verdict** — Classify the price as **Below Market** (bottom quartile), **At Market** (middle 50%), or **Above Market** (top quartile) and recommend an action: hold, adjust down, or raise. Show both market prices in the output:
```
Franchise Market Price:    $XX,XXX  (based on N comps)
Independent Market Price:  $XX,XXX  (based on N comps)
Your Price:                $XX,XXX  ([your dealer_type] dealer)
Gap vs Your Market:        $X,XXX   (X.X% [above/below] [your type] market) ← PRIMARY
Gap vs Other Market:       $X,XXX   (X.X% [above/below] [other type] market) ← CONTEXT
```

## Workflow: Batch Competitive Scan

Use this when a dealer provides a list of VINs (e.g., "check pricing on my front-line inventory").

1. **Accept VIN list** — Collect all VINs from the user. Confirm the market ZIP and radius once (applies to all).

2. **Loop per VIN** — For each VIN:
   - Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type` (Primary — matching source location's type).
   - Call `mcp__marketcheck__predict_price_with_comparables` with the same parameters but `dealer_type` set to the OTHER type (Secondary — franchise<>independent).
   - If the vehicle is CPO, make additional calls with `is_certified=true` for both dealer types.
   - Call `mcp__marketcheck__search_active_cars` with the decoded YMMT, `zip`, `radius`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used`.

3. **Build the price-position table** — For each VIN, calculate: asking price, franchise market price ("Franchise Mkt"), independent market price ("Independent Mkt"), delta vs primary market, delta vs secondary market, percentile rank, competing unit count, and recommended action.

4. **Prioritize actions** — Sort the table by largest overpricing first (highest risk of aging), then by largest underpricing (margin opportunity).

5. **Present the summary** — Show the full table plus a rollup: total units scanned, count overpriced, count underpriced, count at market, estimated margin recovery if adjusted.

## Workflow: Trade-In VIN Price History

Use this when a dealer asks "what's the history on this trade" or needs context before making an offer.

1. **Pull listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=desc` to get the full timeline of listings across dealers.

2. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to get full specs for accurate pricing.

3. **Get predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type`.

4. **Analyze the trajectory** — From the history, extract:
   - Number of dealers that have listed this VIN
   - Price at each listing and the direction of change
   - Total days on market across all listings
   - Whether the vehicle was ever listed as certified

5. **Deliver trade-in context** — Show the price trajectory chart, current market value, and flag any red flags (e.g., multiple dealer hops in a short period, steep price drops suggesting a problem unit).

## Workflow: Market Price Distribution

Use this when a dealer asks "what's the market look like for this model" or wants a statistical overview.

1. **Pull market stats** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=100`, `car_type=used`, `stats=price,miles`, `rows=0`. The `rows=0` returns only stats without individual listings.

2. **Pull the cheapest listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=asc`, `rows=5`.

3. **Pull the most expensive listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=desc`, `rows=5`.

4. **Present the distribution** — Show: mean, median, min, max, standard deviation for price and miles. Identify the price bands (quartiles) and show where the user's vehicle would fall.

5. **Highlight outliers** — Flag any listings priced more than 2 standard deviations from the mean as potential data quality issues or unique units (salvage, high miles, rare trim).

## Workflow: Competitor Price Movement

Use this when a dealer asks "who dropped their price" or "who is undercutting me."

1. **Scan for recent price drops** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=75`, `price_change=negative`, `sort_by=price`, `sort_order=asc`, `rows=20`.

2. **Scan for recent price raises** — Call `mcp__marketcheck__search_active_cars` with the same filters but `price_change=positive`, `rows=10`.

3. **Identify aggressive competitors** — From the price-drop results, group by dealer and count the number of drops. Dealers with multiple recent drops are signaling inventory pressure.

4. **Calculate competitive exposure** — For each dropped listing, compare the new price to the user's asking price on similar units. Flag any that now undercut the user.

5. **Recommend response** — For each unit where the user is now being undercut, suggest whether to match, split the difference, or hold based on the user's DOM and the competitor's DOM.

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Price-to-Market Ratio | Subject price / median market price (e.g., 1.04 = 4% above market) | Ratios above 1.10 correlate with 2x longer DOM; ratios below 0.95 leave $500-$1,500 on the table |
| Competitive Position Percentile | Rank among all competing units (e.g., 35th percentile = cheaper than 65% of market) | Positions in the 40th-60th percentile sell fastest with balanced margin |
| Competing Unit Count | Total active listings matching YMMT within radius | Markets with fewer than 10 comps support higher pricing; 30+ comps demand sharp pricing |
| Price Change Velocity | Number and magnitude of competitor price changes in the last 7-14 days | Rising velocity (many drops) signals a softening market; stable signals holding power |
| DOM vs Price Delta | Scatter of days-on-market against price-to-market ratio across the competitive set | Validates whether the market is truly price-sensitive or if other factors (photos, dealer reputation) dominate |

## Action-to-Outcome Funnel

1. **Overpriced by 5%+ with DOM > 30** — Recommend a price reduction to the 50th percentile. Expected outcome: 40-60% faster turn based on comparable sold data. Cite specific competing units priced lower that are still available (they got there first).

2. **Underpriced by 5%+ with DOM < 15** — Recommend a price increase to the 60th-70th percentile. Expected outcome: $800-$2,000 additional front-end gross without materially extending DOM. Reference the predicted market price as the ceiling.

3. **At Market but DOM > 45** — Price is not the issue. Recommend the dealer review photos, vehicle description, and online merchandising. Provide the competing units with lowest DOM for comparison.

4. **Competitor just dropped below your price** — Quantify the gap. If the gap is under $300, recommend holding (buyers rarely switch for small deltas). If the gap is $500+, recommend matching or adding value (e.g., certified warranty, included service).

5. **New listing entering a thin market (< 10 comps)** — Recommend pricing at the 55th-65th percentile to maximize margin in a low-supply environment. Monitor weekly for new entrants.

## Output Format

Always present results in this structure:

**Vehicle Summary** — Year, Make, Model, Trim, Mileage, VIN (masked last 4 if sensitive)

**Price Position Report**
- Your Price / Predicted Market Price: `$28,500 / $27,800`
- Price-to-Market Ratio: `1.025 (2.5% above market)`
- Percentile Rank: `62nd (higher than 62% of competing units)`
- Competing Units in Market: `23 within 50 miles`

**Competitive Set** — Table with columns: Dealer Name | Price | Miles | DOM | Distance | Price Change

**Recommendation** — One clear action sentence with expected business impact.

**Supporting Data** — Price distribution stats (mean, median, min, max) and any notable market signals (price drops, supply changes).
