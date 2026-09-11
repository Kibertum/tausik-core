"""Bootstrap skills coverage smoke-test.

Catches the v1.3 regression where 9 of 15 built-in skills (review, brain,
commit, debug, interview, markitdown, ship, skill-test, test) were silently
omitted from .claude/skills/ because copy_skills() iterated only the
config-driven allowlist, ignoring filesystem source-of-truth.

Run: pytest tests/test_bootstrap_skills_coverage.py -v
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

# v14b-pytest-fast-lane: every test here spawns the bootstrap process — ~36-86s each.
pytestmark = pytest.mark.slow

_repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
_bootstrap = os.path.join(_repo_root, "bootstrap", "bootstrap.py")
_builtin_skills_dir = os.path.join(_repo_root, "harness", "skills")


def _list_builtin_skills() -> list[str]:
    """All directories under harness/skills/ that contain a SKILL.md."""
    out = []
    for name in sorted(os.listdir(_builtin_skills_dir)):
        if name.startswith(".") or name.startswith("_"):
            continue
        d = os.path.join(_builtin_skills_dir, name)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "SKILL.md")):
            out.append(name)
    return out


def _run_bootstrap(
    target: str, *extra_args: str, ide: str = "claude"
) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, _bootstrap, "--project-dir", target, "--ide", ide, *extra_args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        env=env,
    )


def _enable_brain_for_test(target: str) -> None:
    """Pre-create .tausik/config.json with brain.enabled=true so the test
    project doesn't trip the v14b-skill-core-cleanup gate that hides brain
    from system-reminder when Notion isn't configured."""
    import json

    cfg_dir = os.path.join(target, ".tausik")
    os.makedirs(cfg_dir, exist_ok=True)
    cfg_path = os.path.join(cfg_dir, "config.json")
    cfg = {"brain": {"enabled": True}}
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)


