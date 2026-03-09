# Auction House Plugin — MarketCheck

Automotive market intelligence for **auto auction companies and wholesale marketplaces**. Dealer targeting, consignment sourcing, lane planning, run list analysis, DMA market intelligence, geographic arbitrage, and depreciation tracking.

---

## Who It's For

- Auction house sales executives (Manheim, ADESA, Copart, IAA, SmartAuction, etc.)
- Lane managers optimizing sell-through rates
- Consignment reps acquiring vehicles for auction
- Regional directors overseeing multiple auction locations

---

## Skills (8)

Skills activate automatically when you ask questions in natural language — no slash commands needed.

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **dealer-targeting** | "find dealers to invite", "buyer prospecting", "who should I target" | Identifies dealers likely to BUY at auction — high DOM, mix gaps, volume signals |
| **consignment-sourcer** | "find consignment leads", "who has aged inventory", "wholesale sourcing" | Finds dealers with aged, overpriced inventory ready to wholesale through auction |
| **lane-planner** | "plan my lanes", "what should I run this week", "auction lineup" | Optimizes lane allocation by demand signals with sell-through predictions |
| **run-list-analyzer** | "evaluate run list", "price these VINs", "sale day prep" | Batch evaluates consigned VINs — expected hammer, sell-through probability, lane sequencing |
| **dma-market-intelligence** | "market overview for TX", "DMA health check", "market conditions" | Comprehensive DMA view — supply, demand, pricing, top sellers, dealer groups |
| **dealer-engagement-scorer** | "tell me about [dealer]", "should I reach out", "dealer profile" | Deep-dive on one dealer — inventory health, engagement type (buyer/consigner/dual) |
| **geographic-arbitrage-finder** | "arbitrage opportunities", "price differences between states" | Cross-market price gaps — source cheap, sell expensive, net of transport costs |
| **depreciation-tracker** | "depreciation rate", "which cars lose value fastest" | Value erosion tracking for consignment timing and reserve pricing |

---

## Commands (5)

| Command | Usage | What It Does |
|---------|-------|-------------|
| `/onboarding` | `/onboarding` | One-time profile setup — auction type, target DMAs, fees, segments |
| `/setup-mcp` | `/setup-mcp API_KEY` | Configure MarketCheck MCP connection |
| `/daily-briefing` | `/daily-briefing` | Morning consignment leads + price drop alerts |
| `/weekly-review` | `/weekly-review` | Full weekly: lane projection + pipeline + buyer targets |
| `/market-snapshot` | `/market-snapshot TX` | Quick DMA overview for any state |

---

## Agents (3)

| Agent | When It's Used | What It Does |
|-------|---------------|-------------|
| **dma-scanner** | Daily/weekly briefings, market intelligence | Parallel DMA analysis — demand, supply, top models, dealer groups |
| **run-list-pricer** | Run list analysis, sale day prep | Batch VIN evaluation — decode, price, supply check, sell-through prediction |
| **brand-market-analyst** | Weekly reviews, depreciation tracking | Brand share, depreciation curves, segment trends for auction strategy |

### Agent Orchestration

```
WAVE 1 (parallel):
  ├─ auction-house:dma-scanner         (market demand + supply)
  ├─ auction-house:brand-market-analyst (brand trends)
  └─ Inline: consignment scan          (aged inventory leads)

WAVE 2 (depends on Wave 1):
  └─ auction-house:run-list-pricer     (price consigned VINs)
```

---

## Quick Start

```bash
# 1. Install
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin auction-house

# 2. Connect MCP
/setup-mcp YOUR_API_KEY

# 3. Onboard your auction house
/onboarding
```

After onboarding, try:
- `/daily-briefing` — morning consignment leads + market alerts
- `/market-snapshot TX` — quick market overview
- "Find dealers to invite to our next sale" — buyer targeting
- "Who has aged inventory in my market?" — consignment sourcing
- "Plan my lanes for next week" — demand-based lane optimization

---

## Key Concepts

### Buyer vs Consigner

Every dealer is evaluated as a potential **buyer** (will purchase at auction) or **consigner** (will wholesale through auction), or both:
- **Buyers**: Healthy lots with mix gaps — they need inventory they don't have
- **Consigners**: Aging lots with overpriced units — they need to wholesale
- **Dual**: Both signals present — combined engagement approach

