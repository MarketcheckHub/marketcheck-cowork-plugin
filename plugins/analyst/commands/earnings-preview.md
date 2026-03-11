---
description: Pre-earnings channel check for an automotive ticker — synthesizes volume, pricing, inventory, DOM, EV, and mix into bull/bear scenarios
allowed-tools: ["mcp__marketcheck__get_sold_summary", "mcp__marketcheck__search_active_cars", "Read"]
argument-hint: [ticker, e.g. "F" or "GM"]
---

Pre-earnings channel check for an automotive equity ticker.

## Step 0: Load profile

Read `~/.claude/marketcheck/analyst-profile.json`. Extract `tracked_tickers`, `tracked_makes`, `tracked_states`. Proceed without profile if not found.

## Step 1: Parse input

Stock ticker -> map to makes using: F->Ford,Lincoln | GM->Chevrolet,GMC,Buick,Cadillac | TM->Toyota,Lexus | HMC->Honda,Acura | STLA->Chrysler,Dodge,Jeep,Ram,Fiat,Alfa Romeo,Maserati | TSLA->Tesla | RIVN->Rivian | LCID->Lucid | HYMTF->Hyundai,Kia,Genesis | NSANY->Nissan,Infiniti | MBGAF->Mercedes-Benz | BMWYY->BMW,MINI,Rolls-Royce | VWAGY->Volkswagen,Audi,Porsche,Lamborghini,Bentley | AN->AutoNation | LAD->Lithia | PAG->Penske | SAH->Sonic | GPI->Group 1 | ABG->Asbury | KMX->CarMax | CVNA->Carvana

No ticker -> check profile `tracked_tickers` (use first), else ask.

## Step 2: Run channel check

Use the `earnings-preview` skill to execute the full 8-step pre-earnings channel check for the resolved ticker. This pulls volume momentum, pricing power, inventory health, DOM velocity, EV sell-through (if applicable), and new/used mix — then synthesizes into bull/bear scenarios with composite signal strength.

## Step 3: Present briefing

Format as a structured pre-earnings briefing: ticker/company/quarter header, 6-dimension signal table, bull case, bear case, signal strength, composite signal, key watch items.

End with: "Try `/compare [ticker1] [ticker2]` for peer comparison, or `/watchlist-scan` for full portfolio check."
