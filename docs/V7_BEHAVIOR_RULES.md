# v7 behavior carried forward from v6.6

- Every workbook tab is read, including hidden tabs when readable.
- RAW remains immutable evidence with batch/file/sheet/row lineage.
- Article Manual verified Main/Sub hierarchy outranks Monthly PI hierarchy observations.
- Selling UPC canonical identity resolves to Main/Family; sub-articles resolve separately to Main/Family.
- `#N/A`, blank, and equivalent missing UOM tokens are missing source values, not UOMs.
- POS Sales and MVT are required daily/backfill sources. Other reports are optional and expected only when a new report exists.
- Rolling POS 7D/30D uses the latest 7/30 valid POS data days, not calendar days.
- A valid uploaded POS day with no record for an UPC is a true zero-sales day for that UPC and remains in the denominator.
- A missing/invalid POS day is NULL/MISSING and is excluded. Missing is never converted to zero.
- MVT rolling windows use valid MVT data days independently.
- POS-vs-MVT reconciliation uses overlapping valid coverage only.
- Backfilled daily sources automatically change affected rolling windows when Phase3 is rebuilt.
- Work/Home v7 clients upload through HTTPS only; MySQL credentials remain server-side.

## Canonical receipt / delivery semantics

- A physical delivery is either a direct **101** receipt or the **109** physical GR/release in a **107 + 109** flow.
- **107 never contributes delivery quantity or delivery cadence.** It is valuation/cost-stage evidence for the same physical delivery represented by 109.
- 107 and 109 may post on different dates. The physical delivery date is the **109 posting date**; pairing must not require equal posting dates.
- Direct 101 receipt cost may come from 101. In a 107+109 flow, receipt cost authority comes from **107**, while quantity/date/GR come from **109**.
- Reversals follow the same separation: 102 reverses 101, 108 reverses 107 cost-stage evidence, and 110 reverses 109 physical receipt.
- Delivery history, last receipt, observed delivery weekdays, ordering cadence, and delivery quantities must use physical receipt stages only and must never sum 107 + 109.

## Ordering and Pricing best-available source policy

- Ordering and Price Suggestion do **not** wait for the POS/MVT daily grace cutoff and do not hard-block merely because one or more recent POS or MVT upload dates are missing.
- Use the newest available canonical POS days for sales/velocity/price-response history and the newest available canonical MVT days for receipt cadence/inventory movement evidence.
- Missing source dates are excluded from supported-day calculations; they are never converted to zero.
- Ordering forecasts missing calendar days after the latest usable MVT evidence instead of blocking the suggestion.
- Price optimization may use newer POS evidence even when MVT is a few days behind; POS and MVT data-through dates remain visible separately.
- The 3 PM POS/MVT grace policy remains valid for upload-health/QA monitoring only. It is not a gating rule for Ordering or Price Suggestion.
- Non-freshness blockers such as unresolved UOM, missing cost, invalid identity, or unavailable inventory evidence still fail closed for the affected item.

## Single-Service deployment rule

- v7.0.1 Single-Service Edition runs the HTTPS API and background worker in one App Platform service/container.
- Production App Platform instance count stays at 1 during the initial rollout.
- Do not create a separate always-on Worker component unless future workload measurements justify splitting the service again.
