"""Durable execution leases bind trusted SessionStart identity to mutations."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

from project_backend import SQLiteBackend
from project_service import ProjectService
from service_execution_lease import (
    ExecutionLeaseError,
    authorize_mcp_mutation,
    assertion_from_pre_tool_use,
    assertion_from_session_start,
    consume_mcp_authorization,
    enter_execution_lease_maintenance,
    issue_execution_lease,
    normalize_project_identity,
    recover_execution_lease_state,
    reconcile_execution_lease_state,
    require_execution_lease,
)

MCP_DIR = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))
HOOKS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


@pytest.fixture
def service(tmp_path):
    project = tmp_path / "project"
    backend = SQLiteBackend(str(project / ".tausik" / "tausik.db"))
    svc = ProjectService(backend)
    yield svc, project
    backend.close()


def trusted_assertion(project, now=None, thread_id="thread-a"):
    return assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": thread_id},
        str(project),
        trusted_host="codex",
        now=now,
    )


def prepare(svc, assertion):
    reconcile_execution_lease_state(svc, assertion)


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"hook_event_name": "PreToolUse", "session_id": "thread-a"}, "IDENTITY_UNTRUSTED"),
        ({"hook_event_name": "SessionStart"}, "IDENTITY_MISSING"),
        ({"hook_event_name": "SessionStart", "session_id": " "}, "IDENTITY_MISSING"),
    ],
)
def test_only_complete_session_start_payload_creates_assertion(tmp_path, payload, code):
    with pytest.raises(ExecutionLeaseError, match=code):
        assertion_from_session_start(payload, str(tmp_path), trusted_host="codex")


def test_non_codex_adapter_cannot_mint_codex_authority(tmp_path):
    with pytest.raises(ExecutionLeaseError, match="IDENTITY_UNTRUSTED"):
        assertion_from_session_start(
            {"hook_event_name": "SessionStart", "session_id": "thread-a"},
            str(tmp_path),
            trusted_host="claude",
        )


def test_trusted_pretool_assertion_is_bound_to_its_exact_event_and_thread(tmp_path):
    assertion = assertion_from_pre_tool_use(
        {"hook_event_name": "PreToolUse", "session_id": "thread-a"},
        str(tmp_path),
        trusted_host="cursor",
    )
    assert (assertion.host_instance, assertion.thread_id) == ("cursor", "thread-a")
    with pytest.raises(ExecutionLeaseError, match="IDENTITY_UNTRUSTED"):
        assertion_from_pre_tool_use(
            {"hook_event_name": "SessionStart", "session_id": "thread-a"},
            str(tmp_path),
            trusted_host="cursor",
        )


def test_windows_project_identity_normalizes_case_and_separators():
    assert normalize_project_identity(r"C:\Work\TAUSIK\.") == normalize_project_identity(
        "c:/work/tausik"
    )


def test_repeated_trusted_start_is_idempotent(service):
    svc, project = service
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assertion = trusted_assertion(project, now)
    prepare(svc, assertion)

    first = issue_execution_lease(svc, assertion, now=now)
    repeated = issue_execution_lease(svc, assertion, now=now + timedelta(seconds=1))

    assert repeated["id"] == first["id"]
    assert repeated["nonce"] == first["nonce"]
    assert svc.be.session_current("thread-a")["id"] == first["session_id"]


def test_lease_survives_backend_restart(service):
    svc, project = service
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assertion = trusted_assertion(project, now)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion, now=now)
    db_path = svc.be.db_path
    svc.be.close()
    restarted = ProjectService(SQLiteBackend(db_path))
    try:
        loaded = require_execution_lease(
            restarted,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=lease["nonce"],
            now=now + timedelta(seconds=1),
        )
        assert loaded["id"] == lease["id"]
    finally:
        restarted.be.close()


def test_wrong_thread_and_stale_lease_fail_without_mutation(service):
    svc, project = service
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assertion = trusted_assertion(project, now)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion, now=now, ttl_seconds=10)

    with pytest.raises(ExecutionLeaseError, match="IDENTITY_MISMATCH"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-b",
            nonce=lease["nonce"],
            now=now + timedelta(seconds=1),
        )
    with pytest.raises(ExecutionLeaseError, match="LEASE_STALE"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=lease["nonce"],
            now=now + timedelta(seconds=10),
        )
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is None


def test_plain_mapping_cannot_issue_a_lease(service):
    svc, _project = service
    with pytest.raises(ExecutionLeaseError, match="IDENTITY_UNTRUSTED"):
        issue_execution_lease(svc, {"thread_id": "forged"})


def test_expired_lease_is_replaced_and_old_nonce_stays_revoked(service):
    svc, project = service
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assertion = trusted_assertion(project, now)
    prepare(svc, assertion)
    old = issue_execution_lease(svc, assertion, now=now, ttl_seconds=1)
    with pytest.raises(ExecutionLeaseError, match="ASSERTION_REPLAY"):
        issue_execution_lease(svc, assertion, now=now + timedelta(seconds=2))
    fresh_assertion = trusted_assertion(project, now + timedelta(seconds=2))
    fresh = issue_execution_lease(svc, fresh_assertion, now=now + timedelta(seconds=2))

    assert fresh["nonce"] != old["nonce"]
    assert svc.be._execution_lease_by_nonce(old["nonce"])["revoked_at"] is not None
    with pytest.raises(ExecutionLeaseError, match="LEASE_REVOKED"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=old["nonce"],
            now=now + timedelta(seconds=2),
        )


def test_pretool_boundary_renews_a_lease_expired_during_a_long_turn(service, monkeypatch):
    import execution_lease_gate
    import session_start

    svc, project = service
    old_time = datetime.now(timezone.utc) - timedelta(hours=1)
    assertion = trusted_assertion(project, old_time)
    prepare(svc, assertion)
    old = issue_execution_lease(svc, assertion, now=old_time, ttl_seconds=1)
    monkeypatch.setattr(session_start, "_codex_preflight_hooks_ready", lambda _project: True)

    allowed, reason = execution_lease_gate.require_live_lease(
        {
            "hook_event_name": "PreToolUse",
            "session_id": "thread-a",
            "tool_name": "Write",
            "tool_input": {"file_path": str(project / "x.py")},
        },
        str(project),
        route="codex_implementation_write",
        arguments={"tool": "Write", "payload_sha256": "x"},
        authorize=False,
    )

    assert allowed, reason
    fresh = svc.be._execution_lease_current(
        normalize_project_identity(str(project)), "codex", "thread-a"
    )
    assert fresh is not None and fresh["nonce"] != old["nonce"]
    assert svc.be._execution_lease_by_nonce(old["nonce"])["revoked_at"] is not None


def test_revoked_lease_rejects_assertion_replay_with_typed_error(service, monkeypatch):
    svc, project = service
    monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    issue_execution_lease(svc, assertion)
    svc.session_end(host_session_id="thread-a")

    with pytest.raises(ExecutionLeaseError, match="ASSERTION_REPLAY"):
        issue_execution_lease(svc, assertion)


def test_concurrent_starts_converge_on_one_session_and_lease(tmp_path):
    project = tmp_path / "project"
    db_path = str(project / ".tausik" / "tausik.db")
    seed = SQLiteBackend(db_path)
    seed.close()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assertion = trusted_assertion(project, now)

    def issue():
        backend = SQLiteBackend(db_path)
        try:
            local = ProjectService(backend)
            prepare(local, assertion)
            return issue_execution_lease(local, assertion, now=now)
        finally:
            backend.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(pool.map(lambda _index: issue(), range(2)))

    backend = SQLiteBackend(db_path)
    try:
        assert leases[0]["id"] == leases[1]["id"]
        assert backend._q1("SELECT COUNT(*) AS count FROM sessions")["count"] == 1
        assert backend._q1("SELECT COUNT(*) AS count FROM execution_leases")["count"] == 1
    finally:
        backend.close()


def test_codex_mcp_mutation_requires_bound_lease(service, monkeypatch):
    from handlers import handle_tool

    svc, project = service
    monkeypatch.setenv("TAUSIK_ENFORCE_EXECUTION_LEASE", "1")
    with pytest.raises(ExecutionLeaseError, match="IDENTITY_MISSING"):
        handle_tool(svc, "tausik_audit_mark", {})

    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    authorization = authorize_mcp_mutation(
        svc,
        lease=lease,
        route="tausik_audit_mark",
        arguments={},
        correlated=True,
    )
    result = handle_tool(
        svc,
        "tausik_audit_mark",
        {},
        authorization=authorization,
    )
    assert "Audit marked" in result


def test_mcp_registry_keeps_host_identity_out_of_model_arguments():
    from tools import TOOLS

    for tool in TOOLS:
        properties = tool["inputSchema"].get("properties", {})
        assert "lease_nonce" not in properties
        assert "thread_id" not in properties


def test_every_mcp_mutation_reaches_the_central_authorization_boundary(service, monkeypatch):
    from adherence_registry import _READ_ROUTES
    from handlers import _require_codex_execution_lease
    from tools import TOOLS

    svc, _project = service
    monkeypatch.setenv("TAUSIK_ENFORCE_EXECUTION_LEASE", "1")
    for tool in TOOLS:
        route = f"mcp.{tool['name']}"
        if route in _READ_ROUTES:
            _require_codex_execution_lease(svc, tool["name"], {})
        else:
            with pytest.raises(ExecutionLeaseError, match="IDENTITY_MISSING"):
                _require_codex_execution_lease(svc, tool["name"], {})
    with pytest.raises(ExecutionLeaseError, match="IDENTITY_MISSING"):
        _require_codex_execution_lease(svc, "unknown_future_mutation", {})


@pytest.mark.parametrize(
    "route",
    [
        "tausik_doctor",
        "tausik_tool_schema",
        "tausik_explore_current",
        "tausik_audit_check",
        "tausik_skill_list",
        "tausik_skill_repo_list",
        "tausik_skill_catalog",
        "tausik_session_last_handoff",
        "tausik_memory_related",
        "tausik_memory_graph",
        "tausik_memory_brief",
        "tausik_events",
        "tausik_team",
        "tausik_cq_query",
        "tausik_stack_lint",
        "tausik_stack_diff",
        "tausik_actz_verify",
        "tausik_actz_final_tz",
        "tausik_actz_orphans",
        "tausik_at_diagnose",
        "tausik_at_release_readiness",
    ],
)
def test_side_effect_free_mcp_routes_do_not_require_an_execution_lease(service, monkeypatch, route):
    from handlers import _require_codex_execution_lease

    svc, _project = service
    monkeypatch.setenv("TAUSIK_ENFORCE_EXECUTION_LEASE", "1")
    assert _require_codex_execution_lease(svc, route, {}) is None


def test_session_end_atomically_revokes_lease(service, monkeypatch):
    svc, project = service
    monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)

    svc.session_end(host_session_id="thread-a")

    assert svc.be.session_current("thread-a") is None
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is not None


def test_live_lease_cannot_outlive_its_bound_session(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.be._ex(
        "UPDATE sessions SET ended_at='2026-01-01T00:00:00Z' WHERE id=?", (lease["session_id"],)
    )

    with pytest.raises(ExecutionLeaseError, match="LEASE_REVOKED"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=lease["nonce"],
        )


def test_corrupt_ambiguous_identity_enters_maintenance_and_revokes(service):
    import execution_lease_gate

    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    issue_execution_lease(svc, assertion)
    svc.be._ex("DROP INDEX idx_execution_leases_one_live_thread")
    svc.be._ex(
        "INSERT INTO execution_leases(session_id, project_identity, host_instance, "
        "thread_id, assertion_nonce, assertion_issued_at, assertion_expires_at, "
        "nonce, issued_at, expires_at, revoked_at, projection_build, capability_min, "
        "capability_max) SELECT session_id, project_identity, host_instance, thread_id, "
        "'duplicate-assertion', assertion_issued_at, assertion_expires_at, "
        "'duplicate-lease', issued_at, expires_at, NULL, projection_build, "
        "capability_min, capability_max FROM execution_leases LIMIT 1"
    )

    allowed, reason = execution_lease_gate.require_live_lease(
        {"session_id": "thread-a"}, str(project)
    )

    assert allowed is False
    assert "IDENTITY_AMBIGUOUS" in reason
    assert svc.be._execution_lease_state()["mode"] == "maintenance"
    assert (
        svc.be._q1("SELECT COUNT(*) AS count FROM execution_leases WHERE revoked_at IS NULL")[
            "count"
        ]
        == 0
    )


def test_capability_mismatch_requires_explicit_owner_recovery(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.be._ex(
        "INSERT INTO memory_preflight_tokens(token,lease_id,package_fingerprint,content_revision,"
        "acknowledged_ids,protected_kind,action_id,payload_hash,status,issued_at,expires_at) "
        "VALUES('pending-token',?,'package','revision','[]','commit','action','payload',"
        "'reserved','2026-11-02T00:00:00Z','2099-11-02T00:00:00Z')",
        (lease["id"],),
    )
    svc.be._ex("UPDATE execution_lease_state SET capability_version=999 WHERE singleton=1")

    with pytest.raises(ExecutionLeaseError, match="CAPABILITY_MISMATCH"):
        reconcile_execution_lease_state(svc, trusted_assertion(project))
    assert svc.be._execution_lease_state()["mode"] == "maintenance"
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is not None
    token = svc.be._q1("SELECT status,failure_code FROM memory_preflight_tokens")
    assert token == {"status": "failed", "failure_code": "CAPABILITY_MAINTENANCE"}
    with pytest.raises(ExecutionLeaseError, match="LEASE_MAINTENANCE"):
        reconcile_execution_lease_state(svc, trusted_assertion(project))
    with pytest.raises(ExecutionLeaseError, match="RECOVERY_CONFIRMATION_REQUIRED"):
        recover_execution_lease_state(svc, "yes")

    emergency_marker = project / ".tausik" / "execution-lease-maintenance"
    emergency_marker.write_text("audit failed\n", encoding="utf-8")
    recover_execution_lease_state(svc, "revoke-and-reconcile")
    assert svc.be._execution_lease_state()["mode"] == "ready"
    assert not emergency_marker.exists()


def test_patch_build_drift_preserves_unexecuted_token_without_maintenance(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.be._ex(
        "INSERT INTO memory_preflight_tokens(token,lease_id,package_fingerprint,content_revision,"
        "acknowledged_ids,protected_kind,action_id,payload_hash,status,issued_at,expires_at) "
        "VALUES('unexecuted',?,'package','revision','[]','commit','action','payload',"
        "'issued','2026-11-02T00:00:00Z','2099-11-02T00:00:00Z')",
        (lease["id"],),
    )
    svc.be._ex("UPDATE execution_lease_state SET projection_build='1.11.8' WHERE singleton=1")

    reconcile_execution_lease_state(svc, trusted_assertion(project))

    token = svc.be._q1("SELECT status,failure_code FROM memory_preflight_tokens")
    assert token == {"status": "issued", "failure_code": None}
    assert svc.be._execution_lease_state()["mode"] == "ready"


def test_patch_build_drift_without_pending_action_reconciles_automatically(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    old = issue_execution_lease(svc, assertion)
    svc.be._ex("UPDATE execution_lease_state SET projection_build='1.11.8' WHERE singleton=1")

    fresh_assertion = trusted_assertion(project)
    reconcile_execution_lease_state(svc, fresh_assertion)
    fresh = issue_execution_lease(svc, fresh_assertion)

    assert svc.be._execution_lease_state()["mode"] == "ready"
    assert svc.be._execution_lease_by_nonce(old["nonce"])["revoked_at"] is None
    assert fresh["nonce"] == old["nonce"]
    assert svc.be._q1("SELECT value FROM meta WHERE key='execution_lease_maintenance'") is None


@pytest.mark.parametrize(
    "reason",
    [
        "PostToolUse audit failure: ValueError",
        "protected action completed without an exact reserved preflight token",
    ],
)
def test_ambiguous_1_11_8_audit_failures_require_explicit_owner_recovery(service, reason):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    enter_execution_lease_maintenance(svc, reason)
    svc.be._ex("UPDATE execution_lease_state SET projection_build='1.11.8' WHERE singleton=1")

    with pytest.raises(ExecutionLeaseError, match="LEASE_MAINTENANCE"):
        reconcile_execution_lease_state(svc, trusted_assertion(project))

    assert svc.be._execution_lease_state()["mode"] == "maintenance"
    assert svc.be._q1("SELECT value FROM meta WHERE key='execution_lease_maintenance'") == {
        "value": reason
    }


def test_missing_state_with_existing_lease_persists_maintenance_and_revocation(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.be._ex("DELETE FROM execution_lease_state")

    with pytest.raises(ExecutionLeaseError, match="CAPABILITY_MISMATCH"):
        reconcile_execution_lease_state(svc, trusted_assertion(project))

    assert svc.be._q1("SELECT value FROM meta WHERE key='execution_lease_maintenance'")
    assert svc.be._execution_lease_state()["mode"] == "maintenance"
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is not None


def test_missing_lease_to_session_foreign_key_enters_maintenance(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    schema = svc.be._q1(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='execution_leases'"
    )
    assert schema is not None
    without_session_fk = schema["sql"].replace(" REFERENCES sessions(id) ON DELETE CASCADE", "")
    schema_version = svc.be._conn.execute("PRAGMA schema_version").fetchone()[0]
    svc.be._conn.execute("PRAGMA writable_schema=ON")
    svc.be._conn.execute(
        "UPDATE sqlite_master SET sql=? WHERE type='table' AND name='execution_leases'",
        (without_session_fk,),
    )
    svc.be._conn.execute("PRAGMA writable_schema=OFF")
    svc.be._conn.execute(f"PRAGMA schema_version={schema_version + 1}")
    svc.be._conn.commit()

    with pytest.raises(ExecutionLeaseError, match="CAPABILITY_MISMATCH"):
        reconcile_execution_lease_state(svc, trusted_assertion(project))

    assert svc.be._q1("SELECT value FROM meta WHERE key='execution_lease_maintenance'")
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is not None


def test_identical_pending_hook_actions_fail_closed_as_ambiguous(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    authorize_mcp_mutation(svc, lease=lease, route="same", arguments={"value": 1})
    authorize_mcp_mutation(svc, lease=lease, route="same", arguments={"value": 1})

    with pytest.raises(ExecutionLeaseError, match="AUTHORIZATION_AMBIGUOUS"):
        consume_mcp_authorization(svc, route="same", arguments={"value": 1})


def test_contract_change_makes_bound_lease_stale(service):
    svc, project = service
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assertion = trusted_assertion(project, now)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion, now=now)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "work", "Work", complexity="medium")
    svc.task_update(
        "work",
        goal="ship bounded work",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
        scope="scripts/a.py",
        rollback_plan="git revert",
    )
    svc.task_start("work", include_memory=False, execution_lease_id=lease["id"])
    bound = svc.be._execution_lease_by_nonce(lease["nonce"])
    assert bound["task_slug"] == "work"
    require_execution_lease(
        svc,
        project_dir=str(project),
        host_instance="codex",
        thread_id="thread-a",
        nonce=lease["nonce"],
        now=now + timedelta(seconds=1),
    )

    svc.task_update("work", goal="changed after binding")

    with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=lease["nonce"],
            now=now + timedelta(seconds=2),
        )


def test_active_task_without_persisted_package_refuses_lease_renewal(service):
    svc, project = service
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "legacy", "Legacy", complexity="medium")
    svc.be.task_update("legacy", status="active")
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    assert lease["task_slug"] is None
    renewal = trusted_assertion(project, datetime.now(timezone.utc) + timedelta(seconds=1))
    with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE.*unbound lease"):
        issue_execution_lease(svc, renewal, now=renewal.issued_at + timedelta(milliseconds=1))
    with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE.*not bound"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=lease["nonce"],
        )


def test_missing_thread_lease_binds_the_unique_active_task_package(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    initial = issue_execution_lease(svc, assertion)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "work", "Work", complexity="medium")
    svc.task_update(
        "work",
        goal="repair lease recovery",
        acceptance_criteria="AC-1 recovery works. Negative: stale packages fail.",
        scope="scripts/a.py",
        rollback_plan="revert",
    )
    svc.task_start("work", include_memory=False, execution_lease_id=initial["id"])
    svc.be._execution_lease_revoke_all("2030-01-01T00:00:00.000000Z")

    renewed_assertion = trusted_assertion(project)
    renewed = issue_execution_lease(svc, renewed_assertion)

    assert renewed["task_slug"] == "work"
    assert renewed["task_package_fingerprint"]


def test_fresh_thread_can_rebind_a_stale_unique_active_task(service):
    svc, project = service
    assertion_a = trusted_assertion(project, thread_id="thread-a")
    prepare(svc, assertion_a)
    lease_a = issue_execution_lease(svc, assertion_a)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "work", "Work", complexity="medium")
    svc.task_update(
        "work",
        goal="repair lease recovery",
        acceptance_criteria="AC-1 recovery works. Negative: stale packages fail.",
        scope="scripts/a.py",
        rollback_plan="revert",
    )
    svc.task_start("work", include_memory=False, execution_lease_id=lease_a["id"])
    svc.task_update("work", goal="changed after the first thread bound its package")

    assertion_b = trusted_assertion(project, thread_id="thread-b")
    lease_b = issue_execution_lease(svc, assertion_b)

    assert lease_b["task_slug"] == "work"
    with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-b",
            nonce=lease_b["nonce"],
        )
    svc.task_start("work", include_memory=False, execution_lease_id=lease_b["id"])
    require_execution_lease(
        svc,
        project_dir=str(project),
        host_instance="codex",
        thread_id="thread-b",
        nonce=lease_b["nonce"],
    )


def test_patch_upgrade_preserves_each_thread_binding_with_multiple_active_tasks(service):
    svc, project = service
    assertion_a = trusted_assertion(project, thread_id="thread-a")
    prepare(svc, assertion_a)
    lease_a = issue_execution_lease(svc, assertion_a)
    assertion_b = trusted_assertion(project, thread_id="thread-b")
    lease_b = issue_execution_lease(svc, assertion_b)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    for slug, lease in (("a", lease_a), ("b", lease_b)):
        svc.task_add("s", slug, slug.upper(), complexity="medium")
        svc.task_update(
            slug,
            goal=f"deliver {slug}",
            acceptance_criteria="AC-1 works. Negative: mismatch fails.",
            scope=f"scripts/{slug}.py",
            rollback_plan="revert",
        )
        svc.task_start(slug, include_memory=False, execution_lease_id=lease["id"])
    svc.be._ex("UPDATE execution_lease_state SET projection_build='1.11.8' WHERE singleton=1")

    fresh_a_assertion = trusted_assertion(project, thread_id="thread-a")
    reconcile_execution_lease_state(svc, fresh_a_assertion)
    fresh_a = issue_execution_lease(svc, fresh_a_assertion)
    fresh_b = issue_execution_lease(svc, trusted_assertion(project, thread_id="thread-b"))

    assert (fresh_a["task_slug"], fresh_b["task_slug"]) == ("a", "b")


def test_terminal_historical_binding_yields_to_new_active_task(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    for slug in ("old", "new"):
        svc.task_add("s", slug, slug, complexity="medium")
        svc.task_update(
            slug,
            goal=f"deliver {slug}",
            acceptance_criteria="AC-1 works. Negative: mismatch fails.",
            scope=f"scripts/{slug}.py",
            rollback_plan="revert",
        )
    svc.task_start("old", include_memory=False, execution_lease_id=lease["id"])
    svc.be.task_update("old", status="done")
    svc.be.task_update("new", status="active")
    from task_context_package import build_task_context_package, persist_task_context_package

    persist_task_context_package(svc, build_task_context_package(svc, "new"))
    svc.be._execution_lease_revoke_all("2030-01-01T00:00:00.000000Z")

    renewed = issue_execution_lease(svc, trusted_assertion(project))

    assert renewed["task_slug"] == "new"


def test_consumption_revalidates_lease_capability_and_session(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    authorize_mcp_mutation(svc, lease=lease, route="tausik_task_quick", arguments={"slug": "x"})
    svc.be._ex(
        "UPDATE execution_leases SET capability_min=999,capability_max=999 WHERE id=?",
        (lease["id"],),
    )

    with pytest.raises(ExecutionLeaseError, match="CAPABILITY_MISMATCH"):
        consume_mcp_authorization(svc, route="tausik_task_quick", arguments={"slug": "x"})


def test_session_bootstrap_authorization_works_before_task_package_binding(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "work", "Work", complexity="medium")
    svc.be.task_update("work", status="active")

    unbound = require_execution_lease(
        svc,
        project_dir=str(project),
        host_instance="codex",
        thread_id="thread-a",
        nonce=lease["nonce"],
        allow_package_rebind=True,
    )
    authorize_mcp_mutation(svc, lease=unbound, route="tausik_session_open", arguments={})
    consumed = consume_mcp_authorization(svc, route="tausik_session_open", arguments={})

    assert consumed["id"] == lease["id"]
    with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=lease["nonce"],
        )


def test_contract_change_after_pretool_authorization_blocks_dispatch(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "work", "Work", complexity="medium")
    svc.task_update(
        "work",
        goal="ship bounded work",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
        scope="scripts/a.py",
        rollback_plan="git revert",
    )
    svc.task_start("work", include_memory=False, execution_lease_id=lease["id"])
    bound = svc.be._execution_lease_by_nonce(lease["nonce"])
    authorize_mcp_mutation(svc, lease=bound, route="tausik_task_log", arguments={"slug": "work"})
    svc.task_update("work", goal="changed between hook and dispatch")

    with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE"):
        consume_mcp_authorization(svc, route="tausik_task_log", arguments={"slug": "work"})


def test_task_start_rebinds_only_its_own_lease_and_recovers_stale_contract(service):
    svc, project = service
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assertion_a = trusted_assertion(project, now, "thread-a")
    assertion_b = trusted_assertion(project, now, "thread-b")
    prepare(svc, assertion_a)
    lease_a = issue_execution_lease(svc, assertion_a, now=now)
    prepare(svc, assertion_b)
    lease_b = issue_execution_lease(svc, assertion_b, now=now)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    for slug in ("a", "b"):
        svc.task_add("s", slug, slug.upper(), complexity="medium")
        svc.task_update(
            slug,
            goal=f"ship {slug}",
            acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
            scope=f"scripts/{slug}.py",
            rollback_plan="git revert",
        )
    svc.task_start("a", include_memory=False, execution_lease_id=lease_a["id"])
    svc.task_start("b", include_memory=False, execution_lease_id=lease_b["id"])
    bound_a = svc.be._execution_lease_by_nonce(lease_a["nonce"])
    bound_b = svc.be._execution_lease_by_nonce(lease_b["nonce"])
    assert bound_a["task_slug"] == "a"
    assert bound_b["task_slug"] == "b"
    require_execution_lease(
        svc,
        project_dir=str(project),
        host_instance="codex",
        thread_id="thread-a",
        nonce=lease_a["nonce"],
        now=now + timedelta(seconds=1),
    )
    svc.task_update("a", goal="changed contract")
    with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=lease_a["nonce"],
            now=now + timedelta(seconds=2),
        )
    svc.task_start("a", include_memory=False, execution_lease_id=lease_a["id"])
    require_execution_lease(
        svc,
        project_dir=str(project),
        host_instance="codex",
        thread_id="thread-a",
        nonce=lease_a["nonce"],
        now=now + timedelta(seconds=3),
    )
    assert svc.be._execution_lease_by_nonce(lease_b["nonce"])["task_slug"] == "b"


def test_task_scoped_authorization_must_match_bound_slug(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "a", "A", complexity="simple")
    svc.task_update(
        "a",
        goal="ship a",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
    )
    svc.task_start("a", include_memory=False, execution_lease_id=lease["id"])
    bound = svc.be._execution_lease_by_nonce(lease["nonce"])
    with pytest.raises(ExecutionLeaseError, match="TASK_BINDING_MISMATCH"):
        authorize_mcp_mutation(svc, lease=bound, route="tausik_task_log", arguments={"slug": "b"})

    for route, arguments in (
        ("tausik_decide", {"task_slug": "b"}),
        ("tausik_dead_end", {"task_slug": "b"}),
        ("tausik_reason_step", {"slug": "b"}),
        ("tausik_spec_link", {"task_slug": "b"}),
        ("tausik_spec_unlink", {"task_slug": "b"}),
        ("tausik_adapt_link", {"target_type": "task", "target_slug": "b"}),
        ("tausik_actz_link", {"target_type": "task", "target_slug": "b"}),
        ("tausik_actz_unlink", {"target_type": "task", "target_slug": "b"}),
        ("tausik_verify", {"task_slug": "b"}),
    ):
        with pytest.raises(ExecutionLeaseError, match="TASK_BINDING_MISMATCH"):
            authorize_mcp_mutation(svc, lease=bound, route=route, arguments=arguments)

    for route, arguments in (
        ("tausik_verify_cohort", {"tasks": ["a", "b"]}),
        ("tausik_verify_hierarchy", {"kind": "story", "slug": "s"}),
        ("tausik_task_review", {"cohort": {"action": "open", "tasks": ["a", "b"]}}),
        ("tausik_task_review", {"cohort": {"action": "status", "cohort_id": 10}}),
    ):
        with pytest.raises(ExecutionLeaseError, match="TASK_BINDING_SCOPE"):
            authorize_mcp_mutation(svc, lease=bound, route=route, arguments=arguments)


def test_task_activation_rolls_back_when_exact_lease_cannot_be_bound(service):
    svc, _ = service
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "a", "A", complexity="simple")
    svc.task_update(
        "a",
        goal="ship a",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
    )
    with pytest.raises(Exception, match="LEASE_STALE"):
        svc.task_start("a", include_memory=False, execution_lease_id=999)
    assert svc.task_show("a")["status"] == "planning"
    assert svc.be._q1("SELECT 1 FROM task_context_packages WHERE task_slug='a'") is None


def test_expired_bound_lease_renewal_preserves_current_package_binding(service):
    svc, project = service
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assertion = trusted_assertion(project, now)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion, now=now, ttl_seconds=2)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "a", "A", complexity="simple")
    svc.task_update(
        "a",
        goal="ship a",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
    )
    svc.task_start("a", include_memory=False, execution_lease_id=lease["id"])
    renewal_at = now + timedelta(seconds=3)
    renewed = issue_execution_lease(
        svc,
        trusted_assertion(project, renewal_at),
        now=renewal_at,
    )
    assert renewed["id"] != lease["id"]
    assert renewed["task_slug"] == "a"
    assert (
        renewed["task_package_fingerprint"]
        == svc.be._q1("SELECT fingerprint FROM task_context_packages WHERE task_slug='a'")[
            "fingerprint"
        ]
    )


def test_session_renewal_preserves_stale_binding_for_task_start_recovery(service):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "a", "A", complexity="simple")
    svc.task_update(
        "a",
        goal="ship a",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
    )
    svc.task_start("a", include_memory=False, execution_lease_id=lease["id"])
    svc.task_update("a", goal="stale before renewal")

    renewed = issue_execution_lease(svc, trusted_assertion(project))
    assert renewed["task_slug"] == "a"
    with pytest.raises(ExecutionLeaseError, match="PACKAGE_STALE"):
        require_execution_lease(
            svc,
            project_dir=str(project),
            host_instance="codex",
            thread_id="thread-a",
            nonce=renewed["nonce"],
        )


def test_mcp_task_start_is_the_stale_package_recovery_route(service, monkeypatch):
    from handlers import handle_tool

    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "a", "A", complexity="simple")
    svc.task_update(
        "a",
        goal="ship a",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
    )
    svc.task_start("a", include_memory=False, execution_lease_id=lease["id"])
    svc.task_update("a", goal="refresh through start")
    recoverable = require_execution_lease(
        svc,
        project_dir=str(project),
        host_instance="codex",
        thread_id="thread-a",
        nonce=lease["nonce"],
        allow_package_rebind=True,
    )
    authorization = authorize_mcp_mutation(
        svc,
        lease=recoverable,
        route="tausik_task_start",
        arguments={"slug": "a"},
        correlated=True,
    )
    monkeypatch.setenv("TAUSIK_ENFORCE_EXECUTION_LEASE", "1")
    assert "resumed" in handle_tool(
        svc, "tausik_task_start", {"slug": "a"}, authorization=authorization
    )
    require_execution_lease(
        svc,
        project_dir=str(project),
        host_instance="codex",
        thread_id="thread-a",
        nonce=lease["nonce"],
    )


@pytest.mark.parametrize(
    "corruption",
    [
        "DROP TABLE execution_lease_state",
        "DROP INDEX idx_execution_leases_one_live_thread; "
        "CREATE INDEX idx_execution_leases_one_live_thread "
        "ON execution_leases(project_identity, host_instance, thread_id)",
        "DROP INDEX idx_execution_leases_one_live_thread; "
        "CREATE UNIQUE INDEX idx_execution_leases_one_live_thread "
        "ON execution_leases(project_identity, host_instance, thread_id) "
        "WHERE revoked_at IS NULL AND host_instance <> 'codex'",
        "DROP INDEX idx_task_context_packages_fingerprint",
        "DROP INDEX idx_memory_preflight_audit_action",
        "DROP INDEX idx_memory_preflight_audit_action; DROP TABLE memory_preflight_attempt_audit",
    ],
)
def test_schema_corruption_persists_independent_maintenance_marker(service, corruption):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    svc.be._conn.executescript(corruption)

    with pytest.raises(ExecutionLeaseError, match="CAPABILITY_MISMATCH"):
        reconcile_execution_lease_state(svc, trusted_assertion(project))

    marker = svc.be._q1("SELECT value FROM meta WHERE key='execution_lease_maintenance'")
    assert marker is not None
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is not None


@pytest.mark.parametrize(
    "token_schema_change",
    [
        "missing_override_reason",
        "missing_failure_code",
        "missing_status_check",
        "missing_kind_check",
    ],
)
def test_incomplete_token_capability_enters_maintenance(service, token_schema_change):
    svc, project = service
    assertion = trusted_assertion(project)
    prepare(svc, assertion)
    lease = issue_execution_lease(svc, assertion)
    schema = svc.be._q1(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='memory_preflight_tokens'"
    )["sql"]
    replacements = {
        "missing_override_reason": ("    override_reason TEXT,\n", ""),
        "missing_failure_code": (
            "    completed_at TEXT,\n    failure_code TEXT\n",
            "    completed_at TEXT\n",
        ),
        "missing_status_check": (
            "    status TEXT NOT NULL CHECK(status IN\n"
            "        ('issued','reserved','executed','failed','expired')),\n",
            "    status TEXT NOT NULL,\n",
        ),
        "missing_kind_check": (
            "    protected_kind TEXT NOT NULL CHECK(protected_kind IN\n"
            "        ('framework_ui','release_shell','remote_operation','commit','push','blocker')),\n",
            "    protected_kind TEXT NOT NULL,\n",
        ),
    }
    old, new = replacements[token_schema_change]
    damaged = schema.replace(old, new, 1)
    assert damaged != schema
    schema_version = svc.be._conn.execute("PRAGMA schema_version").fetchone()[0]
    svc.be._conn.execute("PRAGMA writable_schema=ON")
    svc.be._conn.execute(
        "UPDATE sqlite_master SET sql=? WHERE type='table' AND name='memory_preflight_tokens'",
        (damaged,),
    )
    svc.be._conn.execute("PRAGMA writable_schema=OFF")
    svc.be._conn.execute(f"PRAGMA schema_version={schema_version + 1}")
    svc.be._conn.commit()

    with pytest.raises(ExecutionLeaseError, match="CAPABILITY_MISMATCH"):
        reconcile_execution_lease_state(svc, trusted_assertion(project))

    assert svc.be._q1("SELECT value FROM meta WHERE key='execution_lease_maintenance'")
    assert svc.be._execution_lease_by_nonce(lease["nonce"])["revoked_at"] is not None
