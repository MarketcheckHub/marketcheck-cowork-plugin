# Insurer Plugin — MarketCheck

Automotive market intelligence for **insurance companies and adjusters**. Total-loss claims valuation, settlement pricing with cited comparables, vehicle appraisal for insurance context, depreciation tracking for reserves, and market trends for risk assessment.

---

## Who It's For

- Insurance adjusters (total-loss specialists)
- Claims managers
- Underwriters assessing vehicle risk
- Salvage and subrogation analysts

---

## Skills (4)

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **claims-valuation** | "total loss valuation", "settlement offer", "salvage estimate", "what's the claim worth" | Purpose-built for insurance: pre-loss FMV determination, total-loss threshold check, settlement range (low/mid/high), salvage estimation. All backed by cited comparables for dispute resolution. |
| **vehicle-appraiser** | "appraise this vehicle", "fair market value", "pre-loss value" | Comparable-backed valuation adapted for insurance adjuster context |
| **depreciation-tracker** | "depreciation rate", "claim reserve trends", "value retention" | Depreciation intelligence for claim reserve forecasting and replacement cost tracking |
| **market-trends-reporter** | "market trends", "replacement cost trends", "price direction" | Market trend analysis for insurance risk assessment and reserve planning |

---

## Commands (3)

| Command | What It Does |
|---------|-------------|
| `/onboarding` | Insurer profile setup — role, claim types, total-loss threshold %, default comp radius |
| `/vin-lookup` | VIN decode + value for claims processing |
| `/setup-mcp` | Configure MCP connection |

---

## Agents (2)

| Agent | What It Does |
|-------|-------------|
| **portfolio-scanner** | Batch VIN processing for fleet claims or portfolio revaluation |
| **brand-market-analyst** | Brand/segment depreciation and market intelligence for actuarial context |

---

## Quick Start

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin insurer
/setup-mcp YOUR_API_KEY
/onboarding
```

After onboarding, try:
- "Total loss valuation for VIN 1HGCV1F3XPA123456, 45K miles, average condition"
- "What's the settlement range for this vehicle?"
- "Process these 10 claim VINs"

---

## Example Workflows

### Total-Loss Determination
```
Total loss valuation for VIN 5YJ3E1EA8PF123456, 28,400 miles,
average condition, date of loss 2024-01-15
```
→ Pre-loss FMV + total-loss threshold check + settlement range (low/mid/high) + salvage estimate + 18 cited comps

### Settlement Pricing
```
What should our settlement offer be for this 2022 RAV4?
VIN 2T3P1RFV8RW654321, 42K miles, clean condition
```
→ FMV determination + settlement range with low/mid/high offers + comparable evidence for dispute support

### Batch Claims Processing
```
Process these 10 VINs from today's total-loss queue:
[list of VINs with mileage and condition]
```
→ Portfolio scanner runs each through claims valuation, outputs settlement recommendations per VIN

### Depreciation Reserve Analysis
```
How fast are Tesla Model 3s depreciating? We have 200 policies on them.
```
→ Depreciation curve + reserve impact estimate + comparison to segment average

---

## Claims Valuation Methodology

The claims-valuation skill uses a structured approach:

1. **VIN decode** — exact specs, original MSRP
2. **Three-source FMV** — franchise retail prediction, independent retail prediction, condition adjustment
3. **Comparable evidence** — active listings + sold transactions within comp radius (default 100 mi)
4. **Total-loss threshold** — FMV × threshold % (default 75%) to determine total-loss vs repair
5. **Settlement range** — low (conservative), mid (recommended), high (generous) with rationale
6. **Salvage estimate** — based on condition, damage type, and salvage auction data

All values are backed by cited comparables for defensibility in dispute resolution.

---

## Live Example Outputs

> All examples below use **real market data** framed for insurance claims context. Adjuster persona "National Claims Services" is fictional — used for illustration.

---

### `claims-valuation` — Total Loss Determination

**Input:** *"Total loss valuation for VIN JTME6RFV2SD579127, 19,255 miles, good condition, date of loss March 4, 2026"*
*(2025 Toyota RAV4 Hybrid XSE AWD)*

<details>
<summary><strong>View Output</strong></summary>

```
CLAIMS VALUATION: JTME6RFV2SD579127
National Claims Services · Phoenix, AZ · Date of Loss: Mar 4, 2026
═══════════════════════════════════════════════════════════════════

