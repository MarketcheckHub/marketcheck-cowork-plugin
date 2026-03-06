---
name: oem-stock-tracker
description: >
  This skill should be used when the user asks about "brand health check",
  "how is my brand doing", "brand performance dashboard", "pricing power analysis",
  "days supply", "brand volume momentum", "inventory build",
  "operational KPIs", "brand health metrics", "self-monitoring",
  "brand demand trends", "competitive threat assessment",
  or needs help tracking brand health indicators and operational KPIs
  for their own OEM brands and monitoring competitive threats.
version: 0.1.0
---

# OEM Stock Tracker — Brand Health Check & Competitive Threat Monitor

## Manufacturer Profile (Load First)

Before running any workflow, check for a saved manufacturer profile:

1. Read `~/.claude/marketcheck/manufacturer-profile.json`
2. If the file **does not exist**: Ask: "Which brand(s) do you represent?" and "Which states or 'national'?" and "Which competitors to monitor?"
3. If the file **exists**, extract silently:
   - `brands` ← `manufacturer.brands` — your own brands (these are OPERATIONAL KPIs)
   - `states` ← `manufacturer.states` — geographic scope
   - `competitor_brands` ← `manufacturer.competitor_brands` — these are COMPETITIVE THREATS
   - `country` ← `location.country` (this skill is **US-only** — requires `get_sold_summary`)
   - `user_name` ← `user.name`
   - `company` ← `user.company`
4. **Country check:** If `country=UK`, inform the user: "Brand health monitoring requires US sold transaction data. This skill is not available for UK market." Stop.
5. If profile exists, confirm briefly: "Using profile: **[user_name]** at **[company]** — Monitoring: **[brands]**, Watching: **[competitor_brands]**"

## User Context

The primary user is an **OEM regional manager, brand strategist, product planner, or distributor** who needs to self-monitor their own brand's health and track competitive threats. This is NOT an investment signal tool — it is an operational dashboard for brand management.

Each metric is framed as either:
- **OPERATIONAL KPI** (for your own brands) — "How healthy is our brand?"
- **COMPETITIVE THREAT** (for competitor brands) — "Where are competitors gaining on us?"

## Built-in Brand Mapping

```
TOYOTA MOTOR  → Toyota, Lexus
HONDA MOTOR   → Honda, Acura
GM            → Chevrolet, GMC, Buick, Cadillac
FORD MOTOR    → Ford, Lincoln
STELLANTIS    → Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati
TESLA         → Tesla
HYUNDAI MOTOR → Hyundai, Kia, Genesis
NISSAN MOTOR  → Nissan, Infiniti
MERCEDES-BENZ → Mercedes-Benz
BMW GROUP     → BMW, MINI, Rolls-Royce
VW GROUP      → Volkswagen, Audi, Porsche, Lamborghini, Bentley
RIVIAN        → Rivian
LUCID         → Lucid
```

If the user provides a parent company name, map it to makes. If the user provides a make name (e.g., "Toyota"), use directly.

## Workflow: Brand Health Check

Use this when a user asks "How is my brand doing?" or "Brand health dashboard" or "Operational KPIs."

### Step 1 — Resolve the entity

Map the user's input or profile brands to the list of makes. Confirm: "Analyzing brand health for **[Company]**: [Make1, Make2, ...]"

Determine date ranges:
- **Current month:** first day of the most recent complete month → last day
- **Prior month:** the month before current
- **Baseline (3 months ago):** default 3-month lookback

### Step 2 — Volume momentum (YOUR BRANDS — Operational KPI)

For EACH make in your brands, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the make
- `state`: from profile or user input (or omit for national)
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 1

Repeat for prior month and 3-month-ago period.

Sum sold_count across all your makes.

Calculate:
- **MoM Volume Change %** = (current - prior) / prior x 100
- **3-Month Trend %** = (current - 3mo_ago) / 3mo_ago x 100
- **Status:** HEALTHY if MoM > +3% AND 3mo > +5%; DECLINING if MoM < -3% AND 3mo < -5%; STABLE if mixed; WATCH if MoM positive but 3mo negative (short-term bounce)

