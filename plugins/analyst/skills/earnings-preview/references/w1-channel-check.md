---
name: w1-channel-check
description: Workflow 1 — Earnings-Preview Channel Check. Full spec for the W1 Wave A1 + A2 structure, parser pipeline, multi-quarter assembly, banding, and rendering. Quarterly cadence; OEM and dealer-group entity types; Days Supply pairs live active inventory with most-recent-complete-month sold velocity. Wave A1 splits each channel into two calls (year-ago + prior→mrcm) to stay under the upstream 12-month date-range cap.
type: reference
---

# W1 — Earnings-Preview Channel Check

Triggered when an equity analyst asks "pre-earnings channel check on F", "earnings preview for STLA", "what does the print on AN look like", "how is CVNA tracking into the print", "channel signal on TSLA next quarter", or any single-ticker channel read ahead of a public quarterly print.

## Required inputs

| Input | Source | Required? |
|---|---|---|
| Ticker (OEM or dealer-group) or brand name | User prompt | Yes |
| Profile (`country`, optional `coverage_tickers`) | `marketcheck-profile.md` | Optional — if absent, skill prompts |

The skill never crashes for missing inputs — it asks. Per Phase 5 §5a, unknown tickers **halt** at `resolve_ticker.py` (no brand-orphan recovery in this skill).

## Pre-flight (no MCP calls — local only)

1. Read `marketcheck-profile.md`. Extract `location.country`. **Halt if not US** — analyst plugin is US-only per `plugins/analyst/CLAUDE.md §Market Support`.
2. Run `scripts/compute_quarter_windows.py --today <currentDate>`. Capture `current_quarter`, `prior_quarter`, `year_ago_quarter`, `most_recent_complete_month` (the four window blocks).
3. Run `scripts/resolve_ticker.py --input "<user input>"`.
   - If `result.ok == true` → capture `ticker`, `entity_type` (`oem` | `dealer_group`), `classification` (`legacy` | `pure_play` for OEMs; `Used-only` | `New-only` | `Both` for dealer-groups), `company_name` OR `canonical`, `makes[]` (OEM only).
   - If `result.error_type == "missing_input"` → re-prompt the user.
   - If `result.error_type == "no_candidates"` → **HALT** with the candidate list. Per Phase 5 §5a, this skill does not attempt brand-orphan recovery for unknown tickers.
4. **Determine which channels to fetch from `classification`:**

   | Classification | Fetch New channel? | Fetch Used channel? | Fetch EV slice? |
   |---|---|---|---|
   | OEM `legacy` | Yes | Yes | Yes (BEV+PHEV via `EV` filter) |
   | OEM `pure_play` | Yes | Yes | No (volume IS EV) |
   | Dealer-group `Both` | Yes | Yes | Yes |
   | Dealer-group `Used-only` (KMX) | No | Yes | Yes |
   | Dealer-group `New-only` (none currently mapped) | Yes | No | Yes |

5. Confirm with user (one line, no question — just a status):
   - OEM form: *"Analyzing **<ticker>** (<company_name>): <makes> — <classification> OEM. Pulling channel signals across <year_ago_quarter.label>, <prior_quarter.label>, <current_quarter.label>, with Days Supply paired to <most_recent_complete_month.label>…"*
   - Dealer-group form: *"Analyzing **<ticker>** (<canonical>) — dealer group, <classification> inventory. Pulling channel signals across …"*

## Wave A1 — sold-vehicle data (sub-batches of ≤5 concurrent calls)

**Two critical upstream constraints — both verified live 2026-05-14:**

1. **Date-range cap (HTTP 422):** the upstream API rejects requests with `date_to − date_from > 12 months`. The skill's quarterly cadence requires data from `year_ago_quarter` + `prior_quarter` + `current_quarter` + `mrcm`, with a 6-month calendar gap between year_ago_quarter and prior_quarter. A single call covering all four windows would be 15-17 months → 422. **Wave A1 therefore issues TWO calls per channel** (Call A: year_ago_quarter only; Call B: prior_quarter → mrcm). See `references/sold-summary-safety.md §Upstream date-range constraint`.
2. **Rate limit (HTTP 429):** the upstream API rate-limits when more than 3-5 concurrent calls are in flight. **Wave A1 is therefore decomposed into sub-batches of at most 5 concurrent `tool_use` blocks per agent message.** If total Wave A1 calls > 5, sub-batches fire sequentially (Wave A1.1, A1.2, …) — each agent message waits for the prior message's tool results before issuing the next. See `references/sold-summary-safety.md §Upstream rate limit`.

