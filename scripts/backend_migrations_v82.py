"""Migration v82: durable host-thread execution leases."""

MIGRATION_V82 = [
    """CREATE TABLE IF NOT EXISTS execution_leases (
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
        CHECK(capability_min > 0),
        CHECK(capability_max >= capability_min)
    )""",
    """CREATE INDEX IF NOT EXISTS idx_execution_leases_thread
       ON execution_leases(project_identity, host_instance, thread_id, revoked_at)""",
    """CREATE INDEX IF NOT EXISTS idx_execution_leases_session
       ON execution_leases(session_id, revoked_at)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_leases_one_live_thread
       ON execution_leases(project_identity, host_instance, thread_id)
       WHERE revoked_at IS NULL""",
    """CREATE TABLE IF NOT EXISTS execution_lease_state (
        singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
        mode TEXT NOT NULL CHECK(mode IN ('ready', 'maintenance')),
        reason TEXT,
        projection_build TEXT NOT NULL,
        capability_version INTEGER NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS execution_authorizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lease_id INTEGER NOT NULL REFERENCES execution_leases(id) ON DELETE CASCADE,
        route TEXT NOT NULL,
        arguments_hash TEXT NOT NULL,
        issued_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT
    )""",
    """CREATE INDEX IF NOT EXISTS idx_execution_authorizations_pending
       ON execution_authorizations(route, arguments_hash, consumed_at, expires_at)""",
]