VEHICLE
  2025 Toyota RAV4 Hybrid XSE AWD
  Engine: 2.5L I4 · CVT · 4WD · HEV
  MPG: 43 city / 38 hwy · Ext: Silver Sky/Midnight Black
  Original MSRP (combined): $40,835

PRE-LOSS FAIR MARKET VALUE
┌───────────────────────────────────────┬────────────┐
│ Source                                │ Value      │
├───────────────────────────────────────┼────────────┤
│ ML Prediction (Franchise, 19,255 mi)  │ $38,132    │
│ Active Comp Median (14 XSE units)     │ $41,942    │
│ Recent Sold Median  (8 units, AZ)     │ $41,491    │
├───────────────────────────────────────┼────────────┤
│ ★ Blended Pre-Loss FMV               │ $40,522    │
└───────────────────────────────────────┴────────────┘

TOTAL-LOSS ANALYSIS
  Pre-Loss FMV:                  $40,522
  Total-loss threshold (75%):    $30,392
  Repair estimate:               [TBD — adjuster input]
  → If repair estimate > $30,392: TOTAL LOSS
  → If repair estimate ≤ $30,392: REPAIR

SETTLEMENT RANGE
  Low  (conservative — P25 comp):   $38,132
  Mid  (recommended — blended FMV): $40,522
  High (generous — P75 comp):       $41,942

SALVAGE ESTIMATE
  Estimated salvage value:           $4,050 – $6,000
  (10–15% of FMV; final value subject to auction)
  Net settlement after salvage (mid): ~$34,522 – $36,472

COMPARABLE EVIDENCE (XSE trim, franchise dealers, AZ/Southwest)
┌───┬──────────┬─────────┬─────┬──────────────────────────────┐
│ # │  Price   │  Miles  │ DOM │ Dealer                       │
├───┼──────────┼─────────┼─────┼──────────────────────────────┤
│ 1 │ $41,888  │  5,360  │  30 │ Camelback Toyota (4 mi)      │
│ 2 │ $38,872  │ 19,003  │  84 │ Bill Luke Santan (21 mi)     │
│ 3 │ $39,990  │ 24,584  │  44 │ Toyota Of San Bernardino     │
│ 4 │ $41,523  │  9,977  │  13 │ Pat Lobb Toyota Of McKinney  │
│ 5 │ $40,895  │  9,924  │  28 │ Brandon Tomes Volkswagen     │
└───┴──────────┴─────────┴─────┴──────────────────────────────┘
  Active comps: 14 XSE units | Price range: $38,872 – $45,999
  Recent sold (AZ, 90d): 8 units | Sold median: $41,491

  COMPARABLE DATA: Defensible per NAIC total-loss standards.
  All comparables are same year/trim. Mileage adjustments
  applied via ML model. Ready for dispute documentation.
```
</details>

---

### `vehicle-appraiser` — Pre-Loss Fair Market Value

**Input:** *"What's the pre-loss fair market value for VIN 5TDEBRCH0PS123584, 13,182 miles, excellent condition?"*
*(2023 Toyota Highlander Hybrid Platinum)*

<details>
<summary><strong>View Output</strong></summary>

```
VEHICLE APPRAISAL (PRE-LOSS): 2023 Toyota Highlander Hybrid Platinum
VIN: 5TDEBRCH0PS123584 · 13,182 mi · ZIP 85001 · Excellent Condition
═══════════════════════════════════════════════════════════════════

THREE-SOURCE FAIR MARKET VALUE
┌──────────────────────────────────┬────────────┐
│ Source                           │ Value      │
├──────────────────────────────────┼────────────┤
│ ML Prediction (Franchise)        │ $49,165    │
│ Active Comp Median  (8 Platinum) │ $45,490    │
│ Recent Sold Median  (no AZ data) │ — (sparse) │
├──────────────────────────────────┼────────────┤
│ ★ Weighted Pre-Loss FMV         │ $47,960    │
│   MSRP when new                  │ $54,845    │
│   Depreciation from MSRP         │ -$6,885    │
│   MSRP Retention                 │ 87.4%      │
└──────────────────────────────────┴────────────┘
  Confidence: MODERATE (8 active Platinum comps, no recent
  sold in AZ radius — national comps used)

CONDITION ADJUSTMENT NOTE
  VIN appraised at EXCELLENT condition. Market comps reflect
  mixed condition. No downward adjustment applied — excellent
  condition supports upper range of FMV estimate.
  Adjuster: document condition photos for file.

