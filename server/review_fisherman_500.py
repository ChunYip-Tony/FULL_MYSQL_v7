"""Offline source checks for a live FisherMan run; flags require human review."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import statistics


def numbers(answer):
    return [float(x) for x in re.findall(r'(?<![\w])\d+(?:\.\d+)?', answer.replace(',', ''))]


def contains_number(answer, expected, tolerance=.025):
    return any(abs(value-float(expected)) <= max(tolerance, abs(float(expected))*.002) for value in numbers(answer))


def review(root):
    cases = json.loads((root/'questions.json').read_text())
    records = [json.loads(line) for line in (root/'baseline.jsonl').read_text().splitlines() if line.strip()]
    oracle_file = root/'reference-quick-check.json'
    oracles = json.loads(oracle_file.read_text())['items'] if oracle_file.exists() else {}
    rows = []
    checks = Counter()
    for record in records:
        question = record['question']; answer = str(record.get('response', {}).get('answer', ''))
        flags = list(record.get('flags') or [])
        expect = record['expect']
        if 'number' in expect:
            checks['canonical_sales_numbers'] += 1
            if not contains_number(answer, expect['number']): flags.append('CANONICAL_SALES_NUMBER_REVIEW')
        ids = re.findall(r'UPC\s+(\d{1,14})', question, re.I)
        item = oracles.get(ids[0], {}).get('item', {}) if ids else {}
        if expect.get('weekly'):
            match = re.search(r'\|\s*SALE\s*·\s*(\d+)\s*days', answer)
            if not match: match = re.search(r'\((\d+) days\)', answer)
            target = 0 if 'no promotion' in question else 3 if 'three promotion days' in question or 'Assume three' in question or 'Sale only Friday' in question else 7 if 'seven promotion days' in question else None
            if target is not None:
                checks['weekly_promotion_day_counts'] += 1
                if not match or int(match.group(1)) != target: flags.append('PROMOTION_DAY_COUNT_REVIEW')
            unit = str(item.get('selling_uom') or '').upper()
            unit = {'PAC': 'PACK', 'PK': 'PACK', 'EACH': 'EA', 'LBS': 'LB'}.get(unit, unit)
            units = {u.upper() for line in answer.splitlines() if line.startswith('|')
                     for u in re.findall(r'(?:\d+(?:\.\d+)?|—)\s+(lb|ea|each|pack|pac|bx|kg)\b', line, re.I)}
            units = {{'PAC': 'PACK', 'EACH': 'EA'}.get(u, u) for u in units}
            if unit and units:
                checks['weekly_selling_units'] += 1
                if units != {unit}: flags.append('VERIFIED_SELLING_UNIT_REVIEW')
        if item and 'company A, B and C' in question:
            verified = [item.get('company_price_'+key) for key in 'abc']
            if all(value is not None for value in verified):
                checks['available_company_abc_prices'] += 1
                if not all(contains_number(answer, value) for value in verified): flags.append('AVAILABLE_COMPANY_PRICES_REVIEW')
        if item and 'current selling price, price type and selling unit' in question:
            price = item.get('current_price')
            if price is not None:
                checks['current_prices_at_snapshot'] += 1
                if not contains_number(answer, price): flags.append('CURRENT_PRICE_SNAPSHOT_REVIEW')
        if item and 'What GP percent' in question:
            price, cost = item.get('current_price'), item.get('current_cost_per_selling_unit')
            if price is not None and cost is not None and float(price)>0:
                checks['gp_at_current_cost_snapshot'] += 1
                target = (float(price)-float(cost))/float(price)*100
                if not contains_number(answer, target, tolerance=.12): flags.append('CURRENT_GP_SNAPSHOT_REVIEW')
        if item and 'Find the current effective cost' in question:
            cost = item.get('current_cost_per_selling_unit')
            if cost is not None:
                checks['effective_cost_at_snapshot'] += 1
                if not contains_number(answer, cost): flags.append('EFFECTIVE_COST_SNAPSHOT_REVIEW')
        if record['category']=='pricing' and 'historical REG and SALE' in question:
            if re.search(r'SALE\s*[/+]\s*TPR|TPR\s*[/+]\s*SALE', answer): flags.append('SALE_TPR_MERGE_REVIEW')
        for evidence in record.get('response', {}).get('source_evidence') or []:
            decisions = evidence.get('requested_item_decisions') or []
            if decisions:
                checks['exact_upc_price_action_evidence'] += 1
                if any(not d.get('can_recommend_new_price_now') for d in decisions) and re.search(r'^\s*(?:\*\*)?(?:Recommend|Suggest(?: testing)?)\b', answer, re.I):
                    flags.append('BLOCKED_OR_STALE_PRICE_ADVICE_REVIEW')
        rows.append({'id': record['id'], 'category': record['category'], 'flags': sorted(set(flags))})
    statuses = Counter(str(r.get('http_status')) for r in records)
    by_category = Counter(r['category'] for r in records)
    seconds = sorted(r['seconds'] for r in records)
    retests = []
    for path in sorted(root.glob('retest-*.jsonl')):
        retests += [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    summary = {'generated_at': datetime.now(timezone.utc).isoformat(),
               'planned_questions': len(cases), 'completed_questions': len(records),
               'unique_completed_ids': len({r['id'] for r in records}),
               'http_status_counts': dict(statuses), 'category_counts': dict(by_category),
               'source_check_counts': dict(checks),
               'automated_flagged_records': sum(bool(r['flags']) for r in rows),
               'automated_flags': dict(Counter(flag for r in rows for flag in r['flags'])),
               'median_seconds': round(statistics.median(seconds), 2) if seconds else None,
               'p95_seconds': seconds[min(len(seconds)-1,int(len(seconds)*.95))] if seconds else None,
               'targeted_retest_count': len(retests),
               'actual_serving_revision_counts': dict(Counter(r.get('response', {}).get('server_revision') or 'UNSTAMPED_DURING_ROLLOUT' for r in records)),
               'retest_actual_serving_revision_counts': dict(Counter(r.get('response', {}).get('server_revision') or 'UNSTAMPED_DURING_ROLLOUT' for r in retests)),
               'final_retest_revision_counts': dict(Counter(r.get('observed_revision_before_request') for r in retests if r['phase']=='retest-final')),
               'limitations': ['Automated flags are review aids, not a semantic pass/fail score.',
                               'The initial 500-question batch spans multiple deployments. It is not 500 tests of the final revision.',
                               'A status revision observed before a request may differ from the serving instance during a rolling deployment; response.server_revision is authoritative when present.',
                               'Snapshot checks can become stale if store source data changes; requested Oct 7–13 sales checks use a fixed supported-date reference.',
                               'Missing history, company references, price-test coverage or unit conversions must remain unavailable rather than being fabricated.']}
    (root/'automated-review.json').write_text(json.dumps({'summary': summary, 'records': rows}, indent=2))
    (root/'audit-summary.txt').write_text('FISHFINDER SEAFOOD AI EVALUATION\n\n'+json.dumps(summary, indent=2)+'\n\nConfirmed issues and repairs: review-findings.json\nFull prompts and answers: baseline.jsonl\nFinal-revision targeted checks: retest-final.jsonl\nRelease history: release-log.json\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    print(json.dumps(review(args.directory), indent=2))
