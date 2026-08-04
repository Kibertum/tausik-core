"""state-git-roundtrip-gate: the gate that keeps the git-native tree honest.

The durable `tausik/` projection is the source of truth; the DB is the cache. This
gate re-serializes the DB and byte-compares it to the tree, so a commit cannot
carry state that disagrees with the DB (forgot to export, hand-edited a file, or
a non-deterministic serializer). It is opt-in — no tree means no check — and
commit-triggered, never task-done (a close mutates the DB it would compare).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import project_config  # noqa: E402
from gate_state_roundtrip import run_state_roundtrip_gate  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_export import ENTITY_DIRS, build_tree  # noqa: E402
from state_serialize import write_tree  # noqa: E402


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A temp project: seeded DB at <tmp>/.tausik/tausik.db, tree under <tmp>/tausik.

    Patches find_tausik_dir so the gate resolves THIS project, not the real repo.
    """
    # Disable auto-export during seeding: the real repo config has
    # state.auto_export=true, and (correctly, post-fix) the trigger would
    # materialize this tmp project's tausik/ tree as we seed — defeating the
    # "no tree yet" precondition. Each test materializes explicitly via _export.
    import state_triggers

    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: False)
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    db_path = str(tausik_dir / "tausik.db")
    svc = ProjectService(SQLiteBackend(db_path))
    svc.epic_add("e1", "Epic One")
    svc.story_add("e1", "s1", "Story One")
    svc.task_add("s1", "t1", "Task One", complexity="simple", role="developer")
    svc.decide("A real decision", task_slug="t1", rationale="because")
    svc.memory_add("pattern", "A pattern", "body text", ["z", "a"], "t1")
    svc.be.close()
    monkeypatch.setattr(project_config, "find_tausik_dir", lambda: str(tausik_dir))
    return tmp_path


def _export(project_root):
    be = SQLiteBackend(str(project_root / ".tausik" / "tausik.db"))
    tree, _w = build_tree(ProjectService(be))
    be.close()
    write_tree(str(project_root / "tausik"), tree, managed_dirs=set(ENTITY_DIRS))
    return tree


class TestStateRoundtripGate:
    def test_skips_when_no_tree_materialized(self, project):
        # Opt-in: a project that never ran `tausik state export` is not blocked.
        assert not (project / "tausik").exists()
        passed, msg = run_state_roundtrip_gate()
        assert passed
        assert "skipped" in msg.lower()

    def test_green_when_tree_matches_db(self, project):
        _export(project)
        passed, msg = run_state_roundtrip_gate()
        assert passed, msg
        assert "matches the DB export" in msg

    def test_red_on_single_field_hand_edit(self, project):
        _export(project)
        # Corrupt one field of one entity — the exact "hand-edited past the DB" mode.
        task_file = project / "tausik" / "tasks" / "t1.md"
        task_file.write_text(
            task_file.read_text(encoding="utf-8").replace("Task One", "Task EDITED"),
            encoding="utf-8",
            newline="",
        )
        passed, msg = run_state_roundtrip_gate()
        assert not passed
        assert "drift" in msg.lower()
        assert "tausik state export" in msg

    def test_red_on_extra_file(self, project):
        _export(project)
        # A stray entity file the DB has no row for.
        (project / "tausik" / "tasks" / "ghost.md").write_text(
            "---\nslug: ghost\n---\n", encoding="utf-8"
        )
        passed, msg = run_state_roundtrip_gate()
        assert not passed
        assert "drift" in msg.lower()

    def test_red_on_missing_file(self, project):
        _export(project)
        # Delete an exported entity file — the DB row now has no projection.
        for f in (project / "tausik" / "memory").glob("*.md"):
            f.unlink()
            break
        passed, msg = run_state_roundtrip_gate()
        assert not passed

    def test_private_paths_are_not_under_the_gate(self, project):
        # The gate only reads ENTITY_DIRS under tausik/. A private file in the
        # runtime .tausik/ dir (keys, db, receipts) is never compared.
        _export(project)
        (project / ".tausik" / "secret.key").write_text("PRIVATE", encoding="utf-8")
        (project / ".tausik" / "receipts.jsonl").write_text("{}\n", encoding="utf-8")
        passed, msg = run_state_roundtrip_gate()
        assert passed, msg

    def test_fails_open_on_missing_db(self, project, monkeypatch):
        # A gate must never crash the commit: point find_tausik_dir at a dir with
        # a tree but no DB → skip (pass), not raise.
        _export(project)
        os.remove(str(project / ".tausik" / "tausik.db"))
        passed, msg = run_state_roundtrip_gate()
        assert passed
        assert "skipped" in msg.lower() or "unavailable" in msg.lower()


