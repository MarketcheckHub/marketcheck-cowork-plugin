---
name: market-share-analyzer-updated
description: Real-time market share, conquest, dealer-group, EV-adoption, and regional-demand analytics from MarketCheck sold transaction data. Covers five competitive-intelligence workflows — brand share by make with current vs prior period bps shifts, segment conquest by body_type with leader and gap-to-leader, dealer-group benchmarking with efficiency scores, EV/Hybrid penetration tracking with brand-level electrification mix, and regional demand heatmap by state. Every output shows volume + share % + share-change in basis points; period comparison is mandatory for share / penetration workflows. Use when an OEM analyst, dealer-group strategist, market researcher, or competitive-intelligence team asks "what's our market share", "who is winning in SUVs", "which brands are gaining share", "EV adoption rate", "competitor analysis", "dealer group ranking", "segment share breakdown", "brand performance comparison", "conquest analysis", "regional demand heatmap", "quarterly share change", "top dealer groups by volume", "how did we do vs Toyota last quarter", "which brands are gaining EV market share", "where should we allocate more inventory", "what does the competitive landscape look like in pickups" — or raises any volume-share, conquest, or penetration intent without naming the skill. **US-only**; halts UK profiles since `get_sold_summary` is unavailable for the UK market.
version: 1.0.0
---

# Market Share Analyzer

Convert MarketCheck sold transaction data into real-time market share analytics. Track brand and model-level share, segment conquest patterns, dealer group performance, EV adoption curves, and regional demand distribution — all without waiting 60–90 days for traditional syndicated reports.

Five workflows map to distinct competitive-intelligence intents:

- **W1 — Brand Market Share** — "what's the share movement?" (current vs prior month, bps shifts, gainers vs losers)
- **W2 — Segment Conquest Analysis** — "who's winning in SUVs?" (body_type-scoped leader, gap to leader, fastest gainer)
- **W3 — Dealer Group Benchmarking** — "how do AutoNation and Lithia rank?" (volume / DOM / avg-price merged by group, efficiency score)
- **W4 — EV Adoption Tracking** — "EV penetration this month?" (EV/Hybrid % of total + brand-level electrification mix + period delta)
- **W5 — Regional Demand Heatmap** — "where does Toyota sell best?" (per-state volume + price + DOM for one make/model)

## Before you start

1. **Load the profile.** Run `scripts/load_profile.py` (reads `marketcheck-profile.md`, parses YAML frontmatter + JSON body). Profile is **optional** for this skill (it works fine on national/anonymous queries) — on exit 1, the skill emits a "No profile context — running in anonymous mode" line and asks the user for state-or-national + period inputs. On exit 0, the parsed profile flows through.

2. **Confirm the profile (or no-profile).** First user-facing line is one of:
   - `Using profile: <dealer.name>, <state or "national">, <country>`
   - `No profile context — running in <state or national> anonymous mode.`

3. **Branch on country.**
   - `country == "US"` → workflows below.
   - `country == "UK"` → **halt** per `references/country-uk.md` with: *"Market share analysis requires US sold transaction data and is not available for the UK market."* Every workflow depends on `get_sold_summary` which has no UK equivalent (per `mcp_server_tool_docs/get_sold_summary.md` line 202 — "US market only").
   - `country == "CA"` → **halt** with: *"Market share analysis is US-only — Canada has no `get_sold_summary` data surface. Re-visit when `get_ca_sold_summary` ships."*
   - Any other country → halt with the same US-only message.
   - When no profile is loaded, country defaults to US (the calling user is implicitly running US queries; UK users would need a profile to even reach the skill since `country == "UK"` halts there).

4. **Compute session values.**
   - `state` — read `profile.location.state` if profile loaded; otherwise prompt the user or default to national (no `state` filter on calls).
   - `inventory_type_resolved` — read `profile.session.car_type_resolved` (set to "used" / "new" by `load_profile.py`). When `"both"` (i.e. `car_type_resolved is None`), **halt and ask** *"Run market-share for **used** or **new** sales?"* — `get_sold_summary` doesn't mix the two cleanly.
   - `franchise_brands` — read `profile.dealer.franchise_brands` if available; passed to `compute_*.py --user-brand` for highlighting.
   - `run_id` — read `profile.session.run_id` (auto-assigned by `load_profile.py`). Never hardcode a scratch directory.

