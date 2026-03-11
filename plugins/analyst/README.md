# Analyst Plugin — MarketCheck

Automotive market intelligence for **financial analysts, equity researchers, and portfolio managers**. The analyst plugin closes the **90-day information gap** between quarterly earnings — using real-time dealer inventory, transaction velocity, pricing power, and DOM signals as leading indicators for OEM and dealer group equities.

Wall Street's quarterly earnings cycle creates a data void: OEMs report every 90 days, but the channel moves daily. MarketCheck captures 600K+ dealer listings and millions of transactions across the US market. This plugin transforms that data into investment signals — BULLISH, BEARISH, NEUTRAL, CAUTION — tied to stock tickers, with basis-point precision and trend velocity.

---

## Validated Signal Track Record

Early adopters have identified material signals 30–90 days before earnings confirmed them:

| Case | Signal Detected | Lead Time | What Happened |
|------|----------------|-----------|---------------|
| **Carvana (CVNA)** | Sourcing quality deteriorating — avg mileage up ~10% (48K→54K), inventory aging | ~11 months pre-miss | CVNA reported reconditioning cost headwinds and margin compression |
| **Ford (F)** | Mach-E DOM at 354 days, supply/demand gap -1.2pp, EV penetration at 1.1% | ~2 quarters pre-guidance cut | Ford cut EV production targets and wrote down battery investments |
| **Stellantis (STLA)** | Jeep oversupply -1.0pp gap, DOM declining 14% QoQ — turnaround signal | ~1 quarter pre-beat | STLA beat lowered estimates as inventory discipline improved |

These aren't backtested — they're signals that were visible in the data before earnings confirmed the thesis.

---

## Who It's For

| Analyst Type | Primary Skills | Key Use Case |
|-------------|---------------|-------------|
| **Equity Research (OEM coverage)** | oem-stock-tracker, pricing-power-tracker, earnings-preview | Pre-earnings channel checks, margin pressure detection |
| **Equity Research (dealer groups)** | dealer-group-health-monitor, group-dashboard, sourcing-quality-signal | Inventory turns, used vehicle sourcing quality, peer comparison |
| **Hedge Fund / Event-Driven** | earnings-preview, dom-monitor, new-used-mix-analyzer | Signal-driven thesis validation, short/long catalyst identification |
| **Credit / Auto Lending** | depreciation-tracker, sourcing-quality-signal, market-momentum-report | Residual risk, collateral quality, portfolio exposure monitoring |
| **Sell-Side / Sector Strategy** | market-share-analyzer, market-momentum-report, ev-transition-monitor | Sector reports, brand positioning, EV adoption curve tracking |

---

## Data Coverage

| Dimension | Coverage |
|-----------|---------|
| **Frequency** | Real-time dealer listings; monthly sold aggregates |
| **History** | 90-day rolling transaction window, 6-month trend baselines |
| **Scope** | 600K+ active US dealer listings, millions of monthly transactions |
| **Geography** | All 50 US states, state-level and national views |
| **Vehicle Types** | New + Used (key differentiator — most alt-data covers only one) |
| **Inventory Types** | New, Used, Certified Pre-Owned (CPO) |
| **Metrics** | Price, MSRP, DOM, sold count, body type, fuel type, dealer group |

---

## Key Derived Metrics

| Metric | Formula | Investment Signal |
|--------|---------|------------------|
| **Days Supply** | active_inventory / monthly_sold × 30 | <45d BULLISH, 45-75d NEUTRAL, >75d BEARISH |
| **Supply/Demand Gap** | supply_share% - sold_share% | Negative = oversupplied, Positive = undersupplied |
| **Discount Velocity** | (current_discount% - 3mo_discount%) / 3 | Widening >50 bps/mo = margin pressure |
| **DOM Rate of Change** | (current_DOM - prior_DOM) / prior_DOM | Rising >10% = demand deterioration |
| **New-Car Share** | new_sold / (new_sold + used_sold) × 100 | Declining >150 bps/qtr = consumer trade-down |
| **CPO Penetration** | CPO_count / total_used × 100 | Rising = franchise dealer confidence |
| **Recon Risk Score** | (avg_miles / 50,000) × 100, capped at 100 | >75 = high reconditioning cost exposure |

---

## Skills (14)

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **oem-stock-tracker** | "how is Ford stock doing", "OEM investment signal", "F stock" | 8-step OEM analysis: market share + pricing power + depreciation + EV exposure → BULLISH/BEARISH/NEUTRAL signal per ticker |
| **dealer-group-health-monitor** | "how is AutoNation doing", "AN stock", "dealer group health" | Publicly traded dealer group stock health with inventory turn, pricing, DOM, and peer comparison |
| **ev-transition-monitor** | "EV adoption rate", "EV investment thesis", "EV vs ICE" | EV penetration rates, brand-level EV share, EV vs ICE depreciation comparison for investment thesis |
| **market-momentum-report** | "sector momentum", "market momentum", "auto sector trends" | Segment-level volume and pricing momentum with investment signal ratings |
| **depreciation-tracker** | "depreciation rate", "residual value signals", "value retention" | Depreciation curves framed as residual value signals for OEM and lending stocks |
| **market-share-analyzer** | "market share", "who is winning", "brand performance" | Brand market share with basis point changes, segment conquest, competitive positioning |
| **market-trends-reporter** | "market trends", "sector intelligence", "market report" | Comprehensive market trend analysis for sector research |
| **group-dashboard** | "dealer group overview", "how are the public groups doing" | Multi-location group health for tracked dealer group stocks |
| **group-benchmarking** | "compare dealer groups", "group peer comparison" | Peer comparison of publicly traded dealer groups |
| **pricing-power-tracker** | "pricing power", "discount rate trend", "who's discounting", "MSRP vs sale price" | Discount-to-MSRP trajectory over 5 periods with velocity metrics — leading indicator of margin pressure |
| **dom-monitor** | "days on market trend", "DOM signal", "which OEMs are sitting on inventory" | DOM as primary demand signal with rate-of-change, inflection detection, and distress flags |
| **sourcing-quality-signal** | "used vehicle quality", "mileage trends", "sourcing risk for CVNA" | Used vehicle mileage/age analysis for dealer groups — reconditioning cost proxy and sourcing quality |
| **earnings-preview** | "earnings preview for F", "pre-earnings check", "what will Ford report" | 7-dimension pre-earnings channel check synthesizing DOM + discounts + inventory + velocity + EV + mix into bull/bear scenarios |
| **new-used-mix-analyzer** | "new vs used mix", "consumer trade-down", "CPO volume", "new used split" | New vs used vehicle mix analysis — consumer health signal, OEM channel dynamics, dealer margin analysis |

---

## Commands (6)

| Command | What It Does |
|---------|-------------|
| `/onboarding` | Analyst profile setup — tracked tickers, focus area, benchmark period |
| `/market-snapshot` | State or national market intelligence snapshot |
| `/setup-mcp` | Configure MCP connection |
| `/earnings-preview F` | Pre-earnings channel check for a ticker — 6-dimension bull/bear synthesis |
| `/watchlist-scan` | Morning briefing across all tracked tickers — prioritized alerts |
| `/compare F GM` | Head-to-head peer comparison of two tickers |

---

## Agents (5)

