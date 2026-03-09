# Lender Plugin — MarketCheck

Automotive market intelligence for **auto lenders, lease companies, and floor plan providers**. Depreciation tracking framed as residual risk, EV transition monitoring for lending exposure, market momentum for portfolio strategy, and collateral valuation.

---

## Who It's For

- Auto loan officers and underwriters
- Lease residual value analysts
- Floor plan lenders
- Portfolio risk managers
- Credit analysts covering auto lending

---

## Skills (5)

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **depreciation-tracker** | "depreciation rate", "residual value", "residual risk", "which cars hold value" | Multi-point depreciation curves framed as residual risk signals. Brand retention tiers, segment comparisons, geographic variance. |
| **vehicle-appraiser** | "collateral value", "what's it worth", "appraise this vehicle" | Collateral valuation with current market value for LTV calculations |
| **market-trends-reporter** | "market trends", "price trends", "lending risk signals" | Market trend intelligence framed for lending risk assessment |
| **ev-transition-monitor** | "EV depreciation risk", "EV adoption", "battery risk" | EV adoption rates, EV vs ICE depreciation comparison, battery depreciation risk for lending portfolios |
| **market-momentum-report** | "market momentum", "sector trends", "portfolio risk" | Segment-level momentum signals for portfolio allocation decisions |

---

## Commands (3)

| Command | What It Does |
|---------|-------------|
| `/onboarding` | Lender profile setup — portfolio focus, LTV thresholds, tracked segments |
| `/vin-lookup` | VIN decode + current value for collateral checks |
| `/setup-mcp` | Configure MCP connection |

---

## Agents (2)

| Agent | What It Does |
|-------|-------------|
| **portfolio-scanner** | Batch VIN revaluation — process portfolio samples to spot underwater loans and high-risk collateral |
| **brand-market-analyst** | Brand-level depreciation and market share intelligence for sector analysis |

---

## Quick Start

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin lender
/setup-mcp YOUR_API_KEY
/onboarding
```

After onboarding, try:
- "Show me the depreciation curve for Tesla Model Y"
- "Compare EV vs ICE residual risk in the SUV segment"
- "Revalue these 20 VINs from our Q1 portfolio sample"

---

## Example Workflows

### Residual Risk Analysis
```
How fast is the Tesla Model Y depreciating? Show me the curve for the past year.
```
→ Multi-point depreciation curve: retention %, monthly rate, annualized rate, curve shape analysis, risk classification

### Portfolio Revaluation
```
Revalue these 20 VINs from our Q1 portfolio sample:
[list of VINs]
```
→ Current value per VIN, LTV recalculation, flags for underwater (LTV > 100%) and high-risk (LTV > 120%)

### EV Lending Risk
```
What's the EV depreciation risk for our portfolio?
```
→ EV vs ICE depreciation comparison by segment, battery age risk factors, residual value forecast implications

### Brand Tier Rankings
```
Rank brands by value retention for our advance rate tables
```
→ Tier 1-4 brand classification by residual retention percentage, with lending risk commentary

---

## Output Framing

All output is framed for lending context:
- Depreciation → **Residual Risk**
- Price trends → **Collateral Value Signals**
- EV adoption → **Portfolio Exposure Risk**
- Market share shifts → **Sector Concentration Risk**

---

## Live Example Outputs

> All examples below use **real market data** framed for auto lending risk context. Lender persona "Midwest Auto Lending" is fictional — used for illustration.

---

### `depreciation-tracker` — Residual Risk by Brand Tier

**Input:** *"Rank brands by value retention for our advance rate tables"*

<details>
<summary><strong>View Output</strong></summary>

```
BRAND RETENTION TIERS — Ohio Market (Residual Risk Analysis)
Midwest Auto Lending · March 2026
═══════════════════════════════════════════════════════════════

Data: Sold transactions (past 90 days), Ohio statewide
═══════════════════════════════════════════════════════════════

