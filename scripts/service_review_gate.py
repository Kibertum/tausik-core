"""Residual-assurance closure gate for ``task done``."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def enforce_assurance_review(
    service: Any,
    task: dict[str, Any],
    slug: str,
    risk: dict[str, Any] | None,
    report: dict[str, Any],
) -> bool:
    """Append a blocking failure when the latest review cannot satisfy the route."""
    from stack_registry import registry_for_project

    stack = task.get("stack")
    stack_assurance = (
        registry_for_project(service.tausik_dir()).assurance_for(str(stack))
        if stack
        else {"profiles": [], "impact": {}}
    )
    assurance_declared = bool(
        task.get("assurance_profiles") is not None
        or task.get("assurance_impact") is not None
        or stack_assurance.get("profiles")
        or stack_assurance.get("impact")
    )
    if not assurance_declared:
        return False

    from review_routing import build_review_route, review_record_blockers
    from task_context_package import _assurance_projection, _review_route

    assurance = _assurance_projection(service, task)
    review_route = _review_route(service, task, assurance)
    if risk is not None:
        from risk_l3_trigger import MIN_MEASURED_WEIGHT, measured_score, measured_weight
        from risk_model import LEVEL_HIGH

        measured_high = bool(
            measured_weight(risk) >= MIN_MEASURED_WEIGHT
            and (measured_score(risk) or 0) >= LEVEL_HIGH
        )
        if measured_high:
            review_route = build_review_route(
                assurance,
                measured_high=True,
                configured_extreme_floor=bool(review_route.get("deep")),
            )
    project_root = Path(service.tausik_dir()).resolve().parent
    blockers = review_record_blockers(service.be._conn, slug, review_route, project_root)
    if not blockers:
        return False
    report["blocking_failures"].append(
        {
            "stage": "review",
            "gate": "residual-assurance",
            "message": "; ".join(blockers),
        }
    )
    return True
