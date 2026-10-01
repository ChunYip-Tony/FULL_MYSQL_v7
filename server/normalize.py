from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from upc_aliases import service_249_canonical_base

from db import db_conn

V6_6_0 = True

IDENTITY_SOURCES = {
    'monthly_pi_form': 'raw_monthly_pi_form',
    'article_manual': 'raw_article_manual',
}

# Article Manual is authoritative for canonical product hierarchy and selling identity.
# Monthly PI is operational observation evidence and must not override a verified manual mapping.
MISSING_SOURCE_TOKENS = {'#N/A', 'N/A', 'NA', 'NULL', 'NONE', '-', '--'}
SELF_MAIN_ARTICLE_OVERRIDES = {'3480435', '3480438', '1353022'}

HEADER_ALIASES = {
    'article': {
        'art', 'article', 'article number', 'article no', 'article #', 'art no', 'art #',
        'sub article', 'sub article number', 'sub-article', 'sub-article number',
    },
    'main_article': {
        'main article', 'main article number', 'main article no', 'main article #',
        'main art', 'family article', 'family article number', 'family article no',
    },
    'upc': {
        'upc/plu', 'plu/upc', 'plu /upc', 'upc', 'ean/upc', 'ean', 'plu', 'selling upc', 'selling ean', 'ean upc',
    },
    'sales_set': {
        'sales set', 'sales set #', 'sales set no', 'sales set number', 'sales set#',
    },
    'description': {
        'english', 'description', 'english description', 'article description', 'item description',
    },
    'chinese_description': {
        'chinese', 'chinese description', 'chinese desc', 'chinese name',
    },
    'pack': {
        'pack', 'packing size', 'pack size', 'packing', 'case pack',
        'size/dimensions', 'size dimensions', 'size/dimension', 'size dimension',
    },
    'category': {
        'cat', 'category', 'merchandise category', 'merch category',
    },
    'base_uom': {
        'bun', 'base uom', 'base unit', 'base unit of measure',
    },
    'order_uom': {
        'order unit', 'ordering unit', 'order uom', 'ordering uom',
    },
    'receiving_uom': {
        'receiving uom', 'receiving unit', 'receipt uom', 'receipt unit',
    },
    'cost_uom': {
        'cost uom', 'cost unit',
    },
    'selling_uom': {
        'selling uom', 'selling unit', 'sales uom', 'sales unit', 'um',
    },
}


@dataclass
class RowContext:
    batch_id: int
    file_id: int
    sheet_id: int
    raw_table: str
    raw_id: int
    source_row_number: int
    source_type: str
    sheet_name: str


def _norm_header(value: Any) -> str:
    s = '' if value is None else str(value)
    s = s.replace('\n', ' ').replace('\r', ' ').strip().lower()
    s = re.sub(r'[_:/\\-]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def _json_obj(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if isinstance(value, (bytes, bytearray)):
        value = value.decode('utf-8', errors='replace')
    try:
        obj = json.loads(value)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _id_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, 'f').rstrip('0').rstrip('.')
    s = str(value).strip()
    if not s:
        return None
    # Excel numeric identifiers often arrive as strings ending in .0.
    if re.fullmatch(r'\d+\.0+', s):
        return s.split('.', 1)[0]
    # Avoid scientific notation where possible, but never pad or invent leading zeroes.
    if re.fullmatch(r'\d+(?:\.\d+)?[eE][+-]?\d+', s):
        try:
            d = Decimal(s)
            if d == d.to_integral_value():
                return format(d.quantize(Decimal('1')), 'f')
        except InvalidOperation:
            pass
    return s



def _numeric_identifier(value: Any) -> str | None:
    s = _id_text(value)
    if not s:
        return None
    return s if re.fullmatch(r'\d+', s) else None


