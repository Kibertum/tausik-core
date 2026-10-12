"""TAUSIK legacy schema migrations v2-v11.

Separated from backend_migrations.py to keep files under 400 lines.
These migrations are historical -- they ran once per database during upgrades
from early schema versions. v10-v11 moved here in v1.5 when the current
module hit the filesize cap (v15-receipt-emit-on-verify).
"""

from __future__ import annotations

LEGACY_MIGRATIONS: dict[int, list[str]] = {
    2: [
        # Rebuild stories table with CASCADE FK
        """CREATE TABLE IF NOT EXISTS stories_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            epic_id INTEGER NOT NULL REFERENCES epics(id) ON DELETE CASCADE,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            description TEXT,
            created_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO stories_new SELECT * FROM stories",
        "DROP TABLE IF EXISTS stories",
        "ALTER TABLE stories_new RENAME TO stories",
        # Rebuild tasks table with CASCADE FK
        """CREATE TABLE IF NOT EXISTS tasks_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planning',
            stack TEXT, complexity TEXT, role TEXT, score INTEGER,
            goal TEXT, plan TEXT, notes TEXT,
            acceptance_criteria TEXT, relevant_files TEXT,
            started_at TEXT, completed_at TEXT, blocked_at TEXT,
            attempts INTEGER DEFAULT 0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """INSERT OR IGNORE INTO tasks_new
           SELECT id, story_id, slug, title, status, stack, complexity,
                  role, score, goal, plan, notes, acceptance_criteria,
                  relevant_files, started_at, completed_at, blocked_at,
                  attempts, created_at, updated_at
           FROM tasks""",
        "DROP TABLE IF EXISTS tasks",
        "ALTER TABLE tasks_new RENAME TO tasks",
    ],
    3: [
        # Multi-agent support -- claimed_by field on tasks
        "ALTER TABLE tasks ADD COLUMN claimed_by TEXT",
    ],
    4: [
        # Audit log -- events table + indexes
        """CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT,
            details TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_type, entity_id)",
        "CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at)",
    ],
    5: [
        # Recreate audit triggers with json_object() for safe escaping
        "DROP TRIGGER IF EXISTS tasks_audit_insert",
        "DROP TRIGGER IF EXISTS tasks_audit_status",
        "DROP TRIGGER IF EXISTS tasks_audit_claim",
        "DROP TRIGGER IF EXISTS tasks_audit_delete",
    ],
    6: [
        # CHECK constraints -- rebuild epics, stories, tasks, memory, plans
        # --- epics ---
        """CREATE TABLE IF NOT EXISTS epics_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active', 'done', 'archived')),
            description TEXT,
            created_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO epics_new SELECT * FROM epics",
        "DROP TABLE IF EXISTS epics",
        "ALTER TABLE epics_new RENAME TO epics",
        # --- stories ---
        """CREATE TABLE IF NOT EXISTS stories_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            epic_id INTEGER NOT NULL REFERENCES epics(id) ON DELETE CASCADE,
            slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open'
                CHECK(status IN ('open', 'active', 'done')),
            description TEXT,
            created_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO stories_new SELECT * FROM stories",
        "DROP TABLE IF EXISTS stories",
        "ALTER TABLE stories_new RENAME TO stories",
        # --- tasks ---
        """CREATE TABLE IF NOT EXISTS tasks_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
            slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planning'
                CHECK(status IN ('planning', 'active', 'blocked', 'review', 'done')),
            stack TEXT,
            complexity TEXT CHECK(complexity IS NULL OR complexity IN ('simple', 'medium', 'complex')),
            role TEXT CHECK(role IS NULL OR role IN ('developer', 'architect', 'qa', 'tech-writer', 'ui-ux')),
            score INTEGER,
            goal TEXT, plan TEXT, notes TEXT,
            acceptance_criteria TEXT, relevant_files TEXT,
            started_at TEXT, completed_at TEXT, blocked_at TEXT,
            attempts INTEGER DEFAULT 0,
            claimed_by TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """INSERT OR IGNORE INTO tasks_new
           SELECT id, story_id, slug, title, status, stack, complexity,
                  role, score, goal, plan, notes, acceptance_criteria,
                  relevant_files, started_at, completed_at, blocked_at,
                  attempts, claimed_by, created_at, updated_at
           FROM tasks""",
        "DROP TABLE IF EXISTS tasks",
        "ALTER TABLE tasks_new RENAME TO tasks",
        # --- memory ---
        """CREATE TABLE IF NOT EXISTS memory_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('pattern', 'gotcha', 'convention', 'context')),
            title TEXT NOT NULL,
            content TEXT NOT NULL, tags TEXT,
            task_slug TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO memory_new SELECT * FROM memory",
        "DROP TABLE IF EXISTS memory",
        "ALTER TABLE memory_new RENAME TO memory",
        # --- plans ---
        """CREATE TABLE IF NOT EXISTS plans_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
            title TEXT NOT NULL, content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK(status IN ('draft', 'active', 'done', 'abandoned')),
            task_slug TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO plans_new SELECT * FROM plans",
        "DROP TABLE IF EXISTS plans",
        "ALTER TABLE plans_new RENAME TO plans",
    ],
    7: [
        # FK for task_slug -> tasks(slug) ON DELETE SET NULL in 4 tables
        # --- decisions ---
        """CREATE TABLE IF NOT EXISTS decisions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision TEXT NOT NULL,
            task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
            rationale TEXT, created_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO decisions_new SELECT * FROM decisions",
        "DROP TABLE IF EXISTS decisions",
        "ALTER TABLE decisions_new RENAME TO decisions",
        # --- memory ---
        """CREATE TABLE IF NOT EXISTS memory_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('pattern', 'gotcha', 'convention', 'context')),
            title TEXT NOT NULL,
            content TEXT NOT NULL, tags TEXT,
            task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO memory_new SELECT * FROM memory",
        "DROP TABLE IF EXISTS memory",
        "ALTER TABLE memory_new RENAME TO memory",
        # --- web_cache ---
        """CREATE TABLE IF NOT EXISTS web_cache_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL, url TEXT, title TEXT,
            content TEXT NOT NULL, tags TEXT,
            task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
            created_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO web_cache_new SELECT * FROM web_cache",
        "DROP TABLE IF EXISTS web_cache",
        "ALTER TABLE web_cache_new RENAME TO web_cache",
        # --- plans ---
        """CREATE TABLE IF NOT EXISTS plans_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
            title TEXT NOT NULL, content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK(status IN ('draft', 'active', 'done', 'abandoned')),
            task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "INSERT OR IGNORE INTO plans_new SELECT * FROM plans",
        "DROP TABLE IF EXISTS plans",
        "ALTER TABLE plans_new RENAME TO plans",
    ],
    # --- v8: Add ui-ux role ---
    8: [
        """CREATE TABLE IF NOT EXISTS tasks_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
            slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planning'
                CHECK(status IN ('planning', 'active', 'blocked', 'review', 'done')),
            stack TEXT,
            complexity TEXT CHECK(complexity IS NULL OR complexity IN ('simple', 'medium', 'complex')),
            role TEXT CHECK(role IS NULL OR role IN ('developer', 'architect', 'qa', 'tech-writer', 'ui-ux')),
            score INTEGER,
            goal TEXT, plan TEXT, notes TEXT,
            acceptance_criteria TEXT, relevant_files TEXT,
            started_at TEXT, completed_at TEXT, blocked_at TEXT,
            attempts INTEGER DEFAULT 0,
            claimed_by TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """INSERT OR IGNORE INTO tasks_new
           SELECT id, story_id, slug, title, status, stack, complexity,
                  role, score, goal, plan, notes, acceptance_criteria,
                  relevant_files, started_at, completed_at, blocked_at,
                  attempts, claimed_by, created_at, updated_at
           FROM tasks""",
        "DROP TABLE IF EXISTS tasks",
        "ALTER TABLE tasks_new RENAME TO tasks",
    ],
    # --- v9: v2.0 -- drop web_cache, plans, context; free-text roles ---
    9: [
        # Drop FTS indexes and triggers for removed tables
        "DROP TRIGGER IF EXISTS web_cache_ai",
        "DROP TRIGGER IF EXISTS web_cache_ad",
        "DROP TRIGGER IF EXISTS web_cache_au",
        "DROP TRIGGER IF EXISTS plans_ai",
        "DROP TRIGGER IF EXISTS plans_ad",
        "DROP TRIGGER IF EXISTS plans_au",
        "DROP TABLE IF EXISTS fts_web_cache",
        "DROP TABLE IF EXISTS fts_plans",
        # Drop tables
        "DROP TABLE IF EXISTS web_cache",
        "DROP TABLE IF EXISTS plans",
        "DROP TABLE IF EXISTS context",
        # Rebuild tasks without role CHECK constraint (free-text roles)
        """CREATE TABLE IF NOT EXISTS tasks_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
            slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planning'
                CHECK(status IN ('planning', 'active', 'blocked', 'review', 'done')),
            stack TEXT,
            complexity TEXT CHECK(complexity IS NULL OR complexity IN ('simple', 'medium', 'complex')),
            role TEXT,
            score INTEGER,
            goal TEXT, plan TEXT, notes TEXT,
            acceptance_criteria TEXT, relevant_files TEXT,
            started_at TEXT, completed_at TEXT, blocked_at TEXT,
            attempts INTEGER DEFAULT 0,
            claimed_by TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """INSERT OR IGNORE INTO tasks_new
           SELECT id, story_id, slug, title, status, stack, complexity,
                  role, score, goal, plan, notes, acceptance_criteria,
                  relevant_files, started_at, completed_at, blocked_at,
                  attempts, claimed_by, created_at, updated_at
           FROM tasks""",
        "DROP TABLE IF EXISTS tasks",
        "ALTER TABLE tasks_new RENAME TO tasks",
        # Drop removed indexes
        "DROP INDEX IF EXISTS idx_web_cache_task_slug",
        "DROP INDEX IF EXISTS idx_plans_task_slug",
        "DROP INDEX IF EXISTS idx_plans_status",
    ],
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
}