TIER 1 — PREMIUM RETENTION (Low Residual Risk)
Advance Rate: Up to 90% LTV
┌───────────┬──────────────┬────────────────┬──────────────────────────────────────┐
│ Brand     │ Median Sold  │ Vol (90d, OH)  │ Lending Signal                       │
├───────────┼──────────────┼────────────────┼──────────────────────────────────────┤
│ Toyota    │   $34,251    │   42,406 units │ Strong D:S, low DOM, collateral-safe │
│ Honda     │   $30,078    │   48,466 units │ Proven demand, consistent floor       │
└───────────┴──────────────┴────────────────┴──────────────────────────────────────┘

TIER 2 — SOLID RETENTION (Moderate-Low Residual Risk)
Advance Rate: Up to 85% LTV
┌───────────┬──────────────┬────────────────┬──────────────────────────────────────┐
│ Brand     │ Median Sold  │ Vol (90d, OH)  │ Lending Signal                       │
├───────────┼──────────────┼────────────────┼──────────────────────────────────────┤
│ Chevrolet │   $28,666    │   73,679 units │ High volume, balanced supply/demand   │
│ Jeep      │   $30,083    │   35,292 units │ Acceptable retention, watch aging     │
└───────────┴──────────────┴────────────────┴──────────────────────────────────────┘

TIER 3 — MODERATE RETENTION (Elevated Residual Risk)
Advance Rate: Up to 80% LTV
┌───────────┬──────────────┬────────────────┬──────────────────────────────────────┐
│ Brand     │ Median Sold  │ Vol (90d, OH)  │ Lending Signal                       │
├───────────┼──────────────┼────────────────┼──────────────────────────────────────┤
│ Ford      │   $35,458    │   74,989 units │ High $ but wide variance, price risk │
│ Nissan    │   $22,484    │   24,874 units │ Weaker floor, higher LTV exposure    │
└───────────┴──────────────┴────────────────┴──────────────────────────────────────┘

TIER 4 — HIGH VOLATILITY (High Residual Risk)
Advance Rate: Max 75% LTV · Enhanced monitoring required
┌───────────┬──────────────┬────────────────┬──────────────────────────────────────┐
│ Brand     │ Median Sold  │ Vol (90d, OH)  │ Lending Signal                       │
├───────────┼──────────────┼────────────────┼──────────────────────────────────────┤
│ BMW       │   $45,376    │    8,711 units │ High $ luxury — thin demand, slow    │
│           │              │                │ liquidation, concentration risk       │
└───────────┴──────────────┴────────────────┴──────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
LENDING POLICY RECOMMENDATIONS
  → Tier 1 (Toyota/Honda): Standard advance rates, lower reserve requirements
  → Tier 2 (Chevy/Jeep): Standard rates, monitor aging in portfolio reviews
  → Tier 3 (Ford/Nissan): Tighten LTV at origination by 5%; flag for quarterly
    revaluation at 12+ months
  → Tier 4 (BMW/Luxury): Require independent appraisal; 75% LTV hard cap;
    increased loss reserve allocation
═══════════════════════════════════════════════════════════════
```
</details>

---

### `vehicle-appraiser` — Collateral Valuation

**Input:** *"Collateral check on VIN 5TFLA5DB8RX204441, 16,930 miles — we have a $40,000 loan against this"*
*(2024 Toyota Tundra SR5 4WD)*

<details>
<summary><strong>View Output</strong></summary>

```
COLLATERAL VALUATION: 2024 Toyota Tundra SR5 4WD
VIN: 5TFLA5DB8RX204441 · 16,930 mi · ZIP 43004 (Columbus, OH)
Midwest Auto Lending · Loan Balance: $40,000
═══════════════════════════════════════════════════════════════

MARKET VALUATION
┌──────────────────────────────┬────────────┐
│ Source                       │ Value      │
├──────────────────────────────┼────────────┤
│ ML Prediction (Franchise)    │ $43,556    │
│ Active Comp Median (283)     │ $44,850    │
│ Sold Median (26 recent)      │ $44,160    │
├──────────────────────────────┼────────────┤
│ ★ Collateral Estimate        │ $44,189    │
│ MSRP (new sticker)           │ $54,228    │
│ Depreciation from MSRP       │ -$10,039   │
│ MSRP Retention               │ 81.5%      │
└──────────────────────────────┴────────────┘
  Confidence: HIGH (283 active + 26 sold comps, Columbus area)