COMPARABLE LISTINGS (Platinum trim, franchise dealers)
┌───┬──────────┬─────────┬─────┬───────────────────────────────┐
│ # │  Price   │  Miles  │ DOM │ Dealer (Distance)             │
├───┼──────────┼─────────┼─────┼───────────────────────────────┤
│ 1 │ $45,991  │ 37,307  │  36 │ BMW Of Las Vegas (259 mi)     │
│ 2 │ $46,709  │ 28,781  │  28 │ Grapevine Honda (866 mi)      │
│ 3 │ $44,988  │ 27,705  │  72 │ Denny Menholt Chevrolet       │
│ 4 │ $47,459  │ 30,334  │  11 │ Toyota Of Plano (879 mi)      │
│ 5 │ $47,498  │ 26,699  │  35 │ Toyota Of Tri-Cities (959 mi) │
└───┴──────────┴─────────┴─────┴───────────────────────────────┘
  Note: Platinum trim is nationally scarce — 8 active units
  found within extended radius. Low local supply supports
  upper-end FMV valuation.

APPRAISAL SUMMARY FOR CLAIM FILE
  Pre-Loss FMV:          $47,960
  FMV Range (defensible): $44,988 – $49,165
  Recommended reserve:   $47,960
  Supporting comps:      8 active (national)
  Condition note:        Excellent — no downward adj.
```
</details>

---

### `depreciation-tracker` — Reserve Forecasting

**Input:** *"We have 300 Honda CR-V policies. How fast are they depreciating? Need to update our claim reserves"*

<details>
<summary><strong>View Output</strong></summary>

```
DEPRECIATION TRACKER: Honda CR-V — Arizona Market
National Claims Services · 300 policies · Reserve Update
═══════════════════════════════════════════════════════════════════

SOLD PRICE TREND BY MODEL YEAR (New vehicles, AZ, monthly avg)
Source: MarketCheck sold summary — 12-month trend

┌─────────┬──────────────┬──────────────┬─────────────┬──────────┐
│ Month   │ Units Sold   │ Avg Sale     │ Avg MSRP    │ % v MSRP │
├─────────┼──────────────┼──────────────┼─────────────┼──────────┤
│ 2025-07 │     556      │   $37,563    │  $38,243    │  -1.78%  │
│ 2025-06 │     604      │   $37,140    │  $37,919    │  -2.06%  │
│ 2025-05 │     654      │   $37,000    │  $37,719    │  -1.91%  │
│ 2025-04 │     732      │   $37,055    │  $37,757    │  -1.86%  │
│ 2025-03 │     775      │   $37,187    │  $38,143    │  -2.50%  │
│ 2025-02 │     503      │   $36,966    │  $37,840    │  -2.31%  │
│ 2025-01 │     599      │   $36,931    │  $37,728    │  -2.11%  │
│ 2024-12 │     698      │   $37,447    │  $37,956    │  -1.34%  │
│ 2024-11 │     576      │   $37,155    │  $37,886    │  -1.93%  │
│ 2024-10 │     639      │   $37,264    │  $38,045    │  -2.05%  │
│ 2024-09 │     556      │   $36,906    │  $37,785    │  -2.33%  │
│ 2024-08 │     620      │   $36,752    │  $37,609    │  -2.28%  │
└─────────┴──────────────┴──────────────┴─────────────┴──────────┘

ANNUAL DEPRECIATION RATE (Used CR-Vs, AZ, past 90 days)
  Active used CR-V supply (AZ):       1,591 units
  Active median asking price:         $36,850
  Used sold median (AZ, past 90d):    $35,318
  Price range (used sold):            $3,988 – $46,450
  Avg days on market:                 ~45-61 days (new)

DEPRECIATION CURVE ESTIMATE
  MSRP (new 2025 CR-V):     ~$38,100
  Year 1 depreciation:      ~$3,200 (8.4% — new off lot)
  Year 2-3 retention:        82-87% of MSRP typical
  5-year residual estimate:  ~$22,000 – $24,000
  Annual $ loss (Yr 1-3):    ~$3,000 – $4,500 / year

