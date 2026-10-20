"""Rebuild retained Google analysis from exact-UPC backend history snapshots.
Raw source observations are never altered. Run against a local snapshot directory.
"""
import json, pathlib, urllib.request, urllib.parse, concurrent.futures, time, os
ROOT=pathlib.Path(os.environ.get('FISHFINDER_HISTORY_REPAIR_DIR','/tmp/history-repair')); ROOT.mkdir(exist_ok=True)
API='https://seal-app-tkkkd.ondigitalocean.app'
def read(n):return json.loads((ROOT/(n+'.json')).read_text())
def objects(matrix):return [dict(zip(matrix[0],r)) for r in matrix[1:]]
def fetch(batch):
 path=ROOT/('batch-'+batch[0]+'.json')
 if path.exists():
  cached=json.loads(path.read_text())
  if cached.get('historyRepairVersion')==2:return cached
 url=API+'/v1/app/mobile-pricing/history-batch?'+urllib.parse.urlencode({'upcs':','.join(batch)})
 for attempt in range(3):
  try:
   with urllib.request.urlopen(url,timeout=90) as response: data=json.load(response)
   if data.get('historyRepairVersion')!=2:raise ValueError('History repair deployment not ready')
   if data.get('through')!='2026-10-18':raise ValueError('Unexpected source cutoff '+str(data.get('through')))
   path.write_text(json.dumps(data));print('Fetched',batch[0],len(batch),flush=True);return data
  except Exception:
   if attempt==2:raise
   time.sleep(10)

def download():
 ids=sorted({str(r['upc']) for r in objects(read('ANALYSIS_COVERAGE'))}|{'24570200000'}|{str(r['upc']) for r in objects(read('ANALYSIS_PRICE_TRACKING'))}|{str(r['ean_upc']) for r in objects(read('MYSQL_ANALYSIS_CURRENT'))})
 batches=[ids[i:i+24] for i in range(0,len(ids),24)]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  results=list(pool.map(fetch,batches))
 (ROOT/'snapshots.json').write_text(json.dumps(results));print('Downloaded',len(ids),'UPCs',flush=True)

# All calculations retain source dates, exposure qualification, and quantity basis.
def supported_quantity(m,d):
 return m.get('uom')!='LB' or d.get('quantityBasis')=='POS_QTY_WEIGHT'