| # | Tool | Purpose | Span | Fires when | Persistence risk |
|---|---|---|---|---|---|
| W1.A1.sold_new_A[k] | `get_sold_summary` | Per-make / per-group **New** sold, year_ago_quarter only | 3 mo | Channel-table row 1 is "Yes" | ~15-30 KB raw. Usually inline. Write→file→`--file` per `_failure-recovery.md`. |
| W1.A1.sold_new_B[k] | `get_sold_summary` | Per-make / per-group **New** sold, prior_quarter → mrcm | ≤8 mo | Channel-table row 1 is "Yes" | ~50-100 KB raw. Borderline inline/persist — handle both via Write→file→`--file`. |
| W1.A1.sold_used_A[k] | `get_sold_summary` | Per-make / per-group **Used** sold, year_ago_quarter | 3 mo | Channel-table row 2 is "Yes" | ~15-30 KB raw. |
| W1.A1.sold_used_B[k] | `get_sold_summary` | Per-make / per-group **Used** sold, prior_quarter → mrcm | ≤8 mo | Channel-table row 2 is "Yes" | ~50-100 KB raw. |
| W1.A1.ev_slice_A[k] | `get_sold_summary` | Per-make / per-group **EV slice** (`fuel_type_category="EV"` = BEV+PHEV), year_ago_quarter. Channel = dominant channel for the entity (New for OEMs; matches the populated sold-channel for dealer-groups). | 3 mo | Channel-table row 3 is "Yes" | ~10-20 KB raw (often less for low-EV makes). |
| W1.A1.ev_slice_B[k] | `get_sold_summary` | Per-make / per-group **EV slice**, prior_quarter → mrcm | ≤8 mo | Channel-table row 3 is "Yes" | ~30-70 KB raw. |

**Wave A1 sub-batch decomposition (current rate-limit-safe batch size: 5 concurrent):**

| Entity / classification | Wave A1 calls (= 2 × channels × makes) | Sub-batches (≤5 each) |
|---|---|---|
| OEM `legacy`, multi-make N=2 (F: Ford+Lincoln) | 12 | 3 batches (5+5+2) |
| OEM `legacy`, multi-make N=4 (GM: Chevy/GMC/Buick/Cadillac) | 24 | 5 batches (5+5+5+5+4) |
| OEM `legacy`, multi-make N=7 (STLA) | 42 | 9 batches (8×5 + 1×2) |
| OEM `pure_play` (TSLA, RIVN, LCID) | 4 | 1 batch (4) |
| Dealer-group `Both` (AN, LAD, PAG, SAH, GPI, ABG, CVNA) | 6 | 2 batches (5+1) |
| Dealer-group `Used-only` (KMX) | 4 | 1 batch (4) |
| Dealer-group `New-only` (none currently mapped) | 4 | 1 batch (4) |
| Single-make legacy (MBGAF) | 6 | 2 batches (5+1) |
| Multi-make legacy N=3 (BMWYY, HYMTF) | 18 | 4 batches (5+5+5+3) |
| Multi-make legacy N=5 (VWAGY) | 30 | 6 batches (5×6) |

Sub-batches fire **sequentially**, not concurrently — the orchestrator issues a new agent message only after the prior sub-batch's tool results have returned. Calls **within** a sub-batch fire in parallel via the single agent message's multiple `tool_use` blocks.

**Wall-clock cost per sub-batch:** ~6-8 seconds (MCP round-trip + response-persist latency). STLA's 9 sub-batches → ~45-75 seconds for Wave A1 alone. Trade-off accepted: correctness over speed.

### W1.A1.sold_*_A[k] / sold_*_B[k] — per-make (OEM) or per-group (dealer-group) sold, two-call split

**Call A (year-ago window)**, fired once per make per applicable channel:

