"""Live FisherMan evaluation. Resumable, paced, and read-only against store data."""
import argparse
import concurrent.futures
import json
import re
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = 'https://seal-app-tkkkd.ondigitalocean.app'


def build_cases(reference):
    products = [r for r in reference['items'] if float(r.get('sold_quantity') or 0) > 0][:20]
    assert len(products) == 20
    cases = []
    def add(category, question, *, history=None, **expect):
        cases.append({'id': f'Q{len(cases)+1:03}', 'category': category,
                      'question': question, 'history': history or [], 'expect': expect})
    for row in products:
        name, upc = row['name'], str(row['upc'])
        item = f'{name}, UPC {upc}'
        add('sales', f'How is {item} selling? Keep it brief.', tools=['get_sales_performance'], available_sales=True)
        add('sales', f'How many selling units of {item} did we sell October 7–13, 2026? Show its actual unit.', tools=['get_sales_performance'], number=float(row['sold_quantity']), unit=row.get('qty_uom') or row.get('selling_uom'))
        add('sales', f'What were sales dollars for {item} from October 7 through October 13, 2026?', tools=['get_sales_performance'], number=float(row['sales_amount']))
        add('sales', f'Compare the latest 7-day and 14-day sales performance for {item}. Show actual supported dates and daily velocity.', tools=['get_sales_performance'])
        add('sales', f'Compare {item} from October 1–13 this year with October 1–13 last year. Show sales dollars, selling quantity and price. Do not invent missing history.', tools=['get_sales_performance'])
    for row in products:
        item=f"{row['name']}, UPC {row['upc']}"
        for q in [f'Quick check {item}: how much stock is actually available and how old is the stock information?',
                  f'What is the effective OH for {item}? Use the latest snapshot plus later valid movements.',
                  f'Check {item} for potential old stock and days of stock remaining. Explain briefly.',
                  f'Is {item} overstocked? Compare family receipts with family selling movement and show the last two receipts.']:
            add('stock',q,store_tools=True)
    for row in products:
        item=f"{row['name']}, UPC {row['upc']}"
        for q in [f'What is the current selling price, price type and selling unit of {item}? No recommendation.',
                  f'Show current price and company A, B and C prices for {item}. Do not display the current cost.',
                  f'Suggest a price for {item} to improve GP dollars per day while protecting velocity. Use supported price history.',
                  f'Is {item} still inside a seven-completed-day price observation period? Should I change it now?',
                  f'Compare historical REG and SALE prices for {item}. Which supported price had better GP dollars per day and velocity?']:
            add('pricing',q,store_tools=True,no_cost='Do not display the current cost.' in q)
    for row in products:
        item=f"{row['name']}, UPC {row['upc']}"
        for q in [f'Find the current effective cost of {item}, its source date and cost unit.',
                  f'What GP percent does {item} have at its current price using the current effective cost? Verify the cost and price units first.',
                  f'Quick check {item}: is the cost from the latest receipt valuation, the Live/Fresh/Frozen report, or OH fallback?']:
            add('cost',q,store_tools=True)
    for row in products[:14]:
        item=f"{row['name']}, UPC {row['upc']}"
        for q in [f'Estimate weekly usage for {item} with no promotion. Show weekly regular baseline.',
                  f'Estimate weekly usage for {item} with three promotion days. Use historical REG plus TPR and SALE velocity.',
                  f'Estimate weekly usage for {item} with seven promotion days. Label confidence and show the selling unit.',
                  f'Estimate usage for {item} during October 16–22, 2026. Sale only Friday, Saturday and Sunday; regular for the other days. Show exact promotion dates.',
                  f'How much of {item} will we use this week if there is no SALE history? Estimate promotion usage at twice regular usage, with low confidence. Assume three promotion days.']:
            add('weekly_usage',q,weekly=True,store_tools=True)
    receiving = [
        'How should a delivery recorded with movements 107 and 109 be counted?',
        'The same physical delivery has 101, 107 and 109 records. Should I add all three quantities?',
        'Can you get one UPC sold quantity from its family movement 251 minus 252?',
        'Which source should you use for UPC quantity sold: POS or family movement?',
        'Family movement is in LB but the UPC sells by each. Can you add those quantities?',
        'Can POS sales dollars divided by sold units tell you the UPC weight in pounds?',
        'What source has first priority for effective cost?',
        'If no receipt valuation cost exists, which cost source comes next?',
        'If both report cost and OH cost exist, which should win?',
        'Which is the current selling price if a newer price list and an older POS price disagree?',
        'Should SAP retail be used as the current UPC selling price?',
        'Explain Price List priority: IN STORE, SALE, TPR, REG.',
        'A UPC sold $100 and 20 each. What actual average selling price did it achieve?',
        'A UPC sold $80 and 10 LB. What was the actual average selling price per LB?',
        'A UPC sold $0 and zero units. Can you calculate its sold-event average price?',
        'One 4841 each weighs 2.2 LB. Receipt cost is $4 per LB. What is cost per each?',
        'One 4843 each weighs 2 LB. Receipt cost is $6 per LB. What is cost per each?',
        'A 240439 case contains 60 each. Demand is 125 each. How many whole cases cover it?',
        'MBF8501GR has 12 each per pack. Weekly demand is 25 each. How many full packs cover it?',
        'Stock snapshot is 100 LB, later receipts 40 LB, valid sales 30 LB and dumping 5 LB. What is effective stock?',
        'A new OH upload arrives after an earlier True Stock count. Which stock baseline applies?',
        'Does entering True Stock freeze the current stock balance forever?',
        'I set True Stock to zero and later receive 20 LB. What is stock before any later sales?',
        'System stock is negative. Should the ordering estimate credit negative stock?',
        'Can expired stock be credited toward the next delivery requirement?',
        'If we have only five supported days within seven calendar days, what denominator should velocity use?',
        'Should a missing POS day be filled as zero sales?',
        'How is popularity calculated for a specific price type?',
        'An item sold on 7 of 7 supported days at a price. What is popularity?',
        'An item sold on 4 of 7 supported days at a price. What is popularity?',
        'Should 240 and 249 prices match for the same linked product?',
        'When 240 is on promotion, does its linked 249 participate?',
        'Is 240 always a packaged item?',
        'Which prefix usually represents packaged items: 240 or 245?',
        'Should 245 packaged and 247 bones/heads be forced to exactly the 240 main price?',
        'How do you avoid counting one physical receipt twice?',
        'Does observed Tuesday or Wednesday receiving suggest Fresh or Frozen?',
        'Does observed Friday or Saturday receiving suggest Fresh or Frozen?',
        'If the only delivery weekday is Thursday, should you decide the category automatically?',
        'Can a live item category be decided only by receiving weekday?',
    ]
    for q in receiving:add('receiving_units',q)
    qa = [
        'What do Fish Base, Fish Watch and FishFinder each do?',
        'Are mobile stock numbers from Full MySQL or should I assume they come from Google Drive?',
        'What are the latest accepted POS, movement and price file dates?',
        'Can a QA HOLD item be treated as confirmed zero stock?',
        'What does stale stock information mean? Does it prove the stock is zero?',
        'My POS is current but the movement file is old. Can stock roll-forward still be called current?',
        'Can you say sales dropped if last-year sales data is missing?',
        'Can you say a new price improved results after only two completed days?',
        'How many completed days should a REG price step be observed?',
        'If a suggested price differs by only ten cents, should you recommend changing it?',
        'What is the normal minimum price change worth suggesting?',
        'Can you recommend REG equal to or below SALE?',
        'Should a regular suggestion normally remain inside the company A/B/C price range?',
        'What is the exception for Fresh stock beyond seven DOH that needs clearance?',
        'What do the GP colors mean above 36%, from 30–36%, and below 30%?',
        'Which should drive price decisions: GP dollars per day or GP percentage alone?',
        'If quantity sold falls but GP dollars per day rises, should we automatically declare the price a success?',
        'What do you need before converting a pack quantity into pounds?',
        'Can you create an actual store forecast using made-up daily sales?',
        'If the source is unavailable, should you guess current price or clearly say it cannot be verified?',
    ]
    for q in qa:add('quality_rules',q)
    follows = [
        ('How is tilapia selling?','Which tilapia product?','24053300000'),
        ('How is live tilapia selling?','The requested end date is unsupported.','try again'),
        ('Check UPC 24053300000 sales.','The end date is unsupported.','try again'),
        ('Show live tilapia sales for this year.','I can check the supported sales dates.','Compare to last year'),
        ('Suggest a price for fresh tilapia.','Which UPC?','24053300000'),
        ('Check current price for tilapia.','Which UPC?','24060200000'),
        ('Estimate weekly usage for tilapia with three promotion days.','Which product?','24053300000'),
        ('Estimate weekly usage for live tilapia with seven promotion days.','Which product?','24060200000'),
        ('Estimate oyster weekly usage with no promotion.','Which oyster?','OYSTER IN SHELL 60EA UPC 4029551780'),
        ('Show sales of UPC 24053300000.','It sold 161.3 LB during Oct 7–13.','more'),
        ('Show sales of UPC 24060200000.','Here is the latest supported result.','What about GP dollars per day?'),
        ('Show current price for UPC 24053300000.','The current record needs verification.','Check the latest price list'),
        ('Estimate weekly usage for UPC 24053300000 with zero promo days.','Regular weekly usage needs the historical source.','Now apply three promotion days'),
        ('Estimate weekly usage for UPC 24053300000 with three promo days.','The estimator uses regular and promotion rates.','Now seven days'),
        ('Check UPC 24053300000 current stock.','Please verify effective stock from the source.','What about the last two receipts?'),
        ('Can you check stock?','Which product?','Fresh catfish UPC 24052700000'),
        ('What is the cost?','Which product?','Live tilapia UPC 24060200000'),
        ('Show company prices.','Which product?','Golden pompano UPC 24057100000'),
        ('Compare sales.','Which product and periods?','24053300000, October 1–13, 2026 versus October 1–13, 2025'),
        ('What should I order this week?','Which product?','Live tilapia with three sale days'),
        ('Explain movement and POS quantities.','Family and UPC quantities have different sources.','Use a short table'),
        ('I want company B price for live tilapia.','Which UPC?','24060200000, no cost display'),
        ('Check frozen shrimp stock.','Which frozen shrimp?','16/20 H/L JUMBO WHITE SHRIMP 10/5LB UPC 75339325301'),
        ('Check tilapia price.','Which UPC?','24053300000. Answer briefly in Spanish.'),
        ('Check tilapia sales.','Which UPC?','24053300000。用廣東話繁體字回答。'),
        ('Estimate tilapia usage for October 16–22, sale Friday–Sunday.','Which tilapia UPC?','24053300000'),
        ('Show current price and GP of UPC 24053300000.','The source must be verified.','Do not show cost, only current price and GP%'),
        ('How is tilapia selling?','There are fresh, frozen and live variants.','the live one'),
        ('Show UPC 24053300000 REG versus SALE performance.','Use historical price-type evidence.','Treat TPR as REG only for the weekly usage estimate'),
        ('Estimate weekly usage for 24053300000 with 3 sale days.','How much promotion?','Three sale days, no delivery dates needed'),
    ]
    for first,reply,last in follows:
        add('follow_up',last,history=[{'role':'user','content':first},{'role':'assistant','content':reply}],weekly='usage' in first.lower() or 'order this week' in first.lower(),store_tools=any(w in first.lower() for w in ['stock','price','sales','selling','cost','usage','order','receipts']))
    assert len(cases)==500,Counter(x['category'] for x in cases)
    # Interleave categories so early results cover every user workflow.
    groups={c:[x for x in cases if x['category']==c] for c in dict.fromkeys(x['category'] for x in cases)}
    ordered=[]
    while any(groups.values()):
        for bucket in groups.values():
            if bucket:ordered.append(bucket.pop(0))
    for i,c in enumerate(ordered,1):c['id']=f'Q{i:03}'
    return ordered


