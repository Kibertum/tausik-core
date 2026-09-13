"""The public snapshot is the tracked tree minus ONE declared exclusion list (decision #368).

`test_publication_scope.py` holds the older rule — "everything git tracks is
published" — for the module that still states it. This file holds what changed
on top of it for the PUBLIC line: the exclusion list is one constant, the
filtered tree is built from objects without touching the working copy, the
snapshot commit goes on top of the public head and never replaces it, and
"GitLab is identical to GitHub" is a tree comparison a machine performs, with
the differing paths named when it fails. The negatives are the point: a
snapshot that lost a file, a snapshot that carries a file the filter would
drop, a parent that is not a commit.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(_ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import publication_snapshot as snap  # noqa: E402
from conftest import DORMANT_ON_PUBLIC_SNAPSHOT, IS_PUBLIC_SNAPSHOT  # noqa: E402
from publication_scope import PublicationError, base_is_reachable  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/publication_snapshot.py", "tausik/"]


def _git(cwd, *args) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _write(root, rel: str, text: str) -> None:
    path = os.path.join(str(root), *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _commit(root, message: str) -> str:
    assert _git(root, "add", "-A").returncode == 0
    r = _git(root, "commit", "-m", message)
    assert r.returncode == 0, r.stderr
    return _git(root, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A tree shaped like this project's: code, docs, the ratchet JSONs, the
    state projection, the three internal files, and an older public head."""
    root = tmp_path / "repo"
    root.mkdir()
    assert _git(root, "init", "-b", "main").returncode == 0
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _write(root, "README.md", "# project\n")
    _write(root, "scripts/tool.py", "print('hi')\n")
    _write(root, "docs/en/x.md", "x\n")
    _write(root, "tausik/gates.json", "{}\n")
    _write(root, "tausik/policy.json", "{}\n")
    _write(root, "tausik/tasks/some-task.md", "task\n")
    _write(root, "tausik/decisions/d1.md", "decision\n")
    _write(root, "tausik/memory/m1.md", "memory\n")
    _write(root, "TODO.md", "todo\n")
    _write(root, "TAUSIK-plan-1.9.md", "plan\n")
    _write(root, ".gitlab-ci.yml", "stages: []\n")
    public_head = _commit(root, "public head")
    _write(root, "scripts/tool.py", "print('hi again')\n")
    _write(root, "tausik/tasks/other-task.md", "task 2\n")
    _commit(root, "development")
    return root, public_head


def _tree_paths(root, tree: str) -> set[str]:
    return set(_git(root, "ls-tree", "-r", "--name-only", tree).stdout.split())


class TestTheExclusionListIsOneDeclaration:
    def test_the_projection_and_the_internal_files_stay_behind(self, repo):
        root, _ = repo
        kept, left = snap.snapshot_paths(str(root), "HEAD")
        assert set(left) == {
            "tausik/tasks/some-task.md",
            "tausik/tasks/other-task.md",
            "tausik/decisions/d1.md",
            "tausik/memory/m1.md",
            "TODO.md",
            "TAUSIK-plan-1.9.md",
            ".gitlab-ci.yml",
        }
        assert {
            "tausik/gates.json",
            "tausik/policy.json",
            "scripts/tool.py",
            "docs/en/x.md",
        } <= set(kept)

    def test_the_rules_are_the_ones_decision_368_named(self):
        """The list is read by the release procedure and quoted in publishing.md;
        a silent widening or narrowing must show up as a test edit."""
        assert snap.EXCLUDED_FROM_PUBLIC_SNAPSHOT == (
            "tausik/tasks/",
            "tausik/stories/",
            "tausik/epics/",
            "tausik/decisions/",
            "tausik/memory/",
            "tausik/graph-snapshots/",
            "TODO.md",
            "TAUSIK-plan-1.9.md",
            ".gitlab-ci.yml",
        )

    def test_a_directory_rule_is_a_prefix_and_a_file_rule_is_exact(self):
        assert snap.is_excluded("tausik/tasks/x.md")
        assert snap.is_excluded("tausik\\tasks\\x.md")
        assert not snap.is_excluded("tausik/gates.json")
        assert snap.is_excluded("TODO.md")
        assert not snap.is_excluded("docs/TODO.md")
        assert not snap.is_excluded("TODO.md.bak")


class TestTheSnapshotIsBuiltFromObjects:
    def test_the_filtered_tree_holds_exactly_the_kept_paths(self, repo):
        root, _ = repo
        tree = snap.snapshot_tree(str(root), "HEAD")
        kept, _ = snap.snapshot_paths(str(root), "HEAD")
        assert _tree_paths(root, tree) == set(kept)

    def test_the_working_tree_index_and_branch_are_untouched(self, repo):
        root, public_head = repo
        _write(root, "scripts/tool.py", "print('uncommitted edit')\n")
        before_head = _git(root, "rev-parse", "HEAD").stdout.strip()
        commit = snap.build_snapshot_commit(str(root), public_head, "snapshot")
        assert _git(root, "rev-parse", "HEAD").stdout.strip() == before_head
        assert _git(root, "status", "--porcelain").stdout.strip() == "M scripts/tool.py"
        assert (
            "print('uncommitted edit')"
            in open(root / "scripts" / "tool.py", encoding="utf-8").read()
        )
        assert commit and len(commit) == 40

    def test_the_snapshot_sits_on_top_of_the_public_head(self, repo):
        root, public_head = repo
        commit = snap.build_snapshot_commit(str(root), public_head, "snapshot")
        ok, why = base_is_reachable(str(root), public_head, commit)
        assert ok, why
        assert _git(root, "rev-parse", f"{commit}^").stdout.strip() == public_head


