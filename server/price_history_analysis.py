"""Retained price episodes rebuilt from canonical, completed POS observations.

Pure calculation shared by the upload publisher and repair tooling. No family
movement is ever assigned to an individual UPC. Missing observations stay null.
"""

def objects(matrix):
 return [dict(zip(matrix[0], r)) for r in matrix[1:]] if matrix else []

def supported_quantity(member, day):
 return member.get('uom') != 'LB' or day.get('quantityBasis') == 'POS_QTY_WEIGHT'


def price_day_matches(day, episode):
 # Match a known ticket; never manufacture a new ticket from rounded POS pounds.
 if str((day or {}).get('reason') or '').startswith('SOURCE_QUALITY_HOLD'):
  return False
 if not day or day.get('qty') is None or day.get('qty') <= 0 or day.get('sales') is None:
  return False
 if day.get('reason') in {'MIXED_PRICE_DAY','QUANTITY_OR_RETURN_REVIEW','PRICE_TYPE_UNVERIFIED'}:
  return False
 price=day.get('price')
 tolerance=max(.02,float(episode['price'])*.02) if day.get('quantity_basis')=='POS_QTY_WEIGHT' else .02
 return day.get('type')==episode.get('type') and price is not None and abs(float(price)-float(episode['price']))<=tolerance


def episode_observed_windows(items, rows):
 from datetime import date,timedelta
 # The immutable event ID retains the uploaded list date across repeated rebuilds.
 for e in items:
  raw=str(e.get('episode_id','')).rsplit(':',1)[-1]
  try:date.fromisoformat(raw)
  except ValueError:raw=e['change_date']
  e['_configured_date']=raw
 items.sort(key=lambda e:(e['_configured_date'],int(e.get('change_file') or 0)))
 for i,e in enumerate(items):
  raw=date.fromisoformat(e['_configured_date']);observed=None
  lower=date.fromisoformat(items[i-1]['_configured_date']) if i else date(2026,8,27)
  # Backdate only a consecutive run of positive, same-ticket, same-type POS.
  # Missing/mixed/untyped dates stop the run; zero sales cannot establish a change.
  day=raw
  while day>=lower and price_day_matches(rows.get(day.isoformat()),e):
   observed=day;day-=timedelta(days=1)
  e['_observed_start']=observed.isoformat() if observed else None
  e['_first']=observed if observed else raw+timedelta(days=1)
  e['change_date']=observed.isoformat() if observed else e['_configured_date']


