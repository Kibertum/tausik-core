"""Tests for TAUSIK SQLiteBackend — all DB operations."""

import json
import os
import sys
import tempfile

import pytest

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend


@pytest.fixture
def db(tmp_path):
    """Fresh SQLite backend for each test."""
    be = SQLiteBackend(str(tmp_path / "test.db"))
    yield be
    be.close()


# === Schema ===


class TestSchema:
    def test_creates_db_file(self, tmp_path):
        path = str(tmp_path / "new.db")
        be = SQLiteBackend(path)
        assert os.path.exists(path)
        be.close()

    def test_schema_version_set(self, db):
        row = db._q1("SELECT value FROM meta WHERE key='schema_version'")
        assert row is not None
        assert int(row["value"]) >= 1

    def test_wal_mode(self, db):
        row = db._q1("PRAGMA journal_mode")
        assert row["journal_mode"] == "wal"

    def test_foreign_keys_on(self, db):
        row = db._q1("PRAGMA foreign_keys")
        assert row["foreign_keys"] == 1

    def test_idempotent_schema(self, tmp_path):
        path = str(tmp_path / "idem.db")
        be1 = SQLiteBackend(path)
        be1.close()
        be2 = SQLiteBackend(path)  # second init should not fail
        row = be2._q1("SELECT value FROM meta WHERE key='schema_version'")
        assert int(row["value"]) >= 1
        be2.close()

    def test_schema_version_6(self, db):
        row = db._q1("SELECT value FROM meta WHERE key='schema_version'")
        assert int(row["value"]) >= 6


class TestCheckConstraints:
    """CHECK constraints enforce valid values at DB level."""

    def test_epic_invalid_status_rejected(self, db):
        import sqlite3

        with pytest.raises(sqlite3.IntegrityError):
            db._ins(
                "INSERT INTO epics(slug,title,status,created_at) VALUES(?,?,?,?)",
                ("bad", "Bad", "invalid", "2025-01-01T00:00:00Z"),
            )

    def test_story_invalid_status_rejected(self, db):
        import sqlite3

        db.epic_add("e1", "Epic")
        epic = db.epic_get("e1")
        with pytest.raises(sqlite3.IntegrityError):
            db._ins(
                "INSERT INTO stories(epic_id,slug,title,status,created_at) VALUES(?,?,?,?,?)",
                (epic["id"], "bad", "Bad", "invalid", "2025-01-01T00:00:00Z"),
            )

    def test_task_invalid_status_rejected(self, db):
        import sqlite3

        db.epic_add("e1", "Epic")
        db.story_add("e1", "s1", "Story")
        story = db.story_get("s1")
        with pytest.raises(sqlite3.IntegrityError):
            db._ins(
                "INSERT INTO tasks(story_id,slug,title,status,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?)",
                (
                    story["id"],
                    "bad",
                    "Bad",
                    "invalid",
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T00:00:00Z",
                ),
            )

    def test_task_invalid_complexity_rejected(self, db):
        import sqlite3

        db.epic_add("e1", "Epic")
        db.story_add("e1", "s1", "Story")
        story = db.story_get("s1")
        with pytest.raises(sqlite3.IntegrityError):
            db._ins(
                "INSERT INTO tasks(story_id,slug,title,status,complexity,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    story["id"],
                    "bad",
                    "Bad",
                    "planning",
                    "ultra-hard",
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T00:00:00Z",
                ),
            )

    def test_task_free_text_role_accepted(self, db):
        """Roles are now free-text — any string should be accepted."""
        db.epic_add("e1", "Epic")
        db.story_add("e1", "s1", "Story")
        story = db.story_get("s1")
        # Should NOT raise — any role string is valid
        db._ins(
            "INSERT INTO tasks(story_id,slug,title,status,role,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                story["id"],
                "custom-role",
                "Custom",
                "planning",
                "hacker",
                "2025-01-01T00:00:00Z",
                "2025-01-01T00:00:00Z",
            ),
        )
        row = db._q1("SELECT role FROM tasks WHERE slug='custom-role'")
        assert row["role"] == "hacker"

    def test_task_null_complexity_role_accepted(self, db):
        """NULL values for optional fields should pass CHECK."""
        db.epic_add("e1", "Epic")
        db.story_add("e1", "s1", "Story")
        slug = db.task_add("s1", "ok", "OK task")
        task = db.task_get(slug)
        assert task["complexity"] is None
        assert task["role"] is None

    def test_memory_invalid_type_rejected(self, db):
        import sqlite3

        with pytest.raises(sqlite3.IntegrityError):
            db._ins(
                "INSERT INTO memory(type,title,content,created_at,updated_at) VALUES(?,?,?,?,?)",
                (
                    "invalid",
                    "Title",
                    "Content",
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T00:00:00Z",
                ),
            )

    def test_slug_length_limit(self, db):
        import sqlite3

        long_slug = "a" * 65
        with pytest.raises(sqlite3.IntegrityError):
            db._ins(
                "INSERT INTO epics(slug,title,status,created_at) VALUES(?,?,?,?)",
                (long_slug, "Long slug", "active", "2025-01-01T00:00:00Z"),
            )


