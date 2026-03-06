---
description: One-time profile setup for financial analysts — stores your tracked tickers, focus area, and benchmark preferences.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

One-time profile setup for financial analysts (equity researchers, hedge fund analysts, portfolio managers). Collects identity, focus area, tracked tickers, and preferences, then persists them to `~/.claude/marketcheck/analyst-profile.json`. After onboarding, all analyst plugin skills and commands read this profile automatically.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/analyst-profile.json`.

- If **exists and is valid JSON**: Show the current profile summary and ask: "A profile already exists for **[user.name]** at **[user.company]**. Do you want to update it or keep the current settings?"
  - If keep -> stop
  - If update -> proceed with current values shown as defaults
- If **does not exist** -> proceed to Step 1

## Step 1: Collect identity

Ask:
- "What is your name?" -> `user.name`
- "What company or organization are you with?" -> `user.company`

If $ARGUMENTS contains a value, use it as name or company as appropriate.

## Step 2: Collect country

Ask: "Are you based in the **US**?"

Note: MarketCheck analyst data is **US-only**. All sold summary and active inventory data covers the US market. Inform the user accordingly.

Store as `location.country = "US"`.

## Step 3: Collect focus area

Ask: "What is your primary analysis focus?"

| Focus | Description |
|-------|-------------|
| **oem** | OEM/brand performance (Ford, GM, Toyota, etc.) |
| **dealer_groups** | Publicly traded dealer stocks (AN, LAD, PAG, etc.) |
| **ev_transition** | EV adoption & pricing dynamics |
| **lending** | Residual/depreciation risk assessment |
| **general** | Broad market intelligence |

Store as `analyst.focus`.

## Step 4: Collect tracked tickers

Ask: "Which stock tickers do you want to track?" (comma-separated, e.g., F, GM, TSLA, AN, LAD)

Show the built-in ticker-to-makes mapping as reference:

```
OEM TICKERS:
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

DEALER GROUP TICKERS:
AN    -> AutoNation (dealer group)
LAD   -> Lithia Motors (dealer group)
PAG   -> Penske Automotive (dealer group)
SAH   -> Sonic Automotive (dealer group)
GPI   -> Group 1 Automotive (dealer group)
ABG   -> Asbury Automotive (dealer group)
KMX   -> CarMax (dealer/retailer)
CVNA  -> Carvana (dealer/retailer)
```

Store tickers as `analyst.tracked_tickers`. Auto-populate `analyst.tracked_makes` using the mapping above. For dealer group tickers (AN, LAD, etc.), store the group name in `tracked_makes` instead of vehicle makes.

## Step 5: Collect geographic focus

Ask: "Which states or regions do you focus on?" (e.g., TX, CA, FL -- or "national" for all)

Store as `analyst.tracked_states`. If "national", store as an empty array (meaning no state filter).

## Step 6: Collect benchmark period

Ask: "How many months of lookback for trend analysis?" (default: 3)

Store as `analyst.benchmark_period_months`.

## Step 7: Write profile

Create the directory `~/.claude/marketcheck/` if it does not exist.

Write the following JSON to `~/.claude/marketcheck/analyst-profile.json`:

```json
{
  "schema_version": "2.0",
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]",
  "user": {
    "name": "[from Step 1]",
    "company": "[from Step 1]"
  },
  "analyst": {
    "focus": "[oem|dealer_groups|ev_transition|lending|general]",
    "tracked_tickers": ["F", "GM", "TSLA"],
    "tracked_makes": ["Ford", "Lincoln", "Chevrolet", "GMC", "Buick", "Cadillac", "Tesla"],
    "tracked_states": ["TX", "CA"],
    "benchmark_period_months": 3
  },
  "location": {
    "country": "US",
    "zip": null,
    "state": null
  }
}
```

## Step 8: Confirm and suggest next steps

```
PROFILE SAVED -- Financial Analyst
[Name] | [Company]
Focus: [focus area]
Tracking: [tickers] -> [makes]
States: [states or "national"]
Benchmark: [N] months lookback

Try these next:
  "How is Ford doing?"           -- OEM investment signal for F
  "EV market update"             -- EV adoption + pricing vs ICE
  "Monthly auto market report"   -- sector-wide intelligence
  "AutoNation health check"      -- dealer group stock signal
```
