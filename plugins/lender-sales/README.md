# Lender Sales Plugin — MarketCheck

Dealer prospecting intelligence for **auto lender sales reps**. Dealer matching by lending criteria, floor plan opportunity scanning, lending fit analysis, territory dashboards, pitch deck data generation, and subprime dealer prospecting.

> **Note:** This plugin is for lender **sales teams** (finding and pitching dealers). For lender **credit/risk teams** (portfolio valuation, residual risk, collateral monitoring), use the [lender](../lender/) plugin instead.

---

## Who It's For

- Lender sales reps (field sales, calling on dealers)
- Regional sales managers overseeing territories
- BDC agents doing phone/digital dealer outreach
- Floor plan sales teams
- Subprime/non-prime lending sales reps
- Captive finance dealer development managers

---

## Skills (8)

Skills activate automatically when you ask questions in natural language — no slash commands needed.

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **dealer-match-finder** | "find dealers to call", "dealer prospecting", "who fits my criteria" | Finds dealers whose inventory matches your lending sweet spot — right price, makes, volume |
| **dealer-intelligence-brief** | "tell me about [dealer]", "prep for dealer meeting" | Deep-dive: inventory profile, lending fit, aging, floor plan burden, talking points |
| **lending-fit-analyzer** | "how many units can I lend on", "coverage analysis" | Overlays your lending criteria on a dealer's lot with LTV analysis |
| **floor-plan-opportunity-scanner** | "floor plan prospects", "who needs floor plan help" | Finds dealers with high-DOM inventory burning floor plan costs |
| **territory-dashboard** | "territory overview", "where should I focus" | Coverage vs opportunity across your target states with prioritization |
| **pitch-deck-data** | "data for my pitch", "market stats for dealer meeting" | Localized market data points for dealer sales conversations |
| **subprime-opportunity-finder** | "subprime dealers", "buy here pay here", "BHPH prospects" | Finds independent dealers specializing in budget vehicles — subprime sweet spot |
| **ev-lending-risk-monitor** | "EV lending risk", "which EVs hold value", "EV programs" | EV market dynamics for advising dealers on EV lending programs |

---

## Commands (5)

| Command | Usage | What It Does |
|---------|-------|-------------|
| `/onboarding` | `/onboarding` | One-time profile setup — lending type, criteria, territory, preferences |
| `/setup-mcp` | `/setup-mcp API_KEY` | Configure MarketCheck MCP connection |
| `/daily-briefing` | `/daily-briefing` | Morning: new prospects + market pulse + floor plan leads |
| `/weekly-review` | `/weekly-review` | Territory update + top 10 prospects + market trends |
| `/dealer-lookup` | `/dealer-lookup Smith Auto` | Quick dealer profile with lending fit |

---

## Agents (3)

| Agent | When It's Used | What It Does |
|-------|---------------|-------------|
| **territory-scanner** | Territory dashboard, weekly reviews | Parallel scanning across states — dealer counts, lendable units, opportunity scores |
| **dealer-profiler** | Dealer briefs, meeting prep | Deep-dive on one dealer — inventory + lending overlay + aging + talking points |
| **brand-market-analyst** | Weekly reviews, market trends | Brand volume, depreciation risk, segment trends for sales enablement |

### Agent Orchestration

```
WAVE 1 (parallel):
  ├─ lender-sales:territory-scanner    (cross-state coverage)
  ├─ lender-sales:brand-market-analyst (market trends)
  └─ Inline: dealer prospect scan      (top matches)

WAVE 2 (depends on targets):
  └─ lender-sales:dealer-profiler      (deep-dive on top prospects)
```

---

## Quick Start

```bash
# 1. Install
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin lender-sales

# 2. Connect MCP
/setup-mcp YOUR_API_KEY

# 3. Onboard your profile
/onboarding
```

