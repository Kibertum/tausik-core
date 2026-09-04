"""v49 migration: the SPEC type CHECK reaches the standard's eleven — and stays CLOSED.

§8.3 closes the SPEC type list at eleven; ours enumerated nine, so ADR-013's
`SPEC-TEST` and `SPEC-DOC` were rejected by the DB itself. SQLite cannot widen a
CHECK with ALTER, so v49 rebuilds `specs` (the path v24 and v48 took).

Both directions are asserted, and the second is the one that matters. A
migration that dropped the CHECK entirely would pass "TEST is now accepted" just
as happily as a correct one — so the assertion that a type OUTSIDE the eleven is
STILL rejected after the migration is what separates widening the list from
opening it. A rebuild is also a quiet way to lose data, so rows, the FTS index
and all three triggers are checked on a database migrated WITH content rather
than on an empty one.
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
from service_specs import SPEC_TYPES  # noqa: E402
from test_migrations import V1_SCHEMA  # noqa: E402

# The migration UNDER TEST, pinned as a literal rather than derived from
# SCHEMA_VERSION: a fixture that names its subject "latest" stops testing that
# subject the moment something else becomes latest (the lesson v44 taught the
# v43 fixture next door).
_V49 = 49
PRE_V49 = _V49 - 1


def _db_at_v48(tmp_path, name="v48.db"):
    """A v1 database carried by the REAL migrations to v48, and no further.

    v49 and everything after it are removed for the duration, the way the v43
    fixture does it — popping only v49 would let a later migration run against a
    table v49 had not yet rebuilt, and the fixture would stop being "the pre-v49
    state". The statements come from the production registry, so the assertions
    below run against the real old schema rather than an imitation of it.
    """
    conn = sqlite3.connect(str(tmp_path / name))
    conn.isolation_level = None  # run_migrations drives its own transactions
    conn.executescript(V1_SCHEMA)
    removed = {v: bm.MIGRATIONS.pop(v) for v in sorted(bm.MIGRATIONS) if v >= _V49}
    try:
        assert bm.run_migrations(conn, 1) == PRE_V49
    finally:
        bm.MIGRATIONS.update(removed)
    return conn


@pytest.fixture
def seeded(tmp_path):
    """Fully migrated DB (fresh schema at SCHEMA_VERSION) holding two SPECs."""
    be = SQLiteBackend(str(tmp_path / "seed.db"))
    conn = be._conn
    conn.execute(
        "INSERT INTO specs (slug, type, title, content_ref, version, status, "
        "created_at, updated_at) VALUES "
        "('arch-one','ARCH','Arch One','docs/a.md','v1','active','2026-01-01','2026-01-02')"
    )
    conn.execute(
        "INSERT INTO specs (slug, type, title, content_ref, version, status, "
        "created_at, updated_at) VALUES "
        "('sec-two','SEC','Sec Two',NULL,'v2','draft','2026-01-03','2026-01-04')"
    )
    conn.commit()
    yield conn
    be.close()


# --- the version is registered ----------------------------------------------


def test_v49_is_registered_and_not_ahead_of_the_code():
    """v49 stays REGISTERED; being the LATEST version is not v49's property.

    This assertion used to read ``SCHEMA_VERSION == 49``, which made a fixture
    about v49 fail the moment v50 landed — the very coupling this file's own
    header warns against when it pins ``_V49`` as a literal instead of deriving
    it from SCHEMA_VERSION. Which version is current belongs to the newest
    migration's own test file.
    """
    assert 49 in MIGRATIONS
    assert SCHEMA_VERSION >= 49


# --- direction one: the two new types are accepted ---------------------------


@pytest.mark.parametrize("new_type", ["TEST", "DOC"])
def test_the_two_new_types_are_accepted_after_migration(seeded, new_type):
    slug = "s-" + new_type.lower()
    seeded.execute(
        "INSERT INTO specs (slug, type, title, version, status, created_at, updated_at) "
        "VALUES (?,?,'T','v1','draft','2026-01-01','2026-01-01')",
        (slug, new_type),
    )
    seeded.commit()
    assert seeded.execute("SELECT type FROM specs WHERE slug=?", (slug,)).fetchone()[0] == new_type


def test_every_type_the_standard_closes_on_is_insertable(seeded):
    for i, t in enumerate(SPEC_TYPES):
        seeded.execute(
            "INSERT INTO specs (slug, type, title, version, status, created_at, updated_at) "
            "VALUES (?,?,'T','v1','draft','2026-01-01','2026-01-01')",
            ("all-%d" % i, t),
        )
    seeded.commit()
    got = {r[0] for r in seeded.execute("SELECT DISTINCT type FROM specs")}
    assert set(SPEC_TYPES) <= got


# --- direction two: the list is WIDENED, not OPENED --------------------------


@pytest.mark.parametrize("bad_type", ["PLAN", "TESTS", "test", "", "SPEC-TEST"])
def test_a_type_outside_the_closed_list_is_still_rejected(seeded, bad_type):
    """The control that separates widening the list from opening it.

    A migration that dropped the CHECK would satisfy every assertion above this
    one, so without this the suite could not tell the two apart.
    """
    with pytest.raises(sqlite3.IntegrityError):
        seeded.execute(
            "INSERT INTO specs (slug, type, title, version, status, created_at, updated_at) "
            "VALUES ('bad',?,'T','v1','draft','2026-01-01','2026-01-01')",
            (bad_type,),
        )
        seeded.commit()


@pytest.mark.parametrize("bad_type", ["PLAN", "TESTS", "test", ""])
def test_the_migrated_schema_still_rejects_an_outside_type(tmp_path, bad_type):
    """The same control, on the MIGRATION path rather than the fresh one.

    The fresh-schema version above proves the baseline DDL stayed closed; it
    says nothing about the CHECK v49 writes, because a fresh database never
    runs the migration. Mutation testing found exactly this hole: replacing
    v49's CHECK with a bare `type TEXT NOT NULL` — opening the list outright —
    left every other assertion in this file green.
    """
    conn = _db_at_v48(tmp_path, "reject-%s.db" % (bad_type or "empty"))
    try:
        bm.run_migrations(conn, PRE_V49)
        conn.execute(
            "INSERT INTO specs (slug, type, title, version, status, created_at, updated_at) "
            "VALUES ('ok','TEST','T','v1','draft','2026-01-01','2026-01-01')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO specs (slug, type, title, version, status, created_at, "
                "updated_at) VALUES ('bad',?,'T','v1','draft','2026-01-01','2026-01-01')",
                (bad_type,),
            )
    finally:
        conn.close()


def test_migrated_and_fresh_schemas_declare_the_same_type_check(tmp_path):
    """The two paths must converge. A migration that widened one and not the
    other leaves CI green on the fresh schema and wrong in the field — the
    v43 lesson, in the other direction."""
    migrated = _db_at_v48(tmp_path, "converge.db")
    try:
        bm.run_migrations(migrated, PRE_V49)
        mig_sql = migrated.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='specs'"
        ).fetchone()[0]
    finally:
        migrated.close()

    be = SQLiteBackend(str(tmp_path / "fresh.db"))
    try:
        fresh_sql = be._conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='specs'"
        ).fetchone()[0]
    finally:
        be.close()

    def _types(ddl):
        chunk = ddl[ddl.index("CHECK(type IN") :]
        chunk = chunk[chunk.index("(", chunk.index("IN")) : chunk.index(")")]
        return sorted(p.strip().strip("'") for p in chunk.strip("( ").split(",") if p.strip())

    assert _types(mig_sql) == _types(fresh_sql) == sorted(SPEC_TYPES)


def test_before_v49_the_new_types_were_rejected(tmp_path):
    """The defect itself, pinned: on the pre-v49 schema the DB refused SPEC-TEST.

    Without it the migration could be a no-op and nothing here would notice.
    """
    conn = _db_at_v48(tmp_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO specs (slug, type, title, version, status, created_at, "
                "updated_at) VALUES ('t','TEST','T','v1','draft','2026-01-01','2026-01-01')"
            )
            conn.commit()
    finally:
        conn.close()


# --- the rebuild loses nothing ----------------------------------------------


def test_rows_survive_the_rebuild_column_for_column(tmp_path):
    conn = _db_at_v48(tmp_path, "carry.db")
    try:
        conn.execute(
            "INSERT INTO specs (slug, type, title, content_ref, version, status, "
            "created_at, updated_at) VALUES "
            "('keep-me','DATA','Keep Me','docs/k.md','v7','deprecated','2026-02-01','2026-02-02')"
        )
        conn.commit()
        before = conn.execute("SELECT * FROM specs WHERE slug='keep-me'").fetchone()
        bm.run_migrations(conn, PRE_V49)
        after = conn.execute("SELECT * FROM specs WHERE slug='keep-me'").fetchone()
        assert after == before, "the rebuild must preserve every column, id included"
    finally:
        conn.close()


def test_fts_index_and_triggers_work_after_the_rebuild(seeded):
    """Triggers die with the dropped table. If v49 forgets to recreate them the
    index stops tracking silently and search goes stale without an error."""
    names = {r[0] for r in seeded.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert {"specs_ai", "specs_ad", "specs_au"} <= names

    # A row that predates the rebuild is still findable.
    found = seeded.execute("SELECT slug FROM fts_specs WHERE fts_specs MATCH 'Arch'").fetchall()
    assert [r[0] for r in found] == ["arch-one"]

    # INSERT trigger — and on one of the newly admitted types.
    seeded.execute(
        "INSERT INTO specs (slug, type, title, version, status, created_at, updated_at) "
        "VALUES ('doc-new','DOC','Delivered Handbook','v1','draft','2026-03-01','2026-03-01')"
    )
    seeded.commit()
    found = seeded.execute("SELECT slug FROM fts_specs WHERE fts_specs MATCH 'Handbook'").fetchall()
    assert [r[0] for r in found] == ["doc-new"]

    # UPDATE trigger.
    seeded.execute("UPDATE specs SET title='Renamed Handbook' WHERE slug='doc-new'")
    seeded.commit()
    renamed = seeded.execute("SELECT slug FROM fts_specs WHERE fts_specs MATCH 'Renamed'")
    assert [r[0] for r in renamed] == ["doc-new"]

    # DELETE trigger.
    seeded.execute("DELETE FROM specs WHERE slug='doc-new'")
    seeded.commit()
    assert not seeded.execute(
        "SELECT slug FROM fts_specs WHERE fts_specs MATCH 'Renamed'"
    ).fetchall()


def test_type_index_survives_the_rebuild(seeded):
    idx = {r[0] for r in seeded.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_specs_type" in idx


def test_migration_is_idempotent(seeded):
    assert bm.run_migrations(seeded, SCHEMA_VERSION) == SCHEMA_VERSION
    assert seeded.execute("SELECT COUNT(*) FROM specs").fetchone()[0] == 2
