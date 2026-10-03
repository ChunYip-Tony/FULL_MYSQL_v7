from __future__ import annotations

import json
import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from db import db_conn
from data_coverage import source_data_days, coverage_summary
from business_clock import BUSINESS_TIMEZONE, business_today, completed_through_date
from manual_overrides import (
    ensure_override_table,
    ensure_retirement_table,
    ensure_cost_conversion_table,
    ensure_family_cost_table,
    ensure_article_family_override_table,
    apply_manual_upc_overrides,
    apply_manual_upc_retirements,
    apply_manual_cost_conversions,
    apply_manual_family_costs,
    apply_manual_family_subarticles,
    apply_manual_article_family_overrides,
    confirmed_cost_conversion,
    confirmed_family_cost,
    confirmed_receipt_entry_cost_basis,
    confirmed_operational_uom_basis,
)
from active_product_repair import repair_active_product_master
from article_manual_multitab_repair import repair_article_manual_multitab
from cross_tab_signature_repair import repair_cross_tab_signature
from temporary_qa_waivers import apply_temporary_identity_waivers
from active_28d_uom_repair import repair_active_28d_uom
from current_active_cost_repair import repair_current_active_cost
from product_identity_audit import audit_product_identity
from quick_check_app import expire_true_stock_for_new_oh
from inventory_position import rollforward_position
from receipt_semantics import RECEIPT_COST_MOVEMENTS
from upc_aliases import (
    service_249_canonical_base,
    service_249_source_prefix,
    source_ean_predicate,
    normalize_selling_description,
    looks_like_249_service_description,
)
from coverage_backfill import (
    ensure_coverage_backfill_tables,
    resolve_pos_period_backfill,
    relink_pos_backfill,
    article_manual_pos_alias_index,
    resolve_article_manual_pos_upc_id,
)
from analysis_layer import (
    DEPARTMENT_REGISTRY,
    ensure_analysis_layer_tables,
    refresh_analysis_layer,
    audit_analysis_layer,
)

PRICE_TYPE_PRIORITY = {'IN STORE': 4, 'INSTORE': 4, 'STOR': 4, 'SALE': 3, 'TPR': 2, 'REG': 1, 'REGULAR': 1}
SALES_COLS = {
    'REG': ('E', 'F'),
    'IN STORE': ('G', 'H'),
    'TPR': ('I', 'J'),
    'SALE': ('K', 'L'),
}
RECEIPT_MOVEMENTS = {'101', '107', '109'}
FAMILY_SALE_MOVEMENTS = {'251', '252'}
SEAFOOD_DEPT_CODE = '400'
SEAFOOD_PRICE_SUBDEPT_CODES = {'400', '401'}

def _department_from_price_subdept(code: str | None) -> str | None:
    if not code:
        return None
    s = str(code).strip()
    if s in SEAFOOD_PRICE_SUBDEPT_CODES:
        return '400'
    if len(s) == 3 and s.startswith('3'):
        return '300'
    if len(s) == 3 and s.startswith('5'):
        return '500'
    return None


def _department_from_pos_section(code: str | None) -> str | None:
    """Normalize POS section headers to the canonical department code.

    Seafood POS exports can use either 400 or 401 section headers. Both belong
    to Seafood for selling-history purposes, matching the Price List rule.
    """
    if not code:
        return None
    s = str(code).strip()
    if s in SEAFOOD_PRICE_SUBDEPT_CODES:
        return SEAFOOD_DEPT_CODE
    if s == '300':
        return '300'
    if s == '500':
        return '500'
    return None

def _department_from_merch_category(code: str | None) -> str | None:
    """Map perishable SAP merchandise categories to app department codes.

    Current authoritative OH layout:
    - 201... => Meat (300)
    - 301... / 302... => Produce (500)
    - 401... => Seafood (400)

    Unknown categories remain unresolved rather than guessed.
    """
    if not code:
        return None
    s = str(code).strip()
    if s.startswith('201'):
        return '300'
    if s.startswith('301') or s.startswith('302'):
        return '500'
    if s.startswith('401'):
        return '400'
    return None


