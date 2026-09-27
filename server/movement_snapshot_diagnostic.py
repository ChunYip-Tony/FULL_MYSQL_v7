from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from db import db_conn
from data_coverage import source_data_days


_SIGNATURE_FIELDS = (
    "article_number",
    "movement_type",
    "posting_date",
    "entry_quantity",
    "entry_uom_code",
    "base_quantity",
    "base_uom_code",
    "amount_local_currency",
    "sales_value",
    "article_document",
    "purchase_order",
    "vendor_code",
)


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        return None


def _norm(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value == 0:
            return "0"
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _source_chronology(file_row: dict[str, Any]) -> tuple[int, datetime, int]:
    generated = file_row.get("report_generated_at")
    if isinstance(generated, datetime):
        return (0, generated, int(file_row["file_id"]))

    candidate = _as_date(file_row.get("filename_date_candidate"))
    if candidate is not None:
        parsed_time = time.min
        raw_time = str(file_row.get("filename_time_candidate") or "").strip()
        if raw_time:
            try:
                parsed_time = time.fromisoformat(raw_time)
            except Exception:
                parsed_time = time.min
        return (1, datetime.combine(candidate, parsed_time), int(file_row["file_id"]))

    uploaded = file_row.get("upload_timestamp")
    if isinstance(uploaded, datetime):
        return (2, uploaded, int(file_row["file_id"]))
    try:
        return (2, datetime.fromisoformat(str(uploaded)), int(file_row["file_id"]))
    except Exception:
        return (3, datetime.min, int(file_row["file_id"]))


def _signature_counter(rows: list[dict[str, Any]]) -> Counter:
    return Counter(
        tuple(_norm(row.get(field)) for field in _SIGNATURE_FIELDS)
        for row in rows
    )


def _relationship(
    earlier_file: dict[str, Any],
    later_file: dict[str, Any],
    earlier_counter: Counter,
    later_counter: Counter,
) -> dict[str, Any]:
    common = earlier_counter & later_counter
    earlier_only = earlier_counter - later_counter
    later_only = later_counter - earlier_counter

    common_rows = sum(common.values())
    earlier_only_rows = sum(earlier_only.values())
    later_only_rows = sum(later_only.values())
    earlier_rows = sum(earlier_counter.values())
    later_rows = sum(later_counter.values())

    if earlier_rows == 0 and later_rows == 0:
        relation = "BOTH_EMPTY"
    elif earlier_only_rows == 0 and later_only_rows == 0:
        relation = "IDENTICAL"
    elif later_only_rows == 0:
        relation = "LATER_SUBSET_OF_EARLIER"
    elif earlier_only_rows == 0:
        relation = "LATER_SUPERSET_OF_EARLIER"
    elif common_rows == 0:
        relation = "DISJOINT"
    else:
        relation = "PARTIAL_OVERLAP"

    return {
        "earlier_file_id": int(earlier_file["file_id"]),
        "earlier_filename": earlier_file["original_filename"],
        "later_file_id": int(later_file["file_id"]),
        "later_filename": later_file["original_filename"],
        "relationship": relation,
        "earlier_rows": earlier_rows,
        "later_rows": later_rows,
        "common_rows": common_rows,
        "earlier_only_rows": earlier_only_rows,
        "later_only_rows": later_only_rows,
        "common_pct_of_earlier": (
            round(common_rows * 100.0 / earlier_rows, 2) if earlier_rows else None
        ),
        "common_pct_of_later": (
            round(common_rows * 100.0 / later_rows, 2) if later_rows else None
        ),
    }


def movement_same_day_compare(movement_date: str) -> dict[str, Any]:
    """Compare all canonical-eligible MVT exports for one business date.

    Read-only diagnostic. It does not change source selection, Quick Check,
    inventory authority, RAW rows, normalized history, or QA state.
    """
    try:
        requested = datetime.fromisoformat(str(movement_date)).date()
    except Exception as exc:
        raise ValueError("INVALID_MOVEMENT_DATE") from exc

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """SELECT f.file_id,f.batch_id,f.original_filename,f.source_row_count,
                      f.coverage_type,f.coverage_start_date,f.coverage_end_date,
                      f.report_generated_at,f.filename_date_candidate,
                      f.filename_time_candidate,f.upload_timestamp
               FROM ingest_file f
               JOIN phase3_batch_result p ON p.batch_id=f.batch_id
               WHERE f.source_type='movement'
                 AND f.processing_status='INGESTED'
                 AND f.error_count=0
                 AND f.duplicate_of_file_id IS NULL
                 AND f.source_row_count>0
                 AND f.date_semantics_status='RESOLVED'
                 AND f.coverage_start_date=%s
                 AND f.coverage_end_date=%s
               ORDER BY f.file_id""",
            (requested, requested),
        )
        files = cur.fetchall()
        files.sort(key=_source_chronology)

        canonical = next(
            (x for x in source_data_days(cur, "movement") if x["date"] == requested),
            None,
        )
        canonical_file_id = int(canonical["file_id"]) if canonical else None

        summaries: list[dict[str, Any]] = []
        counters: dict[int, Counter] = {}

        for f in files:
            file_id = int(f["file_id"])
            cur.execute(
                """SELECT article_number,article_id,family_id,movement_type,posting_date,
                          entry_quantity,entry_uom_code,base_quantity,base_uom_code,
                          amount_local_currency,sales_value,article_document,
                          purchase_order,vendor_code
                   FROM movement_history
                   WHERE file_id=%s AND posting_date=%s
                   ORDER BY source_row_number""",
                (file_id, requested),
            )
            rows = cur.fetchall()
            counters[file_id] = _signature_counter(rows)

            by_type: dict[str, dict[str, Any]] = {}
            article_numbers = set()
            mapped_articles = 0
            mapped_families = 0
            for row in rows:
                if row.get("article_number") is not None:
                    article_numbers.add(str(row["article_number"]))
                if row.get("article_id") is not None:
                    mapped_articles += 1
                if row.get("family_id") is not None:
                    mapped_families += 1
                mt = str(row.get("movement_type") or "UNKNOWN")
                stat = by_type.setdefault(
                    mt,
                    {"movement_type": mt, "row_count": 0, "base_quantity": Decimal("0")},
                )
                stat["row_count"] += 1
                if row.get("base_quantity") is not None:
                    stat["base_quantity"] += Decimal(str(row["base_quantity"]))

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM raw_movement r
                   JOIN ingest_sheet s ON s.sheet_id=r.sheet_id
                   WHERE s.file_id=%s
                     AND r.observed_business_date=%s""",
                (file_id, requested),
            )
            dated_raw = int((cur.fetchone() or {}).get("c") or 0)

            summaries.append(
                {
                    "file_id": file_id,
                    "filename": f["original_filename"],
                    "batch_id": int(f["batch_id"]),
                    "is_current_canonical": file_id == canonical_file_id,
                    "source_chronology_rank": len(summaries) + 1,
                    "report_generated_at": f.get("report_generated_at"),
                    "filename_date_candidate": f.get("filename_date_candidate"),
                    "filename_time_candidate": f.get("filename_time_candidate"),
                    "upload_timestamp": f.get("upload_timestamp"),
                    "source_row_count": int(f.get("source_row_count") or 0),
                    "dated_raw_rows": dated_raw,
                    "normalized_rows_on_date": len(rows),
                    "distinct_articles": len(article_numbers),
                    "article_mapped_rows": mapped_articles,
                    "family_mapped_rows": mapped_families,
                    "movement_types": [
                        {
                            "movement_type": stat["movement_type"],
                            "row_count": stat["row_count"],
                            "base_quantity": stat["base_quantity"],
                        }
                        for _, stat in sorted(by_type.items())
                    ],
                }
            )

        pairwise = []
        for i in range(1, len(files)):
            earlier = files[i - 1]
            later = files[i]
            pairwise.append(
                _relationship(
                    earlier,
                    later,
                    counters[int(earlier["file_id"])],
                    counters[int(later["file_id"])],
                )
            )

        earliest_vs_latest = None
        if len(files) >= 2:
            earliest_vs_latest = _relationship(
                files[0],
                files[-1],
                counters[int(files[0]["file_id"])],
                counters[int(files[-1]["file_id"])],
            )

        if not files:
            assessment = "NO_ELIGIBLE_FILES"
            next_action = "No same-day comparison can be made."
        elif len(files) == 1:
            assessment = "SINGLE_ELIGIBLE_FILE"
            next_action = "No same-day collision exists for this date."
        else:
            relation = (earliest_vs_latest or {}).get("relationship")
            if relation == "LATER_SUBSET_OF_EARLIER":
                assessment = "LATEST_FILE_SUBSET_RISK"
                next_action = (
                    "Do not treat latest-file-wins as proof of a complete daily snapshot. "
                    "Review source semantics before changing canonical MVT authority."
                )
            elif relation == "LATER_SUPERSET_OF_EARLIER":
                assessment = "LATEST_FILE_SUPERSET"
                next_action = (
                    "Latest file contains all earlier normalized rows plus additional rows; "
                    "validate that this report family is a cumulative snapshot before authority changes."
                )
            elif relation == "IDENTICAL":
                assessment = "EQUIVALENT_SNAPSHOTS"
                next_action = "Latest-file-wins is not losing normalized rows for this date."
            elif relation == "DISJOINT":
                assessment = "DISJOINT_SAME_DAY_EXPORTS"
                next_action = (
                    "Same-day files contain different movement populations; canonical selection "
                    "must fail closed until report scope semantics are established."
                )
            else:
                assessment = "PARTIAL_OVERLAP_REVIEW_REQUIRED"
                next_action = (
                    "Same-day exports partially overlap. Determine whether they are cumulative, "
                    "incremental, or filtered before changing canonical selection."
                )

        cur.close()
        return {
            "requested_date": requested,
            "read_only": True,
            "authority_changed": False,
            "current_canonical_file_id": canonical_file_id,
            "eligible_file_count": len(files),
            "assessment": assessment,
            "recommended_next_action": next_action,
            "signature_fields": list(_SIGNATURE_FIELDS),
            "files": summaries,
            "pairwise_chronology": pairwise,
            "earliest_vs_latest": earliest_vs_latest,
        }
