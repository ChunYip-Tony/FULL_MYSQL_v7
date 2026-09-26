from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator, Any
from config import get_settings

REQUIRED_PHASE1_TABLES = {
    'ingest_batch','ingest_file','ingest_sheet','ingest_column','pipeline_run','ingest_error',
    'raw_movement','raw_price_list','raw_sales_by_price_type','raw_on_hand','raw_frozen_inventory',
    'raw_tx_seafood_abc_price','raw_live_fresh_suggestion','raw_article_manual','raw_monthly_pi_form','raw_unclassified'
}
REQUIRED_PHASE2A_TABLES = {
    'dim_uom','uom_source_alias','product_family','article','selling_upc','bridge_article_family','bridge_article_upc',
    'normalized_source_evidence','article_uom_role_history','uom_conversion_observation','article_uom_conversion',
    'selling_upc_uom_history','article_cost_observation','receiving_observation','qa_identity_uom_issue'
}
REQUIRED_PHASE2C_TABLES = {'phase2c_row_state','phase2c_batch_result'}
REQUIRED_PHASE3_TABLES = {
    'sales_period_observation','price_list_observation','movement_history','family_movement_observation',
    'inventory_observation','company_price_observation','qa_phase3_issue','phase3_batch_result','quick_check_current'
}

@contextmanager
def db_conn() -> Iterator[Any]:
    import mysql.connector
    s = get_settings(); d = s.db_parts(); ca = s.ca_path()
    kwargs = dict(host=d['host'], port=d['port'], user=d['user'], password=d['password'], database=d['database'],
                  autocommit=False, connection_timeout=20, charset='utf8mb4', use_unicode=True)
    if ca:
        kwargs.update(ssl_ca=str(ca), ssl_verify_cert=True, ssl_verify_identity=True)
    conn = mysql.connector.connect(**kwargs)
    try:
        yield conn
    finally:
        conn.close()

def test_database() -> dict[str, Any]:
    with db_conn() as conn:
        cur=conn.cursor(); cur.execute('SELECT DATABASE(), VERSION(), CURRENT_USER()'); database,version,user=cur.fetchone()
        cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()")
        present={r[0] for r in cur.fetchall()}; cur.close()
    m1=sorted(REQUIRED_PHASE1_TABLES-present); m2=sorted(REQUIRED_PHASE2A_TABLES-present); m2c=sorted(REQUIRED_PHASE2C_TABLES-present); m3=sorted(REQUIRED_PHASE3_TABLES-present)
    return {'database':database,'version':version,'user':user,'phase1_schema_ready':not m1,'phase2a_schema_ready':not m2,
            'phase2c_schema_ready':not m2c,'phase3_schema_ready':not m3,'missing_phase1_tables':m1,
            'missing_phase2a_tables':m2,'missing_phase2c_tables':m2c,'missing_phase3_tables':m3}
