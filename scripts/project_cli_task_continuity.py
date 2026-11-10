"""Atomic CLI task recovery dispatch."""

from __future__ import annotations

import os
from typing import Any


def cmd_task(svc: Any, args: Any) -> None:
    from project_cli_task import _cmd_task

    slug = getattr(args, "slug", None)
    action = getattr(args, "task_cmd", None)
    state = None
    if isinstance(slug, str):
        state = svc.be._q1(
            "SELECT pending_requirement FROM task_continuity_state WHERE task_slug=?",
            (slug,),
        )
    pending = bool(state and state.get("pending_requirement"))
    codex_mutation = (
        os.environ.get("TAUSIK_ENFORCE_EXECUTION_LEASE") == "1"
        and isinstance(slug, str)
        and action not in {"start", "show", "logs", "handoff", "replay", "budget-check"}
    )
    if (pending or codex_mutation) and action not in {"start", "show"}:
        from service_execution_lease import consume_mcp_authorization
        from work_continuity import (
            complete_cli_recovery,
            enforce_continuity_boundary,
            require_recovery_generation,
        )

        assert isinstance(slug, str)
        route_args = {"slug": slug, "action": str(action)}
        lease = consume_mcp_authorization(svc, route="cli_task_mutation", arguments=route_args)
        generation = enforce_continuity_boundary(svc, lease, "cli_task_mutation", route_args)
        with svc.be.transaction():
            if generation is not None:
                require_recovery_generation(svc, lease, generation)
            previous_lease = getattr(svc, "_authorized_execution_lease", None)
            svc._authorized_execution_lease = lease
            try:
                _cmd_task(svc, args)
                complete_cli_recovery(svc, lease, str(action), generation)
            finally:
                svc._authorized_execution_lease = previous_lease
        return
    _cmd_task(svc, args)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