class TestBootstrapSkillsCoverage:
    def test_i_have_adhd_skill_keeps_evidence_outside_presentation_rule(self):
        skill = os.path.join(_builtin_skills_dir, "i-have-adhd", "SKILL.md")
        text = open(skill, encoding="utf-8").read()

        assert "https://github.com/ayghri/i-have-adhd" in text
        assert "not a verbatim copy" in text
        assert "output-presentation" in text
        assert "signed verify receipts" in text
        assert os.path.isfile(os.path.join(os.path.dirname(skill), "LICENSE"))

    def test_codex_skills_match_claude_apply_overlay_and_preserve_agents(self, tmp_path):
        """Codex receives the same skills, then its session rebuild applies its delta."""
        claude_project = tmp_path / "claude"
        codex_project = tmp_path / "codex"
        _enable_brain_for_test(str(claude_project))
        _enable_brain_for_test(str(codex_project))
        assert _run_bootstrap(str(claude_project)).returncode == 0
        assert _run_bootstrap(str(codex_project), ide="codex").returncode == 0

        claude_skills = claude_project / ".claude" / "skills"
        codex_skills = codex_project / ".codex" / "skills"
        assert {path.name for path in claude_skills.iterdir()} == {
            path.name for path in codex_skills.iterdir()
        }
        assert all((path / "SKILL.md").is_file() for path in codex_skills.iterdir())
        for skills_dir in (claude_skills, codex_skills):
            deployed = skills_dir / "i-have-adhd"
            assert "output-presentation" in (deployed / "SKILL.md").read_text(encoding="utf-8")
            assert "MIT License" in (deployed / "LICENSE").read_text(encoding="utf-8")

        stale_skill = codex_skills / "stale"
        stale_skill.mkdir()
        agent_dir = codex_project / ".codex" / "agents"
        agent_dir.mkdir(exist_ok=True)
        user_agent = agent_dir / "user-agent.toml"
        user_agent.write_text('name = "user-agent"\n', encoding="utf-8")
        assert _run_bootstrap(str(codex_project), ide="codex").returncode == 0
        assert not stale_skill.exists()
        assert user_agent.is_file()

        sys.path.insert(0, os.path.join(_repo_root, "scripts"))
        from skill_profile_rebuild import rebuild_skills

        rebuilt = rebuild_skills(str(codex_skills), ide="codex", force=True)
        assert not rebuilt["errors"]
        start_text = (codex_skills / "start" / "SKILL.md").read_text(encoding="utf-8")
        assert "Use the `tausik_*` MCP tools as the primary interface." in start_text

    def test_every_builtin_skill_lands_in_claude_skills(self, tmp_path):
        builtin = _list_builtin_skills()
        assert builtin, "harness/skills/ should contain at least one built-in skill"

        # Brain is gated on Notion config — enable it so this coverage smoke
        # test still verifies the full source set deploys (v14b-skill-core-cleanup).
        _enable_brain_for_test(str(tmp_path))
        result = _run_bootstrap(str(tmp_path))
        assert result.returncode == 0, f"bootstrap failed: {result.stderr}"

        deployed = tmp_path / ".claude" / "skills"
        assert deployed.exists(), ".claude/skills/ not created"
        deployed_names = {p.name for p in deployed.iterdir() if p.is_dir()}

        missing = [s for s in builtin if s not in deployed_names]
        assert not missing, (
            f"Built-in skills not deployed to .claude/skills/: {missing}. "
            f"Built-in source-of-truth in harness/skills/ must always reach the IDE — "
            f"this is the v1.3 regression that hid /review, /brain, /commit, etc."
        )

    def test_deployed_skills_have_skill_md(self, tmp_path):
        result = _run_bootstrap(str(tmp_path))
        assert result.returncode == 0, f"bootstrap failed: {result.stderr}"

        deployed = tmp_path / ".claude" / "skills"
        empty_dirs = [
            p.name for p in deployed.iterdir() if p.is_dir() and not (p / "SKILL.md").is_file()
        ]
        assert not empty_dirs, f"Deployed skills with no SKILL.md: {empty_dirs}"

    def test_critical_skills_present(self, tmp_path):
        """Hard list — the 12 always-on core skills + brain (conditional).

        Workflow primitives: start/end/checkpoint (session), plan/task/ship/
        commit (task lifecycle), review/test/debug (quality), explore/
        interview (SENAR primitives). Brain (cross-project knowledge UI)
        is gated on Notion config since v14b-skill-core-cleanup — enable
        it explicitly so this regression test still covers brain deployment.
        """
        critical = {
            "review",
            "commit",
            "debug",
            "interview",
            "ship",
            "test",
            "start",
            "end",
            "task",
            "plan",
            "checkpoint",
            "explore",
            "brain",
            "i-have-adhd",
        }
        _enable_brain_for_test(str(tmp_path))
        result = _run_bootstrap(str(tmp_path))
        assert result.returncode == 0, f"bootstrap failed: {result.stderr}"

        deployed = tmp_path / ".claude" / "skills"
        deployed_names = {p.name for p in deployed.iterdir() if p.is_dir()}
        missing = critical - deployed_names
        assert not missing, f"Critical skills missing after bootstrap: {sorted(missing)}"

    def test_external_skills_coexist(self, tmp_path):
        """Built-in deploy must not strip registry/external skills WHEN they
        are explicitly opted in via --include-official (v14b-skill-core-cleanup
        made registry stubs opt-in to cut system-reminder budget by ~−1k/turn).
        """
        result = _run_bootstrap(str(tmp_path), "--include-official")
        assert result.returncode == 0, f"bootstrap failed: {result.stderr}"

        deployed = tmp_path / ".claude" / "skills"
        deployed_names = {p.name for p in deployed.iterdir() if p.is_dir()}
        # These come from registry/extension lists, not harness/skills/.
        external_examples = {"audit", "init", "diff", "docs"}
        present = external_examples & deployed_names
        assert present, (
            "External/registry skills appear to have been stripped — "
            f"expected at least one of {sorted(external_examples)}, got none. "
            f"Built-in force-include must not break external skill resolution."
        )

    def test_default_excludes_official_stubs(self, tmp_path):
        """v14b-skill-core-cleanup negative scenario: without --include-official,
        registry skills (audit/diff/docs/jira/...) must NOT appear in the
        deployed set. Only built-in source skills + explicitly installed.
        """
        result = _run_bootstrap(str(tmp_path))
        assert result.returncode == 0, f"bootstrap failed: {result.stderr}"

        deployed = tmp_path / ".claude" / "skills"
        deployed_names = {p.name for p in deployed.iterdir() if p.is_dir()}
        # These come strictly from skills-official/registry.json — should NOT
        # be present without --include-official.
        registry_only = {"audit", "jira", "presale", "bitrix24", "sentry", "ultra"}
        leaked = registry_only & deployed_names
        assert not leaked, (
            f"Registry stubs leaked into default deploy: {sorted(leaked)}. "
            "Default since v1.4 must be source-only — opt in via --include-official."
        )

    def test_brain_skipped_without_notion_config(self, tmp_path):
        """v14b-skill-core-cleanup negative: brain stays in source but is NOT
        deployed when the project has no .tausik/config.json brain.enabled."""
        result = _run_bootstrap(str(tmp_path))
        assert result.returncode == 0, f"bootstrap failed: {result.stderr}"
        deployed = tmp_path / ".claude" / "skills"
        deployed_names = {p.name for p in deployed.iterdir() if p.is_dir()}
        assert "brain" not in deployed_names, (
            "brain leaked into default deploy without Notion config — gating broken."
        )

    def test_brain_included_with_notion_config(self, tmp_path):
        """v14b-skill-core-cleanup positive: brain deploys when brain.enabled
        is set in .tausik/config.json (matches `tausik brain init` outcome)."""
        _enable_brain_for_test(str(tmp_path))
        result = _run_bootstrap(str(tmp_path))
        assert result.returncode == 0, f"bootstrap failed: {result.stderr}"
        deployed = tmp_path / ".claude" / "skills"
        deployed_names = {p.name for p in deployed.iterdir() if p.is_dir()}
        assert "brain" in deployed_names, (
            "brain not deployed even with brain.enabled=true — gating logic broken."
        )

    def test_corrupt_config_does_not_crash(self, tmp_path):
        """v14b-skill-core-cleanup negative: missing/corrupt .tausik/config.json
        falls back to brain disabled (no crash, no deploy)."""
        cfg_dir = tmp_path / ".tausik"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text("{not valid json")
        result = _run_bootstrap(str(tmp_path))
        assert result.returncode == 0, f"bootstrap crashed on corrupt config: {result.stderr}"
        deployed = tmp_path / ".claude" / "skills"
        deployed_names = {p.name for p in deployed.iterdir() if p.is_dir()}
        assert "brain" not in deployed_names, (
            "brain leaked despite corrupt config — fallback should treat as disabled."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
