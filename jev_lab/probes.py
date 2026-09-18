"""Two experiments a cheap, fast judgment model makes practical.

Stability probe: send the same case several times and report how much every answer moves.
Evidence ablation: drop one evidence item at a time and report what moved the judgment.

Both hold their attempt slots before sending anything, keep every failure, never retry and
never fall back to replay. Replay mode exists so the layout can be seen offline; it says so.
"""

from __future__ import annotations

import copy
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import engine, provider
from .showcase import MAX_WORKERS, _percentile

PROBE_MIN, PROBE_MAX = 2, 8
# Observed on 18 Sep 2026 across two twelve-case bursts: top-owner probability moved by at most
# 0.03 between calls. Ablation deltas below that are reported as within-noise, not as effects.
NOISE_FLOOR = 0.03


def _hold(mode: str, consent: bool, n: int):
    if mode == "live":
        if not provider.live_enabled():
            raise PermissionError(
                "Live mode disabled. Paste a key in Connect Jev, or set TYPESAFE_API_KEY and "
                "JEV_ALLOW_LIVE=1 in the server terminal."
            )
        if consent is not True:
            raise PermissionError("Explicit consent is required before any live experiment.")
        return provider.BUDGET.hold(n)
    if mode != "replay":
        raise ValueError("Mode must be replay or live")
    return None


def _run_many(cases: list[dict], mode: str, threshold: float, consent: bool, prepaid) -> list[dict]:
    def one(case: dict) -> dict:
        try:
            return {"ok": True, "receipt": engine.run_case(case, mode, threshold, consent, prepaid)}
        except engine.LiveValidationError as exc:
            return {"ok": False, "error": str(exc), "provider_response": exc.response}
        except (ValueError, PermissionError, RuntimeError) as exc:
            return {"ok": False, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(cases))) as pool:
        return list(pool.map(one, cases))


def _answer_row(receipt: dict) -> dict:
    a = receipt["response"]["answers"]
    d = receipt["decision"]
    return {
        "issue": a["issue"]["choice"],
        "issue_probability": a["issue"]["probabilities"][a["issue"]["choice"]],
        "owner": a["owner"]["choice"],
        "owner_probability": a["owner"]["probabilities"][a["owner"]["choice"]],
        "severity": a["severity"]["score"],
        "critical_probability": d["critical_probability"],
        "sufficient": a["sufficient"]["noul"],
        "contradiction": a["contradiction"]["noul"],
        "next_evidence": a["next_evidence"]["choice"],
        "route": d["route"],
        "latency_ms": receipt["provenance"]["latency_ms"],
        "estimated_cost_usd": receipt["provenance"]["estimated_cost_usd"],
    }


def _spread(values: list[float]) -> dict:
    return {
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "range": round(max(values) - min(values), 4),
    }


def probe(case_id: str, repeats: int, mode: str = "replay", consent: bool = False, threshold: float = 0.85) -> dict:
    """The same case, `repeats` times, concurrently. Reports the spread of every answer."""
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not PROBE_MIN <= repeats <= PROBE_MAX:
        raise ValueError(f"Repeats must be a whole number from {PROBE_MIN} to {PROBE_MAX}")
    case = engine.case_by_id(case_id)
    engine.number(threshold)
    prepaid = _hold(mode, consent, repeats)
    started = time.perf_counter()
    results = _run_many([case] * repeats, mode, threshold, consent, prepaid)
    wall_ms = round((time.perf_counter() - started) * 1000, 2)
    receipts = [r["receipt"] for r in results if r["ok"]]
    rows = [_answer_row(r) for r in receipts]
    questions = receipts[0]["request"]["questions"] if receipts else {}
    spread = {}
    for qid, q in questions.items():
        answers = [r["response"]["answers"][qid] for r in receipts]
        if q["type"] == "noul":
            spread[qid] = {"type": "noul", "value": _spread([a["noul"] for a in answers])}
        elif q["type"] == "score":
            spread[qid] = {
                "type": "score",
                "value": _spread([a["score"] for a in answers]),
                "options": {
                    k: _spread([a["probabilities"][k] for a in answers]) for k in answers[0]["probabilities"]
                },
            }
        else:
            spread[qid] = {
                "type": "choice",
                "top_choices": sorted({a["choice"] for a in answers}),
                "options": {
                    k: _spread([a["probabilities"][k] for a in answers]) for k in answers[0]["probabilities"]
                },
            }
    routes = {}
    for row in rows:
        routes[row["route"]] = routes.get(row["route"], 0) + 1
    latencies = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
    costs = [r["estimated_cost_usd"] for r in rows if r["estimated_cost_usd"] is not None]
    widest = max(
        (
            (max(o["range"] for o in s["options"].values()), qid)
            for qid, s in spread.items()
            if "options" in s
        ),
        default=(0, None),
    )
    return {
        "kind": "stability_probe",
        "mode": mode,
        "case_id": case_id,
        "requested": repeats,
        "succeeded": len(receipts),
        "failed": len(results) - len(receipts),
        "failures": [r for r in results if not r["ok"]],
        "wall_ms": wall_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "receipts": receipts,
        "spread": spread,
        "routes": routes,
        "route_stable": len(routes) <= 1,
        "widest_option_range": {"range": widest[0], "question": widest[1]},
        "latency_ms": {"p50": _percentile(latencies, 0.5), "max": max(latencies) if latencies else None},
        "estimated_cost_usd": sum(costs) if costs and len(costs) == len(rows) else None,
        "warning": (
            "Synthetic replay returns the same authored fixture every time, so every range is zero. "
            "Run this live to measure real call-to-call variation."
            if mode == "replay"
            else f"{repeats} calls on one authored case. This measures call-to-call variation of one "
            "model version on one input, not accuracy and not calibration. Ranges are in probability "
            "units after the provider's two-decimal rounding."
        ),
    }


