"""Small evidence-accounting helpers. Missing observations never become zero."""

from __future__ import annotations

import math

from .engine import digest


def costs(rows: list[dict]) -> dict:
    known = [
        r
        for r in rows
        if not isinstance(r.get("estimated_cost_usd"), bool)
        and isinstance(r.get("estimated_cost_usd"), (int, float))
        and math.isfinite(r["estimated_cost_usd"])
        and r["estimated_cost_usd"] >= 0
    ]
    bases = sorted({r.get("billing") or "provider_estimate" for r in known})
    by_basis = {
        b: sum(
            r["estimated_cost_usd"] for r in known if (r.get("billing") or "provider_estimate") == b
        )
        for b in bases
    }
    subtotal = sum(r["estimated_cost_usd"] for r in known)
    complete = bool(rows) and len(known) == len(rows) and len(bases) == 1
    return {
        "attempts": len(rows),
        "known_attempts": len(known),
        "unknown_attempts": len(rows) - len(known),
        "known_cost_usd": subtotal,
        "total_cost_usd": subtotal if complete else None,
        "complete": complete,
        "billing_bases": bases,
        "by_billing_basis": by_basis,
    }


def signature(receipt: dict, include_state: bool = False) -> str:
    request = receipt.get("request") or {}
    obj = {
        "kind": receipt["provenance"]["kind"],
        "model": receipt["response"].get("model"),
        "question_version": receipt.get("question_version"),
        "questions": request.get("questions"),
    }
    if include_state:
        obj["state"] = request.get("state")
    return digest(obj)
