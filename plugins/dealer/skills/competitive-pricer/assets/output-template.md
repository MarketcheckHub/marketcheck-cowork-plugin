# Output Template — Competitive Pricer

This file is the **single source of truth** for output block structure, the
8-column comp table schema, verdict wording, and the internal self-check.
Every workflow renders its output by adapting this template — see the
"Render variations" section at the end for which blocks each workflow uses.

Placeholders in angle brackets `<...>` are interpolated from the parser /
`comp_stats.py` output. Optional blocks are marked `(OPTIONAL)` and only
render when the precondition holds.

**Naming convention.** Lowercase interpolation placeholders like `<primary>`,
`<primary.marketcheck_price>`, `<channel_stats.primary.n>` reference fields on
`comp_stats.py` / `parse_predict.py` output objects — pull the exact numeric
value. Uppercase labels like `<PRIMARY>` are rendered F/I human labels — map
`primary` → `"Franchise"` or `"Independent"` based on the dealer's
`session.dealer_type_title`. Keep the two namespaces distinct.

---

## First line (always)

```
Using profile: <dealer.name>, <zip or postcode>, <country>
```

---

## Decoded Specs

```
Year:         <year>
Make:         <make>
Model:        <model>
Trim:         <trim>
Body Type:    <body_type>
Drivetrain:   <drivetrain>
Engine:       <engine>
Transmission: <transmission>
MSRP:         $<msrp>
VIN:          <VIN>
Mileage:      <user-supplied miles>
Asking Price: $<user_price>     (render "—" if not supplied)
```

For YMMT-entered subjects (UK profile, or user chose not to provide a VIN),
replace the VIN row with `Source: user-supplied YMMT`.

**Null-field rule (hallucination guard):** render any field whose value
parses as `null` / missing as literal `—`. Do NOT substitute plausible
defaults from model knowledge — e.g. if `engine` decoded to null, do not
fill in `"2.0L Turbo I4"` just because the trim sounded turbocharged. The
decoder's silence is authoritative.

For the YMMT-only US branch (no VIN, no decode): omit `body_type`,
`drivetrain`, `engine`, `transmission`, `MSRP` rows entirely (those come
from decode_vin_neovin which we skipped). Keep Year / Make / Model / Trim
/ Mileage / Asking Price.

---

## Headline  (always — leads every workflow except W5)

**Exactly one sentence by default.** First sentence names the verdict, the
dollar gap, and the anchor source.

**A second sentence is added ONLY when `mileage_moat.tier == "moat"`** — i.e.
`is_moat == true`, subject is ≥20% under the local comp median miles. That
second sentence is `mileage_moat.moat_phrase` verbatim — a listing-copy-ready
line the dealer can lift for their VDP description.

For `mileage_moat.tier == "modest"` (10–20% under median) — **NO Headline
second sentence.** The modest-tier signal surfaces as a Key Signals bullet
only (see the Key Signals rule below). For `tier == "none"`, no mileage
signal anywhere.

```
<Verdict>: at $<user_price>, you're $<|gap|> <above/below> the
<anchor> of $<anchor_value> (<gap_pct, 2dp when within 0.5% of −8/−3/+3/+8 else 1dp>%).
<moat_phrase ONLY IF tier=="moat">
```

Where `<anchor>` is:
- `"<sold_count_90d>-unit sold-90d trim median"` when `verdict_source == "sold_anchor"`
- `"<n>-comp active-listing median"` when `verdict_source == "quartile"`

**Gap precision rule.** Render `<gap_pct>` with **two decimals** when `|gap|`
falls within 0.5% of any sold-anchor band boundary (−8%, −3%, +3%, +8%);
otherwise one decimal. The two-decimal form prevents visual ambiguity at the
band edges: a `−2.6%` rendering hides whether the underlying number is −2.55%
(At Market) or −2.65% (still At Market by ±3% rule). At 2dp, `−2.63%` is
unambiguously inside the At-Market band.

**W4 Headline variation (no subject vehicle).** W4 has no asking price and no
sold-anchor verdict, so the W1-shaped Headline above doesn't apply. Render
the W4 Headline as a market-summary sentence:

```
<year> <make> <model> [<trim>] in <profile.location.state>:
<quartile.n> active comps, median $<quartile.median>, p25–p75 $<quartile.p25>–$<quartile.p75>,
state baseline $<state_baseline.weighted_avg_sale_price> across <state_baseline.total_sold_count> sold.
```

