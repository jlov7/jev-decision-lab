"""Typed judgment contracts and explicit policy. No permissions come from a model."""

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
POLICY_VERSION = "route-v2.1"
QUESTION_VERSION = "enterprise-atoms-v1.0"


def load(name: str) -> Any:
    if name not in {"cases", "packs", "replay", "labels", "signals"}:
        raise ValueError("Unknown dataset")
    return json.loads((ROOT / "data" / f"{name}.json").read_text())


def cases() -> list[dict]:
    return load("cases")


def case_by_id(case_id: str) -> dict:
    for case in cases():
        if case["id"] == case_id:
            return case
    raise ValueError("Unknown case ID")


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def request_for(case: dict) -> dict:
    return {
        "model": os.getenv("JEV_MODEL", "jev-1.13.0"),
        "state": copy.deepcopy(case["state"]),
        "questions": load("packs")[case["pack"]]["questions"],
    }


def number(value: Any, low: float = 0, high: float = 1) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError(f"Expected a finite number in [{low}, {high}]")
    return value


def distribution(value: Any, keys: set[str]) -> dict:
    if not isinstance(value, dict) or not keys or set(value) != keys:
        raise ValueError("Probability option set does not match the question")
    for p in value.values():
        number(p)
    if abs(sum(value.values()) - 1) > 0.002:
        raise ValueError("Probabilities must sum to one")
    return value


def validate(request: dict, response: dict, live: bool = False) -> dict:
    """Fail closed on schema drift. Never invent missing scores or probabilities."""
    if (
        not isinstance(response, dict)
        or not isinstance(response.get("model"), str)
        or not response["model"]
    ):
        raise ValueError("Missing returned model identity")
    if (
        live
        and request["model"] not in {"jev-latest", "jev-preview"}
        and response["model"] != request["model"]
    ):
        raise ValueError("Pinned model identity mismatch. Do not reuse calibrated thresholds.")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(request["questions"]):
        raise ValueError("Response question IDs do not match the request")
    usage = response.get("usage")
    if not isinstance(usage, dict):
        raise ValueError("Missing usage object")
    for key in ("input_tokens", "output_tokens"):
        v = usage.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise ValueError("Invalid usage token count")
    for qid, q in request["questions"].items():
        a = answers[qid]
        if not isinstance(a, dict) or a.get("type") != q["type"]:
            raise ValueError(f"Answer type mismatch: {qid}")
        if q["type"] == "noul":
            number(a.get("noul"))
        elif q["type"] == "choice":
            p = distribution(a.get("probabilities"), set(q["criteria"]))
            chosen = a.get("choice")
            if chosen not in p or p[chosen] < max(p.values()) - 0.002:
                raise ValueError(f"Choice is not a highest-probability option: {qid}")
            number(a.get("confidence"))
        elif q["type"] == "score":
            p = distribution(a.get("probabilities"), {str(i) for i in range(len(q["criteria"]))})
            score = number(a.get("score"), 0, len(q["criteria"]) - 1)
            if abs(score - sum(int(k) * v for k, v in p.items())) > 0.02:
                raise ValueError("Score does not match probability-weighted level index")
            if a.get("legend") != {str(i): level for i, level in enumerate(q["criteria"])}:
                raise ValueError("Score legend changed")
            number(a.get("confidence"))
        else:
            raise ValueError("Unsupported primitive")
    return response


# Issue keys that imply a listed team. `routine` and `other` do not constrain the owner.
ISSUE_OWNER = {
    "supply": {"delivery": "operations", "commercial": "procurement", "quality": "quality"},
    "service": {"outage": "operations", "defect": "product", "security": "security"},
    "review": {
        "unsupported": "assurance",
        "contradiction": "assurance",
        "commercial": "commercial",
    },
}
POLICY_VARIANTS = {"original", "stale", "unverified", "strict"}


def head_inconsistencies(case: dict, response: dict) -> list[dict]:
    """Record issue/owner disagreement. Default policy does not change the route; `strict` does."""
    pack = case.get("pack")
    expected = ISSUE_OWNER.get(pack, {}).get(response["answers"]["issue"]["choice"])
    owner = response["answers"]["owner"]["choice"]
    if not expected or expected == owner:
        return []
    return [
        {
            "kind": "issue_owner_mismatch",
            "issue": response["answers"]["issue"]["choice"],
            "owner": owner,
            "implied_owner": expected,
            "explanation": f"The issue head implies {expected}, but the owner head names {owner}.",
        }
    ]


