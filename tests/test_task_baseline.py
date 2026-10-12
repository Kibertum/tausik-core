"""The scope gate measures a task from a git anchor, not from a clock.

scope-gate-baseline-never-moves-after-first-start (Sortula #49 / core#10,
decision #390). Measured from `started_at`, a long-lived task inherited every
commit made by anybody since, and in a shared dirty tree every task inherited
the whole tree. These tests build a REAL git repository: work already dirty
before the anchor must not count as the task's, and a file the task changes
after it must.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

import task_baseline
import verify_git_diff

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


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
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    for name in ("a.py", "b.py", "c.py"):
        (root / name).write_text(f"{name} = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    (root / "b.py").write_text("b.py = 2  # somebody else's uncommitted work\n", encoding="utf-8")
    return root


def test_work_dirty_before_the_anchor_is_not_the_tasks(repo):
    assert task_baseline.anchor(str(repo), "t") is not None
    (repo / "c.py").write_text("c.py = 2  # the task's own edit\n", encoding="utf-8")
    measured = verify_git_diff.changed_files_since(
        "2000-01-01T00:00:00Z", root=str(repo), task_slug="t"
    )
    assert measured == {"c.py"}


def test_without_an_anchor_the_old_clock_measure_applies(repo):
    """NEGATIVE — never looser: no anchor, the whole dirty tree counts as before."""
    (repo / "c.py").write_text("c.py = 2\n", encoding="utf-8")
    measured = verify_git_diff.changed_files_since(
        "2000-01-01T00:00:00Z", root=str(repo), task_slug="nobody-anchored-me"
    )
    assert {"b.py", "c.py"} <= measured


def test_the_tasks_own_change_is_still_caught_after_a_commit(repo):
    """NEGATIVE — the guarantee holds: committing the edit does not hide it."""
    task_baseline.anchor(str(repo), "t")
    (repo / "a.py").write_text("a.py = 3\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-q", "-m", "task work")
    measured = verify_git_diff.changed_files_since(
        "2000-01-01T00:00:00Z", root=str(repo), task_slug="t"
    )
    assert "a.py" in measured and "b.py" not in measured


class _Journal:
    def __init__(self):
        self.lines: list[str] = []

    def task_append_notes(self, slug, message):
        self.lines.append(message)


def test_a_resume_re_anchors_and_says_so(repo):
    tdir = str(repo / ".tausik")
    journal = _Journal()
    assert task_baseline.on_activation(journal, tdir, "t", first=True) is None
    first = task_baseline.baseline_of(str(repo), "t")
    (repo / "c.py").write_text("c.py = 9\n", encoding="utf-8")
    note = task_baseline.on_activation(journal, tdir, "t", first=False)
    assert note and note.startswith("BASELINE re-anchored on resume: " + first[:12])
    assert journal.lines == [note]
    assert verify_git_diff.changed_files_since("x", root=str(repo), task_slug="t") == set()


def test_release_drops_the_anchor(repo):
    task_baseline.anchor(str(repo), "t")
    task_baseline.release(str(repo / ".tausik"), "t")
    assert task_baseline.baseline_of(str(repo), "t") is None


def test_outside_git_nothing_is_anchored(tmp_path):
    """NEGATIVE — no repository: None everywhere, callers keep the clock."""
    assert task_baseline.anchor(str(tmp_path), "t") is None
    assert (
        task_baseline.on_activation(_Journal(), str(tmp_path / ".tausik"), "t", first=False) is None
    )


def test_the_anchor_does_not_touch_the_working_tree(repo):
    before = (repo / "b.py").read_text(encoding="utf-8")
    task_baseline.anchor(str(repo), "t")
    assert (repo / "b.py").read_text(encoding="utf-8") == before
    assert os.path.exists(repo / ".git" / "refs" / "tausik" / "baseline" / "t")
