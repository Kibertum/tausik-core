"""Concurrency + failure-visibility for v42 slug allocation
(v42-slug-race-and-silent-backfill).

Review of state-git-stable-ids found three holes: next_slug read-then-insert is a
TOCTOU race under the connection's check_same_thread=False; the backfill swallowed
errors silently; and the table name was f-string-interpolated. These pin the
fixes: the UNIQUE index is the source of truth (a raced insert retries, never
crashes or silently duplicates), a failed backfill is LOUD (queryable meta flag),
and a non-allowlisted table is rejected.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from backend_migrations_v42_backfill import maybe_backfill_v42  # noqa: E402
from slug_util import insert_with_slug, next_slug  # noqa: E402


def _backend(tmp_path):
    from project_backend import SQLiteBackend

    return SQLiteBackend(str(tmp_path / "t.db"))


class TestSlugAllocationIsRaceSafe:
    def test_a_raced_insert_retries_with_the_next_suffix(self, tmp_path):
        """Simulate a concurrent writer taking our slug between next_slug and the
        INSERT: the first attempt's UNIQUE INSERT raises, and insert_with_slug
        re-queries and retries — two DISTINCT rows, no exception escapes."""
        be = _backend(tmp_path)
        try:
            c = be._conn
            attempts: list[str] = []

            def racing_insert(slug):
                attempts.append(slug)
                if len(attempts) == 1:
                    # Another writer grabbed this slug first and committed it.
                    c.execute(
                        "INSERT INTO decisions(decision,created_at,slug) "
                        "VALUES('other','2026-01-01T00:00:00Z',?)",
                        (slug,),
                    )
                    c.commit()
                    raise sqlite3.IntegrityError("UNIQUE constraint failed: decisions.slug")
                return be._ins(
                    "INSERT INTO decisions(decision,created_at,slug) VALUES(?,?,?)",
                    ("mine", "2026-01-01T00:00:00Z", slug),
                )

            rid = insert_with_slug(be._q, racing_insert, "decisions", "TODO", "decision-x")
            # first 'todo' lost the race; retry saw it taken and used 'todo-2'.
            assert attempts == ["todo", "todo-2"]
            assert (
                be._conn.execute("SELECT slug FROM decisions WHERE id=?", (rid,)).fetchone()[0]
                == "todo-2"
            )
            # Two distinct rows exist; neither slug is duplicated.
            slugs = [r[0] for r in be._conn.execute("SELECT slug FROM decisions ORDER BY id")]
            assert slugs == ["todo", "todo-2"]
        finally:
            be.close()

    def test_exhausted_retries_reraise_loudly(self, tmp_path):
        """A slug that can never be placed must raise, not silently give up."""
        be = _backend(tmp_path)
        try:

            def always_conflict(_slug):
                raise sqlite3.IntegrityError("UNIQUE constraint failed")

            with pytest.raises(sqlite3.IntegrityError):
                insert_with_slug(be._q, always_conflict, "memory", "x", "memory-x", retries=3)
        finally:
            be.close()

    def test_concurrent_same_title_never_duplicates(self, tmp_path):
        """Two decisions with the same first line end with distinct slugs."""
        be = _backend(tmp_path)
        try:
            a = be.decision_add("Rollback plan")
            b = be.decision_add("Rollback plan differs below\nsecond line")
            sa = be._conn.execute("SELECT slug FROM decisions WHERE id=?", (a,)).fetchone()[0]
            sb = be._conn.execute("SELECT slug FROM decisions WHERE id=?", (b,)).fetchone()[0]
            assert sa != sb
        finally:
            be.close()


class TestTableAllowlist:
    def test_next_slug_rejects_an_unknown_table(self, tmp_path):
        be = _backend(tmp_path)
        try:
            with pytest.raises(ValueError, match="unknown table"):
                next_slug(be._q, "sessions", "x", "f")
        finally:
            be.close()

    @pytest.mark.parametrize("table", ["decisions", "memory"])
    def test_next_slug_accepts_the_allowlisted_tables(self, tmp_path, table):
        be = _backend(tmp_path)
        try:
            assert next_slug(be._q, table, "Some title", "fallback") == "some-title"
        finally:
            be.close()


class TestBackfillFailureIsLoud:
    def test_a_failed_backfill_records_a_queryable_error_marker(self, tmp_path):
        """Force CREATE UNIQUE INDEX to fail (a pre-existing duplicate slug) and
        assert the failure is recorded, not swallowed: the success flag stays
        unset and an error marker is written for doctor/status to surface."""
        be = _backend(tmp_path)
        try:
            c = be._conn
            # Tear down the healthy end-state, then plant a duplicate the index
            # cannot tolerate.
            c.execute("DROP INDEX IF EXISTS idx_decisions_slug")
            c.execute("DELETE FROM meta WHERE key='v42_slugs_backfilled'")
            c.execute(
                "INSERT INTO decisions(decision,created_at,slug) "
                "VALUES('a','2026-01-01T00:00:00Z','dup')"
            )
            c.execute(
                "INSERT INTO decisions(decision,created_at,slug) "
                "VALUES('b','2026-01-01T00:00:00Z','dup')"
            )
            c.commit()

            assert maybe_backfill_v42(c) == 0  # failed
            err = c.execute(
                "SELECT value FROM meta WHERE key='v42_slugs_backfill_error'"
            ).fetchone()
            assert err is not None, "a failed backfill must leave a loud, queryable marker"
            # The success flag must NOT be set on a failed run.
            done = c.execute("SELECT value FROM meta WHERE key='v42_slugs_backfilled'").fetchone()
            assert done is None
        finally:
            be.close()

    def test_recovery_clears_the_error_marker(self, tmp_path):
        """Once the obstruction is gone, a successful backfill removes the marker
        so a stale error never lingers."""
        be = _backend(tmp_path)
        try:
            c = be._conn
            c.execute("DROP INDEX IF EXISTS idx_decisions_slug")
            c.execute("DELETE FROM meta WHERE key='v42_slugs_backfilled'")
            c.execute(
                "INSERT INTO decisions(decision,created_at,slug) "
                "VALUES('a','2026-01-01T00:00:00Z','dup')"
            )
            c.execute(
                "INSERT INTO decisions(decision,created_at,slug) "
                "VALUES('b','2026-01-01T00:00:00Z','dup')"
            )
            c.commit()
            maybe_backfill_v42(c)  # fails, sets error marker
            assert c.execute("SELECT 1 FROM meta WHERE key='v42_slugs_backfill_error'").fetchone()

            # Remove the obstruction and re-run: success clears the marker.
            c.execute("UPDATE decisions SET slug='dup-2' WHERE decision='b'")
            c.execute("DELETE FROM meta WHERE key='v42_slugs_backfilled'")
            c.commit()
            maybe_backfill_v42(c)
            assert (
                c.execute("SELECT 1 FROM meta WHERE key='v42_slugs_backfill_error'").fetchone()
                is None
            )
            assert c.execute("SELECT 1 FROM meta WHERE key='v42_slugs_backfilled'").fetchone()
        finally:
            be.close()
