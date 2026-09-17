"""Request-shape experiment; not a Jev-versus-reasoner benchmark."""

from __future__ import annotations

import copy
import random
import time
from concurrent.futures import ThreadPoolExecutor

from . import engine, provider


def compare_shapes(request: dict, call=provider.live, seed: int = 0) -> list[dict]:
    single = [
        dict(copy.deepcopy(request), questions={key: copy.deepcopy(q)})
        for key, q in request["questions"].items()
    ]
    shapes = ["one_batch", "serial_questions", "parallel_requests"]
    random.Random(seed).shuffle(shapes)

    def measured(payload):
        try:
            response, provenance = call(payload)
            engine.validate(payload, response, live=True)
            return {"ok": True, "response": response, "provenance": provenance}
        except (RuntimeError, PermissionError, ValueError) as exc:
            return {"ok": False, "error": str(exc), "cost_unknown": True}

    results = []
    for shape in shapes:
        payloads = [copy.deepcopy(request)] if shape == "one_batch" else copy.deepcopy(single)
        started = time.perf_counter()
        if shape == "parallel_requests":
            with ThreadPoolExecutor(max_workers=min(6, len(payloads))) as pool:
                observations = list(pool.map(measured, payloads))
        else:
            observations = [measured(p) for p in payloads]
        good = [o for o in observations if o["ok"]]
        failed = len(observations) - len(good)
        token_values, token_unknown = [], False
        for o in good:
            usage = (o.get("provenance") or {}).get("usage")
            tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
            if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0:
                token_values.append(tokens)
            else:
                token_unknown = True
        costs = [(o.get("provenance") or {}).get("estimated_cost_usd") for o in good]
        known_costs = [c for c in costs if c is not None]
        results.append(
            {
                "shape": shape,
                "requests": len(payloads),
                "succeeded": len(good),
                "failed": failed,
                "all_successful": failed == 0,
                "client_wall_ms": (time.perf_counter() - started) * 1000,
                "reported_success_input_tokens": (
                    None
                    if token_unknown or (good and len(token_values) != len(good))
                    else (sum(token_values) if token_values else 0)
                ),
                "estimated_success_cost_usd": (
                    sum(known_costs) if known_costs and len(known_costs) == len(good) else None
                ),
                "failed_request_cost_unknown": failed > 0,
                "observations": observations,
            }
        )
    return results


def benchmark(case_id: str = "S02", repeats: int = 1) -> dict:
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 5:
        raise ValueError("Use 1 to 5 repetitions")
    if not provider.live_enabled():
        raise PermissionError("Configure the live provider before benchmarking")
    request = engine.request_for(engine.case_by_id(case_id))
    needed = repeats * (1 + 2 * len(request["questions"]))
    prepaid = provider.BUDGET.hold(needed)

    def gated(payload):
        return provider.live(payload, prepaid=prepaid)

    results = []
    for repetition in range(repeats):
        shapes = compare_shapes(request, call=gated, seed=repetition)
        results.append({"repetition": repetition + 1, "shapes": shapes})
        if any(not x["all_successful"] for x in shapes):
            break
    return {
        "experiment": "same-state request-shape comparison",
        "kind": "live_typesafe",
        "case_id": case_id,
        "request_hash": engine.digest(request),
        "planned_api_attempts": needed,
        "requested_repetitions": repeats,
        "completed_repetitions": len(results),
        "results": results,
        "warning": "Within-Jev only: one batch versus six serial or concurrent requests. Client wall time includes network overhead. One repetition is a smoke test. Failed requests may still be billed. Synthetic input does not establish enterprise performance.",
    }
