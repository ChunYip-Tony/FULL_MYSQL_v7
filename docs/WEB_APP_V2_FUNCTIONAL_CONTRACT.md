# FULL MYSQL Web App V2 Functional Contract

Status: DESIGN BASELINE — DO NOT IMPLEMENT LEGACY MODULE NAVIGATION
Date: 2026-09-28

## 1. Product boundary

Web App V2 has three top-level main functions:

1. CORE
2. PI (Physical Inventory)
3. PERFORMANCE

CORE is the single-item / family navigation and analysis path:
Search -> Search Results -> Family Article / UPC -> Price / Ordering Analysis.

PI is the inventory-count adjustment path. It lets the user locate an inventory owner, enter True Stock, make True Stock immediately authoritative for Effective OH, and record the inventory discrepancy lineage.

Do not make legacy Quick Check, Dumping, Price Change, Admin, Work Queue, or More separate top-level modules.

There is no Web App price-change save/approval workflow and no order save/submit workflow. PI is intentionally write-capable because entering True Stock changes the active inventory reference.

## 2. Global completed-data-day rule

All historical sales, velocity, ranking, trend, promotion, and forecast baseline calculations use completed canonical data-supported dates only.

- A calendar date with no valid source data is ignored completely. It is not a zero.
- A completed canonical POS data date with a complete source snapshot is a valid denominator day.
- On such a valid POS data date, if a UPC has no sales row, that is a genuine zero-sales day for that UPC.
- Today/intraday data is excluded from completed-day historical metrics.
- 7D means latest 7 completed canonical POS data dates.
- 28D means latest 28 completed canonical POS data dates.
- If fewer than the requested supported dates exist, expose actual supported-day count and do not pretend the metric has full 7D/28D coverage.
- Price-vs-sales charts must leave missing-source dates as gaps, never plot them as zero.

### 2.1 Global Ordering OH rule

For every ordering-related calculation in both CORE and the main ORDERING function:

Ordering OH = max(Current Effective OH, 0).

- If Current Effective OH is negative, retain and display the real negative value as an inventory warning.
- Use 0, not the negative number, for DOS eligibility, projected OH, forecast consumption coverage, and suggested order quantity.
- Never let a negative OH artificially increase the suggested order beyond the quantity needed from a zero-stock starting point.
- Example: Effective OH = -18 LB -> Ordering OH Used = 0 LB.
- This rule does not relax UOM requirements. Unresolved/incompatible UOM remains blocked/review rather than guessed.

## 3. Search

Input accepts:
- item name / alias
- Family Article number
- Article / Receiving-Ordering number
- UPC / EAN

Search result entity types:
- FAMILY
- UPC
- RECEIVING_ARTICLE redirect/reference when applicable

Ranking:
1. 28-supported-day sold quantity descending
2. readiness
3. relevance as a tie-breaker

Relevance priority:
1. exact UPC/EAN
2. exact Family Article / Article number
3. exact normalized name/alias
4. prefix name match
5. token/keyword match

Readiness priority:
READY before QA_HOLD / incomplete / historical-only.

28D quantity:
- UPC: latest 28 completed canonical POS data dates.
- Family: aggregate related UPC demand only when quantities can be expressed in one confirmed family operational UOM without double counting. Otherwise use canonical family movement when it is the authoritative comparable family quantity. If neither is safe, Family 28D Qty is unavailable rather than inferred.

Search result displays:
- name
- entity type
- number
- category LIVE/FRESH/FROZEN
- readiness
- 28-supported-day qty sold + UOM
- supported-day count when fewer than 28

## 4. Family Article page

Display:
- Family Article Number
- Family Article Name
- Category: LIVE / FRESH / FROZEN
- Receiving / Ordering Article number(s)
- Current Effective OH + UOM
- Observed Delivery Days
- Observed Delivery Frequency
- Last Receipt Date
- Last Receipt Quantity + Receiving UOM
- Last Receipt Cost + Cost UOM
- Next Expected Delivery Date
- Related UPCs

### 4.1 Family Effective OH

Never sum duplicate inventory ownership.

Inventory aggregation must identify unique stock owners first:
- UPC-owned OH
- Article-owned OH
- Family-owned OH

