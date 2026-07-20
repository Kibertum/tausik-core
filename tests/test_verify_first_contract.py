"""v1.4 Verify-First Contract — end-to-end tests.

Covers the architectural fix that decouples task closure from heavy
verification gates so MCP hosts (VS Code Claude Extension) don't hang
during `task done`. Heavy gates (pytest, tsc, cargo, phpstan, ...) live
on the new "verify" trigger; `task done` enforces a fresh `tausik verify`
green via the verify cache.

Each test class is marked @pytest.mark.verify_first so the autouse compat
shim (`_verify_first_autouse_compat_shim` in conftest) leaves
`_enforce_verify_first` intact.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


@pytest.fixture
def svc(tmp_path):
    db = str(tmp_path / "test.db")
    be = SQLiteBackend(db)
    return ProjectService(be)


# verify-cache-empty-scope-hit: the tasks below declare `relevant_files`.
# They used to leave the scope empty, which was a shortcut — an undeclared
# scope now blocks on its own (the scoped gates never ran, so nothing was
# verified), and these tests are about the *generic* Verify-First path, not
# about that. The empty-scope contract has its own coverage in
# test_verify_cache_empty_scope.py and TestUndeclaredScopeBlocks below.
_SCOPE = ["scripts/x.py"]


@pytest.fixture
def task_ready(svc):
    """Task with goal + AC + declared scope + started, ready for `task done`."""
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "t", "Implement X", goal="Implement X", role="developer")
    svc.task_update(
        "t",
        acceptance_criteria="1. X works\n2. Returns error on invalid input",
        relevant_files=json.dumps(_SCOPE),
    )
    svc.task_start("t")
    svc.task_log("t", "AC verified: 1. X works ✓ 2. Returns error on invalid input ✓")
    return svc


@pytest.fixture
def task_ready_unscoped(svc):
    """Same, but with NO relevant_files on the task row.

    Only for the recovery path: the scope has to be missing from the DB for
    the verify-row fallback to be the thing under test. The recovered list is
    non-empty, so this does not collide with the empty-scope block.
    """
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "t", "Implement X", goal="Implement X", role="developer")
    svc.task_update("t", acceptance_criteria="1. X works\n2. Returns error on invalid input")
    svc.task_start("t")
    svc.task_log("t", "AC verified: 1. X works ✓ 2. Returns error on invalid input ✓")
    return svc


def _stub_verify_only(monkeypatch, *, auto_verify: bool):
    """Pretend the project has a single verify-trigger gate (pytest) and
    no other gates. Returns the service_verification module for cache helpers.
    """
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

    fake_cfg = {"task_done": {"auto_verify": auto_verify}}
    monkeypatch.setattr("project_config.load_config", lambda: fake_cfg)
    monkeypatch.setattr("project_config.get_gates_for_trigger", fake_get_for_trigger)
    import service_verification

    return service_verification


@pytest.mark.verify_first
class TestVerifyFirstEnforcement:
    """task_done refuses to close until a fresh verify run exists."""

    def test_no_verify_run_blocks(self, task_ready, monkeypatch):
        _stub_verify_only(monkeypatch, auto_verify=False)
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            with pytest.raises(ServiceError, match="no fresh `tausik verify`"):
                task_ready.task_done("t", ac_verified=True)

    def test_block_message_points_to_remediation(self, task_ready, monkeypatch):
        # Use the internal _task_done_report to inspect the full structured
        # report (full remediation/output without the 180-char truncation
        # that the public legacy task_done() applies to the ServiceError).
        # Pre-rename this called task_done_v2(); v14b-task-done-rename-drop-v2
        # consolidated to a single tausik_task_done returning structured JSON.
        _stub_verify_only(monkeypatch, auto_verify=False)
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            report = task_ready._task_done_report(
                "t", relevant_files=None, ac_verified=True, no_knowledge=False, evidence=None
            )
        assert not report["ok"]
        failures = report["blocking_failures"]
        assert any(
            f.get("gate") == "verify-first" and "tausik verify" in f.get("output", "")
            for f in failures
        )
        # Remediation must include the explicit two-step command.
        assert any("tausik verify --task" in f.get("remediation", "") for f in failures)

    def test_fresh_verify_run_unblocks(self, task_ready, monkeypatch):
        sv = _stub_verify_only(monkeypatch, auto_verify=False)
        # Recorded against the task's declared scope. It used to be files=[],
        # which no longer certifies anything (verify-cache-empty-scope-hit).
        cache_command = sv._build_cache_command("verify", _SCOPE)
        files_hash = sv.compute_files_hash(_SCOPE)
        sv.record_run(
            task_ready.be._conn,
            task_slug="t",
            scope="standard",
            command=cache_command,
            exit_code=0,
            summary="pytest=PASS",
            files_hash=files_hash,
            duration_ms=42,
        )
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            msg = task_ready.task_done("t", ac_verified=True)
        assert "completed" in msg


@pytest.mark.verify_first
class TestAutoVerifyOptOut:
    """auto_verify=true preserves the legacy "run gates inline" behavior."""

    def test_auto_verify_inline_pass(self, task_ready, monkeypatch):
        _stub_verify_only(monkeypatch, auto_verify=True)
        # When _enforce_verify_first runs verify gates inline → run_gates → PASS.
        mock_run = MagicMock(
            return_value=(
                True,
                [
                    {
                        "name": "pytest",
                        "passed": True,
                        "skipped": False,
                        "severity": "block",
                        "output": "ok",
                    }
                ],
            )
        )
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            msg = task_ready.task_done("t", ac_verified=True)
        assert "completed" in msg

    def test_auto_verify_inline_fail_blocks(self, task_ready, monkeypatch):
        _stub_verify_only(monkeypatch, auto_verify=True)
        mock_run = MagicMock(
            return_value=(
                False,
                [
                    {
                        "name": "pytest",
                        "passed": False,
                        "skipped": False,
                        "severity": "block",
                        "output": "1 failed",
                    }
                ],
            )
        )
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=mock_run)}):
            with pytest.raises(ServiceError):
                task_ready.task_done("t", ac_verified=True)


@pytest.mark.verify_first
class TestCacheBucketSeparation:
    """Verify-First cache key includes trigger; task-done bucket and verify
    bucket must NOT cross-satisfy each other."""

    def test_task_done_bucket_does_not_satisfy_verify_first(self, task_ready, monkeypatch):
        sv = _stub_verify_only(monkeypatch, auto_verify=False)
        # Pre-record a green run with the OLD trigger="task-done" key
        files_hash = sv.compute_files_hash([])
        sv.record_run(
            task_ready.be._conn,
            task_slug="t",
            scope="standard",
            command=sv._build_cache_command("task-done", []),
            exit_code=0,
            summary="x=PASS",
            files_hash=files_hash,
            duration_ms=10,
        )
        # _enforce_verify_first looks up by trigger="verify" cache key — the
        # task-done row above must NOT satisfy it.
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            with pytest.raises(ServiceError, match="no fresh `tausik verify`"):
                task_ready.task_done("t", ac_verified=True)


@pytest.mark.verify_first
class TestNoVerifyGatesProjectIsExempt:
    """Small projects without any verify-trigger gates must not be blocked.

    We don't want the contract to require a verify run for a project where
    there's nothing to verify (e.g. docs-only repo, plain config-as-code).
    """

    def test_empty_verify_trigger_skips_enforcement(self, task_ready, monkeypatch):
        # Patch get_gates_for_trigger to return [] for "verify" specifically.
        from project_config import get_gates_for_trigger as real

        def fake(trigger, cfg=None):
            if trigger == "verify":
                return []
            return real(trigger, cfg)

        monkeypatch.setattr(
            "project_config.load_config", lambda: {"task_done": {"auto_verify": False}}
        )
        monkeypatch.setattr("project_config.get_gates_for_trigger", fake)
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            msg = task_ready.task_done("t", ac_verified=True)
        assert "completed" in msg


@pytest.mark.verify_first
class TestStackGatesMovedToVerify:
    """Sanity: confirm the v1.4 migration in default_gates / stack JSONs."""

    @pytest.mark.parametrize(
        "gate_name",
        ["pytest", "tsc", "cargo-test", "go-test", "phpunit", "phpstan"],
    )
    def test_heavy_gate_is_on_verify_trigger(self, gate_name):
        from project_config import DEFAULT_GATES

        gate = DEFAULT_GATES.get(gate_name)
        if gate is None:
            pytest.skip(f"{gate_name} not registered (stack JSON missing in suite)")
        assert "verify" in gate.get("trigger", []), (
            f"{gate_name} must be on verify trigger after v1.4"
        )
        assert "task-done" not in gate.get("trigger", []), (
            f"{gate_name} must NOT be on task-done trigger after v1.4"
        )

    def test_filesize_stays_universal_on_task_done(self):
        from project_config import DEFAULT_GATES

        gate = DEFAULT_GATES["filesize"]
        # filesize is cheap (line counting only) — stays on task-done.
        assert "task-done" in gate["trigger"]


@pytest.mark.verify_first
class TestRelevantFilesFallback:
    """v14-task-done-relevant-files-fallback: task_done recovers files from verify-row.

    Closes the sharp edge where `tausik verify --task X` (records a verify-row
    with files=[...]) is followed by `task done X` (no CLI args, no DB
    relevant_files) — without fallback the cache key mismatches and verify-first
    reports "no fresh run" despite a green run sitting right there.
    """

    def test_fallback_recovers_files_from_recent_verify(self, task_ready_unscoped, monkeypatch):
        task_ready = task_ready_unscoped
        sv = _stub_verify_only(monkeypatch, auto_verify=False)
        files = ["scripts/foo.py"]
        cmd = sv._build_cache_command("verify", files)
        sv.record_run(
            task_ready.be._conn,
            task_slug="t",
            scope="standard",
            command=cmd,
            exit_code=0,
            summary="pytest=PASS",
            files_hash=sv.compute_files_hash(files),
            duration_ms=10,
        )
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            msg = task_ready.task_done("t", ac_verified=True)
        assert "completed" in msg

    def test_fallback_skipped_for_security_sensitive_paths(self, task_ready, monkeypatch):
        sv = _stub_verify_only(monkeypatch, auto_verify=False)
        files = ["scripts/auth.py"]
        cmd = sv._build_cache_command("verify", files)
        sv.record_run(
            task_ready.be._conn,
            task_slug="t",
            scope="standard",
            command=cmd,
            exit_code=0,
            summary="pytest=PASS",
            files_hash=sv.compute_files_hash(files),
            duration_ms=10,
        )
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            with pytest.raises(ServiceError, match="no fresh `tausik verify`"):
                task_ready.task_done("t", ac_verified=True)

    def test_fallback_skipped_when_no_verify_row(self, task_ready, monkeypatch):
        _stub_verify_only(monkeypatch, auto_verify=False)
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            with pytest.raises(ServiceError, match="no fresh `tausik verify`"):
                task_ready.task_done("t", ac_verified=True)

    def test_auto_verify_failure_reports_gate_files(self, task_ready, monkeypatch):
        """The auto_verify FAILURE branch builds its entries with the file
        extractor. Extracting `_enforce_verify_first` into `gate_verify_first`
        left a `self.` reference on exactly this path — every test passed
        because none of them drove a failing inline run. Ruff caught it; this
        test is why it will not come back silently.
        """
        _stub_verify_only(monkeypatch, auto_verify=True)
        failing = MagicMock(
            return_value=(
                False,
                [
                    {
                        "name": "filesize",
                        "passed": False,
                        "skipped": False,
                        "severity": "block",
                        "output": "  scripts/big.py:  420 lines\n",
                    }
                ],
            )
        )
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=failing)}):
            report = task_ready._task_done_report(
                "t", relevant_files=_SCOPE, ac_verified=True, no_knowledge=False, evidence=None
            )
        assert not report["ok"]
        entry = next(f for f in report["blocking_failures"] if f.get("gate") == "filesize")
        assert entry["files"] == ["scripts/big.py"]

    def test_unscoped_task_blocks_even_under_auto_verify(self, task_ready_unscoped, monkeypatch):
        """The empty-scope rule must not be escapable via config.

        auto_verify=true runs the gates inline, and with no declared files
        `gate_runner` skips the scoped ones — so a scope-independent gate going
        green would close the task on a run that examined nothing. The check is
        ahead of the auto_verify branch precisely so `.tausik/config.json`,
        which travels with the repository, cannot host that bypass.
        """
        _stub_verify_only(monkeypatch, auto_verify=True)
        inline = MagicMock(
            return_value=(
                True,
                [{"name": "filesize", "passed": True, "skipped": False, "severity": "block"}],
            )
        )
        with patch.dict("sys.modules", {"gate_runner": MagicMock(run_gates=inline)}):
            with pytest.raises(ServiceError, match="declares no relevant_files"):
                task_ready_unscoped.task_done("t", ac_verified=True)

    def test_unscoped_task_blocks_with_its_own_reason(self, task_ready_unscoped, monkeypatch):
        """verify-cache-empty-scope-hit: when nothing declares or recovers a
        scope, the block must say so instead of sending the agent to re-run
        `tausik verify` in a loop that can never succeed."""
        _stub_verify_only(monkeypatch, auto_verify=False)
        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            with pytest.raises(ServiceError, match="declares no relevant_files"):
                task_ready_unscoped.task_done("t", ac_verified=True)

    def test_lookup_helper_unit(self, tmp_path):
        """Direct unit test of the helper independent of the service stack."""
        import sqlite3
        from verify_recent_lookup import lookup_relevant_files_from_recent_verify

        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.execute(
            """CREATE TABLE IF NOT EXISTS verification_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT,
    scope TEXT NOT NULL CHECK(scope IN
        ('lightweight', 'standard', 'high', 'critical', 'manual')),
    command TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    summary TEXT,
    files_hash TEXT NOT NULL,
    ran_at TEXT NOT NULL,
    duration_ms INTEGER,
    receipt_json TEXT,
    -- l26-verify-git-diff-wire: how the declared scope related to git at run
    -- time. 'complete' | 'under-declared' | 'unknown'; NULL on rows written
    -- before v38 and read as 'unknown' (never as 'complete').
    declared_scope_status TEXT,
    -- JSON array of files git saw change but relevant_files omitted (capped).
    undeclared_files TEXT,
    -- verify-no-test-mapped-dead-end: 1 when the caller declared, for this run,
    -- that its files map to no test on purpose (docs, config, migrations). Such
    -- a run passes with NO gate executed, so it must stay countable:
    --   SELECT * FROM verification_runs WHERE no_tests_declared = 1;
    -- A dedicated column, not a `scope` value — `scope` is a CHECK-constrained
    -- SENAR tier, and overloading it would have required rebuilding the table
    -- to widen the constraint.
    no_tests_declared INTEGER NOT NULL DEFAULT 0
)"""
        )
        # No row → None.
        assert lookup_relevant_files_from_recent_verify(db, "t") is None

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        db.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            ("t", "manual", "trigger=verify|sig=x|files=a.py,b.py", 0, "ok", "h", now),
        )
        db.commit()
        assert lookup_relevant_files_from_recent_verify(db, "t") == ["a.py", "b.py"]

        # `files=` empty → None (not [])
        db.execute("DELETE FROM verification_runs")
        db.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            ("t", "manual", "trigger=verify|sig=x|files=", 0, "ok", "h", now),
        )
        db.commit()
        assert lookup_relevant_files_from_recent_verify(db, "t") is None

        # Failed run (exit_code != 0) → None
        db.execute("DELETE FROM verification_runs")
        db.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            ("t", "manual", "trigger=verify|sig=x|files=a.py", 1, "fail", "h", now),
        )
        db.commit()
        assert lookup_relevant_files_from_recent_verify(db, "t") is None

    def test_recovery_ignores_task_done_filesize_rows(self, tmp_path):
        """v14b-defect-recover-files-from-task-done-row: recovery must filter
        to trigger=verify rows. A task-done filesize PASS row also has
        exit_code=0 and a `files=...` payload from --relevant-files; if it
        shadowed the verify row, files_hash would mismatch and the next
        `task done` would falsely fail with "no fresh verify run".
        """
        import sqlite3
        from datetime import datetime, timezone

        from verify_recent_lookup import lookup_relevant_files_from_recent_verify

        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.execute(
            """CREATE TABLE IF NOT EXISTS verification_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT,
    scope TEXT NOT NULL CHECK(scope IN
        ('lightweight', 'standard', 'high', 'critical', 'manual')),
    command TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    summary TEXT,
    files_hash TEXT NOT NULL,
    ran_at TEXT NOT NULL,
    duration_ms INTEGER,
    receipt_json TEXT,
    -- l26-verify-git-diff-wire: how the declared scope related to git at run
    -- time. 'complete' | 'under-declared' | 'unknown'; NULL on rows written
    -- before v38 and read as 'unknown' (never as 'complete').
    declared_scope_status TEXT,
    -- JSON array of files git saw change but relevant_files omitted (capped).
    undeclared_files TEXT,
    -- verify-no-test-mapped-dead-end: 1 when the caller declared, for this run,
    -- that its files map to no test on purpose (docs, config, migrations). Such
    -- a run passes with NO gate executed, so it must stay countable:
    --   SELECT * FROM verification_runs WHERE no_tests_declared = 1;
    -- A dedicated column, not a `scope` value — `scope` is a CHECK-constrained
    -- SENAR tier, and overloading it would have required rebuilding the table
    -- to widen the constraint.
    no_tests_declared INTEGER NOT NULL DEFAULT 0
)"""
        )
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        db.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            ("t", "manual", "trigger=verify|sig=x|files=src/foo.py", 0, "pytest=PASS", "h1", now),
        )
        db.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            (
                "t",
                "standard",
                "trigger=task-done|sig=y|files=src/bar.py,src/baz.py",
                0,
                "filesize=PASS",
                "h2",
                now,
            ),
        )
        db.commit()
        assert lookup_relevant_files_from_recent_verify(db, "t") == ["src/foo.py"]
        db.close()


@pytest.mark.verify_first
class TestPipelineEnvelopeRegression:
    """v14-verify-hang-regression-test: end-to-end hang trap.

    Registers a real custom gate that sleeps 300s and confirms the envelope
    timeout aborts the run quickly with a remediation-rich message. If the
    envelope wrapper in `service_verification.run_gates_with_cache` is ever
    removed or its config key is renamed, this test fails — guarding the
    headline v1.4 reliability fix from silent regressions.
    """

    def test_hung_gate_aborts_under_envelope(self, tmp_path, monkeypatch):
        import sqlite3
        import sys as _sys
        import time as _time

        db = sqlite3.connect(str(tmp_path / "regress.db"))
        db.row_factory = sqlite3.Row
        db.executescript(
            """
