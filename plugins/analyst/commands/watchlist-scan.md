---
description: Morning briefing across all tracked tickers — flags material changes in volume, pricing, and inventory with prioritized alerts
allowed-tools: ["mcp__marketcheck__get_sold_summary", "mcp__marketcheck__search_active_cars", "Read"]
argument-hint: [optional: "alerts-only" to show only BEARISH/CAUTION tickers]
---

Watchlist scan across all tracked tickers with prioritized signals.

## Step 0: Load profile

Read the `marketcheck-profile.md` project memory file. Extract `tracked_tickers`, `tracked_makes`, `tracked_states`. If no profile or no tracked_tickers, ask for tickers to scan. Suggest `/onboarding`.

## Step 1: Parse input

"alerts-only" or "alert" -> set alert_only=true (only show BEARISH/CAUTION tickers). Empty -> show all tickers.

## Step 2: Run watchlist scan

Use the `analyst:watchlist-monitor-agent` to scan all tracked tickers. For each ticker, pull 3 key metrics: volume MoM, discount change, and days supply. Assign per-ticker signals and composite quick signal (ALERT / WATCH / STABLE / STRONG).

## Step 3: Present prioritized results

Sort by signal severity: ALERT first. Show signal table with volume MoM %, discount change bps, days supply, and composite signal. Add one-line actionable note for ALERT and WATCH tickers.

End with: "Try `/earnings-preview [ticker]` for full channel check on any flagged ticker."
