"""A fresh database and a migrated one must carry the SAME indexes.

REGRESSION. `test_schema_upgrade_parity.py` compares the two paths' COLUMNS and
has caught real drift there. It says nothing about indexes, and they had
drifted: seven `CREATE INDEX` statements lived only inside migrations, so a
database carried up from v1 had them and a freshly initialised one did not.

The cause is an ordering nobody has to get wrong twice:

  * `INDEXES_SQL` runs BEFORE migrations, so it may only name v1-baseline
    columns — an index on a migration-added column crashes `init_schema` on
    every EXISTING database (`no such column: ...`).
  * putting such an index only in its migration then means a FRESH database
    never creates it, because `init_schema` stamps the current schema version
    and `run_migrations` applies nothing.

Both halves are true at once, so the index has to be stated a third time, after
migrations, on both paths — `POST_MIGRATION_INDEXES_SQL`. That is duplication,
and duplication is only safe when a gate pins it. This file is the gate.
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

from backend_init import init_schema  # noqa: E402
from backend_schema_indexes import POST_MIGRATION_INDEXES_SQL  # noqa: E402
from test_migrations import V1_SCHEMA  # noqa: E402


def _indexes(conn: sqlite3.Connection) -> set[str]:
    """Explicit indexes only — `sqlite_autoindex_*` are UNIQUE side effects."""
    return {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
    }


@pytest.fixture
def fresh(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "fresh.db"))
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def migrated(tmp_path):
    """A v1 database carried up by the real migrations, then handed to
    `init_schema` the way a live upgrade reaches it.

    The migrations run against the BARE v1 tables first, before init_schema
    installs the FTS triggers. That ordering is not a convenience: the audit
    trigger `tasks_audit_status` references `new.claimed_by`, a column a later
    migration adds, so installing the triggers on a v1 `tasks` and then
    migrating makes the first UPDATE inside a migration fail with "no such
    column: new.claimed_by". Real upgrades never hit it because a database that
    HAS those triggers also has the columns they name — it was init'd at its own
    version. The fixture reproduces the state, not the keystrokes.
    """
    import backend_migrations as bm

    path = str(tmp_path / "migrated.db")
    conn = sqlite3.connect(path)
    conn.isolation_level = None
    conn.executescript(V1_SCHEMA)
    head = max(bm.MIGRATIONS)
    # Stop ONE version short and record that, so the `init_schema` call below
    # takes the real upgrade branch. Stamping the head version instead would
    # trip init_schema's "already current, skip DDL" early return, and the test
    # would be comparing a fresh database against one that never ran the code
    # under test — green or red for the wrong reason.
    removed = {v: bm.MIGRATIONS.pop(v) for v in sorted(bm.MIGRATIONS) if v >= head}
    try:
        reached = bm.run_migrations(conn, 1)
    finally:
        bm.MIGRATIONS.update(removed)
    assert reached == head - 1
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)", (str(reached),)
    )
    conn.commit()
    conn.close()
    conn = sqlite3.connect(path)
    init_schema(conn)
    yield conn
    conn.close()


def _declared_post_migration_indexes() -> set[str]:
    return {
        line.split(" ON ")[0].split()[-1]
        for line in POST_MIGRATION_INDEXES_SQL.splitlines()
        if "CREATE INDEX" in line
    }


class TestPostMigrationIndexesReachBothPaths:
    """SCOPED DELIBERATELY to the indexes this block is responsible for.

    A full two-way index comparison between the two paths is RED today for
    reasons that predate this change — a fresh database and a migrated one
    disagree about roughly a dozen indexes on brain_events, reviews, sessions,
    stories, memory and decisions, in both directions. That is a real defect and
    it has its own task (`schema-index-drift-fresh-vs-migrated`); asserting it
    here would either fail for someone else's reason or tempt the next reader to
    weaken this file until it passed. What IS asserted is the property
    POST_MIGRATION_INDEXES_SQL exists to provide, and nothing broader.
    """

    def test_the_block_is_not_empty(self):
        """Guards the premise. Every assertion below is vacuously true against
        an empty set, so a parser that silently matched nothing would make this
        whole file green while proving nothing."""
        assert len(_declared_post_migration_indexes()) >= 7

    def test_present_on_a_fresh_install(self, fresh):
        """The direction that was actually broken: a fresh install stamps the
        current version, so `run_migrations` applies nothing and the indexes
        declared inside migrations never got created."""
        missing = _declared_post_migration_indexes() - _indexes(fresh)
        assert not missing, f"a fresh DB is missing: {sorted(missing)}"

    def test_present_after_a_real_upgrade(self, migrated):
        missing = _declared_post_migration_indexes() - _indexes(migrated)
        assert not missing, f"an upgraded DB is missing: {sorted(missing)}"

    def test_the_handle_index_specifically(self, fresh, migrated):
        """v44's index is what exposed all of this; name it so a future reader
        knows which change the general rule came from."""
        assert "idx_verify_handle" in _indexes(fresh)
        assert "idx_verify_handle" in _indexes(migrated)

    def test_it_restores_an_index_the_v43_rebuild_drops(self, migrated):
        """Found while writing this file. v43 rebuilds `tasks` and recreates its
        indexes from a frozen list that predates v41's
        idx_tasks_no_file_changes_declared — so the rebuild silently dropped it
        and no database has carried it since. The post-migration block puts it
        back on both paths, which is the point of stating the CURRENT set in one
        place rather than trusting each migration's snapshot."""
        assert "idx_tasks_no_file_changes_declared" in _indexes(migrated)
