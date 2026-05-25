---
name: w2-compare-two
description: Workflow 2 — Head-to-head comparison of two dealer groups. Single-wave parallelism; current-month snapshot only (no MoM).
type: reference
---

# W2 — Compare Two Groups

Triggered by "compare AutoNation vs Lithia", "AN vs LAD head-to-head", "is CarMax outperforming Carvana right now". Pairs two dealer groups for a current-month snapshot. **No prior-month / MoM comparison** — that's W1's job for each individual group.

## Required inputs

| Input | Source | Required? |
|---|---|---|
| Group A name or ticker | User prompt | Yes |
| Group B name or ticker | User prompt | Yes |
| Profile (country) | `marketcheck-profile.md` | Read for country gate |

## Pre-flight (no MCP calls — local only)

1. Read `marketcheck-profile.md`. Halt if `country != US`.
2. Run `compute_month_windows.py --today <currentDate>`. Capture `current_month`. (Prior month not used in W2.)
3. Run `resolve_group_name.py --input "<group A>"`. Capture `canonical_A`, `ticker_A`, `classification_A`. On `no_candidates`, fall through to the active-facets recovery branch (SKILL.md "Before you start" step 3) for group A specifically.
4. Run `resolve_group_name.py --input "<group B>"`. Capture `canonical_B`, `ticker_B`, `classification_B`. On `no_candidates`, fall through to the recovery branch for group B. The two recovery flows are independent — only one may fire, or both may fire sequentially.
5. **Same-group halt:** if `canonical_A == canonical_B`, halt before any MCP call with:
   *"Both inputs resolved to the same group (`<canonical>`). Compare two distinct groups, or run W1 for a single-group health check."*
6. Determine each group's `primary_channel`:
   - Used-only → primary = Used
   - New-only → primary = New
   - Both → primary = Used; secondary = New

## Wave A — single agent message, all calls in parallel

W2's wave is larger than W1's because it covers two groups in parallel. Wall-clock still ≈ 12-15s (the slowest call sets the budget).

| # | Tool | Purpose | Fires when |
|---|---|---|---|
| W2.A.1 | `get_sold_summary` | Group A current-month sold, primary | always |
| W2.A.2 | `get_sold_summary` | Group A current-month sold, secondary | A is Both |
| W2.A.3 | `get_sold_summary` | Group B current-month sold, primary | always |
| W2.A.4 | `get_sold_summary` | Group B current-month sold, secondary | B is Both |
| W2.A.5 | `search_active_cars` | Group A active, primary's `car_type` | always |
| W2.A.6 | `search_active_cars` | Group A active, secondary's `car_type` | A is Both |
| W2.A.7 | `search_active_cars` | Group B active, primary's `car_type` | always |
| W2.A.8 | `search_active_cars` | Group B active, secondary's `car_type` | B is Both |
| W2.A.9 | `get_sold_summary` | Group A body_type mix, primary | always |
| W2.A.10 | `get_sold_summary` | Group A make mix, primary | always |
| W2.A.11 | `get_sold_summary` | Group B body_type mix, primary | always |
| W2.A.12 | `get_sold_summary` | Group B make mix, primary | always |

**Wave A counts: 8 (both Used-only or both New-only) up to 12 (both Both).**

