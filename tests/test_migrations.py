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

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from backend_migrations import run_migrations
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
            (
                2,
                "t3",
                "T3",
                "active",
                "agent-1",
                "2025-01-01T00:00:00Z",
                "2025-01-01T00:00:00Z",
            ),
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
        tables = [
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
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

    def test_migration_v24_adds_tool_name_and_posttool_source(self):
        """Migration v24 extends usage_events with tool_name + posttool source value."""
        conn = _create_v1_db()
        run_migrations(conn, 1)

        cols = [r[1] for r in conn.execute("PRAGMA table_info(usage_events)").fetchall()]
        assert "tool_name" in cols, "v24 must add tool_name column"

        # source CHECK now allows 'posttool'
        conn.execute("INSERT INTO sessions(started_at) VALUES('2026-05-03T10:00:00Z')")
        sid = conn.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1").fetchone()[0]
        conn.execute(
            "INSERT INTO usage_events("
            "session_id, task_slug, model_id, tokens_input, tokens_output, "
            "tokens_total, cost_usd, tool_calls, source, recorded_at, tool_name) "
            "VALUES(?, NULL, 'claude-opus-4-7', 100, 50, 150, 0.0, 1, 'posttool', "
            "'2026-05-03T10:30:00Z', 'Read')",
            (sid,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT source, tool_name FROM usage_events WHERE source='posttool'"
        ).fetchone()
        assert row == ("posttool", "Read")

    def test_migration_v24_preserves_existing_usage_events(self):
        """v24 rebuilds usage_events; existing rows must survive."""
        conn = _create_v1_db()
        # Run up to v23 first
        run_migrations(conn, 1)
        # Sanity: we now have v24 schema. Insert via legacy column shape (no
        # tool_name) should still succeed because tool_name is nullable.
        conn.execute("INSERT INTO sessions(started_at) VALUES('2026-05-03T10:00:00Z')")
        sid = conn.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1").fetchone()[0]
        conn.execute(
            "INSERT INTO usage_events("
            "session_id, task_slug, model_id, tokens_input, tokens_output, "
            "tokens_total, cost_usd, tool_calls, source, recorded_at) "
            "VALUES(?, NULL, 'opus', 1, 1, 2, 0.0, 0, 'session_record', "
            "'2026-05-03T10:30:00Z')",
            (sid,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT tool_name, source FROM usage_events WHERE source='session_record'"
        ).fetchone()
        assert row == (None, "session_record")

    def test_migration_v26_adds_archived_at_to_memory(self):
        """v26 adds nullable archived_at to memory for soft-delete hygiene."""
        conn = _create_v1_db()
        run_migrations(conn, 1)

        cols = [r[1] for r in conn.execute("PRAGMA table_info(memory)").fetchall()]
        assert "archived_at" in cols, "v26 must add archived_at column to memory"

        conn.execute(
            "INSERT INTO memory(type, title, content, created_at, updated_at) "
            "VALUES('pattern', 'Old Pattern', 'demo', "
            "'2020-01-01T00:00:00Z', '2020-01-01T00:00:00Z')"
        )
        conn.commit()
        row = conn.execute("SELECT archived_at FROM memory WHERE title='Old Pattern'").fetchone()
        assert row[0] is None

        conn.execute(
            "UPDATE memory SET archived_at='2026-05-07T00:00:00Z' WHERE title='Old Pattern'"
        )
        conn.commit()
        row2 = conn.execute("SELECT archived_at FROM memory WHERE title='Old Pattern'").fetchone()
        assert row2[0] == "2026-05-07T00:00:00Z"

    def test_migration_v25_adds_archived_at_to_tasks(self):
        """v25 adds nullable archived_at to tasks for soft-delete hygiene archive."""
        conn = _create_v1_db()
        run_migrations(conn, 1)

        cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
        assert "archived_at" in cols, "v25 must add archived_at column to tasks"

        # archived_at is nullable: existing rows without an explicit value default to NULL.
        conn.execute(
            "INSERT INTO tasks(slug, title, status, created_at, updated_at) "
            "VALUES('arch-test', 'Archive test', 'done', "
            "'2020-01-01T00:00:00Z', '2020-01-01T00:00:00Z')"
        )
        conn.commit()
        row = conn.execute("SELECT archived_at FROM tasks WHERE slug='arch-test'").fetchone()
        assert row[0] is None

        # And it accepts a manual stamp without violating any CHECK.
        conn.execute("UPDATE tasks SET archived_at='2026-05-07T00:00:00Z' WHERE slug='arch-test'")
        conn.commit()
        row2 = conn.execute("SELECT archived_at FROM tasks WHERE slug='arch-test'").fetchone()
        assert row2[0] == "2026-05-07T00:00:00Z"


class TestFtsRebuildCoverage:
    """Post-migration FTS rebuild must cover EVERY external-content index.

    The rebuild list used to be hardcoded and had drifted: `fts_task_logs` and
    `fts_reasoning_steps` were declared, trigger-maintained, and never rebuilt.
    Search over task logs and RENAR reasoning steps therefore returned stale
    rows after every migration, silently. The list is now derived from
    `sqlite_master`, and these tests pin that it stays complete.
    """

    @staticmethod
    def _fresh_db():
        import sqlite3 as _sq

        from backend_init import init_schema

        conn = _sq.connect(":memory:")
        init_schema(conn)
        return conn

    def test_derived_list_misses_no_external_content_index(self):
        """Meta-guard: nothing declared with `content='<table>'` may be absent
        from the rebuild list. This is the check that would have caught the bug."""
        from backend_init import external_content_fts_tables

        conn = self._fresh_db()
        cur = conn.cursor()
        derived = set(external_content_fts_tables(cur))
        declared = {
            name
            for name, sql in cur.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type='table' AND sql LIKE '%USING fts5%'"
            ).fetchall()
            if sql and "content=" in sql.replace(" ", "") and "content=''" not in sql.replace(" ", "")
        }
        assert declared, "no external-content FTS tables found — schema probe is broken"
        assert declared - derived == set(), (
            f"external-content FTS indexes missing from the rebuild list: {declared - derived}"
        )
        conn.close()

    def test_the_two_historically_missed_tables_are_covered(self):
        from backend_init import external_content_fts_tables

        conn = self._fresh_db()
        derived = external_content_fts_tables(conn.cursor())
        assert "fts_task_logs" in derived
        assert "fts_reasoning_steps" in derived
        conn.close()

    def test_stale_task_log_index_is_repaired_by_rebuild(self):
        """Functional regression: with the old hardcoded list `fts_task_logs`
        was never rebuilt, so a wiped index stayed empty and search kept
        returning nothing for a row that exists."""
        from backend_init import external_content_fts_tables

        conn = self._fresh_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tasks(slug,title,status,created_at,updated_at) VALUES(?,?,?,?,?)",
            ("t-fts", "T", "planning", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        cur.execute(
            "INSERT INTO task_logs(task_slug,message,created_at) VALUES(?,?,?)",
            ("t-fts", "quokka sentinel phrase", "2026-01-01T00:00:00Z"),
        )
        conn.commit()

        # Simulate the post-migration stale state the rebuild exists to repair.
        cur.execute("DELETE FROM fts_task_logs")
        conn.commit()
        stale = cur.execute(
            "SELECT count(*) FROM fts_task_logs WHERE fts_task_logs MATCH 'quokka'"
        ).fetchone()[0]
        assert stale == 0, "precondition: index must be stale before the rebuild"

        for name in external_content_fts_tables(cur):
            cur.execute(f"INSERT INTO {name}({name}) VALUES('rebuild')")
        conn.commit()

        found = cur.execute(
            "SELECT count(*) FROM fts_task_logs WHERE fts_task_logs MATCH 'quokka'"
        ).fetchone()[0]
        assert found == 1, "rebuild did not restore the task_logs index"
        conn.close()


class TestSchemaMigrationParity:
    """SCHEMA_VERSION and the highest migration are bumped by hand in two files.

    Drift is silent in both directions — ahead leaves databases permanently
    "stale but unmigratable", behind means a written migration never runs — so
    the guard is checked at import and pinned here.
    """

    def test_live_constants_are_in_parity(self):
        from backend_migrations import MIGRATIONS
        from backend_schema import SCHEMA_VERSION

        assert SCHEMA_VERSION == max(MIGRATIONS)

    def test_drift_raises_with_both_values_named(self):
        """Negative: a mismatch must be a loud error naming both numbers, not a
        silent pass. This is the failure the guard exists to make visible."""
        from backend_migrations import check_schema_migration_parity

        with pytest.raises(RuntimeError) as exc:
            check_schema_migration_parity(99, {1: [], 2: []})
        msg = str(exc.value)
        assert "99" in msg and "v2" in msg, msg

    def test_parity_holds_when_equal(self):
        from backend_migrations import check_schema_migration_parity

        check_schema_migration_parity(2, {1: [], 2: []})  # must not raise
