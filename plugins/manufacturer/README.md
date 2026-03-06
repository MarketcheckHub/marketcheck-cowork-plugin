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

Built by [MarketCheck Inc.](https://www.marketcheck.com)
