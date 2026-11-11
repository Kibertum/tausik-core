"""Trusted Stop policy: durable turn binding, replay safety, and native fail-closed output."""

from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from can_stop import (
    StopState,
    can_stop,
    classify_native_stop_verdict,
    classify_request,
    decide_persisted_stop,
    record_attempt_event,
    record_trusted_turn,
    run_native_stop_probe,
)
from project_backend import SQLiteBackend
from project_service import ProjectService
from service_execution_lease import (
    assertion_from_session_start,
    issue_execution_lease,
    reconcile_execution_lease_state,
)
from tausik_utils import utcnow_iso
from tausik_utils import ServiceError


HOOK = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "can_stop_gate.py"
PROMPT_HOOK = HOOK.with_name("user_prompt_submit.py")


@pytest.fixture
def bound_service(tmp_path):
    project = tmp_path / "project"
    backend = SQLiteBackend(str(project / ".tausik" / "tausik.db"))
    service = ProjectService(backend)
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assertion = assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": "thread-a"},
        str(project),
        trusted_host="codex",
        now=now,
    )
    reconcile_execution_lease_state(service, assertion)
    lease = issue_execution_lease(service, assertion, now=now)
    stamp = utcnow_iso()
    service.be._ex(
        "INSERT INTO tasks(slug,title,status,complexity,goal,plan,acceptance_criteria,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (
            "stop-work",
            "Stop work",
            "active",
            "complex",
            "Finish the work",
            json.dumps([{"step": "run the negative matrix", "done": False}]),
            "Stop is deterministic",
            stamp,
            stamp,
        ),
    )
    service.be._ex("UPDATE execution_leases SET task_slug=? WHERE id=?", ("stop-work", lease["id"]))
    lease = service.be._q1("SELECT * FROM execution_leases WHERE id=?", (lease["id"],))
    yield service, project, lease
    backend.close()


@pytest.mark.parametrize(
    ("state", "code"),
    [
        (StopState(False, "work", "active", "next"), "ADVISORY_UNTRUSTED"),
        (StopState(True, "read_only", "active", "next"), "ALLOW_READ_ONLY"),
        (StopState(True, "work", "done", None), "ALLOW_DONE"),
        (StopState(True, "work", "blocked", "resume", blocker_verified=True), "ALLOW_BLOCKED"),
        (StopState(True, "work", "active", "resume", handoff_ready=True), "ALLOW_HANDOFF"),
        (StopState(True, "work", "active", "next"), "CONTINUE"),
    ],
)
def test_pure_policy_has_one_typed_verdict_per_state(state, code):
    assert can_stop(state).code == code


@pytest.mark.parametrize(
    ("prompt", "kind"),
    [
        ("", "work"),
        ("Explain how this works", "read_only"),
        ("Покажи статус задачи", "read_only"),
        ("Review this and fix the race", "work"),
        ("Review this and apply the patch", "work"),
        ("Explain then edit the file", "work"),
        ("Show status and deploy it", "work"),
        ("Review: apply the patch", "work"),
        ("Review/fix this", "work"),
        ("Show me how to delete the database", "work"),
        ("Explain while editing the file", "work"),
        ("Review fixing this bug", "work"),
        ("Объясни и исправь ошибку", "work"),
    ],
)
def test_request_classification_cannot_hide_mutation_behind_read_only_prefix(prompt, kind):
    assert classify_request(prompt) == kind


def _record(service, project, prompt="fix the race", turn_id="turn-1"):
    return record_trusted_turn(
        service,
        project_dir=str(project),
        host_instance="codex",
        thread_id="thread-a",
        turn_id=turn_id,
        prompt=prompt,
        payload={"session_id": "thread-a", "turn_id": turn_id, "prompt": prompt},
    )


def test_incomplete_turn_refuses_with_exact_next_plan_action(bound_service):
    service, project, _lease = bound_service
    _record(service, project)

    decision = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert decision.code == "CONTINUE"
    assert decision.action == "complete plan step 1: run the negative matrix"


def test_completed_plan_points_to_first_acceptance_criterion_without_evidence(bound_service):
    service, project, _lease = bound_service
    _record(service, project)
    service.be._ex(
        "UPDATE tasks SET plan=?,acceptance_criteria=?,notes=? WHERE slug='stop-work'",
        (
            json.dumps([{"step": "run the negative matrix", "done": True}]),
            "1. Native failure is covered 2. Resume action is exact",
            "AC-1: ✓ tests/test_can_stop.py::test_native_hook_blocks_malformed_and_missing_durable_turn",
        ),
    )

    decision = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert decision.code == "CONTINUE"
    assert decision.action == "verify acceptance criterion 2: Resume action is exact"


