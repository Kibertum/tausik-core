"""Shared helpers for TAUSIK hooks (previously duplicated across 5 files)."""

from __future__ import annotations

import json
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


# --- Bypass-marker helpers (security-critical) -----------------------------
#
# Several PreToolUse hooks allow the user to override a guard by including a
# marker phrase in their last prompt. A naive substring check is unsafe:
# quoting the hook's own error text (which names the marker) would re-enable
# the bypass on the *next* turn. Requiring the marker on a line by itself,
# outside any fenced code block, closes that hole.


_FENCE_RE = re.compile(r"^```")


def last_user_prompt_text(transcript_path: str) -> str:
    """Return the text of the most recent user message in the JSONL transcript.

    Returns '' on any error (missing file, malformed JSON, unexpected shape).
    Preserves the shape assumed by existing hooks: list-of-parts is joined
    with newlines so anchored marker detection sees the original line
    structure.
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return ""
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return ""
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "user":
            continue
        msg = event.get("message") or {}
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                return "\n".join(parts)
    return ""


def marker_present_anchored(text: str, marker: str) -> bool:
    """True iff `marker` appears on a line by itself outside fenced code blocks.

    - Case-insensitive match.
    - Leading/trailing whitespace on the marker line is tolerated.
    - Any line whose content, stripped, matches the marker counts.
    - Lines inside fenced code blocks (``` ... ```) are skipped — so quoting
      the hook's own error text in a fenced block will NOT trigger the bypass.
    - Empty marker always returns False.
    """
    if not marker or not isinstance(text, str):
        return False
    target = marker.strip().lower()
    if not target:
        return False
    in_fence = False
    for raw in text.splitlines():
        if _FENCE_RE.match(raw.lstrip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if raw.strip().lower() == target:
            return True
    return False
