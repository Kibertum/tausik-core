"""v15mr-phase-surfaces: phase hints surfaced in banner + plan/explore skills."""

from __future__ import annotations

import os

import pytest

from model_routing import format_task_start_banner

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _exists(*parts: str) -> bool:
    return os.path.exists(os.path.join(ROOT, *parts))


# --- AC1: task_start banner routes through the matrix at phase=implement ------


class TestBannerPhase:
    def test_default_phase_is_implement_via_matrix(self):
        # implement/simple -> Sonnet (matrix floor); no explicit phase passed.
        out = format_task_start_banner(complexity="simple", active_model="claude-sonnet-4-6")
        assert "Sonnet 4.6" in out
        assert "✓ model match" in out

    def test_planning_phase_recommends_fable(self):
        out = format_task_start_banner(
            complexity="simple", phase="planning", active_model="claude-fable-5"
        )
        assert "Fable 5" in out
        assert "✓ model match" in out

    def test_research_simple_recommends_haiku(self):
        out = format_task_start_banner(
            complexity="simple", phase="research", active_model="claude-haiku-4-5"
        )
        assert "Haiku 4.5" in out
        assert "✓ model match" in out


# --- AC3: negative — unavailable/empty transcript -> info verdict, no error ---


class TestBannerNegative:
    def test_empty_transcript_path_yields_unknown_no_error(self):
        out = format_task_start_banner(complexity="medium", transcript_path="", active_model=None)
        assert "active model unknown" in out
        assert "MISMATCH" not in out
        assert "Model recommendation:" in out

    def test_missing_transcript_path_yields_unknown(self, tmp_path):
        out = format_task_start_banner(
            complexity="medium",
            transcript_path=str(tmp_path / "absent.jsonl"),
            active_model=None,
        )
        assert "active model unknown" in out
        assert "MISMATCH" not in out


# --- AC2: plan/explore SKILL.md sources carry the phase model-hint ------------


class TestSkillSources:
    def test_plan_skill_has_planning_hint(self):
        text = _read("harness", "skills", "plan", "SKILL.md")
        assert "phase=planning" in text
        assert "Fable 5" in text
        assert "Opus 4.8" in text

    def test_explore_skill_has_research_hint(self):
        text = _read("harness", "skills", "explore", "SKILL.md")
        assert "phase=research" in text
        assert "Haiku 4.5" in text


# --- AC4: bootstrap rebuilds the deployed skills without dropping the hint ----


class TestDeployedSkillParity:
    """The .claude copy is profile-merged, not byte-identical, so assert the
    hint TEXT propagated rather than full equality. Skips when .claude/ is not
    populated (e.g. a fresh checkout before bootstrap)."""

    def test_deployed_plan_skill_carries_hint(self):
        if not _exists(".claude", "skills", "plan", "SKILL.md"):
            pytest.skip(".claude/skills not deployed (run bootstrap)")
        text = _read(".claude", "skills", "plan", "SKILL.md")
        assert "phase=planning" in text
        assert "Fable 5" in text

    def test_deployed_explore_skill_carries_hint(self):
        if not _exists(".claude", "skills", "explore", "SKILL.md"):
            pytest.skip(".claude/skills not deployed (run bootstrap)")
        text = _read(".claude", "skills", "explore", "SKILL.md")
        assert "phase=research" in text
        assert "Haiku 4.5" in text
