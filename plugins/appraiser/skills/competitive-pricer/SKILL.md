---
name: competitive-pricer
description: >
  This skill should be used when the user asks to "price this car",
  "market price for this", "compare pricing", "price check VIN",
  "what's the market on this", or needs help with market pricing context,
  price positioning analysis, or understanding where a vehicle falls
  in the current competitive landscape for appraisal purposes.
version: 0.1.0
---

# Competitive Pricer — Market Price Context for Appraisals

## Appraiser Profile (Load First)

Before running any workflow, check for a saved appraiser profile:

1. Read `~/.claude/marketcheck/appraiser-profile.json`.
2. If the file **does not exist**: Tell the user: "No appraiser profile found. Run `/onboarding` to set up your appraiser context once." Then ask for the minimum required fields (ZIP, radius) to proceed with this one request.
3. If the file **exists**, extract and use silently (do not ask the user for these):
   - `zip` or `postcode` ← `location.zip` (US) or `location.postcode` (UK)
   - `state` or `region` ← `location.state` (US) or `location.region` (UK)
   - `specialization` ← `appraiser.specialization`
   - `radius` ← `preferences.default_radius_miles`
   - `country` ← `location.country`
   - `min_comp_count` ← `appraiser.min_comp_count`
4. **Tool routing by country:**
   - **US**: Use `mcp__marketcheck__search_active_cars`, `mcp__marketcheck__decode_vin_neovin`, `mcp__marketcheck__predict_price_with_comparables`, `mcp__marketcheck__get_car_history`
   - **UK**: Use `mcp__marketcheck__search_uk_active_cars` for listing searches, `mcp__marketcheck__search_uk_recent_cars` for sold/recent data. VIN decode and ML price prediction are **not available** for UK — skip decode steps (ask user for Year/Make/Model/Trim) and use comp median price instead of predicted price.
5. Confirm briefly: "Using appraiser profile: **[user.name]**, [ZIP/Postcode], [Country]"
6. **Dual pricing setup:** For all pricing workflows, the skill reports BOTH franchise and independent market prices, providing the appraiser with complete market context to select the appropriate benchmark.

## CPO Detection

When pricing a vehicle, determine if it is Certified Pre-Owned (CPO):

1. **From user input:** If the user states the vehicle is certified or CPO.
2. **From listing data:** If the vehicle listing includes `is_certified=true`.
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
```

When a vehicle is NOT CPO, skip the CPO-specific calls and price normally.

## User Context

The primary user is an **appraiser** (independent appraiser, insurance adjuster, or fleet valuation analyst) who needs market price context to support a defensible valuation. This skill provides the competitive landscape — what similar vehicles are listed at, what they have sold for, and where a subject vehicle falls in the distribution.

The following fields are loaded from the appraiser profile. Only ask if no profile exists:

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or Year/Make/Model/Trim | Always ask (vehicle-specific) |
| Auto | ZIP code (market center) | Appraiser profile `location.zip` / `location.postcode` |
| Auto | Search radius in miles | Appraiser profile `preferences.default_radius_miles` |
| Recommended | Mileage of the subject vehicle | Always ask (vehicle-specific) |
| Optional | Target price or current asking price | Always ask if relevant |

If the user provides a VIN, always start with a decode to confirm specs before pricing (US only — UK users provide specs manually).

## Workflow: Price-Check a Single VIN

Use this when the user says "price check this VIN" or "what's the market on this one."

1. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to confirm year, make, model, trim, body type, drivetrain, engine, and transmission. Present the decoded specs to the user for confirmation.

2. **Get predicted market prices (dual)** — Make TWO calls to `mcp__marketcheck__predict_price_with_comparables`:
   - **Franchise (retail):** with `vin`, `miles`, `zip`, `dealer_type=franchise`. This represents full retail market value.
   - **Independent (wholesale-proxy):** with the same parameters but `dealer_type=independent`. This provides wholesale-oriented context.
   Record both predicted prices and their comparable VINs.

2a. **CPO pricing (if applicable)** — If the vehicle is CPO (detected per CPO Detection section above), make additional calls with `is_certified=true` for both franchise and independent predictions. Report CPO market price separately from non-CPO market price, and show the CPO premium.

3. **Pull competing active listings** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from step 1), `zip`, `radius=75`, `sort_by=price`, `sort_order=asc`, `rows=15`, `car_type=used`. This returns the competitive set across all dealer types.

4. **Calculate price position** — If the user provided a subject price or asking price, compare it against the competitive set:
   - Percentile rank (e.g., "The subject price is lower than 72% of competing units")
   - Distance to the cheapest and most expensive unit
   - Median and mean market price
   - Number of competing units within +/- 5% of the subject price

5. **Deliver the market context** — Present both market prices for the appraiser to select the appropriate benchmark:
```
Franchise (Retail) Market Price:    $XX,XXX  (based on N comps)
Independent (Wholesale) Market Price:  $XX,XXX  (based on N comps)
Spread:                             $X,XXX   (X.X%)
Active Comps in Market:             N within [radius] miles
```

## Workflow: Trade-In VIN Price History

Use this when the appraiser asks "what's the history on this VIN" or needs listing trajectory context before finalizing a valuation.

1. **Pull listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=desc` to get the full timeline of listings across dealers.

2. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to get full specs for accurate pricing.

3. **Get predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.

4. **Analyze the trajectory** — From the history, extract:
   - Number of dealers that have listed this VIN
   - Price at each listing and the direction of change
   - Total days on market across all listings
   - Whether the vehicle was ever listed as certified

5. **Deliver price history context** — Show the price trajectory, current market value, and flag any red flags (e.g., multiple dealer hops in a short period, steep price drops suggesting a problem unit). This context is critical for the appraiser's confidence assessment.

## Workflow: Market Price Distribution

Use this when the appraiser asks "what's the market look like for this model" or wants a statistical overview to anchor a valuation.

1. **Pull market stats** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=100`, `car_type=used`, `stats=price,miles`, `rows=0`. The `rows=0` returns only stats without individual listings.

2. **Pull the cheapest listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=asc`, `rows=5`.

3. **Pull the most expensive listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=desc`, `rows=5`.

4. **Present the distribution** — Show: mean, median, min, max, standard deviation for price and miles. Identify the price bands (quartiles) and show where the subject vehicle would fall. This statistical context supports the appraiser's valuation methodology.

5. **Highlight outliers** — Flag any listings priced more than 2 standard deviations from the mean as potential data quality issues or unique units (salvage, high miles, rare trim).

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Price-to-Market Ratio | Subject price / median market price (e.g., 1.04 = 4% above market) | Ratios above 1.10 or below 0.90 warrant closer comparable analysis |
| Competitive Position Percentile | Rank among all competing units (e.g., 35th percentile = cheaper than 65% of market) | Provides the appraiser with statistical positioning for defensible reports |
| Competing Unit Count | Total active listings matching YMMT within radius | Markets with fewer than min_comp_count comps lower valuation confidence; 30+ comps support strong confidence |
| Franchise-Independent Spread | Dollar and percentage gap between franchise and independent market prices | Typical spread is 15-22%; this anchors the retail-to-wholesale range for appraisal purposes |
| DOM vs Price Delta | Scatter of days-on-market against price-to-market ratio across the competitive set | Validates whether the market is truly price-sensitive or if other factors dominate |

## Action-to-Outcome Funnel

1. **Insurance claim valuation** — Use the Single VIN price check with dual pricing. The franchise (retail) price is the appropriate benchmark for replacement value claims. Cite specific comparables for the adjuster's report.

2. **Trade-in appraisal** — Use the Single VIN price check. The independent (wholesale-proxy) price anchors the trade-in range. Show the spread to demonstrate the wholesale-to-retail gap.

3. **Estate or legal valuation** — Use the Market Price Distribution workflow to establish fair market value (the midpoint between franchise and independent). The statistical distribution provides defensible methodology for legal proceedings.

4. **Fleet revaluation** — Use the Market Price Distribution workflow for each model in the fleet. The median price and comparable count provide the basis for portfolio-level mark-to-market adjustments.

5. **Pre-purchase inspection pricing** — Use the Single VIN price check to validate whether a seller's asking price aligns with market reality. Flag any vehicle priced 10%+ above market as requiring negotiation leverage data.

## Output Format

Always present results in this structure:

**Vehicle Summary** — Year, Make, Model, Trim, Mileage, VIN (masked last 4 if sensitive)

**Market Price Report**
- Franchise (Retail) Market Price: `$28,500` (based on N comps)
- Independent (Wholesale) Market Price: `$24,200` (based on N comps)
- Franchise-Independent Spread: `$4,300 (17.8%)`
- Active Comps in Market: `23 within 75 miles`

**Competitive Set** — Table with columns: Dealer Name | Price | Miles | DOM | Distance | Dealer Type

**Methodology Notes** — How the market prices were derived, comparable count, and confidence level.

**Supporting Data** — Price distribution stats (mean, median, min, max) and any notable market signals.
