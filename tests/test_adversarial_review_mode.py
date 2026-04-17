"""Test that the /review skill has an adversarial critic agent baked in."""

from __future__ import annotations

import os

_BASE = os.path.join(os.path.dirname(__file__), "..")
_CRITIC_PATH = os.path.join(_BASE, "agents", "skills", "review", "agents", "critic.md")
_SKILL_PATH = os.path.join(_BASE, "agents", "skills", "review", "SKILL.md")


class TestCriticAgentFile:
    def test_critic_agent_exists(self):
        assert os.path.exists(_CRITIC_PATH), "critic.md must exist"

    def test_critic_mentions_three_weaknesses(self):
        content = open(_CRITIC_PATH, encoding="utf-8").read().lower()
        assert (
            "3 weaknesses" in content
            or "3 weakness" in content
            or "three weaknesses" in content
        )

    def test_critic_describes_output_format(self):
        content = open(_CRITIC_PATH, encoding="utf-8").read()
        assert "## Critic findings" in content
        assert "[C1]" in content and "[C2]" in content and "[C3]" in content

    def test_critic_says_no_fabrication(self):
        content = open(_CRITIC_PATH, encoding="utf-8").read().lower()
        assert (
            "do not fabricate" in content
            or "not fabricate" in content
            or "stopped rather than invent" in content
        )

    def test_critic_has_stop_condition(self):
        content = open(_CRITIC_PATH, encoding="utf-8").read().lower()
        assert "stop condition" in content


class TestSkillRegistration:
    def test_skill_mentions_critic(self):
        content = open(_SKILL_PATH, encoding="utf-8").read()
        assert "critic" in content.lower()
        assert "critic.md" in content

    def test_skill_says_six_agents(self):
        content = open(_SKILL_PATH, encoding="utf-8").read()
        assert "6 specialized review agents" in content
        assert "6 agents in a **single message**" in content

    def test_skill_agent_table_includes_critic_row(self):
        content = open(_SKILL_PATH, encoding="utf-8").read()
        # All 6 agents must appear in the parallel-launch table
        for agent in (
            "quality",
            "implementation",
            "testing",
            "simplification",
            "documentation",
            "critic",
        ):
            assert f"**{agent}**" in content, (
                f"agent {agent} missing from SKILL.md table"
            )

    def test_adversarial_mode_still_documented(self):
        """The opt-in deep mode should still be explained, now as extra pass."""
        content = open(_SKILL_PATH, encoding="utf-8").read()
        assert "Adversarial Mode" in content
        assert "adversarial" in content.lower()
