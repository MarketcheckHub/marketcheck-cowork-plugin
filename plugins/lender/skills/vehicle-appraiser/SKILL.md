---
name: vehicle-appraiser
description: >
  This skill should be used when the user asks to "appraise this vehicle",
  "what's it worth", "collateral value", "comparable analysis",
  "fair market value", "wholesale vs retail", "collateral valuation report",
  "LTV calculation", "vehicle valuation", "loan collateral check",
  or needs help with building a defensible, comparable-backed vehicle valuation
  for collateral assessment, portfolio revaluation, or loan origination decisions.
version: 0.1.0
---

# Vehicle Appraiser — Collateral Valuation With Transaction Evidence

## Lender Profile (Load First — Optional)

Before running any workflow, check for a saved lender profile:

1. Read `~/.claude/marketcheck/lender-profile.json`
2. If the file **exists**, use the following silently as defaults (do not ask):
   - `zip` or `postcode` ← `location.zip` (US) or `location.postcode` (UK) — use as default valuation market
   - `radius` ← `preferences.default_radius_miles`
   - `country` ← `location.country`
   - `risk_ltv_threshold` ← `lender.risk_ltv_threshold`
   - `high_risk_ltv_threshold` ← `lender.high_risk_ltv_threshold`
   - `portfolio_focus` ← `lender.portfolio_focus`
3. If the file **does not exist**, ask for ZIP and radius as before — this skill works fine without a profile.
4. **Tool routing by country:**
   - **US**: All tools — `decode_vin_neovin`, `predict_price_with_comparables`, `search_active_cars`, `search_past_90_days`, `get_car_history`
   - **UK**: `search_uk_active_cars`, `search_uk_recent_cars` only. VIN decode, price prediction, and car history are **not available**. Use comp median for valuation, ask user for specs instead of VIN decode, and skip listing history steps.
5. If profile exists, confirm briefly: "Using profile ZIP **[ZIP/Postcode]** for collateral valuation."

## User Context

The primary user is a **lender** (residual value analyst, portfolio risk manager, or auto finance director) who needs a defensible collateral valuation backed by specific comparable vehicles and transaction data to support loan origination, portfolio revaluation, or loss mitigation decisions. The secondary user is a **floor plan auditor** who needs to verify collateral coverage on dealer inventory lines.

The following fields are loaded from the lender profile if available. Otherwise, ask:

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or Year/Make/Model/Trim | Always ask (vehicle-specific) |
| Yes | Current odometer reading | Always ask (vehicle-specific) |
| Auto/Ask | ZIP code of valuation market | Lender profile `location.zip` or ask |
| Recommended | Vehicle condition | Always ask (`Clean`, `Average`, `Rough`) |
| Recommended | Purpose of valuation | Always ask (`Loan Origination`, `Portfolio Revalue`, `Loss Mitigation`, `Floor Plan Audit`) |
| Optional | Loan amount (for LTV calculation) | Always ask |
| Auto/Ask | Search radius | Lender profile `preferences.default_radius_miles` or `100` default |

Always decode the VIN first to lock in exact specs (US only). Valuations built on assumed trim levels lose credibility in audits.

## Workflow: Full Collateral Valuation

Use this for loan origination, portfolio revaluation, or any situation where the valuation must be supported by cited comparables.

1. **Decode the VIN for exact specs** — Call `mcp__marketcheck__decode_vin_neovin` with `vin`. Confirm year, make, model, trim, body type, drivetrain, engine displacement, transmission, and key options. These specs define the comparable search criteria.

