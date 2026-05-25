---
name: outcomes
description: Action-to-outcome scenarios that drive the Investment Thesis block in the output template. Five analyst personas — equity analyst pre-earnings, EV-cohort analyst, public dealer-group analyst, sector strategist, watchlist monitor — each mapped to a workflow and a deliberate phrasing template.
type: reference
---

# Investment outcomes & KPIs

Per-workflow action-to-outcome scenarios for the Investment Thesis block.
This file is the source the SKILL.md and `assets/output-template.md`
delegate to when picking the persona phrasing for each workflow.

## Quantifiable outcomes & KPIs

| KPI | What to show | Investment implication |
|-----|--------------|------------------------|
| Market Share % by Make → Ticker | Ticker's rolled-up share of total sold units for the period | Core revenue-trajectory metric; 100 bps of national share ≈ 15,000-17,000 annual units, which at OEM ASP × gross-margin translates to a measurable EPS impact. |
| Share Change (basis points) | QoQ or YoY movement in ticker share | Early warning of competitive structural shift; a 50+ bps decline sustained over 2 quarters signals revenue downside vs sell-side consensus. |
| EV/Hybrid penetration rate by ticker | Brand-level EV share + market-level EV % of total | Tracks the EV transition; critical for legacy-OEM rerate vs pure-EV-name de-rate narratives (TSLA share loss vs absolute volume is the canonical case). |
| Segment share by body_type and ticker | Position within SUV / Pickup / Sedan | Segment-level share is more actionable than total share — reveals where a ticker is winning or losing the specific gross-profit-pool that matters. |
| Dealer Group volume + DOM | Top-8 listed groups by units sold + days-on-market by group | Identifies which retail partners drive volume vs which run capital-efficient operations. DOM differential of >10 days between top-volume and top-efficiency groups is a meaningful operational moat for the latter. |
| State concentration (top-3 states %) | % of a ticker's national volume in its top-3 states | Concentration ≥ 50% in top-3 states is a regional-macro risk callout (TX demand shock = GM revenue headwind). |
| Combined electrified rate (EV + Hybrid) | (EV sold + Hybrid sold) / Total sold | The transition pace metric the buy-side uses to test OEM EV-bridge narratives. |

## Action-to-outcome scenarios (5)

### Scenario 1 — Equity analyst pre-earnings channel check

**Question**: "How is GM tracking into Q1 2026 earnings?"

**Workflow stack**: Run **W1 Brand Share** for each of the last 3 calendar months. Compute the quarterly aggregate and the QoQ delta. Drill into **W2 Segment Conquest** for the body_types where the GM-vs-cohort gap is largest. Layer in **W3 Dealer Group Benchmarking** scoped to `--user-make GM` to see whether the franchise-group bias is favorable or adverse for the print.

**Investment thesis template**:
> "GM trailed [peer] by [X] bps nationally over the past quarter, with the gap concentrated in [segment] where [model] under-performed. Combined with [DOM differential / used vs new mix], the channel data flags [BULLISH / BEARISH / CAUTION] into the [date] print vs sell-side consensus of [...]."

### Scenario 2 — EV-cohort analyst

**Question**: "Which OEMs are gaining EV market share, and what does that mean for TSLA's bear case?"

**Workflow stack**: Run **W4 EV Penetration** for current and prior period. Identify the top-3 OEM tickers accelerating EV volume vs TSLA. Cross-reference brand-level EV share (% of brand sales that are EV) to separate "growing EV-mix" from "growing absolute-EV-volume."

**Investment thesis template**:
> "TSLA's US EV share moved from [X]% to [Y]% ([bps_signed]) as [Brand A] and [Brand B] launched [models]. However, total EV market grew [Z]%, so TSLA absolute volume is [up / flat / down] [N]%. The bear case is [confirmed / weakening] — TSLA can [lose share while growing volume] if the cohort expands faster, and that pattern [held / broke] this period. For legacy OEMs: F at [X]% EV penetration vs GM at [Y]% — [GM / F] has stronger transition momentum heading into [event]."

### Scenario 3 — Public dealer-group analyst

**Question**: "How does AN rank against LAD and PAG operationally?"

