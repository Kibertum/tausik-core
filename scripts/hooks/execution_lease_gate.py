"""Fail-closed lease check for trusted Codex PreToolUse boundaries."""

from __future__ import annotations

import os
import sys
from typing import Mapping, Sequence


def _scripts_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.dirname(here)
    deployed = os.path.join(os.path.dirname(here), "scripts")
    return deployed if os.path.isfile(os.path.join(deployed, "project_backend.py")) else source


def require_live_lease(
    event: Mapping[str, object],
    project_dir: str,
    *,
    route: str | None = None,
    arguments: Mapping[str, object] | None = None,
    requests: Sequence[tuple[str | None, Mapping[str, object]]] | None = None,
    preflight_actions: Sequence[tuple[str, Mapping[str, object]]] | None = None,
    authorization_tokens: list[str] | None = None,
    correlate_authorizations: bool = False,
    authorize: bool = True,
    trusted_host: str = "codex",
) -> tuple[bool, str]:
    """Validate trusted event identity and optionally authorize one MCP mutation."""

    emergency_marker = os.path.join(project_dir, ".tausik", "execution-lease-maintenance")
    if os.path.isfile(emergency_marker):
        return (
            False,
            "LEASE_MAINTENANCE: PostToolUse audit persistence failed; from the project root "
            "run `.tausik/tausik doctor --reconcile-execution-leases "
            "revoke-and-reconcile`, then reload Cursor; existing chats, tasks and files "
            "are preserved",
        )
    if trusted_host not in {"codex", "cursor"}:
        return False, f"IDENTITY_INVALID: unsupported trusted host {trusted_host!r}"
    thread_id = event.get("session_id")
    if not isinstance(thread_id, str) or not thread_id.strip():
        return False, f"IDENTITY_MISSING: {trusted_host} hook payload has no session_id"
    scripts_dir = _scripts_dir()
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        from project_backend import SQLiteBackend
        from project_service import ProjectService
        from service_host_context import enforce_hard_ceiling
        from service_execution_lease import (
            assertion_from_pre_tool_use,
            authorize_mcp_mutation,
            enter_execution_lease_maintenance,
            issue_execution_lease,
            normalize_project_identity,
            reconcile_execution_lease_state,
            require_execution_lease,
        )

        backend = SQLiteBackend(os.path.join(project_dir, ".tausik", "tausik.db"))
        try:
            svc = ProjectService(backend)
            if (
                enforce_hard_ceiling(svc, host=trusted_host, thread_id=thread_id.strip())
                is not None
            ):
                return False, "HOST_CONTEXT_HARD: continue in a fresh host thread"
            from tausik_version import __version__

            state = backend._execution_lease_state()
            if state is None or state.get("projection_build") != __version__:
                from session_start import (
                    _codex_preflight_hooks_ready,
                    cursor_preflight_hooks_ready,
                )

                ready = (
                    _codex_preflight_hooks_ready(project_dir)
                    if trusted_host == "codex"
                    else cursor_preflight_hooks_ready(project_dir)
                )
                if not ready:
                    return False, (
                        "CAPABILITY_MISMATCH: protected-action hooks are missing or stale"
                    )
                assertion = assertion_from_pre_tool_use(
                    event, project_dir, trusted_host=trusted_host
                )
                reconcile_execution_lease_state(svc, assertion)
            try:
                current = backend._execution_lease_current(
                    normalize_project_identity(project_dir), trusted_host, thread_id.strip()
                )
            except ValueError as exc:
                enter_execution_lease_maintenance(svc, str(exc))
                return False, f"IDENTITY_AMBIGUOUS: {exc}"
            if current is None:
                # A single agent turn may legitimately outlive the prompt lease.
                # Renew only at this attested PreToolUse boundary, after proving
                # the complete pre/post hook set is still deployed.
                from session_start import (
                    _codex_preflight_hooks_ready,
                    cursor_preflight_hooks_ready,
                )

                ready = (
                    _codex_preflight_hooks_ready(project_dir)
                    if trusted_host == "codex"
                    else cursor_preflight_hooks_ready(project_dir)
                )
                if not ready:
                    return False, (
                        "CAPABILITY_MISMATCH: protected-action hooks are missing or stale"
                    )
                assertion = assertion_from_pre_tool_use(
                    event, project_dir, trusted_host=trusted_host
                )
                reconcile_execution_lease_state(svc, assertion)
                current = issue_execution_lease(svc, assertion)
            request_items = list(requests) if requests is not None else [(route, arguments or {})]
            from execution_lease_package import route_allows_package_bypass

            lease = require_execution_lease(
                svc,
                project_dir=project_dir,
                host_instance=trusted_host,
                thread_id=thread_id.strip(),
                nonce=current["nonce"],
                allow_package_rebind=bool(request_items)
                and route_allows_package_bypass(request_items[0][0], current),
            )
            from execution_lease_package import require_task_argument_binding

            for item_route, item_arguments in request_items:
                if item_route is not None:
                    require_task_argument_binding(lease, item_route, item_arguments)
                    from work_continuity import enforce_continuity_boundary

                    # Refusal state must commit before this hook returns a denial.
                    # An outer transaction would roll the refusal counter back.
                    enforce_continuity_boundary(svc, lease, item_route, item_arguments)
            if authorize:
                with backend.transaction():
                    from memory_preflight import reserve_preflight

                    actions = list(preflight_actions or [])
                    if not actions:
                        raw_tool_input = event.get("tool_input")
                        preflight_input: Mapping[str, object] = (
                            raw_tool_input if isinstance(raw_tool_input, Mapping) else {}
                        )
                        actions.append((str(event.get("tool_name") or ""), preflight_input))
                    for action_tool, action_arguments in actions:
                        reserve_preflight(backend, lease, action_tool, action_arguments)
                    for item_route, item_arguments in request_items:
                        if item_route is None:
                            continue
                        correlation = authorize_mcp_mutation(
                            svc,
                            lease=lease,
                            route=item_route,
                            arguments=item_arguments,
                            correlated=correlate_authorizations,
                        )
                        if authorization_tokens is not None and correlation is not None:
                            authorization_tokens.append(correlation)
        finally:
            backend.close()
    except Exception as exc:  # noqa: BLE001 - hook boundary returns typed refusal
        code = getattr(exc, "code", "LEASE_STORE_UNAVAILABLE")
        if code == "LEASE_MAINTENANCE":
            return False, (
                f"{code}: {exc}; from the project root run `.tausik/tausik doctor "
                "--reconcile-execution-leases revoke-and-reconcile`, then reload Cursor; "
                "existing chats, tasks and files are preserved"
            )
        return False, f"{code}: {exc}"
    return True, ""
