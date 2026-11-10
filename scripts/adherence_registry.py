"""Live service, CLI, MCP and hook route inventory."""

from __future__ import annotations

import functools
import hashlib
import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Final, cast

from adherence_policy import POLICY_VERSION, ContractError

_READ_ROUTES: Final[frozenset[str]] = frozenset(
    """
cli.actz.list cli.actz.search cli.actz.show cli.adapt.list cli.adapt.search
cli.adapt.show cli.at.check-freshness cli.at.list cli.at.search cli.at.show
cli.audit.check cli.config.show cli.epic.list cli.explore.current
cli.gates.list cli.gates.status cli.graph.show cli.graph.status cli.key.show
cli.memory.list cli.memory.search cli.memory.show cli.metrics.answers
cli.metrics.calls cli.metrics.cohorts cli.metrics.compare cli.metrics.cost
cli.metrics.target cli.metrics.task-cost cli.metrics.tokens cli.publish.ci-check
cli.publish.senar-check cli.receipt.show cli.redact.list cli.review.cohort-status
cli.review.list cli.review.metrics cli.roadmap cli.role.list cli.role.show
cli.search cli.session.current cli.session.list cli.skill.bundle.list
cli.skill.bundle.show cli.skill.list cli.skill.repo.list cli.spec.list
cli.spec.search cli.spec.show cli.stack.list cli.status cli.story.list
cli.task.budget-check cli.task.list cli.task.next cli.task.show cli.update-check
mcp.tausik_actz_list mcp.tausik_actz_search mcp.tausik_actz_show
mcp.tausik_adapt_list mcp.tausik_adapt_search mcp.tausik_adapt_show
mcp.tausik_at_check_freshness mcp.tausik_at_list mcp.tausik_at_search
mcp.tausik_at_show mcp.tausik_decisions_list mcp.tausik_epic_list
mcp.tausik_gates_status mcp.tausik_health mcp.tausik_memory_list
mcp.tausik_memory_search mcp.tausik_memory_show mcp.tausik_metrics
mcp.tausik_roadmap mcp.tausik_role_list mcp.tausik_role_show mcp.tausik_search
mcp.tausik_self_check mcp.tausik_session_current mcp.tausik_session_list
mcp.tausik_snippet_search mcp.tausik_spec_list mcp.tausik_spec_search
mcp.tausik_spec_show mcp.tausik_stack_list mcp.tausik_stack_show
mcp.tausik_status mcp.tausik_story_list mcp.tausik_task_list
mcp.tausik_task_next mcp.tausik_task_show
service.actz_list service.actz_search service.actz_show service.adapt_list
service.adapt_search service.adapt_show service.at_check_freshness service.at_list
service.at_search service.at_show service.audit_check service.epic_list
service.events_list service.exploration_current service.gates_status
service.get_metrics service.get_roadmap service.get_status service.memory_list
service.memory_search service.memory_show service.search service.session_check_duration
service.session_current service.session_list service.skill_list service.spec_list
service.spec_search service.spec_show service.stack_list service.story_list
service.task_list service.task_next service.task_show service.task_logs
service.reasoning_steps service.team_status mcp.tausik_task_logs cli.task.logs
""".split()
)

_EXACT_OBLIGATIONS: Final[dict[str, tuple[str, ...]]] = {
    **{
        route: ("execution_lease", "task_package")
        for route in ("cli.task.start", "mcp.tausik_task_start", "service.task_start")
    },
    **{
        route: ("execution_lease", "continuity")
        for route in (
            "cli.task.log",
            "cli.task.step",
            "mcp.tausik_task_log",
            "mcp.tausik_task_step",
            "service.task_log",
            "service.task_step",
        )
    },
    **{
        route: ("execution_lease", "continuity", "task_package")
        for route in ("cli.task.done", "mcp.tausik_task_done", "service.task_done")
    },
    **{
        route: ("execution_lease", "continuity", "memory_preflight")
        for route in ("cli.task.block", "mcp.tausik_task_block", "service.task_block")
    },
    **{
        route: ("execution_lease", "continuity")
        for route in (
            "cli.task.reason-step",
            "mcp.tausik_reason_step",
            "service.reasoning_step_add",
        )
    },
    **{
        route: ("execution_lease", "handoff_resume")
        for route in ("cli.session.start", "mcp.tausik_session_start", "service.session_start")
    },
}

_OPTIONAL_OBLIGATIONS: Final[dict[str, tuple[str, ...]]] = {
    route: ("dead_end_repeat",)
    for route in (
        "cli.task.reason-step",
        "mcp.tausik_reason_step",
        "service.reasoning_step_add",
    )
}


def _classification(boundary: str, route: str, hook_event: str = "") -> str:
    if boundary == "hook":
        if hook_event == "Stop":
            return "stop"
        if hook_event == "PreToolUse":
            return "protected"
        return "mutation"
    return "read" if route in _READ_ROUTES else "mutation"


