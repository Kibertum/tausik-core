"""Contextual chunk headers: deterministic, invisible, and idempotent.

`rag-contextual-chunk-prefix`. A header of file/symbol/summary words is indexed
alongside each chunk so a passage cut out of the middle of a file can still be
reached by a query phrased in the file's terms. Three properties carry the
design and each is pinned here:

  * deterministic — built from metadata, never from a model, so the same input
    yields the same bytes and an index is reproducible offline;
  * invisible — it lives in its own column, so search returns the source
    exactly as written and never the header;
  * idempotent — reindexing unchanged sources must not change the index.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "codebase-rag")
    ),
)

import rag_context  # noqa: E402
from rag_indexer import annotate_chunks, chunk_file  # noqa: E402
from rag_store import RAGStore  # noqa: E402

CROSSCUTTING_SCOPE = ["harness/claude/mcp/codebase-rag/"]

SAMPLE = '''"""Doctor drift checks — compares CLAUDE.md against the template."""

import os


def check_claudemd_drift(project_dir):
    """Count sections that diverged."""
    return 0


def scripts_drift_names(project_dir):
    total = 1
    for i in range(10):
        total += i
    return total
'''


# ---------- determinism (AC2) ----------


def test_prefix_is_byte_identical_across_runs():
    a = rag_context.build_context_prefix("scripts/foo_bar.py", "def baz():\n    pass")
    b = rag_context.build_context_prefix("scripts/foo_bar.py", "def baz():\n    pass")
    assert a == b and a != ""


def test_prefix_carries_path_words_and_symbol_words():
    prefix = rag_context.build_context_prefix(
        "scripts/service_doctor_drift.py", "def check_claudemd_drift(x):\n    return 0"
    )
    for word in ("scripts", "service", "doctor", "drift", "claudemd"):
        assert word in prefix, f"{word!r} missing from {prefix!r}"
    assert ".py" not in prefix, "the extension matches every Python chunk — no information"


def test_module_summary_reaches_every_chunk_not_just_the_first():
    chunks = annotate_chunks(chunk_file(SAMPLE, "python"), "scripts/x.py", "python", SAMPLE)
    assert len(chunks) >= 2
    assert all("Doctor drift checks" in c["context_prefix"] for c in chunks), (
        "the file's own summary is what a middle chunk loses when it is cut out"
    )


def test_continuation_chunk_inherits_the_enclosing_symbol():
    """A chunk with no definition line of its own is the whole point."""
    chunks = [
        {"content": "def outer():\n    a = 1", "chunk_index": 0, "chunk_type": "code"},
        {"content": "    b = 2\n    return b", "chunk_index": 1, "chunk_type": "code"},
    ]
    annotate_chunks(chunks, "scripts/x.py", "python", "")
    assert rag_context.extract_symbol(chunks[1]["content"]) == ""
    assert "outer" in chunks[1]["context_prefix"]


def test_chunk_without_metadata_gets_a_usable_prefix_not_a_broken_one():
    prefix = rag_context.build_context_prefix("a.py", "   \n\n")
    assert prefix == "a", "path words alone, no empty separators or None"


# ---------- the header must not leak (AC4) ----------


def test_search_returns_the_source_chunk_never_the_header(tmp_path):
    store = RAGStore(str(tmp_path / "rag.db"))
    try:
        chunks = annotate_chunks(
            chunk_file(SAMPLE, "python"), "scripts/service_doctor_drift.py", "python", SAMPLE
        )
        assert any(c["context_prefix"] for c in chunks)
        store.upsert_file("scripts/service_doctor_drift.py", chunks)

        results = store.search("claudemd drift", limit=5)
        assert results, "the header should make this reachable"
        for r in results:
            assert "context_prefix" not in r
            assert r["content"] in SAMPLE, "returned content must be verbatim source"
    finally:
        store.close()


def test_header_is_searchable_even_though_it_is_not_returned(tmp_path):
    """Query words that exist ONLY in the header, never in the chunk body."""
    store = RAGStore(str(tmp_path / "rag.db"))
    try:
        body = "    total = 1\n    for i in range(3):\n        total += i\n"
        chunks = [{"content": body, "chunk_index": 0, "chunk_type": "code"}]
        annotate_chunks(chunks, "scripts/quokka_ledger.py", "python", "")
        assert "quokka" not in body
        store.upsert_file("scripts/quokka_ledger.py", chunks)

        hits = store.search("quokka ledger", limit=5)
        assert hits, "a word present only in the header must still match"
        assert "quokka" not in hits[0]["content"], "…but must not appear in what is returned"
    finally:
        store.close()


# ---------- idempotence (AC5) ----------


def test_reindexing_unchanged_source_yields_an_identical_index(tmp_path):
    db = str(tmp_path / "rag.db")

    def _index_once() -> list[tuple]:
        store = RAGStore(db)
        try:
            chunks = annotate_chunks(chunk_file(SAMPLE, "python"), "scripts/x.py", "python", SAMPLE)
            store.upsert_file("scripts/x.py", chunks)
            rows = store._conn.execute(
                "SELECT file_path, chunk_index, content, context_prefix "
                "FROM rag_chunks ORDER BY chunk_index"
            ).fetchall()
            return [tuple(r) for r in rows]
        finally:
            store.close()

    assert _index_once() == _index_once()


# ---------- migration of an existing index ----------


def test_pre_v2_database_gains_the_column_and_keeps_its_rows(tmp_path):
    """An installed index must not be emptied by the upgrade.

    The FTS table is dropped and rebuilt because its column list changed; the
    chunks are the source of truth and must survive untouched.
    """
    import sqlite3

    db = str(tmp_path / "rag.db")
    legacy = sqlite3.connect(db)
    legacy.executescript(
        """
        CREATE TABLE rag_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT NOT NULL,
            chunk_index INTEGER NOT NULL, content TEXT NOT NULL, language TEXT,
            start_line INTEGER, end_line INTEGER, chunk_type TEXT DEFAULT 'code',
            indexed_at TEXT NOT NULL, UNIQUE(file_path, chunk_index));
        CREATE TABLE rag_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE VIRTUAL TABLE fts_code USING fts5(
            file_path, content, language, content='rag_chunks', content_rowid='id');
        INSERT INTO rag_chunks (file_path, chunk_index, content, language,
                                start_line, end_line, chunk_type, indexed_at)
        VALUES ('scripts/legacy.py', 0, 'def legacy_marker():\n    return 42',
                'python', 1, 2, 'code', '2026-01-01T00:00:00+00:00');
        """
    )
    legacy.commit()
    legacy.close()

    store = RAGStore(db)
    try:
        columns = {r[1] for r in store._conn.execute("PRAGMA table_info(rag_chunks)").fetchall()}
        assert "context_prefix" in columns
        rows = store._conn.execute("SELECT COUNT(*) FROM rag_chunks").fetchone()
        assert rows[0] == 1, "the upgrade must not drop indexed chunks"
        assert store.search("legacy_marker", limit=5), (
            "the rebuilt FTS index must find pre-existing rows — otherwise the "
            "upgrade silently empties every installed index"
        )
    finally:
        store.close()


def test_migration_is_not_rerun_on_an_already_current_database(tmp_path):
    db = str(tmp_path / "rag.db")
    first = RAGStore(db)
    try:
        first.upsert_file(
            "scripts/x.py",
            [
                {
                    "chunk_index": 0,
                    "content": "def keeper():\n    pass",
                    "context_prefix": "x keeper",
                }
            ],
        )
    finally:
        first.close()

    second = RAGStore(db)
    try:
        assert second._migrate_legacy_layout() is False
        assert second.search("keeper", limit=5)
    finally:
        second.close()
