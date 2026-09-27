from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from db import db_conn
from data_coverage import source_data_days, coverage_summary
from manual_overrides import (
    ensure_override_table,
    ensure_retirement_table,
    apply_manual_upc_overrides,
    apply_manual_upc_retirements,
)
from active_product_repair import repair_active_product_master
from article_manual_multitab_repair import repair_article_manual_multitab
from cross_tab_signature_repair import repair_cross_tab_signature
from temporary_qa_waivers import apply_temporary_identity_waivers
from active_28d_uom_repair import repair_active_28d_uom
from current_active_cost_repair import repair_current_active_cost
from product_identity_audit import audit_product_identity

PRICE_TYPE_PRIORITY = {'IN STORE': 4, 'INSTORE': 4, 'SALE': 3, 'TPR': 2, 'REG': 1, 'REGULAR': 1}
SALES_COLS = {
    'REG': ('E', 'F'),
    'IN STORE': ('G', 'H'),
    'TPR': ('I', 'J'),
    'SALE': ('K', 'L'),
}
RECEIPT_MOVEMENTS = {'101', '107', '109'}
FAMILY_SALE_MOVEMENTS = {'251', '252'}
SEAFOOD_DEPT_CODE = '400'


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


def _numeric_key(v: str | None) -> str | None:
    if not v or not re.fullmatch(r'\d+', v):
        return None
    k = v.lstrip('0')
    return k or '0'


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
    return int(r['upc_id']) if r else None


