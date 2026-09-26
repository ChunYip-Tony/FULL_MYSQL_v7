# Deploy FULL MYSQL v7.0.1 Single-Service Edition on DigitalOcean App Platform

## Goal

Deploy **one App Platform Web Service** that provides the public HTTPS API and also runs the FULL MYSQL background pipeline worker in the same container.

Do **not** create a separate App Platform Worker component for this edition.

## 1. GitHub source

Use the private repository containing this package. The repository root must contain `server/` directly.

## 2. Create one Web Service

DigitalOcean → Apps → Create App → GitHub → select the repository and `main` branch.

Configure exactly one Web Service:

```text
Name: fullmysql
Source Directory: server
Build Command: pip install -r requirements.txt
Run Command: python single_service.py
HTTP Port: 8080
Instances: 1
Size: basic-xs (1 shared vCPU / 1 GiB RAM)
Health Check: /healthz
Autodeploy: ON
```

`single_service.py` starts and supervises both the API process and `worker.py` inside this one container.

## 3. Attach the existing Managed MySQL

Attach the existing production MySQL cluster to the app. Use a simple component name such as `fullmysql-db`. Continue using the existing production database/user; do not create a new database just for v7.

## 4. Prefer private/VPC database traffic

Enable App Platform VPC access in the same region/VPC as the Managed MySQL cluster when available. Use the private bindable URL in production.

## 5. Runtime environment variables

Set these on the **single `fullmysql` service**:

```text
FULLMYSQL_DATABASE_URL=${fullmysql-db.DATABASE_PRIVATE_URL}
FULLMYSQL_DB_CA_CERT=${fullmysql-db.CA_CERT}
FULLMYSQL_API_TOKENS_JSON={"WORK-PC":"...","HOME-PC":"..."}
FULLMYSQL_ADMIN_DEVICES=HOME-PC
FULLMYSQL_UPLOAD_LIMIT_MB=96
FULLMYSQL_WORKER_POLL_SECONDS=5
FULLMYSQL_WORKER_RESTART_SECONDS=5
```

Mark `FULLMYSQL_API_TOKENS_JSON` as encrypted/secret. Do not commit real tokens or database passwords to GitHub.

If private/VPC connectivity is not ready, `${fullmysql-db.DATABASE_URL}` can be used temporarily, but private/VPC is the target production path.

## 6. Verify deployment

Open:

```text
https://YOUR-APP.ondigitalocean.app/healthz
```

Expected response includes:

```json
{"ok":true,"version":"7.0.1-single-service"}
```

Then test authenticated `/v1/status` before installing the v7 client.

## 7. Configure Windows clients

Run `client_installer/INSTALL_V7_CLIENT.bat`, then `CONFIGURE_API.bat`. Enter the HTTPS API base URL, the device ID (`WORK-PC` or `HOME-PC`), and that device's API token.

## Existing database schema

This edition intentionally reuses the current `ingest_batch`, `ingest_file`, `pipeline_run`, RAW, Phase2C, Phase3, Quick Check, and related tables. No new production schema is required just to switch from two App Platform components to one.
