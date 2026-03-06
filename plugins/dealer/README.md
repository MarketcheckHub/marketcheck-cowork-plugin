# Dealer Plugin — MarketCheck

Automotive market intelligence for **franchise and independent car dealers**. Competitive pricing, inventory intelligence, stocking guides, and daily/weekly/monthly operational briefings with franchise + independent dual pricing and CPO-aware comparisons.

---

## Who It's For

- Franchise dealers (Toyota, Ford, Honda, etc.)
- Independent used car dealers
- Used car managers and inventory managers
- General managers who want data-driven lot operations

---

## Skills (10)

Skills activate automatically when you ask questions in natural language — no slash commands needed.

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **competitive-pricer** | "price this car", "am I priced right", "who is undercutting me" | Positions your price against the market with Below/At/Above verdict and dual franchise+independent pricing |
| **vehicle-appraiser** | "appraise this vehicle", "what's it worth", "trade-in value" | Three-source valuation (ML prediction + active comps + sold transactions) with confidence score |
| **deal-finder** | "find me the best deal", "is this a good price", "compare deals" | Sources best-priced vehicles, validates fair pricing, builds negotiation leverage |
| **inventory-intelligence** | "what should I stock", "aging inventory alert", "turn rate" | Demand-to-supply ratios, aging alerts, turn-rate benchmarks, mix analysis |
| **stocking-guide** | "auction run list check", "hot sellers", "should I bid on this" | Pre-auction VIN checks with BUY/CAUTION/PASS verdicts, hot list, avoid list |
| **daily-dealer-briefing** | "daily briefing", "morning check", "what needs attention today" | Aging alerts + competitor price drops + top 3 actions for today (~5 min) |
| **weekly-dealer-review** | "weekly review", "full lot pricing scan", "what should I stock this week" | Full lot competitive scan + stocking hot list + demand snapshot (~15 min) |
| **monthly-dealer-strategy** | "monthly review", "monthly strategy", "end of month analysis" | Market share + depreciation + trends + inventory intel + 30-day plan (~20 min) |
| **depreciation-tracker** | "depreciation rate", "residual value", "which cars hold value" | Multi-point depreciation curves, brand rankings, segment comparisons |
| **market-share-analyzer** | "market share", "who is winning in SUVs", "EV adoption rate" | Brand market share with basis point changes, segment conquest, dealer group rankings |

---

## Commands (8)

| Command | Usage | What It Does |
|---------|-------|-------------|
| `/onboarding` | `/onboarding` | One-time dealer profile setup — franchise/independent type, location, preferences |
| `/price-check` | `/price-check VIN` | Quick price-position check in under 30 seconds |
| `/vin-lookup` | `/vin-lookup VIN` | Full VIN decode + listing history + estimated value |
| `/market-snapshot` | `/market-snapshot TX` | State-level demand, supply, and opportunity snapshot |
| `/setup-mcp` | `/setup-mcp API_KEY` | Configure MarketCheck MCP connection |
| `/daily-briefing` | `/daily-briefing` | Morning operational health check |
| `/weekly-review` | `/weekly-review` | Tactical weekly lot analysis |
| `/monthly-strategy` | `/monthly-strategy` | Comprehensive monthly strategic report |

---

## Agents (5)

| Agent | When It's Used | What It Does |
|-------|---------------|-------------|
| **lot-scanner** | Daily/weekly/monthly briefings | Paginated inventory fetch — gets your complete lot regardless of size |
| **lot-pricer** | Daily/weekly briefings | Batch prices every unit against the market with action recommendations |
| **portfolio-scanner** | Ad-hoc VIN batch requests | Processes auction run lists, portfolio revaluations, fleet appraisals |
| **brand-market-analyst** | Monthly strategy | Brand market share, depreciation watch, market trends |
| **market-demand-agent** | Weekly review, stocking guide | Stocking hot lists, demand-to-supply ratios, turn rates |

### Agent Orchestration

```
WAVE 1 (parallel):
  ├─ dealer:lot-scanner          (your inventory)
  ├─ dealer:market-demand-agent  (what's selling)
  └─ dealer:brand-market-analyst (market position)

WAVE 2 (depends on Wave 1):
  └─ dealer:lot-pricer           (price every unit)
```

---

## Quick Start

```bash
# 1. Install
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin dealer

# 2. Connect MCP
/setup-mcp YOUR_API_KEY

# 3. Onboard your dealership
/onboarding
```

After onboarding, try:
- `/daily-briefing` — morning health check
- `/price-check 1HGCV1F3XPA123456` — quick price position
- "What should I buy at auction?" — stocking recommendations
- "Am I priced right on my RAV4s?" — competitive analysis

---

## Live Example Outputs

> All examples below use **real market data** from the Chicago metro area (ZIP 60659). Dealer identity has been anonymized — "Lakeview Motors" is a fictional franchise Toyota dealer used for illustration.

---

### `/price-check` — Quick Price Position

