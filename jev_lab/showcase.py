"""Showcase operations: a live burst, a free-form playground and a side-by-side compare.

These exist to make Jev itself visible: how fast it answers, what it costs, and how its
typed answers sit next to a generative baseline. The safety posture is unchanged from the
single-case path. Live work needs the server-side key, the enable flag and explicit
consent; nothing retries; nothing falls back to replay; every failure is retained with
its cost marked unknown.
"""

from __future__ import annotations

import json
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import adapters, comparator, engine, llm_arm, provider

MAX_STATE_CHARS = 6000
MAX_QUESTIONS = 8
MAX_OPTIONS = 12
MAX_LEVELS = 10
MAX_INSTRUCTION_CHARS = 1500
MAX_DESCRIPTION_CHARS = 200
MAX_HTTP_BODY = 16384
QUESTION_ID = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
MAX_WORKERS = 6


def _sum_known_ints(values: list) -> int | None:
    """Sum non-negative ints. Any missing or invalid count makes the total unknown, not zero."""
    if not values:
        return None
    known = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None
        known.append(value)
    return sum(known)


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
    prepaid = None
    if mode == "live":
        if not provider.live_enabled():
            raise PermissionError(
                "Live mode disabled. Set TYPESAFE_API_KEY and JEV_ALLOW_LIVE=1 in the server terminal."
            )
        if consent is not True:
            raise PermissionError(
                "Explicit consent is required to send these synthetic cases to TypeSafe."
            )
        prepaid = provider.BUDGET.hold(len(cases))
    elif mode != "replay":
        raise ValueError("Mode must be replay or live")

    def one(case: dict) -> dict:
        try:
            receipt = engine.run(case["id"], mode, threshold, consent, prepaid=prepaid)
            return {"case_id": case["id"], "ok": True, "receipt": receipt}
        except engine.LiveValidationError as exc:
            p = exc.provenance
            return {
                "case_id": case["id"],
                "ok": False,
                "error": str(exc),
                "provider_response": exc.response,
                "model": exc.response.get("model"),
                "latency_ms": p.get("latency_ms"),
                "usage": p.get("usage"),
                "estimated_cost_usd": p.get("estimated_cost_usd"),
                "cost_unknown": p.get("estimated_cost_usd") is None,
            }
        except (ValueError, PermissionError, RuntimeError) as exc:
            return {"case_id": case["id"], "ok": False, "error": str(exc), "cost_unknown": True}

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(cases))) as pool:
        results = list(pool.map(one, cases))
    wall_ms = round((time.perf_counter() - started) * 1000, 2)

    successes = [r["receipt"] for r in results if r["ok"]]
    # A live answer that failed validation still happened: it has latency, usage and a bill.
    answered_failures = [r for r in results if not r["ok"] and "provider_response" in r]
    provenances = [r["provenance"] for r in successes] + answered_failures
    latencies = [p["latency_ms"] for p in provenances if p.get("latency_ms") is not None]
    usages = [p["usage"] for p in provenances if isinstance(p.get("usage"), dict)]
    known_costs = [
        p["estimated_cost_usd"] for p in provenances if p.get("estimated_cost_usd") is not None
    ]
    kind = "live_typesafe" if mode == "live" else "synthetic_replay"
    summary = {
        "requested": len(cases),
        "succeeded": len(successes),
        "failed": len(results) - len(successes),
        "model_calls": sum(r["provenance"]["model_calls"] for r in successes)
        + len(answered_failures),
        "models": sorted(
            {r["response"]["model"] for r in successes}
            | {r["model"] for r in answered_failures if r.get("model")}
        )
        if mode == "live"
        else [],
        "latency_ms": {
            "min": min(latencies) if latencies else None,
            "p50": _percentile(latencies, 0.5),
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
            "mean": round(statistics.fmean(latencies), 2) if latencies else None,
        },
        "input_tokens": _sum_known_ints([u.get("input_tokens") for u in usages])
        if usages
        else None,
        "output_tokens": _sum_known_ints([u.get("output_tokens") for u in usages])
        if usages
        else None,
        "estimated_cost_usd": sum(known_costs)
        if known_costs and len(known_costs) == len(results)
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


def publish_burst(result: dict, store) -> dict:
    """Persist receipts and return the public row shape the live-lab table renders."""
    for row in result["results"]:
        if not row["ok"]:
            continue
        stored = store(row.pop("receipt"))
        decision = stored["decision"]
        provenance = stored["provenance"]
        row.update(
            {
                "receipt_id": stored["receipt_id"],
                "route": decision["route"],
                "owner": decision["owner"],
                "owner_probability": decision["owner_probability"],
                "critical_probability": decision["critical_probability"],
                "model": stored["response"]["model"],
                "latency_ms": provenance["latency_ms"],
                "usage": provenance["usage"],
                "estimated_cost_usd": provenance["estimated_cost_usd"],
            }
        )
    return result


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
    request = {
        "model": engine.request_for(engine.cases()[0])["model"],
        "state": state,
        "questions": clean,
    }
    envelope = json.dumps(
        {"state": state, "questions": clean, "consent": True}, allow_nan=False
    ).encode()
    if len(envelope) > MAX_HTTP_BODY:
        raise ValueError(
            f"Playground request is {len(envelope)} bytes; the lab HTTP ceiling is {MAX_HTTP_BODY}. "
            "Shorten the state or the criteria. Nothing was sent."
        )
    payload = json.dumps(request, allow_nan=False).encode()
    if len(payload) > provider.MAX_INPUT_BYTES:
        raise ValueError(
            f"Playground request is {len(payload)} bytes; the provider ceiling is "
            f"{provider.MAX_INPUT_BYTES}. Shorten the state or the criteria. Nothing was sent."
        )
    return request


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


def prepare_arms(arm_names: list[str], n_cases: int, consent: bool = False) -> list:
    """Build arms once. Reserve live slots only after every live arm can proceed."""
    if not isinstance(arm_names, list) or not arm_names:
        raise ValueError("Choose at least one comparison arm")
    if isinstance(n_cases, bool) or not isinstance(n_cases, int) or n_cases < 1:
        raise ValueError("Compare needs at least one case")
    unknown = [name for name in arm_names if name not in adapters.ARM_NAMES]
    if unknown:
        raise ValueError(
            f"Unknown provider arm {unknown[0]!r}. Registered arms: {sorted(adapters.ARM_NAMES)}"
        )
    if any(name in adapters.LIVE_ARMS for name in arm_names) and consent is not True:
        raise PermissionError("Explicit consent is required before any live arm is called.")
    native_on = "native" in arm_names and provider.live_enabled()
    claude_on = "claude" in arm_names and llm_arm.live_enabled()
    if claude_on and not llm_arm.sdk_available():
        raise PermissionError(
            "The Claude comparison arm needs the optional SDK: run `uv sync --extra compare`. "
            "Nothing was sent."
        )
    shortfalls = []
    if native_on and provider.BUDGET.remaining() < n_cases:
        shortfalls.append(("Jev", provider.BUDGET.remaining()))
    if claude_on and llm_arm.BUDGET.remaining() < n_cases:
        shortfalls.append(("Claude", llm_arm.BUDGET.remaining()))
    if shortfalls:
        label, left = shortfalls[0]
        raise RuntimeError(
            f"Compare needs {n_cases} {label} attempt slots but {left} remain. Nothing was sent."
        )
    prepaid = {}
    if native_on:
        prepaid["native"] = provider.BUDGET.hold(n_cases)
    if claude_on:
        prepaid["claude"] = llm_arm.BUDGET.hold(n_cases)
    return [adapters.build(name, prepaid=prepaid.get(name)) for name in arm_names]


def compare(arm_names: list[str], case_ids: list[str], consent: bool = False) -> dict:
    """Per-arm comparison over the same cases, plus the evaluator's expected owner per case."""
    case_ids = case_ids or [c["id"] for c in engine.cases()]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Repeated case IDs must not inflate the sample")
    for case_id in case_ids:
        engine.case_by_id(case_id)
    arms = prepare_arms(arm_names, len(case_ids), consent)
    report = comparator.compare(case_ids, arms)
    labels = engine.load("labels")
    report["expected_owner"] = {
        case_id: labels[case_id]["expected_owner"] for case_id in report["cases"]
    }
    report["planted_error"] = {
        case_id: bool(labels[case_id].get("planted_error")) for case_id in report["cases"]
    }
    if any(report["planted_error"].values()):
        report["warnings"] = list(report.get("warnings") or []) + [
            (
                "S04 is a planted teaching error: the authored owner is confidently wrong. "
                "It is labelled here so it is not counted as a measured model failure."
            )
        ]
    if "rules" in arm_names:
        report["warnings"] = list(report.get("warnings") or []) + [
            (
                "The keyword-rules arm is hand-fit to these twelve authored cases. It shows what a "
                "delay-word rule does; its agreement count is not a baseline accuracy."
            )
        ]
    report["created_at"] = datetime.now(timezone.utc).isoformat()
    return report
