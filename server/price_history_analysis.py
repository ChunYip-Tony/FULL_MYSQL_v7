"""Retained price episodes rebuilt from canonical, completed POS observations.

Pure calculation shared by the upload publisher and repair tooling. No family
movement is ever assigned to an individual UPC. Missing observations stay null.
"""

def objects(matrix):
 return [dict(zip(matrix[0], r)) for r in matrix[1:]] if matrix else []

def supported_quantity(member, day):
 return member.get('uom') != 'LB' or day.get('quantityBasis') == 'POS_QTY_WEIGHT'

def rebuild_retained_analysis(tables, snapshots, source_days, current_rows, through, revision, policy):
 def read(name):return tables[name]
 from datetime import date,timedelta
 from collections import Counter
 confirmed_registry=set(policy['confirmed_upcs'])|{'24053300000','24953300000'}
 pack_registry={alias:profile for profile in policy.get('pack_profiles',[]) for alias in profile['aliases']}
 members={};source_days={str(r['date'])[:10]:r for r in source_days}
 for page in snapshots:
  for group in page['items']:
   for member in group['members']:
    members[member['upc']]={**member,'family':group['article']}
 current={str(x['ean_upc']):x for x in current_rows}
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
   if rows and end < date.fromisoformat(min(rows)):
    # Keep archived episodes intact outside the bounded source history.
    continue
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
   prev=next((p for p in reversed(items[:idx]) if klass(p.get('type'))==klass(e.get('type')) and p.get('gp_day') is not None),None)
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
  if upc not in members or not items:
   t.update(history_refresh_verified=False,status='Unverified',reason='UPC_HISTORY_SOURCE_NOT_RETURNED');continue
  e=items[-1];t.update(sale_lock=e.get('type')=='SALE',name=e['name'],family=e['family'],previous_price=e.get('old_price'),previous_type=e.get('old_type'),price=e['price'],type=e['type'],change_date=e['change_date'],change_file=e.get('change_file'),first_full=e.get('first_full'),last_full=e.get('last_full'),days=e.get('supported_days'),progress_pct=min(1,e.get('supported_days',0)/7),status='Ready for Review' if e.get('performance_ok') and e.get('supported_days',0)>=7 else 'Under Observation' if e.get('performance_ok') else 'Unverified',reason=e['rationale'],history_processed=True,history_refresh_verified=True,source=e['source'],source_revision=revision,data_through=through)
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
  covrows[upc]=dict(zip(covh,['Seafood',upc,m.get('name'),m['family'],'SOURCE_REFRESHED',len(m.get('priceHistory',[])),len(es),sum(d.get('sales') is not None for d in ds),'POS_CONFIRMED_LB' if upc in confirmed_registry else ('USER_CONFIRMED_'+pack_registry[upc]['selling_uom']+'_'+str(pack_registry[upc]['base_qty_per_selling_unit'])+'_LB') if upc in pack_registry else 'SOURCE_DEPENDENT','COMPARABLE_EPISODES_AVAILABLE' if any(e.get('previous_gp_day') is not None for e in es) else 'PARTIAL_OR_NO_COMPARABLE_BASELINE','; '.join(issues),revision,through]))
 output.update(ANALYSIS_PRICE_EVENTS=matrix(ph,events),ANALYSIS_COST_HISTORY=matrix(costh,costs),ANALYSIS_ITEM_REFERENCE=matrix(refh,list(refrows.values())),ANALYSIS_COVERAGE=matrix(covh,list(covrows.values())))
 audit={'through':through,'revision':revision,'upcs_refreshed':len(members),'retained_tracking_upcs':len(tracks),'episode_rows':len(episodes),'daily_rows':len(daily),'supported_episodes':sum(bool(e.get('performance_ok')) for e in episodes),'before_after_comparisons':comparisons,'fully_supported_comparisons':sum(bool(e.get('preceding_comparable_id') and e.get('performance_ok') and next((p.get('performance_ok') for p in episodes if p['episode_id']==e.get('preceding_comparable_id')),False)) for e in episodes),'gaps':dict(gaps),'missing_upcs':[str(t['upc']) for t in tracks if str(t['upc']) not in members]}
 return output,audit


API = 'https://seal-app-tkkkd.ondigitalocean.app'
HISTORY_CONTRACT = 'UPLOAD_HISTORY_V1'

