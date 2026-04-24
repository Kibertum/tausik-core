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


# Open or close a fenced-code block. Covers both CommonMark fence styles
# (backticks + tildes). We only recognise fences that start at column 0
# — indented-fence bypass is covered by the separate "indented-line"
# rejection below.
_FENCE_RE = re.compile(r"^(?:`{3,}|~{3,})")

# Unicode line separators that `str.splitlines()` splits on but which are
# visually invisible — an attacker can paste them inside an inline prose
# sentence to make any substring look like "its own line" under the naive
# splitlines() contract. We collapse them to newlines BEFORE splitting on
# "\n" so they disappear entirely.
_UNICODE_LINE_SEPS_RE = re.compile(r"[  ]")

# A line that begins with 4+ spaces or a tab is a markdown indented-code
# block. Reject marker lines that live inside one - this closes the
# pasted-hook-error bypass where the user formats the quote with leading
# indentation instead of a fence.
_INDENTED_RE = re.compile(r"^(?: {4,}|	)")


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
    """True iff `marker` appears on a line by itself outside any code block.

    - Case-insensitive match.
    - Leading/trailing whitespace on the marker line is tolerated, BUT lines
      that begin with 4+ spaces or a tab are treated as indented code and
      rejected even without a fence (closes pasted-hook-error bypass).
    - Any line whose content, stripped, matches the marker counts.
    - Lines inside fenced code blocks are skipped. Fences: triple backticks
      ``` or triple tildes ~~~ at column 0 (after lstrip).
    - Invisible unicode line/paragraph separators (U+2028, U+2029, U+0085,
      vertical tab, form feed) are normalised to '\\n' BEFORE splitting, so
      an attacker cannot smuggle the marker into inline prose by inserting
      one of them.
    - Empty marker always returns False.
    """
    if not marker or not isinstance(text, str):
        return False
    target = marker.strip().lower()
    if not target:
        return False
    # Strip invisible line/paragraph separators entirely (do NOT convert to
    # '\n') — an attacker embeds them in inline prose to fake a "line of its
    # own"; removing them collapses the prose back to a single line where
    # the marker is just a substring, not anchored.
    normalised = _UNICODE_LINE_SEPS_RE.sub("", text)
    in_fence = False
    for raw in normalised.split("\n"):
        if _FENCE_RE.match(raw.lstrip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _INDENTED_RE.match(raw):
            continue
        if raw.strip().lower() == target:
            return True
    return False
