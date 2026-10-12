"""v50: the ADAPT status CHECK reaches the standard's §7.8.1 list — and stays CLOSED.

§7.8.1 closes the ADAPT status list at ``draft | review | asked | answered |
approved | frozen | superseded``. Ours enumerated a shorter list of its own, and
the divergence ran BOTH ways: we carried our own ``signed``, which the standard's closed list does
not contain, and we lacked ``approved``, which §13.3.3 p.77 REQUIRES on the
findings-present branch. The second half is the heavy one — the DB CHECK would
have REJECTED ``approved``, so conformance was UNREACHABLE rather than merely
unmet. SQLite cannot widen a CHECK with ALTER, so v50 rebuilds ``adapts`` (the
path v24, v48 and v49 took).

BOTH DIRECTIONS ARE ASSERTED, and the second is the one that matters. A
migration that dropped the CHECK entirely would pass "approved is now accepted"
just as happily as a correct one — so the assertion that a status OUTSIDE the
list is STILL rejected after the migration is what separates widening the list
from opening it. That is not theoretical: v49's own docstring records a mutation
which replaced the CHECK with a bare ``type TEXT NOT NULL`` and survived a test
set that only walked the fresh-DB path.

A rebuild is also a quiet way to lose data, so rows, the FTS index, all three
triggers and every one of the four child tables are checked on a database
migrated WITH content rather than on an empty one.
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
from backend_migrations_v50 import maybe_widen_adapt_statuses_v50  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from service_adapts import ADAPT_STATUSES  # noqa: E402
from test_migrations import V1_SCHEMA  # noqa: E402

# The migration UNDER TEST, pinned as a literal rather than derived from
# SCHEMA_VERSION: a fixture that names its subject "latest" stops testing that
# subject the moment something else becomes latest (the lesson v44 taught the
# v43 fixture, and the reason the v49 file next door pins its own number).
_V50 = 50
PRE_V50 = _V50 - 1

# The §7.8.1 list, written out ONCE, here, as the test's own statement of the
# standard. This is the one place a literal belongs: everywhere else the value
# must be derived, and this file is what proves the derivation lands on the
# standard rather than on itself.
STANDARD_STATUSES = (
    "draft",
    "review",
    "asked",
    "answered",
    "approved",
    "frozen",
    "superseded",
)


def _status_domain(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Values ``adapts.status`` admits, parsed from the DDL the database stores.

    Read from ``sqlite_master`` and not from any Python constant on purpose: the
    CHECK is what the database ACTUALLY enforces, and the whole defect this
    migration repairs was the substrate disagreeing with the constant.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='adapts'"
    ).fetchone()
    assert row and row[0], "adapts table has no stored DDL"
    ddl = str(row[0])
    marker = "CHECK(status IN"
    at = ddl.find(marker)
    assert at >= 0, f"adapts.status carries no CHECK at all:\n{ddl}"
    chunk = ddl[at + len(marker) : ddl.find("))", at + len(marker))]
    return tuple(
        part.strip().strip("'\"") for part in chunk.strip(" (\n").split(",") if part.strip()
    )


def _db_at_v49(tmp_path, name="v49.db"):
    """A v1 database carried by the REAL migrations to v49, and no further.

    v50 and everything after it are removed for the duration, the way the v43
    and v49 fixtures do it — popping only v50 would let a later migration run
    against a table v50 had not yet rebuilt, and the fixture would stop being
    "the pre-v50 state". The statements come from the production registry, so
    the assertions below run against the real old schema rather than an
    imitation of it.
    """
    conn = sqlite3.connect(str(tmp_path / name))
    conn.isolation_level = None  # run_migrations drives its own transactions
    conn.executescript(V1_SCHEMA)
    removed = {v: bm.MIGRATIONS.pop(v) for v in sorted(bm.MIGRATIONS) if v >= _V50}
    try:
        assert bm.run_migrations(conn, 1) == PRE_V50
    finally:
        bm.MIGRATIONS.update(removed)
    return conn


@pytest.fixture
def pre_v50(tmp_path):
    """Pre-v50 database holding a 'signed' ADAPT with all four child rows.

    Content is seeded BEFORE the rebuild so the copy has something to lose. A
    rebuild tested on an empty table proves only that the DDL parses.
    """
    conn = _db_at_v49(tmp_path)
    conn.execute(
        "INSERT INTO adapts(slug, title, tz_ref, status, parent_adapt, delta_n, "
        "created_at, updated_at) VALUES "
        "('ad-old','Old ADAPT','TZ-1','signed',NULL,0,'2026-01-01','2026-01-02')"
    )
    conn.execute(
        "INSERT INTO adapts(slug, title, tz_ref, status, parent_adapt, delta_n, "
        "created_at, updated_at) VALUES "
        "('ad-draft','Draft ADAPT','TZ-2','draft',NULL,0,'2026-01-03','2026-01-04')"
    )
    conn.execute(
        "INSERT INTO adapt_interpretations(adapt_slug, tz_ref, citation, "
        "engineering_interpretation, scope_in, scope_out, created_at) VALUES "
        "('ad-old','TZ§1','cite','interp','in','out','2026-01-01')"
    )
    conn.execute(
        "INSERT INTO adapt_findings(adapt_slug, category, description, created_at) "
        "VALUES ('ad-old','gap','a gap','2026-01-01')"
    )
    conn.execute(
        "INSERT INTO adapt_signatures(adapt_slug, role, signed_by, signed_at) "
        "VALUES ('ad-old','architect','Claude','2026-01-01')"
    )
    conn.execute(
        "INSERT INTO adapt_links(adapt_slug, target_type, target_slug, created_at) "
        "VALUES ('ad-old','spec','sp-1','2026-01-01')"
    )
    conn.commit()
    return conn


# --- the version is registered ----------------------------------------------


def test_v50_is_registered_and_not_in_the_future():
    """v50 is a step in the chain, and the chain has since moved past it.

    This asserted `SCHEMA_VERSION == _V50` while v50 was the newest migration,
    which made every later migration red on a fact about v50. What this module
    is about is v50's own effect; that it is REGISTERED and already reached is
    the part that stays true as the chain grows.
    """
    assert _V50 in MIGRATIONS
    assert SCHEMA_VERSION >= _V50


# --- AC-1: the domain is the standard's, on BOTH schema paths ---------------


def test_fresh_schema_carries_the_standard_list(tmp_path):
    be = SQLiteBackend(str(tmp_path / "fresh.db"))
    try:
        assert _status_domain(be._conn) == STANDARD_STATUSES
    finally:
        be.close()


def test_migrated_schema_carries_the_standard_list(pre_v50):
    """The MIGRATED path, not only the fresh one.

    v49 recorded a mutation that survived because its tests only walked the
    fresh-DB path; asserting the same property on a database that got here by
    migration is what closes that hole.
    """
    assert "approved" not in _status_domain(pre_v50)  # precondition, measured
    maybe_widen_adapt_statuses_v50(pre_v50)
    assert _status_domain(pre_v50) == STANDARD_STATUSES


# --- AC-4: the substrate is PINNED to the Python domain ---------------------


# The FRESH-schema pin lives with the other three mirrors in
# tests/test_enum_single_source.py — a second copy here would be this very
# defect one level up. What belongs to v50 is the MIGRATED path: a database
# that reached the domain by rebuild rather than by fresh DDL.
def test_migrated_check_is_pinned_to_the_python_domain(pre_v50):
    maybe_widen_adapt_statuses_v50(pre_v50)
    assert _status_domain(pre_v50) == tuple(ADAPT_STATUSES)


# --- AC-2 NEGATIVE: widened, not OPENED -------------------------------------


def test_status_outside_the_list_is_rejected_on_fresh_schema(tmp_path):
    be = SQLiteBackend(str(tmp_path / "closed.db"))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            be._conn.execute(
                "INSERT INTO adapts(slug, title, tz_ref, status, delta_n, "
                "created_at, updated_at) VALUES('x','T','TZ','bogus',0,'a','b')"
            )
    finally:
        be.close()


def test_status_outside_the_list_is_rejected_after_migration(pre_v50):
    maybe_widen_adapt_statuses_v50(pre_v50)
    with pytest.raises(sqlite3.IntegrityError):
        pre_v50.execute(
            "INSERT INTO adapts(slug, title, tz_ref, status, delta_n, "
            "created_at, updated_at) VALUES('x','T','TZ','bogus',0,'a','b')"
        )


def test_our_old_signed_is_itself_rejected_after_migration(pre_v50):
    """NEGATIVE, and the sharpest one: the value we INVENTED is now refused.

    'signed' was never in the standard's closed list. A migration that merely
    ADDED the missing values while leaving ours in place would look correct on
    every positive assertion and would still leave the list un-closed.
    """
    maybe_widen_adapt_statuses_v50(pre_v50)
    with pytest.raises(sqlite3.IntegrityError):
        pre_v50.execute(
            "INSERT INTO adapts(slug, title, tz_ref, status, delta_n, "
            "created_at, updated_at) VALUES('x','T','TZ','signed',0,'a','b')"
        )


def test_every_standard_status_is_actually_accepted(pre_v50):
    """The positive half: each of the standard's values inserts without error."""
    maybe_widen_adapt_statuses_v50(pre_v50)
    for i, status in enumerate(STANDARD_STATUSES):
        pre_v50.execute(
            "INSERT INTO adapts(slug, title, tz_ref, status, delta_n, "
            "created_at, updated_at) VALUES(?,'T','TZ',?,0,'a','b')",
            (f"ok-{i}", status),
        )
    got = {r[0] for r in pre_v50.execute("SELECT status FROM adapts WHERE slug LIKE 'ok-%'")}
    assert got == set(STANDARD_STATUSES)


