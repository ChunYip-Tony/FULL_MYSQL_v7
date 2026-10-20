"""Reconcile canonical POS revenue with family 251-minus-252; never allocate LB to UPCs."""
from collections import defaultdict
from decimal import Decimal
import json
import hashlib
from pathlib import Path

POS_LB_CONFIRMATIONS=json.loads(Path(__file__).with_name("pos_quantity_confirmations.json").read_text())
CONFIRMED_POS_LB_UPCS=frozenset(POS_LB_CONFIRMATIONS["confirmed_upcs"])
POS_QUANTITY_POLICY_REVISION=hashlib.sha256(json.dumps(POS_LB_CONFIRMATIONS,sort_keys=True).encode()).hexdigest()

HEADERS = ['department','date','family_id','main_article_number','family_name','pos_sales','movement_qty','movement_uom','cost_per_movement_unit','cost_source','cost_date','family_cogs','family_gp','family_gp_pct','status','upc_count','quantity_basis','batch_id','pos_reported_qty','pos_qty_comparison','pos_price_basis','family_avg_sold_price_per_movement_unit','gp_quantity','gp_quantity_uom','gp_quantity_basis']

def apply_confirmed_selling_profile(row):
    if row.get('cost_scope')=='FAMILY_MOVEMENT_UNIT':
        return row
    for profile in POS_LB_CONFIRMATIONS.get('pack_profiles',[]):
        if str(row.get('ean_upc') or '') in profile['aliases']:
            result={**row,'selling_uom':profile['selling_uom'],'base_uom':profile['base_uom'],
                'base_qty_per_selling_unit':d(profile['base_qty_per_selling_unit']),
                'canonical_upc':profile['canonical_upc'],'upc_aliases':profile['aliases'],
                'selling_unit_confirmation':'TONY_CONFIRMED_'+profile['selling_uom']+'_2026_10_19'}
            base_cost=row.get('current_cost_per_base_uom')
            if base_cost not in (None,''):
                cost=d(base_cost)*d(profile['base_qty_per_selling_unit'])
            elif str(row.get('selling_uom') or '').upper()=='LB' and row.get('current_cost_per_selling_unit') not in (None,''):
                cost=d(row['current_cost_per_selling_unit'])*d(profile['base_qty_per_selling_unit'])
            else:
                cost=None
            if cost is not None:
                result['current_cost_per_selling_unit']=cost
                price=d(row.get('current_price'))
                result['gp_pct_current']=(price-cost)/price if price else None
                if row.get('sales_dollars_7d') not in (None,'') and row.get('pos_qty_7d') not in (None,''):
                    result['gp_dollars_7d']=d(row['sales_dollars_7d'])-d(row['pos_qty_7d'])*cost
                    days=d(row.get('sales_days_7d'))
                    result['gp_per_day_7d']=result['gp_dollars_7d']/days if days else None
            velocity=d(row.get('upc_velocity_7d'))
            if velocity and row.get('current_oh') not in (None,'') and str(row.get('current_oh_uom') or '').upper()=='LB':
                result['dos']=d(row['current_oh'])/(velocity*d(profile['base_qty_per_selling_unit']))
            return result
    return row

def d(v):
    return Decimal(str(v or 0))

def confirmed_pos_lb(row, day):
    # Tony confirmed this exact UPC's observed POS quantity as LB on 2026-10-19.
    # Do not extend the decision to sibling UPCs or earlier business dates.
    upc=str(row.get('ean_upc') or '')
    historical_tilapia=upc in CONFIRMED_POS_LB_UPCS or upc in {'24053300000','24953300000'}
    if not historical_tilapia and (upc != '24929400000' or str(day)[:10] < '2026-10-18'):
        return None
    if str(row.get('selling_uom') or '').upper() != 'LB':
        return None
    value=row.get('latest_daily_pos_reported_qty',row.get('latest_daily_pos_qty'))
    if value in (None,'') or d(value)<0 or (d(value)==0 and d(row.get('latest_daily_sales_dollars'))!=0):
        return None
    return d(value)

