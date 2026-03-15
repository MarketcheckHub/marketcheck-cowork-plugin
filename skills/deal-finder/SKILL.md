---
name: deal-finder
description: >
  This skill should be used when the user asks to "find me the best deal",
  "cheapest option near me", "best price on a", "deal finder",
  "is this a good price", "should I buy now or wait", "compare deals",
  "negotiate this price", "find a car for my customer", or needs help with
  sourcing the best-priced vehicle for a buyer, validating whether a deal
  is fair, or building negotiation leverage with market data.
version: 0.1.0
---

# Deal Finder — Source the Best Price, Validate the Deal, Arm the Negotiation

## Dealer Profile (Load First — Optional)

Before running any workflow, check for a saved dealer profile:

1. Read the `marketcheck-profile.md` project memory file
2. If the file **exists**, it provides useful defaults. However, deal-finder is often used by brokers sourcing for a customer whose location differs from the dealer's:
   - If the user is a **dealer sourcing for their own lot**: use `location.zip` and `preferences.default_radius_miles` from profile
   - If the user is a **broker acting for a customer**: ask for the customer's ZIP code (do not use dealer profile ZIP)
3. **Tool routing by country:**
   - **US**: All tools — `search_active_cars`, `predict_price_with_comparables`, `decode_vin_neovin`, `get_car_history`, `get_sold_summary`
   - **UK**: `search_uk_active_cars`, `search_uk_recent_cars` only. Fair Price Validation uses comp median instead of ML prediction. Market Timing Advice is **US-only** (requires sold summary).
4. If profile exists and applicable, confirm: "Using profile: **[dealer.name]**, [ZIP]"

## User Context

The primary user is an **auto broker or buying service agent** who is sourcing vehicles on behalf of clients and needs to find the best-priced unit, prove the deal is fair, and negotiate from a position of data-backed strength. The secondary user is a **fleet buyer or purchasing manager** acquiring vehicles at scale who needs to identify the lowest-cost options across a market.

The following fields may be loaded from the dealer profile, but always confirm the customer's location:

| Required | Field | Source |
|----------|-------|--------|
| Yes | Year, Make, Model (minimum) | Always ask |
| Yes | Customer's ZIP code | Ask (may differ from dealer profile) |
| Recommended | Trim preference | Always ask |
| Recommended | Maximum budget | Always ask |
| Auto/Ask | Search radius | Dealer profile or `100` miles default |
| Optional | Mileage preference (new vs used) | Always ask |
| Optional | Color preference | Always ask |
| Optional | Specific VIN under consideration | Always ask |
| Optional | Finance vs lease preference | Always ask |

Always confirm whether the search is for new or used inventory — this changes the search parameters and the applicable comparables.

## Workflow: Best Deal Search

Use this when a broker says "find me the cheapest 2024 RAV4 XLE near Phoenix" or a customer asks "what's the best deal."

