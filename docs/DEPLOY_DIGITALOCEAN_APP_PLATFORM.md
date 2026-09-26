# Deploy FULL MYSQL v7.0 on DigitalOcean App Platform

## Why App Platform
App Platform supplies the public HTTPS endpoint automatically. The service and worker run in DigitalOcean, while the Windows clients use ordinary HTTPS 443.

## 1. Put this package in a private GitHub repository
The repository must include the `server/` directory. Do not commit real API tokens or database passwords.

## 2. Create an App Platform app
DigitalOcean → Apps → Create App → choose the private GitHub repository.

Create two components from `/server`:
- **Service** `api`: `uvicorn api:app --host 0.0.0.0 --port 8080`
- **Worker** `worker`: `python worker.py`

Use one instance of each during the initial rollout.

## 3. Attach the existing Managed MySQL database
Attach the existing production MySQL cluster to the app. Give the database component a simple name such as `fullmysql-db` and select the existing `full_mysql_ingest` database user if the UI offers a user selector.

## 4. Enable VPC/private database traffic
On the App Networking page, enable VPC access in the same DigitalOcean region/VPC as the Managed MySQL cluster (or use VPC peering if required). Add the app/VPC private egress source to the database Trusted Sources.

## 5. Environment variables
Set for both API and worker at runtime:

```
FULLMYSQL_DATABASE_URL=${fullmysql-db.DATABASE_PRIVATE_URL}
FULLMYSQL_DB_CA_CERT=${fullmysql-db.CA_CERT}
FULLMYSQL_API_TOKENS_JSON={"WORK-PC":"...","HOME-PC":"..."}
FULLMYSQL_ADMIN_DEVICES=HOME-PC
FULLMYSQL_UPLOAD_LIMIT_MB=96
FULLMYSQL_WORKER_POLL_SECONDS=5
```

Mark `FULLMYSQL_API_TOKENS_JSON` as encrypted/secret. Generate tokens with `GENERATE_API_TOKENS.py`.

If private VPC is not ready yet, `${fullmysql-db.DATABASE_URL}` can be used temporarily, but private/VPC is the intended production path.

## 6. Deploy and verify
App Platform gives the service a starter HTTPS domain ending in `.ondigitalocean.app`. Test:

```
https://YOUR-APP.ondigitalocean.app/healthz
```

Expected JSON includes `"ok": true` and version `7.0.0-secure-api-foundation`.

## 7. Configure Work/Home client
Run `INSTALL_V7_CLIENT.bat`, then `CONFIGURE_API.bat`. Enter the HTTPS API URL, the matching Device ID, and that device's API token.

## Existing database schema
This v7 foundation intentionally uses the existing `ingest_batch`, `ingest_file`, `pipeline_run`, RAW, Phase2C, Phase3, and Quick Check tables. It does not require a new schema migration. Upload session IDs use `ingest_batch.batch_key`, and server processing jobs use `pipeline_run`.
