---
name: sourcing-quality-signal
description: >
  This skill should be used when the user asks about "vehicle quality trends",
  "average mileage", "reconditioning signal", "sourcing quality",
  "used vehicle age", "inventory quality", "KMX sourcing", "CVNA inventory quality",
  "mileage trend", "reconditioning cost signal", "used car quality signal",
  or needs to track average mileage and vehicle age mix for used-vehicle retailers
  as a proxy for reconditioning costs and margin pressure.
version: 0.1.0
---

# Sourcing Quality Signal — Mileage & Vehicle Age Trends for Used-Vehicle Retailer Analysis

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `country`. If missing, ask for ticker and geography. US-only. Confirm profile.

## User Context

Financial analyst covering publicly traded used-vehicle retailers (KMX, CVNA) or dealer groups with significant used-vehicle operations (AN, LAD, PAG). Average mileage trends in sourced inventory serve as a direct proxy for reconditioning costs — the signal that predicted Carvana's Q4 2025 earnings miss (average mileage trending up ~10% through 2025, from ~48K to ~54K miles, signaling rising reconditioning costs months before the earnings report).

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

For this skill, dealer group tickers (KMX, CVNA, AN, LAD, etc.) are the primary focus. OEM tickers are secondary — used to analyze which brands the dealer groups are sourcing.

## Workflow 1: Dealer Group Mileage & Age Profile

Use when user asks "sourcing quality for CarMax" or "Carvana inventory age."

### Step 1 — Pull mileage stats

For each target dealer group, call `mcp__marketcheck__search_active_cars` with:
- `mc_dealership_group_name`: the dealer group name (e.g., "CarMax", "Carvana")
- `car_type`: `used`
- `stats`: `miles,price,dom`
- `rows`: 0

→ **Extract only**: `num_found`, `stats.miles.mean`, `stats.miles.min`, `stats.miles.max`, `stats.miles.stddev`, `stats.price.mean`, `stats.dom.mean`. Discard full response.

### Step 2 — Pull vehicle age mix

Call `mcp__marketcheck__search_active_cars` with:
- `mc_dealership_group_name`: the dealer group
- `car_type`: `used`
- `facets`: `year|0|10|1`
- `rows`: 0

→ **Extract only**: year facets with counts. Discard full response.

### Step 3 — Calculate age distribution

Group model years into bands:
- **0–2 year old** (current_year - 0 to 2): Premium, low recon cost
- **3–5 year old**: Core sweet spot, moderate recon
- **6–8 year old**: Higher recon, larger discount needed
- **8+ year old**: High recon, subprime segment

Calculate % of inventory in each band.

### Step 4 — Reconditioning Risk Score

Calculate: **Recon Risk Score = (avg_miles / 50,000) × 100**, capped at 100.

- Score 0–60: Low recon risk (younger, lower-mileage inventory)
- Score 60–80: Moderate recon risk
- Score 80–100: High recon risk (older, higher-mileage inventory)

### Step 5 — Signal assignment

| Signal | Threshold |
|--------|-----------|
| BULLISH | Avg miles < 35K AND >50% inventory 0–3yr old (premium sourcing, low recon) |
| NEUTRAL | Avg miles 35–55K, balanced age mix |
| CAUTION | Avg miles 55–75K OR age mix shifting older (recon costs rising) |
| BEARISH | Avg miles > 75K OR >40% inventory 6yr+ (margin headwind from recon) |

## Workflow 2: Dealer Group Peer Comparison

Use when user asks "Carvana vs CarMax sourcing" or "compare dealer group inventory quality."

### Step 1 — Run Workflow 1 for each dealer group

Pull mileage stats and age mix for both target groups (e.g., KMX and CVNA).

### Step 2 — Side-by-side comparison

Present:
```
Metric              | CarMax (KMX) | Carvana (CVNA) | Advantage
--------------------|-------------|----------------|----------
Avg Mileage         | 42,300      | 54,800         | KMX
% Inventory 0-3yr   | 38%         | 22%            | KMX
% Inventory 6yr+    | 18%         | 35%            | KMX
Recon Risk Score    | 62          | 84             | KMX
Avg List Price      | $24,500     | $19,800        | -
Avg DOM             | 45          | 62             | KMX
```

### Step 3 — Investment thesis

Translate sourcing quality differences into margin implications: higher mileage = higher reconditioning cost per unit = lower gross profit per vehicle = earnings headwind.

## Workflow 3: Make-Level Sourcing Profile

Use when user asks "what brands is Carvana sourcing" or "CarMax inventory make mix."

### Step 1 — Pull make distribution

Call `mcp__marketcheck__search_active_cars` with:
- `mc_dealership_group_name`: the dealer group
- `car_type`: `used`
- `facets`: `make|0|15|1`
- `stats`: `miles`
- `rows`: 0

→ **Extract only**: make facets with counts, overall stats.miles. Discard full response.

### Step 2 — Analyze make mix

Calculate: % of inventory by make, and cross-reference with which makes typically have lower/higher mileage and reconditioning costs. Premium brands (BMW, Mercedes) have higher recon costs even at same mileage. Volume brands (Toyota, Honda) have lower recon costs and better margin profiles.

## Output

Present: mileage statistics table by dealer group, vehicle age distribution chart data, reconditioning risk score with signal, make-level sourcing profile, peer comparison (if applicable). Every metric includes investment signal. Connect sourcing quality to per-unit economics: avg mileage → reconditioning cost → gross profit per unit → earnings impact.

## Important Notes

- This skill is **US-only**.
- This skill primarily uses `search_active_cars` (not `get_sold_summary`) since mileage stats require active inventory data.
- `mc_dealership_group_name` must match the dealer group's name in the MarketCheck database. Common names: "CarMax", "Carvana", "AutoNation", "Lithia Motors", "Penske Automotive".
- For KMX and CVNA, ALL inventory is used — no need to filter by `car_type`. For AN, LAD, PAG, filter to `car_type=used` to exclude their new vehicle inventory.
- Historical trending is limited by `search_active_cars` being a point-in-time snapshot. For trend analysis, compare current stats with `get_sold_summary` historical sold data for the same dealer group.
- The Carvana mileage signal (avg mileage rising 10% through 2025) was detectable ~11 months before the Q4 2025 earnings miss. This is the core investment thesis for this skill.
- Always cite actual numbers. Always map to tickers.
