"""Request-shape experiment; not a Jev-versus-reasoner benchmark."""
from __future__ import annotations
import copy
import random
import time
from concurrent.futures import ThreadPoolExecutor
from . import engine, provider


def compare_shapes(request: dict, call=provider.live, seed: int = 0) -> list[dict]:
    single = [dict(copy.deepcopy(request), questions={key: copy.deepcopy(q)}) for key, q in request['questions'].items()]
    shapes = ['one_batch', 'serial_questions', 'parallel_requests']
    random.Random(seed).shuffle(shapes)

    def measured(payload):
        try:
            response, provenance = call(payload)
            engine.validate(payload, response)
            return {'ok': True, 'response': response, 'provenance': provenance}
        except (RuntimeError, PermissionError, ValueError) as exc:
            return {'ok': False, 'error': str(exc), 'cost_unknown': True}

    results = []
    for shape in shapes:
        payloads = [copy.deepcopy(request)] if shape == 'one_batch' else copy.deepcopy(single)
        started = time.perf_counter()
        if shape == 'parallel_requests':
            with ThreadPoolExecutor(max_workers=min(6, len(payloads))) as pool:
                observations = list(pool.map(measured, payloads))
        else:
            observations = [measured(p) for p in payloads]
        good = [o for o in observations if o['ok']]
        failed = len(observations) - len(good)
        results.append({'shape': shape, 'requests': len(payloads), 'succeeded': len(good), 'failed': failed,
            'all_successful': failed == 0, 'client_wall_ms': (time.perf_counter() - started) * 1000,
            'reported_success_input_tokens': sum(o['provenance']['usage']['input_tokens'] for o in good),
            'estimated_success_cost_usd': sum(o['provenance']['estimated_cost_usd'] or 0 for o in good),
            'failed_request_cost_unknown': failed > 0, 'observations': observations})
    return results


def benchmark(case_id: str = 'S02', repeats: int = 1) -> dict:
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 5:
        raise ValueError('Use 1 to 5 repetitions')
    if not provider.live_enabled():
        raise PermissionError('Configure the live provider before benchmarking')
    request = engine.request_for(engine.case_by_id(case_id))
    needed = repeats * (1 + 2 * len(request['questions']))
    if provider.BUDGET.limit - provider.BUDGET.used < needed:
        raise RuntimeError(f'Experiment requires {needed} attempt slots. Set JEV_MAX_LIVE_CALLS deliberately, at most 100.')
    results = []
    for repetition in range(repeats):
        shapes = compare_shapes(request, seed=repetition)
        results.append({'repetition': repetition + 1, 'shapes': shapes})
        if any(not x['all_successful'] for x in shapes):
            break
    return {'experiment': 'same-state request-shape comparison', 'kind': 'live_typesafe',
        'case_id': case_id, 'request_hash': engine.digest(request), 'planned_api_attempts': needed,
        'requested_repetitions': repeats, 'completed_repetitions': len(results), 'results': results,
        'warning': 'Within-Jev only: one batch versus six serial or concurrent requests. Client wall time includes network overhead. One repetition is a smoke test. Failed requests may still be billed. Synthetic input does not establish enterprise performance.'}
