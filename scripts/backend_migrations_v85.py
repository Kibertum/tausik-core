"""Migration v85: durable work-continuity state and step evidence."""

MIGRATION_V85 = [
    """CREATE TABLE IF NOT EXISTS task_step_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
        step_num INTEGER NOT NULL CHECK(step_num > 0),
        evidence_ref TEXT NOT NULL,
        evidence_hash TEXT NOT NULL,
        package_fingerprint TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(task_slug, step_num, evidence_hash)
    )""",
    """CREATE TABLE IF NOT EXISTS task_continuity_state (
        task_slug TEXT PRIMARY KEY REFERENCES tasks(slug) ON DELETE CASCADE,
        package_fingerprint TEXT NOT NULL,
        first_incomplete_step INTEGER,
        last_evidence_ref TEXT,
        pending_requirement TEXT,
        recovery_lease_id INTEGER REFERENCES execution_leases(id) ON DELETE SET NULL,
        recovery_issued_at TEXT,
        recovery_consumed_at TEXT,
        refusal_hash TEXT,
        refusal_count INTEGER NOT NULL DEFAULT 0 CHECK(refusal_count >= 0),
        blocker_json TEXT,
        updated_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_task_step_evidence_task ON task_step_evidence(task_slug,step_num,id)",
    "CREATE INDEX IF NOT EXISTS idx_task_continuity_pending ON task_continuity_state(pending_requirement,recovery_consumed_at)",
]
