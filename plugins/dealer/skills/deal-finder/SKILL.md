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

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Deal Finder — Source the Best Price, Validate the Deal, Arm the Negotiation

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip, radius, dealer_type, country. Note: deal-finder often sources for customers — if sourcing for a customer, ask for customer's ZIP (do not use profile ZIP). **US**: `search_active_cars`, `predict_price_with_comparables`, `decode_vin_neovin`, `get_car_history`, `get_sold_summary`. **UK**: `search_uk_active_cars`, `search_uk_recent_cars` only (Fair Price uses comp median; Market Timing is US-only). Confirm: "Using profile: [dealer.name], [ZIP]"

## User Context
Dealer sourcing vehicles for clients or validating deals; needs best price, fair-price proof, and negotiation leverage.

| Required | Field | Source |
|----------|-------|--------|
| Yes | Year/Make/Model, customer ZIP | Ask |
| Recommended | Trim, max budget | Ask |
| Auto/Ask | Radius | Profile or 100mi default |
| Optional | Mileage pref, color, specific VIN, finance/lease, new/used | Ask |

Always confirm new vs used — changes search params and comparables.

## Workflow: Best Deal Search

Use this when a dealer says "find me the cheapest 2024 RAV4 XLE near Phoenix" or a customer asks "what's the best deal."

1. **Search for the lowest-priced matching units** — Call `mcp__marketcheck__search_active_cars` with `year=2024`, `make=Toyota`, `model=RAV4`, `trim=XLE Premium`, `zip=85281`, `radius=100`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used` (or `car_type=new` if specified). This returns the 10 cheapest matching vehicles in the market.
   → **Extract only**: per listing — dealer_name, location, price, miles, dom, distance. Discard full response.

2. **Enrich with market context** — Call `mcp__marketcheck__search_active_cars` with the same YMMT and location filters but `stats=price,miles`, `rows=0` to get the market-level statistics (mean, median, min, max, count) without fetching individual listings again.
   → **Extract only**: mean, median, min, max, count for price and miles. Discard full response.

3. **Score each result** — For each of the 10 listings, calculate:
   - Price vs market median (percent below/above)
   - Miles vs market median (higher miles = less desirable, adjust value)
   - DOM (longer DOM = more negotiation leverage)
   - Distance from customer (closer = less friction)

4. **Rank and present** — Re-rank the 10 listings by a composite score that balances price, miles, DOM, and distance. Present the top 3-5 as recommended options.

5. **Deliver the deal sheet** — For each recommended unit, show: dealer name, price, miles, DOM, distance, price-vs-market percentage, and a one-line assessment (e.g., "Best overall value — 6% below market, average miles, 42 DOM").

## Workflow: Fair Price Validation

Use this when a dealer or customer has found a specific vehicle and asks "is this a good price" or "should I buy this one."

1. **Predict the market value** — Call `mcp__marketcheck__predict_price_with_comparables` with the candidate `vin`, `miles` (listed odometer), `zip` (customer's market), `dealer_type` (match the selling dealer type). Record the predicted price.
   → **Extract only**: predicted_price. Discard full response.

2. **Compare asking price to predicted value** — Calculate the delta:
   - **Below market**: Asking price is lower than predicted — this is a favorable deal.
   - **At market**: Within +/- 3% of predicted — fair deal, standard pricing.
   - **Above market**: Asking price exceeds predicted by more than 3% — the buyer is overpaying unless there are justifying factors (low miles, rare color, certified warranty).

3. **Pull competing alternatives** — Call `mcp__marketcheck__search_active_cars` with the same YMMT, `zip`, `radius=100`, `sort_by=price`, `sort_order=asc`, `rows=5`, `car_type=used`. Show the buyer what else is available — if cheaper options exist, cite them.
   → **Extract only**: per listing — dealer_name, price, miles, dom, distance. Discard full response.

4. **Deliver the verdict** — Present a clear buy/negotiate/pass recommendation:
   - **Buy**: Price is 5%+ below market with acceptable miles and condition.
   - **Negotiate**: Price is at or slightly above market — there is room to negotiate down, especially if DOM is high.
   - **Pass**: Price is 5%+ above market and comparable alternatives exist at lower prices within reasonable distance.

## Workflow: Negotiation Leverage Report

Use this when a dealer is preparing to negotiate on a specific VIN and needs data to strengthen their position.

1. **Pull listing history for the VIN** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=desc`. Check how long this specific unit has been listed and whether the price has already been reduced.
   → **Extract only**: total_dom, price_history (each date + price), number of dealer hops. Discard full response.

2. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to confirm exact specs and identify any features that could justify a premium or that the listing may have wrong.
   → **Extract only**: year, make, model, trim, key features. Discard full response.

3. **Get predicted market value** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`. This establishes the data-backed "fair" price.
   → **Extract only**: predicted_price. Discard full response.

4. **Find competing units** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=100`, `sort_by=price`, `sort_order=asc`, `rows=10`, `car_type=used`. These are the alternatives the dealer can cite during negotiation ("I can get a comparable unit at Dealer X for $1,200 less").
   → **Extract only**: per listing — dealer_name, price, miles, dom, distance, stock_number. Discard full response.

5. **Build the leverage brief** — Present:
   - **DOM leverage**: If the unit has been listed 30+ days, the dealer is motivated. 60+ days = highly motivated.
   - **Price drop history**: If the dealer already dropped the price, they may drop again. If they haven't dropped in 30+ days, a first offer below asking may trigger a counter.
   - **Competing unit citations**: List 3-5 specific competing vehicles with dealer name and price that the dealer can reference by name in the negotiation.
   - **Suggested offer price**: Predicted market value minus a negotiation margin (typically 3-5% below predicted for used, 2-3% for new). Adjust upward if the unit is priced below market or has very low DOM.

## Workflow: Finance/Lease Comparison

Use this when a customer asks "what would my payment be" or a dealer needs to compare financing across dealers.

1. **Search with finance data** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=100`, `include_finance=true`, `sort_by=price`, `sort_order=asc`, `rows=15`, `car_type=new` (finance/lease data is most common on new inventory).
   → **Extract only**: per listing — dealer_name, price, monthly_payment, term, apr, down_payment. Discard full response.

2. **Search with lease data** — Call `mcp__marketcheck__search_active_cars` with the same filters but `include_lease=true`, `rows=15`.
   → **Extract only**: per listing — dealer_name, price, monthly_payment, term, money_factor, down_payment, residual. Discard full response.

3. **Build the comparison table** — For each listing that includes finance or lease data, extract: dealer, selling price, monthly payment, term, APR (finance) or money factor (lease), down payment, and residual (lease).

4. **Calculate total cost of ownership** — For each option, compute: total payments over term + down payment = total out-of-pocket. This allows apples-to-apples comparison even when terms differ.

5. **Present the comparison** — Show a table sorted by lowest monthly payment and a separate sort by lowest total cost. Highlight the best overall deal and note any unusually favorable terms (e.g., manufacturer subvented rates, lease loyalty bonuses).

## Workflow: Market Timing Advice

Use this when a customer asks "should I buy now or wait" or a dealer needs to advise on timing.

1. **Assess current supply** — Call `mcp__marketcheck__search_active_cars` with YMMT, `zip`, `radius=150`, `stats=price,miles`, `rows=0`, `car_type=used`. The total count indicates supply depth. The price stats show current market conditions.
   → **Extract only**: total_count, mean_price, median_price. Discard full response.

2. **Assess recent demand and sell-through** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `date_from` (30 days ago), `date_to` (today), `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`. This shows how many units sold recently — a proxy for demand velocity.
   → **Extract only**: sold_count, average_days_on_market. Discard full response.

3. **Compare supply to demand** — Calculate the supply-to-demand ratio:
   - Active listings (supply) / Units sold in last 30 days (demand) = months of supply
   - Under 30 days of supply = seller's market (prices rising, buy now)
   - 30-60 days of supply = balanced market (prices stable, reasonable to wait for the right unit)
   - Over 60 days of supply = buyer's market (prices softening, negotiate aggressively or wait for further drops)

4. **Check for price trend direction** — From the stats in step 1, note the mean and median prices. Call `mcp__marketcheck__search_active_cars` with `price_change=negative`, same YMMT and location, `rows=0` to count how many dealers are dropping prices. A high percentage of the market dropping prices confirms a softening trend.
   → **Extract only**: total_count of price-drop listings. Discard full response.

5. **Deliver the timing recommendation**:
   - **Buy now**: Supply is low, demand is high, prices are rising or stable. Waiting risks paying more or missing available units.
   - **Buy soon (within 2-4 weeks)**: Market is balanced. The customer can afford to be selective but should not wait indefinitely.
   - **Wait**: Supply is high, prices are trending down, many dealers are reducing prices. Recommend checking back in 2-4 weeks for better options.

## Output
Present: search criteria summary, ranked deals table (dealer, price, miles, DOM, distance, vs-market %), market context (total supply, median price, price range, trend), and one actionable recommendation with negotiation notes where applicable.
