"""The publication scope rule must be checkable, not habitual.

Decision #257 reduced "what goes outside" to one sentence -- everything git
tracks -- and AC7 of `github-is-the-source-gitlab-is-its-mirror` says a rule that
simple has no excuse for being unenforced. These tests are that enforcement.

Two properties are asserted throughout, and the second is the one that costs
effort:

  1. The rule holds.
  2. The check that says so CAN FAIL. Every promise here is paired with a case
     that breaks it -- a dropped file, an orphan commit, a moved tag, a vanished
     tag, a git call that could not run. A control whose red branch is never
     exercised is indistinguishable from a control that is wired to `True`, and
     this project has already measured three of those (memory #404).

Every repository under test is built here from scratch. Asserting against the
live repository would make the suite depend on today's file list and go red on
work that has nothing to do with publication.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from publication_scope import (  # noqa: E402
    PublicationError,
    base_is_reachable,
    build_publication_commit,
    nothing_dropped,
    published_paths,
    tag_map,
    tags_unmoved,
    tree_of,
)

_TIMEOUT = 60


def _git(cwd, *args) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=_TIMEOUT,
    )


def _write(root, rel: str, text: str) -> None:
    path = os.path.join(str(root), *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _commit(root, message: str) -> str:
    assert _git(root, "add", "-A").returncode == 0
    result = _git(root, "commit", "-m", message)
    assert result.returncode == 0, result.stderr
    return _git(root, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A small repository with a nested path, an ignored file and a tag.

    Deliberately not flat: a rule stated over a flat directory can pass while
    dropping a subdirectory, and `tausik/` -- the tree this rule exists to carry
    outward -- is two levels deep.
    """
    root = tmp_path / "repo"
    root.mkdir()
    assert _git(root, "init", "-b", "main").returncode == 0
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")

    _write(root, "README.md", "# project\n")
    _write(root, "scripts/tool.py", "print('hi')\n")
    _write(root, "tausik/tasks/some-task.md", "task\n")
    _write(root, ".gitignore", "secrets/\n")
    _write(root, "secrets/token.txt", "kept-at-home\n")
    _commit(root, "initial")
    assert _git(root, "tag", "v1.0.0").returncode == 0
    return root


# ---- The rule itself -------------------------------------------------


def test_published_paths_is_exactly_what_git_tracks(repo):
    """No filter, no reordering, no second source of truth."""
    expected = tuple(line for line in _git(repo, "ls-files").stdout.splitlines() if line)
    assert published_paths(str(repo)) == expected


def test_an_ignored_file_is_not_published(repo):
    """The boundary is `.gitignore`, and it is the ONLY boundary.

    The kept file exists on disk throughout -- the point is not that it is
    missing but that being untracked is what keeps it home.
    """
    assert os.path.exists(os.path.join(str(repo), "secrets", "token.txt"))
    assert "secrets/token.txt" not in published_paths(str(repo))


def test_a_new_untracked_file_is_not_published(repo):
    """Not-yet-added is not published either, and needs no rule of its own."""
    _write(repo, "draft.md", "unfinished\n")
    assert "draft.md" not in published_paths(str(repo))


def test_a_nested_tracked_file_is_published(repo):
    """The projection tree is two levels deep; a flat check would miss it."""
    assert "tausik/tasks/some-task.md" in published_paths(str(repo))


# ---- The publication commit -----------------------------------------


def test_publication_commit_publishes_the_source_tree_entire(repo):
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _write(repo, "scripts/tool.py", "print('changed')\n")
    _commit(repo, "local work")

    commit = build_publication_commit(str(repo), base, "publish")
    ok, detail = nothing_dropped(str(repo), commit)
    assert ok, detail
    assert tree_of(str(repo), commit) == tree_of(str(repo), "HEAD")


def test_the_public_head_stays_reachable(repo):
    """AC5 in one assertion: publishing ADDS to the public history."""
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _write(repo, "new.md", "more\n")
    _commit(repo, "local work")

    commit = build_publication_commit(str(repo), base, "publish")
    ok, detail = base_is_reachable(str(repo), base, commit)
    assert ok, detail


def test_the_working_tree_is_untouched_by_building_a_commit(repo):
    """`commit-tree` acts on objects, so an uncommitted edit cannot be lost."""
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _write(repo, "scratch.md", "uncommitted\n")
    before = _git(repo, "status", "--porcelain").stdout

    build_publication_commit(str(repo), base, "publish")

    assert _git(repo, "status", "--porcelain").stdout == before
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == base


# ---- The red branches: each promise must be breakable ----------------


def test_a_dropped_path_is_named_not_merely_counted(repo):
    """A publication that loses a file must say WHICH file.

    Built by publishing an EARLIER tree, which is what a hand-curated snapshot
    amounts to: content that exists locally never reaches the remote, and the
    only visible symptom is a diff nobody ran.
    """
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _write(repo, "tausik/tasks/second-task.md", "task two\n")
    _commit(repo, "local work")

    stale = build_publication_commit(str(repo), base, "publish", source=base)
    ok, detail = nothing_dropped(str(repo), stale)
    assert not ok
    assert "tausik/tasks/second-task.md" in detail


def test_an_orphan_publication_is_refused(repo):
    """The 2026 snapshot was an orphan, and nothing in the repo objected.

    `merge-base --is-ancestor` is what would have objected, so the negative case
    is pinned here: a parentless commit carrying the same tree must NOT pass.
    """
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    tree = tree_of(str(repo), "HEAD")
    orphan = _git(repo, "commit-tree", tree, "-m", "orphan").stdout.strip()

    ok, detail = base_is_reachable(str(repo), base, orphan)
    assert not ok
    assert "NOT an ancestor" in detail


def test_a_moved_tag_is_reported(repo):
    before = tag_map(str(repo))
    _write(repo, "another.md", "x\n")
    _commit(repo, "second")
    assert _git(repo, "tag", "-f", "v1.0.0").returncode == 0

    ok, detail = tags_unmoved(before, tag_map(str(repo)))
    assert not ok
    assert "v1.0.0" in detail


def test_a_vanished_tag_is_reported(repo):
    """A pin that disappears breaks a consumer exactly like one that moved."""
    before = tag_map(str(repo))
    assert _git(repo, "tag", "-d", "v1.0.0").returncode == 0

    ok, detail = tags_unmoved(before, tag_map(str(repo)))
    assert not ok
    assert "vanished" in detail


def test_unchanged_tags_pass(repo):
    """The green branch, so the red ones above mean something."""
    before = tag_map(str(repo))
    _write(repo, "another.md", "x\n")
    _commit(repo, "second")

    ok, detail = tags_unmoved(before, tag_map(str(repo)))
    assert ok, detail


# ---- Could-not-run must not read as passed ---------------------------


def test_a_directory_that_is_not_a_repository_raises(tmp_path):
    """An empty answer from a failed git call must never look like an empty scope.

    Returning `()` here would let a misconfigured checkout report "nothing to
    publish" and pass every check above by having nothing to check.
    """
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    with pytest.raises(PublicationError):
        published_paths(str(outside))


def test_an_unknown_revision_raises(repo):
    with pytest.raises(PublicationError):
        tree_of(str(repo), "definitely-not-a-ref")
