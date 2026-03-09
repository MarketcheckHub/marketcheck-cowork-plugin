# Manufacturer Plugin — MarketCheck

Automotive market intelligence for **OEMs, brand managers, and regional distributors**. Market share tracking, competitive positioning, EV adoption monitoring, regional demand intelligence, inventory channel visibility, and brand value retention analysis.

---

## Who It's For

- OEM brand managers
- Regional sales directors
- Product planning teams
- Competitive intelligence analysts at auto manufacturers
- Regional distributors

---

## Skills (7)

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **market-share-analyzer** | "market share", "how are we doing vs Toyota", "segment share" | Own-brand vs competitor share tracking with basis point changes, segment conquest, regional distribution |
| **oem-stock-tracker** | "brand performance", "how is our brand doing", "market position" | Brand health monitoring: share, pricing power, depreciation, segment momentum |
| **ev-transition-monitor** | "EV adoption", "EV market share", "how are our EVs doing" | EV penetration rates, own-brand EV share vs competitors, adoption curve positioning |
| **market-momentum-report** | "market momentum", "demand trends", "which segments are growing" | Segment-level volume and pricing momentum for product planning and allocation |
| **depreciation-tracker** | "depreciation rate", "brand value retention", "residual performance" | Brand value retention rankings, model-level depreciation, competitor residual comparison |
| **market-trends-reporter** | "market trends", "competitive landscape", "market dynamics" | Comprehensive market trend analysis framed as competitive intelligence |
| **inventory-intelligence** | "dealer inventory levels", "channel inventory", "days supply" | Dealer-level inventory visibility for channel management and allocation decisions |

---

## Commands (3)

| Command | What It Does |
|---------|-------------|
| `/onboarding` | Manufacturer profile setup — own brands, competitor brands, focus states, role |
| `/market-snapshot` | Brand market position snapshot for a state or region |
| `/setup-mcp` | Configure MCP connection |

---

## Agents (2)

| Agent | What It Does |
|-------|-------------|
| **brand-market-analyst** | Multi-period brand analysis: share, pricing, depreciation, segment performance |
| **market-demand-agent** | Demand intelligence: what's selling, supply-to-demand ratios, regional patterns |

---

## Quick Start

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin manufacturer
/setup-mcp YOUR_API_KEY
/onboarding
```

During onboarding, you'll set up:
- **Own brands** — e.g., Toyota, Lexus
- **Competitor brands** — e.g., Honda, Hyundai, Ford
- **Focus states** — regional areas of responsibility
- **Role** — brand manager, regional director, product planner

After onboarding, try:
- "How is our SUV market share vs Honda?" — competitive positioning
- "Which states should we allocate more CR-V inventory to?" — regional demand
- "EV adoption update for our brands" — EV transition monitoring

---

## Example Workflows

### Competitive Market Share
```
How did Toyota do vs Honda in SUV market share last month nationally?
```
→ Brand share with basis point changes, model-level breakdown, conquest analysis

### Regional Allocation
```
Which states should we allocate more RAV4 inventory to?
```
→ State-by-state demand-to-supply analysis showing under-penetrated markets with volume estimates

### Brand Value Retention
```
How does our brand stack up on value retention vs competitors?
```
→ Brand tier ranking by residual retention, model-level standouts and concerns

### EV Positioning
```
How are our EVs doing compared to Tesla and Hyundai?
```
→ EV penetration rates by brand, model share within EV segment, adoption momentum

### Channel Inventory Check
```
What do dealer inventory levels look like for our trucks in Texas?
```
→ Dealer-level days supply, aged units, pricing position across the network

---

## Output Framing

All output is framed for manufacturer context:
- Market share → **Competitive Positioning**
- Depreciation → **Brand Value Retention**
- Demand signals → **Allocation Intelligence**
- EV adoption → **Electrification Progress**
- Inventory → **Channel Health**

---

## Live Example Outputs

> All examples below use **real market data** from Texas (primary focus state). Manufacturer persona "Toyota North America Southwest Region" is fictional — used for illustration.

---

### `market-share-analyzer` — Toyota vs Honda in the Texas SUV Segment

**Input:** *"How did Toyota do vs Honda in SUV market share in Texas last quarter?"*

<details>
<summary><strong>View Output</strong></summary>

```
COMPETITIVE POSITIONING: SUV Segment — Texas (TX)
Toyota North America Southwest Region — Q1 2026
═══════════════════════════════════════════════════

