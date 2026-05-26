# Profile loading and session values

This document is the **canonical contract** for how `competitive-pricer` reads the appraiser profile, derives session values, and parses free-form user inputs. Every workflow in this skill reads from this contract — do not re-derive inline.

## Source file

Profile lives at `marketcheck-profile.md` as a **project memory file** (per repo-root `CLAUDE.md`). The file has two parts:

1. **YAML frontmatter** (between `---` delimiters) — structured fields.
2. **JSON body** below the frontmatter — the same fields as raw JSON.

Parse the JSON body after the frontmatter. The frontmatter is the human-readable summary; the JSON is authoritative.

## Required fields (appraiser plugin onboarding)

Per `plugins/appraiser/CLAUDE.md`, the appraiser onboarding profile carries the following fields. The schema is intentionally lean — no `dealer_type`, no `cpo_program`, no `cpo_certification_cost`, no `dom_thresholds`.

| Field | Required | Default | Source |
|---|---|---|---|
| `location.country` | yes | — | `"US"` or `"UK"` |
| `location.zip` | yes | — | US ZIP or UK postcode |
| `location.state` | yes (US) | — | 2-letter state code; required for state baseline |
| `specialization` | no | `null` | Free-form (e.g., "luxury", "trade-in", "salvage") — surfaced in render footer for context |
| `default_radius_miles` | no | `75` | The appraiser-plugin onboarding default per CLAUDE.md |
| `minimum_comps` | no | `6` | Thin-market gate; below this count, value range degrades to thin-market block |
| `preferences.default_inventory_type` | no | `"used"` (with caveat) | `"used"`, `"new"`, or `"both"`; see "Inventory-type handling" below |

If `location.country`, `location.zip`, or (for US) `location.state` are missing, **halt and ask** before any MCP call.

If the profile file does not exist, halt with: *"I don't see your appraiser profile. Run `/onboarding` to set up your profile, or supply ZIP + radius inline for this run."*

## Session values (derived once at workflow start)

These values are computed once when the workflow starts. Cache them in your scratchpad for the remainder of the session — never re-derive inline:

- **`radius_mi_clamped`** = `min(default_radius_miles or 75, 100)`. The 100-mile cap is the `search_past_90_days` hard cap. Active-only calls could in principle go further, but enforcing the cap uniformly keeps the active comp set and the sold-90d comp set on the same scope (apples-to-apples).
- **`min_comp_count`** = `minimum_comps or 6`. Drives the thin-market degradation gate AND the sold-anchor / quartile-anchor selection (sold-anchor fires when `sold_count_90d >= min_comp_count`).
- **`country`** = `location.country` (case-sensitive — uppercase per onboarding convention).
- **`state`** = `location.state` if US; not used on UK.
- **`zip`** = `location.zip` (US ZIP / UK postcode).
- **`car_type_resolved`** — see "Inventory-type handling" below.
- **`dom_thresholds`** — defaulted to `{fresh: 30, aging: 60}` since the appraiser plugin doesn't gather them. These drive the Fresh / Aging / Stale buckets in the DOM Distribution block.
- **`specialization_note`** — `specialization` value if present, used as a single-line footer hint (e.g., "Tuned for: luxury") so the appraiser can sanity-check the result against their domain.

## Inventory-type handling

Per `plugins/appraiser/CLAUDE.md`, the appraiser plugin's onboarding fields do not currently include `preferences.default_inventory_type`. Until that field is added (out of scope for this skill — see Out-of-Scope Follow-ups), apply this resolution:

- If `preferences.default_inventory_type` is **present** with value `"used"` or `"new"` → use directly. No caveat.
- If `preferences.default_inventory_type` is **present** with value `"both"` → halt and ask: *"Market context on used or new units?"* Apply the answer for the rest of the session. If the user replies with anything other than `used` or `new`, re-ask once; on a second non-answer, default to `"used"` and emit Data Quality Notes event (f) noting the defaulted value.
- If `preferences.default_inventory_type` is **absent** → default to `"used"` (the appraisal-defensibility default — used-vehicle markets are the primary appraisal surface) and emit Data Quality Notes event (g): *"Inventory-type defaulted to 'used' (no preference in profile)."*

## Free-form price parsing

User-supplied asking prices accept any of:

- `27000`
- `$27000`
- `$27,000`
- `27,000`
- `27k`
- `27K`

Currency symbols (`$`, `£`) and commas are stripped. Trailing `k` or `K` multiplies by 1000. Reject negative or zero values with a halt: *"Asking price must be a positive number. Please supply a value like `$27,000` or `27k`."*

User-supplied mileage accepts plain integers or comma-separated forms (`96619` or `96,619`). Strip commas, reject negatives.

## VIN format validation

Every workflow that accepts a VIN validates it before any MCP call:

```
^[A-HJ-NPR-Z0-9]{17}$
```

Excludes the letters I, O, Q (never used in real VINs). On failure, halt with: *"VIN is malformed (must be 17 chars, no I/O/Q). Please correct and re-run."* — **fire no MCP calls** until the format check passes.

## Country-routing posture

Branch on `country` before any MCP call:

- `country == "US"` → all workflows available (W1 / W2 / W3).
- `country == "UK"` → `references/country-uk.md` is the authoritative shape. UK has no VIN decoder, no ML predictor, no `get_sold_summary`, no `get_car_history`. W2 Trade-In History halts on UK with the documented message.
- `country == "CA"` → halt with: *"Competitive Pricer does not yet support Canada. The skill is US + UK only — contact support if CA workflows are needed."*
- Any other country → halt with the same US-or-UK-only message.

## Confirming the profile

First user-facing line of every render is:

```
Using profile: <appraiser-or-org name if present in profile, else "appraiser">, <ZIP or postcode>, <country>
```

If a name field is not present in the appraiser profile schema, render `Using profile: appraiser, <ZIP>, <country>` and trust the user to recognise their own ZIP.

## Why these defaults

- **`default_radius_miles = 75`** is the appraiser-plugin default per its CLAUDE.md. Appraisers cast a wider net than dealers (50 mi typical) because comparable-citation defensibility prefers more comps over geographic tightness.
- **`minimum_comps = 6`** matches the reference's `min_n = 6` gate. Below 6 comps, percentile / quartile statistics are not stable enough to render as a defensible value range.
- **`dom_thresholds = {fresh: 30, aging: 60}`** matches dealer-side conventions (Fresh = 0–30d, Aging = 31–60d, Stale = 61+d). Appraisers don't typically tune these, so defaults are durable.
