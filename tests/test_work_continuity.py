"""Progress evidence and live-task continuity policy."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from project_backend import SQLiteBackend
from project_service import ProjectService
from service_execution_lease import (
    ExecutionLeaseError,
    assertion_from_session_start,
    authorize_mcp_mutation,
    issue_execution_lease,
    reconcile_execution_lease_state,
    require_execution_lease,
)
from tausik_utils import utcnow_iso
from work_continuity import ContinuityError, continuity_projection, enforce_continuity_boundary


@pytest.fixture(autouse=True)
def _arm_unattended_budget_guard(monkeypatch):
    monkeypatch.setenv("TAUSIK_AUTONOMOUS_BUDGET_BLOCK", "1")


def _strict_project(tmp_path, *, budget=10):
    project = tmp_path / "project"
    svc = ProjectService(SQLiteBackend(str(project / ".tausik" / "tausik.db")))
    svc.task_add(None, "work", "Work", complexity="complex", call_budget=budget)
    svc.task_update(
        "work",
        goal="deliver bounded continuity",
        acceptance_criteria="AC-1 progress has evidence. Negative: claims alone are refused.",
        scope="scripts and tests",
        scope_exclude="unrelated files",
        scope_paths=["scripts/work.py"],
        scope_tools=["apply_patch"],
        relevant_files=json.dumps(["scripts/work.py", "tests/test_work.py"]),
        rollback_plan="revert the continuity change",
        assurance_profiles=["executable"],
        assurance_impact={
            "level": "high",
            "blast_radius": "broad",
            "reversibility": "reversible",
            "governance_boundary": True,
        },
    )
    svc.task_plan("work", ["implement", "verify"])
    assertion = assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": "thread-a"},
        str(project),
        trusted_host="codex",
    )
    reconcile_execution_lease_state(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.task_start("work", execution_lease_id=lease["id"])
    return svc, project, svc.be._execution_lease_by_nonce(lease["nonce"])


def _seed_legacy_recovery(svc, lease, requirement):
    fingerprint = svc.be._q1(
        "SELECT fingerprint FROM task_context_packages WHERE task_slug='work'"
    )["fingerprint"]
    svc.be._ex(
        "INSERT INTO task_continuity_state("
        "task_slug,package_fingerprint,pending_requirement,recovery_lease_id,"
        "recovery_issued_at,updated_at) VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(task_slug) DO UPDATE SET "
        "package_fingerprint=excluded.package_fingerprint,"
        "pending_requirement=excluded.pending_requirement,"
        "recovery_lease_id=excluded.recovery_lease_id,"
        "recovery_issued_at=excluded.recovery_issued_at,updated_at=excluded.updated_at",
        ("work", fingerprint, requirement, lease["id"], utcnow_iso(), utcnow_iso()),
    )


def test_strict_step_requires_non_log_immutable_evidence_and_writes_atomically(tmp_path):
    svc, _project, _lease = _strict_project(tmp_path)
    try:
        before = svc.task_show("work")["plan"]
        with pytest.raises(ContinuityError, match="STEP_EVIDENCE_REQUIRED"):
            svc.task_step("work", 1)
        with pytest.raises(ContinuityError, match="STEP_EVIDENCE_INVALID"):
            svc.task_step("work", 1, "log:1")
        assert svc.task_show("work")["plan"] == before
        assert svc.be._q("SELECT * FROM task_step_evidence") == []

        svc.reasoning_step_add("work", "action", "implemented bounded transaction")
        message = svc.task_step("work", 1, "reason:1")

        assert "reason:1" in message
        assert json.loads(svc.task_show("work")["plan"])[0]["done"] is True
        evidence = svc.be._q("SELECT * FROM task_step_evidence")
        assert len(evidence) == 1 and evidence[0]["evidence_ref"] == "reason:1"
        assert continuity_projection(svc.be, "work")["first_incomplete_step"] == 2
    finally:
        svc.be.close()


def test_duplicate_and_concurrent_step_delivery_is_idempotent(tmp_path):
    svc, _project, _lease = _strict_project(tmp_path)
    db_path = svc.be.db_path
    svc.reasoning_step_add("work", "verification", "verified behavior")
    svc.be.close()

    def close_step():
        local = ProjectService(SQLiteBackend(db_path))
        try:
            return local.task_step("work", 1, "reason:1")
        finally:
            local.be.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: close_step(), range(2)))
    check = ProjectService(SQLiteBackend(db_path))
    try:
        assert all("Step 1 done" in result for result in results)
        assert len(check.be._q("SELECT * FROM task_step_evidence")) == 1
    finally:
        check.be.close()


@pytest.mark.parametrize("actual", [9, 10, 11, 40, 114, 200, 272, 400])
def test_call_estimates_are_advisory_in_an_armed_live_task(tmp_path, actual):
    svc, _project, lease = _strict_project(tmp_path, budget=10)
    try:
        svc.be.meta_set("tool_calls:work", str(actual))
        result = enforce_continuity_boundary(
            svc, lease, "tausik_task_log", {"slug": "work", "message": "continue"}
        )
        assert result is None
        assert continuity_projection(svc.be, "work").get("pending_requirement") is None
    finally:
        svc.be.close()


@pytest.mark.parametrize("requirement", ["call_budget_exhausted", "checkpoint_required"])
def test_armed_upgrade_retires_legacy_call_count_recovery(tmp_path, requirement):
    svc, _project, lease = _strict_project(tmp_path, budget=1)
    try:
        _seed_legacy_recovery(svc, lease, requirement)
        assert (
            enforce_continuity_boundary(
                svc, lease, "tausik_task_log", {"slug": "work", "message": "continue"}
            )
            is None
        )
        state = svc.be._q1(
            "SELECT pending_requirement,recovery_lease_id,blocker_json "
            "FROM task_continuity_state WHERE task_slug='work'"
        )
        assert state == {
            "pending_requirement": None,
            "recovery_lease_id": None,
            "blocker_json": None,
        }
    finally:
        svc.be.close()


def test_codex_write_gate_allows_apply_patch_past_call_estimate(tmp_path):
    from hooks.codex_write_gate import check_event

    svc, project, _lease = _strict_project(tmp_path, budget=1)
    try:
        svc.be.meta_set("tool_calls:work", "400")
        event = {
            "session_id": "thread-a",
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: scripts/work.py\n@@\n-old\n+new\n*** End Patch"
            },
        }
        assert check_event(event, str(project)) == 0
    finally:
        svc.be.close()


def test_normal_mutation_still_rejects_a_stale_package(tmp_path):
    svc, project, lease = _strict_project(tmp_path)
    try:
        svc.task_update("work", goal="package changed")
        with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE"):
            require_execution_lease(
                svc,
                project_dir=str(project),
                host_instance="codex",
                thread_id="thread-a",
                nonce=lease["nonce"],
            )
    finally:
        svc.be.close()


def test_task_start_rebinds_stale_package_and_clears_legacy_recovery(tmp_path):
    svc, project, lease = _strict_project(tmp_path, budget=1)
    try:
        _seed_legacy_recovery(svc, lease, "call_budget_exhausted")
        svc.task_update("work", goal="changed while legacy recovery is pending")

        recoverable = require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=lease["nonce"],
            allow_package_rebind=True,
        )
        authorize_mcp_mutation(
            svc,
            lease=recoverable,
            route="tausik_task_start",
            arguments={"slug": "work"},
        )
        assert "resumed" in svc.task_start(
            "work", include_memory=False, execution_lease_id=recoverable["id"]
        )
        assert continuity_projection(svc.be, "work").get("pending_requirement") is None
    finally:
        svc.be.close()


def test_handoff_projection_contains_copy_ready_resume_state(tmp_path):
    svc, _project, _lease = _strict_project(tmp_path)
    try:
        svc.reasoning_step_add("work", "action", "implemented")
        svc.task_step("work", 1, "reason:1")
        projection = continuity_projection(svc.be, "work")
        assert projection["package_fingerprint"]
        assert projection["first_incomplete_step"] == 2
        assert projection["last_verified_evidence"] == "reason:1"
        assert projection["resume_action"] == ".tausik/tausik task start work --package"
    finally:
        svc.be.close()
