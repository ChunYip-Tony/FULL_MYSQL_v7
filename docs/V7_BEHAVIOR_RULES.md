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

## Single-Service deployment rule

- v7.0.1 Single-Service Edition runs the HTTPS API and background worker in one App Platform service/container.
- Production App Platform instance count stays at 1 during the initial rollout.
- Do not create a separate always-on Worker component unless future workload measurements justify splitting the service again.
