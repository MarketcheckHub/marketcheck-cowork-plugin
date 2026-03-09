# Appraiser Plugin — MarketCheck

Automotive valuation intelligence for **appraisers and adjusters**. Comparable-backed valuations with transaction evidence, regional price variance, wholesale vs retail spreads, and depreciation tracking.

---

## Who It's For

- Trade-in appraisers at dealerships
- Insurance adjusters valuing claims
- Estate and probate appraisers
- Fleet managers valuing vehicles
- Independent appraisal firms

---

## Skills (4)

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **vehicle-appraiser** | "appraise this vehicle", "what's it worth", "fair market value", "wholesale vs retail" | Three-source valuation: ML prediction + active comps + sold transactions. Cites every comparable by VIN. |
| **competitive-pricer** | "price check", "market price for this", "compare my price" | Market pricing analysis with dual franchise+independent comparisons |
| **depreciation-tracker** | "depreciation rate", "value retention", "residual value" | Multi-point depreciation curves, brand rankings, geographic variance |
| **market-trends-reporter** | "market trends", "fastest depreciating cars", "regional price variance" | Market trend analysis relevant to valuation context |

---

## Commands (4)

| Command | What It Does |
|---------|-------------|
| `/onboarding` | Appraiser profile setup — specialization, default radius (75 mi), minimum comps |
| `/price-check` | Quick price check with comparable citations |
| `/vin-lookup` | Full VIN decode + listing history + estimated value |
| `/setup-mcp` | Configure MCP connection |

---

## Agents (3)

| Agent | What It Does |
|-------|-------------|
| **lot-pricer** | Batch pricing for multiple VINs with comparable citations |
| **portfolio-scanner** | Process auction lists, fleet appraisals, or portfolio revaluations in bulk |
| **brand-market-analyst** | Brand-level market intelligence for valuation context |

---

## Quick Start

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin appraiser
/setup-mcp YOUR_API_KEY
/onboarding
```

After onboarding, try:
- "Appraise VIN 1HGCV1F3XPA123456, 28K miles, clean condition"
- "What's the wholesale vs retail spread on this vehicle?"
- "Compare values across Texas, California, and Florida"

---

## Example Workflows

### Full Comparable Appraisal
```
Appraise VIN 5YJ3E1EA8PF123456, 28,400 miles, clean condition, ZIP 30309
```
→ Predicted value + active comp range + sold transaction range + 18 cited comps + confidence score

### Wholesale vs Retail Spread
```
What's the wholesale vs retail spread on this?
```
→ Franchise retail vs independent wholesale pricing with spread calculation and recommended offer range

### Regional Variance Analysis
```
Compare values for this 2022 RAV4 across Texas, California, and New York
```
→ State-by-state pricing showing where the vehicle is worth most and least

### Batch Fleet Appraisal
```
Appraise these 15 VINs from our fleet:
[list of VINs with mileage]
```
→ Portfolio scanner processes each with current value, confidence, and flag for significant changes

---

## Key Differences from Dealer Plugin

- **Wider default radius** (75 mi vs 50 mi) for broader comparable coverage
- **No dealer_id** required — appraisers work across the market
- **Output emphasizes** comparable citations and confidence scores over competitive positioning
- **Specialization options** — trade-in, insurance, estate, fleet — to tune output framing

---

## Live Example Outputs

> All examples below use **real market data** from the Atlanta metro area (ZIP 30309). Appraiser persona "Valuation Pro Services" is fictional — used for illustration. Default radius: 75 miles.

---

### `vehicle-appraiser` — 2022 Toyota Sienna XLE, 62,264 Miles

**Input:**
```
Appraise VIN 5TDJSKFC2NS055758, 62,264 miles, clean condition, ZIP 30309
```

<details>
<summary><strong>View Output</strong></summary>

```
╔══════════════════════════════════════════════════════════════════╗
║          VEHICLE APPRAISAL — Valuation Pro Services              ║
║                   Atlanta Metro | ZIP 30309                      ║
╠══════════════════════════════════════════════════════════════════╣
║  VIN: 5TDJSKFC2NS055758                                          ║
║  2022 Toyota Sienna XLE | 2.5L I4 Hybrid | CVT | AWD            ║
║  Sunset Bronze Mica | 62,264 miles | Clean condition             ║
║  Original MSRP: $42,575 | Fuel: 35 city / 36 hwy MPG            ║
╠══════════════════════════════════════════════════════════════════╣
║  VALUATION SUMMARY (3 sources)                                   ║
╠══════════════════════════════════════════════════════════════════╣
║  ML Prediction (franchise market):      $38,789                  ║
║  ML Prediction (independent market):    $39,350                  ║
║  Active comp median (17 units, 75mi):   $39,380                  ║
║  Active comp range:                     $29,273 – $74,999        ║
╠══════════════════════════════════════════════════════════════════╣
║  APPRAISED VALUE RANGE                                           ║
║  Wholesale floor (independent offer):   ~$33,000                 ║
║  Fair market value (blended):           ~$38,800 – $39,400       ║
║  Retail ceiling (franchise list):       ~$45,000                 ║
║  MSRP depreciation (3 yrs / 62K mi):   ~9% below original       ║
╠══════════════════════════════════════════════════════════════════╣
║  COMPARABLE CITATIONS (selected, 75mi radius)                    ║
╠═══╦══════════════════════════════╦═════════╦═══════╦════════════╣
║ # ║ Dealer                       ║  Price  ║  Miles ║  Dist (mi) ║
╠═══╬══════════════════════════════╬═════════╬════════╬════════════╣
║ 1 ║ Stone Mountain Toyota        ║ $24,985 ║ 94,771 ║   19.4 mi  ║
║ 2 ║ Auto Gallery Lawrenceville   ║ $26,499 ║ 127,640║   27.1 mi  ║
║ 3 ║ Faith Auto Sales             ║ $40,986 ║  37,200║   14.2 mi  ║
║ 4 ║ Nalley Lexus Smyrna          ║ $42,684 ║   6,811║   18.3 mi  ║
╚═══╩══════════════════════════════╩═════════╩════════╩════════════╝