# === Epics ===


class TestEpics:
    def test_add_and_get(self, db):
        db.epic_add("v1", "Version 1", "First version")
        epic = db.epic_get("v1")
        assert epic["slug"] == "v1"
        assert epic["title"] == "Version 1"
        assert epic["status"] == "active"
        assert epic["description"] == "First version"

    def test_list(self, db):
        db.epic_add("a", "Alpha")
        db.epic_add("b", "Beta")
        epics = db.epic_list()
        assert len(epics) == 2
        assert epics[0]["slug"] == "a"

    def test_update(self, db):
        db.epic_add("v1", "V1")
        db.epic_update("v1", status="done")
        assert db.epic_get("v1")["status"] == "done"

    def test_delete(self, db):
        db.epic_add("v1", "V1")
        db.epic_delete("v1")
        assert db.epic_get("v1") is None

    def test_get_nonexistent(self, db):
        assert db.epic_get("nope") is None

    def test_unique_slug(self, db):
        db.epic_add("v1", "V1")
        with pytest.raises(Exception):  # IntegrityError
            db.epic_add("v1", "Duplicate")


# === Stories ===


class TestStories:
    def test_add_and_get(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "setup", "Initial Setup")
        story = db.story_get("setup")
        assert story["slug"] == "setup"
        assert story["title"] == "Initial Setup"
        assert story["status"] == "open"
        assert story["epic_slug"] == "v1"

    def test_add_to_nonexistent_epic(self, db):
        with pytest.raises(ValueError, match="not found"):
            db.story_add("nope", "s1", "Story")

    def test_list_by_epic(self, db):
        db.epic_add("v1", "V1")
        db.epic_add("v2", "V2")
        db.story_add("v1", "s1", "Story 1")
        db.story_add("v2", "s2", "Story 2")
        stories = db.story_list("v1")
        assert len(stories) == 1
        assert stories[0]["slug"] == "s1"

    def test_list_all(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "s1", "S1")
        db.story_add("v1", "s2", "S2")
        assert len(db.story_list()) == 2

    def test_update(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "s1", "S1")
        db.story_update("s1", status="active")
        assert db.story_get("s1")["status"] == "active"

    def test_delete(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "s1", "S1")
        db.story_delete("s1")
        assert db.story_get("s1") is None

    def test_active_task_count(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "s1", "S1")
        db.task_add("s1", "t1", "Task 1")
        db.task_add("s1", "t2", "Task 2")
        assert db.story_active_task_count("s1") == 2
        db.task_update("t1", status="done")
        assert db.story_active_task_count("s1") == 1
        db.task_update("t2", status="done")
        assert db.story_active_task_count("s1") == 0


# === Tasks ===


class TestTasks:
    def _setup(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "s1", "S1")

    def test_add_and_get(self, db):
        self._setup(db)
        slug = db.task_add(
            "s1",
            "t1",
            "Task 1",
            stack="python",
            complexity="simple",
            score=1,
            goal="Do it",
        )
        assert slug == "t1"
        task = db.task_get("t1")
        assert task["slug"] == "t1"
        assert task["title"] == "Task 1"
        assert task["status"] == "planning"
        assert task["stack"] == "python"
        assert task["attempts"] == 0

    def test_add_to_nonexistent_story(self, db):
        with pytest.raises(ValueError, match="not found"):
            db.task_add("nope", "t1", "Task")

    def test_get_full(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "Task 1")
        full = db.task_get_full("t1")
        assert full["story_slug"] == "s1"
        assert full["epic_slug"] == "v1"

    def test_list_filter_status(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "T1")
        db.task_add("s1", "t2", "T2")
        db.task_update("t1", status="active")
        active = db.task_list(status="active")
        assert len(active) == 1
        assert active[0]["slug"] == "t1"

    def test_list_filter_story(self, db):
        self._setup(db)
        db.story_add("v1", "s2", "S2")
        db.task_add("s1", "t1", "T1")
        db.task_add("s2", "t2", "T2")
        tasks = db.task_list(story="s1")
        assert len(tasks) == 1

    def test_list_filter_role(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "T1", role="developer")
        db.task_add("s1", "t2", "T2", role="qa")
        devs = db.task_list(role="developer")
        assert len(devs) == 1
        assert devs[0]["slug"] == "t1"

    def test_list_multi_status(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "T1")
        db.task_add("s1", "t2", "T2")
        db.task_update("t1", status="active")
        db.task_update("t2", status="blocked")
        result = db.task_list(status="active,blocked")
        assert len(result) == 2

    def test_update(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "T1")
        db.task_update("t1", status="active", goal="New goal")
        task = db.task_get("t1")
        assert task["status"] == "active"
        assert task["goal"] == "New goal"

    def test_delete(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "T1")
        db.task_delete("t1")
        assert db.task_get("t1") is None

    def test_unique_slug(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "T1")
        with pytest.raises(Exception):
            db.task_add("s1", "t1", "Duplicate")


