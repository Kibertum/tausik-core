#!/usr/bin/env python3
"""PostToolUse hook — fire a webhook notification when a task is closed.

Optional; only acts when TAUSIK_SLACK_WEBHOOK / TAUSIK_DISCORD_WEBHOOK /
TAUSIK_TELEGRAM_WEBHOOK is set. Always exits 0; delivery failure is logged
to stderr but never blocks the agent.

Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import sys

_HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOK_DIR)
sys.path.insert(0, os.path.dirname(_HOOK_DIR))

from _common import extract_task_done_slug_from_bash, is_task_done_invocation  # noqa: E402


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    if not is_task_done_invocation(tool_name, tool_input):
        return 0

    if not any(
        os.environ.get(v)
        for v in (
            "TAUSIK_SLACK_WEBHOOK",
            "TAUSIK_DISCORD_WEBHOOK",
            "TAUSIK_TELEGRAM_WEBHOOK",
        )
    ):
        return 0

    slug = tool_input.get("slug") or extract_task_done_slug_from_bash(
        tool_input.get("command") or ""
    )
    if not slug:
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    project_name = os.path.basename(os.path.abspath(project_dir)) or "project"

    message = f"[TAUSIK] Task '{slug}' closed in {project_name}."
    try:
        from notifier import send_notification

        send_notification(message)
    except Exception as exc:
        print(f"notify_on_done: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