def _without(case: dict, evidence_id: str) -> dict:
    variant = copy.deepcopy(case)
    variant["state"]["evidence"] = [e for e in variant["state"]["evidence"] if e["id"] != evidence_id]
    return variant


def ablate(case_id: str, mode: str = "replay", consent: bool = False, threshold: float = 0.85) -> dict:
    """Baseline plus one variant per evidence item removed. Reports what moved."""
    case = engine.case_by_id(case_id)
    engine.number(threshold)
    evidence = case["state"]["evidence"]
    if not evidence:
        raise ValueError("This case has no evidence items to remove")
    variants = [("baseline", None, case)] + [
        (f"without {e['id']}", e, _without(case, e["id"])) for e in evidence
    ]
    prepaid = _hold(mode, consent, len(variants))
    started = time.perf_counter()
    results = _run_many([v[2] for v in variants], mode, threshold, consent, prepaid)
    wall_ms = round((time.perf_counter() - started) * 1000, 2)
    base = results[0]
    base_row = _answer_row(base["receipt"]) if base["ok"] else None
    out_variants = []
    for (label, removed, _), result in zip(variants, results):
        entry = {
            "label": label,
            "removed_evidence": removed,
            "ok": result["ok"],
        }
        if result["ok"]:
            row = _answer_row(result["receipt"])
            entry["answers"] = row
            entry["receipt"] = result["receipt"]
            if base_row and removed is not None:
                deltas = {
                    "owner_probability": round(row["owner_probability"] - base_row["owner_probability"], 4),
                    "severity": round(row["severity"] - base_row["severity"], 4),
                    "sufficient": round(row["sufficient"] - base_row["sufficient"], 4),
                    "contradiction": round(row["contradiction"] - base_row["contradiction"], 4),
                }
                entry["deltas"] = deltas
                entry["owner_changed"] = row["owner"] != base_row["owner"]
                entry["issue_changed"] = row["issue"] != base_row["issue"]
                entry["route_changed"] = row["route"] != base_row["route"]
                entry["movement"] = round(
                    sum(abs(v) for k, v in deltas.items() if k != "severity") + abs(deltas["severity"]) / 3,
                    4,
                )
                entry["above_noise"] = (
                    entry["movement"] > NOISE_FLOOR or entry["owner_changed"] or entry["route_changed"]
                )
        else:
            entry["error"] = result["error"]
            if "provider_response" in result:
                entry["provider_response"] = result["provider_response"]
        out_variants.append(entry)
    moved = [v for v in out_variants if v.get("deltas")]
    most = max(moved, key=lambda v: v["movement"], default=None)
    return {
        "kind": "evidence_ablation",
        "mode": mode,
        "case_id": case_id,
        "requested": len(variants),
        "succeeded": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "wall_ms": wall_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline_ok": base["ok"],
        "variants": out_variants,
        "most_influential": most["removed_evidence"]["id"] if most and most["above_noise"] else None,
        "noise_floor": NOISE_FLOOR,
        "warning": (
            "Synthetic replay returns the same authored fixture for every variant, so nothing moves. "
            "Run this live to see which evidence carries the judgment."
            if mode == "replay"
            else f"One call per variant. Differences below {NOISE_FLOOR:.2f} in probability are within "
            "the call-to-call variation observed on this model version and are marked as noise. Removing "
            "evidence changes the input; it does not show what the model attended to."
        ),
    }


def publish(result: dict, store) -> dict:
    """Store receipts, replace them with ids in the public result."""
    if result["kind"] == "stability_probe":
        ids = [store(r)["receipt_id"] for r in result.pop("receipts")]
        for row, rid in zip(result["rows"], ids):
            row["receipt_id"] = rid
    else:
        for variant in result["variants"]:
            if "receipt" in variant:
                variant["receipt_id"] = store(variant.pop("receipt"))["receipt_id"]
    return result
