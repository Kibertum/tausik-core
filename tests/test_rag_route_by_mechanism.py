"""RAG is the route to code by mechanism: every Grep brings the index's hits.

rag-first-by-mechanism-not-text (1.10, decision #391, replacing #390(1)). Text
telling the agent to search RAG first changed nothing (0 search_code calls in 62,
rag-nudge-replay-protocol §7). The hook scripts/hooks/rag_grep_context.py now
consults the index for the agent after each Grep. The inventory of files that
name search_code stays frozen so a new mention is a decision, not an accident.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_HOOK = _ROOT / "scripts" / "hooks" / "rag_grep_context.py"
sys.path.insert(0, str(_HOOK.parent))
sys.path.insert(0, str(_ROOT / "harness" / "claude" / "mcp" / "codebase-rag"))
# Reads shipped text as data and runs the hook as a process.
CROSSCUTTING_SCOPE = ["harness/skills/", "scripts/hooks/", "bootstrap/"]

import rag_grep_context as hook  # noqa: E402

ALLOWED = {
    "bootstrap/bootstrap_templates.py": "routing table: RAG first, Grep with hits added",
    "harness/skills/debug/SKILL.md": "route to code",
    "harness/skills/explore/SKILL.md": "route to code",
    "harness/skills/start/SKILL.md": "route to code",
    "harness/skills/task/SKILL.md": "route to code",
    "harness/skills/task/variants/model/gpt-5-5.md": "read tools to batch",
    "scripts/hooks/session_start.py": "index-not-ready status line",
    "scripts/hooks/pre-commit": "comment on the post-commit reindex",
    "scripts/hooks/user_prompt_submit.py": "docstring records the removed text nudge",
    "scripts/hooks/rag_grep_context.py": "the mechanism itself",
}


def _mentions() -> set[str]:
    out = set()
    for tree in ("harness/skills", "scripts/hooks", "bootstrap"):
        for path in (_ROOT / tree).rglob("*"):
            if (
                not path.is_file()
                or "__pycache__" in path.parts
                or path.suffix not in {".py", ".md", ""}
            ):
                continue
            if "search_code" in path.read_text(encoding="utf-8", errors="replace"):
                out.add(path.relative_to(_ROOT).as_posix())
    return out


def test_the_inventory_of_mentions_is_frozen():
    assert _mentions() == set(ALLOWED)


def test_the_hook_is_registered_for_grep_on_every_host():
    sys.path.insert(0, str(_ROOT / "bootstrap"))
    from bootstrap_hooks import build_hooks_dict

    hooks = build_hooks_dict(lambda script, suffix="": f"X/{script}{suffix}")
    grep_entries = [
        h["command"]
        for e in hooks["PostToolUse"]
        if "Grep" in str(e.get("matcher", "")).split("|")
        for h in e["hooks"]
    ]
    assert "X/rag_grep_context.py" in grep_entries


@pytest.mark.parametrize(
    "pattern, expected",
    [
        (r"def changed_files_since\(", ["changed_files_since"]),
        (r"class\s+RAGStore", ["RAGStore"]),
        (r"\bx\b|\d+", []),
    ],
)
def test_identifiers_drop_regex_syntax_and_keywords(pattern, expected):
    assert hook.identifiers(pattern) == expected


@pytest.fixture
def indexed(tmp_path):
    from rag_store import RAGStore

    store = RAGStore(str(tmp_path / ".tausik" / "rag" / "rag.db"))
    store.upsert_file(
        "scripts/verify_git_diff.py",
        [
            {
                "content": "def changed_files_since(task_created_at):\n    return set()",
                "language": "python",
                "start_line": 76,
                "end_line": 77,
                "chunk_type": "function",
                "chunk_index": 0,
            }
        ],
    )
    store.close()
    return tmp_path


def _run(project, payload):
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
    )


def test_a_grep_brings_the_index_hits(indexed):
    result = _run(indexed, {"tool_name": "Grep", "tool_input": {"pattern": "changed_files_since"}})
    ctx = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "[TAUSIK RAG]" in ctx and "scripts/verify_git_diff.py:76-77" in ctx


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"tool_name": "Read", "tool_input": {"file_path": "x.py"}}, id="not-grep"),
        pytest.param({"tool_name": "Grep", "tool_input": {"pattern": "\\d+"}}, id="no-identifier"),
        pytest.param(
            {"tool_name": "Grep", "tool_input": {"pattern": "nothing_like_this_zz"}}, id="no-hit"
        ),
    ],
)
def test_nothing_is_added_when_there_is_nothing_to_add(indexed, payload):
    """NEGATIVE: never blocks, never invents."""
    result = _run(indexed, payload)
    assert result.returncode == 0 and result.stdout.strip() == ""


def test_no_index_adds_nothing(tmp_path):
    result = _run(tmp_path, {"tool_name": "Grep", "tool_input": {"pattern": "anything_here"}})
    assert result.returncode == 0 and result.stdout.strip() == ""
