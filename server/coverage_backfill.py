from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from data_coverage import source_data_days
from db import db_conn
from upc_aliases import (
    numeric_digits,
    service_249_canonical_base,
    service_249_product_code,
    retail_barcode_alias_candidates,
    normalize_selling_description,
    looks_like_249_service_description,
)


def ensure_coverage_backfill_tables(cur) -> None:
    """Create derived POS daily backfill storage.

    Multi-date POS reports are period aggregates by price type. They are never
    copied across days. A daily row is materialized only when exactly one
    business date is missing from an otherwise fully-known report period, so the
    missing day can be solved by subtraction at EAN/UPC + price-type grain.
    """
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_daily_backfill_coverage (
            backfill_coverage_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            business_date DATE NOT NULL,
            source_file_id BIGINT UNSIGNED NOT NULL,
            source_batch_id BIGINT UNSIGNED NOT NULL,
            period_start_date DATE NOT NULL,
            period_end_date DATE NOT NULL,
            derivation_method VARCHAR(64) NOT NULL,
            backfill_status VARCHAR(32) NOT NULL,
            known_day_count INT NOT NULL DEFAULT 0,
            missing_day_count INT NOT NULL DEFAULT 0,
            detail_json JSON NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (backfill_coverage_id),
            UNIQUE KEY uq_pos_daily_backfill_coverage
                (business_date,source_file_id),
            KEY ix_pos_daily_backfill_date_status
                (business_date,backfill_status),
            KEY ix_pos_daily_backfill_batch
                (source_batch_id,backfill_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_daily_backfill_observation (
            backfill_observation_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            business_date DATE NOT NULL,
            source_file_id BIGINT UNSIGNED NOT NULL,
            source_batch_id BIGINT UNSIGNED NOT NULL,
            ean_upc VARCHAR(32) NOT NULL,
            upc_id BIGINT UNSIGNED NULL,
            description VARCHAR(512) NULL,
            price_type VARCHAR(32) NOT NULL,
            sales_amount DECIMAL(24,8) NOT NULL,
            sold_quantity DECIMAL(24,8) NOT NULL,
            avg_sold_price DECIMAL(24,8) NULL,
            period_start_date DATE NOT NULL,
            period_end_date DATE NOT NULL,
            derivation_method VARCHAR(64) NOT NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (backfill_observation_id),
            UNIQUE KEY uq_pos_daily_backfill_obs
                (business_date,source_file_id,ean_upc,price_type),
            KEY ix_pos_daily_backfill_upc_date
                (upc_id,business_date),
            KEY ix_pos_daily_backfill_ean_date
                (ean_upc,business_date),
            KEY ix_pos_daily_backfill_file
                (source_file_id,business_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_period_residual_observation (
            period_residual_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            source_file_id BIGINT UNSIGNED NOT NULL,
            source_batch_id BIGINT UNSIGNED NOT NULL,
            period_start_date DATE NOT NULL,
            period_end_date DATE NOT NULL,
            missing_start_date DATE NOT NULL,
            missing_end_date DATE NOT NULL,
            missing_day_count INT NOT NULL,
            missing_dates_json JSON NOT NULL,
            ean_upc VARCHAR(32) NOT NULL,
            upc_id BIGINT UNSIGNED NULL,
            description VARCHAR(512) NULL,
            price_type VARCHAR(32) NOT NULL,
            sales_amount DECIMAL(24,8) NOT NULL,
            sold_quantity DECIMAL(24,8) NOT NULL,
            avg_sold_price DECIMAL(24,8) NULL,
            derivation_method VARCHAR(64) NOT NULL,
            created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                ON UPDATE CURRENT_TIMESTAMP(6),
            PRIMARY KEY (period_residual_id),
            UNIQUE KEY uq_pos_period_residual
                (source_file_id,ean_upc,price_type),
            KEY ix_pos_period_residual_batch
                (source_batch_id,missing_start_date,missing_end_date),
            KEY ix_pos_period_residual_upc
                (upc_id,missing_end_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def _date_span(start: date, end: date) -> list[date]:
    out: list[date] = []
    d = start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def _decimal(v: Any) -> Decimal:
    return Decimal(str(v or 0))


def _canonical_sales_days_in_period(
    cur,
    *,
    start: date,
    end: date,
    include_batch_id: int,
) -> dict[date, dict[str, Any]]:
    days = source_data_days(
        cur,
        "sales_by_price_type",
        include_batch_id=include_batch_id,
        up_to=end,
    )
    return {
        x["date"]: x
        for x in days
        if start <= x["date"] <= end
    }


def _known_sales_by_key(
    cur,
    *,
    canonical_days: dict[date, dict[str, Any]],
) -> dict[tuple[str, str], tuple[Decimal, Decimal]]:
    """Aggregate already-known daily POS by EAN + price type.

    Direct SINGLE_DATE and previously accepted derived residual days are both
    eligible known-day evidence. source_data_days decides which source is
    canonical for each business date.
    """
    totals: dict[tuple[str, str], tuple[Decimal, Decimal]] = {}

    direct_days = [
        x for x in canonical_days.values()
        if x.get("coverage_kind") != "DERIVED_PERIOD_RESIDUAL"
    ]
    if direct_days:
        clauses = []
        args: list[Any] = []
        for d in direct_days:
            clauses.append("(file_id=%s AND period_start_date=%s AND period_end_date=%s)")
            args.extend([int(d["file_id"]), d["date"], d["date"]])
        cur.execute(
            f"""SELECT ean_upc,price_type,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM sales_period_observation
                WHERE temporal_grain='SINGLE_DATE'
                  AND ({' OR '.join(clauses)})
                GROUP BY ean_upc,price_type""",
            tuple(args),
        )
        for r in cur.fetchall():
            totals[(str(r["ean_upc"]), str(r["price_type"]))] = (
                _decimal(r["sales_amount"]),
                _decimal(r["sold_quantity"]),
            )

    derived_days = [
        x for x in canonical_days.values()
        if x.get("coverage_kind") == "DERIVED_PERIOD_RESIDUAL"
    ]
    if derived_days:
        clauses = []
        args = []
        for d in derived_days:
            clauses.append("(source_file_id=%s AND business_date=%s)")
            args.extend([int(d["file_id"]), d["date"]])
        cur.execute(
            f"""SELECT ean_upc,price_type,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM pos_daily_backfill_observation
                WHERE {' OR '.join(clauses)}
                GROUP BY ean_upc,price_type""",
            tuple(args),
        )
        for r in cur.fetchall():
            key = (str(r["ean_upc"]), str(r["price_type"]))
            prev = totals.get(key, (Decimal("0"), Decimal("0")))
            totals[key] = (
                prev[0] + _decimal(r["sales_amount"]),
                prev[1] + _decimal(r["sold_quantity"]),
            )
    return totals


def _period_sales_rows(cur, file_id: int) -> list[dict[str, Any]]:
    cur.execute(
        """SELECT ean_upc,MAX(upc_id) AS upc_id,MAX(description) AS description,price_type,
                  COALESCE(SUM(sales_amount),0) AS sales_amount,
                  COALESCE(SUM(sold_quantity),0) AS sold_quantity
           FROM sales_period_observation
           WHERE file_id=%s
             AND temporal_grain='DATE_RANGE'
           GROUP BY ean_upc,price_type
           ORDER BY ean_upc,price_type""",
        (file_id,),
    )
    return cur.fetchall()


def resolve_pos_period_backfill(cur, batch_id: int) -> dict[str, Any]:
    """Resolve multi-date POS files against canonical daily coverage.

    Rules:
      * 0 missing dates -> reconciliation only; no derived day is written.
      * exactly 1 missing date -> period minus known canonical days, at
        EAN/UPC + price-type grain, becomes a derived single-day backfill.
      * 2+ missing dates -> retain original DATE_RANGE observations as
        period/price-type evidence only; do not invent daily allocation.
      * a range ending today/future is never residual-backfilled because the
        period may still be incomplete.
    """
    completed_through = date.today() - timedelta(days=1)
    cur.execute(
        """SELECT file_id,batch_id,original_filename,
                  COALESCE(header_period_start_date,coverage_start_date) AS period_start,
                  COALESCE(header_period_end_date,coverage_end_date) AS period_end
           FROM ingest_file
           WHERE batch_id=%s
             AND source_type='sales_by_price_type'
             AND processing_status='INGESTED'
             AND error_count=0
             AND duplicate_of_file_id IS NULL
           ORDER BY file_id""",
        (batch_id,),
    )

    files_out: list[dict[str, Any]] = []
    derived_days = 0
    derived_rows = 0
    period_only_files = 0
    reconciliation_only_files = 0
    blocked_files = 0

    for f in cur.fetchall():
        start = f.get("period_start")
        end = f.get("period_end")
        if not start or not end or start >= end:
            continue

        file_id = int(f["file_id"])
        # Re-run safe: replace only this file's derived layer.
        cur.execute(
            "DELETE FROM pos_daily_backfill_observation WHERE source_file_id=%s",
            (file_id,),
        )
        cur.execute(
            "DELETE FROM pos_daily_backfill_coverage WHERE source_file_id=%s",
            (file_id,),
        )
        cur.execute(
            "DELETE FROM pos_period_residual_observation WHERE source_file_id=%s",
            (file_id,),
        )

        period_dates = _date_span(start, end)
        known = _canonical_sales_days_in_period(
            cur,
            start=start,
            end=end,
            include_batch_id=batch_id,
        )
        missing = [d for d in period_dates if d not in known]

        result: dict[str, Any] = {
            "file_id": file_id,
            "filename": f["original_filename"],
            "period_start": start,
            "period_end": end,
            "period_day_count": len(period_dates),
            "known_dates": sorted(known),
            "missing_dates": missing,
            "missing_day_count": len(missing),
        }

        if end > completed_through:
            result["mode"] = "PERIOD_PRICE_TYPE_ONLY"
            result["reason"] = "PERIOD_NOT_COMPLETED"
            period_only_files += 1
            files_out.append(result)
            continue

        if not missing:
            result["mode"] = "RECONCILIATION_ONLY"
            result["reason"] = "NO_DAILY_GAP"
            reconciliation_only_files += 1
            files_out.append(result)
            continue

        missing_day = missing[0]
        period_rows = _period_sales_rows(cur, file_id)
        known_totals = _known_sales_by_key(cur, canonical_days=known)
        period_map = {
            (str(p["ean_upc"]), str(p["price_type"])): p
            for p in period_rows
        }

        negative_residuals: list[dict[str, Any]] = []
        residual_rows: list[dict[str, Any]] = []
        tolerance = Decimal("0.0001")

        all_keys = sorted(set(period_map) | set(known_totals))
        for key in all_keys:
            p = period_map.get(key)
            period_sales = _decimal(p["sales_amount"]) if p else Decimal("0")
            period_qty = _decimal(p["sold_quantity"]) if p else Decimal("0")
            known_sales, known_qty = known_totals.get(
                key, (Decimal("0"), Decimal("0"))
            )
            residual_sales = period_sales - known_sales
            residual_qty = period_qty - known_qty

            if residual_sales < -tolerance or residual_qty < -tolerance:
                negative_residuals.append(
                    {
                        "ean_upc": key[0],
                        "price_type": key[1],
                        "period_sales": period_sales,
                        "period_qty": period_qty,
                        "known_sales": known_sales,
                        "known_qty": known_qty,
                        "residual_sales": residual_sales,
                        "residual_qty": residual_qty,
                        "period_key_present": p is not None,
                    }
                )
                continue

            if abs(residual_sales) <= tolerance:
                residual_sales = Decimal("0")
            if abs(residual_qty) <= tolerance:
                residual_qty = Decimal("0")
            avg = residual_sales / residual_qty if residual_qty != 0 else None
            residual_rows.append(
                {
                    "ean_upc": key[0],
                    "upc_id": p.get("upc_id") if p else None,
                    "description": p.get("description") if p else None,
                    "price_type": key[1],
                    "sales_amount": residual_sales,
                    "sold_quantity": residual_qty,
                    "avg_sold_price": avg,
                }
            )

        if negative_residuals:
            result["mode"] = "BLOCKED"
            result["reason"] = "NEGATIVE_RESIDUAL_AFTER_DAILY_SUBTRACTION"
            result["negative_residual_count"] = len(negative_residuals)
            result["negative_residual_examples"] = negative_residuals[:10]
            blocked_files += 1
            files_out.append(result)
            continue

        if len(missing) > 1:
            import json
            missing_json = json.dumps(
                [d.isoformat() for d in missing],
                ensure_ascii=False,
            )
            for r in residual_rows:
                cur.execute(
                    """INSERT INTO pos_period_residual_observation
                       (source_file_id,source_batch_id,
                        period_start_date,period_end_date,
                        missing_start_date,missing_end_date,
                        missing_day_count,missing_dates_json,
                        ean_upc,upc_id,description,price_type,
                        sales_amount,sold_quantity,avg_sold_price,
                        derivation_method)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,
                               %s,%s,%s,%s,%s,%s,%s,
                               'PERIOD_MINUS_CANONICAL_DAYS_BY_PRICE_TYPE')
                       ON DUPLICATE KEY UPDATE
                         source_batch_id=VALUES(source_batch_id),
                         period_start_date=VALUES(period_start_date),
                         period_end_date=VALUES(period_end_date),
                         missing_start_date=VALUES(missing_start_date),
                         missing_end_date=VALUES(missing_end_date),
                         missing_day_count=VALUES(missing_day_count),
                         missing_dates_json=VALUES(missing_dates_json),
                         upc_id=VALUES(upc_id),
                         description=VALUES(description),
                         sales_amount=VALUES(sales_amount),
                         sold_quantity=VALUES(sold_quantity),
                         avg_sold_price=VALUES(avg_sold_price),
                         derivation_method=VALUES(derivation_method)""",
                    (
                        file_id,
                        batch_id,
                        start,
                        end,
                        min(missing),
                        max(missing),
                        len(missing),
                        missing_json,
                        r["ean_upc"],
                        r.get("upc_id"),
                        r.get("description"),
                        r["price_type"],
                        r["sales_amount"],
                        r["sold_quantity"],
                        r["avg_sold_price"],
                    ),
                )
            result["mode"] = "PERIOD_PRICE_TYPE_RESIDUAL"
            result["reason"] = "MULTIPLE_DAILY_GAPS_RETAINED_AT_PRICE_TYPE_GRAIN"
            result["residual_row_count"] = len(residual_rows)
            result["derivation_method"] = "PERIOD_MINUS_CANONICAL_DAYS_BY_PRICE_TYPE"
            period_only_files += 1
            files_out.append(result)
            continue

        cur.execute(
            """INSERT INTO pos_daily_backfill_coverage
               (business_date,source_file_id,source_batch_id,
                period_start_date,period_end_date,derivation_method,
                backfill_status,known_day_count,missing_day_count,detail_json)
               VALUES (%s,%s,%s,%s,%s,
                       'PERIOD_MINUS_CANONICAL_DAYS_BY_PRICE_TYPE',
                       'READY',%s,1,
                       JSON_OBJECT('source','DATE_RANGE_POS',
                                   'rule','ONE_MISSING_DAY_ONLY'))
               ON DUPLICATE KEY UPDATE
                 source_batch_id=VALUES(source_batch_id),
                 period_start_date=VALUES(period_start_date),
                 period_end_date=VALUES(period_end_date),
                 derivation_method=VALUES(derivation_method),
                 backfill_status='READY',
                 known_day_count=VALUES(known_day_count),
                 missing_day_count=1,
                 detail_json=VALUES(detail_json)""",
            (
                missing_day,
                file_id,
                batch_id,
                start,
                end,
                len(known),
            ),
        )

        for r in residual_rows:
            cur.execute(
                """INSERT INTO pos_daily_backfill_observation
                   (business_date,source_file_id,source_batch_id,
                    ean_upc,upc_id,description,price_type,
                    sales_amount,sold_quantity,avg_sold_price,
                    period_start_date,period_end_date,derivation_method)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                           'PERIOD_MINUS_CANONICAL_DAYS_BY_PRICE_TYPE')
                   ON DUPLICATE KEY UPDATE
                     upc_id=VALUES(upc_id),
                     description=VALUES(description),
                     sales_amount=VALUES(sales_amount),
                     sold_quantity=VALUES(sold_quantity),
                     avg_sold_price=VALUES(avg_sold_price),
                     period_start_date=VALUES(period_start_date),
                     period_end_date=VALUES(period_end_date),
                     derivation_method=VALUES(derivation_method)""",
                (
                    missing_day,
                    file_id,
                    batch_id,
                    r["ean_upc"],
                    r.get("upc_id"),
                    r.get("description"),
                    r["price_type"],
                    r["sales_amount"],
                    r["sold_quantity"],
                    r["avg_sold_price"],
                    start,
                    end,
                ),
            )

        result["mode"] = "DERIVED_SINGLE_DAY_BACKFILL"
        result["backfill_date"] = missing_day
        result["derived_row_count"] = len(residual_rows)
        result["derivation_method"] = "PERIOD_MINUS_CANONICAL_DAYS_BY_PRICE_TYPE"
        derived_days += 1
        derived_rows += len(residual_rows)
        files_out.append(result)

    return {
        "batch_id": batch_id,
        "derived_day_count": derived_days,
        "derived_row_count": derived_rows,
        "period_price_type_only_files": period_only_files,
        "reconciliation_only_files": reconciliation_only_files,
        "blocked_files": blocked_files,
        "files": files_out,
    }




ARTICLE_MANUAL_POS_TABS = {
    "fresh fish",
    "live fish",
    "shrimp",
    "fish ball",
    "frozen fish",
    "frozen pack",
}


def _article_manual_sheet_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = " ".join("".join(ch if ch.isalnum() else " " for ch in text).split())
    return text


def _article_manual_digits(value: Any) -> str | None:
    """Parse one Article Manual identifier without inventing digits."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not value.is_integer():
            return None
        return str(int(value))
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    compact = "".join(ch for ch in text if ch not in {" ", "-"})
    return compact if compact.isdigit() else None


def _unique_alias_map(values: dict[str, set[int]]) -> dict[str, int]:
    return {
        key: next(iter(ids))
        for key, ids in values.items()
        if key and len(ids) == 1
    }


def article_manual_pos_alias_index(cur) -> dict[str, Any]:
    """Build authoritative 249 POS aliases from the newest valid Article Manual.

    User-confirmed Article Manual schemas:
      Fresh/Live/Shrimp/Fish Ball/Frozen Fish:
        A=Family/Main, B=Selling Article, C=Toledo#, D=EAN/UPC.
      Frozen Pack:
        A=Family/Main/Selling Article, D=EAN/UPC.

    Only Article Manual rows whose D value resolves to an existing ACTIVE
    canonical 249 selling UPC are eligible. Ambiguous aliases are withheld.
    Article Manual supplies identity only; POS remains the sole quantity source.
    """
    cur.execute(
        """SELECT file_id,batch_id
           FROM ingest_file
           WHERE source_type='article_manual'
             AND processing_status='INGESTED'
             AND error_count=0
             AND duplicate_of_file_id IS NULL
           ORDER BY file_id DESC"""
    )
    files = cur.fetchall()
    if not files:
        return {
            "source_upc": {},
            "selling_article": {},
            "toledo": {},
            "service_code": {},
            "source_batch_id": None,
            "row_count": 0,
        }

    newest_batch = int(files[0]["batch_id"])
    file_ids = [int(x["file_id"]) for x in files if int(x["batch_id"]) == newest_batch]
    if not file_ids:
        return {
            "source_upc": {},
            "selling_article": {},
            "toledo": {},
            "service_code": {},
            "source_batch_id": newest_batch,
            "row_count": 0,
        }

    cur.execute(
        """SELECT upc_id,ean_upc
           FROM selling_upc
           WHERE record_status='ACTIVE'
             AND ean_upc LIKE '249%'"""
    )
    exact: dict[str, int] = {}
    numeric: dict[str, int] = {}
    canonical_by_id: dict[int, str] = {}
    for row in cur.fetchall():
        ean = str(row.get("ean_upc") or "").strip()
        if not ean:
            continue
        uid = int(row["upc_id"])
        canonical_by_id[uid] = ean
        exact.setdefault(ean, uid)
        key = numeric_digits(ean)
        if key:
            numeric.setdefault(key, uid)

    source_sets: dict[str, set[int]] = {}
    article_sets: dict[str, set[int]] = {}
    toledo_sets: dict[str, set[int]] = {}
    service_sets: dict[str, set[int]] = {}
    row_count = 0

    placeholders = ",".join(["%s"] * len(file_ids))
    cur.execute(
        f"""SELECT sheet_id,sheet_name,file_id
            FROM ingest_sheet
            WHERE file_id IN ({placeholders})
            ORDER BY file_id DESC,sheet_index""",
        tuple(file_ids),
    )
    for sheet in cur.fetchall():
        sheet_key = _article_manual_sheet_key(sheet.get("sheet_name"))
        if sheet_key not in ARTICLE_MANUAL_POS_TABS:
            continue
        cur.execute(
            """SELECT raw_payload
               FROM raw_article_manual
               WHERE sheet_id=%s
               ORDER BY source_row_number""",
            (int(sheet["sheet_id"]),),
        )
        for raw_row in cur.fetchall():
            payload = raw_row.get("raw_payload")
            if isinstance(payload, (bytes, bytearray)):
                payload = payload.decode("utf-8", errors="replace")
            if isinstance(payload, str):
                try:
                    import json
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            if not isinstance(payload, dict):
                continue

            source_upc = _article_manual_digits(payload.get("D"))
            if not source_upc:
                continue
            uid = exact.get(source_upc)
            if uid is None:
                key = numeric_digits(source_upc)
                uid = numeric.get(key) if key else None
            if uid is None:
                continue

            canonical_ean = canonical_by_id.get(int(uid), "")
            if not canonical_ean.startswith("249"):
                continue

            main_article = _article_manual_digits(payload.get("A"))
            selling_article = (
                main_article
                if sheet_key == "frozen pack"
                else (_article_manual_digits(payload.get("B")) or main_article)
            )
            toledo = None if sheet_key == "frozen pack" else _article_manual_digits(payload.get("C"))

            source_key = numeric_digits(source_upc)
            if source_key:
                source_sets.setdefault(source_key, set()).add(int(uid))
            if selling_article:
                article_sets.setdefault(selling_article.lstrip("0") or "0", set()).add(int(uid))
            if toledo:
                toledo_sets.setdefault(toledo.lstrip("0") or "0", set()).add(int(uid))

            service_code = service_249_product_code(canonical_ean)
            if service_code:
                service_sets.setdefault(service_code, set()).add(int(uid))
            row_count += 1

    return {
        "source_upc": _unique_alias_map(source_sets),
        "selling_article": _unique_alias_map(article_sets),
        "toledo": _unique_alias_map(toledo_sets),
        "service_code": _unique_alias_map(service_sets),
        "source_batch_id": newest_batch,
        "row_count": row_count,
    }


def resolve_article_manual_pos_upc_id(index: dict[str, Any], raw_ean: Any) -> int | None:
    """Resolve raw Seafood POS identity from Article Manual before heuristics."""
    raw = _article_manual_digits(raw_ean)
    if not raw:
        return None
    key = raw.lstrip("0") or "0"

    source_map = index.get("source_upc") or {}
    if key in source_map:
        return int(source_map[key])

    article_map = index.get("selling_article") or {}
    if key in article_map:
        return int(article_map[key])

    service_code = service_249_product_code(raw)
    service_map = index.get("service_code") or {}
    if service_code and service_code in service_map:
        return int(service_map[service_code])

    toledo_map = index.get("toledo") or {}
    if key in toledo_map:
        return int(toledo_map[key])

    for candidate in retail_barcode_alias_candidates(raw):
        candidate_key = numeric_digits(candidate)
        if candidate_key and candidate_key in source_map:
            return int(source_map[candidate_key])
    return None


def _active_upc_alias_index(cur) -> dict[str, Any]:
    """Build one in-memory authoritative UPC roster index for raw-source relinking."""
    cur.execute(
        """SELECT upc_id,ean_upc,selling_description
           FROM selling_upc
           WHERE record_status='ACTIVE'
           ORDER BY CHAR_LENGTH(ean_upc),upc_id"""
    )
    rows=cur.fetchall()
    exact: dict[str,int]={}
    numeric: dict[str,int]={}
    service_desc_ids: dict[str,set[int]]={}
    for row in rows:
        ean=str(row.get("ean_upc") or "").strip()
        if not ean:
            continue
        uid=int(row["upc_id"])
        exact.setdefault(ean,uid)
        key=numeric_digits(ean)
        if key:
            numeric.setdefault(key,uid)
        if ean.startswith("249") and looks_like_249_service_description(row.get("selling_description")):
            desc_key=normalize_selling_description(row.get("selling_description"))
            if desc_key:
                service_desc_ids.setdefault(desc_key,set()).add(uid)
    # Description is authority only when exactly one ACTIVE canonical 249 row
    # owns the normalized service description. Ambiguous names fail closed.
    service_desc={
        key: next(iter(ids))
        for key,ids in service_desc_ids.items()
        if len(ids)==1
    }
    return {
        "exact": exact,
        "numeric": numeric,
        "service_desc": service_desc,
        "article_manual": article_manual_pos_alias_index(cur),
    }


def _resolve_source_upc_id(
    index: dict[str, Any],
    raw_ean: Any,
    fallback_upc_id: Any = None,
    description: Any = None,
) -> int | None:
    raw=str(raw_ean or "").strip()
    exact=index["exact"]
    numeric=index["numeric"]

    # Article Manual is the primary identity authority for 249 Seafood POS.
    # Quantity still comes only from this POS row; the manual never contributes
    # sales quantity and therefore cannot create double counting.
    manual_uid = resolve_article_manual_pos_upc_id(
        index.get("article_manual") or {},
        raw,
    )
    if manual_uid is not None:
        return int(manual_uid)

    # A POS row explicitly labeled Fried/Cook Service is selling evidence for
    # the service UPC. If its source barcode is not a canonical 249 spelling,
    # use the unique ACTIVE 249 roster description before trusting another
    # numeric alias. Quantity still comes from the POS row itself.
    if looks_like_249_service_description(description):
        desc_key=normalize_selling_description(description)
        service_uid=index.get("service_desc",{}).get(desc_key)
        if service_uid is not None:
            return int(service_uid)

    if raw in exact:
        return int(exact[raw])
    key=numeric_digits(raw)
    if key and key in numeric:
        return int(numeric[key])
    service=service_249_canonical_base(raw)
    if service and service in exact:
        return int(exact[service])
    for candidate in retail_barcode_alias_candidates(raw):
        if candidate in exact:
            return int(exact[candidate])
    if fallback_upc_id is not None:
        return int(fallback_upc_id)
    return None


def canonical_pos_qty_by_upc(
    cur,
    data_days: list[dict[str, Any]],
) -> dict[int, Decimal]:
    """Aggregate POS quantity by current canonical UPC across all safe raw aliases.

    Raw source EAN/UPC is authoritative lineage evidence. Derived upc_id is used
    only as a fallback when the raw source spelling cannot resolve against the
    current active roster.
    """
    out: dict[int, Decimal]={}
    if not data_days:
        return out
    alias_index=_active_upc_alias_index(cur)

    def add_rows(rows: list[dict[str, Any]]) -> None:
        for row in rows:
            uid=_resolve_source_upc_id(
                alias_index,
                row.get("ean_upc"),
                row.get("upc_id"),
                row.get("description"),
            )
            if uid is None:
                continue
            out[uid]=out.get(uid,Decimal("0"))+_decimal(row.get("qty"))

    direct=[d for d in data_days if d.get("coverage_kind")!="DERIVED_PERIOD_RESIDUAL"]
    if direct:
        clauses=[]
        args: list[Any]=[]
        for d in direct:
            clauses.append("(file_id=%s AND period_start_date=%s AND period_end_date=%s)")
            args.extend([int(d["file_id"]),d["date"],d["date"]])
        cur.execute(
            f"""SELECT ean_upc,upc_id,description,COALESCE(SUM(sold_quantity),0) AS qty
                FROM sales_period_observation
                WHERE temporal_grain='SINGLE_DATE'
                  AND ({' OR '.join(clauses)})
                GROUP BY ean_upc,upc_id,description""",
            tuple(args),
        )
        add_rows(cur.fetchall())

    derived=[d for d in data_days if d.get("coverage_kind")=="DERIVED_PERIOD_RESIDUAL"]
    if derived:
        clauses=[]
        args=[]
        for d in derived:
            clauses.append("(source_file_id=%s AND business_date=%s)")
            args.extend([int(d["file_id"]),d["date"]])
        cur.execute(
            f"""SELECT ean_upc,upc_id,description,COALESCE(SUM(sold_quantity),0) AS qty
                FROM pos_daily_backfill_observation
                WHERE ({' OR '.join(clauses)})
                GROUP BY ean_upc,upc_id,description""",
            tuple(args),
        )
        add_rows(cur.fetchall())

    return out


def relink_pos_backfill(cur) -> int:
    """Repair derived backfill UPC ids from immutable raw EAN/UPC lineage."""
    index=_active_upc_alias_index(cur)
    updated=0
    for table in ("pos_daily_backfill_observation","pos_period_residual_observation"):
        cur.execute(
            f"SELECT DISTINCT ean_upc,upc_id,description FROM {table} WHERE ean_upc IS NOT NULL"
        )
        for row in cur.fetchall():
            resolved=_resolve_source_upc_id(
                index,
                row.get("ean_upc"),
                row.get("upc_id"),
                row.get("description"),
            )
            if resolved is None:
                continue
            current=row.get("upc_id")
            if current is not None and int(current)==resolved:
                continue
            cur.execute(
                f"""UPDATE {table}
                    SET upc_id=%s
                    WHERE ean_upc=%s
                      AND COALESCE(description,'')=COALESCE(%s,'')
                      AND (upc_id IS NULL OR upc_id<>%s)""",
                (resolved,str(row.get("ean_upc")),row.get("description"),resolved),
            )
            updated+=int(cur.rowcount or 0)
    return updated

def diagnose_coverage_backfill(batch_id: int) -> dict[str, Any]:
    """Read-only view of multi-date POS/MVT backfill behavior for one batch."""
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """SELECT file_id,batch_id,original_filename,source_type,
                          coverage_type,coverage_start_date,coverage_end_date,
                          header_period_start_date,header_period_end_date,
                          report_generated_at,filename_date_candidate,
                          filename_time_candidate,processing_status,error_count
                   FROM ingest_file
                   WHERE batch_id=%s
                     AND source_type IN ('sales_by_price_type','movement')
                   ORDER BY file_id""",
                (batch_id,),
            )
            files = cur.fetchall()
            file_ids = {int(x["file_id"]) for x in files}

            cur.execute(
                """SELECT 1
                   FROM information_schema.TABLES
                   WHERE TABLE_SCHEMA=DATABASE()
                     AND TABLE_NAME='pos_daily_backfill_coverage'
                   LIMIT 1"""
            )
            backfill_initialized = bool(cur.fetchone())

            pos_days = [
                x for x in source_data_days(
                    cur, "sales_by_price_type", include_batch_id=batch_id
                )
                if int(x["file_id"]) in file_ids
            ]
            mvt_days = [
                x for x in source_data_days(
                    cur, "movement", include_batch_id=batch_id
                )
                if int(x["file_id"]) in file_ids
            ]

            pos_backfill = []
            pos_backfill_totals = []
            if backfill_initialized:
                cur.execute(
                    """SELECT business_date,source_file_id,source_batch_id,
                              period_start_date,period_end_date,derivation_method,
                              backfill_status,known_day_count,missing_day_count,
                              detail_json
                       FROM pos_daily_backfill_coverage
                       WHERE source_batch_id=%s
                       ORDER BY business_date,source_file_id""",
                    (batch_id,),
                )
                pos_backfill = cur.fetchall()

                cur.execute(
                    """SELECT source_file_id,business_date,COUNT(*) AS row_count,
                              COALESCE(SUM(sales_amount),0) AS sales_amount,
                              COALESCE(SUM(sold_quantity),0) AS sold_quantity
                       FROM pos_daily_backfill_observation
                       WHERE source_batch_id=%s
                       GROUP BY source_file_id,business_date
                       ORDER BY business_date,source_file_id""",
                    (batch_id,),
                )
                pos_backfill_totals = cur.fetchall()

            pos_period_residuals = []
            if backfill_initialized:
                cur.execute(
                    """SELECT source_file_id,source_batch_id,
                              period_start_date,period_end_date,
                              missing_start_date,missing_end_date,
                              missing_day_count,missing_dates_json,
                              ean_upc,upc_id,description,price_type,
                              sales_amount,sold_quantity,avg_sold_price,
                              derivation_method
                       FROM pos_period_residual_observation
                       WHERE source_batch_id=%s
                       ORDER BY source_file_id,ean_upc,price_type""",
                    (batch_id,),
                )
                pos_period_residuals = cur.fetchall()

            return {
                "batch_id": batch_id,
                "initialized": backfill_initialized,
                "files": files,
                "canonical_pos_days_from_batch": pos_days,
                "canonical_movement_days_from_batch": mvt_days,
                "pos_derived_daily_coverage": pos_backfill,
                "pos_derived_daily_totals": pos_backfill_totals,
                "pos_period_price_type_residuals": pos_period_residuals,
                "rules": {
                    "pos_one_missing_day": "PERIOD_MINUS_CANONICAL_DAYS_BY_PRICE_TYPE",
                    "pos_multiple_missing_days": "PERIOD_MINUS_CANONICAL_DAYS_BY_PRICE_TYPE_AS_MULTI_DAY_RESIDUAL",
                    "movement_multi_date": "EXACT_POSTING_DATE_SLICE",
                },
            }
        finally:
            cur.close()
