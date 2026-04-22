#!/usr/bin/env python3
"""PostToolUse hook: audit Claude auto-memory writes for project markers.

Safety-net for the PreToolUse memory_pretool_block. The user could have
used the `confirm: cross-project` bypass and written something that still
carries project-specific traces (paths, slugs, TAUSIK commands, file refs).
This hook scans the just-written file with memory_markers.detect_markers and
emits a stderr warning if anything shows up — it never blocks.

Exit 0 always.
Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory_markers import detect_markers  # noqa: E402
from memory_pretool_block import is_in_claude_memory  # noqa: E402


_AUDITED_TOOLS = ("Write", "Edit", "MultiEdit")
_MAX_REPORTED = 5


def _read_stdin_json() -> dict:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not os.path.exists(os.path.join(project_dir, ".tausik", "tausik.db")):
        return 0

    event = _read_stdin_json()
    if event.get("tool_name") not in _AUDITED_TOOLS:
        return 0

    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    file_path = tool_input.get("file_path") or ""
    if not isinstance(file_path, str):
        return 0

    if not is_in_claude_memory(file_path):
        return 0

    expanded = os.path.expanduser(file_path)
    if not os.path.isfile(expanded):
        return 0

    content = _read_file(expanded)
    if not content:
        return 0

    matches = detect_markers(content)
    if not matches:
        return 0

    head = matches[:_MAX_REPORTED]
    extra = len(matches) - len(head)
    lines = [
        f"AUDIT: auto-memory write at {file_path} contains {len(matches)} "
        "project marker(s):"
    ]
    for m in head:
        lines.append(f"  - [{m.kind}] {m.match}")
    if extra > 0:
        lines.append(f"  ...and {extra} more")
    lines.append(
        "Consider moving project-specific knowledge to "
        "`.tausik/tausik memory add` (pattern|convention|gotcha)."
    )
    print("\n".join(lines), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
