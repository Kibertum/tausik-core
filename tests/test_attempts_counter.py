"""`tasks.attempts` counts attempts — activations and red verifications.

`attempts-counter-never-increments`. Measured in #189: of 1239 closed tasks
exactly one had `attempts > 1`, and the field is shown by `task show` as a
fact. The counter did move on `task start` (since v1.0.0), which is not where
second attempts happen: they happen when a blocked task is UNBLOCKED, and
when a verification of the active task comes back RED. Neither touched the
counter, so FPSR — built on `attempts = 1` — reported a first-pass rate the
history could not support.

History is not rewritten: an old close keeps its 1 (or 0 for a task that was
never activated), and the tests below are about NEW events only.
"""

from __future__ import annotations

import os
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import verify_run_record  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path, monkeypatch):
    import state_triggers

    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: False)
    (tmp_path / ".tausik").mkdir()
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    service.epic_add("e1", "Epic")
    service.story_add("e1", "s1", "Story")
    service.task_add("s1", "t1", "Task", complexity="simple", role="developer")
    yield service
    service.be.close()


def _attempts(svc, slug="t1") -> int:
    return int(svc.be.task_get(slug)["attempts"] or 0)


def _record(svc, *, exit_code: int, slug: str = "t1") -> int:
    return verify_run_record._record_verification(
        svc.be._conn,
        slug=slug,
        command="pytest -q",
        exit_code=exit_code,
        summary="pytest=PASS" if exit_code == 0 else "pytest=FAIL",
        files_hash="h",
        gate_results=[{"gate": "pytest", "passed": exit_code == 0, "output": ""}],
        scope_desc={"status": "unknown"},
        trigger="verify",
        scope="manual",
    )


class TestActivationsCount:
    def test_first_start_is_attempt_one(self, svc):
        assert _attempts(svc) == 0  # never activated: not counted, and says so
        svc.task_start("t1", _internal_force=True)
        assert _attempts(svc) == 1

    def test_unblock_is_a_re_activation_and_counts(self, svc):
        svc.task_start("t1", _internal_force=True)
        svc.task_block("t1", "waiting")
        msg = svc.task_unblock("t1", force=True)
        assert _attempts(svc) == 2
        assert "attempt #2" in msg

    def test_block_itself_is_not_an_attempt(self, svc):
        svc.task_start("t1", _internal_force=True)
        svc.task_block("t1", "waiting")
        assert _attempts(svc) == 1


class TestRedVerificationCounts:
    def test_a_red_run_on_the_active_task_counts(self, svc):
        svc.task_start("t1", _internal_force=True)
        _record(svc, exit_code=1)
        assert _attempts(svc) == 2

    def test_a_green_run_does_not(self, svc):
        svc.task_start("t1", _internal_force=True)
        _record(svc, exit_code=0)
        assert _attempts(svc) == 1

    def test_a_red_run_on_a_task_not_in_flight_does_not(self, svc):
        # planning: never activated, a red run against it is not an attempt
        _record(svc, exit_code=1)
        assert _attempts(svc) == 0

    def test_a_red_run_after_close_leaves_history_alone(self, svc):
        svc.task_start("t1", _internal_force=True)
        svc.be.task_update("t1", status="done")
        _record(svc, exit_code=1)
        assert _attempts(svc) == 1

    def test_the_sequence_of_a_real_second_attempt(self, svc):
        """start → red verify → fix → green verify: two attempts, not one."""
        svc.task_start("t1", _internal_force=True)
        _record(svc, exit_code=2)
        _record(svc, exit_code=0)
        assert _attempts(svc) == 2

    def test_the_helper_reports_whether_it_moved_a_row(self, svc):
        svc.task_start("t1", _internal_force=True)
        assert verify_run_record.count_failed_attempt(svc.be._conn, "t1") is True
        assert verify_run_record.count_failed_attempt(svc.be._conn, "absent") is False

    def test_a_database_without_a_tasks_table_is_not_an_error(self, tmp_path):
        import sqlite3

        conn = sqlite3.connect(str(tmp_path / "bare.db"))
        conn.execute("CREATE TABLE verification_runs (id INTEGER PRIMARY KEY)")
        assert verify_run_record.count_failed_attempt(conn, "t1") is False
        conn.close()


class TestTheMetricReadsIt:
    def test_fpsr_counts_a_task_with_a_red_verify_as_not_first_pass(self, svc):
        svc.task_add("s1", "t2", "Task two", complexity="simple", role="developer")
        for slug in ("t1", "t2"):
            svc.task_start(slug, _internal_force=True)
        _record(svc, exit_code=1, slug="t2")
        for slug in ("t1", "t2"):
            svc.be.task_update(slug, status="done")
        row = svc.be._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='done' AND attempts=1"
        ).fetchone()
        assert row[0] == 1
