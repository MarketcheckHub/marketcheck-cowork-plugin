---
description: One-time profile setup for financial analysts — stores your tracked tickers, focus area, and benchmark preferences.
allowed-tools: ["Read", "Write", "AskUserQuestion"]
argument-hint: [your name or company]
---

Collect identity, focus area, tracked tickers, and preferences. Persist to `~/.claude/marketcheck/analyst-profile.json`.

## Step 0: Check for existing profile

Read `~/.claude/marketcheck/analyst-profile.json`. If valid JSON: show summary, ask update or keep. If keep, stop.

## Step 1: Collect identity

- "What is your name?" -> `user.name`
- "What company?" -> `user.company`

Use $ARGUMENTS as name or company if provided.

## Step 2: Country

US-only. MarketCheck analyst data covers US market only. Store `location.country = "US"`.

## Step 3: Focus area

Ask primary focus -> `analyst.focus`:
- `oem` -- OEM/brand performance
- `dealer_groups` -- publicly traded dealer stocks (AN, LAD, PAG)
- `ev_transition` -- EV adoption & pricing
- `lending` -- residual/depreciation risk
- `general` -- broad market intelligence

## Step 4: Tracked tickers

Ask: "Which stock tickers to track?" (comma-separated). Show ticker-to-makes mapping:

```
OEM: F->Ford,Lincoln | GM->Chevrolet,GMC,Buick,Cadillac | TM->Toyota,Lexus | HMC->Honda,Acura | STLA->Chrysler,Dodge,Jeep,Ram,Fiat,Alfa Romeo,Maserati | TSLA->Tesla | RIVN->Rivian | LCID->Lucid | HYMTF->Hyundai,Kia,Genesis | NSANY->Nissan,Infiniti | MBGAF->Mercedes-Benz | BMWYY->BMW,MINI,Rolls-Royce | VWAGY->VW,Audi,Porsche,Lamborghini,Bentley
DEALER GROUPS: AN->AutoNation | LAD->Lithia | PAG->Penske | SAH->Sonic | GPI->Group 1 | ABG->Asbury | KMX->CarMax | CVNA->Carvana
```

Store as `analyst.tracked_tickers`. Auto-populate `analyst.tracked_makes` from mapping.

## Step 5: Geographic focus

Ask: "Which states?" (comma-separated, or "national"). Store as `analyst.tracked_states` (empty array = national).

## Step 6: Benchmark period

Ask: "Months of lookback for trends?" (default: 3) -> `analyst.benchmark_period_months`.

## Step 7: Write profile

Create `~/.claude/marketcheck/` if needed. Write to `analyst-profile.json`:

```json
{
  "schema_version": "2.0",
  "created_at": "[ISO]", "updated_at": "[ISO]",
  "user": { "name": "", "company": "" },
  "analyst": {
    "focus": "oem|dealer_groups|ev_transition|lending|general",
    "tracked_tickers": [], "tracked_makes": [],
    "tracked_states": [], "benchmark_period_months": 3
  },
  "location": { "country": "US", "zip": null, "state": null }
}
```

## Step 8: Sync to session memory

Write a compact profile summary to your auto-memory file (`MEMORY.md`) so all future chat windows automatically know this user. Append or update the `## MarketCheck Profile` section:

```
## MarketCheck Profile: Analyst
- **User**: [name] | **Company**: [company] | **Focus**: [focus]
- **Tickers**: [tracked_tickers list] → **Makes**: [tracked_makes list]
- **States**: [tracked_states or "National"] | **Benchmark**: [N] months
- **Profile**: ~/.claude/marketcheck/analyst-profile.json
```

Do not overwrite other memory content.

## Step 9: Confirm and suggest next steps

Show profile summary: name, company, focus, tickers->makes, states, benchmark period.

Next steps:
- "How is Ford doing?" -- OEM investment signal
- "EV market update" -- EV adoption + pricing vs ICE
- "Monthly auto market report" -- sector-wide intelligence
- "AutoNation health check" -- dealer group stock signal