RESERVE IMPACT TABLE (300 policy portfolio)
┌──────────────────────────────────┬──────────────┬──────────────┐
│ Scenario                         │ Per-Vehicle  │ Portfolio    │
├──────────────────────────────────┼──────────────┼──────────────┤
│ Current avg claim FMV (mid)      │   $36,850    │ $11,055,000  │
│ 6-month depreciation (~1.5%)     │   -$553      │   -$165,900  │
│ 12-month depreciation (~3.5%)    │  -$1,290     │   -$387,000  │
│ Recommended reserve floor (Yr 2) │   $33,500    │ $10,050,000  │
└──────────────────────────────────┴──────────────┴──────────────┘

  KEY INSIGHT: CR-V holds value well — consistently selling
  within 1.3–2.5% of MSRP in AZ. Reserve reductions can be
  modest (~3.5%/yr) vs. more volatile segments. Stable DOM
  (avg 45-61 days) confirms strong demand and defensible FMV.
  Recommend quarterly reserve review for model years 2022+.
```
</details>

---

### `market-trends-reporter` — Replacement Cost Trends

**Input:** *"Replacement cost trends report for March 2026 — which segments are seeing price increases?"*

<details>
<summary><strong>View Output</strong></summary>

```
REPLACEMENT COST TRENDS: Arizona Market — March 2026
National Claims Services · Risk Assessment & Reserve Planning
═══════════════════════════════════════════════════════════════════

ARIZONA MARKET OVERVIEW (as of Mar 7, 2026)
  Active supply (all makes/types):   132,260 listings
  Recent sold (past 90 days):        311,680 transactions
  Active median asking price:         $35,162
  Sold median price (90d):            $32,990
  Market turnover rate:               2.36x

TOP MAKES BY ACTIVE SUPPLY (Arizona)
┌────┬────────────────┬─────────┬────────┐
│  # │ Make           │  Count  │ Share  │
├────┼────────────────┼─────────┼────────┤
│  1 │ Ford           │  17,145 │ 13.0%  │
│  2 │ Toyota         │  13,458 │ 10.2%  │
│  3 │ Chevrolet      │  13,233 │ 10.0%  │
│  4 │ Nissan         │   9,831 │  7.4%  │
│  5 │ Hyundai        │   8,946 │  6.8%  │
│  6 │ Jeep           │   8,641 │  6.5%  │
│  7 │ KIA            │   7,751 │  5.9%  │
│  8 │ Honda          │   6,287 │  4.8%  │
│  9 │ RAM            │   6,062 │  4.6%  │
│ 10 │ GMC            │   4,736 │  3.6%  │
└────┴────────────────┴─────────┴────────┘

SEGMENT REPLACEMENT COST SNAPSHOT (AZ, Active Inventory)
┌──────────────────────┬──────────┬──────────┬──────────────────┐
│ Segment              │ Median   │ Supply   │ Claims Implication│
├──────────────────────┼──────────┼──────────┼──────────────────┤
│ Toyota RAV4 (all)    │ $39,263  │   432    │ HIGH — under-    │
│                      │          │          │ supplied, rising  │
│ Honda CR-V (all AZ)  │ $36,850  │  1,591   │ STABLE — good    │
│                      │          │          │ comp availability │
│ Toyota Highlander    │ $33,603  │   413    │ MODERATE — wide  │
│   (all years, AZ)    │          │          │ MY spread        │
│ Toyota Tundra (AZ)   │ $55,513  │  5,060   │ HIGH — new model │
│                      │          │          │ premium, rising   │
└──────────────────────┴──────────┴──────────┴──────────────────┘

PRICE DISTRIBUTION — AZ USED MARKET (Active)
  P5:   $10,496    P25: $22,356    P50: $35,162
  P75:  $51,902    P90: $70,798    P95: $84,514

REPLACEMENT COST RISK FLAGS — MARCH 2026
┌──────────────────────────────────────────────────────────────┐
│ ELEVATED RISK — Toyota/Honda SUVs                            │
│   RAV4 and CR-V median retail exceeds $36,800. Hybrid        │
│   variants (RAV4 Hybrid XSE) at $38,000–$42,000 active.     │
│   Under-supply conditions in Southwest = limited comp pool.  │
├──────────────────────────────────────────────────────────────┤
│ ELEVATED RISK — Full-Size Trucks                             │
│   Tundra/F-150/Silverado 2024-2026 median: $44,000–$57,000. │
│   New model premiums adding 8-12% vs prior-year reserves.    │
├──────────────────────────────────────────────────────────────┤
│ STABLE — Sedans and Economy SUVs                             │
│   AZ sold median $32,990 reflects broad market. Sedans and   │
│   economy segments (Corolla, Civic, Sentra) remain stable.   │
└──────────────────────────────────────────────────────────────┘

