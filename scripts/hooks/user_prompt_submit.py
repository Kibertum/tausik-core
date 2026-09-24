#!/usr/bin/env python3
"""UserPromptSubmit hook: nudge the agent on a coding-intent prompt with no task.

Fires before Claude processes the user's message and injects a reminder via
hookSpecificOutput.additionalContext when the prompt looks like a coding
request ("fix", "add", "напиши") and no TAUSIK task is active (SENAR Rule 1).

A second, rag-first nudge (from "where is X" to search_code) lived here until
1.10 and was removed by decision #390: a paired replay (docs/ru/research/
rag-nudge-replay-protocol.md §7) measured 0 search_code calls in 62 with the
nudges delivered and 0 in 76 without. Text injected every turn and never acted
on is cost without effect. Machine-generated prompts (hook feedback,
slash-command expansions) still never arm a nudge.
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


# A prompt carrying this marker is machine-generated: either a hook's own
# additionalContext echoed back, or a slash-command body expanded by the
# harness. Both quote the trigger phrases above and must never re-arm a nudge.
_MACHINE_PROMPT_MARKERS = ("[TAUSIK ", "<command-name>", "<command-message>")


def _is_machine_prompt(prompt: str) -> bool:
    """True for harness-generated text: hook feedback, slash-command expansions."""
    if not prompt:
        return True
    if prompt.lstrip().startswith("/"):
        return True
    return any(marker in prompt for marker in _MACHINE_PROMPT_MARKERS)


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


_PAYLOAD: dict = {}


def _read_prompt() -> str:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    _PAYLOAD.update(data)
    value = data.get("prompt") or data.get("user_prompt") or data.get("message") or ""
    return value if isinstance(value, str) else ""


def _answer_budget_nudge(project_dir: str) -> str | None:
    """terse-answers-enforced-by-mechanism: score the answer the human just read.

    Here and not on Stop: a blocked Stop swallows the turn's output. Never blocks,
    never rewrites; a missing transcript or an answer within budget adds nothing.
    """
    path = _PAYLOAD.get("transcript_path")
    if not isinstance(path, str) or not path:
        return None
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from answer_shape import DEFAULT_BUDGET_WORDS, budget_nudge, last_final_answer
        from tausik_utils import load_effective_config

        budget = DEFAULT_BUDGET_WORDS
        value = load_effective_config(project_dir).get("answer_budget_words")
        if isinstance(value, int) and value > 0:
            budget = value
        return budget_nudge(last_final_answer(path), budget)
    except Exception:  # noqa: BLE001 — an advisory line must never break the prompt hook
        return None


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

    budget_line = _answer_budget_nudge(project_dir)
    if budget_line:
        nudges.append(budget_line)

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
