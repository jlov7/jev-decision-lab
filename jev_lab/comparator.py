"""Per-arm comparison. Arms are never pooled and no arm is ranked.

Three constraints from the source documents shape this module:

  * ``docs/EVALUATION.md:25`` - keep the two tracks apart. An arm that returns only a
    category is still comparable on the minimal decision track, but it is not comparable
    on distributions, and a verbal provider confidence is not a class probability.
  * ``metrics.py:52`` - ``metrics.evaluate`` refuses to mix provenances in one call
    (``Never mix synthetic and live outputs in one evaluation``). Every arm is therefore
    evaluated on its own receipts, and arms meet only at this reporting layer.
  * ``BUILD_PACKET.md:190`` - the bar is an authentic response with recorded provenance
    or a safely retained failure. Nothing here fabricates a result, retries, or falls
    back to replay output.

This module computes no verdict, ranks no arm, and asserts no accuracy. It reports what
each arm returned, what it cost, and what it could not answer. Whether a live arm's
answers came from authenticated calls is stated per report, never assumed.

Consent and transport gating are owned upstream, not here. ``provider.live`` refuses
before sending unless ``TYPESAFE_API_KEY`` and ``JEV_ALLOW_LIVE=1`` are set in the
terminal, and ``engine.run`` owns the explicit-consent check for the single-case path. The
comparator adds no gate of its own: a second refusal would mask the provider's specific
error, and retaining that error verbatim is the whole point of this layer.
"""

from __future__ import annotations

from . import engine, metrics
from .adapters import TRACKS, ProviderArm

SCHEMA_VERSION = "comparator-v1.0"

# metrics.py reads ``answers['owner']['probabilities']``, so the distribution metric is
# scoped to that question by construction rather than by choice made here.
METRIC_QUESTION = "owner"

WARNINGS = (
    (
        "Arms are reported side by side and are never pooled into one evaluation. This report "
        "does not rank arms and does not claim accuracy."
    ),
    "A distribution a provider did not return is reported as unavailable, never as zero.",
    (
        "Synthetic replay probabilities are authored teaching fixtures. They measure no model "
        "capability and are not a benchmark."
    ),
)


NO_LIVE_WARNING = (
    "Live arms were not verified against a live provider route in this run: no authenticated "
    "call was made, so nothing here is evidence of live Jev behaviour."
)


def _live_warning(reports: list[dict], n_cases: int) -> str:
    verified = [r for r in reports if r["live_verified"] and r["succeeded"]]
    if not verified:
        return NO_LIVE_WARNING
    names = ", ".join(r["name"] for r in verified)
    return (
        f"Live arm answers in this run ({names}) came from authenticated calls on the account "
        f"owner's key. {n_cases} case(s) is a smoke test, not a benchmark, and one run does not "
        "establish calibration."
    )


def compare(case_ids: list[str], arms: list[ProviderArm]) -> dict:
    """Call every arm over the same cases and report each arm separately.

    A failure in one arm never stops another, and every failure is retained verbatim
    rather than retried or replaced. Gating is the provider's job, not this layer's.
    """
    cases = _resolved_cases(case_ids, arms)
    reports = [_arm_report(arm, cases) for arm in arms]
    warnings = list(WARNINGS)
    warnings.insert(1, _live_warning(reports, len(cases)))
    return {
        "schema_version": SCHEMA_VERSION,
        "ranked": False,
        "cases": [case["id"] for case in cases],
        "warnings": warnings,
        "arms": reports,
    }


def _resolved_cases(case_ids: list[str], arms: list[ProviderArm]) -> list[dict]:
    """Resolve every case before any call, so an unknown id sends nothing."""
    if not case_ids:
        raise ValueError("At least one case id is required")
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Repeated case IDs must not inflate the sample")
    if not arms:
        raise ValueError("At least one provider arm is required")
    return [engine.case_by_id(case_id) for case_id in case_ids]


def _attempt(arm: ProviderArm, case: dict):
    """Return ``(result, failure)``. Exactly one of the two is ever set.

    No gate is applied here: ``provider.live`` refuses before sending unless the live
    environment is set in the terminal, and retaining that refusal verbatim is the point.
    A failed call still may have consumed a token server-side, so its cost is unknown.
    """
    try:
        return arm.call(engine.request_for(case), case["id"]), None
    except Exception as exc:  # noqa: BLE001 - every failure must be retained, not swallowed
        return None, {
            "case_id": case["id"],
            "error": str(exc),
            "cost_unknown": True,
        }


