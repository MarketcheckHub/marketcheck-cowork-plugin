---
name: competitive-pricer
description: >
  This skill should be used when the user asks to "price this car",
  "am I priced right", "competitive pricing", "price check VIN",
  "who is undercutting me", "market price for this", "price my inventory",
  "compare my price", or needs help with pricing strategy, price positioning,
  competitive price analysis, or identifying pricing opportunities in their market.
version: 0.2.0
---

# Competitive Pricer — Real-Time Price Positioning Against Your Market

## Profile
Load the `marketcheck-profile.md` project memory file if exists. Extract: zip/postcode, state/region, dealer_id, dealer_type, franchise_brands, radius, country, cpo_program, cpo_certification_cost. Also extract: `default_inventory_type` from preferences (`"used"` | `"new"` | `"both"`; default `"used"` if not set). Apply as `car_type` in all comp searches. Override if user explicitly states otherwise. Never mix new and used data in the same pricing section. If missing, ask for ZIP and radius. **US**: `search_active_cars`, `decode_vin_neovin`, `predict_price_with_comparables`, `get_car_history`, `search_past_90_days`, `get_sold_summary`. **UK**: `search_uk_active_cars`, `search_uk_recent_cars` only (no VIN decode/ML prediction — ask user for YMMT, use comp median). Confirm: "Using profile: [dealer.name], [ZIP], [Country]". Dual pricing: report BOTH franchise and independent prices; dealer's `dealer_type` = PRIMARY, other = SECONDARY context.

## Data Quality Rule
**Price filter:** In every listing result set, skip and discard any entry where `price` is 0, null, or missing. Never display a $0 price to the user. When calling `search_active_cars` for cheapest/lowest-priced listings, always include `price_min=1` in the API params to exclude unpriced inventory at the source.

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

## Standard Competitive Analysis Table Schema

**All competitive set tables in this skill — across every workflow and every model — must use this exact 8-column schema. Do not vary columns between models or workflows.**

| Dealer | Type | Price | Miles | DOM | Distance | vs Mkt Median | Price Drop? |
|--------|------|-------|-------|-----|----------|---------------|-------------|

- **Type**: `F` = franchise, `I` = independent
- **vs Mkt Median**: signed % delta from the comp set median (e.g. `-3.2%` or `+1.8%`)
- **Price Drop?**: `Yes` / `No` derived from `price_change` field
- Sort: price ascending by default; mark the row closest to the user's price with `← You`

## User Context
Dealer user (used car manager, pricing analyst, GM) checking competitive price positioning, margin opportunities, and aging risk.

| Required | Field | Source |
|----------|-------|--------|
| Yes | VIN or YMMT | Ask |
| Auto | ZIP, radius, dealer_type | Profile |
| Recommended | Mileage, asking price | Ask |

VIN provided → decode first to confirm specs (US only; UK dealers provide specs manually).

## Workflow: Price-Check a Single VIN

Use this when a dealer says "price check this VIN" or "am I priced right on this one."

1. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to confirm year, make, model, trim, body type, drivetrain, engine, and transmission. Present the decoded specs to the user for confirmation.
   → **Extract only**: year, make, model, trim, body_type, drivetrain, engine, transmission. Discard full response.

2. **Get predicted market prices (dual)** — Make TWO calls to `mcp__marketcheck__predict_price_with_comparables`:
   - **Primary:** with `vin`, `miles`, `zip`, `dealer_type` matching the source dealer's type (from profile). This is the primary comparison.
   - **Secondary:** with the same parameters but `dealer_type` set to the OTHER type (franchise<>independent). This provides market context.
   → **Extract only**: predicted_price, comparable VINs/prices from each call. Discard full response.

2a. **CPO pricing (if applicable)** — If the vehicle is CPO (detected per CPO Detection section above), make additional calls with `is_certified=true` for both franchise and independent predictions. Report CPO market price separately from non-CPO market price, and show the CPO premium.
   → **Extract only**: predicted_price (certified), predicted_price (non-certified), delta for CPO premium. Discard full response.

