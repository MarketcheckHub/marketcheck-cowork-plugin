---
description: Quick market demand snapshot for a state or region — framed as investment signals for financial analysts
allowed-tools: ["mcp__marketcheck__get_sold_summary", "mcp__marketcheck__search_active_cars", "Read"]
argument-hint: [state-code, e.g. "TX" or "CA"]
---

Quick market demand snapshot with investment-relevant signals for financial analysts.

## Step 0: Load profile

Read `~/.claude/marketcheck/analyst-profile.json`. Extract `tracked_tickers`, `tracked_makes`, `tracked_states` for highlighting. Proceed without profile if not found.

## Step 1: Parse input

2-letter state code -> use directly. State name -> convert to code. Empty -> check profile `tracked_states` (use first), else ask.

## Step 2: Pull demand data

`get_sold_summary`: `state`, `ranking_dimensions=make,model`, `ranking_measure=sold_count`, `ranking_order=desc`, `top_n=15`, `date_from`/`date_to` = previous month.

## Step 3: Pull segment data

`get_sold_summary`: same state, `ranking_dimensions=body_type`, `ranking_measure=sold_count`, `ranking_order=desc`, same date range.

## Step 4: Pull supply data

`search_active_cars`: `state`, `facets=body_type|0|20|1,make|0|30|2`, `rows=0`.

## Step 5: Present snapshot with investment signals

Show: top selling models (highlight tracked tickers with star), segment demand vs supply with signals (D/S > 1.5 = BULLISH, 0.8-1.5 = NEUTRAL, < 0.8 = BEARISH), investment-relevant takeaways per segment.

**Ticker-to-makes mapping for highlighting:**
F->Ford,Lincoln | GM->Chevrolet,GMC,Buick,Cadillac | TM->Toyota,Lexus | HMC->Honda,Acura | STLA->Chrysler,Dodge,Jeep,Ram,Fiat,Alfa Romeo,Maserati | TSLA->Tesla | RIVN->Rivian | LCID->Lucid | HYMTF->Hyundai,Kia,Genesis | NSANY->Nissan,Infiniti | MBGAF->Mercedes-Benz | BMWYY->BMW,MINI,Rolls-Royce | VWAGY->VW,Audi,Porsche,Lamborghini,Bentley | AN->AutoNation | LAD->Lithia | PAG->Penske | SAH->Sonic | GPI->Group 1 | ABG->Asbury | KMX->CarMax | CVNA->Carvana

End with: "Try 'How is [ticker] doing?' for full OEM signal, or 'Monthly auto market report' for sector-wide view."
