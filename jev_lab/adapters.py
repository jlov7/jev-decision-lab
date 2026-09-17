"""Provider adapters: one explicit interface, two wire schemas, no shared guesswork.

BUILD_PACKET.md:200 asks for provider adapters behind an explicit interface that
returns the raw response alongside normalized predictions plus model, configuration,
usage and latency, and that reports two separate tracks rather than forcing every
provider to emit a long explanation:

  * ``minimal_decision``          - the smallest actionable answer (a category/action).
  * ``comparable_distribution``   - full distributions, only where a provider gives them.

The native TypeSafe route and the Vercel AI SDK evaluation route do NOT return the
same objects. Native names the yes/no primitive ``noul`` and returns distributions
for choice and score; the AI SDK names it ``boolean``, returns no distribution for
choice or score, and exposes a separate provider confidence statistic. This module
normalizes both without pretending they are interchange-able, and never fabricates a
distribution the provider did not return (route-doc rule at ACCESS_AND_TRADEOFFS:110).

No call in this module has been verified against a live route. ``live_verified`` is
False on every arm and stays that way until an authenticated response is observed.
"""

from __future__ import annotations

import copy
import json
import time

from . import engine, provider

SCHEMA_VERSION = "adapter-v1.0"
TRACKS = ("minimal_decision", "comparable_distribution")

# Pinned to the documented route requirements; see docs/ACCESS_AND_TRADEOFFS.md:93.
GATEWAY_PACKAGE_PIN = "ai@7.0.105"
GATEWAY_MODEL = "typesafe-ai/jev"
GATEWAY_PRICE_PER_MILLION_INPUT = 0.042
GATEWAY_PRICE_AS_OF = "2026-09-17"
MAX_INPUT_BYTES = provider.MAX_INPUT_BYTES

GATEWAY_WIRE_TYPES = frozenset({"choice", "score", "boolean"})

_NO_DISTRIBUTION = (
    "The AI SDK returns no distribution for this primitive. A distribution was not "
    "fabricated. Preserve a redacted raw response and resolve the mismatch instead."
)


class ProviderArm:
    """The adapter contract. Every arm declares its tracks and its verification state.

    ``call`` returns ``{'raw', 'provenance', 'normalized'}``: the untouched provider
    response, the provenance record, and the normalized predictions. Arms fail closed;
    none of them retries and none falls back to replay output.
    """

    name = ""
    kind = ""
    live = False
    live_verified = False
    pinned_version = ""
    tracks = TRACKS

    def call(self, request: dict, case_id: str | None = None) -> dict:
        raise NotImplementedError


class ReplayArm(ProviderArm):
    """Authored teaching fixtures. Sends nothing and measures no Jev capability."""

    name = "replay"
    kind = "synthetic_replay"
    pinned_version = "synthetic-fixture-v1"

    def call(self, request: dict, case_id: str | None = None) -> dict:
        if not case_id:
            raise ValueError("Replay requires a case id; fixtures are keyed by case.")
        response = provider.replay(case_id)
        provenance = {
            "kind": "synthetic_replay",
            "model_calls": 0,
            "latency_ms": None,
            "usage": None,
            "estimated_cost_usd": None,
            "price_as_of": None,
            "live_verified": False,
            "warning": "Authored teaching probabilities, not measured Jev outputs or performance evidence.",
        }
        return {
            "raw": response,
            "provenance": provenance,
            "normalized": normalize_native(request, response),
        }


class NativeArm(ProviderArm):
    """The existing TypeSafe transport, unchanged: no retries, no replay fallback."""

    name = "native"
    kind = "live_typesafe"
    live = True
    pinned_version = provider.ENDPOINT

    def call(self, request: dict, case_id: str | None = None) -> dict:
        response, provenance = provider.live(request)
        provenance = dict(
            provenance, live_verified=False, adapter_schema_version=SCHEMA_VERSION
        )
        return {
            "raw": response,
            "provenance": provenance,
            "normalized": normalize_native(request, response),
        }