3. **Pull competing active listings** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `trim` (from step 1), `zip`, `radius` (from profile `default_radius_miles`, minimum 75), `sort_by=price`, `sort_order=asc`, `price_min=1`, `rows=20`, `car_type=used`. Skip any returned listing where price = 0 or is missing. Additionally, call `mcp__marketcheck__search_active_cars` with the same parameters but add `dealer_type` matching the source dealer's type to get a filtered competitive set from SAME-type dealers only. Also call with `price_change=negative`, `rows=0` to get the count of comps that have recently dropped prices.
   → **Extract only**: per listing — price, miles, dom, dealer_name, dealer_type, distance, price_change; plus total count from each call. Discard full response.

3a. **Pull sold velocity data** — In parallel:
   - Call `mcp__marketcheck__search_past_90_days` with `year`, `make`, `model`, `trim`, `zip`, `radius` (from profile, minimum 75), `car_type=used`, `rows=0` to get total units sold and average metrics.
   - Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `summary_by=state`, `ranking_measure=average_days_to_sell`, `top_n=5`.
   → **Extract only**: sold_count (90 days), avg_sale_price, avg_days_on_market. Discard full response.

3b. **DOM distribution** — From the active comps in step 3, bucket by DOM:
   - **Fresh** (0–30 days): count and %
   - **Aging** (31–60 days): count and %
   - **Stale** (60+ days): count and %
   Calculate: months of supply = active_listing_count ÷ (sold_count_90days ÷ 3). Round to one decimal.

4. **Calculate price position** — From all comp data, compute:
   - Sorted price array → derive Q1 (25th pct), Median (50th pct), Q3 (75th pct)
   - Mean and standard deviation of prices
   - Mean and median of mileage
   - Percentile rank of the dealer's asking price among all comps
   - Count of comps priced within ±5% of the dealer's price
   - Count of comps with price drops (from step 3 price_change=negative call)
   - % of total comps that have dropped price (market price-drop velocity)

5. **Deliver the verdict** — Classify the price as **Below Market** (bottom quartile), **At Market** (middle 50%), or **Above Market** (top quartile) and recommend an action. Present using the structured blocks below:

```
── Market Snapshot ──────────────────────────────────────────────────
Active Supply ([trim]):   N units within [radius]mi  (trim-matched)
Active Supply ([model]):  N units (all trims, broader context)
Sold Last 90 Days:        N units | Avg Sale Price $XX,XXX | Avg DOM XX days
Months of Supply:         X.X months  [< 2.0 = seller's market | > 4.0 = buyer's market]
Price Drop Activity:      N of N comps (XX%) have reduced price

── Price Distribution (trim comps, [radius]mi) ───────────────────────
Min:      $XX,XXX    Q1:   $XX,XXX
Median:   $XX,XXX    Q3:   $XX,XXX
Max:      $XX,XXX    Mean: $XX,XXX   StdDev: ±$X,XXX

── Mileage Distribution ─────────────────────────────────────────────
Min: XX,XXX mi   Median: XX,XXX mi   Max: XX,XXX mi   Mean: XX,XXX mi

── DOM Distribution ─────────────────────────────────────────────────
Fresh (0–30d): N units (XX%) | Aging (31–60d): N units (XX%) | Stale (60+d): N units (XX%)

── Your Price Position ──────────────────────────────────────────────
Your Price:              $XX,XXX
Franchise Mkt Price:     $XX,XXX  (based on N comps)
Independent Mkt Price:   $XX,XXX  (based on N comps)
Gap vs Your Market:      ±$X,XXX  (X.X% [above/below] [dealer_type] market)  ← PRIMARY
Gap vs Other Market:     ±$X,XXX  (X.X% [above/below] other market)          ← CONTEXT
Percentile Rank:         XXth (priced lower than XX% of competing units)
Units within ±5% of your price: N competing units
```

Then show the competitive set table using the Standard Competitive Analysis Table Schema (8 columns). Mark the row closest to the dealer's price with `← You`.

Then deliver: **Verdict** (Below / At / Above Market), **Recommended Action** (one sentence with dollar impact), **Key Signals** (2–3 bullets on market conditions — supply trend, price drop velocity, DOM pattern).

