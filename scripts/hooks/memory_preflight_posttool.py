#!/usr/bin/env python3
"""PostToolUse hook: durably finish a reserved host-bound memory-preflight token."""

from __future__ import annotations

import json
import hashlib
import os
import sys
import argparse
import tempfile
from collections.abc import Mapping

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

EMERGENCY_MARKER = "execution-lease-maintenance"


def _canonical_trusted_host(values: list[str] | None) -> str:
    hosts = values or ["codex"]
    if len(hosts) != 1:
        raise ValueError("exactly one trusted PostToolUse host is required")
    host = hosts[0].casefold()
    if host not in {"codex", "cursor"}:
        raise ValueError(f"unsupported trusted PostToolUse host {hosts[0]!r}")
    return host


def _failed(event: dict) -> bool:
    response = event.get("tool_response")
    if isinstance(response, dict):
        if response.get("is_error") or response.get("isError") or response.get("error"):
            return True
        for key in ("exit_code", "returncode"):
            value = response.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value != 0:
                return True
    return bool(event.get("error"))


def _denied_before_execution(event: dict) -> bool:
    """Recognize Cursor's structural signal that PreToolUse prevented execution."""
    response = event.get("tool_response")
    if not isinstance(response, dict) or not response.get("is_error"):
        return False
    code = response.get("error_code") or response.get("code")
    return isinstance(code, str) and code.strip().upper().replace("-", "_") == "PERMISSION_DENIED"


