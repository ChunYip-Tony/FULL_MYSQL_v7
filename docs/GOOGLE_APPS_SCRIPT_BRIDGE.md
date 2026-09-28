# FULL MYSQL Google Apps Script Bridge

This is the preferred no-service-account transport for publishing the validated FULL MYSQL analysis snapshot into the canonical Google Sheet.

## Target

Canonical spreadsheet:

- Name: `FULL_MYSQL_CHATGPT_ANALYSIS`
- Spreadsheet ID: `1kZQg_dQ79Jagg7hkBKs4YX33QBy9ByrDvq5KActCgwI`

The Apps Script bridge writes only these tabs:

- `MYSQL_SOURCE_STATUS`
- `MYSQL_LOOKUP_INDEX`
- `MYSQL_QUICK_CHECK_CURRENT`
- `MYSQL_FAMILY_CURRENT`
- `MYSQL_ANALYSIS_CURRENT`
- `MYSQL_QA_HOLD`
- `MYSQL_NEGATIVE_STOCK`
- `MYSQL_COST_BACKFILL`
- `BRIDGE_STATUS`

## 1. Create the Apps Script project

1. Open https://script.google.com while signed into the Google account that owns or can edit the target Sheet.
2. Create a **New project**.
3. Replace the default `Code.gs` contents with:
   `google_apps_script/FULLMYSQL_CHATGPT_ANALYSIS_BRIDGE.gs`
4. Save the project as `FULL MYSQL ChatGPT Bridge`.

No manually created Google Cloud service account is used by this transport.

## 2. Set Script Properties

In Apps Script:

1. Open **Project Settings**.
2. Under **Script Properties**, add:

```text
FULLMYSQL_SHEET_ID
1kZQg_dQ79Jagg7hkBKs4YX33QBy9ByrDvq5KActCgwI
```

3. Add a second property:

```text
FULLMYSQL_WEBHOOK_SECRET
<generate a long random secret, at least 24 characters>
```

Use the same secret later in DigitalOcean. Do not commit the secret to GitHub.

## 3. Deploy as a Web App

1. Select **Deploy -> New deployment**.
2. Select **Web app**.
3. Set **Execute as** to the deploying Google account / **Me**.
4. Set access so the DigitalOcean service can call the endpoint without an interactive Google login. For consumer accounts this is the anonymous/public web-app option.
5. Deploy and authorize the script to access the target spreadsheet.
6. Copy the production URL ending in `/exec`.

Do not use the `/dev` test URL in production.

## 4. DigitalOcean variables

Set the following on the FULL MYSQL service:

```text
FULLMYSQL_CHATGPT_SHEET_ENABLED=1
FULLMYSQL_CHATGPT_SHEET_REQUIRED=0
FULLMYSQL_CHATGPT_SHEET_TRANSPORT=APPS_SCRIPT
FULLMYSQL_CHATGPT_SHEET_ID=1kZQg_dQ79Jagg7hkBKs4YX33QBy9ByrDvq5KActCgwI
FULLMYSQL_CHATGPT_BRIDGE_ACTIVE_SOURCE=HYBRID_SQLITE
FULLMYSQL_APPS_SCRIPT_WEB_APP_URL=<the /exec URL>
FULLMYSQL_APPS_SCRIPT_WEBHOOK_SECRET=<same Script Property secret>
```

Store `FULLMYSQL_APPS_SCRIPT_WEBHOOK_SECRET` as an encrypted secret.

For this transport, `FULLMYSQL_GOOGLE_SERVICE_ACCOUNT_JSON` is not required.

## 5. First smoke test

Keep:

```text
FULLMYSQL_CHATGPT_SHEET_REQUIRED=0
```

for the first validated batch.

Expected sequence:

```text
RAW -> Phase 2C -> Phase 3 -> QA PASS
    -> BRIDGE_STATUS=PUBLISHING
    -> Apps Script writes MYSQL_* tabs
    -> read-back verifies batch id, serving row count, lookup header and last row
    -> BRIDGE_STATUS=PASS
```

If the bridge fails during replacement, readers see `PUBLISHING` or a failed status rather than trusting the previous PASS as current.

## 6. Production gate

After one complete publish/read-back succeeds and `BRIDGE_STATUS=PASS`, change:

```text
FULLMYSQL_CHATGPT_SHEET_REQUIRED=1
```

Then a future READY batch is not considered fully complete if the Sheet publish/read-back fails.

Keep:

```text
FULLMYSQL_CHATGPT_BRIDGE_ACTIVE_SOURCE=HYBRID_SQLITE
```

until FULL MYSQL analysis parity is explicitly approved. Only then change it to `FULL_MYSQL`.

## Security

- The Web App is network-reachable, but every POST must carry the high-entropy shared secret.
- The script refuses any spreadsheet ID other than `FULLMYSQL_SHEET_ID`.
- The script refuses tabs outside the explicit allow-list.
- Read-back is restricted to explicit A1 ranges on allowed tabs.
- Keep the webhook secret only in Apps Script Script Properties and DigitalOcean encrypted environment variables.
- Rotate the secret if the deployment URL or secret is exposed.
