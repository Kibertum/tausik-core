"""Test bootstrap generators — CLAUDE.md template enforcement.

Ensures generate_claude_md produces load-bearing content that prevents agent drift.
Run: pytest tests/test_bootstrap_generate.py -v
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

from bootstrap_generate import (
    generate_agents_md,
    generate_claude_md,
    generate_cursorrules,
)
from bootstrap_qwen import generate_qwen_md


class TestGenerateClaudeMd:
    """Verify generated CLAUDE.md is load-bearing (hard constraints before soft guidance)."""

    def _generate_and_read(self, tmp_path, name="demo", stacks=None):
        generate_claude_md(str(tmp_path), name, stacks if stacks is not None else [])
        path = tmp_path / "CLAUDE.md"
        assert path.exists(), "CLAUDE.md not created"
        return path.read_text(encoding="utf-8")

    def test_contains_hard_constraints(self, tmp_path):
        """Every hard constraint must be present by literal marker."""
        text = self._generate_and_read(tmp_path, "proj", ["python"])
        markers = [
            "No code without a task",
            "QG-0 Context Gate",
            "QG-2 Implementation Gate",
            "No commit without gates",
            "MCP-first",
            "Git: ask before commit/push",
            "Max 400 lines per file",
            "Continuous logging",
            "Document dead ends",
            "Checkpoint every 30-50 tool calls",
            "Session limit: 180 min",
        ]
        for marker in markers:
            assert marker in text, f"Missing hard constraint: {marker!r}"

    def test_contains_workflow_and_memory_sections(self, tmp_path):
        text = self._generate_and_read(tmp_path, "proj", ["python"])
        assert "## Workflow" in text
        assert "start → plan → task" in text
        assert "## Memory" in text
        assert "TAUSIK memory" in text
        assert "Agent auto-memory" in text

    def test_contains_senar_rules_table(self, tmp_path):
        text = self._generate_and_read(tmp_path, "proj", ["python"])
        assert "## SENAR Rules Compliance" in text
        assert "Rule 9.2 Session limit" in text
        assert "Rule 9.3 Checkpoint" in text
        assert "Rule 9.4 Dead Ends" in text

    def test_contains_dynamic_block(self, tmp_path):
        text = self._generate_and_read(tmp_path, "proj", ["python"])
        assert "<!-- DYNAMIC:START -->" in text
        assert "<!-- DYNAMIC:END -->" in text

    def test_line_count_in_range(self, tmp_path):
        """Should be 80-150 lines — dense enough to be load-bearing, short enough to read."""
        text = self._generate_and_read(tmp_path, "proj", ["python"])
        lines = text.splitlines()
        assert 80 <= len(lines) <= 150, f"Line count {len(lines)} outside 80-150 range"

    def test_no_dogfooding_leakage(self, tmp_path):
        """Template must NOT reference TAUSIK-development internals."""
        text = self._generate_and_read(tmp_path, "proj", ["python"])
        forbidden = [
            "CLI → Service → Backend",
            "project_backend.py",
            "project_service.py",
            "scripts/project.py",
            "agents/stacks/",
            "dogfooding",
        ]
        for phrase in forbidden:
            assert phrase not in text, (
                f"Dogfooding leakage: {phrase!r} should not be in template"
            )

    def test_preserves_existing_file(self, tmp_path):
        """Must NOT overwrite an existing CLAUDE.md."""
        existing = "# My custom CLAUDE.md\nCustom content here.\n"
        (tmp_path / "CLAUDE.md").write_text(existing, encoding="utf-8")
        generate_claude_md(str(tmp_path), "proj", ["python"])
        result = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert result == existing, "Existing CLAUDE.md was overwritten"

    def test_empty_stacks_renders_not_detected(self, tmp_path):
        """stacks=[] must not produce empty 'Stack: '."""
        text = self._generate_and_read(tmp_path, "proj", [])
        assert "Stack: not detected" in text

    def test_multiple_stacks_comma_separated(self, tmp_path):
        text = self._generate_and_read(
            tmp_path, "proj", ["python", "react", "typescript"]
        )
        assert "Stack: python, react, typescript" in text

    def test_special_chars_in_project_name(self, tmp_path):
        """Project names with spaces/special chars must not crash generation."""
        text = self._generate_and_read(tmp_path, "My Project (v2)", ["python"])
        assert "## Project: My Project (v2)" in text

    def test_empty_project_name(self, tmp_path):
        """Empty project name must not crash."""
        text = self._generate_and_read(tmp_path, "", ["python"])
        assert "## Project:" in text


SHARED_HARD_MARKERS = [
    "No code without a task",
    "QG-0 Context Gate",
    "QG-2 Implementation Gate",
    "MCP-first",
    "Session limit: 180 min",
    "## SENAR Rules Compliance",
    "<!-- DYNAMIC:START -->",
]


class TestGenerateAgentsMd:
    """AGENTS.md must share the same hard constraints as CLAUDE.md (no weak-ruleset IDE)."""

    def _gen(self, tmp_path, name="proj", stacks=None):
        generate_agents_md(
            str(tmp_path), name, stacks if stacks is not None else ["python"]
        )
        return (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

    def test_contains_shared_hard_markers(self, tmp_path):
        text = self._gen(tmp_path)
        for marker in SHARED_HARD_MARKERS:
            assert marker in text, f"AGENTS.md missing shared marker: {marker!r}"

    def test_header_mentions_agent(self, tmp_path):
        text = self._gen(tmp_path)
        assert "# AGENTS.md" in text
        assert "You are an AI agent" in text

    def test_preserves_existing(self, tmp_path):
        existing = "# Custom AGENTS.md\n"
        (tmp_path / "AGENTS.md").write_text(existing, encoding="utf-8")
        generate_agents_md(str(tmp_path), "proj", ["python"])
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == existing

    def test_empty_stacks(self, tmp_path):
        text = self._gen(tmp_path, stacks=[])
        assert "Stack: not detected" in text


class TestGenerateCursorrules:
    """.cursorrules must share the same hard constraints as CLAUDE.md."""

    def _gen(self, tmp_path, name="proj", stacks=None):
        generate_cursorrules(
            str(tmp_path), name, stacks if stacks is not None else ["python"]
        )
        return (tmp_path / ".cursorrules").read_text(encoding="utf-8")

    def test_contains_shared_hard_markers(self, tmp_path):
        text = self._gen(tmp_path)
        for marker in SHARED_HARD_MARKERS:
            assert marker in text, f".cursorrules missing shared marker: {marker!r}"

    def test_header_mentions_cursor(self, tmp_path):
        text = self._gen(tmp_path)
        assert "# Cursor Rules" in text
        assert "Cursor" in text

    def test_points_to_cursor_subdir(self, tmp_path):
        text = self._gen(tmp_path)
        assert ".cursor/roles/" in text
        assert ".cursor/references/" in text

    def test_preserves_existing(self, tmp_path):
        existing = "# Custom .cursorrules\n"
        (tmp_path / ".cursorrules").write_text(existing, encoding="utf-8")
        generate_cursorrules(str(tmp_path), "proj", ["python"])
        assert (tmp_path / ".cursorrules").read_text(encoding="utf-8") == existing


class TestGenerateQwenMd:
    """QWEN.md must share the same hard constraints as CLAUDE.md."""

    def _gen(self, tmp_path, name="proj", stacks=None):
        generate_qwen_md(
            str(tmp_path), name, stacks if stacks is not None else ["python"]
        )
        return (tmp_path / "QWEN.md").read_text(encoding="utf-8")

    def test_contains_shared_hard_markers(self, tmp_path):
        text = self._gen(tmp_path)
        for marker in SHARED_HARD_MARKERS:
            assert marker in text, f"QWEN.md missing shared marker: {marker!r}"

    def test_header_mentions_qwen(self, tmp_path):
        text = self._gen(tmp_path)
        assert "# QWEN.md" in text
        assert "Qwen Code" in text

    def test_points_to_qwen_subdir(self, tmp_path):
        text = self._gen(tmp_path)
        assert ".qwen/roles/" in text
        assert ".qwen/references/" in text

    def test_preserves_existing(self, tmp_path):
        existing = "# Custom QWEN.md\n"
        (tmp_path / "QWEN.md").write_text(existing, encoding="utf-8")
        generate_qwen_md(str(tmp_path), "proj", ["python"])
        assert (tmp_path / "QWEN.md").read_text(encoding="utf-8") == existing


class TestSyncAcrossIdes:
    """All IDE files must share the same hard constraint set — no drift between IDEs."""

    def test_constraint_parity(self, tmp_path):
        """CLAUDE.md, AGENTS.md, .cursorrules, QWEN.md must share hard constraint text."""
        generate_claude_md(str(tmp_path), "proj", ["python"])
        generate_agents_md(str(tmp_path), "proj", ["python"])
        generate_cursorrules(str(tmp_path), "proj", ["python"])
        generate_qwen_md(str(tmp_path), "proj", ["python"])

        claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        cursor = (tmp_path / ".cursorrules").read_text(encoding="utf-8")
        qwen = (tmp_path / "QWEN.md").read_text(encoding="utf-8")

        for marker in SHARED_HARD_MARKERS:
            assert marker in claude, f"CLAUDE.md missing: {marker!r}"
            assert marker in agents, f"AGENTS.md missing: {marker!r}"
            assert marker in cursor, f".cursorrules missing: {marker!r}"
            assert marker in qwen, f"QWEN.md missing: {marker!r}"
