#!/usr/bin/env python3
"""PreToolUse hook: block Write/Edit/MultiEdit to ~/.claude/projects/*/memory/.

Protects Claude auto-memory from accidental project-specific records. Project
knowledge belongs in TAUSIK memory (`.tausik/tausik memory add`); the user's
home memory is for cross-project preferences only.

Bypass: if the last user turn in the transcript contains the marker
`confirm: cross-project`, the hook allows the write (escape hatch for truly
cross-project preferences).

Exit codes: 0 = allow, 2 = block.
Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import last_user_prompt_text, marker_present_anchored  # noqa: E402


_BYPASS_MARKER = "confirm: cross-project"
_BLOCKED_TOOLS = ("Write", "Edit", "MultiEdit")


def _read_stdin_json() -> dict:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _normalize(p: str) -> str:
    """Lowercase + forward-slash path; strips drive-letter case differences on Windows."""
    n = os.path.normpath(p).replace("\\", "/")
    return n.lower() if sys.platform == "win32" else n


def is_in_claude_memory(file_path: str) -> bool:
    """Public alias — callable from other hooks without relying on private name."""
    return _is_in_claude_memory(file_path)


def _is_in_claude_memory(file_path: str) -> bool:
    """True iff file_path sits under $HOME/.claude/projects/<any>/memory/."""
    if not file_path:
        return False
    home = _normalize(os.path.expanduser("~"))
    target = _normalize(os.path.expanduser(file_path))
    prefix = f"{home}/.claude/projects/"
    if not target.startswith(prefix):
        return False
    rest = target[len(prefix) :].split("/", 2)
    return len(rest) >= 2 and rest[1] == "memory"


def _bypass_present(transcript_path: str) -> bool:
    prompt = last_user_prompt_text(transcript_path)
    return marker_present_anchored(prompt, _BYPASS_MARKER)


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not os.path.exists(os.path.join(project_dir, ".tausik", "tausik.db")):
        return 0

    event = _read_stdin_json()
    if event.get("tool_name") not in _BLOCKED_TOOLS:
        return 0

    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    file_path = tool_input.get("file_path") or ""
    if not isinstance(file_path, str):
        return 0

    if not _is_in_claude_memory(file_path):
        return 0

    if _bypass_present(event.get("transcript_path") or ""):
        return 0

    print(
        "BLOCKED: Writing to Claude auto-memory (~/.claude/projects/*/memory/) "
        "from a TAUSIK project.\n"
        "Is this project-specific knowledge? -> .tausik/tausik memory add\n"
        "Is this a cross-project user preference? -> reply explicitly with "
        "the marker `confirm: cross-project` in your next message, then retry.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
