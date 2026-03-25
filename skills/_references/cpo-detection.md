# CPO Detection & Dual Pricing

## Detection

A vehicle is CPO (Certified Pre-Owned) if ANY of these are true:
1. Listing data has `is_certified=true`
2. User states the vehicle is certified/CPO
3. `get_car_history` shows current listing as certified

## Dual Pricing for CPO Units

When a vehicle IS CPO, make **two separate pricing calls** to `predict_price_with_comparables`:

1. **CPO call:** `is_certified=true` + other params → CPO market price
2. **Non-CPO call:** omit `is_certified` (or `is_certified=false`) → standard market price

Also search comps with `is_certified=true` filter for apples-to-apples CPO comparables.

## CPO Premium Calculation

```
CPO Premium ($) = CPO Predicted Price - Non-CPO Predicted Price
CPO Premium (%) = CPO Premium ($) / Non-CPO Predicted Price × 100
```

## Output Format

```
CPO Market Price:      $XX,XXX  (based on N certified comps)
Non-CPO Market Price:  $XX,XXX  (based on N total comps)
CPO Premium:           +$X,XXX  (+X.X%)
Your Price:            $XX,XXX  (CPO unit)
Gap vs CPO Market:     -$XXX    (X.X% below CPO market)
```

For quick formats: `CPO Value: $XX,XXX | Standard Value: $XX,XXX | Premium: +$X,XXX`

## CPO Max Bid (Stocking Guide)

When calculating auction max bid for a CPO-eligible vehicle:

```
CPO Max Bid = CPO predicted_retail × (1 - target_margin%) - recon_cost - cpo_certification_cost
Standard Max Bid = Standard predicted_retail × (1 - target_margin%) - recon_cost
```

Show both scenarios so the dealer can decide whether to certify:

```
IF CERTIFIED:
  CPO Retail Value: $XX,XXX | CPO Max Bid: $XX,XXX (includes $X,XXX cert cost)
IF SOLD AS-IS:
  Standard Retail:  $XX,XXX | Standard Max Bid: $XX,XXX
```

## When to Skip CPO

- Vehicle is NOT CPO (most common) — skip all CPO-specific calls
- UK market — `predict_price_with_comparables` not available, CPO detection still applies but pricing uses comp median for both
- Dealer profile has `cpo_program=false` — skip CPO max bid scenario in stocking guide (dealer can't certify)