def verify_member_performance(member, current, source_days, through, policy):
 """Independent evidence gates, not a synonym for a successful refresh."""
 from datetime import date,timedelta
 import math
 norm=lambda unit:'PACK' if str(unit or '').upper()=='PAC' else str(unit or '').upper()
 def number(value):
  try:return value is not None and math.isfinite(float(value))
  except (TypeError,ValueError):return False
 def cost_ok(cost,day):
  return bool(cost and number(cost.get('value')) and float(cost['value'])>0
      and norm(cost.get('uom'))==norm(member.get('uom'))
      and cost.get('source') and str(cost.get('date') or '')[:10] <= day)
 def source_ok(day):
  source=source_days.get(day,{})
  return not any(str(source.get('file_id',source.get('source_file_id','')))==str(h.get('file_id'))
      and (not h.get('date') or day==h['date']) for h in policy.get('source_quality_holds',[]))
 start='2026-08-27';end=date.fromisoformat(through)
 dates=[(date.fromisoformat(start)+timedelta(days=n)).isoformat()
        for n in range(max(0,(end-date.fromisoformat(start)).days+1))]
 rows={str(d['date'])[:10]:d for d in member.get('days',[]) if start<=str(d['date'])[:10]<=through}
 calendar_missing=[day for day in dates if day not in source_days]
 missing=[day for day in dates if day not in rows or rows[day].get('sales') is None]
 problems={'source_quality':[], 'quantity':[], 'historical_cost':[], 'price_attribution':[]}
 revenue_days=0;verified_gp_days=0
 for day,d in sorted(rows.items()):
  if d.get('sales') is None:continue
  revenue_days+=1
  if not source_ok(day):problems['source_quality'].append(day)
  qty_ok=number(d.get('qty')) and float(d['qty'])>=0 and supported_quantity(member,d)
  if not qty_ok or float(d.get('sales') or 0)<0 or (float(d.get('sales') or 0)>0 and not d.get('qty')):
   problems['quantity'].append(day)
  elif not d.get('sales'):
   verified_gp_days+=1
  elif cost_ok(d.get('cost'),day) and number(d.get('gp')) and abs(float(d['gp'])-(float(d['sales'])-float(d['qty'])*float(d['cost']['value'])))<.011:
   verified_gp_days+=1
  else:problems['historical_cost'].append(day)
  if not (qty_ok and float(d.get('qty') or 0)>0 and float(d.get('sales') or 0)>0
      and d.get('priceBasis') != 'PRICE_LIST_EXPOSURE_REFERENCE'
      and d.get('type') in {'REG','TPR','SALE','IN STORE','IN_STORE','TOTAL'} and number(d.get('price'))
      and float(d['price'])>0 and d.get('reason') not in {'MIXED_PRICE_DAY','PRICE_TYPE_UNVERIFIED','PRICE_EXPOSURE_UNVERIFIED'}):
   problems['price_attribution'].append(day)
 latest=rows.get(through,{})
 current_cost=member.get('cost') or {};ticket=member.get('current') or {}
 identity=bool(member.get('name') and member['name']!='Item identity not verified' and member.get('family') and member.get('uom'))
 current_checks={
  'identity':identity,
  'source':through in source_days and source_ok(through) and through==policy.get('expected_completed_date',through),
  'sales':number(latest.get('sales')) and float(latest['sales'])>=0,
  'quantity':number(latest.get('qty')) and supported_quantity(member,latest)
      and float(latest['qty'])>=0 and not (latest.get('sales') and not latest.get('qty')),
  'cost':cost_ok(current_cost,(end+timedelta(days=1)).isoformat()),
  'price':number(ticket.get('price')) and float(ticket['price'])>0
      and ticket.get('type') in {'REG','TPR','SALE','IN STORE','IN_STORE'},
 }
 if current:
  current_checks['published_cost_matches']=number(current.get('current_cost_per_selling_unit')) and number(current_cost.get('value')) and abs(float(current['current_cost_per_selling_unit'])-float(current_cost['value']))<.00001
  current_checks['published_price_matches']=number(current.get('current_price')) and number(ticket.get('price')) and abs(float(current['current_price'])-float(ticket['price']))<.00001 and current.get('current_price_type')==ticket.get('type')
 current_checks['gp_calculation']=bool(current_checks['sales'] and current_checks['quantity'] and current_checks['cost']
   and number(latest.get('normalized_gp')) and abs(float(latest['normalized_gp'])-(float(latest['sales'])-float(latest['qty'])*float(current_cost['value'])))<.011)
 current_verified=all(current_checks.values())
 economics_verified=identity and not missing and not calendar_missing and not any(problems[k] for k in ('source_quality','quantity','historical_cost'))
 prices_verified=not missing and not calendar_missing and not problems['price_attribution'] and not problems['source_quality']
 eligible=[day for day in sorted(source_days) if start<=day<=through and source_ok(day)]
 eligible_set=set(eligible)
 uploaded_missing=[day for day in eligible if day not in rows or rows[day].get('sales') is None]
 uploaded_sales=bool(eligible) and not uploaded_missing
 uploaded_gp=identity and uploaded_sales and not any(eligible_set.intersection(problems[k]) for k in ('quantity','historical_cost'))
 uploaded_prices=uploaded_sales and not eligible_set.intersection(problems['price_attribution'])
 return {'contract':'ITEM_PERFORMANCE_VERIFICATION_V2','period_start':start,'through':through,
    'uploaded_scope_start':eligible[0] if eligible else None,'uploaded_scope_through':eligible[-1] if eligible else None,
    'eligible_uploaded_dates':eligible,'held_uploaded_dates':[day for day in sorted(source_days) if not source_ok(day)],
    'uploaded_sales_verified':uploaded_sales,'uploaded_gp_verified':bool(uploaded_gp),
    'uploaded_price_verified':bool(uploaded_prices),'uploaded_fully_verified':bool(uploaded_gp and uploaded_prices),
    'uploaded_missing_item_dates':uploaded_missing,
    'calendar_current':through==policy.get('expected_completed_date',through),
    'sales_authority':'POS_ONLY','achieved_price_authority':'POS_ONLY; REALIZED_AVERAGE_IS_NOT_ONE_APPLIED_PRICE',
    'expected_current_date':policy.get('expected_completed_date',through),
    'current_verified':current_verified,'current_checks':current_checks,
    'historical_gp_verified':economics_verified,'historical_price_verified':prices_verified,
    'fully_verified':current_verified and economics_verified and prices_verified,
    'observed_days':revenue_days,'verified_historical_gp_days':verified_gp_days,
    'missing_source_dates':calendar_missing,'missing_item_dates':missing,
    'unresolved_dates':problems,
    'quantity_rule':'UPC_POS_ONLY; FAMILY_MOVEMENT_NEVER_ALLOCATED',
    'historical_gp_basis':'AS_OF_COST; CURRENT_COST_COMPARISON_SEPARATE'}