### Expected Hammer Price

Predicted wholesale transaction price at auction:
- Based on ML-predicted independent dealer retail price × 0.92 (auction discount)
- Adjusted for condition: low-mileage/newer = 0.95, high-mileage/older = 0.90

### Sell-Through Prediction

Based on demand-to-supply ratio:
- D/S > 2.0 = HIGH (90%) — strong bidder competition
- D/S 1.0-2.0 = MEDIUM (75%) — moderate interest
- D/S < 1.0 = LOW (60%) — may no-sale

### Lane Sequencing

Put HIGH sell-through vehicles in early lanes to build bidder energy. Save LOW sell-through for later when bidders are already engaged and more likely to stretch.

---

## UK Support

UK auction houses are supported with inventory scanning via `search_uk_active_cars` and `search_uk_recent_cars`. Select UK during onboarding.

**Works for UK:** Dealer inventory scanning, aging analysis, consignment lead identification
**US-only:** ML pricing, demand analytics, lane planning, arbitrage, depreciation tracking

---

## Live Example Outputs

> All examples below use **real market data** from the Kansas City metro area. Auction persona "Heartland Auto Auction" is fictional — used for illustration.

---

### `dma-market-intelligence` — Kansas City Market Overview

**Input:** *"Give me a market overview for the Kansas City DMA"*

<details>
<summary><strong>View Output</strong></summary>

```
DMA MARKET OVERVIEW: Kansas City Metro (ZIP 64101, 100 mi)
═══════════════════════════════════════════════════

HEADLINE NUMBERS
  Active Supply:        28,172 listings
  Sold (past 90d):     268,500 transactions
  Turnover Ratio:       9.5x
  Median Asking Price: $22,175
  Top DMA States:       MO, KS, IA, NE, IL

SUPPLY BY MAKE (Active, 100 mi)
┌────┬────────────────┬─────────┬────────┐
│  # │ Make           │  Count  │  %     │
├────┼────────────────┼─────────┼────────┤
│  1 │ Ford           │  5,148  │ 18.3%  │
│  2 │ Chevrolet      │  3,835  │ 13.6%  │
│  3 │ Toyota         │  2,089  │  7.4%  │
│  4 │ Jeep           │  1,951  │  6.9%  │
│  5 │ Honda          │  1,517  │  5.4%  │
│  6 │ Nissan         │  1,516  │  5.4%  │
│  7 │ GMC            │  1,418  │  5.0%  │
│  8 │ KIA            │  1,094  │  3.9%  │
│  9 │ Hyundai        │  1,058  │  3.8%  │
│ 10 │ RAM            │  1,035  │  3.7%  │
└────┴────────────────┴─────────┴────────┘

SOLD VOLUME BY MAKE (past 90 days, MO)
┌────┬────────────────┬──────────┐
│  # │ Make           │ Sold 90d │
├────┼────────────────┼──────────┤
│  1 │ Ford           │  44,763  │
│  2 │ Chevrolet      │  40,621  │
│  3 │ Toyota         │  22,140  │
│  4 │ Jeep           │  16,841  │
│  5 │ Nissan         │  16,418  │
│  6 │ GMC            │  16,062  │
│  7 │ KIA            │  13,208  │
│  8 │ Honda          │  13,030  │
│  9 │ RAM            │  10,756  │
│ 10 │ Hyundai        │  10,472  │
└────┴────────────────┴──────────┘

AUCTION OPPORTUNITY SIGNALS
  → Ford F-150 and Chevy Silverado dominate both supply and
    demand — deep bidder pool for trucks at every sale
  → Toyota: 7.4% of supply → 8.2% of sold volume = UNDER-SUPPLIED
    High sell-through probability on quality Toyota units
  → Honda: 5.4% of supply → 4.9% of sold = slight over-supply
    Be selective on older/higher-mile Honda units

DEALER GROUP LANDSCAPE (KC Metro)
  Major groups: Hendrick (KC), Molle (KC), McCarthy, Park Place
  Independent dealers: 60%+ of market — strong consignment base
  Franchise dealers: Target as buyers for high-grade units
```
</details>

---

### `run-list-analyzer` — Pre-Sale VIN Batch

**Input:** *"Price these 5 VINs from our Thursday sale run list"*

<details>
<summary><strong>View Output</strong></summary>

