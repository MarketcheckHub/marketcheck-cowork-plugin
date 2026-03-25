# Facet & Stats Query Syntax

## Facet Format

```
facets=field|offset|limit|min_count
```

| Component | Meaning | Example |
|-----------|---------|---------|
| `field` | Field to facet on | `make`, `model`, `body_type`, `fuel_type` |
| `offset` | Starting position (0-based) | `0` |
| `limit` | Max number of buckets to return | `20` |
| `min_count` | Minimum documents per bucket to include | `1` or `2` |

### Examples

| Query | Meaning |
|-------|---------|
| `body_type\|0\|20\|1` | Top 20 body types, include buckets with 1+ listing |
| `make\|0\|50\|2` | Top 50 makes, only buckets with 2+ listings (filters singletons) |
| `model\|0\|30\|1` | Top 30 models |
| `fuel_type\|0\|10\|1` | Top 10 fuel types |

### Multiple Facets

Comma-separated: `facets=body_type|0|20|1,make|0|30|1,fuel_type|0|10|1`

## Stats Format

```
stats=field1,field2,...
```

Returns min, max, mean, median, stddev, count for each field.

Common: `stats=price,miles,dom`

## Facets + Stats + rows=0

Use `rows=0` with `facets` and `stats` to get aggregates WITHOUT individual listings:

```
search_active_cars(dealer_id=X, facets=make|0|20|1,model|0|50|1, stats=price,dom, rows=0)
```

This is the most efficient way to get inventory composition and pricing stats. Use for:
- Lot composition analysis
- Category gap analysis
- Supply counts for D/S ratio
- Market overview without individual VINs

## min_count Selection

- `min_count=1` — include all buckets (use for complete inventory breakdowns)
- `min_count=2` — filter out singleton listings (use for market-level supply counts to reduce noise)