def _j(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if v is None:
        return {}
    if isinstance(v, (bytes, bytearray)):
        v = v.decode('utf-8', errors='replace')
    try:
        return json.loads(v)
    except Exception:
        return {}


def _text(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _id(v: Any) -> str | None:
    s = _text(v)
    if not s:
        return None
    s = s.replace(',', '')
    if re.fullmatch(r'\d+\.0+', s):
        s = s.split('.', 1)[0]
    if not re.fullmatch(r'\d+', s):
        return None
    return s


def _gr_5014_id(v: Any) -> str | None:
    """Return a validated Seafood SAP GR/material-document number.

    Store-specific receipt evidence confirms GR numbers use the 5014 prefix.
    Do not classify PO/reference/other SAP document values as GR unless this
    prefix is present.
    """
    doc = _id(v)
    return doc if doc and doc.startswith("5014") else None


def _numeric_key(v: str | None) -> str | None:
    if not v or not re.fullmatch(r'\d+', v):
        return None
    k = v.lstrip('0')
    return k or '0'


def _upca_check_digit(body11: str) -> str | None:
    if not re.fullmatch(r'\d{11}', str(body11 or '')):
        return None
    digits=[int(x) for x in body11]
    total=sum(digits[0::2])*3 + sum(digits[1::2])
    return str((10-(total % 10)) % 10)


def _ean13_check_digit(body12: str) -> str | None:
    if not re.fullmatch(r'\d{12}', str(body12 or '')):
        return None
    digits=[int(x) for x in body12]
    total=sum(digits[0::2]) + sum(digits[1::2])*3
    return str((10-(total % 10)) % 10)


def _upca_alias_candidates(raw: str | None) -> list[str]:
    """Deterministic shortened retail-barcode candidates.

    Only generates candidates; callers must require an exact authoritative hit.
    - 12 digits may be an EAN-13 body missing its check digit.
    - 11 digits may be a UPC-A body missing its check digit.
    - 10 digits may be a leading-zero UPC-A body missing its check digit.
    Leading-zero-only variants are already handled by numeric equivalence.
    """
    s=str(raw or '').strip()
    out=[]
    if re.fullmatch(r'\d{12}',s):
        cd=_ean13_check_digit(s)
        if cd is not None:
            out.append(s+cd)
    elif re.fullmatch(r'\d{11}',s):
        cd=_upca_check_digit(s)
        if cd is not None:
            out.append(s+cd)
    elif re.fullmatch(r'\d{10}',s):
        body='0'+s
        cd=_upca_check_digit(body)
        if cd is not None:
            out.append(body+cd)
    return out


def _num(v: Any) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        try:
            return Decimal(str(v))
        except Exception:
            return None
    s = str(v).strip().replace(',', '').replace('$', '')
    if not s or s in {'-', '--'}:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = _text(v)
    if not s:
        return None
    s2 = s.replace('-', '/').replace('.', '/')
    for fmt in ('%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d', '%Y/%m/%d %H:%M:%S', '%m/%d/%Y %H:%M:%S'):
        try:
            return datetime.strptime(s2[:19], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None


def _datetime(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, datetime.min.time())
    s = _text(v)
    if not s:
        return None
    for fmt in ('%m/%d/%Y %I:%M:%S %p', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _norm_header(v: Any) -> str:
    s = (_text(v) or '').upper()
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _row_cells(payload: dict[str, Any]) -> list[Any]:
    def key(col: str) -> int:
        n = 0
        for ch in col:
            if 'A' <= ch <= 'Z':
                n = n * 26 + ord(ch) - 64
        return n
    return [payload[k] for k in sorted(payload.keys(), key=key)]


def _find_upc_id(cur, ean: str | None) -> int | None:
    if not ean:
        return None
    cur.execute('SELECT upc_id FROM selling_upc WHERE ean_upc=%s', (ean,))
    r = cur.fetchone()
    if r:
        return int(r['upc_id'])
    # Internal POS codes can be padded with leading zeroes. Match numerically while preserving
    # the raw source spelling in history (e.g. 00000004918 -> canonical selling_upc 4918).
    key = _numeric_key(ean)
    if key is None:
        return None
    cur.execute(
        """SELECT upc_id FROM selling_upc
           WHERE ean_upc REGEXP '^[0-9]+$'
             AND TRIM(LEADING '0' FROM ean_upc)=%s
           ORDER BY CHAR_LENGTH(ean_upc),upc_id LIMIT 1""",
        (key,),
    )
    r = cur.fetchone()
    if r:
        return int(r['upc_id'])

    # 249 fried/cook-service exports may use the six-digit service code
    # or a scale-derived suffix. Resolve only through an exact ACTIVE
    # canonical 249 + 3-digit product code + 00000 roster hit.
    service_candidate = service_249_canonical_base(ean)
    if service_candidate and service_candidate != str(ean):
        cur.execute(
            """SELECT upc_id FROM selling_upc
               WHERE ean_upc=%s
                 AND record_status='ACTIVE'
               LIMIT 1""",
            (service_candidate,),
        )
        service_hit=cur.fetchone()
        if service_hit:
            return int(service_hit['upc_id'])
    # Conservative UPC-A normalization: a generated check-digit candidate is
    # accepted only when that exact canonical UPC already exists in selling_upc.
    for candidate in _upca_alias_candidates(ean):
        cur.execute(
            """SELECT upc_id
               FROM selling_upc
               WHERE ean_upc=%s
                 AND record_status='ACTIVE'
               LIMIT 1""",
            (candidate,),
        )
        hit=cur.fetchone()
        if hit:
            return int(hit['upc_id'])
    return None


def _find_pos_upc_id(
    cur,
    ean: str | None,
    description: str | None,
    article_manual_index: dict[str, Any] | None = None,
) -> int | None:
    """Resolve one Seafood POS row with RAW identity first, manual verification next.

    Priority:
      1) exact/numeric RAW POS UPC and deterministic 249 product-code alias,
      2) newest Article Manual identity when RAW does not resolve,
      3) explicit Fried/Cook Service description fallback.

    When RAW/product-code identity and Article Manual both resolve but disagree,
    the row fails closed so normal SOLD_UPC_UNMAPPED QA can surface the conflict.
    Sold quantity remains POS-only; Article Manual and SAP movement never add
    UPC sales quantity.
    """
    if article_manual_index is None:
        article_manual_index = article_manual_pos_alias_index(cur)

    base_id=_find_upc_id(cur,ean)
    manual_id = resolve_article_manual_pos_upc_id(
        article_manual_index,
        ean,
        seafood_context=True,
    )

    if base_id is not None:
        if manual_id is not None and int(manual_id) != int(base_id):
            return None
        return int(base_id)

    if manual_id is not None:
        return int(manual_id)

    if not looks_like_249_service_description(description):
        return None

    desc_key=normalize_selling_description(description)
    if not desc_key:
        return None

    cur.execute(
        """SELECT DISTINCT su.upc_id,su.ean_upc,su.selling_description
           FROM selling_upc su
           JOIN bridge_article_upc bau
             ON bau.upc_id=su.upc_id
            AND bau.mapping_status='CONFIRMED'
            AND bau.is_primary=TRUE
            AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
           JOIN bridge_article_family baf
             ON baf.article_id=bau.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           WHERE su.record_status='ACTIVE'
             AND su.ean_upc LIKE '249%'
           ORDER BY su.upc_id"""
    )
    matches={
        int(row["upc_id"])
        for row in cur.fetchall()
        if normalize_selling_description(row.get("selling_description"))==desc_key
    }
    if len(matches)==1:
        return next(iter(matches))
    return None


def _upc_id_identity_ready(cur, upc_id: int | None) -> bool:
    """Return whether one canonical UPC has one current confirmed Article/Family path."""
    if upc_id is None:
        return False
    cur.execute(
        """SELECT 1
           FROM selling_upc su
           JOIN bridge_article_upc bau
             ON bau.upc_id=su.upc_id
            AND bau.mapping_status='CONFIRMED'
            AND bau.is_primary=TRUE
            AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
           JOIN bridge_article_family baf
             ON baf.article_id=bau.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           LEFT JOIN manual_upc_retirement mur
             ON mur.ean_upc=su.ean_upc
            AND mur.retirement_status='CONFIRMED'
           WHERE su.upc_id=%s
             AND su.record_status='ACTIVE'
             AND mur.retirement_id IS NULL
           LIMIT 1""",
        (int(upc_id),),
    )
    return bool(cur.fetchone())


def _upc_identity_ready(cur, ean: str | None) -> bool:
    return _upc_id_identity_ready(cur, _find_upc_id(cur, ean))


def _structural_sap_selling_upc(article_number: str | None) -> str | None:
    """Deterministic Seafood SAP selling-Article -> canonical UPC bridge.

    Known structural forms used by Store #1032:
      1540xxx -> 240xxx00000
      1545xxx -> 245xxx00000
      1549xxx -> 249xxx00000

    This function only derives the exact candidate identifier. Family authority
    still requires that candidate UPC to exist as ACTIVE and resolve through one
    unique current CONFIRMED UPC -> Article -> Family path.
    """
    s = str(article_number or '').strip()
    m = re.fullmatch(r'154([059])(\d{3})', s)
    if not m:
        return None
    prefix = {'0': '240', '5': '245', '9': '249'}[m.group(1)]
    return f"{prefix}{m.group(2)}00000"


def _structural_sap_selling_family(cur, article_number: str | None) -> int | None:
    ean = _structural_sap_selling_upc(article_number)
    if not ean:
        return None
    cur.execute(
        """SELECT COUNT(DISTINCT baf.family_id) AS family_count,
                  MIN(baf.family_id) AS family_id
           FROM selling_upc su
           JOIN bridge_article_upc bau
             ON bau.upc_id=su.upc_id
            AND bau.mapping_status='CONFIRMED'
            AND bau.is_primary=TRUE
            AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
           JOIN bridge_article_family baf
             ON baf.article_id=bau.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           LEFT JOIN manual_upc_retirement mur
             ON mur.ean_upc=su.ean_upc
            AND mur.retirement_status='CONFIRMED'
           WHERE su.ean_upc=%s
             AND su.record_status='ACTIVE'
             AND mur.retirement_id IS NULL""",
        (ean,),
    )
    row = cur.fetchone() or {}
    if int(row.get('family_count') or 0) != 1 or row.get('family_id') is None:
        return None
    return int(row['family_id'])


def _find_article(cur, article_number: str | None) -> tuple[int | None, int | None]:
    if not article_number:
        return None, None
    cur.execute(
        """SELECT a.article_id,baf.family_id
           FROM article a
           LEFT JOIN bridge_article_family baf
             ON baf.article_id=a.article_id AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           WHERE a.article_number=%s
           ORDER BY CASE WHEN baf.family_id IS NULL THEN 1 ELSE 0 END,
                    baf.article_family_id DESC
           LIMIT 1""",
        (article_number,),
    )
    r = cur.fetchone()
    article_id = int(r['article_id']) if r and r.get('article_id') is not None else None
    if r and r.get('family_id') is not None:
        return article_id, int(r['family_id'])

    # A SAP 251/252 selling Article can appear in movement before its SUB bridge
    # is materialized. Recover the Family only through the exact structural
    # Article -> canonical UPC transform and a unique confirmed UPC family.
    family_id = _structural_sap_selling_family(cur, article_number)
    return article_id, family_id


def _uom_id(cur, token: str | None) -> int | None:
    t = _text(token)
    if not t:
        return None
    t = t.upper()
    cur.execute('SELECT uom_id FROM dim_uom WHERE UPPER(uom_code)=%s', (t,))
    r = cur.fetchone()
    return int(r['uom_id']) if r else None


def _issue(cur, batch_id: int, code: str, entity_type: str, entity_key: str, summary: str,
           severity: str = 'MEDIUM', file_id: int | None = None, sheet_id: int | None = None,
           raw_table: str | None = None, raw_id: int | None = None, detail: dict[str, Any] | None = None) -> None:
    # Avoid duplicate open issues for the same raw row/code when Phase 3 is re-run.
    cur.execute(
        """SELECT issue_id FROM qa_phase3_issue
           WHERE batch_id=%s AND issue_status='OPEN' AND issue_code=%s AND entity_type=%s AND entity_key=%s
             AND COALESCE(raw_table_name,'')=COALESCE(%s,'') AND COALESCE(raw_id,0)=COALESCE(%s,0)
           LIMIT 1""",
        (batch_id, code, entity_type, entity_key, raw_table, raw_id),
    )
    if cur.fetchone():
        return
    cur.execute(
        """INSERT INTO qa_phase3_issue
           (batch_id,severity,issue_code,entity_type,entity_key,issue_summary,file_id,sheet_id,raw_table_name,raw_id,detail_json)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (batch_id, severity, code, entity_type, entity_key, summary, file_id, sheet_id, raw_table, raw_id,
         json.dumps(detail or {}, ensure_ascii=False, default=str)),
    )


def _printed_timestamp(rows: list[dict[str, Any]]) -> datetime | None:
    for rr in rows[:120]:
        payload = _j(rr['raw_payload'])
        cells = _row_cells(payload)
        for i, v in enumerate(cells):
            if 'PRINTED' in (_text(v) or '').upper():
                for x in cells[i + 1:i + 4]:
                    dt = _datetime(x)
                    if dt:
                        return dt
    return None


def _process_sales(cur, batch_id: int, f: dict[str, Any]) -> int:
    start = f.get('header_period_start_date') or f.get('coverage_start_date')
    end = f.get('header_period_end_date') or f.get('coverage_end_date')
    if not start or not end:
        _issue(cur, batch_id, 'SALES_PERIOD_UNRESOLVED', 'FILE', str(f['file_id']),
               f"Sales period is unresolved for {f['original_filename']}; Sales history cannot be published safely.",
               'HIGH', file_id=f['file_id'])
        return 0
    temporal = 'SINGLE_DATE' if start == end else 'DATE_RANGE'
    inserted = 0
    # Build once per POS file. RAW UPC / 249 product code resolves first;
    # Article Manual verifies or fills identity and never contributes quantity.
    article_manual_index = article_manual_pos_alias_index(cur)
    cur.execute('SELECT sheet_id FROM ingest_sheet WHERE file_id=%s ORDER BY sheet_index', (f['file_id'],))
    for sh in cur.fetchall():
        cur.execute("SELECT raw_id,source_row_number,raw_payload FROM raw_sales_by_price_type WHERE sheet_id=%s ORDER BY source_row_number", (sh['sheet_id'],))
        rows = cur.fetchall()
        current_dept = None
        for rr in rows:
            p = _j(rr['raw_payload'])
            a = _id(p.get('A'))
            b = _text(p.get('B'))
            # Department section rows are exact 3-digit department IDs and have no total sales columns.
            if a and len(a) == 3 and b and not _num(p.get('M')) and not _num(p.get('N')):
                current_dept = _department_from_pos_section(a)
                continue
            if current_dept not in DEPARTMENT_REGISTRY:
                continue
            ean = a
            if not ean or not b:
                continue
            # Product sales rows have TOTAL amount/qty or at least one price-type amount/qty.
            if not any(_num(p.get(c)) is not None for pair in SALES_COLS.values() for c in pair):
                continue
            upc_id = (
                _find_pos_upc_id(cur, ean, b, article_manual_index)
                if current_dept == SEAFOOD_DEPT_CODE
                else _find_upc_id(cur, ean)
            )
            cur.execute(
                """INSERT INTO upc_department_observation
                   (upc_id,ean_upc,department_code,department_name,source_type,
                    business_date,batch_id,file_id,sheet_id,source_row_number)
                   VALUES (%s,%s,%s,%s,'POS',%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                     upc_id=VALUES(upc_id),
                     department_name=VALUES(department_name),
                     business_date=VALUES(business_date),
                     batch_id=VALUES(batch_id)""",
                (
                    upc_id, ean, current_dept, DEPARTMENT_REGISTRY[current_dept],
                    end, batch_id, f['file_id'], sh['sheet_id'], rr['source_row_number'],
                ),
            )
            total_qty = Decimal('0')
            for price_type, (sales_col, qty_col) in SALES_COLS.items():
                sales = _num(p.get(sales_col)) or Decimal('0')
                qty = _num(p.get(qty_col)) or Decimal('0')
                if sales == 0 and qty == 0:
                    continue
                avg = (sales / qty) if qty != 0 else None
                cur.execute(
                    """INSERT INTO sales_period_observation
                       (batch_id,file_id,sheet_id,raw_id,source_row_number,ean_upc,upc_id,description,
                        period_start_date,period_end_date,temporal_grain,price_type,sales_amount,sold_quantity,avg_sold_price)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE upc_id=VALUES(upc_id),description=VALUES(description),
                        sales_amount=VALUES(sales_amount),sold_quantity=VALUES(sold_quantity),avg_sold_price=VALUES(avg_sold_price)""",
                    (batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], rr['source_row_number'], ean, upc_id, b,
                     start, end, temporal, price_type, sales, qty, avg),
                )
                inserted += 1
                total_qty += qty
            if total_qty > 0 and upc_id is None:
                if current_dept == SEAFOOD_DEPT_CODE:
                    _issue(cur, batch_id, 'SOLD_UPC_UNMAPPED', 'UPC', ean,
                           f'POS sold quantity exists for Seafood UPC {ean}, but no confirmed UPC identity mapping exists.',
                           'HIGH', f['file_id'], sh['sheet_id'], 'raw_sales_by_price_type', rr['raw_id'],
                           {'description': b, 'department_code': current_dept})
                else:
                    _issue(cur, batch_id, f'{DEPARTMENT_REGISTRY[current_dept]}_SOLD_UPC_UNMAPPED', 'UPC', ean,
                           f'POS sold quantity exists for {DEPARTMENT_REGISTRY[current_dept]} UPC {ean}, but no confirmed UPC identity mapping exists.',
                           'MEDIUM', f['file_id'], sh['sheet_id'], 'raw_sales_by_price_type', rr['raw_id'],
                           {'description': b, 'department_code': current_dept, 'scope': 'DEPARTMENT_LOCAL_HOLD'})
    return inserted


def _backfill_recent_pos_history(
    cur,
    *,
    exclude_batch_id: int | None = None,
    lookback_days: int = 45,
) -> dict[str, Any]:
    """Reprocess recent immutable POS RAW with the current department/UPC resolver.

    This is required for historical Seafood service rows that were present in
    RAW but were skipped before 401 POS section headers were normalized to the
    canonical Seafood department 400. Reprocessing is idempotent because
    sales_period_observation and upc_department_observation use their existing
    source-row unique keys with ON DUPLICATE KEY UPDATE.

    POS remains the sole source of UPC sold quantity. No 251/252 or 317/318
    movement quantity is converted into UPC sales by this repair.
    """
    days=max(7,min(int(lookback_days or 45),120))
    cutoff=completed_through_date()-timedelta(days=days)
    args: list[Any]=[cutoff]
    exclude_sql=''
    if exclude_batch_id is not None:
        exclude_sql=' AND batch_id<>%s'
        args.append(int(exclude_batch_id))

    cur.execute(
        f"""SELECT batch_id,file_id,original_filename,source_type,
                   coverage_start_date,coverage_end_date,
                   header_period_start_date,header_period_end_date,
                   report_generated_at,upload_timestamp,filename_date_candidate
            FROM ingest_file
            WHERE source_type='sales_by_price_type'
              AND processing_status='INGESTED'
              AND duplicate_of_file_id IS NULL
              AND COALESCE(header_period_end_date,coverage_end_date)>=%s
              {exclude_sql}
            ORDER BY file_id""",
        tuple(args),
    )
    files=cur.fetchall()
    rows_processed=0
    source_batches:set[int]=set()
    file_ids:list[int]=[]
    for row in files:
        source_batch_id=int(row['batch_id'])
        source_batches.add(source_batch_id)
        file_ids.append(int(row['file_id']))
        rows_processed += _process_sales(cur, source_batch_id, row)

    return {
        'lookback_days': days,
        'cutoff_date': cutoff,
        'files_reprocessed': len(files),
        'source_batches_reprocessed': sorted(source_batches),
        'file_ids_reprocessed': file_ids,
        'sales_rows_processed': rows_processed,
        'rule': 'REPROCESS_RECENT_POS_RAW_WITH_CURRENT_DEPARTMENT_AND_UPC_RESOLVER',
        'upc_qty_source': 'POS_ONLY',
        'movement_used_as_upc_qty': False,
    }


def _process_price(cur, batch_id: int, f: dict[str, Any]) -> int:
    inserted = 0
    cur.execute('SELECT sheet_id FROM ingest_sheet WHERE file_id=%s ORDER BY sheet_index', (f['file_id'],))
    for sh in cur.fetchall():
        cur.execute("SELECT raw_id,source_row_number,raw_payload FROM raw_price_list WHERE sheet_id=%s ORDER BY source_row_number", (sh['sheet_id'],))
        rows = cur.fetchall()
        # Price List is a point-in-time configured-price snapshot.  Per the
        # serving contract, its freshness starts when the file is uploaded,
        # not from a printed/report timestamp embedded in the workbook.
        snapshot = f.get('upload_timestamp') or f.get('report_generated_at') or _printed_timestamp(rows) or datetime.now()
        current_dept = None
        for rr in rows:
            p = _j(rr['raw_payload'])
            a_txt = (_text(p.get('A')) or '')
            if 'SUBDEPT' in a_txt.upper():
                current_dept = _department_from_price_subdept(_id(p.get('B')))
                continue
            if current_dept not in DEPARTMENT_REGISTRY:
                continue
            ean = _id(p.get('A'))
            desc = _text(p.get('B'))
            if not ean or not desc:
                continue
            price = _num(p.get('J'))
            price_qty = _num(p.get('K'))
            ptype = (_text(p.get('P')) or '').upper()
            if ptype not in {'REG', 'TPR', 'SALE', 'IN STORE', 'INSTORE', 'STOR'}:
                continue
            normalized_ptype = 'IN STORE' if ptype in {'INSTORE', 'STOR'} else ptype
            since = _date(p.get('Q'))
            upc_id = _find_upc_id(cur, ean)
            cur.execute(
                """INSERT INTO upc_department_observation
                   (upc_id,ean_upc,department_code,department_name,source_type,
                    business_date,batch_id,file_id,sheet_id,source_row_number)
                   VALUES (%s,%s,%s,%s,'PRICE_LIST',%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                     upc_id=VALUES(upc_id),
                     department_name=VALUES(department_name),
                     business_date=VALUES(business_date),
                     batch_id=VALUES(batch_id)""",
                (
                    upc_id, ean, current_dept, DEPARTMENT_REGISTRY[current_dept],
                    snapshot.date(), batch_id, f['file_id'], sh['sheet_id'], rr['source_row_number'],
                ),
            )
            cur.execute(
                """INSERT INTO price_list_observation
                   (batch_id,file_id,sheet_id,raw_id,source_row_number,ean_upc,upc_id,description,
                    configured_price,price_quantity,price_type,source_since_date,snapshot_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE upc_id=VALUES(upc_id),configured_price=VALUES(configured_price),
                    price_quantity=VALUES(price_quantity),price_type=VALUES(price_type),source_since_date=VALUES(source_since_date),snapshot_at=VALUES(snapshot_at)""",
                (batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], rr['source_row_number'], ean, upc_id, desc,
                 price, price_qty, normalized_ptype, since, snapshot),
            )
            inserted += 1
    return inserted


def _movement_header_map(cur, sheet_id: int, declared_header_row: int | None) -> dict[str, str]:
    """Find the SAP movement header from RAW rows instead of trusting generic header detection.

    Dynamic List Display exports often have leading blank columns and detail rows
    with more non-empty cells than the real header. The generic workbook header
    detector can therefore point at a data row. For movement parsing, scan the
    first 80 RAW rows and require semantic header tokens.
    """
    def _col_rank(col: str) -> int:
        n = 0
        for ch in str(col or "").upper():
            if "A" <= ch <= "Z":
                n = n * 26 + (ord(ch) - 64)
        return n if n > 0 else 10**9

    cur.execute(
        """SELECT source_row_number,raw_payload
           FROM raw_movement
           WHERE sheet_id=%s
             AND source_row_number<=80
           ORDER BY source_row_number""",
        (sheet_id,),
    )
    rows = cur.fetchall()
    seen = set()
    best = None
    best_score = -1
    for rr in rows:
        row_no = int(rr["source_row_number"])
        if row_no in seen:
            continue
        seen.add(row_no)
        p = _j(rr["raw_payload"])

        # SAP exports can contain two visually similar headers in the same row:
        # the real movement type column "MvT" appears before a later status-like
        # "Mvt" column. Both normalize to MVT. MySQL JSON member order is not an
        # authority, so sort by Excel column position and keep the FIRST semantic
        # occurrence. Otherwise the later "Mvt" column (values like B) can replace
        # the real movement type (101/109/251/252) and every detail row is skipped.
        norms: dict[str, str] = {}
        for col, value in sorted(p.items(), key=lambda kv: _col_rank(kv[0])):
            key = _norm_header(value)
            if key and key not in norms:
                norms[key] = col
        tokens = set(norms.keys())
        has_article = "ARTICLE" in tokens
        has_mvt = any(x in tokens for x in {"MVT", "MOVEMENT TYPE", "MOVEMENT"})
        has_posting = any(x in tokens for x in {"PSTNG DATE", "POSTING DATE", "POST DATE", "BUSINESS DATE"})
        if not (has_article and has_mvt and has_posting):
            continue
        score = 0
        for t in (
            "ARTICLE","ARTICLE DESCRIPTION","MVT","PSTNG DATE",
            "QUANTITY","QTY IN UNE","EUN","QUANTITY I","BUN",
            "AMOUNT LC","SALES VAL","PO","VENDOR","ART DOC",
        ):
            if t in tokens:
                score += 1
        if declared_header_row and row_no == int(declared_header_row):
            score += 1
        if score > best_score:
            best = norms
            best_score = score
    return best or {}


def _process_movement(cur, batch_id: int, f: dict[str, Any]) -> int:
    inserted = 0
    unmapped_articles: dict[str, dict[str, Any]] = {}
    cur.execute(
        'SELECT sheet_id,header_row_number FROM ingest_sheet WHERE file_id=%s ORDER BY sheet_index',
        (f['file_id'],),
    )
    for sh in cur.fetchall():
        hmap = _movement_header_map(cur, sh['sheet_id'], sh.get('header_row_number'))

        # SAP Dynamic List exports are not position-stable across report variants.
        # Resolve semantically dangerous movement fields from exact headers first,
        # then retain the legacy column positions only as a compatibility fallback.
        article_col = _pick_exact(hmap, ['Article', 'Article Number', 'Article No', 'Article #']) or 'C'
        desc_col = _pick_exact(hmap, ['Article Description', 'Description']) or 'D'
        mvt_col = _pick_exact(hmap, ['MvT', 'Movement Type', 'Movement']) or 'G'
        posting_col = _pick_exact(hmap, ['Pstng Date', 'Posting Date', 'Post Date', 'Business Date']) or 'H'
        entry_qty_col = _pick_exact(hmap, ['Qty in UnE', 'Quantity in UnE', 'Quantity', 'Entry Quantity']) or 'I'
        entry_uom_col = _pick_exact(hmap, ['EUn', 'Entry UOM', 'Entry Unit']) or 'J'
        base_qty_col = _pick_exact(
            hmap,
            ['Quantity i', 'Quantity in BUn', 'Quantity in Base Unit', 'Base Quantity'],
        ) or 'K'
        base_uom_col = _pick_exact(hmap, ['BUn', 'Base UOM', 'Base Unit']) or 'L'
        amount_col = _pick_exact(hmap, ['Amount LC', 'Amount in LC', 'Local Currency Amount']) or 'M'
        sales_value_col = _pick_exact(hmap, ['Sales Val.', 'Sales Value']) or 'N'
        vendor_col = _pick_exact(hmap, ['Vendor', 'Vendor Code']) or 'S'
        reference_col = _pick_exact(hmap, ['Reference']) or 'Q'
        article_doc_col = _pick_exact(hmap, ['Art. Doc.', 'Article Document', 'Material Document', 'Mat. Doc.'])
        po_col = _pick_exact(hmap, ['Purchase Order', 'PO', 'Purchase Order Number']) or 'R'
        cost_center_col = _pick_exact(hmap, ['Cost Center', 'Cost Ctr', 'CostCenter']) or 'V'

        cur.execute(
            "SELECT raw_id,source_row_number,raw_payload FROM raw_movement WHERE sheet_id=%s ORDER BY source_row_number",
            (sh['sheet_id'],),
        )
        for rr in cur.fetchall():
            p = _j(rr['raw_payload'])
            article_num = _id(p.get(article_col))
            mvt = _id(p.get(mvt_col))
            posting = _date(p.get(posting_col))
            desc = _text(p.get(desc_col))
            cost_center = _text(p.get(cost_center_col))
            if not article_num or not mvt or not posting:
                continue
            article_id, family_id = _find_article(cur, article_num)
            seafood_tag = bool(cost_center and 'SEAFOOD' in cost_center.upper())
            # Preserve every structurally valid movement row in normalized history,
            # even when product identity is not yet resolved. Late Article/Family
            # authority must be able to relink prior movement without replaying RAW.
            # Downstream Seafood analysis still filters through confirmed Family/
            # Article identity; preserving an unmapped row does not publish it.
            if seafood_tag and family_id is None:
                u = unmapped_articles.setdefault(
                    article_num,
                    {
                        'row_count': 0,
                        'movement_types': set(),
                        'descriptions': set(),
                        'posting_dates': set(),
                    },
                )
                u['row_count'] += 1
                u['movement_types'].add(str(mvt))
                if desc:
                    u['descriptions'].add(str(desc))
                u['posting_dates'].add(posting.isoformat())
            entry_qty = _num(p.get(entry_qty_col))
            entry_uom = (_text(p.get(entry_uom_col)) or '').upper() or None
            base_qty = _num(p.get(base_qty_col))
            base_uom = (_text(p.get(base_uom_col)) or '').upper() or None
            amount = _num(p.get(amount_col))
            sales_value = _num(p.get(sales_value_col))
            # Preserve the generic SAP document for non-receipt lineage.
            # For receipt movements, only a 5014... value is accepted as the
            # GR/material-document number. Search explicit Art./Material Doc,
            # Reference, then the remaining raw row cells because SAP exports
            # are not fully consistent about which document column is populated.
            art_doc = (
                _text(p.get(article_doc_col))
                if article_doc_col else None
            )
            reference_doc = _text(p.get(reference_col))
            if mvt in RECEIPT_MOVEMENTS:
                gr_doc = (
                    _gr_5014_id(art_doc)
                    or _gr_5014_id(reference_doc)
                    or next(
                        (_gr_5014_id(v) for v in p.values() if _gr_5014_id(v)),
                        None,
                    )
                )
                if gr_doc:
                    art_doc = gr_doc
                elif not art_doc:
                    art_doc = reference_doc
            elif not art_doc:
                art_doc = reference_doc
            po = _text(p.get(po_col))
            vendor = _text(p.get(vendor_col))
            cur.execute(
                """INSERT INTO movement_history
                   (batch_id,file_id,sheet_id,raw_id,source_row_number,article_number,article_id,family_id,description,
                    movement_type,posting_date,entry_quantity,entry_uom_code,base_quantity,base_uom_code,
                    amount_local_currency,sales_value,article_document,purchase_order,vendor_code,cost_center)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                       article_id=VALUES(article_id),
                       family_id=VALUES(family_id),
                       description=VALUES(description),
                       movement_type=VALUES(movement_type),
                       posting_date=VALUES(posting_date),
                       entry_quantity=VALUES(entry_quantity),
                       entry_uom_code=VALUES(entry_uom_code),
                       base_quantity=VALUES(base_quantity),
                       base_uom_code=VALUES(base_uom_code),
                       amount_local_currency=VALUES(amount_local_currency),
                       sales_value=VALUES(sales_value),
                       article_document=VALUES(article_document),
                       purchase_order=VALUES(purchase_order),
                       vendor_code=VALUES(vendor_code),
                       cost_center=VALUES(cost_center)""",
                (batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], rr['source_row_number'], article_num, article_id, family_id,
                 desc, mvt, posting, entry_qty, entry_uom, base_qty, base_uom, amount, sales_value, art_doc, po, vendor, cost_center),
            )
            inserted += 1
            if article_id is not None and mvt in RECEIPT_MOVEMENTS:
                entry_uom_id = _uom_id(cur, entry_uom)
                base_uom_id = _uom_id(cur, base_uom)
                cur.execute("SELECT receiving_observation_id FROM receiving_observation WHERE raw_table_name='raw_movement' AND raw_id=%s LIMIT 1", (rr['raw_id'],))
                if not cur.fetchone():
                    cur.execute(
                        """INSERT INTO receiving_observation
                           (article_id,family_id,movement_type,posting_date,article_document,purchase_order,vendor_code,
                            entry_quantity,entry_uom_id,base_quantity,base_uom_id,amount_local_currency,currency_code,
                            batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'USD',%s,%s,%s,'raw_movement',%s,%s)""",
                        (article_id, family_id, mvt, posting, art_doc, po, vendor, entry_qty, entry_uom_id, base_qty, base_uom_id,
                         amount, batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], rr['source_row_number']),
                    )
                # Default receipt valuation uses SAP Base quantity/UOM. A narrow
                # user-confirmed exception may instead use Entry quantity/UOM when
                # the business confirms that Entry UOM is the true receiving/cost
                # unit and the SAP Base-UOM label is not a physical conversion.
                receipt_basis = confirmed_receipt_entry_cost_basis(cur, family_id)
                basis_entry_uom = (
                    str(receipt_basis.get('entry_uom_code') or '').strip().upper()
                    if receipt_basis else None
                )
                use_entry_cost_basis = bool(
                    receipt_basis
                    and basis_entry_uom
                    and entry_uom
                    and basis_entry_uom == entry_uom
                    and entry_qty not in (None, 0)
                    and entry_uom_id is not None
                    and amount not in (None, 0)
                )

                valuation_qty = entry_qty if use_entry_cost_basis else base_qty
                valuation_uom_id = entry_uom_id if use_entry_cost_basis else base_uom_id
                if mvt in RECEIPT_COST_MOVEMENTS and amount not in (None, 0) and valuation_qty not in (None, 0) and valuation_uom_id is not None:
                    unit_cost = abs(amount / valuation_qty)
                    cur.execute(
                        "SELECT cost_observation_id FROM article_cost_observation "
                        "WHERE raw_table_name='raw_movement' AND raw_id=%s LIMIT 1",
                        (rr['raw_id'],),
                    )
                    existing_cost = cur.fetchone()
                    if existing_cost and use_entry_cost_basis:
                        # Repair only DERIVED cost semantics. RAW movement_history
                        # remains unchanged, including its supplied Base UOM.
                        cur.execute(
                            """UPDATE article_cost_observation
                               SET article_id=%s,family_id=%s,cost_amount=%s,
                                   currency_code='USD',cost_uom_id=%s,
                                   source_type='MOVEMENT_RECEIPT_VALUATION',
                                   movement_type=%s,business_date=%s,observed_at=%s,
                                   cost_status='OBSERVED',confidence=1.0,
                                   base_uom_id=%s,cost_per_base_uom=%s,
                                   batch_id=%s,file_id=%s,sheet_id=%s,source_row_number=%s
                               WHERE cost_observation_id=%s""",
                            (
                                article_id, family_id, unit_cost, valuation_uom_id,
                                mvt, posting, datetime.combine(posting, datetime.min.time()),
                                valuation_uom_id, unit_cost,
                                batch_id, f['file_id'], sh['sheet_id'], rr['source_row_number'],
                                existing_cost['cost_observation_id'],
                            ),
                        )
                    elif not existing_cost:
                        cur.execute(
                            """INSERT INTO article_cost_observation
                               (article_id,family_id,cost_amount,currency_code,cost_uom_id,source_type,movement_type,business_date,
                                observed_at,cost_status,confidence,base_uom_id,cost_per_base_uom,
                                batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
                               VALUES (%s,%s,%s,'USD',%s,'MOVEMENT_RECEIPT_VALUATION',%s,%s,%s,'OBSERVED',1.0,%s,%s,
                                       %s,%s,%s,'raw_movement',%s,%s)""",
                            (article_id, family_id, unit_cost, valuation_uom_id, mvt, posting, datetime.combine(posting, datetime.min.time()),
                             valuation_uom_id, unit_cost, batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], rr['source_row_number']),
                        )
            if family_id is not None and mvt in FAMILY_SALE_MOVEMENTS:
                # Family movement is a DERIVED operational measure. Preserve the
                # raw SAP Base quantity/UOM in movement_history, but when explicit
                # user authority says the family operates in another unit, use
                # the matching Entry quantity/UOM for the derived movement.
                operational = confirmed_operational_uom_basis(cur, family_id)
                movement_qty = base_qty
                movement_uom = base_uom
                if (
                    operational
                    and str(operational.get('movement_quantity_basis') or '').upper() == 'ENTRY'
                    and entry_qty is not None
                    and entry_uom
                    and str(entry_uom).upper() == str(operational.get('operational_uom_code') or '').upper()
                ):
                    movement_qty = entry_qty
                    movement_uom = str(operational['operational_uom_code']).upper()

                if movement_qty is not None:
                    net_sold = -movement_qty
                    cur.execute(
                        """INSERT INTO family_movement_observation
                           (batch_id,file_id,sheet_id,raw_id,family_id,article_id,movement_type,posting_date,
                            base_quantity_signed,net_sold_quantity,base_uom_code)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON DUPLICATE KEY UPDATE family_id=VALUES(family_id),article_id=VALUES(article_id),
                            base_quantity_signed=VALUES(base_quantity_signed),
                            net_sold_quantity=VALUES(net_sold_quantity),base_uom_code=VALUES(base_uom_code)""",
                        (
                            batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'],
                            family_id, article_id, mvt, posting,
                            movement_qty, net_sold, movement_uom,
                        ),
                    )
    # Unmapped Seafood movement is isolated to the unresolved Article because
    # family_id remains NULL and therefore cannot enter family movement or
    # mapped inventory roll-forward. Record one Article-level review issue
    # instead of one HIGH batch blocker per raw movement row.
    for article_num, u in sorted(unmapped_articles.items()):
        _issue(
            cur,
            batch_id,
            'SEAFOOD_MOVEMENT_ARTICLE_UNMAPPED',
            'ARTICLE',
            article_num,
            (
                f'Seafood movement exists for Article {article_num}, but it has no '
                'confirmed Family mapping. The movement is preserved in history '
                'and excluded from mapped-family calculations until resolved.'
            ),
            'MEDIUM',
            f['file_id'],
            detail={
                'scope': 'ARTICLE_LOCAL_FAIL_CLOSED',
                'row_count': u['row_count'],
                'movement_types': sorted(u['movement_types']),
                'descriptions': sorted(u['descriptions'])[:10],
                'posting_dates': sorted(u['posting_dates']),
            },
        )

    cur.execute(
        """SELECT COUNT(*) AS c
           FROM raw_movement
           WHERE file_id=%s
             AND observed_business_date IS NOT NULL""",
        (f['file_id'],),
    )
    dated_raw_rows = int((cur.fetchone() or {}).get('c') or 0)
    if dated_raw_rows > 0 and inserted == 0:
        _issue(
            cur,
            batch_id,
            'MOVEMENT_HISTORY_FILE_EMPTY',
            'FILE',
            str(f['file_id']),
            (
                f"Movement source file {f.get('original_filename') or f['file_id']} "
                "contains dated RAW rows but produced zero normalized movement rows."
            ),
            'CRITICAL',
            f['file_id'],
            detail={
                'dated_raw_rows': dated_raw_rows,
                'parser': 'HEADER_DRIVEN_WITH_LEGACY_POSITION_FALLBACK_V763',
            },
        )
    return inserted


def _sheet_header_map(cur, raw_table: str, sheet_id: int, header_row: int | None) -> dict[str, str]:
    if not header_row:
        return {}
    cur.execute(f'SELECT raw_payload FROM {raw_table} WHERE sheet_id=%s AND source_row_number=%s LIMIT 1', (sheet_id, header_row))
    r = cur.fetchone()
    if not r:
        return {}
    p = _j(r['raw_payload'])
    return {_norm_header(v): k for k, v in p.items() if _norm_header(v)}


def _pick_exact(hmap: dict[str, str], aliases: Iterable[str]) -> str | None:
    """Strict header match for semantically dangerous fields such as Cost UOM.

    Do not fall back to substring matching here. In particular, the generic
    token "Unit" must never match a numeric "Unit Cost" column.
    """
    for alias in aliases:
        key = _norm_header(alias)
        if key in hmap:
            return hmap[key]
    return None


def _pick(hmap: dict[str, str], aliases: Iterable[str]) -> str | None:
    norm_alias = [_norm_header(a) for a in aliases]
    for a in norm_alias:
        if a in hmap:
            return hmap[a]
    for h, c in hmap.items():
        if any(a and a in h for a in norm_alias):
            return c
    return None


def _company_cost_uom_policy(
    source_type: str,
    hmap: dict[str, str],
    payload: dict[str, Any],
    has_cost: bool,
) -> tuple[str | None, str, str | None]:
    """Resolve company-report cost UOM from explicit source semantics only.

    Frozen Inventory: Unit Cost is per BUN, and BUN is the item-specific unit
    shown in the BUN column (column I in the current report layout).

    Live/Fresh Suggestion: user-confirmed source-wide rule: Unit Cost is per LB.

    TX Seafood ABC Price: retired from current authority. Preserve source rows,
    but do not provide current cost UOM/authority.
    """
    st = str(source_type or '').strip().lower()
    if st == 'frozen_inventory':
        bun_col = _pick_exact(hmap, ['BUN'])
        bun = (_text(payload.get(bun_col)) or '').upper() or None if bun_col else None
        return bun, 'FROZEN_BUN_COLUMN', bun_col
    if st == 'live_fresh_suggestion':
        return ('LB' if has_cost else None), 'LIVE_FRESH_SOURCE_RULE_LB', None
    if st == 'tx_seafood_abc_price':
        return None, 'TX_SEAFOOD_ABC_RETIRED', None

    explicit_col = _pick_exact(
        hmap,
        [
            'Cost UOM',
            'Cost Unit',
            'Cost Unit of Measure',
            'Cost Base UOM',
            'UOM',
            'UM',
            'Unit of Measure',
        ],
    )
    explicit = (
        (_text(payload.get(explicit_col)) or '').upper() or None
        if explicit_col else None
    )
    return explicit, 'EXPLICIT_COST_UOM_COLUMN', explicit_col


def _family_main_article_id(cur, family_id: int | None) -> int | None:
    if family_id is None:
        return None
    cur.execute(
        """SELECT a.article_id
           FROM product_family pf
           JOIN article a ON a.article_number=pf.main_article_number
           WHERE pf.family_id=%s
           LIMIT 1""",
        (family_id,),
    )
    row = cur.fetchone()
    return int(row['article_id']) if row else None


def _process_on_hand(cur, batch_id: int, f: dict[str, Any]) -> int:
    # Any newer ON_HAND file ends the prior manual True Stock authority window.
    # This only updates the manual layer when that feature has already been initialized.
    expire_true_stock_for_new_oh(cur, int(f['file_id']))
    inserted = 0
    cur.execute('SELECT sheet_id,header_row_number FROM ingest_sheet WHERE file_id=%s ORDER BY sheet_index', (f['file_id'],))
    for sh in cur.fetchall():
        hmap = _sheet_header_map(cur, 'raw_on_hand', sh['sheet_id'], sh['header_row_number'])
        # User-confirmed OH layout authority:
        #   Column D = Family Article
        #   Column H = Base UOM
        # These two fields are positional and must not drift with header aliases.
        c_article = 'D'
        # FULL MYSQL identity rule: Sales Set # is not a UPC join key.
        # Only explicit UPC/EAN/Barcode headers may populate selling identity.
        c_upc = _pick_exact(hmap, ['UPC', 'EAN', 'Barcode'])
        c_merch = _pick_exact(hmap, ['Mdse Cat.', 'Mdse Cat', 'Merch. Cat.', 'Merch Cat', 'Merchandise Category'])
        # SAP stock/OH extracts use Unrestr. as the actual unrestricted stock.
        # Do NOT substring-match generic "Stock": that can select "Stock in Transit",
        # which is a different quantity and was the root cause of v7.0.50 zero-OH rows.
        c_oh = _pick_exact(
            hmap,
            ['Unrestr.', 'Unrestr', 'Unrestricted', 'Unrestricted Stock', 'On Hand', 'OH'],
        )
        # OH Column H is the authoritative Base UOM attached to the quantity.
        c_uom = 'H'
        c_date = _pick_exact(hmap, ['Date', 'Inventory Date', 'Count Date'])
        if not c_oh or (not c_article and not c_upc):
            continue
        cur.execute('SELECT raw_id,source_row_number,raw_payload FROM raw_on_hand WHERE sheet_id=%s AND source_row_number>%s ORDER BY source_row_number',
                    (sh['sheet_id'], sh['header_row_number'] or 0))
        for rr in cur.fetchall():
            p = _j(rr['raw_payload'])
            article_num = _id(p.get(c_article)) if c_article else None
            ean = _id(p.get(c_upc)) if c_upc else None
            merch_category = _id(p.get(c_merch)) if c_merch else None
            department_code = _department_from_merch_category(merch_category)
            qty = _num(p.get(c_oh))
            if qty is None or (not article_num and not ean):
                continue
            article_id, family_id = _find_article(cur, article_num)
            upc_id = _find_upc_id(cur, ean)
            # ON_HAND is a point-in-time file snapshot. File-level report/filename
            # date owns the entire snapshot; row-level Date is only a fallback and
            # may represent another SAP business date rather than snapshot time.
            obs_date = (
                f.get('coverage_end_date')
                or f.get('filename_date_candidate')
                or (f.get('report_generated_at').date() if f.get('report_generated_at') else None)
                or (_date(p.get(c_date)) if c_date else None)
                or (f.get('upload_timestamp').date() if f.get('upload_timestamp') else None)
            )
            uom = (_text(p.get(c_uom)) or '').upper() or None if c_uom else None

            if article_num and department_code:
                cur.execute(
                    """INSERT INTO article_department_observation
                       (article_id,article_number,department_code,department_name,source_type,
                        business_date,batch_id,file_id,sheet_id,source_row_number)
                       VALUES (%s,%s,%s,%s,'ON_HAND',%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE
                         article_id=VALUES(article_id),
                         department_name=VALUES(department_name),
                         business_date=VALUES(business_date),
                         batch_id=VALUES(batch_id)""",
                    (
                        article_id, article_num, department_code, DEPARTMENT_REGISTRY[department_code],
                        obs_date, batch_id, f['file_id'], sh['sheet_id'], rr['source_row_number'],
                    ),
                )

            cur.execute(
                """INSERT INTO inventory_observation
                   (batch_id,file_id,sheet_id,raw_id,source_row_number,observation_date,article_number,article_id,family_id,
                    ean_upc,upc_id,on_hand_quantity,uom_code,source_type)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ON_HAND')
                   ON DUPLICATE KEY UPDATE
                    article_number=VALUES(article_number),
                    article_id=VALUES(article_id),
                    family_id=VALUES(family_id),
                    ean_upc=VALUES(ean_upc),
                    upc_id=VALUES(upc_id),
                    on_hand_quantity=VALUES(on_hand_quantity),
                    uom_code=VALUES(uom_code),
                    observation_date=VALUES(observation_date)""",
                (batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], rr['source_row_number'], obs_date, article_num, article_id,
                 family_id, ean, upc_id, qty, uom),
            )
            inserted += 1
    return inserted


def _process_company(cur, batch_id: int, f: dict[str, Any], raw_table: str) -> int:
    inserted = 0
    cur.execute('SELECT sheet_id,header_row_number FROM ingest_sheet WHERE file_id=%s ORDER BY sheet_index', (f['file_id'],))
    for sh in cur.fetchall():
        hmap = _sheet_header_map(cur, raw_table, sh['sheet_id'], sh['header_row_number'])
        c_article = _pick(hmap, ['Article', 'Article Number', 'Order Article', 'Ordering Article'])
        c_main = _pick(hmap, ['Main Article', 'Family Article'])
        c_upc = _pick(hmap, ['UPC', 'EAN', 'Barcode'])
        c_a = _pick(hmap, ['Price A', 'Suggested Price A', 'A Price'])
        c_b = _pick(hmap, ['Price B', 'Suggested Price B', 'B Price'])
        c_c = _pick(hmap, ['Price C', 'Suggested Price C', 'C Price'])
        c_cost = _pick(hmap, ['Cost', 'Official Cost', 'Unit Cost'])
        if not any([c_a, c_b, c_c, c_cost]):
            continue
        cur.execute(f'SELECT raw_id,source_row_number,raw_payload FROM {raw_table} WHERE sheet_id=%s AND source_row_number>%s ORDER BY source_row_number',
                    (sh['sheet_id'], sh['header_row_number'] or 0))
        for rr in cur.fetchall():
            p = _j(rr['raw_payload'])
            article_num = _id(p.get(c_article)) if c_article else None
            main_article = _id(p.get(c_main)) if c_main else None
            ean = _id(p.get(c_upc)) if c_upc else None
            article_id, family_id = _find_article(cur, article_num)
            if family_id is None and main_article:
                cur.execute('SELECT family_id FROM product_family WHERE main_article_number=%s', (main_article,))
                r = cur.fetchone(); family_id = int(r['family_id']) if r else None
            upc_id = _find_upc_id(cur, ean)
            pa = _num(p.get(c_a)) if c_a else None
            pb = _num(p.get(c_b)) if c_b else None
            pc = _num(p.get(c_c)) if c_c else None
            cost = _num(p.get(c_cost)) if c_cost else None
            if all(v is None for v in (pa, pb, pc, cost)):
                continue
            obs_date = f.get('coverage_end_date') or f.get('filename_date_candidate') or (f.get('upload_timestamp').date() if f.get('upload_timestamp') else None)
            cost_uom, cost_uom_policy, _cost_uom_source_col = _company_cost_uom_policy(
                f['source_type'],
                hmap,
                p,
                cost is not None and cost > 0,
            )
            cur.execute(
                """INSERT INTO company_price_observation
                   (batch_id,file_id,sheet_id,raw_id,source_row_number,article_number,article_id,family_id,ean_upc,upc_id,
                    observation_date,source_type,price_a,price_b,price_c,official_cost,cost_uom_code)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE article_id=VALUES(article_id),family_id=VALUES(family_id),upc_id=VALUES(upc_id),
                    price_a=VALUES(price_a),price_b=VALUES(price_b),price_c=VALUES(price_c),official_cost=VALUES(official_cost),
                    cost_uom_code=VALUES(cost_uom_code),observation_date=VALUES(observation_date)""",
                (batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], rr['source_row_number'], article_num, article_id, family_id,
                 ean, upc_id, obs_date, f['source_type'], pa, pb, pc, cost, cost_uom),
            )
            inserted += 1
            if (
                cost is not None
                and cost > 0
                and family_id is not None
                and cost_uom
                and f['source_type'] in {'frozen_inventory', 'live_fresh_suggestion'}
            ):
                uid = _uom_id(cur, cost_uom)
                main_article_id = _family_main_article_id(cur, family_id)
                if uid and main_article_id is not None:
                    cur.execute("SELECT cost_observation_id FROM article_cost_observation WHERE raw_table_name=%s AND raw_id=%s LIMIT 1", (raw_table, rr['raw_id']))
                    existing = cur.fetchone()
                    if existing:
                        cur.execute(
                            """UPDATE article_cost_observation
                               SET article_id=%s,family_id=%s,cost_amount=%s,cost_uom_id=%s,
                                   source_type=%s,business_date=%s,cost_status='OBSERVED',confidence=1.0
                               WHERE cost_observation_id=%s""",
                            (
                                main_article_id,
                                family_id,
                                cost,
                                uid,
                                f['source_type'].upper() + '_OFFICIAL_COST',
                                obs_date,
                                existing['cost_observation_id'],
                            ),
                        )
                    else:
                        cur.execute(
                            """INSERT INTO article_cost_observation
                               (article_id,family_id,cost_amount,currency_code,cost_uom_id,source_type,business_date,
                                cost_status,confidence,batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
                               VALUES (%s,%s,%s,'USD',%s,%s,%s,'OBSERVED',1.0,%s,%s,%s,%s,%s,%s)""",
                            (
                                main_article_id,
                                family_id,
                                cost,
                                uid,
                                f['source_type'].upper() + '_OFFICIAL_COST',
                                obs_date,
                                batch_id,
                                f['file_id'],
                                sh['sheet_id'],
                                raw_table,
                                rr['raw_id'],
                                rr['source_row_number'],
                            ),
                        )
    return inserted



def repair_company_cost_uom_observations(cur) -> dict[str, Any]:
    """Re-derive company-report Cost UOM from authoritative source semantics.

    Source authority confirmed by the user:
    - Frozen Inventory: Unit Cost UOM is the item-specific BUN column.
    - Live/Fresh Suggestion: all Unit Cost values are per LB.
    - TX Seafood ABC Price: retired from current authority; preserve provenance
      but do not use its cost or suggested prices for current serving.

    RAW remains immutable. Only derived observations are repaired.
    """

    sources = {
        'frozen_inventory': 'raw_frozen_inventory',
        'tx_seafood_abc_price': 'raw_tx_seafood_abc_price',
        'live_fresh_suggestion': 'raw_live_fresh_suggestion',
    }
    result = {
        'files_scanned': 0,
        'sheets_scanned': 0,
        'rows_examined': 0,
        'rows_changed': 0,
        'rows_set_from_frozen_bun': 0,
        'rows_set_from_live_fresh_lb_rule': 0,
        'rows_set_null_tx_retired': 0,
        'rows_missing_frozen_bun': 0,
        'derived_cost_rows_superseded_no_supported_uom': 0,
        'derived_cost_rows_superseded_tx_retired': 0,
        'derived_cost_rows_reactivated_supported_uom': 0,
        'derived_cost_rows_reanchored_to_main_article': 0,
        'sheet_header_audit': [],
    }

    for source_type, raw_table in sources.items():
        cur.execute(
            """SELECT file_id,original_filename
               FROM ingest_file
               WHERE source_type=%s
               ORDER BY file_id""",
            (source_type,),
        )
        files = cur.fetchall()
        result['files_scanned'] += len(files)

        for f in files:
            cur.execute(
                """SELECT sheet_id,sheet_name,header_row_number
                   FROM ingest_sheet
                   WHERE file_id=%s
                   ORDER BY sheet_index""",
                (f['file_id'],),
            )
            for sh in cur.fetchall():
                header_row = sh.get('header_row_number')
                if not header_row:
                    continue

                hmap = _sheet_header_map(cur, raw_table, sh['sheet_id'], header_row)
                bun_col = _pick_exact(hmap, ['BUN']) if source_type == 'frozen_inventory' else None
                policy = (
                    'FROZEN_BUN_COLUMN'
                    if source_type == 'frozen_inventory'
                    else 'LIVE_FRESH_SOURCE_RULE_LB'
                    if source_type == 'live_fresh_suggestion'
                    else 'TX_SEAFOOD_ABC_RETIRED'
                )
                result['sheets_scanned'] += 1
                result['sheet_header_audit'].append(
                    {
                        'file_id': int(f['file_id']),
                        'filename': f.get('original_filename'),
                        'sheet_id': int(sh['sheet_id']),
                        'sheet_name': sh.get('sheet_name'),
                        'cost_uom_policy': policy,
                        'bun_column': bun_col,
                        'normalized_headers': sorted(hmap.keys()),
                    }
                )

                cur.execute(
                    f"""SELECT c.company_price_observation_id,c.raw_id,c.cost_uom_code,
                               c.official_cost,r.raw_payload
                        FROM company_price_observation c
                        JOIN {raw_table} r ON r.raw_id=c.raw_id
                        WHERE c.file_id=%s AND c.sheet_id=%s
                        ORDER BY c.company_price_observation_id""",
                    (f['file_id'], sh['sheet_id']),
                )

                for row in cur.fetchall():
                    result['rows_examined'] += 1
                    payload = _j(row['raw_payload'])
                    parsed = None

                    if source_type == 'frozen_inventory':
                        if bun_col:
                            parsed = (_text(payload.get(bun_col)) or '').upper() or None
                        if row.get('official_cost') is not None and row.get('official_cost') > 0:
                            if parsed:
                                result['rows_set_from_frozen_bun'] += 1
                            else:
                                result['rows_missing_frozen_bun'] += 1
                    elif source_type == 'live_fresh_suggestion':
                        if row.get('official_cost') is not None and row.get('official_cost') > 0:
                            parsed = 'LB'
                            result['rows_set_from_live_fresh_lb_rule'] += 1
                    elif source_type == 'tx_seafood_abc_price':
                        parsed = None
                        if row.get('cost_uom_code') is not None:
                            result['rows_set_null_tx_retired'] += 1

                    current = (_text(row.get('cost_uom_code')) or '').upper() or None
                    if current != parsed:
                        cur.execute(
                            """UPDATE company_price_observation
                               SET cost_uom_code=%s
                               WHERE company_price_observation_id=%s""",
                            (parsed, row['company_price_observation_id']),
                        )
                        result['rows_changed'] += 1

    # TX Seafood ABC is retired from CURRENT authority regardless of historical
    # UOM state. Preserve all RAW/company observations, but supersede derived cost.
    cur.execute(
        """UPDATE article_cost_observation aco
           JOIN company_price_observation c
             ON c.raw_id=aco.raw_id
            AND aco.raw_table_name='raw_tx_seafood_abc_price'
           SET aco.cost_status='SUPERSEDED'
           WHERE c.source_type='tx_seafood_abc_price'
             AND aco.source_type='TX_SEAFOOD_ABC_PRICE_OFFICIAL_COST'
             AND aco.cost_status NOT IN ('REJECTED','SUPERSEDED')"""
    )
    result['derived_cost_rows_superseded_tx_retired'] = int(cur.rowcount or 0)

    # Frozen/Live-Fresh rows with missing or unsupported resolved UOM cannot
    # remain active official costs.
    cur.execute(
        """UPDATE article_cost_observation aco
           JOIN company_price_observation c
             ON c.raw_id=aco.raw_id
            AND aco.raw_table_name=
                CASE c.source_type
                  WHEN 'frozen_inventory' THEN 'raw_frozen_inventory'
                  WHEN 'live_fresh_suggestion' THEN 'raw_live_fresh_suggestion'
                  ELSE '__NO_MATCH__'
                END
           LEFT JOIN dim_uom du
             ON UPPER(du.uom_code)=UPPER(TRIM(c.cost_uom_code))
           SET aco.cost_status='SUPERSEDED'
           WHERE c.source_type IN ('frozen_inventory','live_fresh_suggestion')
             AND aco.source_type IN (
                 'FROZEN_INVENTORY_OFFICIAL_COST',
                 'LIVE_FRESH_SUGGESTION_OFFICIAL_COST'
             )
             AND aco.cost_status NOT IN ('REJECTED','SUPERSEDED')
             AND (c.cost_uom_code IS NULL OR du.uom_id IS NULL)"""
    )
    result['derived_cost_rows_superseded_no_supported_uom'] = int(cur.rowcount or 0)

    # A company-report cost is Family/Main-Article authority. Re-anchor and
    # synchronize supported Frozen/Live-Fresh derived rows accordingly.
    cur.execute(
        """UPDATE article_cost_observation aco
           JOIN company_price_observation c
             ON c.raw_id=aco.raw_id
            AND aco.raw_table_name=
                CASE c.source_type
                  WHEN 'frozen_inventory' THEN 'raw_frozen_inventory'
                  WHEN 'live_fresh_suggestion' THEN 'raw_live_fresh_suggestion'
                  ELSE '__NO_MATCH__'
                END
           JOIN product_family pf ON pf.family_id=c.family_id
           JOIN article ma ON ma.article_number=pf.main_article_number
           JOIN dim_uom du
             ON UPPER(du.uom_code)=UPPER(TRIM(c.cost_uom_code))
           SET aco.article_id=ma.article_id,
               aco.family_id=c.family_id,
               aco.cost_uom_id=du.uom_id,
               aco.cost_amount=c.official_cost,
               aco.source_type=CONCAT(UPPER(c.source_type),'_OFFICIAL_COST'),
               aco.cost_status='OBSERVED',
               aco.confidence=1.0
           WHERE c.source_type IN ('frozen_inventory','live_fresh_suggestion')
             AND c.official_cost IS NOT NULL
             AND c.official_cost>0
             AND (
                 NOT (aco.article_id <=> ma.article_id)
                 OR NOT (aco.family_id <=> c.family_id)
                 OR NOT (aco.cost_uom_id <=> du.uom_id)
                 OR NOT (aco.cost_amount <=> c.official_cost)
                 OR aco.cost_status<>'OBSERVED'
             )"""
    )
    result['derived_cost_rows_reactivated_supported_uom'] = int(cur.rowcount or 0)

    cur.execute(
        """SELECT COUNT(*) AS c
           FROM article_cost_observation aco
           JOIN company_price_observation cp
             ON cp.raw_id=aco.raw_id
            AND aco.raw_table_name=
                CASE cp.source_type
                  WHEN 'frozen_inventory' THEN 'raw_frozen_inventory'
                  WHEN 'live_fresh_suggestion' THEN 'raw_live_fresh_suggestion'
                  ELSE '__NO_MATCH__'
                END
           JOIN product_family pf ON pf.family_id=aco.family_id
           JOIN article ma ON ma.article_number=pf.main_article_number
           WHERE cp.source_type IN ('frozen_inventory','live_fresh_suggestion')
             AND aco.cost_status='OBSERVED'
             AND aco.article_id=ma.article_id"""
    )
    result['derived_cost_rows_reanchored_to_main_article'] = int(
        (cur.fetchone() or {}).get('c') or 0
    )

    return result


PRODUCT_IDENTITY_GUARD_ISSUE_CODES = (
    'DUPLICATE_CANONICAL_ACTIVE_UPC',
    'UPC_MULTI_AUTHORITATIVE_IDENTITY',
    'RETIRED_UPC_RESURRECTED',
    'UPC_CURRENT_UOM_CONFLICT',
    'ACTIVE_UPC_WITHOUT_AUTHORITATIVE_IDENTITY',
    'SERVING_IDENTITY_NOT_AUTHORITATIVE',
    'MANUAL_UPC_OVERRIDE_NOT_ENFORCED',
    'DUPLICATE_UPCA_SHORT_LONG_CURRENT',
    'UPCA_SHORT_LONG_CURRENT_IDENTITY_CONFLICT',
    'PRODUCT_IDENTITY_GUARD_BLOCKER',
)

RECOMPUTED_PHASE3_ISSUE_CODES = (
    'SALES_PERIOD_UNRESOLVED',
    'SOLD_UPC_UNMAPPED',
    'SOLD_UPC_UNMAPPED_EVIDENCE',
    'CURRENT_ACTIVE_SOLD_UPC_UNMAPPED',
    'HISTORICAL_SOLD_UPC_UNMAPPED',
    'SEAFOOD_MOVEMENT_ARTICLE_UNMAPPED',
    'MOVEMENT_HISTORY_FILE_EMPTY',
    'QUICK_CHECK_CORE_FIELD_MISSING',
    *PRODUCT_IDENTITY_GUARD_ISSUE_CODES,
)

def retire_recomputed_phase3_issues(cur, batch_id: int) -> int:
    placeholders = ','.join(['%s'] * len(RECOMPUTED_PHASE3_ISSUE_CODES))
    cur.execute(
        f"""UPDATE qa_phase3_issue
            SET issue_status='RESOLVED',
                detail_json=JSON_SET(
                    COALESCE(detail_json,JSON_OBJECT()),
                    '$.resolution',
                    'Superseded by Phase 3 re-evaluation'
                )
            WHERE batch_id=%s
              AND issue_status='OPEN'
              AND issue_code IN ({placeholders})""",
        (batch_id, *RECOMPUTED_PHASE3_ISSUE_CODES),
    )
    return int(cur.rowcount)

def _record_product_identity_guard_issues(
    cur,
    batch_id: int,
    identity_audit: dict[str, Any],
) -> int:
    """Persist only GLOBAL identity blockers from the read-only audit."""
    evaluated = 0
    for blocker in identity_audit.get('blockers', []):
        code = str(blocker.get('code') or 'PRODUCT_IDENTITY_GUARD_BLOCKER')
        issue_code = (
            code if code in PRODUCT_IDENTITY_GUARD_ISSUE_CODES
            else 'PRODUCT_IDENTITY_GUARD_BLOCKER'
        )

        if blocker.get('ean_upc') is not None:
            entity_type = 'UPC'
            entity_key = str(blocker.get('ean_upc'))
        elif blocker.get('short_upc') is not None or blocker.get('valid_upca') is not None:
            entity_type = 'UPC_PAIR'
            entity_key = f"{blocker.get('short_upc') or ''}|{blocker.get('valid_upca') or ''}"
        elif blocker.get('canonical_key') is not None:
            entity_type = 'UPC_CANONICAL'
            entity_key = str(blocker.get('canonical_key'))
        else:
            entity_type = 'PRODUCT_IDENTITY'
            entity_key = code

        _issue(
            cur,
            batch_id,
            issue_code,
            entity_type,
            entity_key,
            f'Phase 3 product-identity publish guard blocked: {code}',
            'CRITICAL',
            detail={
                'guard': 'PRODUCT_IDENTITY_FAIL_CLOSED_V730',
                'original_blocker_code': code,
                'blocker': blocker,
            },
        )
        evaluated += 1
    return evaluated

def relink_history(cur) -> None:
    # Late-arriving identity evidence must repair prior history links without rewriting RAW.
    # Raw EAN/UPC is the sales lineage key. Repair both NULL and stale/wrong
    # derived upc_id links so service/fried UPCs cannot remain attached to an
    # older canonical row after product identity changes.
    cur.execute("""UPDATE sales_period_observation s JOIN selling_upc u ON u.ean_upc=s.ean_upc
                   SET s.upc_id=u.upc_id
                   WHERE s.upc_id IS NULL OR s.upc_id<>u.upc_id""")
    cur.execute("""UPDATE price_list_observation p JOIN selling_upc u ON u.ean_upc=p.ean_upc
                   SET p.upc_id=u.upc_id
                   WHERE p.upc_id IS NULL OR p.upc_id<>u.upc_id""")
    cur.execute("""UPDATE movement_history m JOIN article a ON a.article_number=m.article_number
                   LEFT JOIN bridge_article_family baf ON baf.article_id=a.article_id AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
                     AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   SET m.article_id=a.article_id, m.family_id=COALESCE(m.family_id,baf.family_id)
                   WHERE m.article_id IS NULL OR m.family_id IS NULL""")

    # Late SAP selling Articles such as 1549569 can be authoritative 251/252
    # evidence even when their SUB Article->Family bridge was absent at ingest.
    # Relink only deterministic 1540/1545/1549 Article forms whose exact
    # canonical 240/245/249 UPC resolves to one unique confirmed Family.
    cur.execute(
        """SELECT DISTINCT article_number
           FROM movement_history
           WHERE family_id IS NULL
             AND article_number REGEXP '^154[059][0-9]{3}$'
           ORDER BY article_number"""
    )
    for structural_row in cur.fetchall():
        article_number = str(structural_row.get('article_number') or '').strip()
        article_id, family_id = _find_article(cur, article_number)
        if family_id is None:
            continue
        cur.execute(
            """UPDATE movement_history
               SET article_id=COALESCE(article_id,%s),
                   family_id=%s
               WHERE article_number=%s
                 AND family_id IS NULL""",
            (article_id, family_id, article_number),
        )

    # Rebuild missing derived 251/252 family-movement mirrors after late
    # relinking. Respect the same explicit operational-UOM override used during
    # normal movement ingest; otherwise preserve SAP Base quantity/UOM.
    cur.execute(
        """SELECT m.batch_id,m.file_id,m.sheet_id,m.raw_id,m.article_id,m.family_id,
                  m.movement_type,m.posting_date,m.entry_quantity,m.entry_uom_code,
                  m.base_quantity,m.base_uom_code
           FROM movement_history m
           WHERE m.family_id IS NOT NULL
             AND m.movement_type IN ('251','252')
             AND m.base_quantity IS NOT NULL
             AND NOT EXISTS (
                 SELECT 1
                 FROM family_movement_observation fmo
                 WHERE fmo.raw_id=m.raw_id
             )
           ORDER BY m.raw_id"""
    )
    for movement_row in cur.fetchall():
        family_id = int(movement_row['family_id'])
        movement_qty = movement_row.get('base_quantity')
        movement_uom = movement_row.get('base_uom_code')
        operational = confirmed_operational_uom_basis(cur, family_id)
        if (
            operational
            and str(operational.get('movement_quantity_basis') or '').upper() == 'ENTRY'
            and movement_row.get('entry_quantity') is not None
            and movement_row.get('entry_uom_code')
            and str(movement_row.get('entry_uom_code')).upper()
                == str(operational.get('operational_uom_code') or '').upper()
        ):
            movement_qty = movement_row.get('entry_quantity')
            movement_uom = str(operational['operational_uom_code']).upper()
        if movement_qty is None:
            continue
        net_sold = -Decimal(str(movement_qty))
        cur.execute(
            """INSERT INTO family_movement_observation
               (batch_id,file_id,sheet_id,raw_id,family_id,article_id,movement_type,posting_date,
                base_quantity_signed,net_sold_quantity,base_uom_code)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                 family_id=VALUES(family_id),
                 article_id=VALUES(article_id),
                 base_quantity_signed=VALUES(base_quantity_signed),
                 net_sold_quantity=VALUES(net_sold_quantity),
                 base_uom_code=VALUES(base_uom_code)""",
            (
                movement_row.get('batch_id'),
                movement_row.get('file_id'),
                movement_row.get('sheet_id'),
                movement_row.get('raw_id'),
                family_id,
                movement_row.get('article_id'),
                movement_row.get('movement_type'),
                movement_row.get('posting_date'),
                movement_qty,
                net_sold,
                movement_uom,
            ),
        )
    # Article-based OH rows can be ingested before late product-family repair.
    # Relink them from their exact article number without changing RAW source values.
    cur.execute(
        """UPDATE inventory_observation i
           JOIN article a ON a.article_number=i.article_number
           LEFT JOIN bridge_article_family baf
             ON baf.article_id=a.article_id
            AND baf.mapping_status='CONFIRMED'
            AND baf.is_primary=TRUE
            AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           SET i.article_id=a.article_id,
               i.family_id=COALESCE(i.family_id,baf.family_id)
           WHERE i.article_number IS NOT NULL
             AND (i.article_id IS NULL OR i.family_id IS NULL)"""
    )
    cur.execute("""UPDATE inventory_observation i JOIN selling_upc u ON u.ean_upc=i.ean_upc
                   SET i.upc_id=u.upc_id
                   WHERE i.ean_upc IS NOT NULL
                     AND (i.upc_id IS NULL OR i.upc_id<>u.upc_id)""")
    cur.execute("""UPDATE company_price_observation c JOIN selling_upc u ON u.ean_upc=c.ean_upc
                   SET c.upc_id=u.upc_id
                   WHERE c.ean_upc IS NOT NULL
                     AND (c.upc_id IS NULL OR c.upc_id<>u.upc_id)""")
    cur.execute("""UPDATE upc_department_observation d JOIN selling_upc u ON u.ean_upc=d.ean_upc
                   SET d.upc_id=u.upc_id
                   WHERE d.ean_upc IS NOT NULL
                     AND (d.upc_id IS NULL OR d.upc_id<>u.upc_id)""")

    # Second pass: rebuild Seafood POS identity with the same hybrid resolver.
    # RAW barcode / 249 product code is authoritative first; Article Manual
    # verifies or fills unresolved identity. Description remains last-resort.
    article_manual_index = article_manual_pos_alias_index(cur)
    cur.execute(
        """SELECT DISTINCT ean_upc,description
           FROM sales_period_observation
           WHERE ean_upc IS NOT NULL"""
    )
    for row in cur.fetchall():
        ean=row['ean_upc']
        description=row.get('description')
        upc_id=_find_pos_upc_id(cur,ean,description,article_manual_index)
        if upc_id is not None:
            cur.execute(
                """UPDATE sales_period_observation
                   SET upc_id=%s
                   WHERE ean_upc=%s
                     AND COALESCE(description,'')=COALESCE(%s,'')
                     AND (upc_id IS NULL OR upc_id<>%s)""",
                (upc_id,ean,description,upc_id),
            )

    for table in ('price_list_observation','inventory_observation','company_price_observation'):
        cur.execute(f"SELECT DISTINCT ean_upc FROM {table} WHERE ean_upc IS NOT NULL")
        for row in cur.fetchall():
            ean = row['ean_upc']
            upc_id = _find_upc_id(cur, ean)
            if upc_id is not None:
                cur.execute(
                    f"""UPDATE {table}
                        SET upc_id=%s
                        WHERE ean_upc=%s
                          AND (upc_id IS NULL OR upc_id<>%s)""",
                    (upc_id, ean, upc_id),
                )

    # Department POS lineage must use the same RAW-first hybrid identity as
    # sales history. Restrict the special resolver to Seafood POS rows; other
    # department observations keep ordinary barcode lineage.
    cur.execute(
        """SELECT DISTINCT ean_upc,department_code,source_type
           FROM upc_department_observation
           WHERE ean_upc IS NOT NULL"""
    )
    for row in cur.fetchall():
        ean = row['ean_upc']
        if (
            str(row.get('department_code') or '') == SEAFOOD_DEPT_CODE
            and str(row.get('source_type') or '').upper() == 'POS'
        ):
            upc_id = _find_pos_upc_id(
                cur,
                ean,
                None,
                article_manual_index,
            )
        else:
            upc_id = _find_upc_id(cur, ean)
        if upc_id is not None:
            cur.execute(
                """UPDATE upc_department_observation
                   SET upc_id=%s
                   WHERE ean_upc=%s
                     AND department_code=%s
                     AND source_type=%s
                     AND (upc_id IS NULL OR upc_id<>%s)""",
                (
                    upc_id,
                    ean,
                    row.get('department_code'),
                    row.get('source_type'),
                    upc_id,
                ),
            )


def resolve_late_identity_issues(cur, batch_id: int) -> dict[str, int]:
    """Close only linkage QA that late Article Manual/PI identity evidence has actually repaired."""
    resolved_sales = 0
    resolved_movement = 0
    article_manual_index = article_manual_pos_alias_index(cur)
    cur.execute(
        """SELECT issue_id,issue_code,entity_key FROM qa_phase3_issue
           WHERE batch_id=%s AND issue_status='OPEN'
             AND issue_code IN (
                 'SOLD_UPC_UNMAPPED',
                 'SOLD_UPC_UNMAPPED_EVIDENCE',
                 'CURRENT_ACTIVE_SOLD_UPC_UNMAPPED',
                 'HISTORICAL_SOLD_UPC_UNMAPPED',
                 'SEAFOOD_MOVEMENT_ARTICLE_UNMAPPED'
             )""",
        (batch_id,),
    )
    for issue in cur.fetchall():
        code = issue['issue_code']
        key = str(issue['entity_key'])
        repaired = False
        if code in {
            'SOLD_UPC_UNMAPPED',
            'SOLD_UPC_UNMAPPED_EVIDENCE',
            'CURRENT_ACTIVE_SOLD_UPC_UNMAPPED',
            'HISTORICAL_SOLD_UPC_UNMAPPED',
        }:
            repaired = _upc_identity_ready(cur, key)
            if not repaired:
                manual_id = resolve_article_manual_pos_upc_id(
                    article_manual_index,
                    key,
                    seafood_context=True,
                )
                repaired = _upc_id_identity_ready(cur, manual_id)
        elif code == 'SEAFOOD_MOVEMENT_ARTICLE_UNMAPPED':
            _, family_id = _find_article(cur, key)
            repaired = family_id is not None
        if repaired:
            cur.execute(
                """UPDATE qa_phase3_issue
                   SET issue_status='RESOLVED',detail_json=JSON_SET(COALESCE(detail_json,JSON_OBJECT()),
                     '$.resolution','Resolved automatically after late identity evidence became authoritative')
                   WHERE issue_id=%s""",
                (issue['issue_id'],),
            )
            if code in {
                'SOLD_UPC_UNMAPPED',
                'SOLD_UPC_UNMAPPED_EVIDENCE',
                'CURRENT_ACTIVE_SOLD_UPC_UNMAPPED',
                'HISTORICAL_SOLD_UPC_UNMAPPED',
            }:
                resolved_sales += 1
            else:
                resolved_movement += 1
    return {'sold_upc_unmapped_resolved': resolved_sales, 'movement_article_unmapped_resolved': resolved_movement}



def _latest_price_snapshot(cur) -> datetime | None:
    cur.execute(
        """SELECT MAX(snapshot_at) AS ts
           FROM price_list_observation
           WHERE configured_price>0"""
    )
    row = cur.fetchone()
    return row['ts'] if row else None


def _upc_match_sql(column: str, ean: str) -> tuple[str, tuple[Any, ...]]:
    """Return the shared all-UPC raw-source lineage predicate."""
    return source_ean_predicate(column, ean)


def _sales_daily_aggregates(
    cur,
    data_days: list[dict[str, Any]],
    *,
    upc_id: int | None = None,
    ean: str | None = None,
) -> dict[date, dict[str, Decimal]]:
    """Return canonical daily POS totals from direct + derived daily sources."""
    if not data_days or (upc_id is None and not ean):
        return {}

    out: dict[date, dict[str, Decimal]] = {}

    direct_days = [
        d for d in data_days
        if d.get('coverage_kind') != 'DERIVED_PERIOD_RESIDUAL'
    ]
    if direct_days:
        clauses: list[str] = []
        args: list[Any] = []
        for d in direct_days:
            clauses.append(
                '(file_id=%s AND period_start_date=%s AND period_end_date=%s)'
            )
            args.extend([int(d['file_id']), d['date'], d['date']])
        if upc_id is not None and ean:
            ean_pred, ean_args = _upc_match_sql('ean_upc', str(ean))
            pred = f'(upc_id=%s OR {ean_pred})'
            pred_args: tuple[Any, ...] = (int(upc_id), *ean_args)
        elif upc_id is not None:
            pred = 'upc_id=%s'
            pred_args = (int(upc_id),)
        else:
            pred, pred_args = _upc_match_sql('ean_upc', str(ean))
        cur.execute(
            f"""SELECT period_end_date AS business_date,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM sales_period_observation
                WHERE temporal_grain='SINGLE_DATE'
                  AND ({' OR '.join(clauses)})
                  AND {pred}
                GROUP BY period_end_date""",
            tuple(args) + tuple(pred_args),
        )
        for r in cur.fetchall():
            d = r['business_date']
            out[d] = {
                'sales': Decimal(str(r.get('sales_amount') or 0)),
                'qty': Decimal(str(r.get('sold_quantity') or 0)),
            }

    derived_days = [
        d for d in data_days
        if d.get('coverage_kind') == 'DERIVED_PERIOD_RESIDUAL'
    ]
    if derived_days:
        clauses = []
        args = []
        for d in derived_days:
            clauses.append('(source_file_id=%s AND business_date=%s)')
            args.extend([int(d['file_id']), d['date']])
        if upc_id is not None and ean:
            ean_pred, ean_args = _upc_match_sql('ean_upc', str(ean))
            pred = f'(upc_id=%s OR {ean_pred})'
            pred_args = (int(upc_id), *ean_args)
        elif upc_id is not None:
            pred = 'upc_id=%s'
            pred_args = (int(upc_id),)
        else:
            pred, pred_args = _upc_match_sql('ean_upc', str(ean))
        cur.execute(
            f"""SELECT business_date,
                       COALESCE(SUM(sales_amount),0) AS sales_amount,
                       COALESCE(SUM(sold_quantity),0) AS sold_quantity
                FROM pos_daily_backfill_observation
                WHERE ({' OR '.join(clauses)})
                  AND {pred}
                GROUP BY business_date""",
            tuple(args) + tuple(pred_args),
        )
        for r in cur.fetchall():
            d = r['business_date']
            prev = out.get(d, {'sales': Decimal('0'), 'qty': Decimal('0')})
            out[d] = {
                'sales': prev['sales'] + Decimal(str(r.get('sales_amount') or 0)),
                'qty': prev['qty'] + Decimal(str(r.get('sold_quantity') or 0)),
            }

    return out


def _active_selling_evidence_for_unmapped(
    cur,
    ean: str,
    batch_id: int,
    pos_days: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Current activity scope for an unmapped historical UPC.

    v7.0.10 rule:
      - Positive sales on the latest up-to-28 VALID POS data days => ACTIVE_SELLING.
      - Everything else => HISTORICAL_ONLY for CURRENT production readiness.

    A configured Price List price by itself is NOT active-selling evidence.
    Historical sales and lineage are preserved.
    """
    completed_through = completed_through_date()
    if pos_days is None:
        pos_days = source_data_days(
            cur, 'sales_by_price_type', limit=28,
            include_batch_id=batch_id, up_to=completed_through
        )
    daily = _sales_daily_aggregates(cur, pos_days, ean=ean)
    recent_qty = sum(
        (x['qty'] for x in daily.values()),
        Decimal('0'),
    )
    recent_latest = max(daily) if daily else None

    if recent_qty > 0:
        scope = 'ACTIVE_SELLING'
        basis = 'POS_LATEST_28_VALID_DATA_DAYS'
    else:
        scope = 'HISTORICAL_ONLY'
        basis = 'NO_POS_SALES_LATEST_28_VALID_DATA_DAYS'

    return {
        'activity_scope': scope,
        'activity_basis': basis,
        'recent_pos_qty_28_valid_days': str(recent_qty),
        'recent_pos_valid_day_count': len(pos_days),
        'recent_pos_latest_valid_date': recent_latest,
    }


def classify_unmapped_sales_activity_scope(cur, batch_id: int) -> dict[str, int]:
    """Reclassify historical sold-but-unmapped UPCs for CURRENT readiness only.

    Historical evidence is never deleted. A UPC with no positive sales in the
    latest up-to-28 VALID POS data days becomes non-blocking MEDIUM historical QA.
    Only ACTIVE_SELLING UPCs remain HIGH and blocking until identity is resolved.
    """
    cur.execute(
        """SELECT issue_id,entity_key,detail_json
           FROM qa_phase3_issue
           WHERE batch_id=%s
             AND issue_status='OPEN'
             AND issue_code='SOLD_UPC_UNMAPPED'
           ORDER BY issue_id""",
        (batch_id,),
    )
    issues = cur.fetchall()
    counts = {
        'examined': 0,
        'active_blocking': 0,
        'active_evidence_nonblocking': 0,
        'historical_nonblocking': 0,
    }

    for issue in issues:
        ean = str(issue['entity_key'])
        evidence = _active_selling_evidence_for_unmapped(cur, ean, batch_id)
        counts['examined'] += 1

        try:
            detail = json.loads(issue.get('detail_json') or '{}')
        except Exception:
            detail = {}
        detail.update(evidence)

        if evidence['activity_scope'] == 'HISTORICAL_ONLY':
            cur.execute(
                """UPDATE qa_phase3_issue
                   SET issue_code='HISTORICAL_SOLD_UPC_UNMAPPED',
                       severity='MEDIUM',
                       issue_summary=%s,
                       detail_json=%s
                   WHERE issue_id=%s""",
                (
                    f"Historical POS sold quantity exists for UPC {ean}, but no confirmed identity mapping exists. "
                    "No current active-selling evidence was found; retained as non-blocking historical QA.",
                    json.dumps(detail, ensure_ascii=False, default=str),
                    issue['issue_id'],
                ),
            )
            counts['historical_nonblocking'] += 1
        else:
            detail['gate_role'] = 'RAW_EVIDENCE_ONLY_CURRENT_GLOBAL_GUARD_RECOMPUTES'
            cur.execute(
                """UPDATE qa_phase3_issue
                   SET issue_code='SOLD_UPC_UNMAPPED_EVIDENCE',
                       severity='MEDIUM',
                       issue_summary=%s,
                       detail_json=%s
                   WHERE issue_id=%s""",
                (
                    f"Raw POS evidence shows currently active sold UPC {ean} without confirmed identity. "
                    "Current readiness is evaluated by the global active-selling unmapped UPC guard.",
                    json.dumps(detail, ensure_ascii=False, default=str),
                    issue['issue_id'],
                ),
            )
            counts['active_evidence_nonblocking'] += 1

    return counts


def _recent_pos_canonical_ids_for_raw_ean(
    cur,
    raw_ean: str,
    pos_days: list[dict[str, Any]],
) -> set[int]:
    """Return canonical UPC ids actually carried by one raw POS EAN on selected days.

    This intentionally uses the normalized POS row's current upc_id after
    relink_history()/relink_pos_backfill().  It is the bridge between immutable
    raw EAN evidence and the current canonical selling UPC.  Exact raw EAN is
    required here; no second alias expansion is performed.
    """
    ids: set[int] = set()
    direct_days=[
        d for d in pos_days
        if d.get('coverage_kind')!='DERIVED_PERIOD_RESIDUAL'
    ]
    if direct_days:
        clauses=[]
        args: list[Any]=[]
        for d in direct_days:
            clauses.append('(file_id=%s AND period_start_date=%s AND period_end_date=%s)')
            args.extend([int(d['file_id']),d['date'],d['date']])
        cur.execute(
            f"""SELECT DISTINCT upc_id
                FROM sales_period_observation
                WHERE temporal_grain='SINGLE_DATE'
                  AND ({' OR '.join(clauses)})
                  AND ean_upc=%s
                  AND upc_id IS NOT NULL
                  AND sold_quantity<>0""",
            tuple(args)+(str(raw_ean),),
        )
        ids.update(int(r['upc_id']) for r in cur.fetchall() if r.get('upc_id') is not None)

    derived_days=[
        d for d in pos_days
        if d.get('coverage_kind')=='DERIVED_PERIOD_RESIDUAL'
    ]
    if derived_days:
        clauses=[]
        args=[]
        for d in derived_days:
            clauses.append('(source_file_id=%s AND business_date=%s)')
            args.extend([int(d['file_id']),d['date']])
        cur.execute(
            f"""SELECT DISTINCT upc_id
                FROM pos_daily_backfill_observation
                WHERE ({' OR '.join(clauses)})
                  AND ean_upc=%s
                  AND upc_id IS NOT NULL
                  AND sold_quantity<>0""",
            tuple(args)+(str(raw_ean),),
        )
        ids.update(int(r['upc_id']) for r in cur.fetchall() if r.get('upc_id') is not None)

    return ids


def rebuild_current_active_unmapped_sales_guard(cur, batch_id: int) -> dict[str, Any]:
    """Recompute current Seafood sold-but-unmapped blockers from all retained POS history.

    The readiness gate is current-state based, not source-batch based. Every Phase 3
    run scans all Seafood UPCs observed in POS, evaluates activity on the latest
    up-to-28 valid completed POS data days, and creates one blocking issue per
    currently active UPC that still lacks confirmed UPC->Article->Family identity.
    """
    completed_through = completed_through_date()
    pos_days = source_data_days(
        cur,
        'sales_by_price_type',
        limit=28,
        include_batch_id=batch_id,
        up_to=completed_through,
    )

    cur.execute(
        """SELECT DISTINCT ean_upc
           FROM upc_department_observation
           WHERE source_type='POS'
             AND department_code=%s
             AND ean_upc IS NOT NULL
             AND TRIM(ean_upc)<>''
           ORDER BY ean_upc""",
        (SEAFOOD_DEPT_CODE,),
    )
    candidates = [str(x['ean_upc']) for x in cur.fetchall()]

    result: dict[str, Any] = {
        'candidate_count': len(candidates),
        'active_unmapped_count': 0,
        'inactive_or_historical_count': 0,
        'mapped_count': 0,
        'mapped_by_raw_ean_count': 0,
        'mapped_by_relinked_pos_upc_id_count': 0,
        'ambiguous_relinked_pos_alias_count': 0,
        'active_unmapped_upcs': [],
        'activity_rule': 'POS_POSITIVE_LATEST_UP_TO_28_VALID_COMPLETED_DATA_DAYS',
        'department_code': SEAFOOD_DEPT_CODE,
    }

    for ean in candidates:
        if _upc_identity_ready(cur, ean):
            result['mapped_count'] += 1
            result['mapped_by_raw_ean_count'] += 1
            continue

        evidence = _active_selling_evidence_for_unmapped(
            cur,
            ean,
            batch_id,
            pos_days=pos_days,
        )
        if evidence['activity_scope'] != 'ACTIVE_SELLING':
            result['inactive_or_historical_count'] += 1
            continue

        # A raw POS service/scale code may not itself exist in selling_upc.
        # If the actual recent POS rows for this exact raw EAN have already
        # been deterministically relinked to exactly one canonical UPC, and
        # that canonical UPC has a confirmed current Article/Family identity,
        # the row is mapped and must not become a false global blocker.
        canonical_ids=_recent_pos_canonical_ids_for_raw_ean(cur,ean,pos_days)
        if len(canonical_ids)==1:
            canonical_upc_id=next(iter(canonical_ids))
            if _upc_id_identity_ready(cur,canonical_upc_id):
                result['mapped_count'] += 1
                result['mapped_by_relinked_pos_upc_id_count'] += 1
                continue
        elif len(canonical_ids)>1:
            result['ambiguous_relinked_pos_alias_count'] += 1

        _issue(
            cur,
            batch_id,
            'CURRENT_ACTIVE_SOLD_UPC_UNMAPPED',
            'UPC',
            ean,
            f'Current active-selling Seafood UPC {ean} has positive POS quantity in the latest valid data days but no confirmed UPC identity mapping.',
            'HIGH',
            detail={
                **evidence,
                'guard': 'CURRENT_ACTIVE_SOLD_UPC_GLOBAL_GATE',
                'scope': 'GLOBAL_CURRENT_STATE',
                'department_code': SEAFOOD_DEPT_CODE,
            },
        )
        result['active_unmapped_count'] += 1
        result['active_unmapped_upcs'].append(ean)

    return result


def _mapped_current_activity_scope(
    m28: dict[str, Any],
) -> tuple[str, str]:
    """Activity scope for mapped serving rows.

    v7.0.10 rule:
      Positive sales on the latest up-to-28 VALID POS data days => ACTIVE_SELLING.
      Everything else => HISTORICAL_ONLY.

    Price List presence alone does not make a UPC current-active.
    """
    if Decimal(str(m28['qty'] or 0)) > 0:
        return 'ACTIVE_SELLING', 'POS_LATEST_28_VALID_DATA_DAYS'

    return 'HISTORICAL_ONLY', 'NO_POS_SALES_LATEST_28_VALID_DATA_DAYS'


def _norm_cost_serving_uom(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip().upper()
    if not s:
        return None
    return 'PACK' if s in {'PAC','PACK'} else s


def _product_class(article_desc: str | None, family_desc: str | None, category: str | None) -> str | None:
    # Classification is intentionally conservative: only explicit category/name markers are used.
    text = ' '.join(x for x in [article_desc, family_desc, category] if x).upper()
    if re.search(r'\bLIVE\b', text):
        return 'LIVE'
    if re.search(r'\bFRESH\b', text):
        return 'FRESH'
    if re.search(r'\bFROZEN\b|\bFRZ\b|\bFZ\b', text):
        return 'FROZEN'
    return None


def _latest_cost(cur, family_id: int) -> dict[str, Any] | None:
    # Authority order:
    # 1) valid 101/107 receipt valuation (109 is physical GR quantity/date, not cost)
    # 2) supported OH-report cost: explicit unit cost or Total Value / Unrestricted Qty
    # 3) Live/Fresh/Frozen official report cost
    # 4) user-confirmed fallback
    cur.execute(
        """SELECT co.cost_per_base_uom,co.cost_amount,co.business_date,co.source_type,
                  bu.uom_code AS base_uom, cu.uom_code AS cost_uom
           FROM article_cost_observation co
           LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
           LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
           WHERE co.family_id=%s AND co.source_type='MOVEMENT_RECEIPT_VALUATION'
             AND co.movement_type IN ('101','107')
             AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
             AND COALESCE(co.cost_per_base_uom,co.cost_amount)>0
           ORDER BY co.business_date DESC, co.cost_observation_id DESC LIMIT 1""",
        (family_id,),
    )
    r = cur.fetchone()
    if r:
        return {
            'cost_per_base': r['cost_per_base_uom'] or r['cost_amount'],
            'date': r['business_date'],
            'source': r['source_type'],
            'base_uom': r['base_uom'] or r['cost_uom'],
        }

    # Department official cost is authoritative ahead of OH fallback.
    cur.execute(
        """SELECT co.cost_amount,co.business_date,co.source_type,cu.uom_code AS cost_uom
           FROM article_cost_observation co
           LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
           WHERE co.family_id=%s
             AND co.source_type IN (
                 'FROZEN_INVENTORY_OFFICIAL_COST',
                 'LIVE_FRESH_SUGGESTION_OFFICIAL_COST'
             )
             AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
             AND co.cost_amount>0
           ORDER BY co.business_date DESC,co.cost_observation_id DESC LIMIT 1""",
        (family_id,),
    )
    r = cur.fetchone()
    if r:
        return {
            'cost_per_base': r['cost_amount'],
            'date': r['business_date'],
            'source': r['source_type'],
            'base_uom': r['cost_uom'],
        }

    cur.execute(
        """SELECT co.cost_amount,co.business_date,co.source_type,cu.uom_code AS cost_uom
           FROM article_cost_observation co
           LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
           WHERE co.family_id=%s
             AND co.source_type='ON_HAND_EXPLICIT_COST_FALLBACK'
             AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
             AND co.cost_amount>0
           ORDER BY co.business_date DESC,co.cost_observation_id DESC LIMIT 1""",
        (family_id,),
    )
    r = cur.fetchone()
    if r:
        return {
            'cost_per_base': r['cost_amount'],
            'date': r['business_date'],
            'source': r['source_type'],
            'base_uom': r['cost_uom'],
        }

    manual = confirmed_family_cost(cur, family_id)
    if manual:
        return {
            'cost_per_base': manual['cost_amount'],
            'date': manual.get('confirmed_date'),
            'source': 'USER_CONFIRMED_FAMILY_COST',
            'base_uom': manual['cost_uom_code'],
        }
    return None


def _price_list_upload_business_date(value: Any) -> date | None:
    """Convert MySQL's UTC upload timestamp to the store business date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))
    try:
        return dt.astimezone(ZoneInfo(BUSINESS_TIMEZONE)).date()
    except Exception:
        return dt.date()


def _current_price(cur, upc_id: int, ean: str | None = None) -> dict[str, Any] | None:
    """Resolve authoritative CURRENT retail price across canonical + raw lineage.

    Every lookup treats canonical upc_id and safe raw EAN/UPC aliases as one
    identity lineage. This prevents an older canonical link from hiding newer
    raw-source evidence after identity repairs or source-format differences.
    """
    current_day = business_today()
    completed_day = completed_through_date()

    def _lineage_pred(id_column: str, ean_column: str) -> tuple[str, tuple[Any, ...], str]:
        if not ean:
            return f"{id_column}=%s", (int(upc_id),), "CANONICAL_UPC_ID"
        ean_pred, ean_args = _upc_match_sql(ean_column, str(ean))
        return (
            f"({id_column}=%s OR {ean_pred})",
            (int(upc_id), *ean_args),
            "CANONICAL_PLUS_RAW_EAN_LINEAGE",
        )

    # Price List: newest accepted file containing any row in this UPC lineage.
    cur.execute(
        """SELECT file_id,upload_timestamp,report_generated_at
           FROM ingest_file
           WHERE source_type='price_list'
             AND processing_status='INGESTED'
             AND error_count=0
             AND duplicate_of_file_id IS NULL
           ORDER BY COALESCE(upload_timestamp,report_generated_at) DESC,file_id DESC
           LIMIT 12"""
    )
    price_files = cur.fetchall()
    config = None
    price_pred, price_args, price_match_mode = _lineage_pred("p.upc_id","p.ean_upc")
    for pf in price_files:
        file_id=int(pf["file_id"])
        cur.execute(
            f"""SELECT p.configured_price,p.price_type,p.source_since_date,
                       p.snapshot_at,p.file_id,f.upload_timestamp
                FROM price_list_observation p
                JOIN ingest_file f ON f.file_id=p.file_id
                WHERE p.file_id=%s
                  AND {price_pred}
                  AND p.configured_price>0
                  AND (p.source_since_date IS NULL OR p.source_since_date<=%s)""",
            (file_id, *price_args, current_day),
        )
        price_rows=cur.fetchall()
        if not price_rows:
            continue
        price_rows.sort(
            key=lambda x: PRICE_TYPE_PRIORITY.get(
                str(x.get("price_type") or "").upper(),0
            ),
            reverse=True,
        )
        config=price_rows[0]
        config["match_mode"]=price_match_mode
        if config.get("upload_timestamp") is None:
            config["upload_timestamp"]=pf.get("upload_timestamp")
        break

    # POS_SINGLE_DATE authority: newest completed SINGLE_DATE sold event
    # anywhere in the same canonical/raw lineage. Do not stop at an older
    # canonical-id event.
    pos=None
    if completed_day is not None:
        sales_pred,sales_args,pos_match_mode=_lineage_pred("s.upc_id","s.ean_upc")
        cur.execute(
            f"""SELECT MAX(s.period_end_date) AS sold_date
                FROM sales_period_observation s
                JOIN ingest_file f ON f.file_id=s.file_id
                WHERE {sales_pred}
                  AND s.temporal_grain='SINGLE_DATE'
                  AND s.period_start_date=s.period_end_date
                  AND s.period_end_date<=%s
                  AND s.sold_quantity<>0
                  AND f.source_type='sales_by_price_type'
                  AND f.processing_status='INGESTED'
                  AND f.error_count=0
                  AND f.duplicate_of_file_id IS NULL
                  AND f.date_semantics_status='RESOLVED'""",
            (*sales_args,completed_day),
        )
        sold_date=(cur.fetchone() or {}).get("sold_date")
        if sold_date is not None:
            cur.execute(
                f"""SELECT UPPER(TRIM(s.price_type)) AS price_type,
                           SUM(s.sales_amount) AS sales_amount,
                           SUM(s.sold_quantity) AS sold_quantity
                    FROM sales_period_observation s
                    JOIN ingest_file f ON f.file_id=s.file_id
                    WHERE {sales_pred}
                      AND s.temporal_grain='SINGLE_DATE'
                      AND s.period_start_date=s.period_end_date
                      AND s.period_end_date=%s
                      AND s.sold_quantity<>0
                      AND f.source_type='sales_by_price_type'
                      AND f.processing_status='INGESTED'
                      AND f.error_count=0
                      AND f.duplicate_of_file_id IS NULL
                      AND f.date_semantics_status='RESOLVED'
                    GROUP BY UPPER(TRIM(s.price_type))""",
                (*sales_args,sold_date),
            )
            sold_rows=[x for x in cur.fetchall() if x.get("sold_quantity") not in (None,0)]
            if sold_rows:
                sold_rows.sort(
                    key=lambda x: PRICE_TYPE_PRIORITY.get(
                        str(x.get("price_type") or "").upper(),0
                    ),
                    reverse=True,
                )
                chosen=sold_rows[0]
                qty=Decimal(str(chosen["sold_quantity"]))
                pos={
                    "price":Decimal(str(chosen.get("sales_amount") or 0))/qty,
                    "type":chosen.get("price_type") or "UNKNOWN",
                    "date":sold_date,
                    "match_mode":pos_match_mode,
                }

    price_date=(
        _price_list_upload_business_date(config.get("upload_timestamp"))
        if config is not None and config.get("upload_timestamp") is not None
        else (
            config.get("snapshot_at").date()
            if config is not None and config.get("snapshot_at") is not None
            else None
        )
    )
    if config is not None and price_date is not None and (pos is None or price_date>=pos["date"]):
        return {
            "price":config["configured_price"],
            "type":config["price_type"],
            "source":"PRICE_LIST",
            "date":price_date,
            "source_since_date":config.get("source_since_date"),
            "price_list_file_id":config.get("file_id"),
            "match_mode":config.get("match_mode"),
        }
    if pos is not None:
        return {
            "price":pos["price"],
            "type":pos["type"],
            "source":"POS_CALCULATED",
            "date":pos["date"],
            "source_since_date":None,
            "price_list_file_id":None,
            "match_mode":pos.get("match_mode"),
        }
    if config is not None:
        return {
            "price":config["configured_price"],
            "type":config["price_type"],
            "source":"PRICE_LIST",
            "date":price_date,
            "source_since_date":config.get("source_since_date"),
            "price_list_file_id":config.get("file_id"),
            "match_mode":config.get("match_mode"),
        }
    return None

def _sales_metrics(
    cur,
    upc_id: int,
    data_days: list[dict[str, Any]],
    ean: str | None = None,
) -> dict[str, Any]:
    """Metrics across canonical POS data days.

    Direct single-day files and one-missing-day residual backfills are valid
    daily evidence. Multi-gap DATE_RANGE reports remain period-level only and
    are deliberately excluded from daily velocity/GP metrics.
    """
    if not data_days:
        return {'sales': Decimal('0'), 'qty': Decimal('0'), 'days': 0, 'start': None, 'end': None}
    daily = _sales_daily_aggregates(cur, data_days, upc_id=upc_id, ean=ean)
    sales = sum((x['sales'] for x in daily.values()), Decimal('0'))
    qty = sum((x['qty'] for x in daily.values()), Decimal('0'))
    dates = [x['date'] for x in data_days]
    return {
        'sales': sales,
        'qty': qty,
        'days': len(data_days),
        'start': min(dates),
        'end': max(dates),
    }


def _family_movement_metrics(cur, family_id: int, data_days: list[dict[str, Any]]) -> tuple[Decimal | None, str | None, int]:
    """Family movement over canonical MVT date/file pairs.

    A multi-date MVT source may be canonical for several posting dates, so file_id
    alone is not a sufficient filter. Restrict every contribution to its exact
    canonical (file_id, posting_date) pair.
    """
    if not data_days:
        return None, None, 0

    clauses: list[str] = []
    args: list[Any] = [family_id]
    for d in data_days:
        clauses.append('(file_id=%s AND posting_date=%s)')
        args.extend([int(d['file_id']), d['date']])

    cur.execute(
        f"""SELECT base_uom_code,SUM(net_sold_quantity) AS q
            FROM family_movement_observation
            WHERE family_id=%s
              AND ({' OR '.join(clauses)})
            GROUP BY base_uom_code""",
        tuple(args),
    )
    rows = [r for r in cur.fetchall() if r['q'] is not None]
    if not rows:
        return Decimal('0'), None, len(data_days)
    if len(rows) == 1:
        return rows[0]['q'], rows[0]['base_uom_code'], len(data_days)
    return None, None, len(data_days)


def _latest_inventory(
    cur,
    upc_id: int,
    article_id: int | None,
    family_id: int | None,
) -> dict[str, Any] | None:
    # SAP OH is owned by Article when Article identity is present. A source row
    # may also carry UPC-like metadata, but movement_history rolls inventory by
    # Article/Family, not UPC. Treating an Article-owned OH row as UPC scope
    # creates a false UPC_SCOPE_HAS_NO_EXACT_MOVEMENT_KEY blocker.
    if article_id is not None:
        cur.execute(
            """SELECT file_id,on_hand_quantity,uom_code,observation_date,
                      article_id,article_number,family_id,upc_id,ean_upc
               FROM inventory_observation
               WHERE article_id=%s
                 AND on_hand_quantity IS NOT NULL
               ORDER BY observation_date DESC, inventory_observation_id DESC LIMIT 1""",
            (article_id,),
        )
        r = cur.fetchone()
        if r:
            r['scope_type'] = 'ARTICLE'
            return r

    # UPC scope is only a fallback for a truly UPC-owned inventory row with no
    # Article owner. Such rows still fail closed for post-anchor movement because
    # movement_history has no exact UPC key.
    cur.execute(
        """SELECT file_id,on_hand_quantity,uom_code,observation_date,
                  article_id,article_number,family_id,upc_id,ean_upc
           FROM inventory_observation
           WHERE upc_id=%s
             AND article_id IS NULL
             AND on_hand_quantity IS NOT NULL
           ORDER BY observation_date DESC, inventory_observation_id DESC LIMIT 1""",
        (upc_id,),
    )
    r = cur.fetchone()
    if r:
        r['scope_type'] = 'UPC'
        return r

    # Family-only fallback is reserved for rows that truly have no article owner.
    if family_id is not None:
        cur.execute(
            """SELECT file_id,on_hand_quantity,uom_code,observation_date,
                      article_id,article_number,family_id,upc_id,ean_upc
               FROM inventory_observation
               WHERE family_id=%s
                 AND article_id IS NULL
                 AND upc_id IS NULL
                 AND on_hand_quantity IS NOT NULL
               ORDER BY observation_date DESC, inventory_observation_id DESC LIMIT 1""",
            (family_id,),
        )
        r = cur.fetchone()
        if r:
            r['scope_type'] = 'FAMILY'
            return r
    return None


def _company_prices(cur, upc_id: int, family_id: int | None) -> dict[str, Any] | None:
    if family_id is None:
        cur.execute("SELECT * FROM company_price_observation WHERE upc_id=%s AND source_type<>'tx_seafood_abc_price' ORDER BY observation_date DESC,company_price_observation_id DESC LIMIT 1", (upc_id,))
    else:
        cur.execute("SELECT * FROM company_price_observation WHERE (upc_id=%s OR family_id=%s) AND source_type<>'tx_seafood_abc_price' ORDER BY observation_date DESC,company_price_observation_id DESC LIMIT 1", (upc_id, family_id))
    return cur.fetchone()


def _historical_sweet_spot(
    cur,
    upc_id: int,
    family_id: int,
    factor: Decimal | None,
    data_days: list[dict[str, Any]],
    ean: str | None = None,
) -> Decimal | None:
    if factor is None or not data_days:
        return None
    daily_map = _sales_daily_aggregates(cur, data_days, upc_id=upc_id, ean=ean)
    daily = [
        {'period_end_date': d, 's': x['sales'], 'q': x['qty']}
        for d, x in sorted(daily_map.items())
        if x['qty'] != 0
    ]
    if not daily:
        return None
    buckets: dict[Decimal, list[Decimal]] = defaultdict(list)
    for r in daily:
        price = (r['s'] / r['q']).quantize(Decimal('0.01'))
        cur.execute(
            """SELECT COALESCE(cost_per_base_uom,cost_amount) AS c
               FROM article_cost_observation
               WHERE family_id=%s AND business_date<=%s AND cost_status NOT IN ('REJECTED','SUPERSEDED')
                 AND COALESCE(cost_per_base_uom,cost_amount)>0
               ORDER BY CASE
                          WHEN source_type='MOVEMENT_RECEIPT_VALUATION' THEN 1
                          WHEN source_type IN (
                              'FROZEN_INVENTORY_OFFICIAL_COST',
                              'LIVE_FRESH_SUGGESTION_OFFICIAL_COST'
                          ) THEN 2
                          WHEN source_type='ON_HAND_EXPLICIT_COST_FALLBACK' THEN 3
                          WHEN source_type='USER_CONFIRMED_FAMILY_COST' THEN 4
                          ELSE 9
                        END,
                        business_date DESC,cost_observation_id DESC LIMIT 1""", (family_id, r['period_end_date']))
        cr = cur.fetchone()
        if not cr or cr['c'] is None:
            continue
        cost_sell = Decimal(cr['c']) * factor
        gp_day = r['s'] - (r['q'] * cost_sell)
        buckets[price].append(gp_day)
    if not buckets:
        return None
    return max(buckets.items(), key=lambda kv: sum(kv[1], Decimal('0')) / Decimal(len(kv[1])))[0]



def _days_of_supply(
    inv: dict[str, Any] | None,
    inv_position: dict[str, Any] | None,
    selling_uom: str | None,
    base_uom: str | None,
    factor: Decimal | None,
    velocity7: Decimal,
) -> Decimal | None:
    """Return non-negative DOS from a usable inventory roll-forward.

    Negative/zero OH means there are zero days of stock available, not negative
    days of supply. Positive OH still requires positive velocity and compatible
    inventory/selling units. Blocked/unusable inventory remains NULL.
    """
    if not inv or not inv_position or not inv_position.get('analysis_usable'):
        return None

    iq = Decimal(str(inv_position['quantity']))
    if iq <= 0:
        return Decimal('0')

    if velocity7 <= 0:
        return None

    iu = (inv_position.get('uom') or '').upper()
    if iu and selling_uom and iu == str(selling_uom).upper():
        return iq / velocity7
    if iu and base_uom and iu == str(base_uom).upper() and factor and factor > 0:
        return (iq / factor) / velocity7
    return None

def rebuild_quick_check(cur, batch_id: int, progress=None) -> dict[str, Any]:
    calendar_today = business_today()
    completed_through = completed_through_date()

    # Rolling metrics use completed DATA DAYS, not calendar days. The current batch is eligible
    # because its history rows are inserted immediately before this rebuild. Today's date is
    # excluded to prevent a partial intraday file from entering daily velocity/GP metrics.
    pos_days_7 = source_data_days(cur, 'sales_by_price_type', limit=7, include_batch_id=batch_id, up_to=completed_through)
    pos_days_28 = source_data_days(cur, 'sales_by_price_type', limit=28, include_batch_id=batch_id, up_to=completed_through)
    pos_days_30 = source_data_days(cur, 'sales_by_price_type', limit=30, include_batch_id=batch_id, up_to=completed_through)
    mvt_days_7 = source_data_days(cur, 'movement', limit=7, include_batch_id=batch_id, up_to=completed_through)
    pos_cov = coverage_summary(cur, 'sales_by_price_type', include_batch_id=batch_id)
    mvt_cov = coverage_summary(cur, 'movement', include_batch_id=batch_id)

    # Serving is a derived snapshot. Clean-replace it transactionally; RAW/history remain immutable.
    cur.execute('DELETE FROM quick_check_current')
    cur.execute(
        """SELECT su.upc_id,su.ean_upc,su.selling_description,a.article_id,a.article_number,a.article_description,a.category_code,
                  pf.family_id,pf.main_article_number,pf.family_description,
                  qu.selling_uom,qu.base_uom,qu.base_qty_per_selling_unit
           FROM selling_upc su
           JOIN bridge_article_upc bau ON bau.upc_id=su.upc_id AND bau.mapping_status='CONFIRMED' AND bau.is_primary=TRUE
                AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
           JOIN article a ON a.article_id=bau.article_id
           JOIN bridge_article_family baf ON baf.article_id=a.article_id AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
                AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           JOIN product_family pf ON pf.family_id=baf.family_id
           LEFT JOIN v_current_upc_uom qu ON qu.ean_upc=su.ean_upc
           LEFT JOIN manual_upc_retirement mur
             ON mur.ean_upc=su.ean_upc
            AND mur.retirement_status='CONFIRMED'
           WHERE su.record_status='ACTIVE'
             AND mur.retirement_id IS NULL
           ORDER BY su.upc_id"""
    )
    products = cur.fetchall()
    active_rows = active_ready = active_hold = historical_rows = 0
    live_issue_counts: dict[str, int] = defaultdict(int)
    total_rows = len(products)
    progress_started = time.monotonic()
    progress_last_emit = {'at': progress_started}

    def report_row_progress(current: int, p: dict[str, Any] | None = None, *, force: bool = False):
        if not progress:
            return
        # Exact progress without flooding MySQL: emit at least every 10 rows,
        # or every ~3 seconds when rows are slow, plus start/final events.
        now = time.monotonic()
        if (
            not force
            and current % 10 != 0
            and (now - progress_last_emit['at']) < 3.0
        ):
            return
        progress_last_emit['at'] = now
        elapsed = max(0.001, now - progress_started)
        speed = (Decimal(current) / Decimal(str(elapsed))) if current > 0 else Decimal('0')
        remaining = max(0, total_rows - current)
        eta = (Decimal(remaining) / speed) if speed > 0 else None
        pct = (Decimal(current) * Decimal('100') / Decimal(total_rows)) if total_rows else Decimal('100')
        progress(
            'PHASE3_QUICK_CHECK_REBUILD',
            {
                'progress_kind': 'ROW_COUNT',
                'progress_unit': 'UPC',
                'progress_current': current,
                'progress_total': total_rows,
                'progress_pct': float(pct.quantize(Decimal('0.1'))),
                'progress_ready': active_ready,
                'progress_hold': active_hold,
                'progress_historical': historical_rows,
                'progress_issue_counts': dict(sorted(
                    live_issue_counts.items(),
                    key=lambda kv: (-kv[1], kv[0]),
                )),
                'progress_elapsed_seconds': int(elapsed),
                'progress_rows_per_second': float(speed.quantize(Decimal('0.01'))) if speed > 0 else 0.0,
                'progress_eta_seconds': int(eta) if eta is not None else None,
                'progress_current_upc': str((p or {}).get('ean_upc') or '') or None,
                'progress_current_name': str((p or {}).get('selling_description') or '') or None,
            },
        )

    report_row_progress(0, force=True)
    for row_no, p in enumerate(products, 1):
        upc_id = int(p['upc_id']); family_id = int(p['family_id'])
        m7 = _sales_metrics(cur, upc_id, pos_days_7, p['ean_upc'])
        m28 = _sales_metrics(cur, upc_id, pos_days_28, p['ean_upc'])
        m30 = _sales_metrics(cur, upc_id, pos_days_30, p['ean_upc'])
        price = _current_price(cur, upc_id, p['ean_upc'])
        cost = _latest_cost(cur, family_id)
        cur.execute('SELECT MAX(posting_date) AS d FROM receiving_observation WHERE family_id=%s AND movement_type IN (\'101\',\'109\')', (family_id,))
        rr = cur.fetchone(); last_receipt = rr['d'] if rr else None
        factor = Decimal(str(p['base_qty_per_selling_unit'])) if p['base_qty_per_selling_unit'] is not None else None
        selling_uom = p['selling_uom']; base_uom = p['base_uom']
        norm_selling_uom = _norm_cost_serving_uom(selling_uom)
        norm_base_uom = _norm_cost_serving_uom(base_uom)
        cost_uom = _norm_cost_serving_uom(cost.get('base_uom')) if cost else None
        if factor is None and norm_selling_uom and norm_base_uom and norm_selling_uom == norm_base_uom:
            factor = Decimal('1')

        cost_sell = None
        # v7.0.37: a cost stated in the exact POS Selling UOM can be used
        # directly as cost-per-selling-unit with factor 1. This is a calculation
        # rule only; it does NOT infer or write Base/Inventory UOM.
        if cost and norm_selling_uom and cost_uom and norm_selling_uom == cost_uom:
            cost_sell = Decimal(str(cost['cost_per_base']))
        elif cost and factor is not None and cost_uom and norm_base_uom and cost_uom == norm_base_uom:
            cost_sell = Decimal(str(cost['cost_per_base'])) * factor
        elif cost and norm_selling_uom and cost_uom:
            # v7.0.41: use only an exact user-confirmed cost-to-selling
            # conversion. This does NOT alter Base/Inventory UOM or its factor.
            conv = confirmed_cost_conversion(cur, p['ean_upc'])
            if conv:
                conv_sell = _norm_cost_serving_uom(conv.get('selling_uom_code'))
                conv_cost = _norm_cost_serving_uom(conv.get('cost_uom_code'))
                sell_qty = Decimal(str(conv.get('selling_qty')))
                cost_qty = Decimal(str(conv.get('cost_qty')))
                if (
                    conv_sell == norm_selling_uom
                    and conv_cost == cost_uom
                    and sell_qty > 0
                    and cost_qty > 0
                ):
                    cost_sell = (
                        Decimal(str(cost['cost_per_base']))
                        * cost_qty
                        / sell_qty
                    )
        fm7, fm_uom, _fm_days = _family_movement_metrics(cur, family_id, mvt_days_7)
        inv = _latest_inventory(cur, upc_id, int(p['article_id']) if p.get('article_id') is not None else None, family_id)
        inv_position = None
        if inv:
            inv_position = rollforward_position(
                cur,
                anchor_quantity=inv.get('on_hand_quantity'),
                anchor_uom=inv.get('uom_code'),
                anchor_date=inv.get('observation_date'),
                scope_type=inv.get('scope_type'),
                article_id=inv.get('article_id'),
                family_id=inv.get('family_id') if inv.get('family_id') is not None else family_id,
                upc_id=inv.get('upc_id') if inv.get('upc_id') is not None else upc_id,
                include_batch_id=batch_id,
            )
        cp = _company_prices(cur, upc_id, family_id)
        pclass = _product_class(p['article_description'], p['family_description'], p['category_code'])

        # A valid data day with no UPC sales row is a real zero and remains in the denominator.
        velocity7 = (Decimal(m7['qty']) / Decimal(m7['days'])) if m7['days'] > 0 else Decimal('0')
        velocity30 = (Decimal(m30['qty']) / Decimal(m30['days'])) if m30['days'] > 0 else Decimal('0')
        gp_pct = gp7 = gpday = None
        if price and cost_sell is not None and Decimal(price['price']) > 0:
            gp_pct = (Decimal(price['price']) - cost_sell) / Decimal(price['price'])
            gp7 = Decimal(m7['sales']) - Decimal(m7['qty']) * cost_sell
            gpday = (gp7 / Decimal(m7['days'])) if m7['days'] > 0 else None
        dos = _days_of_supply(
            inv,
            inv_position,
            selling_uom,
            base_uom,
            factor,
            velocity7,
        )

        # DOH is physical/calendar age, not a rolling-data-day metric.
        # Fresh/Live uses the strict >7-day freshness rule; Frozen also keeps
        # receipt age so Pricing Review can surface >60-day markdown risk.
        doh = (
            (calendar_today - last_receipt).days
            if pclass in {'FRESH', 'LIVE', 'FROZEN'} and last_receipt
            else None
        )
        wgpm = None
        if cost_sell is not None and pclass in {'LIVE', 'FRESH', 'FROZEN'}:
            target = {'LIVE': Decimal('0.15'), 'FRESH': Decimal('0.30'), 'FROZEN': Decimal('0.44')}[pclass]
            wgpm = (cost_sell / (Decimal('1') - target)).quantize(Decimal('0.01'))
        sweet = _historical_sweet_spot(cur, upc_id, family_id, factor, pos_days_30, p['ean_upc']) if cost else None
        reasons = []
        activity_scope, activity_basis = _mapped_current_activity_scope(m28)
        # Only positive sales in the latest up-to-28 VALID POS data days make
        # a UPC current-active. Everything else remains historical/non-blocking.
        active_current = activity_scope == 'ACTIVE_SELLING'
        if active_current:
            if not selling_uom: reasons.append('SELLING_UOM_MISSING')
            if cost is None: reasons.append('CURRENT_COST_MISSING')
            if price is None: reasons.append('CURRENT_PRICE_MISSING')
            if cost is not None and cost_sell is None: reasons.append('COST_TO_SELLING_UOM_UNRESOLVED')
            if inv and inv_position and not inv_position.get('analysis_usable'):
                reasons.append('OH_MOVEMENT_ROLLFORWARD_BLOCKED')
        if active_current:
            active_rows += 1
            qc_status = 'QA_HOLD' if reasons else 'READY'
            if qc_status == 'READY':
                active_ready += 1
            else:
                active_hold += 1
                for reason in reasons:
                    live_issue_counts[str(reason)] += 1
                _issue(cur, batch_id, 'QUICK_CHECK_CORE_FIELD_MISSING', 'UPC', p['ean_upc'],
                       f"Quick Check core fields are unresolved for UPC {p['ean_upc']}: {', '.join(reasons)}",
                       'HIGH', detail={
                           'reasons': reasons,
                           'activity_scope': activity_scope,
                           'activity_basis': activity_basis,
                           'recent_pos_qty_28_valid_days': str(m28['qty']),
                           'recent_pos_valid_day_count': m28['days'],
                           'selling_uom': selling_uom,
                           'base_uom': base_uom,
                           'base_qty_per_selling_unit': str(factor) if factor is not None else None,
                           'cost_source': cost.get('source') if cost else None,
                           'cost_uom': cost.get('base_uom') if cost else None,
                           'inventory_scope_type': inv.get('scope_type') if inv else None,
                           'inventory_article_number': inv.get('article_number') if inv else None,
                           'inventory_rollforward_blockers': inv_position.get('blockers') if inv_position else None,
                           'inventory_missing_movement_days': inv_position.get('missing_movement_days') if inv_position else None,
                           'inventory_uom_mismatches': inv_position.get('uom_mismatches') if inv_position else None,
                       })
        else:
            historical_rows += 1
            qc_status = 'HISTORICAL_ONLY'
        cur.execute(
            """INSERT INTO quick_check_current
               (upc_id,ean_upc,selling_description,article_id,article_number,family_id,main_article_number,family_description,
                product_class,selling_uom,base_uom,base_qty_per_selling_unit,current_cost_per_base_uom,current_cost_per_selling_unit,
                cost_source,cost_date,last_receipt_date,current_price,current_price_type,current_price_source,current_price_asof_date,
                sales_dollars_7d,pos_qty_7d,upc_velocity_7d,sales_days_7d,sales_dollars_30d,pos_qty_30d,upc_velocity_30d,sales_days_30d,
                family_movement_7d,family_movement_uom,current_oh,current_oh_uom,oh_date,dos,doh,gp_pct_current,gp_dollars_7d,gp_per_day_7d,
                sweet_spot_price,wgpm_price,company_price_a,company_price_b,company_price_c,quick_check_status,blocking_reason,publish_batch_id,published_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP(6))
               ON DUPLICATE KEY UPDATE
                selling_description=VALUES(selling_description),article_id=VALUES(article_id),article_number=VALUES(article_number),
                family_id=VALUES(family_id),main_article_number=VALUES(main_article_number),family_description=VALUES(family_description),
                product_class=VALUES(product_class),selling_uom=VALUES(selling_uom),base_uom=VALUES(base_uom),
                base_qty_per_selling_unit=VALUES(base_qty_per_selling_unit),current_cost_per_base_uom=VALUES(current_cost_per_base_uom),
                current_cost_per_selling_unit=VALUES(current_cost_per_selling_unit),cost_source=VALUES(cost_source),cost_date=VALUES(cost_date),
                last_receipt_date=VALUES(last_receipt_date),current_price=VALUES(current_price),current_price_type=VALUES(current_price_type),
                current_price_source=VALUES(current_price_source),current_price_asof_date=VALUES(current_price_asof_date),
                sales_dollars_7d=VALUES(sales_dollars_7d),pos_qty_7d=VALUES(pos_qty_7d),upc_velocity_7d=VALUES(upc_velocity_7d),
                sales_days_7d=VALUES(sales_days_7d),sales_dollars_30d=VALUES(sales_dollars_30d),pos_qty_30d=VALUES(pos_qty_30d),
                upc_velocity_30d=VALUES(upc_velocity_30d),sales_days_30d=VALUES(sales_days_30d),family_movement_7d=VALUES(family_movement_7d),
                family_movement_uom=VALUES(family_movement_uom),current_oh=VALUES(current_oh),current_oh_uom=VALUES(current_oh_uom),
                oh_date=VALUES(oh_date),dos=VALUES(dos),doh=VALUES(doh),gp_pct_current=VALUES(gp_pct_current),gp_dollars_7d=VALUES(gp_dollars_7d),
                gp_per_day_7d=VALUES(gp_per_day_7d),sweet_spot_price=VALUES(sweet_spot_price),wgpm_price=VALUES(wgpm_price),
                company_price_a=VALUES(company_price_a),company_price_b=VALUES(company_price_b),company_price_c=VALUES(company_price_c),
                quick_check_status=VALUES(quick_check_status),blocking_reason=VALUES(blocking_reason),publish_batch_id=VALUES(publish_batch_id),
                published_at=CURRENT_TIMESTAMP(6)""",
            (upc_id, p['ean_upc'], p['selling_description'], p['article_id'], p['article_number'], family_id, p['main_article_number'], p['family_description'],
             pclass, selling_uom, base_uom, factor, cost['cost_per_base'] if cost else None, cost_sell,
             cost['source'] if cost else None, cost['date'] if cost else None, last_receipt,
             price['price'] if price else None, price['type'] if price else None, price['source'] if price else None, price['date'] if price else None,
             m7['sales'], m7['qty'], velocity7, m7['days'], m30['sales'], m30['qty'], velocity30, m30['days'], fm7, fm_uom,
             (inv_position['quantity'] if inv and inv_position and inv_position.get('analysis_usable') else (inv['on_hand_quantity'] if inv else None)),
             (inv_position['uom'] if inv and inv_position and inv_position.get('analysis_usable') else (inv['uom_code'] if inv else None)),
             (inv_position['movement_through_date'] if inv and inv_position and inv_position.get('analysis_usable') else (inv['observation_date'] if inv else None)),
             dos, doh,
             gp_pct, gp7, gpday, sweet, wgpm, cp['price_a'] if cp else None, cp['price_b'] if cp else None, cp['price_c'] if cp else None,
             qc_status,
             (','.join(reasons) if reasons else
              ('NO_POS_SALES_LATEST_28_VALID_DATA_DAYS' if not active_current else None)),
             batch_id),
        )
        report_row_progress(row_no, p, force=(row_no == total_rows))

    def _dates(xs: list[dict[str, Any]]) -> list[str]:
        return [x['date'].isoformat() for x in sorted(xs, key=lambda z: z['date'])]

    return {
        # Operational Quick Check scope = current-active only.
        'rows': active_rows,
        'ready': active_ready,
        'hold': active_hold,

        # All confirmed product rows are still published/searchable.
        'serving_rows_total': len(products),
        'historical_rows': historical_rows,
        'activity_rule': 'POS_POSITIVE_LATEST_UP_TO_28_VALID_COMPLETED_DATA_DAYS',
        'data_coverage': {
            'pos_7d_data_days': _dates(pos_days_7),
            'pos_30d_data_days': _dates(pos_days_30),
            'mvt_7d_data_days': _dates(mvt_days_7),
            'pos_missing_dates': [d.isoformat() for d in pos_cov['missing_dates']],
            'mvt_missing_dates': [d.isoformat() for d in mvt_cov['missing_dates']],
            'expected_through': pos_cov['expected_through'].isoformat(),
            'pos_latest_valid_date': pos_cov['latest_valid_date'].isoformat() if pos_cov['latest_valid_date'] else None,
            'mvt_latest_valid_date': mvt_cov['latest_valid_date'].isoformat() if mvt_cov['latest_valid_date'] else None,
        },
    }



def refresh_quick_check_subset(cur, batch_id: int, *, family_ids: Iterable[int] | None = None, upcs: Iterable[str] | None = None) -> dict[str, Any]:
    calendar_today = business_today()
    completed_through = completed_through_date()

    # Rolling metrics use completed DATA DAYS, not calendar days. The current batch is eligible
    # because its history rows are inserted immediately before this rebuild. Today's date is
    # excluded to prevent a partial intraday file from entering daily velocity/GP metrics.
    pos_days_7 = source_data_days(cur, 'sales_by_price_type', limit=7, include_batch_id=batch_id, up_to=completed_through)
    pos_days_28 = source_data_days(cur, 'sales_by_price_type', limit=28, include_batch_id=batch_id, up_to=completed_through)
    pos_days_30 = source_data_days(cur, 'sales_by_price_type', limit=30, include_batch_id=batch_id, up_to=completed_through)
    mvt_days_7 = source_data_days(cur, 'movement', limit=7, include_batch_id=batch_id, up_to=completed_through)
    # Targeted serving refresh: update only explicitly selected UPCs/families.
    # This intentionally does NOT delete or recalculate unrelated Quick Check rows.
    target_family_ids = sorted({int(x) for x in (family_ids or [])})
    target_upcs = sorted({str(x).strip() for x in (upcs or []) if str(x).strip()})
    if not target_family_ids and not target_upcs:
        raise ValueError('TARGETED_QUICK_CHECK_SCOPE_EMPTY')

    target_clauses: list[str] = []
    target_args: list[Any] = []
    if target_family_ids:
        ph = ','.join(['%s'] * len(target_family_ids))
        target_clauses.append(f'pf.family_id IN ({ph})')
        target_args.extend(target_family_ids)
    if target_upcs:
        ph = ','.join(['%s'] * len(target_upcs))
        target_clauses.append(f'su.ean_upc IN ({ph})')
        target_args.extend(target_upcs)
    target_where = ' AND (' + ' OR '.join(target_clauses) + ')'

    cur.execute(
        f"""SELECT su.upc_id,su.ean_upc,su.selling_description,a.article_id,a.article_number,a.article_description,a.category_code,
                  pf.family_id,pf.main_article_number,pf.family_description,
                  qu.selling_uom,qu.base_uom,qu.base_qty_per_selling_unit
           FROM selling_upc su
           JOIN bridge_article_upc bau ON bau.upc_id=su.upc_id AND bau.mapping_status='CONFIRMED' AND bau.is_primary=TRUE
                AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
           JOIN article a ON a.article_id=bau.article_id
           JOIN bridge_article_family baf ON baf.article_id=a.article_id AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
                AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           JOIN product_family pf ON pf.family_id=baf.family_id
           LEFT JOIN v_current_upc_uom qu ON qu.ean_upc=su.ean_upc
           LEFT JOIN manual_upc_retirement mur
             ON mur.ean_upc=su.ean_upc
            AND mur.retirement_status='CONFIRMED'
           WHERE su.record_status='ACTIVE'
             AND mur.retirement_id IS NULL
             {target_where}
           ORDER BY su.upc_id""",
        tuple(target_args),
    )
    products = cur.fetchall()
    if not products:
        raise ValueError('TARGETED_QUICK_CHECK_SCOPE_NOT_FOUND')

    # Resolve only prior per-UPC core holds in the target scope. If a target is
    # still invalid below, _issue() will create a fresh current hold.
    target_eans = sorted({str(p['ean_upc']) for p in products})
    ph = ','.join(['%s'] * len(target_eans))
    cur.execute(
        f"""UPDATE qa_phase3_issue
            SET issue_status='RESOLVED',
                detail_json=JSON_SET(
                  COALESCE(detail_json,JSON_OBJECT()),
                  '$.resolution',
                  'Superseded by targeted Quick Check refresh'
                )
            WHERE batch_id=%s
              AND issue_status='OPEN'
              AND issue_code='QUICK_CHECK_CORE_FIELD_MISSING'
              AND entity_type='UPC'
              AND entity_key IN ({ph})""",
        (batch_id, *target_eans),
    )
    prior_target_core_holds_resolved = int(cur.rowcount or 0)
    active_rows = active_ready = active_hold = historical_rows = 0
    for p in products:
        upc_id = int(p['upc_id']); family_id = int(p['family_id'])
        # Targeted refresh must preserve the same raw-EAN lineage fallback as
        # the full rebuild. This is essential for 249 cook/service POS aliases,
        # whose source rows may not carry the current canonical upc_id.
        m7 = _sales_metrics(cur, upc_id, pos_days_7, p['ean_upc'])
        m28 = _sales_metrics(cur, upc_id, pos_days_28, p['ean_upc'])
        m30 = _sales_metrics(cur, upc_id, pos_days_30, p['ean_upc'])
        price = _current_price(cur, upc_id, p['ean_upc'])
        cost = _latest_cost(cur, family_id)
        cur.execute('SELECT MAX(posting_date) AS d FROM receiving_observation WHERE family_id=%s AND movement_type IN (\'101\',\'109\')', (family_id,))
        rr = cur.fetchone(); last_receipt = rr['d'] if rr else None
        factor = Decimal(str(p['base_qty_per_selling_unit'])) if p['base_qty_per_selling_unit'] is not None else None
        selling_uom = p['selling_uom']; base_uom = p['base_uom']
        norm_selling_uom = _norm_cost_serving_uom(selling_uom)
        norm_base_uom = _norm_cost_serving_uom(base_uom)
        cost_uom = _norm_cost_serving_uom(cost.get('base_uom')) if cost else None
        if factor is None and norm_selling_uom and norm_base_uom and norm_selling_uom == norm_base_uom:
            factor = Decimal('1')

        cost_sell = None
        # v7.0.37: a cost stated in the exact POS Selling UOM can be used
        # directly as cost-per-selling-unit with factor 1. This is a calculation
        # rule only; it does NOT infer or write Base/Inventory UOM.
        if cost and norm_selling_uom and cost_uom and norm_selling_uom == cost_uom:
            cost_sell = Decimal(str(cost['cost_per_base']))
        elif cost and factor is not None and cost_uom and norm_base_uom and cost_uom == norm_base_uom:
            cost_sell = Decimal(str(cost['cost_per_base'])) * factor
        elif cost and norm_selling_uom and cost_uom:
            # v7.0.41: use only an exact user-confirmed cost-to-selling
            # conversion. This does NOT alter Base/Inventory UOM or its factor.
            conv = confirmed_cost_conversion(cur, p['ean_upc'])
            if conv:
                conv_sell = _norm_cost_serving_uom(conv.get('selling_uom_code'))
                conv_cost = _norm_cost_serving_uom(conv.get('cost_uom_code'))
                sell_qty = Decimal(str(conv.get('selling_qty')))
                cost_qty = Decimal(str(conv.get('cost_qty')))
                if (
                    conv_sell == norm_selling_uom
                    and conv_cost == cost_uom
                    and sell_qty > 0
                    and cost_qty > 0
                ):
                    cost_sell = (
                        Decimal(str(cost['cost_per_base']))
                        * cost_qty
                        / sell_qty
                    )
        fm7, fm_uom, _fm_days = _family_movement_metrics(cur, family_id, mvt_days_7)
        inv = _latest_inventory(cur, upc_id, int(p['article_id']) if p.get('article_id') is not None else None, family_id)
        inv_position = None
        if inv:
            inv_position = rollforward_position(
                cur,
                anchor_quantity=inv.get('on_hand_quantity'),
                anchor_uom=inv.get('uom_code'),
                anchor_date=inv.get('observation_date'),
                scope_type=inv.get('scope_type'),
                article_id=inv.get('article_id'),
                family_id=inv.get('family_id') if inv.get('family_id') is not None else family_id,
                upc_id=inv.get('upc_id') if inv.get('upc_id') is not None else upc_id,
                include_batch_id=batch_id,
            )
        cp = _company_prices(cur, upc_id, family_id)
        pclass = _product_class(p['article_description'], p['family_description'], p['category_code'])

        # A valid data day with no UPC sales row is a real zero and remains in the denominator.
        velocity7 = (Decimal(m7['qty']) / Decimal(m7['days'])) if m7['days'] > 0 else Decimal('0')
        velocity30 = (Decimal(m30['qty']) / Decimal(m30['days'])) if m30['days'] > 0 else Decimal('0')
        gp_pct = gp7 = gpday = None
        if price and cost_sell is not None and Decimal(price['price']) > 0:
            gp_pct = (Decimal(price['price']) - cost_sell) / Decimal(price['price'])
            gp7 = Decimal(m7['sales']) - Decimal(m7['qty']) * cost_sell
            gpday = (gp7 / Decimal(m7['days'])) if m7['days'] > 0 else None
        dos = _days_of_supply(
            inv,
            inv_position,
            selling_uom,
            base_uom,
            factor,
            velocity7,
        )

        # DOH is physical/calendar age, not a rolling-data-day metric.
        # Fresh/Live uses the strict >7-day freshness rule; Frozen also keeps
        # receipt age so Pricing Review can surface >60-day markdown risk.
        doh = (
            (calendar_today - last_receipt).days
            if pclass in {'FRESH', 'LIVE', 'FROZEN'} and last_receipt
            else None
        )
        wgpm = None
        if cost_sell is not None and pclass in {'LIVE', 'FRESH', 'FROZEN'}:
            target = {'LIVE': Decimal('0.15'), 'FRESH': Decimal('0.30'), 'FROZEN': Decimal('0.44')}[pclass]
            wgpm = (cost_sell / (Decimal('1') - target)).quantize(Decimal('0.01'))
        sweet = _historical_sweet_spot(cur, upc_id, family_id, factor, pos_days_30, p['ean_upc']) if cost else None
        reasons = []
        activity_scope, activity_basis = _mapped_current_activity_scope(m28)
        # Only positive sales in the latest up-to-28 VALID POS data days make
        # a UPC current-active. Everything else remains historical/non-blocking.
        active_current = activity_scope == 'ACTIVE_SELLING'
        if active_current:
            if not selling_uom: reasons.append('SELLING_UOM_MISSING')
            if cost is None: reasons.append('CURRENT_COST_MISSING')
            if price is None: reasons.append('CURRENT_PRICE_MISSING')
            if cost is not None and cost_sell is None: reasons.append('COST_TO_SELLING_UOM_UNRESOLVED')
            if inv and inv_position and not inv_position.get('analysis_usable'):
                reasons.append('OH_MOVEMENT_ROLLFORWARD_BLOCKED')
        if active_current:
            active_rows += 1
            qc_status = 'QA_HOLD' if reasons else 'READY'
            if qc_status == 'READY':
                active_ready += 1
            else:
                active_hold += 1
                _issue(cur, batch_id, 'QUICK_CHECK_CORE_FIELD_MISSING', 'UPC', p['ean_upc'],
                       f"Quick Check core fields are unresolved for UPC {p['ean_upc']}: {', '.join(reasons)}",
                       'HIGH', detail={
                           'reasons': reasons,
                           'activity_scope': activity_scope,
                           'activity_basis': activity_basis,
                           'recent_pos_qty_28_valid_days': str(m28['qty']),
                           'recent_pos_valid_day_count': m28['days'],
                       })
        else:
            historical_rows += 1
            qc_status = 'HISTORICAL_ONLY'
        cur.execute(
            """INSERT INTO quick_check_current
               (upc_id,ean_upc,selling_description,article_id,article_number,family_id,main_article_number,family_description,
                product_class,selling_uom,base_uom,base_qty_per_selling_unit,current_cost_per_base_uom,current_cost_per_selling_unit,
                cost_source,cost_date,last_receipt_date,current_price,current_price_type,current_price_source,current_price_asof_date,
                sales_dollars_7d,pos_qty_7d,upc_velocity_7d,sales_days_7d,sales_dollars_30d,pos_qty_30d,upc_velocity_30d,sales_days_30d,
                family_movement_7d,family_movement_uom,current_oh,current_oh_uom,oh_date,dos,doh,gp_pct_current,gp_dollars_7d,gp_per_day_7d,
                sweet_spot_price,wgpm_price,company_price_a,company_price_b,company_price_c,quick_check_status,blocking_reason,publish_batch_id,published_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP(6))
               ON DUPLICATE KEY UPDATE
                selling_description=VALUES(selling_description),article_id=VALUES(article_id),article_number=VALUES(article_number),
                family_id=VALUES(family_id),main_article_number=VALUES(main_article_number),family_description=VALUES(family_description),
                product_class=VALUES(product_class),selling_uom=VALUES(selling_uom),base_uom=VALUES(base_uom),
                base_qty_per_selling_unit=VALUES(base_qty_per_selling_unit),current_cost_per_base_uom=VALUES(current_cost_per_base_uom),
                current_cost_per_selling_unit=VALUES(current_cost_per_selling_unit),cost_source=VALUES(cost_source),cost_date=VALUES(cost_date),
                last_receipt_date=VALUES(last_receipt_date),current_price=VALUES(current_price),current_price_type=VALUES(current_price_type),
                current_price_source=VALUES(current_price_source),current_price_asof_date=VALUES(current_price_asof_date),
                sales_dollars_7d=VALUES(sales_dollars_7d),pos_qty_7d=VALUES(pos_qty_7d),upc_velocity_7d=VALUES(upc_velocity_7d),
                sales_days_7d=VALUES(sales_days_7d),sales_dollars_30d=VALUES(sales_dollars_30d),pos_qty_30d=VALUES(pos_qty_30d),
                upc_velocity_30d=VALUES(upc_velocity_30d),sales_days_30d=VALUES(sales_days_30d),family_movement_7d=VALUES(family_movement_7d),
                family_movement_uom=VALUES(family_movement_uom),current_oh=VALUES(current_oh),current_oh_uom=VALUES(current_oh_uom),
                oh_date=VALUES(oh_date),dos=VALUES(dos),doh=VALUES(doh),gp_pct_current=VALUES(gp_pct_current),gp_dollars_7d=VALUES(gp_dollars_7d),
                gp_per_day_7d=VALUES(gp_per_day_7d),sweet_spot_price=VALUES(sweet_spot_price),wgpm_price=VALUES(wgpm_price),
                company_price_a=VALUES(company_price_a),company_price_b=VALUES(company_price_b),company_price_c=VALUES(company_price_c),
                quick_check_status=VALUES(quick_check_status),blocking_reason=VALUES(blocking_reason),publish_batch_id=VALUES(publish_batch_id),
                published_at=CURRENT_TIMESTAMP(6)""",
            (upc_id, p['ean_upc'], p['selling_description'], p['article_id'], p['article_number'], family_id, p['main_article_number'], p['family_description'],
             pclass, selling_uom, base_uom, factor, cost['cost_per_base'] if cost else None, cost_sell,
             cost['source'] if cost else None, cost['date'] if cost else None, last_receipt,
             price['price'] if price else None, price['type'] if price else None, price['source'] if price else None, price['date'] if price else None,
             m7['sales'], m7['qty'], velocity7, m7['days'], m30['sales'], m30['qty'], velocity30, m30['days'], fm7, fm_uom,
             (inv_position['quantity'] if inv and inv_position and inv_position.get('analysis_usable') else (inv['on_hand_quantity'] if inv else None)),
             (inv_position['uom'] if inv and inv_position and inv_position.get('analysis_usable') else (inv['uom_code'] if inv else None)),
             (inv_position['movement_through_date'] if inv and inv_position and inv_position.get('analysis_usable') else (inv['observation_date'] if inv else None)),
             dos, doh,
             gp_pct, gp7, gpday, sweet, wgpm, cp['price_a'] if cp else None, cp['price_b'] if cp else None, cp['price_c'] if cp else None,
             qc_status,
             (','.join(reasons) if reasons else
              ('NO_POS_SALES_LATEST_28_VALID_DATA_DAYS' if not active_current else None)),
             batch_id),
        )

    return {
        'mode': 'TARGETED_UPSERT_NO_GLOBAL_DELETE',
        'target_family_ids': target_family_ids,
        'target_upcs_requested': target_upcs,
        'target_upcs_refreshed': target_eans,
        'target_rows': len(products),
        'target_active_rows': active_rows,
        'target_ready_rows': active_ready,
        'target_hold_rows': active_hold,
        'target_historical_rows': historical_rows,
        'prior_target_core_holds_resolved': prior_target_core_holds_resolved,
    }



def process_phase3(batch_id: int, progress=None) -> dict[str, Any]:
    def report(stage: str, **payload):
        if progress:
            progress(stage, payload)

    report('PHASE3_CONNECT')
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            # Manual authority tables are bootstrap schema. Ensure them before the
            # Phase 3 business transaction because MySQL DDL implicitly commits
            # and would invalidate the later Quick Check SAVEPOINT.
            ensure_override_table(cur)
            ensure_retirement_table(cur)
            ensure_cost_conversion_table(cur)
            ensure_family_cost_table(cur)
            ensure_article_family_override_table(cur)
            ensure_coverage_backfill_tables(cur)
            ensure_analysis_layer_tables(cur)
            conn.commit()
            report('PHASE3_SCHEMA_READY')
            conn.start_transaction()

            cur.execute('SELECT processing_status FROM ingest_batch WHERE batch_id=%s', (batch_id,))
            b = cur.fetchone()
            if not b:
                raise KeyError(f'Batch {batch_id} not found')
            if b['processing_status'] not in {'PHASE2C_READY', 'PHASE3_QA_HOLD', 'QUICK_CHECK_READY', 'QUICK_CHECK_READY_WITH_HOLDS'}:
                raise RuntimeError(f'Batch {batch_id} is not Phase 2C ready; current status={b["processing_status"]}')

            # Seed/apply user authority before automatic repair so confirmed identities are available
            # to history processing. Reapply the same authority again immediately before publish;
            # automatic repair is never allowed to be the last writer.
            override_result_pre = apply_manual_upc_overrides(cur)
            retirement_result_pre = apply_manual_upc_retirements(cur)
            cost_conversion_result = apply_manual_cost_conversions(cur)
            family_cost_result = apply_manual_family_costs(cur)
            family_subarticle_result = apply_manual_family_subarticles(cur)
            article_family_override_result = apply_manual_article_family_overrides(cur)
            if cost_conversion_result.get('held'):
                raise RuntimeError(
                    'One or more confirmed cost conversions could not be applied: '
                    + str(cost_conversion_result.get('held'))
                )
            if family_cost_result.get('held'):
                raise RuntimeError(
                    'One or more confirmed family costs could not be applied: '
                    + str(family_cost_result.get('held'))
                )
            if family_subarticle_result.get('held'):
                raise RuntimeError(
                    'One or more confirmed family subarticles could not be applied: '
                    + str(family_subarticle_result.get('held'))
                )
            if article_family_override_result.get('held'):
                raise RuntimeError(
                    'One or more confirmed Article->Family overrides could not be applied: '
                    + str(article_family_override_result.get('held'))
                )
            retired_recomputed_issues = retire_recomputed_phase3_issues(cur, batch_id)
            report('PHASE3_MANUAL_AUTHORITY_READY')

            cur.execute(
                """SELECT COALESCE(MAX(run_number),0)+1 AS next_run
                   FROM pipeline_run
                   WHERE batch_id=%s
                     AND pipeline_name='FULL_MYSQL_SEAFOOD'
                     AND stage_name='PHASE3_HISTORY_PRECOMPUTE'""",
                (batch_id,),
            )
            phase3_run_number=int((cur.fetchone() or {}).get('next_run') or 1)
            cur.execute(
                """INSERT INTO pipeline_run (batch_id,pipeline_name,stage_name,run_number,processing_status,code_version)
                   VALUES (%s,'FULL_MYSQL_SEAFOOD','PHASE3_HISTORY_PRECOMPUTE',%s,'STARTED','local-agent-v6.6.0')""",
                (batch_id,phase3_run_number),
            )
            run_id = int(cur.lastrowid)
            counts = {'sales': 0, 'price': 0, 'movement': 0, 'inventory': 0, 'company': 0}
            cur.execute(
                """SELECT file_id,original_filename,source_type,coverage_start_date,coverage_end_date,
                          header_period_start_date,header_period_end_date,report_generated_at,upload_timestamp,filename_date_candidate
                   FROM ingest_file WHERE batch_id=%s ORDER BY file_id""", (batch_id,))
            for f in cur.fetchall():
                st = f['source_type']
                if st == 'sales_by_price_type': counts['sales'] += _process_sales(cur, batch_id, f)
                elif st == 'price_list': counts['price'] += _process_price(cur, batch_id, f)
                elif st == 'movement': counts['movement'] += _process_movement(cur, batch_id, f)
                elif st == 'on_hand': counts['inventory'] += _process_on_hand(cur, batch_id, f)
                elif st == 'frozen_inventory': counts['company'] += _process_company(cur, batch_id, f, 'raw_frozen_inventory')
                elif st == 'tx_seafood_abc_price': counts['company'] += _process_company(cur, batch_id, f, 'raw_tx_seafood_abc_price')
                elif st == 'live_fresh_suggestion': counts['company'] += _process_company(cur, batch_id, f, 'raw_live_fresh_suggestion')

            report('PHASE3_HISTORY_INGESTED', counts=counts)

            # Historical POS RAW backfill (v7.0.300):
            # Older Seafood service rows under POS section 401 were preserved
            # in RAW but skipped by pre-v299 Phase 3 because only department
            # codes present in DEPARTMENT_REGISTRY were accepted. Reprocess the
            # recent analytical horizon with the current 400/401 -> Seafood
            # normalizer and hybrid UPC resolver before any 7D/28D metrics.
            historical_pos_backfill = _backfill_recent_pos_history(
                cur,
                exclude_batch_id=batch_id,
                lookback_days=45,
            )
            report(
                'PHASE3_HISTORICAL_POS_BACKFILL_READY',
                historical_pos_backfill=historical_pos_backfill,
            )

            # Coverage-aware multi-date resolver:
            # - POS range file with exactly one missing daily date -> solve by
            #   period minus known canonical days at EAN + price-type grain.
            # - POS range with 2+ missing dates -> keep period/price-type only.
            # - Multi-date MVT daily slices are resolved dynamically from exact
            #   movement_history.posting_date in source_data_days().
            pos_period_backfill = resolve_pos_period_backfill(cur, batch_id)
            pos_backfill_relinked_pre = relink_pos_backfill(cur)
            report('PHASE3_COVERAGE_BACKFILL_READY')

            # Multi-tab Article Manual repair:
            #  - recognizes formatted barcodes such as `0 6139190220 5`
            #  - recognizes conservative POS-shortened barcode aliases
            #  - consumes explicit UM on roster tabs such as Frozen pack
            #  - never accepts one-digit substitutions as automatic identity
            multitab_manual_repair = repair_article_manual_multitab(cur, batch_id)
            cross_tab_signature_repair = repair_cross_tab_signature(cur, batch_id)

            # Evidence-only product-master repair:
            #  - active sold UPC identity from exact authoritative evidence
            #  - exact UPC-specific Selling UOM evidence
            #  - late family/cost mirror backfill
            active_master_repair = repair_active_product_master(cur, batch_id)

            # v7.0.16: UOM repair is CURRENT-ACTIVE ONLY.
            # A target UPC must have positive POS sales in the latest up-to-28
            # valid completed POS data days. Historical-only UPCs are untouched.
            active_28d_uom_repair = repair_active_28d_uom(cur, batch_id)
            report('PHASE3_IDENTITY_UOM_REPAIR_READY')

            relink_history(cur)
            pos_backfill_relinked = relink_pos_backfill(cur)

            # v7.0.42: normalize historical/current company cost UOM semantics
            # before current-active cost repair. Frozen uses item BUN; Live/Fresh
            # uses the source-level LB rule; TX Seafood ABC is retired.
            company_cost_uom_repair = repair_company_cost_uom_observations(cur)

            # v7.0.19: cost repair/audit is CURRENT-ACTIVE ONLY.
            # Authority:
            #   1) valid 101/107/109 receipt valuation
            #   2) explicit official Live/Fresh/Frozen report cost
            #   3) explicit OH cost + explicit supported cost UOM
            # Historical-only UPCs are not targeted.
            current_active_cost_repair = repair_current_active_cost(cur, batch_id)
            report('PHASE3_COST_REPAIR_READY')

            late_identity = resolve_late_identity_issues(cur, batch_id)
            unmapped_activity = classify_unmapped_sales_activity_scope(cur, batch_id)

            # FINAL USER-AUTHORITY LOCK (v7.0.25): automatic identity/UOM repair runs above.
            # Reapply confirmed overrides and retirements after every automatic repair so a
            # rebuild cannot resurrect a nonexistent UPC or overwrite a user-confirmed UOM.
            override_result = apply_manual_upc_overrides(cur)
            retirement_result = apply_manual_upc_retirements(cur)
            family_cost_result_final = apply_manual_family_costs(cur)
            family_subarticle_result_final = apply_manual_family_subarticles(cur)
            article_family_override_result_final = apply_manual_article_family_overrides(cur)
            if family_cost_result_final.get('held'):
                raise RuntimeError(
                    'One or more confirmed family costs failed final authority lock: '
                    + str(family_cost_result_final.get('held'))
                )
            if family_subarticle_result_final.get('held'):
                raise RuntimeError(
                    'One or more confirmed family subarticles failed final authority lock: '
                    + str(family_subarticle_result_final.get('held'))
                )
            if article_family_override_result_final.get('held'):
                raise RuntimeError(
                    'One or more confirmed Article->Family overrides failed final authority lock: '
                    + str(article_family_override_result_final.get('held'))
                )

            # Current sold-but-unmapped readiness is GLOBAL current state, not
            # source-batch state. Evaluate only after the final user-authority
            # lock so confirmed mappings/retirements are the last identity writer.
            current_active_unmapped_guard = rebuild_current_active_unmapped_sales_guard(
                cur,
                batch_id,
            )

            # Explicit temporary waivers, when configured, apply to the newly
            # recomputed current-state blocker rather than stale source-batch QA.
            temporary_qa_waivers = apply_temporary_identity_waivers(cur, batch_id)

            # v7.0.30 fail-closed product-identity publish guard.
            # Candidate serving rows are built under a SAVEPOINT. A GLOBAL
            # identity blocker rolls back only that candidate snapshot so the
            # previously published Quick Check remains intact.
            cur.execute('SAVEPOINT before_quick_check_publish')
            report('PHASE3_QUICK_CHECK_REBUILD')
            qc_attempt = rebuild_quick_check(cur, batch_id, progress=progress)
            report('PHASE3_ANALYSIS_LAYER_REFRESH')
            seafood_analysis_attempt = refresh_analysis_layer(cur, batch_id, SEAFOOD_DEPT_CODE)
            seafood_analysis_audit = audit_analysis_layer(cur, batch_id, SEAFOOD_DEPT_CODE)
            meat_analysis_attempt = refresh_analysis_layer(cur, batch_id, '300')
            meat_analysis_audit = audit_analysis_layer(cur, batch_id, '300')
            produce_analysis_attempt = refresh_analysis_layer(cur, batch_id, '500')
            produce_analysis_audit = audit_analysis_layer(cur, batch_id, '500')
            report('PHASE3_IDENTITY_AUDIT')
            identity_audit = audit_product_identity(cur)
            identity_guard_pass = bool(identity_audit.get('pass'))
            identity_guard_blockers = list(identity_audit.get('blockers') or [])
            analysis_guard_pass = bool(seafood_analysis_audit.get('pass'))
            meat_analysis_pass = bool(meat_analysis_audit.get('pass'))
            produce_analysis_pass = bool(produce_analysis_audit.get('pass'))
            serving_preserved = False

            if identity_guard_pass and analysis_guard_pass:
                cur.execute('RELEASE SAVEPOINT before_quick_check_publish')
                qc = qc_attempt
            else:
                cur.execute('ROLLBACK TO SAVEPOINT before_quick_check_publish')
                cur.execute('RELEASE SAVEPOINT before_quick_check_publish')
                serving_preserved = True
                if not identity_guard_pass:
                    _record_product_identity_guard_issues(cur, batch_id, identity_audit)
                qc = {
                    'rows': 0,
                    'ready': 0,
                    'hold': 0,
                    'serving_rows_total': 0,
                    'historical_rows': 0,
                    'publish_blocked': True,
                    'previous_serving_preserved': True,
                }

            analysis_layer = {
                'seafood': {
                    'refresh': seafood_analysis_attempt,
                    'audit': seafood_analysis_audit,
                    'pass': analysis_guard_pass,
                    'gate_role': 'PRIMARY_READY_GATE',
                },
                'meat': {
                    'refresh': meat_analysis_attempt,
                    'audit': meat_analysis_audit,
                    'pass': meat_analysis_pass,
                    'gate_role': 'DEPARTMENT_LOCAL_STATUS',
                },
                'produce': {
                    'refresh': produce_analysis_attempt,
                    'audit': produce_analysis_audit,
                    'pass': produce_analysis_pass,
                    'gate_role': 'DEPARTMENT_LOCAL_STATUS',
                    'inventory_policy': 'OH_SUPPORTING_ONLY_DO_NOT_DRIVE_DECISIONS_ALONE',
                },
                'policy': 'FAIL_CLOSED_PRESERVE_PREVIOUS_SERVING',
                'previous_serving_preserved': serving_preserved,
            }

            product_identity_guard = {
                'pass': identity_guard_pass,
                'policy': 'FAIL_CLOSED_PRESERVE_PREVIOUS_SERVING',
                'blocking_count': len(identity_guard_blockers),
                'summary': identity_audit.get('summary'),
                'blockers': identity_guard_blockers,
                'warning_count': len(identity_audit.get('warnings') or []),
                'serving_hold_count': len(identity_audit.get('serving_holds') or []),
                'previous_serving_preserved': serving_preserved,
                'candidate_quick_check': qc_attempt,
            }

            # Batch blockers and serving-row QA are different scopes.
            # QUICK_CHECK_CORE_FIELD_MISSING affects only the individual serving UPC:
            # it must not make an otherwise valid POS/MVT ingest batch fail.
            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM qa_phase3_issue
                   WHERE batch_id=%s
                     AND issue_status='OPEN'
                     AND UPPER(severity) IN ('HIGH','CRITICAL')
                     AND issue_code<>'QUICK_CHECK_CORE_FIELD_MISSING'""",
                (batch_id,),
            )
            blocking = int(cur.fetchone()['c'])

            if (not identity_guard_pass) or (not analysis_guard_pass) or blocking > 0 or qc['rows'] == 0:
                status = 'PHASE3_QA_HOLD'
            elif qc['hold'] > 0:
                status = 'QUICK_CHECK_READY_WITH_HOLDS'
            else:
                status = 'QUICK_CHECK_READY'
            report('PHASE3_FINALIZE', blocking=blocking, status=status)
            cur.execute(
                """INSERT INTO phase3_batch_result
                   (batch_id,sales_rows,price_rows,movement_rows,inventory_rows,company_price_rows,
                    quick_check_rows,quick_check_ready_rows,quick_check_hold_rows,blocking_issue_count,result_status,detail_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE sales_rows=VALUES(sales_rows),price_rows=VALUES(price_rows),movement_rows=VALUES(movement_rows),
                    inventory_rows=VALUES(inventory_rows),company_price_rows=VALUES(company_price_rows),quick_check_rows=VALUES(quick_check_rows),
                    quick_check_ready_rows=VALUES(quick_check_ready_rows),quick_check_hold_rows=VALUES(quick_check_hold_rows),
                    blocking_issue_count=VALUES(blocking_issue_count),result_status=VALUES(result_status),detail_json=VALUES(detail_json),
                    updated_at=CURRENT_TIMESTAMP(6)""",
                (batch_id, counts['sales'], counts['price'], counts['movement'], counts['inventory'], counts['company'],
                 qc['rows'], qc['ready'], qc['hold'], blocking, status, json.dumps({'history_counts': counts, 'late_identity_resolution': late_identity, 'manual_overrides_pre_repair': override_result_pre, 'manual_retirements_pre_repair': retirement_result_pre, 'manual_cost_conversions': cost_conversion_result, 'manual_family_costs': family_cost_result, 'manual_family_subarticles': family_subarticle_result, 'manual_family_costs_final': family_cost_result_final, 'manual_family_subarticles_final': family_subarticle_result_final, 'manual_overrides': override_result, 'manual_retirements': retirement_result, 'retired_recomputed_issues': retired_recomputed_issues, 'unmapped_activity_scope': unmapped_activity,
                  'current_active_unmapped_sales_guard': current_active_unmapped_guard,
                  'active_product_master_repair': active_master_repair,
                  'article_manual_multitab_repair': multitab_manual_repair,
                  'cross_tab_signature_repair': cross_tab_signature_repair,
                  'temporary_qa_waivers': temporary_qa_waivers,
                  'active_28d_uom_repair': active_28d_uom_repair,
                  'company_cost_uom_repair': company_cost_uom_repair,
                  'current_active_cost_repair': current_active_cost_repair,
                  'coverage_backfill': pos_period_backfill,
                  'pos_backfill_relinked_pre_repair': pos_backfill_relinked_pre,
                  'pos_backfill_relinked': pos_backfill_relinked,
                  'product_identity_guard': product_identity_guard,
                  'analysis_layer': analysis_layer}, default=str)),
            )
            cur.execute('UPDATE ingest_batch SET processing_status=%s,completed_at=CURRENT_TIMESTAMP(6) WHERE batch_id=%s', (status, batch_id))
            cur.execute(
                """UPDATE pipeline_run SET processing_status=%s,completed_at=CURRENT_TIMESTAMP(6),rows_inserted=%s,error_count=%s,detail_json=%s
                   WHERE pipeline_run_id=%s""",
                ('COMPLETED' if status in {'QUICK_CHECK_READY','QUICK_CHECK_READY_WITH_HOLDS'} else 'FAILED_QA',
                 sum(counts.values()) + qc['rows'], blocking,
                 json.dumps({
                     'counts': counts,
                     'quick_check': qc,
                     'product_identity_guard': product_identity_guard,
                     'analysis_layer': analysis_layer,
                 }, default=str), run_id),
            )
            conn.commit()
            return {'batch_id': batch_id, 'status': status, **counts, 'quick_check': qc, 'late_identity_resolution': late_identity, 'manual_overrides_pre_repair': override_result_pre, 'manual_retirements_pre_repair': retirement_result_pre, 'manual_cost_conversions': cost_conversion_result, 'manual_family_costs': family_cost_result, 'manual_family_subarticles': family_subarticle_result, 'manual_overrides': override_result, 'manual_retirements': retirement_result, 'retired_recomputed_issues': retired_recomputed_issues, 'unmapped_activity_scope': unmapped_activity,
                    'current_active_unmapped_sales_guard': current_active_unmapped_guard,
                    'active_product_master_repair': active_master_repair,
                    'article_manual_multitab_repair': multitab_manual_repair,
                    'cross_tab_signature_repair': cross_tab_signature_repair,
                    'temporary_qa_waivers': temporary_qa_waivers,
                    'active_28d_uom_repair': active_28d_uom_repair,
                    'company_cost_uom_repair': company_cost_uom_repair,
                    'current_active_cost_repair': current_active_cost_repair,
                    'coverage_backfill': pos_period_backfill,
                    'pos_backfill_relinked_pre_repair': pos_backfill_relinked_pre,
                    'pos_backfill_relinked': pos_backfill_relinked,
                    'product_identity_guard': product_identity_guard,
                    'analysis_layer': analysis_layer,
                    'quick_check_attempt': qc_attempt,
                    'blocking_issues': blocking}
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def audit_phase3(batch_id: int) -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT * FROM phase3_batch_result WHERE batch_id=%s', (batch_id,))
        result = cur.fetchone()
        if not result:
            return {'batch_id': batch_id, 'pass': False, 'reason': 'Phase 3 has not run.'}
        cur.execute(
            """SELECT issue_id,severity,issue_code,entity_type,entity_key,issue_summary,detail_json
               FROM qa_phase3_issue WHERE batch_id=%s AND issue_status='OPEN'
               ORDER BY FIELD(UPPER(severity),'CRITICAL','HIGH','MEDIUM','LOW'),issue_id""", (batch_id,))
        issues = cur.fetchall(); cur.close()
    blocking = [
        x for x in issues
        if str(x['severity']).upper() in {'HIGH', 'CRITICAL'}
        and x['issue_code'] != 'QUICK_CHECK_CORE_FIELD_MISSING'
    ]
    serving_issues = [x for x in issues if x['issue_code'] == 'QUICK_CHECK_CORE_FIELD_MISSING']
    return {
        'batch_id': batch_id,
        'pass': result['result_status'] in {'QUICK_CHECK_READY','QUICK_CHECK_READY_WITH_HOLDS'} and not blocking,
        'result': result,
        'blocking_issues': blocking,
        'serving_issues': serving_issues,
        'all_open_issues': issues,
    }