def _unavailable_observation(event: dict) -> tuple[str, dict[str, str]] | None:
    """Accept only structural host error codes, never tool-controlled prose."""
    if not _failed(event):
        return None
    response = event.get("tool_response")
    if not isinstance(response, dict):
        return None
    nested = response.get("error")
    code = response.get("error_code") or response.get("code")
    if code is None and isinstance(nested, dict):
        code = nested.get("code")
    if not isinstance(code, str):
        return None
    normalized = code.strip().upper().replace("-", "_").replace(" ", "_")
    authority_codes = {
        "IDENTITY_MISSING",
        "PERMISSION_DENIED",
        "ACCESS_DENIED",
        "FORBIDDEN",
        "UNAUTHORIZED",
        "AUTHENTICATION_REQUIRED",
    }
    capability_codes = {
        "CAPABILITY_UNAVAILABLE",
        "NOT_INSTALLED",
        "COMMAND_NOT_FOUND",
        "FILE_NOT_FOUND",
    }
    if normalized not in authority_codes | capability_codes:
        return None
    raw = json.dumps(
        response,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return (
        "authority" if normalized in authority_codes else "capability",
        {
            "observed_code": normalized,
            "response_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        },
    )


def _enter_audit_maintenance(project: str, reason: str) -> None:
    db_path = os.path.join(project, ".tausik", "tausik.db")
    if not os.path.isfile(db_path):
        return
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.dirname(scripts_dir)
    deployed = os.path.join(scripts_dir, "scripts")
    runtime = (
        deployed if os.path.isfile(os.path.join(deployed, "project_backend.py")) else source_dir
    )
    if runtime not in sys.path:
        sys.path.insert(0, runtime)
    from project_backend import SQLiteBackend
    from project_service import ProjectService
    from service_execution_lease import enter_execution_lease_maintenance

    backend = SQLiteBackend(db_path)
    try:
        enter_execution_lease_maintenance(ProjectService(backend), reason)
    finally:
        backend.close()


def _write_emergency_marker(project: str, reason: str) -> str:
    state_dir = os.path.join(project, ".tausik")
    os.makedirs(state_dir, exist_ok=True)
    target = os.path.join(state_dir, EMERGENCY_MARKER)
    fd, temporary = tempfile.mkstemp(prefix="lease-maintenance-", dir=state_dir, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(reason.strip() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return target


def main() -> int:
    project = os.getcwd()
    try:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--project")
        parser.add_argument("--trusted-host", action="append")
        args, _ = parser.parse_known_args()
        trusted_host = _canonical_trusted_host(args.trusted_host)
        project = args.project or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        event = json.load(sys.stdin)
        tool = event.get("tool_name")
        tool_input = event.get("tool_input")
        thread_id = event.get("session_id")
        if not isinstance(tool, str) or not isinstance(thread_id, str):
            _enter_audit_maintenance(project, "malformed trusted PostToolUse identity payload")
            print(
                "MEMORY_PREFLIGHT_AUDIT_FAILED: malformed trusted PostToolUse identity payload; "
                "maintenance entered",
                file=sys.stderr,
            )
            return 0
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        source_dir = os.path.dirname(scripts_dir)
        deployed = os.path.join(scripts_dir, "scripts")
        sys.path.insert(
            0,
            deployed
            if os.path.isfile(os.path.join(deployed, "project_backend.py"))
            else source_dir,
        )
        from codex_composite_mcp import COMPOSITE_TOOL_NAMES, parse_composite_calls

        if tool in COMPOSITE_TOOL_NAMES:
            calls = parse_composite_calls(tool, tool_input, accept_authorization=True)
            actions = [(f"mcp__tausik-project__{call.route}", call.arguments) for call in calls]
        elif isinstance(tool_input, Mapping):
            clean_input = dict(tool_input)
            clean_input.pop("_tausik_authorization", None)
            actions = [(tool, clean_input)]
        else:
            raise ValueError("malformed trusted PostToolUse tool_input")
        from memory_preflight import classify_action, complete_preflight_for_thread

        protected = [
            (action_tool, action_input)
            for action_tool, action_input in actions
            if classify_action(action_tool, action_input) is not None
        ]
        if not protected:
            return 0
        from project_backend import SQLiteBackend
        from service_execution_lease import normalize_project_identity

        backend = SQLiteBackend(os.path.join(project, ".tausik", "tausik.db"))
        try:
            if _denied_before_execution(event):
                for action_tool, action_input in protected:
                    complete_preflight_for_thread(
                        backend,
                        normalize_project_identity(project),
                        thread_id.strip(),
                        action_tool,
                        action_input,
                        host_instance=trusted_host,
                        failed=True,
                        failure_code="PRE_EXECUTION_DENIED",
                    )
                return 0
            completed = [
                complete_preflight_for_thread(
                    backend,
                    normalize_project_identity(project),
                    thread_id.strip(),
                    action_tool,
                    action_input,
                    host_instance=trusted_host,
                    failed=_failed(event),
                )
                for action_tool, action_input in protected
            ]
            if not all(completed):
                from project_service import ProjectService
                from service_execution_lease import enter_execution_lease_maintenance

                enter_execution_lease_maintenance(
                    ProjectService(backend),
                    "protected action completed without an exact reserved preflight token",
                )
                print(
                    "MEMORY_PREFLIGHT_AUDIT_FAILED: reserved token was not found; maintenance entered",
                    file=sys.stderr,
                )
            observation = _unavailable_observation(event)
            if observation is not None and all(completed):
                from can_stop import record_attempt_event
                from project_service import ProjectService

                lease = backend._execution_lease_current(
                    normalize_project_identity(project), trusted_host, thread_id.strip()
                )
                if lease is None:
                    raise ValueError("observed unavailable action has no live task lease")
                event_kind, detail = observation
                attempt_event_id = record_attempt_event(
                    ProjectService(backend),
                    lease=lease,
                    event_kind=event_kind,
                    status="unavailable",
                    detail=detail,
                )
                print(
                    json.dumps(
                        {
                            "systemMessage": (
                                "[TAUSIK blocker evidence] trusted attempt_event_id="
                                f"{attempt_event_id}; pass this ID to tausik_task_block."
                            ),
                            "continue": True,
                        }
                    )
                )
        finally:
            backend.close()
    except Exception as exc:  # noqa: BLE001 - audit completion cannot rewrite tool outcome
        maintenance_error: Exception | None = None
        try:
            _enter_audit_maintenance(project, f"PostToolUse audit failure: {type(exc).__name__}")
        except Exception as secondary:  # noqa: BLE001 - emergency marker is the fallback boundary
            maintenance_error = secondary
            try:
                _write_emergency_marker(
                    project,
                    f"PostToolUse audit failure: {type(exc).__name__}; "
                    f"maintenance persistence failed: {type(secondary).__name__}",
                )
            except Exception as marker_error:  # noqa: BLE001 - report both failed boundaries
                print(
                    "MEMORY_PREFLIGHT_EMERGENCY_MARKER_FAILED: "
                    f"{type(marker_error).__name__}: {marker_error}",
                    file=sys.stderr,
                )
        suffix = (
            f"; database maintenance failed: {type(maintenance_error).__name__}"
            if maintenance_error is not None
            else ""
        )
        print(
            f"MEMORY_PREFLIGHT_AUDIT_FAILED: {type(exc).__name__}: {exc}{suffix}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