class GatewayArm(ProviderArm):
    """The Vercel AI SDK evaluation route.

    Evaluation is exposed only through the AI SDK (TypeScript, v7+), so a stdlib-only
    Python process cannot invoke it. This arm therefore requires an injected transport
    that performs the documented call; without one it refuses before sending anything
    rather than inventing a wire schema.
    """

    name = "gateway"
    kind = "live_gateway"
    live = True
    pinned_version = GATEWAY_PACKAGE_PIN

    def __init__(self, transport=None):
        self.transport = transport

    def build_payload(self, request: dict) -> dict:
        questions = {}
        for qid, question in request["questions"].items():
            payload = {
                "type": gateway_wire_type(question["type"]),
                "instructions": question.get("instructions", ""),
            }
            if "criteria" in question:
                payload["criteria"] = copy.deepcopy(question["criteria"])
            questions[qid] = payload
        return {
            "model": GATEWAY_MODEL,
            "state": copy.deepcopy(request["state"]),
            "questions": questions,
            "providerOptions": {
                "gateway": {"zeroDataRetention": True, "noTraining": True}
            },
        }

    def call(self, request: dict, case_id: str | None = None) -> dict:
        if not self.transport:
            raise PermissionError(
                "No approved Gateway transport is configured, so nothing was sent. Evaluation is "
                "exposed only through the AI SDK (TypeScript, v7 or later); supply a transport that "
                "performs that call. Do not guess the wire schema."
            )
        payload = self.build_payload(request)
        body = json.dumps(payload, allow_nan=False).encode()
        if len(body) > MAX_INPUT_BYTES:
            raise ValueError(
                "Request exceeds the lab 16,000-byte ceiling. Nothing was sent."
            )
        started = time.perf_counter()
        response = self.transport(payload)
        latency = round((time.perf_counter() - started) * 1000, 2)
        return {
            "raw": response,
            "provenance": gateway_provenance(response, latency),
            "normalized": normalize_gateway(request, response),
        }


_ARMS = {"replay": ReplayArm, "native": NativeArm, "gateway": GatewayArm}
ARM_NAMES = ("replay", "native", "gateway", "claude")


def build(name: str, transport=None) -> ProviderArm:
    if name == "claude":
        from .llm_arm import ClaudeArm  # optional SDK; imported lazily

        return ClaudeArm()
    if name not in _ARMS:
        raise ValueError(
            f"Unknown provider arm {name!r}. Registered arms: {sorted(ARM_NAMES)}"
        )
    return GatewayArm(transport=transport) if name == "gateway" else _ARMS[name]()


def gateway_wire_type(question_type: str) -> str:
    """Native names the yes/no primitive ``noul``; the AI SDK names it ``boolean``."""
    if question_type == "noul":
        return "boolean"
    if question_type in {"choice", "score"}:
        return question_type
    raise ValueError(f"No Gateway representation for question type {question_type!r}")


def _native_confidence(answer: dict, qid: str):
    value = answer.get("confidence")
    if value is None:
        return None
    return {
        "metric": "typesafe_confidence",
        "value": engine.number(value),
        "interpretation": "Provider confidence statistic for this question. It is not a class "
        "probability and is not interchange-able with the distribution above.",
    }


def _gateway_confidence_metadata(response: dict):
    if not isinstance(response, dict):
        return None
    metadata = response.get("providerMetadata")
    if not isinstance(metadata, dict):
        return None
    typesafe = metadata.get("typesafe")
    if not isinstance(typesafe, dict):
        return None
    confidence = typesafe.get("confidence")
    return confidence if isinstance(confidence, dict) else None


def _gateway_confidence(confidence, qid: str):
    if not confidence:
        return None
    value = confidence.get(qid)
    if value is None:
        return None
    return {
        "metric": "typesafe_confidence",
        "value": engine.number(value),
        "interpretation": "Provider metadata statistic for this question. The AI SDK documents it "
        "as not the selected option probability and not a portable confidence "
        "measure, so it is reported separately from any distribution.",
    }


def normalize_native(request: dict, response: dict) -> dict:
    """Normalize a native TypeSafe response. Strict: schema drift fails closed."""
    answers = response.get("answers") if isinstance(response, dict) else None
    if not isinstance(answers, dict) or set(answers) != set(request["questions"]):
        raise ValueError("Native response question IDs do not match the request")
    records = {}
    for qid, question in request["questions"].items():
        answer, qtype = answers[qid], question["type"]
        if not isinstance(answer, dict) or answer.get("type") != qtype:
            raise ValueError(f"Native answer type mismatch: {qid}")
        if qtype == "choice":
            probabilities = engine.distribution(
                answer.get("probabilities"), set(question["criteria"])
            )
            chosen = answer.get("choice")
            if chosen not in probabilities:
                raise ValueError(
                    f"Native choice is outside the declared criteria: {qid}"
                )
            records[qid] = {
                "wire_type": "choice",
                "primitive": "category",
                "answer": chosen,
                "distribution": {
                    "kind": "categorical",
                    "probabilities": copy.deepcopy(probabilities),
                    "source": "provider_distribution",
                },
                "distribution_note": None,
                "provider_confidence": _native_confidence(answer, qid),
            }
        elif qtype == "score":
            levels = len(question["criteria"])
            probabilities = engine.distribution(
                answer.get("probabilities"), {str(i) for i in range(levels)}
            )
            records[qid] = {
                "wire_type": "score",
                "primitive": "ordered",
                "answer": engine.number(answer.get("score"), 0, levels - 1),
                "distribution": {
                    "kind": "ordinal",
                    "probabilities": copy.deepcopy(probabilities),
                    "source": "provider_distribution",
                },
                "distribution_note": None,
                "provider_confidence": _native_confidence(answer, qid),
            }
        elif qtype == "noul":
            value = engine.number(answer.get("noul"))
            records[qid] = {
                "wire_type": "noul",
                "primitive": "proposition",
                "answer": value,
                "distribution": {
                    "kind": "binary",
                    "probabilities": {"yes": value, "no": round(1 - value, 12)},
                    "source": "provider_noul",
                },
                "distribution_note": None,
                "provider_confidence": _native_confidence(answer, qid),
            }
        else:
            raise ValueError(f"Unsupported native primitive: {qid}")
    return {
        "schema_version": SCHEMA_VERSION,
        "wire_schema": "typesafe_native",
        "tracks": list(TRACKS),
        "live_verified": False,
        "records": records,
    }