| Agent | Color | What It Does |
|-------|-------|-------------|
| **brand-market-analyst** | orange | Multi-period sold data analysis with investment signal framing (BULLISH/BEARISH/NEUTRAL/CAUTION) |
| **portfolio-scanner** | green | Batch VIN analysis for portfolio sample revaluation with ticker-level aggregation |
| **group-scanner** | blue | Multi-location parallel scan for dealer group health assessment |
| **earnings-signal-agent** | orange | Multi-step pre-earnings assessment — combines 7 dimensions into bull/bear scenarios with signal strength |
| **watchlist-monitor-agent** | cyan | Parallel scan across all tracked tickers — prioritized alert list with configurable thresholds |

---

## Quick Start

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin analyst
/setup-mcp YOUR_API_KEY
/onboarding
```

During onboarding, you'll set up:
- **Tracked tickers** — e.g., F, GM, TSLA, AN, LAD, PAG, KMX, CVNA
- **Focus area** — OEM, dealer groups, EV transition, lending, or general
- **Benchmark period** — comparison window (default 3 months)

After onboarding, try:
- "How is Ford doing?" — full OEM investment signal
- `/earnings-preview F` — pre-earnings channel check with bull/bear scenarios
- `/watchlist-scan` — morning briefing across all tracked tickers
- `/compare F GM` — head-to-head peer comparison
- "EV adoption update" — EV transition intelligence
- "Who has pricing power in pickups?" — segment discount comparison

---

## Investment Signal Ratings

Every metric in the analyst plugin gets an explicit signal:

| Signal | Meaning |
|--------|---------|
| **BULLISH** | Positive trend, improving fundamentals |
| **BEARISH** | Negative trend, deteriorating fundamentals |
| **NEUTRAL** | Stable, no significant change |
| **CAUTION** | Mixed signals, requires monitoring |

Signals are assigned per metric with rationale, not as blanket recommendations. Some signals carry **dual perspective** — a BEARISH signal for an OEM ticker (declining new-car share) can simultaneously be BULLISH for used-vehicle retailers (KMX, CVNA).

---

## Built-in Ticker → Makes Mapping

### OEM Tickers (13)

| Ticker | Company | Makes |
|--------|---------|-------|
| F | Ford Motor | Ford, Lincoln |
| GM | General Motors | Chevrolet, GMC, Buick, Cadillac |
| TM | Toyota Motor | Toyota, Lexus |
| HMC | Honda Motor | Honda, Acura |
| STLA | Stellantis | Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati |
| TSLA | Tesla | Tesla |
| RIVN | Rivian | Rivian |
| LCID | Lucid | Lucid |
| HYMTF | Hyundai Motor Group | Hyundai, Kia, Genesis |
| NSANY | Nissan | Nissan, Infiniti |
| MBGAF | Mercedes-Benz | Mercedes-Benz |
| BMWYY | BMW | BMW, MINI, Rolls-Royce |
| VWAGY | Volkswagen Group | Volkswagen, Audi, Porsche, Lamborghini, Bentley |

### Dealer Group Tickers (8)

| Ticker | Company | Type |
|--------|---------|------|
| AN | AutoNation | Franchise (multi-brand) |
| LAD | Lithia Motors | Franchise (multi-brand) |
| PAG | Penske Automotive | Franchise (multi-brand) |
| SAH | Sonic Automotive | Franchise (multi-brand) |
| GPI | Group 1 Automotive | Franchise (multi-brand) |
| ABG | Asbury Automotive | Franchise (multi-brand) |
| KMX | CarMax | Used-only retailer |
| CVNA | Carvana | Used-only retailer (online) |

Note: KMX and CVNA are 100% used retailers. For these tickers, new/used mix analysis is replaced with within-used quality analysis (vehicle age, mileage, reconditioning risk).

---

## Example Workflows

### OEM Investment Signal
```
How is Ford doing?
```
→ 8-step analysis: market share (±bps) + pricing power + depreciation watch + EV exposure + segment momentum → BULLISH/BEARISH/NEUTRAL per metric + overall signal

### Pre-Earnings Channel Check
```
/earnings-preview F
```
→ 6-dimension synthesis: volume momentum + pricing power + inventory health + DOM velocity + EV sell-through + new/used mix → bull case, bear case, composite signal with strength rating

### Morning Watchlist Scan
```
/watchlist-scan
```
→ Parallel scan across all tracked tickers, sorted by signal severity: ALERT (2+ BEARISH) → WATCH (1 BEARISH) → STABLE → STRONG. One-line actionable note per flagged ticker.

### Head-to-Head Peer Comparison
```
/compare F GM
```
→ Side-by-side table: volume MoM, discount rate, days supply, avg DOM — with "edge" column and verdict

### Pricing Power Trend
```
Show me the discount trend for Ford over the last 6 months
```
→ 5-period discount-to-MSRP trajectory with velocity metric (bps/month), nameplate breakdown, and margin pressure signal

### DOM Monitor
```
Which OEMs have rising days on market?
```
→ DOM ranking by OEM with rate-of-change, inflection points flagged, distress threshold alerts (>90 days)

### Sourcing Quality Signal
```
How is Carvana's sourcing quality trending?
```
→ Average mileage, age distribution, recon risk score, peer comparison vs KMX — with 12-month trend direction

### New/Used Mix Analysis
```
Are consumers trading down from new to used?
```
→ National new/used ratio with MoM and 3-month trend, segment breakdown, CPO penetration — dual signal (BEARISH for OEM, BULLISH for used retailers)

### Dealer Group Health
```
How is AutoNation doing compared to Lithia?
```
→ Inventory health, turn rates, pricing position, DOM trends for AN vs LAD with peer benchmarks

### EV Thesis Update
```
Give me an EV transition update for my coverage universe
```
→ EV penetration by brand, EV vs ICE depreciation gap, adoption curve analysis, investment implications

### Sector Report
```
Monthly auto sector report for my tracked tickers
```
→ Per-ticker signals, sector momentum, market share shifts, depreciation watch, EV update

### Market Share Deep Dive
```
Who is winning market share nationally?
```
→ Top brands by sold volume with supply/demand gap, basis-point share changes, segment breakdown

### Discount Velocity Alert
```
Which OEMs are discounting most aggressively?
```
→ All OEMs ranked by discount velocity (bps/month), flagging tickers where velocity exceeds -50 bps/month as margin pressure warning

---

## Live Example Outputs

> All examples below use **real market data** framed for equity research context. Analyst persona "Meridian Capital" is fictional — used for illustration.

---

### `oem-stock-tracker` — Ford ($F) Investment Signal

**Input:** *"How is Ford doing? Give me the investment signal for $F"*

<details>
<summary><strong>View Output</strong></summary>

```
OEM INVESTMENT SIGNAL: Ford Motor Company — $F
Meridian Capital · Automotive Coverage · Mar 7, 2026
═══════════════════════════════════════════════════

TICKER MAPPING: F → Ford, Lincoln

STEP 1: MARKET SUPPLY POSITION
  Ford active supply (200mi, NYC/10001):  90,976 listings
  Ford active supply (TX, all):           98,175 listings
  TX total active supply:                610,694 listings
  Ford supply share (TX):                 16.1%
  → SIGNAL: CAUTION — Ford holds top supply share but
    high inventory = potential pricing pressure

STEP 2: SOLD VOLUME (TX, past 90 days)
  Ford sold:           210,976 transactions
  Toyota sold:         172,030 transactions
  Chevrolet sold:      165,470 transactions
  TX total sold:     1,419,756 transactions
  Ford volume share:    14.9%
  → SIGNAL: BULLISH — #1 in volume share nationally

STEP 3: SUPPLY vs DEMAND GAP
  Ford supply share (TX):  16.1%
  Ford volume share (TX):  14.9%
  Gap:                     −1.2 pp (over-supplied)
  → SIGNAL: BEARISH — Supply outpaces sales velocity;
    dealers holding more Ford inventory than they sell

