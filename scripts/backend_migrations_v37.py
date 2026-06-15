"""v37 migration SQL — dedicated snippets store (v15-snippet-table).

Held in its own module to keep backend_migrations.py under the 400-line
filesize gate. ``MIGRATION_V37`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[37]. Purely additive — new tables only,
no ALTER on any existing table.

Structurally mirrors backend_schema_snippets.SNIPPETS_SQL (fresh-DB path); the
migration test asserts the same tables/triggers exist on an upgraded DB.
"""

from __future__ import annotations

MIGRATION_V37: list[str] = [
    """CREATE TABLE IF NOT EXISTS snippets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hash TEXT NOT NULL UNIQUE,
        language TEXT NOT NULL,
        code TEXT NOT NULL,
        source_file TEXT,
        source_lines TEXT,
        taxonomy_kind TEXT,
        -- fts_rank: cached clustering/relevance score, NULL until the AST
        -- detector scores a cluster.
        fts_rank REAL,
        created_at TEXT NOT NULL
    )""",
    """CREATE VIRTUAL TABLE IF NOT EXISTS fts_snippets USING fts5(
        code, source_file, taxonomy_kind,
        content='snippets', content_rowid='id'
    )""",
    """CREATE TRIGGER IF NOT EXISTS snippets_ai AFTER INSERT ON snippets BEGIN
        INSERT INTO fts_snippets(rowid, code, source_file, taxonomy_kind)
        VALUES (new.id, new.code, new.source_file, new.taxonomy_kind);
    END""",
    """CREATE TRIGGER IF NOT EXISTS snippets_ad AFTER DELETE ON snippets BEGIN
        INSERT INTO fts_snippets(fts_snippets, rowid, code, source_file, taxonomy_kind)
        VALUES ('delete', old.id, old.code, old.source_file, old.taxonomy_kind);
    END""",
    """CREATE TRIGGER IF NOT EXISTS snippets_au AFTER UPDATE ON snippets BEGIN
        INSERT INTO fts_snippets(fts_snippets, rowid, code, source_file, taxonomy_kind)
        VALUES ('delete', old.id, old.code, old.source_file, old.taxonomy_kind);
        INSERT INTO fts_snippets(rowid, code, source_file, taxonomy_kind)
        VALUES (new.id, new.code, new.source_file, new.taxonomy_kind);
    END""",
    "CREATE INDEX IF NOT EXISTS idx_snippets_taxonomy ON snippets(taxonomy_kind)",
    "CREATE INDEX IF NOT EXISTS idx_snippets_language ON snippets(language)",
]