**Input:** `/price-check 5TDEBRCH0PS123584`
*(2023 Toyota Highlander Hybrid Platinum · 13,182 mi · Asking $48,990)*

<details>
<summary><strong>View Output</strong></summary>

<table>
<tr><td colspan="3" style="text-align:center"><h4>PRICE CHECK: 2023 Toyota Highlander Hybrid Platinum</h4></td></tr>
</table>

```
VIN:     5TDEBRCH0PS123584
Miles:   13,182              ZIP: 60659
Asking:  $48,990              MSRP (new): $54,845

═══════════════════════════════════════════════════
  PREDICTED MARKET VALUE        $49,126
  Asking vs Predicted           -$136 (0.3% below)
  MSRP Retention                89.3%
═══════════════════════════════════════════════════

COMPARABLES (Platinum trim, franchise dealers):
┌───┬──────────┬─────────┬────────────────────────────┐
│ # │  Price   │  Miles  │  Dealer                    │
├───┼──────────┼─────────┼────────────────────────────┤
│ 1 │ $48,990  │ 13,182  │ Lakeview Motors (0.9 mi)   │
│ 2 │ $43,872  │ 40,296  │ Graff Toyota (40.6 mi)     │
│ 3 │ $44,034  │ 44,150  │ Smart Toyota (149 mi)      │
│ 4 │ $45,500  │ 39,811  │ Joseph Toyota (251 mi)     │
│ 5 │ $47,983  │ 27,246  │ Toyota Of Madison (253 mi) │
└───┴──────────┴─────────┴────────────────────────────┘

MARKET CONTEXT (all 2023 Highlander trims, 50 mi):
  Competing units:    66
  Price range:        $25,997 – $48,990
  Average asking:     $36,096
  Median asking:      $36,018

  VERDICT: ✅ PRICED RIGHT — $136 below predicted
  value. Lowest-mileage Platinum within 250 mi.
  Premium over market median justified by top trim
  + low miles.
```
</details>

---

### `/vin-lookup` — Full VIN Decode + Value

**Input:** `/vin-lookup 3TMLB5JN4RM005615`
*(2024 Toyota Tacoma TRD Off-Road)*

<details>
<summary><strong>View Output</strong></summary>

```
VIN DECODE: 3TMLB5JN4RM005615
═══════════════════════════════════════════════════

VEHICLE SPECIFICATIONS
  Year:          2024
  Make/Model:    Toyota Tacoma
  Trim:          TRD Off Road
  Version:       TRD Off Road 4x4 Double Cab Long Bed
  Body:          Pickup, 4-door, 5 seats
  Engine:        2.4L I4 Turbo · 4 cyl
  Transmission:  Automatic
  Drivetrain:    4WD
  Fuel:          Unleaded
  MPG:           19 city / 23 hwy / 21 combined
  Made in:       USA

COLORS
  Exterior:      Ice Cap (White)
  Interior:      Boulder/Black Fabric (Gray)

PRICING
  Base MSRP:     $43,400
  Combined MSRP: $51,559 (with options + delivery)

SAFETY RATINGS
  Overall:       ★★★★☆ (4/5)
  Front:         ★★★★☆ (4/5)
  Side:          ★★★★★ (5/5)
  Rollover:      ★★★★☆ (4/5)
  Roof Strength: Good

═══════════════════════════════════════════════════

ESTIMATED MARKET VALUE (18,090 mi, ZIP 60659)
  Predicted:     $39,504
  vs MSRP:       -$12,055 (23.4% depreciation)

COMPARABLE LISTINGS
┌───┬──────────┬─────────┬────────────────────────────┐
│ # │  Price   │  Miles  │  Dealer                    │
├───┼──────────┼─────────┼────────────────────────────┤
│ 1 │ $41,490  │ 18,090  │ Lakeview Motors (0.9 mi)   │
│ 2 │ $39,490  │ 14,506  │ Lakeview Motors (0.9 mi)   │
│ 3 │ $41,998  │ 15,924  │ Carmax Glencoe (9.7 mi)    │
└───┴──────────┴─────────┴────────────────────────────┘
```
</details>

---

### `/market-snapshot` — State-Level Market Overview

**Input:** `/market-snapshot IL`

<details>
<summary><strong>View Output</strong></summary>