### Step 3 — Pricing power (YOUR BRANDS — Operational KPI)

For each make, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the make
- `state`: from profile or user input
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `average_sale_price`
- `top_n`: 1

Repeat for prior month.

Also call for new vehicles specifically:
- `inventory_type`: `New`
- `ranking_measure`: `price_over_msrp_percentage`

Calculate:
- **Avg Sale Price Change %** = MoM change in average_sale_price
- **Price vs MSRP %** = price_over_msrp_percentage (positive = above sticker, negative = discounting)
- **MSRP Trend (bps)** = (current MSRP % - prior MSRP %) x 100
- **Status:** STRONG if price rising AND above MSRP; ERODING if price falling AND below MSRP (deepening discounts); WATCH if price stable but MSRP shifting negative

### Step 4 — Inventory health / Days Supply (YOUR BRANDS — Operational KPI)

Call `mcp__marketcheck__search_active_cars` with:
- `make`: each make
- `state` (via `seller_state`) or national
- `car_type`: `new`
- `stats`: `price,dom`
- `rows`: 0

Call `mcp__marketcheck__get_sold_summary` for the same make/state/period to get monthly sold volume.

Calculate:
- **Days Supply** = (Active Inventory Count / Monthly Sold Count) x 30
- **Status:** TIGHT if < 45 days (strong demand); HEALTHY if 45-75 days; BUILDING if > 75 days (potential production adjustment needed); ALERT if rising rapidly (>15% MoM increase)

### Step 5 — Market share (YOUR BRANDS vs COMPETITORS)

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile or user input
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 25

Repeat for prior month.

Calculate your aggregate share across your makes AND each competitor's share:
- **Your Share %** = sum of your makes sold / total sold x 100
- **Competitor Share %** = same for each competitor
- **Share Change (bps)** for each
- **Net Share Flow** = your bps change - competitor bps change (positive = you are winning)
- **Status:** GAINING if > +30 bps; LOSING if < -30 bps; HOLDING if within +/-30 bps

### Step 6 — DOM trend (demand signal)

From the sold data in Step 2/3, extract `average_days_on_market` for each period.

Calculate:
- **DOM MoM Change %** = (current_dom - prior_dom) / prior_dom x 100
- **Status:** HEALTHY if DOM falling (selling faster); SOFTENING if DOM rising > 10% (demand weakening); STABLE if flat

### Step 7 — EV transition (if applicable)

If your brands sell EVs:

Call `mcp__marketcheck__get_sold_summary` with:
- `make`: your makes
- `fuel_type_category`: `EV`
- Current and prior periods

Calculate:
- **EV % of your total sales** = EV sold / total your brand sold x 100
- **EV MoM change (bps)** = trend direction
- **EV avg price** and MoM change
- Compare to competitor EV penetration

### Step 8 — Segment mix

Call `mcp__marketcheck__get_sold_summary` with:
- `make`: each of your makes
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `sold_count`
- Current period

Calculate share by segment (Pickup, SUV, Sedan, EV, etc.) and pricing trend per segment.

## Output