LTV ANALYSIS
┌──────────────────────────────┬────────────┐
│ Current Loan Balance         │ $40,000    │
│ Collateral Estimate          │ $44,189    │
│ Current LTV                  │ 90.5%      │
│ LTV Status                   │ ACCEPTABLE │
│ Equity Cushion               │ $4,189     │
└──────────────────────────────┴────────────┘

COMPARABLE ACTIVE LISTINGS (SR5 trim, 100 mi from Columbus)
┌───┬──────────┬─────────┬─────┬──────────────────────────────┐
│ # │  Price   │  Miles  │ DOM │ Dealer (Dist from Collateral) │
├───┼──────────┼─────────┼─────┼──────────────────────────────┤
│ 1 │ $48,890  │ 21,517  │ 410 │ Excite Auto (7.9 mi)         │
│ 2 │ $44,850  │ 30,104  │  30 │ Byers Subaru Dublin (16.1 mi)│
│ 3 │ $46,595  │  7,847  │  95 │ Toyota West (18.1 mi)        │
│ 4 │ $46,191  │ 19,165  │ 140 │ Nourse Ford Lincoln (47.1 mi)│
│ 5 │ $43,500  │ 38,843  │  49 │ White-Allen Chevrolet (75 mi)│
└───┴──────────┴─────────┴─────┴──────────────────────────────┘

RECENT SOLD COMPARABLES (past 90 days)
  Sold count:        26 transactions
  Sold range:        $38,994 – $48,951
  Sold median:       $44,160
  Sold mean:         $44,121

RISK CLASSIFICATION
  ┌─────────────────────────────────────────────────────┐
  │ STATUS: LOW RISK — Collateral is adequately secured │
  │ LTV of 90.5% within acceptable range for this       │
  │ collateral type. Toyota Tundra SR5 shows strong     │
  │ residual retention at 81.5% of MSRP at 16,930 mi.  │
  │ 283 active comps confirm liquid market.             │
  │                                                     │
  │ REVALUATION TRIGGER: Flag if mileage exceeds        │
  │ 45,000 mi or loan balance rises above $43,000.      │
  └─────────────────────────────────────────────────────┘
```
</details>

---

### `ev-transition-monitor` — EV Portfolio Exposure Risk

**Input:** *"What's the EV depreciation risk for our Tesla portfolio? We have 450 Model Y loans"*

<details>
<summary><strong>View Output</strong></summary>

```
EV PORTFOLIO RISK MONITOR: Tesla Model Y
Midwest Auto Lending · 450 Model Y loans · March 2026
═══════════════════════════════════════════════════════════════

EV vs ICE DEPRECIATION COMPARISON (Ohio Market, past 90 days)
┌─────────────────────┬──────────────┬─────────────┬──────────────┬──────────────┐
│ Vehicle             │ Sold Vol(OH) │ Median Sold │ Price Range  │ Retention    │
├─────────────────────┼──────────────┼─────────────┼──────────────┼──────────────┤
│ Tesla Model Y (BEV) │  669 units   │   $28,999   │$17K – $53K   │ ~57% MSRP   │
│ Toyota RAV4 (ICE)   │ 6,728 units  │   $32,414   │$2.3K – $55K  │ ~87% MSRP*  │
└─────────────────────┴──────────────┴─────────────┴──────────────┴──────────────┘
  * RAV4 MSRP ~$37,000 base; Model Y MSRP ~$50,000+ (2022 vintage)
  → ICE SUV comp (RAV4) retains ~30% MORE collateral value vs Tesla Model Y

TESLA MODEL Y — ACTIVE MARKET SNAPSHOT (Ohio)
  Active listings:     203 units
  Price range:         $17,990 – $54,999
  Median ask:          $29,994
  Average ask:         $31,113
  Sold past 90d (OH):  669 units | Median sold: $28,999
  Percentile P25:      $26,359 | P75: $33,050

