"""Shared read-only inventory card sales evidence for desktop and mobile."""
from __future__ import annotations
from datetime import date, datetime, timezone
from calendar import monthrange
from decimal import Decimal, InvalidOperation
from collections import OrderedDict
import threading
import time


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = Decimal(str(value))
        return value if value.is_finite() else None
    except (ValueError, InvalidOperation):
        return None


def date_text(value):
    return value.isoformat() if isinstance(value, date) else str(value or '')[:10]


def recent_start(today):
    d=date.fromisoformat(date_text(today))
    month=d.year*12+d.month-1-3
    year, month0=divmod(month,12)
    return date(year,month0+1,min(d.day,monthrange(year,month0+1)[1])).isoformat()

def selling_days(member, price_type, selected):
    if not member.get('uom'):
        return None
    rows={date_text(d['date']):d for d in member.get('days',[]) if date_text(d['date']) in selected}
    count=0
    for day in rows.values():
        found=next((r for r in day.get('typeSales',[]) if r.get('type')==price_type),None)
        if found is None and day.get('type')==price_type and (day.get('valid') or day.get('reason') in ('COST_OR_UNIT_UNVERIFIED','POS_WEIGHT_ESTIMATED')):
            found=day
        if found and number(found.get('qty')) is not None and number(found['qty'])>0 and number(found.get('sales')) is not None and number(found['sales'])>=0:
            count+=1
    return count

def popularity(member, price_type, selected):
    """Daily POS frequency at this type; missing evidence is not zero sales."""
    if not member.get('uom'):
        return {'sellingDays': None, 'appliedDays': None, 'popularityPct': None}
    rows={date_text(d['date']):d for d in member.get('days',[]) if date_text(d['date']) in selected}
    applied=sold=0
    for day in rows.values():
        found=next((r for r in day.get('typeSales',[]) if r.get('type')==price_type),None)
        if found is None and day.get('type')==price_type and (day.get('valid') or day.get('reason') in ('COST_OR_UNIT_UNVERIFIED','POS_WEIGHT_ESTIMATED')):
            found=day
        if found is None:
            continue
        qty, sales=number(found.get('qty')), number(found.get('sales'))
        if qty is None or sales is None or qty<0 or sales<0 or (qty==0 and sales!=0):
            continue
        applied+=1
        sold+=int(qty>0)
    return {'sellingDays':sold, 'appliedDays':applied,
            'popularityPct':Decimal(100)*sold/applied if applied else None}

def recent_reference(member, price_type, start, today):
    rows={}
    for day in member.get('days',[]):
        dt=date_text(day['date'])
        if not start <= dt < today: continue
        types=day.get('typeSales',[])
        found=next((r for r in types if r.get('type')==price_type),None)
        if found is None and day.get('type')==price_type and (day.get('valid') or day.get('reason') in ('COST_OR_UNIT_UNVERIFIED','POS_WEIGHT_ESTIMATED')):
            found=day
        if found is not None and number(found.get('qty')) is not None and number(found['qty'])>=0 and number(found.get('sales')) is not None and number(found['sales'])>=0:
            rows[dt]=found
    values=list(rows.values())
    qty=sum((number(r['qty']) for r in values),Decimal(0))
    sales=sum((number(r['sales']) for r in values),Decimal(0))
    gp=[number(r.get('gp')) for r in values if number(r.get('gp')) is not None]
    valid=bool(values) and bool(member.get('uom'))
    return {**popularity(member,price_type,{date_text(d['date']) for d in member.get('days',[]) if start<=date_text(d['date'])<today}),'periodDays':(date.fromisoformat(today)-date.fromisoformat(start)).days,'quantity':qty if valid else None,'average':qty/len(values) if valid else None,'price':sales/qty if valid and qty>0 else None,'gpDays':len(gp) if valid else 0,'gpDay':sum(gp,Decimal(0))/len(gp) if valid and gp else None,'days':len(values) if valid else 0,'start':start,'through':max(rows) if rows else None}

