---
description: Head-to-head peer comparison of two automotive tickers across volume, pricing power, inventory health, and DOM
allowed-tools: ["mcp__marketcheck__get_sold_summary", "mcp__marketcheck__search_active_cars", "Read"]
argument-hint: [ticker1 ticker2, e.g. "F GM" or "TM HMC"]
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

Head-to-head peer comparison of two automotive tickers.

## Step 0: Load profile

Read `~/.claude/marketcheck/analyst-profile.json`. Extract `tracked_tickers`, `tracked_states`. Proceed without profile if not found.

## Step 1: Parse input

Two stock tickers separated by space -> map each to makes using: F->Ford,Lincoln | GM->Chevrolet,GMC,Buick,Cadillac | TM->Toyota,Lexus | HMC->Honda,Acura | STLA->Chrysler,Dodge,Jeep,Ram,Fiat,Alfa Romeo,Maserati | TSLA->Tesla | RIVN->Rivian | LCID->Lucid | HYMTF->Hyundai,Kia,Genesis | NSANY->Nissan,Infiniti | MBGAF->Mercedes-Benz | BMWYY->BMW,MINI,Rolls-Royce | VWAGY->Volkswagen,Audi,Porsche,Lamborghini,Bentley | AN->AutoNation | LAD->Lithia | PAG->Penske | SAH->Sonic | GPI->Group 1 | ABG->Asbury | KMX->CarMax | CVNA->Carvana

One ticker -> ask for second. No tickers -> ask for both.

## Step 2: Pull data for both tickers

For EACH ticker, pull 4 dimensions using `get_sold_summary` and `search_active_cars`:

**Volume:** `get_sold_summary` with `make` (each make in ticker), `state` from profile, current and prior month, `ranking_dimensions=make`, `ranking_measure=sold_count`, `top_n=1`. → Extract `sold_count`. Calculate MoM %.

**Pricing:** `get_sold_summary` with `make`, `inventory_type=New`, current month, `ranking_dimensions=make`, `ranking_measure=price_over_msrp_percentage`, `top_n=1`. → Extract `price_over_msrp_percentage`.

**Inventory:** `search_active_cars` with `make`, `seller_state`, `car_type=new`, `stats=dom`, `rows=0`. → Extract `num_found`, `stats.dom.mean`. Calculate Days Supply.

**DOM:** Extract `average_days_on_market` from sold data above.

## Step 3: Present comparison

Side-by-side table:

```
Metric              | [Ticker1]  | [Ticker2]  | Edge
--------------------|-----------|-----------|------
Volume MoM          | +X.X%     | +X.X%     | [winner]
Discount Rate       | X.X%      | X.X%      | [winner]
Days Supply         | X days    | X days    | [winner]
Avg DOM             | X days    | X days    | [winner]
```

**Verdict:** "[Ticker] has the stronger channel signal based on X of 4 dimensions." With rationale.

Per-ticker signal: BULLISH / NEUTRAL / BEARISH with one-line thesis.

End with: "Try `/earnings-preview [ticker]` for full pre-earnings channel check."