2. **Get the algorithmic market value** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles` (actual odometer), `zip`, `dealer_type=franchise` (for retail value). Record the predicted price and all returned comparable VINs with their prices and miles.

3. **Pull active retail comparables** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from step 1), `zip`, `radius=75`, `miles_range=<odometer-15000>-<odometer+15000>`, `car_type=used`, `sort_by=price`, `sort_order=asc`, `rows=20`. These are currently available competing units that establish the retail market.

4. **Pull sold/expired transaction evidence** — Call `mcp__marketcheck__search_past_90_days` with the same YMMT and location filters, plus `sold=true`. These are actual transactions that prove what buyers have recently paid. This is the strongest evidence in any collateral valuation.

5. **Synthesize the collateral valuation** — Combine all three data sources:
   - **Algorithmic predicted price** from step 2 (central estimate)
   - **Active comparable range** from step 3 (current retail context)
   - **Sold transaction range** from step 4 (transaction evidence)
   - Calculate a **collateral value range** (low / mid / high) using the overlap of all three.
   - Adjust for condition if the user provided it (rough = low end of range, clean = high end).

6. **Calculate LTV if loan amount provided** — If the user provided a loan amount:
   - **LTV** = loan amount / collateral midpoint value x 100
   - Flag: LTV > risk_ltv_threshold (default 100%) = "UNDERWATER — collateral does not cover loan balance"
   - Flag: LTV > high_risk_ltv_threshold (default 120%) = "HIGH RISK — significant negative equity"
   - Project: At the current segment depreciation rate, when will LTV reach 100% and 120%?

7. **Present the collateral valuation report** — Deliver a structured report with the valuation, every cited comparable (VIN, price, miles, dealer, distance), methodology notes, LTV analysis, and confidence assessment.

## Workflow: Quick Collateral Check

Use this when speed matters — a loan officer needs a collateral value for a quick origination decision.

1. **Get predicted value immediately** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`. This returns the market value and top comparables in a single call.

2. **Pull a tight comparable set** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim`, `zip`, `radius=50`, `sort_by=price`, `sort_order=asc`, `rows=5`, `car_type=used`. These are the top 5 closest-priced competing units.

3. **Deliver the quick collateral value** — Present:
   - **Predicted retail value**: from step 1
   - **Estimated wholesale value**: predicted retail minus a typical retail-to-wholesale spread (usually 15-22% below retail, adjusted by vehicle age and demand)
   - **LTV calculation**: if loan amount provided, calculate LTV against both retail and wholesale values
   - **Top 5 retail comps**: brief table showing the market context
   - **Confidence note**: indicate whether the comparable count supports a high-confidence or low-confidence estimate
   - **Risk flag**: if LTV exceeds threshold, prominently flag the risk level

## Workflow: Regional Collateral Variance

Use this when the lender needs to understand how collateral values differ across geographies, common for multi-state portfolio management or understanding regional LTV exposure.

1. **Pull price stats for the primary market** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip` (primary market), `radius=100`, `stats=price,miles`, `rows=0`, `car_type=used`.

2. **Pull price stats for comparison markets** — Repeat step 1 for each additional ZIP code the user wants to compare (e.g., `10001` for NYC, `90210` for LA, `77001` for Houston).

3. **Pull sold summary by state** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `summary_by=state`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `top_n=10`. This shows which states command the highest average sale prices.

4. **Calculate regional variance and LTV impact** — Build a comparison table: market, median price, mean price, sample size, and delta from the lowest market. For each region, calculate what the LTV would be on a standard loan amount. Identify regions where the same loan would be underwater vs. adequately covered.

5. **Present the regional collateral map** — Show the price variance table and highlight any market where the price delta exceeds 5% — these represent regions where collateral value assumptions need adjustment. Include LTV impact per region.

## Workflow: Wholesale vs Retail Spread

Use this when the lender needs to understand the gap between wholesale and retail values, critical for loss mitigation and recovery estimates.

1. **Get franchise (retail) predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=franchise`.

2. **Get independent (wholesale-proxy) predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type=independent`.

3. **Pull franchise dealer listings** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=75`, `dealer_type=franchise`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used`.

4. **Pull independent dealer listings** — Call `mcp__marketcheck__search_active_cars` with the same filters but `dealer_type=independent`, `rows=10`.

5. **Calculate the spread and recovery implications** — Present:
   - Franchise median price vs Independent median price
   - Spread in dollars and percentage
   - Predicted retail value vs predicted wholesale-proxy value
   - **Recovery estimate**: In a repo/liquidation scenario, expect to recover the wholesale value minus remarketing costs (typically $1,500-2,500)
   - **Deficiency exposure**: If loan balance exceeds wholesale recovery, calculate the expected deficiency

## Workflow: Historical Value Trajectory

Use this when the user asks "what has this VIN been listed at over time" or needs to understand depreciation patterns for a specific collateral unit.

1. **Pull the full listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=asc` to get chronological listing data across all dealers.

2. **Decode the VIN for baseline specs** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to anchor the timeline with exact vehicle specs.

3. **Build the trajectory** — From the history, extract each listing event: date, dealer, asking price, and DOM at that dealer. Calculate:
   - Total days on market across all listings
   - Total price depreciation from first listing to most recent
   - Average price drop per listing hop
   - Number of unique dealers

4. **Contextualize with current market** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip` to get today's predicted value. Compare to the trajectory endpoint.

