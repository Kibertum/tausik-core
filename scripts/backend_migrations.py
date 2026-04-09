"""TAUSIK schema migrations -- version-by-version SQL transformations.

Separated from backend_schema.py to keep files under 400 lines.
Each migration is a list of SQL statements applied in order.
SQLite cannot ALTER TABLE to add CASCADE/CHECK -- must rebuild via
create temp -> copy -> drop -> rename. Migrations are irreversible.

Legacy migrations (v2-v9) are in backend_migrations_legacy.py.
"""

from __future__ import annotations

from backend_migrations_legacy import LEGACY_MIGRATIONS

# Current migrations (v10+)
_CURRENT_MIGRATIONS: dict[int, list[str]] = {
    # --- v10: SENAR alignment -- defect_of, dead_end memory type, explorations ---
    10: [
        # Add defect_of column to tasks
        "ALTER TABLE tasks ADD COLUMN defect_of TEXT REFERENCES tasks(slug) ON DELETE SET NULL",
        # Rebuild memory with dead_end type
        """CREATE TABLE IF NOT EXISTS memory_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('pattern', 'gotcha', 'convention', 'context', 'dead_end')),
            title TEXT NOT NULL,
            content TEXT NOT NULL, tags TEXT,
            task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO memory_new SELECT * FROM memory",
        "DROP TABLE IF EXISTS memory",
        "ALTER TABLE memory_new RENAME TO memory",
        # Explorations table
        """CREATE TABLE IF NOT EXISTS explorations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            time_limit_min INTEGER DEFAULT 30,
            task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            created_at TEXT NOT NULL
        )""",
    ],
    # --- v11: Graph memory -- memory_edges table ---
    11: [
        """CREATE TABLE IF NOT EXISTS memory_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL CHECK(source_type IN ('memory', 'decision')),
            source_id INTEGER NOT NULL,
            target_type TEXT NOT NULL CHECK(target_type IN ('memory', 'decision')),
            target_id INTEGER NOT NULL,
            relation TEXT NOT NULL CHECK(relation IN ('supersedes', 'caused_by', 'relates_to', 'contradicts')),
            confidence REAL NOT NULL DEFAULT 1.0,
            created_by TEXT,
            valid_from TEXT NOT NULL,
            valid_to TEXT,
            invalidated_by INTEGER REFERENCES memory_edges(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_edges_source ON memory_edges(source_type, source_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_target ON memory_edges(target_type, target_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_relation ON memory_edges(relation)",
        "CREATE INDEX IF NOT EXISTS idx_edges_valid ON memory_edges(valid_to)",
    ],
    # --- v12: Scope field on tasks (SENAR Core Rule 2) ---
    12: [
        "ALTER TABLE tasks ADD COLUMN scope TEXT",
    ],
    # --- v13: Scope exclusion field (SENAR Core Start Gate #4) ---
    13: [
        "ALTER TABLE tasks ADD COLUMN scope_exclude TEXT",
    ],
    # --- v14: Structured task logs table ---
    14: [
        """CREATE TABLE IF NOT EXISTS task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
            message TEXT NOT NULL,
            phase TEXT CHECK(phase IS NULL OR phase IN
                ('planning', 'implementation', 'review', 'testing', 'done')),
            diff_stats TEXT,
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_slug ON task_logs(task_slug)",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_phase ON task_logs(phase)",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_created ON task_logs(created_at)",
        """CREATE VIRTUAL TABLE IF NOT EXISTS fts_task_logs USING fts5(
            message,
            content='task_logs', content_rowid='id'
        )""",
    ],
    # --- v15: Rebuild memory_edges with proper constraints + orphan cleanup ---
    15: [
        # Clean up orphaned edges before rebuild
        "DELETE FROM memory_edges WHERE source_type='memory' AND source_id NOT IN (SELECT id FROM memory)",
        "DELETE FROM memory_edges WHERE source_type='decision' AND source_id NOT IN (SELECT id FROM decisions)",
        "DELETE FROM memory_edges WHERE target_type='memory' AND target_id NOT IN (SELECT id FROM memory)",
        "DELETE FROM memory_edges WHERE target_type='decision' AND target_id NOT IN (SELECT id FROM decisions)",
        # Rebuild memory_edges with proper constraints
        """CREATE TABLE memory_edges_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL CHECK(source_type IN ('memory', 'decision')),
            source_id INTEGER NOT NULL,
            target_type TEXT NOT NULL CHECK(target_type IN ('memory', 'decision')),
            target_id INTEGER NOT NULL,
            relation TEXT NOT NULL CHECK(relation IN ('supersedes', 'caused_by', 'relates_to', 'contradicts')),
            confidence REAL NOT NULL DEFAULT 1.0,
            created_by TEXT,
            valid_from TEXT NOT NULL,
            valid_to TEXT,
            invalidated_by INTEGER REFERENCES memory_edges(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL
        )""",
        "INSERT INTO memory_edges_new SELECT * FROM memory_edges",
        "DROP TABLE memory_edges",
        "ALTER TABLE memory_edges_new RENAME TO memory_edges",
        "CREATE INDEX IF NOT EXISTS idx_edges_source ON memory_edges(source_type, source_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_target ON memory_edges(target_type, target_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_relation ON memory_edges(relation)",
        "CREATE INDEX IF NOT EXISTS idx_edges_valid ON memory_edges(valid_to)",
    ],
}

# Merged: legacy + current
MIGRATIONS: dict[int, list[str]] = {**LEGACY_MIGRATIONS, **_CURRENT_MIGRATIONS}


def run_migrations(conn: "sqlite3.Connection", current_version: int) -> int:  # noqa: F821
    """Apply pending migrations. Returns new version.

    Each migration is a list of SQL statements executed in order.
    FK checks are disabled during table rebuilds (SQLite requirement).
    Migrations are irreversible -- no rollback support.
    """
    for ver in sorted(MIGRATIONS.keys()):
        if ver > current_version:
            statements = MIGRATIONS[ver]
            # Disable FK checks for table rebuilds (DROP/RENAME)
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("BEGIN")
            try:
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt and not stmt.startswith("--"):
                        conn.execute(stmt)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                conn.execute("PRAGMA foreign_keys=ON")
                raise
            # Re-enable and verify FK integrity
            conn.execute("PRAGMA foreign_keys=ON")
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"Migration v{ver} broke FK integrity: {violations}")
            current_version = ver
    return current_version
