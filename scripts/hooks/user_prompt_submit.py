#!/usr/bin/env python3
"""UserPromptSubmit hook: nudge the agent on a coding-intent or code-discovery prompt.

Fires before Claude processes the user's message and injects reminders via
hookSpecificOutput.additionalContext. Two independent nudges:

- task nudge — the prompt looks like a coding request ("fix", "add", "напиши")
  and no TAUSIK task is active (SENAR Rule 1).
- rag-first nudge — the prompt looks like a code-discovery question
  ("where is X", "где определ…"), so `mcp__codebase-rag__search_code` beats
  Grep+Read on unfamiliar code. Fires regardless of active task.

The rag-first nudge used to live on the Stop hook, where it was both useless and
harmful: Stop fires after the agent has already searched, and a blocked Stop is
rendered by the harness as a hook error that swallows the turn's output. It also
matched its own reason text — Claude Code feeds a Stop block's reason back as a
user-role message, and that text quoted every trigger phrase verbatim
("where is X" / "how does Z work" / "где определ…"), so the nudge re-armed itself
on every turn. UserPromptSubmit only ever sees genuine human prompts, which
removes that class of bug rather than patching around it.
See task ``keyword-detector-self-trigger-loop``.

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


# Code-discovery questions — "where is X" / "find Y" / "how does Z work".
SEARCH_INTENT_KEYWORDS = (
    # English
    r"\bwhere\s+is\s+\w+",
    r"\bwhere\s+(does|do)\s+\w+",
    r"\bfind\s+(the\s+)?(function|method|class|definition|implementation|usage|usages|references)\b",
    r"\bhow\s+does\s+\w+\s+(work|behave)",
    r"\bhow\s+is\s+\w+\s+(implemented|used|called)",
    r"\bwhich\s+(file|files|module|modules)\s+(define|defines|contain|contains)",
    # Russian
    r"\bгде\s+(определ|реализ|использ|объявл|задан)",
    r"\bнайди\s+(функци|метод|класс|реализаци|использовани)",
    r"\bкак\s+работает\s+\w+",
    r"\bкакие\s+файлы\s+(содерж|определ|использ)",
)

# A prompt carrying this marker is machine-generated: either a hook's own
# additionalContext echoed back, or a slash-command body expanded by the
# harness. Both quote the trigger phrases above and must never re-arm a nudge.
_MACHINE_PROMPT_MARKERS = ("[TAUSIK ", "<command-name>", "<command-message>")

SEARCH_RECOMMENDATION = (
    "**[TAUSIK rag-first nudge]** Your prompt looks like a code-discovery question. "
    "Prefer `mcp__codebase-rag__search_code` for symbol/pattern lookup — it returns "
    "ranked chunks, not full files, and is much cheaper token-wise than Grep+Read on "
    "unfamiliar code. Use Grep/Read only for known file paths."
)


def _is_machine_prompt(prompt: str) -> bool:
    """True for harness-generated text: hook feedback, slash-command expansions."""
    if not prompt:
        return True
    if prompt.lstrip().startswith("/"):
        return True
    return any(marker in prompt for marker in _MACHINE_PROMPT_MARKERS)


def _has_search_intent(prompt: str) -> bool:
    """Return True if the prompt asks where/how some code lives."""
    if not prompt:
        return False
    lowered = prompt.lower()
    return any(re.search(pat, lowered) for pat in SEARCH_INTENT_KEYWORDS)


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
    # hook-stderr-encoding-locale-dependent: this hook's messages contain
    # non-ASCII, and their readability must not depend on how it was
    # launched. Local import: hooks/ is sys.path[0] only when run as a script.
    from _common import force_utf8_io

    force_utf8_io()

    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tausik_db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(tausik_db):
        return 0

    prompt = _read_prompt()
    if _is_machine_prompt(prompt):
        return 0

    nudges = []

    if _has_coding_intent(prompt) and not _has_active_task(project_dir):
        nudges.append(
            "**[TAUSIK nudge]** This looks like a coding request but no TAUSIK task is active. "
            "Before writing code: run `tausik_task_list --status active` to check, "
            "or create a task via `/plan` (SENAR Rule 1, enforced by PreToolUse hook). "
            "Skipping this step means Write/Edit will be blocked."
        )

    # Independent of task state: knowing *how* to search is orthogonal to Rule 1.
    if _has_search_intent(prompt):
        nudges.append(SEARCH_RECOMMENDATION)

    if not nudges:
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n\n".join(nudges),
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
