"""Transparent owner-classification metrics, not product-performance assertions."""
import math

from .engine import distribution


def wilson(correct: int, n: int):
    if not n:
        return None
    z = 1.959963984540054
    p = correct/n
    den = 1 + z*z/n
    centre = (p + z*z/(2*n))/den
    radius = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [max(0, centre-radius), min(1, centre+radius)]


def classification(rows: list[tuple[dict, str]]) -> dict:
    for probs, gold in rows:
        distribution(probs, set(probs))
        if gold not in probs:
            raise ValueError('Gold label absent from option set')
    n = len(rows)
    obs = [(max(p.values()), max(p, key=p.get) == g) for p, g in rows]
    correct = sum(ok for _, ok in obs)
    ece = 0.
    bins = []
    for i in range(10):
        group = [(p, ok) for p, ok in obs if min(int(p*10), 9) == i]
        count = len(group)
        accuracy = sum(ok for _, ok in group)/count if count else None
        confidence = sum(p for p, _ in group)/count if count else None
        if count:
            ece += count/max(n, 1)*abs(accuracy-confidence)
        bins.append({'lower': i/10, 'upper': (i+1)/10, 'n': count, 'accuracy': accuracy, 'mean_top_probability': confidence})
    curve = []
    for t in [0, .5, .7, .8, .85, .9, .95, .99, 1.]:
        accepted = [ok for p, ok in obs if p >= t]
        curve.append({'threshold': t, 'accepted': len(accepted), 'coverage': len(accepted)/n if n else None,
                      'error_rate': 1-sum(accepted)/len(accepted) if accepted else None})
    return {'n': n, 'accuracy': correct/n if n else None, 'accuracy_wilson_95': wilson(correct, n),
            'brier': sum(sum((v-(k == g))**2 for k, v in p.items()) for p, g in rows)/n if n else None,
            'log_loss': -sum(math.log(max(p[g], 1e-15)) for p, g in rows)/n if n else None,
            'ece_10': ece if n else None, 'calibration_bins': bins, 'risk_coverage': curve,
            'definition': 'Owner classification only. Unhalved multiclass Brier; ECE uses top-class probability, not vendor confidence. Risk-coverage excludes policy gates.'}


def evaluate(receipts: list[dict], labels: dict) -> dict:
    ids = [r['case_id'] for r in receipts]
    if len(set(ids)) != len(ids):
        raise ValueError('Repeated case IDs must not inflate the sample')
    kinds = {r['provenance']['kind'] for r in receipts}
    if len(kinds) > 1:
        raise ValueError('Never mix synthetic and live outputs in one evaluation')
    groups = {}
    for r in receipts:
        if r['case_id'] not in labels:
            raise ValueError('Missing gold label')
        groups.setdefault(r['pack'], []).append((r['response']['answers']['owner']['probabilities'], labels[r['case_id']]['expected_owner']))
    return {'provenance': next(iter(kinds), 'empty'),
            'warning': 'Authored examples are not a representative benchmark. Replay measures no Jev capability. Live results on twelve teaching cases are still only a smoke test.',
            'by_pack': {k: classification(v) for k, v in groups.items()},
            'overall': classification([x for group in groups.values() for x in group]),
            'notes': {i: labels[i]['teaching_note'] for i in ids}}
