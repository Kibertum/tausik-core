"""Shared helpers for TAUSIK hooks (previously duplicated across 5 files)."""

from __future__ import annotations

import os
import re
import subprocess
import sys


_TASK_DONE_TOOL_NAMES = (
    "mcp__tausik-project__tausik_task_done",
    "tausik_task_done",
)

# Match actual CLI shape: `.tausik/tausik task done <slug>` or `tausik task done <slug>`
# — not any prose mention of "task done" in a Bash command (echo, grep, git log, ...).
_BASH_TASK_DONE_RE = re.compile(
    r"\btausik(?:\.cmd)?\b[^|;&]*?\btask\s+done\s+([a-z0-9][a-z0-9-]*)"
)


def tausik_path(project_dir: str) -> str | None:
    """Locate the TAUSIK CLI wrapper for the given project."""
    candidates: list[str] = []
    if sys.platform == "win32":
        candidates.append(os.path.join(project_dir, ".tausik", "tausik.cmd"))
    candidates.append(os.path.join(project_dir, ".tausik", "tausik"))
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def has_active_task(project_dir: str, timeout: int = 4) -> bool:
    """Check whether TAUSIK has an active task; graceful-True on CLI failure."""
    tausik_cmd = tausik_path(project_dir)
    if not tausik_cmd:
        return True
    try:
        result = subprocess.run(
            [tausik_cmd, "task", "list", "--status", "active"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=project_dir,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return True
    if result.returncode != 0:
        return True
    out = result.stdout.strip()
    if not out or "(none)" in out or "No tasks" in out:
        return False
    for line in out.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("slug", "---")):
            return True
    return False


def extract_task_done_slug_from_bash(command: str) -> str:
    """Return the task slug if the command is a real `tausik task done <slug>` call, else ''."""
    if not isinstance(command, str):
        return ""
    match = _BASH_TASK_DONE_RE.search(command)
    return match.group(1) if match else ""


def is_task_done_invocation(tool_name: str, tool_input: dict) -> bool:
    """True if this tool call is actually closing a task (MCP or Bash CLI)."""
    if tool_name in _TASK_DONE_TOOL_NAMES:
        return True
    if tool_name != "Bash":
        return False
    return bool(extract_task_done_slug_from_bash(tool_input.get("command") or ""))