After onboarding, try:
- `/daily-briefing` — morning prospect list + market pulse
- `/dealer-lookup Smith Auto` — quick dealer profile
- "Find dealers to call in Texas" — territory prospecting
- "Prep me for a meeting with [dealer name]" — full dealer brief
- "Who needs floor plan help?" — floor plan opportunity scan
- "Territory overview" — cross-state coverage dashboard

---

## Key Concepts

### Dealer Match Score

Every dealer is scored (0-100) based on how well they match your lending criteria:
- **Fit Score** (40 pts): % of dealer inventory matching your price/year/mileage/make criteria
- **Volume Score** (30 pts): Dealer lot size — bigger lots = more origination opportunity
- **Price Alignment** (30 pts): How close their avg price is to your sweet spot center

Classifications: **STRONG MATCH** (70+), **MODERATE** (50-69), **LIGHT** (30-49)

### Lending Fit Overlay

Shows exactly how much of a dealer's lot you can finance:
- **Coverage %**: matching units / total units
- **LTV Distribution**: spot-check sample against ML-predicted values
- **Gap Analysis**: why units don't qualify (too old, too expensive, wrong make)
- **Expansion Suggestions**: "If you raised your max price by $5K, you'd pick up 15 more units"

### Floor Plan Burden

Estimated monthly cost a dealer pays to finance their inventory:
- Calculation: total units × avg DOM × $35/day (industry standard)
- Aged units (DOM > 60) have outsized burden — these dealers are most receptive to competitive terms
- Savings pitch: "If we cut your rate by $5/day, you save $X/month"

### Lender vs Lender-Sales Plugin

| Aspect | Lender Plugin | Lender Sales Plugin |
|--------|--------------|-------------------|
| **User** | Credit analyst, risk manager | Sales rep, regional manager |
| **Goal** | Portfolio risk management | Dealer prospecting & pitching |
| **Focus** | Residual values, LTV, depreciation | Dealer matching, inventory fit, territory |
| **Output** | Risk signals, portfolio alerts | Prospect lists, talking points, pitch data |

---

## UK Support

UK lender sales reps are supported with dealer inventory scanning via `search_uk_active_cars`. Select UK during onboarding.

**Works for UK:** Dealer inventory scanning, inventory mix analysis, dealer matching
**US-only:** ML pricing, LTV analysis, demand analytics, territory velocity, floor plan estimation

---

## Live Example Outputs

> All examples below use **real market data** from the Texas market. Lender sales persona "Alliance Auto Finance / Sarah Chen" is fictional — used for illustration.

---

### `dealer-match-finder` — Find Dealers to Call in DFW

**Input:** *"Find dealers to call in the Dallas-Fort Worth area that match our lending criteria"*
*Criteria: $8K–$35K, 2018–2024 model years, under 90K miles*

<details>
<summary><strong>View Output</strong></summary>