BRAND MARKET SHARE — SUV SEGMENT (past 90 days, TX)
┌────┬────────────────┬──────────┬────────┬─────────┐
│  # │ Brand          │ Sold 90d │ Share  │ Supply  │
├────┼────────────────┼──────────┼────────┼─────────┤
│  1 │ Ford           │  74,113  │ 14.5%  │  34,992 │
│  2 │ Chevrolet      │  71,240  │ 13.9%  │   —     │
│  3 │ Toyota         │  61,676  │ 12.1%  │  17,419 │
│  4 │ Jeep           │  55,170  │ 10.8%  │   —     │
│  5 │ Nissan         │  50,606  │  9.9%  │   —     │
│  6 │ Hyundai        │  42,641  │  8.3%  │  33,153 │
│  7 │ Honda          │  35,114  │  6.9%  │  14,257 │
│  8 │ KIA            │  29,269  │  5.7%  │   —     │
│  9 │ GMC            │  26,929  │  5.3%  │   —     │
│ 10 │ Lexus          │  24,930  │  4.9%  │  10,169 │
└────┴────────────────┴──────────┴────────┴─────────┘
  Total SUV transactions (90d TX): ~511,000

TOYOTA vs HONDA HEAD-TO-HEAD (SUV Segment)
┌─────────────────────────┬───────────┬───────────┐
│ Metric                  │  Toyota   │   Honda   │
├─────────────────────────┼───────────┼───────────┤
│ SUV Units Sold (90d)    │  61,676   │  35,114   │
│ Market Share            │  12.1%    │   6.9%    │
│ Active Supply (all)     │  17,419   │  14,257   │
│ SUV Supply (active)     │  17,419   │  14,257   │
│ Supply-to-Sold Ratio    │   0.28x   │   0.41x   │
│ Demand Signal           │ VERY HOT  │   HEALTHY │
└─────────────────────────┴───────────┴───────────┘

SUPPLY vs DEMAND MISMATCH (Competitive Positioning)
  Toyota:  12.1% of SUV sales vs 8.5% of active supply
           → UNDER-SUPPLIED: demand outpacing channel stock
  Honda:    6.9% of SUV sales vs 7.0% of active supply
           → BALANCED: supply and demand in equilibrium
  Hyundai:  8.3% of SUV sales vs 16.2% of active supply
           → OVER-SUPPLIED: heavy stock relative to sales pace

KEY INSIGHT FOR ALLOCATION:
  Toyota's SUV pull-through is significantly stronger than
  Honda's in TX. With 61,676 units sold vs Honda's 35,114
  in 90 days, Toyota commands a +5.2 point share lead in
  SUVs. Current supply coverage of 0.28x (Toyota) vs 0.41x
  (Honda) confirms Toyota dealer lots are lean — allocation
  increases to TX SUV dealers are justified this quarter.
```
</details>

---

### `inventory-intelligence` — RAV4 Channel Health Check, Texas

**Input:** *"What do dealer inventory levels look like for our RAV4s in Texas? Show me the channel health"*

<details>
<summary><strong>View Output</strong></summary>

```
CHANNEL INVENTORY HEALTH: Toyota RAV4 — Texas (TX)
Toyota North America Southwest Region — March 7, 2026
═══════════════════════════════════════════════════

CHANNEL SNAPSHOT
  Active RAV4 Supply (TX):      5,286 units
  Sold/Expired RAV4 (90d TX):  21,972 units
  Supply-to-Demand Ratio:        0.24x  ← CRITICALLY LEAN
  Median Active Price:          $32,662
  Median DOM:                    33 days  ← Fast mover
  Price Range (active):         $3,499 – $94,942

RAV4 vs CR-V COMPETITIVE CHANNEL COMPARISON
┌──────────────────────────┬───────────┬───────────┐
│ Metric                   │ Toyota    │ Honda     │
│                          │ RAV4 (TX) │ CR-V (TX) │
├──────────────────────────┼───────────┼───────────┤
│ Active Supply            │  5,286    │  7,798    │
│ Sold Past 90d            │ 21,972    │ 18,829    │
│ Supply/Demand Ratio      │  0.24x    │  0.41x    │
│ Median Active Price      │ $32,662   │ $36,075   │
│ Median DOM               │  33 days  │  47 days  │
│ Channel Velocity         │  FASTEST  │   STRONG  │
└──────────────────────────┴───────────┴───────────┘

