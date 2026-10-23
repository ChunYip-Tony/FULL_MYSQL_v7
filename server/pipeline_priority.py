"""Keep optional snapshot warmups behind unfinished ingest and Google publication."""
import time
from db import db_conn


def pipeline_pending():
    with db_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""SELECT EXISTS(SELECT 1 FROM ingest_batch
                            WHERE processing_status='PHASE2C_READY')
                        OR EXISTS(SELECT 1 FROM pipeline_run
                            WHERE stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN','CHATGPT_SHEET_PUBLISH')
                              AND processing_status IN ('QUEUED','STARTED','PAUSE_REQUESTED'))""")
            return bool(cur.fetchone()[0])
        finally:
            cur.close()


def wait_for_pipeline_idle():
    # Used only on background warmup threads, never an HTTP request thread.
    while True:
        try:
            if not pipeline_pending():
                return
        except Exception:
            pass
        time.sleep(30)