def _article_manual_upc_identifier(value: Any) -> str | None:
    """Parse Article Manual UPC cells without inventing digits.

    Article Manual commonly formats EAN/UPC values with visual spaces or hyphens,
    e.g. "4 71106163078 0". Accept only digits separated by whitespace/hyphens;
    reject labels such as "Main" / "Sub" and all fuzzy/non-numeric values.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    raw = str(value).strip()
    if not raw:
        return None
    if re.fullmatch(r'\d+\.0+', raw):
        return raw.split('.', 1)[0]
    if re.fullmatch(r'[\d\s-]+', raw):
        digits = re.sub(r'\D', '', raw)
        return digits or None
    return None

def _text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _source_token(value: Any) -> str | None:
    """Return a usable source token, treating spreadsheet missing-value markers as no value."""
    s = _text(value)
    if not s:
        return None
    return None if s.upper().strip() in MISSING_SOURCE_TOKENS else s


def _numeric_key(value: str | None) -> str | None:
    """Numeric-equivalence key used only for UPC lookup (e.g. 00000004918 == 4918)."""
    if not value or not re.fullmatch(r'\d+', value):
        return None
    k = value.lstrip('0')
    return k or '0'


def _build_column_map(header_payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    normalized_to_field: dict[str, str] = {}
    for field, aliases in HEADER_ALIASES.items():
        for a in aliases:
            normalized_to_field[_norm_header(a)] = field
    for col, value in header_payload.items():
        field = normalized_to_field.get(_norm_header(value))
        if field and field not in result:
            result[field] = col
    return result


ARTICLE_MANUAL_RECEIVING_PACK_TABS = {
    'fresh fish',
    'live fish',
    'shrimp',
    'fish ball',
    'frozen fish',
}


def _article_manual_column_map(
    sheet_name: str | None,
    header_payload: dict[str, Any],
) -> dict[str, str]:
    """Apply the user-confirmed per-tab Article Manual schema.

    Fresh Fish / Live Fish / Shrimp / Fish Ball / Frozen Fish:
      A = Family/Main Article
      B = Selling Article (blank means Main Article for that UPC row)
      C = Toledo #
      D = EAN/UPC
      G = Receiving pack size/dimension
      D EAN/UPC + C Toledo# on the same row => Selling UOM LB

    Frozen Pack:
      A = Family/Main Article
      D = EAN/UPC
      E = Receiving pack size/dimension
      G = Selling UOM

    Header aliases remain available for non-critical descriptive columns, but the
    identity/UOM columns above are positional authority and cannot be reclassified
    by a misleading header label.
    """
    result = _build_column_map(header_payload)
    tab = _norm_header(sheet_name)

    if tab in ARTICLE_MANUAL_RECEIVING_PACK_TABS:
        result['main_article'] = 'A'
        result['article'] = 'B'
        result['sales_set'] = 'C'  # Toledo #
        result['upc'] = 'D'
        result['pack'] = 'G'
        if result.get('selling_uom') == 'G':
            result.pop('selling_uom', None)
    elif tab == 'frozen pack':
        result['main_article'] = 'A'
        # Frozen Pack has no separate Selling Article column in the confirmed
        # schema; the Family/Main Article is the row Article anchor.
        result['article'] = 'A'
        result['upc'] = 'D'
        result['pack'] = 'E'
        result['selling_uom'] = 'G'

    return result


def _monthly_pi_column_map(
    sheet_name: str | None,
    header_payload: dict[str, Any],
) -> dict[str, str]:
    """Apply the user-confirmed Monthly PI per-tab schema.

    Actual current workbook:
      FROZEN:      D = Pack, E = Base Unit, G = Main Article, H = UPC/PLU.
      FRESH&LIVE:  D = Packing Size, E = Order Unit, F = Main Article.

    Important: on FRESH&LIVE the receiving container is not reliably Column E.
    Rows such as 1361596 are D='60LB/CV', E='LB': the receiving unit is CV,
    base unit is LB, and one CV contains 60 LB. Therefore receiving/base
    conversion is parsed from D first; Column E is retained as ORDERING evidence
    and is used only as a fallback container for count/inner-pack expressions.
    """
    result = _build_column_map(header_payload)
    tab = _norm_header(sheet_name)

    if tab == 'frozen' or tab.startswith('frozen '):
        result['pack'] = 'D'
        result['base_uom'] = 'E'
        result['main_article'] = 'G'
        result['upc'] = 'H'
        if result.get('receiving_uom') == 'E':
            result.pop('receiving_uom', None)
        if result.get('order_uom') == 'E':
            result.pop('order_uom', None)

    elif tab in {'fresh&live', 'fresh & live', 'fresh live'}:
        result['pack'] = 'D'
        result['order_uom'] = 'E'
        result['main_article'] = 'F'
        # Do not label E as Receiving. The receiving container is encoded in
        # D when present (e.g. 60LB/CV, 40LB/BAG, 12EA/CV).
        if result.get('receiving_uom') == 'E':
            result.pop('receiving_uom', None)
        if result.get('base_uom') == 'E':
            result.pop('base_uom', None)

    return result


def _monthly_pi_pack_structure(
    value: Any,
    order_uom: Any = None,
) -> dict[str, Any] | None:
    """Parse Monthly PI pack structure without converting between dimensions.

    Supported exact structures from the uploaded form:
      60LB/CV   -> 60 LB per CV
      40 LB/BAG -> 40 LB per BAG
      12 EA/CV  -> 12 EA per CV
      25 PAC/CV -> 25 PAC per CV
      5/2LB     -> with E=CV, 10 LB per CV
      24/6OZ    -> with E=CV, 144 OZ per CV
      LB        -> LB base / LB order, factor 1
      10LB      -> if E=LB, package descriptor only; factor stays 1 LB per LB

    No OZ<->LB, G<->LB, PAC<->EA, or similar conversion is inferred.
    """
    raw = _source_token(value)
    if not raw:
        return None
    token = re.sub(r'\s+', '', str(raw).upper()).replace('LBS', 'LB')
    order = (_source_token(order_uom) or '').upper().strip()

    # QTY BASE / RECEIVING, e.g. 60LB/CV or 25PAC/CV.
    m = re.fullmatch(r'(\d+(?:\.\d+)?)([A-Z]+)/(?:1)?([A-Z]+)', token)
    if m:
        qty = Decimal(m.group(1))
        base = m.group(2)
        receiving = m.group(3)
        if qty > 0:
            return {
                'base_uom': base,
                'receiving_uom': receiving,
                'base_qty_per_receiving_unit': qty,
                'order_uom': order or None,
                'pattern': 'QTY_BASE_PER_RECEIVING',
                'raw': raw,
            }

    # OUTER COUNT / INNER QTY BASE, e.g. 5/2LB or 24/6OZ.
    m = re.fullmatch(r'(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)([A-Z]+)', token)
    if m:
        outer = Decimal(m.group(1))
        inner = Decimal(m.group(2))
        base = m.group(3)
        if outer > 0 and inner > 0:
            if order and order != base:
                return {
                    'base_uom': base,
                    'receiving_uom': order,
                    'base_qty_per_receiving_unit': outer * inner,
                    'outer_count': outer,
                    'inner_qty': inner,
                    'order_uom': order,
                    'pattern': 'OUTER_COUNT_X_INNER_BASE_USING_ORDER_CONTAINER',
                    'raw': raw,
                }
            return {
                'base_uom': base,
                'receiving_uom': base if order == base else None,
                'base_qty_per_receiving_unit': Decimal('1') if order == base else None,
                'outer_count': outer,
                'inner_qty': inner,
                'order_uom': order or None,
                'pattern': 'PACK_DESCRIPTOR_BASE_ORDERED_DIRECTLY',
                'raw': raw,
            }

    # Plain BASE token.
    m = re.fullmatch(r'([A-Z]+)', token)
    if m:
        base = m.group(1)
        receiving = order or base
        return {
            'base_uom': base,
            'receiving_uom': receiving if receiving == base else None,
            'base_qty_per_receiving_unit': Decimal('1') if receiving == base else None,
            'order_uom': order or None,
            'pattern': 'BASE_DIRECT',
            'raw': raw,
        }

    # Plain package quantity, e.g. 10LB. If ordered in LB, do not turn 10LB
    # into a 10x selling/receiving conversion; it is package-size evidence only.
    m = re.fullmatch(r'(\d+(?:\.\d+)?)([A-Z]+)', token)
    if m:
        qty = Decimal(m.group(1))
        base = m.group(2)
        if qty > 0:
            if order and order != base:
                return {
                    'base_uom': base,
                    'receiving_uom': order,
                    'base_qty_per_receiving_unit': qty,
                    'order_uom': order,
                    'pattern': 'QTY_BASE_USING_ORDER_CONTAINER',
                    'raw': raw,
                }
            return {
                'base_uom': base,
                'receiving_uom': base if order == base else None,
                'base_qty_per_receiving_unit': Decimal('1') if order == base else None,
                'order_uom': order or None,
                'package_qty': qty,
                'pattern': 'PACKAGE_DESCRIPTOR_BASE_ORDERED_DIRECTLY',
                'raw': raw,
            }

    return None



def _structured_pack_weight(value: Any) -> dict[str, Any] | None:
    """Parse only the user-confirmed structured weight pack patterns.

    Examples:
      60LB  -> one receiving unit contains 60 LB
      6/5LB -> one receiving case contains 6 inner selling units of 5 LB each

    Slash is a case-pack separator here, never division. No OZ/KG conversion is
    attempted; the unit printed in the source remains the base unit.
    """
    raw = _source_token(value)
    if not raw:
        return None
    token = re.sub(r'\s+', '', str(raw).upper())
    token = token.replace('LBS', 'LB')

    m = re.fullmatch(r'(\d+(?:\.\d+)?)LB', token)
    if m:
        qty = Decimal(m.group(1))
        if qty <= 0:
            return None
        return {
            'outer_count': Decimal('1'),
            'inner_qty': qty,
            'base_uom': 'LB',
            'total_base_qty': qty,
            'pattern': 'SINGLE_WEIGHT',
            'raw': raw,
        }

    m = re.fullmatch(r'(\d+(?:\.\d+)?)[/X*](\d+(?:\.\d+)?)LB', token)
    if m:
        outer = Decimal(m.group(1))
        inner = Decimal(m.group(2))
        if outer <= 0 or inner <= 0:
            return None
        return {
            'outer_count': outer,
            'inner_qty': inner,
            'base_uom': 'LB',
            'total_base_qty': outer * inner,
            'pattern': 'OUTER_COUNT_X_INNER_WEIGHT',
            'raw': raw,
        }
    return None


def _selling_factor_from_frozen_pack(
    selling_uom: str | None,
    pack: Any,
) -> dict[str, Any] | None:
    """Derive selling-unit-to-base conversion from Frozen Pack schema only.

    For N/QTYLB pack text (e.g. 6/5LB):
      - BX/PACK/PAC/BAG/TRAY/EA style selling units use QTY LB per selling unit.
      - CASE/CV selling units use N*QTY LB per selling unit.
    """
    parsed = _structured_pack_weight(pack)
    sell = (_source_token(selling_uom) or '').upper().strip()
    if not parsed or not sell:
        return None

    if sell in {'CASE', 'CV'}:
        factor = parsed['total_base_qty']
        basis = 'FULL_CASE_WEIGHT'
    elif sell in {'BX', 'BOX', 'PACK', 'PAC', 'PK', 'PKG', 'BAG', 'TRAY', 'EA', 'EACH', 'PC', 'PCS'}:
        factor = parsed['inner_qty']
        basis = 'INNER_SELLING_UNIT_WEIGHT'
    elif sell in {'LB', 'LBS'}:
        factor = Decimal('1')
        basis = 'SELLING_EQUALS_BASE'
    else:
        return None

    return {
        **parsed,
        'selling_uom': sell,
        'base_qty_per_selling_unit': factor,
        'conversion_basis': basis,
    }


def _get(row: dict[str, Any], colmap: dict[str, str], field: str) -> Any:
    col = colmap.get(field)
    return row.get(col) if col else None


def _insert_evidence(cur, object_type: str, object_id: int, role: str, ctx: RowContext,
                     field_name: str | None = None, value: Any = None, extra: dict[str, Any] | None = None) -> None:
    cur.execute(
        """
        INSERT INTO normalized_source_evidence
          (object_type,object_id,evidence_role,batch_id,file_id,sheet_id,raw_table_name,raw_id,
           source_row_number,source_field_name,source_value_text,evidence_json)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            object_type, object_id, role, ctx.batch_id, ctx.file_id, ctx.sheet_id, ctx.raw_table,
            ctx.raw_id, ctx.source_row_number, field_name, None if value is None else str(value),
            json.dumps(extra or {}, ensure_ascii=False),
        ),
    )