## Workflow: Batch Competitive Scan

Use this when a dealer provides a list of VINs (e.g., "check pricing on my front-line inventory").

1. **Accept VIN list** — Collect all VINs from the user. Confirm the market ZIP and radius once (applies to all).

2. **Loop per VIN** — For each VIN:
   - Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type` (Primary — matching source dealer's type).
   - Call `mcp__marketcheck__predict_price_with_comparables` with the same parameters but `dealer_type` set to the OTHER type (Secondary — franchise<>independent).
   - If the vehicle is CPO, make additional calls with `is_certified=true` for both dealer types.
   - Call `mcp__marketcheck__search_active_cars` with the decoded YMMT, `zip`, `radius` (from profile, minimum 75), `sort_by=price`, `sort_order=asc`, `price_min=1`, `rows=10`, `car_type=used`. Skip any listing where price = 0 or is missing.
   → **Extract only**: per VIN — predicted_price (franchise+independent), comp count, comp price range (min/median/max), total active supply. Discard full response.

3. **Build the price-position table** — For each VIN, calculate: asking price, franchise market price ("Franchise Mkt"), independent market price ("Independent Mkt"), delta vs primary market, delta vs secondary market, percentile rank, competing unit count, and recommended action.

4. **Prioritize actions** — Sort the table by largest overpricing first (highest risk of aging), then by largest underpricing (margin opportunity).

5. **Present the summary** — Show the full table plus a rollup: total units scanned, count overpriced, count underpriced, count at market, estimated margin recovery if adjusted.

## Workflow: Trade-In VIN Price History

Use this when a dealer asks "what's the history on this trade" or needs context before making an offer.

1. **Pull listing history** — Call `mcp__marketcheck__get_car_history` with `vin`, `sort_order=desc` to get the full timeline of listings across dealers.
   → **Extract only**: per listing — date, dealer_name, price, dom, is_certified. Discard full response.

2. **Decode the VIN** — Call `mcp__marketcheck__decode_vin_neovin` with `vin` to get full specs.
   → **Extract only**: year, make, model, trim. Discard full response.

3. **Get predicted price** — Call `mcp__marketcheck__predict_price_with_comparables` with `vin`, `miles`, `zip`, `dealer_type`.
   → **Extract only**: predicted_price. Discard full response.

4. **Analyze the trajectory** — From the history, extract:
   - Number of dealers that have listed this VIN
   - Price at each listing and the direction of change
   - Total days on market across all listings
   - Whether the vehicle was ever listed as certified

5. **Deliver trade-in context** — Show the price trajectory chart, current market value, and flag any red flags (e.g., multiple dealer hops in a short period, steep price drops suggesting a problem unit).

## Workflow: Market Price Distribution

Use this when a dealer asks "what's the market look like for this model" or wants a statistical overview.

1. **Pull model-level market stats** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=100`, `car_type=used`, `stats=price,miles`, `rows=0`. The `rows=0` returns only stats without individual listings.
   → **Extract only**: mean, median, min, max, stddev for price and miles, total count. Discard full response.

1a. **Pull trim-level stats** — If trim is known, call `mcp__marketcheck__search_active_cars` again adding `trim`, same location and `stats=price,miles`, `rows=0`.
   → **Extract only**: mean, median, min, max, stddev for price and miles, trim count. Discard full response.

1b. **Pull channel split stats** — Make two additional calls:
   - `mcp__marketcheck__search_active_cars` with same YMMT+location filters, `dealer_type=franchise`, `stats=price`, `rows=0`
   - `mcp__marketcheck__search_active_cars` with same YMMT+location filters, `dealer_type=independent`, `stats=price`, `rows=0`
   → **Extract only**: median, mean, count per dealer type. Discard full response.

1c. **Pull sold velocity** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `summary_by=state`, `ranking_measure=sold_count`, `top_n=5`.
   → **Extract only**: sold_count, avg_days_to_sell. Use to compute months of supply = model_active_count ÷ (sold_count ÷ 3). Discard full response.

