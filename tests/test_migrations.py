"""Tests for schema migrations — v1 → v2 → v3."""

import sqlite3
import pytest

# V1 schema: original tables WITHOUT CASCADE and WITHOUT claimed_by
V1_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS epics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    description TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_id INTEGER NOT NULL REFERENCES epics(id),
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    description TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER REFERENCES stories(id),
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning',
    stack TEXT, complexity TEXT, role TEXT, score INTEGER,
    goal TEXT, plan TEXT, notes TEXT,
    acceptance_criteria TEXT, relevant_files TEXT,
    started_at TEXT, completed_at TEXT, blocked_at TEXT,
    attempts INTEGER DEFAULT 0,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL, ended_at TEXT,
    summary TEXT, tasks_done TEXT DEFAULT '[]',
    handoff TEXT
);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision TEXT NOT NULL, task_slug TEXT,
    rationale TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL, title TEXT NOT NULL,
    content TEXT NOT NULL, tags TEXT,
    task_slug TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS web_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL, url TEXT, title TEXT,
    content TEXT NOT NULL, tags TEXT,
    task_slug TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL, content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    task_slug TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS context (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL, updated_at TEXT NOT NULL
);
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from backend_migrations import MIGRATIONS, run_migrations
from backend_schema import SCHEMA_VERSION