APPRAISER NOTE: 17 active comps found within 75 miles. High-mileage
units (90K+) cluster below $27K; clean examples with under 70K miles
support $38K–$42K. Recommend $38,800 as conservative fair market
value for trade-in or insurance purposes. Confidence: HIGH (17 comps).
```

</details>

---

### `competitive-pricer` — 2024 Toyota Tacoma TRD Off Road, 18,090 Miles

**Input:**
```
Price check on VIN 3TMLB5JN4RM005615, 18,090 miles, ZIP 30309
```

<details>
<summary><strong>View Output</strong></summary>

```
╔══════════════════════════════════════════════════════════════════╗
║            MARKET PRICE ANALYSIS — Valuation Pro Services        ║
║                   Atlanta Metro | ZIP 30309                      ║
╠══════════════════════════════════════════════════════════════════╣
║  VIN: 3TMLB5JN4RM005615                                          ║
║  2024 Toyota Tacoma TRD Off Road | 2.4L I4 | Automatic | 4WD    ║
║  Ice Cap (White) | Boulder/Black Fabric | 18,090 miles           ║
║  Base MSRP: $43,400 | Combined MSRP: $51,559 | 19/23 MPG        ║
╠══════════════════════════════════════════════════════════════════╣
║  PRICE BENCHMARKS                                                ║
╠══════════════════════════════════════════════════════════════════╣
║  ML Prediction (franchise):   $41,580                            ║
║  ML Prediction (independent): $42,325                            ║
║  Active comp median (75mi):   $40,834  [207 active listings]     ║
║  Active comp range:           $33,038 – $50,950                  ║
║  Recent sold median (90d):    $40,988  [32 sold transactions]    ║
╠══════════════════════════════════════════════════════════════════╣
║  MARKET POSITION ASSESSMENT                                      ║
║  At ML price of $41,580, this unit is positioned:               ║
║    • $747 above active comp median ($40,834)                     ║
║    • $592 above recent sold median ($40,988)                     ║
║    • $9,979 below combined MSRP ($51,559)                        ║
║  Assessment: FAIRLY PRICED — within normal market spread         ║
╠══════════════════════════════════════════════════════════════════╣
║  NEARBY FRANCHISE COMPARABLES (75mi radius)                      ║
╠═══╦══════════════════════════╦═════════╦════════╦═══════╦═══════╣
║ # ║ Dealer                   ║  Price  ║  Miles ║  DOM  ║  Dist ║
╠═══╬══════════════════════════╬═════════╬════════╬═══════╬═══════╣
║ 1 ║ World Toyota             ║ $37,446 ║ 41,042 ║  18d  ║  9.3mi║
║ 2 ║ Jim Ellis Automotive     ║ $40,113 ║ 32,050 ║  59d  ║  9.3mi║
║ 3 ║ Drive A Dream            ║ $39,500 ║  2,843 ║ 102d  ║ 15.9mi║
║ 4 ║ Kennesaw Mazda           ║ $40,227 ║ 19,581 ║  67d  ║ 21.8mi║
║ 5 ║ Beaver Toyota            ║ $45,680 ║ 26,099 ║  66d  ║ 29.7mi║
╚═══╩══════════════════════════╩═════════╩════════╩═══════╩═══════╝