```
MARKET SNAPSHOT: Illinois (IL) — Used Vehicles
═══════════════════════════════════════════════════

HEADLINE NUMBERS
  Active Supply:        110,556 listings
  Sold (past 90d):      284,554 transactions
  Turnover Ratio:       2.57x
  Median Price:         $22,881
  Median Mileage:       58,934 mi
  Median DOM:           130 days

SUPPLY BY BODY TYPE
┌──────────────┬─────────┬───────┐
│ Segment      │  Count  │  %    │
├──────────────┼─────────┼───────┤
│ SUV          │ 56,829  │ 51.4% │
│ Sedan        │ 22,087  │ 20.0% │
│ Pickup       │ 14,813  │ 13.4% │
│ Hatchback    │  4,350  │  3.9% │
│ Minivan      │  3,057  │  2.8% │
│ Coupe        │  2,541  │  2.3% │
│ Convertible  │  1,847  │  1.7% │
│ Cargo Van    │  1,536  │  1.4% │
└──────────────┴─────────┴───────┘

TOP MAKES BY ACTIVE SUPPLY
┌────┬────────────────┬─────────┬───────┐
│  # │ Make           │  Count  │  %    │
├────┼────────────────┼─────────┼───────┤
│  1 │ Chevrolet      │ 14,945  │ 13.5% │
│  2 │ Ford           │ 14,636  │ 13.2% │
│  3 │ Jeep           │  8,032  │  7.3% │
│  4 │ Toyota         │  6,822  │  6.2% │
│  5 │ Nissan         │  6,617  │  6.0% │
│  6 │ Honda          │  4,952  │  4.5% │
│  7 │ GMC            │  4,643  │  4.2% │
│  8 │ Hyundai        │  4,308  │  3.9% │
│  9 │ BMW            │  4,274  │  3.9% │
│ 10 │ Mercedes-Benz  │  4,015  │  3.6% │
└────┴────────────────┴─────────┴───────┘

PRICE DISTRIBUTION
  P5:   $6,376     P25: $14,421    P50: $22,881
  P75: $33,527     P90: $48,335    P95: $63,122

MODEL YEAR MIX (Active)
┌──────┬─────────┐
│ Year │  Count  │
├──────┼─────────┤
│ 2023 │ 13,441  │
│ 2024 │ 12,749  │
│ 2025 │ 12,448  │
│ 2022 │  9,090  │
│ 2021 │  6,994  │
│ 2019 │  6,644  │
│ 2020 │  6,368  │
│ 2018 │  6,205  │
└──────┴─────────┘
```
</details>

---

### `competitive-pricer` — Dual-Market Price Positioning

**Input:** *"Am I priced right on this RAV4 Hybrid?"*
*(2025 Toyota RAV4 Hybrid XSE AWD · 19,255 mi · Asking $38,990)*

<details>
<summary><strong>View Output</strong></summary>

```
COMPETITIVE PRICING: 2025 Toyota RAV4 Hybrid XSE AWD
VIN: JTME6RFV2SD579127 · 19,255 mi · ZIP 60659
═══════════════════════════════════════════════════

DUAL MARKET PRICING
┌─────────────────────┬────────────┬──────────────┐
│                     │ Franchise  │ Independent  │
├─────────────────────┼────────────┼──────────────┤
│ Predicted Price     │ $38,403    │ $38,684      │
│ Your Asking Price   │ $38,990    │ $38,990      │
│ Delta               │ +$587      │ +$306        │
│ Position            │ 1.5% above │ 0.8% above   │
└─────────────────────┴────────────┴──────────────┘
  MSRP (new): $40,835  ·  Retention: 94.2%

COMPETITIVE SET (XSE Hybrid trim, within 50 mi)
┌───┬──────────┬─────────┬──────────────────────────────┐
│ # │  Price   │  Miles  │  Dealer                      │
├───┼──────────┼─────────┼──────────────────────────────┤
│ 1 │ $38,990  │ 19,255  │ Lakeview Motors (0.9 mi)     │
│ 2 │ $41,914  │ 13,384  │ Toyota Of Naperville (29 mi) │
│ 3 │ $41,914  │  9,519  │ Toyota Of Naperville (29 mi) │
│ 4 │ $38,990  │ 31,055  │ Lakeview Motors (0.9 mi)     │
│ 5 │ $38,498  │ 17,285  │ Libertyville Toyota (31 mi)  │
└───┴──────────┴─────────┴──────────────────────────────┘

BROADER MARKET (all 2025 RAV4 trims, 50 mi)
  Competing units:    180
  Average asking:     $32,946
  Median asking:      $32,499
  Your percentile:    92nd (price) · 50th (mileage)

  VERDICT: ⚠️ SLIGHTLY ABOVE MARKET — $587 over
  franchise predicted. But 3 of 4 XSE comps are
  priced higher ($41,914). Closest comp at $38,498
  (Libertyville) has similar miles — you are within
  $492 of direct competition. Hold price.
```
</details>

---

### `vehicle-appraiser` — Three-Source Valuation

**Input:** *"Appraise this Tundra, 16,930 miles, clean"*
*(2024 Toyota Tundra SR5 4WD · VIN 5TFLA5DB8RX204441)*

<details>
<summary><strong>View Output</strong></summary>

