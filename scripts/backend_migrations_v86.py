"""Migration v86: durable memory-preflight tokens and separate inspection telemetry."""

MIGRATION_V86 = [
    """CREATE TABLE IF NOT EXISTS memory_preflight_tokens (
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
    """CREATE TABLE IF NOT EXISTS memory_inspection_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lease_id INTEGER REFERENCES execution_leases(id) ON DELETE SET NULL,
        action_id TEXT NOT NULL,
        content_revision TEXT NOT NULL,
        selected_ids TEXT NOT NULL,
        inspected_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_memory_preflight_action ON memory_preflight_tokens(lease_id,action_id,payload_hash,status)",
    "CREATE INDEX IF NOT EXISTS idx_memory_preflight_expiry ON memory_preflight_tokens(status,expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_memory_inspection_lease ON memory_inspection_events(lease_id,inspected_at)",
]