```
BRAND HEALTH CHECK — [Company Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: [State or National] | Period: [Current Month] vs [Prior Month] vs [3mo Ago]
Brands: [Make1, Make2, ...]

YOUR BRAND — OPERATIONAL KPIs
Metric                | Current    | Prior Mo   | 3mo Ago    | Trend       | Status
----------------------|------------|------------|------------|-------------|--------
Volume (sold units)   | XXX,XXX    | XXX,XXX    | XXX,XXX    | +X.X% MoM  | HEALTHY
Avg Sale Price        | $XX,XXX    | $XX,XXX    | $XX,XXX    | +X.X% MoM  | STRONG
Price vs MSRP (new)   | +X.X%      | +X.X%      | +X.X%      | ↓ XXX bps   | WATCH
Days Supply (new)     | XX days    | XX days    | XX days    | +X.X%       | HEALTHY
Market Share          | XX.X%      | XX.X%      | XX.X%      | +XX bps     | GAINING
Avg DOM               | XX days    | XX days    | XX days    | +X.X%       | STABLE

COMPETITIVE THREAT MONITOR
Competitor      | Share %  | Share Change | Volume MoM | Pricing Trend | Threat Level
----------------|----------|-------------|------------|---------------|-------------
[Competitor A]  | XX.X%    | +XX bps      | +X.X%      | Rising        | HIGH
[Competitor B]  | XX.X%    | -XX bps      | -X.X%      | Falling       | LOW
[Competitor C]  | XX.X%    | +XX bps      | +X.X%      | Stable        | MODERATE

Net Share Flow: Your brands [gained/lost] [X] bps while competitors [gained/lost] [Y] bps combined.

[If your brands sell EVs:]
EV PROGRESS
EV % of Your Sales   | X.X%       | X.X%       | X.X%       | +XX bps     | Growing/Stalled
EV Avg Price          | $XX,XXX    | $XX,XXX    | $XX,XXX    | -X.X%       | Compressing/Stable
Competitor EV %       | X.X%       | X.X%       |            |             | [Ahead/Behind you]

SEGMENT MIX (your brands)
Segment   | Share   | MoM Trend | Pricing Trend | Status
----------|---------|-----------|---------------|--------
Pickup    | XX%     | stable    | -X.X%         | STABLE
SUV       | XX%     | +X%       | -X.X%         | WATCH
Sedan     | XX%     | -X%       | flat          | STABLE

BRAND HEALTH COMPOSITE: [HEALTHY / STABLE / DECLINING / MIXED]

Strengths:
- [specific data-backed positive, e.g., "Volume growth of +3.8% MoM driven by SUV segment"]
- [second positive]

Areas of Concern:
- [specific data-backed concern, e.g., "MSRP position deteriorated 290 bps — deepening discounts signal weakening demand"]
- [second concern]

Competitive Watch:
- [e.g., "Honda gained 45 bps in your core SUV segment — monitor CR-V pricing"]
- [second competitive signal]

Recommended Actions:
- [e.g., "Consider incentive support for [Model] where DOM is rising in [State]"]
- [e.g., "Increase allocation to [State] where demand exceeds supply"]
```

## Composite Health Logic

For the composite assessment:
- **HEALTHY:** 4+ of 6 operational KPIs are HEALTHY/STRONG/GAINING, no DECLINING signals
- **DECLINING:** 4+ are DECLINING/ERODING/LOSING, volume AND pricing both negative
- **MIXED:** Conflicting signals (volume up but pricing down, or vice versa)
- **STABLE:** Most indicators steady, no strong directional signal

## Multi-Brand Comparison

If the user asks "compare my brand vs Honda" or "competitive deep dive":

1. Run the full workflow for your brand AND each competitor
2. Present a side-by-side comparison table:
   ```
   Metric              | Your Brand | Honda      | Advantage
   --------------------|------------|------------|----------
   Volume MoM          | +3.8%      | +1.2%      | You
   Pricing Power       | -0.9%      | +0.3%      | Honda
   Days Supply         | 72         | 58         | Honda
   Market Share Change  | +30 bps    | -15 bps    | You
   EV Penetration      | 4.2%       | 6.1%       | Honda
   ```
3. Deliver strategic insight: "You have stronger volume momentum but Honda has better inventory discipline. Their lower days supply suggests more efficient allocation — review your production planning for [segment]."

## Important Notes

- This skill is **US-only**. All data comes from `get_sold_summary` and `search_active_cars` which require US market data.
- Date ranges should use the most recent COMPLETE month. If today is March 5, use February as "current month."
- If a make has very low volume (< 100 units/month nationally), note low sample size and reduce confidence.
- Always frame your brand metrics as operational KPIs and competitor metrics as competitive threats.
- Always cite the actual numbers, not just status labels. Brand managers need specifics to act on.
