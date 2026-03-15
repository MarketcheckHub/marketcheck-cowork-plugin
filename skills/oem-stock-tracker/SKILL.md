---
name: oem-stock-tracker
description: >
  This skill should be used when the user asks about "OEM stock signal",
  "how is Ford doing", "Toyota demand trends", "brand health check",
  "investment signal for [OEM]", "pricing power analysis", "days supply",
  "OEM market share trends", "brand volume momentum", "inventory build",
  or needs help tracking leading indicators for publicly traded automotive
  OEMs and dealer groups to support investment decisions.
version: 0.1.0
---

# OEM Stock Tracker — Leading Indicators for Automotive Investment Decisions

## User Profile (Load First)

Before running any workflow, check for a saved user profile:

1. Read the `marketcheck-profile.md` project memory file.
2. If the file **does not exist**: This skill works without a profile. Ask for: "Which OEM or ticker do you want to analyze?" and "Which state(s) or 'national'?"
3. If the file **exists**, extract silently:
   - `user_type` — if `analyst`, use `analyst.tracked_tickers`, `analyst.tracked_states`, `analyst.benchmark_period_months`
   - `country` ← `location.country` (this skill is **US-only** — requires `get_sold_summary`)
   - `state` ← `location.state` or `analyst.tracked_states`
4. **Country check:** If `country=UK`, inform the user: "OEM investment signals require US sold transaction data. This skill is not available for UK market." Stop.
5. If profile exists, confirm briefly: "Using profile: **[user.name]** ([user_type]), tracking [tickers]"

## User Context

The primary user is a **financial analyst** (equity researcher, hedge fund analyst, or portfolio manager) who needs leading indicators to inform investment decisions on publicly traded automotive entities. The secondary user is an **OEM regional manager** or **dealer group strategist** monitoring brand health.

This skill produces **actionable investment signals** — not just data. Each metric includes an explicit BULLISH / BEARISH / NEUTRAL / CAUTION signal with a brief rationale.

## Built-in Ticker → Makes Mapping

```
OEM TICKERS:
F     → Ford, Lincoln
GM    → Chevrolet, GMC, Buick, Cadillac
TM    → Toyota, Lexus
HMC   → Honda, Acura
STLA  → Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati
TSLA  → Tesla
RIVN  → Rivian
LCID  → Lucid
HYMTF → Hyundai, Kia, Genesis
NSANY → Nissan, Infiniti
MBGAF → Mercedes-Benz
BMWYY → BMW, MINI, Rolls-Royce
VWAGY → Volkswagen, Audi, Porsche, Lamborghini, Bentley

DEALER GROUP TICKERS:
AN    → AutoNation
LAD   → Lithia Motors
PAG   → Penske Automotive
SAH   → Sonic Automotive
GPI   → Group 1 Automotive
ABG   → Asbury Automotive
KMX   → CarMax
CVNA  → Carvana
```

If the user provides a ticker, map it to makes using this table. If the user provides a make name (e.g., "Ford"), reverse-map to the ticker. For dealer group tickers, redirect to the `dealer-group-health-monitor` skill.

## Workflow: OEM Investment Signal

Use this when a user asks "How is Ford doing?" or "Investment signal for GM" or "Toyota demand trends."

### Step 1 — Resolve the entity

Map the user's input (ticker or brand name) to the list of makes using the built-in mapping. Confirm: "Analyzing **[Ticker]** ([Company Name]): [Make1, Make2, ...]"

Determine date ranges:
- **Current month:** first day of the most recent complete month → last day
- **Prior month:** the month before current
- **Baseline (3 months ago):** from `analyst.benchmark_period_months` or default 3

### Step 2 — Volume momentum

For EACH make in the ticker's mapping, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the make
- `state`: from profile or user input (or omit for national)
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 1

Repeat for prior month and 3-month-ago period.

Sum sold_count across all makes for the ticker.

