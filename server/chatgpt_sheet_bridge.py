from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from db import db_conn
from quick_check_app import negative_stock_queue
from cost_backfill_queue import cost_backfill_queue

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
API_ROOT = "https://sheets.googleapis.com/v4/spreadsheets"

MYSQL_TABS = {
    "source": "MYSQL_SOURCE_STATUS",
    "lookup": "MYSQL_LOOKUP_INDEX",
    "quick": "MYSQL_QUICK_CHECK_CURRENT",
    "family": "MYSQL_FAMILY_CURRENT",
    "analysis": "MYSQL_ANALYSIS_CURRENT",
    "qa": "MYSQL_QA_HOLD",
    "negative": "MYSQL_NEGATIVE_STOCK",
    "cost_backfill": "MYSQL_COST_BACKFILL",
    "bridge": "BRIDGE_STATUS",
}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def bridge_required() -> bool:
    return _truthy(os.environ.get("FULLMYSQL_CHATGPT_SHEET_REQUIRED"))


def bridge_enabled() -> bool:
    return _truthy(os.environ.get("FULLMYSQL_CHATGPT_SHEET_ENABLED"))


def _bridge_transport() -> str:
    explicit = os.environ.get("FULLMYSQL_CHATGPT_SHEET_TRANSPORT", "").strip().upper()
    if explicit:
        if explicit not in {"APPS_SCRIPT", "SERVICE_ACCOUNT"}:
            raise RuntimeError(
                "FULLMYSQL_CHATGPT_SHEET_TRANSPORT must be APPS_SCRIPT or SERVICE_ACCOUNT."
            )
        return explicit
    if os.environ.get("FULLMYSQL_APPS_SCRIPT_WEB_APP_URL", "").strip():
        return "APPS_SCRIPT"
    return "SERVICE_ACCOUNT"


def _apps_script_url() -> str:
    url = os.environ.get("FULLMYSQL_APPS_SCRIPT_WEB_APP_URL", "").strip()
    if not url:
        raise RuntimeError("FULLMYSQL_APPS_SCRIPT_WEB_APP_URL is not configured.")
    if not url.startswith("https://script.google.com/"):
        raise RuntimeError("FULLMYSQL_APPS_SCRIPT_WEB_APP_URL must be a Google Apps Script web-app URL.")
    return url


def _apps_script_secret() -> str:
    secret = os.environ.get("FULLMYSQL_APPS_SCRIPT_WEBHOOK_SECRET", "")
    if len(secret) < 24:
        raise RuntimeError(
            "FULLMYSQL_APPS_SCRIPT_WEBHOOK_SECRET must be configured with at least 24 characters."
        )
    return secret


def _apps_script_post(payload: dict[str, Any], *, timeout: int = 90) -> dict[str, Any]:
    import requests

    body = {"secret": _apps_script_secret(), **payload}
    resp = requests.post(_apps_script_url(), json=body, timeout=timeout, allow_redirects=True)
    if resp.status_code >= 300:
        raise RuntimeError(f"Apps Script bridge HTTP {resp.status_code}: {resp.text[:500]}")
    try:
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(f"Apps Script bridge returned non-JSON: {resp.text[:500]}") from exc
    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"Apps Script bridge rejected request: {data}")
    return data


def _apps_script_write_matrix(
    spreadsheet_id: str,
    title: str,
    matrix: list[list[Any]],
    *,
    chunk_rows: int = 350,
) -> None:
    if not matrix:
        _apps_script_post(
            {
                "action": "clear_tab",
                "spreadsheet_id": spreadsheet_id,
                "tab": title,
            }
        )
        return
    width = max(len(r) for r in matrix)
    for start in range(0, len(matrix), chunk_rows):
        chunk = matrix[start : start + chunk_rows]
        normalized = [
            [_wire(v) for v in row] + [""] * (width - len(row))
            for row in chunk
        ]
        _apps_script_post(
            {
                "action": "write_tab_chunk",
                "spreadsheet_id": spreadsheet_id,
                "tab": title,
                "start_row": start + 1,
                "clear": start == 0,
                "values": normalized,
            },
            timeout=120,
        )