# --- AC-3: the row mapping, idempotence, and the partial fixture ------------


def test_signed_rows_become_approved(pre_v50):
    maybe_widen_adapt_statuses_v50(pre_v50)
    rows = dict(pre_v50.execute("SELECT slug, status FROM adapts"))
    assert rows == {"ad-old": "approved", "ad-draft": "draft"}


def test_migration_is_idempotent(pre_v50):
    assert maybe_widen_adapt_statuses_v50(pre_v50) == 1
    assert maybe_widen_adapt_statuses_v50(pre_v50) == 0
    assert _status_domain(pre_v50) == STANDARD_STATUSES


def test_fresh_schema_falls_through_the_guard(tmp_path):
    """A fresh DB already carries the standard list — the step must skip it."""
    be = SQLiteBackend(str(tmp_path / "skip.db"))
    try:
        assert maybe_widen_adapt_statuses_v50(be._conn) == 0
    finally:
        be.close()


def test_partial_fixture_without_adapts_is_skipped(tmp_path):
    """NEGATIVE: no adapts table at all → skip, never 'no such table'.

    This is the reason the work lives in a guarded post-step instead of a list
    of statements: test_migration_v36_creates_tables_clean drives a MINIMAL
    database through the registry, and a blind rebuild would take the whole run
    down with it.
    """
    conn = sqlite3.connect(str(tmp_path / "partial.db"))
    conn.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
    conn.commit()
    assert maybe_widen_adapt_statuses_v50(conn) == 0
    conn.close()


