---
name: vehicle-appraiser
description: >
  This skill should be used when the user asks to "appraise this vehicle",
  "what's it worth", "insurance valuation", "comparable analysis",
  "fair market value", "pre-loss value", "appraisal report",
  "settlement valuation", "vehicle valuation", "claims appraisal",
  or needs help with building a defensible, comparable-backed vehicle
  valuation for insurance claims, total-loss determinations, or
  settlement pricing decisions.
version: 0.1.0
---

# Insurance Valuation — Comparable-Backed Valuations With Transaction Evidence

## Insurer Profile (Load First)

Before running any workflow, check for a saved insurer profile:

1. Read `~/.claude/marketcheck/insurer-profile.json`.
2. If the file **exists**, use the following silently as defaults (do not ask):
   - `zip` ← `location.zip` — use as default appraisal market
   - `state` ← `location.state`
   - `radius` ← `preferences.default_radius_miles`
   - `total_loss_threshold_pct` ← `insurer.total_loss_threshold_pct`
   - `default_comp_radius` ← `insurer.default_comp_radius`
3. If the file **does not exist**, ask for ZIP and radius — this skill works fine without a profile. Suggest running `/onboarding` first.
4. **Country check:** US-only. All tools — `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`, `search_past_90_days`, `get_car_history` — require US data. If user indicates UK, inform: "Insurance valuation requires US data tools (ML pricing, sold analytics, VIN history). Not available for the UK market."
5. If profile exists, confirm briefly: "Using profile: **[user.name]**, [ZIP], [State]"

## CPO Detection & Valuation

When appraising a vehicle, determine if it is Certified Pre-Owned (CPO):

1. **From user input:** If the user states the vehicle is certified/CPO.
2. **From listing data:** If the vehicle's listing has `is_certified=true`.
3. **From VIN history:** If `get_car_history` shows the vehicle currently listed as certified.

When the vehicle IS CPO, the Full Comparable Appraisal workflow adds these steps:

- **CPO predicted value:** Call `predict_price_with_comparables` with `is_certified=true` to get the certified market value.
- **Non-CPO predicted value:** Call `predict_price_with_comparables` WITHOUT `is_certified` to get the standard market value.
- **CPO retail comps:** Call `search_active_cars` with the YMMT filters PLUS `is_certified=true` to find certified-only comparables.
- **CPO premium calculation:** CPO Premium = CPO Predicted Value - Non-CPO Predicted Value

In the Valuation Summary output, add:

| Measure | Value |
|---------|-------|
| CPO Predicted Retail Value | $XX,XXX |
| Non-CPO Predicted Retail Value | $XX,XXX |
| CPO Premium | +$X,XXX (+X.X%) |
| Active CPO Comps | N within radius |
| Active Non-CPO Comps | N within radius |

## User Context

The primary user is an **insurance adjuster**, **claims analyst**, or **total-loss specialist** who needs a defensible valuation backed by specific comparable vehicles and transaction data to support settlement offers and dispute resolution.

The following fields are loaded from the insurer profile if available. Otherwise, ask:

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or Year/Make/Model/Trim | Always ask (vehicle-specific) |
| Yes | Current odometer reading | Always ask (vehicle-specific) |
| Auto/Ask | ZIP code of appraisal market | Insurer profile `location.zip` or ask |
| Recommended | Pre-loss vehicle condition | Always ask (`Clean`, `Average`, `Rough`) |
| Recommended | Purpose of appraisal | Always ask (`Total-loss`, `Diminished value`, `Settlement`, `Pre-loss FMV`) |
| Optional | Certified pre-owned status | Always ask |
| Auto/Ask | Search radius | Insurer profile `insurer.default_comp_radius` or `100` default |

Always decode the VIN first to lock in exact specs. Appraisals built on assumed trim levels lose credibility in settlement disputes.

## Workflow: Full Comparable Appraisal

Use this for formal insurance valuations, total-loss claims, or any situation where the valuation must be supported by cited comparables for dispute resolution.

1. **Decode the VIN for exact specs** — Call `mcp__marketcheck__decode_vin_neovin` with `vin`. Confirm year, make, model, trim, body type, drivetrain, engine displacement, transmission, and key options. These specs define the comparable search criteria.