Source fields: `comp_stats.quartile.{n,median,p25,p75}` and
`parse_sold_summary.state_baseline.{weighted_avg_sale_price,total_sold_count}`.
When `state_baseline` is null (sold-summary failed or returned no rows for the
profile's state), omit the "state baseline ..." clause from the Headline. When
trim is absent (W4 model-level mode), drop `[<trim>]` and append `(model-level,
all trims)` to the scope.

**W5 Headline variation (competitor-activity headline, v1.8.0+).** W5 has no
subject vehicle; its Headline is a market-activity summary sourced entirely
from `aggregate_w5_signals` output. Render:

```
<active_count>-comp local market for <year> <make> <model> [<trim>]:
<drop_count> drops in last 30d (<drop_rate*100>%),
<raise_count> raises (<raise_rate*100>%),
MoS <mos>.
```

Source fields: `aggregate_w5_signals.{active_count, drop_count, raise_count,
drop_rate, raise_rate, mos}`. When `mos is null` (sold-90d call failed or
returned 0 sold), omit the `, MoS <mos>` clause. When trim is absent (W5
model-level mode), drop `[<trim>]` and append `(model-level, all trims)` to
the scope.

---

## Market Snapshot  (always)

```
Radius:                <radius_mi> mi from <city> (<profile.location.city>)
Active Comps:          <active_count>   (<kept_count> rendered after variant filters)
Sold (90d, local):     <sold_count_90d>
Months of Supply:      <mos>            (active / (sold_90d / 3))
Price-Drop Rate (visible):     <drops_in_set> of <n> (<drop_rate_visible*100>%)
Price-Drop Rate (market-wide): <drops_market_wide_count> of <active_count> (<drop_rate_market_wide*100>%)
State Baseline (<make> <model> across all trims & years in <STATE>, last 3 full months):
  avg sale $<avg_sale_price>  ·  avg DOM <avg_dom> days  ·  sold <sold_count>
```

**State Baseline scope note (always render below the block when the State Baseline rendered):**

> *State Baseline reflects state-wide sold velocity for the make/model — a broader cut than the trim-specific sold anchor in the Headline. Use it for market-health context, not direct price comparability.*

The scope qualifier is inline (parenthetical on the line itself) and the one-line note below the block — readers scanning the Market Snapshot see the scope at a glance and don't read the $X state average as directly comparable to the trim-specific sold median in the Headline. If the State Baseline call degraded (see `references/sold-summary-safety.md` recovery table), omit both the line and the note.

Two price-drop rates because they answer different questions:
- **Visible rate** tells the reader what's happening in the N comps they're
  about to see in the table.
- **Market-wide rate** tells the reader what's happening across the full
  `active_count` local market, regardless of which rows we pulled. Useful
  for "the market is softening" vs. "just my visible slice is."

Optional Thin-market note (OPTIONAL — only when premium-unit auto-widen fired):
```
Thin market at <orig_radius>mi (<orig_num_found> comps); widened to <new_radius>mi
(<new_num_found> comps) for anchoring.
```

---

## Price Distribution  (always)

Header line reconciles the distribution's computation scope with the
rendered comp table's row count:

```
Price Distribution  (n=<quartile.n>; source: <stats_source>)

Min:        $<quartile.min>
P25:        $<quartile.p25>
Median:     $<quartile.median>
Mean:       $<quartile.mean>   (stddev: $<quartile.stddev>)
P75:        $<quartile.p75>
Max:        $<quartile.max>
```

**Header rule.** When `quartile.n == n` (server-stats count matches the
filtered visible count, or client stats computed directly from `n`), render
the header as above. **When `quartile.n != n`** — typically because the
server returned stats over the full `active_count` but a shadow-VIN or
invalid-price exclusion trimmed the visible rows — render:

```
Price Distribution  (n=<quartile.n> · <n> in table; source: <stats_source>)
```

The ` · <n> in table` suffix tells the reader "distribution is computed
over <quartile.n> comps; the table below shows <n> after exclusions" so the
numbers reconcile at a glance.

- `source: server` — stats computed by the server over all `active_count`
  listings via `stats="price,miles"` on the step-4 asc call.
- `source: client` — stats computed locally from the visible `n`
  subset (only fires when `server_stats.price.count < min_n` or the server
  didn't return stats at all).

**Client-source footnote (D6).** When `stats_source == "client"`, the
distribution covers only the visible subset, not the full market. Render a
footnote directly below the Price Distribution block:

> *Client-computed over `<n>` visible comps; server-wide stats unavailable —
> percentiles and quartile bounds may understate the true spread across the
> `<active_count>`-unit market.*

Do NOT render the footnote when `stats_source == "server"` — server stats
already cover the full market.

---

## Active Mileage Distribution  (always when mileage_distribution present)

Source: `comp_stats.mileage_distribution` — server-preferred (same
`stats="price,miles"` call as the price quartile), with client fallback over
the filtered comp set when server miles stats are absent. The block label is
explicitly "**Active** Mileage Distribution" to distinguish from sold-90d
miles (which feeds only the mileage_moat check, not this block).

```
Min:        <mileage_distribution.min> mi
Median:     <mileage_distribution.median> mi
Mean:       <mileage_distribution.mean> mi
Max:        <mileage_distribution.max> mi
```

When `mileage_distribution.source == "client"`, emit a compact suffix on the
block header: ` (client-computed over <n> visible comps)`.

---

## DOM Distribution  (always)

Using the profile's DOM thresholds `{fresh_max_days, aging_max_days}`:

```
Fresh (0–<fresh_max_days>d):      <dom_buckets.fresh>  (<pct>%)
Aging (<fresh_max+1>–<aging_max_days>d): <dom_buckets.aging>  (<pct>%)
Stale (<aging_max+1>+d):           <dom_buckets.stale>  (<pct>%)
Unknown:                           <dom_buckets.unknown>
```

> Source field: `dom_active` only — never `dom_180` or `dom`. When `dom_active`
> is null, the listing counts toward `Unknown`, not toward any bucket via
> fallback. See `references/w1-price-check.md` step 4 for the field-semantic
> rationale (each DOM variant answers a different market-presence question).

---

## Your Price Position  (W1 only — always when user_price present; W2 has its own per-VIN block in `assets/w2-output-template.md`)

Every "MarketCheck Price" line below renders a value sourced from the
`predict_price_with_comparables` MCP call (the MarketCheck Price ML
prediction product). The `MarketCheck` prefix is load-bearing — it
distinguishes these MarketCheck-sourced numbers from the active-comp
`Market Median` and the realised-sale `Sold-90d Trim Median` anchors below.

The default (non-CPO branch only) layout reads from `marketcheck_predict.<role>`:

```
Your Price:                                 $<user_price>       (<dealer_type> dealer)

Franchise MarketCheck Price (non-CPO):      $<marketcheck_predict.nocpo_primary.marketcheck_price>
  MC active comps:  n=<nocpo_primary.comparables_n> · median $<...comparables_price_stats.median> · IQR $<p25>–$<p75> · range $<min>–$<max>
  MC recent comps:  n=<nocpo_primary.recent_comparables_n> · median $<...recent_comparables_price_stats.median> · IQR $<p25>–$<p75> · range $<min>–$<max>

Independent MarketCheck Price (non-CPO):    $<marketcheck_predict.nocpo_context.marketcheck_price>
  MC active comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
  MC recent comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>

Gap vs Market Median:                       $<gap_vs_median.diff>  (<gap_vs_median.pct>%)
Gap vs Sold-90d Trim Median:                $<sold_gap.diff>  (<sold_gap.pct>%)    — only when verdict_source == "sold_anchor"
Percentile Rank:                            <percentile>th           (<higher than X% of comps>)
Gap vs <PRIMARY>-Only Median:               $<primary_only.diff>   (<primary_only.pct>%)   — only when primary_only is non-null
```

**MC-Price comp sub-line sources.** The `MC active comps` and `MC recent
comps` sub-lines under each `MarketCheck Price` line read from
`marketcheck_predict.<role>.comparables_price_stats` and
`marketcheck_predict.<role>.recent_comparables_price_stats` — the price
distributions over the comp pools the MarketCheck Price model used. Both
are MarketCheck-sourced (note "MC" = MarketCheck abbreviation; the parent
line establishes the brand and the sub-lines inherit it).

Use `<role>.comparables_price_stats.median` for the median, `.percentiles.25.0`
and `.percentiles.75.0` for the IQR, `.min` and `.max` for the range.

**Sub-line absence rule:** if `<role>.comparables_price_stats` is `null`
(parser couldn't extract — empty or malformed `stats.price` block), render
the count line only (`n=<count>`) and omit the median/IQR/range portion.
Mirror for `recent_comparables_price_stats`.

**`Gap vs Sold-90d Trim Median` sourcing.** When `verdict_source == "sold_anchor"`,
render this line directly below `Gap vs Market Median` using `sold_median` from
`comp_stats` output: `diff = user_price - sold_median`, `pct = diff / sold_median * 100`.
This is the gap the verdict is actually anchored on — buyers paid `$<sold_median>` on
median over the last 90 days; `Gap vs Market Median` is computed against the active-
listing median (asking prices, not realised). When both lines are present, the
active-median gap and sold-median gap together tell the reader: *this is where the
market is asking vs. where buyers actually paid*. When `verdict_source == "quartile"`
(sold_count_90d < 5), omit the `Gap vs Sold-90d Trim Median` line — the anchor is the active
quartile distribution, not sold data.

**CPO subject additional lines (D5).** When the subject is CPO (or when the
CPO branch ran regardless), add two more MarketCheck Price lines + their
sub-lines below the non-CPO pair so the reader sees both channels × both
CPO states. Read from `marketcheck_predict.cpo_primary` and
`marketcheck_predict.cpo_context` — populated exactly when those CPO-branch
predict calls captured a `marketcheck_price`.

```
Franchise MarketCheck Price (CPO):          $<marketcheck_predict.cpo_primary.marketcheck_price>
  MC active comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
  MC recent comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
Independent MarketCheck Price (CPO):        $<marketcheck_predict.cpo_context.marketcheck_price>
  MC active comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
  MC recent comps:  n=<...> · median $<...> · IQR $<...>–$<...> · range $<...>–$<...>
```

The `(non-CPO)` / `(CPO)` suffixes are load-bearing — without them, a CPO
dealer reading "Franchise MarketCheck Price $37,656" might assume that's
the CPO-adjusted number when it is not. v5 added these suffixes by judgment
(the agent's §8 ambiguity); this template now prescribes them.

When the CPO roles are missing on `marketcheck_predict` (subject is non-CPO
or CPO branch didn't run), render only the two non-CPO lines — do not add
the `(non-CPO)` suffix in that case (no CPO row to distinguish against).
Use the plain label `Franchise MarketCheck Price:` /
`Independent MarketCheck Price:` as in the original layout.

**`primary_only` sourcing.** The `Gap vs <PRIMARY>-Only Median` line reads the
consolidated `primary_only` block emitted by `comp_stats.py`. The renderer
does NOT pick between `channel_stats.primary` and `channel_stats.primary_non_cpo`
inline — comp_stats makes the decision:

- Subject is non-CPO AND `primary_non_cpo.n >= 2` → `primary_only.source == "primary_non_cpo"` (median strips CPO comps from the same-channel cut so the comparison is apples-to-apples for a non-CPO subject).
- Otherwise (subject is CPO, or `primary_non_cpo.n < 2`) → `primary_only.source == "primary"` (includes any CPO comps in the channel).
- `primary.n < 2` → `primary_only is None` → **omit the entire line**.

When rendered, `<PRIMARY>` is the human label (`Franchise` or `Independent`)
mapped from `session.dealer_type_title`. `<primary_only.diff>` and
`<primary_only.pct>` are the already-computed numbers — do not recompute
against a different source.

Render rules for percentile (four-state, driven by `percentile_source` +
`percentile_approx` + `percentile_bounded`):

| `percentile_source` | `percentile_approx` | `percentile_bounded` | Render (exact string) |
|---|---|---|---|
| `server` | `False` | `null` | `<N>th percentile (exact, server over <active_count> comps)` |
| `server` | `True`  | `null` | `~<N>th percentile (approx, server over <active_count> comps)` + footnote: *"Approx: server count (<server_n>) is thin OR price sits outside the known p5–p99 range. Interpolation is coarse in this regime."* |
| `client` | (ignored) | non-null | `<low>th – <high>th percentile (bounded — visible set only)` + footnote: *"Server percentiles unavailable; rank bounded over visible <n> of <active_count> comps. True rank lies within the displayed range."* |
| `client` | (ignored) | `null` | `<N>th percentile (visible set, n=<n>)` — honest but scoped |

The parenthetical suffix is **prescribed**, not optional — it tells the reader
in a glance whether the rank is exact/approx and over how many comps, without
them having to infer from surrounding blocks.

Never claim 100th percentile unless `percentile_source == "server"` with an
exact match. The `~` prefix on approx, the `(bounded ...)` suffix, and the
`(visible set, n=<n>)` suffix on client-exact are all load-bearing signals —
do not drop them or paraphrase.

---

## CPO Premium  (OPTIONAL — only when subject is CPO and all 4 predict roles populated)

```
CPO Premium (Franchise):     +$<marketcheck_predict.premium_primary>  (<pct_primary>%)
CPO Premium (Independent):   +$<marketcheck_predict.premium_context>  (<pct_context>%)
Certification Cost (you):    $<marketcheck_predict.certification_cost>
Net Margin from CPO:         +$<marketcheck_predict.net_margin_primary>  (<PRIMARY> channel)
```

> *Premium and Net Margin are computed from the MarketCheck Price (CPO) and
> MarketCheck Price (non-CPO) values rendered in the Your Price Position block
> above: `Premium = MC Price (CPO) − MC Price (non-CPO)`; `Net Margin from CPO
> = Premium − Certification Cost`. Premium is a market concept (the dollar
> spread the local market pays for the CPO program), not a MarketCheck
> product — so this block does NOT carry the `MarketCheck` prefix on its line
> labels. The MarketCheck-direct prefix is reserved for `MarketCheck Price`
> and the MC-Price comp counts/distributions that come straight from the
> `predict_price_with_comparables` MCP call.*

**Naming distinction (load-bearing).** Only fields that come **directly** from
the `predict_price_with_comparables` MCP call carry the `MarketCheck` prefix
in rendered labels — that's `MarketCheck Price` (the predicted scalar) and
the MC-Price comp counts/distributions. Derived calculations (`CPO Premium`,
`Net Margin from CPO`) reference MarketCheck Price values as inputs but are
themselves market/dealer concepts and render unprefixed. `Certification Cost
(you):` is also unprefixed — it's dealer-sourced from
`profile.dealer.cpo_certification_cost`, not from any MarketCheck endpoint.

The block renders only when `marketcheck_predict.premium_primary` and
`marketcheck_predict.premium_context` are both non-null (all 4 predict roles
captured). When any role is missing, omit the entire block — the upstream
`Your Price Position` lines still render whatever roles did populate.

---

## Parser field map — what the renderer reads

The renderer reads pre-computed fields from `parse_search.py`'s normalized listing schema and pre-computed scalars from `comp_stats.py`'s output. **Never read raw MCP field names** — the parser has already flattened/computed everything the renderer needs. Re-implementing parser logic during rendering is a rendering bypass and is forbidden (see `references/w1-price-check.md` rendering-bypass warning).

Per-listing fields read from each merged listing:

| Renderer use | Read this field | Never read this raw MCP path |
|---|---|---|
| Dealer column (name) | `dealer_name` | `dealer.name` (parser flattens) |
| Dealer column ((CPO) suffix) | `is_certified` (tri-state True/False/None) | (the parser already normalizes raw integer 1/0/absent to tri-state) |
| Type column | `dealer_type` | `dealer.dealer_type` (parser flattens) |
| Price column | `price` | (no transform) |
| Miles column | `miles` | (no transform) |
| DOM column | `dom_active` | `dom`, `dom_180`, `dom_lifetime` — different semantics |
| Distance column | `distance_mi` | `dist` (parser flattens from raw `dist`/`distance`) |
| Price Change column ($) | `price_change_amount` (PRE-COMPUTED by parser) | the formula at parse_search.py:96–104 — **never re-implement** |
| Price Change column (%) | `price_change_percent` | (no transform; pair with the pre-computed amount) |
| Spec subtitle | `body_type`, `drivetrain`, `engine`, `transmission` | (parser flattens from `build.*`) |

Per-row computed fields (renderer-side, deterministic):

| Field | Formula | Source |
|---|---|---|
| `vs_mkt_median` | `price - quartile.median` | `comp_stats.quartile.median` (single scalar; same for every row) |
| `is_closest_to_user_price` | `abs(price - user_price)` is minimal across the rendered set; tiebreak: first row in ascending sort wins | `user_price` from skill input |

Comp_stats output the renderer reads:

| Field | Use |
|---|---|
| `quartile.median` | "vs Mkt Median" subtraction; render `—` when this scalar is null/missing (thin market) |

Anything not in this map is not a renderer input. If you need a value not listed here, the deterministic pipeline isn't producing it — file an issue, don't reach into the raw MCP response.

---

## Competitive Set  (always — the 8-col table)

Columns, in order, every workflow:

```
| Dealer | Type | Price | Miles | DOM | Distance | vs Mkt Median | Price Change |
```

Column rules (every column reads from the Parser field map above; no recomputation):

- **Dealer** — read `dealer_name` (parser-flattened from raw `dealer.name`). Truncate to 30 chars total with U+2026 ellipsis when `len > 30`: `dealer_name[:29] + "…"`. Then append ` (CPO)` when `is_certified is True` (False and None render no marker — tri-state).
- **Type** — read `dealer_type`. Render `F` for `"franchise"`, `I` for `"independent"`, `—` for null. Never guess from the dealer name or domain.
- **Price** — read `price`, format as `$<int>` with comma thousands. parse_search filters `price ≤ 0` and null prices upstream, so this column never renders `$0` or `—`.
- **Miles** — read `miles`, format as `<int>` with comma thousands; render `—` when null.
- **DOM** — read `dom_active` (the only DOM variant the skill uses). Render `—` when null. Never substitute `dom`, `dom_180`, or `dom_lifetime` — they measure different market-presence questions (see `references/w1-price-check.md` step 4).
- **Distance** — read `distance_mi` (parser-flattened from raw `dist`/`distance`); format as `<dec.2> mi`; render `—` when null. Never read `dist`.
- **vs Mkt Median** — compute `price - comp_stats.quartile.median` per row; render signed (`+$<int>` or `−$<int>` with U+2212 minus). Render `—` only when `comp_stats.quartile.median` is unavailable (thin market). **This is per-row, not per-subject** — `user_price` is not used in this column.
- **Price Change** — read `price_change_amount` (pre-computed by parser per parse_search.py:96–104) and `price_change_percent`. Render `−$<|amount|> (−<pct>%)` (U+2212 minus) when `price_change_amount < 0`; `+$<amount> (+<pct>%)` when `> 0`; `—` when null OR `0`. **Do NOT re-implement the formula** — `price_change_amount` is the parser's authoritative output and handles every edge case (zero `ref_price`, missing `price_change_percent`, sign near zero). Re-implementing produced a fabricated `−$13,807` figure on a listing whose canonical change was `−$27,807` in a prior session; the present prescription closes that hole structurally.

Sort ascending by price. Mark the row whose price is closest to the user's
asking price with ` ← You` after the Price column value, **among rows that
survived the `--subject-vin` / `--exclude-vins` filters**. The comp table is
already post-filter (shadow listings excluded upstream), so the marker lands
on the nearest-priced real comp, never on the user's own shadow. **Skip the
`← You` marker entirely when `user_price` is null** (W4 Market Distribution,
W5 Competitor Price Movement) — there's no "you" without an asking price.

**Shadow-listing footnote (A5).** When `parse_search.py` reports
`filtered_out.self_vin_match > 0`, the subject VIN appeared at a different
dealer's lot (shadow listing) and was excluded from the rendered table.
Render a footnote directly below the Competitive Set:

> *Shadow listing: subject VIN `<VIN>` excluded from the comp set (found at
> `<dealer_name>`, `<distance> mi`, `$<price>`, with `<subject_dom_active>`
> days on lot). Other listings at the same dealer with different VINs remain
> in the comp set as ordinary comps.*

Source `dealer_name` / `distance` / `price` / `subject_dom_active` from the
pre-filter asc response where the self-VIN match occurred.

**Matching rule.** The shadow filter matches **on VIN only**, not on
`(dealer, price)` (see `parse_search.py` lines 200–205). When the same dealer
hosts a non-shadow comp at the same price as the subject — e.g. a sibling
unit (same dealer, same listed price, **different VIN**) — that sibling is a
normal comp and stays in the set. Do **not** annotate it as `(shadow)` and do
**not** merge its fields with the subject's. One prior session merged a sibling
row INTO the subject (using the sibling's mileage as the subject's, while the
prose used the subject's own DOM field) — the resulting row was incoherent.
Two listings at the same dealer at the same price are not "the same listing";
they are two units that happen to share two attributes.

**`← You` marker placement.** Mark the row whose price is closest to the user's
asking price *among rows that survived the `--subject-vin` / `--exclude-vins`
filters*. The marker may land on a sibling row if one is the closest surviving
comp; that's the correct behavior. Do **not** place `← You` on the subject's
own data and do **not** synthesize a "YOUR LISTING" row in the comp table — the
user's data is in the Decoded Specs / Your Price Position blocks above the
table, not inline as a comp. This resolves the ambiguity v4 and v5 hit (v4
marked the shadow, v5 silently moved the marker with no disclosure).

Rows with `price_change_percent == 0` (W5 only) render Price Drop? as `—`
and go below real drops with a footnote: `"Listings with no observed change
are flagged via the server's price_change filter but lack a signed delta."`

### Spec subtitle (handled by `render_comp_set_table.py`)

Heterogeneity detection (deterministic, in the renderer): for each of `body_type`, `drivetrain`, `engine`, `transmission`, count the distinct non-null values across all rendered rows.

- **All 4 fields homogeneous** (each has ≤1 distinct non-null value across rows): renderer emits a single modal-spec line above the table header: `Spec (all comps): <body_type> · <drivetrain> · <engine> · <transmission>` (omits fields that are null on every row; joins the rest with ` · `).
- **Any field heterogeneous** (>1 distinct non-null value): renderer emits a per-row subtitle under each comp row in the format `  ↳ <body_type> · <drivetrain> · <engine> · <transmission>` (2-space indent, U+21B3 down-and-right arrow, then the row's own values; omits null fields silently).
- **All 4 fields null on every row** (rare): renderer omits subtitles entirely.

```
| Lexus of Beverly Hills | F | $45,990 | 32,100 | 45 | 12.00 mi | +$450 | — |
  ↳ SUV · AWD · 3.5L V6 · 8-speed Auto
```

These fields are **display-only**. They do not drive any filter, stats comparison, or API parameter; they exist purely so the reader can eye-ball spec heterogeneity in the comp set.

### Renderer script for the spec subtitle + 8-col table

The 8-column table is the largest rendered chunk in W1 (~208 cells across 26 rows × 8 columns) and the highest-bypass-risk surface. Use the deterministic renderer:

```
scripts/render_comp_set_table.py \
  --merged <merge_comps.py output path> \
  --comp-stats <comp_stats.py output path> \
  --user-price <asking_price>             # numeric; pass empty string for null
  --currency '$|£'                         # default '$'; agent passes from profile.location.country
```

The script:

1. Reads parsed fields per the Parser field map above.
2. Computes the two per-row derived fields (`vs_mkt_median`, `is_closest_to_user_price`).
3. Detects spec-field heterogeneity per the rule above; emits the spec subtitle (above-table or per-row).
4. Applies the column rules (truncation, CPO suffix, signed Unicode-minus formatting).
5. Emits the markdown table verbatim on stdout. Copy stdout into the rendered W1 report.

**The renderer does NOT emit the shadow-listing footnote** — that footnote needs pre-filter asc.json access (for shadow-dealer name/price/dom) which `merged.json` doesn't carry. The agent renders the footnote separately when `parse_search.filtered_out.self_vin_match > 0`.

If the script fails (missing inputs, malformed JSON, script not present), the renderer falls back to manual cells per the column rules — but that path **must** prefix the table with `⚠ table renderer bypassed; manual cells may diverge from canonical formatting` and emit self-check warning #14. Do NOT silently hand-roll the table.

---

## Same-Channel View  (OPTIONAL — W1 only; only when channel_stats.primary.n >= 2)

Two layouts depending on whether `primary_non_cpo` is present. `comp_stats.py`
only emits `primary_non_cpo` when the subject is non-CPO AND there are ≥2
non-CPO comps in the primary channel (see CPO sourcing rule above). For a
CPO subject, or for a non-CPO subject with a thin non-CPO slice,
`primary_non_cpo` is `None` and the comparison falls back to the full primary
median.

**Layout A — `primary_non_cpo` present (non-CPO subject with CPO comps to strip):**

```
Same-Channel View (<PRIMARY>)
  All <PRIMARY> comps:           median $<primary.stats.median> (n=<primary.n>, <primary.cpo_count> CPO)
  <PRIMARY> non-CPO only:        median $<primary_non_cpo.stats.median> (n=<primary_non_cpo.n>)
  Your price vs non-CPO median:  <signed $diff> (<pct>%)
```

**Layout B — `primary_non_cpo` is None (CPO subject OR non-CPO subject with no CPO comps to strip):**

```
Same-Channel View (<PRIMARY>)
  All <PRIMARY> comps:             median $<primary.stats.median> (n=<primary.n>, <primary.cpo_count> CPO)
  Your price vs all-<PRIMARY> median:  <signed $diff> (<pct>%)
```

Note the label change — `Your price vs non-CPO median` in Layout A becomes
`Your price vs all-<PRIMARY> median` in Layout B, because there is no non-CPO
carve-out to compare against. The diff is computed against `primary.stats.median`
in Layout B, against `primary_non_cpo.stats.median` in Layout A.

This block answers "am I priced right against dealers like mine?" — strips
out the cross-channel noise (franchise CPO comps polluting an independent
non-CPO subject's read, etc.).

---

## Outliers  (OPTIONAL — when outliers list non-empty)

```
| VIN | Dealer | Price | z-score |
|-----|--------|-------|---------|
| <VIN>    | <Dealer> | $<price> | <z>   |
```

A listing is an outlier when `|price − mean| > 2 × stddev`. These are
surfaced so the reader can decide whether to discard them from the mental
model (salvage titles, stripped down high-miles, exotic trims, data-quality
artifacts).

### Stale-ref-price annotation  (always render alongside Outliers)

The `Price Change` column derives off `ref_price`. When `ref_price` is a
multi-year-old MSRP/sticker rather than a recent dealer-set reference, the
derived drop figure can be a 50–60% number that misleads. Annotation rule,
**DOM-gated** to avoid false positives on legitimate big drops on heavily-aged
inventory:

- **Soft note** (`⚠ verify`): when `|change_pct| > 25%`. Append to the Price
  Change cell. Add a one-line note in the Outliers explanation: *"Large
  reported drop — verify whether `ref_price` is recent or carries a
  multi-year-old reference."*
- **Hard flag** (`⚠ stale ref`): when **both** `|change_pct| > 25%` **AND**
  the listing's `dom_active <= fresh_max_days` (i.e. the unit was *just listed*
  yet shows a large historical drop — strong signal the reference price is
  from a prior listing era, not a current cut). A fresh listing showing a
  −30% drop is overwhelmingly likely a stale reference; an aged listing
  showing the same may be a real cut.
- **Skip** when `|change_pct| ≤ 25%` regardless of DOM.

The 25% threshold and the DOM gate are tunable; centralise in a
`comp_stats.STALE_REF_THRESHOLDS` constant if this rule moves into the
script later.

---

## Data Quality Notes  (OPTIONAL — only when the event log is non-empty)

Render as a compact bulleted list with typed prefixes `(a)` through `(g)`
that match SKILL.md's Data Quality event log taxonomy. The typed prefix is
**required** (H15) — without it the audit log is only prose, not machine-
readable, and a reviewer can't skim which category an event belongs to.

```
Data Quality Notes
- (a) MCP tool <tool_name> returned <error_type>; recovery: <path>.
  Follow-up: if the tool is failing repeatedly, surface the error_type so the user can escalate — do not hide recurring failures.
- (a1) Facet-discovery retry: <original> → <resolved> on <tool_name>.
  Follow-up: consider correcting the source of the stale casing (profile, prior user input) so the retry isn't needed next session.
- (b) Truncation envelope for <tool_name> unwrapped via --file.
  No follow-up needed — standard recovery path.
- (c) Subject VIN found at <dealer_name> (<distance> mi) — shadow listing excluded from comp_stats.
  Follow-up: confirm with <dealer_name> whether this is a legitimate consignment/wholesale listing or stale data. Shadow listings mean the subject unit is visible in the local market at two dealers, which can suppress search ranking and dealer-level differentiation.
- (d) Filtered: self_vin_match=<n>, exclude_vin_match=<n>, invalid_price=<n>.
  Follow-up: no action unless exclude_vin_match > 0 and came from W3 history-hop — review those VINs to ensure the exclusion was intended.
- (e) Fallback source: <stat> derived from <secondary source> because <reason>.
  Follow-up: flag the affected stat as <fallback-source>-derived in Key Signals when it materially affects the verdict.
- (f) Parameter adaptation: passed <used> in place of <preferred>.
  Follow-up: none unless the adaptation recurs across runs — then update the call-shape spec to name the working parameter.
- (g) Workflow branch skipped by design: <branch_name> — <reason>.
  No follow-up — this event documents a deliberate branch skip for the audit trail.
```

If the event log is empty, **omit this section entirely** — do not render
an empty header. The Follow-up lines are prescribed guidance — render them
verbatim under each event that fires. The reader benefits from seeing the
"what next" alongside the event itself.

---

## Key Signals  (always — 3 to 5 bullets)

Short, punchy bullets that highlight the non-obvious takeaways. Examples:

```
- 40% of local <trim> listings have cut their price in the last 14 days — market is softening.
- Your dealer_type peers median $1,400 lower than the overall median; CPO premium is carrying cross-channel comps up.
- 3 same-brand franchise dealers within 20mi all raised their prices in the last week — watch for a macro signal.
- Sold-90d median and active quartile verdicts disagree: sold says At Market, actives say Modestly Above. Prefer sold anchor.
- Your mileage is 32% under the local median — lean into that in the listing copy.
```

Rules:
- **Surface a sold-vs-quartile disagreement** as one of the bullets when `verdicts_disagree == true`.
- **Surface a CPO-premium alert** when CPO premium is net-negative after certification cost.
- **Surface an MoS alert** when MoS > 4 (heavy supply, weaker pricing power) or < 1.5 (tight supply, room to hold price).
- **Surface a mileage modest-tier bullet** when `mileage_moat.tier == "modest"` (subject is 10–20% under the comp median miles, below the moat cutoff). Template: *"Mileage is <delta_pct>% under the local comp median (<median_comp_miles> mi) — worth mentioning in listing copy, though not a marquee differentiator."* The Headline does NOT get a moat phrase for the modest tier (that's reserved for `tier == "moat"` at ≥20% under median). For `tier == "none"`, surface no mileage signal at all.

---

## Sold-anchor verdict reference  (read before rendering the Verdict block)

When `verdict_source == "sold_anchor"`, the band is determined by
`gap = (user_price − sold_median) / sold_median`. Mirror of
`SOLD_ANCHOR_THRESHOLDS` in `scripts/comp_stats.py` lines 54–61:

| Band                     | Gap range            |
|--------------------------|----------------------|
| Below Market             | gap ≤ −8%            |
| Modestly Below Market    | −8% < gap ≤ −3%      |
| At Market                | −3% < gap < +3%      |
| Modestly Above Market    | +3% ≤ gap < +8%      |
| Above Market             | gap ≥ +8%            |

**Bypass-only rule.** When `comp_stats.py` did NOT run for this report (see
self-check item 13), classify the verdict using this table verbatim — do not
invent a band from prose like "you're below the median by some non-trivial
amount." A −2.6% gap is **At Market**, not Modestly Below; a −3.1% gap is
**Modestly Below**, not At Market. The boundary is exact.

Quartile-anchor verdicts (`verdict_source == "quartile"`) use IQR-extension
fences from `comp_stats.py` lines 261–296: `< p25 − 1.5·IQR` Below;
`[p25 − 1.5·IQR, p25)` Modestly Below; `[p25, p75]` At Market;
`(p75, p75 + 1.5·IQR]` Modestly Above; `> p75 + 1.5·IQR` Above.

---

## Verdict & Recommended Action  (W1 only — always when user_price present; W2 has its own verdict logic in `assets/w2-output-template.md`)

One sentence naming the verdict, the anchor source, and the recommended action:

```
VERDICT: <verdict>.
Anchored on <anchor_source>.
RECOMMENDED ACTION: <action sentence with dollar amount and expected DOM-to-sell impact>.
```

Anchor source phrasing:
- `verdict_source == "sold_anchor"` → `"<sold_count_90d>-unit sold-90d trim median of $<sold_median, gap rendered with the same 2dp-near-edges rule as the Headline>"`
- `verdict_source == "quartile"` → `"<n>-comp active-listing quartile distribution"`

**Field-source labeling for `sold_dom_median`.** The value comes from one of
two server-aggregate paths, exposed via `sold_dom_field`:

- `"dom_active"` (PRIMARY) — current-listing time-to-sell. Use the *"median
  days-to-sell"* phrasing verbatim in the templates below.
- `"dom"` (FALLBACK) — lifetime cross-dealer DOM. Substitute the *"median
  lifetime DOM"* phrasing and add a cross-dealer caveat — e.g. *"Local
  sold-90d median lifetime DOM: `<sold_dom_median>` days (cross-dealer
  accumulator; current-listing time-to-sell on a fresh listing is typically
  lower — upstream did not support `stats=dom_active` for this query, see
  DQ event)."* Surface the field-source mismatch as a Data Quality Notes
  event (e).
- `null` — call degraded entirely; drop DOM phrasing, fall back to
  aging-threshold language.

Recommended-action phrasing (one of). **All DOM-related claims use
`sold_dom_median` from `comp_stats` output (sourced from W1 step 7c —
`stats.dom_active.median` PRIMARY or `stats.dom.median` FALLBACK on
`search_past_90_days`). Never invent days-to-sell predictions — if
`sold_dom_median` is null, drop the DOM clause and phrase in aging-threshold
terms instead.**

- Below Market: `"Raise to $<target> to capture ~$<gain> margin; local sold-90d comps moved in a median of <sold_dom_median> days at these price bands."`
- Modestly Below Market: `"Hold; you're priced to move. Local sold-90d median days-to-sell: <sold_dom_median>."`
- At Market: `"Hold; your price tracks the anchor. <drops_market_wide_count> of <active_count> local comps (<drop_rate_market_wide*100>%) have cut price recently — monitor."`
- Modestly Above Market: `"Consider a $<cut> adjustment to median. Local sold-90d median days-to-sell is <sold_dom_median>; above-median listings historically run longer."`
- Above Market: `"Cut to at-market ($<target>) or lean into a non-price differentiator (miles, CPO). Current positioning aligns with listings that age past <aging_max_days> days."`

When `sold_dom_median` is null (step 7c was not run, or the call degraded),
drop the median-days phrasing and fall back to the aging threshold: e.g.
*"aging risk past day <aging_max_days>"*. Never fabricate a specific
days-to-sell number.

### Action selection when `verdicts_disagree == true`

The five default action templates above assume a single anchor. When
`verdicts_disagree == true` (sold-anchor verdict differs from quartile
verdict), **the action follows the sold-anchor verdict** — but the action
phrasing MUST surface the disagreement so the reader can see both reads.

Disagreement phrasing (prepend to the action sentence):
*"Actives say <quartile_verdict> but sold-90d median says <sold_anchor_verdict>
— buyers paid a median of $<sold_median> over the last 90 days. Prefer
sold anchor."*

**Override matrix.** Even when the sold_anchor verdict is Below or Modestly
Below (template defaults → "Hold; you're priced to move"), the action should
shift to a **price raise** when all of these hold:

| Condition | Source |
|---|---|
| `verdicts_disagree == true` | `comp_stats.verdicts_disagree` |
| `mos_tier == "tight"` | `comp_stats.mos_tier` (MoS < 1.5) |
| `marketcheck_predict.net_margin_primary > 0` | `comp_stats.marketcheck_predict` (CPO branch ran AND net margin after cert cost is positive) |
| `user_price < sold_median` | direct compare |

When all four hold, recommend a raise toward `sold_median`:
*"Raise to $<target> (splits the gap to the sold-90d median of $<sold_median>);
tight supply (MoS <mos>) + positive CPO net margin ($<net_margin>) support
moving up. Local sold-90d median days-to-sell: <sold_dom_median>."*

Target: halfway between `user_price` and `sold_median`, rounded to the nearest
$500. This recaptures margin without pushing the unit above where buyers are
actually paying.

When the override matrix does NOT fire, fall back to the default action
template for the sold_anchor verdict — prefixed with the disagreement phrasing
above.

For symmetry: if the sold_anchor verdict is Above or Modestly Above AND
`mos_tier == "heavy"` (MoS ≥ 4), the action should be a sharper cut than the
default template prescribes (aging risk is higher in heavy-supply markets).
Phrase: *"Cut $<cut> toward the sold-90d median; heavy supply (MoS <mos>)
is lengthening time-to-sell on above-median listings."*

**CPO-headroom-on-non-CPO-subject branch.** When the four standard
override-matrix conditions cannot fire (because the CPO branch was skipped —
DQ event g — and `marketcheck_predict.premium_primary` is `None`), but the same-channel data shows
clear CPO peer headroom, a *recommendation to run the CPO-branch price-check*
is the right call. Fires only when **all** of:

| Condition                  | Source                                                                                                    |
|----------------------------|-----------------------------------------------------------------------------------------------------------|
| Subject is non-CPO         | `subject_cpo == false` (profile / user input)                                                             |
| CPO branch was skipped     | `marketcheck_predict.premium_primary is None` AND DQ event (g) `"CPO branch skipped: user stated non-CPO"` was logged |
| Tight supply               | `comp_stats.mos_tier == "tight"` (MoS < 1.5)                                                              |
| Observable CPO headroom    | `channel_stats.primary.cpo_count >= 2` AND (median of CPO comps in the primary channel) − `channel_stats.primary_non_cpo.stats.median` ≥ $2,500. Compute the CPO-comp median client-side from the comps marked `is_certified == True` in the primary channel; do NOT use `marketcheck_predict` (its CPO roles are null in this branch). |

When all four hold, **append** to the default-template action — do not
replace it:

*"Tight supply (MoS `<mos>`) + observed `<PRIMARY>` CPO comp band
$`<low>`–$`<high>` (n=`<cpo_count>`) sits ~$`<headroom>`K above non-CPO peers
($`<non_cpo_median>`). If CPO certification is operationally viable (cert
cost $`<profile.dealer.cpo_certification_cost>`), there is documented peer
headroom; recommend re-running this report with CPO-stated to compute net
margin and a target raise. **Do not name a specific dollar target without a
CPO-branch predict** — peer-comp headroom is not the same as a model-anchored
CPO premium."*

Specifically: do **not** synthesize a "test $X" raise in this branch. Without
`marketcheck_predict.net_margin_primary`, the override matrix's raise-toward-`sold_median`
formula cannot fire safely. The branch's *only* recommendation is "re-run with
CPO-stated."

Rule of thumb: the template actions are the **baseline**. The override matrix
trips when supporting signals (MoS, CPO margin, verdict disagreement) give
data-grounded reason to diverge. Do not diverge from the template without
at least one of the override conditions firing — and always name the
triggering condition in the action sentence so the reader can audit.

---

## Next Steps  (always for W5; OPTIONAL for W4)

A short list of follow-ups the user can take:

```
Next Steps
- Run /price-check <VIN> to size up your own unit against the competitive set shown.
- Provide your unit's asking price and I'll flag which of these drops now undercut you.
- Run /daily-dealer-briefing to turn this into a daily watch.
```

---

## Self-check  (internal — never render as a grid)

The 13-item verification checklist. Run each item silently before returning
the response. Render only the footer (see Render rule at the end).

1. **Profile loaded and confirmed on first line.** `Using profile: ...` was emitted.
2. **Country-routing applied.** US → US tools; UK → UK tools and UK adaptations.
3. **Dual pricing shown** (franchise + independent), with the dealer's `dealer_type` marked PRIMARY. (W1; W2 follows its own self-check in `assets/w2-output-template.md`.)
4. **CPO detection ran.** If detected, both CPO and non-CPO predictions were made and the CPO Premium block rendered.
5. **`car_type` respected** — session value taken from profile; `"both"` halted and asked before any call.
6. **Subject VIN excluded** from the comp set — as a self-comp and as any shadow-listing VIN from history.
7. **MoS filters match** — numerator (active) and denominator (sold 90d) share `{year, make, model, trim, car_type, zip, radius}`.
8. **No `$0` rows** in any rendered table — `price_range="1-*"` + client-side filter.
9. **Percentile direction** — rank follows the standard convention: percentile = % of comps priced **below** the subject. A $1k unit in a $20k market renders `<5th percentile`; the verdict is Below Market. The verdict name must match the anchor.
10. **8-column standard schema** used on every competitive-listing render.
11. **Percentile render state matches comp_stats output** — four-state render: (a) server exact, (b) server approx (`~N` + approx footnote), (c) client bounded (`low–high` + bounded footnote), (d) client exact (`(visible set)` suffix). Driven by `percentile_source`, `percentile_approx`, `percentile_bounded` fields. Price Distribution block header surfaces `stats_source` (`server` / `client`). **N/A when item 13 fails (pipeline bypassed)** — render `~estimate (no pipeline)` on the percentile line and surface the bypass on the self-check footer.
12. **Data Quality event log** — surfaced when non-empty; omitted when empty.
13. **Pipeline executed for the comp-set.** `parse_search.py` (asc + desc), `merge_comps.py`, `build_comp_stats_input.py | comp_stats.py` all ran for the rendered report. If any was skipped, prefix the response with the warning line `⚠ pipeline bypassed; numeric blocks computed by hand — values may diverge from canonical output` and emit a self-check failure entry under item 13. Do NOT silently render hand-computed numeric blocks. **N/A:** when the workflow has no comp set (W3 trade-in history, W4 with `num_found == 0`). **W4 (v1.7.0+):** the canonical pipeline runs (`parse_search` ×6 + `merge_comps` over cheapest-8 + most-expensive-5 + `build_comp_stats_input` + `comp_stats`) — but `build_comp_stats_input` is invoked WITHOUT `--user-price` and WITHOUT `--subject-vin` (both relaxed in v1.7.0 for the no-subject W4 path). When the rendered W4 report omits `Your Price Position` / `Verdict & Recommended Action` blocks, the self-check passes (no subject means no verdict).
14. **Comp set table came from `render_comp_set_table.py`** (v1.5.1+). Verifiable by checking the agent's tool calls for the script invocation. When the script ran cleanly, the footer line includes "comp set rendered via script". When the script was bypassed (script error, manual fallback, or hand-rolled cells), the rendered table **must** carry the `⚠ table renderer bypassed; manual cells may diverge from canonical formatting` prefix and the footer must list this as a `⚠` line. Hand-rolling the 8-col table risks re-implementing parser-supplied formulas — the same class of bug as the v4/v5/v6 ingestion-side hand-merges that motivated `merge_comps.py`. **N/A:** when item 13 fails (pipeline bypassed — no merged.json to render from), or when the workflow has no comp set (W3, W4-empty). **W5 (v1.8.0+):** the Drop table is rendered via `render_comp_set_table.py --mode=9col-drops`. Footer should include "comp set rendered via script (9col-drops)". Additionally, W5 aggregates (drop/raise rate, dealer-grouping, undercut flags, response matrix, axes_used audit trail) come from `aggregate_w5_signals.py` — its invocation and emitted JSON shape are required for W5; bypassing it is the same class of failure as bypassing `comp_stats.py` for W1/W2/W4. When `aggregate_w5_signals.py` was bypassed, prefix W5 output with `⚠ aggregation bypassed; manual computations may diverge from canonical thresholds` and emit the `⚠` line in the footer. **v1.8.1+:** `aggregate_w5_signals.py` output must include `heterogeneity` and `multi_undercut_alert` blocks; their absence indicates a stale aggregator version (re-sync from canonical).

Render rule at response time:

- **All applicable checks pass** → emit a single footer line listing 5–7
  of the items that were exercised, e.g.:
  `✓ Verified: profile, dual pricing, 8-col schema, MoS filters, no $0 rows, percentile direction.`
- **Any check fails** → emit failures only, one per line, prefixed `⚠`,
  with a one-line note on what was corrected or caveated in the output to
  compensate.
- **Never** render N/A items. **Never** render a pass-by-pass checkbox grid.

---

## Render variations — which blocks per workflow

> *W2 is not in this matrix. W2 renders per `assets/w2-output-template.md` — that file is the W2 single-source-of-truth for block structure (per-VIN card + portfolio rollup). This matrix covers W1 / W3 / W4 / W5 only.*

| Block | W1 | W3 | W4 | W5 |
|---|---|---|---|---|
| Decoded Specs | ✓ | ✓ | — (facet-entered YMMT) | — |
| Headline | ✓ | — | ✓ (market headline) | ✓ (competitor-activity headline) |
| Market Snapshot | ✓ | — | ✓ | ✓ (condensed) |
| Price Distribution | ✓ | — | ✓ | — |
| Mileage Distribution | ✓ | — | ✓ | — |
| DOM Distribution | ✓ | — | ✓ | — |
| Your Price Position | ✓ | — | — | — |
| CPO Premium | ✓ (if CPO) | — | — | — |
| Competitive Set table | ✓ (8-col, W1 schema) | — | ✓ (8-col, cheapest+most-expensive) | ✓ (9-col, W5 drop schema via `render_comp_set_table.py --mode=9col-drops`) |
| Same-Channel View | ✓ | — | ✓ (by channel) | — |
| Outliers | ✓ | — | ✓ | — |
| Data Quality Notes | ✓ (if non-empty) | ✓ (if non-empty) | ✓ (if non-empty) | ✓ (if non-empty) |
| Key Signals | ✓ | ✓ | ✓ | ✓ |
| Verdict & Recommended Action | ✓ | — (no verdict on history-only view) | — | — |
| Next Steps | — | ✓ | ✓ (optional) | ✓ (always) |
| Self-check footer | ✓ | ✓ | ✓ | ✓ |
| Price Trajectory (W3-only) | — | ✓ | — | — |
| Cumulative VIN aging (W3-only) | — | ✓ (when ≥1 row has dom_active) | — | — |
| Listing-vs-transaction caveat (W3-only) | — | ✓ (when listing_count ≥ 2) | — | — |
| Dealer-hop dedup source (W3-only) | — | ✓ (always) | — | — |
| Pagination DQ event (W3-only) | — | ✓ (when num_found > listing_count) | — | — |
| CPO history-known-current-unknown caveat (W3-only) | — | ✓ (when cpo_ever True AND current is_certified None) | — | — |
| Drop / Raise / MoS Headline (W5-only) | — | — | — | ✓ (sourced from `aggregate_w5_signals.{drop_count,raise_count,drop_rate,raise_rate,mos}`) |
| Aggressive-Competitor grouping (W5-only) | — | — | — | ✓ (sourced from `aggregate_w5_signals.{inventory_pressure_dealers,deepest_drops}`) |
| Aggressive-Raisers Key Signal (W5-only) | — | — | — | ✓ (when `aggregate_w5_signals.aggressive_raisers` non-empty) |
| Response Matrix with axes_used audit (W5-only) | — | — | — | ✓ (when `aggregate_w5_signals.response_matrix_fired == true`) |
| Heterogeneity Key Signal (W5-only) | — | — | — | ✓ (when `aggregate_w5_signals.heterogeneity.is_heterogeneous`) |
| Multi-undercut alert (W5-only) | — | — | — | ✓ (when `multi_undercut_alert.fired`) |

**W4 footnote (v1.7.0+).** When no subject vehicle is supplied (W4 default),
`comp_stats.py` runs with `user_price=None` / `subject_vin=""` (both flags
relaxed to optional in `build_comp_stats_input.py` v1.7.0). Verdict-block
fields (`verdict`, `verdict_quartile`, `verdict_sold_anchor`, `gap_vs_median`,
`primary_only.diff`) are emitted as `null` and the renderer skips the Your
Price Position + Verdict & Recommended Action blocks accordingly. The
"Same-Channel View" entry for W4 is the **By-Channel Split** block (franchise
vs independent medians side-by-side) sourced directly from W4 step 5.c
(franchise stats-only) and step 5.d (independent stats-only) — server-wide
medians per channel at the model level — NOT the W1-style subject-vs-peer
comparison from `comp_stats.channel_stats` (which is sample-limited to the
13 merged listings).

W3 adds a workflow-specific block — **Price Trajectory** — which is not used
by any other workflow:

```
Price Trajectory
| Date | Dealer | Type | Inv | Price | Miles | DOM | CPO? |
|------|--------|------|-----|-------|-------|-----|------|
| <date> | <dealer> | F/I/— | new/used/— | $<price> | <miles> | <dom> | Y/N/— |
...

Red Flags:
- multi_dealer_churn: vehicle has passed through <dealer_count> dealers
  (provenance: <dealer_id|mixed|dealer_name>; see "Dealer-hop dedup source"
  line below — when source is "dealer_name", append the caveat
  "(name-based count; dealer_id unavailable in history rows — count may be
  inflated by name variations)"; when "mixed", append
  "(mixed coverage; some history rows lack dealer_id and may be name-merged
  or under-merged)")
- sharp_drops: cumulative price drop <cum_change_pct>% over history
  (>= 15.0% threshold; asymmetric — fires only on cumulative drops, not rises)
- decertified: vehicle was CPO in history but current listing is non-CPO
  (fires only when cpo_ever is definitively True AND current listing is
  definitively False — never on absent/unknown)

Cumulative VIN aging: <max(dom_active across listings)> days (max across history)
  (when at least one row has a non-null dom_active; when all are null:
  "Cumulative VIN aging: unavailable (dom_active absent across all history
  rows)" + emit DQ event (e) "fallback source: dom_active server field
  absent")

Prices reflect listing asks across rooftops, not realized sale prices —
a 15% cumulative drop indicates asking-price softening, not buyer-paid
price drops. (Always render when listing_count >= 2.)

Dealer-hop dedup source: <dealer_id | mixed | dealer_name>.
  (Always rendered; sources from parse_history.dealer_count_source.)
```

**Inv column** — render each row based on the listing's `inventory_type`
value from `parse_history.py`:
- `"new"` → `new`
- `"used"` → `used`
- absent / null → `—`

A row going from `new → used` (e.g., demo / loaner / lease return
conversion) is a non-trivial trade-in signal — when the trajectory shows
this transition, surface as a Key Signals bullet *"Inventory type
transitioned `new → used` between listings — vehicle was previously
demo / loaner / lease unit."*

**Type column** — render each row based on `parse_history.dealer_type` if
present (currently absent on history rows since `get_car_history` does not
return dealer type metadata): `F` / `I` / `—`. Default to `—` for W3 since
the field is generally absent.

**CPO? column tri-state rule** — render each row based on the listing's
`is_certified` value from `parse_history.py`:
- `is_certified == True`  → `Y` (confirmed CPO)
- `is_certified == False` → `N` (explicitly non-CPO)
- `is_certified is None`  → `—` (unknown — the field was absent on this
  row's source response; common on real `get_car_history` responses)

Never default `None` to `N`. "We don't know" is a legitimate — and honest
— render state for this column.

When `cpo_ever is None` (no history row carries `is_certified` at all),
render a caveat below the table: *"CPO history signal unavailable for this
VIN — confirm CPO status with the user before pricing."* The `decertified`
red flag does NOT fire in this case.

When `cpo_ever is True AND current.is_certified is None` (vehicle WAS
CPO at one or more historical listings, but the current listing's
`is_certified` field is absent), render a caveat below the table:
*"⚠ This vehicle was CPO at one or more historical listings; the current
listing's CPO status is unknown — confirm with the seller before pricing."*
The `decertified` red flag does NOT fire in this case (current is None,
not explicitly False — "unknown" is not "confirmed non-CPO").

**Pagination DQ event** — when `parse_history.num_found > listing_count`,
render under Data Quality Notes: *"(b) History pagination gap: `num_found=<N>`
exceeds `listing_count=<n>` — first page shown; cumulative-change and
dealer-hop counts reflect partial coverage."* Also surface as a Key Signals
bullet warning the user that flag accuracy degrades when coverage is partial.

**Cum-change baseline-shift DQ event** — when
`parse_history.dropped_null_price_count > 0`, render under Data Quality
Notes: *"(e) Fallback source: `cum_change_pct` baseline shifted from oldest
history row to oldest priced row (`<n>` rows had null prices)."*

**Render rules — read directly from parser output, do NOT recompute:**
- Trajectory rows: source from `parse_history.listings[*]` (already sorted
  desc by `(last_seen, first_seen)`); render the order as emitted.
- `dealer_count`, `dealer_count_source`: read from parser, render verbatim.
- `cum_change_pct`: read from parser; format with one decimal (e.g.,
  `21.4%`). Sign convention: positive = cumulative drop, negative = rise.
- Cumulative VIN aging: compute `max(parse_history.listings[*].dom_active)`
  across rows where the field is non-null; render the integer value.
- Pagination gap: integer comparison `num_found > listing_count`.
- Baseline-shift count: read `dropped_null_price_count` from parser.

Any divergence between rendered values and parser-emitted values indicates
a render-time recompute, which is the same class of bug the v1.5.1
rendering-fix patched in W1.

---

## Money format

- US profiles: `$` prefix, comma thousands, no decimals. `$28,500`.
- UK profiles: `£` prefix, comma thousands, no decimals. `£18,250`.
- Percentages: one decimal in the report body. **Two decimals in the Headline and Verdict block when `|gap|` falls within 0.5% of any sold-anchor band boundary** (−8%, −3%, +3%, +8%). Avoids visual ambiguity at the band edges: a `−2.6%` rendering hides whether the underlying number is −2.55% (At Market) or −2.65% (still At Market by ±3% rule). At 2dp, `−2.63%` is unambiguously inside the At-Market band. Examples: `+3.2%`, `−8.4%` in body; `−2.63%` in the Headline when gap is at −2.633%.
- Miles: comma thousands, no unit needed inside the Miles column; suffix ` mi`
  elsewhere in narrative prose. `32,100` in the table; `32,100 mi` in the
  Market Snapshot.

## Unsupported countries

**CA (Canada):** Not supported by this skill. `scripts/load_profile.py`
normalises CA profile fields (postcode, province) but the MCP tool surface
is US-centric (`search_active_cars` + `predict_price_with_comparables` +
`get_sold_summary` all presume US market data). The skill's `Before you
start` country routing halts on `country == "CA"` with a user-facing
message rather than producing misleading cross-border results. Revisit when
the MCP surface extends to Canadian market data.

---

## W5 render spec (Competitor Price Movement)

**v1.8.0+** — W5 is now scripted end-to-end. Aggregations come from
`aggregate_w5_signals.py` (deterministic dealer grouping, undercut detection,
8-axis decision algorithm). The Drop table comes from
`render_comp_set_table.py --mode=9col-drops`. No LLM-side hand-rolling on
any aggregate, threshold, or rendered cell.

W5 has a distinct block order vs. W1/W2/W4. Top-to-bottom:

1. **Headline (W5-specific, market-summary form)** — sourced from
   `aggregate_w5_signals` output: `<n_active>-comp local market for <year>
   <make> <model>[ <trim>]: <drop_count> drops (<drop_rate*100>%),
   <raise_count> raises (<raise_rate*100>%), MoS <mos>`. When `mos` is null
   (sold-90d call failed or returned 0), omit the `, MoS <mos>` clause. When
   trim is absent (W5 model-level mode), append `(model-level, all trims)`
   to the scope.
2. **Condensed Market Snapshot** — active count, price min, max, median,
   mean, stddev, drop rate, raise rate, MoS. Sourced from
   `parse_search(step3).stats.price` + `aggregate_w5_signals.{drop_rate,
   raise_rate, mos}`. No State Baseline (usually off-scope; `get_sold_summary`
   not fired in W5).
3. **Aggressive-Competitor grouping** — leads the answer. Reads
   `aggregate_w5_signals.inventory_pressure_dealers` first (dealers with 3+
   drops in the top-20 — flagged "inventory pressure"); otherwise surface
   the top `DEEPEST_CUTS_MAX` (5) individual deepest drops from
   `aggregate_w5_signals.deepest_drops`. Render each dealer with their
   `drop_count` + `drop_total_$`.
4. **Drop table (9-col)** — rendered via `render_comp_set_table.py --mode=9col-drops`:
   `Dealer | Type | Old Price | New Price | Drop $ | Drop % | Miles | DOM | Distance`.
   Source: parse_search step1 listings (sorted deepest-first per
   `sort_by="price_change_percent" sort_order="asc"` per W5 reference). The
   renderer computes Old Price = `price − price_change_amount`, Drop $ =
   `−price_change_amount` (positive magnitude), Drop % = `−price_change_percent`.
   Rows with `price_change_percent == 0` render old/drop as `—` and sort
   to the bottom; footnote appended automatically by the renderer.
5. **Aggressive-Raisers Key Signal** (W5-only, when
   `aggregate_w5_signals.aggressive_raisers` is non-empty) — surface as a
   Key Signal bullet: *"⚠ N dealers raised price >10%: `<dealer list>`;
   raises >10% are frequently data corrections rather than strategic moves."*
   (L3 fix.) Step 2 raises do NOT render their own table.
6. **Undercut list + Response Matrix** (only when
   `aggregate_w5_signals.response_matrix_fired == true`, i.e., user supplied
   `--user-reference-price`). Reads `aggregate_w5_signals.undercut_flags[]`.
   Each undercut row renders:
   ```
   <dealer_name> at $<competitor_price> (<distance_mi> mi away):
     gap <raw_gap_pct>% (adjusted <adjusted_gap_pct>%), DOM <competitor_dom_active>
     Recommendation: <HOLD | SPLIT | MATCH | MATCH-AGGRESSIVE>
     Reason: <reason>
     Suggested price: $<suggested_price>  (or "—" when HOLD)
     [Audit: axes_used = <comma-separated list>]
   ```
   The `axes_used` audit line is rendered as a small caveat at the bottom
   of each row (markdown footnote or italicized) — lets the reader see which
   inputs informed each recommendation.
7. **Key Signals** — 3–5 bullets. Always include the Aggressive-Raisers
   bullet from item 5 when applicable. Other bullets surface tight-market
   (when MoS < 1.5), inventory-pressure dealers (when count > 0), broad
   market pressure (when drop_count > X), and similar pattern signals.

   **v1.8.1+ — three additional Key Signals (W5-only):**

   ```
   ⚠ Heterogeneous comp set: drop scan returned <N> drivetrains
     (<list>), <M> fuel types (<list>), <K> body types (<list>).
     Aggregate signals (drop rate, dealer grouping, deepest drops) span
     variants. For variant-specific intelligence, supply
     --user-reference-vin <V> (decodes to drivetrain/fuel_type filters).
     Source: aggregate_w5_signals.heterogeneity.

   📊 Multi-undercut market pressure: <count> dealers priced 5%+ below your
      reference (median gap <pct>%). Recommend uniform price review across
      affected lot, not per-dealer chase.
      Source: aggregate_w5_signals.multi_undercut_alert.

   ℹ️ Year inferred: filtering on last 3 model years (<min>-<max>); supply
      explicit year for trim-tight intelligence.
      Source: aggregate_w5_signals.year_range_inferred.
   ```

   Heterogeneity bullet fires when `aggregate_w5_signals.heterogeneity.is_heterogeneous == true`.
   Multi-undercut bullet fires when `multi_undercut_alert.fired == true`.
   Year-inferred bullet fires when `year_range_inferred == true`.
8. **Next Steps** — always include for W5. Suggest `/price-check <VIN>`
   for per-unit pricing, or `/market-distribution` (W4) for broader market
   context.
9. **Self-check footer** — per shared template's items 1–14. Item 14's W5
   clause confirms the Drop table came from `render_comp_set_table.py
   --mode=9col-drops`; emit a `⚠` line if the script was bypassed.

Block ordering matters for this workflow because the reader's primary
question is "who moved?", not "am I priced right?". The aggressive-
competitor grouping leads so the punchline hits above the fold.

**Algorithm transparency.** The match/split/hold recommendation is
*deterministic* — same inputs always produce same recommendation. The
`axes_used` field per undercut row records which axes informed each
decision (raw_gap_pct, adjusted_gap_pct, cpo_adjustment_pct,
mileage_delta_pct, dom_delta, mos, competitor_dom_active,
competitor_in_pressure, user_cost_floor). Tunable via constants in
`scripts/aggregate_w5_signals.py` — see module docstring for rationale.