def inspect(case,result):
    flags=[]
    if result.get('http_status')!=200:return ['TRANSPORT_OR_SERVER_ERROR']
    payload=result.get('response') or {};answer=str(payload.get('answer') or '');low=answer.lower();expect=case['expect']
    if not answer.strip():return ['EMPTY_ANSWER']
    if re.search(r'END_DATE_NOT_SUPPORTED|START_DATE_NOT_SUPPORTED|TRACEBACK|OPENAI_TOOL_LOOP_LIMIT',answer):flags.append('RAW_INTERNAL_ERROR')
    tools=payload.get('tool_calls') or []
    if expect.get('tools') and not any(t in tools for t in expect['tools']):flags.append('EXPECTED_SOURCE_TOOL_NOT_USED')
    if expect.get('store_tools') and not tools:flags.append('STORE_FACT_WITHOUT_TOOL_REVIEW')
    if expect.get('available_sales') and re.search(r"(?:cannot|can.t|unable to).{0,55}(?:retrieve|report|verify|access)|unsupported.{0,20}date",low):flags.append('AVAILABLE_SALES_REJECTED')
    if expect.get('weekly') and re.search(r'(?:what|which|provide|need|confirm|tell me).{0,45}(?:delivery date|next delivery)|(?:delivery date|next delivery).{0,35}\?',low):flags.append('UNNECESSARY_DELIVERY_DATE_QUESTION')
    if expect.get('no_cost') and re.search(r'(?:current|effective|latest|unit) cost\s*[:|]?\s*\$?\d|\|\s*cost\s*\|\s*\$?\d',low):flags.append('IGNORED_NO_COST_DISPLAY')
    if 'number' in expect:
        numbers=[float(x) for x in re.findall(r'(?<![\w])\d+(?:\.\d+)?',answer.replace(',',''))]
        tolerance=max(.021,abs(expect['number'])*.002)
        if not any(abs(x-expect['number'])<=tolerance for x in numbers):flags.append('SOURCE_NUMBER_MISMATCH_REVIEW')
    if len(answer)>2800:flags.append('TOO_LONG_FOR_QUICK_CHECK')
    if result.get('seconds',0)>45:flags.append('SLOW_OVER_45_SECONDS')
    return flags


