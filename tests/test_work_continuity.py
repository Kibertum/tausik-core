"""Durable continuity makes progress evidence-bound and recovery bounded."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

import pytest

from project_backend import SQLiteBackend
from project_service import ProjectService
from service_execution_lease import (
    assertion_from_session_start,
    authorize_mcp_mutation,
    consume_mcp_authorization,
    issue_execution_lease,
    reconcile_execution_lease_state,
)
from work_continuity import (
    ContinuityError,
    _action_hash,
    complete_recovery,
    continuity_projection,
    enforce_continuity_boundary,
    require_recovery_generation,
)


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
        assert json.loads(check.task_show("work")["plan"])[0]["done"] is True
    finally:
        check.be.close()


@pytest.mark.parametrize(("actual", "blocked"), [(9, False), (10, True), (11, True)])
def test_call_budget_boundary_is_exact(tmp_path, actual, blocked):
    svc, _project, lease = _strict_project(tmp_path, budget=10)
    try:
        svc.be.meta_set("tool_calls:work", str(actual))
        action = {"slug": "work", "message": "continue"}
        if blocked:
            with pytest.raises(ContinuityError, match="CONTINUITY_RECOVERY_REQUIRED"):
                enforce_continuity_boundary(svc, lease, "tausik_task_log", action)
        else:
            enforce_continuity_boundary(svc, lease, "tausik_task_log", action)
    finally:
        svc.be.close()


@pytest.mark.parametrize(("calls", "blocked"), [(39, False), (40, True), (41, True)])
def test_checkpoint_boundary_is_exact(tmp_path, monkeypatch, calls, blocked):
    svc, _project, lease = _strict_project(tmp_path, budget=100)
    try:
        monkeypatch.setattr("checkpoint_signal.calls_since_checkpoint", lambda _be: calls)
        action = {"slug": "work", "message": "continue"}
        if blocked:
            with pytest.raises(ContinuityError, match="CONTINUITY_RECOVERY_REQUIRED"):
                enforce_continuity_boundary(svc, lease, "tausik_task_log", action)
        else:
            enforce_continuity_boundary(svc, lease, "tausik_task_log", action)
    finally:
        svc.be.close()


def test_checkpoint_boundary_uses_project_configuration(tmp_path, monkeypatch):
    svc, _project, lease = _strict_project(tmp_path, budget=100)
    try:
        monkeypatch.setattr("checkpoint_signal.calls_since_checkpoint", lambda _be: 5)
        monkeypatch.setattr("project_config.load_config", lambda _path: {"checkpoint_calls": 5})
        with pytest.raises(ContinuityError, match="checkpoint_required"):
            enforce_continuity_boundary(
                svc, lease, "tausik_task_log", {"slug": "work", "message": "continue"}
            )
    finally:
        svc.be.close()


def test_budget_recovery_allowlist_forbids_checkpoint_and_consumes_once(tmp_path):
    svc, _project, lease = _strict_project(tmp_path, budget=1)
    try:
        svc.be.meta_set("tool_calls:work", "1")
        with pytest.raises(ContinuityError):
            authorize_mcp_mutation(svc, lease=lease, route="tausik_session_handoff", arguments={})
        authorize_mcp_mutation(
            svc,
            lease=lease,
            route="tausik_task_plan",
            arguments={"slug": "work", "steps": ["split one", "split two"]},
        )
        complete_recovery(
            svc,
            lease,
            "tausik_task_plan",
            {"slug": "work", "steps": ["split one", "split two"]},
        )
        state = svc.be._q1("SELECT * FROM task_continuity_state WHERE task_slug='work'")
        assert state["recovery_consumed_at"] and state["pending_requirement"] is None
        assert svc.be._q1("SELECT revoked_at FROM execution_leases WHERE id=?", (lease["id"],))[
            "revoked_at"
        ]
        assert svc.be._q1("SELECT * FROM task_context_packages WHERE task_slug='work'") is None
        with pytest.raises(ContinuityError, match="RECOVERY_REPLAY"):
            # Restore pending only to exercise the single-use compare-and-set.
            svc.be._ex(
                "UPDATE task_continuity_state SET pending_requirement='call_budget_exhausted' WHERE task_slug='work'"
            )
            complete_recovery(
                svc,
                lease,
                "tausik_task_plan",
                {"slug": "work", "steps": ["split one", "split two"]},
            )
    finally:
        svc.be.close()


def test_override_is_exactly_action_bound_and_refusal_loop_escalates(tmp_path):
    svc, _project, lease = _strict_project(tmp_path, budget=1)
    args = {"slug": "work", "message": "one exact action"}
    try:
        svc.be.meta_set("tool_calls:work", "1")
        svc.reasoning_step_add("work", "action", "generic approval")
        for expected in (
            "CONTINUITY_RECOVERY_REQUIRED",
            "CONTINUITY_RECOVERY_REQUIRED",
            "CONTINUITY_BLOCKED",
        ):
            with pytest.raises(ContinuityError, match=expected):
                enforce_continuity_boundary(svc, lease, "tausik_task_log", args)
        blocker = continuity_projection(svc.be, "work")["blocker"]
        assert blocker["attempts"] == 3 and blocker["requirement"] == "call_budget_exhausted"
    finally:
        svc.be.close()


def test_checkpoint_override_requires_exact_structured_action_reason(tmp_path, monkeypatch):
    svc, _project, lease = _strict_project(tmp_path, budget=100)
    args = {"slug": "work", "message": "one exact action"}
    try:
        monkeypatch.setattr("checkpoint_signal.calls_since_checkpoint", lambda _be: 40)
        payload = {
            "continuity_override": {
                "route": "tausik_task_log",
                "arguments_hash": _action_hash("tausik_task_log", args),
            }
        }
        svc.reasoning_step_add("work", "action", json.dumps(payload, sort_keys=True))

        enforce_continuity_boundary(svc, lease, "tausik_task_log", args)
        complete_recovery(svc, lease, "tausik_task_log", args)

        assert svc.be._q1("SELECT revoked_at FROM execution_leases WHERE id=?", (lease["id"],))[
            "revoked_at"
        ]
    finally:
        svc.be.close()


def test_continuity_state_survives_backend_restart(tmp_path, monkeypatch):
    svc, _project, lease = _strict_project(tmp_path, budget=100)
    db_path = svc.be.db_path
    monkeypatch.setattr("checkpoint_signal.calls_since_checkpoint", lambda _be: 40)
    with pytest.raises(ContinuityError):
        enforce_continuity_boundary(
            svc, lease, "tausik_task_log", {"slug": "work", "message": "blocked"}
        )
    expected = continuity_projection(svc.be, "work")
    svc.be.close()

    restarted = ProjectService(SQLiteBackend(db_path))
    try:
        assert continuity_projection(restarted.be, "work") == expected
    finally:
        restarted.be.close()


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


def test_hook_refusal_for_implementation_write_is_durable_and_escalates(tmp_path):
    svc, project, _lease = _strict_project(tmp_path, budget=1)
    try:
        svc.be.meta_set("tool_calls:work", "1")
        from hooks.execution_lease_gate import require_live_lease

        event = {"session_id": "thread-a"}

        def refuse(_index):
            allowed, error = require_live_lease(
                event,
                str(project),
                route="codex_implementation_write",
                arguments={"tool": "apply_patch", "paths": ["scripts/work.py"]},
            )
            assert allowed is False
            return error

        with ThreadPoolExecutor(max_workers=3) as pool:
            errors = list(pool.map(refuse, range(3)))
        assert sum("CONTINUITY_BLOCKED" in error for error in errors) == 1
        assert sum("CONTINUITY_RECOVERY_REQUIRED" in error for error in errors) == 2
        state = svc.be._q1(
            "SELECT refusal_count,blocker_json FROM task_continuity_state WHERE task_slug='work'"
        )
        assert state["refusal_count"] == 3
        assert json.loads(state["blocker_json"])["attempts"] == 3
    finally:
        svc.be.close()


def test_step_rejects_authorization_bound_to_stale_package(tmp_path):
    svc, _project, lease = _strict_project(tmp_path)
    try:
        svc.reasoning_step_add("work", "action", "implemented")
        svc._authorized_execution_lease = {**lease, "task_package_fingerprint": "stale"}
        with pytest.raises(ContinuityError, match="PACKAGE_STALE"):
            svc.task_step("work", 1, "reason:1")
        assert svc.be._q("SELECT * FROM task_step_evidence") == []
    finally:
        svc.be.close()


def test_budget_decomposition_creates_runnable_children_and_parks_parent(tmp_path):
    svc, _project, lease = _strict_project(tmp_path, budget=1)
    try:
        svc.be.meta_set("tool_calls:work", "1")
        arguments = {"slug": "work", "steps": ["part alpha", "part beta"]}
        authorize_mcp_mutation(svc, lease=lease, route="tausik_task_plan", arguments=arguments)
        svc.task_plan("work", arguments["steps"])
        complete_recovery(svc, lease, "tausik_task_plan", arguments)

        assert svc.task_show("work")["status"] == "blocked"
        children = set(svc.be._task_deps_of("work"))
        assert len(children) == 2
        for index, child in enumerate(sorted(children), 1):
            task = svc.task_show(child)
            assert task["status"] == "planning"
            assert task["goal"] and task["acceptance_criteria"]
            svc.task_start(child)
            assert svc.task_show(child)["status"] == "active"
            svc.task_block(
                child,
                "QG-0 probe complete.",
                f"May decomposed child {index} remain parked after its start probe?",
                "The test records that QG-0 accepted the child.",
            )
    finally:
        svc.be.close()


def test_cli_recovery_consumes_exact_authorization_before_decomposition(tmp_path, capsys):
    from types import SimpleNamespace

    from project_cli_task_continuity import cmd_task

    svc, _project, lease = _strict_project(tmp_path, budget=1)
    arguments = {"slug": "work", "action": "plan"}
    try:
        svc.be.meta_set("tool_calls:work", "1")
        authorize_mcp_mutation(svc, lease=lease, route="cli_task_mutation", arguments=arguments)
        cmd_task(
            svc,
            SimpleNamespace(slug="work", task_cmd="plan", steps=["part alpha", "part beta"]),
        )

        assert "Plan set" in capsys.readouterr().out
        assert svc.task_show("work")["status"] == "blocked"
        authorization = svc.be._q1(
            "SELECT consumed_at FROM execution_authorizations WHERE route='cli_task_mutation'"
        )
        assert authorization["consumed_at"]
    finally:
        svc.be.close()


def test_decomposition_rejects_preexisting_child_identity(tmp_path):
    svc, _project, lease = _strict_project(tmp_path, budget=1)
    child = f"work-{hashlib.sha256(b'work').hexdigest()[:8]}-part-1"
    try:
        svc.task_add(None, child, "unrelated existing task", complexity="simple")
        svc.be.meta_set("tool_calls:work", "1")
        arguments = {"slug": "work", "steps": ["part alpha"]}
        authorize_mcp_mutation(svc, lease=lease, route="tausik_task_plan", arguments=arguments)
        svc.task_plan("work", arguments["steps"])
        with pytest.raises(ContinuityError, match="DECOMPOSITION_COLLISION"):
            complete_recovery(svc, lease, "tausik_task_plan", arguments)
        assert svc.task_show("work")["status"] == "active"
    finally:
        svc.be.close()


def test_codex_write_gate_blocks_exhausted_apply_patch_end_to_end(tmp_path):
    from hooks.codex_write_gate import check_event

    svc, project, _lease = _strict_project(tmp_path, budget=1)
    try:
        svc.be.meta_set("tool_calls:work", "1")
        event = {
            "session_id": "thread-a",
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: scripts/work.py\n@@\n-old\n+new\n*** End Patch"
            },
        }
        assert check_event(event, str(project)) == 2
        state = svc.be._q1(
            "SELECT pending_requirement,refusal_count FROM task_continuity_state WHERE task_slug='work'"
        )
        assert state == {"pending_requirement": "call_budget_exhausted", "refusal_count": 1}
    finally:
        svc.be.close()


def test_normal_codex_cli_step_rejects_package_rebind_after_authorization(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from project_cli_task_continuity import cmd_task
    from service_execution_lease import ExecutionLeaseError

    svc, _project, lease = _strict_project(tmp_path)
    other = ProjectService(SQLiteBackend(svc.be.db_path))
    try:
        svc.reasoning_step_add("work", "action", "implemented")
        arguments = {"slug": "work", "action": "step"}
        authorize_mcp_mutation(svc, lease=lease, route="cli_task_mutation", arguments=arguments)
        other.be._ex(
            "UPDATE task_context_packages SET fingerprint='rebound' WHERE task_slug='work'"
        )
        monkeypatch.setenv("TAUSIK_ENFORCE_EXECUTION_LEASE", "1")
        with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE"):
            cmd_task(
                svc,
                SimpleNamespace(
                    slug="work",
                    task_cmd="step",
                    step_num=1,
                    evidence="reason:1",
                    message=None,
                ),
            )
        assert svc.be._q("SELECT * FROM task_step_evidence") == []
    finally:
        other.be.close()
        svc.be.close()


def test_cli_terminal_action_crossing_boundary_consumes_recovery_lease(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from project_cli_task_continuity import cmd_task
    from service_execution_lease import consume_mcp_authorization

    svc, _project, lease = _strict_project(tmp_path, budget=1)
    arguments = {"slug": "work", "action": "plan"}
    try:
        authorize_mcp_mutation(svc, lease=lease, route="cli_task_mutation", arguments=arguments)

        def cross_boundary(*args, **kwargs):
            svc.be.meta_set("tool_calls:work", "1")
            return consume_mcp_authorization(*args, **kwargs)

        monkeypatch.setattr("service_execution_lease.consume_mcp_authorization", cross_boundary)
        monkeypatch.setenv("TAUSIK_ENFORCE_EXECUTION_LEASE", "1")
        cmd_task(
            svc,
            SimpleNamespace(slug="work", task_cmd="plan", steps=["part alpha"]),
        )

        assert svc.task_show("work")["status"] == "blocked"
        assert len(svc.be._task_deps_of("work")) == 1
        assert svc.be._q1("SELECT revoked_at FROM execution_leases WHERE id=?", (lease["id"],))[
            "revoked_at"
        ]
        assert svc.be._q1("SELECT * FROM task_context_packages WHERE task_slug='work'") is None
    finally:
        svc.be.close()


def test_two_authorized_recovery_actions_commit_exactly_one_mutation(tmp_path):
    svc, _project, lease = _strict_project(tmp_path, budget=1)
    other = ProjectService(SQLiteBackend(svc.be.db_path))
    plan_args = {"slug": "work", "steps": ["winner part"]}
    block_args = {
        "slug": "work",
        "reason": "loser mutation",
        "question": "Should the losing recovery action be discarded?",
        "unblock_criteria": "The winning generation is the only committed action.",
    }
    try:
        svc.be.meta_set("tool_calls:work", "1")
        authorize_mcp_mutation(svc, lease=lease, route="tausik_task_plan", arguments=plan_args)
        authorize_mcp_mutation(svc, lease=lease, route="tausik_task_block", arguments=block_args)
        plan_lease = consume_mcp_authorization(svc, route="tausik_task_plan", arguments=plan_args)
        block_lease = consume_mcp_authorization(
            other, route="tausik_task_block", arguments=block_args
        )
        plan_generation = enforce_continuity_boundary(
            svc, plan_lease, "tausik_task_plan", plan_args
        )
        block_generation = enforce_continuity_boundary(
            other, block_lease, "tausik_task_block", block_args
        )
        assert plan_generation is not None and plan_generation == block_generation
        assert block_generation is not None

        with svc.be.transaction():
            require_recovery_generation(svc, plan_lease, plan_generation)
            svc.task_plan("work", plan_args["steps"])
            complete_recovery(svc, plan_lease, "tausik_task_plan", plan_args, plan_generation)
        with pytest.raises(ContinuityError, match="RECOVERY_REPLAY"):
            with other.be.transaction():
                require_recovery_generation(other, block_lease, block_generation)
                other.task_block(
                    "work",
                    block_args["reason"],
                    block_args["question"],
                    block_args["unblock_criteria"],
                )
                complete_recovery(
                    other,
                    block_lease,
                    "tausik_task_block",
                    block_args,
                    block_generation,
                )
        assert "loser mutation" not in (svc.task_show("work").get("notes") or "")
        assert len(svc.be._task_deps_of("work")) == 1
    finally:
        other.be.close()
        svc.be.close()


def test_consumed_recovery_cannot_fall_back_to_normal_authority(tmp_path):
    svc, _project, lease = _strict_project(tmp_path, budget=1)
    other = ProjectService(SQLiteBackend(svc.be.db_path))
    plan_args = {"slug": "work", "steps": ["winner part"]}
    block_args = {"slug": "work", "question": "loser", "unblock_criteria": "never"}
    try:
        svc.be.meta_set("tool_calls:work", "1")
        authorize_mcp_mutation(svc, lease=lease, route="tausik_task_plan", arguments=plan_args)
        authorize_mcp_mutation(svc, lease=lease, route="tausik_task_block", arguments=block_args)
        plan_lease = consume_mcp_authorization(svc, route="tausik_task_plan", arguments=plan_args)
        block_lease = consume_mcp_authorization(
            other, route="tausik_task_block", arguments=block_args
        )
        generation = enforce_continuity_boundary(svc, plan_lease, "tausik_task_plan", plan_args)
        assert generation is not None
        with svc.be.transaction():
            require_recovery_generation(svc, plan_lease, generation)
            svc.task_plan("work", plan_args["steps"])
            complete_recovery(svc, plan_lease, "tausik_task_plan", plan_args, generation)

        with pytest.raises(ContinuityError, match="PACKAGE_STALE|RECOVERY_LEASE_STALE"):
            enforce_continuity_boundary(other, block_lease, "tausik_task_block", block_args)
        assert "loser" not in (svc.task_show("work").get("notes") or "")
    finally:
        other.be.close()
        svc.be.close()
