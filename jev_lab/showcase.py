"""Showcase operations: a live burst, a free-form playground and a side-by-side compare.

These exist to make Jev itself visible: how fast it answers, what it costs, and how its
typed answers sit next to a generative baseline. The safety posture is unchanged from the
single-case path. Live work needs the server-side key, the enable flag and explicit
consent; nothing retries; nothing falls back to replay; every failure is retained with
its cost marked unknown.
"""

from __future__ import annotations

import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import adapters, comparator, engine, provider

MAX_STATE_CHARS = 6000
MAX_QUESTIONS = 8
MAX_OPTIONS = 12
MAX_LEVELS = 10
MAX_INSTRUCTION_CHARS = 1500
MAX_DESCRIPTION_CHARS = 200
QUESTION_ID = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
MAX_WORKERS = 6


def _percentile(values: list[float], fraction: float):
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def burst(
    case_ids: list[str], mode: str = "replay", consent: bool = False, threshold: float = 0.85
) -> dict:
    """Run several cases at once and summarise latency, tokens and cost per run.

    Live calls run concurrently, so wall time is shorter than the sum of latencies. Each
    case is one attempt against the process cap; the cap is checked before any call so a
    burst never sends a partial batch it cannot finish.
    """
    if not case_ids:
        raise ValueError("At least one case id is required")
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Repeated case IDs must not inflate the sample")
    cases = [engine.case_by_id(case_id) for case_id in case_ids]
    engine.number(threshold)
    if mode == "live":
        if consent is not True:
            raise PermissionError(
                "Explicit consent is required to send these synthetic cases to TypeSafe."
            )
        if not provider.live_enabled():
            raise PermissionError(
                "Live mode disabled. Set TYPESAFE_API_KEY and JEV_ALLOW_LIVE=1 in the server terminal."
            )
        remaining = provider.BUDGET.limit - provider.BUDGET.used
        if remaining < len(cases):
            raise RuntimeError(
                f"Burst needs {len(cases)} attempt slots but {remaining} remain in this process. "
                "Nothing was sent. Restart with JEV_MAX_LIVE_CALLS set deliberately, at most 100."
            )
    elif mode != "replay":
        raise ValueError("Mode must be replay or live")

    def one(case: dict) -> dict:
        try:
            receipt = engine.run(case["id"], mode, threshold, consent)
            return {"case_id": case["id"], "ok": True, "receipt": receipt}
        except (ValueError, PermissionError, RuntimeError) as exc:
            return {"case_id": case["id"], "ok": False, "error": str(exc), "cost_unknown": True}

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(cases))) as pool:
        results = list(pool.map(one, cases))
    wall_ms = round((time.perf_counter() - started) * 1000, 2)

    successes = [r["receipt"] for r in results if r["ok"]]
    latencies = [
        r["provenance"]["latency_ms"]
        for r in successes
        if r["provenance"]["latency_ms"] is not None
    ]
    usages = [
        r["provenance"]["usage"]
        for r in successes
        if isinstance(r["provenance"].get("usage"), dict)
    ]
    costs = [r["provenance"]["estimated_cost_usd"] for r in successes]
    known_costs = [c for c in costs if c is not None]
    kind = "live_typesafe" if mode == "live" else "synthetic_replay"
    summary = {
        "requested": len(cases),
        "succeeded": len(successes),
        "failed": len(results) - len(successes),
        "model_calls": sum(r["provenance"]["model_calls"] for r in successes),
        "models": sorted({r["response"]["model"] for r in successes}) if mode == "live" else [],
        "latency_ms": {
            "min": min(latencies) if latencies else None,
            "p50": _percentile(latencies, 0.5),
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
            "mean": round(statistics.fmean(latencies), 2) if latencies else None,
        },
        "input_tokens": sum(u.get("input_tokens") or 0 for u in usages) if usages else None,
        "output_tokens": sum(u.get("output_tokens") or 0 for u in usages) if usages else None,
        "estimated_cost_usd": sum(known_costs)
        if known_costs and len(known_costs) == len(successes)
        else None,
        "cost_unknown_cases": len(results) - len(known_costs),
    }
    return {
        "mode": mode,
        "kind": kind,
        "wall_ms": wall_ms,
        "concurrency": min(MAX_WORKERS, len(cases)),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "summary": summary,
        "warning": (
            "Client-observed latency includes network time and concurrent scheduling. Cost is an "
            "estimate from reported usage and a dated public price, not an invoice. Failed requests "
            "may still have been billed. Twelve synthetic cases are a smoke test, not a benchmark."
            if mode == "live"
            else "Synthetic replay: authored teaching fixtures, no model call, no latency and no cost."
        ),
    }


