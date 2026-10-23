from __future__ import annotations
from supplementary_movement_cost import REJECTED_RECEIPT_SQL

import json
import os
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from db import db_conn
from quick_check_app import negative_stock_queue
from cost_backfill_queue import cost_backfill_queue
from data_coverage import coverage_summary, source_data_days
from price_history_analysis import HISTORY_CONTRACT

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


def enqueue_chatgpt_publish(
    batch_id: int,
    *,
    pipeline_name: str,
    code_version: str,
    requested_by: str,
    source_pipeline_run_id: int | None = None,
    reason: str = "ASYNC_CHATGPT_SHEET_PUBLISH",
) -> dict[str, Any]:
    """Queue a durable, non-blocking Sheet publish job.

    Phase 3 and Quick Check serving are deliberately independent of this queue.
    A slow or failed Google/Apps Script transport must never roll back or hold a
    committed MySQL serving snapshot.
    """
    bid=int(batch_id)
    if not bridge_enabled():
        return {
            "status":"DISABLED",
            "batch_id":bid,
            "reason":"FULLMYSQL_CHATGPT_SHEET_ENABLED is not enabled.",
        }

    with db_conn() as conn:
        cur=conn.cursor(dictionary=True, buffered=True)
        try:
            # Serialize startup/manual/reconciler enqueue decisions per batch.
            cur.execute("SELECT batch_id FROM ingest_batch WHERE batch_id=%s FOR UPDATE",(bid,))
            if not cur.fetchone():raise ValueError("Publish batch not found")
            cur.execute(
                """SELECT pipeline_run_id,processing_status,code_version,detail_json
                   FROM pipeline_run
                   WHERE batch_id=%s
                     AND pipeline_name=%s
                     AND stage_name='CHATGPT_SHEET_PUBLISH'
                     AND processing_status IN ('QUEUED','STARTED','PAUSE_REQUESTED')
                     AND code_version=%s
                   ORDER BY pipeline_run_id DESC
                   LIMIT 1""",
                (bid,pipeline_name,code_version),
            )
            active=cur.fetchone()
            # A running publisher already captured its source snapshot. A later
            # same-batch rebuild must get a durable follow-up job. An existing
            # QUEUED job can absorb it because it has not loaded any rows yet.
            active_source_run_id = None
            if active:
                try:
                    active_detail = active.get("detail_json") or {}
                    if not isinstance(active_detail, dict):
                        active_detail = json.loads(active_detail)
                    active_source_run_id = active_detail.get("source_pipeline_run_id")
                except (TypeError, ValueError):
                    pass
            needs_followup = bool(
                active
                and str(active.get("processing_status") or "").upper() in {"STARTED", "PAUSE_REQUESTED"}
                and source_pipeline_run_id is not None
                and str(active_source_run_id) != str(source_pipeline_run_id)
            )
            if active and not needs_followup:
                conn.commit()
                return {
                    "status":"ALREADY_QUEUED" if str(active.get("processing_status") or "").upper()=="QUEUED" else "ALREADY_ACTIVE",
                    "batch_id":bid,
                    "publish_run_id":int(active["pipeline_run_id"]),
                    "processing_status":active.get("processing_status"),
                    "code_version":active.get("code_version"),
                }

            cur.execute(
                """SELECT COALESCE(MAX(run_number),0)+1 AS next_run
                   FROM pipeline_run
                   WHERE batch_id=%s
                     AND pipeline_name=%s
                     AND stage_name='CHATGPT_SHEET_PUBLISH'""",
                (bid,pipeline_name),
            )
            run_number=int((cur.fetchone() or {}).get("next_run") or 1)
            detail={
                "requested_by":requested_by,
                "reason":reason,
                "queued_at":datetime.now(timezone.utc).isoformat(),
                "source_pipeline_run_id":source_pipeline_run_id,
                "async_nonblocking":True,
            }
            cur.execute(
                """INSERT INTO pipeline_run
                   (batch_id,pipeline_name,stage_name,run_number,
                    processing_status,code_version,detail_json)
                   VALUES (%s,%s,'CHATGPT_SHEET_PUBLISH',%s,'QUEUED',%s,%s)""",
                (
                    bid,
                    pipeline_name,
                    run_number,
                    code_version,
                    json.dumps(detail,ensure_ascii=False,default=str),
                ),
            )
            publish_run_id=int(cur.lastrowid)
            conn.commit()
            return {
                "status":"QUEUED",
                "batch_id":bid,
                "publish_run_id":publish_run_id,
                "processing_status":"QUEUED",
                "code_version":code_version,
                "source_pipeline_run_id":source_pipeline_run_id,
            }
        finally:
            cur.close()


