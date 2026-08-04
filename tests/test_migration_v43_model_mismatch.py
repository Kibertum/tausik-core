"""v43 migration: tasks.model_mismatch becomes NOT NULL DEFAULT 0 on the upgrade path.

schema-model-mismatch-nullable-on-upgrade. The fresh CREATE TABLE declares
`model_mismatch INTEGER NOT NULL DEFAULT 0`, but the migration that added it
(v33) used `ADD COLUMN ... DEFAULT 0` WITHOUT NOT NULL (SQLite forbids NOT NULL
on ADD COLUMN). So a DB carried from v1 by migrations allows NULL in that column,
and any `WHERE model_mismatch = 0` silently drops a NULL row — green on CI (fresh
schema), wrong in the field (migrated schema). v43 rebuilds `tasks` so both paths
converge on NOT NULL DEFAULT 0.

These tests are the NEGATIVE scenario the task demands: a DB migrated to the
pre-v43 state, a real NULL injected, then v43 applied — proving the constraint is
tightened AND that the central-table rebuild loses nothing (rows, the defect_of
self-FK chain, incoming FKs, and the external-content fts_tasks index).
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backend_migrations as bm  # noqa: E402
from backend_schema import (  # noqa: E402
    FTS_SQL,
    FTS_TRIGGERS_SQL,
    INDEXES_SQL,
)
from test_migrations import V1_SCHEMA  # noqa: E402

# The migration UNDER TEST, pinned as a literal. This file used to derive it
# from the schema version, on the assumption that v43 would stay the newest
# migration forever. v44 broke every derivation at once: the fixture popped v44
# instead of v43 and then asserted the DB had stopped at 43, and the "upgrade
# from the previous version" calls re-ran v44 rather than the v43 they mean to
# exercise. A test that names its subject by "latest" stops testing its subject
# the moment something else becomes latest.
_V43 = 43
_V42 = _V43 - 1

# The `tasks` indexes from the live INDEXES_SQL, and ONLY those. The fixture
# reproduces init_schema's pre-migration state at v42, so it must not apply an
# index that a LATER migration's columns make possible — v44's
# idx_verify_handle names verification_runs.handle_nonce, which does not exist
# at v42, so applying the whole script raised "no such column". Narrowing to
# `tasks` is not a workaround: every index assertion below is about tasks, and
# the other three (archived_at, started_model, model_mismatch) already arrive
# from the migrations themselves.
_TASKS_INDEXES_SQL = "\n".join(
    stmt.strip() + ";" for stmt in INDEXES_SQL.split(";") if " ON tasks(" in stmt
)


def _notnull(conn: sqlite3.Connection, table: str, column: str) -> int:
    for r in conn.execute(f"PRAGMA table_info({table})"):
        if r[1] == column:
            return r[3]  # notnull flag
    raise AssertionError(f"{table}.{column} not found")


def _migrate_to_42_then_inject(conn: sqlite3.Connection) -> None:
    """Bring a v1 DB up to v42 (v43 temporarily removed), then plant a NULL
    model_mismatch and a defect_of chain — the shape v43 must fix in the field."""
    conn.isolation_level = None  # run_migrations drives its own transactions
    conn.executescript(V1_SCHEMA)
    # Remove v43 AND everything after it: `run_migrations` walks sorted keys, so
    # popping only v43 would let v44+ apply against a table v43 had not yet
    # rebuilt, and the fixture would no longer be "the pre-v43 state".
    removed = {v: bm.MIGRATIONS.pop(v) for v in sorted(bm.MIGRATIONS) if v >= _V43}
    try:
        assert bm.run_migrations(conn, 1) == _V42
    finally:
        bm.MIGRATIONS.update(removed)
    # Reproduce the production INVARIANT at v42: init_schema applies FTS + its
    # triggers + the base indexes (backend_init.py:151-153) so that when a
    # migration runs, fts_tasks, the 7 tasks triggers and all 6 indexes exist.
    # The V1_SCHEMA-only `migrated` fixture in test_schema_upgrade_parity omits
    # these because it inspects column structure alone; this test fires triggers
    # and searches fts, so it must stand the DB up the way a real upgrade does.
    conn.executescript(FTS_SQL)
    conn.executescript(FTS_TRIGGERS_SQL)
    conn.executescript(_TASKS_INDEXES_SQL)
    now = "2026-01-01T00:00:00Z"
    # parent task, then a defect that self-references it via defect_of
    conn.execute(
        "INSERT INTO tasks (slug, title, status, model_mismatch, created_at, updated_at) "
        "VALUES ('parent', 'Parent', 'done', 1, ?, ?)",
        (now, now),
    )
    conn.execute(
        "INSERT INTO tasks (slug, title, status, model_mismatch, defect_of, created_at, updated_at) "
        "VALUES ('child', 'Child defect', 'done', NULL, 'parent', ?, ?)",  # the illegal NULL
        (now, now),
    )
    # an incoming FK from decisions -> tasks(slug), to prove it survives the rebuild
    conn.execute(
        "INSERT INTO decisions (decision, task_slug, created_at) VALUES ('d', 'parent', ?)",
        (now,),
    )


@pytest.fixture
def migrated_with_null() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    _migrate_to_42_then_inject(conn)
    yield conn
    conn.close()


class TestConstraintTightened:
    def test_column_is_nullable_before_v43(self, migrated_with_null):
        """Guard the premise: at v42 the column really is nullable (else the test
        proves nothing). This must hold BEFORE we apply v43."""
        assert _notnull(migrated_with_null, "tasks", "model_mismatch") == 0

    def test_model_mismatch_is_not_null_after_v43(self, migrated_with_null):
        # `>=`, not `==`: from v42 the runner applies every pending migration,
        # so the returned version is the HEAD, not v43. What this test asserts
        # is that v43 was among them — which the notnull flag below proves.
        assert bm.run_migrations(migrated_with_null, _V42) >= _V43
        assert _notnull(migrated_with_null, "tasks", "model_mismatch") == 1

    def test_null_value_is_backfilled_to_zero(self, migrated_with_null):
        bm.run_migrations(migrated_with_null, _V42)
        row = migrated_with_null.execute(
            "SELECT model_mismatch FROM tasks WHERE slug='child'"
        ).fetchone()
        assert row[0] == 0, "the illegal NULL must be backfilled to 0 before NOT NULL"

    def test_fresh_schema_column_order_is_matched(self, migrated_with_null):
        """The rebuild recreates tasks in the canonical (fresh) column order, so
        model_mismatch is no longer appended at the tail — the order drift is gone."""
        import sqlite3 as _sql

        from backend_schema import SCHEMA_SQL

        bm.run_migrations(migrated_with_null, _V42)
        fresh = _sql.connect(":memory:")
        fresh.executescript(SCHEMA_SQL)
        try:
            got = [r[1] for r in migrated_with_null.execute("PRAGMA table_info(tasks)")]
            want = [r[1] for r in fresh.execute("PRAGMA table_info(tasks)")]
            assert got == want
        finally:
            fresh.close()


class TestRebuildPreservesData:
    def test_row_count_and_rows_survive(self, migrated_with_null):
        before = migrated_with_null.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        bm.run_migrations(migrated_with_null, _V42)
        after = migrated_with_null.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        assert before == after == 2
        slugs = {r[0] for r in migrated_with_null.execute("SELECT slug FROM tasks")}
        assert slugs == {"parent", "child"}

    def test_defect_of_self_fk_chain_intact(self, migrated_with_null):
        bm.run_migrations(migrated_with_null, _V42)
        row = migrated_with_null.execute(
            "SELECT defect_of FROM tasks WHERE slug='child'"
        ).fetchone()
        assert row[0] == "parent", "the self-referential defect_of link must survive"

    def test_foreign_key_check_is_clean(self, migrated_with_null):
        bm.run_migrations(migrated_with_null, _V42)
        migrated_with_null.execute("PRAGMA foreign_keys=ON")
        violations = migrated_with_null.execute("PRAGMA foreign_key_check").fetchall()
        assert violations == [], f"rebuild broke referential integrity: {violations}"

    def test_incoming_fk_from_decisions_still_resolves(self, migrated_with_null):
        bm.run_migrations(migrated_with_null, _V42)
        row = migrated_with_null.execute(
            "SELECT task_slug FROM decisions WHERE decision='d'"
        ).fetchone()
        assert row[0] == "parent"


class TestFtsAndObjectsRecreated:
    def test_fts_tasks_finds_rebuilt_rows(self, migrated_with_null):
        bm.run_migrations(migrated_with_null, _V42)
        # external-content fts5 keyed by tasks.id; a search must return the row
        hit = migrated_with_null.execute(
            "SELECT t.slug FROM tasks t JOIN fts_tasks f ON t.id=f.rowid "
            "WHERE fts_tasks MATCH 'Child' "
        ).fetchall()
        assert ("child",) in hit, "fts_tasks was not rebuilt against the new tasks table"

    def test_all_six_indexes_recreated(self, migrated_with_null):
        bm.run_migrations(migrated_with_null, _V42)
        idx = {
            r[0]
            for r in migrated_with_null.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND tbl_name='tasks' AND name LIKE 'idx_tasks%'"
            )
        }
        assert idx == {
            "idx_tasks_story_id",
            "idx_tasks_status",
            "idx_tasks_slug",
            "idx_tasks_archived_at",
            "idx_tasks_started_model",
            "idx_tasks_model_mismatch",
        }

    def test_all_seven_triggers_recreated(self, migrated_with_null):
        bm.run_migrations(migrated_with_null, _V42)
        trg = {
            r[0]
            for r in migrated_with_null.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='tasks'"
            )
        }
        assert trg == {
            "tasks_ai",
            "tasks_ad",
            "tasks_au",
            "tasks_audit_insert",
            "tasks_audit_status",
            "tasks_audit_claim",
            "tasks_audit_delete",
        }

    def test_audit_trigger_fires_after_rebuild(self, migrated_with_null):
        """A recreated trigger must actually WORK, not merely exist: inserting a
        task after the rebuild writes a 'created' audit event."""
        bm.run_migrations(migrated_with_null, _V42)
        migrated_with_null.execute(
            "INSERT INTO tasks (slug, title, status, created_at, updated_at) "
            "VALUES ('post', 'Post', 'planning', '2026-01-02T00:00:00Z', '2026-01-02T00:00:00Z')"
        )
        n = migrated_with_null.execute(
            "SELECT COUNT(*) FROM events WHERE entity_type='task' AND entity_id='post' "
            "AND action='created'"
        ).fetchone()[0]
        assert n == 1