```
RUN LIST ANALYSIS: Heartland Auto Auction — Thursday Sale
ZIP 64101 · 5 units · Pricing as of Mar 7, 2026
═══════════════════════════════════════════════════

VEHICLE SUMMARY
┌──────┬─────────────────────────────┬─────────┬──────────────┬────────────┬───────────┬──────────────┬──────────┐
│ Lane │ VIN                         │ Vehicle │    Miles     │ Retail Est │ Hammer Est │ Sell-Through │ Sequence │
├──────┼─────────────────────────────┼─────────┼──────────────┼────────────┼───────────┼──────────────┼──────────┤
│   1  │ 3TMLB5JN4RM005615           │ 2024    │ 18,090       │ $41,816    │ $39,725   │ HIGH (90%)   │ OPEN     │
│      │                             │ Tacoma  │ (low mi)     │            │ (×0.95)   │              │          │
├──────┼─────────────────────────────┼─────────┼──────────────┼────────────┼───────────┼──────────────┼──────────┤
│   2  │ JTME6RFV2SD579127           │ 2025    │ 19,255       │ $38,865    │ $36,922   │ HIGH (90%)   │ OPEN     │
│      │                             │ RAV4    │ (low mi)     │            │ (×0.95)   │              │          │
│      │                             │ Hybrid  │              │            │           │              │          │
├──────┼─────────────────────────────┼─────────┼──────────────┼────────────┼───────────┼──────────────┼──────────┤
│   3  │ 5TFLA5DB8RX204441           │ 2024    │ 16,930       │ $44,364    │ $42,146   │ HIGH (90%)   │ MID      │
│      │                             │ Tundra  │ (low mi)     │            │ (×0.95)   │              │          │
│      │                             │ SR5     │              │            │           │              │          │
├──────┼─────────────────────────────┼─────────┼──────────────┼────────────┼───────────┼──────────────┼──────────┤
│   4  │ 5TDEBRCH0PS123584           │ 2023    │ 13,182       │ $51,899    │ $49,304   │ MEDIUM (75%) │ MID      │
│      │                             │ Highlan-│ (low mi)     │            │ (×0.95)   │              │          │
│      │                             │ der Hyb │              │            │           │              │          │
├──────┼─────────────────────────────┼─────────┼──────────────┼────────────┼───────────┼──────────────┼──────────┤
│   5  │ 5TDJSKFC2NS055758           │ 2022    │ 62,264       │ $38,556    │ $34,700   │ MEDIUM (75%) │ CLOSE    │
│      │                             │ Sienna  │ (high mi)    │            │ (×0.90)   │              │          │
│      │                             │ XLE     │              │            │           │              │          │
└──────┴─────────────────────────────┴─────────┴──────────────┴────────────┴───────────┴──────────────┴──────────┘

HAMMER PRICE METHODOLOGY
  Low mileage (<25K mi):  Retail × 0.95  (low risk, strong retail demand)
  Standard (25-50K mi):   Retail × 0.92  (normal auction discount)
  High mileage (>50K mi): Retail × 0.90  (reconditioning risk premium)

LANE SEQUENCING LOGIC
  OPEN lanes  → High sell-through vehicles build bidder energy early
  MID lanes   → Anchor units that command highest absolute dollars
  CLOSE lanes → Lower sell-through or age-adjusted units run later
                when bidders are already engaged and stretched

TOTAL BLOCK ESTIMATE
  5 units · Combined hammer estimate:  $202,797
  Combined retail value:               $215,500
  Blended auction discount:            6.0%

INDIVIDUAL VEHICLE NOTES
  Lane 1 — Tacoma TRD 4x4 (18K mi): KC market has 152 active
    Tacoma listings with Demand:Supply favoring trucks heavily.
    38 comps found nationally. Open the sale with this one.

  Lane 2 — RAV4 Hybrid XSE (19K mi): 38 comps nationwide, median
    active $41,027. KC recent sold comparable at $42,644 (Crown Toyota
    Lawrence). Strong bidder demand for hybrid SUVs.

  Lane 3 — Tundra SR5 (17K mi): 241 comps. Market median $44,900.
    Molle Toyota KC recently sold comparable. Anchor unit.

  Lane 4 — Highlander Hybrid Platinum (13K mi): 24 comps, median
    $46,117. Recent KC sale at $51,679 (Molle Toyota). Premium unit
    — run mid-block when bidder wallets are open.

  Lane 5 — Sienna XLE (62K mi): 185+ DOM at Chicago dealer, 14 comps.
    High-mile minivans carry reconditioning risk. Conservative reserve.
```
</details>