def _string(value, limit: int, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{what} must be a non-empty string")
    if len(value) > limit:
        raise ValueError(f"{what} exceeds {limit} characters")
    return value


def playground_request(state, questions) -> dict:
    """Validate a user-authored request before it can reach a provider."""
    if not isinstance(state, str):
        raise ValueError("Playground state must be a text string")
    _string(state, MAX_STATE_CHARS, "State")
    if not isinstance(questions, dict) or not questions:
        raise ValueError("Provide at least one question")
    if len(questions) > MAX_QUESTIONS:
        raise ValueError(f"At most {MAX_QUESTIONS} questions per request")
    clean = {}
    for qid, question in questions.items():
        if not isinstance(qid, str) or not QUESTION_ID.match(qid):
            raise ValueError("Question ids must be short snake_case identifiers")
        if not isinstance(question, dict) or set(question) - {"type", "instructions", "criteria"}:
            raise ValueError(f"Question {qid} may only contain type, instructions and criteria")
        qtype = question.get("type")
        instructions = _string(
            question.get("instructions"), MAX_INSTRUCTION_CHARS, f"Instructions for {qid}"
        )
        entry = {"type": qtype, "instructions": instructions}
        criteria = question.get("criteria")
        if qtype == "choice":
            if not isinstance(criteria, dict) or not 2 <= len(criteria) <= MAX_OPTIONS:
                raise ValueError(f"Choice {qid} needs 2 to {MAX_OPTIONS} options")
            entry["criteria"] = {
                _string(k, 64, f"Option key in {qid}"): _string(
                    v, MAX_DESCRIPTION_CHARS, f"Option text in {qid}"
                )
                for k, v in criteria.items()
            }
        elif qtype == "score":
            if not isinstance(criteria, list) or not 2 <= len(criteria) <= MAX_LEVELS:
                raise ValueError(f"Score {qid} needs 2 to {MAX_LEVELS} ordered levels")
            entry["criteria"] = [
                _string(v, MAX_DESCRIPTION_CHARS, f"Level text in {qid}") for v in criteria
            ]
        elif qtype == "noul":
            if criteria is not None:
                if not isinstance(criteria, dict) or set(criteria) != {"true", "false"}:
                    raise ValueError(f"Noul {qid} criteria must describe exactly true and false")
                entry["criteria"] = {
                    k: _string(v, MAX_DESCRIPTION_CHARS, f"Criteria text in {qid}")
                    for k, v in criteria.items()
                }
        else:
            raise ValueError(f"Question {qid} type must be choice, score or noul")
        clean[qid] = entry
    return {
        "model": engine.request_for(engine.cases()[0])["model"],
        "state": state,
        "questions": clean,
    }


def playground(state, questions, consent: bool = False) -> dict:
    """One live call with user-authored synthetic text. No policy, no stored receipt."""
    request = playground_request(state, questions)
    if not provider.live_enabled():
        raise PermissionError(
            "The playground needs a live connection: set TYPESAFE_API_KEY and JEV_ALLOW_LIVE=1 in "
            "the server terminal. There is no replay for text you wrote yourself."
        )
    if consent is not True:
        raise PermissionError("Explicit consent is required to send your text to TypeSafe.")
    response, provenance = provider.live(request)
    engine.validate(request, response, live=True)
    return {
        "request": request,
        "response": response,
        "provenance": provenance,
        "request_hash": engine.digest(request),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "warning": "Playground result. No policy is applied and no receipt is stored. Send only "
        "synthetic or public text; this is not an approved channel for work data.",
    }


def compare(arm_names: list[str], case_ids: list[str], consent: bool = False) -> dict:
    """Per-arm comparison over the same cases, plus the evaluator's expected owner per case."""
    if not isinstance(arm_names, list) or not arm_names:
        raise ValueError("Choose at least one comparison arm")
    arms = [adapters.build(name) for name in arm_names]
    if any(arm.live for arm in arms) and consent is not True:
        raise PermissionError("Explicit consent is required before any live arm is called.")
    case_ids = case_ids or [c["id"] for c in engine.cases()]
    report = comparator.compare(case_ids, arms)
    labels = engine.load("labels")
    report["expected_owner"] = {
        case_id: labels[case_id]["expected_owner"] for case_id in report["cases"]
    }
    report["created_at"] = datetime.now(timezone.utc).isoformat()
    return report