PORTFOLIO RISK SIGNALS — 450 MODEL Y LOANS
  Avg loan assumed ($40K):   Portfolio exposure: ~$18,000,000
  Market median collateral:  ~$29,994 per unit
  Implied portfolio LTV:     ~133% (UNDERWATER — if avg loan balance $40K)

  ⚠ ALERT: Tesla Model Y market prices have declined significantly.
    At median market value of $29,994, a typical $40K loan is
    ~$10,000 underwater. Immediate revaluation recommended.

EV DEPRECIATION RISK FACTORS
  1. Software/OTA updates affect resale perception (unpredictable)
  2. New model year releases compress prior-year values rapidly
  3. Federal EV tax credit changes directly impact used EV pricing
  4. Battery degradation uncertainty adds liquidation risk
  5. Thin dealer network for remarketing vs ICE vehicles

BATTERY AGE RISK TABLE
┌──────────────┬──────────────────┬────────────────────────────────────────┐
│ Battery Age  │ Typical Range    │ Lending Risk                           │
├──────────────┼──────────────────┼────────────────────────────────────────┤
│ 0-2 years    │ ~95% capacity    │ LOW — accept standard LTV              │
│ 3-5 years    │ ~88-92% capacity │ MODERATE — reduce advance rate 5%      │
│ 6+ years     │ <85% capacity    │ HIGH — require battery health report   │
└──────────────┴──────────────────┴────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
PORTFOLIO RECOMMENDATION
  → Conduct immediate batch revaluation of all 450 Model Y loans
  → Set LTV ceiling at 80% for new Tesla originations
  → Reserve 8-12% loss provision on EV portfolio vs 3-5% for ICE
  → Consider concentration cap: max 15% EV exposure in any segment
═══════════════════════════════════════════════════════════════
```
</details>

---

### `market-momentum-report` — Portfolio Allocation Signals

**Input:** *"Give me segment momentum signals for our Q2 portfolio allocation decisions"*

<details>
<summary><strong>View Output</strong></summary>

```
SEGMENT MOMENTUM REPORT: Ohio Market
Midwest Auto Lending · Q2 2026 Portfolio Allocation
═══════════════════════════════════════════════════════════════

ACTIVE SUPPLY BY SEGMENT (Ohio, all used)
Total active inventory: 114,625 units

SEGMENT MOMENTUM TABLE
┌──────────────┬──────────┬──────────────┬──────────────┬───────────┬──────────────────────────────┐
│ Segment      │ Active   │  Sold (90d)  │ Median Sold  │ Signal    │ Portfolio Implication         │
├──────────────┼──────────┼──────────────┼──────────────┼───────────┼──────────────────────────────┤
│ SUV          │  55,179  │  295,893     │   $31,994    │ BULLISH   │ Core collateral — favor       │
│ Pickup       │  18,932  │   96,620     │   $43,093    │ BULLISH   │ High $ loans, strong demand  │
│ Sedan        │  23,153  │   84,540     │   $20,560    │ NEUTRAL   │ Lower LTV exposure, stable   │
│ Hatchback    │   4,794  │     —        │      —       │ NEUTRAL   │ Low-value; limit exposure    │
│ Minivan      │   3,324  │    2,399*    │   $46,101*   │ NEUTRAL   │ Hybrid Siennas: watch EV risk│
│ Coupe        │   2,168  │     —        │      —       │ BEARISH   │ Niche segment; thin liquidity│
│ Cargo Van    │   1,687  │     —        │      —       │ BEARISH   │ Commercial — special handling│
└──────────────┴──────────┴──────────────┴──────────────┴───────────┴──────────────────────────────┘
  * Minivan sold data = Toyota Sienna (OH); broader minivan sold volume higher