5. **Present the timeline with collateral implications** — Show a chronological table of all listings with price, dealer, and DOM. Highlight any unusual patterns (rapid dealer hops suggesting distressed sale, price increases between dealers suggesting reconditioning, or steep drops suggesting undisclosed issues). Flag: "Vehicles with extended market exposure (>90 days total DOM) or multiple dealer hops typically command lower values — apply a 3-5% haircut to collateral value."

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Comparable Count Within Radius | Number of active + sold comps found within the search radius | Fewer than 5 comps = low confidence, flag for manual review; 15+ comps = high confidence valuation |
| Retail-to-Wholesale Spread | Dollar and percentage gap between franchise and independent predicted prices | Critical for recovery estimation; typical spread is 15-22%; spreads above 25% suggest strong retail demand and better recovery potential |
| LTV at Origination | Loan amount / collateral value x 100 | LTV > 100% at origination = negative equity from day one; require additional down payment or GAP coverage |
| Regional Collateral Variance | Standard deviation of median prices across compared markets | Variance above 8% signals need for state-level collateral adjustments rather than national book values |
| Historical Depreciation Rate | Price decline per month from first listing to current value | Rates above 2% per month indicate rapid depreciation; increase LTV monitoring frequency for loans on these vehicles |
| Valuation Confidence Score | Composite of comparable count, spread tightness, and data recency | Present as High / Medium / Low; refuse to give a point estimate on Low confidence — give a range instead and require manual review |

## Action-to-Outcome Funnel

1. **High-confidence valuation (15+ comps, tight spread)** — Deliver a point estimate with a narrow range (+/- 3%). Use as collateral value for LTV calculation with confidence. Cite the 3 closest comparables by VIN.

2. **Medium-confidence valuation (5-14 comps, moderate spread)** — Deliver a range (low to high) with the midpoint as the recommended collateral value. Use the conservative (low) end for LTV calculation. Recommend the lender order a physical inspection if the loan amount exceeds $25K.

3. **Low-confidence valuation (< 5 comps)** — Do not give a point estimate. Deliver a wide range and explicitly state the confidence is low. Recommend broadening the radius, using a third-party appraisal service, or requiring a physical inspection before origination.

4. **LTV exceeds threshold at origination** — Flag prominently. Recommend: require additional down payment to bring LTV below threshold, require GAP insurance, or decline the origination. Show the exact dollar amount needed to bring LTV within policy limits.

5. **Collateral in a declining segment** — If the vehicle's segment is depreciating faster than average, note: "This vehicle is in a segment experiencing accelerated depreciation (X.X%/month vs Y.Y% average). LTV will deteriorate faster than standard models — consider a shorter loan term or lower advance rate."

## Output Format

Always present results in this structure:

**Vehicle Identification**
- VIN: `5YJ3E1EA8PF123456`
- Year / Make / Model / Trim: `2023 Tesla Model 3 Long Range`
- Body: Sedan | Drivetrain: AWD | Engine: Electric | Transmission: Single-Speed
- Odometer: 28,400 miles

**Collateral Valuation Summary**
| Measure | Value |
|---------|-------|
| Predicted Retail Value | $35,200 |
| Predicted Wholesale Value | $28,900 |
| Active Comp Range (25th-75th pctl) | $33,800 — $37,100 |
| Sold Transaction Range (90 days) | $32,500 — $36,400 |
| Recommended Collateral Value (condition-adjusted) | $34,500 — $35,800 |
| Confidence | High (18 active comps, 7 sold comps) |

**LTV Analysis** (if loan amount provided)
| Measure | Value |
|---------|-------|
| Loan Amount | $XX,XXX |
| LTV (vs Retail) | XX.X% |
| LTV (vs Wholesale) | XX.X% |
| Risk Level | ACCEPTABLE / WARNING / HIGH RISK |
| Months to LTV 100% (at current depr. rate) | XX months |

**Active Retail Comparables** — Table with columns: VIN (last 6) | Year | Trim | Miles | Price | Dealer | Distance | DOM

**Sold Transaction Comparables** — Table with columns: VIN (last 6) | Year | Trim | Miles | Sold Price | Dealer | Sale Date

**Methodology Notes** — Brief explanation of how the three data sources were weighted and any condition adjustments applied.

**Risk Factors** — Any factors that could affect collateral value: accident history, aftermarket modifications, regional demand anomalies, segment depreciation trends, EV battery degradation considerations.
