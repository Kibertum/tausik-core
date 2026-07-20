"""Failing gate runs must be recorded — and must never be replayed as green.

l26-gate-results-persist shipped with recording tied to cache eligibility
(`passed and cache_ok and has_real_pass`), so a blocking failure from the
service path was never written to gate_runs. The one question the table exists
to answer — how often does a gate actually block — was unanswerable for exactly
the runs that matter.

The dangerous half of the fix is the other direction: a recorded run must not
become a cache hit. Two guards, both asserted here — failures carry
exit_code=1 (and both lookups filter exit_code=0), and a run that passed but is
not cacheable gets a command prefix neither lookup can match.
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import service_verification as sv  # noqa: E402
from gate_run_record import gate_activity  # noqa: E402
from verify_cache import has_fresh_verify_run  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    import sqlite3

    from backend_schema_gate_runs import GATE_RUNS_SQL

    c = sqlite3.connect(str(tmp_path / "t.db"))
    # Mirror how project_backend opens connections (row_factory + FK on):
    # the cache lookup does dict(row), which only works with Row.
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript(
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
);;
        """
    )
    c.executescript(GATE_RUNS_SQL)
    c.commit()
    yield c
    c.close()


def _run(conn, monkeypatch, gate_results, slug="t", files=None):
    """Drive run_gates_with_cache with a stubbed gate layer.

    run_gates is imported inside the function, so the patch target is the
    source module — patching service_verification would not take effect.
    """
    import gate_runner

    passed = all(r["passed"] for r in gate_results if not r.get("skipped"))
    monkeypatch.setattr(gate_runner, "run_gates", lambda *a, **k: (passed, gate_results))
    return sv.run_gates_with_cache(
        conn,
        slug,
        files if files is not None else ["scripts/x.py"],
        trigger="verify",
    )


def _gate(name, passed, severity="block", skipped=False):
    return {
        "name": name,
        "severity": severity,
        "passed": passed,
        "skipped": skipped,
        "output": "",
        "duration_ms": 3,
    }


class TestFailuresAreRecorded:
    def test_blocking_failure_lands_in_gate_runs(self, conn, monkeypatch):
        _run(conn, monkeypatch, [_gate("filesize", False)])
        rows = conn.execute("SELECT gate_name, passed, severity FROM gate_runs").fetchall()
        assert [tuple(r) for r in rows] == [("filesize", 0, "block")]

    def test_failure_shows_up_in_aggregates(self, conn, monkeypatch):
        _run(conn, monkeypatch, [_gate("filesize", False)])
        summary = gate_activity(conn, [])
        by_name = {g["gate"]: g for g in summary["gates"]}
        assert by_name["filesize"]["failures"] == 1
        assert by_name["filesize"]["blocking_failures"] == 1
        assert summary["blocking_failure_rate"] == 1.0

    def test_failed_run_is_recorded_with_nonzero_exit(self, conn, monkeypatch):
        _run(conn, monkeypatch, [_gate("filesize", False)])
        codes = [r[0] for r in conn.execute("SELECT exit_code FROM verification_runs")]
        assert codes == [1]

    def test_no_gates_ran_records_nothing(self, conn, monkeypatch):
        """Nothing to observe means nothing to write."""
        _run(conn, monkeypatch, [])
        assert conn.execute("SELECT COUNT(*) FROM verification_runs").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == 0


class TestRecordedRunsAreNotReplayedAsGreen:
    def test_failure_does_not_satisfy_verify_first(self, conn, monkeypatch):
        """The whole risk of recording failures, asserted directly."""
        files = ["scripts/x.py"]
        _run(conn, monkeypatch, [_gate("filesize", False)], files=files)
        ok, _hit = has_fresh_verify_run(conn, "t", files)
        assert ok is False

    def test_all_skipped_pass_does_not_satisfy_verify_first(self, conn, monkeypatch):
        """Passed but not cacheable: exit_code is 0, so the command must guard.

        Reached with NO declared files — with files declared, the earlier
        no-test-mapped branch returns a synthetic block before recording.
        """
        _run(conn, monkeypatch, [_gate("pytest", True, skipped=True)], files=[])
        # It was still recorded — observability is not the same as reuse.
        assert conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == 1
        ok, _hit = has_fresh_verify_run(conn, "t", [])
        assert ok is False

    def test_all_skipped_with_declared_files_still_blocks(self, conn, monkeypatch):
        """Regression: the no-test-mapped guard must not become a recorded green."""
        passed, results, status = _run(
            conn, monkeypatch, [_gate("pytest", True, skipped=True)], files=["scripts/x.py"]
        )
        assert passed is False
        assert status == "no-test-mapped"
        assert results[0]["severity"] == "block"

    def test_real_pass_still_satisfies_verify_first(self, conn, monkeypatch):
        """Regression: the cache must keep working for genuine greens."""
        files = ["scripts/x.py"]
        _run(conn, monkeypatch, [_gate("pytest", True)], files=files)
        ok, _hit = has_fresh_verify_run(conn, "t", files)
        assert ok is True


class TestTriggerAndDuration:
    def test_trigger_is_persisted_not_null(self, conn, monkeypatch):
        _run(conn, monkeypatch, [_gate("filesize", False)])
        assert conn.execute("SELECT trigger FROM gate_runs").fetchone()[0] == "verify"

    def test_duration_survives_to_the_row(self, conn, monkeypatch):
        _run(conn, monkeypatch, [_gate("filesize", False)])
        assert conn.execute("SELECT duration_ms FROM gate_runs").fetchone()[0] == 3