# === Task Logs ===


class TestTaskLogs:
    def _create_task(self, db):
        db.epic_add("ep", "Epic")
        db.story_add("ep", "st", "Story")
        db.task_add("st", "tl", "Task for logs")
        return "tl"

    def test_add_and_list(self, db):
        slug = self._create_task(db)
        log_id = db.task_log_add(slug, "Started work", phase="implementation")
        assert log_id > 0
        logs = db.task_log_list(slug)
        assert len(logs) == 1
        assert logs[0]["message"] == "Started work"
        assert logs[0]["phase"] == "implementation"
        assert logs[0]["task_slug"] == slug

    def test_list_empty(self, db):
        logs = db.task_log_list("nonexistent")
        assert logs == []

    def test_filter_by_phase(self, db):
        slug = self._create_task(db)
        db.task_log_add(slug, "Planning done", phase="planning")
        db.task_log_add(slug, "Coding started", phase="implementation")
        db.task_log_add(slug, "Review passed", phase="review")
        assert len(db.task_log_list(slug, phase="implementation")) == 1
        assert len(db.task_log_list(slug, phase="review")) == 1
        assert len(db.task_log_list(slug)) == 3

    def test_multiple_logs(self, db):
        slug = self._create_task(db)
        db.task_log_add(slug, "Step 1")
        db.task_log_add(slug, "Step 2")
        db.task_log_add(slug, "Step 3")
        logs = db.task_log_list(slug)
        assert len(logs) == 3
        assert [l["message"] for l in logs] == ["Step 1", "Step 2", "Step 3"]

    def test_with_diff_stats(self, db):
        slug = self._create_task(db)
        db.task_log_add(slug, "Committed", diff_stats="3 files, +42 -10")
        logs = db.task_log_list(slug)
        assert logs[0]["diff_stats"] == "3 files, +42 -10"

    def test_cascade_delete(self, db):
        slug = self._create_task(db)
        db.task_log_add(slug, "Log entry")
        assert len(db.task_log_list(slug)) == 1
        db.task_delete(slug)
        assert len(db.task_log_list(slug)) == 0


# === Sessions ===


class TestSessions:
    def test_start_and_current(self, db):
        sid = db.session_start()
        assert sid > 0
        current = db.session_current()
        assert current["id"] == sid
        assert current["ended_at"] is None

    def test_end(self, db):
        sid = db.session_start()
        db.session_end(sid, "Done")
        assert db.session_current() is None
        sessions = db.session_list()
        assert sessions[0]["summary"] == "Done"

    def test_list_limit(self, db):
        for _ in range(5):
            sid = db.session_start()
            db.session_end(sid)
        assert len(db.session_list(3)) == 3

    def test_handoff(self, db):
        sid = db.session_start()
        handoff = {"completed": ["t1"], "next_steps": ["t2"]}
        db.session_update_handoff(sid, handoff)
        row = db.session_last_handoff()
        assert json.loads(row["handoff"]) == handoff


# === Decisions ===


class TestDecisions:
    def _make_task(self, db, slug="t1"):
        """Create a minimal epic→story→task for FK references."""
        db.epic_add("e1", "E1")
        db.story_add("e1", "s1", "S1")
        db.task_add("s1", slug, f"Task {slug}")

    def test_add_and_list(self, db):
        self._make_task(db, "t1")
        did = db.decision_add("Use SQLite", "t1", "Simple is better")
        assert did > 0
        decisions = db.decision_list()
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "Use SQLite"
        assert decisions[0]["rationale"] == "Simple is better"

    def test_for_task(self, db):
        self._make_task(db, "t1")
        db.task_add("s1", "t2", "Task t2")
        db.decision_add("D1", "t1")
        db.decision_add("D2", "t2")
        db.decision_add("D3", "t1")
        for_t1 = db.decisions_for_task("t1")
        assert len(for_t1) == 2

    def test_add_without_task(self, db):
        did = db.decision_add("General decision", None, "No task")
        assert did > 0
        decisions = db.decision_list()
        assert decisions[0]["task_slug"] is None

    def test_list_limit(self, db):
        for i in range(10):
            db.decision_add(f"D{i}")
        assert len(db.decision_list(5)) == 5


