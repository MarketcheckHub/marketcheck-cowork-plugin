---
name: depreciation-tracker
description: >
  This skill should be used when the user asks about "claim value trending",
  "replacement cost tracking", "vehicle depreciation for claims",
  "residual value for insurance", "how fast is the insured vehicle losing value",
  "pre-loss value trajectory", "depreciation rate for settlement",
  "value retention for claims", "depreciation curve for total loss",
  "diminished value over time", "claim reserve adjustment",
  "portfolio depreciation exposure", "fleet depreciation risk",
  or needs help with tracking vehicle depreciation in the context of
  insurance claims valuation, replacement cost estimation, settlement
  trending, or reserve adequacy assessment.
version: 0.1.0
---

# Depreciation Tracker — Claim Value Trending & Replacement Cost Tracking

## Insurer Profile (Load First)

Before running any workflow, check for a saved insurer profile:

1. Read `~/.claude/marketcheck/insurer-profile.json`
2. If the file **exists**, use as defaults:
   - `zip` ← `location.zip` — use as default geography
   - `state` ← `location.state`
   - `role` ← `insurer.role` — adjuster, underwriter, claims manager
   - `claim_types` ← `insurer.claim_types` — total_loss, diminished_value, theft_recovery
   - `total_loss_threshold_pct` ← `insurer.total_loss_threshold_pct`
   - `default_comp_radius` ← `insurer.default_comp_radius`
3. If the file **does not exist**, ask for ZIP code to proceed. Suggest running `/onboarding` first.
4. **Country note:** This skill requires `get_sold_summary` and `search_active_cars` which are **US-only**. If user indicates UK, inform: "Depreciation tracking requires US sold transaction data and is not available for the UK market."
5. If profile exists and applicable, confirm: "Using profile: **[user.name]**, [ZIP], [State]"

## User Context

The primary user is an **insurance professional** — adjuster, underwriter, or claims manager — who needs to understand how vehicle values are trending to support accurate claim reserves, settlement offers, and total-loss determinations. Depreciation data directly impacts:

- **Settlement accuracy:** A vehicle depreciating at 2%/month needs a different settlement than one holding value.
- **Reserve adequacy:** Claims reserves must reflect current depreciation velocity, not stale book values.
- **Replacement cost tracking:** The cost to replace a total-loss vehicle changes as the market moves.
- **Subrogation timing:** Understanding depreciation curves helps optimize when to pursue or settle subrogation claims.

The following fields may be auto-filled from the insurer profile:

| Required | Field | Source |
|----------|-------|--------|
| Yes | Make and/or Model (or segment) | Always ask |
| Recommended | Model year(s) of interest | Always ask |
| Auto/Ask | Geography (state or zip) | Profile `location.state` or ask |
| Optional | Inventory type | `New` or `Used` (default: `Used`) |
| Optional | Comparison dimension | `EV vs ICE`, `SUV vs Sedan`, `Brand A vs Brand B` |
| Optional | Time horizon | `30 days`, `90 days`, `6 months`, `1 year` |

Always clarify whether the user wants depreciation of **used vehicles** (price decline over time on the secondary market, relevant for total-loss claims) or **new vehicle transaction-to-MSRP parity** (how much above or below sticker new cars are selling, relevant for replacement cost on newer total-loss claims).

## Workflow: Make/Model Depreciation Curve (Claims Context)

Use this when an adjuster asks "how fast is the RAV4 losing value" or "what's the depreciation trend for 2022 Civics" to inform settlement offers and reserve adjustments.

