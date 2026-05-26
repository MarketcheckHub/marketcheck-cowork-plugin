---
name: w2-compare-oems
description: Workflow 2 — Head-to-head comparison of two OEMs. Two-wave parallelism; current-month snapshot only (no MoM, no 3-mo baseline). Verdicts driven by Days Supply + Market Share + (legacy only) EV transition bands.
type: reference
---

# W2 — Compare Two OEMs

Triggered by "compare Ford vs GM", "F vs TSLA head-to-head", "is GM outperforming Ford right now", "STLA vs VWAGY". Pairs two OEMs for a current-month snapshot. **No prior-month / MoM, no 3-mo baseline** — those are W1's domain for each individual OEM.

## Required inputs

| Input | Source | Required? |
|---|---|---|
| OEM A ticker or brand name | User prompt | Yes |
| OEM B ticker or brand name | User prompt | Yes |
| Profile (country) | `marketcheck-profile.md` | Read for country gate |

## Pre-flight (no MCP calls — local only)

1. Read `marketcheck-profile.md`. Halt if `country != US`.
2. Run `compute_month_windows.py --today <currentDate> --baseline-months 3`. Capture `current_month` only. (Prior month and baseline not used by W2.)
3. Run `resolve_oem.py --input "<OEM A>"`. Branches as in W1 (legacy/pure_play/dealer_group_redirect/no_candidates → brand-orphan recovery).
4. Run `resolve_oem.py --input "<OEM B>"`. Same branches. The two recovery flows are independent.
5. **Same-ticker halt:** if `ticker_A == ticker_B` (both resolved to same ticker), OR `canonical_make_A == canonical_make_B` (both brand-orphan to same brand), halt before any MCP call with:
   *"Both inputs resolved to the same OEM (`<ticker | canonical_make>`). Compare two distinct OEMs, or run W1 for a single-OEM signal."*
6. Determine `inventory_type` (default New, user override to Used). Confirm: *"Comparing **<ticker_A>** vs **<ticker_B>** — <current_month.label>. Pulling <inventory_type> signals…"*

## Wave A1 — sold + market share + EV (parallel)

| # | Tool | Purpose | Fires when |
|---|---|---|---|
| W2.A1.sold_A[k] | `get_sold_summary` | OEM A per-make sold, single month (current) | always, once per make in OEM A's makes |
| W2.A1.sold_B[k] | `get_sold_summary` | OEM B per-make sold, single month (current) | always, once per make in OEM B's makes |
| W2.A1.market | `get_sold_summary` | Top-25 makes leaderboard, current month | always; ONE call covers both OEMs (no make filter) |
| W2.A1.ev_A[k] | `get_sold_summary` | OEM A per-make EV slice, single month | OEM A is legacy or brand_orphan; once per make |
| W2.A1.ev_B[k] | `get_sold_summary` | OEM B per-make EV slice, single month | OEM B is legacy or brand_orphan; once per make |