```
VEHICLE APPRAISAL: 2024 Toyota Tundra SR5 4WD
VIN: 5TFLA5DB8RX204441 · 16,930 mi · ZIP 60659
═══════════════════════════════════════════════════

THREE-SOURCE VALUATION
┌──────────────────────────┬────────────┐
│ Source                   │ Value      │
├──────────────────────────┼────────────┤
│ ML Prediction (Franchise)│ $43,594    │
│ ML Prediction (Indep.)   │ $44,286    │
│ Active Comp Median (277) │ $44,754    │
│ Sold Median (148 units)  │ $47,417    │
├──────────────────────────┼────────────┤
│ ★ Blended Estimate       │ $44,211    │
│ MSRP (new sticker)       │ $54,228    │
│ Depreciation from MSRP   │ -$10,017   │
│ Retention                │ 81.5%      │
└──────────────────────────┴────────────┘
  Confidence: HIGH (277 active + 148 sold comps)

RETAIL RANGE
  Low  (wholesale floor):     $35,980
  Mid  (fair market):         $44,211
  High (retail ceiling):      $58,701

COMPARABLE ACTIVE LISTINGS (SR5 trim)
┌───┬──────────┬─────────┬─────┬──────────────────────────┐
│ # │  Price   │  Miles  │ DOM │ Dealer                   │
├───┼──────────┼─────────┼─────┼──────────────────────────┤
│ 1 │ $44,490  │ 16,930  │  74 │ Lakeview Motors          │
│ 2 │ $42,900  │ 35,357  │  89 │ Toyota Of Naperville     │
│ 3 │ $43,575  │ 23,592  │  78 │ Toyota Of Naperville     │
│ 4 │ $44,998  │ 13,842  │  75 │ Carmax Joliet            │
│ 5 │ $43,997  │ 36,125  │  95 │ Graff Toyota (Chesterton)│
└───┴──────────┴─────────┴─────┴──────────────────────────┘

SOLD TRANSACTIONS (past 90 days, 100 mi)
  Sold volume:       148 units
  Sold price range:  $37,494 – $64,248
  Sold median:       $47,417
  → Current asking ($44,490) is $2,927 BELOW
    recent sold median — strong buyer value.
```
</details>

---

### `deal-finder` — Best-Priced Vehicles Near You

**Input:** *"Find me the best deal on a 2024 Grand Highlander"*

<details>
<summary><strong>View Output</strong></summary>

```
DEAL FINDER: 2024 Toyota Grand Highlander
ZIP 60659 · 75 mi radius · Used
═══════════════════════════════════════════════════

MARKET OVERVIEW
  Active listings:     41
  Median price:        $45,772
  Median miles:        27,799
  Predicted value:     $46,733 (Limited trim @ 27K mi)

TOP 10 DEALS (sorted by price)
┌────┬──────────┬──────────┬─────────┬─────┬──────────────────────────────┐
│  # │  Price   │  Trim    │  Miles  │ DOM │ Dealer (City)                │
├────┼──────────┼──────────┼─────────┼─────┼──────────────────────────────┤
│  1 │ $31,995  │ XLE FWD  │ 107,765 │  28 │ Ford City Motors (Elgin)     │
│  2 │ $35,500  │ XLE AWD  │  90,758 │   7 │ Valley Hyundai (Aurora)      │
│  3 │ $35,998  │ XLE FWD  │  80,422 │ 162 │ Carmax (Oak Lawn)            │
│  4 │ $38,543  │ XLE AWD  │  40,122 │ 122 │ Liberty CDJR (Libertyville)  │
│  5 │ $39,685  │ XLE AWD  │  29,039 │ 113 │ Kunes Ford (Antioch)         │
│  6 │ $39,750  │ XLE AWD  │  63,487 │ 109 │ Anderson Toyota (Loves Park) │
│  7 │ $39,754  │ AWD      │  43,843 │  19 │ Hertz Car Sales (Des Plaines)│
│  8 │ $41,987  │ XLE AWD  │  27,799 │  21 │ Carvana (Joliet)             │
│  9 │ $42,299  │ Limited  │  23,576 │  23 │ Grand Subaru (Bensenville)   │
│ 10 │ $42,990  │ XLE AWD  │  18,439 │  76 │ Honda Of Lisle               │
└────┴──────────┴──────────┴─────────┴─────┴──────────────────────────────┘

BEST VALUE PICK: #4 — $38,543 · XLE AWD · 40,122 mi
  → $7,229 below median asking ($45,772)
  → AWD with moderate miles, 122 DOM = negotiate room
  → Suggested offer: $36,500–$37,500

NEGOTIATION LEVERAGE
  → Listings #5-#6 at 109-113 DOM have floor plan
    pressure — dealers may accept 5-8% below asking
  → 3 units have no listed price — call for quotes
```
</details>

---

### `inventory-intelligence` — Demand-to-Supply Ratios

**Input:** *"What should I stock? Show demand vs supply for my market"*

<details>
<summary><strong>View Output</strong></summary>