def _create_v1_db():
    """Create in-memory v1 database with sample data."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(V1_SCHEMA)
    conn.execute("INSERT INTO meta(key,value) VALUES('schema_version','1')")
    # Seed data
    conn.execute(
        "INSERT INTO epics(slug,title,status,created_at) VALUES(?,?,?,?)",
        ("e1", "Epic 1", "active", "2025-01-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO stories(epic_id,slug,title,status,created_at) VALUES(?,?,?,?,?)",
        (1, "s1", "Story 1", "open", "2025-01-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO tasks(story_id,slug,title,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        (1, "t1", "Task 1", "planning", "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO tasks(story_id,slug,title,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        (1, "t2", "Task 2", "done", "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"),
    )
    conn.commit()
    return conn


class TestMigrationV1ToV2:
    """Test v2 migration: rebuild tables with CASCADE DELETE."""

    def test_migration_preserves_data(self):
        conn = _create_v1_db()
        new_ver = run_migrations(conn, 1)
        assert new_ver == SCHEMA_VERSION  # All pending migrations applied

        # Verify data survived
        epics = conn.execute("SELECT * FROM epics").fetchall()
        assert len(epics) == 1
        stories = conn.execute("SELECT * FROM stories").fetchall()
        assert len(stories) == 1
        tasks = conn.execute("SELECT * FROM tasks").fetchall()
        assert len(tasks) == 2

    def test_cascade_delete_works_after_migration(self):
        conn = _create_v1_db()
        run_migrations(conn, 1)

        # Delete epic → should cascade to stories and tasks
        conn.execute("DELETE FROM epics WHERE slug='e1'")
        conn.commit()

        stories = conn.execute("SELECT * FROM stories").fetchall()
        assert len(stories) == 0
        tasks = conn.execute("SELECT * FROM tasks").fetchall()
        assert len(tasks) == 0

    def test_story_cascade_deletes_tasks(self):
        conn = _create_v1_db()
        run_migrations(conn, 1)

        conn.execute("DELETE FROM stories WHERE slug='s1'")
        conn.commit()

        tasks = conn.execute("SELECT * FROM tasks").fetchall()
        assert len(tasks) == 0
        # Epic still exists
        epics = conn.execute("SELECT * FROM epics").fetchall()
        assert len(epics) == 1

    def test_v1_has_no_cascade(self):
        """Verify v1 schema truly lacks CASCADE (so migration is needed)."""
        conn = _create_v1_db()
        # In v1, deleting epic should NOT cascade (FK not enforced with CASCADE)
        # But SQLite FK enforcement depends on PRAGMA — with FK ON, delete should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM epics WHERE slug='e1'")


class TestMigrationV2ToV3:
    """Test v3 migration: add claimed_by column."""

    def test_claimed_by_added(self):
        """Test that v3 migration adds claimed_by when applied from v2."""
        conn = _create_v1_db()
        # Apply only v2 by pretending current version is 1
        # Then apply v3 separately
        new_ver = run_migrations(conn, 1)
        assert new_ver == SCHEMA_VERSION

        # Verify claimed_by column exists and works
        conn.execute("UPDATE tasks SET claimed_by='agent-1' WHERE slug='t1'")
        conn.commit()
        row = conn.execute("SELECT claimed_by FROM tasks WHERE slug='t1'").fetchone()
        assert row[0] == "agent-1"

    def test_claimed_by_default_null(self):
        conn = _create_v1_db()
        run_migrations(conn, 1)

        row = conn.execute("SELECT claimed_by FROM tasks WHERE slug='t1'").fetchone()
        assert row[0] is None


class TestFullMigrationPath:
    """Test complete migration from v1 to latest."""

    def test_v1_to_latest(self):
        conn = _create_v1_db()
        new_ver = run_migrations(conn, 1)
        assert new_ver == SCHEMA_VERSION

        # All data preserved
        tasks = conn.execute("SELECT * FROM tasks").fetchall()
        assert len(tasks) == 2

        # CASCADE works
        conn.execute("DELETE FROM epics WHERE slug='e1'")
        conn.commit()
        tasks = conn.execute("SELECT * FROM tasks").fetchall()
        assert len(tasks) == 0

        # claimed_by exists
        conn.execute(
            "INSERT INTO epics(slug,title,status,created_at) VALUES(?,?,?,?)",
            ("e2", "E2", "active", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO stories(epic_id,slug,title,status,created_at) VALUES(?,?,?,?,?)",
            (2, "s2", "S2", "open", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks(story_id,slug,title,status,claimed_by,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (2, "t3", "T3", "active", "agent-1", "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z"),
        )
        conn.commit()
        row = conn.execute("SELECT claimed_by FROM tasks WHERE slug='t3'").fetchone()
        assert row[0] == "agent-1"

    def test_migration_idempotent(self):
        """Running migrations twice doesn't break anything."""
        conn = _create_v1_db()
        run_migrations(conn, 1)
        # Running again from current version should be no-op
        ver = run_migrations(conn, SCHEMA_VERSION)
        assert ver == SCHEMA_VERSION

        tasks = conn.execute("SELECT * FROM tasks").fetchall()
        assert len(tasks) == 2

    def test_new_db_no_migration_needed(self):
        """Fresh DB starts at latest version — no migrations applied."""
        conn = sqlite3.connect(":memory:")
        ver = run_migrations(conn, SCHEMA_VERSION)
        assert ver == SCHEMA_VERSION

    def test_task_fields_preserved_after_full_migration(self):
        """Ensure all task fields survive the table rebuild."""
        conn = _create_v1_db()
        # Add rich data to a task before migration
        conn.execute(
            "UPDATE tasks SET goal='build API', notes='WIP', "
            "acceptance_criteria='tests pass', stack='python', "
            "complexity='medium', role='developer', score=3 "
            "WHERE slug='t1'"
        )
        conn.commit()

        run_migrations(conn, 1)

        row = conn.execute(
            "SELECT goal, notes, acceptance_criteria, stack, complexity, role, score "
            "FROM tasks WHERE slug='t1'"
        ).fetchone()
        assert row[0] == "build API"
        assert row[1] == "WIP"
        assert row[2] == "tests pass"
        assert row[3] == "python"
        assert row[4] == "medium"
        assert row[5] == "developer"
        assert row[6] == 3

    def test_migration_v14_creates_task_logs(self):
        """Migration v14 creates task_logs table and FTS index."""
        conn = _create_v1_db()
        run_migrations(conn, 1)

        # Verify task_logs table exists
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        assert "task_logs" in tables

        # Verify columns
        cols = [r[1] for r in conn.execute("PRAGMA table_info(task_logs)").fetchall()]
        assert "task_slug" in cols
        assert "message" in cols
        assert "phase" in cols
        assert "diff_stats" in cols
        assert "created_at" in cols

        # Verify FTS table
        assert "fts_task_logs" in tables

        # Verify we can insert and query
        conn.execute(
            "INSERT INTO task_logs(task_slug, message, phase, created_at) "
            "VALUES('t1', 'test log', 'implementation', '2026-01-01T00:00:00Z')"
        )
        conn.commit()
        rows = conn.execute("SELECT * FROM task_logs WHERE task_slug='t1'").fetchall()
        assert len(rows) == 1
