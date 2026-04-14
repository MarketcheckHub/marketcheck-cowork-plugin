---
name: earnings-preview
description: >
  Pre-earnings channel check for auto equities. Triggers: "earnings preview",
  "pre-earnings check", "channel check", "what will Ford report",
  "earnings risk signal", "quarterly preview", "earnings estimate check",
  "what should I expect from [ticker] earnings",
  structured pre-earnings channel check synthesizing multiple
  data dimensions into bull/bear scenarios with confidence levels.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# Earnings Preview — Pre-Earnings Channel Check for Automotive Equities

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for ticker and geography. US-only. Confirm profile.

## User Context

Financial analyst preparing for earnings season. This is a SYNTHESIS skill — it pulls DOM, discount rates, inventory levels, sales velocity, EV sell-through, and new/used mix into a single unified pre-earnings risk assessment with explicit bull/bear scenarios and signal strength. This is the plugin's highest-value use case: "Ford reports next week, what's the channel data showing?"

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

## `get_sold_summary` Parameter Best Practices

> **CRITICAL — read before calling `get_sold_summary`:**
>
> Each response row is a unique **(month × state/city × ranking_dimension_combo)** tuple. Row count = (months in range) × (geographic groups from `summary_by`) × (unique combos of `ranking_dimensions`, capped by `top_n`). The `limit` parameter caps **rows returned**, not vehicles — truncation silently drops entire vehicle groups.
>
> | `ranking_dimensions` value | Typical unique combos | ×50 states ×3 months | Fits limit=1000? |
> |---|---|---|---|
> | `dealership_group_name` | 1 (filtered) | ~150 | Yes |
> | `make` | ~40 | ~6,000 | **No** |
> | `make,body_type` | ~200 | ~30,000 | **No** |
> | `make,model,body_type` (DEFAULT) | ~1,000+ | ~150,000 | **No — catastrophic** |
>
> **Rules for every `get_sold_summary` call in this skill:**
> 1. **Always set `inventory_type` explicitly** — backend defaults to `New` when omitted; used-car dealers (KMX, CVNA) return **zero results** silently
> 2. **Always set `limit: 5000`** to avoid silent truncation
> 3. **Always set `summary_by` explicitly** (or omit to avoid state-level row multiplication)
> 4. **For total volume**: use `ranking_dimensions: dealership_group_name` (1 combo → no truncation)
> 5. **For breakdowns**: use a separate call with the needed dimension + `limit: 5000`

## Workflow: Pre-Earnings Channel Check

### Step 1 — Resolve entity and determine quarter

Map ticker to makes **or dealer group name**. Determine the quarter under review: most recent complete quarter. Define:
- **Current quarter:** 3 months ending with the most recent complete month
- **Prior quarter:** the 3 months before that
- **Year-ago quarter:** same quarter last year (if available)

Determine **entity type**:
- **OEM ticker** (F, GM, TM, HMC, STLA, TSLA, RIVN, LCID, HYMTF, NSANY, MBGAF, BMWYY, VWAGY): filter by `make`
- **Dealer group ticker** (AN, LAD, PAG, SAH, GPI, ABG, KMX, CVNA): filter by `dealership_group_name`

For dealer groups, also determine **inventory focus**:
- **Used-only groups** (KMX, CVNA): always use `inventory_type: Used`
- **Franchise groups** (AN, LAD, PAG, SAH, GPI, ABG): query New and Used separately

Confirm: "Pre-Earnings Channel Check: **[Ticker]** ([Company]) — [Quarter] Earnings"

### Step 2 — Volume momentum (REVENUE SIGNAL)

#### For OEM tickers:

For EACH make in the ticker's mapping, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the make
- `inventory_type`: `New`
- `state`: from profile (or omit for national)
- `date_from` / `date_to`: current quarter
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 1
- `limit`: 5000
- `summary_by`: `state`

Repeat for prior quarter.
→ **Extract only**: `sold_count` per make per period. Discard full response.

Sum to ticker level.

#### For dealer group tickers:

Call `mcp__marketcheck__get_sold_summary` with:
- `dealership_group_name`: the group name (e.g., `Carmax`, `AutoNation Inc.`)
- `inventory_type`: `Used` (for KMX, CVNA) or call twice for New + Used (for franchise groups)
- `date_from` / `date_to`: current quarter
- `ranking_dimensions`: `dealership_group_name`
- `ranking_measure`: `sold_count`
- `top_n`: 1
- `limit`: 5000
- `summary_by`: `state`

