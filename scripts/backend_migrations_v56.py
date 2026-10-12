"""Migration v56: the artifact graph (artifacts, symbols, edges).

FROZEN LITERAL, NOT AN IMPORT. `backend_schema_graph` describes the CURRENT
cumulative shape and will evolve; this module must keep describing what v56
actually shipped. Importing the schema constants by reference would make a
later edit retroactively change what this migration did -- the defect that
`backend_migrations_v52` had to be rewritten to remove.

Brand-new tables with their own indexes, so no guarded postseed is needed: the
unconditional DDL block in `init_schema` can create them on a fresh database
without touching anything that already exists.
"""

from __future__ import annotations

MIGRATION_V56: list[str] = [
    """CREATE TABLE IF NOT EXISTS artifacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL CHECK(kind IN ('code', 'doc', 'test', 'config', 'data', 'other')),
        content_hash TEXT NOT NULL,
        indexed_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind)",
    """CREATE TABLE IF NOT EXISTS artifact_symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        line INTEGER,
        UNIQUE(artifact_id, name)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_artifact_symbols_name ON artifact_symbols(name)",
    """CREATE TABLE IF NOT EXISTS artifact_edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
        target_artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
        relation TEXT NOT NULL CHECK(relation IN ('co_changes', 'covers', 'documents', 'references', 'defines', 'implements')),
        layer TEXT NOT NULL CHECK(layer IN ('git_cochange', 'declared_crosscutting', 'declared_relevant_files', 'declared_scope_paths', 'declared_renar')),
        confidence REAL NOT NULL,
        observations INTEGER NOT NULL DEFAULT 1,
        source_ref TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(source_artifact_id, target_artifact_id, relation, layer)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_artifact_edges_source ON artifact_edges(source_artifact_id)",
    "CREATE INDEX IF NOT EXISTS idx_artifact_edges_target ON artifact_edges(target_artifact_id)",
    "CREATE INDEX IF NOT EXISTS idx_artifact_edges_layer ON artifact_edges(layer)",
]
