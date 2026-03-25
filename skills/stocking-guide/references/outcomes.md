## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Max Bid Price | predicted_retail - margin% - recon_cost | Prevents overbidding at auction; every $500 over max bid comes directly from gross profit |
| Demand-to-Supply Ratio | monthly sold / active supply | Above 3.0 = strong (bid confidently), 1.5-3.0 = moderate (bid carefully), below 1.5 = oversupplied (avoid or lowball) |
| Expected Turn Days | average_days_on_market from sold data | Every 10 extra days = $350 floor plan cost + ~0.5% depreciation on a $25K unit ($125) = $475 lost |
| Projected Net Profit per Unit | retail - buy price - recon - floor plan - depreciation | The single number that matters; target $2,000+ for independent dealers to cover overhead |
| Inventory Mix Alignment Score | weighted average of category gap magnitudes | Score near 0 = well-aligned with market demand; every 5% gap in a major category = estimated 3-5 extra days average DOM across the lot |
| Floor Plan Cost Avoidance | slow-mover holding cost x units NOT purchased | The money saved by avoiding bad buys; 3 avoided slow movers/month x $2,500 avg holding cost = $7,500/month saved |

## Action-to-Outcome Funnel

1. **VIN scores BUY with demand-to-supply > 3.0 and turn < 30 days** — Bid up to the calculated max bid confidently. Expected outcome: retail sale within 25-35 days at target margin. If the auction price exceeds max bid by more than $500, walk away — the next lane will have another unit.

2. **VIN scores CAUTION with demand-to-supply 1.5-2.5** — Bid only if the auction price is 10%+ below max bid to create a cushion for the moderate turn time. If the vehicle has cosmetic issues that inflate recon above $2,000, convert this to a PASS. Expected turn: 35-50 days.

3. **VIN scores PASS but the dealer really wants it** — Show the holding cost math explicitly. A vehicle with 65-day average turn and $35/day floor plan costs $2,275 in floor plan alone before it sells. Add 2 months of depreciation (~3% on a $25K unit = $750). Total: $3,025 in invisible costs. The front-end gross needs to be $3,025+ just to break even.

4. **Hot List model appears on the auction run list** — Flag it proactively with the max bid calculation. These are the units worth driving to a farther auction to get. If the dealer's average monthly buy is 25 units, ideally 60%+ should come from the Hot List.

5. **Dealer's inventory is 15%+ over-indexed in a slow category** — Do not buy any more units in that category regardless of individual VIN scores. The lot-level oversupply in that category will drag DOM higher for all units in the category, not just the new one. Recommend holding until natural sales bring the category back into alignment.