def seed_v18_roles(conn) -> dict:
    """Post-migration seed for v18 roles table.

    Lives here (with the legacy migrations) to keep backend_migrations.py under
    the 400-line filesize cap; re-exported from backend_migrations for callers.
    """
    import re
    import sqlite3 as _sqlite3

    try:
        rows = conn.execute(
            "SELECT DISTINCT role FROM tasks WHERE role IS NOT NULL AND role != ''"
        ).fetchall()
    except _sqlite3.OperationalError:
        return {"seeded": 0, "tasks_rewritten": 0, "dropped_legacy_values": []}
    legacy = {r[0] for r in rows if r[0]}
    seeded = 0
    rewritten = 0
    dropped: list[str] = []
    for original in legacy:
        norm = re.sub(r"[^a-z0-9-]+", "-", original.strip().lower()).strip("-")
        if not norm or not re.match(r"^[a-z0-9][a-z0-9-]*$", norm):
            dropped.append(original)
            continue
        if len(norm) > 64:
            norm = norm[:64].rstrip("-")
        title = norm.replace("-", " ").title()
        conn.execute(
            "INSERT OR IGNORE INTO roles(slug, title, description, created_at, updated_at) "
            "VALUES (?, ?, NULL, "
            "strftime('%Y-%m-%dT%H:%M:%SZ','now'), "
            "strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
            (norm, title),
        )
        seeded += 1
        if original != norm:
            cur = conn.execute("UPDATE tasks SET role = ? WHERE role = ?", (norm, original))
            rewritten += cur.rowcount
    return {
        "seeded": seeded,
        "tasks_rewritten": rewritten,
        "dropped_legacy_values": dropped,
    }