W2 has no Wave B (no MoM, no peer leaderboard — those are W1's territory).

### Per-call shape

W2's `get_sold_summary` calls (A.1–A.4, A.9–A.12) mirror W1's shapes — same parameter discipline, same parsers, same payload-shaping knobs. Refer to `w1-single-group.md` and `references/sold-summary-safety.md` for the parameter details. The only differences:

- Each sold-summary call (A.1-A.4) uses `top_n=1` and `ranking_dimensions=dealership_group_name` (target-group filter), parsed with `parse_sold_summary.py --aggregate-group "<canonical>"`.
- Mix calls (A.9-A.12) use `top_n=10` (body_type) or `top_n=15` (make), `ranking_dimensions=body_type` or `=make`. Parse with `parse_sold_summary.py --aggregate-by-dimension body_type` (or `make`) — the parser emits a `dimension_values` array; the W2 template renders `dimension_values[:3]` per group per category.
- W2 does NOT issue a peer-leaderboard call — comparison is direct.

W2's `search_active_cars` calls (A.5–A.8) use the exact shape below — same as W1.A.6/A.7 but fired once per group × per car_type (2-4 invocations total). The `price_range="1-*"` filter is required so downstream `compute_group_stats.days_supply` is not biased by null-price rows (see `references/sold-summary-safety.md §search_active_cars`).

```python
search_active_cars(
    mc_dealership_group_name="<group A canonical>" | "<group B canonical>",
    car_type="used" | "new",                 # per A.5/A.6/A.7/A.8 — see table above
    stats="price,dom",
    rows=0,
    price_range="1-*",
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

### Parser invocation

All W2 parsers read from **stdin** per `SKILL.md §Script invocation discipline`. Full I/O contracts (CLI flags, output shapes, error envelopes) in `references/script-contracts.md`:
- Target-group sold (A.1–A.4) → `§parse_sold_summary` with `--aggregate-group`
- Active-cars stats (A.5–A.8) → `§parse_search` (stats mode)
- Mix calls (A.9–A.12) → `§parse_sold_summary` with `--aggregate-by-dimension {body_type|make}`

## After Wave A — per-group stats assembly

For each group A and B, assemble a `compute_group_stats.py` input. The shape below shows W2's workflow-specific assembly (no prior month, empty peer leaderboard); for the full per-field type schema see `references/script-contracts.md §compute_group_stats`.

```json
{
  "group_canonical": "<canonical>",
  "ticker": "<ticker | null>",
  "classification": "<...>",
  "current_month_window": <current_month from compute_month_windows>,
  "current_month": {
    "used": <A.1 (or A.3) group_baseline | null>,
    "new":  <A.2 (or A.4) group_baseline | null>
  },
  "prior_month": {"used": null, "new": null},
  "active": {
    "used": <A.5 (or A.7) {num_found, stats} | null>,
    "new":  <A.6 (or A.8) {num_found, stats} | null>
  },
  "peer_leaderboard": []
}
```

Run `compute_group_stats.py` twice (once per group). Capture the two output objects.

**MoM fields will be null** in both outputs (prior_month is null). That's expected — W2 is a snapshot.

## After compute_group_stats — limited aggregate_signals

W2 verdicts are derived **only from active-health bands** (Days Supply Used / Days Supply New). MoM bands are all null. The `aggregate_signals.py` reduction rule still works — it just operates over fewer non-null inputs. Full I/O contract in `references/script-contracts.md §aggregate_signals`; band definitions in `references/signal-aggregation.md`.

- If both `days_supply_used` and `days_supply_new` are null (e.g., `stats_present: false` on both calls), `aggregate_signals.verdict = null` — render the W2 KPI table without verdicts.
- Otherwise, the verdict is computed from whatever bands are available.

This is a documented W2 limitation: **W2 verdicts are inventory-position reads, not momentum reads.** The output template's footer should note this.

## Render

Use `assets/w2-output-template.md`. Interpolate fields per-group:

- Side-by-side KPI table covers headline + active inventory.
- Mix breakdown for body_type and make (top 3 each per group).
- Two-sentence relative thesis (cohort positioning + implication).

## Wall-clock budget (W2)

- Pre-flight: ~2s (4 local script calls — 2× resolve_group_name, plus profile/dates).
- Wave A: ~12-15s (8-12 parallel calls).
- Post-Wave-A scripts: ~2s (compute_group_stats × 2, aggregate_signals × 2).
- **Total ≈ 16-19s common path.**

## DQ event triggers in W2

- **(c)** Either group resolved via fuzzy match → log.
- **(d)** A.5 / A.6 / A.7 / A.8 returned `stats_present: false` → log per-group.
- **(e)** Days Supply rendered → footnote always rendered.
- **(h)** Same-group halt fires before any MCP call (handled in pre-flight, not a runtime DQ event but worth noting in user-facing error).

## Edge case: one group has no current-month sold data

If `compute_group_stats.headline.sold_count_total` is null for either group (e.g., a brand-new group with no rows), render that group's KPI column as `—` with a DQ event noting the absence. Do NOT halt.
