"""Pure request, contract and routing logic. No provider credentials or gold labels."""
from __future__ import annotations
import copy
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
POLICY_VERSION = 'route-v1.0'
QUESTION_VERSION = 'enterprise-atoms-v1.0'

def load(name: str) -> Any:
    return json.loads((ROOT / 'data' / f'{name}.json').read_text())

def cases() -> list[dict]:
    return load('cases')

def case_by_id(case_id: str) -> dict:
    for case in cases():
        if case['id'] == case_id:
            return case
    raise ValueError('Unknown case ID')

def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def request_for(case: dict) -> dict:
    return {'model': os.getenv('JEV_MODEL', 'jev-1.13.0'),
            'state': copy.deepcopy(case['state']),
            'questions': load('packs')[case['pack']]['questions']}

def number(value: Any, low: float = 0, high: float = 1) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'Expected a finite number in [{low}, {high}]')
    return value

def distribution(value: Any, keys: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError('Probability option set does not match the question')
    for p in value.values():
        number(p)
    if abs(sum(value.values()) - 1) > 0.002:
        raise ValueError('Probabilities must sum to one')
    return value

def validate(request: dict, response: dict) -> dict:
    """Fail closed on schema drift; never fabricate missing probability fields."""
    if not isinstance(response, dict) or not isinstance(response.get('model'), str) or not response['model']:
        raise ValueError('Missing returned model identity')
    answers = response.get('answers')
    if not isinstance(answers, dict) or set(answers) != set(request['questions']):
        raise ValueError('Response question IDs do not match the request')
    usage = response.get('usage')
    if not isinstance(usage, dict):
        raise ValueError('Missing usage object')
    for key in ('input_tokens', 'output_tokens'):
        v = usage.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise ValueError('Invalid usage token count')
    for qid, q in request['questions'].items():
        a = answers[qid]
        if not isinstance(a, dict) or a.get('type') != q['type']:
            raise ValueError(f'Answer type mismatch: {qid}')
        if q['type'] == 'noul':
            number(a.get('noul'))
        elif q['type'] == 'choice':
            p = distribution(a.get('probabilities'), set(q['criteria']))
            chosen = a.get('choice')
            if chosen not in p or p[chosen] < max(p.values()) - .002:
                raise ValueError(f'Choice is not a highest-probability option: {qid}')
            number(a.get('confidence'))
        elif q['type'] == 'score':
            keys = {str(i) for i in range(len(q['criteria']))}
            p = distribution(a.get('probabilities'), keys)
            score = number(a.get('score'), 0, len(keys)-1)
            if abs(score - sum(int(k)*v for k,v in p.items())) > .02:
                raise ValueError('Score does not match its probability-weighted level index')
            if a.get('legend') != {str(i): level for i,level in enumerate(q['criteria'])}:
                raise ValueError('Score legend changed')
            number(a.get('confidence'))
        else:
            raise ValueError('Unsupported primitive')
    return response

def decide(case: dict, response: dict, threshold: float = .85, variant: str = 'original') -> dict:
    number(threshold)
    if variant not in ('original', 'stale', 'unverified'):
        raise ValueError('Unknown policy-only variant')
    a = response['answers']
    owner = a['owner']['choice']
    p = a['owner']['probabilities'][owner]
    critical = a['severity']['probabilities']['3']
    facts = copy.deepcopy(case['facts'])
    if variant == 'stale': facts['source_fresh'] = False
    if variant == 'unverified': facts['source_verified'] = False
    trace = []
    def check(rule: str, matched: bool, route: str, text: str) -> str | None:
        trace.append({'rule': rule, 'matched': bool(matched), 'explanation': text})
        return route if matched else None
    route = check('source_trust', not facts['source_verified'], 'VERIFY_SOURCE', 'Unverified evidence must be checked before routing.')
    if not route: route = check('source_freshness', not facts['source_fresh'], 'REFRESH_EVIDENCE', 'Expired evidence needs a refresh; model confidence cannot make it current.')
    if not route: route = check('mandatory_review', facts['mandatory_review'], 'HUMAN_REVIEW', 'The case contains an explicit human-review requirement.')
    if not route: route = check('critical_tail', critical >= .30, 'HUMAN_REVIEW', 'At least 0.30 probability on the critical level triggers human review. This is a teaching threshold, not a validated risk bound.')
    if not route: route = check('conflicting_evidence', a['contradiction']['noul'] >= .5, 'REQUEST_EVIDENCE', 'Material disagreement triggers an evidence-repair request.')
    if not route: route = check('insufficient_evidence', a['sufficient']['noul'] < .75, 'REQUEST_EVIDENCE', 'The evidence-sufficiency signal falls below the illustrative 0.75 threshold.')
    if not route: route = check('owner_uncertain', owner == 'other' or p < threshold, 'HUMAN_REVIEW', f'Top owner probability must reach {threshold:.2f} and identify a listed team.')
    if not route:
        route = 'ROUTE_TO_TEAM'
        trace.append({'rule':'recommend_team','matched':True,'explanation':'All prior checks passed. Recommend a team; do not execute an external action.'})
    evidence = a['next_evidence']['choice']
    if route == 'REQUEST_EVIDENCE' and evidence == 'none':
        trace.append({'rule':'inconsistent_heads','matched':True,'explanation':'Evidence is needed but the next-evidence head says none. A person must reconcile this inconsistency.'})
        route = 'HUMAN_REVIEW'
    return {'route':route,'owner':owner,'owner_probability':p,'critical_probability':critical,
            'next_evidence':evidence,'threshold':threshold,'variant':variant,'trace':trace,
            'policy_version':POLICY_VERSION,'policy_facts':facts,'external_actions':0}

def run(case_id: str, mode: str = 'replay', threshold: float = .85, consent: bool = False) -> dict:
    from . import provider
    case = case_by_id(case_id)
    number(threshold)
    request = request_for(case)
    if mode == 'replay':
        response = provider.replay(case_id)
        provenance = {'kind':'synthetic_replay','model_calls':0,'latency_ms':None,'usage':None,'estimated_cost_usd':None,
                      'warning':'Authored teaching probabilities. Not measured Jev outputs or benchmark evidence.'}
    elif mode == 'live':
        if consent is not True: raise PermissionError('Explicit consent is required to send this synthetic case to TypeSafe.')
        response, provenance = provider.live(request)
    else:
        raise ValueError('Mode must be replay or live')
    validate(request, response)
    receipt = {'schema_version':'1.0','created_at':datetime.now(timezone.utc).isoformat(),'case_id':case_id,'pack':case['pack'],
               'request':request,'response':response,'provenance':provenance,'question_version':QUESTION_VERSION,
               'request_hash':digest(request),'question_hash':digest(request['questions']),
               'policy_source_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'decision':decide(case,response,threshold),'additional_model_calls':provenance['model_calls']}
    receipt['receipt_hash'] = digest(receipt)
    return receipt

def reconsider(receipt: dict, threshold: float, variant: str = 'original') -> dict:
    result = copy.deepcopy(receipt)
    result.pop('receipt_hash',None)
    result['parent_receipt_hash'] = receipt['receipt_hash']
    result['decision'] = decide(case_by_id(receipt['case_id']),receipt['response'],threshold,variant)
    result['additional_model_calls'] = 0
    result['policy_evaluated_at'] = datetime.now(timezone.utc).isoformat()
    result['receipt_hash'] = digest(result)
    return result