def summarize(page, movements):
    today = date_text(page['today'])
    dates = sorted({date_text(d) for d in page.get('days', []) if date_text(d) < today})
    start=recent_start(today)
    members = {}
    for item in page.get('items', []):
        for member in item.get('members', []):
            members[member['upc']] = member
    def average(member, price_type, window):
        selected = set(dates[-window:])
        rows = {date_text(d['date']): d for d in member.get('days', []) if date_text(d['date']) in selected}
        rows = [d for d in rows.values() if (d.get('valid') or d.get('reason') in ('COST_OR_UNIT_UNVERIFIED','POS_WEIGHT_ESTIMATED')) and d.get('type') == price_type and number(d.get('qty')) is not None and number(d['qty']) >= 0 and number(d.get('sales')) is not None and number(d['sales']) >= 0]
        quantity = sum((number(d['qty']) for d in rows), Decimal(0))
        sales = sum((number(d['sales']) for d in rows), Decimal(0))
        unit = member.get('uom')
        profits = [number(d.get('gp')) for d in rows if number(d.get('gp')) is not None]
        gp_day = sum(profits, Decimal(0)) / len(profits) if profits and unit else None
        return {**popularity(member,price_type,selected),'periodDays':window,'gpDays':len(profits) if unit else 0,'gpDay': gp_day, 'average': quantity / len(rows) if rows and unit else None, 'price': sales / quantity if quantity > 0 and unit else None, 'quantity': quantity, 'days': len(rows) if unit else 0, 'start': min(selected) if selected else None, 'through': max(selected) if selected else None}
    out = []
    for member in members.values():
        types = {d['type'] for d in member.get('days', []) if d.get('valid') and d.get('type') and number(d.get('qty')) is not None and number(d['qty']) > 0 and date_text(d['date']) < today}
        types.update(r['type'] for d in member.get('days',[]) if start<=date_text(d['date'])<today for r in d.get('typeSales',[]) if number(r.get('qty')) is not None and number(r['qty'])>0)
        types.update(d['type'] for d in member.get('days',[]) if start<=date_text(d['date'])<today and d.get('type') and d.get('reason') in ('COST_OR_UNIT_UNVERIFIED','POS_WEIGHT_ESTIMATED') and number(d.get('qty')) is not None and number(d['qty'])>0)
        types={t for t in types if any(start<=date_text(d['date'])<today and ((d.get('type')==t and (d.get('valid') or d.get('reason') in ('COST_OR_UNIT_UNVERIFIED','POS_WEIGHT_ESTIMATED')) and number(d.get('qty')) is not None and number(d['qty'])>0) or any(r.get('type')==t and number(r.get('qty')) is not None and number(r['qty'])>0 for r in d.get('typeSales',[]))) for d in member.get('days',[]))}
        if not types:
            continue
        selected=set(dates[-7:])
        quantities={date_text(d['date']):number(d.get('qty')) for d in member.get('days',[]) if date_text(d['date']) in selected and number(d.get('qty')) is not None and number(d['qty'])>=0 and number(d.get('sales')) is not None and number(d['sales'])>=0 and not (number(d['qty'])==0 and number(d['sales'])!=0) and d.get('reason')!='QUANTITY_OR_RETURN_REVIEW'}
        qty7=sum(quantities.values(),Decimal(0)) if quantities and member.get('uom') else None
        out.append({'posQty7':qty7,'velocity7':qty7/len(selected) if qty7 is not None and selected else None,'current':member.get('current'),'upc': member['upc'], 'name': member.get('name'), 'uom': member.get('uom') or '', 'types': [{'type': t, 'seven': average(member, t, 7), 'fourteen': average(member, t, 14), 'recent': recent_reference(member,t,start,today)} for t in sorted(types, key=lambda t: ({'REG': 0, 'TPR': 1, 'SALE': 2, 'IN STORE': 3, 'IN_STORE': 3}.get(t, 4), t))]})
    for result in out:
        if members[result['upc']].get('quantityStatus') not in ('POS_WEIGHT_MISSING','POS_WEIGHT_ESTIMATED'):
            continue
        result.update(quantityStatus='POS_WEIGHT_ESTIMATED', quantityBasis='POS_SALES_DIVIDED_BY_STABLE_HISTORICAL_TICKET')
        for row in result['types']:
            for key in ('seven', 'fourteen', 'recent'):
                row[key]['estimated'] = True
                if not row[key]['days']:
                    row[key].update(quantity=None, average=None, price=None, gpDay=None, gpDays=0)
    out.sort(key=lambda m:(m['posQty7'] is None,-(m['posQty7'] or 0),m['upc']))
    return {'historyStart':start,'historyMonths':3,'through': max(dates) if dates else None, 'movement': movements, 'members': out}