```
INVENTORY INTELLIGENCE: Chicago Metro (ZIP 60659, 30 mi)
═══════════════════════════════════════════════════

HEADLINE METRICS
  Active Supply:      53,882 units
  Sold (90 days):    149,939 transactions
  Turnover Ratio:     2.78x
  Avg Asking Price:   $28,708
  Median DOM:         126 days

HOT MODELS — Highest Demand-to-Supply Ratio
(ratio >3.0 = under-supplied = STOCK THESE)
┌────┬─────────────────┬─────────┬──────────┬───────┐
│  # │ Model           │ Supply  │ Sold 90d │ D:S   │
├────┼─────────────────┼─────────┼──────────┼───────┤
│  1 │ Toyota RAV4     │    650  │   2,715  │ 4.18x │
│  2 │ Honda Accord    │    475  │   1,772  │ 3.73x │
│  3 │ Honda CR-V      │    635  │   2,331  │ 3.67x │
│  4 │ Honda Civic     │    459  │   1,537  │ 3.35x │
│  5 │ Toyota Camry    │    842  │   2,730  │ 3.24x │
│  6 │ Hyundai Tucson  │    444  │   1,422  │ 3.20x │
│  7 │ Chevy Silverado │    558  │   1,761  │ 3.16x │
│  8 │ Toyota Corolla  │    687  │   2,160  │ 3.14x │
└────┴─────────────────┴─────────┴──────────┴───────┘

SLOW MOVERS — Lowest Demand-to-Supply Ratio
(ratio <2.5 = over-supplied = AVOID STOCKING)
┌────┬─────────────────┬─────────┬──────────┬───────┐
│  # │ Model           │ Supply  │ Sold 90d │ D:S   │
├────┼─────────────────┼─────────┼──────────┼───────┤
│  1 │ Nissan Altima   │    729  │   1,678  │ 2.30x │
│  2 │ Nissan Rogue    │    902  │   2,310  │ 2.56x │
│  3 │ Jeep Compass    │    746  │   1,883  │ 2.52x │
└────┴─────────────────┴─────────┴──────────┴───────┘

MAKE-LEVEL VELOCITY
┌────┬────────────────┬───────┬─────────────────────┐
│  # │ Make           │ D:S   │ Signal              │
├────┼────────────────┼───────┼─────────────────────┤
│  1 │ Honda          │ 3.53x │ 🔥 Strong demand    │
│  2 │ Toyota         │ 3.51x │ 🔥 Strong demand    │
│  3 │ Subaru         │ 3.41x │ 🔥 Strong demand    │
│  4 │ Mazda          │ 2.99x │ ✅ Healthy           │
│  5 │ Hyundai        │ 2.89x │ ✅ Healthy           │
│  … │ Mercedes-Benz  │ 2.37x │ ⚠️  Over-supplied   │
│  … │ Nissan         │ 2.46x │ ⚠️  Over-supplied   │
└────┴────────────────┴───────┴─────────────────────┘
```
</details>

---

### `stocking-guide` — Pre-Auction VIN Check

**Input:** *"Should I bid on this Sienna at auction?"*
*(2022 Toyota Sienna XLE · VIN 5TDJSKFC2NS055758 · 62,264 mi)*

<details>
<summary><strong>View Output</strong></summary>

```
PRE-AUCTION VIN CHECK: 2022 Toyota Sienna XLE
VIN: 5TDJSKFC2NS055758 · 62,264 mi
═══════════════════════════════════════════════════

VALUATION
  Predicted Retail:    $37,874
  MSRP (new):          $46,750
  Retention:           81.0%

MARKET SUPPLY & DEMAND (75 mi from 60659)
  Active Supply:       23 units
  Sold (90 days):      82 units
  Demand:Supply:       3.57x ← STRONG

SUPPLY STATS (23 active)
  Price range:         $26,995 – $79,990
  Median price:        $35,998
  Median mileage:      55,595
  Median DOM:          56 days ← Fast mover

SOLD STATS (82 recent)
  Sold price range:    $17,999 – $79,990
  Sold median:         $36,649

COMPARABLE ACTIVE LISTINGS
┌───┬──────────┬──────────┬─────┬───────────────────────┐
│ # │  Price   │  Miles   │ DOM │ Dealer                │
├───┼──────────┼──────────┼─────┼───────────────────────┤
│ 1 │ $37,990  │  62,264  │ 183 │ Lakeview Motors       │
│ 2 │ $39,380  │  37,295  │ 117 │ TERA Chevy GMC        │
│ 3 │ $30,938  │ 134,648  │  12 │ Andy Mohr Toyota      │
└───┴──────────┴──────────┴─────┴───────────────────────┘

AUCTION BID CALCULATION
  Target Retail:       $37,874
  Target Margin (15%): - $5,681
  Est. Recon Cost:     - $1,500
  ─────────────────────────────
  MAX BID:             $30,693

═══════════════════════════════════════════════════
  VERDICT: ✅ BUY (if under $30,693)
  D:S ratio of 3.57x = strong demand.
  Median DOM of 56 days = fast turn.
  Floor plan cost at $35/day × 56 days = $1,960.
  Expected gross at retail: ~$5,221.
═══════════════════════════════════════════════════
```
</details>

---

### `depreciation-tracker` — Multi-Year Value Curves

**Input:** *"Show me the depreciation curve for Toyota RAV4 in Illinois"*

<details>
<summary><strong>View Output</strong></summary>

