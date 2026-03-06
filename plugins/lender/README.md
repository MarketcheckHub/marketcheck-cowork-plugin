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

Built by [MarketCheck Inc.](https://www.marketcheck.com)