def _qa_issue(cur, code: str, entity_type: str, entity_key: str, summary: str, ctx: RowContext,
              expected: Any = None, observed: Any = None, severity: str = 'CRITICAL') -> int:
    # De-duplicate an open issue for the same current source row/code.
    cur.execute(
        """
        SELECT issue_id FROM qa_identity_uom_issue
        WHERE issue_status='OPEN' AND issue_code=%s AND entity_type=%s AND entity_key=%s
          AND batch_id=%s AND raw_table_name=%s AND raw_id=%s
        ORDER BY issue_id LIMIT 1
        """,
        (code, entity_type, entity_key, ctx.batch_id, ctx.raw_table, ctx.raw_id),
    )
    found = cur.fetchone()
    if found:
        return int(found['issue_id'])
    cur.execute(
        """
        INSERT INTO qa_identity_uom_issue
          (issue_status,severity,issue_code,entity_type,entity_key,issue_summary,expected_json,observed_json,
           batch_id,file_id,sheet_id,raw_table_name,raw_id)
        VALUES ('OPEN',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            severity, code, entity_type, entity_key, summary,
            json.dumps(expected, ensure_ascii=False) if expected is not None else None,
            json.dumps(observed, ensure_ascii=False) if observed is not None else None,
            ctx.batch_id, ctx.file_id, ctx.sheet_id, ctx.raw_table, ctx.raw_id,
        ),
    )
    return int(cur.lastrowid)


def _ensure_family(cur, main_article: str, description: str | None, ctx: RowContext) -> int:
    cur.execute("SELECT family_id FROM product_family WHERE main_article_number=%s", (main_article,))
    row = cur.fetchone()
    if row:
        family_id = int(row['family_id'])
        if description:
            cur.execute(
                "UPDATE product_family SET family_description=COALESCE(family_description,%s) WHERE family_id=%s",
                (description, family_id),
            )
    else:
        cur.execute(
            """INSERT INTO product_family
               (main_article_number,family_description,mapping_status)
               VALUES (%s,%s,'CONFIRMED')""",
            (main_article, description),
        )
        family_id = int(cur.lastrowid)
    _insert_evidence(cur, 'PRODUCT_FAMILY', family_id, 'MAIN_ARTICLE_SOURCE', ctx, 'main_article', main_article)
    return family_id


def _ensure_article(cur, article_number: str, description: str | None, category: str | None, ctx: RowContext) -> int:
    cur.execute("SELECT article_id FROM article WHERE article_number=%s", (article_number,))
    row = cur.fetchone()
    if row:
        article_id = int(row['article_id'])
        cur.execute(
            """UPDATE article SET article_description=COALESCE(article_description,%s),
               category_code=COALESCE(category_code,%s) WHERE article_id=%s""",
            (description, category, article_id),
        )
    else:
        cur.execute(
            """INSERT INTO article (article_number,article_description,category_code,record_status)
               VALUES (%s,%s,%s,'ACTIVE')""",
            (article_number, description, category),
        )
        article_id = int(cur.lastrowid)
    _insert_evidence(cur, 'ARTICLE', article_id, 'ARTICLE_SOURCE', ctx, 'article', article_number)
    return article_id


def _ensure_upc(cur, ean_upc: str, description: str | None, ctx: RowContext) -> int:
    # Exact source spelling wins. If it is not present, allow leading-zero-equivalent
    # matching so internal POS codes such as 4918 and 00000004918 resolve to one identity.
    cur.execute("SELECT upc_id,ean_upc FROM selling_upc WHERE ean_upc=%s", (ean_upc,))
    row = cur.fetchone()
    if not row:
        key = _numeric_key(ean_upc)
        if key is not None:
            cur.execute(
                """SELECT upc_id,ean_upc FROM selling_upc
                   WHERE ean_upc REGEXP '^[0-9]+$'
                     AND TRIM(LEADING '0' FROM ean_upc)=%s
                   ORDER BY CHAR_LENGTH(ean_upc),upc_id LIMIT 1""",
                (key,),
            )
            row = cur.fetchone()
    if not row:
        service_candidate=service_249_canonical_base(ean_upc)
        if service_candidate and service_candidate!=str(ean_upc):
            cur.execute(
                """SELECT upc_id,ean_upc FROM selling_upc
                   WHERE ean_upc=%s
                     AND record_status='ACTIVE'
                   LIMIT 1""",
                (service_candidate,),
            )
            row=cur.fetchone()
    if row:
        upc_id = int(row['upc_id'])
        if description:
            cur.execute(
                "UPDATE selling_upc SET selling_description=COALESCE(selling_description,%s) WHERE upc_id=%s",
                (description, upc_id),
            )
    else:
        cur.execute(
            "INSERT INTO selling_upc (ean_upc,selling_description,record_status) VALUES (%s,%s,'ACTIVE')",
            (ean_upc, description),
        )
        upc_id = int(cur.lastrowid)
    _insert_evidence(cur, 'SELLING_UPC', upc_id, 'UPC_SOURCE', ctx, 'upc', ean_upc)
    return upc_id


def _bridge_has_article_manual_evidence(cur, object_type: str, object_id: int) -> bool:
    cur.execute(
        """SELECT 1 FROM normalized_source_evidence
           WHERE object_type=%s AND object_id=%s AND raw_table_name='raw_article_manual'
           LIMIT 1""",
        (object_type, object_id),
    )
    return bool(cur.fetchone())


def _manual_article_family(cur, article_number: str) -> dict[str, Any] | None:
    cur.execute(
        """SELECT baf.article_family_id,baf.family_id,pf.main_article_number,baf.relationship_type
           FROM article a
           JOIN bridge_article_family baf ON baf.article_id=a.article_id
           JOIN product_family pf ON pf.family_id=baf.family_id
           WHERE a.article_number=%s AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
             AND EXISTS (SELECT 1 FROM normalized_source_evidence nse
                         WHERE nse.object_type='ARTICLE_FAMILY' AND nse.object_id=baf.article_family_id
                           AND nse.raw_table_name='raw_article_manual')
           ORDER BY baf.article_family_id DESC LIMIT 1""",
        (article_number,),
    )
    return cur.fetchone()


def _manual_upc_anchor(cur, upc_id: int) -> dict[str, Any] | None:
    # A legacy v6 row may have linked the UPC directly to a SUB article.  Resolve the
    # manual evidence through that article's canonical family and return the MAIN
    # article id as the selling identity anchor.
    cur.execute(
        """SELECT bau.article_upc_id,bau.article_id AS observed_article_id,a.article_number AS observed_article_number,
                  baf.family_id,pf.main_article_number,amain.article_id AS main_article_id
           FROM bridge_article_upc bau
           JOIN article a ON a.article_id=bau.article_id
           JOIN bridge_article_family baf ON baf.article_id=bau.article_id
             AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           JOIN product_family pf ON pf.family_id=baf.family_id
           JOIN article amain ON amain.article_number=pf.main_article_number
           WHERE bau.upc_id=%s AND bau.mapping_status='CONFIRMED' AND bau.is_primary=TRUE
             AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
             AND EXISTS (SELECT 1 FROM normalized_source_evidence nse
                         WHERE nse.object_type='ARTICLE_UPC' AND nse.object_id=bau.article_upc_id
                           AND nse.raw_table_name='raw_article_manual')
           ORDER BY bau.article_upc_id DESC LIMIT 1""",
        (upc_id,),
    )
    return cur.fetchone()


def _active_article_main(cur, article_id: int) -> str | None:
    cur.execute(
        """SELECT pf.main_article_number
           FROM bridge_article_family baf
           JOIN product_family pf ON pf.family_id=baf.family_id
           WHERE baf.article_id=%s AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
             AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
           ORDER BY baf.article_family_id DESC LIMIT 1""",
        (article_id,),
    )
    r = cur.fetchone()
    return str(r['main_article_number']) if r else None


def _ensure_article_family(cur, article_id: int, family_id: int, article_number: str, main_article: str,
                           ctx: RowContext) -> tuple[int, str]:
    rel = 'MAIN' if article_number == main_article else 'SUB'
    cur.execute(
        """
        SELECT baf.article_family_id,pf.main_article_number,baf.family_id
        FROM bridge_article_family baf
        JOIN product_family pf ON pf.family_id=baf.family_id
        WHERE baf.article_id=%s AND baf.mapping_status='CONFIRMED' AND baf.is_primary=TRUE
          AND (baf.valid_to IS NULL OR baf.valid_to>CURRENT_TIMESTAMP(6))
        """,
        (article_id,),
    )
    active = cur.fetchall()
    conflicts = [r for r in active if int(r['family_id']) != family_id]

    # Article Manual is authoritative. It may safely supersede a prior non-manual mapping,
    # but two conflicting manual-confirmed families are a true blocking conflict.
    if conflicts and ctx.source_type == 'article_manual':
        manual_conflicts = [r for r in conflicts if _bridge_has_article_manual_evidence(cur, 'ARTICLE_FAMILY', int(r['article_family_id']))]
        if manual_conflicts:
            _qa_issue(
                cur, 'ARTICLE_MANUAL_MULTI_FAMILY_CONFLICT', 'ARTICLE', article_number,
                f'Article Manual contains conflicting active family mappings for Article {article_number}.',
                ctx, expected={'main_article': main_article},
                observed={'existing_main_articles': [r['main_article_number'] for r in manual_conflicts]},
            )
            status = 'QA_HOLD'
        else:
            for r in conflicts:
                cur.execute(
                    """UPDATE bridge_article_family
                       SET mapping_status='SUPERSEDED',is_primary=FALSE,valid_to=COALESCE(valid_to,CURRENT_TIMESTAMP(6))
                       WHERE article_family_id=%s""",
                    (r['article_family_id'],),
                )
            status = 'CONFIRMED'
    elif conflicts:
        _qa_issue(
            cur, 'ARTICLE_MULTI_FAMILY_CONFLICT', 'ARTICLE', article_number,
            f'Article {article_number} is observed under Main Article {main_article}, but another active confirmed family already exists.',
            ctx, expected={'main_article': main_article},
            observed={'existing_main_articles': [r['main_article_number'] for r in conflicts]},
        )
        status = 'QA_HOLD'
    else:
        status = 'CONFIRMED'

    cur.execute(
        """SELECT article_family_id,mapping_status,is_primary FROM bridge_article_family
           WHERE article_id=%s AND family_id=%s AND relationship_type=%s
           ORDER BY article_family_id DESC LIMIT 1""",
        (article_id, family_id, rel),
    )
    row = cur.fetchone()
    if row:
        bridge_id = int(row['article_family_id'])
        if status == 'CONFIRMED' and (row['mapping_status'] != 'CONFIRMED' or not row['is_primary']):
            cur.execute(
                """UPDATE bridge_article_family SET mapping_status='CONFIRMED',is_primary=TRUE,confidence=1.0,valid_to=NULL
                   WHERE article_family_id=%s""",
                (bridge_id,),
            )
    else:
        cur.execute(
            """INSERT INTO bridge_article_family
               (article_id,family_id,relationship_type,is_primary,mapping_status,confidence)
               VALUES (%s,%s,%s,TRUE,%s,%s)""",
            (article_id, family_id, rel, status, 1.0 if status == 'CONFIRMED' else 0.0),
        )
        bridge_id = int(cur.lastrowid)
    _insert_evidence(cur, 'ARTICLE_FAMILY', bridge_id, 'ARTICLE_FAMILY_SOURCE', ctx, extra={'relationship_type': rel})
    return bridge_id, status


def _ensure_article_upc(cur, article_id: int, upc_id: int, article_number: str, ean_upc: str,
                        sales_set: str | None, ctx: RowContext) -> tuple[int, str]:
    # article_id/article_number here must be the canonical MAIN/FAMILY article anchor.
    cur.execute(
        """
        SELECT bau.article_upc_id,a.article_number,bau.article_id
        FROM bridge_article_upc bau
        JOIN article a ON a.article_id=bau.article_id
        WHERE bau.upc_id=%s AND bau.mapping_status='CONFIRMED' AND bau.is_primary=TRUE
          AND (bau.valid_to IS NULL OR bau.valid_to>CURRENT_TIMESTAMP(6))
        """,
        (upc_id,),
    )
    active = cur.fetchall()
    conflicts = [r for r in active if int(r['article_id']) != article_id]

    # Legacy v6 linked selling UPCs directly to SUB articles.  Those are not true
    # conflicts when the old article resolves to the same canonical Main/Family.
    same_family_legacy = []
    true_conflicts = []
    for r in conflicts:
        old_main = _active_article_main(cur, int(r['article_id']))
        if old_main == article_number:
            same_family_legacy.append(r)
        else:
            true_conflicts.append(r)

    for r in same_family_legacy:
        cur.execute(
            """UPDATE bridge_article_upc
               SET mapping_status='SUPERSEDED',is_primary=FALSE,valid_to=COALESCE(valid_to,CURRENT_TIMESTAMP(6))
               WHERE article_upc_id=%s""",
            (r['article_upc_id'],),
        )

    if true_conflicts and ctx.source_type == 'article_manual':
        manual_conflicts = [r for r in true_conflicts if _bridge_has_article_manual_evidence(cur, 'ARTICLE_UPC', int(r['article_upc_id']))]
        if manual_conflicts:
            _qa_issue(
                cur, 'ARTICLE_MANUAL_UPC_MULTI_FAMILY_CONFLICT', 'UPC', ean_upc,
                f'Article Manual maps UPC {ean_upc} to more than one canonical family article.',
                ctx, expected={'main_article': article_number},
                observed={'existing_main_articles': [r['article_number'] for r in manual_conflicts]},
            )
            status = 'QA_HOLD'
        else:
            for r in true_conflicts:
                cur.execute(
                    """UPDATE bridge_article_upc
                       SET mapping_status='SUPERSEDED',is_primary=FALSE,valid_to=COALESCE(valid_to,CURRENT_TIMESTAMP(6))
                       WHERE article_upc_id=%s""",
                    (r['article_upc_id'],),
                )
            status = 'CONFIRMED'
    elif true_conflicts:
        _qa_issue(
            cur, 'UPC_MULTI_FAMILY_CONFLICT', 'UPC', ean_upc,
            f'UPC {ean_upc} resolves to canonical Main/Family Article {article_number}, but another active confirmed family anchor exists.',
            ctx, expected={'main_article': article_number},
            observed={'existing_main_articles': [r['article_number'] for r in true_conflicts]},
        )
        status = 'QA_HOLD'
    else:
        status = 'CONFIRMED'

    cur.execute(
        """SELECT article_upc_id,mapping_status,is_primary FROM bridge_article_upc
           WHERE article_id=%s AND upc_id=%s AND relationship_type='SELLING'
           ORDER BY article_upc_id DESC LIMIT 1""",
        (article_id, upc_id),
    )
    row = cur.fetchone()
    if row:
        bridge_id = int(row['article_upc_id'])
        if status == 'CONFIRMED':
            cur.execute(
                """UPDATE bridge_article_upc
                   SET mapping_status='CONFIRMED',is_primary=TRUE,confidence=1.0,valid_to=NULL,
                       sales_set_number=COALESCE(sales_set_number,%s)
                   WHERE article_upc_id=%s""",
                (sales_set, bridge_id),
            )
    else:
        cur.execute(
            """INSERT INTO bridge_article_upc
               (article_id,upc_id,relationship_type,sales_set_number,is_primary,mapping_status,confidence)
               VALUES (%s,%s,'SELLING',%s,TRUE,%s,%s)""",
            (article_id, upc_id, sales_set, status, 1.0 if status == 'CONFIRMED' else 0.0),
        )
        bridge_id = int(cur.lastrowid)
    _insert_evidence(cur, 'ARTICLE_UPC', bridge_id, 'ARTICLE_UPC_SOURCE', ctx, extra={'sales_set_number': sales_set, 'canonical_family_anchor': article_number})
    return bridge_id, status


def _canonical_uom(cur, source_type: str, token: str | None) -> tuple[int | None, str | None]:
    token = _source_token(token)
    if not token:
        return None, None
    source_token = token.upper().strip()
    cur.execute("SELECT uom_id,uom_code FROM dim_uom WHERE UPPER(uom_code)=%s", (source_token,))
    row = cur.fetchone()
    if row:
        uom_id = int(row['uom_id'])
        cur.execute(
            """INSERT INTO uom_source_alias
               (source_system,source_uom_code,canonical_uom_id,mapping_status,confidence,notes)
               VALUES (%s,%s,%s,'CONFIRMED',1.0,'Exact canonical token match; no conversion implied')
               ON DUPLICATE KEY UPDATE
                 canonical_uom_id=VALUES(canonical_uom_id),mapping_status='CONFIRMED',confidence=1.0""",
            (source_type, token, uom_id),
        )
        return uom_id, row['uom_code']
    cur.execute(
        """INSERT INTO uom_source_alias
           (source_system,source_uom_code,canonical_uom_id,mapping_status,confidence,notes)
           VALUES (%s,%s,NULL,'UNRESOLVED',0.0,'Observed source UOM token; no silent canonical inference')
           ON DUPLICATE KEY UPDATE notes=VALUES(notes)""",
        (source_type, token),
    )
    return None, None


def _ensure_article_uom_role(cur, article_id: int, role: str, uom_id: int, ctx: RowContext, token: str) -> None:
    cur.execute(
        """SELECT article_uom_role_id FROM article_uom_role_history
           WHERE article_id=%s AND uom_role=%s AND uom_id=%s AND role_status='CONFIRMED'
             AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP(6))
           ORDER BY article_uom_role_id LIMIT 1""",
        (article_id, role, uom_id),
    )
    row = cur.fetchone()
    if row:
        role_id = int(row['article_uom_role_id'])
    else:
        # Detect a conflicting active confirmed UOM for this explicit role.
        cur.execute(
            """SELECT au.article_uom_role_id,du.uom_code
               FROM article_uom_role_history au JOIN dim_uom du ON du.uom_id=au.uom_id
               WHERE au.article_id=%s AND au.uom_role=%s AND au.role_status='CONFIRMED'
                 AND (au.effective_to IS NULL OR au.effective_to>CURRENT_TIMESTAMP(6))""",
            (article_id, role),
        )
        active = cur.fetchall()
        if active:
            _qa_issue(
                cur, 'ARTICLE_UOM_ROLE_CONFLICT', 'ARTICLE', str(article_id),
                f'Explicit {role} UOM observation {token} conflicts with an existing active confirmed UOM.',
                ctx,
                expected={'uom': token}, observed={'existing_uoms': [r['uom_code'] for r in active]},
            )
            return
        cur.execute(
            """INSERT INTO article_uom_role_history
               (article_id,uom_role,uom_id,role_status,confidence)
               VALUES (%s,%s,%s,'CONFIRMED',1.0)""",
            (article_id, role, uom_id),
        )
        role_id = int(cur.lastrowid)
    _insert_evidence(cur, 'ARTICLE_UOM_ROLE', role_id, 'EXPLICIT_UOM_ROLE_SOURCE', ctx, value=token, extra={'role': role})


def _mark_row_state(cur, ctx: RowContext, status: str, detail: dict[str, Any]) -> None:
    cur.execute(
        """INSERT INTO phase2c_row_state
           (batch_id,file_id,sheet_id,raw_table_name,raw_id,source_row_number,normalization_status,detail_json)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE normalization_status=VALUES(normalization_status),detail_json=VALUES(detail_json),updated_at=CURRENT_TIMESTAMP(6)""",
        (ctx.batch_id, ctx.file_id, ctx.sheet_id, ctx.raw_table, ctx.raw_id, ctx.source_row_number, status,
         json.dumps(detail, ensure_ascii=False)),
    )


def _normalize_identity_row(cur, ctx: RowContext, row: dict[str, Any], colmap: dict[str, str]) -> str:
    article_number = _numeric_identifier(_get(row, colmap, 'article'))
    source_main_article = _numeric_identifier(_get(row, colmap, 'main_article'))
    raw_upc = _get(row, colmap, 'upc')
    ean_upc = (
        _article_manual_upc_identifier(raw_upc)
        if ctx.source_type == 'article_manual'
        else _numeric_identifier(raw_upc)
    )
    sales_set = _numeric_identifier(_get(row, colmap, 'sales_set'))
    description = _text(_get(row, colmap, 'description'))
    category = _text(_get(row, colmap, 'category'))
    pack = _text(_get(row, colmap, 'pack'))

    # On the confirmed Article Manual roster tabs, a UPC row may leave Column B
    # (Selling Article) blank. That means the Selling Article is the Column A
    # Family/Main Article; it is not an unmapped product row.
    if (
        ctx.source_type == 'article_manual'
        and not article_number
        and source_main_article
        and ean_upc
    ):
        article_number = source_main_article

    if not article_number:
        _mark_row_state(cur, ctx, 'SKIPPED_NON_PRODUCT_ROW', {'reason': 'no article identifier'})
        return 'SKIPPED_NON_PRODUCT_ROW'

    # User-confirmed exceptions: these specific articles are their own Main/Family when the source leaves Main blank.
    if not source_main_article and article_number in SELF_MAIN_ARTICLE_OVERRIDES:
        source_main_article = article_number

    # Monthly PI cannot override a verified Article Manual hierarchy.
    manual_family = _manual_article_family(cur, article_number) if ctx.source_type != 'article_manual' else None
    canonical_main_article = str(manual_family['main_article_number']) if manual_family else source_main_article

    if not canonical_main_article:
        _qa_issue(
            cur, 'MAIN_ARTICLE_MISSING', 'ARTICLE', article_number,
            f'Article {article_number} is present in an identity source row but Main/Family Article is missing.',
            ctx, observed={'article': article_number, 'sheet': ctx.sheet_name}, severity='CRITICAL',
        )
        _mark_row_state(cur, ctx, 'QA_HOLD', {'article': article_number, 'reason': 'main article missing'})
        return 'QA_HOLD'

    family_id = _ensure_family(cur, canonical_main_article, description, ctx)
    article_id = _ensure_article(cur, article_number, description, category, ctx)
    # Ensure the family anchor itself is a real MAIN article record.
    main_article_id = _ensure_article(cur, canonical_main_article, description, category, ctx)
    _, main_anchor_status = _ensure_article_family(cur, main_article_id, family_id, canonical_main_article, canonical_main_article, ctx)
    _, family_status = _ensure_article_family(cur, article_id, family_id, article_number, canonical_main_article, ctx)

    if source_main_article and source_main_article != canonical_main_article:
        _insert_evidence(
            cur, 'ARTICLE', article_id, 'SOURCE_MAIN_ARTICLE_OBSERVED', ctx, 'main_article', source_main_article,
            {'accepted_as_canonical': False, 'canonical_main_article': canonical_main_article},
        )
        _qa_issue(
            cur, 'SOURCE_HIERARCHY_CONFLICT', 'ARTICLE', article_number,
            f'Source reports Main Article {source_main_article} for Article {article_number}, but Article Manual resolves it to {canonical_main_article}. Canonical hierarchy was not changed.',
            ctx, expected={'main_article': canonical_main_article}, observed={'source_main_article': source_main_article}, severity='MEDIUM',
        )

    upc_status = None
    upc_id = None
    if ean_upc:
        upc_id = _ensure_upc(cur, ean_upc, description, ctx)
        manual_upc = _manual_upc_anchor(cur, upc_id) if ctx.source_type != 'article_manual' else None
        upc_anchor_id = main_article_id
        upc_anchor_article = canonical_main_article

        if manual_upc:
            upc_anchor_id = int(manual_upc['main_article_id'])
            upc_anchor_article = str(manual_upc['main_article_number'])
            if source_main_article and source_main_article != upc_anchor_article:
                _qa_issue(
                    cur, 'SOURCE_UPC_FAMILY_CONFLICT', 'UPC', ean_upc,
                    f'Source places UPC {ean_upc} under Main Article {source_main_article}, but Article Manual resolves the UPC to {upc_anchor_article}. Canonical UPC identity was not changed.',
                    ctx, expected={'main_article': upc_anchor_article}, observed={'source_main_article': source_main_article, 'row_article': article_number}, severity='MEDIUM',
                )
        elif ctx.source_type == 'monthly_pi_form' and source_main_article and source_main_article != canonical_main_article:
            # The PI row conflicts with the manual hierarchy for its Article and there is no manual UPC mapping
            # to arbitrate. Do not manufacture a canonical UPC link from an inconsistent row.
            _qa_issue(
                cur, 'UPC_FAMILY_UNRESOLVED', 'UPC', ean_upc,
                f'UPC {ean_upc} appears on a Monthly PI row whose Article hierarchy conflicts with Article Manual; no authoritative UPC family mapping is available.',
                ctx, expected={'authoritative_upc_family': 'Article Manual or verified mapping'},
                observed={'row_article': article_number, 'source_main_article': source_main_article, 'article_manual_main': canonical_main_article},
                severity='HIGH',
            )
            upc_status = 'QA_HOLD'
        else:
            _, upc_status = _ensure_article_upc(cur, upc_anchor_id, upc_id, upc_anchor_article, ean_upc, sales_set, ctx)

        if manual_upc:
            # Keep source observation, but only reinforce the already-authoritative manual anchor.
            _, upc_status = _ensure_article_upc(cur, upc_anchor_id, upc_id, upc_anchor_article, ean_upc, sales_set, ctx)

    # Explicit source UOM roles only. Pack text is evidence; no conversion is inferred from descriptions like 10/4LB.
    uom_fields = [
        ('base_uom', 'BASE_INVENTORY'),
        ('order_uom', 'ORDERING'),
        ('receiving_uom', 'RECEIVING'),
        ('cost_uom', 'COST'),
    ]
    for field, role in uom_fields:
        token = _source_token(_get(row, colmap, field))
        if not token:
            continue
        uom_id, canonical = _canonical_uom(cur, ctx.source_type, token)
        _insert_evidence(cur, 'ARTICLE', article_id, f'{role}_UOM_OBSERVED', ctx, field, token, {'canonical_exact_match': canonical})
        if uom_id is not None:
            _ensure_article_uom_role(cur, article_id, role, uom_id, ctx, token)
        else:
            _qa_issue(
                cur, 'UOM_TOKEN_UNRESOLVED', 'ARTICLE', article_number,
                f'Explicit {role} UOM token {token!r} is not in the canonical UOM dictionary.',
                ctx, observed={'source_uom': token, 'role': role}, severity='HIGH',
            )

    selling_token = _source_token(_get(row, colmap, 'selling_uom'))
    selling_rule = "EXPLICIT_SOURCE_UOM"
    selling_source_field = 'selling_uom'
    # User-confirmed Article Manual semantics for Fresh Fish / Live Fish /
    # Shrimp / Fish Ball / Frozen Fish: when a numeric EAN/UPC exists in D and
    # the same row has a Toledo# in C, that EAN/UPC is sold by pound. A Toledo-
    # only row with no D EAN/UPC is NOT covered by this rule (e.g. UPC 4816 has
    # separate explicit user authority: EA, 1 EA = 4 LB).
    if (
        ctx.source_type == 'article_manual'
        and _norm_header(ctx.sheet_name) in ARTICLE_MANUAL_RECEIVING_PACK_TABS
        and ean_upc
        and sales_set
    ):
        selling_token = 'LB'
        selling_rule = "ARTICLE_MANUAL_TOLEDO_EAN_LB"
        selling_source_field = 'C_TOLEDO_PLUS_D_EAN'

    if selling_token:
        selling_uom_id, canonical = _canonical_uom(cur, ctx.source_type, selling_token)
        target_type, target_id = ('SELLING_UPC', upc_id) if upc_id else ('ARTICLE', article_id)
        _insert_evidence(
            cur,
            target_type,
            int(target_id),
            'SELLING_UOM_OBSERVED',
            ctx,
            selling_source_field,
            selling_token,
            {
                'canonical_exact_match': canonical,
                'resolution_rule': selling_rule,
                'toledo_number': sales_set if selling_rule == 'ARTICLE_MANUAL_TOLEDO_EAN_LB' else None,
            },
        )
        if upc_id is not None and selling_uom_id is not None:
            cur.execute("SELECT uom_dimension FROM dim_uom WHERE uom_id=%s", (selling_uom_id,))
            dimrow = cur.fetchone()
            dimension = dimrow['uom_dimension'] if dimrow else None
            base_uom_id = selling_uom_id if dimension in {'WEIGHT','COUNT'} else None
            factor = 1 if base_uom_id is not None else None
            cur.execute(
                """SELECT upc_uom_id FROM selling_upc_uom_history
                   WHERE upc_id=%s AND selling_uom_id=%s
                     AND ((base_uom_id IS NULL AND %s IS NULL) OR base_uom_id=%s)
                     AND mapping_status='CONFIRMED'
                     AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP(6))
                   ORDER BY upc_uom_id DESC LIMIT 1""",
                (upc_id, selling_uom_id, base_uom_id, base_uom_id),
            )
            existing_uom = cur.fetchone()
            if not existing_uom:
                cur.execute(
                    """INSERT INTO selling_upc_uom_history
                       (upc_id,selling_uom_id,base_uom_id,base_qty_per_selling_unit,mapping_status,confidence,resolution_method)
                       VALUES (%s,%s,%s,%s,'CONFIRMED',1.0,%s)""",
                    (upc_id, selling_uom_id, base_uom_id, factor, selling_rule),
                )

    if pack:
        pack_extra: dict[str, Any] = {
            'note': 'Pack text retained as structured source evidence; conversion is applied only for user-confirmed tab semantics.'
        }
        parsed_pack = _structured_pack_weight(pack)
        if parsed_pack:
            pack_extra['structured_pack'] = {
                k: str(v) if isinstance(v, Decimal) else v
                for k, v in parsed_pack.items()
            }
        _insert_evidence(cur, 'ARTICLE', article_id, 'PACK_TEXT_OBSERVED', ctx, 'pack', pack, pack_extra)

        # Monthly PI Fresh/Live: D is Pack Size and E is Receiving Unit.
        # An explicit structured weight pack (e.g. 60LB or 1/60LB) establishes
        # LB as Base UOM and the full pack weight per Receiving Unit. This is a
        # source-schema rule, not a
        # description-text inference.
        if (
            ctx.source_type == 'monthly_pi_form'
            and (
                _norm_header(ctx.sheet_name) == 'fresh'
                or _norm_header(ctx.sheet_name).startswith('fresh ')
                or _norm_header(ctx.sheet_name) == 'live'
                or _norm_header(ctx.sheet_name).startswith('live ')
            )
            and parsed_pack
        ):
            receiving_token = _source_token(_get(row, colmap, 'receiving_uom'))
            base_token = str(parsed_pack.get('base_uom') or '')
            base_uom_id, base_canonical = _canonical_uom(cur, ctx.source_type, base_token)
            if base_uom_id is not None:
                _ensure_article_uom_role(cur, article_id, 'BASE_INVENTORY', base_uom_id, ctx, base_token)
            _insert_evidence(
                cur,
                'ARTICLE',
                article_id,
                'RECEIVING_PACK_CONVERSION_OBSERVED',
                ctx,
                'pack',
                pack,
                {
                    'receiving_uom': receiving_token,
                    'base_uom': base_canonical or base_token,
                    'base_qty_per_receiving_unit': str(parsed_pack['total_base_qty']),
                    'resolution_rule': 'MONTHLY_PI_FRESH_LIVE_D_PACK_E_RECEIVING',
                },
            )

    status = 'NORMALIZED'
    if family_status == 'QA_HOLD' or main_anchor_status == 'QA_HOLD' or upc_status == 'QA_HOLD':
        status = 'QA_HOLD'
    _mark_row_state(
        cur, ctx, status,
        {'article': article_number, 'source_main_article': source_main_article, 'canonical_main_article': canonical_main_article,
         'upc': ean_upc, 'sales_set': sales_set, 'pack': pack,
         'selling_uom_rule': selling_rule if selling_token else None,
         'family_status': family_status, 'upc_status': upc_status},
    )
    return status



def _preload_article_manual_authority(cur, batch_id: int) -> dict[str, Any]:
    """
    Build authoritative Article Manual hierarchy first, then build an authoritative
    UPC->Main/Family index from Article Manual roster sheets.

    The Article Manual uses two complementary layouts:
      1) Link sheet: Sub Article -> Main Article hierarchy.
      2) Product roster sheets: Article/Main Article + numeric EAN/UPC rows.

    Only UPCs that resolve to exactly one family across the Article Manual are promoted
    to authoritative canonical mappings. Cross-family manual duplicates are retained
    as MEDIUM QA observations and are not assigned an arbitrary canonical family.
    """
    stats = {
        'hierarchy_rows_preloaded': 0,
        'manual_upc_rows_seen': 0,
        'manual_upcs_unique': 0,
        'manual_upcs_ambiguous': 0,
        'manual_upc_links_confirmed': 0,
    }

    cur.execute(
        """SELECT file_id,source_type,original_filename FROM ingest_file
           WHERE batch_id=%s AND source_type='article_manual'
           ORDER BY file_id""",
        (batch_id,),
    )
    manual_files = cur.fetchall()
    if not manual_files:
        return stats

    sheet_infos: list[dict[str, Any]] = []
    for f in manual_files:
        cur.execute(
            """SELECT sheet_id,sheet_name,header_row_number,sheet_index FROM ingest_sheet
               WHERE file_id=%s ORDER BY sheet_index""",
            (f['file_id'],),
        )
        for sh in cur.fetchall():
            header_row = sh['header_row_number']
            if not header_row:
                continue
            cur.execute(
                """SELECT raw_id,raw_payload FROM raw_article_manual
                   WHERE sheet_id=%s AND source_row_number=%s LIMIT 1""",
                (sh['sheet_id'], header_row),
            )
            h = cur.fetchone()
            if not h:
                continue
            colmap = _article_manual_column_map(
                sh['sheet_name'],
                _json_obj(h['raw_payload']),
            )
            sheet_infos.append({
                'file_id': int(f['file_id']),
                'sheet_id': int(sh['sheet_id']),
                'sheet_name': sh['sheet_name'],
                'header_row': int(header_row),
                'colmap': colmap,
            })

    # Pass A: authoritative Sub -> Main hierarchy.
    for info in sheet_infos:
        colmap = info['colmap']
        if 'article' not in colmap or 'main_article' not in colmap:
            continue
        cur.execute(
            """SELECT raw_id,source_row_number,raw_payload FROM raw_article_manual
               WHERE sheet_id=%s AND source_row_number>%s ORDER BY source_row_number""",
            (info['sheet_id'], info['header_row']),
        )
        for rr in cur.fetchall():
            ctx = RowContext(
                batch_id=batch_id,
                file_id=info['file_id'],
                sheet_id=info['sheet_id'],
                raw_table='raw_article_manual',
                raw_id=int(rr['raw_id']),
                source_row_number=int(rr['source_row_number']),
                source_type='article_manual',
                sheet_name=info['sheet_name'],
            )
            cur.execute(
                """SELECT normalization_status FROM phase2c_row_state
                   WHERE raw_table_name='raw_article_manual' AND raw_id=%s""",
                (rr['raw_id'],),
            )
            if not cur.fetchone():
                _normalize_identity_row(cur, ctx, _json_obj(rr['raw_payload']), colmap)
                stats['hierarchy_rows_preloaded'] += 1

    # Pass B: collect numeric Article Manual UPC roster observations.
    candidates: dict[str, list[dict[str, Any]]] = {}
    for info in sheet_infos:
        colmap = info['colmap']
        if 'upc' not in colmap or ('article' not in colmap and 'main_article' not in colmap):
            continue
        cur.execute(
            """SELECT raw_id,source_row_number,raw_payload FROM raw_article_manual
               WHERE sheet_id=%s AND source_row_number>%s ORDER BY source_row_number""",
            (info['sheet_id'], info['header_row']),
        )
        for rr in cur.fetchall():
            payload = _json_obj(rr['raw_payload'])
            ean_upc = _article_manual_upc_identifier(_get(payload, colmap, 'upc'))
            if not ean_upc:
                continue
            anchor_article = (
                _numeric_identifier(_get(payload, colmap, 'article'))
                or _numeric_identifier(_get(payload, colmap, 'main_article'))
            )
            if not anchor_article:
                continue

            manual_family = _manual_article_family(cur, anchor_article)
            canonical_main = str(manual_family['main_article_number']) if manual_family else anchor_article
            key = _numeric_key(ean_upc) or ean_upc
            ctx = RowContext(
                batch_id=batch_id,
                file_id=info['file_id'],
                sheet_id=info['sheet_id'],
                raw_table='raw_article_manual',
                raw_id=int(rr['raw_id']),
                source_row_number=int(rr['source_row_number']),
                source_type='article_manual',
                sheet_name=info['sheet_name'],
            )
            candidates.setdefault(key, []).append({
                'ean_upc': ean_upc,
                'canonical_main': canonical_main,
                'ctx': ctx,
                'description': _text(_get(payload, colmap, 'description')),
                'category': _text(_get(payload, colmap, 'category')),
                'sales_set': _numeric_identifier(_get(payload, colmap, 'sales_set')),
            })
            stats['manual_upc_rows_seen'] += 1

    # Pass C: promote only unambiguous manual UPC identities.
    for key, rows in candidates.items():
        families = sorted({r['canonical_main'] for r in rows})
        if len(families) != 1:
            stats['manual_upcs_ambiguous'] += 1
            first = rows[0]
            _qa_issue(
                cur,
                'ARTICLE_MANUAL_UPC_AMBIGUOUS',
                'UPC',
                first['ean_upc'],
                f'Article Manual contains UPC {first["ean_upc"]} under more than one Main/Family Article; no canonical UPC family was chosen.',
                first['ctx'],
                expected={'one_canonical_family': True},
                observed={'candidate_main_articles': families},
                severity='MEDIUM',
            )
            continue

        canonical_main = families[0]
        stats['manual_upcs_unique'] += 1
        family_id = _ensure_family(cur, canonical_main, rows[0]['description'], rows[0]['ctx'])
        main_article_id = _ensure_article(cur, canonical_main, rows[0]['description'], rows[0]['category'], rows[0]['ctx'])
        _ensure_article_family(
            cur, main_article_id, family_id, canonical_main, canonical_main, rows[0]['ctx']
        )

        for r in rows:
            upc_id = _ensure_upc(cur, r['ean_upc'], r['description'], r['ctx'])
            _, status = _ensure_article_upc(
                cur, main_article_id, upc_id, canonical_main, r['ean_upc'], r['sales_set'], r['ctx']
            )
            if status == 'CONFIRMED':
                stats['manual_upc_links_confirmed'] += 1

    return stats


def normalize_batch(batch_id: int) -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT processing_status FROM ingest_batch WHERE batch_id=%s", (batch_id,))
            batch = cur.fetchone()
            if not batch:
                raise KeyError(f'Batch {batch_id} not found')
            if batch['processing_status'] not in {'RAW_RELEASED', 'RELEASED', 'PHASE2C_QA_HOLD', 'PHASE2C_READY'}:
                raise RuntimeError(f'Batch {batch_id} is not RAW released; current status={batch["processing_status"]}')

            cur.execute(
                """INSERT INTO pipeline_run
                   (batch_id,pipeline_name,stage_name,run_number,processing_status,code_version)
                   VALUES (%s,'FULL_MYSQL_SEAFOOD','PHASE2C_IDENTITY_UOM',1,'STARTED','local-agent-v6.6.0')""",
                (batch_id,),
            )
            pipeline_run_id = int(cur.lastrowid)

            manual_authority_preload = _preload_article_manual_authority(cur, batch_id)

            normalized = held = skipped = source_rows = 0
            source_files = 0
            processed_sheets = 0

            cur.execute(
                """SELECT file_id,source_type,original_filename FROM ingest_file
                   WHERE batch_id=%s AND source_type IN ('monthly_pi_form','article_manual')
                   ORDER BY CASE source_type WHEN 'article_manual' THEN 0 ELSE 1 END, file_id""",
                (batch_id,),
            )
            files = cur.fetchall()
            source_files = len(files)

            for f in files:
                raw_table = IDENTITY_SOURCES[f['source_type']]
                cur.execute(
                    """SELECT sheet_id,sheet_name,header_row_number FROM ingest_sheet
                       WHERE file_id=%s ORDER BY sheet_index""",
                    (f['file_id'],),
                )
                sheets = cur.fetchall()
                for sh in sheets:
                    header_row = sh['header_row_number']
                    if not header_row:
                        continue
                    cur.execute(
                        f"SELECT raw_id,raw_payload FROM {raw_table} WHERE sheet_id=%s AND source_row_number=%s LIMIT 1",
                        (sh['sheet_id'], header_row),
                    )
                    h = cur.fetchone()
                    if not h:
                        continue
                    colmap = (
                        _article_manual_column_map(
                            sh['sheet_name'],
                            _json_obj(h['raw_payload']),
                        )
                        if f['source_type'] == 'article_manual'
                        else _monthly_pi_column_map(
                            sh['sheet_name'],
                            _json_obj(h['raw_payload']),
                        )
                    )
                    # Only treat sheets with explicit Article + Main Article headers as product-identity sheets.
                    if 'article' not in colmap or 'main_article' not in colmap:
                        continue
                    processed_sheets += 1
                    cur.execute(
                        f"""SELECT raw_id,source_row_number,raw_payload FROM {raw_table}
                            WHERE sheet_id=%s AND source_row_number>%s ORDER BY source_row_number""",
                        (sh['sheet_id'], header_row),
                    )
                    for rr in cur.fetchall():
                        source_rows += 1
                        ctx = RowContext(
                            batch_id=batch_id, file_id=int(f['file_id']), sheet_id=int(sh['sheet_id']),
                            raw_table=raw_table, raw_id=int(rr['raw_id']), source_row_number=int(rr['source_row_number']),
                            source_type=f['source_type'], sheet_name=sh['sheet_name'],
                        )
                        cur.execute(
                            "SELECT normalization_status FROM phase2c_row_state WHERE raw_table_name=%s AND raw_id=%s",
                            (raw_table, rr['raw_id']),
                        )
                        already = cur.fetchone()
                        if already:
                            st = already['normalization_status']
                        else:
                            st = _normalize_identity_row(cur, ctx, _json_obj(rr['raw_payload']), colmap)
                        if st == 'NORMALIZED':
                            normalized += 1
                        elif st == 'QA_HOLD':
                            held += 1
                        else:
                            skipped += 1

            cur.execute(
                """SELECT COUNT(*) AS c FROM qa_identity_uom_issue
                   WHERE batch_id=%s AND issue_status='OPEN' AND UPPER(severity) IN ('HIGH','CRITICAL')""",
                (batch_id,),
            )
            blocking = int(cur.fetchone()['c'])

            result_status = 'QA_HOLD' if blocking else 'READY'
            cur.execute(
                """INSERT INTO phase2c_batch_result
                   (batch_id,source_file_count,processed_sheet_count,source_row_count,normalized_row_count,
                    qa_hold_row_count,skipped_row_count,blocking_issue_count,result_status,detail_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                     source_file_count=VALUES(source_file_count),processed_sheet_count=VALUES(processed_sheet_count),
                     source_row_count=VALUES(source_row_count),normalized_row_count=VALUES(normalized_row_count),
                     qa_hold_row_count=VALUES(qa_hold_row_count),skipped_row_count=VALUES(skipped_row_count),
                     blocking_issue_count=VALUES(blocking_issue_count),result_status=VALUES(result_status),
                     detail_json=VALUES(detail_json),updated_at=CURRENT_TIMESTAMP(6)""",
                (
                    batch_id, source_files, processed_sheets, source_rows, normalized, held, skipped, blocking, result_status,
                    json.dumps({'identity_sources_present': bool(source_files), 'manual_authority_preload': manual_authority_preload}, ensure_ascii=False),
                ),
            )
            batch_status = 'PHASE2C_QA_HOLD' if blocking else 'PHASE2C_READY'
            cur.execute("UPDATE ingest_batch SET processing_status=%s WHERE batch_id=%s", (batch_status, batch_id))
            cur.execute(
                """UPDATE pipeline_run SET processing_status=%s,completed_at=CURRENT_TIMESTAMP(6),
                   rows_read=%s,rows_inserted=%s,rows_rejected=%s,error_count=%s,detail_json=%s
                   WHERE pipeline_run_id=%s""",
                (
                    'FAILED_QA' if blocking else 'COMPLETED', source_rows, normalized, held, blocking,
                    json.dumps({'source_files': source_files, 'processed_sheets': processed_sheets, 'skipped': skipped, 'manual_authority_preload': manual_authority_preload}, ensure_ascii=False),
                    pipeline_run_id,
                ),
            )
            conn.commit()
            return {
                'batch_id': batch_id,
                'status': batch_status,
                'source_files': source_files,
                'processed_sheets': processed_sheets,
                'source_rows': source_rows,
                'normalized_rows': normalized,
                'qa_hold_rows': held,
                'skipped_rows': skipped,
                'blocking_issues': blocking,
                'manual_authority_preload': manual_authority_preload,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def audit_phase2c(batch_id: int) -> dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM phase2c_batch_result WHERE batch_id=%s", (batch_id,))
        result = cur.fetchone()
        if not result:
            cur.close()
            return {'batch_id': batch_id, 'pass': False, 'reason': 'Phase 2C has not run.'}
        cur.execute(
            """SELECT issue_id,severity,issue_code,entity_type,entity_key,issue_summary,file_id,sheet_id,raw_table_name,raw_id
               FROM qa_identity_uom_issue
               WHERE batch_id=%s AND issue_status='OPEN'
               ORDER BY FIELD(UPPER(severity),'CRITICAL','HIGH','MEDIUM','LOW'),issue_id""",
            (batch_id,),
        )
        issues = cur.fetchall()
        cur.close()
    blocking = [i for i in issues if str(i['severity']).upper() in {'CRITICAL', 'HIGH'}]
    return {
        'batch_id': batch_id,
        'pass': len(blocking) == 0 and result['result_status'] == 'READY',
        'result': result,
        'blocking_issues': blocking,
        'all_open_issues': issues,
    }
