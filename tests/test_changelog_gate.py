"""changelog-continuous-gate — the continuous-CHANGELOG QG-2 gate.

Convention #275 (every task updates CHANGELOG.md + its mirror CHANGELOG.ru.md)
made mechanical: `task done` blocks unless git shows a real changelog entry in
every configured file. Mechanism generic, policy configured — the requirement
is read from config.task_done.changelog_gate, disabled by default so the
framework never blocks a project that keeps no changelog.

s129-review-fixes reshaped three of the gate's answers, and the tests follow:

  * CONTENT, not byte-dirtiness. The first cut asked git "did these bytes
    change", which a single appended blank line satisfies. `TestRealGit`
    exercises that against a REAL repository rather than a stubbed git — the
    hole existed precisely because every test stubbed the layer that held it
    (convention #268).
  * A commit made DURING the task counts. `/ship` commits at step 7 and closes
    at step 8, so an uncommitted-only rule blocked the framework's own
    canonical close path and left `--no-changelog` as the sole way through.
  * A malformed config BLOCKS instead of silently disabling the gate: a policy
    that cannot be read is unknown, not off (Decision #157).

Coverage:
  - _read_changelog_gate_config: absent → silently off; valid → (enabled,
    files); malformed shapes → an error string the caller fails closed on.
  - enforce_changelog: disabled → no-op; entries present → allow + note; a
    missing entry → block naming it + the flag; git None → fail-closed; no
    project dir → fail-closed; broken config → fail-closed; --no-changelog →
    skip + countable bypass event.
  - files_with_substantive_additions against real git: whitespace-only edit
    does NOT pass, real edit does, committed-during-task passes via `since`,
    untracked file counts, and a linked worktree (where `.git` is a FILE) is
    still recognised as a repository.
  - fail-then-pass end-to-end via _run_quality_gates_report wiring (AC4).
  - docs/ru/agent-contract.md documents the gate + flag (AC5 doc-drift guard).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import gate_changelog as gc  # noqa: E402
import verify_git_diff as vgd  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]


# --- config reader ----------------------------------------------------------


class TestReadConfig:
    def _patch_cfg(self, monkeypatch, cfg):
        monkeypatch.setattr("project_config.load_config", lambda *a, **k: cfg)

    def test_absent_block_is_silently_off(self, monkeypatch):
        """Never adopted → disabled, and NOT an error: opt-in means silence."""
        self._patch_cfg(monkeypatch, {})
        assert gc._read_changelog_gate_config() == (False, [], None)

    def test_enabled_with_explicit_files(self, monkeypatch):
        self._patch_cfg(
            monkeypatch,
            {"task_done": {"changelog_gate": {"enabled": True, "files": ["A.md", "B.md"]}}},
        )
        assert gc._read_changelog_gate_config() == (True, ["A.md", "B.md"], None)

    def test_enabled_without_files_uses_defaults(self, monkeypatch):
        self._patch_cfg(monkeypatch, {"task_done": {"changelog_gate": {"enabled": True}}})
        enabled, files, err = gc._read_changelog_gate_config()
        assert (enabled, err) == (True, None)
        assert files == gc._DEFAULT_CHANGELOG_FILES

    def test_empty_file_list_falls_back_to_defaults(self, monkeypatch):
        self._patch_cfg(
            monkeypatch, {"task_done": {"changelog_gate": {"enabled": True, "files": []}}}
        )
        _, files, err = gc._read_changelog_gate_config()
        assert err is None
        assert files == gc._DEFAULT_CHANGELOG_FILES

    def test_tausik_dir_is_forwarded_to_load_config(self, monkeypatch):
        """Policy is read for the project the gate speaks for, not the cwd
        (memory #265 / mcp-config-read-paths)."""
        seen: list = []

        def _spy(tausik_dir=None):
            seen.append(tausik_dir)
            return {"task_done": {"changelog_gate": {"enabled": True}}}

        monkeypatch.setattr("project_config.load_config", _spy)
        gc._read_changelog_gate_config("/somewhere/.tausik")
        assert seen == ["/somewhere/.tausik"]

    # --- malformed shapes: an ERROR, never a silent off ---------------------

    @pytest.mark.parametrize(
        "cfg,needle",
        [
            ({"task_done": {"changelog_gate": "nope"}}, "must be an object"),
            ({"task_done": {"changelog_gate": {"enabled": "false"}}}, "true or false"),
            ({"task_done": {"changelog_gate": {"enabled": 1}}}, "true or false"),
            (
                {"task_done": {"changelog_gate": {"enabled": True, "files": "CHANGELOG.md"}}},
                "must be a list",
            ),
            (
                {"task_done": {"changelog_gate": {"enabled": True, "files": ["A.md", 3]}}},
                "must be a list",
            ),
        ],
    )
    def test_malformed_shape_reports_error(self, monkeypatch, cfg, needle):
        self._patch_cfg(monkeypatch, cfg)
        enabled, _, err = gc._read_changelog_gate_config()
        assert enabled is False
        assert err and needle in err

    def test_config_load_raises_reports_error(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("bad config")

        monkeypatch.setattr("project_config.load_config", boom)
        _, _, err = gc._read_changelog_gate_config()
        assert err and "RuntimeError" in err

    def test_real_true_enables(self, monkeypatch):
        self._patch_cfg(monkeypatch, {"task_done": {"changelog_gate": {"enabled": True}}})
        assert gc._read_changelog_gate_config()[0] is True


# --- enforce_changelog: the gate --------------------------------------------


def _enable(monkeypatch, files=("CHANGELOG.md", "CHANGELOG.ru.md")):
    monkeypatch.setattr(
        gc, "_read_changelog_gate_config", lambda *a, **k: (True, [str(f) for f in files], None)
    )


def _found(monkeypatch, paths):
    """Stub the content-aware git probe with what it would have found."""
    monkeypatch.setattr(
        vgd,
        "files_with_substantive_additions",
        lambda *a, **k: paths if paths is None else set(paths),
    )


def _report():
    return {"passed": True, "blocking_failures": []}


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    s = ProjectService(be)
    s.epic_add("e", "E")
    s.story_add("e", "s", "S")
    s.task_add("s", "t", "A behaviour change", goal="Change behaviour", role="developer")
    s.task_update(
        "t",
        acceptance_criteria="1. behaviour changed\n2. blocked when changelog entry missing",
    )
    s.task_start("t")
    return s


class TestEnforceChangelog:
    def test_disabled_is_noop(self, svc, monkeypatch):
        monkeypatch.setattr(gc, "_read_changelog_gate_config", lambda *a, **k: (False, [], None))
        # Even a None from git (unverifiable) must NOT block when disabled.
        _found(monkeypatch, None)
        report = _report()
        gc.enforce_changelog(svc, report, "t")
        assert report["passed"] is True
        assert report["blocking_failures"] == []

    def test_broken_config_fails_closed(self, svc, monkeypatch):
        """A policy that cannot be read is unknown, not off. The first cut fell
        open here, justified by a `tausik doctor` check that does not exist."""
        monkeypatch.setattr(
            gc,
            "_read_changelog_gate_config",
            lambda *a, **k: (False, [], "`task_done.changelog_gate.enabled` must be true or false"),
        )
        report = _report()
        gc.enforce_changelog(svc, report, "t")
        assert report["passed"] is False
        out = report["blocking_failures"][0]["output"]
        assert "unreadable" in out and "unknown, not off" in out

    def test_both_files_written_allows(self, svc, monkeypatch):
        _enable(monkeypatch)
        _found(monkeypatch, ["CHANGELOG.md", "CHANGELOG.ru.md"])
        report = _report()
        gc.enforce_changelog(svc, report, "t")
        assert report["passed"] is True
        assert report["blocking_failures"] == []
        assert "Changelog gate: verified" in (svc.be.task_get("t")["notes"] or "")

    def test_one_file_missing_blocks_naming_it(self, svc, monkeypatch):
        _enable(monkeypatch)
        # Only the English changelog gained text — the mirror is missing.
        _found(monkeypatch, ["CHANGELOG.md"])
        report = _report()
        gc.enforce_changelog(svc, report, "t")
        assert report["passed"] is False
        out = report["blocking_failures"][0]["output"]
        assert "in: CHANGELOG.ru.md" in out
        # the message must teach WHY a dirty-but-empty edit failed
        assert "whitespace-only" in out
        assert "--no-changelog" in report["blocking_failures"][0]["remediation"]

    def test_neither_file_written_blocks_naming_both(self, svc, monkeypatch):
        _enable(monkeypatch)
        _found(monkeypatch, [])
        report = _report()
        gc.enforce_changelog(svc, report, "t")
        assert report["passed"] is False
        out = report["blocking_failures"][0]["output"]
        assert "CHANGELOG.md" in out and "CHANGELOG.ru.md" in out

    def test_git_none_fails_closed(self, svc, monkeypatch):
        _enable(monkeypatch)
        _found(monkeypatch, None)
        report = _report()
        gc.enforce_changelog(svc, report, "t")
        assert report["passed"] is False
        assert "could not verify" in report["blocking_failures"][0]["output"]

    def test_no_project_dir_fails_closed(self, monkeypatch):
        _enable(monkeypatch)
        # A service that exposes no callable tausik_dir → cannot scope git.
        fake = MagicMock(spec=[])  # no attributes at all
        report = _report()
        gc.enforce_changelog(fake, report, "t")
        assert report["passed"] is False
        assert "no " in report["blocking_failures"][0]["output"].lower()

    def test_task_started_at_is_passed_as_since(self, svc, monkeypatch):
        """Commits made during the task must be visible to the probe — the
        `/ship` ordering (commit, then close) depends on it."""
        _enable(monkeypatch)
        seen: dict = {}

        def _probe(files, *, root=None, since=None, **k):
            seen["since"] = since
            return set(files)

        monkeypatch.setattr(vgd, "files_with_substantive_additions", _probe)
        gc.enforce_changelog(svc, _report(), "t")
        assert seen["since"] == svc.be.task_get("t")["started_at"]

    def test_no_changelog_flag_skips_and_logs_bypass(self, svc, monkeypatch):
        _enable(monkeypatch)

        # git must NOT even be consulted on the exception path.
        def _boom(*a, **k):
            raise AssertionError("git must not run under --no-changelog")

        monkeypatch.setattr(vgd, "files_with_substantive_additions", _boom)
        report = _report()
        gc.enforce_changelog(svc, report, "t", no_changelog=True)
        assert report["passed"] is True
        assert report["blocking_failures"] == []
        # countable bypass event recorded (l26-bypass-telemetry)
        events = svc.be._conn.execute(
            "SELECT action FROM events WHERE entity_id = 't' AND action = 'bypass_changelog_gate'"
        ).fetchall()
        assert len(events) == 1


# --- the content probe, against a REAL repository ---------------------------


# The seed commit is backdated far outside every test's `since` window, so a
# window that must see ONLY the commits a test makes cannot accidentally sweep
# the fixture's own content in — the bug that first showed up here as a green
# whitespace test.
_SEED_DATE = "2020-01-01T00:00:00+0000"
_SINCE_AFTER_SEED = "2021-01-01T00:00:00Z"


def _git(repo: Path, *args: str, date: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    return subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "user.name=T",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )


@pytest.fixture
def repo(tmp_path):
    """A real git repo with a committed CHANGELOG.md — no git stubbing.

    The whitespace hole survived twenty tests because every one of them stubbed
    the git layer that held it (convention #268).
    """
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    (r / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "seed", date=_SEED_DATE)
    return r


@pytest.mark.skipif(not __import__("shutil").which("git"), reason="git not on PATH")
class TestRealGit:
    def test_whitespace_only_edit_does_not_count(self, repo):
        with open(repo / "CHANGELOG.md", "a", encoding="utf-8") as fh:
            fh.write("\n   \n\t\n")
        assert vgd.files_with_substantive_additions(["CHANGELOG.md"], root=str(repo)) == set()

    def test_real_entry_counts(self, repo):
        with open(repo / "CHANGELOG.md", "a", encoding="utf-8") as fh:
            fh.write("\n### A real entry\n")
        assert vgd.files_with_substantive_additions(["CHANGELOG.md"], root=str(repo)) == {
            "CHANGELOG.md"
        }

    def test_staged_entry_counts(self, repo):
        with open(repo / "CHANGELOG.md", "a", encoding="utf-8") as fh:
            fh.write("\n### Staged entry\n")
        _git(repo, "add", "CHANGELOG.md")
        assert vgd.files_with_substantive_additions(["CHANGELOG.md"], root=str(repo)) == {
            "CHANGELOG.md"
        }

    def test_committed_during_task_counts_only_with_since(self, repo):
        """The `/ship` ordering: commit at step 7, close at step 8."""
        with open(repo / "CHANGELOG.md", "a", encoding="utf-8") as fh:
            fh.write("\n### Shipped entry\n")
        _git(repo, "commit", "-qam", "entry")
        # Without `since` the working tree is clean — nothing to see.
        assert vgd.files_with_substantive_additions(["CHANGELOG.md"], root=str(repo)) == set()
        # With it, the commit made during the task is proof enough.
        assert vgd.files_with_substantive_additions(
            ["CHANGELOG.md"], root=str(repo), since=_SINCE_AFTER_SEED
        ) == {"CHANGELOG.md"}

    def test_committed_whitespace_only_still_does_not_count(self, repo):
        with open(repo / "CHANGELOG.md", "a", encoding="utf-8") as fh:
            fh.write("\n  \n")
        _git(repo, "commit", "-qam", "blank")
        assert (
            vgd.files_with_substantive_additions(
                ["CHANGELOG.md"], root=str(repo), since=_SINCE_AFTER_SEED
            )
            == set()
        )

    def test_untracked_new_file_counts_when_it_has_text(self, repo):
        (repo / "CHANGELOG.ru.md").write_text("## [Unreleased]\n\n### Запись\n", encoding="utf-8")
        assert vgd.files_with_substantive_additions(
            ["CHANGELOG.md", "CHANGELOG.ru.md"], root=str(repo)
        ) == {"CHANGELOG.ru.md"}

    def test_untracked_blank_file_does_not_count(self, repo):
        (repo / "CHANGELOG.ru.md").write_text("\n\n   \n", encoding="utf-8")
        assert vgd.files_with_substantive_additions(["CHANGELOG.ru.md"], root=str(repo)) == set()

    def test_not_a_repo_is_unverifiable(self, tmp_path):
        assert vgd.files_with_substantive_additions(["CHANGELOG.md"], root=str(tmp_path)) is None

    def test_linked_worktree_is_a_repository(self, repo, tmp_path):
        """`.git` is a FILE in a linked worktree. Reading only directories made
        every worktree 'not a repo' → unverifiable → fail-closed, so an agent
        in a worktree could not close a task at all."""
        wt = tmp_path / "wt"
        _git(repo, "worktree", "add", "-q", str(wt), "-b", "wt-branch")
        assert (wt / ".git").is_file()  # precondition, not a stub
        with open(wt / "CHANGELOG.md", "a", encoding="utf-8") as fh:
            fh.write("\n### Entry from a worktree\n")
        assert vgd.files_with_substantive_additions(["CHANGELOG.md"], root=str(wt)) == {
            "CHANGELOG.md"
        }


# --- wiring through _run_quality_gates_report (AC4 fail-then-pass) -----------


def _stub_gates_pass(monkeypatch):
    """Scoped gates pass and Verify-First is a no-op, so the changelog gate is
    the only thing that can block — isolates the wiring under test."""
    import service_gates

    monkeypatch.setattr(
        "service_verification.run_gates_with_cache",
        lambda *a, **k: (True, [], "ok"),
    )
    monkeypatch.setattr(service_gates.GatesMixin, "_enforce_verify_first", lambda *a, **k: None)


@pytest.mark.verify_first
class TestWiring:
    def test_missing_entry_blocks_then_present_passes(self, svc, monkeypatch):
        _stub_gates_pass(monkeypatch)
        _enable(monkeypatch)

        # 1. neither changelog gained text → blocked by the changelog gate
        _found(monkeypatch, [])
        rep = svc._run_quality_gates_report("t", ["scripts/x.py"], trigger="task-done")
        assert rep["passed"] is False
        assert any(f.get("gate") == "changelog" for f in rep["blocking_failures"])

        # 2. both written → passes
        _found(monkeypatch, ["CHANGELOG.md", "CHANGELOG.ru.md"])
        rep = svc._run_quality_gates_report("t", ["scripts/x.py"], trigger="task-done")
        assert rep["passed"] is True

    def test_no_changelog_flag_passes_through_wiring(self, svc, monkeypatch):
        _stub_gates_pass(monkeypatch)
        _enable(monkeypatch)
        _found(monkeypatch, [])
        rep = svc._run_quality_gates_report(
            "t", ["scripts/x.py"], trigger="task-done", no_changelog=True
        )
        assert rep["passed"] is True

    def test_verify_trigger_does_not_run_changelog_gate(self, svc, monkeypatch):
        # The changelog gate is a task-done concern only. `tausik verify` must
        # not block on it.
        _stub_gates_pass(monkeypatch)
        _enable(monkeypatch)
        _found(monkeypatch, [])
        rep = svc._run_quality_gates_report("t", ["scripts/x.py"], trigger="verify")
        assert rep["passed"] is True


# --- doc-drift guard (AC5) --------------------------------------------------


class TestDocDrift:
    def test_agent_contract_documents_gate_and_flag(self):
        doc = (_REPO_ROOT / "docs" / "ru" / "agent-contract.md").read_text(encoding="utf-8")
        assert "--no-changelog" in doc
        assert "changelog_gate" in doc

    def test_gate_enabled_in_own_config(self):
        import json

        cfg = json.loads((_REPO_ROOT / ".tausik" / "config.json").read_text(encoding="utf-8"))
        gate = cfg["task_done"]["changelog_gate"]
        assert gate["enabled"] is True
        assert "CHANGELOG.md" in gate["files"] and "CHANGELOG.ru.md" in gate["files"]