def request_case(case,phase):
    start=time.monotonic();record={'id':case['id'],'category':case['category'],'question':case['question'],'history':case['history'],'expect':case['expect'],'phase':phase,'started_at':datetime.now(timezone.utc).isoformat()}
    language='' if ('Spanish' in case['question'] or '廣東話' in case['question']) else '\nReply in English.'
    data=json.dumps({'message':case['question']+language,'history':case['history']}).encode()
    try:
        req=urllib.request.Request(BASE+'/v1/yipman/ai/chat',data=data,headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=100) as r:record.update(http_status=r.status,response=json.loads(r.read()))
    except urllib.error.HTTPError as exc:
        record.update(http_status=exc.code,error=exc.read().decode()[:2000])
    except Exception as exc:record.update(http_status=0,error=f'{type(exc).__name__}: {exc}')
    record['seconds']=round(time.monotonic()-start,2);record['flags']=inspect(case,record)
    return record


def run(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    cases=build_cases(json.loads(Path(args.reference).read_text()))
    (out/'questions.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2))
    if args.ids:
        selected=set(args.ids.split(','));cases=[c for c in cases if c['id'] in selected]
    results=out/(args.phase+'.jsonl');completed={json.loads(s)['id'] for s in results.read_text().splitlines() if s.strip()} if results.exists() else set()
    pending=[c for c in cases if c['id'] not in completed]
    print(json.dumps({'event':'start','phase':args.phase,'total':len(cases),'remaining':len(pending),'interval':args.interval}),flush=True)
    active={};last_start=0.;processed=len(completed);flags=0;started=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool,results.open('a',buffering=1) as handle:
        while pending or active:
            now=time.monotonic()
            if pending and len(active)<3 and now-last_start>=args.interval:
                case=pending.pop(0);active[pool.submit(request_case,case,args.phase)]=case;last_start=now
            finished=[f for f in active if f.done()]
            for f in finished:
                record=f.result();active.pop(f);handle.write(json.dumps(record,ensure_ascii=False)+'\n');handle.flush()
                processed+=1;flags+=bool(record['flags'])
                print(json.dumps({'event':'result','id':record['id'],'category':record['category'],'http':record['http_status'],'seconds':record['seconds'],'flags':record['flags'],'done':processed,'total':len(cases),'answer':str(record.get('response',{}).get('answer',''))[:180]},ensure_ascii=False),flush=True)
                (out/'progress.json').write_text(json.dumps({'phase':args.phase,'done':processed,'total':len(cases),'flagged_this_run':flags,'active':len(active),'elapsed_seconds':round(time.monotonic()-started),'updated_at':datetime.now(timezone.utc).isoformat()}))
                if record['http_status']==429:last_start=time.monotonic()+60
            time.sleep(.2)
    print(json.dumps({'event':'complete','phase':args.phase,'done':processed,'total':len(cases),'flagged_this_run':flags}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--reference',required=True);parser.add_argument('--output',required=True);parser.add_argument('--phase',default='baseline');parser.add_argument('--interval',type=float,default=6.2);parser.add_argument('--ids',default='');run(parser.parse_args())
