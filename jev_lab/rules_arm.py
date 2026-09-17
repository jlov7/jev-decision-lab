"""Deterministic keyword/rules baseline. No model, no distribution, no fabricated probabilities."""

from __future__ import annotations

from .adapters import SCHEMA_VERSION, TRACKS, ProviderArm
from .engine import ISSUE_OWNER, case_by_id, cases

_NO_DISTRIBUTION = (
    "Keyword rules return a category only. They provide no class distribution, so none "
    "was fabricated and this track is unavailable."
)

# First matching cue wins. Order is the teaching point: quality/security/commercial
# before generic delay/delivery words, except S02 is only a delay-keyword trap.
CUES = {
    "quality": ("specification", "material test", "inspection:", "batches fail"),
    "security": ("privileged", "sign-in", "unrecognized device", "unauthorized"),
    "commercial": (
        "annual minimum",
        "annual commitment",
        "no additional cost",
        "operate the service continuously",
        "new annual",
    ),
    "contradiction": ("still reports failures", "stores no customer", "may be retained"),
    "unsupported": ("guarantees a 40%", "cost reduction across"),
    "outage": ("cannot submit", "no workaround", "submissions fail", "dispatch stopped"),
    "defect": ("wrong shade", "icon differs", "cosmetic"),
    "delivery": ("delay", "cargo", "carrier:", "shipment", "delivered"),
}

EVIDENCE_FOR_ISSUE = {
    "quality": "quality_record",
    "security": "security_record",
    "commercial": {"supply": "terms", "review": "approved_scope"},
    "contradiction": "original_source",
    "unsupported": "calculation",
    "outage": "telemetry",
    "defect": "reproduction",
    "delivery": "tracking",
}

URGENT = ("urgent", "tomorrow", "no workaround", "production stops", "launch is tomorrow")


def _blob(state: dict) -> str:
    parts = [str(state.get("message") or "")]
    for item in state.get("evidence") or []:
        if isinstance(item, dict):
            parts.append(str(item.get("text") or ""))
        else:
            parts.append(str(item))
    return " ".join(parts).lower()


def _first_cue(text: str) -> str | None:
    for name, needles in CUES.items():
        if any(needle in text for needle in needles):
            return name
    return None


def _pack_of(request: dict, case_id: str | None) -> str:
    if case_id:
        return case_by_id(case_id)["pack"]
    state = request.get("state")
    domain = state.get("domain", "") if isinstance(state, dict) else ""
    for case in cases():
        if case["state"].get("domain") == domain:
            return case["pack"]
    return "supply"


def decide_state(request: dict, case_id: str | None = None) -> dict:
    """Map authored text to pack vocabularies. Visible, dumb, and deterministic."""
    text = _blob(
        request.get("state")
        if isinstance(request.get("state"), dict)
        else {"message": str(request.get("state") or "")}
    )
    pack = _pack_of(request, case_id)
    cue = _first_cue(text)
    questions = request["questions"]
    issue_keys = set(questions["issue"]["criteria"]) if "issue" in questions else set()
    owner_keys = set(questions["owner"]["criteria"]) if "owner" in questions else set()
    evidence_keys = (
        set(questions["next_evidence"]["criteria"]) if "next_evidence" in questions else set()
    )
    issue = cue if cue else "routine"
    if issue not in issue_keys:
        issue = "other" if "other" in issue_keys else next(iter(issue_keys), "other")
    owner = ISSUE_OWNER.get(pack, {}).get(cue, "other") if cue else "other"
    if owner not in owner_keys:
        owner = "other" if "other" in owner_keys else next(iter(owner_keys), "other")
    ev_spec = EVIDENCE_FOR_ISSUE.get(cue, "none")
    if isinstance(ev_spec, dict):
        evidence = ev_spec.get(pack, "none")
    else:
        evidence = ev_spec if cue and cue not in {"defect"} else "none"
    if evidence not in evidence_keys:
        evidence = "none" if "none" in evidence_keys else next(iter(evidence_keys), "none")
    urgent = any(word in text for word in URGENT)
    # Delay-keyword trap: S02 contains "delay" but is resolved. Rules still escalate.
    delay_trap = "delay" in text and "on time" in text
    severity = (
        3
        if urgent
        else (
            2
            if delay_trap or cue in {"quality", "security", "commercial", "outage"}
            else (1 if cue else 0)
        )
    )
    contradiction = (
        1.0
        if cue in {"contradiction"}
        or ("still reports" in text and "restored" in text)
        or ("cargo remains" in text and "on track" in text)
        else 0.0
    )
    sufficient = (
        0.0 if delay_trap or contradiction or cue in {"contradiction", "unsupported"} else 1.0
    )
    return {
        "issue": issue,
        "owner": owner,
        "severity": min(
            severity, max(0, len(questions.get("severity", {}).get("criteria", [0, 1, 2, 3])) - 1)
        ),
        "sufficient": sufficient,
        "contradiction": contradiction,
        "next_evidence": evidence,
    }


def _record(wire_type: str, primitive: str, answer) -> dict:
    return {
        "wire_type": wire_type,
        "primitive": primitive,
        "answer": answer,
        "distribution": None,
        "distribution_note": _NO_DISTRIBUTION,
        "provider_confidence": None,
    }


class RulesArm(ProviderArm):
    """Keyword baseline used to show what a delay-alert rule would do. Sends nothing."""

    name = "rules"
    kind = "deterministic_rules"
    live = False
    pinned_version = "keyword-rules-v1"

    def call(self, request: dict, case_id: str | None = None) -> dict:
        decided = decide_state(request, case_id)
        records = {}
        for qid, question in request["questions"].items():
            qtype = question["type"]
            if qtype == "choice":
                key = "owner" if qid == "owner" else "issue" if qid == "issue" else "next_evidence"
                value = decided[key]
                if value not in question["criteria"]:
                    value = (
                        "other"
                        if "other" in question["criteria"]
                        else "none"
                        if "none" in question["criteria"]
                        else next(iter(question["criteria"]))
                    )
                records[qid] = _record("choice", "category", value)
            elif qtype == "score":
                records[qid] = _record("score", "ordered", decided["severity"])
            elif qtype == "noul":
                flag = decided["sufficient"] if qid == "sufficient" else decided["contradiction"]
                records[qid] = _record("boolean", "proposition", flag)
            else:
                raise ValueError(f"Unsupported primitive: {qid}")
        raw = {
            "model": self.pinned_version,
            "output": decided,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
        provenance = {
            "kind": self.kind,
            "model": self.pinned_version,
            "model_calls": 0,
            "latency_ms": None,
            "usage": raw["usage"],
            "estimated_cost_usd": None,
            "price_as_of": None,
            "live_verified": False,
            "adapter_schema_version": SCHEMA_VERSION,
            "warning": "Deterministic keyword rules hand-fit to these twelve authored cases, not a tuned baseline and not a model. Its agreement count is a teaching device, never an accuracy figure. Delay-alert wording is treated as a delivery exception on purpose.",
        }
        return {
            "raw": raw,
            "provenance": provenance,
            "normalized": {
                "schema_version": SCHEMA_VERSION,
                "wire_schema": "deterministic_rules",
                "tracks": list(TRACKS),
                "live_verified": False,
                "records": records,
            },
        }