APPRAISER NOTE: 207 active comps in market. Recent sold evidence (32
units) confirms market clearing near $40,988. Drive A Dream unit at
$39,500 with only 2,843 miles has been sitting 102 days — possible
pricing anomaly. Fair market value: $40,800–$42,300.
```

</details>

---

### `depreciation-tracker` — Honda CR-V Multi-Year Curve, Georgia

**Input:**
```
Show depreciation curve for Honda CR-V, Georgia market
```

<details>
<summary><strong>View Output</strong></summary>

```
╔══════════════════════════════════════════════════════════════════╗
║          DEPRECIATION ANALYSIS — Valuation Pro Services          ║
║                 Honda CR-V | Georgia Market                      ║
╠══════════════════════════════════════════════════════════════════╣
║  Data source: sold transactions (past 90 days), state of Georgia ║
╠══════════════════════════════════════════════════════════════════╣
║  MULTI-YEAR DEPRECIATION CURVE                                   ║
╠═══════╦══════════╦════════════════╦═══════════════════╦═════════╣
║  Year ║  # Sold  ║  Median Price  ║  Price Range       ║  YoY Δ  ║
╠═══════╬══════════╬════════════════╬════════════════════╬═════════╣
║  2024 ║   362    ║    $31,220     ║ $21,999 – $50,000  ║   base  ║
║  2023 ║   259    ║    $29,440     ║ $16,002 – $36,998  ║  -$1,780║
║  2022 ║   226    ║    $26,427     ║ $14,999 – $35,740  ║  -$3,013║
║  2021 ║   152    ║    $23,998     ║ $16,050 – $50,000  ║  -$2,429║
╚═══════╩══════════╩════════════════╩════════════════════╩═════════╝

DEPRECIATION SUMMARY
  2024 → 2023: -$1,780  (-5.7% / 1yr)
  2024 → 2022: -$4,793  (-15.4% / 2yrs)
  2024 → 2021: -$7,222  (-23.1% / 3yrs)

  Average annual depreciation (3yr):     ~$2,407/year
  Percentage retained after 3 years:     76.9%