---

### `consignment-sourcer` — Find Aged Inventory Leads

**Input:** *"Who has aged inventory in my market? I need consignment leads for next week's sale"*

<details>
<summary><strong>View Output</strong></summary>

```
CONSIGNMENT LEADS: Kansas City Metro — Mar 7, 2026
ZIP 64101 · 75 mi radius · DOM > 60 days
═══════════════════════════════════════════════════

AGED INVENTORY FOUND: 17,959 units with DOM > 60 in market

TOP CONSIGNMENT TARGETS
┌───┬───────────────────────────────┬────────────┬────────────┬─────┬───────────────────────────────────────────────┐
│ # │ Dealer                        │ Location   │ Vehicle    │ DOM │ Pitch                                         │
├───┼───────────────────────────────┼────────────┼────────────┼─────┼───────────────────────────────────────────────┤
│ 1 │ Thoroughbred Ford             │ KC, MO     │ 2022 MB    │ 978 │ GLE 350, 12K mi — luxury unit >2 years on     │
│   │ (thoroughbredford.com)        │            │ GLE 350    │     │ lot. Reserve consignment before floor plan     │
│   │                               │            │ $44,900    │     │ kills margin.                                  │
├───┼───────────────────────────────┼────────────┼────────────┼─────┼───────────────────────────────────────────────┤
│ 2 │ Auto Now KC                   │ KC, MO     │ Multiple   │ 726-│ Independent with chronic aging — 2010 Tucson  │
│   │ (autonowkc.com)               │            │ units      │ 980 │ at 726 DOM, 2011 HHR at 980 DOM. Offer        │
│   │                               │            │            │     │ wholesale consignment to clear the lot.        │
├───┼───────────────────────────────┼────────────┼────────────┼─────┼───────────────────────────────────────────────┤
│ 3 │ Premier Motors KC             │ KC, MO     │ 2016 Honda │ 944 │ Pilot EX-L 109K mi at 944 DOM. Originally     │
│   │ (premiermotorskc.com)         │            │ Pilot EX-L │     │ listed $16,995, now $15,995. Pain point        │
│   │                               │            │ $15,995    │     │ pitch — this one needs to go.                  │
├───┼───────────────────────────────┼────────────┼────────────┼─────┼───────────────────────────────────────────────┤
│ 4 │ Morris Smith Ford             │ Leavenworth│ 2019 Linc. │  87 │ Nautilus Reserve 50K mi. Franchise dealer      │
│   │ (Leavenworth, KS)             │ KS         │ Nautilus   │     │ with off-brand aging unit — sweet spot for     │
│   │                               │            │ $20,448    │     │ consignment conversation.                      │
├───┼───────────────────────────────┼────────────┼────────────┼─────┼───────────────────────────────────────────────┤
│ 5 │ Ideal Auto Sales              │ KC, KS     │ 2003 HUMMER│ 995 │ H2 at 995 DOM — specialty unit with narrow    │
│   │ (idealautosaleskc.com)        │            │ H2 $15,500 │     │ buyer pool. Run in specialty/collectible lane. │
└───┴───────────────────────────────┴────────────┴────────────┴─────┴───────────────────────────────────────────────┘

MARKET-LEVEL AGING SIGNAL
  17,959 of 28,172 active KC units (63.7%) show DOM > 60
  Average aging unit: $25,686 asking price
  Floor plan pressure at $35/day × 90 DOM = $3,150 sunk cost

CONSIGNMENT PITCH FRAMEWORK
  Thoroughbred Ford (978 DOM GLE): "Your floor plan on that GLE
    is now ~$34,230 buried. Let us run it Thursday — no-cost
    consignment. Reserve price, you set it."

  Premier Motors (944 DOM Pilot): "That Pilot has been up 944
    days at $16K. Your floor plan burn exceeds its margin. We
    move minivans and crossovers reliably — let it go wholesale."
```
</details>

---

### `geographic-arbitrage-finder` — Price Gaps Between Markets

**Input:** *"Find me arbitrage opportunities — where can I source cheap and sell expensive?"*

