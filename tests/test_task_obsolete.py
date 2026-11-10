"""A task can be closed as obsolete: kept on record, left out of delivery metrics.

a-task-cannot-be-closed-as-obsolete (1.10, decision #390). Session #265: four
tasks time had resolved could only be closed by writing criteria after the fact
or by a hard delete. `task obsolete` keeps the record, needs a reason, skips
QG-2, and a closed finding does not count as a shipped one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import claudemd_state
from project_backend import SQLiteBackend
from project_service import ProjectService
from service_execution_lease import (
    ExecutionLeaseError,
    authorize_mcp_mutation,
    assertion_from_session_start,
    consume_mcp_authorization,
    issue_execution_lease,
    reconcile_execution_lease_state,
    require_execution_lease,
)
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


def _issue_thread_lease(svc, project, thread_id):
    assertion = assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": thread_id},
        str(Path(svc.tausik_dir()).resolve().parent),
        trusted_host="cursor",
    )
    reconcile_execution_lease_state(svc, assertion)
    return issue_execution_lease(svc, assertion)


def _start_with_lease(svc, slug, lease_id):
    svc.task_update(
        slug,
        goal=f"deliver {slug}",
        acceptance_criteria="AC-1 works. Negative: stale state is refused.",
        scope=f"scripts/{slug}.py",
        rollback_plan="revert",
        complexity="medium",
    )
    svc.task_start(slug, include_memory=False, execution_lease_id=lease_id)


def test_obsolete_close_releases_the_same_thread_for_its_next_task(svc, tmp_path):
    lease = _issue_thread_lease(svc, tmp_path, "thread-a")
    _start_with_lease(svc, "stale", lease["id"])
    lease = svc.be._execution_lease_by_nonce(lease["nonce"])
    old_arguments = {"slug": "stale", "message": "old pending write"}
    authorize_mcp_mutation(svc, lease=lease, route="tausik_task_log", arguments=old_arguments)

    close_obsolete(svc, "stale", REASON)

    released = svc.be._execution_lease_by_nonce(lease["nonce"])
    assert released["task_slug"] is None
    assert released["task_package_fingerprint"] is None
    validated = require_execution_lease(
        svc,
        project_dir=str(Path(svc.tausik_dir()).resolve().parent),
        host_instance="cursor",
        thread_id="thread-a",
        nonce=lease["nonce"],
    )
    svc.story_add("e", "next-story", "Next story")
    authorize_mcp_mutation(
        svc,
        lease=validated,
        route="tausik_task_add",
        arguments={"story": "next-story", "slug": "next", "title": "Next"},
    )
    consume_mcp_authorization(
        svc,
        route="tausik_task_add",
        arguments={"story": "next-story", "slug": "next", "title": "Next"},
    )
    svc.task_add("next-story", "next", "Next")
    _start_with_lease(svc, "next", lease["id"])
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["task_slug"] == "next"
    with pytest.raises(ExecutionLeaseError, match="IDENTITY_MISSING"):
        consume_mcp_authorization(svc, route="tausik_task_log", arguments=old_arguments)


def test_obsolete_close_does_not_unbind_another_threads_active_task(svc, tmp_path):
    lease_a = _issue_thread_lease(svc, tmp_path, "thread-a")
    _start_with_lease(svc, "stale", lease_a["id"])
    svc.task_add("s", "other", "Other")
    lease_b = _issue_thread_lease(svc, tmp_path, "thread-b")
    _start_with_lease(svc, "other", lease_b["id"])

    close_obsolete(svc, "stale", REASON)

    released = require_execution_lease(
        svc,
        project_dir=str(Path(svc.tausik_dir()).resolve().parent),
        host_instance="cursor",
        thread_id="thread-a",
        nonce=lease_a["nonce"],
        allow_package_rebind=True,
    )
    authorize_mcp_mutation(
        svc,
        lease=released,
        route="tausik_task_add",
        arguments={"story": "s", "slug": "next", "title": "Next"},
    )
    consume_mcp_authorization(
        svc,
        route="tausik_task_add",
        arguments={"story": "s", "slug": "next", "title": "Next"},
    )
    svc.task_add("s", "next", "Next")
    _start_with_lease(svc, "next", lease_a["id"])
    assert svc.be._execution_lease_by_nonce(lease_a["nonce"])["task_slug"] == "next"
    assert svc.be._execution_lease_by_nonce(lease_b["nonce"])["task_slug"] == "other"


def test_obsolete_close_rolls_back_lease_release_on_failure(svc, tmp_path, monkeypatch):
    lease = _issue_thread_lease(svc, tmp_path, "thread-a")
    _start_with_lease(svc, "stale", lease["id"])
    lease = svc.be._execution_lease_by_nonce(lease["nonce"])
    arguments = {"slug": "stale", "message": "still valid after rollback"}
    authorize_mcp_mutation(svc, lease=lease, route="tausik_task_log", arguments=arguments)
    unbind = svc.be._execution_lease_unbind_task

    def fail_after_unbind(task_slug, changed_at):
        unbind(task_slug, changed_at)
        raise RuntimeError("injected failure after lease release")

    monkeypatch.setattr(svc.be, "_execution_lease_unbind_task", fail_after_unbind)
    with pytest.raises(RuntimeError, match="injected failure"):
        close_obsolete(svc, "stale", REASON)

    assert svc.be.task_get("stale")["status"] == "active"
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["task_slug"] == "stale"
    consume_mcp_authorization(svc, route="tausik_task_log", arguments=arguments)


def test_task_done_refuses_a_task_that_never_started(svc):
    """task-done-closes-a-task-that-never-started: planning -> done skipped QG-0
    and left no started_at. NEGATIVE: full evidence does not help."""
    svc.task_log("stale", "AC-1: ✓ manual: checked the thing by hand, it works")
    with pytest.raises(ServiceError, match="was never started") as exc:
        svc.task_done("stale", ac_verified=True)
    assert "task obsolete stale" in str(exc.value)
    assert svc.be.task_get("stale")["status"] == "planning"


class TestTheRefusalSurvivesTheTree:
    """A refusal that does not reach `tausik/tasks/` is a refusal nobody will read.

    The record lived only in the database: `state_export` never selected
    `resolution` or `resolution_reason`, so in the tracked tree a task refused as
    unnecessary was `status: done` and nothing else -- indistinguishable from one
    that shipped. MEASURED before the fix: the database held 1617 delivered plus 3
    obsolete, and all 1620 task files said `done` with no trace of the difference.

    WHY THE ROUND-TRIP GATE WAS GREEN THROUGHOUT: it re-serializes the database and
    byte-compares the result to the tree, so both sides of the comparison come from
    the same exporter. A column the exporter never selects cannot appear on either
    side. The gate is structurally unable to see an omission, which is why this
    pair needs a test that names the two fields.
    """

    def test_an_obsolete_close_reaches_the_tree_with_its_reason(self, svc):
        from state_export import build_tree

        close_obsolete(svc, "stale", REASON)
        tree, _ = build_tree(svc)
        doc = tree["tasks/stale.md"]
        assert "resolution: obsolete" in doc
        assert REASON in doc

    def test_a_delivered_task_is_told_apart_from_a_refused_one(self, svc):
        """Both are `status: done`, so the distinction has to be somewhere else.

        The delivered task carries the keys with no value. Empty rather than absent
        is the point: a missing line means the exporter dropped the field, which is
        exactly how this pair went unnoticed for two releases.
        """
        from state_export import build_tree

        close_obsolete(svc, "stale", REASON)
        tree, _ = build_tree(svc)
        delivered, refused = tree["tasks/delivered.md"], tree["tasks/stale.md"]
        assert "status: done" in delivered and "status: done" in refused
        assert "resolution:" in delivered and "resolution: obsolete" not in delivered
        assert "resolution: obsolete" in refused

    def test_the_reason_comes_back_on_import(self, svc, tmp_path):
        """Export then import: the refusal has to survive the clone, not just the write.

        A field written but never read back is lost on the first `git pull` followed
        by `tausik sync`, which is the path a second machine takes.
        """
        import state_import
        from state_export import build_tree
        from state_serialize import write_tree

        close_obsolete(svc, "stale", REASON)
        tree, _ = build_tree(svc)
        root = tmp_path / "tree"
        # The exporter's own writer, not `write_text`: on Windows the default
        # newline translation appends a carriage return to the `---` fence and the
        # parser rejects the file, failing this test for the wrong reason.
        write_tree(str(root), tree)

        fresh = ProjectService(SQLiteBackend(str(tmp_path / "fresh.db")))
        try:
            state_import.import_tree(fresh, str(root))
            back = fresh.be.task_get("stale")
            assert back["resolution"] == "obsolete"
            assert back["resolution_reason"] == REASON
        finally:
            fresh.be.close()
