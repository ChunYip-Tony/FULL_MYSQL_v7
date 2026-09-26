# Work/Home cutover checklist — Single-Service Edition

1. Keep the current v6 production path available until v7 health/API tests pass.
2. Update GitHub to v7.0.1 Single-Service Edition.
3. Create **one** App Platform Web Service (`fullmysql`); do not add a separate Worker.
4. Attach existing Managed MySQL and configure private/VPC database access when available.
5. Confirm `/healthz` returns `7.0.1-single-service`.
6. Confirm authenticated `/v1/status` can read the production database.
7. Install v7 client beside v6 on Work PC; configure Work token only (no MySQL credentials).
8. Upload one small known spreadsheet and verify RAW → Phase2C → Phase3 → Quick Check.
9. Stop v6 production uploader before the first real v7 production batch.
10. Configure Home PC with its separate API token.
11. Keep one canonical ingest path. API batch locking/deduplication remains active centrally.
