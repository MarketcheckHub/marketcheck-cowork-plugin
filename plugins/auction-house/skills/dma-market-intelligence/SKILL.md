---
name: dma-market-intelligence
description: >
  This skill should be used when the user asks for "market overview for [state]",
  "DMA health check", "market intelligence", "what's the market like in [area]",
  "state market snapshot", "market conditions in Texas",
  "how is the [state] wholesale market", "market report",
  or needs a comprehensive view of a target DMA including supply levels,
  demand velocity, pricing trends, top sellers, and key dealer groups.
version: 0.1.0
---

> **Date anchor:** Today's date comes from the `# currentDate` system context. Compute ALL relative dates from it. Example: if today = 2026-03-14, then "prior month" = 2026-02-01 to 2026-02-28, "current month" (most recent complete) = February 2026, "three months ago" = December 2025. Never use training-data dates.

# DMA Market Intelligence — Comprehensive Market Overview for Auction Planning

## Profile
Load `~/.claude/marketcheck/auction-house-profile.json` if exists. Extract: zip/postcode, state/region, target_dmas, vehicle_segments, country, radius. If missing, ask for target state. **US**: `get_sold_summary`, `search_active_cars`. **UK**: `search_uk_active_cars` only (limited — supply snapshot only, no demand data). Confirm: "Using profile: [company], [state], [Country]". All preference values from profile — do not re-ask.

## User Context
Auction house sales exec or regional director assessing a DMA for auction potential. Need to understand: Is this market worth running sales in? What segments have demand? Who are the big players?

| Field | Source | Default |
|-------|--------|---------|
| Target state | User input or profile | — |
| Vehicle segments | Profile | all |

## Workflow: Full DMA Report

**Multi-agent approach:** Use the `dma-scanner` agent for comprehensive DMA analysis.

Use the Agent tool to spawn the `auction-house:dma-scanner` agent with this prompt:

> DMA market intelligence for state=[state]. Date range: [first of prior month] to [last of prior month]. Sections: all.

The agent returns: demand snapshot, supply health, top models, top dealer groups.

After receiving agent results, synthesize:

1. **Market scorecard** — Headline metrics: total monthly sold volume, avg sale price, avg DOM, days supply, volume trend (MoM).

2. **Market classification**:
   - EXPANDING: Volume > +5% MoM, days supply < 50, ASP rising
   - STABLE: Volume ±5%, days supply 50-75, ASP flat
   - CONTRACTING: Volume < -5%, days supply > 75, ASP falling
   - MIXED: Conflicting signals

3. **Auction strategy implications**:
   - EXPANDING: Increase sale frequency, more lanes, aggressive consignment sourcing
   - STABLE: Maintain current pace, focus on lane optimization
   - CONTRACTING: Reduce lanes, focus on high-demand segments only, lower reserves
   - MIXED: Segment-specific strategy

4. **Top dealer groups** — Frame as both potential consigners (they wholesale trades) AND buyers (they restock from auction). Note which groups are likely auction participants.

5. **Segment opportunity map** — Which segments to source for (high D/S) vs avoid (low D/S). Connect to lane planning.

## Workflow: Multi-DMA Comparison

Use this when the user says "compare Texas vs California" or "which of my markets is strongest."

1. Run `dma-scanner` agent for each state in parallel.
2. Compare: total volume, ASP, DOM, days supply, growth rate.
3. Rank markets by auction opportunity score = (volume × 40) + (1/days_supply × 30) + (growth_rate × 30).

## Output
Market scorecard table: metric, value, trend signal. Demand by segment with D/S ratios. Top 10 models table. Top 10 dealer groups table (flagged as potential consigners or buyers). Market classification with auction strategy. 3 actionable recommendations.