def build_summary(family):
    from mobile_pricing import build_page
    from db import db_conn
    from business_clock import completed_through_date
    from data_coverage import source_data_days
    from webapp_v2_runtime import _ordering_family_movement_metrics, _family_receipt_events, _receipt_events_summary
    # Internal builder reads a complete family in one bounded request; it never
    # changes the public mobile-pricing endpoint's pagination contract.
    page = build_page(family=family, limit=10000, history_days=100)
    family_ids = {int(i['familyId']) for i in page['items']}
    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            if not family_ids:
                cur.execute('SELECT family_id FROM product_family WHERE main_article_number=%s OR family_id=%s LIMIT 1', (family, int(family)))
                row = cur.fetchone()
                if row:
                    family_ids.add(int(row['family_id']))
            if len(family_ids) != 1:
                raise ValueError('Family identity unavailable or ambiguous.')
            fid = next(iter(family_ids))
            movement = {}
            for name, count in [('seven', 7), ('fourteen', 14)]:
                days = sorted(source_data_days(cur, 'movement', limit=count, up_to=completed_through_date()), key=lambda d: d['date'])
                metrics = _ordering_family_movement_metrics(cur, fid, days)
                valid = metrics.get('status') == 'READY' and number(metrics.get('quantity')) is not None and number(metrics['quantity']) >= 0 and metrics.get('uom') and days
                receipts = _family_receipt_events(cur, fid, count, data_days=days)
                receipt = _receipt_events_summary(receipts)
                unresolved = any(number(e.get('receipt_quantity')) is None for e in receipts)
                receipt_qty = number(receipt.get('quantity'))
                receipt_uom = receipt.get('uom') or metrics.get('uom')
                if receipt.get('event_count') == 0 and days and not unresolved:
                    receipt_qty = Decimal(0)
                receipt_ready = bool(days) and not unresolved and receipt_qty is not None and receipt_uom not in (None, '', 'MIXED')
                movement[name] = {'average': number(metrics['quantity']) / len(days) if valid else None, 'price': None, 'quantity': metrics.get('quantity') if valid else 0, 'days': len(days) if valid else 0, 'uom': metrics.get('uom') or '', 'start': date_text(days[0]['date']) if days else None, 'through': date_text(days[-1]['date']) if days else None, 'status': metrics.get('status'), 'basis': metrics.get('basis'), 'supportedDays': [date_text(d['date']) for d in days]}
                movement[name]['receipt'] = {'quantity': receipt_qty if receipt_ready else None, 'uom': receipt_uom or None, 'status': 'READY' if receipt_ready else 'UNVERIFIED', 'days': len(days), 'start': movement[name]['start'], 'through': movement[name]['through'], 'basis': 'CANONICAL_COMPLETED_PHYSICAL_RECEIPTS_101_OR_109_NO_DOUBLE_COUNT'}
            diagnostic=None
            if any(m.get('status')!='READY' for m in movement.values()):
                from family_movement_read import movement_evidence
                diagnostic=movement_evidence(cur,fid,days)
        finally:
            cur.close()
    result=summarize(page, movement)
    if diagnostic is not None:
        result['movementEvidence']=diagnostic
    return result


_cache = OrderedDict()
_lock = threading.Lock()


