---
description: Quick market demand snapshot for a state or region — framed as investment signals for financial analysts
allowed-tools: ["mcp__marketcheck__get_sold_summary", "mcp__marketcheck__search_active_cars", "Read"]
argument-hint: [state-code, e.g. "TX" or "CA"]
---

Quick market demand snapshot showing what is selling, supply/demand imbalances, and investment-relevant signals. Designed for financial analysts (equity researchers, hedge fund analysts, portfolio managers) who need a rapid sector read on a specific geography. Takes 30 seconds.

## Step 0: Load profile

Read `~/.claude/marketcheck/analyst-profile.json`.

- If exists: extract `analyst.tracked_tickers`, `analyst.tracked_makes`, `analyst.tracked_states` to highlight relevant brands in results
- If not found: proceed without profile context

## Step 1: Parse input

Check $ARGUMENTS:

- **If a 2-letter state code** (e.g., "TX", "CA"): Use it directly
- **If a state name** (e.g., "Texas"): Convert to 2-letter code
- **If empty**: Check profile for `analyst.tracked_states`. If available, use the first state. Otherwise ask: "Which state? (e.g., TX, CA, FL)"

## Step 2: Pull demand data

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: the state code
- `ranking_dimensions`: "make,model"
- `ranking_measure`: "sold_count"
- `ranking_order`: "desc"
- `top_n`: 15
- `date_from`: first day of previous month (YYYY-MM-01)
- `date_to`: last day of previous month

## Step 3: Pull segment data

Call `mcp__marketcheck__get_sold_summary` with:
- `state`: same state
- `ranking_dimensions`: "body_type"
- `ranking_measure`: "sold_count"
- `ranking_order`: "desc"
- Same date range

## Step 4: Pull supply data

Call `mcp__marketcheck__search_active_cars` with:
- `state`: same state
- `facets`: "body_type|0|20|1,make|0|30|2"
- `rows`: 0

## Step 5: Present snapshot with investment signals

```
MARKET SNAPSHOT: [State Name] -- [Month Year]
Investment Signal View

TOP SELLING MODELS:
#  | Make Model          | Sold | Avg Price  | Avg DOM | Signal
1  | Toyota RAV4         | XXX  | $XX,XXX    | XX days | [ticker highlight if tracked]
2  | Ford F-150          | XXX  | $XX,XXX    | XX days |
...

[Highlight models belonging to tracked tickers with a star]

SEGMENT DEMAND vs SUPPLY:
Body Type  | Sold  | Avg Price  | Active Supply | Demand/Supply | Signal
SUV        | X,XXX | $XX,XXX    | X,XXX         | X.Xx          | BULLISH/BEARISH/NEUTRAL
Pickup     | X,XXX | $XX,XXX    | X,XXX         | X.Xx          |
Sedan      | X,XXX | $XX,XXX    | X,XXX         | X.Xx          |
...

SUPPLY SIGNALS:
- Demand/Supply > 1.5 = BULLISH (tight supply, pricing power)
- Demand/Supply 0.8-1.5 = NEUTRAL (balanced)
- Demand/Supply < 0.8 = BEARISH (oversupply, margin pressure)

INVESTMENT-RELEVANT TAKEAWAYS:
- [Segment with highest D/S ratio] -- pricing power intact, BULLISH for OEMs heavy in this segment
- [Segment with lowest D/S ratio] -- oversupply risk, BEARISH signal for [relevant OEM tickers]
- [Any notable brand concentration or shift]
```

## Built-in Ticker -> Makes Mapping (for highlighting)

```
F     -> Ford, Lincoln
GM    -> Chevrolet, GMC, Buick, Cadillac
TM    -> Toyota, Lexus
HMC   -> Honda, Acura
STLA  -> Chrysler, Dodge, Jeep, Ram, Fiat, Alfa Romeo, Maserati
TSLA  -> Tesla
RIVN  -> Rivian
LCID  -> Lucid
HYMTF -> Hyundai, Kia, Genesis
NSANY -> Nissan, Infiniti
MBGAF -> Mercedes-Benz
BMWYY -> BMW, MINI, Rolls-Royce
VWAGY -> Volkswagen, Audi, Porsche, Lamborghini, Bentley
AN    -> AutoNation
LAD   -> Lithia Motors
PAG   -> Penske Automotive
SAH   -> Sonic Automotive
GPI   -> Group 1 Automotive
ABG   -> Asbury Automotive
KMX   -> CarMax
CVNA  -> Carvana
```

End with: "Want to dig deeper? Try: 'How is [ticker] doing?' for a full OEM investment signal, or 'Monthly auto market report' for a sector-wide view."
