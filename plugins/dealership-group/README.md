# Dealership Group Plugin — MarketCheck

Automotive market intelligence for **multi-location dealer groups**. Everything in the dealer plugin PLUS group dashboard, cross-location inventory balancing, rooftop benchmarking, dealer group health monitoring, and group rollup briefings.

---

## Who It's For

- Dealership group operators (2+ locations)
- Group inventory directors
- Regional managers overseeing multiple rooftops
- Publicly traded dealer group executives (AutoNation, Lithia, Penske, etc.)

---

## Skills (13)

All 10 skills from the dealer plugin, plus 3 group-specific skills:

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **group-dashboard** | "group overview", "how are my stores doing", "location health" | Multi-location health dashboard with 0-100 scoring per rooftop |
| **cross-location-balancer** | "transfer recommendations", "balance inventory", "redistribute" | Identifies units that would sell faster at a different rooftop and recommends transfers |
| **group-benchmarking** | "compare locations", "rooftop benchmarking", "which store is best" | Rooftop-vs-rooftop comparison on pricing, DOM, turn rate, and market position |
| **dealer-group-health-monitor** | "dealer group stock", "how is AutoNation doing" | Publicly traded dealer group stock health with peer comparison |
| **competitive-pricer** | "price this car", "am I priced right" | Dual franchise+independent pricing with CPO awareness |
| **vehicle-appraiser** | "appraise this vehicle", "trade-in value" | Three-source comparable-backed valuation |
| **inventory-intelligence** | "what should I stock", "aging inventory" | Demand-to-supply ratios and aging alerts |
| **stocking-guide** | "auction run list", "hot sellers" | Pre-auction VIN checks with BUY/CAUTION/PASS |
| **daily-dealer-briefing** | "daily briefing", "morning check" | Aging alerts + competitor price drops with group rollup |
| **weekly-dealer-review** | "weekly review", "lot scan" | Full lot scan + stocking hot list with group rollup |
| **monthly-dealer-strategy** | "monthly review", "monthly strategy" | Market share + depreciation + trends with group rollup |
| **depreciation-tracker** | "depreciation rate", "residual value" | Depreciation curves and brand rankings |
| **market-share-analyzer** | "market share", "competitor analysis" | Brand share with basis point changes |

---

## Commands (8)

| Command | What It Does |
|---------|-------------|
| `/onboarding` | Group profile setup — group name, ticker, N locations with their dealer IDs |
| `/price-check` | Quick price position check |
| `/vin-lookup` | Full VIN decode + history |
| `/market-snapshot` | State-level demand and supply |
| `/setup-mcp` | Configure MCP connection |
| `/daily-briefing` | Morning check with group rollup |
| `/weekly-review` | Weekly analysis with group rollup |
| `/monthly-strategy` | Monthly report with group rollup |

---

## Agents (6)

| Agent | What It Does |
|-------|-------------|
| **lot-scanner** | Paginated inventory fetch per location |
| **lot-pricer** | Batch pricing per location |
| **portfolio-scanner** | Ad-hoc VIN batch processing |
| **group-scanner** | Multi-location parallel inventory scan — scans all rooftops simultaneously |
| **brand-market-analyst** | Brand share, depreciation, market trends |
| **market-demand-agent** | Stocking hot lists, demand-to-supply ratios |

### Group Agent Orchestration

```
WAVE 1 (parallel):
  ├─ dealership-group:group-scanner        (all locations)
  ├─ dealership-group:market-demand-agent  (what's selling)
  └─ dealership-group:brand-market-analyst (market position)

WAVE 2 (depends on Wave 1):
  └─ dealership-group:lot-pricer           (price units across all locations)

GROUP ROLLUP:
  └─ Aggregate Wave 1+2 results into group-level KPIs
```

---

