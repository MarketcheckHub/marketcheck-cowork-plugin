# Country Routing — US vs UK Tool Availability

> **Progressive disclosure:** Skills reference this file via `→ Full matrix: _references/country-routing.md`. Read on-demand when you need the complete tool matrix or UK workflow adjustments — the skill's inline summary covers the common case.

## Tool Matrix

| Tool | US | UK | UK Substitute |
|------|----|----|---------------|
| `search_active_cars` | Yes | No | `search_uk_active_cars` |
| `search_uk_active_cars` | No | Yes | — |
| `search_past_90_days` | Yes | No | `search_uk_recent_cars` (partial) |
| `search_uk_recent_cars` | No | Yes | — |
| `decode_vin_neovin` | Yes | No | Ask user for Year/Make/Model/Trim |
| `predict_price_with_comparables` | Yes | No | Use comp median from `search_uk_active_cars` |
| `get_car_history` | Yes | No | Not available for UK |
| `get_sold_summary` | Yes | No | Not available for UK |
| `get_server_info` | Yes | Yes | — |

## UK Workflow Adjustments

When `country == UK`:

1. **VIN decode** — Do NOT call `decode_vin_neovin`. Ask user for Year, Make, Model, Trim, Mileage directly.
2. **Price prediction** — Do NOT call `predict_price_with_comparables`. Instead, search 10-15 comps via `search_uk_active_cars` and use the **median listed price** as the market value estimate.
3. **Sold data** — `get_sold_summary` is unavailable. Any workflow requiring sold transaction data (market share, demand snapshots, D/S ratios, turn rates, hot lists, avoid lists, depreciation curves, MSRP parity) is **US-only**. Inform the user immediately.
4. **Listing history** — `get_car_history` is unavailable. Skip listing timeline and trajectory steps.
5. **Competitor price drops** — If `price_change` parameter is not supported in `search_uk_active_cars`, skip competitor scan and note: "Competitor price tracking not available for UK market."

## Skills Affected by UK Limitations

| Skill | UK Status |
|-------|-----------|
| competitive-pricer | Partial — comp median pricing only, no VIN decode |
| vehicle-appraiser | Partial — comp median only, no sold evidence |
| stocking-guide | Pre-Auction VIN Check works (comp-based); Hot List/Avoid List US-only |
| depreciation-tracker | Not available |
| inventory-intelligence | Aging Alert only (supply-side); all demand workflows US-only |
| market-share-analyzer | Not available |
| daily-dealer-briefing | Partial — lot-scanner works, no lot-pricer, inline comp pricing |
| weekly-dealer-review | Partial — lot scan works, no demand analytics |
| monthly-dealer-strategy | Section 5 only (supply-side overview) |

## Agent Availability by Country

| Agent | US | UK |
|-------|----|----|
| `lot-scanner` | Yes | Yes (uses `search_uk_active_cars`) |
| `lot-pricer` | Yes | No — price inline with comp median |
| `market-demand-agent` | Yes | No |
| `brand-market-analyst` | Yes | No |
| `group-scanner` | Yes | Yes |
| `portfolio-scanner` | Yes | Partial (no decode/predict) |
| `cohort-benchmarking-agent` | Yes | No |