CREATE TABLE IF NOT EXISTS verification_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT,
    scope TEXT NOT NULL CHECK(scope IN
        ('lightweight', 'standard', 'high', 'critical', 'manual')),
    command TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    summary TEXT,
    files_hash TEXT NOT NULL,
    ran_at TEXT NOT NULL,
    duration_ms INTEGER,
    receipt_json TEXT,
    -- l26-verify-git-diff-wire: how the declared scope related to git at run
    -- time. 'complete' | 'under-declared' | 'unknown'; NULL on rows written
    -- before v38 and read as 'unknown' (never as 'complete').
    declared_scope_status TEXT,
    -- JSON array of files git saw change but relevant_files omitted (capped).
    undeclared_files TEXT,
    -- verify-no-test-mapped-dead-end: 1 when the caller declared, for this run,
    -- that its files map to no test on purpose (docs, config, migrations). Such
    -- a run passes with NO gate executed, so it must stay countable:
    --   SELECT * FROM verification_runs WHERE no_tests_declared = 1;
    -- A dedicated column, not a `scope` value — `scope` is a CHECK-constrained
    -- SENAR tier, and overloading it would have required rebuilding the table
    -- to widen the constraint.
    no_tests_declared INTEGER NOT NULL DEFAULT 0
);
            """
        )

        # The custom gate dict mirrors what a real stack-scoped gate would
        # provide. The autouse `_mock_run_gates` shim in conftest stubs
        # `gate_runner.run_gates` to (True, []), so we install our own slow
        # implementation on top — the goal here is the envelope timeout, not
        # subprocess fan-out (covered by per-gate timeouts elsewhere).
        sleep_cmd = f'"{_sys.executable}" -c "import time; time.sleep(300)"'

        def slow_run_gates(_trigger, _files, **_kw):
            assert _trigger == "verify", (
                f"envelope test must run under verify trigger, got {_trigger}"
            )
            _time.sleep(10)  # well past the 2s envelope
            return True, [
                {
                    "name": "hung-test-gate",
                    "passed": True,
                    "skipped": False,
                    "severity": "block",
                    "output": sleep_cmd,
                }
            ]

        monkeypatch.setattr(
            "project_config.load_config",
            lambda: {"verify_pipeline_timeout_seconds": 2},
        )
        monkeypatch.setattr("gate_runner.run_gates", slow_run_gates)

        import service_verification as sv

        t0 = _time.monotonic()
        with pytest.raises(sv.GateEnvelopeTimeoutError) as exc:
            sv.run_gates_with_cache(db, "regress-task", ["scripts/foo.py"], trigger="verify")
        elapsed = _time.monotonic() - t0
        assert elapsed < 6.0, (
            f"envelope timeout did not abort under 6s: took {elapsed:.2f}s — "
            "regression in run_gates_with_cache envelope wrapper"
        )
        msg = str(exc.value)
        assert "verify_pipeline_timeout_seconds" in msg
        assert "auto_verify" in msg
        assert "relevant_files" in msg
        db.close()