def rebuild():
 from datetime import date,timedelta
 from collections import Counter
 snapshots=read('snapshots');members={};source_days={r['date']:r for r in read('source-days')['dates']};through='2026-10-18';revision='MYSQL_BATCH_64;HISTORY_REPAIR_POS_CONFIRMED_2026_10_19'
 for page in snapshots:
  for group in page['items']:
   for member in group['members']:
    members[member['upc']]={**member,'family':group['article']}
 current={str(x['ean_upc']):x for x in objects(read('MYSQL_ANALYSIS_CURRENT'))}
 olddaily=read('ANALYSIS_UPC_DAILY');dh=olddaily[0];daily={(str(x['upc']),x['date']):x for x in objects(olddaily)}
 for upc,m in members.items():
  for d in m['days']:
   if d['date']<'2026-08-27':continue
   cost=d.get('cost') or {};cc=m.get('cost') or {};rawqty=d.get('posReportedQty',d.get('posItemCount',d.get('qty')));rawsales=d.get('posReportedSales',d.get('sales'))
   qgood=supported_quantity(m,d) and d.get('qty') is not None and not(d.get('qty')==0 and rawsales not in (None,0))
   qty=d.get('qty') if qgood else None
   basis=d.get('quantityBasis',m.get('quantityBasis'))
   norm=rawsales-qty*cc['value'] if qgood and rawsales is not None and cc.get('value') is not None else None
   historical=rawsales-qty*cost['value'] if qgood and rawsales is not None and cost.get('value') is not None else None
   reason=d.get('reason')
   if not qgood and rawsales is not None:reason='POS_WEIGHT_UNVERIFIED' if m.get('uom')=='LB' else 'QUANTITY_OR_RETURN_REVIEW'
   old=daily.get((upc,d['date']),{})
   daily[(upc,d['date'])]=dict(zip(dh,['Seafood',upc,m.get('name'),m['family'],d['date'],d.get('price'),d.get('type'),rawsales,qty,m.get('uom'),rawqty,basis,d.get('quantityEstimated',False),bool(d.get('valid') and qgood),reason,cc.get('value'),cc.get('uom'),cc.get('source'),cc.get('date'),norm,historical,d.get('zero_sale',False),source_days.get(d['date'],{}).get('source_file_id',old.get('pos_file','')),old.get('pos_batch',''),revision,through]))
 oldepisodes=read('ANALYSIS_PRICE_EPISODES');eh=oldepisodes[0];episodes=objects(oldepisodes);keys={r['episode_id'] for r in episodes}
 priority={'REG':1,'TPR':2,'SALE':3,'IN STORE':4,'IN_STORE':4}
 for upc,m in members.items():
  byfile={}
  for event in m.get('priceHistory',[]):
   key=(event['date'],event.get('file_id',0));prev=byfile.get(key)
   if prev is None or priority.get(event['type'],0)>priority.get(prev['type'],0):byfile[key]=event
  prev=None
  for (day,fid),event in sorted(byfile.items()):
   changed=prev is None or (prev['price'],prev['type'])!=(event['price'],event['type'])
   eid=f'{upc}:{fid}:{day}'
   if changed and eid not in keys:
    episodes.append({'department':'Seafood','episode_id':eid,'upc':upc,'name':m.get('name'),'family':m['family'],'old_price':prev['price'] if prev else '', 'old_type':prev['type'] if prev else '', 'price':event['price'],'type':event['type'],'change_date':day,'change_file':fid});keys.add(eid)
   prev=event
 byupc={}
 for e in episodes:byupc.setdefault(str(e['upc']),[]).append(e)
 gaps=Counter();comparisons=0
 for upc,items in byupc.items():
  items.sort(key=lambda e:(str(e['change_date']),int(e.get('change_file') or 0)))
  m=members.get(upc)
  if not m:
   gaps['UPC_HISTORY_SOURCE_NOT_RETURNED']+=1;continue
  cc=(m.get('cost') or {}).get('value');rows={d['date']:daily[(upc,d['date'])] for d in m['days'] if (upc,d['date']) in daily}
  for idx,e in enumerate(items):
   next_e=items[idx+1] if idx+1<len(items) else None
   first=date.fromisoformat(e['change_date'])+timedelta(days=1)
   end=min(date.fromisoformat(through),date.fromisoformat(next_e['change_date'])-timedelta(days=1)) if next_e else date.fromisoformat(through)
   expected=max(0,(end-first).days+1);exposed=[];weekday=Counter();qmissing=0
   for n in range(expected):
    day=first+timedelta(days=n);d=rows.get(day.isoformat())
    if not d or d.get('sales') is None:continue
    # Observed selling-unit average can differ from the ticket because POS is rounded.
    tolerance=max(.02,float(e['price'])*.02) if d.get('quantity_basis')=='POS_QTY_WEIGHT' else .02
    if d.get('type')!=e['type'] or d.get('price') is None or abs(d['price']-float(e['price']))>tolerance:continue
    if d.get('reason') in {'MIXED_PRICE_DAY','QUANTITY_OR_RETURN_REVIEW','PRICE_TYPE_UNVERIFIED'}:continue
    exposed.append(d);weekday[day.strftime('%a')]+=1
    if d.get('qty') is None:qmissing+=1
   n=len(exposed);positive=sum(d['sales']>0 for d in exposed);sales=sum(d['sales'] for d in exposed);quantity=sum(d['qty'] for d in exposed) if n and qmissing==0 else None
   gpday=(sales-quantity*cc)/n if quantity is not None and cc is not None else None
   reasons=[]
   if not expected:reasons.append('NO_FULL_COMPLETED_POST_CHANGE_DAY')
   if n<expected:reasons.append('PARTIAL_PRICE_EXPOSURE_OR_SOURCE_COVERAGE')
   if qmissing:reasons.append('POS_WEIGHT_OR_QUANTITY_UNVERIFIED')
   if cc is None:reasons.append('SELLING_UNIT_COST_UNRESOLVED')
   ok=bool(expected and n==expected and qmissing==0 and cc is not None)
   e.update(name=m.get('name') or e.get('name'),family=m['family'],first_full=first.isoformat() if expected else '',last_full=end.isoformat() if expected else '',end_before=next_e['change_date'] if next_e else '',superseded_by_file=next_e.get('change_file','') if next_e else '',episode_status='Superseded' if next_e else 'Current',applied_days=expected,supported_days=n,support_pct=n/expected if expected else None,positive_days=positive,popularity=positive/n if n else None,sales=sales if n else None,sales_day=sales/n if n else None,qty=quantity,qty_day=quantity/n if quantity is not None else None,uom=m.get('uom'),cost=cc,cost_source=(m.get('cost') or {}).get('source'),cost_date=(m.get('cost') or {}).get('date'),gp_day=gpday,performance_ok=ok,weekday_mix=', '.join(f'{k}:{v}' for k,v in sorted(weekday.items())),availability='UNKNOWN; stockouts not verified',confidence='SUPPORTED_POS_CONFIRMED_UNIT' if ok else 'PARTIAL_OR_UNVERIFIED',action='Review' if not next_e and expected>=7 else ('Continue' if not next_e else ''),next_price=e['price'] if not next_e else '',next_type=e['type'] if not next_e else '',rationale='; '.join(reasons) or 'Completed canonical POS dates; current-cost-normalized GP',source=API+'/v1/app/mobile-pricing/history-batch',source_revision=revision,data_through=through)
   e['_qualified_dates']=[d['date'] for d in exposed]
   for key in ['preceding_comparable_id','previous_gp_day','previous_qty_day','gp_day_change','qty_day_change','weekday_adjusted_gp_day_change']:e[key]=None
   for reason in reasons:gaps[reason]+=1
   # REG and historical TPR are one regular-price comparison class. SALE is separate.
   klass=lambda x:'SALE' if x=='SALE' else 'REGULAR' if x in ('REG','TPR') else x
   prev=items[idx-1] if idx else None
   if prev and gpday is not None and prev.get('gp_day') is not None and klass(prev['type'])==klass(e['type']):
    if not(prev.get('performance_ok') and ok):
     e['confidence']='PARTIAL_OBSERVED_COMPARISON'
     e['rationale']+='; comparison uses supported dates only; prior coverage '+str(prev.get('supported_days'))+'/'+str(prev.get('applied_days'))
    e.update(preceding_comparable_id=prev['episode_id'],previous_gp_day=prev['gp_day'],previous_qty_day=prev['qty_day'],gp_day_change=gpday-prev['gp_day'],qty_day_change=e['qty_day']-prev['qty_day']);comparisons+=1
    prior_dates=[rows[day] for day in prev.get('_qualified_dates',[]) if rows[day].get('normalized_gp') is not None]
    prev_weekday={}
    for d in prior_dates:prev_weekday.setdefault(date.fromisoformat(d['date']).weekday(),[]).append(d['normalized_gp'])
    if all(date.fromisoformat(d['date']).weekday() in prev_weekday for d in exposed):
     expected_before=sum(sum(prev_weekday[date.fromisoformat(d['date']).weekday()])/len(prev_weekday[date.fromisoformat(d['date']).weekday()]) for d in exposed)/len(exposed)
     e['weekday_adjusted_gp_day_change']=gpday-expected_before
 tracking=read('ANALYSIS_PRICE_TRACKING');th=tracking[0];tracks=objects(tracking)
 tracked={str(t['upc']) for t in tracks}
 for upc,es in byupc.items():
  if upc in members and upc not in tracked and es:tracks.append({'department':'Seafood','upc':upc,'sale_lock':es[-1].get('type')=='SALE'});tracked.add(upc)
 for t in tracks:
  upc=str(t['upc']);items=byupc.get(upc,[])
  if upc not in members or not items:continue
  e=items[-1];t.update(name=e['name'],family=e['family'],previous_price=e.get('old_price'),previous_type=e.get('old_type'),price=e['price'],type=e['type'],change_date=e['change_date'],change_file=e.get('change_file'),first_full=e.get('first_full'),last_full=e.get('last_full'),days=e.get('supported_days'),progress_pct=min(1,e.get('supported_days',0)/7),status='Ready for Review' if e.get('performance_ok') and e.get('supported_days',0)>=7 else 'Under Observation' if e.get('performance_ok') else 'Unverified',reason=e['rationale'],history_processed=True,history_refresh_verified=True,source=e['source'],source_revision=revision,data_through=through)
  for k in ['sales_day','qty_day','uom','gp_day','previous_gp_day','previous_qty_day','gp_day_change','qty_day_change','popularity','cost','cost_source','cost_date']:t[k]=e.get(k)
  ref=current.get(upc,{})
  for k in ['a','b','c']:t['company_'+k]=ref.get('company_price_'+k,t.get('company_'+k))
 def matrix(header,rows):return [header]+[[r.get(k) for k in header] for r in rows]
 output={'ANALYSIS_UPC_DAILY':matrix(dh,[daily[k] for k in sorted(daily)]),'ANALYSIS_PRICE_EPISODES':matrix(eh,episodes),'ANALYSIS_PRICE_TRACKING':matrix(th,tracks)}
 # Retain event and cost lineage; append newly observed facts without deleting raw history.
 pe=read('ANALYSIS_PRICE_EVENTS');ph=pe[0];events=objects(pe);eventkeys={str(x['event_id']) for x in events}
 ch=read('ANALYSIS_COST_HISTORY');costh=ch[0];costs=objects(ch);costkeys={(str(x['upc']),str(x['date']),str(x['cost']),str(x['uom']),str(x['source'])) for x in costs}
 refs=read('ANALYSIS_ITEM_REFERENCE');refh=refs[0];refrows={str(x['upc']):x for x in objects(refs)}
 cov=read('ANALYSIS_COVERAGE');covh=cov[0];covrows={str(x['upc']):x for x in objects(cov)}
 for upc,m in members.items():
  for event in m.get('priceHistory',[]):
   eid=f"{upc}|{event['date']}|{event.get('file_id',0)}|{event['type']}|{event['price']}"
   if eid not in eventkeys:
    events.append(dict(zip(ph,['Seafood',eid,upc,m.get('name'),m['family'],event['date'],event['price'],event['type'],m.get('uom'),event.get('file_id'),event.get('source'),revision,through])));eventkeys.add(eid)
  for d in m['days']:
   cost=d.get('cost')
   if not cost:continue
   key=(upc,str(cost['date']),str(cost['value']),str(cost['uom']),str(cost['source']))
   if key not in costkeys:
    costs.append(dict(zip(costh,['Seafood',upc,m.get('article'),cost['date'],cost['value'],cost['uom'],cost['source'],None,None,None,'AS_OF_SELLING_UNIT_COST',revision,through])));costkeys.add(key)
  ref=current.get(upc,{});old=refrows.get(upc,{})
  refrows[upc]=dict(zip(refh,['Seafood',upc,m.get('name'),m['family'],ref.get('product_class',old.get('category')),m.get('uom'),(m.get('current') or {}).get('price'),(m.get('current') or {}).get('type'),(m.get('cost') or {}).get('value'),(m.get('cost') or {}).get('source'),ref.get('company_price_a',old.get('company_a')),ref.get('company_price_b',old.get('company_b')),ref.get('company_price_c',old.get('company_c')),revision,through]))
  es=byupc.get(upc,[]);ds=[daily[(upc,d['date'])] for d in m['days'] if (upc,d['date']) in daily];issues=sorted({d.get('reason') for d in ds if d.get('reason')})
  covrows[upc]=dict(zip(covh,['Seafood',upc,m.get('name'),m['family'],'SOURCE_REFRESHED',len(m.get('priceHistory',[])),len(es),sum(d.get('sales') is not None for d in ds),'POS_CONFIRMED_LB' if upc in {'24053300000','24953300000'} else 'SOURCE_DEPENDENT','COMPARABLE_EPISODES_AVAILABLE' if any(e.get('previous_gp_day') is not None for e in es) else 'PARTIAL_OR_NO_COMPARABLE_BASELINE','; '.join(issues),revision,through]))
 output.update(ANALYSIS_PRICE_EVENTS=matrix(ph,events),ANALYSIS_COST_HISTORY=matrix(costh,costs),ANALYSIS_ITEM_REFERENCE=matrix(refh,list(refrows.values())),ANALYSIS_COVERAGE=matrix(covh,list(covrows.values())))
 for name,values in output.items():(ROOT/(name+'-rebuilt.json')).write_text(json.dumps(values,allow_nan=False))
 audit={'through':through,'revision':revision,'upcs_refreshed':len(members),'retained_tracking_upcs':len(tracks),'episode_rows':len(episodes),'daily_rows':len(daily),'supported_episodes':sum(bool(e.get('performance_ok')) for e in episodes),'before_after_comparisons':comparisons,'fully_supported_comparisons':sum(bool(e.get('preceding_comparable_id') and e.get('performance_ok') and next((p.get('performance_ok') for p in episodes if p['episode_id']==e.get('preceding_comparable_id')),False)) for e in episodes),'gaps':dict(gaps),'missing_upcs':[str(t['upc']) for t in tracks if str(t['upc']) not in members]}
 (ROOT/'audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))

if __name__=="__main__":
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument("mode",choices=["download","rebuild","all"],default="all",nargs="?");args=parser.parse_args()
 if args.mode in ("download","all"):download()
 if args.mode in ("rebuild","all"):rebuild()