## Quick Start

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin dealership-group
/setup-mcp YOUR_API_KEY
/onboarding
```

After onboarding, try:
- "How are my stores doing?" — group health dashboard
- "Which location should I move this Camry to?" — transfer recommendation
- "Compare my Dallas and Houston stores" — rooftop benchmarking
- `/daily-briefing` — group-wide morning check

---

## Example Workflows

### Group Health Check
```
How are my stores doing?
```
→ 0-100 health score per location with pricing, aging, and turn rate KPIs

### Inventory Rebalancing
```
Which vehicles should I transfer between locations?
```
→ Units that would sell faster at a different rooftop with estimated gain

### Rooftop Comparison
```
Compare all my locations on pricing and turn rate
```
→ Side-by-side rooftop metrics with best/worst performers highlighted

---

## Live Example Outputs

> All examples below use **real market data** from the Texas market (Dallas, Houston, Austin). Dealer group persona "Southwest Auto Group" is fictional — used for illustration.

---

### `group-dashboard` — Group Health Overview

**Input:** *"How are my 3 stores doing? Give me the group health dashboard"*

<details>
<summary><strong>View Output</strong></summary>

```
GROUP HEALTH DASHBOARD: Southwest Auto Group — Mar 7, 2026
══════════════════════════════════════════════════════════════

┌─────────────────────────┬───────────────┬──────────┬─────────┬────────────┬────────┐
│ Location                │ Active Supply │ Med DOM  │ Med Ask │ Price Band │ Score  │
├─────────────────────────┼───────────────┼──────────┼─────────┼────────────┼────────┤
│ Dallas (Toyota)         │ 8,792 units   │ 58 days  │ $30,653 │$18.5K–77K  │  78/100│
│ Houston (Honda)         │ 5,278 units   │ 123 days │ $29,900 │$13K–81K    │  61/100│
│ Austin (Used Hub)       │ 34,920 units  │ 71 days  │ $38,544 │$2.8K–725K  │  73/100│
└─────────────────────────┴───────────────┴──────────┴─────────┴────────────┴────────┘

GROUP AGGREGATE
  Combined Active Units:   49,000+
  Weighted Avg DOM:        84 days
  Group Health Score:      71/100

SCORE BREAKDOWN PER ROOFTOP
──────────────────────────────────────────────────────────────
DALLAS — TOYOTA FRANCHISE              Score: 78/100  HEALTHY
  Active supply:  8,792 Toyota units (2020-2026 recent mix: 3,021)
  Median DOM:     58 days  (market median: 88 days in TX)
  Median asking:  $30,653  |  Avg asking: $33,743
  Top 3 models:   Camry (1,544) · Tacoma (1,439) · Corolla (1,070)
  Sold volume:    42,843 Toyota transactions in 90d (Dallas 50mi)
  Pricing health: PASS — median below TX state median of $37,819
  DOM health:     PASS — 34% faster than TX median (58 vs 88 days)
  Gap: Tundra/4Runner stocking opportunity — high sold velocity

HOUSTON — HONDA FRANCHISE              Score: 61/100  NEEDS ATTENTION
  Active supply:  5,278 Honda units (2020-2026 recent mix: 1,535)
  Median DOM:     123 days  (vs market median: 88 days TX)
  Median asking:  $29,900  |  Avg asking: $31,470
  Top 3 models:   CR-V (1,549) · Accord (916) · Civic (808)
  Sold volume:    21,114 Honda transactions in 90d (Houston 50mi)
  Pricing health: PASS — median below market
  DOM health:     FAIL — 40% slower than TX median (123 vs 88 days)
  Alert: CR-V inventory aging — 55 active comps, heavy competition

AUSTIN — USED CAR HUB (Independent)   Score: 73/100  STABLE
  Active supply:  34,920 units (all makes, 20mi radius)
  Median DOM:     71 days   (vs market median: 88 days TX)
  Median asking:  $38,544  |  Avg asking: $43,926
  Top makes:      Toyota (4,838) · Ford (3,809) · Chevy (2,533)
  Pricing health: PASS — near market midpoint
  DOM health:     PASS — 19% faster than TX median
  Alert: High median ($38.5K) suggests inventory skew to newer units

