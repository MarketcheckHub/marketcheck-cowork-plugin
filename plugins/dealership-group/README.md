# Dealership Group Plugin — MarketCheck

Automotive market intelligence for **multi-location dealer groups**. Everything in the dealer plugin PLUS group dashboard, cross-location inventory balancing, rooftop benchmarking, dealer group health monitoring, and group rollup briefings.

---

## Who It's For

- Dealership group operators (2+ locations)
- Group inventory directors
- Regional managers overseeing multiple rooftops
- Publicly traded dealer group executives (AutoNation, Lithia, Penske, etc.)

---

## Skills (13)

All 10 skills from the dealer plugin, plus 3 group-specific skills:

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **group-dashboard** | "group overview", "how are my stores doing", "location health" | Multi-location health dashboard with 0-100 scoring per rooftop |
| **cross-location-balancer** | "transfer recommendations", "balance inventory", "redistribute" | Identifies units that would sell faster at a different rooftop and recommends transfers |
| **group-benchmarking** | "compare locations", "rooftop benchmarking", "which store is best" | Rooftop-vs-rooftop comparison on pricing, DOM, turn rate, and market position |
| **dealer-group-health-monitor** | "dealer group stock", "how is AutoNation doing" | Publicly traded dealer group stock health with peer comparison |
| **competitive-pricer** | "price this car", "am I priced right" | Dual franchise+independent pricing with CPO awareness |
| **vehicle-appraiser** | "appraise this vehicle", "trade-in value" | Three-source comparable-backed valuation |
| **inventory-intelligence** | "what should I stock", "aging inventory" | Demand-to-supply ratios and aging alerts |
| **stocking-guide** | "auction run list", "hot sellers" | Pre-auction VIN checks with BUY/CAUTION/PASS |
| **daily-dealer-briefing** | "daily briefing", "morning check" | Aging alerts + competitor price drops with group rollup |
| **weekly-dealer-review** | "weekly review", "lot scan" | Full lot scan + stocking hot list with group rollup |
| **monthly-dealer-strategy** | "monthly review", "monthly strategy" | Market share + depreciation + trends with group rollup |
| **depreciation-tracker** | "depreciation rate", "residual value" | Depreciation curves and brand rankings |
| **market-share-analyzer** | "market share", "competitor analysis" | Brand share with basis point changes |

---

## Commands (8)

| Command | What It Does |
|---------|-------------|
| `/onboarding` | Group profile setup — group name, ticker, N locations with their dealer IDs |
| `/price-check` | Quick price position check |
| `/vin-lookup` | Full VIN decode + history |
| `/market-snapshot` | State-level demand and supply |
| `/setup-mcp` | Configure MCP connection |
| `/daily-briefing` | Morning check with group rollup |
| `/weekly-review` | Weekly analysis with group rollup |
| `/monthly-strategy` | Monthly report with group rollup |

---

## Agents (6)

| Agent | What It Does |
|-------|-------------|
| **lot-scanner** | Paginated inventory fetch per location |
| **lot-pricer** | Batch pricing per location |
| **portfolio-scanner** | Ad-hoc VIN batch processing |
| **group-scanner** | Multi-location parallel inventory scan — scans all rooftops simultaneously |
| **brand-market-analyst** | Brand share, depreciation, market trends |
| **market-demand-agent** | Stocking hot lists, demand-to-supply ratios |

### Group Agent Orchestration

```
WAVE 1 (parallel):
  ├─ dealership-group:group-scanner        (all locations)
  ├─ dealership-group:market-demand-agent  (what's selling)
  └─ dealership-group:brand-market-analyst (market position)

WAVE 2 (depends on Wave 1):
  └─ dealership-group:lot-pricer           (price units across all locations)

GROUP ROLLUP:
  └─ Aggregate Wave 1+2 results into group-level KPIs
```

---

## Quick Start

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin dealership-group
/setup-mcp YOUR_API_KEY
/onboarding
```

After onboarding, try:
- "How are my stores doing?" — group health dashboard
- "Which location should I move this Camry to?" — transfer recommendation
- "Compare my Dallas and Houston stores" — rooftop benchmarking
- `/daily-briefing` — group-wide morning check

---

## Example Workflows

### Group Health Check
```
How are my stores doing?
```
→ 0-100 health score per location with pricing, aging, and turn rate KPIs

### Inventory Rebalancing
```
Which vehicles should I transfer between locations?
```
→ Units that would sell faster at a different rooftop with estimated gain

### Rooftop Comparison
```
Compare all my locations on pricing and turn rate
```
→ Side-by-side rooftop metrics with best/worst performers highlighted

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