```
DEALER MATCH FINDER — Dallas-Fort Worth Metro
Alliance Auto Finance · ZIP 75201 · 50-mile radius
Lending Criteria: $8K–$35K · 2018–2024 · <90K mi
═══════════════════════════════════════════════════

MARKET OVERVIEW (lendable units)
  Total active units in criteria:   12,892
  Dealer type:                       Independent
  Avg price (in-criteria):          $22,908
  Median DOM:                        142 days
  Lendable price range:             $13,515–$33,243 (P5–P95)

TOP DEALER MATCHES
┌───┬──────────────────────────┬──────────────┬──────┬──────────────────┬──────────────────────┐
│ # │ Dealer                   │ City         │Score │ Lendable Units   │ Signal               │
├───┼──────────────────────────┼──────────────┼──────┼──────────────────┼──────────────────────┤
│ 1 │ Carvana Blue Mound       │ Fort Worth   │  79  │ 1,393            │ HIGH VOLUME          │
│ 2 │ CarMax McKinney          │ McKinney     │  76  │ 1,268            │ HIGH VOLUME          │
│ 3 │ Dealer ID 1023368        │ DFW Metro    │  71  │   759            │ STRONG MATCH         │
│ 4 │ Dealer ID 1038232        │ DFW Metro    │  68  │   652            │ MODERATE             │
│ 5 │ Dealer ID 1058095        │ DFW Metro    │  65  │   609            │ MODERATE             │
│ 6 │ Dealer ID 10020326       │ DFW Metro    │  59  │   367            │ MODERATE             │
│ 7 │ Sign It Drive It         │ Denton       │  54  │  ~130            │ MODERATE             │
│ 8 │ First Start Motors LLC   │ Dallas       │  52  │   ~80            │ LIGHT / GROWING      │
└───┴──────────────────────────┴──────────────┴──────┴──────────────────┴──────────────────────┘

MATCH SCORE BREAKDOWN (Top Independent — Dealer 1023368)
  Fit Score (40 pts):       28 / 40   → ~70% of lot in criteria price/year/mile range
  Volume Score (30 pts):    24 / 30   → 759 lendable units (strong lot size)
  Price Alignment (30 pts): 19 / 30   → Avg $24,615 — slightly above sweet spot center
  ─────────────────────────────────────
  TOTAL:                    71 / 100  → STRONG MATCH

CLASSIFICATIONS
  STRONG MATCH (70+):   3 dealers   → prioritize for outreach this week
  MODERATE (50–69):     5 dealers   → warm pipeline, schedule Q2 calls
  LIGHT (30–49):        balance     → monitor, not yet worth floor-plan pitch
```
</details>

---

### `dealer-intelligence-brief` — Meeting Prep: Sign It Drive It, Denton TX

**Input:** *"Prep me for a meeting with Sign It Drive It in Denton — what's their inventory profile?"*
*(Independent dealer, 809 South Woodrow Lane, Denton TX 76205)*

<details>
<summary><strong>View Output</strong></summary>

```
DEALER INTELLIGENCE BRIEF
═══════════════════════════════════════════════════
  Dealer:   Sign It Drive It
  Address:  809 South Woodrow Lane, Denton, TX 76205
  Phone:    940-383-0200
  Type:     Independent used car lot
  Source:   signitdriveit.com

INVENTORY PROFILE (active listings)
  Active Units:        ~130 used vehicles
  Price Range:         $8,000 – $35,000
  Avg Asking Price:    $22,908 (market avg, criteria segment)
  Median Miles:        ~35,000 mi (well within 90K limit)
  Median DOM:          178 days (active listing, high aging)

FLOOR PLAN BURDEN ESTIMATE
  Units on lot:              ~130
  Avg DOM (active):           178 days
  Floor plan rate:           × $35/day
  ──────────────────────────────────────
  Est. Monthly Burden:       ~$809,900/mo (annualized carry)
  High-aging units (DOM>60): significant portion of lot

LENDING FIT SNAPSHOT
  In-criteria units (est.):   ~75–90 (Dealer market avg 70% fit)
  Price segment:              Nissan Rogue Sport, Sentra, Altima — core lendable
  Sample unit on lot:         2020 Nissan Rogue Sport S · 35,788 mi · $15,727
                              → ML Price: $16,635 (priced $908 BELOW market)
                              → LTV at $15,727: 94.5% of $16,635 — within lending band

TALKING POINTS FOR MEETING
  1. "Your Nissan Rogues and Sentras are exactly in our wheelhouse — $8K–$35K,
     2018–2024 vintage. We can fund same-day on 70–80% of your floor."
  2. "At 178 average DOM on active listings, you're carrying real floor plan
     cost. We have dealer-friendly terms that can cut your monthly carry."
  3. "Your price point at ~$15K–$16K is ideal for our $10K–$25K sweet spot
     — these are the deals that close fastest at retail."
  4. "We do ML-backed LTV validation in real time — no paper chase, fast
     approvals mean you turn units faster."
```
</details>

---

### `lending-fit-analyzer` — Coverage Analysis: DFW Independent Dealers

**Input:** *"How many units can we lend on at these dealers? Show me the coverage analysis"*
*Based on real DFW independent dealer data (50-mile radius, ZIP 75201)*