STEP 4: EV TRANSITION EXPOSURE (F → Mustang Mach-E)
  Ford BEV active listings (TX):   1,092
  Total Ford active (TX):         98,175
  Ford EV penetration:              1.1% of active supply
  Mach-E median DOM:              354 days (1 unit sampled)
  → SIGNAL: BEARISH — EV lineup thin; Mach-E aging on
    lots. F-150 Lightning ramp needed to compete

STEP 5: COMPETITIVE POSITION (GM comparison)
  Chevrolet sold (TX 90d):        165,470
  Chevrolet supply share (TX):     11.3%
  Chevrolet volume share (TX):     11.7%
  → Chevrolet supply-demand BALANCED vs Ford OVERSUPPLIED
  → SIGNAL: CAUTION — Ford losing supply efficiency vs GM

STEP 6: SEGMENT EXPOSURE
  SUV (50% of TX sales) — Ford strong via Explorer/Expedition
  Pickup (25% of TX sales) — Ford #1 via F-Series
  Sedan (17% of TX sales) — Ford minimal presence
  → SIGNAL: NEUTRAL — segment mix favorable via truck dominance

STEP 7: PRICING PRESSURE
  TX median active asking price:  $37,819
  Ford median (range implied):    competitive truck pricing
  DOM pressure above 60d:         elevated on Mach-E
  → SIGNAL: CAUTION — Potential discounting risk on EV
    units; ICE truck pricing stable

