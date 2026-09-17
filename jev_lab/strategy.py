"""Executable teaching boundaries, not enterprise authorization or procurement advice."""
from .engine import verify_receipt


def action_preview(receipt: dict, current: dict) -> dict:
    verify_receipt(receipt)
    if not isinstance(current, dict):
        raise ValueError('Current simulated metadata must be an object')
    keys = ['state_unchanged', 'source_fresh', 'approval_current', 'permission_granted']
    if set(current) - set(keys):
        raise ValueError('Unknown action-gate field')
    checks = []
    for key in keys:
        value = current.get(key)
        if value is not None and not isinstance(value, bool):
            raise ValueError('Action-gate fields must be boolean or unknown')
        checks.append({'check': key, 'passed': value is True, 'value': value})
    checks.append({'check': 'prior_recommendation', 'passed': receipt['decision']['route'] == 'ROUTE_TO_TEAM'})
    return {'result': 'SIMULATED_RECOMMENDATION' if all(c['passed'] for c in checks) else 'HOLD',
            'checks': checks, 'additional_model_calls': 0, 'external_actions': 0,
            'receipt_hash': receipt['receipt_hash'],
            'warning': 'Local simulation only. Checkbox values are not verified grants. Production needs authoritative state, authenticated approvals and a separately enforced effect boundary.'}


def garden(task: str, allow_cloud: bool, consequence_high: bool) -> dict:
    if not isinstance(allow_cloud, bool) or not isinstance(consequence_high, bool):
        raise ValueError('Garden constraints must be explicit booleans')
    roles = {
        'calculate': ('deterministic', 'Use code, SQL or a solver for exact calculations; a model may help interpret the request, never substitute for arithmetic checks.'),
        'classify': ('bounded_judgment', 'Compare rules, a local discriminative model, Jev and a cheap constrained-output LLM on the same held-out cases.'),
        'write': ('generation', 'Use a capable writing model with authorized evidence. Apply deterministic checks and selectively validated semantic review to the draft.'),
        'investigate': ('reasoning_and_tools', 'Use a reasoning model with bounded retrieval and tools. Verify source facts and outcome separately; more reasoning is not guaranteed correctness.'),
        'forecast': ('predictive_models', 'Compare statistical, tree-based and domain time-series models before assuming an LLM or judgment model predicts operational outcomes.'),
        'simulate': ('world_model_experiment', 'A world-model experiment is relevant only with a state/action task, a grounded simulator and a measurable transfer question.')}
    if task not in roles:
        raise ValueError('Unknown model-garden task')
    lane, explanation = roles[task]
    return {'task': task, 'lane': lane, 'explanation': explanation,
            'hosted_jev_eligible': allow_cloud and task == 'classify',
            'human_authority_required': consequence_high,
            'constraints': {'allow_cloud': allow_cloud, 'consequence_high': consequence_high},
            'checks': ['Data rights and location', 'Task-specific measured quality', 'Full cost including review', 'Version and rollback', 'Independent acceptance', 'Provider failure route'],
            'warning': 'Capability-role worksheet, not a benchmark ranking or approval. No model is contacted. Hosted eligibility is necessary, never sufficient, for procurement.'}
