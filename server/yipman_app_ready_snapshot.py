from __future__ import annotations

"""Atomic App Ready snapshot contract for Yipman."""
from dataclasses import dataclass,field
from datetime import datetime,timezone
from threading import RLock
from typing import Any,Callable
import uuid
APP_READY_STAGES=('PUBLISH','PRECALCULATE','PREANALYZE','BUILD_SNAPSHOT','APP_READY')
SNAPSHOT_SECTIONS=('stock_flow','quick_check','ordering_regular','ordering_promotion','price_reg','price_tpr_suggestions','price_tpr_progress','price_clearance','inventory','performance','decision_intelligence')
@dataclass
class SnapshotBuild:
    build_id:str;source_batch_id:str|None;data_through:str|None;stage:str='PUBLISH';started_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat());completed_at:str|None=None;sections:dict[str,Any]=field(default_factory=dict);section_status:dict[str,str]=field(default_factory=dict);error:str|None=None
class AppReadySnapshotStore:
    def __init__(self):self._lock=RLock();self._active=None;self._building=None
    def begin(self,*,source_batch_id=None,data_through=None):
        with self._lock:self._building=SnapshotBuild(str(uuid.uuid4()),source_batch_id,data_through,section_status={n:'PENDING' for n in SNAPSHOT_SECTIONS});return self._building
    def set_stage(self,stage):
        if stage not in APP_READY_STAGES:raise ValueError(f'Unknown App Ready stage: {stage}')
        with self._lock:
            if not self._building:raise RuntimeError('No App Ready build in progress')
            self._building.stage=stage
    def put_section(self,name,payload):
        if name not in SNAPSHOT_SECTIONS:raise ValueError(f'Unknown App Ready section: {name}')
        with self._lock:
            if not self._building:raise RuntimeError('No App Ready build in progress')
            self._building.sections[name]=payload;self._building.section_status[name]='READY'
    def fail_section(self,name,error):
        with self._lock:
            if not self._building:raise RuntimeError('No App Ready build in progress')
            self._building.section_status[name]='FAILED';self._building.error=error
    def promote(self):
        with self._lock:
            if not self._building:raise RuntimeError('No App Ready build in progress')
            missing=[n for n in SNAPSHOT_SECTIONS if self._building.section_status.get(n)!='READY']
            if missing:raise RuntimeError('Snapshot is not complete: '+', '.join(missing))
            self._building.stage='APP_READY';self._building.completed_at=datetime.now(timezone.utc).isoformat();self._active=self._building;self._building=None;return self._active
    def active(self):
        with self._lock:return self._active
    def status(self):
        with self._lock:
            b=self._building;a=self._active
            if not b and not a:return {'status':'NO_SNAPSHOT','stage':None,'app_ready':False}
            current=b or a;ready=sum(v=='READY' for v in current.section_status.values())
            return {'status':'BUILDING' if b else 'APP_READY','stage':current.stage,'app_ready':a is not None,'serving_build_id':a.build_id if a else None,'serving_data_through':a.data_through if a else None,'build_id':current.build_id,'source_batch_id':current.source_batch_id,'data_through':current.data_through,'sections_ready':ready,'sections_total':len(SNAPSHOT_SECTIONS),'sections':dict(current.section_status),'started_at':current.started_at,'completed_at':current.completed_at,'error':current.error}
APP_READY_SNAPSHOTS=AppReadySnapshotStore()
def build_app_ready_snapshot(builders:dict[str,Callable[[],Any]],*,source_batch_id=None,data_through=None):
    APP_READY_SNAPSHOTS.begin(source_batch_id=source_batch_id,data_through=data_through);APP_READY_SNAPSHOTS.set_stage('PRECALCULATE')
    analyze={'price_reg','price_tpr_suggestions','price_tpr_progress','price_clearance','performance','decision_intelligence'}
    for name in SNAPSHOT_SECTIONS:
        if name in analyze and APP_READY_SNAPSHOTS.status().get('stage')!='PREANALYZE':APP_READY_SNAPSHOTS.set_stage('PREANALYZE')
        builder=builders.get(name)
        if builder is None:APP_READY_SNAPSHOTS.fail_section(name,'BUILDER_NOT_REGISTERED');raise RuntimeError(f'App Ready builder not registered: {name}')
        try:APP_READY_SNAPSHOTS.put_section(name,builder())
        except Exception as exc:APP_READY_SNAPSHOTS.fail_section(name,f'{type(exc).__name__}: {exc}');raise
    APP_READY_SNAPSHOTS.set_stage('BUILD_SNAPSHOT');return APP_READY_SNAPSHOTS.promote()