def reconcile_coverage_identifiers(coverage, current):
 """Repair only proven leading-zero loss in this derived Google table.

 Exact canonical UPCs always win. An orphan can be restored only when the
 digits without leading zeroes identify one master UPC in the same family.
 Raw POS/history identities are never rewritten or merged here.
 """
 by_digits={}
 for upc,row in current.items():
  if upc.isdigit():by_digits.setdefault(upc.lstrip('0') or '0',[]).append(upc)
 repaired=0
 for upc,row in list(coverage.items()):
  if upc in current or not upc.isdigit():continue
  matches=by_digits.get(upc.lstrip('0') or '0',[])
  if len(matches)!=1:continue
  canonical=matches[0];master=current[canonical]
  if str(row.get('family') or '')!=str(master.get('main_article_number') or ''):continue
  restored={**row,'upc':canonical}
  coverage.pop(upc)
  coverage.setdefault(canonical,restored)
  repaired+=1
 return repaired

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
   source=source_days.get(d['date'],{})
   held=any(str(source.get('file_id',source.get('source_file_id','')))==str(h.get('file_id')) and (not h.get('date') or h['date']==d['date']) for h in policy.get('source_quality_holds',[]))
   if held:
    reason='SOURCE_QUALITY_HOLD:USER_REPORTED_WRONG_POS_FILE'
    # Raw evidence remains in MySQL. Derived totals must not consume a
    # rejected source as valid sales or silently count its date as zero.
    rawsales=qty=norm=historical=None
    qgood=False
   old=daily.get((upc,d['date']),{})
   daily[(upc,d['date'])]=dict(zip(dh,['Seafood',upc,m.get('name'),m['family'],d['date'],rawsales/qty if qgood and qty>0 and rawsales is not None and rawsales>0 else None,d.get('type'),rawsales,qty,m.get('uom'),rawqty,basis,d.get('quantityEstimated',False),bool(d.get('valid') and qgood and not held),reason,cc.get('value'),cc.get('uom'),cc.get('source'),cc.get('date'),norm,historical,d.get('zero_sale',False),source_days.get(d['date'],{}).get('file_id',source_days.get(d['date'],{}).get('source_file_id',old.get('pos_file',''))),old.get('pos_batch',''),revision,through]))
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
  m=members.get(upc)
  if not m:
   gaps['UPC_HISTORY_SOURCE_NOT_RETURNED']+=1;continue
  cc=(m.get('cost') or {}).get('value');rows={d['date']:daily[(upc,d['date'])] for d in m['days'] if (upc,d['date']) in daily}
  episode_observed_windows(items,rows)
  for idx,e in enumerate(items):
   next_e=items[idx+1] if idx+1<len(items) else None
   first=e['_first']
   next_boundary=next_e['_first'] if next_e and next_e['_observed_start'] else date.fromisoformat(next_e['_configured_date']) if next_e else None
   end=min(date.fromisoformat(through),next_boundary-timedelta(days=1)) if next_boundary else date.fromisoformat(through)
   if rows and end < date.fromisoformat(min(rows)):
    # Keep archived episodes intact outside the bounded source history.
    continue
   expected=max(0,(end-first).days+1);exposed=[];weekday=Counter();qmissing=0;price_supported=0;held_days=[]
   for n in range(expected):
    day=first+timedelta(days=n);d=rows.get(day.isoformat())
    if d and str(d.get('reason') or '').startswith('SOURCE_QUALITY_HOLD'):
     held_days.append(day.isoformat());continue
    if not d or d.get('sales') is None:continue
    # Window observations and price attribution are independent. TOTAL types,
    # mixed prices and rounded pounds must not silently erase positive sales
    # while leaving zero-sales days in the denominator. Retain the observed
    # performance, but do not certify it as a clean price experiment.
    tolerance=max(.02,float(e['price'])*.02) if d.get('quantity_basis')=='POS_QTY_WEIGHT' else .02
    price_ok=(d.get('type')==e['type'] and d.get('price') is not None
              and abs(d['price']-float(e['price']))<=tolerance
              and d.get('reason') not in {'MIXED_PRICE_DAY','QUANTITY_OR_RETURN_REVIEW','PRICE_TYPE_UNVERIFIED'})
    if str(d.get('reason') or '').startswith('SOURCE_QUALITY_HOLD'):price_ok=False
    if price_ok:price_supported+=1
    exposed.append(d);weekday[day.strftime('%a')]+=1
    if d.get('qty') is None:qmissing+=1
   n=len(exposed);positive=sum(d['sales']>0 for d in exposed);sales=sum(d['sales'] for d in exposed);quantity=sum(d['qty'] for d in exposed) if n and qmissing==0 else None
   gpday=(sales-quantity*cc)/n if quantity is not None and cc is not None else None
   reasons=[]
   if e['_observed_start']:
    reasons.append('POS_OBSERVED_START:'+e['_observed_start']+'; PRICE_LIST_UPLOAD_DATE:'+e['_configured_date'])
   if not expected:reasons.append('NO_FULL_COMPLETED_POST_CHANGE_DAY')
   if n<expected:reasons.append('PARTIAL_PRICE_EXPOSURE_OR_SOURCE_COVERAGE')
   if price_supported<n:reasons.append(f'PRICE_ATTRIBUTION_UNVERIFIED:{n-price_supported}/{n}')
   if held_days:reasons.append('SOURCE_QUALITY_HOLD:REPLACE_REPORTED_WRONG_POS_FILE; excluded dates '+','.join(held_days))
   if qmissing:reasons.append('POS_WEIGHT_OR_QUANTITY_UNVERIFIED')
   if cc is None:reasons.append('SELLING_UNIT_COST_UNRESOLVED')
   ok=bool(expected and n==expected and price_supported==n and qmissing==0 and cc is not None)
   e.update(name=m.get('name') or e.get('name'),family=m['family'],first_full=first.isoformat() if expected else '',last_full=end.isoformat() if expected else '',end_before=next_e['change_date'] if next_e else '',superseded_by_file=next_e.get('change_file','') if next_e else '',episode_status='Superseded' if next_e else 'Current',applied_days=expected,supported_days=n,support_pct=n/expected if expected else None,positive_days=positive,popularity=positive/n if n else None,sales=sales if n else None,sales_day=sales/n if n else None,qty=quantity,qty_day=quantity/n if quantity is not None else None,uom=m.get('uom'),cost=cc,cost_source=(m.get('cost') or {}).get('source'),cost_date=(m.get('cost') or {}).get('date'),gp_day=gpday,performance_ok=ok,weekday_mix=', '.join(f'{k}:{v}' for k,v in sorted(weekday.items())),availability='UNKNOWN; stockouts not verified',confidence='SUPPORTED_POS_CONFIRMED_UNIT' if ok else 'PARTIAL_OR_UNVERIFIED',action='Review' if not next_e and expected>=7 else ('Continue' if not next_e else ''),next_price=e['price'] if not next_e else '',next_type=e['type'] if not next_e else '',rationale='; '.join(reasons) or 'Completed canonical POS dates; current-cost-normalized GP',source=API+'/v1/app/mobile-pricing/history-batch',source_revision=revision,data_through=through)
   e['_qualified_dates']=[d['date'] for d in exposed]
   e['rationale']+='; PRICE_LIST_REFERENCE_WINDOW; achieved selling prices come only from ANALYSIS_UPC_DAILY POS revenue / verified quantity. Metrics are observed POS performance in the recorded reference window; price-attributed days '+str(price_supported)+'/'+str(n)
   # A retained list price describes the historical reference window, not an
   # approved future selling price or a measured POS average.
   e['next_price']=None;e['next_type']=None
   e['_previous']=None
   for key in ['preceding_comparable_id','previous_gp_day','previous_qty_day','gp_day_change','qty_day_change','weekday_adjusted_gp_day_change']:e[key]=None
   for reason in reasons:gaps[reason]+=1
   # REG and historical TPR are one regular-price comparison class. SALE is separate.
   klass=lambda x:'SALE' if x=='SALE' else 'REGULAR' if x in ('REG','TPR') else x
   prev=next((p for p in reversed(items[:idx]) if klass(p.get('type'))==klass(e.get('type')) and p.get('gp_day') is not None),None)
   if prev and gpday is not None and prev.get('gp_day') is not None and klass(prev['type'])==klass(e['type']):
    if not(prev.get('performance_ok') and ok):
     e['confidence']='PARTIAL_OBSERVED_COMPARISON'
     e['rationale']+='; comparison uses supported dates only; prior coverage '+str(prev.get('supported_days'))+'/'+str(prev.get('applied_days'))
    e['_previous']=prev
    e.update(preceding_comparable_id=prev['episode_id'],previous_gp_day=prev['gp_day'],previous_qty_day=prev['qty_day'],gp_day_change=gpday-prev['gp_day'],qty_day_change=e['qty_day']-prev['qty_day']);comparisons+=1
    prior_dates=[rows[day] for day in prev.get('_qualified_dates',[]) if rows[day].get('normalized_gp') is not None]
    prev_weekday={}
    for d in prior_dates:prev_weekday.setdefault(date.fromisoformat(d['date']).weekday(),[]).append(d['normalized_gp'])
    if exposed and all(date.fromisoformat(d['date']).weekday() in prev_weekday for d in exposed):
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
  baseline=e.get('_previous')
  if baseline:
   t.update(previous_price=baseline['price'],previous_type=baseline['type'])
   if t['status']=='Ready for Review' and not baseline.get('performance_ok'):
    t['status']='Review — partial baseline'
  ref=current.get(upc,{})
  if (ref.get('pos_qty_7d') not in (None,'') and float(ref['pos_qty_7d'])==0
      and ref.get('family_movement_7d') not in (None,'') and float(ref['family_movement_7d'])==0):
   t.update(status='QA HOLD',reason=t['reason']+'; NO_POS_OR_FAMILY_MOVEMENT_7D: verify stock/display/mapping before price action')
  for k in ['a','b','c']:t['company_'+k]=ref.get('company_price_'+k,t.get('company_'+k))
 def matrix(header,rows):return [header]+[[r.get(k) for k in header] for r in rows]
 output={'ANALYSIS_UPC_DAILY':matrix(dh,[daily[k] for k in sorted(daily)]),'ANALYSIS_PRICE_EPISODES':matrix(eh,episodes),'ANALYSIS_PRICE_TRACKING':matrix(th,tracks)}
 # Retain event and cost lineage; append newly observed facts without deleting raw history.
 pe=read('ANALYSIS_PRICE_EVENTS');ph=pe[0];events=objects(pe);eventkeys={str(x['event_id']) for x in events}
 ch=read('ANALYSIS_COST_HISTORY');costh=ch[0];costs=objects(ch);costkeys={(str(x['upc']),str(x['date']),str(x['cost']),str(x['uom']),str(x['source'])) for x in costs}
 refs=read('ANALYSIS_ITEM_REFERENCE');refh=refs[0];refrows={str(x['upc']):x for x in objects(refs)}
 cov=read('ANALYSIS_COVERAGE');covh=cov[0];covrows={str(x['upc']):x for x in objects(cov)}
 coverage_identifier_repairs=reconcile_coverage_identifiers(covrows,current)
 verification={}
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
  import json
  verified=verify_member_performance(m,ref,source_days,through,policy);verification[upc]=verified
  covrows[upc]=dict(zip(covh,['Seafood',upc,m.get('name'),m['family'],
   'FULLY_VERIFIED' if verified['fully_verified'] else 'PARTIAL_REQUIRES_EVIDENCE',
   len(m.get('priceHistory',[])),len(es),verified['observed_days'],
   'VERIFIED_POS_ONLY' if not verified['unresolved_dates']['quantity'] else 'UNRESOLVED_POS_QUANTITY',
   'CURRENT_'+('VERIFIED' if verified['current_verified'] else 'PARTIAL')+';HISTORICAL_GP_'+('VERIFIED' if verified['historical_gp_verified'] else 'PARTIAL')+';PRICE_HISTORY_'+('VERIFIED' if verified['historical_price_verified'] else 'PARTIAL'),
   json.dumps(verified,sort_keys=True,separators=(',',':')),revision,through]))
 # Account for the complete master, including inactive profiles without a
 # retained performance history. No-activity summaries are not proof of a
 # complete historical zero, so these rows explicitly require history evidence.
 for upc,ref in current.items():
  if upc not in covrows:
   covrows[upc]={'department':'Seafood','upc':upc,'name':ref.get('selling_description'),
    'family':ref.get('main_article_number'),'history_status':'HISTORY_EVIDENCE_REQUIRED',
    'quantity_status':'UNVERIFIED','gp_status':'UNVERIFIED',
    'blocking_reason':'MASTER_PROFILE_NOT_YET_BACKED_BY_RETAINED_DAILY_PERFORMANCE; no activity summary is not a verified historical zero',
    'source_revision':revision,'data_through':through}
 for upc,retained in covrows.items():
  if upc not in members:
   if retained.get('history_status')!='HISTORY_EVIDENCE_REQUIRED':
    retained.update(history_status='SOURCE_NOT_RETURNED',gp_status='UNVERIFIED',blocking_reason='UPC_HISTORY_SOURCE_NOT_RETURNED',source_revision=revision,data_through=through)
 # The main bridge already gates these values against eligible dated POS and
 # verified selling units. Never fall back to a price-list ticket in a generic
 # item price field, including retained profiles not returned this refresh.
 for upc,item in refrows.items():
  ref=current.get(upc,{})
  verified_pos=ref.get('current_price_source')=='CANONICAL_POS_REALIZED_AVERAGE'
  item['price']=ref.get('current_price') if verified_pos else None
  item['price_type']='POS_REALIZED_AVERAGE' if item['price'] is not None else 'POS_PRICE_UNVERIFIED'
  item.update(source_revision=revision,data_through=through)
 output.update(ANALYSIS_PRICE_EVENTS=matrix(ph,events),ANALYSIS_COST_HISTORY=matrix(costh,costs),ANALYSIS_ITEM_REFERENCE=matrix(refh,list(refrows.values())),ANALYSIS_COVERAGE=matrix(covh,list(covrows.values())))
 audit={'through':through,'revision':revision,'upcs_refreshed':len(members),'retained_tracking_upcs':len(tracks),'episode_rows':len(episodes),'daily_rows':len(daily),'supported_episodes':sum(bool(e.get('performance_ok')) for e in episodes),'before_after_comparisons':comparisons,'fully_supported_comparisons':sum(bool(e.get('preceding_comparable_id') and e.get('performance_ok') and next((p.get('performance_ok') for p in episodes if p['episode_id']==e.get('preceding_comparable_id')),False)) for e in episodes),'gaps':dict(gaps),'missing_upcs':[str(t['upc']) for t in tracks if str(t['upc']) not in members]}
 audit['coverage_identifier_repairs']=coverage_identifier_repairs
 # A successful Sheets write is distinct from source eligibility. Consumers
 # must match each uploaded file to this canonical date/file manifest.
 canonical=[{'date':day,'file_id':r.get('file_id',r.get('source_file_id')),'batch_id':r.get('batch_id'),'original_filename':r.get('original_filename')}
            for day,r in sorted(source_days.items())]
 held=[r for r in canonical if any(str(r['file_id'])==str(h.get('file_id'))
       and (not h.get('date') or h['date']==r['date'])
       for h in policy.get('source_quality_holds',[]))]
 audit['source_quality']={'contract':'POS_SOURCE_ELIGIBILITY_V1',
     'canonical_days':canonical,'held_sources':held,
     'status':'HELD_SOURCE_REQUIRES_REPLACEMENT' if held else 'ELIGIBLE'}
 audit['verification']={'contract':'ITEM_PERFORMANCE_VERIFICATION_V2','items':len(covrows),
  **{k:sum(bool(v[k]) for v in verification.values()) for k in ('fully_verified','current_verified','historical_gp_verified','historical_price_verified','uploaded_sales_verified','uploaded_gp_verified','uploaded_price_verified','uploaded_fully_verified')},
  'unresolved_items':len(covrows)-sum(v['fully_verified'] for v in verification.values())}
 return output,audit


