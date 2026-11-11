"""Host-context lifecycle policy: real thread identity, ceilings and degradation."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import service_host_context as policy
from project_backend import SQLiteBackend
from project_service import ProjectService
from service_execution_lease import (
    assertion_from_session_start,
    issue_execution_lease,
    reconcile_execution_lease_state,
)
from tausik_utils import ServiceError


@pytest.fixture
def svc(tmp_path):
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    yield service
    service.be.close()


def measured(responses=1, input_tokens=100, context_tokens=50):
    return {
        "availability": "native",
        "responses": responses,
        "input_tokens": input_tokens,
        "context_tokens": context_tokens,
    }


def test_same_thread_reopen_is_not_fresh_but_a_new_thread_is(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    first = policy.open_session(svc, host="codex", thread_id="thread-a", usage=measured())
    reopened = policy.open_session(svc, host="codex", thread_id="thread-a", usage=measured())
    another = policy.open_session(svc, host="codex", thread_id="thread-b", usage=measured())

    assert first["host_context"]["fresh_context"] is True
    assert reopened["host_context"]["reopened"] is True
    assert reopened["host_context"]["fresh_context"] is False
    assert reopened["session"]["id"] == first["session"]["id"]
    assert another["host_context"]["fresh_context"] is True
    assert another["session"]["id"] != first["session"]["id"]


def test_advisory_saves_one_checkpoint_and_returns_a_new_window_prompt(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    usage = measured(responses=24)
    result = policy.open_session(svc, host="codex", thread_id="thread-a", usage=usage)
    repeated = policy.open_session(svc, host="codex", thread_id="thread-a", usage=usage)
    handoff = svc.session_last_handoff(result["session"]["id"])

    assert result["host_context"]["level"] == "advisory"
    assert result["host_context"]["checkpoint_saved"] is True
    assert repeated["host_context"]["checkpoint_saved"] is False
    assert result["host_context"]["fresh_window_prompt"] in handoff["next_steps"]


def test_hard_ceiling_refuses_an_old_unbound_thread_and_stops_a_bound_one(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    hard = measured(responses=32)
    refused = policy.open_session(svc, host="codex", thread_id="old-thread", usage=hard)
    policy.open_session(svc, host="codex", thread_id="bound-thread", usage=measured())
    stopped = policy.open_session(svc, host="codex", thread_id="bound-thread", usage=hard)

    assert refused["session"]["ended_at"] is not None
    assert svc.be.session_current("old-thread") is None
    assert refused["host_context"]["allow_continue"] is False
    assert stopped["host_context"]["allow_continue"] is False
    assert stopped["host_context"]["checkpoint_saved"] is True


def test_hard_ceiling_revokes_live_lease_and_checkpoints_only_once(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    project = os.path.dirname(svc.tausik_dir())
    assertion = assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": "thread-a"},
        project,
        trusted_host="codex",
    )
    reconcile_execution_lease_state(svc, assertion)
    lease = issue_execution_lease(svc, assertion)

    first = policy.open_session(
        svc, host="codex", thread_id="thread-a", usage=measured(responses=32)
    )
    repeated = policy.open_session(
        svc, host="codex", thread_id="thread-a", usage=measured(responses=32)
    )

    assert first["host_context"]["checkpoint_saved"] is True
    assert repeated["host_context"]["checkpoint_saved"] is False
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is not None
    assert svc.be.session_current("thread-a") is None


def test_pretool_boundary_rejects_old_thread_after_hard_ceiling(svc, monkeypatch):
    hooks_dir = os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks")
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    import execution_lease_gate

    project = os.path.dirname(svc.tausik_dir())
    assertion = assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": "thread-a"},
        project,
        trusted_host="codex",
    )
    reconcile_execution_lease_state(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    monkeypatch.setattr(policy, "_usage", lambda *_args: measured(responses=32))

    allowed, reason = execution_lease_gate.require_live_lease({"session_id": "thread-a"}, project)

    assert allowed is False
    assert "HOST_CONTEXT_HARD" in reason
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is not None


@pytest.mark.parametrize("lease_state", ["live", "expired"])
def test_hard_ceiling_persists_copy_ready_handoff_without_reopening_old_thread(
    svc, monkeypatch, lease_state
):
    hooks_dir = os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks")
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    import execution_lease_gate
    from can_stop import decide_persisted_stop, record_trusted_turn

    project = os.path.dirname(svc.tausik_dir())
    assertion = assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": "thread-a"},
        project,
        trusted_host="codex",
    )
    reconcile_execution_lease_state(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.task_add(None, "resume-work", "Resume work", complexity="simple")
    svc.task_update(
        "resume-work",
        goal="Persist recovery state",
        acceptance_criteria=(
            "A fresh thread can resume the active task. "
            "Negative: ordinary writes stay blocked in the old thread."
        ),
    )
    svc.task_start("resume-work", include_memory=False, execution_lease_id=lease["id"])
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    advisory = policy.open_session(
        svc, host="codex", thread_id="thread-a", usage=measured(responses=24)
    )
    assert advisory["host_context"]["level"] == "advisory"
    assert advisory["host_context"]["checkpoint_saved"] is True
    monkeypatch.setattr(policy, "_usage", lambda *_args: measured(responses=32))
    event = {"hook_event_name": "PreToolUse", "session_id": "thread-a"}
    record_trusted_turn(
        svc,
        project_dir=project,
        host_instance="codex",
        thread_id="thread-a",
        turn_id="turn-1",
        prompt="save the unfinished work",
        payload={"session_id": "thread-a", "turn_id": "turn-1"},
    )
    first_stop = decide_persisted_stop(
        svc, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )
    assert first_stop.code == "CONTINUE"
    if lease_state == "expired":
        svc.be._ex(
            "UPDATE execution_leases SET expires_at='2000-01-01T00:00:00Z' WHERE id=?",
            (lease["id"],),
        )
    write_allowed, write_reason = execution_lease_gate.require_live_lease(
        event,
        project,
        route="codex_implementation_write",
        arguments={"tool": "Write", "payload_sha256": "x"},
        authorize=False,
    )
    assert write_allowed is False
    assert "HOST_CONTEXT_HARD" in write_reason
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is not None
    expected = ".tausik/tausik task start resume-work --package"
    repeated_stop = decide_persisted_stop(
        svc, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )
    assert repeated_stop.code == "ALLOW_HANDOFF"
    assert repeated_stop.action == expected
    assert expected in str(svc.session_last_handoff(lease["session_id"]))
    assert svc.be.meta_get(f"host_context_hard_lease:{lease['id']}") == expected
    assert svc.be.session_current("thread-a") is None

    for route in ("tausik_session_handoff", "cli_session_handoff", "tausik_task_log"):
        allowed, reason = execution_lease_gate.require_live_lease(
            event,
            project,
            route=route,
            arguments={},
        )
        assert allowed is False
        assert "HOST_CONTEXT_HARD" in reason
    mixed_allowed, mixed_reason = execution_lease_gate.require_live_lease(
        event,
        project,
        requests=[
            ("tausik_task_done", {"slug": "resume-work", "ac_verified": True}),
            ("tausik_session_handoff", {}),
        ],
    )
    assert mixed_allowed is False
    assert "HOST_CONTEXT_HARD" in mixed_reason
    assert svc.be.session_current("thread-a") is None


def test_pretool_boundary_allows_only_task_done_after_hard_ceiling(svc, monkeypatch):
    hooks_dir = os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks")
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    import execution_lease_gate
    from can_stop import decide_persisted_stop, record_trusted_turn

    mcp_dir = os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)
    from handlers import handle_tool

    project = os.path.dirname(svc.tausik_dir())
    assertion = assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": "thread-a"},
        project,
        trusted_host="codex",
    )
    reconcile_execution_lease_state(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.task_add(None, "stop-work", "Stop work", complexity="simple")
    svc.task_update(
        "stop-work",
        goal="Close verified work",
        acceptance_criteria="Closure succeeds. Negative: unfinished work stays active.",
    )
    svc.task_plan("stop-work", ["finish the verified work"])
    svc.task_start("stop-work", include_memory=False, execution_lease_id=lease["id"])
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    monkeypatch.setattr(policy, "_usage", lambda *_args: measured(responses=32))
    monkeypatch.setenv("TAUSIK_ENFORCE_EXECUTION_LEASE", "1")

    event = {"hook_event_name": "PreToolUse", "session_id": "thread-a"}
    record_trusted_turn(
        svc,
        project_dir=project,
        host_instance="codex",
        thread_id="thread-a",
        turn_id="turn-1",
        prompt="close the verified task",
        payload={"session_id": "thread-a", "turn_id": "turn-1"},
    )
    first_stop = decide_persisted_stop(
        svc, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )
    assert first_stop.code == "CONTINUE"
    incomplete_args = {"slug": "stop-work", "ac_verified": True, "full_path": True}
    incomplete_authorizations = []
    incomplete_allowed, incomplete_reason = execution_lease_gate.require_live_lease(
        event,
        project,
        route="tausik_task_done",
        arguments=incomplete_args,
        authorization_tokens=incomplete_authorizations,
        correlate_authorizations=True,
    )
    assert incomplete_allowed, incomplete_reason
    incomplete = json.loads(
        handle_tool(
            svc,
            "tausik_task_done",
            incomplete_args,
            authorization=incomplete_authorizations[0],
        )
    )
    assert incomplete["ok"] is False
    assert incomplete["blocking_failures"][0]["stage"] == "ac"
    assert svc.task_show("stop-work")["status"] == "active"
    svc.task_step("stop-work", 1, "verified work finished")
    svc.task_start("stop-work", include_memory=False, execution_lease_id=lease["id"])

    close_args = {
        "slug": "stop-work",
        "ac_verified": True,
        "full_path": True,
        "evidence": "AC-1: ✓ closure succeeds. AC-2: ✓ unfinished work is refused.",
    }
    authorizations = []
    close_allowed, close_reason = execution_lease_gate.require_live_lease(
        event,
        project,
        route="tausik_task_done",
        arguments=close_args,
        authorization_tokens=authorizations,
        correlate_authorizations=True,
    )
    assert close_allowed, close_reason
    assert len(authorizations) == 1
    handle_tool(
        svc,
        "tausik_task_done",
        close_args,
        authorization=authorizations[0],
    )
    repeated_stop = decide_persisted_stop(
        svc, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )
    write_allowed, write_reason = execution_lease_gate.require_live_lease(
        event,
        project,
        route="codex_implementation_write",
        arguments={"tool": "Write", "payload_sha256": "x"},
        authorize=False,
    )

    assert svc.task_show("stop-work")["status"] == "done"
    assert repeated_stop.code == "ALLOW_DONE"
    assert write_allowed is False
    assert "HOST_CONTEXT_HARD" in write_reason


def test_hard_ceiling_checkpoints_a_legacy_unbound_session_without_reopening_it(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    svc.session_start()
    legacy_id = svc.session_current()["id"]

    result = policy.open_session(
        svc, host="codex", thread_id="old-thread", usage=measured(responses=32)
    )

    assert result["session"]["id"] == legacy_id
    assert result["host_context"]["checkpoint_saved"] is True
    assert result["host_context"]["allow_continue"] is False
    assert svc.be.session_current("old-thread") is None


def test_missing_native_usage_is_explicit_and_never_claims_fresh_context(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    result = policy.open_session(
        svc,
        host="claude",
        thread_id="thread-a",
        usage={"availability": "unavailable", "reason": "no native signal"},
    )

    assert result["host_context"]["level"] == "unavailable"
    assert result["host_context"]["fresh_context"] is False
    assert result["host_context"]["usage"]["reason"]


@pytest.mark.parametrize(
    "config",
    [
        {"host_context_budget": {"advisory": {"responses": 0}}},
        {
            "host_context_budget": {
                "advisory": {"responses": 40},
                "hard": {"responses": 32},
            }
        },
    ],
)
def test_invalid_budget_configuration_fails_before_opening_a_session(svc, monkeypatch, config):
    monkeypatch.setattr(policy, "load_config", lambda _path: config)
    with pytest.raises(ServiceError):
        policy.open_session(svc, host="codex", thread_id="thread-a", usage=measured())
    assert svc.be.session_current("thread-a") is None