# Fixed schemas make new deployments independent of a manual starter workbook.
HEADERS = {
 'ANALYSIS_UPC_DAILY': 'department upc name family date price type sales qty uom pos_reported_count quantity_basis quantity_estimated valid reason current_cost cost_uom cost_source cost_date normalized_gp historical_gp zero_sale pos_file pos_batch source_revision data_through'.split(),
 'ANALYSIS_PRICE_EPISODES': 'department episode_id upc name family old_price old_type price type change_date change_file first_full last_full end_before superseded_by_file episode_status applied_days supported_days support_pct positive_days popularity sales sales_day qty qty_day uom cost cost_source cost_date gp_day performance_ok preceding_comparable_id previous_gp_day previous_qty_day gp_day_change qty_day_change weekday_adjusted_gp_day_change weekday_mix availability confidence action next_price next_type rationale source source_revision data_through'.split(),
 'ANALYSIS_PRICE_TRACKING': 'department upc name family previous_price previous_type price type change_date change_file first_full last_full days progress_pct status sales_day qty_day uom gp_day previous_gp_day previous_qty_day gp_day_change qty_day_change popularity cost cost_source cost_date company_a company_b company_c sale_lock history_processed history_refresh_verified reason source source_revision data_through'.split(),
 'ANALYSIS_PRICE_EVENTS': 'department event_id upc name family date price type uom file_id source source_revision data_through'.split(),
 'ANALYSIS_COST_HISTORY': 'department upc article date cost uom source quantity value movement status source_revision data_through'.split(),
 'ANALYSIS_ITEM_REFERENCE': 'department upc name family category selling_uom price price_type cost cost_basis company_a company_b company_c source_revision data_through'.split(),
 'ANALYSIS_COVERAGE': 'department upc name family history_status price_event_count episode_count supported_days quantity_status gp_status blocking_reason source_revision data_through'.split(),
}

_HISTORY_DATE_COLUMNS = frozenset({
 'date', 'cost_date', 'data_through', 'change_date',
 'first_full', 'last_full', 'end_before',
})

def _history_date_value(value, column):
 """Canonical calendar dates across Sheets serials and Apps Script Date JSON."""
 if column not in _HISTORY_DATE_COLUMNS or value in (None, ''):
  return value
 from datetime import date, datetime, timedelta
 if isinstance(value, datetime):
  return value.date().isoformat()
 if isinstance(value, date):
  return value.isoformat()
 if isinstance(value, (int, float)) and not isinstance(value, bool):
  if 1 <= value <= 2958465 and float(value).is_integer():
   try:return (date(1899, 12, 30) + timedelta(days=int(value))).isoformat()
   except (OverflowError, ValueError):return value
 if isinstance(value, str):
  try:
   if len(value) == 10:return date.fromisoformat(value).isoformat()
   if len(value) > 10 and value[10] in ('T', ' '):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).date().isoformat()
  except ValueError:pass
 return value

def _history_compare_value(value, column=None):
 value = _history_date_value(value, column)
 if value is None or value == '':return ''
 if isinstance(value, bool):return str(value).lower()
 from decimal import Decimal, InvalidOperation
 if column in {'company_a', 'company_b', 'company_c'} and isinstance(value, (str, Decimal)):
  try:
   price = Decimal(value)
   if price.is_finite():return format(price.normalize(), 'f')
  except InvalidOperation:pass
 if isinstance(value, (float, int, Decimal)):
  # Plain decimal spelling keeps numeric UPCs ending in zero comparable to text.
  return format(Decimal(str(value)).normalize(), 'f')
 return str(value)