5. **Date window.** Default to `compute_period_window.py --months-back 1 --num-months 1` (last full calendar month) for the **current period**, and `--months-back 2 --num-months 1` for the **prior period**. The user can override (e.g. "Q1 2026 vs Q1 2025") — the skill expands quarterly into 3 monthly fan-out calls per period and concatenates the parsed rows before piping to the compute script. **Never accept mid-month dates** — `get_sold_summary` rejects them with HTTP 422 (per `references/sold-summary-safety.md`).

6. **Working directory.** All intermediate files (raw MCP responses, parsed outputs, compute outputs) are written to `/tmp/marketcheck/<session.run_id>/`. The directory is created lazily; the agent can `Write` files there directly. Always read `session.run_id` from the loaded profile when assembling paths.

7. **Session continuity.** Re-run `scripts/load_profile.py --run-id <previously-emitted>` after compaction to preserve the scratch directory. The path-traversal-safe override mirrors `competitive-pricer-updated`'s convention.

## `get_sold_summary` safety

Every workflow calls `get_sold_summary` exclusively. Per `references/sold-summary-safety.md`, every call MUST set:

- `inventory_type` — explicitly `"Used"` or `"New"`. Omitting defaults to `"New"` upstream, silently returning new-inventory rollups for a used-vehicle workflow.
- `limit=5000` — the default 1000 silently truncates multi-dimensional results (see `references/sold-summary-safety.md` line 40).
- `ranking_dimensions` — minimal per workflow. Avoid the default 3-dim `make,model,body_type`.
- `summary_by="state"` — explicit, even though it's the tool default.
- `date_from` / `date_to` — month-aligned via `compute_period_window.py` (or `compute_sold_summary_dates.py` for W3's 3-month rolling window).
- **Never pass `dealer_type`** — combined with narrow filters, it silently suppresses valid data (see `references/sold-summary-safety.md` line 63).

`compute_sold_summary_dates.py` exists for W3's "last 3 full months" canonical window; `compute_period_window.py` is the flexible windower for W1/W2/W4/W5 (`--months-back N --num-months M`).

## Truncation handling

`get_sold_summary` is the one tool in the toolset that returns raw JSON without an envelope (per `references/truncation-recovery.md`). `_common._maybe_unwrap` passes unwrapped payloads through transparently, so the standard `parse_sold_summary.py --file <path>` recipe works without any special casing. Truncation has not been observed in practice on `get_sold_summary` calls — but the recovery recipe is documented defensively.

## Facet discipline

Pass the user's `make` / `model` / `body_type` **verbatim** to `get_sold_summary`. If a call returns `error_type=make_model_not_found` (per `parse_sold_summary.py`), read `references/facet-discovery.md` and retry once with a facet-discovery call against `search_active_cars` (the same canonical make/model index serves both endpoints). Cache the resolved casing for the session; don't re-discover per call.

User-typed YMMT (e.g. "honda" lowercase) is NOT trusted-casing — run discovery once on the first filtered call. Decoded casing from a prior `decode_vin_neovin` run in the same session IS trusted.

## Parallelization (universal contract)

Every workflow follows the same wave-execution contract:

- **A wave is a batch of MCP calls fired in a single agent message** — multiple `tool_use` blocks in one assistant turn, dispatched concurrently by the runtime. The agent emits all calls in the wave together, then waits for the full batch of `tool_result` messages before issuing the next wave.
- **Within a wave, calls share no cross-dependency.**
- **Wait for the entire wave** before running the parser fan-out (Write → `parse_sold_summary.py --file`) and the `compute_*.py` step.
- **Wave content lives in the per-workflow reference.** Each `references/wN-*.md` defines its workflow's wave structure.

Latency budget at a glance:
- W1 (Brand Share): ~12s, 1 wave, 2 calls
- W2 (Segment Conquest): ~12s, 1 wave, 2 calls (or 12 calls for all-segments mode)
- W3 (Dealer Group Benchmarking): ~12–15s, 1 wave, 3 calls
- W4 (EV Penetration): ~15s, 1 wave, 6 calls
- W5 (Regional Heatmap): ~12s, 1 wave, 1–2 calls

## Data quality rule

Treat per-row missing fields (`average_msrp`, `median_days_on_market`, etc.) as `null`; render `—` for nulls. Don't infer. Surface non-trivial gaps as DQ events.

---

## Workflow 1 — Brand Market Share

Reference workflow. Triggers: "market share", "who is gaining share", "share change", "compared to last month", etc. Two parallel `get_sold_summary` calls (current + prior month) with `ranking_dimensions=make`. Aggregator computes per-make share %, share change in **basis points**, and gainer/loser classification.

→ Full spec in **`references/w1-brand-share.md`**.

---

## Workflow 2 — Segment Conquest Analysis

Triggers: "who is winning in SUVs", "segment leader", "Toyota vs Honda in pickups", "conquest opportunity". Two parallel calls with `body_type=<segment>` filter and `ranking_dimensions=make,model`. Computes segment leader, user-brand rank, gap to leader (units + share points), and fastest-gainer model.

→ Full spec in **`references/w2-segment-conquest.md`**.

---

## Workflow 3 — Dealer Group Benchmarking

Triggers: "top dealer groups by volume", "AutoNation vs Lithia", "rank dealer groups by efficiency", "which group has the lowest DOM". Three parallel calls (volume / DOM / avg sale price) for the current period with `ranking_dimensions=dealership_group_name`. Merge-by-group + efficiency score (sold_count / avg_dom). Q2=A: current-period only.

→ Full spec in **`references/w3-dealer-group-benchmarking.md`**.

---

## Workflow 4 — EV Adoption Tracking

Triggers: "EV penetration", "Hybrid adoption rate", "which brands are most electrified", "EV market share". Six parallel calls (EV / Hybrid / Total × current/prior). Q3=A: separate "no fuel filter" call per period for the total-market denominator. Outputs penetration percentages, period-over-period bps shifts, top EV/Hybrid models, and a brand-level EV-share table.

→ Full spec in **`references/w4-ev-penetration.md`**.

---

## Workflow 5 — Regional Demand Heatmap

Triggers: "where does Toyota sell best", "F-150 demand by state", "regional pattern", "geographic concentration". Single `get_sold_summary` call (or two, for dual-period) for one make (and optional model) with `summary_by=state` and no state filter. Computes per-state volume, % of national, weighted-mean price, price-vs-national ratio, and weighted-mean DOM.

→ Full spec in **`references/w5-regional-heatmap.md`**.

---

## Output

All workflows render via **`assets/output-template.md`** — single source of truth for block structure, per-workflow table schemas, period-comparison wording, and the internal self-check.

Render rules at a glance:

- **Lead with the competitive headline** — verdict + bps shift / leader / penetration / regional pattern.
- **Always show both volume + share %** in every per-make / per-model row. Raw counts without context are meaningless; percentages without counts lack scale.
- **Share change in basis points (`bps`)**, not percentage points. A move from 14.2% to 14.5% is `+30 bps`, never `+0.3%`.
- **Comparison period mandatory** for W1, W2, W4. W3 and W5 default to current-period only.
- **User brand bolded** in tables when `profile.dealer.franchise_brands` (or `--user-brand`) is set.
- **Source line at the bottom**: `Source: MarketCheck sold data, <period>, <state-or-national>, <inventory_type>.`

### Data Quality event log

Accumulate a running list of events across every workflow; feed it into the Data Quality Notes section at render time. Track:

- (a) **MCP tool errors or non-200 responses recovered from** — tool name, `error_type`, recovery path.
- (a1) **Facet-discovery retries** — when a `get_sold_summary` call returned `error_type=make_model_not_found` and a facet lookup resolved the correct casing.
- (b) **Truncation envelope unwraps** via `--file <path>` — rare on `get_sold_summary` (no envelope on success), but log if encountered.
- (e) **Fallback source attribution** — most commonly: *"Share computed over visible top-50 makes; long-tail (~2-5% of national volume) excluded."* (Q1=A footnote on W1, W4 total denominator.) Other examples: *"State Baseline weighted mean unavailable (`<reason>`)"*, *"EV brand share table sourced from total-current vs ev-current; brands present in ev but absent in total render `null` brand_total"*.
- (f) **Parameter adaptations** — when `ranking_dimensions=make` was used after a `validation_dimension_limit` retry, etc.
- (g) **Workflow branches skipped by design** — examples:
  - *"Quarterly aggregation skipped: user supplied a single-month period."*
  - *"Dual-period regional heatmap skipped: --prior not supplied."*
  - *"User-brand highlighting skipped: profile has no franchise_brands."*
  - *"`--user-make` filter skipped: user did not scope dealer-group benchmarking to a brand."*

If the list is empty, omit the Data Quality Notes section entirely (do not render an empty header).

## Self-check

The 13-item verification checklist lives in `assets/output-template.md`. It is an **internal guardrail** — the model runs each check silently before returning and does NOT render the full checklist to the reader.

- **All applicable checks pass** → emit a single footer line, e.g. `✓ Verified: profile, geography + period, bps formatting, comparison period, dual columns, pipeline executed.`
- **Any check fails** → emit failures only, one per line, prefixed `⚠`, with a one-line note on what was corrected or caveated in the output to compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.