TOP METRO MARKETS — RAV4 Active Supply
┌────┬──────────────┬──────────────────────────────┐
│  # │ Metro        │ Active Supply                │
├────┼──────────────┼──────────────────────────────┤
│  1 │ Houston      │ 1,081 units                  │
│  2 │ San Antonio  │   407 units                  │
│  3 │ Dallas       │   310 units                  │
│  4 │ Austin       │   266 units                  │
│  5 │ El Paso      │   145 units                  │
│  6 │ McKinney     │   138 units                  │
│  7 │ Leander      │   135 units                  │
│  8 │ Arlington    │   130 units                  │
│  9 │ Fort Worth   │   122 units                  │
│ 10 │ Spring       │   121 units                  │
└────┴──────────────┴──────────────────────────────┘

ALLOCATION RECOMMENDATIONS
  CRITICAL — Texas RAV4 supply at 0.24x demand coverage.
  Industry benchmark: 0.33x = healthy, 0.50x = adequate.
  Current pace requires immediate allocation increase.

  Priority 1: Houston dealers — 1,081 units across
    largest metro but demand is proportionally higher.
    Allocate +15% to Houston network this quarter.

  Priority 2: Austin/Leander corridor — 266 + 135 units
    in a high-growth tech corridor. Under-indexed for
    population. Accelerate franchise allocation here.

  Priority 3: El Paso — 145 units serving border market
    with high conquest potential from Mexico-adjacent
    demand. RAV4 at 33-day median DOM = fastest SUV
    turn in state. Do not reduce allocation here.
```
</details>

---

### `depreciation-tracker` — Brand Value Retention Rankings

**Input:** *"How does Toyota's brand stack up on value retention vs Honda and Hyundai?"*

<details>
<summary><strong>View Output</strong></summary>

```
BRAND VALUE RETENTION RANKINGS — Texas (TX)
Toyota North America Southwest Region — March 2026
═══════════════════════════════════════════════════

MODEL YEAR PRICE COMPARISON (90-day sold, TX)
Toyota RAV4
┌──────┬──────────┬──────────┬──────────┬───────────────────────┐
│ MY   │ Volume   │ Median   │ Floor    │ Ceiling               │
├──────┼──────────┼──────────┼──────────┼───────────────────────┤
│ 2024 │  2,427   │ $27,710  │ $18,988  │ $45,676               │
│ 2022 │    841   │ $25,995  │ $17,871  │ $42,105               │
└──────┴──────────┴──────────┴──────────┴───────────────────────┘
  2-year depreciation: -$1,715 (−6.2%)  ← Exceptional retention

Honda CR-V
┌──────┬──────────┬──────────┬──────────┬───────────────────────┐
│ MY   │ Volume   │ Median   │ Floor    │ Ceiling               │
├──────┼──────────┼──────────┼──────────┼───────────────────────┤
│ 2024 │    911   │ $29,991  │ $20,900  │ $42,005               │
│ 2022 │    485   │ $25,709  │ $12,487  │ $34,991               │
└──────┴──────────┴──────────┴──────────┴───────────────────────┘
  2-year depreciation: -$4,282 (−14.3%)

Hyundai Tucson
┌──────┬──────────┬──────────┬──────────┬───────────────────────┐
│ MY   │ Volume   │ Median   │ Floor    │ Ceiling               │
├──────┼──────────┼──────────┼──────────┼───────────────────────┤
│ All  │ 13,898   │ $30,526  │  $1,800  │ $66,645               │
└──────┴──────────┴──────────┴──────────┴───────────────────────┘
  Wide floor spread (to $1,800) reflects high volume
  across older model years pulling category median down.

COMPETITIVE RESIDUAL BENCHMARKS
┌───────────────┬──────────────┬──────────────┬──────────────┐
│ Brand/Model   │ 2024 Median  │ 2022 Median  │ 2yr Δ       │
├───────────────┼──────────────┼──────────────┼──────────────┤
│ Toyota RAV4   │   $27,710    │   $25,995    │ −$1,715      │
│ Honda CR-V    │   $29,991    │   $25,709    │ −$4,282      │
│ Hyundai Tucson│   $30,526    │      —       │ wide spread  │
└───────────────┴──────────────┴──────────────┴──────────────┘

