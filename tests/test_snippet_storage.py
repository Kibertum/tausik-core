"""v15-snippet-table: dedicated snippets store + CRUD helpers.

Covers schema presence on the fresh-DB path, fresh-vs-migration structural
equivalence (v37), CRUD round-trips, FTS5 search, and the dedup-by-hash guard
(NEGATIVE: re-adding an identical snippet must not create a second row).
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from backend_migrations_v37 import MIGRATION_V37  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from snippet_storage import (  # noqa: E402
    add_snippet,
    count_snippets,
    delete_snippet,
    get_by_hash,
    get_snippet,
    search_snippets,
)

# Named objects this feature owns (excludes FTS5 internal shadow tables, which
# both paths create identically anyway).
_EXPECTED_OBJECTS = {
    "snippets",
    "fts_snippets",
    "snippets_ai",
    "snippets_ad",
    "snippets_au",
    "idx_snippets_taxonomy",
    "idx_snippets_language",
}


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "snip.db")))
    yield s
    s.be.close()


def _owned_objects(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE name IN ({})".format(
            ",".join("?" * len(_EXPECTED_OBJECTS))
        ),
        tuple(_EXPECTED_OBJECTS),
    ).fetchall()
    return {r[0] for r in rows}


# --- schema ----------------------------------------------------------------


def test_schema_version_bumped():
    # `>=`, not `==`: this asserts that the v37 snippet migration landed, which
    # stays true forever. An equality here turns every later migration into a
    # spurious failure in an unrelated test file (it did exactly that on v38).
    assert SCHEMA_VERSION >= 37


def test_fresh_db_has_all_objects(svc):
    assert _owned_objects(svc.be._conn) == _EXPECTED_OBJECTS


def test_fresh_db_records_version(svc):
    # Compared against the constant rather than a literal: the property under
    # test is "a fresh DB records the CURRENT schema version", which is what
    # this test is named for. A literal tested "the version is 37" instead.
    row = svc.be._conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert int(row[0]) == SCHEMA_VERSION


def _strip_sql(sql: str) -> str:
    """Drop `--` comments and collapse whitespace so the two DDL sources compare
    on structure, not on their (intentionally different) explanatory comments."""
    lines = [ln.split("--", 1)[0] for ln in sql.splitlines()]
    return " ".join(" ".join(lines).split())


def _owned_ddl(conn: sqlite3.Connection) -> dict[str, str]:
    """name -> structure-normalized DDL for owned objects (sql IS NOT NULL)."""
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE name IN ({}) AND sql IS NOT NULL".format(
            ",".join("?" * len(_EXPECTED_OBJECTS))
        ),
        tuple(_EXPECTED_OBJECTS),
    ).fetchall()
    return {n: _strip_sql(s) for n, s in rows}


def test_migration_v37_matches_fresh(svc):
    """MIGRATION_V37 on a bare DB yields the same owned objects AND DDL bodies."""
    fresh = _owned_objects(svc.be._conn)
    fresh_ddl = _owned_ddl(svc.be._conn)
    raw = sqlite3.connect(":memory:")
    try:
        for stmt in MIGRATION_V37:
            raw.execute(stmt)
        assert _owned_objects(raw) == fresh == _EXPECTED_OBJECTS
        # Body-level equivalence: triggers/indexes must be byte-identical (after
        # whitespace normalisation), not merely present by name.
        assert _owned_ddl(raw) == fresh_ddl
    finally:
        raw.close()


# --- CRUD ------------------------------------------------------------------


def test_add_and_get(svc):
    sid = add_snippet(
        svc.be._conn,
        code_hash="h1",
        language="python",
        code="def f():\n    return 1",
        source_file="a.py",
        source_lines="1-2",
        taxonomy_kind="function",
    )
    got = get_snippet(svc.be._conn, sid)
    assert got is not None
    assert got["hash"] == "h1"
    assert got["language"] == "python"
    assert got["source_file"] == "a.py"
    assert got["created_at"]  # auto-stamped


def test_get_missing_returns_none(svc):
    assert get_snippet(svc.be._conn, 9999) is None
    assert get_by_hash(svc.be._conn, "nope") is None


def test_dedup_by_hash(svc):
    """NEGATIVE: re-adding the same hash returns the original id, no 2nd row."""
    first = add_snippet(svc.be._conn, code_hash="dup", language="python", code="x=1")
    second = add_snippet(
        svc.be._conn, code_hash="dup", language="python", code="x=1 # different text"
    )
    assert first == second
    assert count_snippets(svc.be._conn) == 1


def test_count(svc):
    assert count_snippets(svc.be._conn) == 0
    add_snippet(svc.be._conn, code_hash="a", language="go", code="a")
    add_snippet(svc.be._conn, code_hash="b", language="go", code="b")
    assert count_snippets(svc.be._conn) == 2


# --- FTS5 search -----------------------------------------------------------


def test_search_finds_match(svc):
    add_snippet(
        svc.be._conn,
        code_hash="s1",
        language="python",
        code="def calculate_invoice_total(items): pass",
    )
    add_snippet(svc.be._conn, code_hash="s2", language="python", code="def render_button(): pass")
    hits = search_snippets(svc.be._conn, "invoice")
    assert len(hits) == 1
    assert hits[0]["hash"] == "s1"


def test_search_no_match_returns_empty(svc):
    add_snippet(svc.be._conn, code_hash="s1", language="python", code="def foo(): pass")
    assert search_snippets(svc.be._conn, "nonexistentxyz") == []


def test_search_empty_query_returns_empty(svc):
    add_snippet(svc.be._conn, code_hash="s1", language="python", code="def foo(): pass")
    assert search_snippets(svc.be._conn, "") == []
    assert search_snippets(svc.be._conn, "   ") == []


def test_search_special_chars_no_raise(svc):
    """A query with FTS operator chars must not raise — treated as a phrase."""
    add_snippet(svc.be._conn, code_hash="s1", language="python", code='print("hi")')
    # Must not raise; quote/operator chars are neutralised into a literal phrase.
    assert isinstance(search_snippets(svc.be._conn, 'AND "or" ('), list)


# --- delete + FTS sync -----------------------------------------------------


def test_delete(svc):
    sid = add_snippet(svc.be._conn, code_hash="d1", language="python", code="def gone(): pass")
    assert delete_snippet(svc.be._conn, sid) is True
    assert get_snippet(svc.be._conn, sid) is None
    assert delete_snippet(svc.be._conn, sid) is False  # already gone, no raise


def test_delete_resyncs_fts(svc):
    """After delete, the FTS index must not still surface the snippet."""
    sid = add_snippet(
        svc.be._conn, code_hash="d2", language="python", code="def uniqueword(): pass"
    )
    delete_snippet(svc.be._conn, sid)
    assert search_snippets(svc.be._conn, "uniqueword") == []


def test_update_resyncs_fts(svc):
    """The au (after-update) trigger keeps FTS in sync: old term gone, new found."""
    sid = add_snippet(svc.be._conn, code_hash="u1", language="python", code="def oldterm(): pass")
    svc.be._conn.execute("UPDATE snippets SET code=? WHERE id=?", ("def newterm(): pass", sid))
    svc.be._conn.commit()
    assert search_snippets(svc.be._conn, "oldterm") == []
    assert len(search_snippets(svc.be._conn, "newterm")) == 1