Calculate:
- **MoM Volume Change %** = (current - prior) / prior × 100
- **3-Month Trend %** = (current - 3mo_ago) / 3mo_ago × 100
- **Signal:** BULLISH if MoM > +3% AND 3mo > +5%; BEARISH if MoM < -3% AND 3mo < -5%; NEUTRAL if mixed; CAUTION if MoM positive but 3mo negative (short-term bounce)

### Step 3 — Pricing power

For each make, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the make
- `state`: from profile or user input
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `average_sale_price`
- `top_n`: 1

Repeat for prior month.

Also call for new vehicles specifically to get MSRP positioning:
- `inventory_type`: `New`
- `ranking_measure`: `price_over_msrp_percentage`

Calculate:
- **Avg Sale Price Change %** = MoM change in average_sale_price
- **Price vs MSRP %** = price_over_msrp_percentage (positive = above sticker, negative = discounting)
- **MSRP Trend (bps)** = (current MSRP % - prior MSRP %) × 100
- **Signal:** BULLISH if price rising AND above MSRP; BEARISH if price falling AND below MSRP (deepening discounts); CAUTION if price stable but MSRP shifting negative

### Step 4 — Inventory health (Days Supply)

Call `mcp__marketcheck__search_active_cars` with:
- `make`: each make
- `state` (via `seller_state`) or national
- `car_type`: `new`
- `stats`: `price,dom`
- `rows`: 0

This gives total active NEW inventory count and average DOM.

Call `mcp__marketcheck__get_sold_summary` for the same make/state/period to get monthly sold volume.

Calculate:
- **Days Supply** = (Active Inventory Count / Monthly Sold Count) × 30
- **Signal:** BULLISH if < 45 days (tight supply, pricing power); NEUTRAL if 45-75 days; BEARISH if > 75 days (building inventory, production cuts likely); CAUTION if rising rapidly (>15% MoM increase)

### Step 5 — Market share

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile or user input
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 25

Repeat for prior month.

Calculate the OEM's aggregate share across its makes:
- **Current Share %** = sum of OEM's makes sold / total sold × 100
- **Prior Share %** = same for prior month
- **Share Change (bps)** = (current - prior) × 100
- **Signal:** BULLISH if gaining > +30 bps; BEARISH if losing > -30 bps; NEUTRAL if within ±30 bps

### Step 6 — DOM trend (demand softness)

From the sold data in Step 2/3, extract `average_days_on_market` for each period.

Calculate:
- **DOM MoM Change %** = (current_dom - prior_dom) / prior_dom × 100
- **Signal:** BULLISH if DOM falling (selling faster); BEARISH if DOM rising > 10% (demand softening); NEUTRAL if stable

### Step 7 — EV transition (if applicable)

If the OEM sells EVs (Tesla, Rivian, Lucid, or legacy OEMs with EV models):

Call `mcp__marketcheck__get_sold_summary` with:
- `make`: the OEM's makes
- `fuel_type_category`: `EV`
- Current and prior periods

Calculate:
- **EV % of OEM's total sales** = EV sold / total OEM sold × 100
- **EV MoM change (bps)** = trend direction
- **EV avg price** and MoM change

For EV pure-plays (TSLA, RIVN, LCID), this IS the entire analysis. For legacy OEMs, it shows transition progress.

### Step 8 — Segment mix

Call `mcp__marketcheck__get_sold_summary` with:
- `make`: each of the OEM's makes
- `ranking_dimensions`: `body_type`
- `ranking_measure`: `sold_count`
- Current period

Calculate share by segment (Pickup, SUV, Sedan, EV, etc.) and pricing trend per segment.

## Output