BRAND VALUE RETENTION VERDICT
  TIER 1 — Toyota RAV4: Only −6.2% median depreciation
  over 2 years. Exceptional price floor defense driven
  by 21,972 units of demand vs 5,286 active supply in TX.
  Scarcity premium is protecting residuals market-wide.

  TIER 2 — Honda CR-V: −14.3% over same period. Heavier
  supply (7,798 active vs 5,286 RAV4) means faster price
  discovery downward. Still above market average.

  TIER 3 — Hyundai Tucson: Wide price dispersion ($1,800
  to $66,645) driven by high volume and broader year
  range in market. Residual floors less defended.

  RECOMMENDATION: Toyota's residual advantage supports
  stronger CPO pricing and lease programs in TX. Use this
  data to negotiate more favorable floorplan terms with
  franchisees — Toyota's faster turn reduces lender risk.
```
</details>

---

### `ev-transition-monitor` — Electrification Progress, Texas

**Input:** *"How are our EVs doing in Texas vs Tesla and Hyundai? EV adoption update"*

<details>
<summary><strong>View Output</strong></summary>

```
ELECTRIFICATION PROGRESS: Texas (TX) EV Market
Toyota North America Southwest Region — March 7, 2026
═══════════════════════════════════════════════════

EV PENETRATION — ACTIVE SUPPLY SNAPSHOT (TX)
Total Active TX Market:          610,694 units
Toyota BEV Supply (bZ series):      479 units   (0.08%)
Tesla BEV Supply:                  1,553 units   (0.25%)
Hyundai BEV Supply (IONIQ+Kona):     908 units   (0.15%)
Toyota PHEV/HEV (est.):           ~12,000+ units (2.0%)
─────────────────────────────────────────────────────────
  Toyota EV share of own supply: BEV at ~0.9% of Toyota
  total (479 of 52,937 active units statewide)

BRAND EV SHARE TABLE (Active Supply, TX)
┌──────────────────┬───────────┬─────────────────────────┐
│ Brand            │ BEV Units │ Model Breakdown          │
├──────────────────┼───────────┼─────────────────────────┤
│ Tesla            │   1,553   │ Model 3: 623             │
│                  │           │ Model Y: 491             │
│                  │           │ Model S: 210             │
│                  │           │ Model X: 192             │
│                  │           │ Cybertruck: 34           │
│                  │           │ Roadster: 3              │
├──────────────────┼───────────┼─────────────────────────┤
│ Hyundai          │     908   │ IONIQ 5: 454             │
│                  │           │ IONIQ 9: 273             │
│                  │           │ IONIQ 6: 132             │
│                  │           │ Kona EV: 44              │
│                  │           │ IONIQ: 5                 │
├──────────────────┼───────────┼─────────────────────────┤
│ Toyota (BEV)     │     479   │ bZ series: 434           │
│                  │           │ bZ4X: 42                 │
│                  │           │ RAV4 EV: 3               │
└──────────────────┴───────────┴─────────────────────────┘

ADOPTION CURVE ASSESSMENT
  Tesla:   1,553 units = clear BEV market leader in TX.
           Model Y + Model 3 dominate (72% of Tesla BEV).
           Established charging infra drives preference.

  Hyundai: 908 units = #2 BEV position. IONIQ 5 (454)
           strongest non-Tesla BEV. Rapid model expansion
           (IONIQ 9 at 273 units) signals growing momentum.

  Toyota:  479 units BEV — 3.2x behind Tesla's position.
           bZ series at 434 units shows product is in
           market but retail velocity is suppressed.
           bZ4X DOM data shows extended days on lot —
           pricing and awareness gaps are limiting uptake.

STRATEGIC IMPLICATIONS
  1. ELECTRIFICATION GAP: Toyota BEV share in TX is 0.08%
     of total market vs Tesla at 0.25% — a 3.1x deficit.
     Critical window: Hyundai is scaling IONIQ line fast.

  2. HYBRID STRENGTH IS A BRIDGE: Toyota's HEV/PHEV fleet
     (RAV4 Hybrid, Highlander Hybrid, Prius) represents
     the real electrification story. Monitor hybrid share
     vs pure BEV to show full electrification progress.

  3. ALLOCATION SIGNAL: bZ4X supply at 479 units with
     extended DOM — consider incentive programs or dealer
     training to accelerate BEV sell-through in TX before
     Hyundai's IONIQ expansion captures conquest buyers.
