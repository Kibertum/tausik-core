"""Smoke test for `tausik skill ...` CLI: help consistency + friendly errors.

Covers v14-skill-cli-help-pass: every help text reads as a noun phrase, every
negative scenario (unknown skill / repo / URL) prints `Error: ...` to stderr
and exits non-zero — no Python traceback in user-facing output.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

# v14b-pytest-fast-lane: every assertion spawns the tausik CLI subprocess.
pytestmark = pytest.mark.slow

REPO = Path(__file__).resolve().parents[1]
PYTHON = REPO / ".tausik" / "venv" / "Scripts" / "python.exe"
if not PYTHON.is_file():
    # Linux/macOS layout
    PYTHON = REPO / ".tausik" / "venv" / "bin" / "python"
PROJECT_PY = REPO / "scripts" / "project.py"


def _run(args: list[str], cwd: Path = REPO) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PYTHON), str(PROJECT_PY), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


class TestSkillHelpConsistency:
    def test_skill_help_lists_subcommands(self):
        r = _run(["skill", "--help"])
        assert r.returncode == 0
        for sub in ("activate", "deactivate", "list", "install", "uninstall", "repo"):
            assert sub in r.stdout, f"`tausik skill --help` missing '{sub}'"

    def test_repo_help_lists_subcommands(self):
        r = _run(["skill", "repo", "--help"])
        assert r.returncode == 0
        for sub in ("add", "remove", "list"):
            assert sub in r.stdout, f"`tausik skill repo --help` missing '{sub}'"


class TestSkillNegativeExitCode:
    """Negative scenarios must print friendly `Error: ...` and exit 1, not a traceback."""

    def test_install_unknown_skill(self, tmp_path):
        r = _run(["skill", "install", "nonexistent-skill-xyz"], cwd=tmp_path)
        assert r.returncode == 1
        assert "Traceback" not in r.stderr
        assert r.stderr.startswith("Error: ")
        assert "nonexistent-skill-xyz" in r.stderr

    def test_repo_add_untrusted_url(self, tmp_path):
        r = _run(["skill", "repo", "add", "https://example.com/foo.git"], cwd=tmp_path)
        assert r.returncode == 1
        assert "Traceback" not in r.stderr
        assert r.stderr.startswith("Error: ")
        assert "--force" in r.stderr  # remediation hint

    def test_activate_unknown_skill(self, tmp_path):
        r = _run(["skill", "activate", "nonexistent-skill-xyz"], cwd=tmp_path)
        assert r.returncode == 1
        assert "Traceback" not in r.stderr
        assert r.stderr.startswith("Error: ")