<details>
<summary><strong>View Output</strong></summary>

```
ARBITRAGE OPPORTUNITIES: Ford F-150 — KC Source → Chicago Sale
Data as of Mar 7, 2026
═══════════════════════════════════════════════════

MARKET COMPARISON: Ford F-150 (Used, All Years)
┌─────────────────────────────┬──────────┬──────────┬──────────┐
│ Market                      │ Listings │ Median   │ Mean     │
├─────────────────────────────┼──────────┼──────────┼──────────┤
│ KC / Rural MO-KS            │  4,064   │ $29,284  │ $30,317  │
│   (ZIP 64101, 200 mi)       │          │          │          │
├─────────────────────────────┼──────────┼──────────┼──────────┤
│ Chicago Metro               │  1,545   │ $29,990  │ $30,639  │
│   (ZIP 60601, 50 mi)        │          │          │          │
├─────────────────────────────┼──────────┼──────────┼──────────┤
│ MO Recent Sold (all years)  │  10,312  │ $41,477  │ $42,362  │
│   (sold in past 90 days)    │  sold    │          │          │
├─────────────────────────────┼──────────┼──────────┼──────────┤
│ MO 2022 MY Sold             │   610    │ $37,072  │ $37,254  │
├─────────────────────────────┼──────────┼──────────┼──────────┤
│ MO 2024 MY Sold             │   445    │ $45,200  │ $48,152  │
└─────────────────────────────┴──────────┴──────────┴──────────┘

NOTE: Active median asking prices are broadly similar between
KC and Chicago ($700 gap on F-150). The real arbitrage is
in vintage — sourcing 2022-2023 retail-grade units at KC auction
prices, then selling to Chicago dealers who face deeper floor
plans and a more competitive retail environment.

ARBITRAGE PLAY: Vintage Premium (2022 MY F-150)
┌─────────────────────────────────────────────────────────────┐
│ Source: 2022 F-150 XLT at KC auction                        │
│   Expected Hammer (retail $37,072 × 0.92):    $34,106       │
│                                                             │
│ Sell: Retail to Chicago-area buyer dealer                   │
│   Chicago asking median (all MY):              $29,990      │
│   Target sale to Chicago dealer at:            $36,500      │
│   (2022 MY commands $6,000+ premium vs all-MY median)       │
│                                                             │
│ Transport KC → Chicago (310 mi):              - $   450     │
│ Gross Arbitrage:                                $  2,394    │
│ Per-Unit Profit:                              ~$1,900-2,400 │
└─────────────────────────────────────────────────────────────┘

TOP ARBITRAGE OPPORTUNITIES BY SEGMENT
┌────┬────────────────────┬──────────────┬────────────────┬──────────┬───────────┐
│  # │ Vehicle Segment    │ Source Mkt   │ Sale Mkt       │ Price Gap│ Transport │
├────┼────────────────────┼──────────────┼────────────────┼──────────┼───────────┤
│  1 │ F-150 2022-23 MY   │ KC/Rural MO  │ Chicago (IL)   │ ~$6,000  │ ~$450     │
│  2 │ Silverado 2022 MY  │ KC/Rural MO  │ Chicago (IL)   │ ~$5,500  │ ~$450     │
│    │ (MO sold $35,900)  │              │                │          │           │
│  3 │ Toyota Tacoma      │ KC auction   │ Chicago/St.L.  │ ~$3,000  │ ~$350     │
│    │ (scarce supply)    │              │                │          │           │
│  4 │ Toyota RAV4 Hybrid │ KC auction   │ Midwest retail │ ~$2,500  │ ~$350     │
│    │ (under-supplied)   │              │                │          │           │
└────┴────────────────────┴──────────────┴────────────────┴──────────┴───────────┘

  KEY INSIGHT: The Kansas City metro has 63% more used truck
  supply than Chicago at comparable prices. Volume opportunity
  for auction houses is in 2021-2023 model-year trucks sourced
  regionally and sold to urban dealer buyers who struggle to
  source at scale.
```
</details>

---

### `dealer-targeting` — Find Buyers for Next Sale

**Input:** *"Find dealers in Kansas City to invite to our sale — who needs inventory they don't have?"*

<details>
<summary><strong>View Output</strong></summary>