```
</details>

---

### `market-momentum-report` — Segment Demand for Q2 Allocation

**Input:** *"Which segments are growing in demand in Texas? Need this for Q2 allocation planning"*

<details>
<summary><strong>View Output</strong></summary>

```
ALLOCATION INTELLIGENCE: Segment Momentum — Texas (TX)
Toyota North America Southwest Region — Q2 2026 Planning
═══════════════════════════════════════════════════

SEGMENT SUPPLY vs DEMAND OVERVIEW (TX)
┌──────────────┬──────────┬──────────┬───────┬──────────┐
│ Segment      │ Active   │ Sold 90d │ D:S   │ Signal   │
│              │ Supply   │ TX       │ Ratio │          │
├──────────────┼──────────┼──────────┼───────┼──────────┤
│ SUV          │ 303,399  │ 708,000  │ 2.33x │ STRONG   │
│ Pickup       │ 151,146  │ 350,136  │ 2.32x │ STRONG   │
│ Sedan        │  98,672  │ 240,742  │ 2.44x │ HEALTHY  │
│ Hatchback    │  15,918  │   —      │  —    │ MONITOR  │
│ Minivan      │   8,875  │   —      │  —    │ STABLE   │
│ Coupe        │  11,744  │   —      │  —    │ SLOW     │
└──────────────┴──────────┴──────────┴───────┴──────────┘
  Note: D:S = Demand-to-Supply (sold 90d / active supply).
  Higher ratio = segment is being absorbed faster.

TOP BRANDS BY SEGMENT (Sold 90 days, TX)
SUV Segment Leaders:
  1. Ford       74,113 units (14.5% SUV share)
  2. Chevrolet  71,240 units (13.9%)
  3. Toyota     61,676 units (12.1%)  ← our brand

Pickup Segment Leaders:
  1. Ford      111,574 units (31.9% pickup share)
  2. Chevrolet  70,463 units (20.1%)
  3. RAM        52,383 units (15.0%)
  4. Toyota     49,807 units (14.2%)  ← #4 pickup, closing gap

Sedan Segment Leaders:
  1. Toyota     49,214 units (20.4% sedan share)  ← #1
  2. Nissan     34,857 units (14.5%)
  3. Honda      24,907 units (10.3%)

GROWING vs DECLINING ASSESSMENT (TX Q2 Outlook)
  ACCELERATE ALLOCATION:
  → SUV: Toyota at #3 with 61,676 sold but only 17,419
    active supply. D:S coverage of 0.28x is critically
    lean. RAV4 and Highlander platforms need volume boost.
  → Pickup: Tundra/Tacoma at #4 in TX (49,807 sold 90d).
    Ford dominates with 111,574 but Toyota holds strong
    #4 position — increase allocation to gain on RAM.

  HOLD/MONITOR:
  → Sedan: Toyota #1 in TX sedan segment at 49,214 units.
    Camry and Corolla performing well. Supply is meeting
    demand — no allocation increase needed this quarter.

  REDUCE ALLOCATION RISK:
  → Coupe/Convertible: Low volume segments with rising
    inventory relative to demand. Avoid over-allocation.

Q2 ALLOCATION RECOMMENDATIONS
┌───┬─────────────────────────────────────────────────┐
│ 1 │ SUV PRIORITY — Increase RAV4 TX allocation +15% │
│   │ Demand-supply gap is largest in market segment.  │
├───┼─────────────────────────────────────────────────┤
│ 2 │ PICKUP PRIORITY — Add Tacoma/Tundra to Houston + │
│   │ Dallas corridors. Ford/Chevy dominance shows     │
│   │ conquest opportunity with TX truck buyers.       │
├───┼─────────────────────────────────────────────────┤
│ 3 │ SEDAN — Maintain Camry/Corolla allocation. #1    │
│   │ position in TX sedans; no supply gap to fill.    │
└───┴─────────────────────────────────────────────────┘
```
</details>

---

### `/market-snapshot` — Texas Brand Market Position

**Input:** `/market-snapshot TX`

<details>
<summary><strong>View Output</strong></summary>

```
MARKET SNAPSHOT: Texas (TX) — Toyota North America SW Region
═══════════════════════════════════════════════════════════════

