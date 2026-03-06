# MarketCheck — Automotive Market Intelligence for Claude Code

7 specialized plugins powered by [MarketCheck's](https://www.marketcheck.com) automotive data platform. Install only the one that fits your role — each plugin comes pre-loaded with the skills, agents, and commands designed for your specific workflow.

---

## Choose Your Plugin

### For Car Dealers (Franchise & Independent)

**Plugin: `dealer`** — 10 skills, 5 agents, 8 commands

Competitive pricing, inventory intelligence, stocking guides, and daily/weekly/monthly operational briefings. Franchise + independent dual pricing with CPO-aware comparisons. Works for both franchise and independent dealers — onboarding asks your type and adapts all pricing accordingly.

[Full details →](plugins/dealer/README.md)

---

### For Dealership Groups (Multi-Location)

**Plugin: `dealership-group`** — 13 skills, 6 agents, 8 commands

Everything in the dealer plugin PLUS group dashboard, cross-location inventory balancing, rooftop benchmarking, dealer group health monitoring, and group rollup briefings. Designed for operators managing multiple rooftops.

[Full details →](plugins/dealership-group/README.md)

---

### For Auto Appraisers

**Plugin: `appraiser`** — 4 skills, 3 agents, 4 commands

Comparable-backed valuations with transaction evidence, regional price variance analysis, wholesale vs retail spreads, and depreciation intelligence. Output emphasizes cited comparables and confidence scores. Default search radius is wider (75 mi) for broader comp coverage.

[Full details →](plugins/appraiser/README.md)

---

### For Auto Lenders

**Plugin: `lender`** — 5 skills, 2 agents, 3 commands

Depreciation tracking framed as residual risk, EV transition monitoring for lending exposure, market momentum for portfolio strategy, and collateral valuation. Built for auto loan officers, lease companies, and floor plan providers.

[Full details →](plugins/lender/README.md)

---

### For Auto Insurers

**Plugin: `insurer`** — 4 skills, 2 agents, 3 commands

Total-loss claims valuation with settlement pricing, vehicle appraisal for insurance context, depreciation tracking for claim reserves, and market trends for risk assessment. Includes a purpose-built **claims-valuation** skill for total-loss determination and settlement offers.

[Full details →](plugins/insurer/README.md)

---

### For Financial Analysts

**Plugin: `analyst`** — 9 skills, 3 agents, 3 commands

OEM investment signals (BULLISH / BEARISH / NEUTRAL / CAUTION), publicly traded dealer group health monitoring, EV transition intelligence, sector momentum reporting, market share analysis, and dealer group benchmarking. All output is framed with stock ticker context and investment signal ratings.

[Full details →](plugins/analyst/README.md)

---

### For Manufacturers & OEMs

**Plugin: `manufacturer`** — 7 skills, 2 agents, 3 commands

Market share tracking (own brands vs competitors), EV adoption monitoring, regional demand intelligence, inventory channel visibility, and brand value retention analysis. Output is framed as competitive positioning and brand strategy.

[Full details →](plugins/manufacturer/README.md)

---

## Quick Start

### 1. Install the plugin for your segment

```bash
claude plugin add https://github.com/MarketcheckHub/marketcheck-cowork-plugin.git --plugin dealer
```

Replace `dealer` with your segment: `dealership-group`, `appraiser`, `lender`, `insurer`, `analyst`, or `manufacturer`.

### 2. Connect the MCP server

```
/setup-mcp YOUR_API_KEY
```

This configures the MarketCheck MCP connection. No npm packages or local processes required — it connects directly to the hosted server.

You can also manually add this to `~/.claude/.mcp.json`:

```json
{
  "mcpServers": {
    "marketcheck": {
      "type": "url",
      "url": "https://mc-api.marketcheck.com/mcp?api_key=YOUR_API_KEY"
    }
  }
}
```

### 3. Run onboarding

```
/onboarding
```

Each plugin has its own onboarding that collects only what's relevant to your role. After onboarding, all skills read your profile automatically — no more re-entering ZIP codes or preferences.

### 4. Start using skills

Just ask questions in natural language. Skills activate automatically based on your intent:

| You say... | What happens |
|------------|-------------|
| "Price check VIN 1HGCV1F3XPA123456" | Competitive pricing analysis with market position |
| "What should I stock this week?" | Demand-to-supply stocking recommendations |
| "How is Ford doing vs Toyota?" | Market share comparison with trend signals |
| "Total loss valuation for VIN..." | Insurance settlement pricing with cited comps |
| "Show me the depreciation curve for Model Y" | Multi-point value retention analysis |

---

## Data Source

All plugins are powered by the MarketCheck MCP server (9 tools):

### US Tools (7)

| Tool | Purpose |
|------|---------|
| `decode_vin_neovin` | VIN decode to full specs — year, make, model, trim, MSRP, engine, drivetrain |
| `predict_price_with_comparables` | ML price prediction with comparable vehicle citations |
| `search_active_cars` | Current US dealer listings with 30+ filters |
| `search_past_90_days` | Recently sold/expired listings for transaction evidence |
| `get_car_history` | Full listing history for a VIN across all dealers |
| `get_sold_summary` | Aggregated sold data — market share, volume, prices, DOM |
| `get_server_info` | Server status and API info |

### UK Tools (2)

| Tool | Purpose |
|------|---------|
| `search_uk_active_cars` | Current UK dealer listings |
| `search_uk_recent_cars` | Recently listed/sold UK vehicles |

## US + UK Support

Full feature set for US market. UK market supported for active listings and recent cars (pricing predictions and sold analytics are US-only).

---

## Plugin Comparison

| Capability | dealer | group | appraiser | lender | insurer | analyst | manufacturer |
|------------|:------:|:-----:|:---------:|:------:|:-------:|:-------:|:------------:|
| Competitive pricing | ** | ** | ** | | | | |
| Vehicle appraisal | ** | ** | ** | ** | ** | | |
| Inventory intelligence | ** | ** | | | | | ** |
| Stocking guide | ** | ** | | | | | |
| Daily/weekly/monthly ops | ** | ** | | | | | |
| Depreciation tracking | ** | ** | ** | ** | ** | ** | ** |
| Market share analysis | ** | ** | | | | ** | ** |
| Market trends | | | ** | ** | ** | ** | ** |
| Group dashboard | | ** | | | | ** | |
| Cross-location balancing | | ** | | | | | |
| Group benchmarking | | ** | | | | ** | |
| Claims valuation | | | | | ** | | |
| EV transition monitor | | | | ** | | ** | ** |
| OEM stock tracker | | | | | | ** | ** |
| Market momentum | | | | ** | | ** | ** |
| Deal finder | ** | | | | | | |

---

## Getting Help

- **MarketCheck API docs:** [marketcheck.com](https://www.marketcheck.com)
- **Plugin issues:** [GitHub Issues](https://github.com/MarketcheckHub/marketcheck-cowork-plugin/issues)
- **API key:** [Sign up](https://www.marketcheck.com)

---

## License

MIT

---

Built by [MarketCheck Inc.](https://www.marketcheck.com)
