from __future__ import annotations
import json,os,shutil,time,traceback
from datetime import datetime
from pathlib import Path
from config import APP_DIR,get_settings
from api_client import post_json,upload,get
ALLOWED={'.xls','.xlsx','.csv','.txt'}; PID=APP_DIR/'agent.pid'; STATUS=APP_DIR/'agent_status.json'; QUEUE=APP_DIR/'client_queue.json'; LOG=APP_DIR/'logs'
TERMINAL_GOOD={'QUICK_CHECK_READY'}; TERMINAL_BAD={'QA_HOLD','PHASE2C_QA_HOLD','PHASE3_QA_HOLD','FAILED','FATAL'}
def log(m):
    LOG.mkdir(exist_ok=True); (LOG/f'client-{datetime.now():%Y-%m-%d}.log').open('a',encoding='utf-8').write(f'{datetime.now().isoformat(timespec="seconds")} | {m}\n')
def status(**kw): STATUS.write_text(json.dumps({'updated_at':datetime.now().isoformat(timespec='seconds'),**kw},indent=2,default=str),encoding='utf-8')
def stable(directory,seen,secs):
    now=time.time(); ready=[]; names=set()
    for p in directory.iterdir():
        if not p.is_file() or p.suffix.lower() not in ALLOWED: continue
        names.add(str(p)); st=p.stat(); prev=seen.get(str(p)); sig=(st.st_size,st.st_mtime)
        if prev is None or (prev[0],prev[1])!=sig: seen[str(p)]=(st.st_size,st.st_mtime,now); continue
        if now-prev[2]>=secs: ready.append(p)
    for k in list(seen):
        if k not in names: seen.pop(k,None)
    return sorted(ready,key=lambda p:(p.stat().st_mtime,p.name.lower()))
def loadq():
    try:return json.loads(QUEUE.read_text(encoding='utf-8'))
    except:return None
def saveq(q): QUEUE.write_text(json.dumps(q,indent=2),encoding='utf-8')
def clearq(): QUEUE.unlink(missing_ok=True)
def move(files,dst,batch_id):
    d=dst/f'Batch_{batch_id}_{datetime.now():%Y%m%d_%H%M%S}'; d.mkdir(parents=True,exist_ok=True)
    for name in files:
        p=Path(name)
        if p.exists(): shutil.move(str(p),str(d/p.name))
def poll_pending(q):
    s=get_settings(); sid=q['session_id']; r=get(f'/v1/batches/{sid}',timeout=30); st=r['batch']['processing_status']; bid=r['batch']['batch_id']; status(state=st,batch_id=bid,session_id=sid,files=[Path(x).name for x in q['files']],server=r)
    if st in TERMINAL_GOOD: move(q['files'],s.path(s.archive_dir),bid); clearq(); return True
    if st in TERMINAL_BAD: move(q['files'],s.path(s.failed_dir),bid); clearq(); return True
    return False
def process(files):
    s=get_settings(); create=post_json('/v1/batches',{'label':f'Seafood HTTPS batch {datetime.now().isoformat(timespec="minutes")}'})
    sid=create['session_id']; q={'session_id':sid,'batch_id':create['batch_id'],'files':[str(p) for p in files],'uploaded':[]}; saveq(q); status(state='UPLOADING_HTTPS',session_id=sid,files=[p.name for p in files])
    for p in files:
        r=upload(sid,p); q['uploaded'].append({'file':p.name,'result':r}); saveq(q); status(state='UPLOADING_HTTPS',session_id=sid,last_file=p.name,uploaded=len(q['uploaded']),total=len(files))
    c=post_json(f'/v1/batches/{sid}/commit'); q['commit']=c; saveq(q); status(state='SERVER_PROCESSING',session_id=sid,batch_id=c['batch_id'])
def main():
    s=get_settings(); [p.mkdir(parents=True,exist_ok=True) for p in [s.path(s.incoming_dir),s.path(s.archive_dir),s.path(s.failed_dir),LOG]]; PID.write_text(str(os.getpid()))
    try:
        get('/v1/status'); status(state='WATCHING_HTTPS',incoming=str(s.path(s.incoming_dir))); seen={}; sig0=None; since=None
        while True:
            q=loadq()
            if q:
                try: poll_pending(q)
                except Exception as e: status(state='POLL_ERROR',error=str(e),session_id=q.get('session_id'))
                time.sleep(max(3,s.poll_seconds)); continue
            files=stable(s.path(s.incoming_dir),seen,max(2,s.stable_seconds)); sig=tuple((str(p),p.stat().st_size,p.stat().st_mtime) for p in files)
            if files:
                if sig!=sig0: sig0=sig; since=time.time(); status(state='COLLECTING_BATCH',files=[p.name for p in files])
                elif since and time.time()-since>=max(5,s.batch_quiet_seconds):
                    try: process(files)
                    except Exception as e: log(traceback.format_exc()); status(state='UPLOAD_ERROR',error=str(e),files=[p.name for p in files]); time.sleep(15)
                    sig0=None; since=None
            else: sig0=None; since=None
            time.sleep(max(1,s.scan_seconds))
    except KeyboardInterrupt: status(state='STOPPED'); return 0
    except Exception as e: log(traceback.format_exc()); status(state='FATAL',error=str(e)); return 1
    finally: PID.unlink(missing_ok=True)
if __name__=='__main__': raise SystemExit(main())
