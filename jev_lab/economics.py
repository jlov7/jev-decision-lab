"""Transparent, assumption-only decision economics. Never a measured Jev result."""

from __future__ import annotations

import math

from .engine import digest

# Values are authored teaching assumptions, in USD, fractions and hours as named.
DEFAULTS = {
    "volume": 1000,
    "model_cost_per_attempt": 0.001,
    "failure_rate": 0.02,
    "auto_share": 0.6,
    "auto_error_rate": 0.03,
    "reviewer_error_rate": 0.01,
    "baseline_error_rate": 0.01,
    "review_minutes": 5,
    "hourly_cost": 60,
    "error_loss": 100,
    "overhead": 500,
    "review_capacity_hours": 40,
}
BOUNDS = {
    "volume": (1, 10_000_000),
    "model_cost_per_attempt": (0, 1000),
    "failure_rate": (0, 1),
    "auto_share": (0, 1),
    "auto_error_rate": (0, 1),
    "reviewer_error_rate": (0, 1),
    "baseline_error_rate": (0, 1),
    "review_minutes": (0, 1440),
    "hourly_cost": (0, 10_000),
    "error_loss": (0, 1_000_000),
    "overhead": (0, 10_000_000),
    "review_capacity_hours": (0, 1_000_000),
}


def _validate(a):
    if not isinstance(a, dict) or set(a) != set(DEFAULTS):
        raise ValueError("Supply exactly the twelve named economics assumptions")
    for k, v in a.items():
        lo, hi = BOUNDS[k]
        if (
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not lo <= v <= hi
            or not math.isfinite(v)
        ):
            raise ValueError(f"{k} must be a finite number between {lo} and {hi}")
    if type(a["volume"]) is not int:
        raise ValueError("volume must be an integer")


def _calculate(a):
    n = a["volume"]
    failed = n * a["failure_rate"]
    automated = (n - failed) * a["auto_share"]
    reviewed = n - automated  # Every failed call is reviewed; none disappears.
    hours = reviewed * a["review_minutes"] / 60
    auto_errors, review_errors = (
        automated * a["auto_error_rate"],
        reviewed * a["reviewer_error_rate"],
    )
    model, review = n * a["model_cost_per_attempt"], hours * a["hourly_cost"]
    loss = (auto_errors + review_errors) * a["error_loss"]
    baseline = (
        n * a["review_minutes"] / 60 * a["hourly_cost"]
        + n * a["baseline_error_rate"] * a["error_loss"]
    )
    proposed = model + review + loss + a["overhead"]
    denominator = automated * a["error_loss"]
    return {
        "cases": {"attempted": n, "failed": failed, "automated": automated, "reviewed": reviewed},
        "errors": {"automated": auto_errors, "reviewed": review_errors},
        "costs": {
            "model": model,
            "review": review,
            "residual_error_loss": loss,
            "overhead": a["overhead"],
            "proposed": proposed,
            "baseline": baseline,
            "difference": baseline - proposed,
        },
        "capacity": {
            "required_hours": hours,
            "available_hours": a["review_capacity_hours"],
            "shortfall_hours": max(0, hours - a["review_capacity_hours"]),
            "feasible": hours <= a["review_capacity_hours"],
        },
        "break_even_auto_error_rate": (
            baseline - model - review - review_errors * a["error_loss"] - a["overhead"]
        )
        / denominator
        if denominator
        else None,
    }


def calculate(assumptions: dict) -> dict:
    _validate(assumptions)
    a = dict(assumptions)
    r = _calculate(a)
    r.update(
        {
            "kind": "assumption_only",
            "version": "decision-economics-v1",
            "assumptions": a,
            "assumptions_hash": digest(a),
            "model_calls": 0,
            "status": "CAPACITY_FEASIBLE_UNDER_ASSUMPTIONS"
            if r["capacity"]["feasible"]
            else "REVIEW_CAPACITY_SHORTFALL",
            "warning": "Teaching assumptions, not observed outcomes, a savings claim or a deployment recommendation. Error rates need local validation. Expected case counts may be fractional. Review may fail. Delay, tail risk, integration and recovery are not independently modelled; include their cost in overhead. No deployment follows from a positive difference.",
            "sensitivity": [],
        }
    )
    for key in ("auto_error_rate", "review_minutes"):
        for factor in (0.5, 1.5):
            changed = dict(a, **{key: min(BOUNDS[key][1], a[key] * factor)})
            scenario = _calculate(changed)
            r["sensitivity"].append(
                {
                    "changed": key,
                    "value": changed[key],
                    "cost_difference": scenario["costs"]["difference"],
                    "capacity_feasible": scenario["capacity"]["feasible"],
                }
            )
    return r
