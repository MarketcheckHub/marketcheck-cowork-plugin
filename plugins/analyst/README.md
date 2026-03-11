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

Built by [MarketCheck Inc.](https://www.marketcheck.com)
