"""Migration v87: repair lease attestation and preserve preflight attempt history."""

MIGRATION_V87 = [
    # Terminal attempts are immutable audit evidence. The live token table
    # cannot retain them while its parent lease table is rebuilt, so preserve
    # the complete terminal record in a FK-free audit table first.
    """CREATE TABLE IF NOT EXISTS memory_preflight_attempt_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_token_id INTEGER NOT NULL UNIQUE,
        source_lease_id INTEGER NOT NULL,
        token TEXT NOT NULL,
        package_fingerprint TEXT NOT NULL,
        content_revision TEXT NOT NULL,
        acknowledged_ids TEXT NOT NULL,
        protected_kind TEXT NOT NULL,
        action_id TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        override_reason TEXT,
        status TEXT NOT NULL CHECK(status IN ('executed','failed','expired')),
        issued_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        reserved_at TEXT,
        completed_at TEXT,
        failure_code TEXT
    )""",
    """INSERT INTO memory_preflight_attempt_audit(
        source_token_id,source_lease_id,token,package_fingerprint,content_revision,
        acknowledged_ids,protected_kind,action_id,payload_hash,override_reason,status,
        issued_at,expires_at,reserved_at,completed_at,failure_code)
       SELECT id,lease_id,token,package_fingerprint,content_revision,acknowledged_ids,
        protected_kind,action_id,payload_hash,override_reason,status,issued_at,expires_at,
        reserved_at,completed_at,failure_code
       FROM memory_preflight_tokens WHERE status IN ('executed','failed','expired')""",
    "CREATE INDEX IF NOT EXISTS idx_memory_preflight_audit_action ON memory_preflight_attempt_audit(action_id,payload_hash,status)",
    # Capability v2 deliberately revokes all live authority before rebuilding
    # the parent table. Owner reconciliation is required before new leases.
    "DELETE FROM memory_preflight_tokens",
    "DELETE FROM execution_authorizations",
    "DELETE FROM execution_leases",
    "DROP TABLE execution_leases",
    """CREATE TABLE execution_leases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        project_identity TEXT NOT NULL,
        host_instance TEXT NOT NULL,
        thread_id TEXT NOT NULL,
        assertion_nonce TEXT NOT NULL UNIQUE,
        assertion_issued_at TEXT NOT NULL,
        assertion_expires_at TEXT NOT NULL,
        nonce TEXT NOT NULL UNIQUE,
        issued_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        revoked_at TEXT,
        projection_build TEXT NOT NULL,
        capability_min INTEGER NOT NULL,
        capability_max INTEGER NOT NULL,
        task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
        task_package_fingerprint TEXT,
        CHECK(capability_min > 0),
        CHECK(capability_max >= capability_min)
    )""",
    """CREATE UNIQUE INDEX idx_execution_leases_one_live_thread
       ON execution_leases(project_identity, host_instance, thread_id)
       WHERE revoked_at IS NULL""",
    "ALTER TABLE memory_preflight_tokens RENAME TO memory_preflight_tokens_v86",
    """CREATE TABLE memory_preflight_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL UNIQUE,
        lease_id INTEGER NOT NULL REFERENCES execution_leases(id) ON DELETE CASCADE,
        package_fingerprint TEXT NOT NULL,
        content_revision TEXT NOT NULL,
        acknowledged_ids TEXT NOT NULL,
        protected_kind TEXT NOT NULL CHECK(protected_kind IN
            ('framework_ui','release_shell','remote_operation','commit','push','blocker')),
        action_id TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        override_reason TEXT,
        status TEXT NOT NULL CHECK(status IN
            ('issued','reserved','executed','failed','expired')),
        issued_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        reserved_at TEXT,
        completed_at TEXT,
        failure_code TEXT
    )""",
    "DROP TABLE memory_preflight_tokens_v86",
    "CREATE INDEX idx_memory_preflight_action ON memory_preflight_tokens(lease_id,action_id,payload_hash,status)",
    "CREATE INDEX idx_memory_preflight_expiry ON memory_preflight_tokens(status,expires_at)",
    "UPDATE execution_lease_state SET mode='maintenance', reason='capability v2 requires owner reconciliation', capability_version=2",
]