APPRAISER NOTE: CR-V shows strong value retention vs. class average
(~25–30% per year). GA market reflects 999 total sold transactions
over 90 days across all four model years — high liquidity, confident
pricing curve. Insurance and estate appraisals should use year-specific
median with ±$2,000 adjustment for mileage deviation from average.
```

</details>

---

### `market-trends-reporter` — SUV Market Intelligence, Georgia

**Input:**
```
Market trends for SUVs in Georgia — supply, demand, pricing
```

<details>
<summary><strong>View Output</strong></summary>

```
╔══════════════════════════════════════════════════════════════════╗
║         MARKET TRENDS REPORT — Valuation Pro Services            ║
║                  SUV Segment | Georgia Statewide                 ║
╠══════════════════════════════════════════════════════════════════╣
║  SUPPLY & DEMAND SNAPSHOT                                        ║
╠══════════════════════════════════════════════════════════════════╣
║  Active listings (GA):       101,371 vehicles                    ║
║  Active median asking price:  $36,445                            ║
║  Active mean asking price:    $40,892                            ║
║                                                                  ║
║  Sold transactions (past 90d, GA): 236,002 vehicles              ║
║  Sold median price (90d):     $34,419                            ║
║  Sold mean price (90d):       $39,164                            ║
║                                                                  ║
║  Ask-to-sale discount:        ~$2,026 (-5.6% off list)           ║
╠══════════════════════════════════════════════════════════════════╣
║  ACTIVE SUPPLY BY MAKE (Top 10)                                  ║
╠══════════════════════════╦════════════════════════════════════════╣
║  Make                    ║  Active Listings                       ║
╠══════════════════════════╬════════════════════════════════════════╣
║  Ford                    ║       11,448                           ║
║  Jeep                    ║       10,179                           ║
║  Chevrolet               ║        8,229                           ║
║  Nissan                  ║        7,912                           ║
║  Hyundai                 ║        7,761                           ║
║  Toyota                  ║        6,555                           ║
║  KIA                     ║        5,682                           ║
║  Honda                   ║        4,979                           ║
║  Mercedes-Benz           ║        4,125                           ║
║  GMC                     ║        3,221                           ║
╚══════════════════════════╩════════════════════════════════════════╝

APPRAISER NOTE: 236,002 SUV transactions in past 90 days signals
extremely high market liquidity in GA — comp evidence is abundant.
Mean ask ($40,892) exceeds median ask ($36,445) by $4,447, indicating
a long tail of luxury/premium SUVs pulling averages up. Use median
for standard appraisal work; mean only for luxury segment context.
Ford and Jeep dominate active supply; Toyota and Honda show tighter
supply relative to transaction volume — potential for stronger values.
```

</details>

---

### `/vin-lookup` — 2025 Toyota RAV4 Hybrid XSE AWD, 19,255 Miles

**Input:**
```
/vin-lookup JTME6RFV2SD579127
```

<details>
<summary><strong>View Output</strong></summary>

```
╔══════════════════════════════════════════════════════════════════╗
║             VIN LOOKUP — Valuation Pro Services                  ║
║                   Atlanta Metro | ZIP 30309                      ║
╠══════════════════════════════════════════════════════════════════╣
║  VIN: JTME6RFV2SD579127                                          ║
╠══════════════════════════════════════════════════════════════════╣
║  VEHICLE IDENTITY                                                ║
║  Year/Make/Model:  2025 Toyota RAV4 Hybrid XSE                   ║
║  Trim:             XSE | HEV (Hybrid Electric)                   ║
║  Engine:           2.5L I4 | CVT | AWD                          ║
║  Body:             SUV | 5-door                                  ║
║  Fuel Economy:     43 city / 38 hwy MPG                          ║
║  Original MSRP:    $38,510                                       ║
╠══════════════════════════════════════════════════════════════════╣
║  ESTIMATED VALUE                                                 ║
║  ML Prediction (franchise):  $39,195                             ║
║  vs. Original MSRP:          +$685 above MSRP (+1.8%)            ║
║  Active comp median (75mi):  $41,523  [53 active listings]       ║
║  Active comp range:          $34,490 – $46,990                   ║
║  Recent sold median (90d):   $40,997  [11 sold transactions]     ║
╠══════════════════════════════════════════════════════════════════╣
║  ACTIVE COMPARABLE LISTINGS (75mi radius)                        ║
╠═══╦══════════════════════════════╦═════════╦════════╦═══════╦════╣
║ # ║ Dealer                       ║  Price  ║  Miles ║  DOM  ║ mi ║
╠═══╬══════════════════════════════╬═════════╬════════╬═══════╬════╣
║ 1 ║ Marietta Toyota              ║ $41,648 ║ 12,512 ║  22d  ║ 12 ║
║ 2 ║ Jim Ellis Toyota McDonough   ║ $41,400 ║    886 ║  45d  ║ 28 ║
║ 3 ║ Subaru Newnan                ║ $38,795 ║ 35,714 ║  38d  ║ 36 ║
║ 4 ║ Group 1 GMC Rivertown        ║ $41,860 ║  7,479 ║  14d  ║ 93 ║
║ 5 ║ Serra Toyota                 ║ $39,894 ║ 10,867 ║  11d  ║133 ║
╚═══╩══════════════════════════════╩═════════╩════════╩═══════╩════╝