TOP MAKES BY ACTIVE SUPPLY (Ohio)
┌────┬────────────────┬──────────┬───────┐
│  # │ Make           │  Active  │   %   │
├────┼────────────────┼──────────┼───────┤
│  1 │ Chevrolet      │  17,560  │ 15.3% │
│  2 │ Ford           │  16,420  │ 14.3% │
│  3 │ Jeep           │   8,773  │  7.7% │
│  4 │ Honda          │   7,728  │  6.7% │
│  5 │ Toyota         │   6,708  │  5.9% │
│  6 │ Nissan         │   5,633  │  4.9% │
│  7 │ KIA            │   5,114  │  4.5% │
│  8 │ GMC            │   4,876  │  4.3% │
│  9 │ Hyundai        │   4,551  │  4.0% │
│ 10 │ RAM            │   4,148  │  3.6% │
└────┴────────────────┴──────────┴───────┘

Q2 PORTFOLIO ALLOCATION SIGNALS
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│ INCREASE EXPOSURE (Bullish)                  │ REDUCE EXPOSURE (Bearish)                    │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ SUV segment (Toyota, Honda brands)           │ EV/BEV collateral (depreciation risk)        │
│ Pickup trucks (Tundra, F-150, Silverado)     │ Luxury/Coupe segments (thin liquidity)       │
│ Tier 1 brands (Toyota, Honda) — see above    │ High-mileage Nissan, Jeep at full advance    │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
```
</details>

---

### `market-trends-reporter` — Monthly Lending Risk Report

**Input:** *"Monthly lending risk report — market trends for March 2026"*

<details>
<summary><strong>View Output</strong></summary>

```
MARKET TRENDS — LENDING RISK REPORT
Midwest Auto Lending · Ohio Market · March 2026
═══════════════════════════════════════════════════════════════

MARKET OVERVIEW
  Active Ohio Inventory:    114,625 used units
  Ohio Sold (90 days):      ~600,000+ transactions (all makes)
  Market Median Price:      ~$28,000–$35,000 (varies by segment)
  Top Supply Segments:      SUV (48.1%), Pickup (16.5%), Sedan (20.2%)

PRICE TREND SIGNALS BY MAKE (Ohio, past 90 days)
┌────────────────┬──────────────┬──────────────┬──────────────────────────────────┐
│ Make           │ Median Sold  │ Vol (90d)    │ Collateral Value Signal          │
├────────────────┼──────────────┼──────────────┼──────────────────────────────────┤
│ Toyota         │   $34,251    │  42,406      │ STABLE — strong demand, low risk │
│ Honda          │   $30,078    │  48,466      │ STABLE — high volume, consistent │
│ Chevrolet      │   $28,666    │  73,679      │ STABLE — dominant market share   │
│ Jeep           │   $30,083    │  35,292      │ WATCH — wide variance $1.5K–540K │
│ Ford           │   $35,458    │  74,989      │ WATCH — high $ avg, wide spread  │
│ Nissan         │   $22,484    │  24,874      │ CAUTION — lower floor, weak ICV  │
│ BMW (Luxury)   │   $45,376    │   8,711      │ CAUTION — thin volume, slow DOM  │
└────────────────┴──────────────┴──────────────┴──────────────────────────────────┘

COLLATERAL VALUE RISK FACTORS — MARCH 2026
  1. EV PRICE EROSION: Tesla Model Y median at $28,999 — down significantly
     from origination values; portfolio revaluation overdue
  2. LUXURY SEGMENT: BMW median $45,376 but only 8,711 sold (90d) in OH —
     thin liquidation pool = extended loss timelines if repossessed
  3. SUV DOMINANCE: 48.1% of active inventory is SUV — favorable for
     collateral liquidity; Toyota/Honda SUVs most liquid
  4. PICKUP STRENGTH: Pickup trucks (18,932 active, median sold $43,093)
     remain strong collateral, especially domestic full-size trucks

LENDING RISK RECOMMENDATIONS
  ┌──────────────────────────────────────────────────────────────────┐
  │ HIGH CONFIDENCE collateral: Toyota, Honda (all segments)        │
  │   → Maintain standard advance rates; lowest repossession risk   │
  │                                                                  │
  │ MONITOR: Ford F-Series, Chevrolet Silverado, RAM 1500           │
  │   → Strong market but high $ — ensure income verification       │
  │                                                                  │
  │ TIGHTEN: Tesla BEV, Nissan across portfolio                     │
  │   → Require updated appraisal at 12-month anniversary           │
  │                                                                  │
  │ RESTRICT: BMW, Mercedes-Benz, Coupe/Convertible segments        │
  │   → Max 75% LTV; dealer-only origination preferred              │
  └──────────────────────────────────────────────────────────────────┘