# --- AC-9: the rebuild loses nothing ----------------------------------------


def test_rebuild_preserves_rows_children_and_integrity(pre_v50):
    """A rebuild is a quiet way to lose data — so count both sides of it."""
    tables = (
        "adapts",
        "adapt_interpretations",
        "adapt_findings",
        "adapt_signatures",
        "adapt_links",
    )
    before = {t: pre_v50.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    ids_before = dict(pre_v50.execute("SELECT slug, id FROM adapts"))

    maybe_widen_adapt_statuses_v50(pre_v50)

    after = {t: pre_v50.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    assert after == before
    # ids are preserved because fts_adapts is an external-content index keyed by
    # rowid: a renumbering would silently invalidate every entry in it.
    assert dict(pre_v50.execute("SELECT slug, id FROM adapts")) == ids_before
    assert pre_v50.execute("PRAGMA foreign_key_check").fetchall() == []


def test_rebuild_restores_the_three_triggers_and_the_index(pre_v50):
    maybe_widen_adapt_statuses_v50(pre_v50)
    names = {
        r[0]
        for r in pre_v50.execute("SELECT name FROM sqlite_master WHERE type IN ('trigger','index')")
    }
    assert {"adapts_ai", "adapts_ad", "adapts_au", "idx_adapts_parent"} <= names


# The slug carries a hyphen, which FTS5 reads as an OPERATOR unless the term is
# quoted inside the query string. Passed as a parameter rather than inlined so
# the quoting stays visible instead of fighting Python's own quotes.
_FTS_TERM = '"ad-old"'


def test_fts_search_still_finds_a_copied_row(pre_v50):
    """The FTS index survives the rebuild rather than being silently emptied."""
    maybe_widen_adapt_statuses_v50(pre_v50)
    hits = {
        r[0]
        for r in pre_v50.execute(
            "SELECT slug FROM fts_adapts WHERE fts_adapts MATCH ?", (_FTS_TERM,)
        )
    }
    assert "ad-old" in hits


def test_copy_does_not_duplicate_fts_entries(pre_v50):
    """Triggers are dropped BEFORE the copy; if they were not, every row would
    land in the index twice and search would return it twice."""
    maybe_widen_adapt_statuses_v50(pre_v50)
    n = pre_v50.execute(
        "SELECT COUNT(*) FROM fts_adapts WHERE fts_adapts MATCH ?", (_FTS_TERM,)
    ).fetchone()[0]
    assert n == 1


# --- AC-6: the two ADR-007 columns exist on both paths ----------------------


def test_new_columns_exist_on_fresh_schema(tmp_path):
    be = SQLiteBackend(str(tmp_path / "cols.db"))
    try:
        cols = {r[1] for r in be._conn.execute("PRAGMA table_info(adapts)")}
    finally:
        be.close()
    assert {"trigger_stage", "supersession_rationale"} <= cols


def test_new_columns_exist_after_migration(pre_v50):
    maybe_widen_adapt_statuses_v50(pre_v50)
    cols = {r[1] for r in pre_v50.execute("PRAGMA table_info(adapts)")}
    assert {"trigger_stage", "supersession_rationale"} <= cols


def test_broken_fk_integrity_stops_the_migration(pre_v50):
    """The FK check after the rebuild has a SUBJECT, and it is asserted here.

    A mutation that deleted the `raise` survived the first suite: every fixture
    had intact references, so the branch was never entered. Surviving mutants
    clustered in an unexercised layer are a sign of a missing test rather than a
    weak assertion (memory #552) — this is that test, and it is the only place
    the rebuild is allowed to fail loudly.

    The dangling child row is inserted with foreign keys OFF, which is exactly
    how such a row reaches a real database: the rebuild itself runs with them
    off, so a pre-existing violation would otherwise be carried across silently.
    """
    pre_v50.execute("PRAGMA foreign_keys=OFF")
    pre_v50.execute(
        "INSERT INTO adapt_findings(adapt_slug, category, description, created_at) "
        "VALUES ('ghost-adapt','gap','references an ADAPT that does not exist','2026-01-01')"
    )
    pre_v50.commit()
    with pytest.raises(RuntimeError, match="FK integrity"):
        maybe_widen_adapt_statuses_v50(pre_v50)


def test_intact_fk_integrity_does_not_stop_the_migration(pre_v50):
    """NEGATION of the bucket above: the refusal must be EARNED, not constant.

    Same fixture, no dangling row. If this went red too, the test above would be
    proving nothing about integrity — only that the migration raises.
    """
    assert maybe_widen_adapt_statuses_v50(pre_v50) == 1