APPRAISER NOTE: 2025 RAV4 Hybrid is commanding slight premium over
MSRP ($39,195 ML vs $38,510 MSRP) — demand exceeds current supply.
53 active comps cluster in $38,795–$46,990 range; 11 recent sold
transactions confirm clearing near $40,997. This is a market-value-
above-replacement-cost scenario. Insurance ACV: $39,195. Trade-in
fair value: $37,500–$39,000. Retail replacement: $41,500+.
```

</details>

---

### `/price-check` — 2023 Toyota Highlander Hybrid Platinum, 13,182 Miles

**Input:**
```
/price-check VIN 5TDEBRCH0PS123584, 13,182 miles, ZIP 30309
```

<details>
<summary><strong>View Output</strong></summary>

```
╔══════════════════════════════════════════════════════════════════╗
║              PRICE CHECK — Valuation Pro Services                ║
║                   Atlanta Metro | ZIP 30309                      ║
╠══════════════════════════════════════════════════════════════════╣
║  VIN: 5TDEBRCH0PS123584                                          ║
║  2023 Toyota Highlander Hybrid Platinum | 13,182 miles           ║
║  Original MSRP: $54,845                                          ║
╠══════════════════════════════════════════════════════════════════╣
║  PRICE BENCHMARKS                                                ║
╠══════════════════════════════════════════════════════════════════╣
║  ML Prediction (franchise):    $50,537                           ║
║  ML Prediction (independent):  $51,149                           ║
║  Active comp median (75mi):    $45,634  [27 active listings]     ║
║  Active comp range:            $34,555 – $49,998                 ║
║  Recent sold median (GA, 90d): $46,687  [4 sold transactions]    ║
╠══════════════════════════════════════════════════════════════════╣
║  WHOLESALE vs RETAIL SPREAD                                      ║
║  Independent wholesale floor:  ~$44,000 – $45,000               ║
║  Fair market value (blended):  ~$46,687 – $50,537               ║
║  Franchise retail ceiling:      $50,537 – $51,149               ║
║  MSRP depreciation:            ~$4,308 below MSRP (-7.9%)        ║
╠══════════════════════════════════════════════════════════════════╣
║  RECENT SOLD COMPARABLE CITATIONS (GA area, 90 days)             ║
╠═══╦══════════════════════════════════╦═════════╦════════════════╣
║ # ║ Dealer                           ║  Price  ║  Miles         ║
╠═══╬══════════════════════════════════╬═════════╬════════════════╣
║ 1 ║ Rick Hendrick Toyota Sandy Spgs  ║ $46,474 ║  41,438        ║
║ 2 ║ ALM Mazda South                  ║ $39,720 ║  66,802        ║
║ 3 ║ Butler Toyota                    ║ $46,900 ║  36,862        ║
║ 4 ║ Capital Toyota Chattanooga       ║ $48,355 ║  27,621        ║
╚═══╩══════════════════════════════════╩═════════╩════════════════╝

ACTIVE COMPS — nearby units currently listed (75mi)
  ALM Mazda South:        $40,320 | 66,802 mi | 184 DOM | 16.8mi
  Beaver Toyota Cumming:  $49,000 | 55,794 mi |  58 DOM | 29.7mi
  Butler Toyota:          $46,900 | 36,866 mi |  11 DOM | 72.4mi

APPRAISER NOTE: ML prediction ($50,537 franchise / $51,149 independent)
sits $3,850–$5,515 above recent sold evidence ($46,687 median). Active
comp median of $45,634 reflects mix of higher-mileage units pulling
prices down. At 13,182 miles this unit is the lowest-mileage in the
comp set — supports ML prediction over comp median. Recommended fair
market value: $48,500–$50,500. Wholesale offer range: $44,000–$46,000.
```

</details>

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