def install_inventory_sales(app, api):
    from fastapi import HTTPException
    from fastapi.encoders import jsonable_encoder
    from read_singleflight import ReadSingleFlight, ReadBusy
    reads = ReadSingleFlight(max_running=2, wait_seconds=20)
    @app.get('/v1/app/inventory-sales')
    def inventory_sales(family: str):
        if not family.isdigit() or len(family) > 18:
            raise HTTPException(422, 'Invalid family article.')
        def produce():
            with _lock:
                cached = _cache.get(family)
                if cached and time.monotonic() - cached[0] < 300:
                    return cached[1]
            result = jsonable_encoder({'sales': build_summary(family), 'checkedAt': datetime.now(timezone.utc).isoformat(), 'source': 'FULL MYSQL', 'basis': 'FAMILY_MVT_AND_SEPARATE_UPC_POS'})
            with _lock:
                _cache[family] = (time.monotonic(), result)
                while len(_cache) > 300:
                    _cache.popitem(last=False)
            return result
        try:
            return reads.run(family, produce)
        except ReadBusy:
            raise HTTPException(503, 'Sales history busy. Retry shortly.')
    for name in ('backoffice_html', 'yipman_html'):
        original = getattr(api, name)
        def render(*args, _original=original, **kwargs):
            html = _original(*args, **kwargs)
            return html if 'inventorySalesDesktop' in html else html.replace('</body>', DESKTOP_SCRIPT + '</body>', 1)
        setattr(api, name, render)


