---
name: sourcing-quality-signal
description: >
  Mileage and vehicle age trends as margin signals. Triggers:
  "average mileage", "reconditioning signal", "sourcing quality",
  "used vehicle age", "inventory quality", "KMX sourcing", "CVNA inventory quality",
  "reconditioning cost signal", "used car quality signal",
  "dealer group mileage benchmark", "sourcing quality for [dealer name]",
  tracking average mileage and vehicle age mix for any dealer group
  (publicly traded or private) as a proxy for reconditioning costs and margin pressure.
version: 0.1.0
---

# Sourcing Quality Signal — Mileage & Vehicle Age Trends for Used-Vehicle Retailer Analysis

## User Profile (Load First)

Load the `marketcheck-profile.md` project memory file if exists. Extract: `tracked_tickers`, `tracked_makes`, `tracked_states`, `benchmark_period_months`, `country`. If `country` is not `US`, halt with: *"This skill is US-only — dealer-group inventory analysis requires US `search_active_cars` data."* If profile is missing, ask for the target ticker (or dealer-group name) and confirm US geography. Confirm profile before proceeding.

## User Context

Financial analyst covering publicly traded used-vehicle retailers (KMX, CVNA) or dealer groups with significant used-vehicle operations (AN, LAD, PAG). Average mileage in sourced inventory is a direct proxy for reconditioning costs — a signal that, tracked across periodic snapshots through 2025, would have flagged Carvana's Q4 2025 earnings miss (average mileage rose ~10%, from ~48K to ~54K miles, signaling rising reconditioning costs months before the earnings report). This skill is snapshot-based; build the trend yourself by re-running it across periods.

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
- `country`: `US`
- `stats`: `miles,price,dom`
- `rows`: 0

→ **Extract only**: `num_found`, `stats.miles.mean`, `stats.miles.min`, `stats.miles.max`, `stats.price.mean`, `stats.dom.mean`. Discard full response.

### Step 2 — Pull vehicle age mix

Call `mcp__marketcheck__search_active_cars` with:
- `mc_dealership_group_name`: the dealer group
- `car_type`: `used`
- `country`: `US`
- `facets`: `year|0|10|1`
- `rows`: 0

→ **Extract only**: year facets with counts. Discard full response.

### Step 3 — Calculate age distribution

Group model years into bands:
- **0–2 year old** (current_year - 0 to 2): Premium, low recon cost
- **3–5 year old**: Core sweet spot, moderate recon
- **6–8 year old**: Higher recon, larger discount needed
- **9+ year old**: High recon, subprime segment

Calculate % of inventory in each band.

### Step 4 — Reconditioning Risk Score

Calculate: **Recon Risk Score = (avg_miles / 75,000) × 100**, capped at 100. The divisor is the BEARISH mileage threshold, so the score saturates exactly when the signal table classifies the group as BEARISH on mileage.

- Score 0–47: Low recon risk (avg miles in BULLISH zone, <35K)
- Score 47–73: Moderate recon risk (avg miles in NEUTRAL zone, 35–55K)
- Score 73–100: High recon risk (avg miles in CAUTION zone, 55–75K)
- Score 100 (capped): Very high recon risk (avg miles in BEARISH zone, ≥75K)

### Step 5 — Signal assignment

| Signal | Threshold |
|--------|-----------|
| BULLISH | Avg miles < 35K AND >50% inventory 0–2yr old (premium sourcing, low recon) |
| NEUTRAL | Avg miles < 55K |
| CAUTION | Avg miles 55–75K (recon costs rising) |
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
% Inventory 0-2yr   | 38%         | 22%            | KMX
% Inventory 6yr+    | 18%         | 35%            | KMX
Recon Risk Score    | 56          | 73             | KMX
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
- `country`: `US`
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
- Setting `mc_dealership_group_name` reroutes the request through the Dealer Inventory Syndication endpoint. If a response is missing `data.stats` or `data.facets` for that reason, record `num_found` only and disclose the data gap in the output rather than fabricating distribution percentages.
- For KMX and CVNA, ALL inventory is used — no need to filter by `car_type`. For AN, LAD, PAG, filter to `car_type=used` to exclude their new vehicle inventory.
- Historical trending is limited by `search_active_cars` being a point-in-time snapshot. For trend analysis, compare current stats with `get_sold_summary` historical sold data for the same dealer group.
- By running this skill periodically through 2025, an analyst would have seen Carvana's avg mileage rise ~10% — a leading indicator that surfaces ~11 months before the Q4 2025 earnings miss when snapshots are compared side-by-side. This periodic-snapshot pattern is the core investment thesis for this skill.
- Always cite actual numbers. Always map to tickers.