```
BUYER TARGETS: Heartland Auto Auction — Thursday Sale
Kansas City Metro · Used Market Analysis
═══════════════════════════════════════════════════

MARKET MIX GAP ANALYSIS
  KC Active Supply (75 mi): 28,172 units
  Toyota share of supply:    7.4% (2,089 units)
  Toyota share of MO sold:   8.2% (22,140 units)
  → Toyota under-supplied by 0.8 pts — buyers paying premium

  Ford F-150 active supply:  5,148 units (largest segment)
  F-150 MO sold 90d:         10,312 transactions
  → Strong truck velocity — franchise dealers restocking

TOP BUYER TARGETS
┌───┬────────────────────────────┬──────────────┬─────────────────────────────┬────────┬──────────┐
│ # │ Dealer                     │ Location     │ Mix Gap / Signal            │ Target │ Priority │
├───┼────────────────────────────┼──────────────┼─────────────────────────────┼────────┼──────────┤
│ 1 │ Molle Toyota               │ KC, MO       │ Toyota franchise — needs    │ Buyer  │ HIGH     │
│   │ (Hendrick/Franchise)       │              │ CPO + used Toyota supply.   │        │          │
│   │                            │              │ Recent comp sold = $51,679  │        │          │
│   │                            │              │ (Highlander Hybrid near KC) │        │          │
├───┼────────────────────────────┼──────────────┼─────────────────────────────┼────────┼──────────┤
│ 2 │ Hendrick Toyota Merriam    │ Merriam, KS  │ Franchise Toyota buyer.     │ Buyer  │ HIGH     │
│   │                            │              │ Active Tacoma comp at       │        │          │
│   │                            │              │ $42,641 (19,875 mi).        │        │          │
│   │                            │              │ Needs low-mile trucks.      │        │          │
├───┼────────────────────────────┼──────────────┼─────────────────────────────┼────────┼──────────┤
│ 3 │ Enterprise Car Sales       │ Independence,│ Fleet operator — high       │ Buyer  │ HIGH     │
│   │ (Independence / Olathe)    │ MO & Olathe  │ velocity buyer. Active      │        │          │
│   │                            │ KS           │ Tacoma comps at $38,499.    │        │          │
│   │                            │              │ Will buy multiples.         │        │          │
├───┼────────────────────────────┼──────────────┼─────────────────────────────┼────────┼──────────┤
│ 4 │ Reliable Toyota            │ Springfield, │ Toyota franchise 150 mi     │ Buyer  │ MEDIUM   │
│   │ (reliabletoyotamo.com)     │ MO           │ south. Active comp at       │        │          │
│   │                            │              │ $38,975 (RAV4 Hybrid XSE).  │        │          │
│   │                            │              │ Buys at KC for Springfield  │        │          │
├───┼────────────────────────────┼──────────────┼─────────────────────────────┼────────┼──────────┤
│ 5 │ Carmax Kansas City         │ KC Metro     │ National buyer with deep    │ Buyer  │ MEDIUM   │
│   │                            │              │ pockets. Active Tacoma comp │        │          │
│   │                            │              │ at $43,998. Volume buyer,   │        │          │
│   │                            │              │ consistent attendance.      │        │          │
└───┴────────────────────────────┴──────────────┴─────────────────────────────┴────────┴──────────┘

MARKET SIGNAL SUMMARY
  Toyota under-supplied → target Toyota franchises as BUYERS
  Trucks (F-150, Silverado) dominate sales volume → all truck-stocking
    dealers are active buyers. Invite broadly.
  KIA/Hyundai: 13.7% of active supply, 8.7% of MO sold → over-supplied
    → KIA/Hyundai dealers likely CONSIGNERS, not buyers this week

OUTREACH PRIORITY THIS WEEK
  Run: 2024 Tacoma TRD + 2025 RAV4 Hybrid + 2024 Tundra SR5
  → Toyota franchises will bid aggressively on low-mile units
  → Enterprise will buy anything grade 3.0+ under wholesale
```
</details>

---

### `depreciation-tracker` — Consignment Timing

**Input:** *"Which vehicles are losing value fastest? I need to know timing for consignors"*

<details>
<summary><strong>View Output</strong></summary>