If one Family/Article OH is shared by multiple UPCs, count it once.
Do not combine incompatible UOMs without an explicit confirmed conversion.
If safe family aggregation cannot be proven, show OH unavailable/blocked with reason.

True Stock remains authoritative for its inventory owner until superseded by a later accepted OH upload.

### 4.2 Receiving / Ordering Articles

Use confirmed product identity relationships where available.
Also expose observed receiving article numbers from canonical receipt history.
If multiple active receiving articles exist, show them; do not force one inferred master.

### 4.3 Canonical receipt event

Receipt evidence types: 101, 107, 109.
Avoid counting stages of the same receipt more than once.

For receipt-event quantity:
- prefer physical receipt-stage 101 or 107 evidence;
- 109 is fallback when no matching 101/107 receipt-stage evidence exists;
- retain document/PO/raw lineage;
- 107 is receipt evidence only and does not add unrestricted OH.

Group related receipt rows by strongest available receipt identity:
purchase order / article document + article + posting context.

Last receipt quantity and last receipt cost must preserve their actual UOM. Do not silently convert.

### 4.4 Observed delivery pattern

Derive from canonical completed receipt events, not from manually assumed policy.

Use recent canonical receipt history, preferring at least 6 events when available.

Output:
- observed weekday(s)
- observed delivery frequency
- confidence
- evidence event count
- recent receipt dates

Suggested classification:
- WEEKLY: approximately one recurring receipt per week on a stable weekday pattern
- MULTIPLE_PER_WEEK: stable recurring multiple weekdays
- IRREGULAR: no stable cadence
- INSUFFICIENT_HISTORY: not enough evidence

Next Expected Delivery:
- calculate only when cadence is sufficiently stable;
- project the next observed cadence occurrence after the reference/order date;
- otherwise return Uncertain / unavailable;
- always label this as observed expectation, not a guaranteed vendor schedule.

## 5. Related UPCs on Family page

Sort:
1. READY first
2. 28-supported-day Qty Sold descending

Display per UPC:
- UPC name
- UPC number
- readiness
- current price
- current price type
- 7-supported-day Qty Sold + UOM
- 28-supported-day Qty Sold + UOM

Selecting a UPC opens the UPC page.

## 6. UPC page

Display:
- UPC number
- UPC name
- Category LIVE/FRESH/FROZEN
- readiness

Primary navigation buttons only:
1. Family Article
2. Price
3. Ordering

No save/submit workflow from this page.

## 7. Price page

Analysis only. No Save Price Change / Proposal / Approve / Execute.

Display current:
- price
- price type
- price as-of
- cost + UOM
- cost date/source
- GP%
- GP$/supported day

Sales:
- 7-supported-day Qty
- 28-supported-day Qty
- 7-supported-day velocity
- 28-supported-day velocity

Price references:
- Sweet Spot
- WGPM
- Company A/B/C

### 7.1 Price vs Sales Trend

Show only the latest 7 completed canonical supported sales dates in the visual trend.

Rules:
- use completed canonical POS data dates only;
- missing source dates are gaps;
- valid POS dates with no UPC movement are true zero-sales dates;
- show price type per date/period;
- SALE must be visually distinguishable;
- TPR is not Promotion.

### 7.2 14-supported-day sales history

Below the 7-day graph, show the latest 14 completed supported sales dates with:
- weekday + date
- sales dollars
- sold quantity
- average sold price
- price type(s)

Missing source dates are skipped and never displayed as zero-data dates.

## 8. Promotion definition

Promotion = price type SALE only.

Explicitly:
- SALE = Promotion
- TPR != Promotion
- other non-SALE price types are not Promotion unless a future explicit business rule says otherwise.

Legacy logic that classifies TPR as promotion must not be reused in V2.

### 8.1 Historical promotion periods

Historical promotion periods are observed from SALE evidence.

Classify when evidence supports:
- WEEKEND_PROMOTION: Friday through Sunday
- WEEKLY_PROMOTION: Thursday through the following Friday
- OTHER_SALE
- UNCERTAIN when continuity/boundaries are not sufficiently supported

Display:
- Promotion Type
- Start Date
- End Date
- SALE Price
- Calendar Duration
- Data-Supported SALE Days
- Qty Sold on supported SALE days
- Avg SALE Qty / supported day
- data coverage, e.g. 8/9 supported days

