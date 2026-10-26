from __future__ import annotations

from sites_cutover_gate import require_worker_enabled
require_worker_enabled()

import json
from datetime import datetime, timezone

import worker as _worker
from v7_ingest import API_PIPELINE, API_VERSION
from chatgpt_daily_gp_v493 import (
    apply_chatgpt_daily_gp_v493,
    publish_chatgpt_snapshot_v493,
)


"""v7.0.482 worker convergence patch + v7.0.493 ChatGPT daily GP fix.

A batch whose authoritative ingest_batch status is PHASE2C_READY still requires
Phase 3, regardless of whether an older/stale phase3_batch_result row exists.
The prior orphan-recovery query required phase3_batch_result to be absent. That
could strand a batch after Phase 2C was rerun/reset while a previous Phase 3
result row remained.

v7.0.493 additionally guarantees that the async ChatGPT Sheet publisher resolves
completed-day selling-unit cost independently for every UPC. Family-level cost
authority remains shared, but an already-converted LB/PACK/CASE cost is never
reused across sibling UPCs.
"""


# worker.py imported the publisher by value. Patch the bridge helper and then
# replace that worker-level publisher alias explicitly so production execution
# is guaranteed to pass through the corrected v493 entrypoint.
apply_chatgpt_daily_gp_v493()
_worker.publish_chatgpt_snapshot = publish_chatgpt_snapshot_v493


def _queue_orphaned_phase2c_ready(cur) -> int:
    # PHASE2C_READY is the authoritative state transition contract: Phase 2C is
    # complete and Phase 3 still has to converge. A stale phase3_batch_result
    # must never suppress recovery. No active run + PHASE2C_READY => queue a
    # Phase 3 rerun, subject to the existing bounded retry policy.
    cur.execute(
        """SELECT ib.batch_id,
                  EXISTS(
                      SELECT 1
                      FROM phase3_batch_result p3
                      WHERE p3.batch_id=ib.batch_id
                  ) AS stale_phase3_result_present
           FROM ingest_batch ib
           WHERE ib.processing_status='PHASE2C_READY'
             AND NOT EXISTS (
                 SELECT 1
                 FROM pipeline_run active
                 WHERE active.batch_id=ib.batch_id
                   AND active.pipeline_name=%s
                   AND active.stage_name IN ('POST_RAW_PIPELINE','PHASE3_RERUN')
                   AND active.processing_status IN ('QUEUED','STARTED','PAUSE_REQUESTED')
             )
             AND (
                 SELECT COUNT(*)
                 FROM pipeline_run prior
                 WHERE prior.batch_id=ib.batch_id
                   AND prior.pipeline_name=%s
                   AND prior.stage_name='PHASE3_RERUN'
                   AND prior.code_version=%s
                   AND prior.processing_status IN (
                       'FAILED','FAILED_QA','QA_HOLD','ABORTED','PAUSED','COMPLETED'
                   )
             ) < 3
           ORDER BY ib.batch_id""",
        (API_PIPELINE, API_PIPELINE, API_VERSION),
    )

    queued = 0
    for row in cur.fetchall():
        bid = int(row['batch_id'])
        run_number = _worker._next_run_number(cur, bid, 'PHASE3_RERUN')
        detail = {
            'auto_recovery': True,
            'reason': 'ORPHANED_PHASE2C_READY_V482',
            'queued_at': datetime.now(timezone.utc).isoformat(),
            'required_code_version': API_VERSION,
            'stale_phase3_result_present': bool(row.get('stale_phase3_result_present')),
            'convergence_rule': 'PHASE2C_READY_ALWAYS_REQUIRES_PHASE3',
        }
        cur.execute(
            """INSERT INTO pipeline_run
               (batch_id,pipeline_name,stage_name,run_number,
                processing_status,code_version,detail_json)
               VALUES (%s,%s,'PHASE3_RERUN',%s,'QUEUED',%s,%s)""",
            (
                bid,
                API_PIPELINE,
                run_number,
                API_VERSION,
                json.dumps(detail, ensure_ascii=False),
            ),
        )
        queued += 1
    return queued


_worker._queue_orphaned_phase2c_ready = _queue_orphaned_phase2c_ready


if __name__ == '__main__':
    _worker.main()