**Wave A1 size (legacy-vs-legacy):** `(N_A + N_B) + 1 + (N_A + N_B) = 2(N_A + N_B) + 1` calls.
**Wave A1 size (legacy-vs-pure-play):** `(N_A + N_B) + 1 + N_A` calls (pure-play's EV slice is skipped).
**Wave A1 size (pure-play-vs-pure-play):** `(N_A + N_B) + 1` calls (no EV slices).

### Per-call shape (sold and market follow W1 but with M=1 single month)

W2's `get_sold_summary` calls mirror W1's shapes except `date_from = date_to = current_month` (single-month, M=1). Parse with `parse_sold_summary.py --aggregate-make "<Make>"` (single-month single-make rollup; emits `make_baseline`) instead of `--aggregate-make-by-window`.

The market call uses `--aggregate-by-dimension make` (no `--by-window`, single month).

EV slice per make: `parse_sold_summary.py --aggregate-make "<Make>"` (single-month version).

## Wave A2 — active inventory + segment mix (parallel)

| # | Tool | Purpose | Fires when |
|---|---|---|---|
| W2.A2.active_A[k] | `search_active_cars` | OEM A per-make active inventory | always |
| W2.A2.active_B[k] | `search_active_cars` | OEM B per-make active inventory | always |
| W2.A2.seg_A[k] | `get_sold_summary` | OEM A per-make segment mix | always |
| W2.A2.seg_B[k] | `get_sold_summary` | OEM B per-make segment mix | always |

**Wave A2 size:** `2(N_A + N_B)` calls.

Same call shapes as W1 Wave A2 (no changes).

**Total W2 calls (legacy-vs-legacy):** `4(N_A + N_B) + 1`.
- F vs GM (2+4 = 6 makes): **25 calls**.
- STLA vs VWAGY (7+5 = 12 makes): **49 calls** — heavy comparison; consider running W1 individually if performance matters.
- F vs TSLA (2+1 = 3 makes, pure-play TSLA skips EV slice): **3(3) + 1 = 10 calls**.

## After Wave A1 + A2 — per-OEM stats assembly

For each OEM (A and B), assemble a `compute_oem_stats.py` input. The shape mirrors W1 but with `prior_month` data set to null (W2 is single-snapshot):

```json
{
  "ticker": "<ticker_A | null>",
  "company_name": "<company_A>",
  "classification": "<classification_A>",
  "makes": ["<Make1>", "<Make2>", ...],
  "inventory_type": "New" | "Used",
  "windows": {
    "current_month": <from compute_month_windows>,
    "prior_month":   null,                          // LITERAL null (Gap W2-C fix)
    "baseline_3mo":  null                           // LITERAL null
  },
  "per_make": {
    "<Make>": {
      "sold_by_window": {"months": {"<current_yymm>": <single-month aggregate>}},
      "active": <from Wave A2>,
      "segment_mix": <from Wave A2>,
      "ev_slice_by_window": {"months": {"<current_yymm>": <single-month aggregate>}} | null
    }
  },
  "market_top25": {
    "current": <from W2.A1.market>,
    "prior":   []                                  // empty — no prior call in W2
  },
  "ev_market_leaders": null                         // not fetched in W2
}
```

**IMPORTANT (Gap W2-C):** `prior_month` and `baseline_3mo` MUST be literal `null` — NOT stubbed copies of `current_month`. The earlier "stub same as current_month for placeholder" wording was contradictory: when the script's `_extract_window_aggregates` saw `prior_yymm == current_yymm`, it read the SAME month for both and produced 0.0 deltas (banded NEUTRAL) instead of null deltas (skipped from reducer). Silent verdict bug — a BEARISH Days Supply (score −2) would have been diluted to mean = −2/6 = −0.33 → NEUTRAL.

With literal null:
- `_extract_window_aggregates` returns `prior_combined = None` and `baseline_combined = None`.
- All MoM-derived fields (`volume.mom_pct`, `asp.mom_pct`, `msrp_gap.delta_bps`, `dom.delta_days`, `ev_transition.delta_bps`) are null.
- `aggregate_signals.py` skips those composite slots; the reducer operates on **Days Supply only** (the W2 design intent).
- Defensive layer: script ALSO treats `prior_yymm == current_yymm` as null — even if the orchestrator violates this spec, the verdict math is correct.

**Pure-play EV in W2 (Gap W2-A/B):** when `classification == "pure_play"` and `ev_market_leaders == null`, `compute_oem_stats.py` synthesizes an `ev_block.transition` block from headline values (`ticker_ev_pct = 100.0`, ASP/DOM/sold = headline). The W2 KPI table's "EV % of total volume" row renders `100.00%` for pure-play OEMs without model-side inference. The per-make breakdown table renders the single make (e.g., Tesla) with full headline volume.

Run `compute_oem_stats.py` twice (once per OEM). MoM-bearing fields (`leading_indicators_raw.volume.mom_pct`, `asp.mom_pct`, `msrp_gap.delta_bps`, `market_share.delta_bps`, `dom.delta_days`, `ev_transition.delta_bps`) will be null because prior-month data is stubbed.

## After compute_oem_stats — limited aggregate_signals

W2 verdicts are derived **only from the bands that don't require prior-month data**:
- `days_supply` (uses current value only)
- `market_share.delta_bps` — actually requires prior, so will be **null** in W2; the slot is null in composite_slots.
- `dom.delta_days` — requires prior, also null.
- `volume_momentum` — requires prior + 3-mo, null in W2.
- `pricing_power` — requires prior (asp.mom_pct), null in W2.
- `ev_transition.delta_bps` — requires prior, null in W2.

**Effective W2 composite slots: `days_supply` only** (plus optionally `market_share` if prior is somehow available, which it isn't in W2). This is a documented W2 limitation: **W2 verdicts are inventory-position reads only**, not momentum reads.

Pipe to `aggregate_signals.py` anyway; it will produce a verdict based on the single active slot (`days_supply`) OR `verdict: null, reason: "no_scoreable_signals"` if `days_supply` is also unavailable.

Run `aggregate_signals.py` twice (once per OEM). Capture both verdicts.

## Render

Use `assets/w2-output-template.md`. Interpolate per-OEM fields side-by-side. Render the W2-limitation footnote indicating the inventory-only verdict basis.

## Wall-clock budget (W2)

- Pre-flight: ~3s (4 local script calls — 2× resolve_oem, plus profile/dates).
- Wave A1: ~12-15s (parallel; 6-25 calls depending on N_A + N_B).
- Wave A2: ~12-15s (parallel; 4-24 calls).
- Post-Wave-A2 scripts: ~3s (`compute_oem_stats` × 2 + `aggregate_signals` × 2).
- **Total ≈ 25–35s common path.**

## DQ event triggers in W2

- **(c)** Either OEM resolved via fuzzy match → log per-OEM.
- **(d)** Active-inventory stats absent on any make → log per-OEM.
- **(e)** Days Supply rendered → footnote always rendered.
- **(g)** Target OEM's makes absent from top-25 → log per-OEM.
- **(h)** Same-ticker halt (pre-flight) → handled before Wave A1, surfaced to user (not a runtime DQ event).
- **(i)** Low-volume make → log per-OEM per-make.
- **(j)** Brand-orphan path taken (one or both OEMs) → log per-OEM.
- **(k)** EV slice omitted for pure_play OR zero-EV legacy → log per-OEM.

## Edge case: one OEM has no current-month sold data

If `compute_oem_stats.headline.sold_count_total` is null for either OEM (e.g., a brand-new tracked ticker with no current-month data), render that OEM's KPI column as `—` with a DQ event noting the absence. Do NOT halt — the comparison still works for the other OEM.

## Edge case: pure-play vs legacy

For W2 comparisons of one pure-play (TSLA/RIVN/LCID) and one legacy (F/GM/...), the asymmetry is the headline:
- Legacy OEM has EV% rendered (e.g., Ford EV = 4.8%).
- Pure-play has EV% = 100% (by definition).
- The KPI table renders both; the pair-trade thesis highlights the asymmetry.

## What W2 deliberately does NOT do

- **No 3-mo baseline.** Multi-month trend lives in W1 for each individual OEM.
- **No EV market leaders substitute call.** W2 compares two specific OEMs; market-level EV context isn't relevant.
- **No per-make divergence callouts.** That's a W1-specific concern; W2 shows per-OEM aggregates side-by-side.
- **No MoM-dependent signal slots in the verdict.** W2 is an inventory-position read.