1. **Search for the lowest-priced matching units** — Call `mcp__marketcheck__search_active_cars` with `year=2024`, `make=Toyota`, `model=RAV4`, `trim=XLE Premium`, `zip=85281`, `radius=100`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used` (or `car_type=new` if specified). This returns the 10 cheapest matching vehicles in the market.

2. **Enrich with market context** — Call `mcp__marketcheck__search_active_cars` with the same YMMT and location filters but `stats=price,miles`, `rows=0` to get the market-level statistics (mean, median, min, max, count) without fetching individual listings again.

3. **Score each result** — For each of the 10 listings, calculate:
   - Price vs market median (percent below/above)
   - Miles vs market median (higher miles = less desirable, adjust value)
   - DOM (longer DOM = more negotiation leverage)
   - Distance from customer (closer = less friction)

4. **Rank and present** — Re-rank the 10 listings by a composite score that balances price, miles, DOM, and distance. Present the top 3-5 as recommended options.

5. **Deliver the deal sheet** — For each recommended unit, show: dealer name, price, miles, DOM, distance, price-vs-market percentage, and a one-line assessment (e.g., "Best overall value — 6% below market, average miles, 42 DOM").

## Workflow: Fair Price Validation

Use this when a broker or customer has found a specific vehicle and asks "is this a good price" or "should I buy this one."

1. **Predict the market value** — Call `mcp__marketcheck__predict_price_with_comparables` with the candidate `vin`, `miles` (listed odometer), `zip` (customer's market), `dealer_type` (match the selling dealer type). Record the predicted price.

2. **Compare asking price to predicted value** — Calculate the delta:
   - **Below market**: Asking price is lower than predicted — this is a favorable deal.
   - **At market**: Within +/- 3% of predicted — fair deal, standard pricing.
   - **Above market**: Asking price exceeds predicted by more than 3% — the buyer is overpaying unless there are justifying factors (low miles, rare color, certified warranty).

3. **Pull competing alternatives** — Call `mcp__marketcheck__search_active_cars` with the same YMMT, `zip`, `radius=100`, `sort_by=price`, `sort_order=asc`, `rows=5`, `car_type=used`. Show the buyer what else is available — if cheaper options exist, cite them.

4. **Deliver the verdict** — Present a clear buy/negotiate/pass recommendation:
   - **Buy**: Price is 5%+ below market with acceptable miles and condition.
   - **Negotiate**: Price is at or slightly above market — there is room to negotiate down, especially if DOM is high.
   - **Pass**: Price is 5%+ above market and comparable alternatives exist at lower prices within reasonable distance.

## Workflow: Negotiation Leverage Report

Use this when a broker is preparing to negotiate on a specific VIN and needs data to strengthen their position.

1. **Pull listing history for the VIN** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=desc`. Check how long this specific unit has been listed and whether the price has already been reduced.

2. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to confirm exact specs and identify any features that could justify a premium or that the listing may have wrong.

3. **Get predicted market value** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`. This establishes the data-backed "fair" price.

4. **Find competing units** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=100`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used`. These are the alternatives the broker can cite during negotiation ("I can get a comparable unit at Dealer X for $1,200 less").

5. **Build the leverage brief** — Present:
   - **DOM leverage**: If the unit has been listed 30+ days, the dealer is motivated. 60+ days = highly motivated.
   - **Price drop history**: If the dealer already dropped the price, they may drop again. If they haven't dropped in 30+ days, a first offer below asking may trigger a counter.
   - **Competing unit citations**: List 3-5 specific competing vehicles with dealer name and price that the broker can reference by name in the negotiation.
   - **Suggested offer price**: Predicted market value minus a negotiation margin (typically 3-5% below predicted for used, 2-3% for new). Adjust upward if the unit is priced below market or has very low DOM.

## Workflow: Finance/Lease Comparison

Use this when a customer asks "what would my payment be" or a broker needs to compare financing across dealers.

1. **Search with finance data** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=100`, `include_finance=true`, `sort_by=price`, `sort_order=asc`, `rows=15`, `car_type=new` (finance/lease data is most common on new inventory).

2. **Search with lease data** — Call `mcp__marketcheck__search_active_cars` with the same filters but `include_lease=true`, `rows=15`.

3. **Build the comparison table** — For each listing that includes finance or lease data, extract: dealer, selling price, monthly payment, term, APR (finance) or money factor (lease), down payment, and residual (lease).

4. **Calculate total cost of ownership** — For each option, compute: total payments over term + down payment = total out-of-pocket. This allows apples-to-apples comparison even when terms differ.

5. **Present the comparison** — Show a table sorted by lowest monthly payment and a separate sort by lowest total cost. Highlight the best overall deal and note any unusually favorable terms (e.g., manufacturer subvented rates, lease loyalty bonuses).

## Workflow: Market Timing Advice

Use this when a customer asks "should I buy now or wait" or a broker needs to advise on timing.

