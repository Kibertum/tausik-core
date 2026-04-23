"""Tests for brain database schema (local mirror of Notion brain).

Verifies DDL application, FTS5 indexing with unicode61 tokenizer,
CHECK constraints, trigger sync, and schema idempotence.
"""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_schema  # noqa: E402


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    brain_schema.apply_schema(c)
    yield c
    c.close()


def _objects(conn, type_name):
    return {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type=?", (type_name,)
        ).fetchall()
    }


def test_all_core_tables_created(conn):
    tables = _objects(conn, "table")
    for t in (
        "brain_meta",
        "brain_decisions",
        "brain_web_cache",
        "brain_patterns",
        "brain_gotchas",
        "sync_state",
    ):
        assert t in tables, f"missing table {t}"


def test_all_fts_virtual_tables_created(conn):
    tables = _objects(conn, "table")
    for t in (
        "fts_brain_decisions",
        "fts_brain_web_cache",
        "fts_brain_patterns",
        "fts_brain_gotchas",
    ):
        assert t in tables, f"missing FTS virtual table {t}"


def test_expected_indexes_present(conn):
    indexes = _objects(conn, "index")
    expected = {
        "idx_brain_decisions_last_edited",
        "idx_brain_decisions_project",
        "idx_brain_decisions_date",
        "idx_brain_web_cache_last_edited",
        "idx_brain_web_cache_project",
        "idx_brain_web_cache_content_hash",
        "idx_brain_web_cache_fetched",
        "idx_brain_patterns_last_edited",
        "idx_brain_patterns_project",
        "idx_brain_patterns_date",
        "idx_brain_gotchas_last_edited",
        "idx_brain_gotchas_project",
        "idx_brain_gotchas_date",
    }
    missing = expected - indexes
    assert not missing, f"missing indexes: {missing}"


def test_fts_triggers_created_for_all_tables(conn):
    triggers = _objects(conn, "trigger")
    for table in (
        "brain_decisions",
        "brain_web_cache",
        "brain_patterns",
        "brain_gotchas",
    ):
        for suffix in ("ai", "ad", "au"):
            assert f"{table}_{suffix}" in triggers, f"missing trigger {table}_{suffix}"


def test_schema_is_idempotent(conn):
    brain_schema.apply_schema(conn)
    brain_schema.apply_schema(conn)


def test_schema_version_recorded(conn):
    row = conn.execute(
        "SELECT value FROM brain_meta WHERE key='schema_version'"
    ).fetchone()
    assert row is not None
    assert row[0] == str(brain_schema.SCHEMA_VERSION)


def test_fts_search_finds_ascii(conn):
    conn.execute(
        """INSERT INTO brain_decisions
           (notion_page_id, name, context, decision, rationale,
            source_project_hash, last_edited_time, created_time)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "page-1",
            "Use urllib instead of requests",
            "Need HTTP client for Notion API",
            "stdlib urllib.request",
            "zero deps convention",
            "a1b2c3d4e5f67890",
            "2026-04-23T10:00:00.000Z",
            "2026-04-23T10:00:00.000Z",
        ),
    )
    conn.commit()
    rows = conn.execute(
        "SELECT rowid FROM fts_brain_decisions WHERE fts_brain_decisions MATCH ?",
        ("urllib",),
    ).fetchall()
    assert len(rows) == 1


def test_fts_search_finds_cyrillic(conn):
    """Regression: unicode61 tokenizer must index Cyrillic (design §8 gotcha)."""
    conn.execute(
        """INSERT INTO brain_decisions
           (notion_page_id, name, context, decision, rationale,
            source_project_hash, last_edited_time, created_time)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "page-2",
            "Использовать urllib вместо requests",
            "Нужен HTTP-клиент для Notion API",
            "stdlib urllib.request",
            "zero deps соглашение",
            "a1b2c3d4e5f67890",
            "2026-04-23T10:00:00.000Z",
            "2026-04-23T10:00:00.000Z",
        ),
    )
    conn.commit()
    rows = conn.execute(
        "SELECT rowid FROM fts_brain_decisions WHERE fts_brain_decisions MATCH ?",
        ("Использовать",),
    ).fetchall()
    assert len(rows) == 1
    rows = conn.execute(
        "SELECT rowid FROM fts_brain_decisions WHERE fts_brain_decisions MATCH ?",
        ("соглашение",),
    ).fetchall()
    assert len(rows) == 1


