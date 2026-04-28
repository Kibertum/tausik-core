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

_repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
_bootstrap = os.path.join(_repo_root, "bootstrap", "bootstrap.py")
_builtin_skills_dir = os.path.join(_repo_root, "agents", "skills")


def _list_builtin_skills() -> list[str]:
    """All directories under agents/skills/ that contain a SKILL.md."""
    out = []
    for name in sorted(os.listdir(_builtin_skills_dir)):
        d = os.path.join(_builtin_skills_dir, name)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "SKILL.md")):
            out.append(name)
    return out


def _run_bootstrap(target: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, _bootstrap, "--project-dir", target, "--ide", "claude"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        env=env,
    )


class TestBootstrapSkillsCoverage:
    def test_every_builtin_skill_lands_in_claude_skills(self, tmp_path):
        builtin = _list_builtin_skills()
        assert builtin, "agents/skills/ should contain at least one built-in skill"

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
            p.name
            for p in deployed.iterdir()
            if p.is_dir() and not (p / "SKILL.md").is_file()
        ]
        assert not empty_dirs, f"Deployed skills with no SKILL.md: {empty_dirs}"

    def test_critical_skills_present(self, tmp_path):
        """Hard list — the 13 core skills required for any TAUSIK project.

        Workflow primitives: start/end/checkpoint (session), plan/task/ship/
        commit (task lifecycle), review/test/debug (quality), explore/
        interview (SENAR primitives), brain (cross-project knowledge UI).

        v1.3 vendor split: markitdown, zero-defect, skill-test moved to
        skills-official/ — opt-in / niche / meta skills not required for
        baseline operation. brain stays core because cross-project memory
        is a v1.3 headline feature.
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
        result = _run_bootstrap(str(tmp_path))
        assert result.returncode == 0, f"bootstrap failed: {result.stderr}"

        deployed = tmp_path / ".claude" / "skills"
        deployed_names = {p.name for p in deployed.iterdir() if p.is_dir()}
        missing = critical - deployed_names
        assert not missing, (
            f"Critical skills missing after bootstrap: {sorted(missing)}"
        )

    def test_external_skills_coexist(self, tmp_path):
        """Built-in deploy must not strip registry/external skills (audit, init, etc)."""
        result = _run_bootstrap(str(tmp_path))
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