def chatgpt_publish_status(batch_id: int, *, pipeline_name: str) -> dict[str, Any]:
    bid=int(batch_id)
    with db_conn() as conn:
        cur=conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT pipeline_run_id,processing_status,code_version,
                          started_at,completed_at,error_count,detail_json
                   FROM pipeline_run
                   WHERE batch_id=%s
                     AND pipeline_name=%s
                     AND stage_name='CHATGPT_SHEET_PUBLISH'
                   ORDER BY CASE WHEN processing_status IN ('STARTED','PAUSE_REQUESTED') THEN 0 WHEN processing_status='QUEUED' THEN 1 ELSE 2 END,pipeline_run_id DESC
                   LIMIT 1""",
                (bid,pipeline_name),
            )
            row=cur.fetchone()
        finally:
            cur.close()
    if not row:
        return {"status":"NONE","batch_id":bid}
    detail={}
    try:
        detail=json.loads(row.get("detail_json") or "{}")
    except Exception:
        detail={}
    return {
        "status":str(row.get("processing_status") or "").upper(),
        "batch_id":bid,
        "publish_run_id":int(row.get("pipeline_run_id") or 0),
        "code_version":row.get("code_version"),
        "started_at":row.get("started_at"),
        "completed_at":row.get("completed_at"),
        "error_count":int(row.get("error_count") or 0),
        "publish_result":detail.get("publish_result"),
        "failure_error":(detail.get("publish_result") or {}).get("error") or detail.get("error") or detail.get("recovery_reason"),
        "worker":detail.get("worker"),
        "heartbeat_at":detail.get("heartbeat_at"),
        "publisher_stage":detail.get("phase3_stage") or detail.get("bridge_stage"),
        "publisher_elapsed_seconds":detail.get("progress_elapsed_seconds"),
        "async_nonblocking":True,
    }


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


class _AppsScriptPermanentError(RuntimeError):
    """Bridge configuration or validation failures require a change before retrying."""


def _apps_script_post(payload: dict[str, Any], *, timeout: int = 90) -> dict[str, Any]:
    import requests
    import time as _time

    body = {"secret": _apps_script_secret(), **payload}
    last_error: Exception | None = None
    for attempt in range(1, 5):
        try:
            resp = requests.post(
                _apps_script_url(),
                json=body,
                timeout=timeout,
                allow_redirects=True,
            )
            if resp.status_code >= 300:
                raise RuntimeError(
                    f"Apps Script bridge HTTP {resp.status_code}: {resp.text[:500]}"
                )
            try:
                data = resp.json()
            except Exception as exc:
                raise RuntimeError(
                    f"Apps Script bridge returned non-JSON: {resp.text[:500]}"
                ) from exc
            if not isinstance(data, dict) or not data.get("ok"):
                error = str(data.get("error") or "") if isinstance(data, dict) else ""
                permanent_codes = {
                    "TAB_NOT_ALLOWED", "UNAUTHORIZED", "SPREADSHEET_ID_MISMATCH",
                }
                if error.split(":", 1)[0].strip() in permanent_codes:
                    raise _AppsScriptPermanentError(
                        f"Apps Script bridge rejected request: {error}"
                    )
                raise RuntimeError(f"Apps Script bridge rejected request: {data}")
            return data
        except _AppsScriptPermanentError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt >= 4:
                break
            # Apps Script can transiently throttle or time out during a multi-tab
            # snapshot replacement. Back off before retrying the same idempotent
            # chunk/read request.
            _time.sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError(
        f"Apps Script bridge failed after 4 attempts: {last_error!r}"
    )


def _apps_script_write_matrix(
    spreadsheet_id: str,
    title: str,
    matrix: list[list[Any]],
    *,
    chunk_rows: int = 1500,
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
    # Apps Script rejects payloads above 50,000 cells. Use a dynamic chunk size
    # that stays below that limit while avoiding dozens of tiny HTTP executions.
    safe_chunk_rows = max(1, min(int(chunk_rows), max(1, 40000 // max(1, width))))
    for start in range(0, len(matrix), safe_chunk_rows):
        chunk = matrix[start : start + safe_chunk_rows]
        normalized = [
            [_apps_script_wire(v) for v in row] + [""] * (width - len(row))
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
        # Sheets stores 15 significant decimal digits. Use the same finite
        # transport value for writes and full-cell expected readback.
        return float(format(value, '.15g'))
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return float(format(value, '.15g'))
    if isinstance(value, (int, str)):
        return value
    return str(value)


def _apps_script_wire(value: Any) -> Any:
    """Protect text identifiers from SpreadsheetApp.setValues coercion.

    The Sheets RAW API already preserves strings. Apps Script's setValues
    interprets numeric-looking strings using the cell format, so UPCs with
    leading zeroes need Sheets' literal-text prefix on that transport only.
    Readback still compares the original unmodified identifier exactly.
    """
    value = _wire(value)
    # Every string is literal source text. Comma-separated UPC lists can be
    # interpreted as enormous numbers; dates can be timezone-shifted, and names
    # beginning '=' can become formulas. Numeric Python values stay numeric.
    return "'" + value if isinstance(value, str) and value else value


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

POS_3D_COLUMNS = [
    "pos_3d_window_start",
    "pos_3d_window_end",
    "pos_3d_supported_days",
    "sales_dollars_3d",
    "pos_qty_3d",
    "upc_velocity_3d",
    "selling_days_3d",
    "pos_3d_coverage_status",
    "pos_3d_data_day_definition",
]

LATEST_DAILY_COLUMNS = [
    "latest_daily_business_date",
    "latest_daily_sales_dollars",
    "latest_daily_pos_qty",
    "latest_daily_avg_sold_price",
    "latest_daily_price_type",
    "latest_daily_cost_per_selling_unit",
    "latest_daily_cost_source",
    "latest_daily_cost_date",
    "latest_daily_cogs",
    "latest_daily_gp_dollars",
    "latest_daily_gp_pct",
    "latest_daily_cost_status",
    "latest_daily_source_file",
    "latest_daily_coverage_kind",
    "latest_daily_pos_reported_qty",
    "latest_daily_pos_reported_avg_price",
    "latest_daily_quantity_basis",
]


def _norm_uom(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    return "PACK" if text in {"PAC", "PACK"} else text


def _family_cost_as_of(
    cur,
    row: dict[str, Any],
    business_date: date,
) -> dict[str, Any]:
    """Resolve the family cost that was applicable on a completed POS business date.

    Authority mirrors Phase 3:
      1) valid receipt valuation
      2) official Live/Fresh/Frozen cost
      3) OH explicit-cost fallback
      4) already-resolved user-confirmed fallback when it predates the day
    """
    from family_daily_gp import apply_confirmed_selling_profile
    row=apply_confirmed_selling_profile(row)
    family_id = row.get("family_id")
    if family_id is None:
        return {"status": "NO_FAMILY"}

    # Tony confirmed 2026-10-19: loose 240/245 article 3400136 and frozen
    # pack article 1348021 share receipt cost per LB. Cost authority only;
    # inventory, POS quantities and family movement remain separate.
    shared_cost_article = None
    if str(row.get("main_article_number") or "") == "3400136" or str(row.get("ean_upc") or "") in {"24013600000","24513600000"}:
        cur.execute("SELECT family_id FROM product_family WHERE main_article_number=%s",("1348021",))
        shared = cur.fetchone()
        if shared:
            family_id = shared["family_id"]
            shared_cost_article = "1348021"

    cur.execute(
        """SELECT co.cost_per_base_uom,co.cost_amount,co.business_date,co.source_type,
                  bu.uom_code AS base_uom,cu.uom_code AS cost_uom
           FROM article_cost_observation co
           LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
           LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
           WHERE co.family_id=%s
             AND co.business_date<=%s
             AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
             """ + REJECTED_RECEIPT_SQL + """
             AND COALESCE(co.cost_per_base_uom,co.cost_amount)>0
             AND co.source_type IN (
                 'MOVEMENT_RECEIPT_VALUATION',
                 'FROZEN_INVENTORY_OFFICIAL_COST',
                 'LIVE_FRESH_SUGGESTION_OFFICIAL_COST',
                 'ON_HAND_EXPLICIT_COST_FALLBACK'
             )
           ORDER BY CASE co.source_type
                      WHEN 'MOVEMENT_RECEIPT_VALUATION' THEN 1
                      WHEN 'FROZEN_INVENTORY_OFFICIAL_COST' THEN 2
                      WHEN 'LIVE_FRESH_SUGGESTION_OFFICIAL_COST' THEN 2
                      WHEN 'ON_HAND_EXPLICIT_COST_FALLBACK' THEN 3
                      ELSE 9
                    END,
                    co.business_date DESC,
                    co.cost_observation_id DESC
           LIMIT 1""",
        (family_id, business_date),
    )
    cost = cur.fetchone()
    if not cost or cost.get('source_type') != 'MOVEMENT_RECEIPT_VALUATION':
        from supplementary_movement_cost import latest_movement_cost
        supplemental=latest_movement_cost(cur,row,business_date)
        if supplemental:
            cost={'cost_per_base_uom':supplemental['cost_value'],'cost_amount':supplemental['cost_value'],
                'business_date':supplemental['business_date'],'source_type':supplemental['source_type'],
                'base_uom':supplemental['cost_uom'],'cost_uom':supplemental['cost_uom']}
    if not cost:
        current_cost = row.get("current_cost_per_selling_unit")
        current_cost_date = row.get("cost_date")
        if (
            current_cost is not None
            and current_cost_date is not None
            and current_cost_date <= business_date
            and str(row.get("cost_source") or "").upper() == "USER_CONFIRMED_FAMILY_COST"
        ):
            return {
                "status": "RESOLVED",
                "cost_per_selling_unit": Decimal(str(current_cost)),
                "source": row.get("cost_source"),
                "date": current_cost_date,
            }
        return {"status": "NO_COST_ASOF"}

    cost_per_base = cost.get("cost_per_base_uom")
    if cost_per_base is None:
        cost_per_base = cost.get("cost_amount")
    if cost_per_base is None:
        return {"status": "NO_COST_ASOF"}

    cost_per_base = Decimal(str(cost_per_base))
    source_uom = _norm_uom(cost.get("base_uom") or cost.get("cost_uom"))
    row_base_uom = _norm_uom(row.get("base_uom"))
    selling_uom = _norm_uom(row.get("selling_uom"))
    factor_raw = row.get("base_qty_per_selling_unit")

    if source_uom and row_base_uom and source_uom == row_base_uom:
        if factor_raw not in (None, ""):
            factor = Decimal(str(factor_raw))
        elif selling_uom == row_base_uom:
            factor = Decimal("1")
        else:
            return {
                "status": "FACTOR_MISSING",
                "source": (str(cost.get("source_type"))+"_SHARED_1348021_TONY_CONFIRMED" if shared_cost_article else cost.get("source_type")),
                "date": cost.get("business_date"),
            }
        return {
            "status": "RESOLVED",
            "cost_per_selling_unit": cost_per_base * factor,
            "source": (str(cost.get("source_type"))+"_SHARED_1348021_TONY_CONFIRMED" if shared_cost_article else cost.get("source_type")),
            "date": cost.get("business_date"),
        }

    if source_uom and selling_uom and source_uom == selling_uom:
        return {
            "status": "RESOLVED",
            "cost_per_selling_unit": cost_per_base,
            "source": (str(cost.get("source_type"))+"_SHARED_1348021_TONY_CONFIRMED" if shared_cost_article else cost.get("source_type")),
            "date": cost.get("business_date"),
        }

    return {
        "status": "UOM_MISMATCH",
        "source": (str(cost.get("source_type"))+"_SHARED_1348021_TONY_CONFIRMED" if shared_cost_article else cost.get("source_type")),
        "date": cost.get("business_date"),
    }


def _fetch_latest_daily_sales(
    cur,
    batch_id: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Attach exact latest completed canonical Seafood POS-day metrics to Quick Check rows."""
    # coverage_summary is bounded to the latest completed business day.
    coverage = coverage_summary(cur, "sales_by_price_type", include_batch_id=int(batch_id))
    from pos_evidence import eligible_sales_days
    eligible = eligible_sales_days(source_data_days(cur,"sales_by_price_type",include_batch_id=int(batch_id),up_to=coverage.get("latest_valid_date")))
    target_date = eligible[0]['date'] if eligible else None
    if target_date is None:
        return {
            "business_date": None,
            "coverage_kind": None,
            "source_file": None,
            "sales_dollars": Decimal("0"),
            "pos_qty": Decimal("0"),
            "cogs": Decimal("0"),
            "gp_dollars": Decimal("0"),
            "gp_pct": None,
            "gp_status": "NO_DAILY_POS",
            "cost_unresolved_sales": Decimal("0"),
            "unmapped_sales": Decimal("0"),
            "sales_row_count": 0,
        }
    canonical = [
        d for d in source_data_days(
            cur,
            "sales_by_price_type",
            include_batch_id=int(batch_id),
            up_to=target_date,
        )
        if d.get("date") == target_date
    ]
    if not canonical:
        return {
            "business_date": target_date,
            "coverage_kind": None,
            "source_file": None,
            "sales_dollars": Decimal("0"),
            "pos_qty": Decimal("0"),
            "cogs": Decimal("0"),
            "gp_dollars": Decimal("0"),
            "gp_pct": None,
            "gp_status": "NO_CANONICAL_DAY",
            "cost_unresolved_sales": Decimal("0"),
            "unmapped_sales": Decimal("0"),
            "sales_row_count": 0,
        }

    day = canonical[0]
    file_id = int(day["file_id"])
    coverage_kind = str(day.get("coverage_kind") or "")
    source_file = str(day.get("original_filename") or "")

    if coverage_kind == "DERIVED_PERIOD_RESIDUAL":
        cur.execute(
            """SELECT b.ean_upc,MAX(b.upc_id) AS upc_id,MAX(b.description) AS description,
                      COALESCE(SUM(b.sales_amount),0) AS sales_dollars,
                      COALESCE(SUM(b.sold_quantity),0) AS pos_qty,
                      COUNT(DISTINCT UPPER(TRIM(b.price_type))) AS price_type_count,
                      GROUP_CONCAT(DISTINCT UPPER(TRIM(b.price_type))
                                   ORDER BY UPPER(TRIM(b.price_type)) SEPARATOR '+') AS price_types
               FROM pos_daily_backfill_observation b
               WHERE b.source_file_id=%s
                 AND b.business_date=%s
                 AND EXISTS (
                     SELECT 1
                     FROM upc_department_observation d
                     WHERE d.file_id=b.source_file_id
                       AND d.ean_upc=b.ean_upc
                       AND d.source_type='POS'
                       AND UPPER(TRIM(d.department_name))='SEAFOOD'
                 )
               GROUP BY b.ean_upc
               ORDER BY b.ean_upc""",
            (file_id, target_date),
        )
    else:
        cur.execute(
            """SELECT s.ean_upc,MAX(s.upc_id) AS upc_id,MAX(s.description) AS description,
                      COALESCE(SUM(s.sales_amount),0) AS sales_dollars,
                      COALESCE(SUM(s.sold_quantity),0) AS pos_qty,
                      COUNT(DISTINCT UPPER(TRIM(s.price_type))) AS price_type_count,
                      GROUP_CONCAT(DISTINCT UPPER(TRIM(s.price_type))
                                   ORDER BY UPPER(TRIM(s.price_type)) SEPARATOR '+') AS price_types
               FROM sales_period_observation s
               WHERE s.file_id=%s
                 AND s.period_start_date=%s
                 AND s.period_end_date=%s
                 AND s.temporal_grain='SINGLE_DATE'
                 AND EXISTS (
                     SELECT 1
                     FROM upc_department_observation d
                     WHERE d.file_id=s.file_id
                       AND d.sheet_id=s.sheet_id
                       AND d.source_row_number=s.source_row_number
                       AND d.ean_upc=s.ean_upc
                       AND d.source_type='POS'
                       AND UPPER(TRIM(d.department_name))='SEAFOOD'
                 )
               GROUP BY s.ean_upc
               ORDER BY s.ean_upc""",
            (file_id, target_date, target_date),
        )
    observed = list(cur.fetchall())

    by_upc_id = {
        int(r["upc_id"]): r for r in rows if r.get("upc_id") is not None
    }
    by_ean = {
        str(r.get("ean_upc") or "").strip(): r
        for r in rows
        if str(r.get("ean_upc") or "").strip()
    }

    row_obs: dict[int, dict[str, Any]] = {}
    unmapped_sales = Decimal("0")
    total_sales = Decimal("0")
    total_qty = Decimal("0")
    for obs in observed:
        sales = Decimal(str(obs.get("sales_dollars") or 0))
        qty = Decimal(str(obs.get("pos_qty") or 0))
        total_sales += sales
        total_qty += qty
        row = None
        if obs.get("upc_id") is not None:
            row = by_upc_id.get(int(obs["upc_id"]))
        if row is None:
            row = by_ean.get(str(obs.get("ean_upc") or "").strip())
        if row is None:
            unmapped_sales += sales
            continue
        key = int(row["upc_id"])
        agg = row_obs.setdefault(
            key,
            {
                "sales": Decimal("0"),
                "qty": Decimal("0"),
                "price_types": set(),
            },
        )
        agg["sales"] += sales
        agg["qty"] += qty
        for pt in str(obs.get("price_types") or "").split("+"):
            pt = pt.strip()
            if pt:
                agg["price_types"].add(pt)

    cost_cache: dict[Any, dict[str, Any]] = {}
    total_cogs = Decimal("0")
    total_gp = Decimal("0")
    unresolved_sales = Decimal("0")
    sales_row_count = 0

    for row in rows:
        row["latest_daily_business_date"] = target_date
        row["latest_daily_source_file"] = source_file
        row["latest_daily_coverage_kind"] = coverage_kind
        obs = row_obs.get(int(row["upc_id"])) if row.get("upc_id") is not None else None
        if not obs:
            row["latest_daily_sales_dollars"] = Decimal("0")
            row["latest_daily_pos_qty"] = Decimal("0")
            row["latest_daily_avg_sold_price"] = None
            row["latest_daily_price_type"] = None
            row["latest_daily_cost_per_selling_unit"] = None
            row["latest_daily_cost_source"] = None
            row["latest_daily_cost_date"] = None
            row["latest_daily_cogs"] = Decimal("0")
            row["latest_daily_gp_dollars"] = Decimal("0")
            row["latest_daily_gp_pct"] = None
            row["latest_daily_cost_status"] = "ZERO_SALES"
            continue

        sales = obs["sales"]
        qty = obs["qty"]
        sales_row_count += 1
        row["latest_daily_sales_dollars"] = sales
        row["latest_daily_pos_qty"] = qty
        row["latest_daily_avg_sold_price"] = (sales / qty) if qty != 0 else None
        pts = sorted(obs["price_types"])
        row["latest_daily_price_type"] = pts[0] if len(pts) == 1 else ("MIXED" if pts else None)

        from pos_evidence import verified_pos_quantity
        verified,basis=verified_pos_quantity(row,{'sold_quantity':qty,'sales_amount':sales,'price_types':{p:{} for p in pts}},target_date)
        row['latest_daily_pos_reported_qty']=qty
        row['latest_daily_pos_reported_avg_price']=sales/qty if qty else None
        row['latest_daily_quantity_basis']=basis
        if verified is None:
            row.update(latest_daily_pos_qty=None,latest_daily_avg_sold_price=None,
                latest_daily_cogs=None,latest_daily_gp_dollars=None,latest_daily_gp_pct=None,
                latest_daily_cost_status='QUANTITY_OR_UNIT_UNVERIFIED')
            unresolved_sales+=abs(sales)
            continue
        qty=verified
        family_key = (row.get("family_id"),row.get("selling_uom"),row.get("base_qty_per_selling_unit"),row.get("article_number"))
        cost = cost_cache.get(family_key)
        if cost is None:
            cost = _family_cost_as_of(cur, row, target_date)
            cost_cache[family_key] = cost

        row["latest_daily_cost_status"] = cost.get("status")
        row["latest_daily_cost_per_selling_unit"] = cost.get("cost_per_selling_unit")
        row["latest_daily_cost_source"] = cost.get("source")
        row["latest_daily_cost_date"] = cost.get("date")
        if cost.get("status") == "RESOLVED" and qty != 0:
            cogs = qty * Decimal(str(cost["cost_per_selling_unit"]))
            gp = sales - cogs
            row["latest_daily_cogs"] = cogs
            row["latest_daily_gp_dollars"] = gp
            row["latest_daily_gp_pct"] = (gp / sales) if sales != 0 else None
            total_cogs += cogs
            total_gp += gp
        elif cost.get("status") == "RESOLVED":
            row["latest_daily_cogs"] = Decimal("0")
            row["latest_daily_gp_dollars"] = sales
            row["latest_daily_gp_pct"] = (Decimal("1") if sales != 0 else None)
            total_gp += sales
        else:
            row["latest_daily_cogs"] = None
            row["latest_daily_gp_dollars"] = None
            row["latest_daily_gp_pct"] = None
            unresolved_sales += abs(sales)

    unresolved_sales += abs(unmapped_sales)
    gp_complete = unresolved_sales <= Decimal("0.0001")
    return {
        "business_date": target_date,
        "coverage_kind": coverage_kind,
        "source_file": source_file,
        "sales_dollars": total_sales,
        "pos_qty": None,  # Department units are mixed; use individual UPC units.
        "cogs": total_cogs if gp_complete else None,
        "gp_dollars": total_gp if gp_complete else None,
        "gp_pct": (total_gp / total_sales) if gp_complete and total_sales != 0 else None,
        "gp_status": "COMPLETE" if gp_complete else "PARTIAL_COST_OR_MAPPING",
        "cost_unresolved_sales": unresolved_sales,
        "unmapped_sales": unmapped_sales,
        "sales_row_count": sales_row_count,
    }