```
DEPRECIATION TRACKER: Toyota RAV4 — Illinois
═══════════════════════════════════════════════════

SOLD PRICE BY MODEL YEAR (past 90 days, IL)
┌──────────┬──────────┬──────────┬──────────┬──────────┬────────┐
│ MY       │ Volume   │ Min      │ Median   │ Max      │ Δ MSRP │
├──────────┼──────────┼──────────┼──────────┼──────────┼────────┤
│ 2024     │ 679 sold │ $21,860  │ $28,499  │ $48,000  │  base  │
│ 2023     │ 368 sold │ $18,329  │ $29,100  │ $48,011  │ +2.1%  │
│ 2022     │ 270 sold │ $16,988  │ $28,814  │ $38,062  │ +1.1%  │
└──────────┴──────────┴──────────┴──────────┴──────────┴────────┘

  Note: 2023/2022 median HIGHER than 2024 — driven
  by trim mix. 2024 has high volume of base-trim
  fleet/rental returns pulling median down. Older
  years have higher-trim survivorship in resale.

PRICE FLOOR ANALYSIS
  2024 floor:  $21,860 (deepest depreciation on newest)
  2023 floor:  $18,329 (−16% from 2024 floor)
  2022 floor:  $16,988 (−22% from 2024 floor)

ACTIVE INVENTORY BREAKDOWN (IL)
┌──────┬──────────┬──────────────────────┐
│ Year │ Active   │ Median Active Price  │
├──────┼──────────┼──────────────────────┤
│ 2024 │  223     │                      │
│ 2023 │   81     │  $28,990 (combined)  │
│ 2022 │   59     │                      │
├──────┼──────────┼──────────────────────┤
│ All  │  363     │  $28,990             │
└──────┴──────────┴──────────────────────┘

  KEY INSIGHT: RAV4 holds value exceptionally well.
  Median sold prices are within 2% across 2022-2024
  model years — one of the strongest retention
  profiles in the SUV segment. Demand:Supply ratio
  of 4.18x in Chicago confirms under-supply.
```
</details>

---

### `market-share-analyzer` — Brand & Segment Analysis

**Input:** *"Who is winning market share in Illinois?"*

<details>
<summary><strong>View Output</strong></summary>

```
MARKET SHARE ANALYSIS: Illinois — Used Vehicles
═══════════════════════════════════════════════════

BRAND MARKET SHARE (past 90 days sold volume)
┌────┬────────────────┬──────────┬────────┬─────────┐
│  # │ Make           │ Sold 90d │ Share  │ Supply  │
├────┼────────────────┼──────────┼────────┼─────────┤
│  1 │ Chevrolet      │  36,503  │ 12.83% │  14,945 │
│  2 │ Ford           │  34,549  │ 12.14% │  14,636 │
│  3 │ Toyota         │  21,818  │  7.67% │   6,822 │
│  4 │ Jeep           │  19,519  │  6.86% │   8,032 │
│  5 │ Nissan         │  16,256  │  5.71% │   6,617 │
│  6 │ Honda          │  16,125  │  5.67% │   4,952 │
│  7 │ Hyundai        │  12,235  │  4.30% │   4,308 │
│  8 │ GMC            │  11,879  │  4.17% │   4,643 │
│  9 │ BMW            │  10,584  │  3.72% │   4,274 │
│ 10 │ KIA            │   9,822  │  3.45% │   3,841 │
│ 11 │ Mercedes-Benz  │   9,013  │  3.17% │   4,015 │
│ 12 │ RAM            │   7,931  │  2.79% │   3,084 │
│ 13 │ Volkswagen     │   7,835  │  2.75% │   2,887 │
│ 14 │ Subaru         │   7,251  │  2.55% │   2,311 │
│ 15 │ Dodge          │   6,355  │  2.23% │   2,589 │
└────┴────────────────┴──────────┴────────┴─────────┘

SEGMENT BREAKDOWN (past 90 days sold)
┌──────────────┬──────────┬────────┐
│ Body Type    │ Sold 90d │ Share  │
├──────────────┼──────────┼────────┤
│ SUV          │ 151,181  │ 53.1%  │
│ Sedan        │  57,753  │ 20.3%  │
│ Pickup       │  37,680  │ 13.2%  │
│ Hatchback    │  10,839  │  3.8%  │
│ Minivan      │   7,619  │  2.7%  │
│ Coupe        │   5,977  │  2.1%  │
│ Convertible  │   3,440  │  1.2%  │
│ Cargo Van    │   2,952  │  1.0%  │
└──────────────┴──────────┴────────┘

SUPPLY vs DEMAND MISMATCH
  Toyota:  6.2% of supply → 7.7% of sales = UNDER-SUPPLIED
  Honda:   4.5% of supply → 5.7% of sales = UNDER-SUPPLIED
  Subaru:  2.1% of supply → 2.5% of sales = UNDER-SUPPLIED
  Jeep:    7.3% of supply → 6.9% of sales = BALANCED
  Chevy:  13.5% of supply → 12.8% of sales = SLIGHTLY OVER
  Ford:   13.2% of supply → 12.1% of sales = SLIGHTLY OVER
  M-Benz:  3.6% of supply → 3.2% of sales = OVER-SUPPLIED

  KEY INSIGHT: Toyota and Honda consistently sell
  faster than their supply share in IL. Chevrolet
  and Ford dominate volume but have proportionally
  more supply sitting. Luxury brands (BMW, Mercedes)
  show the slowest sell-through relative to supply.
```
</details>

