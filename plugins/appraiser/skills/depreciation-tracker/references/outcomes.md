## Quantifiable Outcomes & KPIs (Appraiser Personas)

| KPI | What to Show | Appraisal Impact |
|-----|-------------|------------------|
| Monthly Depreciation Rate % | (Prior month avg price - Current month avg price) / Prior month avg price | Trend-adjustment factor against book-based starting points; a 1% monthly acceleration on a $30K vehicle = $300 of trend-discount per appraisal that must be applied against the book value, or the appraisal is overstated. |
| Residual Retention % | Current transaction price / Original MSRP x 100 | Insurance total-loss settlements and fleet revaluation use this directly. Every 1% retention error on a $30K vehicle = $300 of settlement variance — load-bearing for defensible claim valuations. |
| Segment Depreciation Comparison | Side-by-side retention % for EV vs ICE, SUV vs Sedan, etc. | Fleet revaluation: portfolios concentrated in a fast-depreciating segment carry outsized devaluation risk; the appraiser should flag the segment concentration even when individual vehicles still appraise within book range. |
| Brand Residual Ranking | Ranked list of makes by retention % with tier classification | Trade-in appraisers: build a per-brand trend-discount table; T1 brands = book, T4 brands = book minus 2–4%. Insurance: tier feeds replacement-cost defense narrative. |
| Price-Over-MSRP % | Transaction price / MSRP - 1, expressed as percentage | New-vehicle insurance replacement-cost: positive values mean the floor for replacement-cost is *above* MSRP; negative values mean incentives are reducing the defensible replacement-cost. |
| Geographic Value Variance | State price index (state avg / national avg x 100) | Multi-state insurance claims and fleet relocation appraisals: anchor on the relevant state's index, not the national book. For estate / probate appraisals across jurisdictions, geographic variance can swing the appraisal by $1,000–$3,000 on a $30K vehicle. |

## Action-to-Outcome Funnel (Appraiser-Tailored)

1. **Depreciation accelerating beyond 2% monthly on a specific model** —
   Trade-in appraisers: drop bid by 3–5% from book on this model;
   re-confirm before quoting. Insurance adjusters: total-loss settlement
   should anchor on the trailing-30-days transaction window rather than
   published book — cite three or more comps from `parse_sold_summary`
   in the claim narrative. Estate appraisers: note the rapidly declining
   value in the report so the executor can move quickly on disposition.
   Cite the specific monthly rate and the segment average.

2. **EV depreciation running 1.5x+ faster than ICE equivalent** — Fleet
   managers: portfolios concentrated in EVs face outsized revaluation
   exposure — flag for portfolio-rebalancing review. Insurance: EV
   total-loss settlements should use EV-specific residual curves rather
   than blended auto residuals. Show the EV vs ICE gap in dollars and
   percentage at each time interval.

3. **Brand drops from Tier 1 to Tier 2 retention** — Trade-in appraisers:
   add a 1–2% per-brand trend discount when valuing this make. Fleet
   managers: review portfolio concentration in that brand; consider an
   accelerated revaluation cycle. Estate appraisers: rapid tier movement
   may justify an earlier-than-book appraisal date if the estate
   disposition is delayed. Show the trajectory over the prior 3–6 months
   to distinguish a blip from a trend.

4. **State-level price 10%+ above or below national average** — Multi-state
   insurance claims: anchor replacement-cost on the destination state's
   index, not the national book. Fleet relocation appraisals: net
   replacement-cost shift can be $2,000–$4,000 per unit on a relocation
   from a discount state to a premium state; surface explicitly in the
   appraisal notes. Trade-in appraisers near state borders should validate
   the print against the source-state index. Quantify the dollar
   opportunity per unit.

5. **New model flips from above-MSRP to below-MSRP** — New-vehicle insurance
   replacement-cost claims must now reflect the prevailing transaction
   price, not MSRP. Trade-in appraisers valuing a trade-in for a customer
   buying that model: confirm the in-pocket transaction price (not MSRP)
   in the deal narrative. Show the timeline of the flip and the rate of
   discount deepening so the customer / insurer can validate the
   appraiser's anchor.