<details>
<summary><strong>View Output</strong></summary>

```
LENDING FIT OVERLAY — DFW Independent Dealers
Alliance Auto Finance · Criteria: $8K–$35K · 2018–2024 · <90K mi
═══════════════════════════════════════════════════

COVERAGE SUMMARY
  Total independent units (50 mi):    44,898
  In-criteria (lendable):             12,892
  Overall Coverage %:                 28.7%

PRICE DISTRIBUTION OF LENDABLE UNITS
  Median price:     $22,507
  P25:              $18,381    P75: $27,434
  P90:              $31,453    P95: $33,243

MILEAGE PROFILE
  Median miles:     53,408
  P25:              35,199 mi  P75: 70,014 mi
  P90:              81,479 mi  (most well below 90K cap)

LTV SPOT-CHECK (ML-backed, 3 sample units)
┌───┬──────────────────────────────┬─────────┬────────────┬──────────┬───────┐
│ # │ Vehicle                      │ Asking  │ ML Value   │ LTV      │ Fit   │
├───┼──────────────────────────────┼─────────┼────────────┼──────────┼───────┤
│ 1 │ 2020 Nissan Rogue Sport S    │ $15,727 │ $16,635    │ 94.5%    │ YES   │
│ 2 │ 2019 Nissan Sentra S         │ $12,995 │ ~$13,800   │ 94.2%    │ YES   │
│ 3 │ 2018 Nissan Rogue S (9K mi) │ $15,500 │ ~$16,200   │ 95.7%    │ YES   │
└───┴──────────────────────────────┴─────────┴────────────┴──────────┴───────┘
  Comps available: 104 active listings in 50 mi (Rogue Sport comp set)
  Active comp median: $14,935 (dealers pricing well in range)

GAP ANALYSIS — Why Units Don't Qualify
  Too old (pre-2018):     ~38% of non-qualifying units
  Too expensive (>$35K):  ~22% of non-qualifying units
  Too many miles (>90K):  ~28% of non-qualifying units
  Other/missing data:     ~12%

EXPANSION SUGGESTIONS
  If you raised max price to $40K:   +3,200 more lendable units (+25%)
  If you extended to 2017 model year: +2,100 more units (+16%)
  If you raised max miles to 100K:   +1,400 more units (+11%)
  → Biggest win: raising price ceiling to $40K captures more 2022–2024 SUVs
    (RAV4, CR-V, Tucson) that are pricing just above your current $35K cap
```
</details>

---

### `floor-plan-opportunity-scanner` — High-DOM Dealers in DFW

**Input:** *"Who in my territory has the highest floor plan burden? I want to pitch competitive floor plan rates"*

<details>
<summary><strong>View Output</strong></summary>