Do not treat missing-source dates inside a promotion as zero sales.
Do not claim continuity across missing dates unless price/source evidence supports the calendar boundaries.

## 9. CORE -> Ordering page

CORE Ordering is a Family Article decision reached from the selected UPC. The UPC is the navigation context; demand, Effective OH, promotion history, delivery cadence, DOS, forecast usage, and Suggested Order Qty are calculated at the Family Article level. No Save Order / Final Order / Submit.

Inputs:
- Ordering Date — default current date
- Expected Delivery Date — default observed next expected delivery date
- Regular or Promotion Involved
- if Promotion:
  - Promotion Type (observed/recommended or manual)
  - Promotion Start Date
  - Promotion End Date
  - Promotion Price

No Sales Event input.

Default Next Next Delivery Date:
- derived from observed delivery cadence after Expected Delivery Date;
- user-visible;
- if cadence is uncertain, ordering suggestion must be blocked or require user date input rather than guessed.

### 9.1 Ordering inventory inputs

Display:
- Current Effective OH + UOM
- OH source
- 7-supported-day Qty / velocity
- 28-supported-day Qty / velocity
- DOS
- DOH for Fresh/Live when applicable
- Last Receipt Date
- Last Receipt Qty + UOM
- Last Receipt Cost + UOM
- Observed Delivery Days/Frequency
- Expected Delivery
- Next Next Delivery

### 9.2 Regular demand baseline

Use completed canonical POS data dates only.

Regular baseline excludes SALE dates.
TPR remains eligible as regular/non-promotion demand because TPR is not Promotion.

Baseline should consider:
- recent 7 supported regular days
- recent 28 supported regular days
- recent trend
- weekday behavior when enough history exists

Do not fill missing source dates with zeros.

### 9.3 Promotion demand forecast

Use historical SALE periods only.

Priority:
1. same UPC
2. same promotion type (Weekend vs Weekly)
3. similar SALE price / discount
4. recent history
5. stronger supported-day coverage

Show evidence:
- historical SALE velocity
- regular baseline
- observed uplift
- supported-day counts
- confidence

Do not multiply independent event factors. There is no Sales Event model in V2.

### 9.4 Ordering quantity calculation

Coverage goal: expected demand from Ordering Date through the day before Next Next Delivery Date.

Break forecast into:
- pre-delivery regular/promotion demand
- post-delivery through next-next-delivery regular/promotion demand

Projected OH at Expected Delivery =
Current Effective OH - forecast usage before Expected Delivery.

Suggested receipt/order qty =
max(0, forecast usage from Ordering Date through day before Next Next Delivery - Current Effective OH)

Default ending-stock target is zero unless a future explicit business rule adds safety stock.

If current OH is forecast to run out before Expected Delivery, show the pre-delivery shortage separately; the arriving order cannot solve a shortage before its delivery date.

Apply only confirmed UOM/order-multiple conversions. Show raw qty and rounded qty separately. Fail closed if UOM conversion is unresolved.

## 10. Main ORDERING function — CANCELLED

The standalone/top-level Main ORDERING function is cancelled and must not appear in Web App V2 navigation or public V2 routes.

Ordering analysis remains available only through CORE -> UPC -> Ordering, where the decision level is Family Article.

## 11. PI (Physical Inventory)

PI is the Family Article physical-inventory workflow.

Search may begin from:
- item name / alias
- Family Article number
- Article / Receiving-Ordering number
- UPC / EAN

Every search result resolves to exactly one Family Article target. PI does not ask the user to count individual selling UPC inventory.

The PI Family page displays:
- Family Article number/name
- category
- Family System OH + UOM
- Family Effective OH + UOM
- OH source
- current signed discrepancy
- last receipt
- recent Family True Stock history

Input:
- Family True Stock quantity
- authoritative Family UOM
- optional note

Rules:
- True Stock must be non-negative.
- A new Family True Stock immediately becomes the Family Effective OH.
- It supersedes any older active Family/Article/UPC True Stock inside that Family so only one physical-count authority remains active.
- It remains authoritative until a later accepted OH upload supersedes it.
- Ordering immediately uses the new Family Effective OH.
- Shortage creates/updates the pending Family discrepancy/dumping record.
- Overage is retained as a positive PI discrepancy; it does not create dumping quantity.
- PI is an operational write function, not an approval workflow.

