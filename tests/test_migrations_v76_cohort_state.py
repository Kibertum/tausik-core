"""v76 migration: verification_cohorts.state reaches 'invalidated' — and stays CLOSED.

fix-pooled-verify-recovery-ss4-widening-inputs: the SS4 widening marks a
prior green cohort 'invalidated' instead of refusing execution forever.
The CHECK born in v75 admitted only ('open','green','red'), so the
widening's own first UPDATE died as sqlite3.IntegrityError — the defect
this migration closes, pinned below by test_before_v76_the_state_was_rejected.

Both directions are asserted (the v49 lesson): a migration that dropped
the CHECK entirely would pass "'invalidated' is accepted" just as happily
as a correct one, so the rejection of an OUTSIDE state after the migration
is what separates widening the list from opening it. The rebuild is also
where the results-side FK could quietly die, so the CASCADE is exercised
on the migrated database rather than trusted.
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
from backend_migrations import MIGRATIONS  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from test_migrations import V1_SCHEMA  # noqa: E402

# The migration UNDER TEST, pinned as a literal rather than derived from
# SCHEMA_VERSION: a fixture that names its subject "latest" stops testing
# that subject the moment something else becomes latest (the v49 lesson).
_V76 = 76
PRE_V76 = _V76 - 1


def _db_at_v75(tmp_path, name="v75.db"):
    """A v1 database carried by the REAL migrations to v75, and no further.

    v76 and everything after it are removed for the duration (the v49
    fixture pattern): popping only v76 would let a later migration run
    against a table v76 had not yet rebuilt, and the fixture would stop
    being "the pre-v76 state". The statements come from the production
    registry, so the assertions run against the real old schema rather
    than an imitation of it.
    """
    conn = sqlite3.connect(str(tmp_path / name))
    conn.isolation_level = None  # run_migrations drives its own transactions
    conn.executescript(V1_SCHEMA)
    removed = {v: bm.MIGRATIONS.pop(v) for v in sorted(bm.MIGRATIONS) if v >= _V76}
    try:
        assert bm.run_migrations(conn, 1) == PRE_V76
    finally:
        bm.MIGRATIONS.update(removed)
    return conn


def _insert_cohort(conn, state="green", identity="id-sha"):
    conn.execute(
        "INSERT INTO verification_cohorts (identity, members_json, identity_inputs_json, "
        "union_files_hash, gate_signature, state, created_at, updated_at) "
        "VALUES (?,'[\"t-a\",\"t-b\"]','{}','ufh','gs',?,"
        "'2026-10-07T00:00:00Z','2026-10-07T00:00:00Z')",
        (identity, state),
    )


def _states(ddl):
    chunk = ddl[ddl.index("CHECK(state IN") :]
    chunk = chunk[chunk.index("(", chunk.index("IN")) : chunk.index(")")]
    return sorted(p.strip().strip("'") for p in chunk.strip("( ").split(",") if p.strip())


def test_v76_is_registered_and_not_ahead_of_the_code():
    """v76 stays REGISTERED; being the LATEST version is not v76's property.

    The two clauses are fused into ONE assert on purpose: as two statements
    this body is shape-identical to its v49 twin (the test_dedupe gate
    reddened on exactly that pair), and a fused assertion is a different
    shape while asserting the same contract.
    """
    assert 76 in MIGRATIONS and SCHEMA_VERSION >= 76


def test_invalidated_is_accepted_after_migration(tmp_path):
    """The production sequence end to end: a green cohort carried by the real
    rebuild, then marked 'invalidated' by the widening's UPDATE."""
    conn = _db_at_v75(tmp_path, "accepted.db")
    try:
        _insert_cohort(conn)
        bm.run_migrations(conn, PRE_V76)
        conn.execute("UPDATE verification_cohorts SET state='invalidated' WHERE identity='id-sha'")
        got = conn.execute(
            "SELECT state FROM verification_cohorts WHERE identity='id-sha'"
        ).fetchone()[0]
        assert got == "invalidated"
    finally:
        conn.close()