def family_result(sales, movement, cost):
    if movement.get('status') != 'READY':
        return {'status':'MOVEMENT_UNVERIFIED','cogs':None,'gp':None,'gp_pct':None}
    if cost.get('status') != 'RESOLVED':
        return {'status':'COST_UNIT_UNVERIFIED','cogs':None,'gp':None,'gp_pct':None}
    qty=movement.get('quantity')
    if qty is None or d(qty)<0 or (d(sales)!=0 and d(qty)==0) or (d(sales)==0 and d(qty)!=0):
        return {'status':'SALES_MOVEMENT_REVIEW','cogs':None,'gp':None,'gp_pct':None}
    cogs=d(qty)*d(cost['cost_per_selling_unit']);gp=d(sales)-cogs
    return {'status':'RESOLVED_FAMILY_MVT','cogs':cogs,'gp':gp,'gp_pct':gp/d(sales) if d(sales) else None}

def build_family_daily(cur, rows, daily, batch_id):
    from data_coverage import source_data_days
    from chatgpt_sheet_bridge import _family_cost_as_of
    from webapp_v2_runtime import _ordering_family_movement_metrics
    day=daily.get('business_date');matrix=[HEADERS]
    if not day:
        return matrix,{'status':'NO_POS_DAY','gp':None,'cogs':None,'unresolved_sales':None}
    days=[x for x in source_data_days(cur,'movement',limit=90,up_to=day) if x['date']==day]
    # Canonical file + date, never latest MVT date substituted for the POS date.
    raw=[]
    if days:
        clauses=' OR '.join('(file_id=%s AND posting_date=%s)' for _ in days)
        args=tuple(v for x in days for v in (x['file_id'],x['date']))
        cur.execute('SELECT family_id,base_uom_code,SUM(net_sold_quantity) AS q FROM family_movement_observation WHERE ('+clauses+') GROUP BY family_id,base_uom_code',args)
        raw=cur.fetchall()
    movements=defaultdict(list)
    for r in raw:
        movements[int(r['family_id'])].append(r)
    grouped=defaultdict(list)
    for r in rows:
        if r.get('family_id') is not None:
            grouped[int(r['family_id'])].append(r)
    total_gp=Decimal(0);total_cogs=Decimal(0);resolved_sales=Decimal(0);unresolved_sales=abs(d(daily.get('unmapped_sales')));failures=0;pos_fallbacks=0;blockers=[]
    for fid,members in sorted(grouped.items()):
        sales=sum((d(r.get('latest_daily_sales_dollars')) for r in members),Decimal(0))
        obs=movements.get(fid,[])
        if not sales and not any(d(r.get('q')) for r in obs):
            continue
        units={str(r.get('base_uom_code') or '').upper().strip() for r in obs}
        movement={'status':'UNAVAILABLE','quantity':None,'uom':None}
        if len(units)==1 and '' not in units:
            movement={'status':'READY','quantity':sum((d(r['q']) for r in obs),Decimal(0)),'uom':next(iter(units))}
        elif not obs and days:
            # Retain the existing canonical raw-history recovery for active families.
            movement=_ordering_family_movement_metrics(cur,fid,days)
        first=members[0];unit=movement.get('uom')
        selling=[r for r in members if d(r.get('latest_daily_sales_dollars'))]
        reported=sum((d(r.get('latest_daily_pos_reported_qty',r.get('latest_daily_pos_qty'))) for r in selling),Decimal(0))
        same_unit=bool(selling) and all(str(r.get('selling_uom') or '').upper()==str(unit or '').upper() for r in selling)
        comparison='DIFFERENT_SELLING_UNITS'
        if same_unit and movement.get('quantity') is not None:
            comparison='CONSISTENT_WITH_ROUNDING' if abs(reported-d(movement['quantity']))<=Decimal('.5')*len(selling)+Decimal('.01') else 'QUANTITY_MISMATCH_REVIEW'
        synthetic={**first,'cost_scope':'FAMILY_MOVEMENT_UNIT','selling_uom':unit,'base_uom':unit,'base_qty_per_selling_unit':1,'current_cost_per_selling_unit':None,'cost_source':None}
        cost=_family_cost_as_of(cur,synthetic,day) if unit else {'status':'NO_MOVEMENT_UNIT'}
        result=family_result(sales,movement,cost)
        gp_qty=movement.get('quantity');gp_unit=unit;gp_basis='FAMILY_251_MINUS_252'
        if result['status']!='RESOLVED_FAMILY_MVT' and selling and all(confirmed_pos_lb(r,day) is not None for r in selling):
            fallback_costs=[_family_cost_as_of(cur,r,day) for r in selling]
            if all(c.get('status')=='RESOLVED' for c in fallback_costs):
                gp_qty=sum((confirmed_pos_lb(r,day) for r in selling),Decimal(0))
                gp_unit='LB';gp_basis='USER_CONFIRMED_POS_LB_251_252_UNMATCHED'
                cogs=sum((confirmed_pos_lb(r,day)*d(c['cost_per_selling_unit']) for r,c in zip(selling,fallback_costs)),Decimal(0))
                gp=sales-cogs;result={'status':'RESOLVED_USER_CONFIRMED_POS','cogs':cogs,'gp':gp,'gp_pct':gp/sales if sales else None}
                cost=fallback_costs[0];comparison='POS_USED_251_252_UNMATCHED';pos_fallbacks+=1
        if result['status'] in ('RESOLVED_FAMILY_MVT','RESOLVED_USER_CONFIRMED_POS'):
            total_gp+=result['gp'];total_cogs+=result['cogs'];resolved_sales+=sales
        else:
            failures+=1;unresolved_sales+=abs(sales)
            blockers.append({'family_id':fid,'main_article':first.get('main_article_number'),'name':first.get('family_description'),'sales':str(sales),'movement_qty':str(movement.get('quantity')),'movement_uom':unit,'reason':result['status']})
        matrix.append(['Seafood',day,fid,first.get('main_article_number'),first.get('family_description'),sales,movement.get('quantity'),unit,cost.get('cost_per_selling_unit'),cost.get('source'),cost.get('date'),result['cogs'],result['gp'],result['gp_pct'],result['status'],len({r.get('ean_upc') for r in members}),'FAMILY_251_MINUS_252_NO_UPC_ALLOCATION',batch_id,reported,comparison,'POS_SALES_DIV_REPORTED_QTY_IS_NOT_VERIFIED_PRICE_PER_LB',sales/d(movement['quantity']) if movement.get('status')=='READY' and d(movement.get('quantity'))>0 else None,gp_qty,gp_unit,gp_basis])
    # Do not claim complete if a POS family was absent, a movement-only family is
    # unresolved, or department revenue does not equal the reconstructed scope.
    complete=bool(days) and failures==0 and unresolved_sales==0 and abs(resolved_sales-d(daily.get('sales_dollars')))<=Decimal('.01')
    estimated_gp=total_gp
    estimates=[]
    for item in blockers:
        sales=d(item['sales']);fid=item['family_id'];members=grouped[fid]
        rec=next(r for r in matrix[1:] if r[2]==fid)
        qty=rec[6];cost=rec[8]
        if qty is not None and d(qty)!=0 and cost is not None:
            adjustment=sales-d(qty)*d(cost);basis='NET_FAMILY_MOVEMENT_COST_WITH_POS_MISMATCH'
        else:
            adjustment=sales*(total_gp/resolved_sales) if resolved_sales else Decimal(0)
            basis='RESOLVED_DEPARTMENT_MARGIN_FALLBACK' if sales else 'NO_RELIABLE_COST_ADJUSTMENT_AVAILABLE'
        estimated_gp+=adjustment
        estimates.append({**item,'estimated_gp':str(adjustment),'estimate_basis':basis})
    missing_sales=d(daily.get('sales_dollars'))-resolved_sales-sum((d(x['sales']) for x in blockers),Decimal(0))
    if missing_sales:
        adjustment=missing_sales*(total_gp/resolved_sales) if resolved_sales else Decimal(0)
        estimated_gp+=adjustment
        estimates.append({'sales':str(missing_sales),'estimated_gp':str(adjustment),'reason':'POS_SALES_OUTSIDE_FAMILY_SCOPE','estimate_basis':'RESOLVED_DEPARTMENT_MARGIN_FALLBACK'})
    return matrix,{'estimated_department_gp':estimated_gp,'estimated_department_gp_pct':estimated_gp/d(daily.get('sales_dollars')) if d(daily.get('sales_dollars')) else None,'estimate_details':estimates,'estimate_status':'ESTIMATED' if not complete else 'COMPLETE','status':('COMPLETE_WITH_CONFIRMED_POS' if pos_fallbacks else 'COMPLETE_FAMILY_MVT') if complete else 'PARTIAL_FAMILY_MVT','gp':total_gp if complete else None,'cogs':total_cogs if complete else None,'verified_family_gp_subtotal':total_gp,'unresolved_sales':unresolved_sales,'family_count':len(matrix)-1,'blockers':blockers,'resolved_sales':resolved_sales,'sales_reconciliation_gap':d(daily.get('sales_dollars'))-resolved_sales}
