# Analyst Plugin — MarketCheck

Automotive market intelligence for **financial analysts, equity researchers, and portfolio managers**. OEM investment signals, publicly traded dealer group health, EV transition intelligence, sector momentum reporting, market share analysis, and depreciation tracking — all framed with stock ticker context and investment signal ratings.

---

## Who It's For

- Equity research analysts covering automotive
- Hedge fund analysts tracking OEM and dealer stocks
- Portfolio managers with auto sector exposure
- Credit analysts covering auto lending
- Sell-side analysts producing sector reports

---

## Skills (9)

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

---

## Commands (3)

| Command | What It Does |
|---------|-------------|
| `/onboarding` | Analyst profile setup — tracked tickers, focus area, benchmark period |
| `/market-snapshot` | State or national market intelligence snapshot |
| `/setup-mcp` | Configure MCP connection |

---

## Agents (3)

| Agent | What It Does |
|-------|-------------|
| **brand-market-analyst** | Multi-period sold data analysis with investment signal framing (BULLISH/BEARISH/NEUTRAL/CAUTION) |
| **portfolio-scanner** | Batch VIN analysis for portfolio sample revaluation |
| **group-scanner** | Multi-location parallel scan for dealer group health assessment |

---

## Quick Start

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin analyst
/setup-mcp YOUR_API_KEY
/onboarding
```

During onboarding, you'll set up:
- **Tracked tickers** — e.g., F, GM, TSLA, AN, LAD, PAG
- **Focus area** — OEM, dealer groups, EV transition, lending, or general
- **Benchmark period** — comparison window (default 3 months)

After onboarding, try:
- "How is Ford doing?" — full OEM investment signal
- "Compare GM vs Toyota market position" — competitive analysis
- "EV adoption update" — EV transition intelligence

---

## Investment Signal Ratings

Every metric in the analyst plugin gets an explicit signal:

| Signal | Meaning |
|--------|---------|
| **BULLISH** | Positive trend, improving fundamentals |
| **BEARISH** | Negative trend, deteriorating fundamentals |
| **NEUTRAL** | Stable, no significant change |
| **CAUTION** | Mixed signals, requires monitoring |

Signals are assigned per metric with rationale, not as blanket recommendations.

---

## Built-in Ticker → Makes Mapping

The plugin automatically maps stock tickers to automotive brands:

| Ticker | Makes |
|--------|-------|
| F | Ford, Lincoln |
| GM | Chevrolet, GMC, Buick, Cadillac |
| TM | Toyota, Lexus |
| HMC | Honda, Acura |
| STLA | Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati |
| TSLA | Tesla |
| HYMTF | Hyundai, Genesis |
| KIMTF | Kia |
| NSANY | Nissan, Infiniti |
| BMWYY | BMW, MINI |
| MBGAF | Mercedes-Benz |
| VWAGY | Volkswagen, Audi, Porsche, Lamborghini, Bentley |
| AN | AutoNation |
| LAD | Lithia Motors |
| PAG | Penske Automotive |
| SAH | Sonic Automotive |
| ABG | Asbury Automotive |
| GPI | Group 1 Automotive |
| RUSHA | Rush Enterprises |
| SFT | Shift Technologies |

---

## Example Workflows

### OEM Investment Signal
```
How is Ford doing?
```
→ 8-step analysis: market share (±bps) + pricing power + depreciation watch + EV exposure + segment momentum → BULLISH/BEARISH/NEUTRAL per metric + overall signal

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

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
