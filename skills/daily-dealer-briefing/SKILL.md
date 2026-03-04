---
name: daily-dealer-briefing
description: >
  This skill should be used when the user asks for a "daily briefing",
  "morning check", "what needs attention today", "daily pricing check",
  "what's urgent on my lot", "daily dealer report", "start my day",
  "morning report", "daily ops", or needs a quick operational health check
  covering aging inventory and competitor price movements.
version: 0.1.0
---

# Daily Dealer Briefing — Morning Operational Health Check

A 5-minute morning briefing that surfaces the two things a dealer needs to act on immediately: **aging inventory bleeding floor plan** and **competitors who just dropped their prices**.

## Dealer Profile (Load First)

1. Read `~/.claude/marketcheck/dealer-profile.json`
2. If the file **does not exist**: Tell the user: "No dealer profile found. Run `/dealer-onboarding` to set up your dealer context once. The daily briefing needs your dealer ID, ZIP, and preferences to run." Then stop.
3. If the file **exists**, extract:
   - `dealer_id` ← `dealer.dealer_id` (**required** — if null, tell the user to update their profile with a dealer ID)
   - `dealer_name` ← `dealer.name`
   - `dealer_type` ← `dealer.dealer_type`
   - `franchise_brands` ← `dealer.franchise_brands`
   - `zip` or `postcode` ← `location.zip` (US) or `location.postcode` (UK)
   - `state` or `region` ← `location.state` (US) or `location.region` (UK)
   - `country` ← `location.country`
   - `radius` ← `preferences.default_radius_miles`
   - `aging_threshold` ← `preferences.dom_aging_threshold` (default 60)
   - `floor_plan_per_day` ← `preferences.floor_plan_cost_per_day` (default $35)
4. **Tool routing by country:**
   - **US**: `mcp__marketcheck__search_active_cars`, `mcp__marketcheck__predict_price_with_comparables`
   - **UK**: `mcp__marketcheck__search_uk_active_cars`. Price prediction not available — use comp median instead.
5. Confirm: "Running daily briefing for **[dealer_name]**, [ZIP/Postcode]..."

## Step 1: Aging Inventory Alert

Identify units on the dealer's lot that have exceeded the aging threshold.

**US dealers:**

1. Call `mcp__marketcheck__search_active_cars` with:
   - `dealer_id`: from profile
   - `dom_range`: `{aging_threshold}-999` (e.g., `60-999`)
   - `sort_by`: `dom`
   - `sort_order`: `desc`
   - `rows`: `15`
   - `car_type`: `used`

2. For each returned unit (up to 10 highest-DOM), call `mcp__marketcheck__predict_price_with_comparables` with:
   - `vin`: the vehicle's VIN
   - `miles`: the vehicle's listed mileage
   - `zip`: dealer's ZIP
   - `dealer_type`: from profile

3. Calculate for each unit:
   - **Price Gap** = Listed Price - Predicted Market Price
   - **Price Gap %** = (Listed Price - Predicted Price) / Predicted Price × 100
   - **Daily Floor Plan Burn** = floor_plan_per_day
   - **Total Burn to Date** = (DOM - aging_threshold) × floor_plan_per_day

4. Assign action:
   - Price Gap > +10%: **REDUCE NOW** (overpriced and aging)
   - Price Gap +0% to +10% AND DOM > 90: **CONSIDER WHOLESALE**
   - Price Gap < 0%: **PRICED RIGHT — review merchandising** (price isn't the issue)

**UK dealers:**

1. Call `mcp__marketcheck__search_uk_active_cars` with dealer filtering parameters if available, or search by the dealer's web domain. Pull units sorted by DOM descending.

2. For each unit, search for 10 comparable listings (same make/model/year within radius) to calculate the comp median price.

3. Use comp median in place of predicted price for all gap calculations.

4. Note to user: "UK pricing uses comparable listing medians. ML price prediction is available for US dealers."

## Step 2: Competitor Price Drop Alert

Scan for competitors who just dropped their prices on models the dealer sells.

**US dealers:**

1. For each brand in `franchise_brands` (or top 3 makes in the dealer's inventory if independent):

   Call `mcp__marketcheck__search_active_cars` with:
   - `make`: the brand
   - `zip`: dealer's ZIP
   - `radius`: dealer's radius
   - `price_change`: `negative`
   - `sort_by`: `price`
   - `sort_order`: `asc`
   - `rows`: `10`
   - `car_type`: `used`
   - `seller_type`: `dealer`

2. From the results, identify:
   - Number of competitors who dropped prices
   - Group by dealer — dealers with 3+ drops are signaling inventory pressure
   - For each dropped unit, compare the new price to the dealer's own inventory on matching models (if dealer_id is available, cross-reference)

3. Flag **UNDERCUT** alerts: any competitor unit now priced below the dealer's equivalent model.

**UK dealers:**

1. Call `mcp__marketcheck__search_uk_active_cars` with similar filters. Note: `price_change` parameter may not be available for UK — if not supported, skip this step and note: "Competitor price tracking not available for UK market."

## Step 3: Present the Daily Briefing

```
DAILY DEALER BRIEFING — [Dealer Name] — [Today's Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 AGING INVENTORY ([N] units over [threshold] days)

VIN (last 6) | Year Make Model | DOM | Your Price | Market Price | Gap | Action
-------------|-----------------|-----|------------|--------------|-----|--------
[table rows sorted by highest DOM first]

Floor Plan Burn (aged units): ~$[X,XXX] total ($[X]/day ongoing)

🟡 COMPETITOR ALERTS ([N] price drops in your market)

Model | Competitor Dealer | Their New Price | Your Price | Gap | Their DOM
------|-------------------|-----------------|------------|-----|----------
[table rows, UNDERCUT items highlighted]

Aggressive Competitors: [Dealer X] dropped [N] units — possible inventory pressure

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOP 3 ACTIONS TODAY:
1. [Most impactful action — e.g., "Reduce VIN ...X4532 by $2,100 to match market"]
2. [Second action]
3. [Third action]

Estimated impact: $[X,XXX] in floor plan savings + $[X,XXX] in margin recovery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For a full lot scan + stocking analysis, ask for your "weekly review".
```

If there are **no aging units** and **no competitor drops**, say:

```
DAILY DEALER BRIEFING — [Dealer Name] — [Today's Date]

✅ All clear. No units over [threshold]-day threshold. No competitor price drops detected.

Inventory health: [N] total units | Oldest: [X] days | Market: stable
```
