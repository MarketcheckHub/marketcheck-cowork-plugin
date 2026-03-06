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

Built by [MarketCheck Inc.](https://www.marketcheck.com)
