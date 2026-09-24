"""No text the framework injects or ships tells the agent to search RAG first.

rag-first-nudges-do-not-change-tool-choice, decision #390. A paired replay
(docs/ru/research/rag-nudge-replay-protocol.md §7) measured 0 search_code calls
in 62 with every rag-first text delivered and 0 in 76 without, so the texts were
removed from the hooks, the skills and the host template. The INVENTORY of files
that still name search_code is frozen here: a new mention — the way six of them
appeared unnoticed — turns this red until someone decides it belongs.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
# Reads shipped text as data; no import edge selects this test.
CROSSCUTTING_SCOPE = ["harness/skills/", "scripts/hooks/", "bootstrap/"]

_TREES = ("harness/skills", "scripts/hooks", "bootstrap")
_SUFFIXES = {".py", ".md", ""}

#: Files allowed to NAME search_code, each for a factual reason, not advice.
ALLOWED = {
    "bootstrap/bootstrap_templates.py": "routing table lists it as one option; reindex hint",
    "harness/skills/debug/SKILL.md": "neutral availability note",
    "harness/skills/explore/SKILL.md": "neutral availability note",
    "harness/skills/start/SKILL.md": "neutral availability note",
    "harness/skills/task/SKILL.md": "neutral availability note",
    "harness/skills/task/variants/model/gpt-5-5.md": "lists it among read tools to batch",
    "scripts/hooks/session_start.py": "index-not-ready status line",
    "scripts/hooks/pre-commit": "comment on the post-commit reindex",
    "scripts/hooks/user_prompt_submit.py": "docstring records the removed nudge",
}

_PREFERENCE = re.compile(
    r"(prefer|first choice|before any grep|use .{0,30}search_code.{0,20}first|"
    r"search_code.{0,40}\bfirst\b)",
    re.IGNORECASE,
)


def _mentions() -> dict[str, str]:
    out = {}
    for tree in _TREES:
        for path in (_ROOT / tree).rglob("*"):
            if not path.is_file() or path.suffix not in _SUFFIXES or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "search_code" in text:
                out[path.relative_to(_ROOT).as_posix()] = text
    return out


def test_the_inventory_of_mentions_is_frozen():
    assert set(_mentions()) == set(ALLOWED)


def test_no_mention_is_advice_to_search_rag_first():
    offenders = []
    for rel, text in _mentions().items():
        for line in text.splitlines():
            if "search_code" in line and _PREFERENCE.search(line) and "removed" not in line:
                offenders.append(f"{rel}: {line.strip()[:120]}")
    assert not offenders, offenders


def test_the_reader_can_fail():
    assert _PREFERENCE.search("Prefer `mcp__codebase-rag__search_code` for symbol lookup")
    assert _PREFERENCE.search("1. search_code — first choice for symbols")