def test_stop_cannot_select_a_turn_from_another_thread_or_replay_one(bound_service):
    service, project, _lease = bound_service
    _record(service, project)

    spoof = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-b", turn_id="turn-1"
    )
    first = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )
    replay = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert spoof.code == "CONTINUE"
    assert first.code == replay.code == "CONTINUE"
    assert replay.action == "complete plan step 1: run the negative matrix"


def test_repeated_stop_allows_a_task_completed_after_continue(bound_service):
    service, project, _lease = bound_service
    _record(service, project)
    first = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )
    service.be._ex("UPDATE tasks SET status='done' WHERE slug='stop-work'")
    service.be._execution_lease_unbind_task("stop-work", utcnow_iso())

    repeated = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert first.code == "CONTINUE"
    assert repeated.code == "ALLOW_DONE"
    assert repeated.action == "task is complete"
    row = service.be._q1("SELECT consumed_at,decision FROM can_stop_turns WHERE turn_id='turn-1'")
    assert row["consumed_at"] and row["decision"] == "CONTINUE"


def test_concurrent_stop_consumers_are_idempotent(bound_service):
    service, project, _lease = bound_service
    _record(service, project)
    db_path = service.be.db_path

    def consume():
        backend = SQLiteBackend(db_path)
        try:
            return decide_persisted_stop(
                ProjectService(backend),
                host_instance="codex",
                thread_id="thread-a",
                turn_id="turn-1",
            ).code
        finally:
            backend.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _index: consume(), range(2)))

    assert codes == ["CONTINUE", "CONTINUE"]
    row = service.be._q1("SELECT consumed_at,decision FROM can_stop_turns WHERE turn_id='turn-1'")
    assert row["consumed_at"] and row["decision"] == "CONTINUE"


def test_new_prompt_supersedes_old_unconsumed_turn(bound_service):
    service, project, _lease = bound_service
    _record(service, project, turn_id="old")
    _record(service, project, turn_id="current")

    old = decide_persisted_stop(service, host_instance="codex", thread_id="thread-a", turn_id="old")
    current = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="current"
    )

    assert old.code == "CONTINUE"
    assert old.action == "trusted turn record is missing; continue safely"
    assert current.code == "CONTINUE"


def test_old_allowed_turn_cannot_be_selected_after_a_new_work_turn(bound_service):
    service, project, _lease = bound_service
    _record(service, project, prompt="show status", turn_id="old-read")
    assert (
        decide_persisted_stop(
            service, host_instance="codex", thread_id="thread-a", turn_id="old-read"
        ).code
        == "ALLOW_READ_ONLY"
    )
    _record(service, project, prompt="fix the race", turn_id="current-work")

    stale = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="old-read"
    )

    assert stale.code == "CONTINUE"


def test_exact_current_turn_identity_blocks_stale_allow_when_prompt_record_failed(bound_service):
    service, project, _lease = bound_service
    _record(service, project, prompt="show status", turn_id="old-read")

    decision = decide_persisted_stop(
        service,
        host_instance="codex",
        thread_id="thread-a",
        turn_id="current-work-that-failed-to-record",
    )

    assert decision.code == "CONTINUE"
    assert decision.action == "trusted turn record is missing; continue safely"


