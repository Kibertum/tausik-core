"""memory-only: task knowledge hits are optional backlog, not SENAR workflow."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_RAG = _REPO / "harness" / "claude" / "mcp" / "codebase-rag"
for _p in (_REPO / "scripts", _RAG):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rag_handlers import _format_knowledge_results  # noqa: E402


def test_memory_only_labels_task_hits_as_optional_backlog():
    text = _format_knowledge_results(
        {
            "tasks": [{"slug": "old", "title": "Old work", "status": "done"}],
            "memory": [{"title": "Fact", "content": "Owner said X"}],
            "decisions": [{"id": 1, "decision": "Use B"}],
        },
        governance_profile="memory-only",
    )
    assert "historical/optional" in text
    assert "not required SENAR workflow" in text
    assert "old: Old work" in text
    assert "Fact: Owner said X" in text
    assert "Use B" in text
    assert "=== MEMORY" in text
    assert "=== DECISIONS" in text


def test_full_profile_task_hits_keep_plain_heading():
    text = _format_knowledge_results(
        {"tasks": [{"slug": "t", "title": "T", "status": "active"}]},
        governance_profile="full",
    )
    assert "=== TASKS (1 results) ===" in text
    assert "historical/optional" not in text
    assert "SENAR workflow" not in text
