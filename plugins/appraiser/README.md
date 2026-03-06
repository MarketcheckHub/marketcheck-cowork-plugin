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

Built by [MarketCheck Inc.](https://www.marketcheck.com)