def test_malformed_prompt_identity_does_not_consume_other_threads(bound_service):
    service, project, lease = bound_service
    _record(service, project, prompt="show status", turn_id="thread-a-read")
    row = service.be._q1("SELECT * FROM can_stop_turns WHERE turn_id='thread-a-read'")
    service.be._ex(
        "INSERT INTO can_stop_turns(project_identity,host_instance,thread_id,turn_id,lease_id,"
        "task_slug,request_kind,payload_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (
            row["project_identity"],
            "codex",
            "thread-b",
            "thread-b-read",
            lease["id"],
            row["task_slug"],
            "read_only",
            row["payload_hash"],
            row["created_at"],
        ),
    )
    result = subprocess.run(
        [sys.executable, str(PROMPT_HOOK), "--trusted-host", "codex"],
        input=json.dumps({"turn_id": "malformed-current", "prompt": "fix the race"}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project), "PYTHONUTF8": "1"},
    )

    assert result.returncode == 0
    rows = service.be._q("SELECT thread_id,consumed_at FROM can_stop_turns ORDER BY thread_id")
    assert rows == [
        {"thread_id": "thread-a", "consumed_at": None},
        {"thread_id": "thread-b", "consumed_at": None},
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"session_id": "thread-a", "prompt": "/start"},
        {"session_id": "thread-a", "turn_id": "old-read", "prompt": "fix the race"},
    ],
)
def test_machine_or_failed_prompt_record_cannot_leave_old_allow_selected(bound_service, payload):
    service, project, _lease = bound_service
    _record(service, project, prompt="show status", turn_id="old-read")
    result = subprocess.run(
        [sys.executable, str(PROMPT_HOOK), "--trusted-host", "codex"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project), "PYTHONUTF8": "1"},
    )
    assert result.returncode == 0

    decision = decide_persisted_stop(service, host_instance="codex", thread_id="thread-a")

    assert decision.code == "CONTINUE"


def test_stop_uses_the_task_currently_bound_to_the_lease(bound_service):
    service, project, lease = bound_service
    _record(service, project)
    now = utcnow_iso()
    service.be._ex("UPDATE tasks SET status='done' WHERE slug='stop-work'")
    service.be._ex(
        "INSERT INTO tasks(slug,title,status,complexity,goal,plan,acceptance_criteria,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (
            "new-work",
            "New work",
            "active",
            "complex",
            "Finish new work",
            json.dumps([{"step": "finish the rebound task", "done": False}]),
            "New work completes",
            now,
            now,
        ),
    )
    service.be._ex("UPDATE execution_leases SET task_slug='new-work' WHERE id=?", (lease["id"],))

    decision = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert decision.code == "CONTINUE"
    assert decision.action == "complete plan step 1: finish the rebound task"


def test_rebound_task_can_use_blocker_evidence_from_the_current_lease_task(bound_service):
    service, project, lease = bound_service
    _record(service, project)
    now = utcnow_iso()
    service.be._ex(
        "INSERT INTO tasks(slug,title,status,complexity,goal,acceptance_criteria,created_at,updated_at) "
        "VALUES('new-work','New work','blocked','complex','goal','criterion',?,?)",
        (now, now),
    )
    service.be._ex("UPDATE execution_leases SET task_slug='new-work' WHERE id=?", (lease["id"],))
    rebound_lease = service.be._q1("SELECT * FROM execution_leases WHERE id=?", (lease["id"],))
    event_id = record_attempt_event(
        service,
        lease=rebound_lease,
        event_kind="authority",
        status="unavailable",
        detail={"observed_code": "IDENTITY_MISSING"},
    )
    preflight_id = service.be._ins(
        "INSERT INTO memory_preflight_tokens(token,lease_id,package_fingerprint,content_revision,"
        "acknowledged_ids,protected_kind,action_id,payload_hash,status,issued_at,expires_at,completed_at) "
        "VALUES('rebound-token',?,'package','revision','[]','blocker','rebound','hash','executed',?,?,?)",
        (lease["id"], now, "2999-01-01T00:00:00Z", now),
    )
    service.be._ex(
        "INSERT INTO task_continuity_state(task_slug,package_fingerprint,blocker_json,updated_at) "
        "VALUES('new-work','package',?,?)",
        (
            json.dumps(
                {
                    "attempt_event_ids": [event_id],
                    "memory_preflight_id": preflight_id,
                    "resume_action": "retry after identity is restored",
                }
            ),
            now,
        ),
    )

    decision = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert decision.code == "ALLOW_BLOCKED"
    assert decision.action == "retry after identity is restored"


def test_expired_lease_cannot_record_a_trusted_turn(bound_service):
    service, project, lease = bound_service
    service.be._ex(
        "UPDATE execution_leases SET expires_at='2000-01-01T00:00:00Z' WHERE id=?",
        (lease["id"],),
    )

    with pytest.raises(ValueError, match="TURN_LEASE_MISSING"):
        _record(service, project)