def read_retained_tables(reader, row_limit=200000):
 """Read bounded pages; fail rather than truncate or erase retained history."""
 result = {}
 for title, columns in HEADERS.items():
  # Read one row at a time for the header, then pages capped below 50k cells.
  h = reader(title, 1, 1, len(columns))
  if h and h[0] != columns:
   raise ValueError('Retained history schema mismatch: '+title)
  rows = [columns]
  start = 2
  while start <= row_limit:
   count = min(max(1,min(1500,40000//len(columns))), row_limit-start+1)
   page = reader(title, start, start+count-1, len(columns))
   page = [[_history_date_value(v, columns[i]) if i < len(columns) else v
            for i,v in enumerate(row)] for row in page]
   # Apps Script returns padded empty rows; Sheets API trims them.
   while page and not any(v not in ('', None) for v in page[-1]):page.pop()
   rows.extend(page)
   if len(page) < count:break
   start += count
  else:
   raise ValueError('Retained history exceeds safe scan bound: '+title)
  result[title] = rows
 return result


def build_upload_history(rows, tables, source_days, batch_id, through, loader=None):
 import json
 from pathlib import Path
 from datetime import date
 from business_clock import completed_through_date
 if not through or date.fromisoformat(through) > completed_through_date():
  raise ValueError('History requires a completed canonical POS date')
 if loader is None:
  from mobile_pricing import build_page
  from fastapi.encoders import jsonable_encoder
  loader = lambda ids: jsonable_encoder(build_page(limit=len(ids),history_days=90,requested_upcs=set(ids),history_only=True))
 ids = {str(r['ean_upc']) for r in rows if r.get('ean_upc') and r.get('quick_check_status') in ('READY','QA_HOLD')}
 for title in ('ANALYSIS_PRICE_TRACKING','ANALYSIS_COVERAGE'):
  ids.update(str(r['upc']) for r in objects(tables[title]))
 ids = sorted(ids)
 snapshots = []
 for start in range(0,len(ids),500):
  page = loader(ids[start:start+500])
  if str(page.get('through'))[:10] != through:
   raise ValueError('History source changed during publication; retry latest revision')
  snapshots.append(page)
 policy=json.loads(Path(__file__).with_name('pos_quantity_confirmations.json').read_text())
 revision=f'MYSQL_BATCH_{int(batch_id)};{HISTORY_CONTRACT}'
 output,audit=rebuild_retained_analysis(tables,snapshots,source_days,rows,through,revision,policy)
 active_ids={str(r['ean_upc']) for r in rows if r.get('quick_check_status')=='READY'}
 missing_active=active_ids.intersection(audit['missing_upcs'])
 if missing_active:
  raise ValueError('History source omitted active UPCs: '+','.join(sorted(missing_active)[:12]))
 audit.update(contract=HISTORY_CONTRACT,batch_id=int(batch_id),requested_upcs=len(ids))
 return output,audit


def verify_history_tables(expected, reader):
 """Compare all written values, including interior rows, at bounded cost."""
 for title,matrix in expected.items():
  width=len(matrix[0])
  size=max(1,min(1500,40000//width))
  for start in range(0,len(matrix),size):
   chunk=matrix[start:start+size]
   actual=reader(title,start+1,start+len(chunk),width)
   actual += [[] for _ in range(len(chunk)-len(actual))]
   for offset,(want,got) in enumerate(zip(chunk,actual)):
    want=[_history_compare_value(v,matrix[0][i]) for i,v in enumerate(want)]+['']*(width-len(want))
    got=[_history_compare_value(v,matrix[0][i]) for i,v in enumerate(got)]+['']*(width-len(got))
    if want != got:
     different = [matrix[0][i] for i,(a,b) in enumerate(zip(want,got)) if a != b]
     raise ValueError(f'History readback mismatch: {title} row {start+offset+1}; columns: {different}')
 return {'pass':True,'tables':{t:len(v)-1 for t,v in expected.items()},'contract':HISTORY_CONTRACT}


def preserve_unchanged_lineage(output, previous):
 """Unchanged raw facts keep their original source stamp, reducing Google IO."""
 keys={'ANALYSIS_UPC_DAILY':('upc','date'),'ANALYSIS_PRICE_EPISODES':('episode_id',),
       'ANALYSIS_PRICE_TRACKING':('upc',),'ANALYSIS_PRICE_EVENTS':('event_id',),
       'ANALYSIS_COST_HISTORY':('upc','date','cost','uom','source'),
       'ANALYSIS_ITEM_REFERENCE':('upc',),'ANALYSIS_COVERAGE':('upc',)}
 def canonical(v):
  if v in (None,''):return ''
  return _history_compare_value(v)
 for title,matrix in output.items():
  h=matrix[0];old=previous.get(title,[h]);identity=keys[title]
  oldrows={tuple(canonical(r.get(k)) for k in identity):r for r in objects(old)}
  for values in matrix[1:]:
   row=dict(zip(h,values));prior=oldrows.get(tuple(canonical(row.get(k)) for k in identity))
   if prior and all(canonical(row.get(k))==canonical(prior.get(k)) for k in h if k not in ('source_revision','data_through')):
    for k in ('source_revision','data_through'):
     if k in h:values[h.index(k)]=prior.get(k)
 return output
