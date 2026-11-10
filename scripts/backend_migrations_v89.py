"""Migration v89: trusted turn records and lease-bound attempt evidence."""

MIGRATION_V89 = [
    "ALTER TABLE task_continuity_state ADD COLUMN recovery_action TEXT CHECK(recovery_action IS NULL OR recovery_action IN ('checkpoint','block','decompose'))",
    """CREATE TABLE IF NOT EXISTS can_stop_turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_identity TEXT NOT NULL,
        host_instance TEXT NOT NULL,
        thread_id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        lease_id INTEGER NOT NULL REFERENCES execution_leases(id) ON DELETE CASCADE,
        task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
        request_kind TEXT NOT NULL CHECK(request_kind IN ('read_only','work')),
        payload_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        consumed_at TEXT,
        decision TEXT,
        UNIQUE(host_instance, thread_id, turn_id)
    )""",
    """CREATE TABLE IF NOT EXISTS task_attempt_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
        lease_id INTEGER NOT NULL REFERENCES execution_leases(id) ON DELETE CASCADE,
        event_kind TEXT NOT NULL CHECK(event_kind IN ('attempt','capability','authority')),
        status TEXT NOT NULL CHECK(status IN ('failed','unavailable','verified')),
        detail_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_can_stop_turn_current ON can_stop_turns(host_instance,thread_id,consumed_at,id)",
    "CREATE INDEX IF NOT EXISTS idx_task_attempt_events_task ON task_attempt_events(task_slug,lease_id,id)",
]
