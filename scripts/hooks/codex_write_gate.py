#!/usr/bin/env python3
"""Adapt observed Codex write payloads to the existing task/scope gates.

Codex 0.153.4 reports apply_patch as command text and PowerShell as Bash.
The latter lacks shell identity: only leading literal PowerShell write cmdlets
are recognized here. This is bounded syntax coverage, not shell inference or
a guarantee about arbitrary programs, variables, aliases or computed writes.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bash_write_gate
import execution_lease_gate
import scope_write_gate
import shell_channel
import task_gate
import write_tools
from _common import force_utf8_io, shell_cwd
from codex_cli_authorization import cli_authorization_requests

_PWSH_WRITE = re.compile(
    r"^\s*(?:Set-Content|Add-Content|Out-File|New-Item|Remove-Item|Move-Item|Copy-Item)\b",
    re.IGNORECASE,
)
_PATCH_PATH = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$")


def _implementation_arguments(tool: object, tool_input: dict) -> dict[str, object]:
    encoded = json.dumps(tool_input, sort_keys=True, separators=(",", ":"), default=str)
    return {
        "tool": str(tool),
        "payload_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
    }


def _mcp_route(tool: object) -> str | None:
    if not isinstance(tool, str):
        return None
    for prefix in ("mcp__tausik-project__", "mcp__tausik_project__"):
        if tool.startswith(prefix):
            return tool[len(prefix) :]
    return None


def _mcp_is_read(route: str) -> bool:
    scripts_dir = execution_lease_gate._scripts_dir()
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from adherence_registry import _READ_ROUTES

    return f"mcp.{route}" in _READ_ROUTES


def patch_paths(command: object) -> list[str]:
    """Read structural headers, including BOTH ends of a rename; fail closed."""
    if not isinstance(command, str) or "\x00" in command:
        raise ValueError("invalid patch text")
    lines = command.strip().splitlines()
    if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise ValueError("unsupported patch envelope")
    paths = []
    for line in lines[1:-1]:
        match = _PATCH_PATH.fullmatch(line)
        if match:
            path = match.group(1).strip()
            if not path:
                raise ValueError("empty patch target")
            paths.append(path)
        elif line.startswith("*** ") and line != "*** End of File":
            raise ValueError("unsupported patch header")
    if not paths:
        raise ValueError("patch has no targets")
    return list(dict.fromkeys(paths))


def _run_gate(gate: Callable[[], int], event: dict) -> int:
    """Use real gate logic; leave refusal stderr intact, suppress optional forecasts."""
    previous = sys.stdin
    try:
        sys.stdin = io.StringIO(json.dumps(event))
        with contextlib.redirect_stdout(io.StringIO()):
            return gate()
    finally:
        sys.stdin = previous


def check_event(event: dict, project: str, *, trusted_host: str = "codex") -> int:
    if trusted_host not in {"codex", "cursor"}:
        raise ValueError(f"unsupported trusted host {trusted_host!r}")
    event["_tausik_trusted_host"] = trusted_host
    tool = event.get("tool_name")
    from codex_composite_mcp import (
        AUTHORIZATION_ARGUMENT,
        COMPOSITE_TOOL_NAMES,
        parse_composite_calls,
        rewrite_composite_authorizations,
    )

    if tool in COMPOSITE_TOOL_NAMES:
        calls = parse_composite_calls(tool, event.get("tool_input"))
        mutations = [call for call in calls if not _mcp_is_read(call.route)]
        if not mutations:
            return 0
        correlations: list[str] = []
        result = _require_lease_requests(
            event,
            project,
            [(call.route, call.arguments) for call in mutations],
            preflight_actions=[
                (f"mcp__tausik-project__{call.route}", call.arguments) for call in mutations
            ],
            authorization_tokens=correlations,
            correlate_authorizations=True,
            authorize=True,
        )
        if result == 0:
            event["_tausik_updated_input"] = rewrite_composite_authorizations(
                tool, event.get("tool_input"), mutations, correlations
            )
        return result
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        raise ValueError("missing tool_input")
    command = tool_input.get("command")
    mcp_route = _mcp_route(tool)
    if mcp_route is not None:
        if _mcp_is_read(mcp_route):
            return 0
        if AUTHORIZATION_ARGUMENT in tool_input:
            raise ValueError("model-supplied MCP authorization is forbidden")
        correlations = []
        result = _require_lease(
            event,
            project,
            route=mcp_route,
            arguments=tool_input,
            authorization_tokens=correlations,
            correlate_authorizations=True,
        )
        if result == 0:
            if len(correlations) != 1:
                raise ValueError("MCP authorization correlation was not issued")
            event["_tausik_updated_input"] = {
                **tool_input,
                AUTHORIZATION_ARGUMENT: correlations[0],
            }
        return result
    if tool == "apply_patch":
        base = shell_cwd(event, project)
        for path in patch_paths(command):
            normalized = {
                **event,
                "tool_name": "Write",
                "tool_input": {"file_path": os.path.abspath(os.path.join(base, path))},
            }
            for gate in (task_gate.main, scope_write_gate.main):
                if result := _run_gate(gate, normalized):
                    return result
        return _require_lease(
            event,
            project,
            route="codex_implementation_write",
            arguments=_implementation_arguments(tool, tool_input),
        )
    if write_tools.is_write_tool(tool):
        return _require_lease(
            event,
            project,
            route="codex_implementation_write",
            arguments=_implementation_arguments(tool, tool_input),
        )
    if tool in ("Bash", "PowerShell", *write_tools.MCP_SHELL_TOOLS):
        if not isinstance(command, str):
            raise ValueError("missing shell command")
        shell_tool = "PowerShell" if tool in write_tools.MCP_SHELL_TOOLS else str(tool)
        normalized = {**event, "tool_name": shell_tool}
        cli_requests, cli_seen = cli_authorization_requests(command)
        if cli_requests:
            if result := _require_lease_requests(event, project, cli_requests, authorize=False):
                return result
        if _PWSH_WRITE.match(command):
            if not shell_channel.write_targets("PowerShell", command, shell_cwd(event, project)):
                raise ValueError("PowerShell write has no supported literal target")
            normalized = {**event, "tool_name": "PowerShell"}
            result = _run_gate(bash_write_gate.main, normalized)
            if not result and not cli_requests:
                result = _require_lease(
                    event,
                    project,
                    route="codex_implementation_write",
                    arguments=_implementation_arguments(tool, tool_input),
                )
            if result:
                return result
            if cli_requests:
                return _require_lease_requests(event, project, cli_requests, authorize=True)
            return 0
        result = _run_gate(bash_write_gate.main, normalized)
        if result:
            return result
        if not cli_requests and shell_channel.write_targets(
            shell_tool, command, shell_cwd(event, project)
        ):
            if result := _require_lease(
                event,
                project,
                route="codex_implementation_write",
                arguments=_implementation_arguments(tool, tool_input),
            ):
                return result
        if cli_requests:
            return _require_lease_requests(event, project, cli_requests, authorize=True)
        if cli_seen:
            return 0
        from memory_preflight import classify_action

        if classify_action(tool, tool_input) is not None:
            return _require_lease(
                event,
                project,
                route="codex_protected_shell",
                arguments=_implementation_arguments(tool, tool_input),
            )
        return 0
    return 0


def _require_lease(
    event: dict,
    project: str,
    *,
    route: str | None = None,
    arguments: dict | None = None,
    authorization_tokens: list[str] | None = None,
    correlate_authorizations: bool = False,
) -> int:
    lease_ok, lease_error = execution_lease_gate.require_live_lease(
        event,
        project,
        route=route,
        arguments=arguments,
        authorization_tokens=authorization_tokens,
        correlate_authorizations=correlate_authorizations,
        trusted_host=str(event.get("_tausik_trusted_host") or "codex"),
    )
    if lease_ok:
        return 0
    print(f"BLOCKED: {lease_error}", file=sys.stderr)
    return 2


def _require_lease_requests(
    event: dict,
    project: str,
    requests: list[tuple[str | None, dict[str, object]]],
    *,
    preflight_actions: list[tuple[str, dict[str, object]]] | None = None,
    authorization_tokens: list[str] | None = None,
    correlate_authorizations: bool = False,
    authorize: bool,
) -> int:
    lease_ok, lease_error = execution_lease_gate.require_live_lease(
        event,
        project,
        requests=requests,
        preflight_actions=preflight_actions,
        authorization_tokens=authorization_tokens,
        correlate_authorizations=correlate_authorizations,
        authorize=authorize,
        trusted_host=str(event.get("_tausik_trusted_host") or "codex"),
    )
    if lease_ok:
        return 0
    print(f"BLOCKED: {lease_error}", file=sys.stderr)
    return 2


def _read_event() -> tuple[str, dict, str]:
    force_utf8_io()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--trusted-host", choices=("codex", "cursor"), default="codex")
    args = parser.parse_args()
    project = str(Path(args.project).resolve())
    # The deployed configuration owns jurisdiction; payload cwd only resolves targets.
    os.environ["CLAUDE_PROJECT_DIR"] = project
    event = json.load(sys.stdin)
    if not isinstance(event, dict):
        raise ValueError("hook payload is not an object")
    return project, event, args.trusted_host


def main() -> int:
    try:
        project, event, trusted_host = _read_event()
        return check_event(event, project, trusted_host=trusted_host)
    except (ValueError, TypeError, OSError) as exc:
        print(f"BLOCKED: Codex write payload could not be checked: {exc}", file=sys.stderr)
        return 2


def protocol_main() -> int:
    """Emit Codex's explicit decision instead of relying on shell exit forwarding."""
    error = io.StringIO()
    with contextlib.redirect_stderr(error):
        try:
            project, event, trusted_host = _read_event()
            result = check_event(event, project, trusted_host=trusted_host)
        except (ValueError, TypeError, OSError) as exc:
            print(f"BLOCKED: Codex write payload could not be checked: {exc}", file=sys.stderr)
            result = 2
    if result:
        reason = error.getvalue().strip() or "TAUSIK write gate rejected the operation"
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
    elif "_tausik_updated_input" in event:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": event["_tausik_updated_input"],
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(protocol_main())