```
FLOOR PLAN OPPORTUNITY SCANNER
Alliance Auto Finance · ZIP 75201 · 100-mile radius
═══════════════════════════════════════════════════

MARKET CONTEXT (independent dealers, DOM > 45 days)
  Units with DOM > 45:    44,898 (all independents, 100 mi)
  Units with DOM > 60:    39,135
  Mean DOM (aging units):    249 days
  Median DOM (aging units):  192 days

TOP FLOOR PLAN PROSPECTS (by estimated burden)
┌───┬──────────────────────────┬──────┬─────────┬──────────┬────────────────────────┐
│ # │ Dealer                   │ City │ Units   │ Avg DOM  │ Est. Monthly Burden    │
├───┼──────────────────────────┼──────┼─────────┼──────────┼────────────────────────┤
│ 1 │ Carvana (DFW network)    │ FTW  │ 1,969   │ ~192     │ ~$13,200,000/mo est.  │
│ 2 │ CarMax McKinney          │ MCK  │ 1,396   │ ~192     │ ~$9,364,800/mo est.   │
│ 3 │ Dealer ID 1023368        │ DFW  │   967   │ ~192     │ ~$6,490,560/mo est.   │
│ 4 │ Dealer ID 1058095        │ DFW  │   869   │ ~249     │ ~$7,561,395/mo est.   │
│ 5 │ Bad Credit Call Fadi     │ DAL  │   577   │ ~148     │ ~$2,984,820/mo est.   │
│ 6 │ Dealer ID 10020326       │ DFW  │   447   │ ~192     │ ~$2,999,520/mo est.   │
└───┴──────────────────────────┴──────┴─────────┴──────────┴────────────────────────┘
  Burden formula: units × avg DOM × $35/day (industry standard)

HIGH-VELOCITY SAVINGS PITCH
  Dealer ID 1058095 (869 units × 249 avg DOM × $35):
    Current estimated burden:   ~$7,561,395/mo
    If we cut rate by $5/day:   Save ~$1,080,195/mo = $12.9M/year
    Talking point: "At your current DOM and unit count, we could save you
    over $1 million a month with competitive floor plan financing."

MOST RECEPTIVE PROSPECTS (aging + volume sweet spot)
  → Dealers with 200–800 units AND DOM > 150 = highest pain + decision authority
  → Bad Credit Call Fadi (577 units, 148 DOM): BHPH overlap — dual pitch
    opportunity for retail paper AND floor plan
  → Sign It Drive It (Denton, 178 active DOM): smaller lot but severe aging

CALL PRIORITY THIS WEEK
  1. Dealer 1058095 — largest floor plan pain relative to lot size
  2. Dealer 1023368 — strong lendable fit + high volume + aging burden
  3. Bad Credit Call Fadi — BHPH candidate, dual pitch floor plan + retail
```
</details>

---

### `territory-dashboard` — Texas Territory Overview

**Input:** *"Give me a territory overview for Texas — where should I focus my calls?"*

<details>
<summary><strong>View Output</strong></summary>

```
TERRITORY DASHBOARD: Texas (TX)
Alliance Auto Finance · Sarah Chen · March 2026
═══════════════════════════════════════════════════

HEADLINE NUMBERS
  Active Supply (TX):      265,901 listings
  Sold (past 90 days):   1,419,756 transactions
  State Turnover Ratio:     5.34x (sold vs. active supply)
  Median Active Price:     $23,417
  Median DOM:               124 days

TOP MAKES BY SOLD VOLUME (TX, 90 days)
┌────┬──────────────┬──────────┬────────┬────────────────────────────┐
│  # │ Make         │ Sold 90d │ Share  │ Lending Fit                │
├────┼──────────────┼──────────┼────────┼────────────────────────────┤
│  1 │ Ford         │  210,976 │ 14.9%  │ F-150, Escape = strong     │
│  2 │ Toyota       │  172,030 │ 12.1%  │ Camry, RAV4 = best fit     │
│  3 │ Chevrolet    │  165,470 │ 11.7%  │ Silverado, Equinox = fit   │
│  4 │ Nissan       │   97,696 │  6.9%  │ Altima, Rogue = core       │
│  5 │ Honda        │   72,989 │  5.1%  │ Civic, CR-V = strong       │
│  6 │ GMC          │   71,417 │  5.0%  │ terrain = moderate fit     │
│  7 │ Hyundai      │   68,465 │  4.8%  │ Elantra, Tucson = strong   │
│  8 │ Jeep         │   62,201 │  4.4%  │ mixed — watch LTV          │
│  9 │ KIA          │   59,078 │  4.2%  │ Sportage, Forte = fit      │
│ 10 │ RAM          │   56,449 │  4.0%  │ pickups = moderate LTV     │
└────┴──────────────┴──────────┴────────┴────────────────────────────┘

MARKET OPPORTUNITY BY METRO
┌──────────────────┬─────────┬──────────────┬──────────────┬───────────┐
│ Metro            │ Active  │ Median Price │ Median DOM   │ Priority  │
├──────────────────┼─────────┼──────────────┼──────────────┼───────────┤
│ Dallas-Fort Worth│  85,000+│    $23,417   │  124 days    │ TIER 1    │
│ Houston          │  74,082 │    $21,726   │  143 days    │ TIER 1    │
│ San Antonio      │  26,256 │    $23,098   │  107 days    │ TIER 2    │
│ Austin           │  20,300 │    $24,317   │   99 days    │ TIER 2    │
└──────────────────┴─────────┴──────────────┴──────────────┴───────────┘

PRIORITY AREAS — WHERE TO FOCUS
  1. Dallas-Fort Worth: Largest market, 12,892 lendable independent units,
     avg DOM 142 days = dealers feeling floor plan pain. Best metro for
     immediate prospecting.

  2. Houston: 74,082 active, highest median DOM (143 days) = most floor
     plan pressure in state. Budget segment ($3K–$12K subprime dealers:
     8,293 units) = dual channel opportunity.

  3. San Antonio: Balanced market, fast DOM (107 days) = less floor plan
     pain but dealers are active buyers → pitch retail paper instead.

  4. Austin: Smallest active market, fastest DOM (99 days) = best demand
     signal. Target franchise-adjacent independents here.

WEEKLY CALL TARGETS (by tier)
  Mon–Tue:  DFW independents (focus dealer IDs 1023368, 1058095, 1038232)
  Wed:      Houston floor plan sweep (high-DOM independents)
  Thu:      San Antonio franchise-adjacent independents
  Fri:      Austin top independents + follow-up callbacks
```
</details>