1. **Get current period sold data** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model`, `inventory_type=Used`, `date_from` set to the first of the current month minus 30 days (e.g., `2026-02-01`), `date_to` set to the last day of that month (e.g., `2026-02-28`). If the user specified a state, include `state`. Record the `average_sale_price` and `sold_count`.

2. **Get historical sold data at multiple intervals** — Make separate calls to `mcp__marketcheck__get_sold_summary` for each lookback period to build the curve:
   - **60 days ago**: `date_from=2026-01-01`, `date_to=2026-01-31`
   - **90 days ago**: `date_from=2025-12-01`, `date_to=2025-12-31`
   - **6 months ago**: `date_from=2025-09-01`, `date_to=2025-09-30`
   - **1 year ago**: `date_from=2025-03-01`, `date_to=2025-03-31`
   Record `average_sale_price` at each point. Adjust the actual dates based on today's date.

3. **Get current active market asking price** — Call `mcp__marketcheck__search_active_cars` with `year`, `make`, `model`, `car_type=used`, `stats=price`, `rows=0`. If state/zip was provided, include `zip` and `radius=100` or `state` in the filter. This gives the current asking price stats (mean, median, min, max) for unsold inventory — the forward-looking indicator of where settlement values are headed.

4. **Get original MSRP baseline** — Call `mcp__marketcheck__search_active_cars` with the same `year`, `make`, `model`, `rows=1`, `sort_by=price`, `sort_order=desc` to find a representative listing. Then call `mcp__marketcheck__decode_vin_neovin` with that listing's VIN to extract the original MSRP from the build data. If MSRP is not available from the decode, use the highest transaction price from the 1-year-ago sold data as a proxy ceiling.

5. **Build the depreciation curve with claims impact** — Calculate at each time interval:
   - **Retention %** = (average_sale_price at interval / original MSRP) x 100
   - **Monthly depreciation rate** = (price change between consecutive intervals) / (months between intervals)
   - **Annualized depreciation rate** = monthly rate x 12
   - **Settlement impact** = dollar change in FMV over the period (affects claim reserve accuracy)
   Present as a table and describe the curve shape (linear, accelerating, stabilizing).

## Workflow: Segment Value Trends (Portfolio Risk Context)

Use this when an underwriter asks "are SUVs holding value better than sedans in our claims portfolio" or "how is EV depreciation affecting our total-loss exposure."

1. **Get current period segment data** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=body_type`, `ranking_measure=average_sale_price`, `date_from` (first of prior month), `date_to` (last of prior month), `inventory_type=Used`, `top_n=10`. This returns average transaction prices by body type for the current period.

