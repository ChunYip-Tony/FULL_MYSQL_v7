# FULL MYSQL Web App V2 Functional Contract

Version: V2 Contract v1
Backend baseline: 7.0.109

## Product boundary

Web App V2 is a read/analysis application.

It does not:
- save price changes,
- submit orders,
- maintain a Work Queue,
- expose an Admin module,
- expose a More module.

Primary navigation:
Search -> Search Results -> Family Article / UPC -> Price or Ordering analysis.

## Global completed-data rule

All 7D, 28D, velocity, trend, and promotion calculations use canonical completed data-supported dates only.

A missing source date:
- is ignored,
- is not inserted as a zero,
- is not included in the velocity denominator.

A canonical supported sales date with no row for the UPC is a supported zero-sale UPC day.

Definitions:
- 7D = latest up to 7 canonical completed supported POS dates.
- 28D = latest up to 28 canonical completed supported POS dates.
- Velocity = quantity / supported day count.
- Coverage count is always exposed.

## Search

Search inputs:
- Item name
- Family Article #
- Article #
- UPC #

Results contain FAMILY and UPC objects.

Sort order:
1. Relevance descending
2. Readiness
3. Qty sold across latest 28 supported completed POS dates descending

Relevance prioritizes:
- exact numeric identity,
- exact name,
- starts-with,
- token/substring match.

Family result 28D quantity is the sum of related UPC 28-supported-day sales quantities.

## Family Article page contract

Required:
- Family Article Number
- Family Article Name
- Category: LIVE / FRESH / FROZEN
- Confirmed related / receiving-ordering Article numbers
- Current Effective OH
- Observed delivery days
- Observed delivery frequency
- Last receipt date
- Last receipt quantity and UOM
- Last receipt cost and UOM
- Next expected delivery date
- Related UPCs

Related UPC sort:
1. Readiness
2. 28-supported-day Qty descending

Related UPC row:
- UPC
- Name
- Current Price
- Current Price Type
- 7D Qty
- 28D Qty
- Readiness

Observed delivery is derived from canonical completed movement receipt dates and is explicitly labeled observed, not contracted.

## UPC page contract

Required:
- UPC
- UPC Name
- Category
- Readiness
- Family Article identity
- 7D and 28D supported-day sales metrics

Actions:
- Family Article
- Price
- Ordering

## Price analysis

Read-only.

Shows:
- Current Price
- Price Type
- Price As Of
- Current Cost / UOM
- Cost Date / Source
- GP%
- GP$/day
- 7D Qty / Velocity
- 28D Qty / Velocity
- Sweet Spot
- WGPM
- Company A/B/C
- Price vs Sales trend
- Historical SALE periods

Price-vs-Sales trend uses supported completed dates only. Missing source dates are gaps, never zeros.

## Promotion definition

Promotion = Price Type SALE only.

TPR is not Promotion.

Historical SALE period classifications:
- WEEKEND = Friday through Sunday, 3 calendar days
- WEEKLY = Thursday through the following Friday, 9 calendar days
- OTHER = all other observed SALE periods

Each historical promotion exposes:
- Promotion Type
- Start / End Date
- Calendar Duration
- Supported Sales Day Count
- SALE Observed Day Count
- Coverage Ratio
- SALE Price
- SALE Qty
- SALE Velocity per supported day
- Coverage Status

Missing source dates inside the calendar period are excluded from quantity/velocity denominators and lower coverage.

## Ordering analysis

Read-only simulation. Nothing is saved or submitted.

Inputs:
- Ordering Date; default current business date
- Expected Delivery Date; default observed expected delivery
- Promotion involved: yes/no
- Promotion Start Date, End Date, SALE Price when applicable

There is no Sales Event input.

Historical regular baseline:
- latest 28 canonical completed supported POS dates,
- SALE days excluded,
- TPR days retained as regular behavior.

Historical promotion baseline:
- SALE only,
- same promotion type first,
- closest SALE price next,
- most recent evidence next.

No matching SALE history:
- no invented uplift,
- promotion dates fall back to regular baseline,
- confidence is explicitly low.

Forecast horizon:
Ordering Date through the day before Next Next Delivery.

Suggested Order Qty:
Forecast Usage Until Next Next Delivery - Current Effective OH,
floored at zero.

Also expose:
- Projected OH at Expected Delivery
- Forecast Usage Before Expected Delivery
- Forecast Usage Until Next Next Delivery
- Daily demand type and basis
- Next Next Delivery
- Promotion evidence / confidence
- Any blockers

No rounding is applied unless an explicit authoritative ordering-unit rule is available.

## Current implementation endpoints

- GET /v1/app/v2/search
- GET /v1/app/v2/family/{family_key}
- GET /v1/app/v2/upc/{upc}
- GET /v1/app/v2/upc/{upc}/price
- GET /v1/app/v2/upc/{upc}/ordering

The current Web App UI is not yet switched to these V2 endpoints.