→ **Sum `sold_count` across ALL returned rows** for the true total volume. Each row is one (month × state) — you must sum them all.

Repeat for prior quarter and year-ago quarter.

Then, for **make breakdown** (separate call):
- `dealership_group_name`: the group name
- `inventory_type`: `Used` (for KMX, CVNA)
- `date_from` / `date_to`: current quarter
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `ranking_order`: `desc`
- `top_n`: 15
- `limit`: 5000
- `summary_by`: `state`

→ **Extract**: top makes by volume for mix analysis. Do NOT use this call for total volume — it may truncate.

Calculate:
- **QoQ Volume Change %** = (current_q - prior_q) / prior_q × 100
- **Signal:** BULLISH if QoQ > +3%; BEARISH if QoQ < -3%; NEUTRAL if within ±3%

### Step 3 — Pricing/discount trend (MARGIN SIGNAL)

#### For OEM tickers:

For each make, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the make
- `inventory_type`: `New`
- `date_from` / `date_to`: last month of current quarter
- `ranking_dimensions`: `make`
- `ranking_measure`: `price_over_msrp_percentage`
- `top_n`: 1
- `limit`: 5000

Repeat for last month of prior quarter.
→ **Extract only**: `price_over_msrp_percentage` per make per period. Discard full response.

#### For dealer group tickers:

**Skip MSRP analysis for used-only groups (KMX, CVNA)** — `price_over_msrp_percentage` is not meaningful for used vehicles.

For franchise groups (AN, LAD, PAG, SAH, GPI, ABG), call with:
- `dealership_group_name`: the group name
- `inventory_type`: `New`
- `date_from` / `date_to`: last month of current quarter
- `ranking_dimensions`: `dealership_group_name`
- `ranking_measure`: `price_over_msrp_percentage`
- `top_n`: 1
- `limit`: 5000

Instead, for used-only groups, use **ASP trend** as the margin signal:
- Compare `average_sale_price` from Step 2 current vs prior quarter
- **Signal:** BULLISH if ASP rising (gross profit expansion); BEARISH if ASP falling >3%; NEUTRAL if stable

Calculate:
- **Discount Rate Change (bps):** QoQ change in price_over_msrp_percentage × 100
- **Signal:** BULLISH if discount narrowing >30 bps; BEARISH if widening >30 bps; NEUTRAL if stable

### Step 4 — Inventory health (BALANCE SHEET SIGNAL)

#### For OEM tickers:

Call `mcp__marketcheck__search_active_cars` with:
- `make`: each make
- `seller_state`: from profile
- `car_type`: `new`
- `stats`: `price,dom`
- `rows`: 0

→ **Extract only**: `num_found`, `stats.dom.mean`. Discard full response.

Call `mcp__marketcheck__get_sold_summary` for same make/state for the most recent month with:
- `inventory_type`: `New`
- `limit`: 5000
→ **Extract only**: `sold_count`. Discard full response.

#### For dealer group tickers:

Call `mcp__marketcheck__search_active_cars` with:
- `mc_dealership_group_name`: the group name
- `car_type`: `used` (for KMX, CVNA) or both `new` and `used` (for franchise groups)
- `stats`: `price,dom`
- `rows`: 0

→ **Extract only**: `num_found`, `stats.dom.mean`. Discard full response.