---

### `daily-dealer-briefing` — Morning Health Check

**Input:** `/daily-briefing`

<details>
<summary><strong>View Output</strong></summary>

```
DAILY BRIEFING: Lakeview Motors — Mar 6, 2026
═══════════════════════════════════════════════════

AGING INVENTORY ALERT (DOM > 60 days)
┌───┬─────────────────────────────┬──────────┬─────┬──────────┐
│ # │ Vehicle                     │ Asking   │ DOM │ Action   │
├───┼─────────────────────────────┼──────────┼─────┼──────────┤
│ 1 │ 2022 Sienna XLE (62K mi)   │ $37,990  │ 183 │ REDUCE   │
│ 2 │ 2024 Tacoma TRD (18K mi)   │ $41,490  │ 135 │ REDUCE   │
│ 3 │ 2024 Sienna LE (35K mi)    │ $42,990  │ 107 │ REVIEW   │
│ 4 │ 2024 Tundra SR5 (17K mi)   │ $44,490  │  74 │ REVIEW   │
│ 5 │ 2025 Sequoia Ltd (8K mi)   │ $70,990  │  64 │ MONITOR  │
└───┴─────────────────────────────┴──────────┴─────┴──────────┘
  Floor plan burn on aging units: ~$612/day (5 × $35 avg × 3.5)

COMPETITOR PRICE DROPS (last 7 days, 50 mi)
  • Graff Toyota:     2023 Highlander Platinum dropped to $43,872
  • Toyota Naperville: 2024 Tundra SR5 listed at $42,900 (−$1,590 vs you)

TOP 3 ACTIONS TODAY
  1. REDUCE 2022 Sienna XLE by $2,000 → $35,990
     (183 DOM, predicted value $37,874, competitors at $35,998)
  2. REDUCE 2024 Tacoma TRD by $1,500 → $39,990
     (135 DOM, predicted value $39,504, competitor at $39,490)
  3. REVIEW 2025 Sequoia Limited pricing strategy
     (64 DOM, $70,990 — only Sequoia in market, hold if no pressure)
```
</details>

---

### `weekly-dealer-review` — Full Lot Scan + Hot List

**Input:** `/weekly-review`

<details>
<summary><strong>View Output</strong></summary>

```
WEEKLY REVIEW: Lakeview Motors — Week of Mar 2, 2026
═══════════════════════════════════════════════════

LOT SUMMARY
  Total used units:    ~138
  Median asking:       $24,990
  Avg mileage:         41,263 mi

LOT PRICING SCAN (selected units)
┌───┬──────────────────────────┬──────────┬───────────┬────────┬────────────┐
│ # │ Vehicle                  │ Asking   │ Predicted │ Gap    │ Action     │
├───┼──────────────────────────┼──────────┼───────────┼────────┼────────────┤
│ 1 │ 2023 Highlander Platinum │ $48,990  │ $49,126   │ -$136  │ ✅ HOLD    │
│ 2 │ 2025 RAV4 Hybrid XSE    │ $38,990  │ $38,403   │ +$587  │ ✅ HOLD    │
│ 3 │ 2024 Tundra SR5          │ $44,490  │ $43,594   │ +$896  │ ⚠️ REVIEW │
│ 4 │ 2024 Grand Highlander    │ $46,990  │ $46,733   │ +$257  │ ✅ HOLD    │
│ 5 │ 2024 Tacoma TRD          │ $41,490  │ $39,504   │ +$1,986│ 🔴 REDUCE │
│ 6 │ 2022 Sienna XLE          │ $37,990  │ $37,874   │ +$116  │ 🔴 REDUCE │
└───┴──────────────────────────┴──────────┴───────────┴────────┴────────────┘
  (6 of 138 shown — full scan runs all units)

STOCKING HOT LIST (Chicago 30 mi, D:S > 3.0)
┌────┬─────────────────┬───────┬─────────────────────────┐
│  # │ Model           │ D:S   │ Max Auction Bid         │
├────┼─────────────────┼───────┼─────────────────────────┤
│  1 │ Toyota RAV4     │ 4.18x │ Depends on MY/trim/mi   │
│  2 │ Honda Accord    │ 3.73x │ Depends on MY/trim/mi   │
│  3 │ Honda CR-V      │ 3.67x │ Depends on MY/trim/mi   │
│  4 │ Honda Civic     │ 3.35x │ Depends on MY/trim/mi   │
│  5 │ Toyota Camry    │ 3.24x │ Depends on MY/trim/mi   │
└────┴─────────────────┴───────┴─────────────────────────┘

TOP 5 ACTIONS THIS WEEK
  1. DROP Tacoma TRD to $39,990 (135 DOM, $1,986 over predicted)
  2. DROP Sienna XLE to $35,990 (183 DOM, aging + floor plan burn)
  3. SOURCE RAV4s at auction (4.18x D:S = fastest turn in market)
  4. HOLD Highlander Platinum (right-priced, low miles, 29 DOM)
  5. MONITOR Tundra SR5 — $896 above predicted but only 74 DOM
```
</details>

