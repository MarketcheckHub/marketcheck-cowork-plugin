---
name: new-used-mix-analyzer
description: >
  This skill should be used when the user asks about "new vs used mix",
  "consumer trade-down", "CPO volume", "new car share", "used car shift",
  "inventory type mix", "are consumers trading down", "new used split",
  "certified pre-owned trends", "used vehicle share",
  or needs to analyze the new vs used vehicle mix as a signal for consumer
  health, OEM channel dynamics, and dealer group margin analysis.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# New/Used Mix Analyzer — Inventory Type Shifts as Consumer & Market Signals

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for focus area and geography. US-only. Confirm profile.

## User Context

Financial analyst needing new vs used vehicle mix analysis as a multi-faceted signal: (1) for OEM tickers — declining new-car share signals consumer trade-down and potential revenue headwind; (2) for dealer group tickers — the new/used revenue split drives margin mix; (3) for macro — new/used ratio is a consumer confidence proxy. Most alternative auto data covers either new or used — MarketCheck covers both, a key differentiator.

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
KMX   → CarMax (used-only)
CVNA  → Carvana (used-only)
```

Note: KMX and CVNA are used-only retailers. Their "mix" is 100% used by definition. For these tickers, the skill instead analyzes the vehicle age/quality mix within used inventory (see Workflow 5).

## Workflow 1: OEM New/Used Split

Use when user asks "new vs used mix for Ford" or "is GM's new car share declining."

### Step 1 — Pull new vehicle sold data

For EACH make in the ticker's mapping, call `mcp__marketcheck__get_sold_summary` with:
- `make`: the make
- `state`: from profile (or omit for national)
- `inventory_type`: `New`
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 1

→ **Extract only**: `sold_count` per make. Discard full response.

### Step 2 — Pull used vehicle sold data

Repeat Step 1 with `inventory_type`: `Used`.
→ **Extract only**: `sold_count` per make. Discard full response.

### Step 3 — Repeat for prior periods

Repeat Steps 1–2 for prior month and 3-month-ago period.

### Step 4 — Calculate mix metrics

- **New %** = new_sold / (new_sold + used_sold) × 100
- **Used %** = 100 - New %
- **MoM Mix Shift (bps)** = (current_new_% - prior_new_%) × 100
- **3-Month Mix Trend (bps)** = (current_new_% - 3mo_new_%) × 100

### Step 5 — Signal assignment

| Signal | Investment Implication |
|--------|----------------------|
| BULLISH (for OEM) | New-car share rising >100 bps/quarter — consumer confidence, strong demand for new |
| NEUTRAL | Mix stable within ±50 bps |
| CAUTION | New-car share declining 50–150 bps — early trade-down signal |
| BEARISH (for OEM) | New-car share declining >150 bps — strong trade-down (BUT: BULLISH for KMX/CVNA) |

**Key nuance:** A BEARISH signal for OEM tickers simultaneously can be BULLISH for used-vehicle retailer tickers. Always present both perspectives.

## Workflow 2: CPO Volume Tracking

Use when user asks "CPO trends" or "certified pre-owned volume."

### Step 1 — Pull CPO inventory

Call `mcp__marketcheck__search_active_cars` with:
- `make`: each make in the ticker's mapping
- `seller_state`: from profile
- `car_type`: `certified`
- `stats`: `price,dom`
- `rows`: 0

→ **Extract only**: `num_found`, `stats.price.mean`, `stats.dom.mean`. Discard full response.

### Step 2 — Pull total used inventory

Repeat with `car_type`: `used`.

### Step 3 — Calculate CPO penetration

- **CPO % of Used** = CPO count / (CPO count + non-CPO used count) × 100
- **CPO Avg Price Premium** = CPO avg price - non-CPO used avg price
- **Signal:** Rising CPO % = BULLISH for franchise OEM tickers (dealer confidence in brand), falling = CAUTION

## Workflow 3: Consumer Trade-Down Signal (National)

Use when user asks "are consumers trading down" or "national new/used ratio."

### Step 1 — Pull national new vs used

Call `mcp__marketcheck__get_sold_summary` with:
- (no make filter — total market)
- `inventory_type`: `New`
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 25

→ **Extract only**: total `sold_count` across all makes. Discard full response.

Repeat with `inventory_type`: `Used`.

Repeat both for prior month and 3-month-ago period.

### Step 2 — Calculate national ratio trend

- **New/Used Ratio** = total_new_sold / total_used_sold
- **MoM change** in ratio
- **3-Month trend** direction
- **Signal:** Declining ratio = consumers shifting to used = macro stress signal; Rising ratio = confidence returning

## Workflow 4: Segment-Specific Mix

Use when user asks "new vs used in SUVs" or "pickup truck new/used split."

### Step 1 — Pull by body type

For target segment (SUV, Pickup, Sedan), call `mcp__marketcheck__get_sold_summary` with:
- `body_type`: the segment
- `state`: from profile
- `inventory_type`: `New`
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 15

→ **Extract only**: make, sold_count per make. Discard full response.

Repeat with `inventory_type`: `Used`.

### Step 2 — Identify segment-specific shifts

Which segments are seeing the strongest new→used shift? Map to tickers most exposed (e.g., if SUV mix shifting to used, BEARISH for SUV-heavy OEMs like F, GM).

## Workflow 5: Dealer Group New/Used Mix

Use when user asks "dealer group new/used split" or "compare AN vs LAD revenue mix."

### Step 1 — Pull by dealer group

For each target dealer group ticker, call `mcp__marketcheck__get_sold_summary` with:
- `dealership_group_name`: the group name
- `inventory_type`: `New`
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `sold_count`
- `top_n`: 15

→ **Extract only**: total sold_count. Discard full response.

Repeat with `inventory_type`: `Used`.

### Step 2 — Compare groups

Calculate new% and used% for each group. Compare:
- **Used-heavy groups** (KMX, CVNA): 100% used — analyze by vehicle age instead
- **Balanced groups** (AN, LAD, PAG): Track the new/used split trend — shifting toward used = margin mix change
- Higher used % generally means higher gross margin per unit but lower revenue per unit

## Output

Present: OEM new/used split table with trend and signal, CPO penetration data, national trade-down signal, segment-specific mix shifts, dealer group comparison. Every metric includes signal with dual perspective (OEM impact vs used-retailer impact). Connect mix shifts to revenue and margin implications.

## Important Notes

- This skill is **US-only**.
- Date ranges use the most recent COMPLETE month.
- KMX and CVNA are 100% used retailers — for these tickers, use Workflow 5 variant that analyzes WITHIN-used quality mix instead of new/used split.
- The `car_type` parameter in `search_active_cars` accepts: `new`, `used`, `certified`. The `inventory_type` in `get_sold_summary` accepts: `New`, `Used`.
- Always present the dual signal perspective: a decline in new-car share is BEARISH for OEM tickers but can be BULLISH for used-vehicle retailer tickers.
- Always cite actual numbers. Always map to tickers.