def _arm_report(arm: ProviderArm, cases: list[dict]) -> dict:
    successes, failures = [], []
    for case in cases:
        result, failure = _attempt(arm, case)
        (failures if failure else successes).append(failure or (case, result))
    return {
        "name": arm.name,
        "kind": arm.kind,
        "live": bool(getattr(arm, "live", False)),
        "pinned_version": arm.pinned_version,
        "live_verified": _live_verified(arm, successes),
        "attempts": len(cases),
        "succeeded": len(successes),
        "failed": len(failures),
        "failures": failures,
        "cases": [_case_row(case, result) for case, result in successes],
        "tracks": _tracks(successes),
    }


def _case_row(case: dict, result: dict) -> dict:
    """What this arm answered for one case, with its own latency and cost. No verdict."""
    provenance = result["provenance"]
    return {
        "case_id": case["id"],
        "pack": case["pack"],
        "model": provenance.get("model") or result["raw"].get("model"),
        "answers": {
            qid: record["answer"] for qid, record in result["normalized"]["records"].items()
        },
        "latency_ms": provenance.get("latency_ms"),
        "usage": provenance.get("usage"),
        "estimated_cost_usd": provenance.get("estimated_cost_usd"),
    }


def _live_verified(arm: ProviderArm, successes: list) -> bool:
    """True only if the arm and every successful call agree that a live response was seen."""
    if not successes or not getattr(arm, "live_verified", False):
        return False
    return all(result["provenance"].get("live_verified") is True for _, result in successes)


def _answered(result: dict) -> bool:
    records = result["normalized"]["records"]
    return bool(records) and all(r["answer"] is not None for r in records.values())


def _tracks(successes: list) -> dict:
    answered = sum(1 for _, result in successes if _answered(result))
    available, block, reason = _distribution_metrics(successes)
    tracks = {
        "minimal_decision": {"answered": answered},
        "comparable_distribution": {
            "available": available,
            "metrics": block,
            "metric_scope": [METRIC_QUESTION],
            "reason": reason,
            "pooled_with_other_arms": False,
        },
    }
    if tuple(tracks) != TRACKS:
        raise AssertionError("Comparator tracks drifted from the adapter contract")
    return tracks


def _distribution_metrics(successes: list):
    """Distribution metrics, or an explicit reason they are unavailable.

    A missing distribution is unavailable, not zero: the arm did not measure anything on
    this track, and reporting 0.0 would read as a measured failure. No distribution is
    ever synthesized to fill the gap (docs/ACCESS_AND_TROUBLESHOOTING.md). Planted teaching
    errors stay in the case rows and are dropped here so they are not scored as failures.
    """
    if not successes:
        return (
            False,
            None,
            (
                "No successful call, so this arm produced no distribution metrics. Reported as "
                "unavailable rather than as zero."
            ),
        )
    labels = engine.load("labels")
    measurable = [
        (case, result)
        for case, result in successes
        if not labels.get(case["id"], {}).get("planted_error")
    ]
    if not measurable:
        return (
            False,
            None,
            (
                "Every successful case is a planted teaching error, so distribution metrics are "
                "unavailable rather than scored as a measured model failure."
            ),
        )
    missing = []
    for case, result in measurable:
        record = result["normalized"]["records"].get(METRIC_QUESTION)
        if record is None or record["distribution"] is None:
            missing.append((case["id"], record["distribution_note"] if record else None))
    if missing:
        detail = "; ".join(
            f"{case_id}: {note or 'no distribution returned'}" for case_id, note in missing
        )
        return (
            False,
            None,
            (
                f"No distribution for question {METRIC_QUESTION!r} in {len(missing)} of "
                f"{len(measurable)} scorable case(s), so every metric on this track is "
                f"unavailable rather than zero. None was fabricated. {detail}"
            ),
        )
    receipts = [
        {
            "case_id": case["id"],
            "pack": case["pack"],
            "provenance": {"kind": result["provenance"]["kind"]},
            "response": result["raw"],
        }
        for case, result in measurable
    ]
    try:
        evaluated = metrics.evaluate(receipts, engine.load("labels"))
    except ValueError as exc:
        return (
            False,
            None,
            (
                f"Distribution metrics could not be computed for this arm: {exc}. Reported as "
                "unavailable rather than as zero."
            ),
        )
    block = dict(evaluated["overall"])
    block["by_pack"] = evaluated["by_pack"]
    block["metrics_warning"] = evaluated["warning"]
    return True, block, None
