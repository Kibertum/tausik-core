"""Tests for FTS5 synchronization with content tables.

Verifies that INSERT/UPDATE/DELETE triggers keep FTS5 indexes
in sync with their source tables (tasks, memory, decisions).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend


@pytest.fixture
def db(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    yield be
    be.close()


def _fts_count(db, table, query):
    """Count FTS matches for a query."""
    rows = db._q(
        f"SELECT rowid FROM {table} WHERE {table} MATCH ?", (query,)
    )
    return len(rows)


# === Tasks FTS sync ===

class TestTasksFTS:
    def _setup(self, db):
        db.epic_add("e1", "E1")
        db.story_add("e1", "s1", "S1")

    def test_insert_indexes_task(self, db):
        self._setup(db)
        db.task_add("s1", "auth-fix", "Fix authentication", goal="Repair JWT tokens")
        assert _fts_count(db, "fts_tasks", "authentication") >= 1
        assert _fts_count(db, "fts_tasks", "JWT") >= 1

    def test_update_reindexes_task(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "Original title", goal="Original goal")
        assert _fts_count(db, "fts_tasks", "Original") >= 1
        db.task_update("t1", title="Rewritten heading", goal="Rewritten objective")
        # Old content should not match
        assert _fts_count(db, "fts_tasks", "Original") == 0
        # New content should match
        assert _fts_count(db, "fts_tasks", "Rewritten") >= 1

    def test_delete_removes_from_fts(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "Searchable task")
        assert _fts_count(db, "fts_tasks", "Searchable") >= 1
        db.task_delete("t1")
        assert _fts_count(db, "fts_tasks", "Searchable") == 0

    def test_multiple_tasks_independent(self, db):
        self._setup(db)
        db.task_add("s1", "t1", "Alpha task")
        db.task_add("s1", "t2", "Beta task")
        db.task_delete("t1")
        assert _fts_count(db, "fts_tasks", "Alpha") == 0
        assert _fts_count(db, "fts_tasks", "Beta") >= 1


# === Memory FTS sync ===

class TestMemoryFTS:
    def test_insert_indexes_memory(self, db):
        db.memory_add("pattern", "Connection pooling", "Always pool database connections", ["python"])
        assert _fts_count(db, "fts_memory", "pooling") >= 1
        assert _fts_count(db, "fts_memory", "python") >= 1

    def test_delete_removes_from_fts(self, db):
        mid = db.memory_add("pattern", "Temporary note", "Will be removed")
        assert _fts_count(db, "fts_memory", "Temporary") >= 1
        db.memory_delete(mid)
        assert _fts_count(db, "fts_memory", "Temporary") == 0

    def test_search_matches_content(self, db):
        db.memory_add("gotcha", "Timezone trap", "Always convert to UTC before storage")
        results = db.memory_search("UTC")
        assert len(results) >= 1
        assert results[0]["title"] == "Timezone trap"


# === Decisions FTS sync ===

class TestDecisionsFTS:
    def test_insert_indexes_decision(self, db):
        db.decision_add("Use PostgreSQL for persistence", rationale="ACID compliance needed")
        assert _fts_count(db, "fts_decisions", "PostgreSQL") >= 1
        assert _fts_count(db, "fts_decisions", "ACID") >= 1

    def test_search_finds_decision(self, db):
        db.decision_add("Adopt microservices architecture", rationale="Scalability requirements")
        results = db.search_all("microservices", "decisions")
        assert len(results.get("decisions", [])) >= 1


# === Cross-table FTS isolation ===

class TestFTSIsolation:
    def test_task_fts_does_not_leak_to_memory(self, db):
        db.epic_add("e1", "E1")
        db.story_add("e1", "s1", "S1")
        db.task_add("s1", "t1", "Xylophone task")
        # Task content should NOT appear in memory FTS
        assert _fts_count(db, "fts_memory", "Xylophone") == 0

    def test_memory_fts_does_not_leak_to_tasks(self, db):
        db.memory_add("pattern", "Zeppelin pattern", "Airship approach")
        assert _fts_count(db, "fts_tasks", "Zeppelin") == 0

    def test_all_fts_tables_searchable(self, db):
        """Verify search_all queries all 3 FTS tables without errors."""
        db.epic_add("e1", "E1")
        db.story_add("e1", "s1", "S1")
        db.task_add("s1", "t1", "Quantum task")
        db.memory_add("pattern", "Quantum memory", "Content")
        db.decision_add("Quantum decision")
        results = db.search_all("Quantum", "all")
        total = sum(len(v) for v in results.values())
        assert total >= 3
