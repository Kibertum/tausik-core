"""Smoke checks for agent-native estimation guidance in skills + CLAUDE.md."""

from __future__ import annotations

import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TestPlanSkill:
    def test_mentions_tier_or_call_budget(self):
        text = _read("harness", "skills", "plan", "SKILL.md").lower()
        assert "tier" in text
        assert "call_budget" in text or "call-budget" in text

    def test_mentions_tool_calls_not_hours(self):
        text = _read("harness", "skills", "plan", "SKILL.md").lower()
        assert "tool call" in text or "tool-call" in text

    def test_lists_all_five_tiers(self):
        text = _read("harness", "skills", "plan", "SKILL.md").lower()
        for label in ("trivial", "light", "moderate", "substantial", "deep"):
            assert label in text, f"missing tier label: {label}"

    def test_creates_the_complete_contract_in_one_lease_safe_call(self):
        text = _read("harness", "skills", "plan", "SKILL.md")
        for field in (
            "tausik_task_add",
            "acceptance_criteria",
            "scope_paths",
            "rollback_plan",
            "call_budget",
            "plan_steps",
            "rationale",
            "depends_on",
            "TASK_BINDING_MISMATCH",
        ):
            assert field in text

    @pytest.mark.parametrize(
        "model",
        ["gpt-4.md", "gpt-5.md", "gpt-5-5.md", "haiku.md", "sonnet.md"],
    )
    def test_model_overlay_never_prescribes_cross_task_followups(self, model):
        text = _read("harness", "skills", "plan", "variants", "model", model)
        assert "tausik_task_add" in text
        assert "task_quick` + `task_update" not in text
        assert "tausik_task_log" not in text

    def test_plan_skill_never_prescribes_pre_start_task_log(self):
        text = _read("harness", "skills", "plan", "SKILL.md")
        assert "tausik_task_log" not in text
        assert "rationale" in text

    def test_deployed_plan_skill_keeps_the_atomic_contract(self):
        text = _read(".claude", "skills", "plan", "SKILL.md")
        for field in (
            "tausik_task_add",
            "acceptance_criteria",
            "scope_paths",
            "rollback_plan",
            "call_budget",
            "plan_steps",
            "rationale",
            "depends_on",
        ):
            assert field in text
        assert "task_quick` + `task_update" not in text
        assert "tausik_task_log" not in text


class TestClaudeMd:
    def test_has_agent_native_estimation_section(self):
        text = _read("CLAUDE.md")
        # The 4096B static cap trim moved the full estimation contract to
        # docs/ru/agent-contract.md. CLAUDE.md must still expose the keyword
        # plus the pointer so the agent can reach the contract.
        assert "estimation" in text.lower()
        assert "agent-contract" in text.lower()

    def test_section_mentions_tool_calls(self):
        text = _read("CLAUDE.md").lower()
        assert "tool call" in text or "tool-call" in text


class TestMcpToolsDescription:
    def test_task_add_description_mentions_tool_calls(self):
        text = _read("harness", "claude", "mcp", "project", "tools.py")
        # Find tausik_task_add block and check its description.
        assert "tausik_task_add" in text
        idx = text.index('"name": "tausik_task_add"')
        block = text[idx : idx + 600]
        assert "TOOL CALLS" in block

    def test_call_budget_description_lists_tiers(self):
        text = _read("harness", "claude", "mcp", "project", "tools.py")
        # All five tier labels should appear in the call_budget description text.
        for label in ("trivial", "light", "moderate", "substantial", "deep"):
            assert label in text, f"missing tier label in tools.py: {label}"

    def test_task_add_advertises_atomic_plan_and_dependency_fields(self):
        text = _read("harness", "claude", "mcp", "project", "tools.py")
        start = text.index('"name": "tausik_task_add"')
        end = text.index('"name": "tausik_task_start"', start)
        block = text[start:end]
        for field in ('"depends_on"', '"plan_steps"', '"rationale"', '"relevant_files"'):
            assert field in block

    def test_mirror_in_sync(self):
        src = _read("harness", "claude", "mcp", "project", "tools.py")
        mirror = _read(".claude", "mcp", "project", "tools.py")
        assert src == mirror, "harness/claude/mcp tools.py and .claude/mcp mirror diverged"

    @pytest.mark.parametrize(
        ("source", "deployed"),
        [
            (
                ("harness", "claude", "mcp", "project", "handlers_task.py"),
                (".claude", "mcp", "project", "handlers_task.py"),
            ),
            (
                ("scripts", "project_cli_task.py"),
                (".claude", "scripts", "project_cli_task.py"),
            ),
            (
                ("scripts", "project_parser_task.py"),
                (".claude", "scripts", "project_parser_task.py"),
            ),
            (
                ("scripts", "service_task_create.py"),
                (".claude", "scripts", "service_task_create.py"),
            ),
        ],
    )
    def test_changed_execution_surface_mirrors_are_exact(self, source, deployed):
        assert _read(*source) == _read(*deployed)