2. **Get the algorithmic market value** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles` (actual odometer), `zip`, `dealer_type=franchise` (for retail value), and `is_certified` if applicable. Record the predicted price and all returned comparable VINs with their prices and miles.

3. **Pull active retail comparables** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from step 1), `zip`, `radius=100`, `miles_range=<odometer-15000>-<odometer+15000>`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=20`. Use a wider 100-mile radius to ensure adequate comparable pool for defensible claims valuations.

4. **Pull sold/expired transaction evidence** — Call `mcp__marketcheck__search_past_90_days` with the same YMMT and location filters, plus `sold=true`. These are actual transactions that prove what buyers have recently paid. **Sold transaction data is the strongest evidence in any insurance settlement dispute.**

5. **Synthesize the valuation** — Combine all three data sources:
   - **Algorithmic predicted price** from step 2 (central estimate)
   - **Active comparable range** from step 3 (current retail context)
   - **Sold transaction range** from step 4 (transaction evidence)
   - Calculate a **recommended value range** (low / mid / high) using the overlap of all three.
   - Adjust for condition if the user provided it (rough = low end of range, clean = high end).

6. **Total-loss threshold calculation** — Using the condition-adjusted FMV:
   - **Repair cost threshold** = FMV x total_loss_threshold_pct (default 75%)
   - Present: "This vehicle is a total loss if repair costs exceed $XX,XXX (XX% of FMV)"
   - If estimated repair cost was provided, render the determination: TOTAL LOSS or NOT TOTAL LOSS

7. **Present the insurance valuation report** — Deliver a structured report with the valuation, every cited comparable (VIN, price, miles, dealer, distance), total-loss threshold, methodology notes, and confidence assessment.

## Workflow: Regional Price Variance

Use this when the user needs to understand how values differ across geographies, important for understanding settlement variation by region and ensuring fair market value reflects the claimant's local market.

1. **Pull price stats for the primary market** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip` (primary market), `radius=100`, `stats=price,miles`, `rows=0`, `car_type=used`.

2. **Pull price stats for comparison markets** — Repeat step 1 for each additional ZIP code the user wants to compare (e.g., `10001` for NYC, `90210` for LA, `77001` for Houston).

3. **Pull sold summary by state** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `summary_by=state`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`. This shows which states command the highest average sale prices.

4. **Calculate regional variance** — Build a comparison table: market, median price, mean price, sample size, and delta from the lowest market. Regional price variance directly impacts settlement values — the same vehicle may warrant a higher settlement in a premium market.

5. **Present the regional map** — Show the price variance table and highlight any market where the price delta exceeds 5%. Note: "Settlement offers should reflect the claimant's local market. Regional variance of X% supports adjusting the FMV for geographic factors."

## Workflow: Wholesale vs Retail Spread

Use this when understanding the gap between wholesale and retail values, critical for determining fair settlement amounts and salvage value estimates.

1. **Get franchise (retail) predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.

2. **Get independent (wholesale-proxy) predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=independent`.

3. **Pull franchise dealer listings** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=100`, `dealer_type=franchise`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used`.

4. **Pull independent dealer listings** — Call `mcp__marketcheck__search_active_cars` with the same filters but `dealer_type=independent`, `rows=10`.

5. **Calculate the spread** — Present:
   - Franchise median price vs Independent median price
   - Spread in dollars and percentage
   - Predicted retail value vs predicted wholesale-proxy value
   - Note: "The franchise retail value represents the replacement cost a claimant would face. Settlement offers should be anchored to the retail replacement cost, not wholesale."

## Workflow: Historical Value Trajectory

Use this when the user asks "what has this VIN been listed at over time" or needs to understand the pricing history of a specific unit for claims documentation.

1. **Pull the full listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=asc` to get chronological listing data across all dealers.

2. **Decode the VIN for baseline specs** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to anchor the timeline with exact vehicle specs.

3. **Build the trajectory** — From the history, extract each listing event: date, dealer, asking price, and DOM at that dealer. Calculate:
   - Total days on market across all listings
   - Total price depreciation from first listing to most recent
   - Average price drop per listing hop
   - Number of unique dealers