API = 'https://seal-app-tkkkd.ondigitalocean.app'
HISTORY_CONTRACT = 'UPLOAD_HISTORY_V8_SOURCE_ELIGIBILITY'

def bounded_history_read(reader, title, start, end, width):
 """Keep bridge read responses small without dropping requested rows."""
 size=max(1,min(1000,20000//max(1,width)))
 rows=[]
 for first in range(start,end+1,size):
  last=min(end,first+size-1)
  page=reader(title,first,last,width)
  rows.extend(page)
  if len(page)<last-first+1:
   break
 return rows

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
 if (column not in _HISTORY_DATE_COLUMNS and not str(column or '').endswith(('_date','_asof_date'))) or value in (None, ''):
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
  # Match the writer's rounding on the ORIGINAL numeric type. Converting a
  # binary float to Decimal first can change half-way rounding (33.57 / 7),
  # causing a false mismatch against the exact value sent to Google.
  numeric = Decimal(str(value)) if isinstance(value, int) else Decimal(format(value, '.15g'))
  return format(numeric.normalize(), 'f')
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
  loader = lambda ids: jsonable_encoder(build_page(limit=len(ids),history_days=max(90,len(source_days)),requested_upcs=set(ids),history_only=True))
 ids = {str(r['ean_upc']) for r in rows if r.get('ean_upc') and (r.get('quick_check_status') in ('READY','QA_HOLD') or any(float(r.get(k) or 0)!=0 for k in ('sales_dollars_7d','sales_dollars_30d','pos_qty_7d','pos_qty_30d')))}
 ids.update(str(r['upc']) for r in objects(tables['ANALYSIS_UPC_DAILY']) if r.get('upc') and r.get('sales') not in (None,''))
 for title in ('ANALYSIS_PRICE_TRACKING','ANALYSIS_COVERAGE'):
  ids.update(str(r['upc']) for r in objects(tables[title]) if r.get('history_status')!='HISTORY_EVIDENCE_REQUIRED')
 ids = sorted(ids)
 # The API and publisher share one small container. Loading 500 histories at
 # once also creates a full jsonable_encoder copy of the page. Bound that peak
 # and yield pages instead of retaining a second collection of all snapshots.
 def snapshots():
  for start in range(0,len(ids),25):
   page = loader(ids[start:start+25])
   if str(page.get('through'))[:10] != through:
    raise ValueError('History source changed during publication; retry latest revision')
   yield page
 policy=json.loads(Path(__file__).with_name('pos_quantity_confirmations.json').read_text())
 policy['expected_completed_date']=completed_through_date().isoformat()
 revision=f'MYSQL_BATCH_{int(batch_id)};{HISTORY_CONTRACT}'
 output,audit=rebuild_retained_analysis(tables,snapshots(),source_days,rows,through,revision,policy)
 active_ids={str(r['ean_upc']) for r in rows if r.get('quick_check_status')=='READY'}
 missing_active=active_ids.intersection(audit['missing_upcs'])
 if missing_active:
  raise ValueError('History source omitted active UPCs: '+','.join(sorted(missing_active)[:12]))
 audit.update(contract=HISTORY_CONTRACT,batch_id=int(batch_id),requested_upcs=len(ids))
 return output,audit


def verify_history_tables(expected, reader):
 """Compare every cell; retry a bounded chunk after transient bridge reads."""
 for title,matrix in expected.items():
  width=len(matrix[0]);size=max(1,min(1500,40000//width))
  normalize=lambda row:[_history_compare_value(v,matrix[0][i]) for i,v in enumerate(row)]+['']*(width-len(row))
  for start in range(0,len(matrix),size):
   chunk=matrix[start:start+size]
   for attempt in range(3):
    actual=reader(title,start+1,start+len(chunk),width)
    actual += [[] for _ in range(len(chunk)-len(actual))]
    mismatch=None
    for offset,(want,got) in enumerate(zip(chunk,actual)):
     wanted,observed=normalize(want),normalize(got)
     if wanted!=observed:
      different=[matrix[0][i] for i,(a,b) in enumerate(zip(wanted,observed)) if a!=b]
      mismatch=(offset,different,wanted,observed);break
    if mismatch is None:break
   else:
    offset,different,wanted,observed=mismatch
    sample={k:{'expected':wanted[i][:120],'actual':observed[i][:120]} for i,k in enumerate(matrix[0]) if k in different[:3]}
    raise ValueError(f'History readback mismatch: {title} row {start+offset+1}; columns: {different}; sample: {sample}')
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




