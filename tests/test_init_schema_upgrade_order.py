"""`init_schema` on an EXISTING database, one version behind.

REGRESSION. v2-verify-receipt-as-argument added `idx_verify_handle` to
`INDEXES_SQL` — the obvious home for an index. It crashed every upgrading
installation with `sqlite3.OperationalError: no such column: handle_nonce`, and
the whole test suite stayed green while it did.

The reason is an ordering that only exists on the upgrade path.
`backend_init.init_schema` runs, in this order:

    SCHEMA_SQL -> FTS -> INDEXES_SQL -> ... -> run_migrations()

On a FRESH database SCHEMA_SQL creates every column, so INDEXES_SQL can name
any of them. On an EXISTING database SCHEMA_SQL is a no-op (`CREATE TABLE IF NOT
EXISTS`), the new columns do not arrive until `run_migrations` — which happens
LAST. So an index in INDEXES_SQL naming a migration-added column is fine on
every fresh DB and fatal on every real one.

`backend_schema_indexes` states this rule in its docstring, and it was still
broken, because nothing executed the path the rule protects. This file does:
it stands up a database at the PREVIOUS schema version and calls the real
`init_schema` on it. It has no assertions about the handle feature in
particular — it asserts that the upgrade path runs at all, which is the
property that was missing.
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
from backend_init import init_schema  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from test_migrations import V1_SCHEMA  # noqa: E402


def _db_at_previous_version(path: str) -> None:
    """A real on-disk database stopped one migration short of HEAD.

    Built by running the actual migrations rather than by pasting a snapshot:
    a hand-written "previous schema" is a copy that drifts, which is the same
    class of defect as the hand-rolled verification_runs DDL that once produced
    twenty green tests for a feature failing on every live write.
    """
    conn = sqlite3.connect(path)
    conn.isolation_level = None
    conn.executescript(V1_SCHEMA)
    head = max(bm.MIGRATIONS)
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


@pytest.fixture
def legacy_db(tmp_path):
    path = str(tmp_path / "tausik.db")
    _db_at_previous_version(path)
    return path


class TestUpgradePathRuns:
    def test_init_schema_survives_a_database_one_version_behind(self, legacy_db):
        """The assertion is that this does not raise. `no such column: X` here
        means an index or a DDL statement in the pre-migration block names a
        column that only a migration adds — move it into that migration."""
        conn = sqlite3.connect(legacy_db)
        try:
            init_schema(conn)
        finally:
            conn.close()

    def test_the_upgrade_reaches_head(self, legacy_db):
        conn = sqlite3.connect(legacy_db)
        try:
            init_schema(conn)
            row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            assert int(row[0]) == SCHEMA_VERSION
        finally:
            conn.close()

    def test_head_migration_columns_exist_after_upgrade(self, legacy_db):
        """Guards the premise: the fixture really did stop short of HEAD, so the
        test above exercised a REAL upgrade rather than a no-op."""
        conn = sqlite3.connect(legacy_db)
        try:
            before = {r[1] for r in conn.execute("PRAGMA table_info(verification_runs)")}
            init_schema(conn)
            after = {r[1] for r in conn.execute("PRAGMA table_info(verification_runs)")}
            assert after > before, "the fixture was already at HEAD — nothing was upgraded"
        finally:
            conn.close()
