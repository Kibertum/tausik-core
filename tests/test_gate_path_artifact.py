"""A guarded path moves its artifact in the same commit (github#90, 1.10).

Driven in a throwaway git repository: the gate reads the STAGED set, so a
fixture without git would prove nothing about it.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

import gate_outcome
from gate_path_artifact import REASON_NO_PATH_MAP, run_path_artifact_gate

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")

GATE = {"map": [{"paths": ["scripts/**"], "artifacts": ["CHANGELOG.md"]}]}


def _git(root, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root,
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "a.py").write_text("A = 1\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    (tmp_path / "scripts" / "a.py").write_text("A = 2\n", encoding="utf-8")
    _git(tmp_path, "add", "scripts/a.py")
    return tmp_path


def _run(repo, gate=GATE):
    return run_path_artifact_gate(gate, [], root=str(repo))


def test_a_guarded_change_without_its_artifact_blocks(repo):
    out = _run(repo)
    assert out.outcome == gate_outcome.FAILED and "CHANGELOG.md" in out.detail


def test_a_guarded_change_with_its_artifact_passes(repo):
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n- A is 2\n", encoding="utf-8")
    _git(repo, "add", "CHANGELOG.md")
    assert _run(repo).outcome == gate_outcome.PASSED


def test_a_whitespace_only_touch_of_the_artifact_does_not_count(repo):
    """NEGATIVE: a blank line added is not a move."""
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n\n", encoding="utf-8")
    _git(repo, "add", "CHANGELOG.md")
    assert _run(repo).outcome == gate_outcome.FAILED


def test_an_empty_map_is_skipped_out_loud_not_passed(repo):
    """NEGATIVE: nothing guarded is NOT_APPLICABLE with a reason, never PASSED."""
    out = _run(repo, {"map": []})
    assert out.outcome == gate_outcome.NOT_APPLICABLE and out.reason_code == REASON_NO_PATH_MAP


def test_an_unreadable_staged_set_blocks(tmp_path):
    """NEGATIVE: no repository -> COULD_NOT_RUN, which blocks (fail-closed)."""
    out = run_path_artifact_gate(GATE, [], root=str(tmp_path))
    assert out.outcome == gate_outcome.COULD_NOT_RUN


def test_it_guards_nothing_until_a_project_declares_a_map():
    """Off by default in effect: the default map is empty (skipped out loud), and
    a block gate switched off would read as silence to the degeneracy audit."""
    from gate_registry import GATE_REGISTRY

    assert GATE_REGISTRY["path_artifact"].default_config["map"] == []