```python
get_sold_summary(
    make="<Make>",                                          # OEM: per-make
    # OR
    dealership_group_name="<canonical>",                    # dealer-group: exact match to resolve_ticker.canonical
    inventory_type="New" | "Used",                          # TitleCase — channel-specific
    ranking_dimensions="make",                              # or "dealership_group_name" for dealer-group
    ranking_measure="sold_count",
    top_n=1,
    limit=5000,
    summary_by="state",
    date_from="<year_ago_quarter.date_from>",               # e.g., 2025-01-01
    date_to="<year_ago_quarter.date_to>",                   # e.g., 2025-03-31    (3-month span)
)
```

**Call B (prior → mrcm window)**, fired once per make per applicable channel in parallel with Call A:

```python
get_sold_summary(
    make="<Make>",
    inventory_type="New" | "Used",
    ranking_dimensions="make",
    ranking_measure="sold_count",
    top_n=1,
    limit=5000,
    summary_by="state",
    date_from="<prior_quarter.date_from>",                  # e.g., 2025-10-01
    date_to="<max(current_quarter.date_to, mrcm.date_to)>", # e.g., 2026-04-30 — covers prior_q + current_q + 1-2 mrcm months
)
```

**Worst-case Call B span: 8 months** (current_quarter and mrcm both populated; mrcm extends current_q by up to 2 months). All Call B spans are safely under the 12-month upstream cap — see `references/sold-summary-safety.md §Upstream date-range constraint §Verification of Call B max span` for the calendar-walk table.

### Why this split? Why not a single 12-month call?

Tempting alternative: `date_from = year_ago_quarter.date_from, date_to = year_ago_quarter.date_from + 12 months`. Discarded for two reasons:
1. **Span math fails.** From `2025-01-01` + 12 months = `2026-01-01`. Captures year_ago_quarter (Q1 2025) + Q2 2025 + Q3 2025 + Q4 2025 + first day of 2026. Misses **current_quarter (Q1 2026) entirely** and **mrcm** (e.g., April 2026). Then we'd need ANOTHER call to cover those. Same total call count, but the "wasted" 6 months of Q2/Q3 2025 data is fetched.
2. **No useful Q2/Q3 2025 data.** The skill's quarterly cadence only uses 4 specific quarters; everything in between is over-fetch. The two-call split deliberately skips the 6-month gap and saves ~33% of rows per channel.

### Persist each MCP response to a scratch file

Each call (A and B) is persisted to disk per `_failure-recovery.md §The pattern`. The orchestrator parses each scratch file in-process via imported helpers (no model-side `parse_sold_summary.py` invocation).

```bash
# Per Wave A1 / A2 MCP response:
#   PERSISTED (runtime saved to <path>) → use that path directly in the manifest.
#   INLINE   → Write(/tmp/marketcheck/<sid>/<call-name>.json, <response-string>)
#              where <call-name> follows _failure-recovery.md §<call-name> conventions.
```

The model never invokes `parse_sold_summary.py` directly. The orchestrator imports `_aggregate_make_by_window` / `_aggregate_group_by_window` and runs them per scratch file, extracting the inner `make_by_window` / `group_by_window` block automatically.

### W1.A1.ev_slice_A[k] / ev_slice_B[k] — per-make / per-group EV slice (BEV+PHEV)

Fires only when the entity has a non-skipped EV signal (legacy OEM OR any dealer-group). Skipped for `pure_play` (volume IS EV — DQ event k logged).

```python
# Call A
get_sold_summary(
    make="<Make>" | dealership_group_name="<canonical>",
    fuel_type_category="EV",                                # BEV ∪ PHEV per sold-summary-safety.md §EV classification
    inventory_type="New",                                   # Channel: dominant new-channel for OEMs;
                                                            #          matches Used-only=Used / New-only=New / Both=New for dealer-groups
    ranking_dimensions="make" | "dealership_group_name",
    ranking_measure="sold_count",
    top_n=1,
    limit=5000,
    summary_by="state",
    date_from="<year_ago_quarter.date_from>",
    date_to="<year_ago_quarter.date_to>",
)

# Call B
get_sold_summary(
    ...,                                                    # same params
    date_from="<prior_quarter.date_from>",
    date_to="<max(current_quarter.date_to, mrcm.date_to)>",
)
```

