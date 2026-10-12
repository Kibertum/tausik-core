"""Migration v57: collapse the session_record pile in usage_events.

DATA ONLY -- no column, no index, nothing new on a database that already has the
table. `session_usage_record` mirrors a session's CUMULATIVE total into
`usage_events` and used to APPEND that mirror on every call, so the slice its own
docstring recommends -- "session totals only: WHERE source = 'session_record'" --
filled with snapshots of the same fact. Measured on this project in session #228:
15,517 rows for 155 sessions, summing to 88x the truth. The writer now replaces
instead of appending; this clears what the appending already wrote.

THE COLLAPSE IS EXACT, NOT A GUESS. Every row of a session carries that session's
running total, so the newest row is the complete answer and the rest are strictly
stale copies of it. Rows with no session_id fall into one group and keep a
representative rather than being deleted: an unattributable row is still evidence
that something was recorded.

FROZEN LITERAL, NOT AN IMPORT -- the same rule v52 and v56 state. The DELETE needs
`usage_events` to exist before it can be PREPARED (SQLite resolves table names at
prepare time, so a missing table is a hard error rather than a no-op), and partial
fixtures jump from an old version straight to head without it. The DDL below is
therefore a COPY of the shape as of v57, deliberately NOT re-extracted from
`backend_schema.SCHEMA_SQL`: reading the live schema would make a later column
addition retroactively change what this migration created, which is the defect
`backend_migrations_v52` was rewritten to remove. On every real database the
statement is a no-op.
"""

from __future__ import annotations

#: `usage_events` as it stood at v57. A copy on purpose -- see the module note.
_USAGE_EVENTS_AS_OF_V57 = """CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    model_id TEXT,
    tokens_input INTEGER NOT NULL CHECK(tokens_input >= 0),
    tokens_output INTEGER NOT NULL CHECK(tokens_output >= 0),
    tokens_total INTEGER NOT NULL CHECK(tokens_total >= 0),
    cost_usd REAL NOT NULL DEFAULT 0 CHECK(cost_usd >= 0),
    tool_calls INTEGER NOT NULL DEFAULT 0 CHECK(tool_calls >= 0),
    source TEXT NOT NULL CHECK(source IN ('session_record', 'manual', 'posttool')),
    recorded_at TEXT NOT NULL,
    tool_name TEXT
);"""

MIGRATION_V57: list[str] = [
    _USAGE_EVENTS_AS_OF_V57,
    "DELETE FROM usage_events "
    "WHERE source = 'session_record' AND id NOT IN ("
    "SELECT MAX(id) FROM usage_events WHERE source = 'session_record' "
    "GROUP BY session_id)",
]