2. **Pull the cheapest listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=asc`, `price_min=1`, `rows=8`. Skip and exclude any listing where price = 0, null, or missing before displaying.
   → **Extract only**: per listing — price, miles, dom, dealer_name, dealer_type, distance. Discard full response.

3. **Pull the most expensive listings** — Call `mcp__marketcheck__search_active_cars` with the same filters plus `sort_by=price`, `sort_order=desc`, `price_min=1`, `rows=5`. Skip any listing where price = 0 or missing.
   → **Extract only**: per listing — price, miles, dom, dealer_name, dealer_type. Discard full response.

4. **Present the distribution** — For each scope (model-level and trim-level where available), show using this consistent block:

```
── [YEAR] [MAKE] [MODEL] ([all trims] or [TRIM]) — Local Market Distribution ──
Active Supply:      N listings within [radius]mi  |  N franchise / N independent
Sold (90 days):     N units  |  Avg Sale Price: $XX,XXX  |  Avg DOM: XX days
Months of Supply:   X.X months  [< 2.0 = seller's market | > 4.0 = buyer's market]

Price Distribution:
  Min:    $XX,XXX        Q1:    $XX,XXX
  Median: $XX,XXX        Q3:    $XX,XXX
  Max:    $XX,XXX        Mean:  $XX,XXX   ±$X,XXX (1σ)

By Channel:
  Franchise dealers:    N units  |  Median $XX,XXX  |  Mean $XX,XXX
  Independent dealers:  N units  |  Median $XX,XXX  |  Mean $XX,XXX
  Channel spread:       $X,XXX   ([franchise premium / independent discount])

Price Bands (quartiles):
  Bottom 25% — deal territory:   $XX,XXX – $XX,XXX
  Middle 50% — market range:     $XX,XXX – $XX,XXX
  Top 25%    — premium territory: $XX,XXX – $XX,XXX
```

Show where the user's vehicle falls in the price bands (if asking price is known).

Then display the lowest-priced listings table using the Standard Competitive Analysis Table Schema (8 columns). Only show listings with a valid price > 0.

5. **Highlight outliers** — Flag any listings priced more than 2 standard deviations from the mean. For each flagged listing show: price, miles, dealer, DOM, and suspected reason (low miles premium / high miles discount / salvage title / rare trim / data quality issue). These are potential data quality issues or genuinely unique units — do not use them to anchor pricing decisions.

## Workflow: Competitor Price Movement

Use this when a dealer asks "who dropped their price" or "who is undercutting me."

1. **Scan for recent price drops** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `zip`, `radius=75`, `price_change=negative`, `sort_by=price`, `sort_order=asc`, `price_min=1`, `rows=20`.
   → **Extract only**: per listing — price, price_change_amount, dealer_name, dealer_type, dom, distance. Discard full response.

2. **Scan for recent price raises** — Call `mcp__marketcheck__search_active_cars` with the same filters but `price_change=positive`, `rows=10`.
   → **Extract only**: per listing — price, price_change_amount, dealer_name. Discard full response.

3. **Identify aggressive competitors** — From the price-drop results, group by dealer and count the number of drops. Dealers with multiple recent drops are signaling inventory pressure.

4. **Calculate competitive exposure** — For each dropped listing, compare the new price to the user's asking price on similar units. Flag any that now undercut the user.

5. **Recommend response** — For each unit where the user is now being undercut, suggest whether to match, split the difference, or hold based on the user's DOM and the competitor's DOM.

## Output

Present: summary headline (vehicle + price position verdict), the structured Market Snapshot and Price Position blocks (see Price-Check Single VIN step 5 format), competitive set table using the Standard Competitive Analysis Table Schema (8 columns — consistent across all models), comparison context (franchise vs independent), key signals (2–3 bullets), and one actionable recommendation with dollar impact.

**Table consistency rule:** Every competitive analysis table rendered in this skill — for a single VIN or model-level distributions — MUST use the standard 8-column schema: `Dealer | Type | Price | Miles | DOM | Distance | vs Mkt Median | Price Drop?`. Column names, order, and presence must be identical across all models in the same output. Never use different column names for the same data.