**EV channel rationale.** Equity analysts read EV-mix as "of the dominant channel, what share is electrified" — for OEMs this is New (OEM EV programs ship new; used EVs are a downstream secondary market); for dealer-groups, `compute_earnings_signals._build_ev_block` derives EV share against whichever combined channel populated, so a single-channel fetch on the dominant channel suffices. Cross-channel EV detail (Used-EV vs New-EV separately) is a v1.1 candidate.

### Months-map merge (internal to orchestrator)

The Call A and Call B months-maps are merged internally by `orchestrate._merge_months_maps` — no model-side step. Call A covers months in `year_ago_quarter.months[]` (e.g., `2025-01`, `2025-02`, `2025-03`); Call B covers months in `prior_quarter.months[]` ∪ `current_quarter.months[]` ∪ `[mrcm.label]` (e.g., `2025-10`–`2025-12`, `2026-01`–`2026-03`, `2026-04`). The two month-sets are disjoint by construction; the orchestrator uses dict-union and pools defensively via `_combine_monthly_aggs` on any unexpected collision.

**Failure cases (orchestrator-handled):**
- Call A fails, Call B succeeds → `year_ago_quarter` months absent → DQ event (m) → `volume_momentum.degraded_to: "qoq_only"`. Verdict still renders.
- Call B fails, Call A succeeds → `current_quarter` months absent → orchestrator returns `ok: false`, `error_type: "no_current_quarter_data"`. Render the halt block per template.
- Both fail → halt (same).
- Any per-call parser error → DQ event (a) for that call; downstream halt-vs-degrade rule applies.

## Wave A2 — active inventory (sub-batches of ≤5 concurrent calls)

Same sub-batching rule as Wave A1 applies. Wave A2 total = `channels × makes`:

| Entity / classification | Wave A2 calls | Sub-batches |
|---|---|---|
| Single-channel single-make (KMX, pure_play) | 1-2 | 1 batch |
| TSLA / RIVN / LCID (2 channels × 1 make) | 2 | 1 batch |
| Both dealer-groups | 2 | 1 batch |
| F / TM / HMC / NSANY (2 makes × 2 channels) | 4 | 1 batch |
| BMWYY / HYMTF (3 makes × 2 channels) | 6 | 2 batches (5+1) |
| GM (4 makes × 2 channels) | 8 | 2 batches (5+3) |
| VWAGY (5 makes × 2 channels) | 10 | 2 batches (5+5) |
| STLA (7 makes × 2 channels) | 14 | 3 batches (5+5+4) |

`search_active_cars` may or may not share the upstream rate-limit bucket with `get_sold_summary` — we conservatively apply the same ≤5 rule to Wave A2. If empirically they're separate buckets, we're over-batching A2 (correctness preserved, slightly slower than necessary).


| # | Tool | Purpose | Fires when | Persistence risk |
|---|---|---|---|---|
| W1.A2.active_new[k] | `search_active_cars` | Per-make / per-group **New** active inventory + price/DOM stats | Channel-table row 1 is "Yes" | ~1 KB — never persists. Stdin pipe always works. |
| W1.A2.active_used[k] | `search_active_cars` | Per-make / per-group **Used** active inventory + price/DOM stats | Channel-table row 2 is "Yes" | ~1 KB — never persists. |

### W1.A2.active_new[k] / active_used[k] — active inventory

**For OEMs** (per make):
```python
search_active_cars(
    make="<Make>",
    car_type="new" | "used",                                # lowercased channel
    stats="price,dom",
    rows=0,
    price_range="1-*",
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

**For dealer-groups** (per group):
```python
search_active_cars(
    mc_dealership_group_name="<canonical>",                 # syntax per sold-summary-safety.md §Active-inventory filter
    car_type="new" | "used",
    stats="price,dom",
    rows=0,
    price_range="1-*",
    fetch_all_photos=False,
    include_dealer_object=False,
    include_mc_dealership_object=False,
    include_build_object=False,
)
```

Pipe through:
```bash
echo '<response>' | python scripts/parse_search.py
# (parse_search responses are ~1 KB — heredoc/stdin pipe is fine for this script only)
```

Captures `{num_found, stats_present, stats: {price, dom}}`.

**Active-inventory failure handling.** Per `_failure-recovery.md §Halt-vs-degrade rule`, a failed active call DOES NOT halt the workflow — Days Supply for that channel degrades to null and the verdict is reduced over the remaining contributing slots. Log DQ event (a).

## After Wave A1 + A2 — assemble compute_earnings_signals input

The model writes the manifest JSON and invokes the orchestrator once. The orchestrator owns: per-file parsing, Call A+B months-map merge, unwrap of inner `make_by_window` / `group_by_window` blocks, channel-null assignment per classification, compute + aggregate invocation, dq_events accumulation.

```bash
1. Build manifest JSON listing every scratch file + pre-flight outputs.
2. Write(/tmp/marketcheck/<sid>/manifest.json, <manifest-json>)
3. python scripts/orchestrate.py --manifest /tmp/marketcheck/<sid>/manifest.json
4. Capture stdout — single structured envelope with verdict, leading indicators,
   per-make breakdown, signal drivers, dq_events.