class TestIdenticalIsATreeComparison:
    def test_a_faithful_snapshot_matches(self, repo):
        root, public_head = repo
        commit = snap.build_snapshot_commit(str(root), public_head, "snapshot")
        ok, why = snap.snapshot_matches(str(root), commit, "HEAD")
        assert ok, why

    def test_a_snapshot_that_lost_a_file_is_refused_by_name(self, repo):
        """Negative: the filtered tree minus one file is not the snapshot."""
        root, public_head = repo
        commit = snap.build_snapshot_commit(str(root), public_head, "snapshot")
        # Build a rival: the same tree without docs/en/x.md.
        env = {**os.environ, "GIT_INDEX_FILE": str(root / ".rival.idx")}
        assert (
            subprocess.run(
                ["git", "read-tree", f"{commit}^{{tree}}"], cwd=str(root), env=env
            ).returncode
            == 0
        )
        assert (
            subprocess.run(
                ["git", "rm", "--cached", "-q", "docs/en/x.md"], cwd=str(root), env=env
            ).returncode
            == 0
        )
        rival_tree = subprocess.run(
            ["git", "write-tree"],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        rival = _git(
            root, "commit-tree", rival_tree, "-p", public_head, "-m", "rival"
        ).stdout.strip()
        ok, why = snap.snapshot_matches(str(root), rival, "HEAD")
        assert not ok
        assert "D" + chr(9) + "docs/en/x.md" in why, why

    def test_a_snapshot_that_carries_the_projection_is_refused_by_name(self, repo):
        """Negative the other way: the whole tree published as before #368."""
        root, public_head = repo
        whole = _git(
            root, "commit-tree", "HEAD^{tree}", "-p", public_head, "-m", "whole"
        ).stdout.strip()
        ok, why = snap.snapshot_matches(str(root), whole, "HEAD")
        assert not ok
        assert "tausik/tasks/some-task.md" in why and "TODO.md" in why


class TestRefusalsAreLoud:
    def test_a_parent_that_is_not_a_commit_raises(self, repo):
        root, _ = repo
        with pytest.raises(PublicationError):
            snap.build_snapshot_commit(str(root), "0000000000000000000000000000000000000000", "x")

    def test_an_unknown_source_raises(self, repo):
        root, _ = repo
        with pytest.raises(PublicationError):
            snap.snapshot_tree(str(root), "no-such-ref")


class TestTheLiveTree:
    """The real repository: the ratchet JSONs travel, the projection does not,
    and the two leak classes the publication guard declares as a remainder are
    ZERO on the snapshot — the remainder lives in what stays behind."""

    def test_the_ratchet_files_are_kept_and_the_projection_is_not(self):
        if IS_PUBLIC_SNAPSHOT:
            pytest.skip(DORMANT_ON_PUBLIC_SNAPSHOT)
        kept, left = snap.snapshot_paths(_ROOT, "HEAD")
        assert {"tausik/gates.json", "tausik/policy.json", "tausik/published_tags.json"} <= set(
            kept
        )
        assert not any(p.startswith("tausik/tasks/") for p in kept)
        assert any(p.startswith("tausik/tasks/") for p in left)
        assert "TAUSIK-plan-1.9.md" in left and ".gitlab-ci.yml" in left and "TODO.md" in left

    def test_no_leak_class_survives_on_the_snapshot(self):
        """Over the WORKING tree restricted to the snapshot set, so the ratchet
        judges the tree about to be committed (the CLI's `leaks_in_snapshot`
        reads a revision's blobs, which is right for a snapshot of a commit and
        wrong for a gate that runs before the commit exists)."""
        import re

        BS = chr(92)
        classes = {
            "internal host": re.compile("gitlab" + BS + ".yumash" + BS + ".ru", re.I),
            "dev-machine path": re.compile("[Dd]:[" + BS + BS + "/]{1,2}Work", re.I),
        }
        kept, _ = snap.snapshot_paths(_ROOT, "HEAD")
        hits: dict[str, list[str]] = {name: [] for name in classes}
        for rel in kept:
            if rel in snap.MAY_DESCRIBE_LEAKS:
                continue
            try:
                text = open(os.path.join(_ROOT, rel), encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            for name, rx in classes.items():
                if rx.search(text):
                    hits[name].append(rel)
        assert not any(hits.values()), hits