**Workflow stack**: Run **W3 Dealer Group Benchmarking** nationally for `inventory_type=Used` and `inventory_type=New` separately. Surface the volume vs efficiency leaderboard. For the user's tracked dealer-group tickers (AN / LAD / PAG / SAH / GPI / ABG / KMX / CVNA), highlight current-period rank.

**Investment thesis template**:
> "AN ranks #[X] in volume but #[Y] in efficiency for the period. LAD moves units [N] days faster on average — a [N]-day DOM differential at AN's [M]-rooftop scale would free approximately $[Z] in annual floor-plan capital. KMX and CVNA are gaining used-only share against the franchise cohort, reinforcing the [used-stock retail / pure-online] narrative. [BULLISH / BEARISH / CAUTION] read on [ticker] vs cohort."

### Scenario 4 — Sector strategist

**Question**: "What does the competitive landscape look like in pickups for the next 2 quarters?"

**Workflow stack**: Run **W2 Segment Conquest** with `body_type=Pickup`. Pull the top-15 model rollup with per-ticker mapping. Cross-reference with **W5 Regional Exposure Heatmap** for the top-3 pickup models to surface state-level concentration risk.

**Investment thesis template**:
> "F-150 still leads the pickup segment with [X]% share but lost [bps_signed] to Silverado (GM) and Ram 1500 (STLA). The share shift is concentrated in [state] and [state] — GM's pickup volume in TX is now [Z]% of national pickup volume for the ticker, raising regional-macro sensitivity for the GM thesis. Sector view: BULLISH on GM pickup-share, NEUTRAL on STLA, BEARISH on F's pickup gross-profit pool."

### Scenario 5 — Watchlist monitor

**Question**: "Tracked-ticker scan — flag any structural shift this month."

**Workflow stack**: Run **W1 Brand Share** with `--tracked-tickers <profile_tickers>`. The Ticker Impact Summary block surfaces only the user's tracked cohort with their per-ticker verdict. CAUTION or BEARISH on a tracked ticker is the flag; NEUTRAL is the all-clear.

**Investment thesis template**:
> "Across your tracked cohort ([N] tickers): [M] BULLISH ([list]), [P] NEUTRAL ([list]), [Q] BEARISH ([list]). Flagged for follow-up: [ticker] — [verdict_reason]. The print on [ticker] aligns / diverges with the [most-recent-event] read."

## Workflow → scenario routing

The output template uses this table to pick the scenario phrasing per
workflow. When the user's `analyst.focus` field is set, the routing is
biased toward the matching scenario.

| Workflow | Default scenario | Bias when `focus` matches |
|---|---|---|
| W1 Brand Share | Scenario 5 (Watchlist Monitor) | `oem` → Scenario 1 (Pre-earnings); `general` → Scenario 5; `dealer_groups` → Scenario 3 |
| W2 Segment Conquest | Scenario 4 (Sector Strategist) | `oem` → Scenario 1; `ev_transition` → fold W4 in |
| W3 Dealer Group Benchmarking | Scenario 3 (Public Dealer-Group Analyst) | `dealer_groups` → Scenario 3 (no change); `general` → Scenario 5 |
| W4 EV Penetration | Scenario 2 (EV Analyst) | `ev_transition` → Scenario 2; `oem` → Scenario 1 + Scenario 2 layered |
| W5 Regional Exposure Heatmap | Scenario 4 (Sector Strategist) | `oem` → Scenario 1 + state concentration paragraph |

When `focus` is unset or set to `general`, default to the workflow's
default scenario.

## Phrasing rules

- **Lead with the verdict.** Every Investment Thesis paragraph opens
  with the headline verdict for the ticker(s) in scope.
- **Quantify the move.** Always cite the bps shift, the volume change %,
  and the units-equivalent of the bps move (using the 100 bps ≈ 15-17K
  annual units rule of thumb).
- **Anchor on a concrete catalyst when known.** When the user supplied a
  catalyst window (earnings date, model-launch date, regulatory
  inflection), name it; when unknown, default to "the upcoming
  quarter."
- **Avoid forecasting EPS or price targets.** This skill produces
  operational reads. The analyst converts them to EPS / PT — that is
  their job and the model should not pre-empt it.
