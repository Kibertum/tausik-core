"""qg2-cannot-close-fileless-task — the third QG-2 scope state.

A task that legitimately touches no files (pure planning, a `tausik decide`,
a premise reformulation) had no honest exit: `task done` blocked on an empty
`relevant_files`, and the class of tasks the framework itself encourages
(convention #251) was un-closeable. `task done --no-file-changes` adds the
third state — provable by git, never by the agent's word.

Coverage:
  - uncommitted_changes(): the git porcelain seam (clean / dirty / rename /
    untracked / pathspec / fail-closed to None).
  - enforce_verify_first(no_file_changes=True): clean scope allows, dirty
    scope blocks, unverifiable git blocks (fail-closed) — the non-vacuity
    proof (AC3): a declaration git cannot back never closes.
  - end-to-end task_done: closes on a clean scope, records the countable
    column, runs no scoped gates; blocks and leaves the column 0 on a dirty
    scope.
  - the plain (no-flag) empty-scope path is unchanged (AC8 regression).
  - the agent-contract doc matches behavior and the stale claim cannot return
    (AC6 / AC7 doc-drift gate).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import verify_git_diff as vgd  # noqa: E402
from gate_verify_first import enforce_verify_first  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _porcelain_runner(stdout: str, *, returncode: int = 0):
    """A subprocess.run stand-in returning canned `git status --porcelain`."""

    def run(cmd, **kwargs):  # noqa: ANN001
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")

    return run


# --- uncommitted_changes: the git seam -------------------------------------


class TestUncommittedChanges:
    def _repo(self, tmp_path: Path) -> Path:
        (tmp_path / ".git").mkdir()  # mirrors changed_files_since test setup
        return tmp_path

    def test_clean_tree_is_empty_list_not_none(self, tmp_path):
        # Empty porcelain output = provably clean. Must be [] (a positive fact),
        # never None (which means "could not check").
        got = vgd.uncommitted_changes(root=str(self._repo(tmp_path)), runner=_porcelain_runner(""))
        assert got == []

    def test_dirty_tree_lists_paths(self, tmp_path):
        out = " M scripts/a.py\n?? scripts/new.py\nA  scripts/staged.py\n"
        got = vgd.uncommitted_changes(root=str(self._repo(tmp_path)), runner=_porcelain_runner(out))
        assert got == ["scripts/a.py", "scripts/new.py", "scripts/staged.py"]

    def test_rename_records_new_path(self, tmp_path):
        out = "R  scripts/old.py -> scripts/new.py\n"
        got = vgd.uncommitted_changes(root=str(self._repo(tmp_path)), runner=_porcelain_runner(out))
        assert got == ["scripts/new.py"]

    def test_pathspec_forwarded_to_git(self, tmp_path):
        captured = {}

        def run(cmd, **kwargs):  # noqa: ANN001
            captured["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        vgd.uncommitted_changes(["docs/", "README.md"], root=str(self._repo(tmp_path)), runner=run)
        assert captured["cmd"][:3] == ["git", "status", "--porcelain"]
        assert captured["cmd"][3:] == ["--", "docs/", "README.md"]

    def test_no_pathspec_scans_whole_tree(self, tmp_path):
        captured = {}

        def run(cmd, **kwargs):  # noqa: ANN001
            captured["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        vgd.uncommitted_changes(root=str(self._repo(tmp_path)), runner=run)
        assert "--" not in captured["cmd"]  # no pathspec separator

    def test_not_a_repo_is_none_not_clean(self, tmp_path):
        # No .git dir → cannot verify → None. Fail-closed: the caller must not
        # read None as "clean".
        assert vgd.uncommitted_changes(root=str(tmp_path), runner=_porcelain_runner("")) is None

    def test_git_nonzero_is_none(self, tmp_path):
        got = vgd.uncommitted_changes(
            root=str(self._repo(tmp_path)), runner=_porcelain_runner("x", returncode=128)
        )
        assert got is None

    def test_git_raises_is_none(self, tmp_path):
        def boom(cmd, **kwargs):  # noqa: ANN001
            raise OSError("git exploded")

        assert vgd.uncommitted_changes(root=str(self._repo(tmp_path)), runner=boom) is None


# --- gate branch: enforce_verify_first(no_file_changes=True) ---------------


def _stub_verify_gates(monkeypatch, *, auto_verify: bool = False):
    """Pretend the project has one verify-trigger gate so the fileless branch
    (which lives after the 'no verify gates configured' early return) is
    reached."""
    from project_config import get_gates_for_trigger as real_for_trigger

    def fake_get_for_trigger(trigger, cfg=None):
        if trigger == "verify":
            return [
                {
                    "name": "pytest",
                    "enabled": True,
                    "trigger": ["verify"],
                    "command": "pytest",
                    "severity": "block",
                }
            ]
        return real_for_trigger(trigger, cfg)

    monkeypatch.setattr(
        "project_config.load_config", lambda: {"task_done": {"auto_verify": auto_verify}}
    )
    monkeypatch.setattr("project_config.get_gates_for_trigger", fake_get_for_trigger)


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    s = ProjectService(be)
    s.epic_add("e", "E")
    s.story_add("e", "s", "S")
    s.task_add("s", "t", "Reformulate premise", goal="Reformulate premise", role="architect")
    s.task_update(
        "t",
        acceptance_criteria="1. premise restated\n2. blocked when the git scope is dirty",
    )
    s.task_start("t")
    s.task_log("t", "AC verified: 1. premise restated ✓ 2. dirty scope blocks ✓")
    return s


class TestFilelessGateBranch:
    def _report(self):
        return {
            "passed": True,
            "results": [],
            "cache_status": None,
            "blocking_failures": [],
            "scope": None,
        }

    def test_clean_scope_allows_close(self, svc, monkeypatch):
        _stub_verify_gates(monkeypatch)
        monkeypatch.setattr(vgd, "uncommitted_changes", lambda *a, **k: [])
        report = self._report()
        enforce_verify_first(svc, report, "t", None, no_file_changes=True)
        assert report["passed"] is True
        assert report["blocking_failures"] == []
        assert any("--no-file-changes verified" in n for n in [svc.be.task_get("t")["notes"] or ""])

    def test_dirty_scope_blocks(self, svc, monkeypatch):
        _stub_verify_gates(monkeypatch)
        monkeypatch.setattr(vgd, "uncommitted_changes", lambda *a, **k: ["scripts/other.py"])
        report = self._report()
        enforce_verify_first(svc, report, "t", None, no_file_changes=True)
        assert report["passed"] is False
        out = report["blocking_failures"][0]["output"]
        assert "uncommitted changes" in out and "scripts/other.py" in out

    def test_unverifiable_git_fails_closed(self, svc, monkeypatch):
        # AC2/AC3: git returns None → the declaration is unbacked → BLOCK.
        # This is the non-vacuity guard: the flag alone can never close a task.
        _stub_verify_gates(monkeypatch)
        monkeypatch.setattr(vgd, "uncommitted_changes", lambda *a, **k: None)
        report = self._report()
        enforce_verify_first(svc, report, "t", None, no_file_changes=True)
        assert report["passed"] is False
        assert "could not verify" in report["blocking_failures"][0]["output"]

    def test_flag_off_still_blocks_empty_scope(self, svc, monkeypatch):
        # AC8 regression: without the flag, an empty scope blocks as before —
        # the fileless path must not weaken the default.
        _stub_verify_gates(monkeypatch)
        # uncommitted_changes must NOT even be consulted on the no-flag path.
        monkeypatch.setattr(
            vgd,
            "uncommitted_changes",
            lambda *a, **k: pytest.fail("git consulted without the flag"),
        )
        report = self._report()
        enforce_verify_first(svc, report, "t", None, no_file_changes=False)
        assert report["passed"] is False
        assert "declares no relevant_files" in report["blocking_failures"][0]["output"]


def _stub_no_verify_gates(monkeypatch):
    """A project with NO verify-trigger gates (registry absent / all disabled)."""
    monkeypatch.setattr("project_config.load_config", lambda: {"task_done": {"auto_verify": False}})
    monkeypatch.setattr("project_config.get_gates_for_trigger", lambda trigger, cfg=None: [])


class TestFilelessProvenEvenWithoutVerifyGates:
    """Regression for defect-fileless-close-fail-open-no-verify-gates: the git
    proof must run BEFORE the no-verify-gates early return, or `--no-file-changes`
    closes a dirty tree and records a flag git never backed."""

    def _report(self):
        return {
            "passed": True,
            "results": [],
            "cache_status": None,
            "blocking_failures": [],
            "scope": None,
        }

    def test_dirty_tree_blocks_with_no_verify_gates(self, svc, monkeypatch):
        # THE FAIL-OPEN: pre-fix this returned early (passed=True) without ever
        # consulting git. Now git must still block a dirty scope.
        _stub_no_verify_gates(monkeypatch)
        monkeypatch.setattr(vgd, "uncommitted_changes", lambda *a, **k: ["scripts/x.py"])
        report = self._report()
        enforce_verify_first(svc, report, "t", None, no_file_changes=True)
        assert report["passed"] is False
        assert "uncommitted changes" in report["blocking_failures"][0]["output"]

    def test_clean_tree_passes_with_no_verify_gates(self, svc, monkeypatch):
        _stub_no_verify_gates(monkeypatch)
        monkeypatch.setattr(vgd, "uncommitted_changes", lambda *a, **k: [])
        report = self._report()
        enforce_verify_first(svc, report, "t", None, no_file_changes=True)
        assert report["passed"] is True
        assert report["blocking_failures"] == []

    def test_unresolvable_project_dir_fails_closed(self, monkeypatch):
        # AC4: a service exposing no tausik_dir must block, not fall back to cwd.
        import types

        _stub_verify_gates(monkeypatch)
        bare = types.SimpleNamespace()  # no tausik_dir attribute
        report = self._report()
        enforce_verify_first(bare, report, "t", None, no_file_changes=True)
        assert report["passed"] is False
        assert "no project directory" in report["blocking_failures"][0]["output"]


# --- end-to-end task_done ---------------------------------------------------


@pytest.mark.verify_first
class TestFilelessTaskDone:
    def test_clean_scope_closes_and_records_column(self, svc, monkeypatch):
        _stub_verify_gates(monkeypatch)
        monkeypatch.setattr(vgd, "uncommitted_changes", lambda *a, **k: [])
        # No scoped gate must run — assert run_gates is never called.
        run_gates = MagicMock(return_value=(True, []))
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=run_gates)}):
            svc.task_done("t", ac_verified=True, no_knowledge=True, no_file_changes=True)
        row = svc.be.task_get("t")
        assert row["status"] == "done"
        assert row["no_file_changes_declared"] == 1
        run_gates.assert_not_called()

    def test_dirty_scope_blocks_and_leaves_column_zero(self, svc, monkeypatch):
        _stub_verify_gates(monkeypatch)
        monkeypatch.setattr(vgd, "uncommitted_changes", lambda *a, **k: ["scripts/x.py"])
        with patch.dict(
            "sys.modules", {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))}
        ):
            with pytest.raises(ServiceError, match="no-file-changes"):
                svc.task_done("t", ac_verified=True, no_knowledge=True, no_file_changes=True)
        row = svc.be.task_get("t")
        assert row["status"] != "done"
        assert row["no_file_changes_declared"] == 0


# --- migration / schema parity ---------------------------------------------


class TestColumnPresence:
    def test_fresh_db_has_column(self, tmp_path):
        be = SQLiteBackend(str(tmp_path / "fresh.db"))
        cols = {r[1] for r in be._conn.execute("PRAGMA table_info(tasks)").fetchall()}
        assert "no_file_changes_declared" in cols


# --- doc-drift gate (AC6 / AC7) --------------------------------------------


class TestContractDocMatchesBehavior:
    CONTRACT = REPO / "docs" / "ru" / "agent-contract.md"

    def test_stale_full_suite_fallback_claim_is_gone(self):
        # The exact behaviour the contract described was removed in #118. If the
        # phrase returns, doc and code have drifted again — fail the suite.
        text = self.CONTRACT.read_text(encoding="utf-8")
        assert "fallback на полный suite остаётся" not in text

    def test_contract_states_the_real_behavior(self):
        text = self.CONTRACT.read_text(encoding="utf-8")
        assert "БЛОКИРУЕТ" in text
        assert "--no-file-changes" in text
        assert "no_file_changes_declared" in text
