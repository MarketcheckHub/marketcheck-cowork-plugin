## Quantifiable Outcomes & KPIs

| KPI | What to Show | Business Impact |
|-----|-------------|-----------------|
| Market Share % by Make | Brand's share of total sold units in period | Core competitive metric; 100 bps of national share ~ 15,000-17,000 annual units |
| Share Change (basis points) | QoQ or YoY movement in share | Early warning of competitive shifts; a 50+ bps decline sustained over 2 quarters signals structural issue |
| EV/Hybrid Penetration Rate | Electrified sales as % of total market | Tracks transition pace; critical for production planning and dealer allocation |
| Segment Share by Body Type | Brand's position within SUV, Sedan, Pickup etc. | Reveals where a brand is winning or losing; segment-level share is more actionable than total share |
| Dealer Group Volume Ranking | Top 20 groups by units sold | Identifies which retail partners drive volume; informs co-op allocation and incentive design |
| Dealer Group Avg DOM | Operational efficiency by group | Groups with low DOM are more capital-efficient; DOM gap between top and bottom group often exceeds 20 days |
| Regional Volume Distribution | State-by-state unit sales | Reveals geographic concentration risk and under-penetrated growth markets |
| Price-to-MSRP Ratio | Average sale price / MSRP by model | Models selling above MSRP signal constrained supply; below MSRP signals incentive dependency |

## Action-to-Outcome Funnel

1. **Scenario: OEM brand manager asks "How did we do vs Toyota last quarter?"**
   Run *Brand Market Share* for each of the last 3 months. Calculate quarterly aggregate. Compare Toyota vs the user's brand: total volume, share %, share change. Drill into *Segment Conquest Analysis* for the body types where the gap is largest. Recommend: "You trailed Toyota by X units nationally. The gap is concentrated in SUVs where RAV4 and Highlander outsold your [models] by Y units. Focus incentive spend on [model] to close the segment gap."

2. **Scenario: Analyst asks "Which brands are gaining EV market share?"**
   Run *EV Adoption Tracking* for current and prior period. Show brand-level EV share change. Identify the top 3 brands accelerating EV volume. Recommend: "Tesla's EV share dropped from X% to Y% as [Brand A] and [Brand B] launched [models]. Hyundai/Kia combined now represent Z% of EV sales, up from W% a year ago."

3. **Scenario: Dealer group CEO asks "How do we rank against Lithia and Hendrick?"**
   Run *Dealer Group Benchmarking* nationally and for the user's primary state. Show volume, DOM, and efficiency score side by side. Recommend: "You rank #X in volume but #Y in efficiency. Lithia moves units 8 days faster on average. Closing that DOM gap across your 45 rooftops would free approximately $Z in annual floor plan savings."

4. **Scenario: OEM regional director asks "Where should we allocate more inventory?"**
   Run *Regional Demand Heatmap* for the OEM's brand. Identify states where the brand's share of segment sales is below its national average — these are under-allocated markets. Cross-reference with *Segment Conquest Analysis* in those states. Recommend: "In Florida, your brand holds X% of SUV sales vs Y% nationally. Increasing allocation by Z units/month could capture an estimated W additional sales based on current demand-to-supply ratios."

5. **Scenario: Market researcher asks "What does the competitive landscape look like in pickups?"**
   Run *Segment Conquest Analysis* with `body_type=Pickup`. Show top 15 models, share %, and share change. Layer in *Regional Demand Heatmap* for the top 3 pickup models. Recommend: "Ford F-150 still leads with X% segment share but lost Y bps to Chevrolet Silverado and Ram 1500. The share shift is most pronounced in Texas and Michigan."
