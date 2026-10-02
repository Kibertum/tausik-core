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
import io
import json
import os
from pathlib import Path
import re
import sys
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bash_write_gate
import scope_write_gate
import shell_channel
import task_gate
from _common import force_utf8_io, shell_cwd

_PWSH_WRITE = re.compile(
    r"^\s*(?:Set-Content|Add-Content|Out-File|New-Item|Remove-Item|Move-Item|Copy-Item)\b",
    re.IGNORECASE,
)
_PATCH_PATH = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$")


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


def check_event(event: dict, project: str) -> int:
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        raise ValueError("missing tool_input")
    command = tool_input.get("command")
    tool = event.get("tool_name")
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
    elif tool in ("Bash", "PowerShell"):
        if not isinstance(command, str):
            raise ValueError("missing shell command")
        if _PWSH_WRITE.match(command):
            if not shell_channel.write_targets("PowerShell", command, shell_cwd(event, project)):
                raise ValueError("PowerShell write has no supported literal target")
            return _run_gate(bash_write_gate.main, {**event, "tool_name": "PowerShell"})
        return _run_gate(bash_write_gate.main, event)
    return 0


def main() -> int:
    force_utf8_io()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    project = str(Path(parser.parse_args().project).resolve())
    # The deployed configuration owns jurisdiction; payload cwd only resolves targets.
    os.environ["CLAUDE_PROJECT_DIR"] = project
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("hook payload is not an object")
        return check_event(event, project)
    except (ValueError, TypeError, OSError) as exc:
        print(f"BLOCKED: Codex write payload could not be checked: {exc}", file=sys.stderr)
        return 2


def protocol_main() -> int:
    """Emit Codex's explicit decision instead of relying on shell exit forwarding."""
    error = io.StringIO()
    with contextlib.redirect_stderr(error):
        result = main()
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
    return 0


if __name__ == "__main__":
    sys.exit(protocol_main())