Use sold volume from Step 2 (most recent month's rows only) for days supply calculation.

Calculate:
- **Days Supply** = (num_found / sold_count) × 30
- **Signal:** BULLISH if < 45 days (tight supply); NEUTRAL if 45–75 days; BEARISH if > 75 days

### Step 5 — DOM velocity (DEMAND SIGNAL)

From sold data in Steps 2/3, extract `average_days_on_market` for current and prior quarter.

Calculate:
- **DOM Change %** = (current_dom - prior_dom) / prior_dom × 100
- **Signal:** BULLISH if DOM declining (selling faster); BEARISH if DOM rising >10%; NEUTRAL if stable

### Step 6 — EV sell-through (if applicable)

Skip for non-EV OEMs (if EV makes <1% of portfolio). For EV pure-plays (TSLA, RIVN, LCID), this IS the volume analysis — skip and use Step 2 data.

For legacy OEMs with EV models, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the OEM's makes
- `inventory_type`: `New`
- `fuel_type_category`: `EV`
- `date_from` / `date_to`: current quarter
- `ranking_dimensions`: `make`
- `top_n`: 1
- `limit`: 5000
→ **Extract only**: `sold_count`, `average_sale_price` per period. Discard full response.

Repeat for prior quarter.

For **dealer group tickers**, call with:
- `dealership_group_name`: the group name
- `inventory_type`: `Used`
- `fuel_type_category`: `EV`
- `date_from` / `date_to`: current quarter
- `ranking_dimensions`: `dealership_group_name`
- `top_n`: 1
- `limit`: 5000

Calculate:
- **EV % of total OEM/group sales**
- **EV volume QoQ change %**
- **Signal:** BULLISH if EV share growing >50 bps/quarter; BEARISH if EV DOM >90 days; NEUTRAL if stable

### Step 7 — New/used mix (CONSUMER HEALTH SIGNAL)

**For OEM tickers:**

Call `mcp__marketcheck__get_sold_summary` with:
- `make`: the OEM's makes
- `inventory_type`: `New`
- `date_from` / `date_to`: current quarter
- `ranking_dimensions`: `make`
- `top_n`: 1
- `limit`: 5000
→ Extract `sold_count` for new.

Repeat with `inventory_type`: `Used`.
→ Extract `sold_count` for used.

**For dealer group tickers:**

Call `mcp__marketcheck__get_sold_summary` with:
- `dealership_group_name`: the group name
- `inventory_type`: `New`
- `date_from` / `date_to`: current quarter
- `ranking_dimensions`: `dealership_group_name`
- `top_n`: 1
- `limit`: 5000
→ Extract `sold_count` for new.

Repeat with `inventory_type`: `Used`.
→ Extract `sold_count` for used.

**For used-only groups (KMX, CVNA):** Skip this step — they have zero New inventory. Note "100% Used" in the output.

Calculate:
- **New % of total** = new_sold / (new_sold + used_sold) × 100
- **QoQ shift** in new% vs prior quarter
- **Signal:** BULLISH for OEM if new-car share rising (consumer confidence); BEARISH if falling (trade-down signal)

### Step 8 — Synthesize Bull/Bear Scenarios

Compile all 6 dimensions (7 if EV applicable):

```
Dimension              | Data Point        | Signal
-----------------------|-------------------|----------
Volume Momentum        | QoQ: +X.X%        | [SIGNAL]
Pricing Power          | MSRP %: X.X%      | [SIGNAL]
Inventory Health       | X days supply      | [SIGNAL]
DOM Velocity           | X days, QoQ +X%   | [SIGNAL]
EV Sell-Through        | X% of total        | [SIGNAL]
New/Used Mix           | New: X%, shift Xbps| [SIGNAL]
```

**Bull Case:** List the conditions from data that support an earnings beat. Example: "Volume up QoQ, pricing power intact (above MSRP), tight days supply — suggests revenue and margin upside."

**Bear Case:** List the conditions that support an earnings miss. Example: "DOM rising, discount rate widening, inventory building — suggests demand softening and margin pressure."

**Signal Strength:**
- **Strong:** 5+ of 6 dimensions aligned in same direction
- **Moderate:** 3–4 dimensions aligned, 1–2 mixed
- **Weak:** No clear directional lean, mixed signals

**Composite Signal:**
| Composite Signal | Criteria |
|------------------|----------|
| BULLISH | 5+ dimensions positive, no BEARISH on volume or pricing |
| CAUTIOUSLY BULLISH | 4 positive, 1–2 mixed |
| NEUTRAL | Mixed signals, no strong directional lean |
| CAUTIOUSLY BEARISH | 4 negative, 1–2 mixed |
| BEARISH | 5+ negative, especially volume AND pricing both negative |

## Output

Present: ticker/company/quarter header, 6-dimension data table with signals, bull case narrative, bear case narrative, signal strength rating, composite signal, key watch items for the earnings call. Format as a structured pre-earnings briefing that can be shared with a portfolio manager.

## Important Notes

- This skill is **US-only**.
- Date ranges use COMPLETE quarters. If in March 2026, the "current quarter" is Q4 2025 (Oct-Dec).
- This is a synthesis skill — it intentionally overlaps with other skills (pricing-power-tracker, dom-monitor, etc.) but combines their outputs into a unified thesis.
- For dealer group tickers (AN, KMX, CVNA), emphasize inventory turns, used vehicle mix, and DOM over MSRP metrics.
- Always present BOTH bull and bear cases, even when the signal is strongly directional. Analysts need to evaluate both sides.
- Signal strength should be explicit: "Strong BEARISH (5 of 6 negative)" or "Moderate BULLISH (4 of 6 positive, volume and pricing both up)."
- Always cite actual numbers. Always map to tickers.
