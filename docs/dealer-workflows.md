# Dealer Workflow Guide — Daily, Weekly, Monthly Operations

This guide explains the three cadenced workflows designed for car dealers using the MarketCheck Cowork Plugin. Each workflow builds on the dealer profile created during onboarding.

## Prerequisites

1. **MarketCheck MCP connected** — run `/setup-mcp YOUR_API_KEY` if not done
2. **Dealer profile created** — run `/dealer-onboarding` once to save your identity, location, and preferences

Your profile is stored at the `marketcheck-profile.md` project memory file and is read automatically by every skill.

---

## Daily Briefing (~5 minutes)

**When:** Every morning before starting operations

**Trigger:** Run `/daily-briefing` or say "daily briefing", "morning check", "what needs attention today"

**What it covers:**

### 1. Aging Inventory Alert
- Finds every unit on your lot past your DOM threshold (default: 60 days)
- Prices each against current market value using ML prediction (US) or comp median (UK)
- Calculates your floor plan burn on aged units
- Flags units as **REDUCE NOW** (overpriced + aging) or **CONSIDER WHOLESALE** (at market but stale)

### 2. Competitor Price Drop Alert
- Scans for competitors within your radius who just dropped prices on models you sell
- Groups drops by dealer to identify aggressive sellers under inventory pressure
- Flags any competitor now priced below your equivalent units (**UNDERCUT** alert)

**What you get:** A table of urgent actions with dollar impact estimates.

**When to act:**
- REDUCE NOW items: adjust price today before more DOM accumulates
- UNDERCUT alerts: decide within 24 hours — match, add value, or hold based on your own DOM

---

## Weekly Review (~15 minutes)

**When:** Monday morning, or before your main auction day

**Trigger:** Run `/weekly-review` or say "weekly review", "inventory scan", "what should I stock this week"

**What it covers:**

### 1. Full Lot Competitive Scan
- Pulls your entire front-line inventory
- Prices every unit against the market
- Classifies each as Below Market / At Market / Above Market
- Sorts by overpricing severity (highest risk first)
- Summarizes: total units overpriced, total margin recovery opportunity, total units underpriced with margin upside

### 2. Stocking Hot List (US only)
- Top 10 models to seek at auction based on turn speed + demand-to-supply ratio + volume
- Cross-referenced against your current lot to show what you're missing
- Includes max auction buy price for each model (based on your target margin and recon cost)

### 3. Market Demand Snapshot (US only)
- Top-selling models in your state for the most recent month
- Body type demand breakdown
- Highlights segments where your brand is strong or absent

**What you get:** Full pricing report + auction buying guidance + market context.

**When to act:**
- Price adjustments: implement the overpriced list on Monday
- Hot list: print it or screenshot for the auction lane
- Missing models: prioritize these in your auction run list scanning

---

## Monthly Strategy (~20 minutes)

**When:** First Monday of each month

**Trigger:** Run `/monthly-strategy` or say "monthly strategy", "monthly review", "end of month analysis"

**What it covers:**

### 1. Brand Performance (US only)
- Your franchise brand's market share in your state
- Month-over-month share change in basis points
- Comparison against top 20 competing brands

### 2. Depreciation Watch
- Identifies the top 5 models currently on your lot
- Tracks their depreciation rate over the past 3 months
- Flags any depreciating faster than 1.5%/month as high risk

### 3. Market Trends (US only)
- Fastest depreciating models statewide
- MSRP parity status for your franchise brands (above/at/below sticker)

### 4. Full Inventory Intelligence (US only)
- Demand-to-supply ratios for top 30 models
- Aging inventory summary with floor plan exposure
- Turn rates by body type segment

### 5. Supply-Side Market Overview (US + UK)
- Total active supply in your market
- Breakdown by body type and make
- Average asking price and DOM

**What you get:** A 5-section strategic report with a 30-day action plan.

**When to act:**
- Fast-depreciating models on your lot: price aggressively or wholesale this month
- Under-supplied models: increase acquisition focus at auction
- Market share trends: inform your marketing and allocation requests

---

## UK Dealer Notes

UK dealers have access to competitive pricing features but not sold data analytics:

| Workflow | US | UK |
|----------|----|----|
| Daily — aging alert | Full (ML pricing) | Partial (comp median pricing) |
| Daily — competitor drops | Full | Full |
| Weekly — lot scan | Full | Partial (comp median pricing) |
| Weekly — hot list | Full | Not available |
| Weekly — demand snapshot | Full | Not available |
| Monthly — market share | Full | Not available |
| Monthly — depreciation | Full | Not available |
| Monthly — supply overview | Full | Full |

UK tools available: `search_uk_active_cars`, `search_uk_recent_cars`

---

## Ad Hoc Commands

Beyond the cadenced workflows, use these anytime:

| Need | What to Say |
|------|------------|
| Price check a trade-in | `/price-check VIN` or "appraise VIN [VIN], [miles] miles" |
| Check VINs before auction | Give a list of VINs — "check these VINs from tomorrow's auction" |
| Who's undercutting me | "who dropped their price on [Model] near me" |
| What to stock | "what should I buy at auction this week" |
| Avoid list | "which models should I stay away from" |
| Market report | "what's happening in the auto market in my state" |

---

## Updating Your Profile

To change your preferences (radius, margin target, recon cost, aging threshold):

```
/dealer-onboarding
```

Select "update" when prompted. Your new preferences take effect immediately for all subsequent workflows.
