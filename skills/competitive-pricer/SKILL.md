---
name: competitive-pricer
description: >
  Price positioning and competitive analysis. Triggers: "price this car",
  "am I priced right", "competitive pricing", "price check VIN",
  "who is undercutting me", "market price for this", "price my inventory",
  "compare my price", pricing strategy, price positioning,
  competitive price analysis, identifying pricing opportunities.
version: 0.1.0
---

# Competitive Pricer — Real-Time Price Positioning Against Your Market

## Dealer Profile (Load First)

→ Full procedure: read `_references/profile-loading.md`

Parse `marketcheck-profile.md` → extract: `dealer_id`, `dealer_type`, `franchise_brands`, `zip`/`postcode`, `state`/`region`, `country`, `radius`, `cpo_program`, `cpo_certification_cost`. If missing: tell user to run `/onboarding`.

**Country routing:** US = all tools. UK = `search_uk_active_cars` / `search_uk_recent_cars` only — no VIN decode, no ML prediction (ask user for YMMT, use comp median). → Full matrix: `_references/country-routing.md`

Confirm: "Using profile: **[dealer.name]**, [ZIP/Postcode], [Country]"

**Dual pricing:** Every pricing output shows BOTH franchise AND independent market prices. Dealer's `dealer_type` = PRIMARY; other type = SECONDARY context.

## CPO Detection

→ Full procedure: read `_references/cpo-detection.md`

If vehicle is CPO: make TWO `predict_price_with_comparables` calls (with and without `is_certified=true`). Show CPO premium as the difference. If NOT CPO: skip CPO calls, price normally.

## User Context

The primary user is a **dealer** (used car manager, pricing analyst, or GM) who needs to know whether their asking prices are competitive, where they stand relative to nearby sellers, and where margin is being left on the table or lost to aging inventory. The secondary user is an **appraiser** validating that a proposed retail price aligns with the competitive set.

The following fields are loaded from the dealer profile. Only ask if no profile exists:

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or Year/Make/Model/Trim | Always ask (vehicle-specific) |
| Auto | ZIP code (market center) | Dealer profile `location.zip` / `location.postcode` |
| Auto | Search radius in miles | Dealer profile `preferences.default_radius_miles` |
| Recommended | Mileage of the subject vehicle | Always ask (vehicle-specific) |
| Auto | Dealer type filter | Dealer profile `dealer.dealer_type` |
| Optional | Target price or current asking price | Always ask if relevant |

If the user provides a VIN, always start with a decode to confirm specs before pricing (US only — UK dealers provide specs manually).

## Gotchas

- **CPO requires dual API calls** — call `predict_price_with_comparables` once WITH `is_certified=true` and once WITHOUT to get both CPO and non-CPO market prices. Skipping the second call gives wrong CPO premium numbers.
- **UK has no VIN decode or ML prediction** — ask the user for Year/Make/Model/Trim directly and use comp median price instead of predicted price. Do not attempt `decode_vin_neovin` or `predict_price_with_comparables` for UK.
- **Always set `price_min=1`** (or filter out $0 results) on all `search_active_cars` calls — $0 listings are junk/placeholder data that will skew stats.
- **Dual pricing is always required** — every pricing output must show BOTH franchise and independent market prices regardless of the dealer's own type. The dealer's type determines the PRIMARY comparison; the other type is SECONDARY context.
- **`rows=0` with `stats=price`** returns only aggregate statistics without individual listings — use this for distribution workflows to avoid pulling unnecessary data.

## Workflow: Price-Check a Single VIN

Use this when a dealer says "price check this VIN" or "am I priced right on this one."

1. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to confirm year, make, model, trim, body type, drivetrain, engine, and transmission. Present the decoded specs to the user for confirmation.

2. **Get predicted market prices (dual)** — Make TWO calls to `mcp__marketcheck__predict_price_with_comparables`:
   - **Primary:** with `vin`, `miles`, `zip`, `dealer_type` matching the source dealer's type (from profile). This is the primary comparison.
   - **Secondary:** with the same parameters but `dealer_type` set to the OTHER type (franchise<>independent). This provides market context.
   Record both predicted prices and their comparable VINs.

2a. **CPO pricing (if applicable)** — If the vehicle is CPO (detected per CPO Detection section above), make additional calls with `is_certified=true` for both franchise and independent predictions. Report CPO market price separately from non-CPO market price, and show the CPO premium.

3. **Pull competing active listings** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from step 1), `zip`, `radius=50`, `sort_by=price`, `sort_order=asc`, `rows=15`, `car_type=used`. This returns the competitive set. Additionally, call `mcp__marketcheck__search_active_cars` with the same parameters but add `dealer_type` matching the source dealer's type to get a filtered competitive set from SAME-type dealers only.

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
   - Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type` (Primary — matching source dealer's type).
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

## KPIs & Business Impact

→ After assembling results, read `references/outcomes.md` to frame recommendations with quantified business impact, KPI benchmarks, and action-to-outcome guidance.

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

## Self-Check (before presenting to user)

- [ ] Both franchise AND independent market prices shown (dual pricing requirement)
- [ ] No $0 or null prices in any table
- [ ] Percentile rank calculated correctly (lower price = higher percentile of units priced above)
- [ ] Price-to-market ratio uses median, not mean
- [ ] Recommendation is one clear action sentence with expected business impact
- [ ] CPO premium shown separately if vehicle is certified