def decide(case: dict, response: dict, threshold: float = 0.85, variant: str = "original") -> dict:
    number(threshold)
    if variant not in POLICY_VARIANTS:
        raise ValueError("Unknown policy-only variant")
    a = response["answers"]
    owner = a["owner"]["choice"]
    p = a["owner"]["probabilities"][owner]
    critical = a["severity"]["probabilities"]["3"]
    facts = copy.deepcopy(case["facts"])
    if variant == "stale":
        facts["source_fresh"] = False
    if variant == "unverified":
        facts["source_verified"] = False
    for key in ("source_fresh", "source_verified", "mandatory_review"):
        if not isinstance(facts.get(key), bool):
            raise ValueError("Policy facts must be explicit booleans")
    mismatches = head_inconsistencies(case, response)
    rules = [
        (
            "source_trust",
            not facts["source_verified"],
            "VERIFY_SOURCE",
            "An unverified source cannot be made trustworthy by model confidence.",
        ),
        (
            "source_freshness",
            not facts["source_fresh"],
            "REFRESH_EVIDENCE",
            "Expired evidence needs a refresh, not a more confident prediction.",
        ),
        (
            "mandatory_review",
            facts["mandatory_review"],
            "HUMAN_REVIEW",
            "Current policy explicitly requires a person.",
        ),
        (
            "critical_tail",
            critical >= 0.30,
            "HUMAN_REVIEW",
            "The critical-level probability reaches the illustrative 0.30 review threshold.",
        ),
        (
            "conflicting_evidence",
            a["contradiction"]["noul"] >= 0.5,
            "REQUEST_EVIDENCE",
            "Material disagreement needs evidence repair.",
        ),
        (
            "insufficient_evidence",
            a["sufficient"]["noul"] < 0.75,
            "REQUEST_EVIDENCE",
            "The sufficiency signal is below the illustrative 0.75 threshold.",
        ),
        (
            "owner_uncertain",
            owner == "other" or p < threshold,
            "HUMAN_REVIEW",
            f"The top owner probability must reach {threshold:.2f} and name a listed team.",
        ),
    ]
    trace = []
    route = "ROUTE_TO_TEAM"
    for rule, matched, next_route, explanation in rules:
        trace.append({"rule": rule, "matched": matched, "explanation": explanation})
        if matched:
            route = next_route
            break
    if route == "ROUTE_TO_TEAM":
        trace.append(
            {
                "rule": "recommend_team",
                "matched": True,
                "explanation": "Recommend an investigating team. This is not approval to execute a business action.",
            }
        )
    evidence = a["next_evidence"]["choice"]
    if route == "REQUEST_EVIDENCE" and evidence == "none":
        trace.append(
            {
                "rule": "inconsistent_heads",
                "matched": True,
                "explanation": "Evidence is needed but its selector says none. A person must reconcile this conflict.",
            }
        )
        route = "HUMAN_REVIEW"
    if variant == "strict" and route == "ROUTE_TO_TEAM" and mismatches:
        trace.append(
            {
                "rule": "inconsistent_issue_owner",
                "matched": True,
                "explanation": mismatches[0]["explanation"]
                + " Strict policy holds for a person to reconcile the heads.",
            }
        )
        route = "HUMAN_REVIEW"
    elif mismatches:
        trace.append(
            {
                "rule": "inconsistent_issue_owner",
                "matched": False,
                "explanation": mismatches[0]["explanation"]
                + " Default policy still follows owner confidence; switch to strict heads to hold.",
            }
        )
    return {
        "route": route,
        "owner": owner,
        "owner_probability": p,
        "critical_probability": critical,
        "next_evidence": evidence,
        "threshold": threshold,
        "variant": variant,
        "trace": trace,
        "inconsistencies": mismatches,
        "policy_version": POLICY_VERSION,
        "policy_facts": facts,
        "external_actions": 0,
    }


def verify_receipt(receipt: dict) -> None:
    body = {k: v for k, v in receipt.items() if k not in {"receipt_hash", "receipt_id"}}
    if digest(body) != receipt.get("receipt_hash"):
        raise ValueError("Receipt content hash mismatch")


def run(
    case_id: str,
    mode: str = "replay",
    threshold: float = 0.85,
    consent: bool = False,
    prepaid=None,
) -> dict:
    from . import provider

    case = case_by_id(case_id)
    number(threshold)
    request = request_for(case)
    if mode == "replay":
        response = provider.replay(case_id)
        provenance = {
            "kind": "synthetic_replay",
            "model_calls": 0,
            "latency_ms": None,
            "usage": None,
            "estimated_cost_usd": None,
            "warning": "Authored teaching probabilities, not measured Jev outputs or performance evidence.",
        }
    elif mode == "live":
        if consent is not True:
            raise PermissionError(
                "Explicit consent is required to send this synthetic case to TypeSafe."
            )
        response, provenance = provider.live(request, prepaid=prepaid)
    else:
        raise ValueError("Mode must be replay or live")
    validate(request, response, live=mode == "live")
    receipt = {
        "schema_version": "2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "pack": case["pack"],
        "facts_snapshot": case["facts"],
        "request": request,
        "response": response,
        "provenance": provenance,
        "question_version": QUESTION_VERSION,
        "request_hash": digest(request),
        "question_hash": digest(request["questions"]),
        "case_hash": digest(case),
        "policy_source_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "decision": decide(case, response, threshold),
        "additional_model_calls": provenance["model_calls"],
    }
    receipt["receipt_hash"] = digest(receipt)
    return receipt


def reconsider(receipt: dict, threshold: float, variant: str = "original") -> dict:
    verify_receipt(receipt)
    number(threshold)
    result = copy.deepcopy(receipt)
    result.pop("receipt_hash", None)
    result.pop("receipt_id", None)
    result["parent_receipt_hash"] = receipt["receipt_hash"]
    result["decision"] = decide(
        {"facts": receipt["facts_snapshot"], "pack": receipt.get("pack")},
        receipt["response"],
        threshold,
        variant,
    )
    result["additional_model_calls"] = 0
    result["policy_evaluated_at"] = datetime.now(timezone.utc).isoformat()
    result["receipt_hash"] = digest(result)
    return result