```
</details>

---

### `/vin-lookup` — Collateral Check

**Input:** `/vin-lookup 5TDJSKFC2NS055758`
*(2022 Toyota Sienna XLE 7-Passenger Hybrid AWD · 62,264 mi)*

<details>
<summary><strong>View Output</strong></summary>

```
VIN COLLATERAL CHECK: 5TDJSKFC2NS055758
═══════════════════════════════════════════════════════════════

VEHICLE SPECIFICATIONS
  Year:          2022
  Make/Model:    Toyota Sienna
  Trim:          XLE 7-Passenger Hybrid AWD
  Version:       XLE 7-Passenger Hybrid AWD
  Body:          Minivan · 7 seats
  Engine:        2.5L I4 Hybrid
  Transmission:  CVT
  Drivetrain:    AWD
  Fuel:          Hybrid (Unleaded)
  MPG:           35 city / 36 hwy
  Powertrain:    Hybrid Electric (HEV)

COLORS
  Exterior:      Sunset Bronze Mica (Orange)
  Interior:      Chateau SofTex (Beige)

MSRP (new):    $42,575
VIN MSRP:      $46,750 (with options)

═══════════════════════════════════════════════════════════════

COLLATERAL VALUATION (62,264 mi, ZIP 43004)
┌──────────────────────────────┬────────────┐
│ Source                       │ Value      │
├──────────────────────────────┼────────────┤
│ ML Prediction (Franchise)    │ $38,096    │
│ Active Comp Median (17)      │ $39,380    │
│ Sold Median (2 recent)       │ $32,166    │
├──────────────────────────────┼────────────┤
│ ★ Collateral Estimate        │ $36,547    │
│ vs MSRP                      │ -$10,203   │
│ MSRP Retention               │ 78.1%      │
└──────────────────────────────┴────────────┘
  Note: Hybrid AWD Sienna holds value well — 78.1%
  retention at 62,264 mi is above-average for minivan
  segment. Limited active comps (17 nationally) reflects
  genuine market scarcity.

COMPARABLE ACTIVE LISTINGS (2022 Sienna XLE)
┌───┬──────────┬──────────┬─────┬────────────────────────────────┐
│ # │  Price   │  Miles   │ DOM │ Dealer                         │
├───┼──────────┼──────────┼─────┼────────────────────────────────┤
│ 1 │ $29,500  │ 113,178  │  28 │ Toyota Direct (Columbus, 5.7mi)│
│ 2 │ $37,171  │  70,109  │  67 │ Diehl Volkswagen (Butler, PA)  │
│ 3 │ $30,938  │ 134,648  │  14 │ Andy Mohr Toyota (Avon, IN)    │
│ 4 │ $37,990  │  62,264  │ 185 │ Chicago Northside Toyota (IL)  │
│ 5 │ $39,380  │  37,295  │ 119 │ TERA Chevrolet GMC (IL)        │
└───┴──────────┴──────────┴─────┴────────────────────────────────┘

LTV ANALYSIS
  Collateral Estimate:  $36,547
  Market Active Range:  $29,500 – $74,999 (incl. wheelchair conv.)
  Standard comps range: $29,500 – $41,777 (excl. specialty)

  At $36,547 estimated value:
  → 80% LTV advance = max loan $29,238
  → 85% LTV advance = max loan $31,065
  → 90% LTV advance = max loan $32,892

  RISK NOTE: 185 DOM on Chicago unit signals liquidity
  risk. Columbus-area Toyota Direct has unit at $29,500
  (113K mi) — sets a local price floor for this model.
  Recommend 85% max LTV at origination for this VIN.
═══════════════════════════════════════════════════════════════
```
</details>

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
