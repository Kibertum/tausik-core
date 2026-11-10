"""Schema and index attestation for the Codex execution capability."""

from __future__ import annotations

import re
from typing import Any

CAPABILITY_VERSION = 2
_COLUMNS = {
    "tasks": {"task_package_legacy"},
    "execution_leases": {
        "session_id",
        "project_identity",
        "host_instance",
        "thread_id",
        "assertion_nonce",
        "assertion_issued_at",
        "assertion_expires_at",
        "nonce",
        "issued_at",
        "expires_at",
        "revoked_at",
        "projection_build",
        "capability_min",
        "capability_max",
        "task_slug",
        "task_package_fingerprint",
    },
    "execution_lease_state": {
        "singleton",
        "mode",
        "reason",
        "projection_build",
        "capability_version",
        "updated_at",
    },
    "execution_authorizations": {
        "id",
        "lease_id",
        "route",
        "arguments_hash",
        "issued_at",
        "expires_at",
        "consumed_at",
    },
    "task_context_packages": {
        "task_slug",
        "fingerprint",
        "payload_json",
        "bytes",
        "max_bytes",
        "task_revision",
        "selected_memory_revisions",
        "created_at",
    },
    "memory_preflight_tokens": {
        "id",
        "token",
        "lease_id",
        "package_fingerprint",
        "content_revision",
        "acknowledged_ids",
        "protected_kind",
        "action_id",
        "payload_hash",
        "override_reason",
        "status",
        "issued_at",
        "expires_at",
        "reserved_at",
        "completed_at",
        "failure_code",
    },
    "memory_inspection_events": {
        "lease_id",
        "action_id",
        "content_revision",
        "selected_ids",
        "inspected_at",
    },
    "memory_preflight_attempt_audit": {
        "id",
        "source_token_id",
        "source_lease_id",
        "token",
        "package_fingerprint",
        "content_revision",
        "acknowledged_ids",
        "protected_kind",
        "action_id",
        "payload_hash",
        "override_reason",
        "status",
        "issued_at",
        "expires_at",
        "reserved_at",
        "completed_at",
        "failure_code",
    },
}
_INDEXES = {
    "idx_execution_leases_one_live_thread",
    "idx_execution_authorizations_pending",
    "idx_task_context_packages_fingerprint",
    "idx_memory_preflight_action",
    "idx_memory_preflight_expiry",
    "idx_memory_inspection_lease",
    "idx_memory_preflight_audit_action",
}


def _has_fk(svc: Any, table: str, parent: str, source: str, target: str, action: str) -> bool:
    rows = svc.be._conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    return any(
        row[2] == parent and row[3] == source and row[4] == target and row[6] == action
        for row in rows
    )


def schema_compatible(svc: Any) -> bool:
    from work_continuity import continuity_schema_compatible

    if not continuity_schema_compatible(svc.be):
        return False
    for table, required in _COLUMNS.items():
        rows = svc.be._conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not required <= {row[1] for row in rows}:
            return False
    indexes = {
        row[0]: " ".join((row[1] or "").upper().split())
        for row in svc.be._conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    if not _INDEXES <= indexes.keys():
        return False
    expected = {
        "idx_execution_leases_one_live_thread": (
            "CREATE UNIQUE INDEX IDX_EXECUTION_LEASES_ONE_LIVE_THREAD ON "
            "EXECUTION_LEASES(PROJECT_IDENTITY, HOST_INSTANCE, THREAD_ID) WHERE REVOKED_AT IS NULL"
        ),
        "idx_execution_authorizations_pending": (
            "CREATE INDEX IDX_EXECUTION_AUTHORIZATIONS_PENDING ON "
            "EXECUTION_AUTHORIZATIONS(ROUTE, ARGUMENTS_HASH, CONSUMED_AT, EXPIRES_AT)"
        ),
        "idx_task_context_packages_fingerprint": (
            "CREATE INDEX IDX_TASK_CONTEXT_PACKAGES_FINGERPRINT ON TASK_CONTEXT_PACKAGES(FINGERPRINT)"
        ),
        "idx_memory_preflight_action": (
            "CREATE INDEX IDX_MEMORY_PREFLIGHT_ACTION ON "
            "MEMORY_PREFLIGHT_TOKENS(LEASE_ID,ACTION_ID,PAYLOAD_HASH,STATUS)"
        ),
        "idx_memory_preflight_audit_action": (
            "CREATE INDEX IDX_MEMORY_PREFLIGHT_AUDIT_ACTION ON "
            "MEMORY_PREFLIGHT_ATTEMPT_AUDIT(ACTION_ID,PAYLOAD_HASH,STATUS)"
        ),
    }
    if any(indexes[name] != sql for name, sql in expected.items()):
        return False
    if not _has_fk(
        svc, "execution_authorizations", "execution_leases", "lease_id", "id", "CASCADE"
    ) or not _has_fk(
        svc, "memory_preflight_tokens", "execution_leases", "lease_id", "id", "CASCADE"
    ):
        return False
    if not _has_fk(svc, "execution_leases", "sessions", "session_id", "id", "CASCADE"):
        return False
    if not _has_fk(svc, "execution_leases", "tasks", "task_slug", "slug", "SET NULL"):
        return False
    if not _has_fk(svc, "task_context_packages", "tasks", "task_slug", "slug", "CASCADE"):
        return False
    table_sql = {
        row[0]: " ".join((row[1] or "").upper().split())
        for row in svc.be._conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' "
            "AND name IN ('execution_leases','execution_lease_state','memory_preflight_tokens',"
            "'memory_preflight_attempt_audit')"
        ).fetchall()
    }
    lease_sql = table_sql.get("execution_leases", "")
    state_sql = table_sql.get("execution_lease_state", "")
    token_sql = table_sql.get("memory_preflight_tokens", "")
    audit_sql = table_sql.get("memory_preflight_attempt_audit", "")
    return bool(
        re.search(r"(?:\(|,) NONCE TEXT NOT NULL UNIQUE(?:,|\))", lease_sql)
        and re.search(r"(?:\(|,) ASSERTION_NONCE TEXT NOT NULL UNIQUE(?:,|\))", lease_sql)
        and "CHECK(CAPABILITY_MIN > 0)" in lease_sql
        and "CHECK(CAPABILITY_MAX >= CAPABILITY_MIN)" in lease_sql
        and "SINGLETON INTEGER PRIMARY KEY CHECK(SINGLETON = 1)" in state_sql
        and "CHECK(MODE IN ('READY', 'MAINTENANCE'))" in state_sql
        and "CHECK(STATUS IN ('ISSUED','RESERVED','EXECUTED','FAILED','EXPIRED'))" in token_sql
        and "CHECK(PROTECTED_KIND IN ('FRAMEWORK_UI','RELEASE_SHELL','REMOTE_OPERATION','COMMIT','PUSH','BLOCKER'))"
        in token_sql
        and re.search(r"(?:\(|,) SOURCE_TOKEN_ID INTEGER NOT NULL UNIQUE(?:,|\))", audit_sql)
        and "CHECK(STATUS IN ('EXECUTED','FAILED','EXPIRED'))" in audit_sql
    )


__all__ = ["CAPABILITY_VERSION", "schema_compatible"]
