"""Tests for `scripts/audit_tracked_files.py` (audit-stale-docs-scope-noise).

Covers:
  AC-1 — the shared git-index helper: happy path, and `None` (not an empty
    set) whenever git cannot answer.
  AC-6 (negative) — audits degrade to a filesystem walk with a stderr
    warning instead of raising when git is unavailable.
  Negative — an empty `git ls-files` listing is treated as "git unavailable",
    never as "the repo has no files" (which would report everything stale).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import audit_stale_docs  # noqa: E402
import audit_tracked_files  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

# Gitignored by .gitignore:84 — the exact false positive this task removes.
INTERNAL_RESEARCH_DIR = "docs/research/_internal/"


class _FakeProc:
    def __init__(self, returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestTrackedFilesHappyPath:
    def test_returns_tracked_paths_of_real_repo(self):
        tracked = audit_tracked_files.tracked_files(REPO)
        assert tracked is not None
        assert "scripts/audit_stale_docs.py" in tracked

    def test_gitignored_paths_absent(self):
        tracked = audit_tracked_files.tracked_files(REPO)
        assert tracked is not None
        assert not any(rel.startswith(INTERNAL_RESEARCH_DIR) for rel in tracked)


class TestTrackedFilesDegradation:
    """`None` means unknown. An empty set would make every audit report the
    whole tree as unreferenced, so the helper never returns one."""

    def test_outside_git_repo_returns_none(self, tmp_path: Path, capsys):
        assert audit_tracked_files.tracked_files(tmp_path) is None
        assert "falling back to filesystem walk" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "proc,reason",
        [
            pytest.param(
                _FakeProc(returncode=128, stderr=b"not a repo"), "exit", id="nonzero_exit"
            ),
            pytest.param(_FakeProc(returncode=0, stdout=b""), "nothing", id="empty_listing"),
            pytest.param(_FakeProc(returncode=0, stdout=b"\0\0"), "nothing", id="only_separators"),
        ],
    )
    def test_unusable_git_output_returns_none(self, monkeypatch, capsys, proc, reason):
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: proc)
        assert audit_tracked_files.tracked_files(REPO) is None
        assert reason in capsys.readouterr().err

    @pytest.mark.parametrize(
        "exc",
        [
            pytest.param(FileNotFoundError("git"), id="git_missing"),
            pytest.param(subprocess.TimeoutExpired("git", 30), id="timeout"),
        ],
    )
    def test_subprocess_failure_returns_none_not_raise(self, monkeypatch, capsys, exc):
        def _boom(*_a, **_k):
            raise exc

        monkeypatch.setattr(subprocess, "run", _boom)
        assert audit_tracked_files.tracked_files(REPO) is None
        assert "falling back to filesystem walk" in capsys.readouterr().err

    def test_warn_false_stays_quiet(self, tmp_path: Path, capsys):
        assert audit_tracked_files.tracked_files(tmp_path, warn=False) is None
        assert capsys.readouterr().err == ""


class TestIsTracked:
    def test_unknown_index_admits_everything(self):
        # None == "git didn't answer" — must not silently drop files.
        assert audit_tracked_files.is_tracked("anything/at/all.md", None)

    @pytest.mark.parametrize(
        "rel,expected",
        [
            pytest.param("docs/en/cli.md", True, id="tracked"),
            pytest.param("docs/research/_internal/x.md", False, id="untracked"),
        ],
    )
    def test_membership(self, rel, expected):
        assert audit_tracked_files.is_tracked(rel, frozenset({"docs/en/cli.md"})) is expected


class TestAuditDegradesGracefully:
    """AC-6: with git unavailable the audit still runs (filesystem walk).

    Patched through the module — a `from ... import tracked_files` in the
    audit would bind the original and this test would measure nothing.
    """

    def test_collect_stale_survives_unavailable_git(self, tmp_path: Path, monkeypatch):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        docs_en = tmp_path / "docs" / "en"
        docs_en.mkdir(parents=True)
        (docs_en / "lonely.md").write_text("nobody links here\n")

        called: list[Path] = []

        def _unavailable(root, **_kwargs):
            called.append(root)
            return None

        monkeypatch.setattr(audit_tracked_files, "tracked_files", _unavailable)

        stale = audit_stale_docs.collect_stale(tmp_path)

        assert called, "audit must consult the shared helper, not call git itself"
        assert "docs/en/lonely.md" in stale


class TestRealRepoHasNoUntrackedCandidates:
    """The invariant this task establishes: an audit candidate is always a
    file the repo actually tracks. A gitignored file references nothing by
    definition, so reporting one is noise that can never be actioned."""

    def test_no_stale_candidate_is_untracked(self):
        tracked = audit_tracked_files.tracked_files(REPO)
        assert tracked is not None
        for rel in audit_stale_docs.collect_stale(REPO):
            assert rel in tracked, f"{rel} is not tracked by git — false positive"

    def test_internal_research_never_reported(self):
        # Convention #176: internal research names must not reach shared reports.
        stale = audit_stale_docs.collect_stale(REPO)
        assert not any(rel.startswith(INTERNAL_RESEARCH_DIR) for rel in stale)

    def test_research_dump_home_excluded(self):
        # docs/research/* is the research home, same as its localized twins.
        stale = audit_stale_docs.collect_stale(REPO)
        assert not any(rel.startswith("docs/research/") for rel in stale)


class TestPositiveControlWithGitAvailable:
    """Keeps the three invariants above from passing vacuously.

    Each of them asserts "X is absent from the output", and on the current
    tree the output is empty — so all three would stay green even if
    `collect_stale` regressed into an always-empty no-op, and the audit
    would silently stop auditing. This pins the other half of the contract:
    with git available, a tracked-but-unreferenced doc IS still reported,
    while a gitignored sibling is not.
    """

    def test_tracked_stale_reported_gitignored_skipped(self, tmp_path: Path):
        def git(*argv: str) -> None:
            subprocess.run(
                ["git", "-C", str(tmp_path), *argv],
                check=True,
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )

        try:
            git("init", "-q")
        except (OSError, subprocess.SubprocessError) as exc:
            pytest.skip(f"git unavailable: {exc}")

        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        (tmp_path / ".gitignore").write_text("docs/research/_internal/\n")
        docs_en = tmp_path / "docs" / "en"
        docs_en.mkdir(parents=True)
        (docs_en / "unreferenced.md").write_text("nothing links here\n")
        internal = tmp_path / "docs" / "research" / "_internal"
        internal.mkdir(parents=True)
        (internal / "local-note.md").write_text("also unreferenced, but local\n")
        git("add", "-A")

        stale = audit_stale_docs.collect_stale(tmp_path)

        assert "docs/en/unreferenced.md" in stale, (
            "audit reported nothing on a tree that genuinely has a stale doc — "
            "the invariant tests would pass vacuously"
        )
        assert not any(rel.startswith("docs/research/_internal/") for rel in stale)
