#!/usr/bin/env python3
"""Stop hook — keyword detector for agent-output drift.

Inspired by oh-my-claudecode's keyword-detector. Fires when the agent tries to
stop its turn. Reads the conversation transcript, inspects the last assistant
message for drift-announcement keywords ("I'll implement", "let me code",
"реализую это"), and if the agent is about to act without an active TAUSIK task
— blocks the stop and forces the agent to re-check task state before continuing.

Output schema for the block response (Claude Code Stop hook):
    {"decision": "block", "reason": "<instruction>"}

Always exits 0 (non-blocking outcomes are signalled via the decision field).
Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import has_active_task as _has_active_task  # noqa: E402


DRIFT_KEYWORDS = (
    # English — "I'm about to start coding" announcements
    r"\bi['’]?ll\s+(now\s+)?(implement|code|write|create|build|add|refactor|fix)\b",
    r"\blet\s+me\s+(now\s+)?(implement|code|write|create|build|add|refactor|fix|start)\b",
    r"\bi\s+will\s+(now\s+)?(implement|code|write|create|build|add|refactor|fix)\b",
    r"\bi['’]?m\s+going\s+to\s+(implement|code|write|create|build|add|refactor|fix)\b",
    r"\bgoing\s+to\s+(implement|code|write|create|build|add|refactor|fix)\s+",
    r"\bnext\s+step\s+is\s+to\s+(implement|code|write|create|build|add|refactor|fix)",
    # Russian
    r"сейчас\s+(напишу|реализую|добавлю|создам|исправлю|запилю)",
    r"приступ[аю|аем|им]\s+к\s+(реализации|написанию|добавлению|кодированию)",
    r"давайте\s+(напишем|реализуем|добавим|создадим|исправим)",
    r"я\s+(напишу|реализую|добавлю|создам|исправлю|запилю)",
)


def _extract_text(content) -> str:
    """Normalize assistant message content to plain text.

    Claude transcripts store content as either a string or a list of blocks,
    each block being {type, text, ...}. We concatenate all text blocks.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def _read_last_assistant_message(transcript_path: str) -> str:
    if not transcript_path or not os.path.exists(transcript_path):
        return ""
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return ""
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        role = entry.get("role") or entry.get("type")
        if role != "assistant":
            message = entry.get("message") or {}
            role = message.get("role") if isinstance(message, dict) else None
            if role != "assistant":
                continue
            return _extract_text(message.get("content"))
        return _extract_text(
            entry.get("content") or entry.get("message", {}).get("content")
        )
    return ""


def _has_drift_keyword(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(re.search(pat, lowered) for pat in DRIFT_KEYWORDS)


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0

    # Anti-infinite-loop: if our previous block already injected, don't block again.
    if payload.get("stop_hook_active"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tausik_db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(tausik_db):
        return 0

    transcript_path = payload.get("transcript_path") or ""
    last_message = _read_last_assistant_message(transcript_path)
    if not _has_drift_keyword(last_message):
        return 0

    if _has_active_task(project_dir):
        return 0

    reason = (
        "[TAUSIK drift guard] Your last message announced code changes "
        "('I'll implement' / 'сейчас напишу' / similar) but there is no active TAUSIK task. "
        "Before proceeding: run `tausik_task_list --status active` to verify, "
        "and if no task is active, create one with `/plan` or `/go`. "
        "SENAR Rule 1 (enforced by PreToolUse) will block Write/Edit otherwise."
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
