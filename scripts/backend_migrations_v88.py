"""Migration v88: repair the terminal preflight audit capability on stamped v87 DBs."""

MIGRATION_V88 = [
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
    "CREATE INDEX IF NOT EXISTS idx_memory_preflight_audit_action ON memory_preflight_attempt_audit(action_id,payload_hash,status)",
]