2. **Get prior period segment data** — Call `mcp__marketcheck__get_sold_summary` with the same parameters but `date_from` and `date_to` shifted back 3 months (or the user's chosen comparison window). This gives the baseline for calculating segment-level price movement.

3. **Get fuel type comparison** — Call `mcp__marketcheck__get_sold_summary` with `fuel_type_category=EV`, `date_from` (current period), `date_to` (current period end), `inventory_type=Used`. Record the average sale price and sold count. Repeat with `fuel_type_category=ICE`. Repeat both calls for the prior period.

4. **Calculate segment trends with insurance impact** — For each body type and fuel type:
   - **Period-over-period price change** = (current avg price - prior avg price) / prior avg price x 100
   - **Volume change** = (current sold_count - prior sold_count) / prior sold_count x 100
   - **Claims impact assessment:**
     - Segments with price declined more than 3%: "Accelerating depreciation — total-loss claims in this segment are becoming less expensive, but existing reserves may be overstated"
     - Segments held within +/- 1%: "Stable — current settlement benchmarks remain reliable"
     - Segments where price increased: "Appreciating — replacement costs are rising, reserves may be understated"

5. **Deliver the segment comparison** — Present a ranked table from strongest retention to weakest. Highlight the EV vs ICE gap specifically (EV depreciation directly impacts claims exposure for insured EV portfolios). Include volume context — a segment with strong prices but falling volume may signal softening ahead, requiring proactive reserve adjustment.

## Workflow: Brand Residual Ranking (Underwriting Context)

Use this when an underwriter asks "which brands hold value best" or "rank automakers by residual value for our risk models."

1. **Get current period brand prices** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=average_sale_price`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `inventory_type=Used`, `top_n=25`.

2. **Get prior period brand prices** — Call `mcp__marketcheck__get_sold_summary` with the same parameters but dates shifted back 6 months (or user's preferred comparison window). This establishes the baseline for retention calculation.

3. **Get volume context** — Call `mcp__marketcheck__get_sold_summary` with `ranking_dimensions=make`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (current period), `date_to` (current period end), `inventory_type=Used`, `top_n=25`.

4. **Calculate brand retention scores with risk tiers** — For each make:
   - **Retention %** = current average_sale_price / prior average_sale_price x 100
   - **Volume trend** = current sold_count vs prior sold_count (indicates demand strength)
   - Rank brands by retention % descending
   - Classify into **insurance risk tiers**:
     - Tier 1 — Low Risk (>98% retention): Strong value retention, lower total-loss claim severity
     - Tier 2 — Moderate Risk (95-98%): Normal depreciation, standard reserves adequate
     - Tier 3 — Elevated Risk (90-95%): Faster depreciation, consider adjusting reserves upward
     - Tier 4 — High Risk (<90%): Rapid depreciation, total-loss claims increasingly likely; may warrant premium adjustments

5. **Present the brand ranking** — Show a ranked table with: Rank, Make, Current Avg Price, Prior Avg Price, Retention %, Volume, Risk Tier. Note: "Brands in Tier 4 have the highest total-loss claim frequency due to rapid depreciation. Underwriters should factor retention tier into premium calculations for comprehensive and collision coverage."

## Workflow: Geographic Depreciation Variance (Settlement Calibration)

Use this when an adjuster asks "where do Tacomas hold value best" or "which states have the highest replacement costs" to calibrate settlement offers by region.

1. **Get state-level transaction data** — Call `mcp__marketcheck__get_sold_summary` with `make`, `model` (from user), `summary_by=state`, `date_from` (first of prior month), `date_to` (last of prior month), `inventory_type=Used`, `limit=5000`.

2. **Get national baseline** — Call `mcp__marketcheck__get_sold_summary` with the same `make`, `model`, same date range, but without `summary_by` to get the national average transaction price.

3. **Calculate geographic variance for settlement calibration** — For each state:
   - **Price index** = state average_sale_price / national average_sale_price x 100 (100 = national average)
   - **Premium/discount** = state price - national price in dollars
   - Sort by price index descending to show where vehicles command the highest premiums

4. **Identify settlement calibration patterns** — Group states into:
   - **Premium markets** (index > 105): Higher replacement costs — settlements should reflect the claimant's local market, not national averages
   - **At-national-average** (index 95-105): Standard settlement benchmarks apply
   - **Discount markets** (index < 95): Lower replacement costs — but settlements must still reflect what the claimant would actually pay to replace the vehicle in their local market
   Note: "Settlement offers must reflect the claimant's local market. Using a national average in a premium market understates replacement cost and invites disputes."

5. **Deliver the geographic map** — Present as a ranked table: State, Avg Transaction Price, National Avg, Price Index, Premium/Discount $, Sold Count. Highlight the top 5 and bottom 5 states for the specific vehicle. Note the settlement implications for each region.

## Workflow: MSRP Parity Tracker (Replacement Cost for New Vehicles)

Use this when a claims manager asks "which new cars are selling over sticker" or "what's the actual replacement cost for a new [Model]" — critical for claims on vehicles less than 1 year old where replacement cost may exceed MSRP.

1. **Get current MSRP parity data** — Call `mcp__marketcheck__get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=price_over_msrp_percentage`, `ranking_order=desc`, `date_from` (first of prior month), `date_to` (last of prior month), `top_n=30`.

2. **Get prior period parity data** — Call `mcp__marketcheck__get_sold_summary` with the same parameters but dates shifted back 3 months. This shows the direction of parity movement.

3. **Get volume context** — Call `mcp__marketcheck__get_sold_summary` with `inventory_type=New`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `date_from` (current period), `date_to` (current period end), `top_n=30`.

4. **Classify parity status with claims implications** — For each make/model:
   - **Above MSRP** (price_over_msrp_percentage > 0): "Replacement cost exceeds MSRP — total-loss settlements on these vehicles may need to reflect actual market replacement cost, not sticker price"
   - **At MSRP** (price_over_msrp_percentage between -1% and 0%): "Replacement at MSRP — standard settlement"
   - **Below MSRP** (price_over_msrp_percentage < -1%): "Replacement below MSRP — settlement can reflect actual transaction prices"
   - **Trend direction**: compare current vs prior period to show if replacement costs are rising or falling

5. **Present the parity report** — Show a table: Make/Model, Current % Over/Under MSRP, Prior Period %, Change Direction, Sold Volume. Highlight:
   - Models that flipped from above-MSRP to below (replacement costs normalizing)
   - Models still commanding premiums (claims on these vehicles may face dispute if settled at MSRP)
   - Models with deepening discounts (favorable for claims resolution)

## Quantifiable Outcomes & KPIs

| KPI | What to Show | Insurance Business Impact |
|-----|-------------|--------------------------|
| Monthly Depreciation Rate % | (Prior month avg price - Current month avg price) / Prior month avg price | Directly impacts settlement accuracy; a 1% monthly acceleration on a $30K vehicle = $300/month change in claim value |
| Residual Retention % | Current transaction price / Original MSRP x 100 | Core metric for total-loss threshold calculations; determines when repair cost exceeds vehicle value |
| Segment Depreciation Comparison | Side-by-side retention % for EV vs ICE, SUV vs Sedan | Portfolio exposure assessment; if EVs depreciate 2x faster, total-loss frequency increases for insured EV fleets |
| Brand Risk Tier | Retention-based tier classification (Tier 1-4) | Underwriting signal; Tier 4 brands have higher total-loss claim frequency and may warrant premium adjustments |
| Price-Over-MSRP % | Transaction price / MSRP - 1, expressed as percentage | Replacement cost for new-vehicle total-loss claims; above-MSRP models cost more to replace than sticker suggests |
| Geographic Value Variance | State price index (state avg / national avg x 100) | Settlement calibration; using national averages in premium markets understates replacement cost and invites claimant disputes |

## Action-to-Outcome Funnel

1. **Depreciation accelerating beyond 2% monthly on a specific model** — Claims managers should review open reserves on that model and adjust downward. Underwriters should note the acceleration for renewal pricing. Present the specific monthly rate and compare to the segment average. "Open claims on 2022 [Model] should be re-reserved — FMV has declined $X,XXX in the past 90 days."

2. **EV depreciation running 1.5x+ faster than ICE equivalent** — Underwriters should apply separate depreciation assumptions for EV portfolios. Claims adjusters should use tighter comparable windows (60 days vs 90 days) for EV total-loss valuations since values are moving faster. Show the EV vs ICE gap in dollars and percentage at each time interval.

3. **Brand drops from Tier 1 to Tier 3 risk** — Underwriting should review premium adequacy for that brand's comprehensive and collision coverage. Claims adjusters should expect increasing total-loss frequency for that brand. Show the trajectory over the prior 3-6 months to distinguish a blip from a trend.

4. **State-level replacement cost 10%+ above national average** — Settlement offers in that state must reflect the local market, not the national average. Using national averages will result in disputes and bad-faith claims. Quantify the dollar gap per vehicle.

5. **New model replacement cost exceeds MSRP by 5%+** — Total-loss settlements on these vehicles should reflect actual market replacement cost, not MSRP. Document the premium with transaction evidence. "Settling at MSRP on a [Model] understates replacement cost by $X,XXX based on [N] recent transactions."

## Output Format

Always present results in this structure:

**Analysis Summary** — What was analyzed (make/model/segment), time period, geography, and inventory type.

**Claims Impact Headline** — One sentence with the key finding framed for insurance (e.g., "The 2022 Toyota RAV4 has retained 87.3% of its original MSRP after 3 years, depreciating at 0.35% per month. Current total-loss claims on this model should settle in the $28,500-$30,200 range based on transaction evidence.").

**Depreciation Curve / Trend Table**

| Period | Avg Transaction Price | Retention % | Monthly Rate | Volume | Settlement Impact |
|--------|----------------------|-------------|--------------|--------|-------------------|
| Current Month | $XX,XXX | XX.X% | X.XX% | X,XXX | Current FMV benchmark |
| 60 Days Ago | $XX,XXX | XX.X% | X.XX% | X,XXX | +/- $X,XXX vs current |
| 90 Days Ago | $XX,XXX | XX.X% | X.XX% | X,XXX | +/- $X,XXX vs current |
| 6 Months Ago | $XX,XXX | XX.X% | X.XX% | X,XXX | +/- $X,XXX vs current |
| 1 Year Ago | $XX,XXX | XX.X% | X.XX% | X,XXX | +/- $X,XXX vs current |

**Comparison Context** — How the subject compares to its segment, competing models, or prior periods. Always include at least one comparison dimension.

**Claims & Underwriting Signals** — Bullet list of notable trends:
- Acceleration or deceleration in depreciation rate and impact on open claims
- Volume trends that may predict future settlement value movements
- Geographic or segment-specific anomalies affecting specific markets
- MSRP parity shifts affecting replacement cost on newer total-loss claims
- Reserve adequacy assessment based on current depreciation velocity

**Recommendation** — One clear action tied to the user's role:
- **Adjuster:** Adjust settlement offer range based on current depreciation velocity
- **Underwriter:** Review premium adequacy and risk tier for the brand/segment
- **Claims Manager:** Re-reserve open claims if depreciation has accelerated beyond initial assumptions

Include the quantified business impact (e.g., "Re-reserving the 47 open claims on this model at the current FMV would reduce reserve exposure by $X,XXX per claim, or $XX,XXX total").