def test_delete_propagates_to_fts(conn):
    conn.execute(
        """INSERT INTO brain_decisions
           (notion_page_id, name, source_project_hash,
            last_edited_time, created_time)
           VALUES ('pdel', 'UniqueMarker42', 'h',
                   '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"""
    )
    conn.commit()
    conn.execute("DELETE FROM brain_decisions WHERE notion_page_id='pdel'")
    conn.commit()
    rows = conn.execute(
        "SELECT rowid FROM fts_brain_decisions WHERE fts_brain_decisions MATCH ?",
        ("UniqueMarker42",),
    ).fetchall()
    assert len(rows) == 0


def test_update_reindexes_fts(conn):
    conn.execute(
        """INSERT INTO brain_decisions
           (notion_page_id, name, source_project_hash,
            last_edited_time, created_time)
           VALUES ('pupd', 'AlphaMarker', 'h',
                   '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"""
    )
    conn.commit()
    conn.execute(
        "UPDATE brain_decisions SET name='BetaMarker' WHERE notion_page_id='pupd'"
    )
    conn.commit()
    old = conn.execute(
        "SELECT rowid FROM fts_brain_decisions WHERE fts_brain_decisions MATCH ?",
        ("AlphaMarker",),
    ).fetchall()
    new = conn.execute(
        "SELECT rowid FROM fts_brain_decisions WHERE fts_brain_decisions MATCH ?",
        ("BetaMarker",),
    ).fetchall()
    assert len(old) == 0
    assert len(new) == 1


def test_unique_notion_page_id(conn):
    conn.execute(
        """INSERT INTO brain_decisions
           (notion_page_id, name, source_project_hash,
            last_edited_time, created_time)
           VALUES ('dup', 't', 'h', 'x', 'x')"""
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO brain_decisions
               (notion_page_id, name, source_project_hash,
                last_edited_time, created_time)
               VALUES ('dup', 't2', 'h', 'x', 'x')"""
        )


def test_generalizable_check_constraint(conn):
    conn.execute(
        """INSERT INTO brain_decisions
           (notion_page_id, name, source_project_hash,
            last_edited_time, created_time, generalizable)
           VALUES ('p-ok', 't', 'h', 'x', 'x', 0)"""
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO brain_decisions
               (notion_page_id, name, source_project_hash,
                last_edited_time, created_time, generalizable)
               VALUES ('p-bad', 't', 'h', 'x', 'x', 5)"""
        )


def test_confidence_check_constraint(conn):
    conn.execute(
        """INSERT INTO brain_patterns
           (notion_page_id, name, source_project_hash,
            last_edited_time, created_time, confidence)
           VALUES ('pat-ok', 't', 'h', 'x', 'x', 'proven')"""
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO brain_patterns
               (notion_page_id, name, source_project_hash,
                last_edited_time, created_time, confidence)
               VALUES ('pat-bad', 't', 'h', 'x', 'x', 'maybe')"""
        )


def test_severity_check_constraint(conn):
    conn.execute(
        """INSERT INTO brain_gotchas
           (notion_page_id, name, source_project_hash,
            last_edited_time, created_time, severity)
           VALUES ('g-ok', 't', 'h', 'x', 'x', 'high')"""
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO brain_gotchas
               (notion_page_id, name, source_project_hash,
                last_edited_time, created_time, severity)
               VALUES ('g-bad', 't', 'h', 'x', 'x', 'critical')"""
        )


def test_sync_state_check_constraint(conn):
    for cat in ("decisions", "web_cache", "patterns", "gotchas"):
        conn.execute(
            "INSERT INTO sync_state(category, last_pull_at) VALUES (?, ?)",
            (cat, "2026-01-01T00:00:00Z"),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO sync_state(category) VALUES (?)", ("bogus",))


def test_required_not_null_columns(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO brain_web_cache
               (notion_page_id, name, fetched_at, source_project_hash,
                last_edited_time, created_time)
               VALUES ('wc-miss', 'n', 'x', 'h', 'x', 'x')"""
        )


def test_multi_select_defaults_to_empty_array(conn):
    conn.execute(
        """INSERT INTO brain_patterns
           (notion_page_id, name, source_project_hash,
            last_edited_time, created_time)
           VALUES ('pat-def', 't', 'h', 'x', 'x')"""
    )
    row = conn.execute(
        "SELECT tags, stack FROM brain_patterns WHERE notion_page_id='pat-def'"
    ).fetchone()
    assert row[0] == "[]"
    assert row[1] == "[]"