STEP 8: OVERALL SIGNAL SUMMARY
┌─────────────────────────────┬──────────────┐
│ Metric                      │ Signal       │
├─────────────────────────────┼──────────────┤
│ Market Supply Position      │ CAUTION      │
│ Sold Volume Share (#1)      │ BULLISH      │
│ Supply vs Demand Efficiency │ BEARISH      │
│ EV Transition Exposure      │ BEARISH      │
│ Competitive Position vs GM  │ CAUTION      │
│ Segment Mix (truck heavy)   │ NEUTRAL      │
│ Pricing Pressure            │ CAUTION      │
└─────────────────────────────┴──────────────┘

══════════════════════════════════════════════
  OVERALL SIGNAL: CAUTION
  Ford dominates volume (#1 in TX sales) but
  carries the largest inventory overhang of
  any OEM. EV transition lagging — Mach-E
  DOM of 354d signals consumer hesitancy.
  Truck strength is the bull case; monitor
  F-150 Lightning sell-through quarterly.
══════════════════════════════════════════════
```
</details>

---

### `market-share-analyzer` — National Brand Share (Texas Market)

**Input:** *"Who is winning market share nationally? Show me the top 10 brands"*

<details>
<summary><strong>View Output</strong></summary>

```
MARKET SHARE ANALYSIS: Texas (TX) — All Vehicle Types
Meridian Capital · Sector Intelligence · Mar 7, 2026
═══════════════════════════════════════════════════

DATA: Past 90 days sold + current active supply · TX

BRAND MARKET SHARE (past 90 days sold volume)
┌────┬────────────────┬───────────┬────────┬─────────┬───────────┐
│  # │ Make           │ Sold 90d  │ Share  │ Supply  │ S/D Gap   │
├────┼────────────────┼───────────┼────────┼─────────┼───────────┤
│  1 │ Ford           │ 210,976   │ 14.9%  │  98,175 │ -1.2 pp   │
│  2 │ Toyota         │ 172,030   │ 12.1%  │  52,937 │ +3.5 pp   │
│  3 │ Chevrolet      │ 165,470   │ 11.7%  │  68,836 │ -0.4 pp   │
│  4 │ Nissan         │  97,696   │  6.9%  │  44,613 │  -0.2 pp  │
│  5 │ Honda          │  72,989   │  5.1%  │  29,700 │ +0.4 pp   │
│  6 │ GMC            │  71,417   │  5.0%  │  27,937 │ +0.3 pp   │
│  7 │ Hyundai        │  68,465   │  4.8%  │  33,153 │ -0.6 pp   │
│  8 │ Jeep           │  62,201   │  4.4%  │  32,206 │ -1.0 pp   │
│  9 │ BMW            │  41,962   │  3.0%  │  19,870 │ -0.8 pp   │
│ 10 │ Mercedes-Benz  │  36,415   │  2.6%  │  17,633 │ -0.7 pp   │
├────┼────────────────┼───────────┼────────┼─────────┼───────────┤
│    │ TX Total       │1,419,756  │        │ 610,694 │           │
└────┴────────────────┴───────────┴────────┴─────────┴───────────┘
  S/D Gap = supply % share minus sold % share
  Negative = over-supplied · Positive = under-supplied

INVESTMENT SIGNALS BY OEM
┌────────────────┬────────────────────────────────────────────────┐
│ Make / Ticker  │ Supply-Demand Signal                           │
├────────────────┼────────────────────────────────────────────────┤
│ Toyota (TM)    │ BULLISH — +3.5 pp undersupply; sells faster    │
│                │ than stocked. Pricing power intact.            │
│ Honda (HMC)    │ BULLISH — +0.4 pp; efficient inventory turns   │
│ Ford (F)       │ CAUTION — −1.2 pp overhang; monitor discounts  │
│ Chevrolet (GM) │ NEUTRAL — near-balanced; GM truck mix helping  │
│ BMW (BMWYY)    │ BEARISH — −0.8 pp luxury oversupply; DOM risk  │
│ Mercedes (MBGAF)│ BEARISH — −0.7 pp; luxury demand softening   │
│ Hyundai (HYMTF)│ CAUTION — −0.6 pp; Ioniq ramp not yet showing │
│ Jeep (STLA)    │ BEARISH — −1.0 pp; Stellantis losing shelf     │
└────────────────┴────────────────────────────────────────────────┘

SEGMENT BREAKDOWN (TX sold 90d by body type)
┌──────────────┬───────────┬────────┐
│ Body Type    │  Sold 90d │ Share  │
├──────────────┼───────────┼────────┤
│ SUV          │  708,000  │ 49.9%  │
│ Pickup       │  350,136  │ 24.7%  │
│ Sedan        │  240,742  │ 17.0%  │
│ Hatchback    │   34,764  │  2.4%  │
│ Coupe        │   27,116  │  1.9%  │
│ Minivan      │   20,197  │  1.4%  │
│ Cargo Van    │    9,820  │  0.7%  │
│ Convertible  │    8,832  │  0.6%  │
└──────────────┴───────────┴────────┘
  SUV + Pickup = 74.6% of all TX transactions
  → Bullish for truck/SUV-heavy OEMs (F, GM, TM, STLA)
```
</details>

---

### `ev-transition-monitor` — EV Adoption Update

**Input:** *"Give me an EV transition update for my coverage universe — Tesla, GM, Ford"*

<details>
<summary><strong>View Output</strong></summary>

```
EV TRANSITION MONITOR: Tesla, GM, Ford — Mar 7, 2026
Meridian Capital · EV Coverage Universe
═══════════════════════════════════════════════════

EV ACTIVE INVENTORY (Texas — dealer listed)
┌─────────────────┬──────────────┬──────────────┬──────────────┐
│ Ticker / Make   │ Total Active │  BEV Active  │ EV Pen. Rate │
├─────────────────┼──────────────┼──────────────┼──────────────┤
│ TSLA / Tesla    │    1,604     │    1,604     │   100.0%     │
│ GM / Chevrolet  │   68,836     │    2,114     │     3.1%     │
│ F / Ford        │   98,175     │    1,092     │     1.1%     │
└─────────────────┴──────────────┴──────────────┴──────────────┘
  BEV = Battery Electric Vehicle (active dealer listings, TX)
  Ford BEV: Mustang Mach-E · GM BEV: Bolt EV / Bolt EUV

EV SOLD VELOCITY (TX, past 90 days)
  Tesla sold:       8,514 transactions (all-EV)
  Chevrolet BEV:    ~2,100 est. (Bolt/EUV segment)
  Ford BEV:         ~900 est. (Mach-E segment)

EV vs ICE SUPPLY COMPARISON
┌────────────────┬───────────┬──────────┬──────────────────────┐
│ Brand          │ ICE Units │ EV Units │ EV Dom Signal        │
├────────────────┼───────────┼──────────┼──────────────────────┤
│ Tesla          │        0  │   1,604  │ 9 day avg DOM — FAST │
│ Chevrolet Bolt │   66,722  │   2,114  │ 132 day avg — SLOW   │
│ Ford Mach-E    │   97,083  │   1,092  │ 354 day avg — STALE  │
└────────────────┴───────────┴──────────┴──────────────────────┘

INVESTMENT THESIS BY TICKER
┌──────────┬──────────────────────────────────────────────────────┐
│ Ticker   │ EV Thesis                                            │
├──────────┼──────────────────────────────────────────────────────┤
│ TSLA     │ BULLISH — Only pure-play; 9-day avg DOM confirms     │
│          │ strong consumer pull. 8,514 TX sold in 90d at        │
│          │ scale no legacy OEM matches. Pricing discipline       │
│          │ monitored post-2025 cuts.                            │
│ GM       │ NEUTRAL — Bolt platform selling but at thin margin.  │
│          │ 3.1% EV penetration of fleet is behind forecast.     │
│          │ Equinox EV ramp in 2026 is the key watch item.       │
│ F        │ BEARISH — 1.1% EV penetration with 354-day Mach-E   │
│          │ DOM is a warning. F-150 Lightning consumer demand     │
│          │ unclear from current TX supply signals. Risk of       │
│          │ production cuts.                                      │
└──────────┴──────────────────────────────────────────────────────┘

ADOPTION CURVE: EV share of new-car equivalent dealer stock
  2024 baseline:  ~1.5% EV share (estimated national avg)
  2026 current:   TSLA=100% · GM=3.1% · F=1.1%
  → Adoption bifurcating: Tesla pulling away while legacy
    OEM EV transitions remain in sub-4% territory.
```
</details>

---

### `depreciation-tracker` — Residual Value Signals (Toyota RAV4)

**Input:** *"Show me depreciation signals for Toyota RAV4 — residual value analysis for our ABS exposure"*

<details>
<summary><strong>View Output</strong></summary>

```
DEPRECIATION TRACKER: Toyota RAV4 — Texas (TX)
Meridian Capital · ABS / Residual Value Analysis · Mar 7, 2026
═══════════════════════════════════════════════════

SOLD PRICE BY MODEL YEAR (past 90 days, TX)
┌──────┬──────────┬──────────┬──────────┬──────────┬─────────────┐
│  MY  │  Volume  │  Min     │  Median  │  Max     │ Ret. (est.) │
├──────┼──────────┼──────────┼──────────┼──────────┼─────────────┤
│ 2024 │  2,427   │ $18,988  │ $27,710  │ $45,676  │ ~74% MSRP   │
│ 2023 │  1,154   │ $18,200  │ $27,978  │ $99,000  │ ~75% MSRP   │
│ 2022 │    841   │ $17,871  │ $25,995  │ $42,105  │ ~71% MSRP   │
└──────┴──────────┴──────────┴──────────┴──────────┴─────────────┘
  MSRP base reference: 2022 RAV4 LE ~$26,975 · 2024 LE ~$30,270

DEPRECIATION RATE ANALYSIS
  2024 MY: $27,710 median sold · ~74% retention at ~1yr
  2023 MY: $27,978 median sold · ~75% retention at ~2yr
  2022 MY: $25,995 median sold · ~71% retention at ~3yr
  → Annual depreciation rate: ~3–4% per year (1–3yr window)
  → Exceptionally low — RAV4 is one of top 5 retention brands

RESIDUAL VALUE RISK TIERS
┌────────────────────────┬────────────────┬───────────────────────┐
│ Metric                 │ Value          │ Risk Tier             │
├────────────────────────┼────────────────┼───────────────────────┤
│ 2022 retention (~3yr)  │ ~71% of MSRP   │ LOW RISK              │
│ 2024 retention (~1yr)  │ ~74% of MSRP   │ LOW RISK              │
│ Annual depr. rate      │ ~3–4%/yr       │ LOW RISK              │
│ Volume liquidity (90d) │ 4,422 units    │ HIGH LIQUIDITY        │
│ Price floor stability  │ <$3K MY spread │ LOW RISK              │
└────────────────────────┴────────────────┴───────────────────────┘

ABS / LENDING IMPLICATIONS
  → RAV4 collateral carries LOW residual risk.
  → 3-yr depreciation of ~29% is best-in-class for SUVs.
  → High 90d transaction volume (4,422 units TX only)
    confirms liquid secondary market — strong collateral.
  → No distressed pricing signals observed in floor data.
  → TM ticker (Toyota) = BULLISH from lending / ABS lens.
    RAV4 is the most financeable SUV collateral in the book.

SIGNAL: BULLISH for TM, HMC (similar profiles)
SIGNAL: BEARISH for STLA, NSANY (faster depreciators)
```
</details>

---

### `market-momentum-report` — Sector Momentum Q1 2026

**Input:** *"Give me sector momentum for Q1 2026 — which segments have the most tailwind?"*

<details>
<summary><strong>View Output</strong></summary>

```
SECTOR MOMENTUM REPORT: Q1 2026 — Texas Market
Meridian Capital · Auto Sector Intelligence · Mar 7, 2026
═══════════════════════════════════════════════════

HEADLINE METRICS (Texas — largest US auto market)
  Total Active Supply:   610,694 listings
  Sold (past 90 days): 1,419,756 transactions
  Market Turnover:          2.32x (sold ÷ active)
  Median Active Price:     $37,819

SEGMENT MOMENTUM TABLE
┌──────────────┬─────────┬───────────┬────────┬────────┬──────────┐
│ Segment      │ Supply  │ Sold 90d  │ D:S    │ Share  │ Signal   │
├──────────────┼─────────┼───────────┼────────┼────────┼──────────┤
│ SUV          │ 303,399 │  708,000  │ 2.33x  │ 49.9%  │ BULLISH  │
│ Pickup       │ 151,146 │  350,136  │ 2.32x  │ 24.7%  │ BULLISH  │
│ Sedan        │  98,672 │  240,742  │ 2.44x  │ 17.0%  │ NEUTRAL  │
│ Hatchback    │  15,918 │   34,764  │ 2.18x  │  2.4%  │ NEUTRAL  │
│ Coupe        │  11,744 │   27,116  │ 2.31x  │  1.9%  │ NEUTRAL  │
│ Minivan      │   8,875 │   20,197  │ 2.28x  │  1.4%  │ NEUTRAL  │
│ Cargo Van    │   6,158 │    9,820  │ 1.59x  │  0.7%  │ BEARISH  │
│ Convertible  │   4,421 │    8,832  │ 2.00x  │  0.6%  │ CAUTION  │
└──────────────┴─────────┴───────────┴────────┴────────┴──────────┘
  D:S = Demand-to-Supply ratio (sold 90d ÷ active supply)
  >2.5 = strong tailwind · 2.0–2.5 = stable · <2.0 = headwind

INVESTMENT IMPLICATIONS BY SEGMENT
  SUV / Crossover (49.9% of market):
    → Tailwind for: TM (RAV4, Highlander), HMC (CR-V), GM (Equinox)
    → D:S of 2.33x confirms sustained consumer preference
    → New SUV launches carry pricing power signal = BULLISH

  Pickup (24.7% of market):
    → Tailwind for: F (F-Series #1), GM (Silverado/Sierra)
    → D:S near-equal to SUV = healthy absorption rate
    → STLA Ram competing, but F and GM dominate Texas volumes

  Sedan (17.0% of market):
    → NEUTRAL — Sedan share has compressed 5pp over 3 years
    → TM Camry, HMC Accord hold position via value retention
    → NSANY, HYMTF sedan exposure creates volume risk

  Cargo Van (0.7% of market):
    → BEARISH — D:S of 1.59x signals softening commercial demand
    → Negative signal for last-mile logistics / fleet buyers

TOP OEM BENEFICIARIES OF Q1 MOMENTUM
  1. Toyota (TM) — SUV & Sedan strength, undersupplied
  2. Ford (F) — Pickup volume leader; SUV presence
  3. GM (GM) — Balanced across Pickup/SUV with BEV ramp
```
</details>

---

### `/market-snapshot` — Texas Market Intelligence

**Input:** `/market-snapshot TX`

<details>
<summary><strong>View Output</strong></summary>

```
MARKET SNAPSHOT: Texas (TX) — Mar 7, 2026
Meridian Capital · National Market Intelligence
═══════════════════════════════════════════════════

HEADLINE NUMBERS
  Active Supply:        610,694 listings
  Sold (past 90d):    1,419,756 transactions
  Turnover Ratio:          2.32x
  Median Price (active):  $37,819
  P25 / P75:           $25,156 / $54,423
  P90:                 $72,542

SUPPLY BY BODY TYPE (Active)
┌──────────────┬─────────┬────────┐
│ Segment      │  Count  │   %    │
├──────────────┼─────────┼────────┤
│ SUV          │ 303,399 │  49.7% │
│ Pickup       │ 151,146 │  24.7% │
│ Sedan        │  98,672 │  16.2% │
│ Hatchback    │  15,918 │   2.6% │
│ Coupe        │  11,744 │   1.9% │
│ Minivan      │   8,875 │   1.5% │
│ Cargo Van    │   6,158 │   1.0% │
│ Convertible  │   4,421 │   0.7% │
└──────────────┴─────────┴────────┘

TOP MAKES BY ACTIVE SUPPLY
┌────┬────────────────┬─────────┬────────┐
│  # │ Make           │  Count  │   %    │
├────┼────────────────┼─────────┼────────┤
│  1 │ Ford           │  98,175 │  16.1% │
│  2 │ Chevrolet      │  68,836 │  11.3% │
│  3 │ Toyota         │  52,937 │   8.7% │
│  4 │ Nissan         │  44,613 │   7.3% │
│  5 │ Hyundai        │  33,153 │   5.4% │
│  6 │ Jeep           │  32,206 │   5.3% │
│  7 │ Honda          │  29,700 │   4.9% │
│  8 │ RAM            │  28,651 │   4.7% │
│  9 │ GMC            │  27,937 │   4.6% │
│ 10 │ KIA            │  26,199 │   4.3% │
│ 11 │ BMW            │  19,870 │   3.3% │
│ 12 │ Mercedes-Benz  │  17,633 │   2.9% │
└────┴────────────────┴─────────┴────────┘

TOP MAKES BY SOLD VOLUME (past 90 days)
┌────┬────────────────┬───────────┬────────┐
│  # │ Make           │  Sold 90d │  Share │
├────┼────────────────┼───────────┼────────┤
│  1 │ Ford           │  210,976  │  14.9% │
│  2 │ Toyota         │  172,030  │  12.1% │
│  3 │ Chevrolet      │  165,470  │  11.7% │
│  4 │ Nissan         │   97,696  │   6.9% │
│  5 │ Honda          │   72,989  │   5.1% │
│  6 │ GMC            │   71,417  │   5.0% │
│  7 │ Hyundai        │   68,465  │   4.8% │
│  8 │ Jeep           │   62,201  │   4.4% │
│  9 │ BMW            │   41,962  │   3.0% │
│ 10 │ Mercedes-Benz  │   36,415  │   2.6% │
└────┴────────────────┴───────────┴────────┘

PRICE DISTRIBUTION (Active)
  P5:   $11,211    P25:  $25,156    P50:  $37,819
  P75:  $54,423    P90:  $72,542    P95:  $84,822

ANALYST SIGNALS (TX as national proxy)
  Toyota: BULLISH — 12.1% share, 8.7% supply = undersupplied
  Ford:   CAUTION — #1 volume but 16.1% supply overhang
  Chevrolet: NEUTRAL — balanced supply/demand profile
  Luxury (BMW/M-Benz): BEARISH — high supply, slowing turns
  EV (TSLA): BULLISH — 1,604 active, 9-day avg DOM in TX
```
</details>

---

### `pricing-power-tracker` — OEM Discount Velocity Ranking

**Input:** *"Which OEMs are discounting most aggressively? Show me the discount velocity."*

<details>
<summary><strong>View Output</strong></summary>

```
PRICING POWER TRACKER: OEM Discount Velocity — Texas (TX)
Meridian Capital · Margin Pressure Intelligence · Mar 11, 2026
═══════════════════════════════════════════════════

PERIOD: Feb 2026 vs Nov 2025 (3-month window)
MEASURE: price_over_msrp_percentage (New vehicles only)

OEM DISCOUNT RATE TABLE (ranked by velocity — fastest discounting first)
┌────┬────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│  # │ Make (Ticker)  │ Feb '26  │ Nov '25  │  Δ (bps) │ Vel/mo   │ Signal   │
├────┼────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│  1 │ Audi (VWAGY)   │  -6.02%  │  -3.76%  │  -226    │  -75/mo  │ BEARISH  │
│  2 │ Mazda          │  -6.26%  │  -4.27%  │  -199    │  -66/mo  │ BEARISH  │
│  3 │ VW (VWAGY)     │  -9.03%  │  -7.57%  │  -146    │  -49/mo  │ CAUTION  │
│  4 │ Lincoln (F)    │  -6.86%  │  -5.38%  │  -148    │  -49/mo  │ CAUTION  │
│  5 │ Ford (F)       │  -7.42%  │  -6.35%  │  -107    │  -36/mo  │ BEARISH  │
│  6 │ Chevrolet (GM) │  -7.61%  │  -6.84%  │   -77    │  -26/mo  │ CAUTION  │
│  7 │ RAM (STLA)     │ -10.57%  │ -10.03%  │   -54    │  -18/mo  │ NEUTRAL  │
│  8 │ Buick (GM)     │  -6.26%  │  -8.09%  │  +183    │  +61/mo  │ BULLISH  │
│  9 │ Hyundai (HYMTF)│  -4.72%  │  -4.79%  │    +7    │   +2/mo  │ NEUTRAL  │
│ 10 │ Kia (HYMTF)    │  -4.03%  │  -4.08%  │    +5    │   +2/mo  │ NEUTRAL  │
│ 11 │ GMC (GM)       │  -5.83%  │  -6.02%  │   +19    │   +6/mo  │ NEUTRAL  │
│ 12 │ Nissan (NSANY) │ -11.09%  │ -12.09%  │  +100    │  +33/mo  │ BULLISH  │
│ 13 │ Jeep (STLA)    │ -10.02%  │ -10.97%  │   +95    │  +32/mo  │ BULLISH  │
│ 14 │ Dodge (STLA)   │  -6.06%  │  -7.11%  │  +105    │  +35/mo  │ BULLISH  │
└────┴────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
  Velocity = (Feb% - Nov%) / 3 months × 100 bps
  Negative velocity = discounts widening = margin pressure

TICKER-LEVEL AGGREGATION
┌──────────┬────────────────────────────────────────────────────────┐
│ Ticker   │ Pricing Power Signal                                   │
├──────────┼────────────────────────────────────────────────────────┤
│ VWAGY    │ BEARISH — VW -49 bps/mo, Audi -75 bps/mo. Both       │
│          │ brands accelerating discounts. Margin headwind for     │
│          │ next earnings. Audi at -6% below MSRP now.            │
│ F        │ BEARISH — Ford -36 bps/mo + Lincoln -49 bps/mo.       │
│          │ Both brands widening. Ford now -7.4% below MSRP.      │
│          │ Combined with 113d DOM = pricing pressure signal.      │
│ GM       │ MIXED — Chevrolet -26 bps/mo (CAUTION) but Buick      │
│          │ +61 bps/mo (BULLISH) and GMC stable. Net: NEUTRAL     │
│          │ with Buick turnaround as bright spot.                  │
│ STLA     │ BULLISH — Jeep +32, Dodge +35, RAM stable. All        │
│          │ brands narrowing discounts vs 3 months ago. Early      │
│          │ sign of inventory discipline paying off.               │
│ HYMTF    │ NEUTRAL — Hyundai and Kia both flat (±5 bps/mo).      │
│          │ Pricing discipline intact at -4% to -5% below MSRP.   │
│ NSANY    │ BULLISH — Nissan narrowing +33 bps/mo. Still deepest  │
│          │ discounter (-11.1%) but trajectory improving.          │
└──────────┴────────────────────────────────────────────────────────┘

KEY INSIGHT: VWAGY is the biggest pricing power loser this
quarter. Audi discount velocity of -75 bps/month is the fastest
in the dataset — watch for margin compression in next earnings.
STLA is the surprise improver — all three volume brands narrowing.
```
</details>

---

### `dom-monitor` — Days on Market Ranking with Rate of Change

**Input:** *"Which OEMs have rising days on market? Show me DOM signals."*

<details>
<summary><strong>View Output</strong></summary>

```
DOM MONITOR: New Vehicle DOM Ranking — Texas (TX)
Meridian Capital · Demand Signal Intelligence · Mar 11, 2026
═══════════════════════════════════════════════════

PERIOD: Feb 2026 vs Nov 2025 (3-month rate of change)
DATA: New vehicle sold DOM averages (TX)

DOM RANKING BY OEM (highest DOM = slowest sellers)
┌────┬────────────────┬─────────┬─────────┬────────┬────────┬──────────┐
│  # │ Make (Ticker)  │ Feb DOM │ Nov DOM │  Δ DOM │   RoC  │ Signal   │
├────┼────────────────┼─────────┼─────────┼────────┼────────┼──────────┤
│  1 │ Jeep (STLA)    │  130d   │  112d   │  +18d  │ +16.4% │ BEARISH  │
│  2 │ Lincoln (F)    │  121d   │  136d   │  -15d  │ -11.4% │ BULLISH  │
│  3 │ Ford (F)       │  114d   │  101d   │  +13d  │ +12.7% │ BEARISH  │
│  4 │ VW (VWAGY)     │  112d   │  112d   │    0d  │   0.0% │ NEUTRAL  │
│  5 │ RAM (STLA)     │  111d   │  107d   │   +4d  │  +3.5% │ NEUTRAL  │
│  6 │ Mazda          │  102d   │  108d   │   -6d  │  -5.6% │ BULLISH  │
│  7 │ Nissan (NSANY) │   99d   │   88d   │  +11d  │ +13.5% │ BEARISH  │
│  8 │ Dodge (STLA)   │  100d   │   94d   │   +6d  │  +5.8% │ NEUTRAL  │
│  9 │ GMC (GM)       │   92d   │   68d   │  +24d  │ +34.5% │ BEARISH  │
│ 10 │ Hyundai (HYMTF)│   91d   │   86d   │   +5d  │  +4.7% │ NEUTRAL  │
│ 11 │ Buick (GM)     │   86d   │   96d   │  -10d  │ -10.4% │ BULLISH  │
│ 12 │ BMW (BMWYY)    │   82d   │    —    │    —   │    —   │ NEUTRAL  │
│ 13 │ Kia (HYMTF)    │   78d   │   72d   │   +7d  │  +9.0% │ NEUTRAL  │
│ 14 │ Chevrolet (GM) │   78d   │   69d   │   +9d  │ +12.5% │ CAUTION  │
│ 15 │ Honda (HMC)    │   64d   │    —    │    —   │    —   │ BULLISH  │
│ 16 │ Lexus (TM)     │   46d   │    —    │    —   │    —   │ BULLISH  │
│ 17 │ Toyota (TM)    │   28d   │    —    │    —   │    —   │ BULLISH  │
└────┴────────────────┴─────────┴─────────┴────────┴────────┴──────────┘
  RoC = Rate of Change (Feb vs Nov). Rising >10% = BEARISH.
  DOM >90d = entering distress territory.

DISTRESS FLAGS (DOM >90 days + rising)
┌────────────────┬────────┬────────────────────────────────────────┐
│ Make (Ticker)  │ DOM    │ Distress Signal                        │
├────────────────┼────────┼────────────────────────────────────────┤
│ Jeep (STLA)    │ 130d ↑ │ DISTRESS — Highest DOM + rising. Jeep  │
│                │        │ inventory not clearing. Watch for       │
│                │        │ deeper incentives next quarter.         │
│ Ford (F)       │ 114d ↑ │ DISTRESS — DOM rising 13% in 3 months. │
│                │        │ 64K new Ford units sitting on TX lots.  │
│                │        │ Production cut risk if trend continues. │
│ VW (VWAGY)     │ 112d → │ ELEVATED — Stable but stuck above 90d. │
│                │        │ Chronic slow-seller, not improving.     │
│ RAM (STLA)     │ 111d → │ ELEVATED — Slight rise but stable.     │
│                │        │ Full-size truck segment softening?      │
│ Nissan (NSANY) │  99d ↑ │ WARNING — Crossed 90d threshold. DOM   │
│                │        │ up 13.5% in 3 months. Volume fading.   │
└────────────────┴────────┴────────────────────────────────────────┘

INFLECTION POINT: GMC (GM)
  GMC DOM rose from 68d to 92d (+34.5%) — the sharpest
  acceleration in the dataset. Not yet in distress territory
  but approaching 90d threshold rapidly. If sustained, signals
  demand softening for GM's premium truck/SUV lineup.

BRIGHT SPOTS
  Toyota (TM): 28d avg DOM — sells in under a month.
    Best-in-class demand signal. BULLISH.
  Honda (HMC): 64d — well below 90d threshold. BULLISH.
  Buick (GM): 86d, DOWN 10% — improving. BULLISH.
  Lincoln (F): 121d, DOWN 11% — improving but still elevated.
```
</details>

---

### `sourcing-quality-signal` — Carvana vs CarMax Sourcing Comparison

**Input:** *"Compare sourcing quality for Carvana vs CarMax — what does their inventory tell us?"*

<details>
<summary><strong>View Output</strong></summary>

```
SOURCING QUALITY SIGNAL: CVNA vs KMX — Texas (TX)
Meridian Capital · Used Retailer Intelligence · Mar 11, 2026
═══════════════════════════════════════════════════

INVENTORY OVERVIEW
┌───────────────────┬───────────┬───────────┐
│ Metric            │ CVNA      │ KMX       │
├───────────────────┼───────────┼───────────┤
│ Active Units (TX) │    5,865  │    8,627  │
│ Avg Price         │  $26,254  │  $28,437  │
│ Median Price      │  $23,233  │  $25,982  │
│ Avg DOM           │   120.6d  │   109.8d  │
│ Median DOM        │    89.3d  │    79.0d  │
└───────────────────┴───────────┴───────────┘

MILEAGE PROFILE (Sourcing Quality Core Metric)
┌───────────────────┬───────────┬───────────┬──────────────┐
│ Metric            │ CVNA      │ KMX       │ Edge         │
├───────────────────┼───────────┼───────────┼──────────────┤
│ Avg Miles         │  52,386   │  44,099   │ KMX by 8,287 │
│ Median Miles      │  50,345   │  39,818   │ KMX by 10,527│
│ P25 Miles         │  26,915   │  22,249   │ KMX by 4,666 │
│ P75 Miles         │  75,415   │  59,413   │ KMX by 16,002│
│ P95 Miles         │ 101,079   │ 100,694   │ ~Equal       │
└───────────────────┴───────────┴───────────┴──────────────┘

RECON RISK SCORE
  CVNA: (52,386 / 50,000) × 100 = 100 (CAPPED)  → HIGH RISK
  KMX:  (44,099 / 50,000) × 100 = 88.2           → ELEVATED

AGE DISTRIBUTION (Model Year Mix)
┌──────────┬──────────────┬──────────────┐
│ MY Range │ CVNA (% inv) │ KMX (% inv)  │
├──────────┼──────────────┼──────────────┤
│ 2024-25  │  31.8%       │  26.5%       │
│ 2021-23  │  25.1%       │  39.9%       │
│ 2018-20  │  25.7%       │  19.5%       │
│ ≤2017    │   9.7%       │   8.0%       │
└──────────┴──────────────┴──────────────┘
  CVNA "barbell" pattern: high share of newest + oldest
  KMX concentrated in 2021-23 sweet spot (lower recon, higher margin)

INVESTMENT SIGNAL
┌──────────┬──────────────────────────────────────────────────────┐
│ Ticker   │ Sourcing Quality Signal                              │
├──────────┼──────────────────────────────────────────────────────┤
│ KMX      │ NEUTRAL — Avg mileage at 44K is within acceptable   │
│          │ range but approaching CAUTION (>55K). Strong 2021-23 │
│          │ vintage concentration = lower recon costs. Median    │
│          │ DOM of 79d suggests healthy turn rate.               │
│ CVNA     │ CAUTION — Avg mileage at 52K exceeds 50K threshold. │
│          │ Recon Risk Score at 100 (capped) = highest tier.     │
│          │ Higher mileage sourcing means higher recon costs per │
│          │ unit = gross margin pressure. DOM of 121d is 10d     │
│          │ slower than KMX, suggesting pricing/quality friction.│
│          │ The 8,287-mile gap vs KMX is the key signal.         │
└──────────┴──────────────────────────────────────────────────────┘

KEY INSIGHT: Carvana's average sourcing mileage is 19% higher
than CarMax (52K vs 44K). This translates directly to higher
reconditioning costs and lower gross margins per unit. Combined
with 10-day slower DOM, CVNA faces a sourcing quality headwind
that KMX does not — monitor for recon cost callouts in earnings.
```
</details>

---

### `earnings-preview` — Ford ($F) Pre-Earnings Channel Check

**Input:** `/earnings-preview F`

<details>
<summary><strong>View Output</strong></summary>

```
PRE-EARNINGS CHANNEL CHECK: Ford Motor Company — $F
Meridian Capital · Q1 FY2026 (Dec '25 – Feb '26) · Mar 11, 2026
═══════════════════════════════════════════════════

TICKER MAPPING: F → Ford, Lincoln
QUARTER: Q1 FY2026 (Dec 2025 – Feb 2026) vs Q4 FY2025 (Sep – Nov 2025)
STATE: Texas (largest US auto market proxy)

DIMENSION 1: VOLUME MOMENTUM (REVENUE SIGNAL)
  Q1 FY26 new sold (TX):     51,345 units
  Q4 FY25 new sold (TX):     54,854 units
  QoQ Change:                 -6.4%
  → SIGNAL: BEARISH — Volume declining mid-single digits.
    Ford losing 3,509 units QoQ in TX alone.

DIMENSION 2: PRICING POWER (MARGIN SIGNAL)
  Feb 2026 discount rate:     -7.42% below MSRP
  Nov 2025 discount rate:     -6.35% below MSRP
  3-Month Change:             -107 bps (widening)
  Velocity:                   -36 bps/month
  → SIGNAL: BEARISH — Discounts accelerating. Ford now selling
    at 7.4% below MSRP, up from 6.4% three months ago.

DIMENSION 3: INVENTORY HEALTH (BALANCE SHEET SIGNAL)
  Active new inventory (TX):  64,293 units
  Feb sold rate:              15,439 units/month
  Days Supply:                124.9 days
  Active avg DOM:             132.8 days (median: 92d)
  → SIGNAL: BEARISH — Days supply at 125 is well above the
    75-day healthy threshold. Over 4 months of inventory
    sitting on TX dealer lots.

DIMENSION 4: DOM VELOCITY (DEMAND SIGNAL)
  Feb 2026 sold avg DOM:      113.8 days
  Nov 2025 sold avg DOM:      101.0 days
  QoQ Change:                 +12.7%
  → SIGNAL: BEARISH — Vehicles taking 13 days longer to sell.
    Demand weakening quarter-over-quarter.

DIMENSION 5: EV SELL-THROUGH
  Q1 FY26 Ford EV sold (TX):    625 units
  Q1 FY26 total new sold:    51,345 units
  EV % of total:                1.2%
  Feb EV avg DOM:             138.5 days
  → SIGNAL: BEARISH — EV share negligible at 1.2%.
    F-150 Lightning DOM of 177d (Jan) signals consumer
    hesitancy. EV transition lagging Tesla and GM.

DIMENSION 6: NEW/USED MIX (CONSUMER HEALTH SIGNAL)
  Q1 FY26 new sold:          51,345 units
  Q1 FY26 used sold:         60,374 units
  New % of total:             46.0%
  Q4 FY25 new %:              46.7%
  QoQ Shift:                  -70 bps
  → SIGNAL: CAUTION — New-car share declining. Consumers
    shifting toward used Ford vehicles. Early trade-down
    signal for the brand.

FORD NAMEPLATE DISCOUNT LEADERS/LAGGARDS
┌────┬───────────────────┬──────────┬──────────┬──────────┐
│  # │ Model             │ Discount │ Sold     │ DOM      │
├────┼───────────────────┼──────────┼──────────┼──────────┤
│  1 │ Escape PHEV       │  -21.1%  │      28  │   144d   │
│  2 │ Escape            │  -14.8%  │     339  │   138d   │
│  3 │ Bronco Sport      │  -14.0%  │   1,126  │   143d   │
│  4 │ Explorer          │  -11.9%  │   1,399  │   129d   │
│  5 │ F-150 Lightning   │  -10.5%  │      22  │   177d   │
│  6 │ Bronco 2-Door     │  -11.0%  │      52  │   121d   │
└────┴───────────────────┴──────────┴──────────┴──────────┘
  Every major Ford nameplate discounted >10% below MSRP.
  Bronco Sport (1,126 units) is the biggest volume drag.

SYNTHESIS
┌─────────────────────────┬──────────────────┬──────────┐
│ Dimension               │ Data Point       │ Signal   │
├─────────────────────────┼──────────────────┼──────────┤
│ Volume Momentum         │ QoQ: -6.4%       │ BEARISH  │
│ Pricing Power           │ -7.42%, -107 bps │ BEARISH  │
│ Inventory Health        │ 125 days supply  │ BEARISH  │
│ DOM Velocity            │ 114d, +12.7%     │ BEARISH  │
│ EV Sell-Through         │ 1.2%, 139d DOM   │ BEARISH  │
│ New/Used Mix            │ 46.0%, -70 bps   │ CAUTION  │
└─────────────────────────┴──────────────────┴──────────┘

══════════════════════════════════════════════════
  COMPOSITE SIGNAL: BEARISH
  SIGNAL STRENGTH: Strong (5 of 6 dimensions negative)
══════════════════════════════════════════════════

BULL CASE:
  → Ford remains #1 in TX new-vehicle sales by volume (51K)
  → Lincoln DOM improving (-11%), suggesting luxury stabilizing
  → Truck franchise (F-Series) remains segment leader
  → Used Ford volume (60K) shows strong secondary demand

BEAR CASE:
  → Volume, pricing, inventory, DOM, AND EV all negative
  → 125 days supply is dangerously high — production cuts likely
  → Every major nameplate >10% below MSRP — margin erosion
  → EV transition at 1.2% is far behind GM (3.1%) and Tesla
  → DOM rising 13% QoQ signals softening consumer demand
  → Discount velocity of -36 bps/month = accelerating margin
    pressure with no sign of stabilization

EARNINGS CALL WATCH ITEMS:
  1. Inventory management commentary — are production cuts planned?
  2. Incentive spending guidance for Q2
  3. F-150 Lightning demand pipeline and pricing strategy
  4. Bronco Sport/Escape discount trajectory
  5. Used vehicle market share (strong used demand may offset)
```
</details>

---

### `new-used-mix-analyzer` — Consumer Trade-Down Signal

**Input:** *"Are consumers trading down from new to used? Show me the new/used split by brand."*

<details>
<summary><strong>View Output</strong></summary>

```
NEW/USED MIX ANALYZER: Consumer Trade-Down Signal — Texas (TX)
Meridian Capital · Channel Dynamics Intelligence · Mar 11, 2026
═══════════════════════════════════════════════════

PERIOD: February 2026 sold data (TX)

NEW vs USED SPLIT BY MAKE (ranked by new-car share)
┌────┬────────────────┬──────────┬──────────┬────────┬──────────┐
│  # │ Make (Ticker)  │ New Sold │ Used Sold│ New %  │ Signal   │
├────┼────────────────┼──────────┼──────────┼────────┼──────────┤
│  1 │ Toyota (TM)    │  22,155  │  16,556  │ 57.2%  │ BULLISH  │
│  2 │ Lexus (TM)     │   2,850  │   3,611  │ 44.1%  │ NEUTRAL  │
│  3 │ Honda (HMC)    │   6,316  │   8,526  │ 42.6%  │ NEUTRAL  │
│  4 │ GMC (GM)       │   6,544  │   6,923  │ 48.6%  │ NEUTRAL  │
│  5 │ Kia (HYMTF)    │   4,773  │   6,088  │ 43.9%  │ NEUTRAL  │
│  6 │ Ford (F)       │  15,439  │  20,407  │ 43.1%  │ NEUTRAL  │
│  7 │ Hyundai (HYMTF)│   4,460  │   6,376  │ 41.2%  │ CAUTION  │
│  8 │ RAM (STLA)     │   3,339  │   5,866  │ 36.3%  │ CAUTION  │
│  9 │ Chevrolet (GM) │  10,905  │  19,432  │ 35.9%  │ CAUTION  │
│ 10 │ Nissan (NSANY) │   5,897  │  11,485  │ 33.9%  │ BEARISH  │
│ 11 │ BMW (BMWYY)    │   2,198  │   4,659  │ 32.1%  │ BEARISH  │
│ 12 │ Jeep (STLA)    │   2,827  │   7,338  │ 27.8%  │ BEARISH  │
└────┴────────────────┴──────────┴──────────┴────────┴──────────┘
  New % = new_sold / (new_sold + used_sold) × 100
  >50% = new-dominant (strong OEM demand)
  <35% = used-dominant (consumer trade-down signal)

TICKER-LEVEL AGGREGATION
┌──────────┬──────────┬──────────┬────────┬──────────────────────────┐
│ Ticker   │ New Sold │ Used Sold│ New %  │ Signal                   │
├──────────┼──────────┼──────────┼────────┼──────────────────────────┤
│ TM       │  25,005  │  20,167  │ 55.4%  │ BULLISH — Only OEM with  │
│          │          │          │        │ new > used. Pricing power.│
│ GM       │  20,439* │  27,615* │ 42.5%  │ NEUTRAL — Balanced but   │
│          │          │          │        │ Chevrolet pulling used.   │
│ F        │  16,258* │  20,907* │ 43.7%  │ NEUTRAL — Used outpacing  │
│          │          │          │        │ new. Monitor for shift.   │
│ HYMTF    │   9,233  │  12,464  │ 42.6%  │ NEUTRAL — Balanced.      │
│ STLA     │   6,458* │  17,176* │ 27.3%  │ BEARISH — Heavily used-  │
│          │          │          │        │ dominant. Jeep + RAM both │
│          │          │          │        │ below 37%. Consumer       │
│          │          │          │        │ trade-down in full effect.│
│ NSANY    │   5,897  │  11,485  │ 33.9%  │ BEARISH — 2:1 used vs    │
│          │          │          │        │ new ratio. Deep discounts │
│          │          │          │        │ (-11%) not driving new    │
│          │          │          │        │ sales. Demand has shifted.│
└──────────┴──────────┴──────────┴────────┴──────────────────────────┘
  * includes subsidiary brands (Lincoln, Buick, Cadillac, etc.)

DUAL PERSPECTIVE: TRADE-DOWN = MIXED SIGNAL
┌──────────────────────────────────────────────────────────────────┐
│ OEM lens: Consumer trade-down is BEARISH for OEMs with low      │
│ new-car share. STLA and NSANY most exposed — consumers are      │
│ choosing used over new at 2:1 and 3:1 ratios respectively.      │
│                                                                  │
│ Used-retailer lens: Consumer trade-down is BULLISH for KMX      │
│ and CVNA. Higher used demand means more traffic, more           │
│ transactions, and stronger pricing power in the used market.    │
│ This is their tailwind quarter.                                  │
└──────────────────────────────────────────────────────────────────┘

KEY INSIGHT: Toyota is the ONLY major OEM where consumers
still prefer new over used (55.4% new share). Every other OEM
has flipped to used-dominant — signals broad consumer trade-down
driven by pricing pressure (avg new car discount -7% to -11%
below MSRP, yet consumers still choosing used). This is a
fundamental demand shift, not a pricing problem.
```
</details>

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
