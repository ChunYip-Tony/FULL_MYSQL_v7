from __future__ import annotations

from decimal import Decimal
from typing import Any

from db import db_conn
from quick_check_app import (
    get_quick_check_detail,
    negative_stock_queue,
    pending_dumping_discrepancies,
)


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def verify_current_work(
    *,
    api_version: str,
    expected_version: str | None = None,
    session_id: str | None = None,
    focus_upc: str = "74709410002",
) -> dict[str, Any]:
    """Read-only server-side verification of the current serving state."""

    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def check(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})
        if not passed:
            failures.append(name)

    if expected_version:
        check(
            "VERSION_MATCH",
            str(api_version) == str(expected_version),
            {"expected": expected_version, "actual": api_version},
        )
    else:
        check("VERSION_PRESENT", bool(api_version), {"actual": api_version})

    neg = negative_stock_queue(limit=500)
    check(
        "NEGATIVE_QUEUE_GRAIN",
        neg.get("queue_grain") == "INVENTORY_OWNER",
        {"actual": neg.get("queue_grain")},
    )

    owner_keys = [
        str(r.get("inventory_owner_key"))
        for r in (neg.get("rows") or [])
        if r.get("inventory_owner_key")
    ]
    duplicate_owner_keys = sorted({
        key for key in owner_keys if owner_keys.count(key) > 1
    })
    check(
        "NEGATIVE_QUEUE_OWNER_UNIQUE",
        not duplicate_owner_keys,
        {"duplicate_owner_keys": duplicate_owner_keys},
    )

    blocked_owner_count = int(neg.get("blocked_owner_count") or 0)
    unresolved_owner_upc_count = int(neg.get("unresolved_owner_upc_count") or 0)
    check(
        "NEGATIVE_QUEUE_NO_BLOCKED_OWNERS",
        blocked_owner_count == 0,
        {"blocked_owner_count": blocked_owner_count},
    )
    check(
        "NEGATIVE_QUEUE_NO_UNRESOLVED_OWNER_UPCS",
        unresolved_owner_upc_count == 0,
        {"unresolved_owner_upc_count": unresolved_owner_upc_count},
    )

    pending = pending_dumping_discrepancies()

    focus = get_quick_check_detail(focus_upc) if focus_upc else None
    if focus_upc:
        check("FOCUS_UPC_FOUND", focus is not None, {"focus_upc": focus_upc})

    focus_summary = None
    if focus:
        item = focus.get("item") or {}
        effective = focus.get("effective_oh") or {}
        current_oh = _decimal(item.get("current_oh"))
        dos = _decimal(item.get("dos"))
        stock_status = item.get("stock_status")
        if current_oh is not None and current_oh < 0:
            check(
                "FOCUS_NEGATIVE_STATUS",
                stock_status == "NEGATIVE",
                {"current_oh": str(current_oh), "stock_status": stock_status},
            )
            check(
                "FOCUS_NEGATIVE_DOS_ZERO",
                dos is not None and dos == 0,
                {"dos": None if dos is None else str(dos)},
            )

        focus_summary = {
            "upc": focus_upc,
            "current_oh": item.get("current_oh"),
            "current_oh_uom": item.get("current_oh_uom"),
            "dos": item.get("dos"),
            "negative_stock": item.get("negative_stock"),
            "stock_status": item.get("stock_status"),
            "quick_check_status": item.get("quick_check_status"),
            "blocking_reason": item.get("blocking_reason"),
            "effective_oh": effective.get("quantity"),
            "effective_oh_uom": effective.get("uom"),
            "effective_oh_source": effective.get("source"),
            "effective_analysis_usable": effective.get("analysis_usable"),
        }

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)

        batch = None
        if session_id:
            cur.execute(
                """SELECT batch_id,batch_key,processing_status
                   FROM ingest_batch
                   WHERE batch_key=%s
                   LIMIT 1""",
                (session_id,),
            )
            batch = cur.fetchone()
            check(
                "SESSION_FOUND",
                batch is not None,
                {"session_id": session_id},
            )

        cur.execute(
            """SELECT
                   COUNT(*) AS serving_rows_total,
                   SUM(CASE WHEN quick_check_status='HISTORICAL_ONLY' THEN 1 ELSE 0 END) AS historical_rows,
                   SUM(CASE WHEN quick_check_status IN ('READY','QA_HOLD') THEN 1 ELSE 0 END) AS current_active_rows,
                   SUM(CASE WHEN quick_check_status='READY' THEN 1 ELSE 0 END) AS current_ready_rows,
                   SUM(CASE WHEN quick_check_status='QA_HOLD' THEN 1 ELSE 0 END) AS current_hold_rows
               FROM quick_check_current"""
        )
        qc_scope = cur.fetchone() or {}

        cur.execute(
            """SELECT ean_upc,blocking_reason
               FROM quick_check_current
               WHERE quick_check_status='QA_HOLD'
               ORDER BY ean_upc"""
        )
        hold_rows = cur.fetchall()
        reason_counts: dict[str, int] = {}
        for row in hold_rows:
            reasons = [
                x.strip()
                for x in str(row.get("blocking_reason") or "").split(",")
                if x and x.strip()
            ]
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

        hold_count = int(qc_scope.get("current_hold_rows") or 0)
        check(
            "QUICK_CHECK_HOLD_ROW_PARITY",
            hold_count == len(hold_rows),
            {
                "current_hold_rows": hold_count,
                "hold_row_count": len(hold_rows),
            },
        )

        phase3 = None
        if batch:
            cur.execute(
                """SELECT result_status,blocking_issue_count,
                          quick_check_rows,quick_check_ready_rows,quick_check_hold_rows,updated_at
                   FROM phase3_batch_result
                   WHERE batch_id=%s""",
                (int(batch["batch_id"]),),
            )
            phase3 = cur.fetchone()

        cur.close()

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "api_version": api_version,
        "expected_version": expected_version,
        "checks": checks,
        "failures": failures,
        "negative_stock": {
            "count": neg.get("count"),
            "queue_grain": neg.get("queue_grain"),
            "candidate_upc_count": neg.get("candidate_upc_count"),
            "inventory_owner_count": neg.get("inventory_owner_count"),
            "actionable_owner_count": neg.get("actionable_owner_count"),
            "suppressed_by_true_stock_count": neg.get("suppressed_by_true_stock_count"),
            "blocked_owner_count": neg.get("blocked_owner_count"),
            "unresolved_owner_upc_count": neg.get("unresolved_owner_upc_count"),
            "duplicate_owner_keys": duplicate_owner_keys,
        },
        "pending_dumping_count": len(pending),
        "focus": focus_summary,
        "quick_check_scope": {
            **qc_scope,
            "hold_row_count": len(hold_rows),
            "hold_reason_row_parity": hold_count == len(hold_rows),
        },
        "quick_check_reason_counts": reason_counts,
        "session": batch,
        "phase3": phase3,
    }