# === Memory ===


class TestMemory:
    def test_add_and_get(self, db):
        mid = db.memory_add(
            "pattern", "Singleton", "Use singleton for DB", ["python", "db"]
        )
        assert mid > 0
        mem = db.memory_get(mid)
        assert mem["type"] == "pattern"
        assert mem["title"] == "Singleton"
        assert json.loads(mem["tags"]) == ["python", "db"]

    def test_list_by_type(self, db):
        db.memory_add("pattern", "P1", "Content")
        db.memory_add("gotcha", "G1", "Content")
        patterns = db.memory_list("pattern")
        assert len(patterns) == 1
        all_mem = db.memory_list()
        assert len(all_mem) == 2

    def test_search_fts(self, db):
        db.memory_add(
            "pattern",
            "Database connection pooling",
            "Always use connection pools for PostgreSQL",
        )
        db.memory_add("gotcha", "Timezone handling", "Always use UTC timestamps")
        results = db.memory_search("database connection")
        assert len(results) >= 1
        assert results[0]["title"] == "Database connection pooling"

    def test_delete(self, db):
        mid = db.memory_add("pattern", "P1", "Content")
        db.memory_delete(mid)
        assert db.memory_get(mid) is None


# === Search ===


class TestSearch:
    def test_search_tasks(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "s1", "S1")
        db.task_add(
            "s1", "fix-auth", "Fix authentication bug", goal="Fix JWT validation"
        )
        results = db.search_all("authentication", "tasks")
        assert "tasks" in results
        assert len(results["tasks"]) >= 1

    def test_search_memory(self, db):
        db.memory_add("pattern", "Caching strategy", "Use Redis for session cache")
        results = db.search_all("caching", "memory")
        assert len(results["memory"]) >= 1

    def test_search_all_scopes(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "s1", "S1")
        db.task_add("s1", "t1", "Database migration")
        db.memory_add("pattern", "Database patterns", "Use migrations")
        db.decision_add("Use PostgreSQL for database", rationale="ACID compliance")
        results = db.search_all("database", "all")
        assert "tasks" in results
        assert "memory" in results
        assert "decisions" in results

    def test_fts_optimize(self, db):
        db.memory_add("pattern", "Test", "Content for optimize")
        results = db.fts_optimize()
        assert all(v == "ok" for v in results.values())
        assert len(results) == 3

    def test_search_with_limit(self, db):
        for i in range(10):
            db.memory_add("pattern", f"Item {i}", f"Searchable content {i}")
        results = db.search_all("searchable", "memory", n=3)
        assert len(results["memory"]) == 3

    def test_search_returns_snippet(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "s1", "S1")
        db.task_add(
            "s1", "fix-auth", "Fix authentication bug", goal="Fix JWT validation"
        )
        db.memory_add("pattern", "Caching strategy", "Use Redis for session cache")
        db.decision_add("Use PostgreSQL for database", rationale="ACID compliance")
        # tasks snippet
        tasks_results = db.search_all("authentication", "tasks")
        assert tasks_results["tasks"][0].get("_snippet") is not None
        assert (
            "authentication" in tasks_results["tasks"][0]["_snippet"].lower()
            or ">>>" in tasks_results["tasks"][0]["_snippet"]
        )
        # memory snippet
        mem_results = db.memory_search("Redis")
        assert mem_results[0].get("_snippet") is not None
        # decisions snippet
        dec_results = db.search_all("PostgreSQL", "decisions")
        assert dec_results["decisions"][0].get("_snippet") is not None


# === Status / Roadmap ===


class TestStatusRoadmap:
    def test_status_data(self, db):
        db.epic_add("v1", "V1")
        db.story_add("v1", "s1", "S1")
        db.task_add("s1", "t1", "T1")
        db.task_add("s1", "t2", "T2")
        db.task_update("t1", status="active")
        status = db.get_status_data()
        assert status["task_counts"]["planning"] == 1
        assert status["task_counts"]["active"] == 1
        assert len(status["epics"]) == 1

    def test_roadmap_excludes_done(self, db):
        db.epic_add("v1", "V1")
        db.epic_add("v2", "V2")
        db.epic_update("v1", status="done")
        roadmap = db.get_roadmap_data(include_done=False)
        assert len(roadmap) == 1
        assert roadmap[0]["slug"] == "v2"

    def test_roadmap_includes_done(self, db):
        db.epic_add("v1", "V1")
        db.epic_update("v1", status="done")
        roadmap = db.get_roadmap_data(include_done=True)
        assert len(roadmap) == 1