HEADLINE NUMBERS (March 7, 2026)
  Total Active Supply (TX):      610,694 listings
  Sold/Expired (past 90d):     1,419,756 transactions
  Market Turnover Ratio:            2.33x
  Median Active Price:             $37,819
  Median DOM (active):              88 days
  Toyota Active Supply:            52,937 units (8.7% share)
  Toyota Sold 90d:                172,030 units (12.1% share)

BRAND COMPETITIVE POSITIONING (Active Supply, TX)
┌────┬────────────────┬─────────┬────────┐
│  # │ Brand          │ Supply  │ Share  │
├────┼────────────────┼─────────┼────────┤
│  1 │ Ford           │  98,175 │ 16.1%  │
│  2 │ Chevrolet      │  68,836 │ 11.3%  │
│  3 │ Toyota         │  52,937 │  8.7%  │
│  4 │ Nissan         │  44,613 │  7.3%  │
│  5 │ Hyundai        │  33,153 │  5.4%  │
│  6 │ Jeep           │  32,206 │  5.3%  │
│  7 │ Honda          │  29,700 │  4.9%  │
│  8 │ RAM            │  28,651 │  4.7%  │
│  9 │ GMC            │  27,937 │  4.6%  │
│ 10 │ KIA            │  26,199 │  4.3%  │
└────┴────────────────┴─────────┴────────┘

BRAND SALES VELOCITY (Past 90d Sold, TX)
┌────┬────────────────┬──────────┬────────┐
│  # │ Brand          │ Sold 90d │ Share  │
├────┼────────────────┼──────────┼────────┤
│  1 │ Ford           │ 210,976  │ 14.9%  │
│  2 │ Toyota         │ 172,030  │ 12.1%  │
│  3 │ Chevrolet      │ 165,470  │ 11.7%  │
│  4 │ Nissan         │  97,696  │  6.9%  │
│  5 │ Honda          │  72,989  │  5.1%  │
│  6 │ GMC            │  71,417  │  5.0%  │
│  7 │ Hyundai        │  68,465  │  4.8%  │
│  8 │ Jeep           │  62,201  │  4.4%  │
│  9 │ KIA            │  59,078  │  4.2%  │
│ 10 │ RAM            │  56,449  │  4.0%  │
└────┴────────────────┴──────────┴────────┘

SUPPLY BY BODY TYPE (Active, TX)
┌──────────────┬─────────┬────────┐
│ Segment      │  Count  │ Share  │
├──────────────┼─────────┼────────┤
│ SUV          │ 303,399 │ 49.7%  │
│ Pickup       │ 151,146 │ 24.7%  │
│ Sedan        │  98,672 │ 16.2%  │
│ Hatchback    │  15,918 │  2.6%  │
│ Coupe        │  11,744 │  1.9%  │
│ Minivan      │   8,875 │  1.5%  │
│ Cargo Van    │   6,158 │  1.0%  │
│ Convertible  │   4,421 │  0.7%  │
└──────────────┴─────────┴────────┘

TOYOTA CHANNEL HEALTH
  Supply Share:   8.7%  │  Sales Share: 12.1%
  Gap:           +3.4 pts → UNDER-SUPPLIED
  RAV4 Supply:   5,286  │  RAV4 Sold (90d): 21,972
  RAV4 D:S:      4.16x  ← Critical allocation signal

TOYOTA RECENT VOLUME MIX BY MODEL YEAR (TX, 90d)
┌──────┬──────────┐
│ Year │  Sold    │
├──────┼──────────┤
│ 2026 │  81,458  │
│ 2025 │  24,743  │
│ 2024 │  13,379  │
│ 2023 │  10,256  │
│ 2022 │   6,298  │
│ 2021 │   5,846  │
└──────┴──────────┘

KEY TAKEAWAYS FOR SOUTHWEST REGION
  1. Toyota ranks #2 in TX by 90-day sold volume (172,030)
     but only #3 in active supply (52,937). This 3.4-point
     gap between sales share and supply share confirms
     Toyota dealers are running lean — reorder velocity
     is not keeping pace with consumer absorption.

  2. Pickup segment is 24.7% of TX active supply and Ford
     dominates (111,574 sold, 90d). Toyota Tundra/Tacoma
     at #4 in pickups (49,807 sold) — real conquest
     opportunity in this Texas-dominant segment.

  3. SUV = 49.7% of all TX supply. Toyota's RAV4 at a 4.16x
     demand-to-supply ratio is the single hottest model
     in the state. Q2 allocation must prioritize RAV4.
```
</details>

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