DESKTOP_SCRIPT = r'''
<style id="inventorySalesDesktop">
#ydesk .inventory-sales-card{grid-column:1/-1;width:100%;min-width:0;margin:6px 0;padding:8px;border-top:1px solid currentColor;font-size:14px}
.inventory-sales-card .mvt-summary{display:flex;gap:24px;flex-wrap:wrap}.inventory-sales-card table{width:100%;font-size:13px;border-collapse:collapse}.inventory-sales-card th,.inventory-sales-card td{padding:5px;text-align:left;border-bottom:1px solid #55715d}.inventory-sales-card small{font-size:11px}.inventory-sales-card details{margin-top:6px}.inventory-sales-card .sales-upc{margin-top:8px;font-weight:bold}
</style>
<script>
(()=>{
 const cache=new Map(),pending=new Map(),queue=[];let running=0;
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt=x=>x==null?'—':Number(x).toLocaleString(undefined,{maximumFractionDigits:2});
 function pump(){while(running<2&&queue.length){const work=queue.shift();running++;work().finally(()=>{running--;pump()})}}
 function read(family){const old=cache.get(family);if(old&&Date.now()-old.at<300000)return Promise.resolve(old.data);if(pending.has(family))return pending.get(family);const p=new Promise((resolve,reject)=>{queue.push(async()=>{try{const r=await fetch('/v1/app/inventory-sales?family='+encodeURIComponent(family),{cache:'no-store',signal:AbortSignal.timeout(45000)});const d=await r.json();if(!r.ok||!d.sales)throw Error(d.detail||'Sales history unavailable');cache.set(family,{at:Date.now(),data:d.sales});resolve(d.sales)}catch(e){reject(e)}finally{pending.delete(family)}});pump()});pending.set(family,p);return p}
 function avg(v,u){if(!v)return '—';return '<small>POS qty</small><br><b>'+fmt(v.quantity)+' '+esc(u)+'</b><br><small>Avg/day</small><br><b>'+fmt(v.average)+' '+esc(u)+'/day</b><br><small>Avg price</small><br><b>'+(v.price==null?'—':'$'+Number(v.price).toFixed(2))+' / '+esc(u)+'</b><br><small>GP$/day</small><br><b>'+(v.gpDay==null?'—':'$'+Number(v.gpDay).toFixed(2))+' / day</b><br><small>Popularity: '+(v.popularityPct==null?'—':fmt(v.popularityPct)+'%')+'</small><br><small>'+v.days+' valid days</small>'}
 function paint(node,d,upc){const rows=upc?d.members.filter(m=>m.upc===upc):d.members;node.innerHTML='<div class="mvt-summary">'+[['7D',d.movement.seven],['14D',d.movement.fourteen]].map(([label,m])=>'<div><small>'+label+' Receipts · total</small><br><b>'+fmt(m.receipt?.quantity)+' '+esc(m.receipt?.uom||m.uom||'—')+'</b><br>'+label+' Family MVT · avg/day<br><b>'+fmt(m.average)+' '+esc(m.uom||'—')+'/day</b><br><small>'+esc(m.through||'Not verified')+' · '+m.days+' valid days</small></div>').join('')+'<small>3M POS: '+esc(d.historyStart)+' – '+esc(d.through)+'</small>'+rows.map(m=>'<div class="sales-upc">'+esc(m.name)+' · UPC '+esc(m.upc)+'</div><table><thead><tr><th>Price type</th><th>7D POS</th><th>14D POS</th><th>3M POS</th></tr></thead><tbody>'+m.types.map(t=>'<tr><th>'+esc(t.type)+'</th><td>'+avg(t.seven,m.uom)+'</td><td>'+avg(t.fourteen,m.uom)+'</td><td>'+avg(t.recent,m.uom)+'</td></tr>').join('')+'</tbody></table>').join('')+'<details><summary>Sales source & dates</summary><small>MVT 251 − 252 is the family total. Price-type rows use UPC POS only. Avg/day = quantity ÷ valid days at that price type, including verified zero-sales days. Avg sold price = sales ÷ quantity. GP$/day divides verified historical GP by verified GP days; POS/GP day counts show coverage. 7D/14D exclude missing and mixed-price days; 3M includes verified actual type quantities on mixed-price days. Popularity = positive-sales days ÷ verified applied days at that price type × 100%. Verified zero-sales days count in the denominator; each mixed-price day counts once per verified type. No applied days shows —. Missing cost leaves GP$ unverified.</small></details>';if(rows.some(m=>m.quantityStatus==='POS_WEIGHT_ESTIMATED'))node.insertAdjacentHTML('afterbegin','<p>Estimated LB and GP: POS dollars divided by the stable historical price-list ticket. Actual POS weight is unavailable; item counts are not LB. Avg price is a ticket reference, not an independently measured selling price.</p>');node.dataset.loaded='1'}
 const observe=new IntersectionObserver(entries=>entries.forEach(e=>{if(!e.isIntersecting)return;const n=e.target;if(n.dataset.loading||n.dataset.loaded)return;n.dataset.loading='1';read(n.dataset.family).then(d=>{if(n.isConnected)paint(n,d,n.dataset.upc)}).catch(()=>{if(n.isConnected)n.innerHTML='<small>Sales history unavailable.</small> <button type="button">Retry</button>';const b=n.querySelector('button');if(b)b.onclick=e=>{e.stopPropagation();delete n.dataset.loading;observe.unobserve(n);observe.observe(n)}}).finally(()=>delete n.dataset.loading)}),{rootMargin:'80px'});
 function attach(){
  document.querySelectorAll('#yd-pi .pirow[data-family]').forEach(row=>{if(row.querySelector('.inventory-sales-card'))return;const n=document.createElement('div');n.className='inventory-sales-card';n.dataset.family=row.dataset.family;n.textContent='Loading sales history…';n.onclick=e=>e.stopPropagation();row.appendChild(n);observe.observe(n)});
  document.querySelectorAll('#invRows tr').forEach(row=>{if(row.dataset.inventorySalesAttached||row.classList.contains('inventory-sales-extra'))return;const family=row.querySelector('[data-family]')?.dataset.family,upc=row.querySelector('[data-upc]')?.dataset.upc;if(!family||!upc)return;row.dataset.inventorySalesAttached='1';const extra=document.createElement('tr');extra.className='inventory-sales-extra';const td=document.createElement('td');td.colSpan=row.children.length;const n=document.createElement('div');n.className='inventory-sales-card';n.dataset.family=family;n.dataset.upc=upc;n.textContent='Loading sales history…';td.appendChild(n);extra.appendChild(td);row.after(extra);observe.observe(n)});
 }
 let scheduled=false;new MutationObserver(()=>{if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;attach()})}).observe(document.body,{childList:true,subtree:true});attach();
})();
</script>
'''


