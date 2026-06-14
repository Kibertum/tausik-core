"""Context-memory surfaced at session start + memory-first constraint.

Regression for v15p-memory-first-recall: durable `context` facts (hosts,
machines, access) must appear in CLAUDE.md every session so the agent does not
"forget" them and ask the user for something already recorded.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

from project_backend import SQLiteBackend  # noqa: E402
from service_knowledge_aggregates import (  # noqa: E402
    build_compact_memory_tail,
    build_memory_block,
)


def _backend(tmp_path) -> SQLiteBackend:
    return SQLiteBackend(str(tmp_path / "t.db"))


class TestContextInMemoryTail:
    def test_context_surfaced_when_present(self, tmp_path):
        be = _backend(tmp_path)
        be.memory_add("context", "Test machine 212 is Linux, ssh user@212", "details")
        out = build_compact_memory_tail(be)
        joined = "\n".join(out)
        assert "Context (" in joined
        assert "212" in joined

    def test_no_context_section_when_none(self, tmp_path):
        be = _backend(tmp_path)
        be.memory_add("convention", "snake_case files", "x")
        out = build_compact_memory_tail(be)
        assert all("Context (" not in line for line in out)

    def test_empty_db_returns_empty(self, tmp_path):
        assert build_compact_memory_tail(_backend(tmp_path)) == []

    def test_context_capped_at_five(self, tmp_path):
        be = _backend(tmp_path)
        for i in range(8):
            be.memory_add("context", f"host-{i}", "x")
        out = build_compact_memory_tail(be)
        ctx_lines = [ln for ln in out if ln.startswith("- #") and "host-" in ln]
        assert len(ctx_lines) == 5

    def test_memory_block_includes_context(self, tmp_path):
        be = _backend(tmp_path)
        be.memory_add("context", "prod DB at db.internal:5432", "x")
        block = build_memory_block(be)
        assert "Context" in block and "db.internal" in block


class TestMemoryFirstConstraintInTemplates:
    def test_full_memory_template_has_memory_first_rule(self):
        from bootstrap_templates import MEMORY

        low = MEMORY.lower()
        assert "memory-first" in low
        assert "memory_search" in low
        assert "process violation" in low

    def test_minimal_memory_template_has_memory_first_rule(self):
        from bootstrap_templates import MINIMAL_MEMORY

        assert "memory_search" in MINIMAL_MEMORY.lower()