def _upc_identity_ready(cur, ean: str | None) -> bool:
    upc_id = _find_upc_id(cur, ean)
    if upc_id is None:
        return False
    cur.execute(
        """SELECT 1
           FROM bridge_article_upc bau
           JOIN bridge_article_family baf ON baf.article_id=bau.article_id
             AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           WHERE bau.upc_id=%s AND bau.mapping_status='CONFIRMED' AND bau.is_primary=TRUE
             AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
           LIMIT 1""",
        (upc_id,),
    )
    return bool(cur.fetchone())


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
           ORDER BY baf.article_family_id DESC LIMIT 1""",
        (article_number,),
    )
    r = cur.fetchone()
    return (int(r['article_id']), int(r['family_id']) if r and r['family_id'] is not None else None) if r else (None, None)


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
                current_dept = a
                continue
            if current_dept != SEAFOOD_DEPT_CODE:
                continue
            ean = a
            if not ean or not b:
                continue
            # Product sales rows have TOTAL amount/qty or at least one price-type amount/qty.
            if not any(_num(p.get(c)) is not None for pair in SALES_COLS.values() for c in pair):
                continue
            upc_id = _find_upc_id(cur, ean)
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
                _issue(cur, batch_id, 'SOLD_UPC_UNMAPPED', 'UPC', ean,
                       f'POS sold quantity exists for Seafood UPC {ean}, but no confirmed UPC identity mapping exists.',
                       'HIGH', f['file_id'], sh['sheet_id'], 'raw_sales_by_price_type', rr['raw_id'], {'description': b})
    return inserted


def _process_price(cur, batch_id: int, f: dict[str, Any]) -> int:
    inserted = 0
    cur.execute('SELECT sheet_id FROM ingest_sheet WHERE file_id=%s ORDER BY sheet_index', (f['file_id'],))
    for sh in cur.fetchall():
        cur.execute("SELECT raw_id,source_row_number,raw_payload FROM raw_price_list WHERE sheet_id=%s ORDER BY source_row_number", (sh['sheet_id'],))
        rows = cur.fetchall()
        snapshot = _printed_timestamp(rows) or f.get('report_generated_at') or f.get('upload_timestamp') or datetime.now()
        current_dept = None
        for rr in rows:
            p = _j(rr['raw_payload'])
            a_txt = (_text(p.get('A')) or '')
            if 'SUBDEPT' in a_txt.upper():
                current_dept = _id(p.get('B'))
                continue
            if current_dept != SEAFOOD_DEPT_CODE:
                continue
            ean = _id(p.get('A'))
            desc = _text(p.get('B'))
            if not ean or not desc:
                continue
            price = _num(p.get('J'))
            price_qty = _num(p.get('K'))
            ptype = (_text(p.get('P')) or '').upper()
            if ptype not in {'REG', 'TPR', 'SALE', 'IN STORE', 'INSTORE'}:
                continue
            since = _date(p.get('Q'))
            upc_id = _find_upc_id(cur, ean)
            cur.execute(
                """INSERT INTO price_list_observation
                   (batch_id,file_id,sheet_id,raw_id,source_row_number,ean_upc,upc_id,description,
                    configured_price,price_quantity,price_type,source_since_date,snapshot_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE upc_id=VALUES(upc_id),configured_price=VALUES(configured_price),
                    price_quantity=VALUES(price_quantity),price_type=VALUES(price_type),source_since_date=VALUES(source_since_date),snapshot_at=VALUES(snapshot_at)""",
                (batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], rr['source_row_number'], ean, upc_id, desc,
                 price, price_qty, 'IN STORE' if ptype == 'INSTORE' else ptype, since, snapshot),
            )
            inserted += 1
    return inserted


def _process_movement(cur, batch_id: int, f: dict[str, Any]) -> int:
    inserted = 0
    cur.execute('SELECT sheet_id FROM ingest_sheet WHERE file_id=%s ORDER BY sheet_index', (f['file_id'],))
    for sh in cur.fetchall():
        cur.execute("SELECT raw_id,source_row_number,raw_payload FROM raw_movement WHERE sheet_id=%s ORDER BY source_row_number", (sh['sheet_id'],))
        for rr in cur.fetchall():
            p = _j(rr['raw_payload'])
            article_num = _id(p.get('C'))
            mvt = _id(p.get('G'))
            posting = _date(p.get('H'))
            desc = _text(p.get('D'))
            cost_center = _text(p.get('V'))
            if not article_num or not mvt or not posting:
                continue
            article_id, family_id = _find_article(cur, article_num)
            seafood_tag = bool(cost_center and 'SEAFOOD' in cost_center.upper())
            if not seafood_tag and family_id is None:
                continue
            if seafood_tag and family_id is None:
                _issue(cur, batch_id, 'SEAFOOD_MOVEMENT_ARTICLE_UNMAPPED', 'ARTICLE', article_num,
                       f'Seafood movement exists for Article {article_num}, but it has no confirmed Family mapping.',
                       'HIGH', f['file_id'], sh['sheet_id'], 'raw_movement', rr['raw_id'], {'movement_type': mvt, 'description': desc})
            entry_qty = _num(p.get('I'))
            entry_uom = (_text(p.get('J')) or '').upper() or None
            base_qty = _num(p.get('K'))
            base_uom = (_text(p.get('L')) or '').upper() or None
            amount = _num(p.get('M'))
            sales_value = _num(p.get('N'))
            art_doc = _text(p.get('Q'))
            po = _text(p.get('R'))
            vendor = _text(p.get('S'))
            cur.execute(
                """INSERT INTO movement_history
                   (batch_id,file_id,sheet_id,raw_id,source_row_number,article_number,article_id,family_id,description,
                    movement_type,posting_date,entry_quantity,entry_uom_code,base_quantity,base_uom_code,
                    amount_local_currency,sales_value,article_document,purchase_order,vendor_code,cost_center)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE article_id=VALUES(article_id),family_id=VALUES(family_id)""",
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
                if amount not in (None, 0) and base_qty not in (None, 0) and base_uom_id is not None:
                    unit_cost = abs(amount / base_qty)
                    cur.execute("SELECT cost_observation_id FROM article_cost_observation WHERE raw_table_name='raw_movement' AND raw_id=%s LIMIT 1", (rr['raw_id'],))
                    if not cur.fetchone():
                        cur.execute(
                            """INSERT INTO article_cost_observation
                               (article_id,family_id,cost_amount,currency_code,cost_uom_id,source_type,movement_type,business_date,
                                observed_at,cost_status,confidence,base_uom_id,cost_per_base_uom,
                                batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
                               VALUES (%s,%s,%s,'USD',%s,'MOVEMENT_RECEIPT_VALUATION',%s,%s,%s,'OBSERVED',1.0,%s,%s,
                                       %s,%s,%s,'raw_movement',%s,%s)""",
                            (article_id, family_id, unit_cost, base_uom_id, mvt, posting, datetime.combine(posting, datetime.min.time()),
                             base_uom_id, unit_cost, batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], rr['source_row_number']),
                        )
            if family_id is not None and mvt in FAMILY_SALE_MOVEMENTS and base_qty is not None:
                net_sold = -base_qty
                cur.execute(
                    """INSERT INTO family_movement_observation
                       (batch_id,file_id,sheet_id,raw_id,family_id,article_id,movement_type,posting_date,
                        base_quantity_signed,net_sold_quantity,base_uom_code)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE family_id=VALUES(family_id),article_id=VALUES(article_id),
                        net_sold_quantity=VALUES(net_sold_quantity),base_uom_code=VALUES(base_uom_code)""",
                    (batch_id, f['file_id'], sh['sheet_id'], rr['raw_id'], family_id, article_id, mvt, posting, base_qty, net_sold, base_uom),
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


def _pick(hmap: dict[str, str], aliases: Iterable[str]) -> str | None:
    norm_alias = [_norm_header(a) for a in aliases]
    for a in norm_alias:
        if a in hmap:
            return hmap[a]
    for h, c in hmap.items():
        if any(a and a in h for a in norm_alias):
            return c
    return None


def _process_on_hand(cur, batch_id: int, f: dict[str, Any]) -> int:
    inserted = 0
    cur.execute('SELECT sheet_id,header_row_number FROM ingest_sheet WHERE file_id=%s ORDER BY sheet_index', (f['file_id'],))
    for sh in cur.fetchall():
        hmap = _sheet_header_map(cur, 'raw_on_hand', sh['sheet_id'], sh['header_row_number'])
        c_article = _pick(hmap, ['Article', 'Article Number'])
        c_upc = _pick(hmap, ['UPC', 'EAN', 'Barcode', 'Sales Set'])
        c_oh = _pick(hmap, ['On Hand', 'OH', 'Stock', 'Quantity'])
        c_uom = _pick(hmap, ['UOM', 'Unit'])
        c_date = _pick(hmap, ['Date', 'Inventory Date', 'Count Date'])
        if not c_oh or (not c_article and not c_upc):
            continue
        cur.execute('SELECT raw_id,source_row_number,raw_payload FROM raw_on_hand WHERE sheet_id=%s AND source_row_number>%s ORDER BY source_row_number',
                    (sh['sheet_id'], sh['header_row_number'] or 0))
        for rr in cur.fetchall():
            p = _j(rr['raw_payload'])
            article_num = _id(p.get(c_article)) if c_article else None
            ean = _id(p.get(c_upc)) if c_upc else None
            qty = _num(p.get(c_oh))
            if qty is None or (not article_num and not ean):
                continue
            article_id, family_id = _find_article(cur, article_num)
            upc_id = _find_upc_id(cur, ean)
            obs_date = _date(p.get(c_date)) if c_date else (f.get('coverage_end_date') or f.get('filename_date_candidate'))
            uom = (_text(p.get(c_uom)) or '').upper() or None if c_uom else None
            cur.execute(
                """INSERT INTO inventory_observation
                   (batch_id,file_id,sheet_id,raw_id,source_row_number,observation_date,article_number,article_id,family_id,
                    ean_upc,upc_id,on_hand_quantity,uom_code,source_type)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ON_HAND')
                   ON DUPLICATE KEY UPDATE article_id=VALUES(article_id),family_id=VALUES(family_id),upc_id=VALUES(upc_id),
                    on_hand_quantity=VALUES(on_hand_quantity),uom_code=VALUES(uom_code),observation_date=VALUES(observation_date)""",
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
        c_uom = _pick(hmap, ['Cost UOM', 'UOM', 'Unit'])
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
            cost_uom = (_text(p.get(c_uom)) or '').upper() or None if c_uom else None
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
            if cost is not None and article_id is not None and cost_uom:
                uid = _uom_id(cur, cost_uom)
                if uid:
                    cur.execute("SELECT cost_observation_id FROM article_cost_observation WHERE raw_table_name=%s AND raw_id=%s LIMIT 1", (raw_table, rr['raw_id']))
                    if not cur.fetchone():
                        cur.execute(
                            """INSERT INTO article_cost_observation
                               (article_id,family_id,cost_amount,currency_code,cost_uom_id,source_type,business_date,
                                cost_status,confidence,batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number)
                               VALUES (%s,%s,%s,'USD',%s,%s,%s,'OBSERVED',1.0,%s,%s,%s,%s,%s,%s)""",
                            (article_id, family_id, cost, uid, f['source_type'].upper() + '_OFFICIAL_COST', obs_date,
                             batch_id, f['file_id'], sh['sheet_id'], raw_table, rr['raw_id'], rr['source_row_number']),
                        )
    return inserted



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
    'HISTORICAL_SOLD_UPC_UNMAPPED',
    'SEAFOOD_MOVEMENT_ARTICLE_UNMAPPED',
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
    cur.execute("""UPDATE sales_period_observation s JOIN selling_upc u ON u.ean_upc=s.ean_upc
                   SET s.upc_id=u.upc_id WHERE s.upc_id IS NULL""")
    cur.execute("""UPDATE price_list_observation p JOIN selling_upc u ON u.ean_upc=p.ean_upc
                   SET p.upc_id=u.upc_id WHERE p.upc_id IS NULL""")
    cur.execute("""UPDATE movement_history m JOIN article a ON a.article_number=m.article_number
                   LEFT JOIN bridge_article_family baf ON baf.article_id=a.article_id AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
                     AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
                   SET m.article_id=a.article_id, m.family_id=COALESCE(m.family_id,baf.family_id)
                   WHERE m.article_id IS NULL OR m.family_id IS NULL""")
    cur.execute("""UPDATE inventory_observation i JOIN selling_upc u ON u.ean_upc=i.ean_upc
                   SET i.upc_id=u.upc_id WHERE i.upc_id IS NULL AND i.ean_upc IS NOT NULL""")
    cur.execute("""UPDATE company_price_observation c JOIN selling_upc u ON u.ean_upc=c.ean_upc
                   SET c.upc_id=u.upc_id WHERE c.upc_id IS NULL AND c.ean_upc IS NOT NULL""")

    # Second pass: resolve leading-zero-equivalent UPCs that cannot match by exact string.
    for table in ('sales_period_observation','price_list_observation','inventory_observation','company_price_observation'):
        cur.execute(f"SELECT DISTINCT ean_upc FROM {table} WHERE upc_id IS NULL AND ean_upc IS NOT NULL")
        for row in cur.fetchall():
            ean = row['ean_upc']
            upc_id = _find_upc_id(cur, ean)
            if upc_id is not None:
                cur.execute(f"UPDATE {table} SET upc_id=%s WHERE upc_id IS NULL AND ean_upc=%s", (upc_id, ean))


def resolve_late_identity_issues(cur, batch_id: int) -> dict[str, int]:
    """Close only linkage QA that late Article Manual/PI identity evidence has actually repaired."""
    resolved_sales = 0
    resolved_movement = 0
    cur.execute(
        """SELECT issue_id,issue_code,entity_key FROM qa_phase3_issue
           WHERE batch_id=%s AND issue_status='OPEN'
             AND issue_code IN ('SOLD_UPC_UNMAPPED','HISTORICAL_SOLD_UPC_UNMAPPED','SEAFOOD_MOVEMENT_ARTICLE_UNMAPPED')""",
        (batch_id,),
    )
    for issue in cur.fetchall():
        code = issue['issue_code']
        key = str(issue['entity_key'])
        repaired = False
        if code in {'SOLD_UPC_UNMAPPED','HISTORICAL_SOLD_UPC_UNMAPPED'}:
            repaired = _upc_identity_ready(cur, key)
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
            if code in {'SOLD_UPC_UNMAPPED','HISTORICAL_SOLD_UPC_UNMAPPED'}:
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
    """Return SQL predicate + params for exact or leading-zero-equivalent numeric UPC."""
    key = _numeric_key(ean)
    if key is None:
        return f"{column}=%s", (ean,)
    return (
        f"({column}=%s OR "
        f"({column} REGEXP '^[0-9]+$' AND TRIM(LEADING '0' FROM {column})=%s))",
        (ean, key),
    )


def _active_selling_evidence_for_unmapped(cur, ean: str, batch_id: int) -> dict[str, Any]:
    """Current activity scope for an unmapped historical UPC.

    v7.0.10 rule:
      - Positive sales on the latest up-to-28 VALID POS data days => ACTIVE_SELLING.
      - Everything else => HISTORICAL_ONLY for CURRENT production readiness.

    A configured Price List price by itself is NOT active-selling evidence.
    Historical sales and lineage are preserved.
    """
    completed_through = date.today() - timedelta(days=1)
    pos_days = source_data_days(
        cur, 'sales_by_price_type', limit=28,
        include_batch_id=batch_id, up_to=completed_through
    )
    file_ids = [int(x['file_id']) for x in pos_days]

    recent_qty = Decimal('0')
    recent_latest = None
    if file_ids:
        placeholders = ','.join(['%s'] * len(file_ids))
        pred, pred_params = _upc_match_sql('ean_upc', ean)
        cur.execute(
            f"""SELECT COALESCE(SUM(sold_quantity),0) AS q,
                       MAX(period_end_date) AS latest_date
                FROM sales_period_observation
                WHERE temporal_grain='SINGLE_DATE'
                  AND file_id IN ({placeholders})
                  AND {pred}""",
            (*file_ids, *pred_params),
        )
        row = cur.fetchone()
        if row:
            recent_qty = Decimal(str(row['q'] or 0))
            recent_latest = row['latest_date']

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
            cur.execute(
                """UPDATE qa_phase3_issue
                   SET severity='HIGH',detail_json=%s
                   WHERE issue_id=%s""",
                (json.dumps(detail, ensure_ascii=False, default=str), issue['issue_id']),
            )
            counts['active_blocking'] += 1

    return counts


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
    # Authority: valid receipt valuation first, then official Live/Fresh/Frozen report cost.
    cur.execute(
        """SELECT co.cost_per_base_uom,co.cost_amount,co.business_date,co.source_type,
                  bu.uom_code AS base_uom, cu.uom_code AS cost_uom
           FROM article_cost_observation co
           LEFT JOIN dim_uom bu ON bu.uom_id=co.base_uom_id
           LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
           WHERE co.family_id=%s AND co.source_type='MOVEMENT_RECEIPT_VALUATION'
             AND co.cost_status NOT IN ('REJECTED','SUPERSEDED')
             AND COALESCE(co.cost_per_base_uom,co.cost_amount)>0
           ORDER BY co.business_date DESC, co.cost_observation_id DESC LIMIT 1""",
        (family_id,),
    )
    r = cur.fetchone()
    if r:
        return {'cost_per_base': r['cost_per_base_uom'] or r['cost_amount'], 'date': r['business_date'],
                'source': r['source_type'], 'base_uom': r['base_uom'] or r['cost_uom']}
    cur.execute(
        """SELECT co.cost_amount,co.business_date,co.source_type,cu.uom_code AS cost_uom
           FROM article_cost_observation co
           LEFT JOIN dim_uom cu ON cu.uom_id=co.cost_uom_id
           WHERE co.family_id=%s AND co.source_type IN ('FROZEN_INVENTORY_OFFICIAL_COST','TX_SEAFOOD_ABC_PRICE_OFFICIAL_COST','LIVE_FRESH_SUGGESTION_OFFICIAL_COST')
             AND co.cost_status NOT IN ('REJECTED','SUPERSEDED') AND co.cost_amount>0
           ORDER BY co.business_date DESC, co.cost_observation_id DESC LIMIT 1""",
        (family_id,),
    )
    r = cur.fetchone()
    if r:
        return {'cost_per_base': r['cost_amount'], 'date': r['business_date'], 'source': r['source_type'], 'base_uom': r['cost_uom']}

    # Third authority: explicit cost observed in an On-Hand source.
    # This is used only when the raw OH row contains both a positive explicit
    # cost and an explicit supported cost-UOM. Generic inventory UOM is never
    # silently treated as cost UOM.
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
        return {'cost_per_base': r['cost_amount'], 'date': r['business_date'], 'source': r['source_type'], 'base_uom': r['cost_uom']}
    return None


def _current_price(cur, upc_id: int) -> dict[str, Any] | None:
    # Latest point-in-time Price List vs latest period-level POS evidence.
    cur.execute(
        """SELECT snapshot_at FROM price_list_observation WHERE upc_id=%s AND configured_price>0
           ORDER BY snapshot_at DESC LIMIT 1""", (upc_id,))
    pr = cur.fetchone()
    price_snapshot = pr['snapshot_at'] if pr else None
    config = None
    if price_snapshot:
        cur.execute(
            """SELECT configured_price,price_type,snapshot_at FROM price_list_observation
               WHERE upc_id=%s AND snapshot_at=%s AND configured_price>0""", (upc_id, price_snapshot))
        rows = cur.fetchall()
        if rows:
            rows.sort(key=lambda x: PRICE_TYPE_PRIORITY.get(str(x['price_type']).upper(), 0), reverse=True)
            config = rows[0]
    cur.execute('SELECT MAX(period_end_date) AS d FROM sales_period_observation WHERE upc_id=%s AND sold_quantity<>0', (upc_id,))
    sr = cur.fetchone(); sales_date = sr['d'] if sr else None
    pos = None
    if sales_date:
        cur.execute(
            """SELECT SUM(sales_amount) AS s,SUM(sold_quantity) AS q,COUNT(DISTINCT price_type) AS types,
                      GROUP_CONCAT(DISTINCT price_type ORDER BY price_type SEPARATOR '+') AS price_types
               FROM sales_period_observation WHERE upc_id=%s AND period_end_date=%s""", (upc_id, sales_date))
        r = cur.fetchone()
        if r and r['q'] not in (None, 0):
            pos = {'price': r['s'] / r['q'], 'type': r['price_types'] if r['types'] == 1 else 'MIXED', 'date': sales_date}
    price_date = price_snapshot.date() if price_snapshot else None
    # If same date, Price List is a point-in-time snapshot and outranks period average sold price.
    if config and (not pos or price_date >= pos['date']):
        return {'price': config['configured_price'], 'type': config['price_type'], 'source': 'PRICE_LIST', 'date': price_date}
    if pos:
        return {'price': pos['price'], 'type': pos['type'], 'source': 'POS_PERIOD_AVG', 'date': pos['date']}
    return None


def _sales_metrics(cur, upc_id: int, data_days: list[dict[str, Any]]) -> dict[str, Any]:
    """Metrics across the latest valid POS data days, not calendar days.

    A UPC with no row on a valid POS day is a verified zero sale for that day.
    A calendar day without a valid POS file is absent from the denominator entirely.
    """
    if not data_days:
        return {'sales': Decimal('0'), 'qty': Decimal('0'), 'days': 0, 'start': None, 'end': None}
    file_ids = [int(x['file_id']) for x in data_days]
    placeholders = ','.join(['%s'] * len(file_ids))
    cur.execute(
        f"""SELECT COALESCE(SUM(sales_amount),0) AS s,COALESCE(SUM(sold_quantity),0) AS q
            FROM sales_period_observation
            WHERE upc_id=%s AND temporal_grain='SINGLE_DATE' AND file_id IN ({placeholders})""",
        tuple([upc_id] + file_ids),
    )
    r = cur.fetchone()
    dates = [x['date'] for x in data_days]
    return {
        'sales': r['s'] or Decimal('0'),
        'qty': r['q'] or Decimal('0'),
        'days': len(data_days),
        'start': min(dates),
        'end': max(dates),
    }


def _family_movement_metrics(cur, family_id: int, data_days: list[dict[str, Any]]) -> tuple[Decimal | None, str | None, int]:
    """Family movement over valid MVT data days.

    No family rows on a valid MVT day means verified zero movement. No MVT file means
    the day is missing and therefore not part of the rolling window.
    """
    if not data_days:
        return None, None, 0
    file_ids = [int(x['file_id']) for x in data_days]
    placeholders = ','.join(['%s'] * len(file_ids))
    cur.execute(
        f"""SELECT base_uom_code,SUM(net_sold_quantity) AS q
            FROM family_movement_observation
            WHERE family_id=%s AND file_id IN ({placeholders})
            GROUP BY base_uom_code""",
        tuple([family_id] + file_ids),
    )
    rows = [r for r in cur.fetchall() if r['q'] is not None]
    if not rows:
        return Decimal('0'), None, len(data_days)
    if len(rows) == 1:
        return rows[0]['q'], rows[0]['base_uom_code'], len(data_days)
    return None, None, len(data_days)


def _latest_inventory(cur, upc_id: int, family_id: int | None) -> dict[str, Any] | None:
    cur.execute(
        """SELECT on_hand_quantity,uom_code,observation_date FROM inventory_observation
           WHERE upc_id=%s AND on_hand_quantity IS NOT NULL
           ORDER BY observation_date DESC, inventory_observation_id DESC LIMIT 1""", (upc_id,))
    r = cur.fetchone()
    if r:
        return r
    if family_id is not None:
        cur.execute(
            """SELECT on_hand_quantity,uom_code,observation_date FROM inventory_observation
               WHERE family_id=%s AND upc_id IS NULL AND on_hand_quantity IS NOT NULL
               ORDER BY observation_date DESC, inventory_observation_id DESC LIMIT 1""", (family_id,))
        return cur.fetchone()
    return None


def _company_prices(cur, upc_id: int, family_id: int | None) -> dict[str, Any] | None:
    if family_id is None:
        cur.execute("SELECT * FROM company_price_observation WHERE upc_id=%s ORDER BY observation_date DESC,company_price_observation_id DESC LIMIT 1", (upc_id,))
    else:
        cur.execute("SELECT * FROM company_price_observation WHERE (upc_id=%s OR family_id=%s) ORDER BY observation_date DESC,company_price_observation_id DESC LIMIT 1", (upc_id, family_id))
    return cur.fetchone()


def _historical_sweet_spot(cur, upc_id: int, family_id: int, factor: Decimal | None,
                           data_days: list[dict[str, Any]]) -> Decimal | None:
    if factor is None or not data_days:
        return None
    file_ids = [int(x['file_id']) for x in data_days]
    placeholders = ','.join(['%s'] * len(file_ids))
    cur.execute(
        f"""SELECT period_end_date,SUM(sales_amount) s,SUM(sold_quantity) q
            FROM sales_period_observation
            WHERE upc_id=%s AND temporal_grain='SINGLE_DATE' AND file_id IN ({placeholders})
            GROUP BY period_end_date HAVING SUM(sold_quantity)<>0 ORDER BY period_end_date""",
        tuple([upc_id] + file_ids),
    )
    daily = cur.fetchall()
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
               ORDER BY CASE WHEN source_type='MOVEMENT_RECEIPT_VALUATION' THEN 1 ELSE 2 END,
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


def rebuild_quick_check(cur, batch_id: int) -> dict[str, Any]:
    calendar_today = date.today()
    completed_through = calendar_today - timedelta(days=1)

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
    for p in products:
        upc_id = int(p['upc_id']); family_id = int(p['family_id'])
        m7 = _sales_metrics(cur, upc_id, pos_days_7)
        m28 = _sales_metrics(cur, upc_id, pos_days_28)
        m30 = _sales_metrics(cur, upc_id, pos_days_30)
        price = _current_price(cur, upc_id)
        cost = _latest_cost(cur, family_id)
        cur.execute('SELECT MAX(posting_date) AS d FROM receiving_observation WHERE family_id=%s AND movement_type IN (\'101\',\'107\',\'109\')', (family_id,))
        rr = cur.fetchone(); last_receipt = rr['d'] if rr else None
        factor = Decimal(str(p['base_qty_per_selling_unit'])) if p['base_qty_per_selling_unit'] is not None else None
        selling_uom = p['selling_uom']; base_uom = p['base_uom']
        if factor is None and selling_uom and base_uom and selling_uom == base_uom:
            factor = Decimal('1')
        cost_sell = None
        if cost and factor is not None and cost.get('base_uom') and base_uom and str(cost['base_uom']).upper() == str(base_uom).upper():
            cost_sell = Decimal(str(cost['cost_per_base'])) * factor
        fm7, fm_uom, _fm_days = _family_movement_metrics(cur, family_id, mvt_days_7)
        inv = _latest_inventory(cur, upc_id, family_id)
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
        dos = None
        if inv and velocity7 > 0:
            iq = Decimal(str(inv['on_hand_quantity']))
            iu = (inv['uom_code'] or '').upper()
            if iu and selling_uom and iu == str(selling_uom).upper():
                dos = iq / velocity7
            elif iu and base_uom and iu == str(base_uom).upper() and factor and factor > 0:
                dos = (iq / factor) / velocity7

        # DOH is physical/calendar age, not a rolling-data-day metric.
        doh = (calendar_today - last_receipt).days if pclass in {'FRESH', 'LIVE'} and last_receipt else None
        wgpm = None
        if cost_sell is not None and pclass in {'LIVE', 'FRESH', 'FROZEN'}:
            target = {'LIVE': Decimal('0.15'), 'FRESH': Decimal('0.30'), 'FROZEN': Decimal('0.44')}[pclass]
            wgpm = (cost_sell / (Decimal('1') - target)).quantize(Decimal('0.01'))
        sweet = _historical_sweet_spot(cur, upc_id, family_id, factor, pos_days_30) if cost else None
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
             inv['on_hand_quantity'] if inv else None, inv['uom_code'] if inv else None, inv['observation_date'] if inv else None, dos, doh,
             gp_pct, gp7, gpday, sweet, wgpm, cp['price_a'] if cp else None, cp['price_b'] if cp else None, cp['price_c'] if cp else None,
             qc_status,
             (','.join(reasons) if reasons else
              ('NO_POS_SALES_LATEST_28_VALID_DATA_DAYS' if not active_current else None)),
             batch_id),
        )

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


def process_phase3(batch_id: int) -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            # Manual authority tables are bootstrap schema. Ensure them before the
            # Phase 3 business transaction because MySQL DDL implicitly commits
            # and would invalidate the later Quick Check SAVEPOINT.
            ensure_override_table(cur)
            ensure_retirement_table(cur)
            conn.commit()
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
            retired_recomputed_issues = retire_recomputed_phase3_issues(cur, batch_id)

            cur.execute(
                """INSERT INTO pipeline_run (batch_id,pipeline_name,stage_name,run_number,processing_status,code_version)
                   VALUES (%s,'FULL_MYSQL_SEAFOOD','PHASE3_HISTORY_PRECOMPUTE',1,'STARTED','local-agent-v6.6.0')""", (batch_id,))
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

            relink_history(cur)

            # v7.0.19: cost repair/audit is CURRENT-ACTIVE ONLY.
            # Authority:
            #   1) valid 101/107/109 receipt valuation
            #   2) explicit official Live/Fresh/Frozen report cost
            #   3) explicit OH cost + explicit supported cost UOM
            # Historical-only UPCs are not targeted.
            current_active_cost_repair = repair_current_active_cost(cur, batch_id)

            late_identity = resolve_late_identity_issues(cur, batch_id)
            unmapped_activity = classify_unmapped_sales_activity_scope(cur, batch_id)

            # Explicit temporary waivers are applied only after active/historical
            # classification so a rerun cannot silently restore them to HIGH.
            # Identity remains unresolved and Quick Check remains unavailable.
            temporary_qa_waivers = apply_temporary_identity_waivers(cur, batch_id)

            # FINAL USER-AUTHORITY LOCK (v7.0.25): automatic identity/UOM repair runs above.
            # Reapply confirmed overrides and retirements after every automatic repair so a
            # rebuild cannot resurrect a nonexistent UPC or overwrite a user-confirmed UOM.
            override_result = apply_manual_upc_overrides(cur)
            retirement_result = apply_manual_upc_retirements(cur)

            # v7.0.30 fail-closed product-identity publish guard.
            # Candidate serving rows are built under a SAVEPOINT. A GLOBAL
            # identity blocker rolls back only that candidate snapshot so the
            # previously published Quick Check remains intact.
            cur.execute('SAVEPOINT before_quick_check_publish')
            qc_attempt = rebuild_quick_check(cur, batch_id)
            identity_audit = audit_product_identity(cur)
            identity_guard_pass = bool(identity_audit.get('pass'))
            identity_guard_blockers = list(identity_audit.get('blockers') or [])
            serving_preserved = False

            if identity_guard_pass:
                cur.execute('RELEASE SAVEPOINT before_quick_check_publish')
                qc = qc_attempt
            else:
                cur.execute('ROLLBACK TO SAVEPOINT before_quick_check_publish')
                cur.execute('RELEASE SAVEPOINT before_quick_check_publish')
                serving_preserved = True
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

            if (not identity_guard_pass) or blocking > 0 or qc['rows'] == 0:
                status = 'PHASE3_QA_HOLD'
            elif qc['hold'] > 0:
                status = 'QUICK_CHECK_READY_WITH_HOLDS'
            else:
                status = 'QUICK_CHECK_READY'
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
                 qc['rows'], qc['ready'], qc['hold'], blocking, status, json.dumps({'history_counts': counts, 'late_identity_resolution': late_identity, 'manual_overrides_pre_repair': override_result_pre, 'manual_retirements_pre_repair': retirement_result_pre, 'manual_overrides': override_result, 'manual_retirements': retirement_result, 'retired_recomputed_issues': retired_recomputed_issues, 'unmapped_activity_scope': unmapped_activity,
                  'active_product_master_repair': active_master_repair,
                  'article_manual_multitab_repair': multitab_manual_repair,
                  'cross_tab_signature_repair': cross_tab_signature_repair,
                  'temporary_qa_waivers': temporary_qa_waivers,
                  'active_28d_uom_repair': active_28d_uom_repair,
                  'current_active_cost_repair': current_active_cost_repair,
                  'product_identity_guard': product_identity_guard}, default=str)),
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
                 }, default=str), run_id),
            )
            conn.commit()
            return {'batch_id': batch_id, 'status': status, **counts, 'quick_check': qc, 'late_identity_resolution': late_identity, 'manual_overrides_pre_repair': override_result_pre, 'manual_retirements_pre_repair': retirement_result_pre, 'manual_overrides': override_result, 'manual_retirements': retirement_result, 'retired_recomputed_issues': retired_recomputed_issues, 'unmapped_activity_scope': unmapped_activity,
                    'active_product_master_repair': active_master_repair,
                    'article_manual_multitab_repair': multitab_manual_repair,
                    'cross_tab_signature_repair': cross_tab_signature_repair,
                    'temporary_qa_waivers': temporary_qa_waivers,
                    'active_28d_uom_repair': active_28d_uom_repair,
                    'current_active_cost_repair': current_active_cost_repair,
                    'product_identity_guard': product_identity_guard,
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