GROUP-WIDE ALERTS
  ! Houston DOM at 123 days — 40% above benchmark — pricing review needed
  ! Houston CR-V segment: 55 active comps creating downward price pressure
  ! Austin ask median 25% above Dallas/Houston — reassess mix strategy
```
</details>

---

### `cross-location-balancer` — Transfer Recommendations

**Input:** *"Which vehicles should I transfer between my Dallas and Houston stores?"*

<details>
<summary><strong>View Output</strong></summary>

```
CROSS-LOCATION TRANSFER ANALYSIS: Southwest Auto Group
Dallas Toyota (ZIP 75201) ↔ Houston Honda (ZIP 77001)
══════════════════════════════════════════════════════════════

MARKET CONTEXT
  Dallas Toyota supply:   8,792 units | Median DOM: 58d | Sold 90d: 42,843
  Houston Honda supply:   5,278 units | Median DOM: 123d | Sold 90d: 21,114
  Spread signal: Dallas turns 2.1× faster than Houston on same-category units

TRANSFER RECOMMENDATIONS
┌────┬──────────────────────────────┬─────────┬──────────┬──────────────────────────────────────────────┐
│  # │ Vehicle Type / Category      │ From    │ To       │ Reason & Est. Benefit                        │
├────┼──────────────────────────────┼─────────┼──────────┼──────────────────────────────────────────────┤
│  1 │ Toyota RAV4 (2022-24 used)   │ Dallas  │ Houston  │ RAV4 is top-3 by sold vol in TX; Houston     │
│    │                              │         │          │ CR-V supply overhang creates sub demand;      │
│    │                              │         │          │ RAV4 fills gap at similar price point ($30K+) │
│    │                              │         │          │ Est. DOM reduction: 123d → ~65d (+$1,400/unit)│
├────┼──────────────────────────────┼─────────┼──────────┼──────────────────────────────────────────────┤
│  2 │ Honda CR-V (aged 90+ DOM)    │ Houston │ Austin   │ Austin used hub handles broader brand mix;   │
│    │ Priced $25K-$29K             │         │          │ Austin median $38.5K — CR-Vs at $27K stand   │
│    │                              │         │          │ out as value; 34,920 unit market absorbs more │
│    │                              │         │          │ Est. benefit: clear 3-5 aged units, free floor│
├────┼──────────────────────────────┼─────────┼──────────┼──────────────────────────────────────────────┤
│  3 │ Toyota Tacoma (used, 60+ DOM)│ Dallas  │ Austin   │ Austin top-make is Toyota (4,838 units) — high│
│    │                              │         │          │ absorption. Tacoma (#2 by sold vol in Dallas) │
│    │                              │         │          │ at $30-40K fits Austin median price range     │
│    │                              │         │          │ Est. DOM reduction: 60+ days → ~35d           │
├────┼──────────────────────────────┼─────────┼──────────┼──────────────────────────────────────────────┤
│  4 │ Honda Pilot/Odyssey (aging)  │ Houston │ Dallas   │ Dallas used Toyota lot can absorb Honda SUVs  │
│    │ DOM > 75 days                │         │          │ as cross-brand value units; Dallas DOM 58d vs │
│    │                              │         │          │ Houston 123d means faster disposal in DFW     │
│    │                              │         │          │ Est. benefit: $35/day floor savings × 45 days │
└────┴──────────────────────────────┴─────────┴──────────┴──────────────────────────────────────────────┘

FLOOR PLAN SAVINGS SUMMARY (Houston aging units — estimated)
  Units flagged 90+ DOM at Houston:     ~18-22 units (based on DOM dist.)
  Floor plan cost rate:                 $35/day/unit
  Avg days stranded if not moved:       45 additional days
  Est. floor plan burn if not actioned: ~$31,500/month

TRANSFER LOGISTICS
  Dallas → Houston:  135 mi · 2hr drive · transporter est. $250-$350/unit
  Houston → Austin:  162 mi · 2.5hr drive · transporter est. $300-$400/unit
  Dallas → Austin:   185 mi · 3hr drive · transporter est. $350-$450/unit
  Break-even on transfers: 12-15 floor plan days recovered per move
```
</details>

---

### `group-benchmarking` — Rooftop Comparison

**Input:** *"Compare all 3 of my locations on pricing, DOM, and turn rate"*

<details>
<summary><strong>View Output</strong></summary>

```
ROOFTOP BENCHMARKING: Southwest Auto Group — Mar 7, 2026
══════════════════════════════════════════════════════════════

SIDE-BY-SIDE METRICS
┌─────────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Metric                  │ Dallas (Toyota)  │ Houston (Honda)  │ Austin (Used Hub)│
├─────────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Active Inventory        │ 8,792 units      │ 5,278 units      │ 34,920 units     │
│ Recent Mix (2020-26)    │ 3,021 units      │ 1,535 units      │ ~15,000 est.     │
│ Median Asking Price     │ $30,653          │ $29,900          │ $38,544          │
│ Avg Asking Price        │ $33,743          │ $31,470          │ $43,926          │
│ Median DOM              │ 58 days          │ 123 days         │ 71 days          │
│ DOM vs TX Median        │ -34% (FASTER)    │ +40% (SLOWER)    │ -19% (FASTER)    │
│ Sold 90d (brand)        │ 42,843 Toyota    │ 21,114 Honda     │ market-wide      │
│ Top Model by Inventory  │ Camry (1,544)    │ CR-V (1,549)     │ Toyota (4,838)   │
│ Price Band (P5-P95)     │ $18.5K–$59.7K    │ $20K–$48.8K      │ $10.9K–$91.5K    │
└─────────────────────────┴──────────────────┴──────────────────┴──────────────────┘

TX MARKET BENCHMARK (state-wide baseline)
  Active supply:    610,694  |  Median ask: $37,819  |  Median DOM: 88 days
  Sold 90d:       1,419,756  |  Median sold: $35,335

BEST PERFORMERS
  Fastest Turn:   Dallas Toyota — 58-day median DOM, 34% faster than TX benchmark
  Highest Volume: Austin Used Hub — 34,920 active units, broadest market reach
  Best Sell-Through: Dallas Toyota — 42,843 Toyota transactions in 90 days within 50mi

WORST PERFORMERS
  Slowest Turn:   Houston Honda — 123-day median DOM, 40% slower than TX benchmark
  Highest Stale Risk: Houston — DOM dist. shows units bunching above 100-day mark

ACTION ITEMS BY ROOFTOP
  DALLAS  1. Source more Tundras and 4Runners — high sold velocity, under-supplied
          2. Hold Toyota pricing — 58-day DOM confirms market acceptance
          3. Identify Camry overage (1,544 units) — largest segment, watch aging

  HOUSTON 1. URGENT — Price-reduce CR-V units over 75 DOM by $1,500-$2,500
          2. Transfer 3-5 aged Hondas to Austin where value units turn faster
          3. Introduce Toyota brand trade-ins to diversify away from Honda-only lot

  AUSTIN  1. Lean into Toyota and Ford — #1 and #2 makes in Austin market
          2. Source value-priced units ($25K-$35K) to undercut $38.5K median
          3. Accept Houston Honda transfers — broad lot absorbs brand variety
```
</details>

---

### `/daily-briefing` — Group Morning Check

**Input:** `/daily-briefing`

<details>
<summary><strong>View Output</strong></summary>

```
GROUP DAILY BRIEFING: Southwest Auto Group — Mar 7, 2026
══════════════════════════════════════════════════════════════

DALLAS — TOYOTA FRANCHISE
  Inventory:   8,792 active Toyota units (Dallas 20mi)
  Median DOM:  58 days ✅ — tracking 34% faster than TX benchmark (88d)
  Top 3 aging: Camry, Tacoma, Corolla — monitor units crossing 75-day mark
  Market note: 42,843 Toyota sold in 90d within 50mi — strong absorption
  Floor plan:  Monitor aging Camry inventory (1,544 units — watch for overlap)

HOUSTON — HONDA FRANCHISE
  Inventory:   5,278 active Honda units (Houston 20mi)
  Median DOM:  123 days — 40% ABOVE TX benchmark ALERT
  Top aging:   CR-V (1,549 units), Accord (916), Civic (808)
  Market note: 21,114 Honda sold in 90d within 50mi
  Floor plan:  At $35/day, units at 123d median are burning $4,305/unit above benchmark
  ACTION:      Flag all Honda units > 75 DOM for immediate price review

AUSTIN — USED CAR HUB
  Inventory:   34,920 active units (Austin 20mi, all makes)
  Median DOM:  71 days ✅ — tracking 19% faster than TX benchmark
  Top makes:   Toyota (4,838) · Ford (3,809) · Chevrolet (2,533)
  Market note: 34,920-unit market with $38,544 median — broad absorption capacity
  Floor plan:  Stable — 71-day median tracks near benchmark

GROUP TOP 3 ACTIONS TODAY
  1. REVIEW Houston Honda pricing — 123d median DOM = 40% over benchmark
     Pull all units 75+ DOM; target $1,500-$2,500 reductions to break logjam
  2. TRANSFER Houston aged CR-Vs to Austin used hub (3-5 units)
     Austin absorbs Honda well (1,872 active); value-priced units ($25-27K)
     will sit below Austin median ($38.5K) = fast turn
  3. SOURCE Tundra and 4Runner for Dallas lot
     Tundra #5 by inventory (891 units, 2020-26) but sold volume strong;
     Dallas DOM 58 days confirms buying appetite — keep supply fresh
```
</details>

---

### `vehicle-appraiser` — Trade-In at the Desk

**Input:** *"Trade-in appraisal: 2023 Honda CR-V EX-L AWD, 28,500 miles, clean condition, Houston store"*
*(VIN 5J6RS3H7XPL002510 — 2023 CR-V EX-L FWD)*

<details>
<summary><strong>View Output</strong></summary>

```
VEHICLE APPRAISAL: 2023 Honda CR-V EX-L
VIN: 5J6RS3H7XPL002510 · 28,500 mi · ZIP 77001 (Houston)
══════════════════════════════════════════════════════════════

THREE-SOURCE VALUATION
┌──────────────────────────────┬────────────┐
│ Source                       │ Value      │
├──────────────────────────────┼────────────┤
│ ML Prediction (Franchise)    │ $28,602    │
│ Active Comp Median (55 units)│ $29,440    │
│ Sold Median (18 units, 90d)  │ $28,198    │
├──────────────────────────────┼────────────┤
│ ★ Blended Estimate           │ $28,747    │
│ MSRP (new sticker)           │ $37,140    │
│ Depreciation from MSRP       │ -$8,393    │
│ Retention                    │ 77.4%      │
└──────────────────────────────┴────────────┘
  Confidence: HIGH (55 active + 18 sold comps in TX market)

RETAIL RANGE
  Low  (wholesale floor):      $22,417
  Mid  (fair market):          $28,747
  High (retail ceiling):       $34,201

COMPARABLE ACTIVE LISTINGS (2023 CR-V, 75mi from 77001)
┌───┬──────────┬─────────┬─────┬───────────────────────────────────────┐
│ # │  Price   │  Miles  │ DOM │ Dealer                                │
├───┼──────────┼─────────┼─────┼───────────────────────────────────────┤
│ 1 │ $28,441  │ 44,771  │  30 │ Houston franchise dealer (48 mi)      │
│ 2 │ $27,490  │ 54,722  │  29 │ TX dealer (158 mi)                    │
│ 3 │ $30,494  │ 28,210  │  48 │ TX dealer (175 mi)                    │
│ 4 │ $29,613  │ 12,626  │  57 │ TX dealer (185 mi)                    │
│ 5 │ $29,357  │ 22,607  │ 123 │ TX dealer (197 mi) — aging unit       │
└───┴──────────┴─────────┴─────┴───────────────────────────────────────┘
  Active market range: $22,417 – $34,201 | Median: $29,440

SOLD TRANSACTIONS (past 90 days, Houston 75mi)
  Sold volume:       18 units
  Sold price range:  $25,482 – $31,000
  Sold median:       $28,198
  → Blended estimate ($28,747) is $549 above sold median — strong alignment.

TRADE-IN OFFER RECOMMENDATION (Houston Store)
  Retail target:     $28,747  (blended estimate)
  Target margin:     -$4,312  (15%)
  Recon estimate:    -$1,500  (clean condition — minimal recon)
  ─────────────────────────────────────────────────────────────
  OFFER RANGE:       $21,935 – $23,935
  Strong offer:      $23,000  (leaves $5,747 gross at retail)

  GROUP CONTEXT: Houston Honda lot median DOM is 123 days —
  this 2023 CR-V EX-L at fair pricing should turn in 30-45 days,
  well below your current location average. Recommend buying it.
```
</details>

---

### `/market-snapshot` — Texas Market Overview

**Input:** `/market-snapshot TX`

<details>
<summary><strong>View Output</strong></summary>

```
MARKET SNAPSHOT: Texas (TX) — All Vehicles
══════════════════════════════════════════════════════════════

HEADLINE NUMBERS
  Active Supply:       610,694 listings
  Sold (past 90d):   1,419,756 transactions
  Turnover Ratio:      2.32x
  Median Ask Price:   $37,819
  Median Sold Price:  $35,335
  Median DOM:          88 days

SUPPLY BY BODY TYPE
┌──────────────┬─────────┬───────┐
│ Segment      │  Count  │  %    │
├──────────────┼─────────┼───────┤
│ SUV          │ 303,399 │ 49.7% │
│ Pickup       │ 151,146 │ 24.7% │
│ Sedan        │  98,672 │ 16.2% │
│ Hatchback    │  15,918 │  2.6% │
│ Coupe        │  11,744 │  1.9% │
│ Minivan      │   8,875 │  1.5% │
│ Cargo Van    │   6,158 │  1.0% │
│ Convertible  │   4,421 │  0.7% │
└──────────────┴─────────┴───────┘

TOP MAKES BY ACTIVE SUPPLY
┌────┬────────────────┬─────────┬───────┐
│  # │ Make           │  Count  │  %    │
├────┼────────────────┼─────────┼───────┤
│  1 │ Ford           │  98,175 │ 16.1% │
│  2 │ Chevrolet      │  68,836 │ 11.3% │
│  3 │ Toyota         │  52,937 │  8.7% │
│  4 │ Nissan         │  44,613 │  7.3% │
│  5 │ Hyundai        │  33,153 │  5.4% │
│  6 │ Jeep           │  32,206 │  5.3% │
│  7 │ Honda          │  29,700 │  4.9% │
│  8 │ RAM            │  28,651 │  4.7% │
│  9 │ GMC            │  27,937 │  4.6% │
│ 10 │ KIA            │  26,199 │  4.3% │
│ 11 │ BMW            │  19,870 │  3.3% │
│ 12 │ Mercedes-Benz  │  17,633 │  2.9% │
│ 13 │ Volkswagen     │  15,944 │  2.6% │
│ 14 │ Mazda          │  13,903 │  2.3% │
│ 15 │ Subaru         │  10,742 │  1.8% │
└────┴────────────────┴─────────┴───────┘

PRICE DISTRIBUTION (Active)
  P5:  $11,211    P25: $25,156    P50: $37,819
  P75: $54,423    P90: $72,542    P95: $84,822

GROUP INTEL FOR SOUTHWEST AUTO GROUP
  Toyota (#3 in TX, 52,937 units):  Your Dallas franchise brand —
    robust sold velocity (42,843 Toyota sold in 90d in DFW market)
  Honda (#7 in TX, 29,700 units):   Your Houston franchise brand —
    lower supply rank but strong CR-V demand; DOM lag suggests pricing issues
  TX pickup market = 24.7% of supply — important for Dallas/Austin lots
  SUVs dominate at 49.7% — aligns with Toyota RAV4 and Honda CR-V focus
```
</details>

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