## 12. V2 UI transition

V2 test UI route: /app/v2.

The existing /app remains available as a fallback while CORE / ORDERING / PI are tested. Do not switch the primary /app route until V2 interaction and data regression testing is complete.

## 13. PERFORMANCE

PERFORMANCE is a read-only analysis and review function.

Category filter:
- ALL
- LIVE
- FRESH
- FROZEN

Report summary includes:
- active UPC count
- 7 / 14 / 28 supported-day sales dollars
- 7D GP dollars
- slowing-item count
- low-GP-item count
- price-review candidate count

The report may generate up to 100 urgent price-review suggestions.

Price-review suggestion rules:
- READY items only
- active SALE items excluded
- minimum 3% difference from current price
- primary objective: maximize observed GP dollars per day using actual historical demand observed at historical price points
- use current cost for candidate comparability
- Company C is a hard bottom-line price floor when available
- urgency list is primarily sorted by estimated GP$/day opportunity
- 7D vs 28D velocity and GP vs category reference remain secondary urgency evidence
- do not invent demand elasticity beyond observed price/demand history
- suggestions are analysis only; there is no Save/Approve/Execute action in Web App V2

## 14. Elder-friendly UI and navigation

UI must prioritize readability and low cognitive load:
- large text and large touch targets
- high contrast
- clear page titles
- key values in large cards
- minimal dense tables
- status conveyed by text/icons as well as color
- no horizontal-scrolling dependency for primary decisions
- three persistent main tabs: CORE / PI / PERFORMANCE

Phone/system Back must move to the previous in-app screen. At the V2 root it must remain inside the app instead of navigating away.

## 15. Implementation guard

Do not redesign runtime UI until these contracts are represented by dedicated V2 API/data outputs.
Do not reuse legacy promotion classification where TPR/IN STORE were labeled promotion.
Do not reuse calendar-day denominators for 7D/28D metrics.


## Elder-friendly UI requirements

The V2 UI must prioritize readability and low cognitive load:
- large body text and large numeric values
- minimum large touch targets for buttons and controls
- high contrast between text, cards, controls, and status
- clear page titles and visible Back controls
- primary actions presented as large buttons
- avoid dense multi-column presentation on phones when not necessary
- key operational values shown in large cards
- status conveyed using text/icons in addition to color
- mobile/system Back remains inside the V2 navigation flow
- top-level navigation contains only CORE / PI / PERFORMANCE


## Performance Report Date contract

PERFORMANCE is anchored to a selected completed canonical supported POS date.

- Report Date defaults to the latest completed supported sales date.
- A manually selected Report Date must itself be a supported canonical sales date; unsupported dates are rejected rather than silently shifted.
- The report shows that date's sales performance separately from rolling trends.
- 7D / 14D / 28D metrics mean the latest 7 / 14 / 28 completed supported sales dates ending on or before Report Date.
- Missing source dates are ignored and never inserted as zero.
- Report Date Top Sellers are ranked from that date's actual sales.
- Performance analysis compares Report Date sales against supported-day rolling baselines.
- Top 100 urgent price suggestions use sales evidence only through Report Date.
- Price suggestions retain Company Price C as a hard floor when applicable.
- Price suggestion priority is positive observed GP$/day opportunity.
- Current authoritative cost is used until historical daily cost lineage is available in the V2 serving layer; this limitation must be disclosed in the report.


## Core Ordering delivery fallback

CORE -> UPC -> Ordering remains a Family Article decision.

Expected Delivery priority:
1. user-entered Expected Delivery Date
2. stable observed delivery pattern
3. FRESH fallback = following Friday
4. FROZEN fallback = following Tuesday
5. other categories remain unresolved unless observed/user-entered

When FRESH/FROZEN delivery is resolved but the next observed delivery cannot be inferred, Next Next Delivery uses a transparent weekly fallback of Expected Delivery + 7 days.

This fallback prevents Core Ordering from failing solely because receipt cadence history is sparse or irregular.