def test_read_only_and_done_are_durable_allow_verdicts(bound_service):
    service, project, _lease = bound_service
    _record(service, project, prompt="show status", turn_id="read")
    assert (
        decide_persisted_stop(
            service, host_instance="codex", thread_id="thread-a", turn_id="read"
        ).code
        == "ALLOW_READ_ONLY"
    )
    _record(service, project, turn_id="done")
    service.be._ex("UPDATE tasks SET status='done' WHERE slug='stop-work'")
    assert (
        decide_persisted_stop(
            service, host_instance="codex", thread_id="thread-a", turn_id="done"
        ).code
        == "ALLOW_DONE"
    )


def _persist_blocker(service, lease, event_id):
    now = utcnow_iso()
    preflight_id = service.be._ins(
        "INSERT INTO memory_preflight_tokens(token,lease_id,package_fingerprint,content_revision,"
        "acknowledged_ids,protected_kind,action_id,payload_hash,status,issued_at,expires_at,completed_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            f"token-{event_id}",
            lease["id"],
            "package",
            "revision",
            "[]",
            "blocker",
            f"block-{event_id}",
            f"hash-{event_id}",
            "executed",
            now,
            "2999-01-01T00:00:00Z",
            now,
        ),
    )
    blocker = json.dumps(
        {
            "attempt_event_ids": [event_id],
            "memory_preflight_id": preflight_id,
            "resume_action": "retry after the owner grants repository access",
        }
    )
    service.be._ex(
        "INSERT INTO task_continuity_state(task_slug,package_fingerprint,blocker_json,updated_at) "
        "VALUES(?,?,?,?) ON CONFLICT(task_slug) DO UPDATE SET blocker_json=excluded.blocker_json",
        ("stop-work", "package", blocker, now),
    )
    service.be._ex("UPDATE tasks SET status='blocked' WHERE slug='stop-work'")


def _reserve_blocker_preflight(service, lease):
    now = utcnow_iso()
    return service.be._ins(
        "INSERT INTO memory_preflight_tokens(token,lease_id,package_fingerprint,content_revision,"
        "acknowledged_ids,protected_kind,action_id,payload_hash,status,issued_at,expires_at,reserved_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "token-product-path",
            lease["id"],
            "package",
            "revision",
            "[]",
            "blocker",
            "block-product-path",
            "hash-product-path",
            "reserved",
            now,
            "2999-01-01T00:00:00Z",
            now,
        ),
    )


def test_task_block_product_path_persists_lease_bound_evidence(bound_service):
    service, project, lease = bound_service
    _record(service, project)
    token_id = _reserve_blocker_preflight(service, lease)
    service._authorized_execution_lease = lease

    service.task_block(
        "stop-work",
        "repository rejected the authenticated write",
        "Can the owner grant repository write access?",
        "Repository write succeeds with the current identity",
        [
            record_attempt_event(
                service,
                lease=lease,
                event_kind="authority",
                status="unavailable",
                detail={"observed_code": "permission denied"},
            )
        ],
        "retry the repository write after the owner grants access",
    )
    service.be._ex(
        "UPDATE memory_preflight_tokens SET status='executed',completed_at=? WHERE id=?",
        (utcnow_iso(), token_id),
    )

    blocker = json.loads(
        service.be._q1(
            "SELECT blocker_json FROM task_continuity_state WHERE task_slug='stop-work'"
        )["blocker_json"]
    )
    assert blocker["memory_preflight_id"] == token_id
    assert service.be._q1(
        "SELECT event_kind,status FROM task_attempt_events WHERE id=?",
        (blocker["attempt_event_ids"][0],),
    ) == {"event_kind": "authority", "status": "unavailable"}
    assert (
        decide_persisted_stop(
            service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
        ).code
        == "ALLOW_BLOCKED"
    )


def test_invalid_structured_blocker_rolls_back_task_state(bound_service):
    service, _project, lease = bound_service
    _reserve_blocker_preflight(service, lease)
    service._authorized_execution_lease = lease

    with pytest.raises(ServiceError, match="event was not observed"):
        service.task_block(
            "stop-work",
            "claimed unavailable authority",
            "Can the owner grant repository write access?",
            "Repository write succeeds",
            [999_999],
            "retry after access is granted",
        )

    assert service.be.task_get("stop-work")["status"] == "active"
    assert (
        service.be._q1("SELECT blocker_json FROM task_continuity_state WHERE task_slug='stop-work'")
        is None
    )