def _fetch_recent_3d_sales(
    cur,
    batch_id: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Attach strict latest-3 completed canonical POS metrics to every serving UPC.

    Missing calendar dates are ignored rather than zero-filled. UPC sold quantity
    remains POS-only. These fields are exported to the ChatGPT bridge so 3-day
    TPR and recent-sales analysis never has to infer a 3D window from 7D totals.
    """
    from pos_evidence import eligible_sales_days
    coverage = coverage_summary(
        cur,
        "sales_by_price_type",
        include_batch_id=int(batch_id),
    )
    target_date = coverage.get("latest_valid_date")
    days = []
    if target_date is not None:
        days = sorted(
            eligible_sales_days(source_data_days(
                cur,
                "sales_by_price_type",
                include_batch_id=int(batch_id),
                up_to=target_date,
            )),
            key=lambda x: x["date"],
        )[-3:]

    start_date = min((x["date"] for x in days), default=None)
    end_date = max((x["date"] for x in days), default=None)
    supported_days = len(days)
    coverage_status = "COMPLETE" if supported_days >= 3 else "PARTIAL"

    by_upc_id = {
        int(r["upc_id"]): r for r in rows if r.get("upc_id") is not None
    }
    by_ean = {
        str(r.get("ean_upc") or "").strip(): r
        for r in rows
        if str(r.get("ean_upc") or "").strip()
    }

    aggregates: dict[int, dict[str, Any]] = {}
    for row in rows:
        row["pos_3d_window_start"] = start_date
        row["pos_3d_window_end"] = end_date
        row["pos_3d_supported_days"] = supported_days
        row["sales_dollars_3d"] = Decimal("0")
        row["pos_qty_3d"] = Decimal("0")
        row["upc_velocity_3d"] = Decimal("0") if supported_days else None
        row["selling_days_3d"] = 0
        row["pos_3d_coverage_status"] = coverage_status
        row["pos_3d_data_day_definition"] = (
            "LATEST_3_COMPLETED_CANONICAL_POS_DATA_DAYS"
        )

    for day in days:
        file_id = int(day["file_id"])
        business_date = day["date"]
        coverage_kind = str(day.get("coverage_kind") or "")
        if coverage_kind == "DERIVED_PERIOD_RESIDUAL":
            cur.execute(
                """SELECT b.ean_upc,MAX(b.upc_id) AS upc_id,
                          COALESCE(SUM(b.sales_amount),0) AS sales_dollars,
                          COALESCE(SUM(b.sold_quantity),0) AS pos_qty
                   FROM pos_daily_backfill_observation b
                   WHERE b.source_file_id=%s
                     AND b.business_date=%s
                     AND EXISTS (
                         SELECT 1
                         FROM upc_department_observation d
                         WHERE d.file_id=b.source_file_id
                           AND d.ean_upc=b.ean_upc
                           AND d.source_type='POS'
                           AND UPPER(TRIM(d.department_name))='SEAFOOD'
                     )
                   GROUP BY b.ean_upc""",
                (file_id, business_date),
            )
        else:
            cur.execute(
                """SELECT s.ean_upc,MAX(s.upc_id) AS upc_id,
                          COALESCE(SUM(s.sales_amount),0) AS sales_dollars,
                          COALESCE(SUM(s.sold_quantity),0) AS pos_qty
                   FROM sales_period_observation s
                   WHERE s.file_id=%s
                     AND s.period_start_date=%s
                     AND s.period_end_date=%s
                     AND s.temporal_grain='SINGLE_DATE'
                     AND EXISTS (
                         SELECT 1
                         FROM upc_department_observation d
                         WHERE d.file_id=s.file_id
                           AND d.sheet_id=s.sheet_id
                           AND d.source_row_number=s.source_row_number
                           AND d.ean_upc=s.ean_upc
                           AND d.source_type='POS'
                           AND UPPER(TRIM(d.department_name))='SEAFOOD'
                     )
                   GROUP BY s.ean_upc""",
                (file_id, business_date, business_date),
            )

        day_seen: set[int] = set()
        for obs in cur.fetchall():
            row = None
            if obs.get("upc_id") is not None:
                row = by_upc_id.get(int(obs["upc_id"]))
            if row is None:
                row = by_ean.get(str(obs.get("ean_upc") or "").strip())
            if row is None or row.get("upc_id") is None:
                continue
            uid = int(row["upc_id"])
            agg = aggregates.setdefault(
                uid,
                {"sales": Decimal("0"), "qty": Decimal("0"), "selling_days": 0},
            )
            sales = Decimal(str(obs.get("sales_dollars") or 0))
            qty = Decimal(str(obs.get("pos_qty") or 0))
            agg["sales"] += sales
            agg["qty"] += qty
            if qty != 0 and uid not in day_seen:
                agg["selling_days"] += 1
                day_seen.add(uid)

    for row in rows:
        uid = int(row["upc_id"]) if row.get("upc_id") is not None else None
        agg = aggregates.get(uid) if uid is not None else None
        if not agg:
            continue
        row["sales_dollars_3d"] = agg["sales"]
        row["pos_qty_3d"] = agg["qty"]
        row["selling_days_3d"] = agg["selling_days"]
        row["upc_velocity_3d"] = (
            agg["qty"] / Decimal(supported_days)
            if supported_days
            else None
        )

    return {
        "window_start": start_date,
        "window_end": end_date,
        "supported_days": supported_days,
        "coverage_status": coverage_status,
        "data_day_definition": "LATEST_3_COMPLETED_CANONICAL_POS_DATA_DAYS",
    }


def _protect_current_export(rows, source_days):
    from pos_evidence import eligible_sales_days
    from family_daily_gp import confirmed_pos_lb
    allowed={(str(d['date']),str(d.get('file_id'))) for d in eligible_sales_days(source_days)}
    held=[d for d in source_days[:30] if (str(d['date']),str(d.get('file_id'))) not in allowed]
    aggregate_columns=['sales_dollars_7d','sales_dollars_30d','pos_qty_7d','pos_qty_30d',
        'upc_velocity_7d','upc_velocity_30d','sales_days_7d','sales_days_30d',
        'gp_dollars_7d','gp_per_day_7d','gp_pct_current','sweet_spot_price','wgpm_price','dos']
    for row in rows:
        if held:
            for key in aggregate_columns:row[key]=None
            row['blocking_reason']='; '.join(filter(None,[row.get('blocking_reason'),'SOURCE_QUALITY_HOLD: legacy rolling POS metrics withheld; use eligible dated history']))
        if str(row.get('selling_uom') or '').upper()=='LB':
            q=confirmed_pos_lb({**row,'latest_daily_pos_reported_qty':1},row.get('latest_daily_business_date'))
            if q is None:
                for key in ['pos_qty_7d','pos_qty_30d','pos_qty_3d','upc_velocity_7d','upc_velocity_30d','upc_velocity_3d','gp_dollars_7d','gp_per_day_7d','dos']:row[key]=None
        # Configured company references retain their own columns. The selling
        # price field is an achieved POS average only, never a Price List value.
        row['current_price']=row.get('latest_daily_avg_sold_price')
        row['current_price_type']='POS_REALIZED_AVERAGE' if row['current_price'] is not None else None
        row['current_price_source']='CANONICAL_POS_REALIZED_AVERAGE' if row['current_price'] is not None else 'POS_PRICE_UNVERIFIED'
        row['current_price_asof_date']=row.get('latest_daily_business_date')
        row['gp_pct_current']=None  # A historical achieved average is not a current-ticket margin.
    return held


def _fetch_quick_rows(cur) -> list[dict[str, Any]]:
    cur.execute("SELECT " + ",".join(QC_COLUMNS) + " FROM quick_check_current ORDER BY ean_upc")
    from family_daily_gp import apply_confirmed_selling_profile
    rows = [apply_confirmed_selling_profile(r) for r in cur.fetchall()]
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
    export_columns = QC_COLUMNS + DERIVED_QC_COLUMNS + POS_3D_COLUMNS + LATEST_DAILY_COLUMNS
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

    QA_HOLD rows remain isolated in MYSQL_QA_HOLD. HISTORICAL_ONLY rows remain
    searchable in MYSQL_QUICK_CHECK_CURRENT but are neither analytical input nor
    QA HOLD rows.
    """
    ready = [
        row for row in rows
        if str(row.get("quick_check_status") or "").upper() == "READY"
    ]
    out = [["Sheet_Row"] + ANALYSIS_COLUMNS + POS_3D_COLUMNS + LATEST_DAILY_COLUMNS + ["Analysis_Source"]]
    for sheet_row, row in enumerate(ready, start=2):
        out.append(
            [sheet_row]
            + [row.get(col) for col in ANALYSIS_COLUMNS]
            + [row.get(col) for col in POS_3D_COLUMNS]
            + [row.get(col) for col in LATEST_DAILY_COLUMNS]
            + ["FULL_MYSQL_PHASE3_READY_ONLY"]
        )
    return out


def _build_qa(rows: list[dict[str, Any]]) -> list[list[Any]]:
    """Export only true operational QA HOLD rows.

    HISTORICAL_ONLY is an informational/current-activity classification, not a
    blocker. In particular, NO_POS_SALES_LATEST_28_VALID_DATA_DAYS must never
    appear in MYSQL_QA_HOLD or contribute to hold/excluded counts.
    """
    header = ["Sheet_Row","ean_upc","main_article_number","article_number","selling_description",
              "selling_uom","current_price","current_cost_per_selling_unit","pos_qty_7d",
              "quick_check_status","blocking_reason","publish_batch_id"]
    out = [header]
    for sheet_row, row in enumerate(rows, start=2):
        if str(row.get("quick_check_status") or "").upper() == "QA_HOLD":
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
        # Keep all families with actual daily POS sales in department reconciliation.
        # UPC readiness never determines whether department revenue exists.
        if not ready_rs and not any(Decimal(str(r.get('latest_daily_sales_dollars') or 0)) != 0 for r in rs):
            continue
        representative = max(
            ready_rs or rs,
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


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    iso = getattr(value, "isoformat", None)
    return iso() if callable(iso) else str(value)


def _canonical_freshness(cur, batch_id: int) -> dict[str, Any]:
    """Compute serving freshness from FULL MYSQL canonical coverage only."""
    bid = int(batch_id)
    pos = coverage_summary(cur, "sales_by_price_type", include_batch_id=bid)
    mvt = coverage_summary(cur, "movement", include_batch_id=bid)

    pos_days = source_data_days(
        cur,
        "sales_by_price_type",
        limit=1,
        include_batch_id=bid,
        up_to=pos.get("latest_valid_date") or pos.get("expected_through"),
    )
    mvt_days = source_data_days(
        cur,
        "movement",
        limit=1,
        include_batch_id=bid,
        up_to=mvt.get("latest_valid_date") or mvt.get("expected_through"),
    )
    pos_latest = pos_days[0] if pos_days else {}
    mvt_latest = mvt_days[0] if mvt_days else {}

    return {
        "authority": "FULL_MYSQL_CANONICAL_COVERAGE",
        "pos_data_through": _iso_date(pos.get("latest_valid_date")),
        "pos_expected_through": _iso_date(pos.get("expected_through")),
        "pos_status": pos.get("status"),
        "pos_source": pos_latest.get("original_filename") or "",
        "movement_data_through": _iso_date(mvt.get("latest_valid_date")),
        "movement_expected_through": _iso_date(mvt.get("expected_through")),
        "movement_status": mvt.get("status"),
        "movement_source": mvt_latest.get("original_filename") or "",
    }


def _source_status(
    batch: dict[str, Any],
    phase3: dict[str, Any],
    row_count: int,
    *,
    analysis_ready_rows: int,
    analysis_family_rows: int,
    analysis_hold_rows: int,
    freshness: dict[str, Any],
    latest_daily: dict[str, Any],
    recent_3d: dict[str, Any],
) -> list[list[Any]]:
    fields = [
        ("Snapshot_Status","MYSQL_PUBLISH_READY"),("MySQL_Batch_ID",batch.get("batch_id")),
        ("MySQL_Batch_Key",batch.get("batch_key")),("MySQL_Batch_Label",batch.get("batch_label")),
        ("MySQL_Batch_Status",batch.get("processing_status")),("Phase3_Result_Status",phase3.get("result_status")),
        ("Freshness_Authority",freshness.get("authority")),
        ("POS_Data_Through",freshness.get("pos_data_through")),
        ("POS_Expected_Through",freshness.get("pos_expected_through")),
        ("POS_Coverage_Status",freshness.get("pos_status")),
        ("POS_Canonical_Source",freshness.get("pos_source")),
        ("Movement_Data_Through",freshness.get("movement_data_through")),
        ("Movement_Expected_Through",freshness.get("movement_expected_through")),
        ("Movement_Coverage_Status",freshness.get("movement_status")),
        ("Canonical_Movement_Source",freshness.get("movement_source")),
        ("Phase3_Blocking_Issues",phase3.get("blocking_issue_count")),("Current_Active_Rows",phase3.get("quick_check_rows")),
        ("Current_READY_Rows",phase3.get("quick_check_ready_rows")),("Current_HOLD_Rows",phase3.get("quick_check_hold_rows")),
        ("Serving_Rows_Total",row_count),
        ("Analysis_READY_Rows",analysis_ready_rows),
        ("Analysis_Family_Rows",analysis_family_rows),
        ("Analysis_Excluded_HOLD_Rows",analysis_hold_rows),
        ("Analysis_Input_Policy","READY_IDENTITY; METRIC_EVIDENCE_GATES_APPLY"),
        ("Latest_Daily_Business_Date",latest_daily.get("business_date")),
        ("Latest_Daily_Coverage_Kind",latest_daily.get("coverage_kind")),
        ("Latest_Daily_Source",latest_daily.get("source_file")),
        ("Latest_Daily_Seafood_Sales",latest_daily.get("sales_dollars")),
        ("Latest_Daily_Seafood_POS_Qty",latest_daily.get("pos_qty")),
        ("Latest_Daily_Seafood_COGS",latest_daily.get("cogs")),
        ("Latest_Daily_Seafood_GP_Dollars",latest_daily.get("gp_dollars")),
        ("Latest_Daily_Seafood_GP_Pct",latest_daily.get("gp_pct")),
        ("Latest_Daily_GP_Status",latest_daily.get("gp_status")),
        ("Family_MVT_GP_Status",latest_daily.get("family_mvt_gp",{}).get("status")),
        ("Family_MVT_Family_Count",latest_daily.get("family_mvt_gp",{}).get("family_count")),
        ("Family_MVT_Department_GP",latest_daily.get("family_mvt_gp",{}).get("gp")),
        ("Family_MVT_Verified_GP_Subtotal",latest_daily.get("family_mvt_gp",{}).get("verified_family_gp_subtotal")),
        ("Family_MVT_Unresolved_Sales",latest_daily.get("family_mvt_gp",{}).get("unresolved_sales")),
        ("Latest_Daily_Cost_Unresolved_Sales",latest_daily.get("cost_unresolved_sales")),
        ("Latest_Daily_Unmapped_Sales",latest_daily.get("unmapped_sales")),
        ("Latest_Daily_Sales_Row_Count",latest_daily.get("sales_row_count")),
        ("POS_3D_Window_Start",recent_3d.get("window_start")),
        ("POS_3D_Window_End",recent_3d.get("window_end")),
        ("POS_3D_Supported_Days",recent_3d.get("supported_days")),
        ("POS_3D_Coverage_Status",recent_3d.get("coverage_status")),
        ("POS_3D_Data_Day_Definition",recent_3d.get("data_day_definition")),
        ("Snapshot_Published_At_UTC",datetime.now(timezone.utc).isoformat()),
        ("Publisher","FULL_MYSQL_CHATGPT_SHEET_BRIDGE"),("Active_ChatGPT_Source",_active_source()),
        ("Analysis_Cutover_Status","READY_ONLY_SAFE_PARTIAL"),
    ]
    fields.extend([("Sales_And_Achieved_Price_Authority","POS_ONLY"),("Current_Price_Basis","POS_REALIZED_AVERAGE_NOT_ONE_APPLIED_PRICE"),("Held_Source_Policy","Affected legacy rolling metrics withheld; use eligible dated POS history"),("Department_Quantity_Policy","Do not sum LB, EA or PACK")])
    family_summary=latest_daily.get("family_mvt_gp",{})
    fields.extend([
        ("Department_GP_Best_Estimate",family_summary.get("estimated_department_gp")),
        ("Department_GP_Pct_Best_Estimate",family_summary.get("estimated_department_gp_pct")),
        ("Department_GP_Estimate_Status",family_summary.get("estimate_status")),
        ("Department_GP_Estimate_Assumptions",json.dumps(family_summary.get("estimate_details",[]),default=str)),
        ("Family_GP_Blocking_Family_Count",len(family_summary.get("blockers",[]))),
        ("Family_GP_Blockers",json.dumps(family_summary.get("blockers",[]),default=str)),
        ("Family_GP_Resolved_Sales",family_summary.get("resolved_sales")),
        ("Family_GP_Sales_Reconciliation_Gap",family_summary.get("sales_reconciliation_gap")),
    ])
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


def _validate_readback_once(
    session,
    spreadsheet_id: str,
    batch_id: int,
    row_count: int,
    *,
    analysis_row_count: int,
    reader=None,
    expected_matrices=None,
) -> dict[str, Any]:
    read = reader or _read_values
    source = read(session, spreadsheet_id, f"'{MYSQL_TABS['source']}'!A1:B40")
    lookup_head = read(session, spreadsheet_id, f"'{MYSQL_TABS['lookup']}'!A1:I2")
    lookup_tail = read(session, spreadsheet_id,
                       f"'{MYSQL_TABS['lookup']}'!A{row_count + 1}:I{row_count + 1}")
    analysis_head = read(session, spreadsheet_id, f"'{MYSQL_TABS['analysis']}'!A1:B2")
    analysis_tail = read(
        session,
        spreadsheet_id,
        f"'{MYSQL_TABS['analysis']}'!A{analysis_row_count + 1}:B{analysis_row_count + 1}",
    )
    family_daily_head = read(session, spreadsheet_id, f"'{MYSQL_TABS["family"]}'!S1:AN2")
    source_map = {str(r[0]): r[1] if len(r) > 1 else "" for r in source[1:] if r}
    failures: list[str] = []
    if not family_daily_head or family_daily_head[0][:3] != ["daily_department", "daily_date", "daily_family_id"]:
        failures.append("FAMILY_DAILY_HEADER_MISMATCH")
    if len(family_daily_head)>1 and len(family_daily_head[1])>17 and family_daily_head[1][17] not in (None, "") and str(family_daily_head[1][17]) != str(batch_id):
        failures.append("FAMILY_DAILY_BATCH_MISMATCH")
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
    if expected_matrices:
        from price_history_analysis import verify_history_tables
        try:
            verify_history_tables({t:[[_wire(v) for v in r] for r in m] for t,m in expected_matrices.items()}, lambda title,start,end,width:
                read(session,spreadsheet_id,f"'{title}'!A{start}:{_col_letters(width)}{end}"))
        except ValueError as exc:
            failures.append(str(exc))
    return {
        "full_cell_readback":bool(expected_matrices) and not failures,
        "pass":not failures,
        "failures":failures,
        "source_status":source_map,
        "expected_last_sheet_row":expected_last_sheet_row,
        "expected_analysis_last_row":expected_analysis_last_row,
    }


def _validate_readback(
    session,
    spreadsheet_id: str,
    batch_id: int,
    row_count: int,
    *,
    analysis_row_count: int,
    reader=None,
    expected_matrices=None,
    attempts: int = 3,
    retry_delay_seconds: float = 1.0,
) -> dict[str, Any]:
    """Retry readback to absorb short Google Sheets/Apps Script propagation lag."""
    last: dict[str, Any] = {}
    total = max(1, int(attempts))
    for attempt in range(1, total + 1):
        last = _validate_readback_once(
            session,
            spreadsheet_id,
            batch_id,
            row_count,
            analysis_row_count=analysis_row_count,
            reader=reader,
            expected_matrices=expected_matrices,
        )
        last["attempts"] = attempt
        if last.get("pass"):
            return last
        if attempt < total:
            time.sleep(max(0.0, float(retry_delay_seconds)))
    return last


def publish_chatgpt_snapshot(batch_id: int, *, progress=None) -> dict[str, Any]:
    if not bridge_enabled():
        return {"status":"DISABLED","batch_id":batch_id,
                "reason":"FULLMYSQL_CHATGPT_SHEET_ENABLED is not enabled."}
    spreadsheet_id: str | None = None
    transport: str | None = None
    publish_row_count = 0
    started = time.monotonic()
    def stage(name):
        if progress:progress(name, round(time.monotonic()-started, 1))
    try:
        stage('PREPARING_CURRENT')
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
                freshness = _canonical_freshness(cur, batch_id)
                latest_daily = _fetch_latest_daily_sales(cur, batch_id, rows)
                recent_3d = _fetch_recent_3d_sales(cur, batch_id, rows)
                stage('PREPARING_MOVEMENT_EVIDENCE')
                from inventory_gp_adjustments import build_adjustment_export
                adjustment_matrix, adjustment_coverage = build_adjustment_export(
                    cur, rows, batch_id, freshness["pos_data_through"])
                from analysis_movement import build_movement_export
                movement_export = build_movement_export(cur, rows, batch_id, freshness["pos_data_through"])
                from analysis_pos import build_pos_export
                stage('PREPARING_TYPED_POS')
                pos_export = build_pos_export(cur, rows, batch_id)
                from family_daily_gp import build_family_daily
                stage('PREPARING_FAMILY_GP')
                family_daily_matrix, family_daily_summary = build_family_daily(cur, rows, latest_daily, batch_id)
                latest_daily["family_mvt_gp"] = family_daily_summary
                from business_clock import completed_through_date
                history_days = source_data_days(cur, "sales_by_price_type", limit=3650,
                    up_to=completed_through_date())
                # Routine rebuilds retain unchanged historical rows from older batches.
                # Only the newest serving revision determines whether this export
                # is stale; older preserved rows must not block publication.
                if rows and max(int(r.get("publish_batch_id") or 0) for r in rows) != int(batch_id):
                    return {"status":"SUPERSEDED","batch_id":batch_id,
                            "reason":"A newer serving snapshot is ready; publish its revision."}
            finally:
                cur.close()

        if not rows:
            return {"status":"BLOCKED","batch_id":batch_id,"reason":"quick_check_current is empty."}

        publish_row_count = len(rows)
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
        stage('WRITING_CURRENT')

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

        _protect_current_export(rows,history_days)
        analysis_matrix = _build_analysis(rows)
        family_matrix = _build_family(rows)
        daily_by_family = {str(r[2]): r for r in family_daily_matrix[1:]}
        daily_width = len(family_daily_matrix[0])
        family_matrix = [family_matrix[0] + ["daily_"+str(c) for c in family_daily_matrix[0]]] + [r + daily_by_family.get(str(r[0]), [None]*daily_width) for r in family_matrix[1:]]
        analysis_row_count = max(0, len(analysis_matrix) - 1)
        analysis_family_count = max(0, len(family_matrix) - 1)

        matrices = {
            MYSQL_TABS["source"]:_source_status(
                batch,
                phase3,
                len(rows),
                analysis_ready_rows=analysis_row_count,
                analysis_family_rows=analysis_family_count,
                analysis_hold_rows=len(hold_rows),
                freshness=freshness,
                latest_daily=latest_daily,
                recent_3d=recent_3d,
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
                stage('WRITING_'+title)
                _apps_script_write_matrix(spreadsheet_id, title, matrix)
            stage('VERIFYING_CURRENT')
            readback = _validate_readback(
                None,
                spreadsheet_id,
                batch_id,
                len(rows),
                analysis_row_count=analysis_row_count,
                expected_matrices=matrices,
                reader=lambda _session, sid, a1: _apps_script_read_values(sid, a1),
            )
        else:
            session, publisher_identity = _session()
            _ensure_tabs(session, spreadsheet_id, list(matrices) + [MYSQL_TABS["bridge"]])
            for title, matrix in matrices.items():
                _write_matrix(session, spreadsheet_id, title, matrix)
            stage('VERIFYING_CURRENT')
            readback = _validate_readback(
                session,
                spreadsheet_id,
                batch_id,
                len(rows),
                analysis_row_count=analysis_row_count,
                expected_matrices=matrices,
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

        from upload_history_publish import publish_upload_history
        stage('PUBLISHING_HISTORY')
        def history_transport_reader(title, start, end, width):
            a1=f"'{title}'!A{start}:{_col_letters(width)}{end}"
            return (_apps_script_read_values(spreadsheet_id,a1) if transport == "APPS_SCRIPT"
                    else _read_values(session,spreadsheet_id,a1))
        def history_reader(title, start, end, width):
            from price_history_analysis import bounded_history_read
            return bounded_history_read(history_transport_reader,title,start,end,width)
        def history_writer(title,matrix,previous=None):
            if previous is not None:
                _write_changed_history(session,spreadsheet_id,title,matrix,previous,transport)
            elif transport == "APPS_SCRIPT":
                _apps_script_write_matrix(spreadsheet_id,title,matrix)
            else:
                _ensure_tabs(session,spreadsheet_id,[title])
                _write_matrix(session,spreadsheet_id,title,matrix,chunk_rows=1500)
        history = publish_upload_history(rows=rows,source_days=history_days,batch_id=batch_id,
            through=freshness["pos_data_through"],reader=history_reader,writer=history_writer)
        # Use bridge-approved tables: no Apps Script permissions/deployment change.
        from inventory_gp_adjustments import publish_supported_adjustments
        stage('PUBLISHING_MOVEMENT_AND_POS_LEDGER')
        readback["inventory_adjustments"] = publish_supported_adjustments(
            history_reader,history_writer,adjustment_matrix,adjustment_coverage,movement_export,pos_export)
        stage('VERIFYING_FINAL_REVISION')
        # A concurrent upload cannot certify an older export as current.
        with db_conn() as conn:
            cur=conn.cursor(dictionary=True,buffered=True)
            try:
                cur.execute("SELECT MIN(publish_batch_id) AS lo, MAX(publish_batch_id) AS hi FROM quick_check_current")
                current=cur.fetchone() or {}
                # Older preserved rows are expected. A changed newest revision
                # still invalidates this export before certification.
                if int(current.get("hi") or 0)!=int(batch_id):
                    raise RuntimeError("Serving snapshot changed during Google publication; retry newest batch")
            finally:cur.close()
        readback["history"]=history["readback"]
        readback["history_source_revision"]=history["revision"]
        readback["history_data_through"]=history["through"]

        bridge_matrix = _bridge_status(
            batch_id=batch_id,
            row_count=len(rows),
            publisher_identity=publisher_identity,
            transport=transport,
            status="PASS",
            detail=(
                f"READY-only analytical snapshot published: {analysis_row_count} READY rows; "
                f"{len(hold_rows)} true QA HOLD rows excluded to MYSQL_QA_HOLD; "
                "HISTORICAL_ONLY rows remain verification-only."
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
            "history_contract":HISTORY_CONTRACT,
            "history":history,
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
        error = repr(exc)
        # Never leave readers stuck on PUBLISHING after a transport failure.
        # Best-effort write a terminal FAILED state; preserve the original error
        # if even that status write cannot be completed.
        if spreadsheet_id and transport:
            try:
                failed_matrix = _bridge_status(
                    batch_id=batch_id,
                    row_count=publish_row_count,
                    publisher_identity=(
                        "GOOGLE_APPS_SCRIPT_WEB_APP"
                        if transport == "APPS_SCRIPT"
                        else "GOOGLE_SERVICE_ACCOUNT"
                    ),
                    transport=transport,
                    status="FAILED",
                    detail=error[:1000],
                )
                if transport == "APPS_SCRIPT":
                    _apps_script_write_matrix(
                        spreadsheet_id,
                        MYSQL_TABS["bridge"],
                        failed_matrix,
                    )
                else:
                    failed_session, _ = _session()
                    _ensure_tabs(
                        failed_session,
                        spreadsheet_id,
                        [MYSQL_TABS["bridge"]],
                    )
                    _write_matrix(
                        failed_session,
                        spreadsheet_id,
                        MYSQL_TABS["bridge"],
                        failed_matrix,
                    )
            except Exception:
                pass
        return {"status":"FAILED","batch_id":batch_id,"error":error}




def _write_changed_history(session, spreadsheet_id, title, matrix, previous, transport):
    """Rewrite only differing bounded chunks; never clear retained history first."""
    width=len(matrix[0]);end_col=_col_letters(width)
    size=max(1,min(1500,40000//width))
    for start in range(0,max(len(matrix),len(previous)),size):
        target=matrix[start:start+size]
        prior=previous[start:start+size]
        normalize=lambda rows:[[_wire(v) for v in r]+[""]*(width-len(r)) for r in rows]
        if normalize(target)==normalize(prior):continue
        target=normalize(target)+[[""]*width for _ in range(max(0,len(prior)-len(target)))]
        if not target:continue
        if transport=="APPS_SCRIPT":
            _apps_script_post({"action":"write_tab_chunk","spreadsheet_id":spreadsheet_id,
                "tab":title,"start_row":start+1,"clear":False,"values":[[_apps_script_wire(v) for v in row] for row in target]},timeout=120)
        else:
            rng=f"'{title}'!A{start+1}:{end_col}{start+len(target)}"
            _put_json(session,f"{API_ROOT}/{spreadsheet_id}/values/{quote(rng,safe='')}?valueInputOption=RAW",
                {"range":rng,"majorDimension":"ROWS","values":target})