```
OEM INVESTMENT SIGNAL — [Company Name] ([Ticker])
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: [State or National] | Period: [Current Month] vs [Prior Month] vs [3mo Ago]
Makes: [Make1, Make2, ...]

LEADING INDICATORS
Metric                | Current    | Prior Mo   | 3mo Ago    | Trend       | Signal
----------------------|------------|------------|------------|-------------|--------
Volume (sold units)   | XXX,XXX    | XXX,XXX    | XXX,XXX    | +X.X% MoM  | BULLISH
Avg Sale Price        | $XX,XXX    | $XX,XXX    | $XX,XXX    | +X.X% MoM  | NEUTRAL
Price vs MSRP (new)   | +X.X%      | +X.X%      | +X.X%      | ↓ XXX bps   | BEARISH
Days Supply (new)     | XX days    | XX days    | XX days    | +X.X%       | CAUTION
Market Share          | XX.X%      | XX.X%      | XX.X%      | +XX bps     | BULLISH
Avg DOM               | XX days    | XX days    | XX days    | +X.X%       | NEUTRAL

[If OEM has EV sales:]
EV TRANSITION
EV % of Sales         | X.X%       | X.X%       | X.X%       | +XX bps     | Growing/Stalled
EV Avg Price          | $XX,XXX    | $XX,XXX    | $XX,XXX    | -X.X%       | Compressing/Stable
EV Days Supply        | XX days    | XX days    |            |             |

SEGMENT MIX (by volume)
Segment   | Share   | MoM Trend | Pricing Trend | Signal
----------|---------|-----------|---------------|--------
Pickup    | XX%     | stable    | -X.X%         | NEUTRAL
SUV       | XX%     | +X%       | -X.X%         | CAUTION
Sedan     | XX%     | -X%       | flat          | NEUTRAL
EV        | X.X%    | +XX%      | -X.X%         | BULLISH

COMPOSITE INVESTMENT THESIS: [BULLISH / BEARISH / MIXED / NEUTRAL]

Positive factors:
- [specific data-backed positive signal, e.g., "Volume growth of +3.8% MoM driven by SUV segment"]
- [second positive]

Negative factors:
- [specific data-backed negative signal, e.g., "MSRP position deteriorated 290 bps — deepening discounts signal weakening demand"]
- [second negative]

Key watchpoints:
- [forward-looking signal, e.g., "If days supply exceeds 80 next month, expect production cut announcement"]
- [second watchpoint]
```

## Signal Classification Logic

For the composite thesis:
- **BULLISH:** 4+ of 6 leading indicators are BULLISH, none are BEARISH
- **BEARISH:** 4+ are BEARISH or CAUTION, volume AND pricing power both negative
- **MIXED:** Conflicting signals (volume up but pricing down, or vice versa)
- **NEUTRAL:** Most indicators stable, no strong directional signal

Always provide the specific data that drives each signal — analysts need to verify the reasoning, not just the conclusion.

## Multi-OEM Comparison

If the user asks "compare Ford vs GM" or "which OEM is winning":

1. Run the full workflow for each OEM
2. Present a side-by-side comparison table:
   ```
   Metric              | Ford (F) | GM (GM) | Advantage
   --------------------|----------|---------|----------
   Volume MoM          | +3.8%    | +1.2%   | Ford
   Pricing Power       | -0.9%    | +0.3%   | GM
   Days Supply         | 72       | 58      | GM
   Market Share Change  | +30 bps  | -15 bps | Ford
   EV Penetration      | 4.2%     | 6.1%    | GM
   ```
3. Deliver a relative thesis: "Ford has stronger volume momentum but GM has better inventory discipline and faster EV adoption."

## Important Notes

- This skill is **US-only**. All data comes from `get_sold_summary` and `search_active_cars` which require US market data.
- Date ranges should use the most recent COMPLETE month. If today is March 5, use February as "current month."
- If a make has very low volume (< 100 units/month nationally), note low sample size and reduce confidence.
- For EV pure-plays (TSLA, RIVN, LCID), skip the EV Transition section (all their sales are EV) and instead focus on total volume, pricing, and DOM.
- Always cite the actual numbers, not just signals. An analyst needs to cross-reference against their own models.