---

### `pitch-deck-data` — Market Stats for Toyota Dealer Meeting

**Input:** *"Give me market data points for my pitch to a Dallas Toyota dealer — they're skeptical about our rates"*

<details>
<summary><strong>View Output</strong></summary>

```
PITCH DECK DATA: Toyota Market — Dallas, TX
Alliance Auto Finance · ZIP 75201 · 50-mile radius
═══════════════════════════════════════════════════

TOYOTA ACTIVE MARKET (DFW, 50 mi)
  Active Toyota listings:    7,084
  Median asking price:       $23,713
  Median mileage:            62,288 mi
  Median DOM:                85 days (faster than market avg of 124)

TOP TOYOTA MODELS — ACTIVE SUPPLY (DFW)
┌────┬───────────────────┬──────────┬─────────────────────────────────┐
│  # │ Model             │ Active   │ Lender Note                     │
├────┼───────────────────┼──────────┼─────────────────────────────────┤
│  1 │ Camry             │  1,406   │ Core sweet spot — $18K–$28K    │
│  2 │ Corolla           │  1,149   │ Entry fit — $15K–$22K          │
│  3 │ RAV4              │    824   │ Strong LTV, fast turn           │
│  4 │ Tacoma            │    775   │ Trucks hold value — LTV-safe   │
│  5 │ Tundra            │    622   │ Higher price — near $35K cap   │
│  6 │ Highlander        │    581   │ $22K–$38K — partial coverage   │
│  7 │ 4Runner           │    464   │ Strong retention, price varies │
│  8 │ Sienna            │    280   │ Minivan — solid sub-$30K fit   │
└────┴───────────────────┴──────────┴─────────────────────────────────┘

TOYOTA SOLD VELOCITY (TX statewide, 90 days)
  Total Toyota sold (TX):  172,030 transactions
  Top sellers: Camry (28,671) · Tacoma (27,993) · RAV4 (21,961) · Tundra (21,794)
  Toyota = #2 brand in TX by sold volume (behind Ford, ahead of Chevrolet)

SOLD PRICING (Dallas 50 mi, Toyota, 90 days)
  Transactions:   42,843 sold
  Median sold:    $34,473
  P25 sold:       $25,061   P75 sold: $47,047
  → Median active ($23,713) vs median sold ($34,473): Toyota resale is
    strong in DFW — these cars are moving at higher-than-asking prices

VALUE POINTS FOR DEALER CONVERSATION
  1. "Toyota is the #2 brand in Texas — 172,030 units sold last 90 days.
     Your inventory has built-in demand we can leverage for faster paper."

  2. "Your Camrys and Corollas are exactly in our $15K–$28K lending band.
     We can fund same-day on those — no back-and-forth."

  3. "With a median DOM of 85 days on Toyota vs the 124-day market average,
     you turn faster than most — that means you need a lender who can keep
     up. We can."

  4. "RAV4s and Tacomas hold collateral value exceptionally well in TX —
     our LTV approval rates on those models are among the highest we have."

  5. "42,843 Toyota transactions in DFW last 90 days. That's velocity. Help
     us help you capture more of it with faster financing decisions."
```
</details>

