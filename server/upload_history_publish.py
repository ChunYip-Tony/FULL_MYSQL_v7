"""Upload-triggered retained history publication on the existing bridge transport."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from price_history_analysis import HEADERS, HISTORY_CONTRACT, build_upload_history, read_retained_tables, verify_history_tables, preserve_unchanged_lineage


def publish_upload_history(*, rows, source_days, batch_id, through, reader, writer):
 # Preflight every retained table before replacing any history. A bridge which
 # has not enabled ANALYSIS_* fails explicitly instead of silently claiming PASS.
 old=read_retained_tables(reader)
 output,audit=build_upload_history(rows,old,source_days,batch_id,through)
 output=preserve_unchanged_lineage(output,old)
 status=[['Field','Value'],['Schema','DEPARTMENT_ANALYSIS_V1'],
  ['Source revision',audit['revision']],['Data through',through],
  ['Built at UTC',datetime.now(timezone.utc).isoformat()],['Write verification','PUBLISHING'],
  ['History completeness','PARTIAL_AUDITED_WITH_EXPLICIT_SOURCE_GAPS'],
  ['History UPCs',audit['requested_upcs']],['Histories refreshed',audit['upcs_refreshed']],
  ['Episodes retained',audit['episode_rows']],['Performance qualified episodes',audit['supported_episodes']],
  ['Availability','UNKNOWN unless separately verified'],['Before-after comparisons',audit['before_after_comparisons']],
  ['Fully supported comparisons',audit['fully_supported_comparisons']],
  ['Partial observed comparisons',audit['before_after_comparisons']-audit['fully_supported_comparisons']],
  ['Refresh contract',HISTORY_CONTRACT],['Source batch',batch_id],
  ['Comparison basis','Current-cost normalized; supported POS dates only; no family allocation'],
  ['Coverage gaps',json.dumps(audit['gaps'],sort_keys=True)],
  ['Item verification contract','ITEM_PERFORMANCE_VERIFICATION_V2'],
  ['Uploaded-scope verified sales',audit.get('verification',{}).get('uploaded_sales_verified',0)],
  ['Uploaded-scope verified GP',audit.get('verification',{}).get('uploaded_gp_verified',0)],
  ['Uploaded-scope fully verified',audit.get('verification',{}).get('uploaded_fully_verified',0)],
  ['Item verification',json.dumps(audit.get('verification',{}),sort_keys=True)],
  ['Fully verified items',audit.get('verification',{}).get('fully_verified',0)],
  ['Items requiring evidence',audit.get('verification',{}).get('unresolved_items',0)],
  ['Sales and achieved selling price authority','POS_ONLY; average price requires verified POS selling quantity'],
  ['Price episode and event values','PRICE_LIST_REFERENCE_WINDOWS; not evidence of achieved selling price or causal price lift'],
  ['Inventory evidence authority','MVT signed quantities and posted costs; no MVT sales revenue; family movement never allocated to UPCs'],
  ['Aggregation rule','POS source detail and daily totals are alternative grains of the same sales. Inventory GP adjustments are derived from MVT detail. Never add both views.']]
 status.extend([['Source eligibility contract','POS_SOURCE_ELIGIBILITY_V1'],['Source eligibility',json.dumps(audit.get('source_quality',{}),sort_keys=True)]])
 writer('ANALYSIS_STATUS',status)
 try:
  for title,matrix in output.items():writer(title,matrix,previous=old[title])
  readback=verify_history_tables(output,reader)
  status[5][1]='VERIFIED'
  writer('ANALYSIS_STATUS',status)
  if reader('ANALYSIS_STATUS',1,len(status),2)!=status:
   # Sheets may return numbers as strings: status contract is checked separately.
   got={str(r[0]):str(r[1]) if len(r)>1 else '' for r in reader('ANALYSIS_STATUS',1,len(status),2) if r}
   if got.get('Write verification')!='VERIFIED' or got.get('Source revision')!=audit['revision']:
    raise ValueError('History status readback mismatch')
  return {'status':'PASS',**audit,'readback':readback}
 except Exception:
  status[5][1]='FAILED'
  try:writer('ANALYSIS_STATUS',status)
  except Exception:pass
  raise


