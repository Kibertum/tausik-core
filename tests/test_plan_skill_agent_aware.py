"""Smoke checks for agent-native estimation guidance in skills + CLAUDE.md."""

from __future__ import annotations

import os

import pytest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _exists(*parts: str) -> bool:
    return os.path.exists(os.path.join(ROOT, *parts))


class TestPlanSkill:
    def test_mentions_tier_or_call_budget(self):
        text = _read("agents", "skills", "plan", "SKILL.md").lower()
        assert "tier" in text
        assert "call_budget" in text or "call-budget" in text

    def test_mentions_tool_calls_not_hours(self):
        text = _read("agents", "skills", "plan", "SKILL.md").lower()
        assert "tool call" in text or "tool-call" in text

    def test_lists_all_five_tiers(self):
        text = _read("agents", "skills", "plan", "SKILL.md").lower()
        for label in ("trivial", "light", "moderate", "substantial", "deep"):
            assert label in text, f"missing tier label: {label}"


class TestGoSkill:
    def test_mentions_estimation(self):
        # /go skill source is in skills-official/ — gitignored external repo.
        # Skip if not vendored locally (CI does not clone tausik-skills).
        if not _exists("skills-official", "go", "SKILL.md"):
            pytest.skip("skills-official/ not vendored (external repo)")
        text = _read("skills-official", "go", "SKILL.md").lower()
        assert "tier" in text or "call_budget" in text


class TestClaudeMd:
    def test_has_agent_native_estimation_section(self):
        text = _read("CLAUDE.md")
        assert "Agent-native estimation" in text

    def test_section_mentions_tool_calls(self):
        text = _read("CLAUDE.md").lower()
        assert "tool call" in text or "tool-call" in text


class TestMcpToolsDescription:
    def test_task_add_description_mentions_tool_calls(self):
        text = _read("agents", "claude", "mcp", "project", "tools.py")
        # Find tausik_task_add block and check its description.
        assert "tausik_task_add" in text
        idx = text.index('"name": "tausik_task_add"')
        block = text[idx : idx + 600]
        assert "TOOL CALLS" in block

    def test_call_budget_description_lists_tiers(self):
        text = _read("agents", "claude", "mcp", "project", "tools.py")
        # All five tier labels should appear in the call_budget description text.
        for label in ("trivial", "light", "moderate", "substantial", "deep"):
            assert label in text, f"missing tier label in tools.py: {label}"

    def test_mirror_in_sync(self):
        src = _read("agents", "claude", "mcp", "project", "tools.py")
        mirror = _read(".claude", "mcp", "project", "tools.py")
        assert src == mirror, "agents/claude/mcp tools.py and .claude/mcp mirror diverged"