```

See `references/_failure-recovery.md §Manifest schema` for the manifest shape, and `references/script-contracts.md §orchestrate.py` for the output envelope and error catalogue.

### Halt condition (the only post-MCP halt in W1)

If the orchestrator output's `ok == false` AND `error_type == "no_current_quarter_data"`:
- **HALT immediately.** Render the halt block from `assets/w1-output-template.md §Halt rendering`.
- Surface `dq_events` verbatim in the halt block's Data Quality Notes.

For other halt error types (`manifest_invalid`, `all_calls_failed`, `scratch_file_unreadable`, `missing_manifest`, `internal_error`): surface a one-line error to the user; no template render — investigate root cause.

All non-halt degradation (missing prior_quarter, missing year_ago_quarter, missing one channel, missing mrcm sold) is handled inside the orchestrator: leading-indicator fields land null, `aggregate_signals` skips those slots, the verdict reduces over remaining slots. When `year_ago_quarter` is null the `volume_momentum` slot degrades to QoQ-only with `degraded_to: "qoq_only"` (DQ event m logged) — the verdict still renders.

## Render

Use `assets/w1-output-template.md` verbatim. Every placeholder resolves against the orchestrator's single output envelope:
- Pre-flight passthrough: `<ticker>`, `<company_name>` or `<canonical>`, `<makes>`, `<classification>`, `<entity_type>`, `<windows.current_quarter.label>`, etc.
- Compute fields: `<headline.*>`, `<leading_indicators_raw.*>` (including `channel_split.{new,used}.{volume,asp,dom,msrp_gap}` and `dom.median_*` — new in v1.2), `<per_make_raw[i].*>` (with `share_pct`, ASP/DOM/MSRP-gap deltas, prior/year_ago volume — new in v1.2), `<active_inventory.*>` (with `active_p50_price` / `_p75_price` / `_p90_price` / `_median_price` and dom percentiles + `mrcm_sold_count` — new in v1.2), `<ev_block.*>` (with prior + year_ago ASP/DOM/units — new in v1.2), `<mix_block.*>`.
- Aggregate fields (flattened): `<verdict>`, `<per_metric_bands.*>`, `<composite_slots.*>`, `<scores.*>`, `<signal_drivers.strongest>`, `<signal_drivers.weakest>`, `<n_bullish>`, `<n_bearish>`, `<mean_score>`, `<rationale>`, `<per_make_divergence[i].*>`.
- DQ list: `<dq_events>`.

Template sections rendered (12 sections; §3.5 Channel Split is new in v1.2): §1 Identity, §2 Verdict, §3 Leading Indicators (now with median DOM row), §3.5 Channel Split (new — multi-channel entities only), §4 Per-Make Breakdown (expanded with share/deltas), §5 Inventory Health (expanded with percentiles + mrcm sold), §6 EV Transition (now with full trajectory), §7 Mix, §8 Bull Case, §9 Bear Case, §10 Signal Drivers, §11 Earnings-Preview Statement, §12 DQ Notes.

**Rendering rules to enforce (see template §Self-check):**
- Bull Case + Bear Case + Earnings-Preview Statement are **exactly 3 sentences each**.
- When `signal_drivers.weakest is null` (C12 fallback), Bear Case + Section 11 sentence 3 collapse to their fallback forms — no manufactured downside.
- No buy/sell/hold language anywhere. No consensus comparisons. No specific EPS forecasts.

## Wall-clock budget (W1)

Each wave now includes a 6-second inter-batch sleep between sub-batches (per `references/sold-summary-safety.md §Inter-batch delay`); the per-tier numbers below reflect that.

- Pre-flight: ~2s (3 local script calls).
- Wave A1: sub-batched at ≤5 concurrent per agent message; ~6-8s per sub-batch + 6s inter-batch sleep. Single-make tickers (TSLA/RIVN/LCID/KMX) = 1 sub-batch. F/TM/HMC/NSANY (2 makes) = 3 sub-batches. BMWYY/HYMTF (3 makes) = 4. GM (4 makes) = 5. VWAGY (5 makes) = 6. STLA (7 makes) = 9.
- Wave A2: same sub-batching + 6s inter-batch sleep rule. Wave A1 → Wave A2 boundary also gets a 6s sleep.
- Orchestrator invocation: ~1-2s (pure Python; reads scratch files, runs compute + aggregate in-process).
- **Per-tier totals (A1 + A2 sub-batches; includes inter-batch delays + orchestrator + pre-flight):**

| Ticker class | Sub-batches (A1+A2) | Wall-clock |
|---|---|---|
| TSLA / RIVN / LCID (pure_play 1 make) | 1+1 = 2 | ~21-27s |
| KMX (Used-only DG) | 1+1 = 2 | ~21-27s |
| Both DG (AN/LAD/PAG/SAH/GPI/ABG/CVNA) | 2+1 = 3 | ~32-44s |
| F / TM / HMC / NSANY (legacy, 2 makes) | 3+1 = 4 | ~43-58s |
| BMWYY / HYMTF (legacy, 3 makes) | 4+2 = 6 | ~60-80s |
| GM (legacy, 4 makes) | 5+2 = 7 | ~81-106s |
| VWAGY (legacy, 5 makes) | 6+2 = 8 | ~95-125s |
| STLA (legacy, 7 makes) | 9+3 = 12 | ~156-186s |

Sub-batches fire sequentially with 6s sleep between them; calls within a sub-batch fire in parallel. See `references/sold-summary-safety.md §Upstream rate limit` for the 5-concurrent rationale and `§Inter-batch delay` for the 6-second sleep rationale + fallback ladder (6→8→10).

## DQ event triggers in W1

| Event | Trigger | Emitter |
|---|---|---|
| `(a)` | Any Wave A1 or A2 call returns an error envelope (network, 422, **429 rate-limited**, 5xx, unexpected_shape) OR a scratch file referenced by the manifest can't be opened | `orchestrate.py` (per-call parser layer). **429 retries are FORBIDDEN within the same workflow** — log and continue. |
| `(b)` | Truncation envelope unwrapped via runtime path | `_common._maybe_unwrap` (inside orchestrator) |
| `(c)` | `resolve_ticker` returned `resolution=fuzzy` | Pre-flight step 3 (model-side) |
| `(d)` | Active-inventory `stats_present: false` — `num_found` rendered; price/DOM stats skipped | `compute_earnings_signals._build_active_inventory_channel` |
| `(f)` | Mix dimension skipped (Used-only / New-only DG OR OEM) | `compute_earnings_signals._build_mix_block` + OEM branch |
| `(i)` | Per-make / per-group / EV slice low-volume (< 100 sold) in current quarter | `compute_earnings_signals._build_ev_block` + `_build_per_make_raw` |
| `(k)` | EV slice skipped (pure_play OR zero EV current quarter) | `compute_earnings_signals._build_ev_block` |
| `(l)` | Per-make divergence detected (`aggregate.per_make_divergence` non-empty) | `orchestrate.py` (canonical formatter for the divergence list) |
| `(m)` | Year-ago quarter has no usable data → `yoy_*` fields null; volume_momentum degrades to QoQ-only | `compute_earnings_signals._compute_*_block` |
| `(n)` | Prior-quarter has no usable data → `qoq_*` fields null; volume_momentum degrades to YoY-only (rare; defensive) | Same |
| `(r)` | Per-make breakdown excluded a make — no current-quarter sold OR no data assembled | `compute_earnings_signals._build_per_make_raw` |

Render every DQ event VERBATIM in template Section 12 — do not paraphrase, do not invent new event codes.

## Worked example — small-cap legacy OEM (F)

**Pre-flight on 2026-05-13:**
- `compute_quarter_windows --today 2026-05-13` → current=Q1 2026, prior=Q4 2025, year_ago=Q1 2025, mrcm=April 2026.
- `resolve_ticker --input "F"` → exact: `ticker=F`, `entity_type=oem`, `classification=legacy`, `makes=["Ford","Lincoln"]`, `company_name="Ford Motor Company"`.
- Classification = legacy → fetch New + Used + EV channels.

**Wave A1 (2 makes × 3 channels × 2 splits = 12 calls in parallel):**
- `sold_new_A[Ford]` (2025-01-01 → 2025-03-31), `sold_new_B[Ford]` (2025-10-01 → 2026-04-30)
- `sold_used_A[Ford]`, `sold_used_B[Ford]` (same date pair)
- `ev_slice_A[Ford]`, `ev_slice_B[Ford]` (same date pair)
- Same 6 calls for Lincoln.
- Each call ≤8 months; well under the 12-month upstream cap.

**Wave A2 (2N = 4 calls in parallel):**
- `active_new[Ford]`, `active_new[Lincoln]`, `active_used[Ford]`, `active_used[Lincoln]`.

**Orchestrator invocation:** Write each scratch file (12 sold/EV + 4 active = 16 files) + manifest. Single invocation `python scripts/orchestrate.py --manifest /tmp/marketcheck/<sid>/manifest.json`. Orchestrator merges Call A+B months-maps internally (Ford New = {2025-01, 2025-02, 2025-03} ∪ {2025-10..2025-12, 2026-01..2026-04} = 10 months; same for Ford Used, Ford EV, Lincoln New/Used/EV), unwraps inner blocks, assembles compute input, runs `compute(cfg)` + `aggregate(cfg)`, emits the single envelope.

**Output envelope:** `leading_indicators_raw` with 8 slots (Volume, ASP, MSRP gap, DOM, Days Supply Used, Days Supply New, EV share, Mix=null), `per_make_raw` (2 rows: Ford, Lincoln with `sold_count_current`), `verdict` + bands + signal_drivers + per_make_divergence + `dq_events`.

**Template renders Sections 1-12**, with Mix section omitted (OEM), per-make breakdown rendered (multi-make), divergence callout if Ford's Volume QoQ band differs from the F composite by ≥ 2 score-points.

## Worked example — Used-only dealer group (KMX)

**Pre-flight on 2026-05-13:**
- Same quarter windows.
- `resolve_ticker --input "KMX"` → exact: `ticker=KMX`, `entity_type=dealer_group`, `classification=Used-only`, `canonical="Carmax"`.
- Classification = Used-only → fetch ONLY Used channel + EV slice.

**Wave A1 (1 group × 2 channels × 2 splits = 4 calls in parallel):**
- `sold_used_A` (per group, 2025-01-01 → 2025-03-31), `sold_used_B` (per group, 2025-10-01 → 2026-04-30)
- `ev_slice_A` (per group, Used channel, 2025-01-01 → 2025-03-31), `ev_slice_B` (per group, Used channel, 2025-10-01 → 2026-04-30)
- Do NOT fire sold_new — KMX is `Used-only` per classification table; the call would return empty and waste a slot.

**Wave A2 (1 call):**
- `active_used` only.

**Orchestrator invocation:** Write 4 sold/EV scratch files + 1 active + manifest. Single invocation. Orchestrator merges Call A+B internally (Used: 3 + 7 = 10 monthly aggregates; same for EV-Used), sets `sold_new_by_window: null` and `active_new: null` per Used-only classification.

**Output envelope:** Volume / ASP / MSRP gap / DOM derived from Used channel; `days_supply_used` populated; `days_supply_new = null` (Used-only); `mix_block = null` (no New channel to compute mix). Composite slots: 6 populated (volume_momentum, asp, msrp_gap, dom, days_supply_used, ev_share); 2 null (days_supply_new, mix). Verdict reduces over 6 contributing slots; BULLISH requires mean ≥ +1.0 across them.

**Template renders:** Section 7 (Mix) omitted; Section 5 renders only the Used row; otherwise standard.