---

### `monthly-dealer-strategy` — 30-Day Strategic Plan

**Input:** `/monthly-strategy`

<details>
<summary><strong>View Output</strong></summary>

```
MONTHLY STRATEGY: Lakeview Motors — March 2026
═══════════════════════════════════════════════════

SECTION 1: BRAND PERFORMANCE (IL Used Market Share)
┌────────────┬──────────┬────────┬──────────────────┐
│ Make       │ Sold 90d │ Share  │ Supply Mismatch  │
├────────────┼──────────┼────────┼──────────────────┤
│ Toyota     │  21,818  │  7.67% │ Under-supplied   │
│ (vs Chevy) │  36,503  │ 12.83% │ Balanced         │
│ (vs Ford)  │  34,549  │ 12.14% │ Slightly over    │
│ (vs Honda) │  16,125  │  5.67% │ Under-supplied   │
└────────────┴──────────┴────────┴──────────────────┘
  Toyota ranks #3 in IL sales volume with only #4 supply
  share — favorable sell-through dynamics.

SECTION 2: DEPRECIATION WATCH (your lot models)
┌────────────────────┬──────────┬──────────┬──────────┐
│ Model              │ 2024 Med │ 2023 Med │ Δ Annual │
├────────────────────┼──────────┼──────────┼──────────┤
│ Toyota RAV4        │ $28,499  │ $29,100  │ +2.1%*   │
│ Toyota Highlander  │ $36,018  │    —     │   —      │
│ Toyota Tundra      │ $47,417  │    —     │   —      │
│ Toyota Sienna      │ $36,649  │    —     │   —      │
└────────────────────┴──────────┴──────────┴──────────┘
  * RAV4 shows inverted depreciation (2023 > 2024) due
    to trim-mix effects. True depreciation is ~$900/yr
    at the floor level.

SECTION 3: MARKET DEMAND (Chicago 30 mi)
  Total active supply:   53,882
  Total sold (90d):     149,939
  Market turnover:       2.78x
  Your franchise brand (Toyota): 3.51x — FASTEST turn

  SUVs = 53% of all sales. Pickup = 13%. Sedan = 20%.

SECTION 4: INVENTORY SCORECARD
  Units on lot:         ~138 used
  Avg DOM:              ~80 days (estimated)
  Units over 60 DOM:    5 identified
  Est. floor plan burn: ~$18,000/month on aging units

SECTION 5: 30-DAY ACTION PLAN
┌────┬──────────────────────────────────────────────────┬──────────┐
│  # │ Action                                           │ Est. $   │
├────┼──────────────────────────────────────────────────┼──────────┤
│  1 │ Clear aging Sienna XLE + Tacoma TRD (price drops)│ +$3,500  │
│  2 │ Source 3-5 RAV4s at auction (4.18x D:S)          │ +$12,000 │
│  3 │ Source 2-3 Honda CR-Vs (3.67x D:S)               │ +$6,000  │
│  4 │ Hold Highlander Platinum pricing (29 DOM, right)  │ held     │
│  5 │ Review Tundra SR5 if no traffic by Day 90         │ TBD      │
├────┼──────────────────────────────────────────────────┼──────────┤
│    │ PROJECTED INCREMENTAL GROSS (30 days)            │ +$21,500 │
└────┴──────────────────────────────────────────────────┴──────────┘
```
</details>

---

## Example Workflows

### Morning Routine (5 min)
```
/daily-briefing
```
→ Aging units over 60 DOM with floor plan burn + competitors who dropped prices + top 3 actions

### Before Auction
```
Check these VINs from tomorrow's Manheim auction:
1HGCV1F3XPA012345
2T3P1RFV8RW654321
5YJ3E1EA8PF789012
```
→ BUY/CAUTION/PASS verdict for each with max bid prices

### Trade-In at the Desk
```
Appraise VIN 2T3P1RFV8RW654321, 32K miles, clean condition
```
→ 60-second valuation with comps and recommended offer range

### Weekly Deep Dive
```
/weekly-review
```
→ Every unit on your lot priced against market + hot list for auction + 5 prioritized actions

---

## UK Dealer Support

UK dealers are supported with competitive pricing using `search_uk_active_cars` and `search_uk_recent_cars`. Select UK during onboarding and enter your postcode.

**Works for UK:** Competitive listing search, price comparisons, active supply scanning, daily briefing (~80% functional)

**US-only:** ML price predictions, VIN decode, market share, depreciation tracking, stocking hot lists, demand-to-supply ratios

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
