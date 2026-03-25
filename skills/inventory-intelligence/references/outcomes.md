## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Demand-to-Supply Ratio | Ratio per make/model in the user's market | Identifies under-served segments; each correct stocking decision can add $1,500-3,000 in front-end gross |
| Average DOM by Segment | Days on market for body type and make/model | Every day over 45 DOM costs ~$30 in floor plan interest; reducing avg DOM by 10 days saves ~$300/unit |
| Aged Unit Count (60+ / 90+ DOM) | Total units and estimated carrying cost | A 200-unit dealer with 15% aged inventory burns ~$13,500/month in excess floor plan |
| Turn Rate | Monthly sold / avg inventory level | Industry benchmark: 8-12 turns/year for used; dealers below 8 should investigate mix |
| New vs Used Mix Alignment | Current lot ratio vs market absorption ratio | Misaligned mix ties up capital; a 5-point shift toward market demand can improve turns by 0.5-1.0/year |
| Price-to-Market Gap on Aged Units | Listed price vs predicted market price | Overpriced aged units represent the largest single source of preventable loss |

## Action-to-Outcome Funnel

1. **Scenario: Dealer says "I don't know what to buy at auction this week."**
   Run *Market Demand Snapshot* then *What Should I Stock?* Present the top 5 under-supplied models with price guidance from `predict_price_with_comparables`. Recommend: "Target these models at auction. Acquire at or below predicted wholesale price for maximum margin."

2. **Scenario: Used Car Manager asks "What's sitting too long on my lot?"**
   Run *Aging Inventory Alert*. For each unit over 90 DOM with a positive price gap, recommend an immediate price reduction to predicted market value. For units with negative gap already, recommend wholesale exit. Quantify: "These 8 units are costing you approximately $7,200/month in floor plan interest."

3. **Scenario: GM asks "Should I be stocking more SUVs or sedans?"**
   Run *Turn Rate by Segment* + *New vs Used Mix Analysis*. Compare DOM and volume by body type. If SUVs turn in 28 days and sedans in 52 days in the local market, recommend shifting mix toward SUVs. Quantify the DOM savings and capital velocity improvement.

4. **Scenario: OEM Regional Manager asks "How are my dealers stocking compared to demand?"**
   Run *Market Demand Snapshot* filtered by the OEM's make, then *What Should I Stock?* across the region. Identify which models are under-represented on dealer lots relative to consumer demand. Provide dealer-level or state-level recommendations for allocation adjustments.

5. **Scenario: Dealer group CFO asks "Where is our floor plan exposure highest?"**
   Run *Aging Inventory Alert* across multiple dealer_ids. Aggregate the carrying cost exposure by rooftop. Rank locations by total aged-unit floor plan burn. Recommend priority actions for the top 3 most exposed stores.
