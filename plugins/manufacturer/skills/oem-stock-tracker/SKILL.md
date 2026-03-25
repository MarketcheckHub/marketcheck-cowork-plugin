---
name: oem-stock-tracker
description: >
  Brand health and competitive threat monitoring. Triggers: "brand health check",
  "how is my brand doing", "brand performance dashboard", "pricing power analysis",
  "days supply", "brand volume momentum", "inventory build",
  "operational KPIs", "brand health metrics", "self-monitoring",
  "brand demand trends", "competitive threat assessment",
  tracking brand health indicators and operational KPIs
  for OEM brands and monitoring competitive threats.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# OEM Stock Tracker — Brand Health Check & Competitive Threat Monitor

## Manufacturer Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `brands` (operational KPIs), `states`, `competitor_brands` (competitive threats), `country`, `user_name`, `company`. If missing, ask brand, states, and competitors. US-only; if UK, inform not available and stop. Confirm profile.

## User Context

User is an OEM regional manager, brand strategist, or distributor self-monitoring brand health and tracking competitive threats. Frame your-brand metrics as OPERATIONAL KPIs; competitor metrics as COMPETITIVE THREATS.

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
-> **Extract only**: `sold_count`, `average_days_on_market` per make per period. Discard full response.

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
-> **Extract only**: `average_sale_price` per make per period. Discard full response.

Also call for new vehicles specifically:
- `inventory_type`: `New`
- `ranking_measure`: `price_over_msrp_percentage`
-> **Extract only**: `price_over_msrp_percentage` per make per period. Discard full response.

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
-> **Extract only**: `num_found`, `stats.dom.mean` per make. Discard full response.

Call `mcp__marketcheck__get_sold_summary` for the same make/state/period to get monthly sold volume.
-> **Extract only**: `sold_count` per make. Discard full response.

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
-> **Extract only**: `make`, `sold_count` per brand per period, plus `total_sold_count`. Discard full response.

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
-> **Extract only**: `sold_count`, `average_sale_price` per make per period. Discard full response.

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
-> **Extract only**: `body_type`, `sold_count`, `average_sale_price` per segment. Discard full response.

Calculate share by segment (Pickup, SUV, Sedan, EV, etc.) and pricing trend per segment.

## Output

Present: operational KPI table (volume, price, MSRP position, days supply, share, DOM with status labels), competitive threat monitor table, EV progress (if applicable), segment mix, composite health signal (HEALTHY/STABLE/DECLINING/MIXED), and actionable recommendations citing specific data.

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