def normalize_gateway(request: dict, response: dict) -> dict:
    """Normalize an AI SDK evaluation response. Never invents a missing distribution."""
    answers = response.get("answers") if isinstance(response, dict) else None
    if not isinstance(answers, dict) or set(answers) != set(request["questions"]):
        raise ValueError(
            "Gateway response question IDs do not match the request. "
            "No answer was fabricated to fill the gap."
        )
    confidence = _gateway_confidence_metadata(response)
    records = {}
    for qid, question in request["questions"].items():
        answer = answers[qid]
        if not isinstance(answer, dict):
            raise TypeError(f"Gateway answer is not an object: {qid}")
        wire_type = answer.get("type")
        if wire_type not in GATEWAY_WIRE_TYPES:
            raise ValueError(f"Unknown Gateway wire type {wire_type!r}: {qid}")
        expected = gateway_wire_type(question["type"])
        if wire_type != expected:
            raise ValueError(
                f"Gateway wire type {wire_type!r} cannot answer question {qid} "
                f"({question['type']})"
            )
        provider_confidence = _gateway_confidence(confidence, qid)
        if wire_type == "choice":
            chosen = answer.get("choice")
            if chosen not in question["criteria"]:
                raise ValueError(
                    f"Gateway choice is outside the declared criteria: {qid}"
                )
            records[qid] = {
                "wire_type": wire_type,
                "primitive": "category",
                "answer": chosen,
                "distribution": None,
                "distribution_note": _NO_DISTRIBUTION,
                "provider_confidence": provider_confidence,
            }
        elif wire_type == "score":
            levels = len(question["criteria"])
            records[qid] = {
                "wire_type": wire_type,
                "primitive": "ordered",
                "answer": engine.number(answer.get("score"), 0, levels - 1),
                "distribution": None,
                "distribution_note": _NO_DISTRIBUTION,
                "provider_confidence": provider_confidence,
            }
        else:
            value = engine.number(answer.get("probability"))
            records[qid] = {
                "wire_type": "boolean",
                "primitive": "proposition",
                "answer": value,
                "distribution": {
                    "kind": "binary",
                    "probabilities": {"yes": value, "no": round(1 - value, 12)},
                    "source": "provider_boolean",
                },
                "distribution_note": "Boolean probability is documented as not confidence in "
                "either outcome and not guaranteed to be calibrated. It is "
                "comparable as a primitive, not as evidence of accuracy.",
                "provider_confidence": provider_confidence,
            }
    return {
        "schema_version": SCHEMA_VERSION,
        "wire_schema": "ai_sdk_evaluation",
        "tracks": list(TRACKS),
        "live_verified": False,
        "records": records,
    }


def gateway_provenance(response: dict, latency_ms: float) -> dict:
    """Provenance for a Gateway call. A missing count is reported unknown, never zero."""
    usage = response.get("usage") if isinstance(response, dict) else None
    usage = copy.deepcopy(usage) if isinstance(usage, dict) else {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if (
        not isinstance(input_tokens, int)
        or isinstance(input_tokens, bool)
        or input_tokens < 0
    ):
        input_tokens = None
    if (
        not isinstance(output_tokens, int)
        or isinstance(output_tokens, bool)
        or output_tokens < 0
    ):
        output_tokens = None
    usage["output_tokens"] = output_tokens
    usage["output_tokens_known"] = output_tokens is not None
    estimated = (
        input_tokens / 1_000_000 * GATEWAY_PRICE_PER_MILLION_INPUT
        if input_tokens is not None
        else None
    )
    return {
        "kind": "live_gateway",
        "model": GATEWAY_MODEL,
        "model_calls": 1,
        "latency_ms": latency_ms,
        "usage": usage,
        "estimated_cost_usd": estimated,
        "price_per_million_input_usd": GATEWAY_PRICE_PER_MILLION_INPUT,
        "price_as_of": GATEWAY_PRICE_AS_OF,
        "pinned_version": GATEWAY_PACKAGE_PIN,
        "live_verified": False,
        "adapter_schema_version": SCHEMA_VERSION,
        "warning": "Estimated from reported usage and a dated public price, not an invoice. Output "
        "tokens are priced at zero for this model. Unknown counts stay unknown. No call "
        "in this prototype has been verified against the live route.",
    }
