# W2 Output Template — Compare Two Groups

Side-by-side comparison of two dealer groups for the most recent complete
calendar month. Static snapshot; no MoM (per the user's W2 spec).

---

## First line (always)

```
Comparing <ticker_A | canonical_A> vs. <ticker_B | canonical_B> — <current_month.label>
```

(If a group isn't in the 8-name public ticker map, use its canonical name.)

---

## Joint headline (always)

```
<VERDICT_A> · <ticker_A> | <VERDICT_B> · <ticker_B>
```

The verdict for each group comes from a per-group `aggregate_signals.py`
invocation. Both verdicts are computed on the current-month window only
(no MoM), so the W2 verdict is **derived solely from active-health bands**
(Days Supply Used / Days Supply New). This is documented as a known
limitation: W2 is a snapshot comparison, not a momentum read.

---

## Side-by-side KPI table (always)

```
| Metric                  | <ticker_A> (<canonical_A>) | <ticker_B> (<canonical_B>) | Winner |
|-------------------------|---------------------------|---------------------------|--------|
| Classification          | <classification_A>        | <classification_B>        | —      |
| Volume (sold count)     | <sold_count_total_A>      | <sold_count_total_B>      | <higher> |
| Avg Sale Price          | $<weighted_avg_sale_price_A> | $<weighted_avg_sale_price_B> | <higher> |
| Avg Days on Market      | <weighted_avg_days_on_market_A> days | <weighted_avg_days_on_market_B> days | <lower> |
| Efficiency Score        | <efficiency_score_A>      | <efficiency_score_B>      | <higher> |
| Active inventory (used) | <num_found_used_A>        | <num_found_used_B>        | —      |
| Active inventory (new)  | <num_found_new_A>         | <num_found_new_B>         | —      |
| Days Supply (used)¹     | <days_supply_used_A>      | <days_supply_used_B>      | <lower> |
| Days Supply (new)¹      | <days_supply_used_B>      | <days_supply_new_B>       | <lower> |
```

The `Winner` column shows the ticker whose value wins on that metric, or `—` for non-comparable rows. Direction:
- Higher is better: Volume, ASP, Efficiency Score, Active inventory (informational only).
- Lower is better: DOM, Days Supply (used), Days Supply (new).
- Render `—` when both groups' values are equal or one is null.

Apply same formatting rules as W1 (commas in volume, `$` and no decimals on ASP, 1 decimal on DOM, etc.).

**Footnote (always render):**
```
¹ Days Supply pairs live active inventory (today's snapshot) with the most-recent-complete-month sold velocity — a live-vs-historical mix.
```

---

## Mix breakdown — body type & make (always when Wave A.9-12 returned data)

```
**<ticker_A> top body types:** <body_type_1> (N), <body_type_2> (N), <body_type_3> (N)
**<ticker_B> top body types:** <body_type_1> (N), <body_type_2> (N), <body_type_3> (N)

**<ticker_A> top makes:**      <make_1> (N), <make_2> (N), <make_3> (N)
**<ticker_B> top makes:**      <make_1> (N), <make_2> (N), <make_3> (N)
```

Values come from `parse_sold_summary.py --aggregate-by-dimension body_type` / `--aggregate-by-dimension make` — slice `dimension_values[:3]` for each group/category. `<body_type_i>` is `dimension_values[i].value`; `N` is `dimension_values[i].total_sold_count` rendered with a thousands separator. Skip the section if both groups have empty `dimension_values` for both dimensions.

---

## Relative thesis (always — 2 sentences)

**Exactly 2 sentences:**

1. **Cohort positioning.** `<ticker_A> leads on <metric>; <ticker_B> leads on <metric>.`
2. **Implication.** `<which group has the better operational read this month, and which signal carries it>.`

---

## Data Quality Notes (OPTIONAL)

Same shape as W1's DQ section. Common W2 events:
- (h) Both groups resolved to the same canonical name (this should halt before MCP calls; if it slipped through, a halt error renders here).
- (i) One group's active-inventory stats absent.

---

## Footer (always)

```
✓ Verified: both profiles, all-channels active health, days-supply caveats.
```