4. **Contextualize with current market** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip` to get today's predicted value. Compare to the trajectory endpoint.

5. **Present the timeline** — Show a chronological table of all listings with price, dealer, and DOM. Note any pre-loss listing history that establishes the vehicle's market value trajectory — useful for supporting or challenging settlement offers.

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Comparable Count Within Radius | Number of active + sold comps found within the search radius | Fewer than 5 comps = low confidence, flag for manual review; 15+ comps = high confidence valuation |
| Retail-to-Wholesale Spread | Dollar and percentage gap between franchise and independent predicted prices | Settlement should be anchored to retail replacement cost; spread above 25% suggests strong retail demand |
| Regional Price Variance | Standard deviation of median prices across compared markets | Variance above 8% signals the need for geographic adjustment in the settlement offer |
| Historical Depreciation Rate | Price decline per month from first listing to current value | Rates above 2% per month indicate rapid depreciation; factor into pre-loss FMV if date of loss predates appraisal |
| Valuation Confidence Score | Composite of comparable count, spread tightness, and data recency | Present as High / Medium / Low; refuse to give a point estimate on Low confidence — give a range instead |

## Action-to-Outcome Funnel

1. **High-confidence appraisal (15+ comps, tight spread)** — Deliver a point estimate with a narrow range (+/- 3%). The adjuster can present a defensible settlement. Cite the 3 closest comparables by VIN.

2. **Medium-confidence appraisal (5-14 comps, moderate spread)** — Deliver a range (low to high) with the midpoint as the recommended value. Note which data source (active, sold, predicted) most heavily influenced the range. Recommend factoring pre-loss condition carefully as it will determine where in the range the settlement falls.

3. **Low-confidence appraisal (< 5 comps)** — Do not give a point estimate. Deliver a wide range and explicitly state the confidence is low. Recommend broadening the radius to 150-200 miles, relaxing the trim filter, or consulting additional valuation sources.

4. **Total-loss determination** — Present the total-loss threshold prominently. If repair costs exceed the threshold, the determination is clear. If close to the threshold, present both options with financial impact of each (repair vs. total-loss settlement).

5. **Disputed settlement** — Use the Full Comparable Appraisal workflow with the widest defensible radius (150-200 miles). Emphasize sold transaction evidence over active listings. Present every comparable with full detail — adjusters and claimants need to see the work. Sold transactions are the most defensible evidence in any dispute.

## Output Format

Always present results in this structure:

**INSURANCE VALUATION**

**Vehicle Identification**
- VIN: `5YJ3E1EA8PF123456`
- Year / Make / Model / Trim: `2023 Tesla Model 3 Long Range`
- Body: Sedan | Drivetrain: AWD | Engine: Electric | Transmission: Single-Speed
- Odometer: 28,400 miles | Pre-Loss Condition: Average

**Valuation Summary**
| Measure | Value |
|---------|-------|
| Franchise Retail Value | $35,200 |
| Independent Retail Value | $32,800 |
| Condition-Adjusted FMV | $34,000 |
| Active Comp Range (25th-75th pctl) | $33,800 — $37,100 |
| Sold Transaction Range (90 days) | $32,500 — $36,400 |
| Confidence | High (18 active comps, 7 sold comps) |

**Total-Loss Threshold**
| Measure | Value |
|---------|-------|
| FMV | $34,000 |
| Threshold (75%) | $25,500 |
| Determination | PENDING REPAIR ESTIMATE |

**Settlement Range**
| Tier | Value | Basis |
|------|-------|-------|
| Low | $32,500 | 25th percentile sold transactions |
| Mid (recommended) | $34,000 | Condition-adjusted FMV |
| High | $36,400 | 75th percentile sold transactions |

**Active Retail Comparables** — Table with columns: VIN (last 6) | Year | Trim | Miles | Price | Dealer | Distance

**Sold Transaction Comparables** — Table with columns: VIN (last 6) | Year | Trim | Miles | Sold Price | Dealer | Sale Date

**Methodology Notes** — Brief explanation of how the three data sources were weighted and any condition adjustments applied. Note the total-loss threshold percentage used and its source (profile default or state regulation).

**Caveats** — Any factors that could not be accounted for (accident history, aftermarket modifications, regional demand anomalies, low comp count).