def test_prose_only_reblock_clears_stale_structured_evidence(bound_service):
    service, _project, lease = bound_service
    event_id = record_attempt_event(
        service,
        lease=lease,
        event_kind="authority",
        status="unavailable",
        detail={"observed": "permission denied"},
    )
    _persist_blocker(service, lease, event_id)

    service.task_block(
        "stop-work",
        "waiting for a decision",
        "Which supported policy should apply?",
        "The owner selects one supported policy",
    )

    row = service.be._q1(
        "SELECT blocker_json FROM task_continuity_state WHERE task_slug='stop-work'"
    )
    assert row["blocker_json"] is None


def test_unblock_clears_structured_evidence_and_cannot_allow_stop(bound_service):
    service, project, lease = bound_service
    _record(service, project)
    event_id = record_attempt_event(
        service,
        lease=lease,
        event_kind="authority",
        status="unavailable",
        detail={"observed": "permission denied"},
    )
    _persist_blocker(service, lease, event_id)
    service.be._ex(
        "UPDATE tasks SET status='blocked',blocked_question=?,unblock_criteria=? "
        "WHERE slug='stop-work'",
        ("Can the owner grant access?", "Write succeeds"),
    )

    service.task_unblock("stop-work", "Owner granted access", "test")

    row = service.be._q1(
        "SELECT blocker_json FROM task_continuity_state WHERE task_slug='stop-work'"
    )
    assert row["blocker_json"] is None
    assert (
        decide_persisted_stop(
            service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
        ).code
        == "CONTINUE"
    )


def test_only_real_lease_bound_unavailable_authority_allows_blocker(bound_service):
    service, project, lease = bound_service
    _record(service, project)
    first = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )
    event_id = record_attempt_event(
        service,
        lease=lease,
        event_kind="authority",
        status="unavailable",
        detail={"capability": "repository write", "observed": "permission denied"},
    )
    _persist_blocker(service, lease, event_id)

    decision = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert first.code == "CONTINUE"
    assert decision.code == "ALLOW_BLOCKED"
    assert decision.action == "retry after the owner grants repository access"


def test_forged_attempt_id_cannot_turn_blocker_text_into_authority(bound_service):
    service, project, lease = bound_service
    _record(service, project)
    _persist_blocker(service, lease, 999_999)

    decision = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert decision.code == "CONTINUE"


def _persist_ceiling_checkpoint(service, lease, handoff):
    now = utcnow_iso()
    service.be._ex("UPDATE tasks SET call_budget=10,call_actual=10 WHERE slug='stop-work'")
    service.be._ex(
        "INSERT INTO task_continuity_state(task_slug,package_fingerprint,recovery_lease_id,"
        "recovery_issued_at,recovery_consumed_at,recovery_action,updated_at) VALUES(?,?,?,?,?,?,?)",
        ("stop-work", "package", lease["id"], now, now, "checkpoint", now),
    )
    service.be._ex("UPDATE execution_leases SET revoked_at=? WHERE id=?", (now, lease["id"]))
    service.be._ex("UPDATE sessions SET handoff=? WHERE id=?", (handoff, lease["session_id"]))


@pytest.mark.parametrize(
    ("handoff", "expected"),
    [
        ("checkpoint saved", "CONTINUE"),
        ("Resume: .tausik/tausik task start stop-work --package", "ALLOW_HANDOFF"),
    ],
)
def test_hard_ceiling_requires_copy_ready_checkpoint_handoff(bound_service, handoff, expected):
    service, project, lease = bound_service
    _record(service, project)
    first = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )
    _persist_ceiling_checkpoint(service, lease, handoff)

    decision = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert first.code == "CONTINUE"
    assert decision.code == expected
    if expected == "ALLOW_HANDOFF":
        assert decision.action == ".tausik/tausik task start stop-work --package"


@pytest.mark.parametrize("armed", [True, False])
def test_legacy_call_count_requirement_never_replaces_the_next_action(
    bound_service, monkeypatch, armed
):
    service, project, _lease = bound_service
    if armed:
        monkeypatch.setenv("TAUSIK_AUTONOMOUS_BUDGET_BLOCK", "1")
    else:
        monkeypatch.delenv("TAUSIK_AUTONOMOUS_BUDGET_BLOCK", raising=False)
    _record(service, project)
    service.be._ex(
        "INSERT INTO task_continuity_state(task_slug,package_fingerprint,pending_requirement,updated_at) "
        "VALUES(?,?,?,?)",
        ("stop-work", "package", "call_budget_exhausted", utcnow_iso()),
    )

    decision = decide_persisted_stop(
        service, host_instance="codex", thread_id="thread-a", turn_id="turn-1"
    )

    assert decision.code == "CONTINUE"
    assert decision.action == "complete plan step 1: run the negative matrix"


