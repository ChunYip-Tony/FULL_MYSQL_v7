from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from db import db_conn


def _j(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if v is None:
        return {}
    if isinstance(v, (bytes, bytearray)):
        v = v.decode("utf-8", errors="replace")
    try:
        obj = json.loads(v)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _text(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _norm_header(v: Any) -> str:
    s = (_text(v) or "").upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _id(v: Any) -> str | None:
    s = _text(v)
    if not s:
        return None
    s = s.replace(",", "")
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".", 1)[0]
    return s if re.fullmatch(r"\d+", s) else None


def _date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = _text(v)
    if not s:
        return None
    s2 = s.replace("-", "/").replace(".", "/")
    for fmt in (
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(s2[:19], fmt).date()
        except ValueError:
            pass
    return None


def _num(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("$", "")
    if not s or s in {"-", "--"}:
        return None
    try:
        float(s)
        return s
    except Exception:
        return None


def _col_rank(col: str) -> int:
    n = 0
    for ch in str(col or "").upper():
        if "A" <= ch <= "Z":
            n = n * 26 + (ord(ch) - 64)
    return n if n > 0 else 10**9


def movement_parser_diagnostic(file_id: int) -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """SELECT file_id,batch_id,original_filename,source_type,processing_status,
                      source_row_count,coverage_start_date,coverage_end_date,
                      date_semantics_status,upload_timestamp
               FROM ingest_file
               WHERE file_id=%s
               LIMIT 1""",
            (int(file_id),),
        )
        source = cur.fetchone()
        if not source:
            cur.close()
            raise KeyError("MOVEMENT_FILE_NOT_FOUND")
        if str(source.get("source_type") or "").lower() != "movement":
            cur.close()
            raise ValueError("FILE_IS_NOT_MOVEMENT")

        cur.execute(
            """SELECT sheet_id,sheet_index,sheet_name,header_row_number,row_count,column_count
               FROM ingest_sheet
               WHERE file_id=%s
               ORDER BY sheet_index""",
            (int(file_id),),
        )
        sheets = cur.fetchall()

        sheet_results = []
        for sh in sheets:
            cur.execute(
                """SELECT raw_id,source_row_number,observed_business_date,
                          raw_payload,raw_text
                   FROM raw_movement
                   WHERE sheet_id=%s
                     AND source_row_number<=80
                   ORDER BY source_row_number""",
                (sh["sheet_id"],),
            )
            rows = cur.fetchall()

            candidates = []
            for rr in rows:
                p = _j(rr.get("raw_payload"))
                occurrences: dict[str, list[dict[str, Any]]] = {}
                for col, value in sorted(p.items(), key=lambda kv: _col_rank(kv[0])):
                    key = _norm_header(value)
                    if not key:
                        continue
                    occurrences.setdefault(key, []).append(
                        {"column": col, "raw_header": _text(value)}
                    )

                tokens = set(occurrences)
                has_article = "ARTICLE" in tokens
                has_mvt = any(x in tokens for x in {"MVT", "MOVEMENT TYPE", "MOVEMENT"})
                has_posting = any(
                    x in tokens
                    for x in {"PSTNG DATE", "POSTING DATE", "POST DATE", "BUSINESS DATE"}
                )
                if has_article and has_mvt and has_posting:
                    candidates.append(
                        {
                            "source_row_number": rr["source_row_number"],
                            "declared_header_row": sh.get("header_row_number"),
                            "header_occurrences": occurrences,
                        }
                    )

            chosen = candidates[0] if candidates else None
            resolved = {}
            duplicate_headers = {}
            if chosen:
                occ = chosen["header_occurrences"]
                for key, values in occ.items():
                    resolved[key] = values[0]["column"]
                    if len(values) > 1:
                        duplicate_headers[key] = values

            article_col = resolved.get("ARTICLE")
            mvt_col = (
                resolved.get("MVT")
                or resolved.get("MOVEMENT TYPE")
                or resolved.get("MOVEMENT")
            )
            posting_col = (
                resolved.get("PSTNG DATE")
                or resolved.get("POSTING DATE")
                or resolved.get("POST DATE")
                or resolved.get("BUSINESS DATE")
            )
            entry_qty_col = (
                resolved.get("QTY IN UNE")
                or resolved.get("QUANTITY IN UNE")
                or resolved.get("QUANTITY")
                or resolved.get("ENTRY QUANTITY")
            )
            entry_uom_col = resolved.get("EUN") or resolved.get("ENTRY UOM")
            base_qty_col = (
                resolved.get("QUANTITY I")
                or resolved.get("QUANTITY IN BUN")
                or resolved.get("QUANTITY IN BASE UNIT")
                or resolved.get("BASE QUANTITY")
            )
            base_uom_col = resolved.get("BUN") or resolved.get("BASE UOM")

            parsed_samples = []
            valid_count = 0
            dated_raw_count = 0
            for rr in rows:
                if rr.get("observed_business_date") is not None:
                    dated_raw_count += 1
                if not chosen or int(rr["source_row_number"]) <= int(chosen["source_row_number"]):
                    continue
                p = _j(rr.get("raw_payload"))
                sample = {
                    "source_row_number": rr["source_row_number"],
                    "observed_business_date": rr.get("observed_business_date"),
                    "article_raw": p.get(article_col) if article_col else None,
                    "article_parsed": _id(p.get(article_col)) if article_col else None,
                    "mvt_raw": p.get(mvt_col) if mvt_col else None,
                    "mvt_parsed": _id(p.get(mvt_col)) if mvt_col else None,
                    "posting_raw": p.get(posting_col) if posting_col else None,
                    "posting_parsed": _date(p.get(posting_col)) if posting_col else None,
                    "entry_qty_raw": p.get(entry_qty_col) if entry_qty_col else None,
                    "entry_qty_numeric": _num(p.get(entry_qty_col)) if entry_qty_col else None,
                    "entry_uom": _text(p.get(entry_uom_col)) if entry_uom_col else None,
                    "base_qty_raw": p.get(base_qty_col) if base_qty_col else None,
                    "base_qty_numeric": _num(p.get(base_qty_col)) if base_qty_col else None,
                    "base_uom": _text(p.get(base_uom_col)) if base_uom_col else None,
                }
                sample["structurally_valid"] = bool(
                    sample["article_parsed"]
                    and sample["mvt_parsed"]
                    and sample["posting_parsed"]
                )
                if sample["structurally_valid"]:
                    valid_count += 1
                if len(parsed_samples) < 12 and (
                    sample["observed_business_date"] is not None
                    or sample["structurally_valid"]
                ):
                    parsed_samples.append(sample)

            sheet_results.append(
                {
                    "sheet": sh,
                    "header_candidates": candidates,
                    "chosen_header_row": chosen["source_row_number"] if chosen else None,
                    "resolved_columns": {
                        "article": article_col,
                        "movement_type": mvt_col,
                        "posting_date": posting_col,
                        "entry_quantity": entry_qty_col,
                        "entry_uom": entry_uom_col,
                        "base_quantity": base_qty_col,
                        "base_uom": base_uom_col,
                    },
                    "duplicate_headers": duplicate_headers,
                    "dated_raw_rows_in_first_80": dated_raw_count,
                    "structurally_valid_rows_in_first_80": valid_count,
                    "parsed_samples": parsed_samples,
                }
            )

        cur.close()
        return {
            "source_file": source,
            "sheets": sheet_results,
            "diagnostic_note": (
                "Read-only parser diagnostic over stored RAW payload. "
                "No normalization or authority is changed."
            ),
        }