1. **Assess current supply** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=150`, `stats=price,miles`, `rows=0`, `car_type=used`. The total count indicates supply depth. The price stats show current market conditions.

2. **Assess recent demand and sell-through** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `date_from` (30 days ago), `date_to` (today), `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`. This shows how many units sold recently — a proxy for demand velocity.

3. **Compare supply to demand** — Calculate the supply-to-demand ratio:
   - Active listings (supply) / Units sold in last 30 days (demand) = months of supply
   - Under 30 days of supply = seller's market (prices rising, buy now)
   - 30-60 days of supply = balanced market (prices stable, reasonable to wait for the right unit)
   - Over 60 days of supply = buyer's market (prices softening, negotiate aggressively or wait for further drops)

4. **Check for price trend direction** — From the stats in step 1, note the mean and median prices. Call `mcp__marketcheck__search_active_cars` with `price_change=negative`, same YMMT and location, `rows=0` to count how many dealers are dropping prices. A high percentage of the market dropping prices confirms a softening trend.

5. **Deliver the timing recommendation**:
   - **Buy now**: Supply is low, demand is high, prices are rising or stable. Waiting risks paying more or missing available units.
   - **Buy soon (within 2-4 weeks)**: Market is balanced. The customer can afford to be selective but should not wait indefinitely.
   - **Wait**: Supply is high, prices are trending down, many dealers are reducing prices. Recommend checking back in 2-4 weeks for better options.

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Price vs Market Average (%) | (Asking price - market median) / market median | Deals more than 5% below market are strong buys; above 5% are overpriced |
| DOM of Found Units | Days on market for each recommended unit | Units with 45+ DOM have the most negotiation room; under 15 DOM sell fast, act quickly |
| Options Within Radius | Total matching active listings in the search area | Fewer than 5 = limited selection, may need to expand radius or relax specs; 20+ = strong buyer's market |
| Finance Payment Range | Lowest to highest monthly payment across matching dealers | Shows the customer the payment spread and which dealer offers the best terms |
| Supply Trend Direction | Active inventory count trend (current vs 30 days ago) and price change activity | Rising supply + falling prices = wait; falling supply + stable prices = buy now |

## Action-to-Outcome Funnel

1. **Customer wants the cheapest option, no preference on dealer** — Run the Best Deal Search workflow. Present the top 3 options sorted by composite score. The broker can contact the selling dealer directly with a specific stock number and negotiate from the listed price.

2. **Customer found a specific listing online and wants validation** — Run the Fair Price Validation workflow. If the price is at or below market, confirm it is a fair deal and recommend proceeding. If above market, show the competing alternatives and recommend negotiating down to predicted value.

3. **Broker preparing for a dealer visit or phone negotiation** — Run the Negotiation Leverage Report. Arm the broker with DOM data, price history, predicted value, and 3-5 competing units to cite. A broker who walks in with specific competing stock numbers and market data commands significantly more negotiating power.

4. **Customer is undecided between buying and leasing** — Run the Finance/Lease Comparison workflow. Show total cost of ownership for both paths. In most cases, buying is cheaper long-term, but leasing offers lower monthly payments and flexibility. Let the data drive the recommendation.

5. **Customer has no urgency and asks "is now a good time to buy?"** — Run the Market Timing Advice workflow. If the market favors buyers (high supply, falling prices), recommend acting within 2-4 weeks while selection is strong. If the market favors sellers, recommend buying now before prices climb further or supply tightens.

## Output Format

Always present results in this structure:

**Search Criteria** — Year, Make, Model, Trim, ZIP, Radius, Budget, New/Used

**Top Deals** — Table with columns: Rank | Dealer | Location | Price | Miles | DOM | Distance | vs Market (%)

Example:
| Rank | Dealer | Location | Price | Miles | DOM | Distance | vs Market |
|------|--------|----------|-------|-------|-----|----------|-----------|
| 1 | Camelback Toyota | Phoenix, AZ | $33,200 | 18,400 | 52 days | 8 mi | -6.2% |
| 2 | AutoNation Toyota Tempe | Tempe, AZ | $33,800 | 22,100 | 38 days | 12 mi | -4.5% |
| 3 | Larry H. Miller Toyota | Mesa, AZ | $34,100 | 15,600 | 21 days | 18 mi | -3.7% |

**Market Context**
- Total matching units in market: `47`
- Market median price: `$35,400`
- Market price range: `$31,200 — $41,800`
- Supply trend: `Stable (similar count vs 30 days ago)`

**Recommendation** — One clear action sentence: which unit to pursue, what price to target, and why.

**Negotiation Notes** — If applicable, specific leverage points for the recommended unit (DOM, price drops, competing alternatives).
