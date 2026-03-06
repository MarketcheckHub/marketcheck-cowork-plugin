# Dealer Plugin — MarketCheck

Automotive market intelligence for **franchise and independent car dealers**. Competitive pricing, inventory intelligence, stocking guides, and daily/weekly/monthly operational briefings with franchise + independent dual pricing and CPO-aware comparisons.

---

## Who It's For

- Franchise dealers (Toyota, Ford, Honda, etc.)
- Independent used car dealers
- Used car managers and inventory managers
- General managers who want data-driven lot operations

---

## Skills (10)

Skills activate automatically when you ask questions in natural language — no slash commands needed.

| Skill | Trigger Phrases | What It Does |
|-------|----------------|-------------|
| **competitive-pricer** | "price this car", "am I priced right", "who is undercutting me" | Positions your price against the market with Below/At/Above verdict and dual franchise+independent pricing |
| **vehicle-appraiser** | "appraise this vehicle", "what's it worth", "trade-in value" | Three-source valuation (ML prediction + active comps + sold transactions) with confidence score |
| **deal-finder** | "find me the best deal", "is this a good price", "compare deals" | Sources best-priced vehicles, validates fair pricing, builds negotiation leverage |
| **inventory-intelligence** | "what should I stock", "aging inventory alert", "turn rate" | Demand-to-supply ratios, aging alerts, turn-rate benchmarks, mix analysis |
| **stocking-guide** | "auction run list check", "hot sellers", "should I bid on this" | Pre-auction VIN checks with BUY/CAUTION/PASS verdicts, hot list, avoid list |
| **daily-dealer-briefing** | "daily briefing", "morning check", "what needs attention today" | Aging alerts + competitor price drops + top 3 actions for today (~5 min) |
| **weekly-dealer-review** | "weekly review", "full lot pricing scan", "what should I stock this week" | Full lot competitive scan + stocking hot list + demand snapshot (~15 min) |
| **monthly-dealer-strategy** | "monthly review", "monthly strategy", "end of month analysis" | Market share + depreciation + trends + inventory intel + 30-day plan (~20 min) |
| **depreciation-tracker** | "depreciation rate", "residual value", "which cars hold value" | Multi-point depreciation curves, brand rankings, segment comparisons |
| **market-share-analyzer** | "market share", "who is winning in SUVs", "EV adoption rate" | Brand market share with basis point changes, segment conquest, dealer group rankings |

---

## Commands (8)

| Command | Usage | What It Does |
|---------|-------|-------------|
| `/onboarding` | `/onboarding` | One-time dealer profile setup — franchise/independent type, location, preferences |
| `/price-check` | `/price-check VIN` | Quick price-position check in under 30 seconds |
| `/vin-lookup` | `/vin-lookup VIN` | Full VIN decode + listing history + estimated value |
| `/market-snapshot` | `/market-snapshot TX` | State-level demand, supply, and opportunity snapshot |
| `/setup-mcp` | `/setup-mcp API_KEY` | Configure MarketCheck MCP connection |
| `/daily-briefing` | `/daily-briefing` | Morning operational health check |
| `/weekly-review` | `/weekly-review` | Tactical weekly lot analysis |
| `/monthly-strategy` | `/monthly-strategy` | Comprehensive monthly strategic report |

---

## Agents (5)

| Agent | When It's Used | What It Does |
|-------|---------------|-------------|
| **lot-scanner** | Daily/weekly/monthly briefings | Paginated inventory fetch — gets your complete lot regardless of size |
| **lot-pricer** | Daily/weekly briefings | Batch prices every unit against the market with action recommendations |
| **portfolio-scanner** | Ad-hoc VIN batch requests | Processes auction run lists, portfolio revaluations, fleet appraisals |
| **brand-market-analyst** | Monthly strategy | Brand market share, depreciation watch, market trends |
| **market-demand-agent** | Weekly review, stocking guide | Stocking hot lists, demand-to-supply ratios, turn rates |

### Agent Orchestration

```
WAVE 1 (parallel):
  ├─ dealer:lot-scanner          (your inventory)
  ├─ dealer:market-demand-agent  (what's selling)
  └─ dealer:brand-market-analyst (market position)

WAVE 2 (depends on Wave 1):
  └─ dealer:lot-pricer           (price every unit)
```

---

## Quick Start

```bash
# 1. Install
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin dealer

# 2. Connect MCP
/setup-mcp YOUR_API_KEY

# 3. Onboard your dealership
/onboarding
```

After onboarding, try:
- `/daily-briefing` — morning health check
- `/price-check 1HGCV1F3XPA123456` — quick price position
- "What should I buy at auction?" — stocking recommendations
- "Am I priced right on my RAV4s?" — competitive analysis

---

## Example Workflows

### Morning Routine (5 min)
```
/daily-briefing
```
→ Aging units over 60 DOM with floor plan burn + competitors who dropped prices + top 3 actions

### Before Auction
```
Check these VINs from tomorrow's Manheim auction:
1HGCV1F3XPA012345
2T3P1RFV8RW654321
5YJ3E1EA8PF789012
```
→ BUY/CAUTION/PASS verdict for each with max bid prices

### Trade-In at the Desk
```
Appraise VIN 2T3P1RFV8RW654321, 32K miles, clean condition
```
→ 60-second valuation with comps and recommended offer range

### Weekly Deep Dive
```
/weekly-review
```
→ Every unit on your lot priced against market + hot list for auction + 5 prioritized actions

---

## UK Dealer Support

UK dealers are supported with competitive pricing using `search_uk_active_cars` and `search_uk_recent_cars`. Select UK during onboarding and enter your postcode.

**Works for UK:** Competitive listing search, price comparisons, active supply scanning, daily briefing (~80% functional)

**US-only:** ML price predictions, VIN decode, market share, depreciation tracking, stocking hot lists, demand-to-supply ratios

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