RESERVE PLANNING RECOMMENDATIONS
  1. Increase Toyota RAV4 Hybrid reserves by 5-8% for 2025 MY
  2. Flag full-size truck claims for supplemental valuation
  3. Honda CR-V reserves current — stable comp availability
  4. Review Highlander reserves by trim (Platinum = sparse supply)
  5. Sold median ($32,990) is 6.3% below active median ($35,162)
     → Use active market data for total-loss FMV, not sold-only
```
</details>

---

### `/vin-lookup` — Claims Processing

**Input:** `/vin-lookup 5TFLA5DB8RX204441`
*(2024 Toyota Tundra SR5 4WD, 16,930 mi)*

<details>
<summary><strong>View Output</strong></summary>

```
VIN LOOKUP — CLAIMS PROCESSING: 5TFLA5DB8RX204441
National Claims Services · Phoenix, AZ (85001)
═══════════════════════════════════════════════════════════════════

VEHICLE SPECIFICATIONS
  Year:          2024
  Make/Model:    Toyota Tundra SR5
  Version:       SR5 3.4L 4WD CrewMax 5.5' Bed
  Body:          Pickup · 4-door
  Engine:        3.4L V6 · Automatic · 4WD
  Fuel:          Unleaded (Combustion)
  MPG:           17 city / 22 hwy
  Made in:       USA

COLORS
  Exterior:      Lunar Rock (Gray)
  Interior:      Black Cloth

PRICING AT TIME OF PURCHASE
  Base MSRP:     $50,550
  Combined MSRP: $54,228 (with options + delivery)

═══════════════════════════════════════════════════════════════════

PRE-LOSS FAIR MARKET VALUE (16,930 mi, ZIP 85001)
┌──────────────────────────────────┬────────────┐
│ Source                           │ Value      │
├──────────────────────────────────┼────────────┤
│ ML Prediction (Franchise)        │ $43,250    │
│ Active Comp Median (140 SR5s)    │ $44,332    │
│ Recent Sold Median (57 units)    │ $42,981    │
├──────────────────────────────────┼────────────┤
│ ★ Blended Pre-Loss FMV          │ $43,521    │
│   MSRP (new combined)            │ $54,228    │
│   Depreciation from MSRP         │ -$10,707   │
│   MSRP Retention                 │ 80.3%      │
└──────────────────────────────────┴────────────┘
  Confidence: HIGH (140 active + 57 sold comps)

TOTAL-LOSS THRESHOLD (75%)
  Pre-Loss FMV:                $43,521
  Total-loss threshold (75%):  $32,641
  → Claim is TOTAL LOSS if repair estimate > $32,641

SETTLEMENT RANGE
  Low  (conservative — sold P25): $41,761
  Mid  (recommended — blended):   $43,521
  High (generous — comp median):  $44,332

SALVAGE ESTIMATE: $4,350 – $6,530
  (10-15% of FMV; adjust for damage extent and auction conditions)

COMPARABLE ACTIVE LISTINGS (SR5 trim, AZ region)
┌───┬──────────┬─────────┬─────┬──────────────────────────────┐
│ # │  Price   │  Miles  │ DOM │ Dealer                       │
├───┼──────────┼─────────┼─────┼──────────────────────────────┤
│ 1 │ $43,840  │ 27,129  │  18 │ Camelback Toyota (4 mi)      │
│ 2 │ $44,988  │  1,610  │  38 │ Camelback Toyota (4 mi)      │
│ 3 │ $43,488  │ 10,901  │  58 │ Camelback Toyota (4 mi)      │
│ 4 │ $38,400  │ 82,613  │  71 │ Chapman Ford (11 mi)         │
│ 5 │ $43,840  │ 27,129  │  18 │ Lifted Trucks Scottsdale     │
└───┴──────────┴─────────┴─────┴──────────────────────────────┘

SOLD MARKET (AZ, past 90 days, 2024 Tundra)
  Sold volume:       57 units
  Sold price range:  $35,990 – $59,586
  Sold median:       $42,981
  Sold P25:          $41,761  ← conservative settlement floor

CLAIM NOTES
  → 140 active comp listings = HIGH market liquidity
  → Strong comparable evidence for dispute defense
  → Document mileage (16,930) for precise FMV positioning
  → This VIN sits at 80.3% MSRP retention (strong for MY 2024)
  → Salvage value note: Tundra parts demand is high in AZ
```
</details>

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
