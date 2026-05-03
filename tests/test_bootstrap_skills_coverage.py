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
_builtin_skills_dir = os.path.join(_repo_root, "agents", "skills")


def _list_builtin_skills() -> list[str]:
    """All directories under agents/skills/ that contain a SKILL.md."""
    out = []
    for name in sorted(os.listdir(_builtin_skills_dir)):
        if name.startswith(".") or name.startswith("_"):
            continue
        d = os.path.join(_builtin_skills_dir, name)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "SKILL.md")):
            out.append(name)
    return out


def _run_bootstrap(target: str, *extra_args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, _bootstrap, "--project-dir", target, "--ide", "claude", *extra_args],
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
    def test_every_builtin_skill_lands_in_claude_skills(self, tmp_path):
        builtin = _list_builtin_skills()
        assert builtin, "agents/skills/ should contain at least one built-in skill"

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
            f"Built-in source-of-truth in agents/skills/ must always reach the IDE — "
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
        # These come from registry/extension lists, not agents/skills/.
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
