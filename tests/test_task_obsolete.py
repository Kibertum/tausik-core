"""A task can be closed as obsolete: kept on record, left out of delivery metrics.

a-task-cannot-be-closed-as-obsolete (1.10, decision #390). Session #265: four
tasks time had resolved could only be closed by writing criteria after the fact
or by a hard delete. `task obsolete` keeps the record, needs a reason, skips
QG-2, and a closed finding does not count as a shipped one.
"""

from __future__ import annotations

import pytest

import claudemd_state
from project_backend import SQLiteBackend
from project_service import ProjectService
from task_obsolete import close_obsolete
from tausik_utils import ServiceError

REASON = "resolved by commit 077e0957 under another task; HEAD no longer has the symbol"
DELIVERY_KEYS = (
    "fpsr",
    "der",
    "throughput",
    "lead_time_hours",
    "cycle_time_hours",
    "knowledge_capture_rate",
    "populations",
    "per_tier",
    "calibration_drift",
    "cost_per_task",
)


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "obs.db")))
    s.session_start()
    s.epic_add("e", "E")
    s.story_add("e", "s", "S")
    s.task_add("s", "delivered", "Delivered")
    s.be.task_update(
        "delivered",
        status="done",
        attempts=1,
        started_at="2026-09-01T10:00:00Z",
        completed_at="2026-09-01T12:00:00Z",
        call_budget=10,
        call_actual=8,
        tier="light",
    )
    s.task_add("s", "stale", "Stale")
    yield s
    s.be.close()


def test_a_planning_task_closes_as_obsolete_and_keeps_its_record(svc):
    msg = close_obsolete(svc, "stale", REASON)
    task = svc.be.task_get("stale")
    assert task["status"] == "done" and task["completed_at"]
    assert task["resolution"] == "obsolete"
    assert task["resolution_reason"] == REASON
    assert "OBSOLETE (was planning): " + REASON in task["notes"]
    assert "closed as OBSOLETE" in msg


@pytest.mark.parametrize(
    "reason",
    [
        pytest.param("", id="empty"),
        pytest.param("stale", id="too-short"),
        pytest.param("TODO later, TBD", id="placeholder"),
    ],
)
def test_a_close_without_a_checkable_reason_is_refused(svc, reason):
    with pytest.raises(ServiceError, match="needs a reason"):
        close_obsolete(svc, "stale", reason)
    assert svc.be.task_get("stale")["status"] == "planning"


def test_a_task_already_done_is_not_marked_obsolete(svc):
    with pytest.raises(ServiceError, match="already closed"):
        close_obsolete(svc, "delivered", REASON)
    assert svc.be.task_get("delivered")["resolution"] is None


def test_delivery_metrics_do_not_move(svc):
    """NEGATIVE: the obsolete task had attempts=1, a cycle time and a tier —
    everything that would count — and none of the delivery numbers change."""
    svc.be.task_update(
        "stale", attempts=1, started_at="2026-09-02T10:00:00Z", call_budget=5, call_actual=50
    )
    before = svc.be.get_metrics()
    close_obsolete(svc, "stale", REASON)
    after = svc.be.get_metrics()
    assert {k: after[k] for k in DELIVERY_KEYS} == {k: before[k] for k in DELIVERY_KEYS}
    assert after["tasks_done"] == before["tasks_done"]
    assert after["tasks"]["obsolete"] == 1


def test_the_status_line_and_claude_md_report_it_apart(svc):
    close_obsolete(svc, "stale", REASON)
    counts = svc.be.get_status_data()["task_counts"]
    assert counts["done"] == 1 and counts["obsolete"] == 1
    state = claudemd_state.build_dynamic_state(svc, ".")
    assert "Tasks: 1/2 done, 1 obsolete" in state


def test_the_story_closes_when_its_last_open_task_goes_obsolete(svc):
    msg = close_obsolete(svc, "stale", REASON)
    assert "Story 's' auto-closed." in msg


def test_task_done_refuses_a_task_that_never_started(svc):
    """task-done-closes-a-task-that-never-started: planning -> done skipped QG-0
    and left no started_at. NEGATIVE: full evidence does not help."""
    svc.task_log("stale", "AC-1: ✓ manual: checked the thing by hand, it works")
    with pytest.raises(ServiceError, match="was never started") as exc:
        svc.task_done("stale", ac_verified=True)
    assert "task obsolete stale" in str(exc.value)
    assert svc.be.task_get("stale")["status"] == "planning"