def _required_events(classification: str, route: str) -> list[str]:
    if classification == "read":
        return []
    if classification == "protected":
        return ["execution_lease", "memory_preflight"]
    if classification == "stop":
        return ["execution_lease", "stop_decision"]

    return list(_EXACT_OBLIGATIONS.get(route, ("execution_lease",)))


def _cli_routes() -> list[str]:
    import argparse

    from project_parser import build_parser

    routes: list[str] = []

    def walk(parser: argparse.ArgumentParser, prefix: tuple[str, ...] = ()) -> None:
        for action in parser._actions:
            if not isinstance(action, argparse._SubParsersAction):
                continue
            for name, child in sorted(action.choices.items()):
                path = (*prefix, name)
                has_children = any(
                    isinstance(candidate, argparse._SubParsersAction)
                    for candidate in child._actions
                )
                if has_children:
                    walk(child, path)
                else:
                    routes.append("cli." + ".".join(path))

    walk(build_parser())
    return routes


def _hook_route(event: str, matcher: str, command: str) -> str:
    script = next((part for part in command.split() if part.endswith(".py")), command)
    matcher_id = hashlib.sha256(matcher.encode("utf-8")).hexdigest()[:12]
    command_id = hashlib.sha256(command.encode("utf-8")).hexdigest()[:12]
    return f"hook.{event}.{Path(script).name}.{matcher_id}.{command_id}"


def discover_dispatch_inventory(
    project_root: str | os.PathLike[str] | None = None,
) -> list[dict[str, object]]:
    """Discover live service, CLI, MCP and hook entry points.

    Unknown additions default to ``mutation``.  The frozen registry hash then
    changes and forces an explicit policy-version review instead of silently
    treating a new write route as read-only.
    """

    root = (
        Path(project_root) if project_root is not None else Path(__file__).resolve().parent.parent
    )
    harness_dir = root / "harness" / "claude" / "mcp" / "project"
    bootstrap_dir = root / "bootstrap"
    for path in (str(harness_dir), str(bootstrap_dir), str(root / "scripts")):
        if path not in sys.path:
            sys.path.insert(0, path)

    from mcp_handler_shape import dispatch_entries
    from project_service import ProjectService

    discovered: list[tuple[str, str, str]] = []
    for name, member in inspect.getmembers(ProjectService, predicate=callable):
        if not name.startswith("_"):
            discovered.append(("service", f"service.{name}", ""))
    mcp_entries = dispatch_entries(str(root))
    for entry in sorted(mcp_entries):
        name = entry[0] if isinstance(entry, tuple) else entry
        discovered.append(("mcp", f"mcp.{name}", ""))
    for route in _cli_routes():
        discovered.append(("cli", route, ""))

    bootstrap_hooks = importlib.import_module("bootstrap_hooks")
    hooks = bootstrap_hooks.build_hooks_dict(lambda script, suffix="": f"{script}{suffix}")
    for event, entries in sorted(hooks.items()):
        for entry in entries:
            matcher = str(entry.get("matcher", ""))
            for hook in entry.get("hooks", []):
                command = str(hook.get("command", ""))
                discovered.append(("hook", _hook_route(event, matcher, command), event))
    # Codex adds one host-specific catch-all adapter around the shared hooks.
    # Its deployed command contains machine-specific absolute paths, so the
    # semantic inventory hashes the canonical script identity and matcher.
    bootstrap_codex = importlib.import_module("bootstrap_codex")
    discovered.append(
        (
            "hook",
            _hook_route(
                "PreToolUse",
                bootstrap_codex.CODEX_WRITE_MATCHER,
                bootstrap_codex.CODEX_WRITE_ADAPTER,
            ),
            "PreToolUse",
        )
    )

    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for boundary, route, hook_event in sorted(discovered, key=lambda row: row[1]):
        if route in seen:
            raise ContractError(f"duplicate dispatch identity: {route}")
        seen.add(route)
        classification = _classification(boundary, route, hook_event)
        rows.append(
            {
                "boundary": boundary,
                "classification": classification,
                "optional_events": list(_OPTIONAL_OBLIGATIONS.get(route, ())),
                "required_events": _required_events(classification, route),
                "route": route,
            }
        )
    return rows


@functools.cache
def _registry_snapshot() -> str:
    return json.dumps(
        {"policy_version": POLICY_VERSION, "routes": discover_dispatch_inventory()},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def registry_artifact() -> dict[str, object]:
    """Return the closed registry derived from live dispatch surfaces."""

    return cast(dict[str, object], json.loads(_registry_snapshot()))


@functools.cache
def _route_by_name() -> dict[str, dict[str, object]]:
    routes = cast(list[dict[str, object]], registry_artifact()["routes"])
    return {str(row["route"]): row for row in routes}
