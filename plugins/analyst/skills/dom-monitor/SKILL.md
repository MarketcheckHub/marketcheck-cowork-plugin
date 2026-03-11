---
name: dom-monitor
description: >
  This skill should be used when the user asks about "days on market",
  "DOM trends", "inventory aging", "sell-through velocity", "demand distress",
  "which brands are sitting longest", "DOM signal", "DOM inflection",
  "what's sitting on lots", "demand softening signal",
  or needs a dedicated days-on-market analysis as a PRIMARY leading indicator
  for investment decisions rather than as a secondary metric.
version: 0.1.0
---

# DOM Monitor — Days on Market as a Leading Investment Signal

## User Profile (Load First)

Load `~/.claude/marketcheck/analyst-profile.json` if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for OEM/ticker and geography. US-only. Confirm profile.

## User Context

Financial analyst needing DOM as a primary analytical dimension — not a secondary metric buried inside other analyses. Days on market is the single most predictive metric for earnings direction in recent cycles: Ford's DOM rose 54% Q3→Q4 2025 preceding a 32% earnings miss; Stellantis's DOM fell 14% Q2→Q4 signaling a turnaround. This skill provides dedicated DOM tracking with rate-of-change calculations, inflection point detection, and distress flagging.

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

## Workflow 1: DOM Ranking by OEM

Use when user asks "which brands are sitting longest" or "DOM ranking across OEMs."

### Step 1 — Pull current DOM data

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile or user input (or omit for national)
- `date_from` / `date_to`: most recent complete month
- `ranking_dimensions`: `make`
- `ranking_measure`: `average_days_on_market`
- `ranking_order`: `desc` (longest first)
- `top_n`: 25

→ **Extract only**: `make`, `average_days_on_market`, `sold_count` per make. Discard full response.

### Step 2 — Aggregate to ticker level

Map makes to tickers. For multi-make tickers, calculate weighted average DOM (weighted by sold_count). Rank tickers by DOM.

### Step 3 — Signal assignment per ticker

| Signal | Threshold |
|--------|-----------|
| BULLISH | Avg DOM < 30 days (hot seller, pricing power intact) |
| NEUTRAL | Avg DOM 30–60 days (healthy range) |
| CAUTION | Avg DOM 60–90 days (aging, incentives likely) |
| BEARISH | Avg DOM > 90 days (distress, production cuts likely) |

## Workflow 2: DOM Trend (Multi-Period with Rate-of-Change)

Use when user asks "DOM trend for Ford" or "is demand softening for Toyota."

### Step 1 — Pull 5-period DOM data

For EACH period (current, 1mo, 2mo, 3mo, 6mo), call `mcp__marketcheck__get_sold_summary` with:
- `make`: each make in the target ticker's mapping
- `state`: from profile
- `date_from` / `date_to`: the period's date range
- `ranking_dimensions`: `make`
- `ranking_measure`: `average_days_on_market`
- `top_n`: 1

→ **Extract only**: `average_days_on_market`, `sold_count` per make per period. Discard full response.

### Step 2 — Calculate rate-of-change

- **DOM at each period:** Weighted average across ticker's makes
- **MoM DOM Change:** current_dom - prior_dom (days)
- **MoM DOM Change %:** (current - prior) / prior × 100
- **3-Month Acceleration:** Compare MoM change at period 1 vs period 3 — is the rate of change itself increasing?
- **6-Month Trajectory:** Direction from Period 5 → Period 1

### Step 3 — Inflection detection

Flag if DOM trajectory changes direction (declining → rising, or rising → declining) within the 5-period window. An inflection from declining to rising is a CAUTION signal — it means demand was improving but is now softening.

### Step 4 — Signal assignment

| Signal | Threshold |
|--------|-----------|
| BULLISH | DOM declining >5 days/month (accelerating sell-through) |
| NEUTRAL | DOM stable within ±2 days/month |
| CAUTION | DOM rising 2–5 days/month OR inflection from declining to rising |
| BEARISH | DOM rising >5 days/month (sustained demand deterioration) |

## Workflow 3: Segment Velocity Comparison

Use when user asks "which vehicle segments have slowing velocity" or "SUV vs truck DOM."

### Step 1 — Pull segment-level DOM

For each major body type (SUV, Pickup, Sedan, Hatchback), call `mcp__marketcheck__get_sold_summary` with:
- `state`: from profile
- `body_type`: the segment
- `date_from` / `date_to`: current month
- `ranking_dimensions`: `make`
- `ranking_measure`: `average_days_on_market`
- `ranking_order`: `desc`
- `top_n`: 15

→ **Extract only**: `make`, `average_days_on_market`, `sold_count` per make per segment. Discard full response.

Repeat for prior month.

### Step 2 — Cross-segment comparison

Map makes to tickers. For each segment, calculate:
- Segment average DOM (all makes)
- Ticker's DOM within segment vs segment average
- MoM change per ticker per segment

### Step 3 — Identify most-exposed tickers

Flag tickers with above-average DOM in high-volume segments (SUV, Pickup). These tickers face the most margin pressure from aging inventory.

## Workflow 4: DOM Inflection Point Flagging

Use when user asks "DOM distress signals" or "which OEMs are crossing danger thresholds."

### Step 1 — Pull active inventory DOM

Call `mcp__marketcheck__search_active_cars` with:
- `make`: each make in target ticker(s)
- `seller_state`: from profile
- `stats`: `dom`
- `rows`: 0

→ **Extract only**: `num_found`, `stats.dom.mean`, `stats.dom.min`, `stats.dom.max`. Discard full response.

### Step 2 — Threshold check

Flag makes crossing these thresholds:
- **>60 days active DOM:** CAUTION — aging inventory, expect discounts
- **>90 days active DOM:** BEARISH — demand distress, incentive costs rising
- **>120 days active DOM:** BEARISH SEVERE — production cut signal, channel stuffing risk

### Step 3 — Compare active vs sold DOM

Active DOM (from Step 1) vs Sold DOM (from Workflow 2) reveals the demand velocity gap:
- If active DOM >> sold DOM: inventory is building faster than it's selling = BEARISH
- If active DOM ≈ sold DOM: healthy flow-through = NEUTRAL
- If active DOM << sold DOM: tight supply, undersupply premium = BULLISH

## Output

Present: DOM ranking table by ticker with signal, 5-period trend table with rate-of-change and trajectory, segment velocity comparison, inflection alerts, active vs sold DOM gap. Every metric includes signal with rationale. Connect DOM trends to earnings implications: rising DOM → incentive spend → margin compression → earnings headwind.

## Important Notes

- This skill is **US-only**.
- Date ranges use the most recent COMPLETE month.
- DOM is the PRIMARY metric in this skill — do not dilute with pricing or volume analysis. Those are covered by other skills.
- For EV pure-plays (TSLA, RIVN, LCID), DOM is especially important as it reveals whether demand is keeping pace with production ramp.
- Low volume makes (<100 units/month) should be flagged with reduced confidence.
- Always cite actual numbers. Always map to tickers.
- Differentiation from existing skills: DOM appears as a secondary metric in `oem-stock-tracker` (Step 6) and `dealer-group-health-monitor`. This skill makes DOM the sole analytical dimension with dedicated rate-of-change tracking, inflection detection, and distress threshold flagging.
