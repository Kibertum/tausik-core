"""Baseline DDL for the dedicated snippets store (v15-snippet-table).

Kept out of backend_schema.py to hold that file under the 400-line filesize
gate. ``init_schema`` runs SNIPPETS_SQL on the fresh-DB path; the migration path
(v37 in backend_migrations.py) builds the same objects for existing DBs.

The two DDL sources MUST stay structurally equivalent — the v37 migration test
and the fresh-DB test both assert the same tables/triggers exist.

This is the storage substrate for the v15 snippet system: the AST clone
detector (v15-snippet-ast-detect) writes clusters here; classifier
(v15-snippet-classifier) fills taxonomy_kind; MCP search reads via fts_snippets.
``hash`` is UNIQUE so re-ingesting an identical snippet is a no-op dedup.
``taxonomy_kind`` is intentionally NOT CHECK-constrained — the taxonomy is
advisory (set by a later classifier), not a RENAR closed list.
"""

from __future__ import annotations

SNIPPETS_SQL = """
CREATE TABLE IF NOT EXISTS snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT NOT NULL UNIQUE,
    language TEXT NOT NULL,
    code TEXT NOT NULL,
    source_file TEXT,
    source_lines TEXT,
    taxonomy_kind TEXT,
    -- fts_rank: cached clustering/relevance score (REAL, nullable). Written by
    -- the AST detector when it scores a cluster; NULL until then.
    fts_rank REAL,
    created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_snippets USING fts5(
    code, source_file, taxonomy_kind,
    content='snippets', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS snippets_ai AFTER INSERT ON snippets BEGIN
    INSERT INTO fts_snippets(rowid, code, source_file, taxonomy_kind)
    VALUES (new.id, new.code, new.source_file, new.taxonomy_kind);
END;
CREATE TRIGGER IF NOT EXISTS snippets_ad AFTER DELETE ON snippets BEGIN
    INSERT INTO fts_snippets(fts_snippets, rowid, code, source_file, taxonomy_kind)
    VALUES ('delete', old.id, old.code, old.source_file, old.taxonomy_kind);
END;
CREATE TRIGGER IF NOT EXISTS snippets_au AFTER UPDATE ON snippets BEGIN
    INSERT INTO fts_snippets(fts_snippets, rowid, code, source_file, taxonomy_kind)
    VALUES ('delete', old.id, old.code, old.source_file, old.taxonomy_kind);
    INSERT INTO fts_snippets(rowid, code, source_file, taxonomy_kind)
    VALUES (new.id, new.code, new.source_file, new.taxonomy_kind);
END;

CREATE INDEX IF NOT EXISTS idx_snippets_taxonomy ON snippets(taxonomy_kind);
CREATE INDEX IF NOT EXISTS idx_snippets_language ON snippets(language);
"""
