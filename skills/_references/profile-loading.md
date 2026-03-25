# Profile Loading Procedure

## Read Profile

1. Read the `marketcheck-profile.md` project memory file
2. The file has YAML frontmatter (`---` delimiters) followed by raw JSON — parse the JSON after the frontmatter

## Extract Fields by User Type

### Dealer / Dealership Group
| Field | JSON Path | Notes |
|-------|-----------|-------|
| `dealer_id` | `dealer.dealer_id` | Required for lot-level queries; if null, ask |
| `dealer_name` | `dealer.name` | |
| `dealer_type` | `dealer.dealer_type` | `franchise` or `independent` |
| `franchise_brands` | `dealer.franchise_brands` | Array; may be empty for independents |
| `cpo_program` | `dealer.cpo_program` | Boolean |
| `cpo_certification_cost` | `dealer.cpo_certification_cost` | Dollar amount |
| `zip` / `postcode` | `location.zip` (US) / `location.postcode` (UK) | |
| `state` / `region` | `location.state` (US) / `location.region` (UK) | |
| `country` | `location.country` | `US` or `UK` |
| `radius` | `preferences.default_radius_miles` | Default: 50 |
| `target_margin` | `preferences.target_margin_pct` | Default: 15% |
| `recon_cost` | `preferences.recon_cost_estimate` | Default: $1,500 |
| `floor_plan_per_day` | `preferences.floor_plan_cost_per_day` | Default: $35 |
| `max_dom` | `preferences.max_acceptable_dom` | Default: 45 days |
| `aging_threshold` | `preferences.dom_aging_threshold` | Default: 60 days |

### Dealer Group (additional)
| Field | JSON Path | Notes |
|-------|-----------|-------|
| `locations[]` | `dealer_group.locations` | Array of `{dealer_id, name, zip, state, dealer_type, country}` |
| `group_name` | `dealer_group.name` | |
| `ticker` | `dealer_group.ticker` | For public groups |

### Analyst
| Field | JSON Path |
|-------|-----------|
| `tracked_tickers` | `analyst.tracked_tickers` |
| `focus_area` | `analyst.focus_area` |
| `benchmark_period` | `analyst.benchmark_period` |

### Manufacturer
| Field | JSON Path |
|-------|-----------|
| `brand` | `manufacturer.brand` |
| `competitive_set` | `manufacturer.competitive_set` |
| `regional_focus` | `manufacturer.regional_focus` |

### Lender
| Field | JSON Path |
|-------|-----------|
| `portfolio_focus` | `lender.portfolio_focus` |
| `ltv_thresholds` | `lender.ltv_thresholds` |
| `tracked_segments` | `lender.tracked_segments` |

### Appraiser
| Field | JSON Path |
|-------|-----------|
| `specialization` | `appraiser.specialization` |

### Insurer
| Field | JSON Path |
|-------|-----------|
| `role` | `insurer.role` |
| `claim_types` | `insurer.claim_types` |

## Missing Profile

If `marketcheck-profile.md` does not exist:
- Tell user: "No profile found. Run `/onboarding` to set up your profile once."
- For skills that can work without a profile (appraiser, depreciation-tracker), ask for minimum fields (ZIP, radius) to proceed with this one request
- For skills that require `dealer_id` (daily-briefing, weekly-review, aging alerts), stop and require onboarding

## Confirmation

If profile loaded successfully, confirm briefly: "Using profile: **[name]**, [ZIP/Postcode], [Country]"
Do NOT enumerate every loaded field — just the identity confirmation.