class TestGateRegistration:
    def test_state_roundtrip_registered_on_commit_not_task_done(self):
        import gate_registry as reg

        spec = next((s for s in reg._SCOPED if s.name == "state_roundtrip"), None)
        assert spec is not None, "state_roundtrip gate not registered"
        cfg = spec.default_config
        assert cfg["trigger"] == ["commit"], "must fire at commit, not task-done (auto-close drift)"
        assert cfg["severity"] == "block"
        assert cfg["enabled"] is True


class TestFailOpenAndExportError:
    """Review HIGH-1 (fail-open must survive an internal fault, incl. a broken
    import) and MED-3 (ExportError is a hard block, not a fail-open pass)."""

    def test_internal_fault_fails_open_never_raises(self, project, monkeypatch):
        # A non-ExportError fault anywhere in the guarded block (a broken import
        # chain lands here too, now that the import is inside the try) must
        # degrade to a PASS with 'unavailable', never propagate to gate_runner.
        _export(project)
        import state_export

        def _boom(_svc):
            raise RuntimeError("simulated internal fault")

        monkeypatch.setattr(state_export, "build_tree", _boom)
        passed, msg = run_state_roundtrip_gate()  # must NOT raise
        assert passed
        assert "unavailable" in msg.lower()

    def test_export_error_is_a_hard_block(self, project, monkeypatch):
        _export(project)
        import state_export

        def _refuse(_svc):
            raise state_export.ExportError("slug-less entity needs a migration")

        monkeypatch.setattr(state_export, "build_tree", _refuse)
        passed, msg = run_state_roundtrip_gate()
        assert not passed
        assert "refused" in msg.lower()


class TestStagedCheck:
    """Review HIGH-2: the working tree can match the DB while the export is not
    staged (`git add tausik/` forgotten) — the commit would then omit it. The
    gate must go red on unstaged/untracked tausik/ paths."""

    @pytest.fixture
    def git_project(self, project):
        import subprocess

        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
        run = lambda *a: subprocess.run(  # noqa: E731
            ["git", *a],
            cwd=str(project),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        init = run("init")
        if init.returncode != 0:  # pragma: no cover - git always present in CI
            pytest.skip("git unavailable")
        run("config", "user.email", "t@t")
        run("config", "user.name", "t")
        _export(project)
        return project, run

    def test_red_when_export_unstaged(self, git_project):
        project, _run = git_project
        # Tree matches DB (just exported) but nothing is staged → untracked.
        passed, msg = run_state_roundtrip_gate()
        assert not passed
        assert "not staged" in msg.lower()
        assert "git add tausik/" in msg

    def test_green_when_export_staged(self, git_project):
        project, run = git_project
        run("add", "tausik")
        passed, msg = run_state_roundtrip_gate()
        assert passed, msg
        assert "matches the DB export" in msg

    def test_red_when_staged_then_worktree_edited(self, git_project):
        project, run = git_project
        run("add", "tausik")
        # Stage the good export, then hand-edit the worktree copy: the index still
        # matches the DB, but the check_tree (worktree vs DB) now differs first.
        task_file = project / "tausik" / "tasks" / "t1.md"
        task_file.write_text(
            task_file.read_text(encoding="utf-8").replace("Task One", "EDITED"),
            encoding="utf-8",
            newline="",
        )
        passed, _msg = run_state_roundtrip_gate()
        assert not passed
