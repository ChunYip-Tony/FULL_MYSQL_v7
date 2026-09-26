# FULL MYSQL v7.0 Secure API Foundation

This package starts the migration from direct-PC MySQL connections to HTTPS 443. It reuses the current v6.6 business rules and existing `full_mysql` schema. No rebuild of the production database is required.

## Architecture

Work/Home Client → HTTPS 443 → DigitalOcean App Platform API → DigitalOcean Managed MySQL → server-side Phase 1/2C/3 → Quick Check/AppSheet.

The Windows clients no longer need the MySQL hostname, password, CA certificate, port 25060, or Trusted Source IP entry.

## Safe migration

1. Deploy `server/` first.
2. Test `/healthz` and API authentication.
3. Install the v7 client on the Work PC **beside** v6 (`C:\FULL_MYSQL\FULL_MYSQL_Seafood_Client_v7`).
4. Upload one small known file as a test.
5. Verify the same MySQL batch/QA/Quick Check behavior.
6. Only after validation, stop using v6 direct-MySQL uploaders for production ingest.

Do not run both v6 and v7 production uploaders on the same new files during cutover.
