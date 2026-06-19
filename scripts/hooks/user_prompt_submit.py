#!/usr/bin/env python3
"""UserPromptSubmit hook: nudge the agent when a coding-intent prompt arrives without an active task.

Anti-drift mechanism. Fires before Claude processes the user's message. If the prompt
looks like a coding request ("fix", "add", "напиши", etc.) and there is no active
TAUSIK task, the hook injects a reminder via hookSpecificOutput.additionalContext.

Always exits 0 (non-blocking). Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import has_active_task as _has_active_task  # noqa: E402


CODING_INTENT_KEYWORDS = (
    # English
    r"\b(fix|add|create|build|implement|refactor|write|modify|update|change|remove|delete|rename|migrate|port)\b",
    r"\b(code|function|method|class|module|endpoint|api|component|feature|bug)\b",
    # Russian
    r"\b(напиши|добавь|сделай|создай|реализуй|поправ|почини|исправ|перепиши|удали|переименуй)\b",
    r"\b(функци[яюие]|метод|класс|модул[ьяе]|эндпойнт|компонент|фича|баг)\b",
)

QUESTION_PATTERNS = (
    r"^\s*(что\s+такое|как\s+работает|как\s+устроен|explain|what\s+is|how\s+does|how\s+do|why\s+does)",
    r"^\s*(покажи|show\s+me|расскажи|tell\s+me|describe)",
    r"^\s*(объясни|поясни|summarize|give\s+me\s+a\s+summary)",
)


def _has_coding_intent(prompt: str) -> bool:
    """Return True if the prompt looks like a coding request."""
    if not prompt:
        return False
    lowered = prompt.lower().strip()
    for pat in QUESTION_PATTERNS:
        if re.search(pat, lowered):
            return False
    for pat in CODING_INTENT_KEYWORDS:
        if re.search(pat, lowered):
            return True
    return False


def _read_prompt() -> str:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    value = data.get("prompt") or data.get("user_prompt") or data.get("message") or ""
    return value if isinstance(value, str) else ""


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tausik_db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(tausik_db):
        return 0

    prompt = _read_prompt()
    if not _has_coding_intent(prompt):
        return 0

    if _has_active_task(project_dir):
        return 0

    reminder = (
        "**[TAUSIK nudge]** This looks like a coding request but no TAUSIK task is active. "
        "Before writing code: run `tausik_task_list --status active` to check, "
        "or create a task via `/plan` or `/go` (SENAR Rule 1, enforced by PreToolUse hook). "
        "Skipping this step means Write/Edit will be blocked."
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reminder,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