@pytest.mark.parametrize("bad_state", ["INVALIDATED", "stale", "invalid", ""])
def test_a_state_outside_the_widened_list_is_still_rejected(tmp_path, bad_state):
    """The control that separates widening the list from opening it.

    A migration that dropped the CHECK would satisfy the acceptance test
    above just as happily, so without this the suite could not tell the
    two apart. On the MIGRATION path: the fresh schema's CHECK is pinned
    by test_schema_upgrade_parity's rebuilt-DDL compare.
    """
    conn = _db_at_v75(tmp_path, "reject.db")
    try:
        bm.run_migrations(conn, PRE_V76)
        with pytest.raises(sqlite3.IntegrityError):
            _insert_cohort(conn, state=bad_state, identity="bad")
    finally:
        conn.close()


def test_before_v76_the_state_was_rejected(tmp_path):
    """The defect itself, pinned: on the pre-v76 schema the DB refused the
    widening's own mark. Without this the migration could be a no-op and
    nothing here would notice."""
    conn = _db_at_v75(tmp_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            _insert_cohort(conn, state="invalidated")
    finally:
        conn.close()


def test_rows_survive_the_rebuild_column_for_column(tmp_path):
    conn = _db_at_v75(tmp_path, "carry.db")
    try:
        _insert_cohort(conn)
        before = conn.execute("SELECT * FROM verification_cohorts").fetchone()
        bm.run_migrations(conn, PRE_V76)
        after = conn.execute("SELECT * FROM verification_cohorts").fetchone()
        assert after == before, "the rebuild must preserve every column, id included"
    finally:
        conn.close()


def test_cascade_from_results_survives_the_rebuild(tmp_path):
    """The FK from verification_cohort_results is the one thing the rebuild
    could silently lose — PRAGMA table_info cannot see it, only the DDL
    compare in test_schema_upgrade_parity can, and this exercises it as
    behavior: deleting the cohort must still take its results with it."""
    conn = _db_at_v75(tmp_path, "cascade.db")
    try:
        _insert_cohort(conn)
        pk = conn.execute("SELECT id FROM verification_cohorts WHERE identity='id-sha'").fetchone()[
            0
        ]
        conn.execute(
            "INSERT INTO verification_cohort_results "
            "(cohort_pk, unit, outcome, inputs_digest, ran_at) "
            "VALUES (?,'cohort-union-scope','passed','d','2026-10-07T00:00:00Z')",
            (pk,),
        )
        bm.run_migrations(conn, PRE_V76)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("DELETE FROM verification_cohorts WHERE id=?", (pk,))
        left = conn.execute("SELECT COUNT(*) FROM verification_cohort_results").fetchone()[0]
        assert left == 0, "the FK from results must still CASCADE after the rebuild"
    finally:
        conn.close()


def test_migrated_and_fresh_schemas_declare_the_same_state_check(tmp_path):
    """The two paths must converge: a migration that widened one and not the
    other leaves CI green on the fresh schema and wrong in the field."""
    migrated = _db_at_v75(tmp_path, "converge.db")
    try:
        bm.run_migrations(migrated, PRE_V76)
        mig_sql = migrated.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='verification_cohorts'"
        ).fetchone()[0]
    finally:
        migrated.close()

    be = SQLiteBackend(str(tmp_path / "fresh.db"))
    try:
        fresh_sql = be._conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='verification_cohorts'"
        ).fetchone()[0]
    finally:
        be.close()

    assert (
        _states(mig_sql)
        == _states(fresh_sql)
        == [
            "green",
            "invalidated",
            "open",
            "red",
        ]
    )


def test_the_guard_skips_a_schema_that_never_needed_rebuilding(tmp_path):
    """Fresh install: SCHEMA_SQL already admits 'invalidated', so the guarded
    post-step returns on its guard and rebuilds nothing. Double invocation
    after a genuine rebuild is covered by test_migrations.py::
    test_migration_idempotent."""
    be = SQLiteBackend(str(tmp_path / "fresh.db"))
    conn = be._conn
    try:
        assert bm.run_migrations(conn, SCHEMA_VERSION) == SCHEMA_VERSION
        assert conn.execute("SELECT COUNT(*) FROM verification_cohorts").fetchone()[0] == 0
    finally:
        be.close()
