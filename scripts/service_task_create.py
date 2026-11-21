"""One atomic task-creation contract shared by every transport."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from project_service import ProjectService


def _string_list(name: str, value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of strings")
    return value


def task_add_complete(
    svc: ProjectService,
    *,
    story_slug: str | None,
    slug: str,
    title: str,
    stack: str | None = None,
    complexity: str | None = None,
    goal: str | None = None,
    role: str | None = None,
    defect_of: str | None = None,
    call_budget: int | None = None,
    tier: str | None = None,
    cost_budget_usd: float | None = None,
    token_budget: int | None = None,
    acceptance_criteria: str | None = None,
    scope: str | None = None,
    scope_exclude: str | None = None,
    scope_paths: object = None,
    scope_tools: object = None,
    rollback_plan: str | None = None,
    assurance_profiles: object = None,
    assurance_impact: object = None,
    relevant_files: object = None,
    plan_steps: object = None,
    rationale: object = None,
    depends_on: object = None,
    tickets: object = None,
) -> str:
    """Create a fully specified task or leave no task, log, plan, or edge behind."""

    predecessors = _string_list("depends_on", depends_on)
    steps = _string_list("plan_steps", plan_steps)
    ticket_refs = _string_list("tickets", tickets)
    if rationale is not None and not isinstance(rationale, str):
        raise ValueError("rationale must be a string")

    files = relevant_files
    if isinstance(files, list):
        files = json.dumps(list(files))
    contract: dict[str, Any] = {
        name: value
        for name, value in {
            "acceptance_criteria": acceptance_criteria,
            "scope": scope,
            "scope_exclude": scope_exclude,
            "scope_paths": scope_paths,
            "scope_tools": scope_tools,
            "rollback_plan": rollback_plan,
            "assurance_profiles": assurance_profiles,
            "assurance_impact": assurance_impact,
            "relevant_files": files,
        }.items()
        if value is not None
    }

    with svc.be.transaction():
        result = svc.task_add(
            story_slug,
            slug,
            title,
            stack,
            complexity,
            goal,
            role,
            defect_of,
            call_budget,
            tier,
            cost_budget_usd=cost_budget_usd,
            token_budget=token_budget,
        )
        if contract:
            svc.task_update(slug, **contract)
        # Route/backlog handoff (task_add_complete): incomplete complex packages
        # get the one-shot legacy marker so task start can normalize — same
        # premise as state import (TB-011). Ad-hoc CLI/MCP complexity=complex
        # without this path stays strict PACKAGE_INVALID.
        if complexity == "complex":
            from backend_migrations_v84 import legacy_marker_for_imported_task

            row = svc.be.task_get(slug) or {}
            marker = legacy_marker_for_imported_task(
                complexity=row.get("complexity"),
                call_budget=row.get("call_budget"),
                assurance_profiles=row.get("assurance_profiles"),
                assurance_impact=row.get("assurance_impact"),
            )
            if marker is not None:
                svc.task_update(slug, task_package_legacy=marker)
        if steps:
            svc.task_plan(slug, steps)
        if rationale:
            svc.task_log(slug, rationale)
        if predecessors:
            from service_task_order import task_depends

            for predecessor in predecessors:
                task_depends(svc, slug, predecessor)
        if ticket_refs:
            import tracker_ref

            svc.task_update(
                slug, tracker_refs=tracker_ref.dumps(tracker_ref.normalise_all(ticket_refs))
            )
    return cast(str, result)