```
DEPRECIATION TRACKER: Missouri Market — Mar 7, 2026
Past 90 days sold data · Key segments for KC auction
═══════════════════════════════════════════════════

TOYOTA RAV4 — SOLD PRICE BY MODEL YEAR (MO, past 90d)
┌──────┬──────────┬──────────┬──────────┬──────────┬──────────────────┐
│ MY   │ Vol Sold │ Min      │ Median   │ Max      │ Year-to-Year Δ   │
├──────┼──────────┼──────────┼──────────┼──────────┼──────────────────┤
│ 2024 │  508     │ $22,977  │ $28,805  │ $44,979  │ base             │
│ 2023 │  153     │ $17,900  │ $29,485  │ $40,919  │ +2.4% vs 2024    │
│ 2022 │  109     │ $20,000  │ $28,112  │ $49,215  │ −2.4% vs 2024    │
└──────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘
  RAV4 VERDICT: Exceptional value retention. Median sold prices
  within $1,000 across three model years. 2023 MY slightly
  ABOVE 2024 (trim-mix effect — more hybrid/limited in resale).
  Consigners holding 2022 RAV4s are NOT in pain — values stable.

FORD F-150 — SOLD PRICE BY MODEL YEAR (MO, past 90d)
┌──────┬──────────┬──────────┬──────────┬──────────┬──────────────────┐
│ MY   │ Vol Sold │ Min      │ Median   │ Max      │ Year-to-Year Δ   │
├──────┼──────────┼──────────┼──────────┼──────────┼──────────────────┤
│ 2024 │  445     │ $12,700  │ $45,200  │$119,800  │ base             │
│ 2022 │  610     │ $10,900  │ $37,072  │ $68,750  │ −17.9% vs 2024   │
│ All  │ 10,312   │ $  650   │ $41,477  │$654,321  │ —                │
└──────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘
  F-150 VERDICT: Steep 2-year depreciation (~$8,000 drop from
  2024→2022 median). Dealers holding 2021-2022 F-150s in
  high-spec trims are feeling margin pressure.
  CONSIGNMENT OPPORTUNITY: Target F-150 dealers with 2021-2022
  MY trucks at 60+ DOM. They need to move.

CHEVROLET SILVERADO 1500 — SOLD (MO, past 90d)
┌──────┬──────────┬──────────┬──────────┬──────────┬──────────────────┐
│ MY   │ Vol Sold │ Min      │ Median   │ Max      │ Year-to-Year Δ   │
├──────┼──────────┼──────────┼──────────┼──────────┼──────────────────┤
│ 2022 │  325     │ $14,990  │ $35,900  │ $54,950  │ base (vs $42,160)│
│ All  │ 8,768    │ $ 3,600  │ $42,160  │ $99,237  │ −14.9% vs median │
└──────┴──────────┴──────────┴──────────┴──────────┴──────────────────┘
  SILVERADO VERDICT: Similar steep depreciation curve to F-150.
  2022 MY median $6,260 below overall market median.
  Silverado 2021-2022 with high miles = strong consignment pitch.

TOYOTA CAMRY — SOLD (MO, past 90d)
  Volume sold: 3,389 · Median: $28,063 · Range: $2,500-$47,129
  → High-velocity sedan. Dealers restock constantly.

DEPRECIATION RATE RANKINGS (for consignment urgency)
┌────┬────────────────────┬───────────────┬────────────────────────────┐
│  # │ Model              │ 2-Year Depr.  │ Consignment Timing         │
├────┼────────────────────┼───────────────┼────────────────────────────┤
│  1 │ Ford F-150 (2022)  │ −$8,128 / 2yr │ URGENT — pitch now         │
│  2 │ Chevy Silverado    │ −$6,260 / 2yr │ URGENT — pitch now         │
│    │ (2022 vs median)   │               │                            │
│  3 │ Toyota RAV4        │ −$  693 / 2yr │ HOLD — values stable       │
│    │ (2022 vs 2024)     │               │                            │
└────┴────────────────────┴───────────────┴────────────────────────────┘

CONSIGNMENT TIMING RECOMMENDATIONS
  1. Contact truck dealers with 2021-2023 MY F-150 / Silverado
     aging 45+ days. Floor plan burn + depreciation = motivation.
  2. RAV4 holders have pricing power — no urgency. Better as
     buyer-side vehicles at your sale (franchises will bid up).
  3. Minivans (Sienna/Odyssey): Demand is stable but supply is thin
     — good consignment candidate with motivated niche bidders.
```
</details>

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
