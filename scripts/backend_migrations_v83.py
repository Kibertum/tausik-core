"""Migration v83: atomic bounded task packages bound to execution leases."""

MIGRATION_V83 = [
    "ALTER TABLE execution_leases ADD COLUMN task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL",
    "ALTER TABLE execution_leases ADD COLUMN task_package_fingerprint TEXT",
    """CREATE TABLE IF NOT EXISTS task_context_packages (
        task_slug TEXT PRIMARY KEY REFERENCES tasks(slug) ON DELETE CASCADE,
        fingerprint TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        bytes INTEGER NOT NULL CHECK(bytes >= 0),
        max_bytes INTEGER NOT NULL CHECK(max_bytes > 0),
        task_revision TEXT NOT NULL,
        selected_memory_revisions TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_task_context_packages_fingerprint ON task_context_packages(fingerprint)",
]