---

### `subprime-opportunity-finder` — BHPH Prospects in Houston

**Input:** *"Find BHPH and buy-here-pay-here dealers in Houston for our subprime program"*

<details>
<summary><strong>View Output</strong></summary>

```
SUBPRIME OPPORTUNITY FINDER — Houston, TX
Alliance Auto Finance · ZIP 77001 · 30-mile radius
Budget segment: $3K–$12K · Independent dealers only
═══════════════════════════════════════════════════

MARKET OVERVIEW
  Budget units active (30 mi):    8,293
  Median price:                   $8,553
  Median mileage:                 126,713 mi
  Avg DOM:                        312 days (extreme aging = high pain)

TOP SUBPRIME PROSPECTS
┌───┬────────────────────────────┬───────────────────────┬────────┬──────────┬────────────────────────────┐
│ # │ Dealer                     │ Address               │ Units  │ Avg Px   │ Program Fit                │
├───┼────────────────────────────┼───────────────────────┼────────┼──────────┼────────────────────────────┤
│ 1 │ Scott Harrison Motor Co    │ 2303 W Mt Houston Rd  │  208+  │ ~$4,800  │ Deep subprime / BHPH       │
│ 2 │ 713 Car Loan               │ 7070 SW Freeway       │  166+  │ ~$10,500 │ In-house finance / BHPH   │
│ 3 │ Regal Preowned Autos       │ 11321 S Main St       │  155+  │ ~$5,500  │ Cash/BHPH, aging stock    │
│ 4 │ Dealer ID 1089020          │ Houston metro         │  129   │ ~$8,500  │ Subprime sweet spot       │
│ 5 │ Dealer ID 10004180         │ Houston metro         │  115   │ ~$8,500  │ Moderate subprime fit     │
└───┴────────────────────────────┴───────────────────────┴────────┴──────────┴────────────────────────────┘

DEALER PROFILES

Scott Harrison Motor Co (scottharrisonmotorco.com)
  Type:    Independent BHPH / deep subprime
  Area:    North Houston (77038)
  Mix:     Budget sedans $3,500–$7,000, older vehicles, high mileage
  Signal:  BMW 325i for $4,999 at 159K mi; GL-Class for $3,999 at 157K mi
           → operating at cash/note buyer level
  Pitch:   "We have a subprime program that starts at $5K. Let's move
            your oldest units with financing instead of cash."

713 Car Loan (713carloan.com)
  Type:    BHPH / in-house finance specialist (name confirms)
  Area:    SW Houston (77074)
  Mix:     $8,000–$12,000 range, 2010–2018 vehicles
  Signal:  Hyundai Sonata $10,450; Ford Fusion $11,998; Volvo S60 $10,900
  DOM:     1,168+ days active on some units — extreme aging
  Pitch:   "You're already doing in-house — let us take the paper off your
            hands. We can fund your volume and free up your capital."

SUBPRIME PROGRAM FIT SUMMARY
  Price point ($3K–$12K):    8,293 units in Houston metro
  Avg mileage:                127K — requires flexible LTV/mileage policy
  Avg DOM:                    312 days → dealers desperate to move units
  Opportunity:                Dealers currently using cash/BHPH would convert
                              to lender paper if terms are competitive

TALKING POINT: "Houston has 8,293 active budget-segment units sitting
an average of 312 days. These dealers are bleeding floor plan costs.
Our subprime program can convert aged inventory into funded deals —
same day approvals on qualifying vehicles."
```
</details>

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