def _apps_script_read_values(spreadsheet_id: str, a1: str) -> list[list[Any]]:
    data = _apps_script_post(
        {
            "action": "read_range",
            "spreadsheet_id": spreadsheet_id,
            "a1": a1,
        },
        timeout=60,
    )
    values = data.get("values") or []
    return values if isinstance(values, list) else []


def _wire(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    return str(value)


def _col_letters(n: int) -> str:
    if n < 1:
        raise ValueError("Column count must be >= 1.")
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def _credentials_info() -> dict[str, Any]:
    raw = os.environ.get("FULLMYSQL_GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("FULLMYSQL_GOOGLE_SERVICE_ACCOUNT_JSON is not configured.")
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise RuntimeError("FULLMYSQL_GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON.") from exc
    if not isinstance(data, dict) or not data.get("client_email") or not data.get("private_key"):
        raise RuntimeError("Google service-account JSON is missing required fields.")
    return data


def _session():
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    info = _credentials_info()
    creds = service_account.Credentials.from_service_account_info(info, scopes=[SHEETS_SCOPE])
    return AuthorizedSession(creds), info.get("client_email")


def _sheet_id() -> str:
    sheet_id = os.environ.get("FULLMYSQL_CHATGPT_SHEET_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("FULLMYSQL_CHATGPT_SHEET_ID is not configured.")
    return sheet_id


def _active_source() -> str:
    value = os.environ.get("FULLMYSQL_CHATGPT_BRIDGE_ACTIVE_SOURCE", "HYBRID_SQLITE").strip().upper()
    return value or "HYBRID_SQLITE"


def _get_json(session, url: str) -> dict[str, Any]:
    resp = session.get(url, timeout=45)
    if resp.status_code >= 300:
        raise RuntimeError(f"Google Sheets GET failed {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def _post_json(session, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    resp = session.post(url, json=payload, timeout=60)
    if resp.status_code >= 300:
        raise RuntimeError(f"Google Sheets POST failed {resp.status_code}: {resp.text[:500]}")
    return resp.json() if resp.text else {}


def _put_json(session, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    resp = session.put(url, json=payload, timeout=90)
    if resp.status_code >= 300:
        raise RuntimeError(f"Google Sheets PUT failed {resp.status_code}: {resp.text[:500]}")
    return resp.json() if resp.text else {}


def _ensure_tabs(session, spreadsheet_id: str, titles: list[str]) -> None:
    meta = _get_json(session, f"{API_ROOT}/{spreadsheet_id}?fields=sheets.properties(sheetId,title)")
    existing = {
        str(s.get("properties", {}).get("title"))
        for s in meta.get("sheets", [])
        if s.get("properties", {}).get("title")
    }
    missing = [title for title in titles if title not in existing]
    if missing:
        _post_json(
            session,
            f"{API_ROOT}/{spreadsheet_id}:batchUpdate",
            {"requests": [{"addSheet": {"properties": {"title": t}}} for t in missing]},
        )


def _clear_tab(session, spreadsheet_id: str, title: str) -> None:
    enc = quote(f"'{title}'", safe="")
    _post_json(session, f"{API_ROOT}/{spreadsheet_id}/values/{enc}:clear", {})


def _write_matrix(session, spreadsheet_id: str, title: str, matrix: list[list[Any]], *, chunk_rows: int = 350) -> None:
    _clear_tab(session, spreadsheet_id, title)
    if not matrix:
        return
    width = max(len(r) for r in matrix)
    end_col = _col_letters(width)
    for start in range(0, len(matrix), chunk_rows):
        chunk = matrix[start : start + chunk_rows]
        start_row = start + 1
        end_row = start + len(chunk)
        rng = f"'{title}'!A{start_row}:{end_col}{end_row}"
        enc = quote(rng, safe="")
        _put_json(
            session,
            f"{API_ROOT}/{spreadsheet_id}/values/{enc}?valueInputOption=RAW",
            {"range": rng, "majorDimension": "ROWS", "values": [[_wire(v) for v in row] for row in chunk]},
        )


def _read_values(session, spreadsheet_id: str, a1: str) -> list[list[Any]]:
    enc = quote(a1, safe="")
    data = _get_json(session, f"{API_ROOT}/{spreadsheet_id}/values/{enc}?valueRenderOption=UNFORMATTED_VALUE")
    return data.get("values", [])


def _fetch_batch_state(cur, batch_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    cur.execute(
        """SELECT batch_id,batch_key,batch_label,processing_status,file_count,
                  source_row_count,error_count,completed_at
           FROM ingest_batch WHERE batch_id=%s""",
        (batch_id,),
    )
    batch = cur.fetchone()
    if not batch:
        raise KeyError(f"Batch {batch_id} not found.")
    cur.execute(
        """SELECT batch_id,quick_check_rows,quick_check_ready_rows,
                  quick_check_hold_rows,blocking_issue_count,result_status,updated_at
           FROM phase3_batch_result WHERE batch_id=%s""",
        (batch_id,),
    )
    return batch, (cur.fetchone() or {})


def _stock_state(quantity: Any) -> tuple[bool, str]:
    if quantity is None:
        return False, "UNKNOWN"
    try:
        q = Decimal(str(quantity))
    except Exception:
        return False, "UNKNOWN"
    if q < 0:
        return True, "NEGATIVE"
    if q == 0:
        return False, "ZERO"
    return False, "POSITIVE"


QC_COLUMNS = [
    "upc_id","ean_upc","selling_description","article_id","article_number","family_id",
    "main_article_number","family_description","product_class","selling_uom","base_uom",
    "base_qty_per_selling_unit","current_cost_per_base_uom","current_cost_per_selling_unit",
    "cost_source","cost_date","last_receipt_date","current_price","current_price_type",
    "current_price_source","current_price_asof_date","sales_dollars_7d","pos_qty_7d",
    "upc_velocity_7d","sales_days_7d","sales_dollars_30d","pos_qty_30d","upc_velocity_30d",
    "sales_days_30d","family_movement_7d","family_movement_uom","current_oh","current_oh_uom",
    "oh_date","dos","doh","gp_pct_current","gp_dollars_7d","gp_per_day_7d","sweet_spot_price",
    "wgpm_price","company_price_a","company_price_b","company_price_c","quick_check_status",
    "blocking_reason","publish_batch_id","published_at",
]


DERIVED_QC_COLUMNS = ["negative_stock", "stock_status"]


def _fetch_quick_rows(cur) -> list[dict[str, Any]]:
    cur.execute("SELECT " + ",".join(QC_COLUMNS) + " FROM quick_check_current ORDER BY ean_upc")
    rows = list(cur.fetchall())
    for row in rows:
        negative_stock, stock_status = _stock_state(row.get("current_oh"))
        row["negative_stock"] = negative_stock
        row["stock_status"] = stock_status
    return rows


def _build_lookup(rows: list[dict[str, Any]]) -> list[list[Any]]:
    header = ["Sheet_Row","upc_id","family_id","main_article_number","article_number","ean_upc",
              "selling_description","family_description","Search_Text"]
    out = [header]
    for sheet_row, row in enumerate(rows, start=2):
        search = " | ".join(
            str(v) for v in [
                row.get("ean_upc"),row.get("article_number"),row.get("main_article_number"),
                row.get("selling_description"),row.get("family_description")
            ] if v not in (None, "")
        )
        out.append([sheet_row,row.get("upc_id"),row.get("family_id"),row.get("main_article_number"),
                    row.get("article_number"),row.get("ean_upc"),row.get("selling_description"),
                    row.get("family_description"),search])
    return out


def _build_quick(rows: list[dict[str, Any]]) -> list[list[Any]]:
    export_columns = QC_COLUMNS + DERIVED_QC_COLUMNS
    return [["Sheet_Row"] + export_columns] + [
        [sheet_row] + [row.get(col) for col in export_columns]
        for sheet_row, row in enumerate(rows, start=2)
    ]


ANALYSIS_COLUMNS = [
    "ean_upc","main_article_number","article_number","selling_description","product_class",
    "selling_uom","current_price","current_price_type","current_cost_per_selling_unit",
    "gp_pct_current","gp_dollars_7d","gp_per_day_7d","pos_qty_7d","upc_velocity_7d",
    "family_movement_7d","family_movement_uom","current_oh","current_oh_uom",
    "negative_stock","stock_status","dos","doh",
    "sweet_spot_price","wgpm_price","company_price_a","company_price_b","company_price_c",
    "quick_check_status","blocking_reason","publish_batch_id","published_at",
]


def _build_analysis(rows: list[dict[str, Any]]) -> list[list[Any]]:
    """ChatGPT analytical input: READY rows only.

    QA_HOLD/HISTORICAL rows remain available in dedicated verification tabs but
    are never mixed into the analytical matrix used for recommendations.
    """
    ready = [
        row for row in rows
        if str(row.get("quick_check_status") or "").upper() == "READY"
    ]
    out = [["Sheet_Row"] + ANALYSIS_COLUMNS + ["Analysis_Source"]]
    for sheet_row, row in enumerate(ready, start=2):
        out.append(
            [sheet_row] + [row.get(col) for col in ANALYSIS_COLUMNS]
            + ["FULL_MYSQL_PHASE3_READY_ONLY"]
        )
    return out


def _build_qa(rows: list[dict[str, Any]]) -> list[list[Any]]:
    header = ["Sheet_Row","ean_upc","main_article_number","article_number","selling_description",
              "selling_uom","current_price","current_cost_per_selling_unit","pos_qty_7d",
              "quick_check_status","blocking_reason","publish_batch_id"]
    out = [header]
    for sheet_row, row in enumerate(rows, start=2):
        if str(row.get("quick_check_status") or "").upper() != "READY":
            out.append([sheet_row,row.get("ean_upc"),row.get("main_article_number"),row.get("article_number"),
                        row.get("selling_description"),row.get("selling_uom"),row.get("current_price"),
                        row.get("current_cost_per_selling_unit"),row.get("pos_qty_7d"),
                        row.get("quick_check_status"),row.get("blocking_reason"),row.get("publish_batch_id")])
    return out



def _build_negative_stock(rows: list[dict[str, Any]]) -> list[list[Any]]:
    columns = [
        "inventory_owner_scope","inventory_owner_id","inventory_owner_key",
        "inventory_owner_article_number","inventory_owner_family_id",
        "representative_upc","related_upcs","related_upc_count",
        "main_article_number","selling_description","selling_uom",
        "system_oh","system_oh_uom","effective_oh","effective_oh_uom","effective_oh_source",
        "active_true_stock","active_true_stock_uom","true_stock_required_uom",
        "pos_qty_7d","upc_velocity_7d","dos",
        "related_quick_check_statuses","quick_check_status","blocking_reason",
        "stock_status","negative_stock","action_upc","action_code","action_reason","action_endpoint",
        "publish_batch_id","published_at",
    ]

    def value(row: dict[str, Any], col: str) -> Any:
        v = row.get(col)
        if col in {"related_upcs","related_quick_check_statuses"} and isinstance(v, list):
            return ",".join(str(x) for x in v)
        return v

    return [columns] + [[value(row, col) for col in columns] for row in rows]




def _build_cost_backfill(rows: list[dict[str, Any]]) -> list[list[Any]]:
    columns = [
        "backfill_sequence","family_id","main_article_number","representative_upc",
        "related_upcs","related_upc_count","confirmed_article_numbers",
        "current_hold_row_count","current_hold_reason",
        "requested_lookback_days","requested_backfill_start","requested_backfill_end",
        "earliest_loaded_movement_date","latest_loaded_movement_date",
        "loaded_movement_row_count","source_valid_days_in_window",
        "source_missing_day_count","source_first_missing_date","source_last_missing_date",
        "earliest_loaded_receipt_date","latest_loaded_receipt_date",
        "loaded_receipt_row_count","valid_receipt_valuation_row_count",
        "diagnostic_classification","diagnostic_proposed_action","diagnostic_status",
        "coverage_status","backfill_needed","backfill_mode","required_upload_scope",
        "required_receipt_movements","action_code",
    ]

    def value(row: dict[str, Any], col: str) -> Any:
        v = row.get(col)
        if isinstance(v, list):
            return ",".join(str(x) for x in v)
        return v

    return [columns] + [[value(row, col) for col in columns] for row in rows]



def _build_family(rows: list[dict[str, Any]]) -> list[list[Any]]:
    header = ["family_id","main_article_number","family_description","Representative_UPC","UPC_Row_Count",
              "Current_Active_Row_Count","READY_Row_Count","QA_HOLD_Row_Count","Historical_Row_Count",
              "Family_Movement_7D","Family_Movement_UOM","Representative_Current_OH","Representative_OH_UOM",
              "Representative_Negative_Stock","Representative_Stock_Status",
              "Representative_DOS","Representative_DOH","Publish_Batch_ID"]
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row.get("family_id")].append(row)
    out = [header]
    for family_id in sorted(groups, key=lambda v: (v is None, str(v))):
        rs = groups[family_id]
        statuses = Counter(str(r.get("quick_check_status") or "") for r in rs)
        ready_rs = [
            r for r in rs
            if str(r.get("quick_check_status") or "").upper() == "READY"
        ]
        # Families with no READY UPC are excluded from analytical family input.
        # Their held rows remain visible in MYSQL_QA_HOLD.
        if not ready_rs:
            continue
        representative = max(
            ready_rs,
            key=lambda r: (float(r.get("pos_qty_7d") or 0), 1 if r.get("current_price") is not None else 0),
        )
        active = statuses.get("READY", 0) + statuses.get("QA_HOLD", 0)
        out.append([family_id,representative.get("main_article_number"),representative.get("family_description"),
                    representative.get("ean_upc"),len(rs),active,statuses.get("READY",0),statuses.get("QA_HOLD",0),
                    statuses.get("HISTORICAL_ONLY",0),representative.get("family_movement_7d"),
                    representative.get("family_movement_uom"),representative.get("current_oh"),
                    representative.get("current_oh_uom"),representative.get("negative_stock"),
                    representative.get("stock_status"),representative.get("dos"),representative.get("doh"),
                    representative.get("publish_batch_id")])
    return out


def _source_status(
    batch: dict[str, Any],
    phase3: dict[str, Any],
    row_count: int,
    *,
    analysis_ready_rows: int,
    analysis_family_rows: int,
) -> list[list[Any]]:
    fields = [
        ("Snapshot_Status","MYSQL_PUBLISH_READY"),("MySQL_Batch_ID",batch.get("batch_id")),
        ("MySQL_Batch_Key",batch.get("batch_key")),("MySQL_Batch_Label",batch.get("batch_label")),
        ("MySQL_Batch_Status",batch.get("processing_status")),("Phase3_Result_Status",phase3.get("result_status")),
        ("Phase3_Blocking_Issues",phase3.get("blocking_issue_count")),("Current_Active_Rows",phase3.get("quick_check_rows")),
        ("Current_READY_Rows",phase3.get("quick_check_ready_rows")),("Current_HOLD_Rows",phase3.get("quick_check_hold_rows")),
        ("Serving_Rows_Total",row_count),
        ("Analysis_READY_Rows",analysis_ready_rows),
        ("Analysis_Family_Rows",analysis_family_rows),
        ("Analysis_Excluded_HOLD_Rows",phase3.get("quick_check_hold_rows")),
        ("Analysis_Input_Policy","READY_ONLY"),
        ("Snapshot_Published_At_UTC",datetime.now(timezone.utc).isoformat()),
        ("Publisher","FULL_MYSQL_CHATGPT_SHEET_BRIDGE"),("Active_ChatGPT_Source",_active_source()),
        ("Analysis_Cutover_Status","READY_ONLY_SAFE_PARTIAL"),
    ]
    return [["Field","Value"]] + [[k,v] for k,v in fields]


def _bridge_status(
    *,
    batch_id: int,
    row_count: int,
    publisher_identity: str | None,
    transport: str,
    status: str,
    detail: str,
) -> list[list[Any]]:
    values = [
        ("Last_Publish_Status",status),("MySQL_Publish_Batch_ID",batch_id),("MySQL_Serving_Rows",row_count),
        ("Active_Source",_active_source()),("Cutover_Status","PARITY_REQUIRED"),
        ("Transport",transport),("Publisher_Identity",publisher_identity or ""),
        ("Last_Readback_At_UTC",datetime.now(timezone.utc).isoformat()),
        ("Detail",detail),
    ]
    return [["Field","Value"]] + [[k,v] for k,v in values]


def _validate_readback(
    session,
    spreadsheet_id: str,
    batch_id: int,
    row_count: int,
    *,
    analysis_row_count: int,
    reader=None,
) -> dict[str, Any]:
    read = reader or _read_values
    source = read(session, spreadsheet_id, f"'{MYSQL_TABS['source']}'!A1:B20")
    lookup_head = read(session, spreadsheet_id, f"'{MYSQL_TABS['lookup']}'!A1:I2")
    lookup_tail = read(session, spreadsheet_id,
                       f"'{MYSQL_TABS['lookup']}'!A{row_count + 1}:I{row_count + 1}")
    analysis_head = read(session, spreadsheet_id, f"'{MYSQL_TABS['analysis']}'!A1:B2")
    analysis_tail = read(
        session,
        spreadsheet_id,
        f"'{MYSQL_TABS['analysis']}'!A{analysis_row_count + 1}:B{analysis_row_count + 1}",
    )
    source_map = {str(r[0]): r[1] if len(r) > 1 else "" for r in source[1:] if r}
    failures: list[str] = []
    if str(source_map.get("MySQL_Batch_ID")) != str(batch_id):
        failures.append("BATCH_ID_MISMATCH")
    if str(source_map.get("Serving_Rows_Total")) != str(row_count):
        failures.append("ROW_COUNT_MISMATCH")
    if not lookup_head or lookup_head[0][:2] != ["Sheet_Row","upc_id"]:
        failures.append("LOOKUP_HEADER_MISMATCH")
    expected_last_sheet_row = row_count + 1
    if not lookup_tail or not lookup_tail[0] or str(lookup_tail[0][0]) != str(expected_last_sheet_row):
        failures.append("LOOKUP_LAST_ROW_MISMATCH")
    if str(source_map.get("Analysis_READY_Rows")) != str(analysis_row_count):
        failures.append("ANALYSIS_READY_ROW_COUNT_MISMATCH")
    if not analysis_head or analysis_head[0][:2] != ["Sheet_Row","ean_upc"]:
        failures.append("ANALYSIS_HEADER_MISMATCH")
    expected_analysis_last_row = analysis_row_count + 1
    if (
        not analysis_tail
        or not analysis_tail[0]
        or str(analysis_tail[0][0]) != str(expected_analysis_last_row)
    ):
        failures.append("ANALYSIS_LAST_ROW_MISMATCH")
    return {
        "pass":not failures,
        "failures":failures,
        "source_status":source_map,
        "expected_last_sheet_row":expected_last_sheet_row,
        "expected_analysis_last_row":expected_analysis_last_row,
    }


def publish_chatgpt_snapshot(batch_id: int) -> dict[str, Any]:
    if not bridge_enabled():
        return {"status":"DISABLED","batch_id":batch_id,
                "reason":"FULLMYSQL_CHATGPT_SHEET_ENABLED is not enabled."}
    try:
        spreadsheet_id = _sheet_id()
        transport = _bridge_transport()

        with db_conn() as conn:
            cur = conn.cursor(dictionary=True, buffered=True)
            try:
                batch, phase3 = _fetch_batch_state(cur, batch_id)
                allowed = {"QUICK_CHECK_READY","QUICK_CHECK_READY_WITH_HOLDS"}
                if str(batch.get("processing_status")) not in allowed:
                    return {"status":"BLOCKED","batch_id":batch_id,
                            "reason":f"MySQL batch status is {batch.get('processing_status')}; READY required."}
                if int(phase3.get("blocking_issue_count") or 0) != 0:
                    return {"status":"BLOCKED","batch_id":batch_id,
                            "reason":"Phase 3 blocking_issue_count is non-zero."}
                rows = _fetch_quick_rows(cur)
            finally:
                cur.close()

        if not rows:
            return {"status":"BLOCKED","batch_id":batch_id,"reason":"quick_check_current is empty."}

        ready_rows = [
            row for row in rows
            if str(row.get("quick_check_status") or "").upper() == "READY"
        ]
        hold_rows = [
            row for row in rows
            if str(row.get("quick_check_status") or "").upper() == "QA_HOLD"
        ]
        if not ready_rows:
            return {
                "status":"BLOCKED",
                "batch_id":batch_id,
                "reason":"No READY Quick Check rows are available for safe analytical publish.",
                "hold_row_count":len(hold_rows),
            }

        negative_queue = negative_stock_queue(limit=500)
        cost_backfill = cost_backfill_queue(lookback_days=90)

        # Fail closed for readers while a new snapshot is being replaced.
        publishing_matrix = _bridge_status(
            batch_id=batch_id,
            row_count=len(rows),
            publisher_identity="GOOGLE_APPS_SCRIPT_WEB_APP" if transport == "APPS_SCRIPT" else "GOOGLE_SERVICE_ACCOUNT",
            transport=transport,
            status="PUBLISHING",
            detail="Snapshot replacement in progress; do not serve as current until PASS.",
        )
        if transport == "APPS_SCRIPT":
            _apps_script_write_matrix(spreadsheet_id, MYSQL_TABS["bridge"], publishing_matrix)
        else:
            publishing_session, publishing_identity = _session()
            _ensure_tabs(publishing_session, spreadsheet_id, [MYSQL_TABS["bridge"]])
            _write_matrix(publishing_session, spreadsheet_id, MYSQL_TABS["bridge"], publishing_matrix)

        analysis_matrix = _build_analysis(rows)
        family_matrix = _build_family(rows)
        analysis_row_count = max(0, len(analysis_matrix) - 1)
        analysis_family_count = max(0, len(family_matrix) - 1)

        matrices = {
            MYSQL_TABS["source"]:_source_status(
                batch,
                phase3,
                len(rows),
                analysis_ready_rows=analysis_row_count,
                analysis_family_rows=analysis_family_count,
            ),
            MYSQL_TABS["lookup"]:_build_lookup(rows),
            MYSQL_TABS["quick"]:_build_quick(rows),
            MYSQL_TABS["family"]:family_matrix,
            MYSQL_TABS["analysis"]:analysis_matrix,
            MYSQL_TABS["qa"]:_build_qa(rows),
            MYSQL_TABS["negative"]:_build_negative_stock(negative_queue.get("rows") or []),
            MYSQL_TABS["cost_backfill"]:_build_cost_backfill(cost_backfill.get("actions") or []),
        }

        session = None
        publisher_identity = None
        if transport == "APPS_SCRIPT":
            publisher_identity = "GOOGLE_APPS_SCRIPT_WEB_APP"
            for title, matrix in matrices.items():
                _apps_script_write_matrix(spreadsheet_id, title, matrix)
            readback = _validate_readback(
                None,
                spreadsheet_id,
                batch_id,
                len(rows),
                analysis_row_count=analysis_row_count,
                reader=lambda _session, sid, a1: _apps_script_read_values(sid, a1),
            )
        else:
            session, publisher_identity = _session()
            _ensure_tabs(session, spreadsheet_id, list(matrices) + [MYSQL_TABS["bridge"]])
            for title, matrix in matrices.items():
                _write_matrix(session, spreadsheet_id, title, matrix)
            readback = _validate_readback(
                session,
                spreadsheet_id,
                batch_id,
                len(rows),
                analysis_row_count=analysis_row_count,
            )

        if not readback["pass"]:
            bridge_matrix = _bridge_status(
                batch_id=batch_id,
                row_count=len(rows),
                publisher_identity=publisher_identity,
                transport=transport,
                status="FAILED_READBACK",
                detail=",".join(readback["failures"]),
            )
            if transport == "APPS_SCRIPT":
                _apps_script_write_matrix(spreadsheet_id, MYSQL_TABS["bridge"], bridge_matrix)
            else:
                _write_matrix(session, spreadsheet_id, MYSQL_TABS["bridge"], bridge_matrix)
            return {
                "status":"FAILED_READBACK",
                "batch_id":batch_id,
                "spreadsheet_id":spreadsheet_id,
                "row_count":len(rows),
                "transport":transport,
                "readback":readback,
            }

        bridge_matrix = _bridge_status(
            batch_id=batch_id,
            row_count=len(rows),
            publisher_identity=publisher_identity,
            transport=transport,
            status="PASS",
            detail=(
                f"READY-only analytical snapshot published: {analysis_row_count} READY rows; "
                f"{len(hold_rows)} HOLD rows excluded to MYSQL_QA_HOLD."
            ),
        )
        if transport == "APPS_SCRIPT":
            _apps_script_write_matrix(spreadsheet_id, MYSQL_TABS["bridge"], bridge_matrix)
            bridge_rb = _apps_script_read_values(
                spreadsheet_id, f"'{MYSQL_TABS['bridge']}'!A1:B12"
            )
        else:
            _write_matrix(session, spreadsheet_id, MYSQL_TABS["bridge"], bridge_matrix)
            bridge_rb = _read_values(
                session, spreadsheet_id, f"'{MYSQL_TABS['bridge']}'!A1:B12"
            )

        bridge_map = {str(r[0]): r[1] if len(r) > 1 else "" for r in bridge_rb[1:] if r}
        if (
            str(bridge_map.get("Last_Publish_Status")) != "PASS"
            or str(bridge_map.get("MySQL_Publish_Batch_ID")) != str(batch_id)
        ):
            return {
                "status":"FAILED_BRIDGE_READBACK",
                "batch_id":batch_id,
                "spreadsheet_id":spreadsheet_id,
                "row_count":len(rows),
                "transport":transport,
            }

        return {
            "status":"PASS",
            "batch_id":batch_id,
            "spreadsheet_id":spreadsheet_id,
            "row_count":len(rows),
            "analysis_ready_row_count":analysis_row_count,
            "analysis_family_row_count":analysis_family_count,
            "excluded_hold_row_count":len(hold_rows),
            "analysis_input_policy":"READY_ONLY",
            "active_source":_active_source(),
            "transport":transport,
            "publisher_identity":publisher_identity,
            "readback":readback,
        }
    except Exception as exc:
        return {"status":"FAILED","batch_id":batch_id,"error":repr(exc)}