def _run_hook(project, payload):
    return subprocess.run(
        [sys.executable, str(HOOK), "--trusted-host", "codex"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project), "PYTHONUTF8": "1"},
    )


def test_native_hook_blocks_malformed_and_missing_durable_turn(bound_service):
    _service, project, _lease = bound_service

    malformed = subprocess.run(
        [sys.executable, str(HOOK), "--trusted-host", "codex"],
        input="not-json",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project), "PYTHONUTF8": "1"},
    )
    missing = _run_hook(project, {"session_id": "thread-a"})

    for result in (malformed, missing):
        verdict = json.loads(result.stdout)
        assert result.returncode == 0
        assert verdict["decision"] == "block"


def test_native_hook_allows_only_a_persisted_allow_verdict(bound_service):
    service, project, _lease = bound_service
    _record(service, project, prompt="show status", turn_id="read-turn")

    result = _run_hook(project, {"session_id": "thread-a", "turn_id": "read-turn"})

    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("stdout", "returncode", "timed_out"),
    [
        ("", 1, False),  # process crash
        ("", None, True),  # host timeout
        ("not-json", 0, False),  # malformed stdout
        ("", 0, False),  # no stdout
        (json.dumps({"decision": "allow"}), 0, False),
    ],
)
def test_native_failure_without_block_json_is_never_counted_as_enforcement(
    stdout, returncode, timed_out
):
    assert not classify_native_stop_verdict(
        stdout=stdout, returncode=returncode, timed_out=timed_out
    ).enforced


def test_native_block_json_is_the_only_hard_enforcement_evidence():
    verdict = classify_native_stop_verdict(
        stdout=json.dumps({"decision": "block", "reason": "continue exact step"}),
        returncode=0,
    )
    assert verdict.enforced


@pytest.mark.parametrize(
    ("program", "timeout"),
    [
        ("raise SystemExit(7)", 2.0),
        ("import time; time.sleep(2)", 0.05),
        ("print('not-json')", 2.0),
        ("", 2.0),
    ],
)
def test_native_process_failure_matrix_never_counts_as_enforcement(program, timeout):
    verdict = run_native_stop_probe([sys.executable, "-c", program], payload={}, timeout=timeout)
    assert not verdict.enforced


def test_native_process_block_json_counts_as_enforcement():
    program = "import json; print(json.dumps({'decision':'block','reason':'continue'}))"
    verdict = run_native_stop_probe([sys.executable, "-c", program], payload={})
    assert verdict.enforced
    assert verdict.reason == "continue"


@pytest.mark.parametrize("checkpoint_kind", ["call_budget", "host_context"])
def test_fresh_process_reads_persisted_handoff_and_returns_exact_resume_action(
    bound_service, checkpoint_kind
):
    service, project, lease = bound_service
    _record(service, project)
    resume = ".tausik/tausik task start stop-work --package"
    if checkpoint_kind == "call_budget":
        _persist_ceiling_checkpoint(service, lease, f"Resume: {resume}")
    else:
        now = utcnow_iso()
        service.be._ex("UPDATE execution_leases SET revoked_at=? WHERE id=?", (now, lease["id"]))
        service.be._ex(
            "UPDATE sessions SET handoff=? WHERE id=?", (f"Resume: {resume}", lease["session_id"])
        )
        service.be.meta_set(f"host_context_hard_lease:{lease['id']}", resume)
    code = """
import json, sys
from can_stop import decide_persisted_stop, decision_json
from project_backend import SQLiteBackend
from project_service import ProjectService
backend = SQLiteBackend(sys.argv[1] + '/.tausik/tausik.db')
try:
    decision = decide_persisted_stop(
        ProjectService(backend), host_instance='codex', thread_id='thread-a', turn_id='turn-1'
    )
    print(json.dumps(decision_json(decision)))
finally:
    backend.close()
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(project)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env={**os.environ, "PYTHONPATH": str(HOOK.parents[1]), "PYTHONUTF8": "1"},
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "code": "ALLOW_HANDOFF",
        "action": ".tausik/tausik task start stop-work --package",
    }
